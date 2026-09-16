import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from applications.kml_roi.kml_merge import merge_kml_increment
from applications.kml_roi.preprocess import preprocess_inference_inputs
from applications.region_source import resolve_default_jiangxi_kmz
from applications.interface.inference_device import resolve_inference_device


def _parse_last_json(stdout_text: str) -> dict:
    parsed = None
    for line in reversed((stdout_text or "").splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
            break
        except Exception:
            continue
    if parsed is None:
        parsed = {"status": "completed", "message": "no json output"}
    return parsed


def _acquire_inference_lock_for_merge(output_root):
    """父进程侧获取与子进程相同的跨进程推理锁（fcntl 可用时）。

    KML 增量合并在父进程对共享 runtime.kml 读-改-写，而推理互斥锁原先在
    子进程 kml_roi_infer.py 才获取——并发请求可在锁外互相覆盖合并结果，
    先启动的子进程还可能读到非本次请求的合并产物。现在合并挪进与子进程
    同一持锁区：父进程先取锁，合并后把锁 fd 传给子进程复用（--lock_fd，
    子进程跳过重复 flock），直到推理结束才由父进程 finally 释放。
    fcntl 不可用（Windows 开发机）时返回 None，由 merge 的原子写兜底。
    """
    try:
        import fcntl
    except ImportError:
        return None
    lock_path = Path(output_root) / ".kml_roi_infer.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "w")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise ValueError("已有一个图斑推理任务正在执行，请等待完成后再提交")
    return handle


def run_kml_roi_inference(
    *,
    old_tif_path: str,
    new_tif_path: Optional[str] = None,
    kml_path: Optional[str] = None,
    output_root: Optional[str] = None,
    device: str = "cpu",
    limit: int = 0,
    year: str = "",
    old_year: str = "",
    new_year: str = "",
    manifest_path: Optional[str] = None,
    prehandle: int = 0,
    denoise: int = 0,
) -> dict:
    if not old_tif_path:
        raise ValueError("缺少 old_tif_path")

    new_tif_path = new_tif_path or old_tif_path
    if not os.path.exists(old_tif_path):
        raise FileNotFoundError(f"old_tif_path 不存在: {old_tif_path}")
    if not new_tif_path or not os.path.exists(new_tif_path):
        raise FileNotFoundError(f"new_tif_path 不存在: {new_tif_path}")

    prehandle = int(prehandle or 0)
    denoise = int(denoise or 0)

    backend_root = Path(__file__).resolve().parents[2]
    repo_root = backend_root.parent
    script_path = backend_root / "kml_roi_infer.py"
    if not script_path.exists():
        raise FileNotFoundError(f"脚本不存在: {script_path}")

    default_kml_path = resolve_default_jiangxi_kmz()
    input_kml_path = Path(kml_path).expanduser().resolve() if kml_path else default_kml_path
    output_root = output_root or os.getenv("MINER_CHANGE_OUTPUT_ROOT") or str(repo_root / "miner" / "change_matrix_outputs")
    effective_kml_path = default_kml_path
    kml_update = {"inserted": 0, "updated": 0, "skipped": 0, "fids": [], "kml_path": str(default_kml_path)}
    parent_lock = None
    try:
        if input_kml_path != default_kml_path:
            # 合并共享 runtime.kml 的读-改-写必须发生在推理锁内（见
            # _acquire_inference_lock_for_merge），否则并发合并互相覆盖、
            # 子进程可能以别的请求的合并结果为推理输入。
            parent_lock = _acquire_inference_lock_for_merge(output_root)
            merge_target = default_kml_path
            if default_kml_path.suffix.lower() == ".kmz":
                merge_target = repo_root / "miner" / "Jiangxi_NaturalMine.runtime.kml"
            kml_update = merge_kml_increment(default_kml_path, input_kml_path, output_kml=merge_target)
            effective_kml_path = Path(kml_update["kml_path"])
        kml_path = str(effective_kml_path)
        if not os.path.exists(kml_path):
            raise FileNotFoundError(f"kml_path 不存在: {kml_path}")

        manifest_path = Path(
            manifest_path
            or os.getenv("JIANGXI_ASSET_MANIFEST_PATH")
            or repo_root / "docker" / "standalone" / "runtime_data" / "Jiangxi_asset_manifest.json"
        ).expanduser().resolve()
        if not manifest_path.is_file():
            raise FileNotFoundError(f"江西资产 manifest 不存在: {manifest_path}")

        runtime = resolve_inference_device(device)

        with tempfile.TemporaryDirectory(prefix="kml-roi-infer-") as work_dir:
            # prehandle/denoise 只影响推理输入，产物必须放在 work_dir 之外的独立临时目录：
            # 子进程 pipeline.py 启动时会 rmtree(work_dir) 清空工作目录（防上一轮残留），
            # 写在 work_dir 内的预处理产物会被删掉，导致切瓦片时 "No such file or directory"
            preprocess_dir = None
            if int(prehandle or 0) or int(denoise or 0):
                preprocess_dir = tempfile.mkdtemp(prefix="kml-roi-preprocess-")
                old_tif_path, new_tif_path = preprocess_inference_inputs(
                    old_tif_path=old_tif_path,
                    new_tif_path=new_tif_path,
                    base_dir=Path(preprocess_dir),
                    prehandle=prehandle,
                    denoise=denoise,
                )
            try:
                result = _run_inference_subprocess(
                    old_tif_path=old_tif_path,
                    new_tif_path=new_tif_path,
                    kml_path=kml_path,
                    output_root=output_root,
                    manifest_path=manifest_path,
                    runtime=runtime,
                    year=year,
                    old_year=old_year,
                    new_year=new_year,
                    limit=limit,
                    work_dir=work_dir,
                    script_path=script_path,
                    backend_root=backend_root,
                    parent_lock=parent_lock,
                )
            finally:
                if preprocess_dir:
                    shutil.rmtree(preprocess_dir, ignore_errors=True)
            result["kml_update"] = kml_update
            return result
    finally:
        # 无论哪条路径退出（异常/合并失败/子进程结束），锁都在父进程收口释放；
        # 子进程退出关闭继承 fd 不会提前释放锁（锁属于父进程的 open file description）
        if parent_lock is not None:
            parent_lock.close()


def _run_inference_subprocess(
    *,
    old_tif_path,
    new_tif_path,
    kml_path,
    output_root,
    manifest_path,
    runtime,
    year,
    old_year,
    new_year,
    limit,
    work_dir,
    script_path,
    backend_root,
    parent_lock=None,
):
    cmd = [
        os.getenv("PYTHON_EXE") or sys.executable,
        str(script_path),
        "--old_tif",
        str(old_tif_path),
        "--new_tif",
        str(new_tif_path),
        "--kml",
        str(kml_path),
        "--output_root",
        str(output_root),
        "--device",
        runtime["effective_device"],
        "--manifest",
        str(manifest_path),
    ]

    if year:
        cmd.extend(["--year", str(year)])
    else:
        if old_year:
            cmd.extend(["--old_year", str(old_year)])
        if new_year:
            cmd.extend(["--new_year", str(new_year)])
    if int(limit or 0) > 0:
        cmd.extend(["--limit", str(int(limit))])

    cmd.extend(["--work_dir", work_dir])
    popen_kwargs = {}
    if parent_lock is not None:
        # 锁 fd 随子进程传递：子进程复用父进程已持有的锁（--lock_fd），
        # 不再自行 flock（重复取会 busy 自杀）；锁的释放在父进程 finally。
        cmd.extend(["--lock_fd", str(parent_lock.fileno())])
        popen_kwargs["pass_fds"] = (parent_lock.fileno(),)
    try:
        run_res = subprocess.run(
            cmd,
            cwd=str(backend_root),
            capture_output=True,
            text=True,
            timeout=3600,
            **popen_kwargs,
        )
    except Exception as e:
        raise RuntimeError(f"执行失败: {str(e)}") from e

    if run_res.returncode == 3:
        # kml_roi_infer.py 的跨进程推理锁占用退出码：转成业务异常向上透出可读信息
        raise ValueError("已有一个图斑推理任务正在执行，请等待完成后再提交")
    if run_res.returncode != 0:
        err = (run_res.stderr or run_res.stdout or "").strip()
        raise RuntimeError(f"执行失败: {err[:500]}")

    return _parse_last_json(run_res.stdout or "")
