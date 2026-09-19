"""kml_roi 推理输入的预处理适配层。

把 interface/analysis.handle() 的「目录 + 文件名」语义适配到 kml_roi 的单文件
GeoTIFF 输入上：在本次推理的独立临时目录内渲染 RGB、串起预处理步骤、再把产物
写回保留原始 CRS/transform 的 GeoTIFF，作为切瓦片输入。原文件只读不写。

RGB 渲染复用 tiff_processor.read_tiff_as_rgb —— 与切瓦片链路（tif_to_png）完全
一致，因此预处理只影响推理看到的像素，不引入新的波段/量化语义，也不改变输出
目录结构与 fid 组织。
"""

from pathlib import Path
from typing import Tuple

import cv2
import rasterio

from applications.common.utils.tiff_processor import MAX_TIFF_SIZE_MB, read_tiff_as_rgb

# 上传硬上限（8GB）：切片推理路径逐窗口读取/逐行拼接，内存与影像大小解耦；
# 图像增强/降噪路径仍受 MAX_TIFF_SIZE_MB（500MB）约束（整图读内存）
MAX_UPLOAD_TIFF_SIZE_MB = 8192
from applications.interface.analysis import handle


def preprocess_tif_for_inference(
    tif_path: Path,
    base_dir: Path,
    prehandle: int = 0,
    denoise: int = 0,
) -> Path:
    """对单个输入 tif 应用预处理，返回产物路径。

    prehandle/denoise 均为 0 时直接返回原路径（零行为变化，不创建任何目录）。
    fun_type 映射（与老接口一致）：2→CLAHE、3→中值滤波、4→锐化、5→高斯滤波。
    """
    steps = [int(step) for step in (prehandle, denoise) if int(step)]
    if not steps:
        return tif_path

    tif_path = Path(tif_path)

    # 尺寸防护（2026-09-16 审查 P2-5 最小版）：预处理在 Flask 请求线程内经
    # read_tiff_as_rgb 整图读内存（两份全图副本 + 全尺寸 PNG 往返），超阈值
    # 输入直接以业务 ValueError 拒绝（端点映射 400 明确报错），不做子进程化。
    # 检查必须发生在任何读内存/写盘动作之前；prehandle=denoise=0 的默认路径
    # 在上方已短路返回，不受影响。阈值沿用 read_tiff_as_rgb 的 MAX_TIFF_SIZE_MB。
    file_size_mb = tif_path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_TIFF_SIZE_MB:
        raise ValueError(
            f"预处理输入影像过大: {file_size_mb:.1f}MB 超过上限 {MAX_TIFF_SIZE_MB}MB。"
            "大影像请关闭图像增强/降噪（不勾选即可按切片模式正常推理），"
            "或先裁剪至 500MB 内再启用预处理"
        )

    base_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(tif_path) as src:
        profile = src.profile.copy()

    rgb = read_tiff_as_rgb(str(tif_path))

    stage_root = base_dir / "stages"
    current_dir = stage_root / "step0"
    current_dir.mkdir(parents=True, exist_ok=True)
    current_name = "input.png"
    if not cv2.imwrite(str(current_dir / current_name), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
        raise RuntimeError(f"预处理中间产物写入失败: {current_dir / current_name}")

    for index, step in enumerate(steps, start=1):
        output_dir = stage_root / f"step{index}"
        output_dir.mkdir(parents=True, exist_ok=True)
        names = handle(step, [current_name], str(current_dir), str(output_dir))
        if not names:
            raise RuntimeError(f"预处理未返回产物: fun_type={step}")
        current_name = names[0]
        current_dir = output_dir

    processed = cv2.imread(str(current_dir / current_name), cv2.IMREAD_COLOR)
    if processed is None:
        raise RuntimeError(f"预处理产物无法读回: {current_dir / current_name}")
    processed_rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)

    out_path = base_dir / f"preprocessed{tif_path.suffix or '.tif'}"
    profile.update(count=3, dtype="uint8", compress="lzw", nodata=None)
    with rasterio.open(out_path, "w", **profile) as dst:
        for band_index in range(3):
            dst.write(processed_rgb[:, :, band_index], band_index + 1)
    return out_path


def preprocess_inference_inputs(
    *,
    old_tif_path: str,
    new_tif_path: str,
    base_dir: Path,
    prehandle: int = 0,
    denoise: int = 0,
) -> Tuple[str, str]:
    """把两期推理输入复制到独立临时目录并应用预处理，返回切瓦片应使用的路径。

    两期为同一文件时只预处理一次；prehandle/denoise 均为 0 时原样返回，
    不触碰文件系统（与历史行为完全一致）。
    """
    if not int(prehandle or 0) and not int(denoise or 0):
        return old_tif_path, new_tif_path

    old_product = preprocess_tif_for_inference(
        Path(old_tif_path), base_dir / "old", prehandle=prehandle, denoise=denoise
    )
    if Path(new_tif_path).resolve() == Path(old_tif_path).resolve():
        new_product = old_product
    else:
        new_product = preprocess_tif_for_inference(
            Path(new_tif_path), base_dir / "new", prehandle=prehandle, denoise=denoise
        )
    return str(old_product), str(new_product)
