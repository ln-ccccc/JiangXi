import contextlib
import csv
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from openpyxl import Workbook


BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from applications.project_hub.tbbh_identity import (
        build_tbbh_map_fid_mapping,
        normalize_tbbh,
        validate_tbbh_sets,
    )
except ModuleNotFoundError as exc:
    if exc.name != "flask":
        raise
    import importlib.util

    identity_path = BACKEND_ROOT / "applications" / "project_hub" / "tbbh_identity.py"
    identity_spec = importlib.util.spec_from_file_location("test_tbbh_identity_module", identity_path)
    identity_module = importlib.util.module_from_spec(identity_spec)
    identity_spec.loader.exec_module(identity_module)
    build_tbbh_map_fid_mapping = identity_module.build_tbbh_map_fid_mapping
    normalize_tbbh = identity_module.normalize_tbbh
    validate_tbbh_sets = identity_module.validate_tbbh_sets

try:
    from tools.validate_jiangxi_assets import (
        main as validate_assets_main,
        validate_jiangxi_assets,
    )
except ImportError as exc:  # RED 阶段让测试以断言失败而不是收集错误结束
    _VALIDATOR_IMPORT_ERROR = exc
    validate_assets_main = None
    validate_jiangxi_assets = None

try:
    from tools.build_jiangxi_asset_manifest import main as build_manifest_main
except ImportError as exc:  # RED 阶段让测试以断言失败而不是收集错误结束
    _MANIFEST_IMPORT_ERROR = exc
    build_manifest_main = None


TARGET_TBBH = "ZJ3607232021018001"


def _assert_imported(test_case, value, error_name):
    test_case.assertIsNotNone(
        value,
        f"{error_name} 尚未实现: {globals().get('_' + error_name.upper() + '_IMPORT_ERROR')}",
    )


def _write_shp_header(file_length_words):
    header = bytearray(100)
    struct.pack_into(">i", header, 0, 9994)
    struct.pack_into(">i", header, 24, file_length_words)
    struct.pack_into("<i", header, 28, 1000)
    struct.pack_into("<i", header, 32, 0)
    return header


