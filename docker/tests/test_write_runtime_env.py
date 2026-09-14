"""Runtime environment regression tests."""

import importlib.util
import os
import re
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

    def test_inference_device_is_written_to_both_frontend_build_environments(self):
        outputs = run_main_with_environment({"JIANGXI_INFERENCE_DEVICE": "cuda:0"})

        self.assertIn("VUE_APP_JIANGXI_INFERENCE_DEVICE=cuda:0", outputs["/app/frontend/.env"])
        self.assertIn("VITE_JIANGXI_INFERENCE_DEVICE=cuda:0", outputs["/app/miner/.env"])

    def test_missing_public_urls_remain_empty_without_generic_port_fallbacks(self):
        outputs = run_main_with_environment({})

        frontend_env = outputs["/app/frontend/.env"]
        miner_env = outputs["/app/miner/.env"]
        self.assertIn("VUE_APP_BACKEND_URL=", frontend_env)
        self.assertIn("VUE_APP_MINER_URL=", frontend_env)
        self.assertIn('VITE_GEOVIEW_URL=""', miner_env)
        self.assertIn("VITE_MINER_MAP_PROVIDER=gaode", miner_env)
        self.assertIn("VITE_MINER_LOCAL_TILE_URL=/tiles/{z}/{x}/{y}.png", miner_env)
        combined = frontend_env + miner_env
        self.assertNotIn("http://localhost:3000", combined)
        self.assertNotIn("http://localhost:4000", combined)


class RuntimeUrlValidationTests(unittest.TestCase):
    """三个公网 URL 的坏值必须回退默认；所有写入值必须清洗 CR/LF。"""

    def _assert_exact_line(self, env_text, line):
        self.assertIsNotNone(
            re.search(rf"^{re.escape(line)}$", env_text, re.MULTILINE),
            f"expected exact line {line!r} in env file",
        )

    def test_malformed_backend_url_falls_back_to_config_host_port(self):
        # 非 http 协议与内嵌换行都是坏值；回退由 config 的 host/port 构造
        for bad_value in ("ftp://10.0.0.1:5008", "http://127.0.0.1:5178/\nEVIL=1"):
            outputs = run_main_with_environment({"VUE_APP_BACKEND_URL": bad_value})
            frontend_env = outputs["/app/frontend/.env"]
            self._assert_exact_line(frontend_env, "VUE_APP_BACKEND_URL=http://0.0.0.0:5008")
            self.assertNotIn("EVIL=1", frontend_env)

    def test_malformed_miner_url_falls_back_to_default_empty(self):
        for bad_value in ("javascript:alert(1)", "http://x\nVUE_APP_BACKEND_URL=http://evil"):
            outputs = run_main_with_environment({"VUE_APP_MINER_URL": bad_value})
            frontend_env = outputs["/app/frontend/.env"]
            self._assert_exact_line(frontend_env, "VUE_APP_MINER_URL=")
            self.assertNotIn("evil", frontend_env)

    def test_malformed_geoview_url_falls_back_to_default_empty(self):
        for bad_value in ("not-a-url", "https ://bad", "http://x\r\nVITE_TDT_KEY=\"evil\""):
            outputs = run_main_with_environment({"VITE_GEOVIEW_URL": bad_value})
            miner_env = outputs["/app/miner/.env"]
            self._assert_exact_line(miner_env, 'VITE_GEOVIEW_URL=""')
            self.assertNotIn("evil", miner_env)

    def test_valid_urls_survive_validation(self):
        outputs = run_main_with_environment(
            {
                "VUE_APP_BACKEND_URL": "http://192.168.1.10:5178/",
                "VUE_APP_MINER_URL": "http://192.168.1.10:4173/",
                "VITE_GEOVIEW_URL": "http://192.168.1.10:4174/",
            }
        )
        self._assert_exact_line(
            outputs["/app/frontend/.env"], "VUE_APP_BACKEND_URL=http://192.168.1.10:5178/"
        )
        self._assert_exact_line(
            outputs["/app/frontend/.env"], "VUE_APP_MINER_URL=http://192.168.1.10:4173/"
        )
        self._assert_exact_line(
            outputs["/app/miner/.env"], 'VITE_GEOVIEW_URL="http://192.168.1.10:4174/"'
        )

    def test_newline_injection_is_sanitized_from_non_url_values(self):
        outputs = run_main_with_environment(
            {
                "MINER_TDT_KEY": "abc\ndef",
                "MINER_MAP_PROVIDER": "gaode\nVITE_MINER_MAP_PROVIDER=evil",
                "VITE_MINER_LOCAL_MAX_NATIVE_ZOOM": "13\nMINER_EXTRA=1",
            }
        )
        miner_env = outputs["/app/miner/.env"]
        lines = miner_env.splitlines()
        self.assertIn('VITE_TDT_KEY="abcdef"', lines)
        self.assertIn("VITE_MINER_MAP_PROVIDER=gaodeVITE_MINER_MAP_PROVIDER=evil", lines)
        self.assertIn("VITE_MINER_LOCAL_MAX_NATIVE_ZOOM=13MINER_EXTRA=1", lines)
        # env 文件任何一行都不可能由换行注入产生新键
        self.assertNotIn("MINER_EXTRA=1", lines)
        self.assertNotIn("def", lines)

    def test_whitespace_only_url_values_stay_empty(self):
        outputs = run_main_with_environment(
            {
                "VUE_APP_BACKEND_URL": "   ",
                "VUE_APP_MINER_URL": "\t\n",
                "VITE_GEOVIEW_URL": " ",
            }
        )
        self._assert_exact_line(outputs["/app/frontend/.env"], "VUE_APP_BACKEND_URL=")
        self._assert_exact_line(outputs["/app/frontend/.env"], "VUE_APP_MINER_URL=")
        self._assert_exact_line(outputs["/app/miner/.env"], 'VITE_GEOVIEW_URL=""')


if __name__ == "__main__":
    unittest.main()
