import os
import tempfile
import unittest
from pathlib import Path

from applications.common.utils.safe_paths import (
    PathValidationError,
    resolve_managed_file,
    resolve_output_file,
)


class SafePathTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path("C:/managed-output")

    def test_resolve_output_file_accepts_numeric_fid_and_png_name(self):
        resolved = resolve_output_file(self.root, "101", "101+2024.png", {".png"})

        self.assertEqual(resolved, self.root / "101" / "101+2024.png")

    def test_resolve_output_file_rejects_path_traversal(self):
        with self.assertRaises(PathValidationError):
            resolve_output_file(self.root, "..", "../server.js", {".png"})

    def test_resolve_output_file_rejects_non_whitelisted_extension(self):
        with self.assertRaises(PathValidationError):
            resolve_output_file(self.root, "101", "secret.txt", {".png"})

    def test_resolve_output_file_rejects_zero_and_absolute_inputs(self):
        with self.assertRaises(PathValidationError):
            resolve_output_file(self.root, "0", "101+2024.png", {".png"})
        with self.assertRaises(PathValidationError):
            resolve_output_file(self.root, "101", "C:/outside.png", {".png"})

    def test_resolve_managed_file_accepts_only_basename_and_suffix(self):
        resolved = resolve_managed_file(self.root, "scene.tif", {".tif"})
        self.assertEqual(resolved, self.root / "scene.tif")

        for filename in ("../scene.tif", "%2e%2e%2fscene.tif", "C:/scene.tif", "scene.png"):
            with self.assertRaises(PathValidationError):
                resolve_managed_file(self.root, filename, {".tif"})

    def test_resolve_managed_file_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "managed"
            root.mkdir()
            outside = Path(temp_dir) / "outside.tif"
            outside.write_bytes(b"tif")
            link = root / "linked.tif"
            try:
                os.symlink(outside, link)
            except OSError as exc:
                self.skipTest(f"当前环境不允许创建符号链接: {exc}")

            with self.assertRaises(PathValidationError):
                resolve_managed_file(root, link.name, {".tif"})


if __name__ == "__main__":
    unittest.main()
