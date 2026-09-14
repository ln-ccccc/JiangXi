import os
import re
import sys
from pathlib import Path

import yaml


CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", "/app/config.yaml"))

DEFAULT_LOCAL_TILE_URL = "/tiles/{z}/{x}/{y}.png"

# 公网 URL 校验：非空值必须是 http(s) 绝对地址且不含任何空白字符
#（\S+ 天然拒绝内嵌换行/空格，防止坏值注入额外 env 行），否则回退默认
URL_PATTERN = re.compile(r"https?://\S+")


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def write_text(path, content):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def sanitize_env_value(value: str) -> str:
    """剥离 CR/LF：env 文件是按行解析的，值内换行会注入额外的 env 条目。"""
    return re.sub(r"[\r\n]", "", value or "")


def resolve_public_url(raw: str, fallback: str, name: str = "") -> str:
    """非空公网 URL 必须过 http(s) 校验；坏值（含换行、非 http、损坏串）回退默认。

    留空语义保持不变（entrypoint 的 :- 默认值已在上游处理，显式空表示用户要空）。
    坏值回退不打断启动（自愈），但必须写 stderr 留痕，避免静默吞掉配置错误。
    """
    value = (raw or "").strip()
    if not value:
        return ""
    if URL_PATTERN.fullmatch(value):
        return value
    if name:
        print(
            f"[write-runtime-env] rejected invalid {name}={value!r}, falling back to {fallback!r}",
            file=sys.stderr,
        )
    return fallback


def main():
    cfg = load_config()
    host_cfg = cfg.get("host", {})
    port_cfg = cfg.get("port", {})
    miner_cfg = cfg.get("miner", {})

    backend_host = host_cfg.get("backend", "0.0.0.0")
    backend_port = int(port_cfg.get("backend", 5008))
    miner_enabled = "true" if miner_cfg.get("enabled", False) else "false"
    backend_url = resolve_public_url(
        os.environ.get("VUE_APP_BACKEND_URL", ""),
        fallback=f"http://{backend_host}:{backend_port}",
        name="VUE_APP_BACKEND_URL",
    )
    miner_url = resolve_public_url(
        os.environ.get("VUE_APP_MINER_URL", ""),
        fallback="",
        name="VUE_APP_MINER_URL",
    )
    inference_device = os.environ.get("JIANGXI_INFERENCE_DEVICE", "cpu").strip().lower() or "cpu"
    # 本地瓦片模板严格校验：只接受标准 XYZ 形态（/tiles/{z}/{x}/{y}.png，层级字母可换），
    # 其余任何值（历史 env 血统污染/损坏串）一律回退默认模板，防止坏模板导致整层瓦片 404
    local_tile_url_raw = os.environ.get("MINER_LOCAL_TILE_URL", "").strip()
    if re.fullmatch(r"/tiles/\{[a-z0-9]+\}/\{[a-z0-9]+\}/\{[a-z0-9]+\}\.png", local_tile_url_raw):
        local_tile_url = local_tile_url_raw
    else:
        if local_tile_url_raw:
            print(
                f"[write-runtime-env] rejected invalid MINER_LOCAL_TILE_URL={local_tile_url_raw!r}, falling back to {DEFAULT_LOCAL_TILE_URL!r}",
                file=sys.stderr,
            )
        local_tile_url = DEFAULT_LOCAL_TILE_URL

    write_text(
        "/app/frontend/.env",
        "\n".join(
            [
                f"VUE_APP_BACKEND_PORT = {backend_port}",
                "VUE_APP_BACKEND_IP =",
                f"VUE_APP_BACKEND_URL={sanitize_env_value(backend_url)}",
                f"VUE_APP_MINER_ENABLED = {sanitize_env_value(miner_enabled)}",
                f"VUE_APP_MINER_URL={sanitize_env_value(miner_url)}",
                f"VUE_APP_JIANGXI_INFERENCE_DEVICE={sanitize_env_value(inference_device)}",
                "",
            ]
        ),
    )

    geoview_url = resolve_public_url(
        os.environ.get("VITE_GEOVIEW_URL", ""),
        fallback="",
        name="VITE_GEOVIEW_URL",
    )
    miner_api_base_url = os.environ.get("VITE_MINER_API_BASE_URL", "")
    local_max_native_zoom = (
        os.environ.get("VITE_MINER_LOCAL_MAX_NATIVE_ZOOM")
        or os.environ.get("MINER_LOCAL_MAX_NATIVE_ZOOM")
        or os.environ.get("MINER_TILE_MAX_ZOOM")
        or "13"
    )
    local_min_native_zoom = (
        os.environ.get("VITE_MINER_LOCAL_MIN_NATIVE_ZOOM")
        or os.environ.get("MINER_LOCAL_MIN_NATIVE_ZOOM")
        or "8"
    )
    miner_env = [
        f'VITE_GEOVIEW_URL="{sanitize_env_value(geoview_url)}"',
        f"VITE_MINER_API_BASE_URL={sanitize_env_value(miner_api_base_url)}",
        f"VITE_MINER_MAP_PROVIDER={sanitize_env_value(os.environ.get('MINER_MAP_PROVIDER', 'gaode'))}",
        # f-string 定界与内部字符串引号不可同为单引号：镜像内 MMSeg310 是 Python 3.10，
        # 嵌套同类引号 SyntaxError（宿主机 3.12+ 才放行，宿主验证不可代替容器验证）
        f'VITE_TDT_KEY="{sanitize_env_value(os.environ.get("MINER_TDT_KEY", ""))}"',
        f"VITE_MINER_LOCAL_TILE_URL={sanitize_env_value(local_tile_url)}",
        f"VITE_MINER_LOCAL_TMS={sanitize_env_value(os.environ.get('MINER_LOCAL_TMS', '0'))}",
        f"VITE_MINER_LOCAL_MAX_NATIVE_ZOOM={sanitize_env_value(local_max_native_zoom)}",
        f"VITE_MINER_LOCAL_MIN_NATIVE_ZOOM={sanitize_env_value(local_min_native_zoom)}",
        f"VITE_JIANGXI_INFERENCE_DEVICE={sanitize_env_value(inference_device)}",
        "",
    ]
    write_text("/app/miner/.env", "\n".join(miner_env))


if __name__ == "__main__":
    main()
