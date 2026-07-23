"""Runtime environment regression tests."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "write-runtime-env.py"
BACKEND_APP_PATH = Path(__file__).resolve().parents[2] / "backend" / "app.py"


def load_runtime_env_module():
    # The behavior under test does not require YAML parsing, so avoid a runtime
    # dependency when this focused regression test is run on a host machine.
    sys.modules.setdefault("yaml", types.ModuleType("yaml"))
    spec = importlib.util.spec_from_file_location("write_runtime_env", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ClientHostTests(unittest.TestCase):
    def test_wildcard_backend_host_uses_localhost_for_browser_session(self):
        runtime_env = load_runtime_env_module()

        self.assertEqual(runtime_env.client_host("0.0.0.0"), "localhost")

    def test_backend_startup_keeps_the_same_localhost_session_host(self):
        backend_app = BACKEND_APP_PATH.read_text(encoding="utf-8")

        self.assertIn('else "localhost"', backend_app)


if __name__ == "__main__":
    unittest.main()
