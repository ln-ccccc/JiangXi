import os
from pathlib import Path


def resolve_runtime_config_path(config_path=None, default_path=None):
    if config_path:
        return Path(config_path)

    configured_path = os.environ.get("CONFIG_PATH")
    if configured_path:
        return Path(configured_path)

    if default_path:
        return Path(default_path)

    return Path(__file__).resolve().parents[1] / "config.yaml"


def load_runtime_config():
    import yaml

    config_path = resolve_runtime_config_path()
    with config_path.open(encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def write_legacy_frontend_env(config, frontend_env_path=None, standalone_mode=None):
    if standalone_mode is None:
        standalone_mode = os.environ.get("STANDALONE_MODE") == "1"
    if standalone_mode:
        return False

    target = Path(frontend_env_path or Path(__file__).resolve().parents[1] / "frontend" / ".env")
    host = config["host"]["backend"]
    backend_ip = host if host != "0.0.0.0" else "localhost"
    access_key = config.get("baidu_map", {}).get("access_key", "")
    target.write_text(
        "VUE_APP_BACKEND_PORT = {}\n"
        "VUE_APP_BACKEND_IP = {}\n"
        "VUE_APP_BAIDU_MAP_ACCESS_KEY = {}".format(
            config["port"]["backend"], backend_ip, access_key
        ),
        encoding="utf-8",
    )
    return True
