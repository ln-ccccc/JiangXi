import tempfile
import unittest
from pathlib import Path

try:
    from runtime_frontend_env import (
        resolve_runtime_config_path,
        write_legacy_frontend_env,
    )
except ModuleNotFoundError:
    resolve_runtime_config_path = None
    write_legacy_frontend_env = None


class StandaloneFrontendRuntimeConfigTests(unittest.TestCase):
    def test_runtime_config_helper_is_available(self):
        self.assertIsNotNone(resolve_runtime_config_path)
        self.assertIsNotNone(write_legacy_frontend_env)

    def test_standalone_preserves_runtime_frontend_env(self):
        self.assertIsNotNone(write_legacy_frontend_env)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / ".env"
            expected = "VUE_APP_BACKEND_URL=http://127.0.0.1:5178/\n"
            target.write_text(expected, encoding="utf-8")

            changed = write_legacy_frontend_env(
                {"host": {"backend": "0.0.0.0"}, "port": {"backend": 5008}},
                target,
                standalone_mode=True,
            )

            self.assertFalse(changed)
            self.assertEqual(target.read_text(encoding="utf-8"), expected)

    def test_non_standalone_keeps_legacy_frontend_env_behavior(self):
        self.assertIsNotNone(write_legacy_frontend_env)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / ".env"

            changed = write_legacy_frontend_env(
                {"host": {"backend": "127.0.0.1"}, "port": {"backend": 5008}},
                target,
                standalone_mode=False,
            )

            self.assertTrue(changed)
            written = target.read_text(encoding="utf-8")
            self.assertIn("VUE_APP_BACKEND_PORT = 5008", written)
            self.assertIn("VUE_APP_BACKEND_IP = 127.0.0.1", written)

    def test_explicit_runtime_config_path_takes_precedence(self):
        self.assertIsNotNone(resolve_runtime_config_path)
        self.assertEqual(
            resolve_runtime_config_path("/workspace/config.yaml", "/workspace/default.yaml"),
            Path("/workspace/config.yaml"),
        )


if __name__ == "__main__":
    unittest.main()
