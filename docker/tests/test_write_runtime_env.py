"""Runtime environment regression tests."""

import importlib.util
import os
import re
import shutil
import subprocess
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


def _find_python310_command():
    """定位真实 Python 3.10 解释器，返回命令前缀列表；找不到返回 None。

    容器内权威跑法本身是 3.10，直接用 sys.executable；宿主 3.12+ 时 Windows 找
    `py -3.10`，POSIX 找 `python3.10`（再退到版本恰为 3.10 的 python3）。
    """
    if sys.version_info[:2] == (3, 10):
        return [sys.executable]
    candidates = []
    if os.name == "nt":
        if shutil.which("py"):
            candidates.append(["py", "-3.10"])
    else:
        candidates.append(["python3.10"])
        if shutil.which("python3"):
            candidates.append(["python3"])
    for command in candidates:
        try:
            probe = subprocess.run(
                command + ["-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "3.10":
            return command
    return None


class RuntimeSourceCompatibilityTests(unittest.TestCase):
    """write-runtime-env.py 必须能被真实 Python 3.10 解释器编译。

    2026-09-14 教训（testing_playbook T22 / 23c71a P0）：f-string 嵌套同类引号
    在 3.12+ 按 PEP 701 放行，镜像内 3.10 直接 SyntaxError、整机起不来。
    2026-09-16 修正：ast.parse(source, feature_version=(3, 10)) 在 3.12+ 宿主
    拦不住该形态（PEP 701 改变了 f-string 的文法，feature_version 不回退它，
    3.14 实测 ACCEPTED）——旧守卫是假绿。因此改为子进程调用真实 3.10 解释器
    compile；并用嵌套同类引号 fixture 元测试守卫本身确实能 reject。
    """

    @classmethod
    def setUpClass(cls):
        cls.python310_command = _find_python310_command()

    def setUp(self):
        if self.python310_command is None:
            print(
                "[WARN] 未找到真实 Python 3.10 解释器，write-runtime-env.py 的"
                " 3.10 语法守卫本轮未执行（Windows 需 py -3.10；Linux 需 python3.10"
                " 或容器内 3.10）——宿主 3.12+ 的 ast feature_version 已证实是假绿，"
                "请安装 3.10 后复跑",
                file=sys.stderr,
            )
            self.skipTest("no real Python 3.10 interpreter available")

    def _compile_with_python310(self, source):
        return subprocess.run(
            self.python310_command
            + [
                "-c",
                "import sys; compile(sys.stdin.read(), 'write-runtime-env.py', 'exec')",
            ],
            input=source.encode("utf-8"),
            capture_output=True,
            timeout=60,
        )

    def test_source_compiles_under_real_python_3_10(self):
        result = self._compile_with_python310(
            MODULE_PATH.read_text(encoding="utf-8")
        )
        self.assertEqual(
            result.returncode,
            0,
            "write-runtime-env.py must compile under real Python 3.10:\n"
            + result.stderr.decode("utf-8", "replace"),
        )

    def test_guard_rejects_nested_same_quote_fstring_fixture(self):
        # 元测试：守卫必须能 reject 正是 T22 那个 P0 形态的嵌套同类引号 f-string
        #（3.12+ 宿主 ast.parse feature_version 拦不住它），否则上一个用例
        # 只是又一次假绿
        offender = "v = f'{os.environ.get('X', '')}'\n"
        result = self._compile_with_python310(offender)
        self.assertNotEqual(
            result.returncode,
            0,
            "3.10 guard must reject nested same-quote f-string (PEP 701 form)",
        )
        self.assertIn("SyntaxError", result.stderr.decode("utf-8", "replace"))


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

    def test_malformed_local_tile_url_falls_back_to_default_template(self):
        # 历史 env 血统污染形态（T-tile 教训）：模板尾部被拼接出多余的
        # `{x}/{y}.png}`，坏模板会让整层本地瓦片 404——必须回退默认 XYZ 模板
        bad_value = "/tiles/{z}/{x}/{y}.png/{x}/{y}.png}"
        outputs = run_main_with_environment({"MINER_LOCAL_TILE_URL": bad_value})
        miner_env = outputs["/app/miner/.env"]
        self._assert_exact_line(
            miner_env, "VITE_MINER_LOCAL_TILE_URL=/tiles/{z}/{x}/{y}.png"
        )
        self.assertNotIn(bad_value, miner_env)

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
