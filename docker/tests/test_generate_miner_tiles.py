"""Tile generation source selection regression tests."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "generate_miner_tiles.py"


def load_tile_module():
    spec = importlib.util.spec_from_file_location("generate_miner_tiles", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TileSourceTests(unittest.TestCase):
    def test_missing_explicit_tif_does_not_select_another_file(self):
        tile_module = load_tile_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "other.tif").write_bytes(b"tif")
            with patch.dict(
                os.environ,
                {"MINER_TILE_TIF_PATH": str(root / "missing.tif")},
                clear=True,
            ):
                self.assertIsNone(tile_module.resolve_source_tif())

    def test_unconfigured_tif_is_skipped_with_clear_message(self):
        tile_module = load_tile_module()
        with patch.dict(os.environ, {"MINER_MAP_PROVIDER": "local"}, clear=True), patch(
            "builtins.print"
        ) as print_mock, patch.object(tile_module.subprocess, "run") as run_command:
            result = tile_module.main()

        self.assertEqual(result, 0)
        messages = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
        self.assertIn("MINER_TILE_TIF_PATH is not configured", messages)
        run_command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
