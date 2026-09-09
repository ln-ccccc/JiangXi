import os
import re
from pathlib import Path

import yaml


CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", "/app/config.yaml"))


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def write_text(path, content):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def main():
    cfg = load_config()
    host_cfg = cfg.get("host", {})
    port_cfg = cfg.get("port", {})
    miner_cfg = cfg.get("miner", {})

    backend_host = host_cfg.get("backend", "0.0.0.0")
    backend_port = int(port_cfg.get("backend", 5008))
    miner_enabled = "true" if miner_cfg.get("enabled", False) else "false"
    backend_url = os.environ.get("VUE_APP_BACKEND_URL", "")
    miner_url = os.environ.get("VUE_APP_MINER_URL", "")
    inference_device = os.environ.get("JIANGXI_INFERENCE_DEVICE", "cpu").strip().lower() or "cpu"
    # 本地瓦片模板严格校验：只接受标准 XYZ 形态（/tiles/{z}/{x}/{y}.png，层级字母可换），
    # 其余任何值（历史 env 血统污染/损坏串）一律回退默认模板，防止坏模板导致整层瓦片 404
    local_tile_url_raw = os.environ.get("MINER_LOCAL_TILE_URL", "").strip()
    if re.fullmatch(r"/tiles/\{[a-z0-9]+\}/\{[a-z0-9]+\}/\{[a-z0-9]+\}\.png", local_tile_url_raw):
        local_tile_url = local_tile_url_raw
    else:
        local_tile_url = "/tiles/{z}/{x}/{y}.png"

    write_text(
        "/app/frontend/.env",
        "\n".join(
            [
                f"VUE_APP_BACKEND_PORT = {backend_port}",
                "VUE_APP_BACKEND_IP =",
                f"VUE_APP_BACKEND_URL={backend_url}",
                f"VUE_APP_MINER_ENABLED = {miner_enabled}",
                f"VUE_APP_MINER_URL={miner_url}",
                f"VUE_APP_JIANGXI_INFERENCE_DEVICE={inference_device}",
                "",
            ]
        ),
    )

    miner_api_base_url = os.environ.get("VITE_MINER_API_BASE_URL", "")
    geoview_url = os.environ.get("VITE_GEOVIEW_URL", "")
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
        f'VITE_GEOVIEW_URL="{geoview_url}"',
        f"VITE_MINER_API_BASE_URL={miner_api_base_url}",
        f"VITE_MINER_MAP_PROVIDER={os.environ.get('MINER_MAP_PROVIDER', 'gaode')}",
        f"VITE_TDT_KEY={os.environ.get('MINER_TDT_KEY', '')}",
        f"VITE_MINER_LOCAL_TILE_URL={local_tile_url}",
        f"VITE_MINER_LOCAL_TMS={os.environ.get('MINER_LOCAL_TMS', '0')}",
        f"VITE_MINER_LOCAL_MAX_NATIVE_ZOOM={local_max_native_zoom}",
        f"VITE_MINER_LOCAL_MIN_NATIVE_ZOOM={local_min_native_zoom}",
        f"VITE_JIANGXI_INFERENCE_DEVICE={inference_device}",
        "",
    ]
    write_text("/app/miner/.env", "\n".join(miner_env))


if __name__ == "__main__":
    main()
