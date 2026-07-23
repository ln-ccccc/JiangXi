#!/usr/bin/env python3
"""Create and audit a Jiangxi state-dict-only MMSeg inference checkpoint."""

import argparse
import hashlib
import json
from pathlib import Path

import torch


JIANGXI_CLASSES = (
    "grassland",
    "forest",
    "building",
    "road",
    "bareground",
    "water",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_checkpoint(path: Path):
    checkpoint = torch.load(
        str(path),
        map_location="cpu",
        mmap=True,
        weights_only=False,
    )
    if not isinstance(checkpoint, dict) or not isinstance(
        checkpoint.get("state_dict"), dict
    ):
        raise RuntimeError(f"checkpoint 缺少 state_dict：{path}")
    return checkpoint


def validate_dataset_meta(checkpoint: dict, path: Path) -> dict:
    dataset_meta = (checkpoint.get("meta") or {}).get("dataset_meta") or {}
    classes = tuple(dataset_meta.get("classes") or ())
    if classes != JIANGXI_CLASSES:
        raise RuntimeError(
            f"checkpoint 六类顺序不匹配 {path}：{','.join(classes)}"
        )
    return dataset_meta


def compare_state_dicts(source: dict, output: dict) -> dict:
    source_keys = list(source)
    output_keys = list(output)
    if source_keys != output_keys:
        missing = sorted(set(source_keys) - set(output_keys))
        extra = sorted(set(output_keys) - set(source_keys))
        raise RuntimeError(
            f"state_dict 键不一致：missing={missing[:10]}, extra={extra[:10]}"
        )

    tensor_count = 0
    non_tensor_count = 0
    for key in source_keys:
        source_value = source[key]
        output_value = output[key]
        if isinstance(source_value, torch.Tensor):
            tensor_count += 1
            if not isinstance(output_value, torch.Tensor):
                raise RuntimeError(f"参数类型不一致：{key}")
            if source_value.shape != output_value.shape:
                raise RuntimeError(f"参数形状不一致：{key}")
            if source_value.dtype != output_value.dtype:
                raise RuntimeError(f"参数类型不一致：{key}")
            if not torch.equal(source_value, output_value):
                raise RuntimeError(f"参数值不一致：{key}")
        else:
            non_tensor_count += 1
            if source_value != output_value:
                raise RuntimeError(f"非张量状态不一致：{key}")
    return {
        "state_dict_count": len(source_keys),
        "tensor_count": tensor_count,
        "non_tensor_count": non_tensor_count,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="迁移并审计江西 MMSeg 推理 checkpoint"
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--expected-source-sha256", default="")
    parser.add_argument("--expected-output-sha256", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"源 checkpoint 不存在：{source}")
    if args.verify_only and not output.is_file():
        raise FileNotFoundError(f"推理 checkpoint 不存在：{output}")
    if not args.verify_only and output.exists() and not args.force:
        raise FileExistsError(f"输出已存在，请使用 --force 明确覆盖：{output}")

    source_hash = file_sha256(source)
    if (
        args.expected_source_sha256
        and source_hash != args.expected_source_sha256.lower()
    ):
        raise RuntimeError("源 checkpoint SHA-256 不匹配")

    source_checkpoint = load_checkpoint(source)
    dataset_meta = validate_dataset_meta(source_checkpoint, source)
    if not args.verify_only:
        output.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "meta": {
                    "epoch": (source_checkpoint.get("meta") or {}).get("epoch"),
                    "dataset_meta": dataset_meta,
                    "region": "jiangxi",
                    "source_checkpoint_sha256": source_hash,
                },
                "state_dict": source_checkpoint["state_dict"],
            },
            str(output),
        )

    output_hash = file_sha256(output)
    if (
        args.expected_output_sha256
        and output_hash != args.expected_output_sha256.lower()
    ):
        raise RuntimeError("推理 checkpoint SHA-256 不匹配")

    output_checkpoint = load_checkpoint(output)
    validate_dataset_meta(output_checkpoint, output)
    if set(output_checkpoint) != {"meta", "state_dict"}:
        raise RuntimeError(
            "推理 checkpoint 顶层只能包含 meta 和 state_dict："
            + ",".join(output_checkpoint)
        )
    comparison = compare_state_dicts(
        source_checkpoint["state_dict"],
        output_checkpoint["state_dict"],
    )
    print(
        json.dumps(
            {
                "status": "verified",
                "source": str(source),
                "output": str(output),
                "source_sha256": source_hash,
                "output_sha256": output_hash,
                "classes": list(JIANGXI_CLASSES),
                **comparison,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
