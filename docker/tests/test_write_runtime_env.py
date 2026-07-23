"""Runtime environment regression tests."""

import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "write-runtime-env.py"


def load_runtime_env_module():
    # The focused tests replace load_config, so YAML parsing is not required.
    sys.modules.setdefault("yaml", types.ModuleType("yaml"))
    spec = importlib.util.spec_from_file_location("write_runtime_env", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_main_with_environment(environment):
    runtime_env = load_runtime_env_module()
    outputs = {}

    def capture(path, content):
        outputs[path] = content

    config = {
        "host": {"backend": "0.0.0.0"},
        "port": {"backend": 5008},
        "miner": {"enabled": True, "backend_port": 8000},
    }
    with patch.dict(os.environ, environment, clear=True), patch.object(
        runtime_env, "load_config", return_value=config
    ), patch.object(runtime_env, "write_text", side_effect=capture):
        runtime_env.main()
    return outputs


class RuntimePublicUrlTests(unittest.TestCase):
    def test_explicit_jiangxi_public_urls_are_written_for_both_frontends(self):
        outputs = run_main_with_environment(
            {
                "VUE_APP_BACKEND_URL": "http://127.0.0.1:5178/",
                "VUE_APP_MINER_URL": "http://127.0.0.1:4173/",
                "VITE_GEOVIEW_URL": "http://127.0.0.1:4174/",
            }
        )

        frontend_env = outputs["/app/frontend/.env"]
        miner_env = outputs["/app/miner/.env"]
        self.assertIn("VUE_APP_BACKEND_URL=http://127.0.0.1:5178/", frontend_env)
        self.assertIn("VUE_APP_MINER_URL=http://127.0.0.1:4173/", frontend_env)
        self.assertIn('VITE_GEOVIEW_URL="http://127.0.0.1:4174/"', miner_env)

    def test_missing_public_urls_remain_empty_without_generic_port_fallbacks(self):
        outputs = run_main_with_environment({})

        frontend_env = outputs["/app/frontend/.env"]
        miner_env = outputs["/app/miner/.env"]
        self.assertIn("VUE_APP_BACKEND_URL=", frontend_env)
        self.assertIn("VUE_APP_MINER_URL=", frontend_env)
        self.assertIn('VITE_GEOVIEW_URL=""', miner_env)
        self.assertIn("VITE_MINER_LOCAL_TILE_URL=/tiles/{z}/{x}/{y}.png", miner_env)
        combined = frontend_env + miner_env
        self.assertNotIn("http://localhost:3000", combined)
        self.assertNotIn("http://localhost:4000", combined)


if __name__ == "__main__":
    unittest.main()
