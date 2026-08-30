#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Long-lived local MMSeg worker for the Jiangxi standalone GPU runtime."""

from __future__ import annotations

import argparse
import errno
import json
import os
import signal
import socket
import stat
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict


backend_root = Path(__file__).resolve().parents[2]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))


DEFAULT_WORKER_SOCKET = "/tmp/jiangxi-mmseg-worker.sock"
MAX_MESSAGE_BYTES = 1024 * 1024


class WorkerUnavailableError(RuntimeError):
    """Raised when a configured GPU worker cannot be reached."""


def _read_message(connection: socket.socket) -> Dict[str, Any]:
    chunks = bytearray()
    while b"\n" not in chunks:
        data = connection.recv(64 * 1024)
        if not data:
            break
        chunks.extend(data)
        if len(chunks) > MAX_MESSAGE_BYTES:
            raise ValueError("Worker 请求超过允许大小")

    line = bytes(chunks).split(b"\n", 1)[0].strip()
    if not line:
        raise ValueError("Worker 请求为空")
    try:
        payload = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Worker JSON 无效：{exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Worker JSON 请求必须是对象")
    return payload


def _send_message(connection: socket.socket, payload: Dict[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    connection.sendall(encoded)


def _remove_stale_socket(socket_path: str) -> Path:
    path = Path(socket_path)
    if not path.parent.is_dir():
        raise RuntimeError(f"GPU 推理 Worker Socket 目录不存在：{path.parent}")
    if os.path.lexists(path):
        mode = os.lstat(path).st_mode
        if not stat.S_ISSOCK(mode):
            raise RuntimeError(f"GPU 推理 Worker Socket 路径不是 Socket：{path}")
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client.settimeout(0.2)
            client.connect(str(path))
        except OSError as exc:
            if exc.errno not in {errno.ECONNREFUSED, errno.ENOENT}:
                raise RuntimeError(
                    f"无法确认现有 GPU 推理 Worker Socket 状态：{path}（{exc}）"
                ) from exc
        else:
            raise RuntimeError(f"GPU 推理 Worker 已在运行：{path}")
        finally:
            client.close()
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    return path


def request_worker(
    socket_path: str,
    payload: Dict[str, Any],
    *,
    timeout: float = 1200.0,
) -> Dict[str, Any]:
    """Send one internal request to the locally running worker."""
    if not socket_path:
        raise WorkerUnavailableError("GPU 推理 Worker 不可用：未配置 Socket 路径")
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(timeout)
            client.connect(socket_path)
            _send_message(client, payload)
            response = _read_message(client)
    except (OSError, ValueError) as exc:
        raise WorkerUnavailableError(
            f"GPU 推理 Worker 不可用：{socket_path}（{exc}）"
        ) from exc
    return response


def ping_worker(socket_path: str, *, timeout: float = 2.0) -> Dict[str, Any]:
    response = request_worker(socket_path, {"action": "ping"}, timeout=timeout)
    if response.get("status") != "ok" or not response.get("model_ready"):
        raise WorkerUnavailableError(
            "GPU 推理 Worker 不可用：Worker 未报告已加载模型"
        )
    return response


class MmsegWorker:
    """A single-threaded request handler around one already-loaded MMSeg model."""

    def __init__(
        self,
        *,
        model: Any,
        runtime: Dict[str, Any],
        inference_fn: Callable[..., Dict[str, Any]] | None = None,
    ) -> None:
        self.model = model
        self.runtime = dict(runtime)
        self.inference_fn = inference_fn or self._run_loaded_model_inference

    def _run_loaded_model_inference(self, **kwargs: Any) -> Dict[str, Any]:
        from applications.interface.mmseg_segmentation import run_loaded_model_inference

        return run_loaded_model_inference(**kwargs)

    def _ping_response(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "model_ready": True,
            "asset_validation_passed": True,
            "runtime": dict(self.runtime),
        }

    @staticmethod
    def _queue_wait_seconds(payload: Dict[str, Any]) -> float:
        try:
            submitted_at = float(payload.get("submitted_at", time.time()))
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, time.time() - submitted_at)

    def handle_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        action = payload.get("action") if isinstance(payload, dict) else None
        if action == "ping":
            return self._ping_response()
        if action != "infer":
            return {"status": "error", "error": f"未知 Worker 动作：{action}"}

        input_dir = str(payload.get("input_dir") or "").strip()
        output_dir = str(payload.get("output_dir") or "").strip()
        file_names = payload.get("file_names")
        if not input_dir or not output_dir:
            return {"status": "error", "error": "Worker 推理请求缺少输入或输出目录"}
        if not isinstance(file_names, list) or not all(
            isinstance(name, str) and name.strip() for name in file_names
        ):
            return {"status": "error", "error": "Worker 推理请求缺少有效文件名列表"}

        try:
            result = self.inference_fn(
                model=self.model,
                input_dir=input_dir,
                output_dir=output_dir,
                file_names=[name.strip() for name in file_names],
                device=self.runtime.get("effective_device", "cuda:0"),
                opacity=float(payload.get("opacity", 0.3)),
                runtime=dict(self.runtime),
            )
            if not isinstance(result, dict):
                raise RuntimeError("Worker 推理返回值必须是对象")
            response = dict(result)
            result_runtime = dict(response.get("runtime") or {})
            result_runtime.setdefault(
                "effective_device", self.runtime.get("effective_device", "cuda:0")
            )
            result_runtime["queue_wait_seconds"] = self._queue_wait_seconds(payload)
            result_runtime["model_load_once"] = True
            response["runtime"] = result_runtime
            return response
        except Exception as exc:
            return {"status": "error", "error": f"GPU 推理 Worker 执行失败：{exc}"}


def build_model_worker(model_id: str, device: str) -> MmsegWorker:
    """Validate all model assets once, load one GPU model, then expose it to the socket."""
    from applications.interface.inference_device import resolve_inference_device
    from applications.interface.mmseg_inference_caller import get_model_paths
    from applications.interface.mmseg_segmentation import _validate_loaded_model_contract
    from mmseg.apis import init_model

    runtime = resolve_inference_device(device)
    if runtime["effective_device"] != "cuda:0":
        raise RuntimeError("常驻 MMSeg Worker 仅支持 cuda:0")

    config_path, checkpoint_path = get_model_paths(model_id)
    print(
        f"[MMSeg-Worker] loading model once from {checkpoint_path}",
        file=sys.stderr,
        flush=True,
    )
    model = init_model(config_path, checkpoint_path, device=runtime["effective_device"])
    _validate_loaded_model_contract(model)
    print("[MMSeg-Worker] model ready", file=sys.stderr, flush=True)
    return MmsegWorker(model=model, runtime=runtime)


def serve_worker(socket_path: str, worker: MmsegWorker) -> None:
    """Serve requests serially so the GPU always hosts exactly one loaded model."""
    path = _remove_stale_socket(socket_path)
    stopping = False

    def request_stop(_signum, _frame) -> None:
        nonlocal stopping
        stopping = True

    previous_handlers = {}
    for signum in (signal.SIGTERM, signal.SIGINT):
        previous_handlers[signum] = signal.signal(signum, request_stop)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(str(path))
        os.chmod(path, 0o600)
        server.listen(16)
        server.settimeout(0.5)
        print(f"[MMSeg-Worker] listening on {path}", file=sys.stderr, flush=True)
        while not stopping:
            try:
                connection, _ = server.accept()
            except socket.timeout:
                continue
            with connection:
                try:
                    request = _read_message(connection)
                    response = worker.handle_request(request)
                except Exception as exc:
                    response = {
                        "status": "error",
                        "error": f"GPU 推理 Worker 请求无效：{exc}",
                    }
                _send_message(connection, response)
    finally:
        server.close()
        if os.path.lexists(path) and stat.S_ISSOCK(os.lstat(path).st_mode):
            path.unlink()
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Jiangxi persistent MMSeg GPU worker")
    parser.add_argument("--socket", default=os.getenv("JIANGXI_MMSEG_WORKER_SOCKET", DEFAULT_WORKER_SOCKET))
    parser.add_argument("--model-id", default="cc-ln/CUGRS")
    parser.add_argument("--device", default=os.getenv("JIANGXI_INFERENCE_DEVICE", "cpu"))
    parser.add_argument("--ping", action="store_true")
    parser.add_argument("--expect-device", default="")
    args = parser.parse_args()

    if args.ping:
        response = ping_worker(args.socket)
        expected_device = args.expect_device.strip().lower()
        if expected_device == "cuda":
            expected_device = "cuda:0"
        actual_device = str(
            (response.get("runtime") or {}).get("effective_device", "")
        ).lower()
        if expected_device and actual_device != expected_device:
            raise WorkerUnavailableError(
                f"GPU 推理 Worker 设备不匹配：{actual_device} != {expected_device}"
            )
        print(json.dumps(response, ensure_ascii=False))
        return 0

    worker = build_model_worker(args.model_id, args.device)
    serve_worker(args.socket, worker)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[MMSeg-Worker] {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
