import tempfile
import unittest
from pathlib import Path

from applications.common.utils.safe_paths import PathValidationError
from applications.kml_roi.kml import load_kml_features


class KmlRoiPathTestCase(unittest.TestCase):
    def test_kml_roi_rejects_non_numeric_fid(self):
        content = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<kml xmlns=\"http://www.opengis.net/kml/2.2\"><Document><Placemark>
<name>../../outside</name><Polygon><outerBoundaryIs><LinearRing><coordinates>
116,28 116.1,28 116.1,28.1 116,28
</coordinates></LinearRing></outerBoundaryIs></Polygon>
</Placemark></Document></kml>"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "unsafe.kml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(PathValidationError):
                load_kml_features(path)
