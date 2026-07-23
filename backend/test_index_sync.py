import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from applications.kml_roi.index_sync import _default_miner_dir, sync_miner_index_rows


class TestIndexSyncDirectory(unittest.TestCase):
    def test_environment_selects_writable_jiangxi_index_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"MINER_INDEX_DATA_DIR": temp_dir}):
                self.assertEqual(_default_miner_dir(), Path(temp_dir))
                result = sync_miner_index_rows(
                    "NDVI",
                    "2026",
                    [{"fid": 1, "mean": 0.42}],
                )

            self.assertTrue(result["synced"])
            self.assertTrue((Path(temp_dir) / "NDVI_2year.xlsx").is_file())


if __name__ == "__main__":
    unittest.main()
