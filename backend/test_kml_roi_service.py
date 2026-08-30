import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from applications.kml_roi import service


class KmlRoiServiceWorkdirTests(unittest.TestCase):
    def test_each_inference_gets_an_isolated_temporary_workdir(self):
        with tempfile.TemporaryDirectory(prefix="kml-roi-service-test-") as temp_dir:
            root = Path(temp_dir)
            tif_path = root / "input.tif"
            kml_path = root / "roi.kml"
            manifest_path = root / "manifest.json"
            output_root = root / "outputs"
            tif_path.write_bytes(b"tif")
            kml_path.write_text("<kml />", encoding="utf-8")
            manifest_path.write_text(
                json.dumps({"status": "ok", "mapping": {"tbbh_to_map_fid": {}}}),
                encoding="utf-8",
            )

            commands = []

            def fake_run(command, **kwargs):
                commands.append(command)
                return SimpleNamespace(
                    returncode=0,
                    stdout='{"status":"completed"}\n',
                    stderr="",
                )

            with patch.object(service, "resolve_default_jiangxi_kmz", return_value=kml_path), \
                    patch.object(service.subprocess, "run", side_effect=fake_run):
                service.run_kml_roi_inference(
                    old_tif_path=str(tif_path),
                    new_tif_path=str(tif_path),
                    output_root=str(output_root),
                    manifest_path=str(manifest_path),
                )
                service.run_kml_roi_inference(
                    old_tif_path=str(tif_path),
                    new_tif_path=str(tif_path),
                    output_root=str(output_root),
                    manifest_path=str(manifest_path),
                )

            self.assertEqual(len(commands), 2)
            workdirs = [Path(command[command.index("--work_dir") + 1]) for command in commands]
            self.assertNotEqual(workdirs[0], workdirs[1])
            self.assertTrue(all(not workdir.exists() for workdir in workdirs))


if __name__ == "__main__":
    unittest.main()
