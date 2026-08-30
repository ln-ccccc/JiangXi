import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from tools.migrate_jiangxi_tbbh import (
        build_legacy_tbbh_mapping,
        load_manifest_mapping,
        migrate_sqlite,
    )
except ImportError:
    build_legacy_tbbh_mapping = None
    load_manifest_mapping = None
    migrate_sqlite = None


class TbbhMigrationTestCase(unittest.TestCase):
    def test_manifest_mapping_is_loaded_in_both_directions(self):
        self.assertIsNotNone(load_manifest_mapping)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manifest.json"
            path.write_text(
                json.dumps({"status": "ok", "mapping": {"tbbh_to_map_fid": {"A": 23, "B": 24}}}),
                encoding="utf-8",
            )
            tbbh_to_fid, fid_to_tbbh = load_manifest_mapping(path)
        self.assertEqual(tbbh_to_fid, {"A": 23, "B": 24})
        self.assertEqual(fid_to_tbbh, {23: "A", 24: "B"})

    def test_legacy_fids_are_mapped_only_when_positive_and_known(self):
        self.assertIsNotNone(build_legacy_tbbh_mapping)
        self.assertEqual(build_legacy_tbbh_mapping([23, 24], {23: "A", 24: "B"}), {23: "A", 24: "B"})
        self.assertEqual(build_legacy_tbbh_mapping(["23.0"], {23: "A"}), {23: "A"})
        with self.assertRaises(ValueError):
            build_legacy_tbbh_mapping([0], {23: "A"})
        with self.assertRaises(ValueError):
            build_legacy_tbbh_mapping([25], {23: "A"})

    def test_sqlite_migration_rebuilds_tables_and_preserves_counts(self):
        self.assertIsNotNone(migrate_sqlite)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "jiangxi.sqlite3"
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps({"status": "ok", "mapping": {"tbbh_to_map_fid": {"A": 23}}}),
                encoding="utf-8",
            )
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE project_export_record (id INTEGER PRIMARY KEY, project_id INTEGER);
                CREATE TABLE project_mine_binding (
                    id INTEGER PRIMARY KEY, project_id INTEGER, mine_fid INTEGER,
                    mine_name_snapshot TEXT, city_snapshot TEXT, area_snapshot FLOAT,
                    status_snapshot TEXT, sort_order INTEGER, create_time TEXT, update_time TEXT
                );
                CREATE TABLE project_dataset (
                    id INTEGER PRIMARY KEY, project_id INTEGER, dataset_kind TEXT,
                    display_name TEXT, file_path TEXT, source_format TEXT, mine_fid INTEGER,
                    year_start INTEGER, year_end INTEGER, slice_config_json TEXT,
                    create_time TEXT, update_time TEXT
                );
                CREATE TABLE jiangxi_mine_plot (
                    id INTEGER PRIMARY KEY, project_id INTEGER, mine_fid INTEGER,
                    subject_code TEXT, city TEXT, county TEXT, location_text TEXT,
                    plot_code TEXT, restored_plot_code TEXT, plot_category TEXT,
                    repair_status TEXT, repair_mode TEXT, completed_at TEXT, area FLOAT,
                    untreated_area FLOAT, center_lng FLOAT, center_lat FLOAT,
                    closed_year TEXT, plot_attr TEXT, create_time TEXT, update_time TEXT
                );
                """
            )
            connection.execute("INSERT INTO project VALUES (1, '江西')")
            connection.execute("INSERT INTO project_export_record VALUES (1, 1)")
            connection.execute(
                "INSERT INTO project_mine_binding VALUES (1, 1, 23, '矿山', '赣州', 1.0, '待治理', 1, 'now', 'now')"
            )
            connection.execute(
                "INSERT INTO project_dataset VALUES (1, 1, 'report', '报告', 'report.csv', 'csv', 23, 2024, 2024, '{}', 'now', 'now')"
            )
            connection.execute(
                "INSERT INTO jiangxi_mine_plot VALUES (1, 1, 23, 'A', '赣州', '县', '位置', 'P1', 'P1', '类别', '待治理', '工程', '2024', 1.0, 0.1, 114.0, 25.0, '2020', '1', 'now', 'now')"
            )
            connection.commit()
            connection.close()

            dry_run = migrate_sqlite(db_path, manifest_path, apply=False)
            self.assertEqual(dry_run["status"], "validated")
            self.assertEqual(dry_run["output_record_count"], 1)
            applied = migrate_sqlite(db_path, manifest_path, apply=True)
            self.assertEqual(applied["status"], "applied")
            self.assertTrue(Path(applied["backup"]).is_file())

            connection = sqlite3.connect(db_path)
            for table_name in ("project_mine_binding", "project_dataset", "jiangxi_mine_plot"):
                columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")}
                self.assertIn("tbbh", columns)
                self.assertNotIn("mine_fid", columns)
                self.assertNotIn("subject_code", columns)
            self.assertEqual(connection.execute("SELECT tbbh FROM project_mine_binding").fetchone()[0], "A")
            self.assertEqual(connection.execute("SELECT tbbh FROM project_dataset").fetchone()[0], "A")
            self.assertEqual(connection.execute("SELECT tbbh FROM jiangxi_mine_plot").fetchone()[0], "A")
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM project_export_record").fetchone()[0], 1)
            connection.close()


if __name__ == "__main__":
    unittest.main()