def _write_shapefile(root, tbbhs):
    shp_path = root / "plots.shp"
    shx_path = root / "plots.shx"
    dbf_path = root / "plots.dbf"
    prj_path = root / "plots.prj"

    null_shape = struct.pack("<i", 0)
    shp_records = []
    for record_number, _tbbh in enumerate(tbbhs, start=1):
        shp_records.append(struct.pack(">ii", record_number, len(null_shape) // 2) + null_shape)
    shp_body = b"".join(shp_records)
    shp_path.write_bytes(_write_shp_header((100 + len(shp_body)) // 2) + shp_body)

    shx_records = []
    offset_words = 50
    for _tbbh in tbbhs:
        shx_records.append(struct.pack(">ii", offset_words, len(null_shape) // 2))
        offset_words += 4 + len(null_shape) // 2
    shx_body = b"".join(shx_records)
    shx_path.write_bytes(_write_shp_header((100 + len(shx_body)) // 2) + shx_body)

    field_name = b"TBBH" + b"\x00" * 7
    header_length = 32 + 32 + 1
    record_length = 1 + 40
    dbf_header = bytearray(header_length)
    dbf_header[0] = 0x03
    dbf_header[1:4] = b"\x7e\x08\x1a"
    struct.pack_into("<I", dbf_header, 4, len(tbbhs))
    struct.pack_into("<H", dbf_header, 8, header_length)
    struct.pack_into("<H", dbf_header, 10, record_length)
    dbf_header[32:43] = field_name
    dbf_header[43] = ord("C")
    dbf_header[48] = 40
    dbf_header[64] = 0x0D
    dbf_body = b"".join(
        b" " + tbbh.encode("ascii").ljust(40, b" ") for tbbh in tbbhs
    )
    dbf_path.write_bytes(dbf_header + dbf_body + b"\x1a")
    prj_path.write_text(
        'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]]]',
        encoding="ascii",
    )
    return shp_path, shx_path, dbf_path, prj_path


def _write_kmz(path, map_fids):
    kml = [
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
    ]
    for map_fid in map_fids:
        kml.append(
            "<Placemark><name>{0}</name><ExtendedData><SchemaData>"
            '<SimpleData name="FID">{0}</SimpleData>'
            "</SchemaData></ExtendedData></Placemark>".format(map_fid)
        )
    kml.append("</Document></kml>")
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", "".join(kml).encode("utf-8"))


def _write_workbook(path, rows):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["FID", "TBBH", "序号", "SHI", "XIAN", "面积", "矿山位置_"])
    for row in rows:
        worksheet.append(row)
    workbook.save(path)


def _write_csv(path):
    headers = [
        "主体编号",
        "地市",
        "区县",
        "矿山位置",
        "Area",
        "未治理面积",
        "Lon",
        "Lat",
        "图斑编号",
    ]
    rows = [
        ["LEGACY-1", "赣州市", "大余县", "地点 A", "10.5", "0", "114.4", "25.5", "PLOT-1"],
        ["LEGACY-1", "赣州市", "大余县", "地点 A", "11", "1", "114.5", "25.6", "PLOT-2"],
    ]
    with path.open("w", encoding="gbk", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(headers)
        writer.writerows(rows)


class TbbhIdentityTestCase(unittest.TestCase):
    def test_normalize_tbbh_only_trims_preserves_case_and_rejects_invalid_values(self):
        _assert_imported(self, normalize_tbbh, "identity")
        self.assertEqual(normalize_tbbh("  AbC-01\t"), "AbC-01")
        for value in (None, "", " \t\n"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_tbbh(value)
        with self.assertRaises(ValueError):
            normalize_tbbh("x" * 129)

    def test_mapping_uses_map_fid_column_instead_of_excel_fid(self):
        _assert_imported(self, build_tbbh_map_fid_mapping, "identity")
        mapping = build_tbbh_map_fid_mapping(
            [
                {"FID": 0, "TBBH": TARGET_TBBH, "序号": 23},
                {"FID": 1, "TBBH": "TBBH-2", "序号": 22},
            ],
            tbbh_field="TBBH",
            map_fid_field="序号",
        )
        self.assertEqual(mapping[TARGET_TBBH], 23)
        self.assertNotEqual(mapping[TARGET_TBBH], 0)

    def test_mapping_rejects_duplicate_tbbh_or_map_fid(self):
        _assert_imported(self, build_tbbh_map_fid_mapping, "identity")
        with self.assertRaises(ValueError):
            build_tbbh_map_fid_mapping(
                [
                    {"TBBH": "A", "map_fid": 1},
                    {"TBBH": "A", "map_fid": 2},
                ]
            )

        with self.assertRaises(ValueError):
            build_tbbh_map_fid_mapping([{"TBBH": "A", "map_fid": 1.5}])
        with self.assertRaises(ValueError):
            build_tbbh_map_fid_mapping(
                [
                    {"TBBH": "A", "map_fid": 1},
                    {"TBBH": "B", "map_fid": 1},
                ]
            )

    def test_validate_tbbh_sets_reports_duplicates_intersection_and_missing_values(self):
        _assert_imported(self, validate_tbbh_sets, "identity")
        result = validate_tbbh_sets(
            {
                "excel": [" A ", "B", "B"],
                "shp": ["A", "B"],
                "kmz": ["A", "C"],
            }
        )
        self.assertEqual(result["duplicates"]["excel"], ["B"])
        self.assertEqual(result["intersection"], ["A"])
        self.assertEqual(result["missing"]["excel"], ["B"])
        self.assertEqual(result["missing"]["kmz"], ["C"])


class JiangxiAssetCliTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jiangxi_asset_fixture_")
        self.root = Path(self.temp_dir.name)
        self.excel_path = self.root / "assets.xlsx"
        self.shp_path, self.shx_path, self.dbf_path, self.prj_path = _write_shapefile(
            self.root, [TARGET_TBBH, "TBBH-2"]
        )
        self.kmz_path = self.root / "assets.kmz"
        _write_kmz(self.kmz_path, [23, 22])
        self.csv_path = self.root / "Mine.csv"
        _write_csv(self.csv_path)
        _write_workbook(
            self.excel_path,
            [
                [0, TARGET_TBBH, 23, "赣州市", "大余县", 10, "地点 A"],
                [1, "TBBH-2", 22, "赣州市", "大余县", 11, "地点 B"],
            ],
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _asset_args(self):
        return [
            "--excel",
            str(self.excel_path),
            "--shp",
            str(self.shp_path),
            "--kmz",
            str(self.kmz_path),
            "--csv",
            str(self.csv_path),
        ]

    def test_validator_checks_fixture_and_labels_csv_subject_code_as_legacy(self):
        _assert_imported(self, validate_jiangxi_assets, "validator")
        report = validate_jiangxi_assets(
            excel_path=self.excel_path,
            shp_path=self.shp_path,
            kmz_path=self.kmz_path,
            csv_path=self.csv_path,
        )
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["tbbh"]["intersection_count"], 2)
        self.assertEqual(report["mapping"]["tbbh_to_map_fid"][TARGET_TBBH], 23)
        self.assertEqual(report["csv"]["field_role"], "legacy_subject_code")
        self.assertEqual(report["csv"]["duplicate_checks"]["legacy_subject_code"]["count"], 1)
        self.assertNotIn("主体编号", report["tbbh"]["sets"])

    def test_validator_cli_prints_clear_summary(self):
        _assert_imported(self, validate_assets_main, "validator")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = validate_assets_main(self._asset_args())
        text = output.getvalue()
        self.assertEqual(exit_code, 0)
        for label in ("Excel", "SHP", "KMZ", "TBBH intersection", "duplicate TBBH", "status"):
            self.assertIn(label, text)

    def test_validator_returns_failure_for_missing_shp_sidecar(self):
        _assert_imported(self, validate_assets_main, "validator")
        self.shx_path.unlink()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = validate_assets_main(self._asset_args())
        self.assertNotEqual(exit_code, 0)
        self.assertIn("status: failed", output.getvalue())
        self.assertIn(".shx", output.getvalue())

    def test_manifest_writes_hash_size_count_mapping_and_csv_result(self):
        _assert_imported(self, build_manifest_main, "manifest")
        output_path = self.root / "manifest.json"
        exit_code = build_manifest_main(self._asset_args() + ["--output", str(output_path)])
        self.assertEqual(exit_code, 0)
        manifest = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["source"], "jiangxi-runtime-assets")
        self.assertEqual(manifest["version"], 1)
        self.assertTrue(manifest["generated_at"])
        self.assertEqual(manifest["mapping"]["count"], 2)
        self.assertEqual(manifest["mapping"]["tbbh_to_map_fid"][TARGET_TBBH], 23)
        self.assertEqual(manifest["csv"]["field_role"], "legacy_subject_code")
        for file_info in manifest["files"].values():
            self.assertIn("sha256", file_info)
            self.assertIn("size", file_info)
            self.assertIn("count", file_info)

    def test_manifest_returns_failure_when_validation_fails(self):
        _assert_imported(self, build_manifest_main, "manifest")
        self.shx_path.unlink()
        output_path = self.root / "manifest.json"
        exit_code = build_manifest_main(self._asset_args() + ["--output", str(output_path)])
        self.assertNotEqual(exit_code, 0)
        self.assertTrue(output_path.exists())
        manifest = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "failed")


if __name__ == "__main__":
    unittest.main()
