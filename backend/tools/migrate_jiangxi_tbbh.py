from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import subprocess
import math
from urllib.parse import unquote, urlparse
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from applications.project_hub.tbbh_identity import normalize_tbbh
except ModuleNotFoundError as exc:
    if exc.name != "flask":
        raise
    import importlib.util

    _identity_path = BACKEND_ROOT / "applications" / "project_hub" / "tbbh_identity.py"
    _identity_spec = importlib.util.spec_from_file_location("jiangxi_tbbh_identity_migration", _identity_path)
    _identity_module = importlib.util.module_from_spec(_identity_spec)
    _identity_spec.loader.exec_module(_identity_module)
    normalize_tbbh = _identity_module.normalize_tbbh


def _repo_root():
    return Path(__file__).resolve().parents[2]


def _default_manifest():
    return _repo_root() / "docker" / "standalone" / "runtime_data" / "Jiangxi_asset_manifest.json"


def _default_sqlite_path():
    return Path(os.getenv("SQLITE_PATH") or "/app/runtime_data/jiangxi.sqlite3")


def load_manifest_mapping(path):
    manifest_path = Path(path).expanduser().resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("status") != "ok":
        raise ValueError(f"manifest 状态不是 ok: {manifest_path}")
    raw = ((data.get("mapping") or {}).get("tbbh_to_map_fid") or {})
    tbbh_to_map_fid = {}
    map_fid_to_tbbh = {}
    for raw_tbbh, raw_map_fid in raw.items():
        tbbh = normalize_tbbh(raw_tbbh)
        try:
            map_fid = int(raw_map_fid)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"manifest 中 map_fid 非法: {raw_map_fid}") from exc
        if map_fid <= 0 or tbbh in tbbh_to_map_fid or map_fid in map_fid_to_tbbh:
            raise ValueError(f"manifest 中 TBBH/map_fid 重复或非法: {tbbh}/{map_fid}")
        tbbh_to_map_fid[tbbh] = map_fid
        map_fid_to_tbbh[map_fid] = tbbh
    if not tbbh_to_map_fid:
        raise ValueError(f"manifest 没有有效的 TBBH 映射: {manifest_path}")
    return tbbh_to_map_fid, map_fid_to_tbbh


def build_legacy_tbbh_mapping(legacy_fids, map_fid_to_tbbh):
    result = {}
    for raw_fid in legacy_fids:
        fid = _parse_legacy_map_fid(raw_fid)
        if fid <= 0 or fid not in map_fid_to_tbbh:
            raise ValueError(f"历史编号无法通过 manifest 映射为 TBBH: {raw_fid}")
        result[fid] = map_fid_to_tbbh[fid]
    return result


def _parse_legacy_map_fid(raw_fid):
    try:
        number = float(str(raw_fid).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"历史编号不是整数: {raw_fid}") from exc
    if not math.isfinite(number) or not number.is_integer():
        raise ValueError(f"历史编号不是整数: {raw_fid}")
    return int(number)


def _table_columns(connection, table_name):
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")]


def _mysql_table_columns(connection, table_name):
    with connection.cursor() as cursor:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        return [row[0] for row in cursor.fetchall()]


def _legacy_tbbh(row, map_fid_to_tbbh, tbbh_to_map_fid):
    resolved_tbbh = None
    existing_tbbh = row.get("tbbh")
    if existing_tbbh not in (None, ""):
        resolved_tbbh = normalize_tbbh(existing_tbbh)
        if resolved_tbbh not in tbbh_to_map_fid:
            raise ValueError(f"历史 TBBH 不在权威 manifest 中: {resolved_tbbh}")
    subject_code = row.get("subject_code")
    if subject_code not in (None, ""):
        tbbh = normalize_tbbh(subject_code)
        if tbbh not in tbbh_to_map_fid:
            raise ValueError(f"历史 subject_code 不在权威 manifest 中: {tbbh}")
        if resolved_tbbh is not None and resolved_tbbh != tbbh:
            raise ValueError(f"历史记录 TBBH 与 subject_code 冲突: {resolved_tbbh}/{tbbh}")
        resolved_tbbh = tbbh
        legacy_fid = row.get("mine_fid")
        if legacy_fid not in (None, ""):
            parsed_fid = _parse_legacy_map_fid(legacy_fid)
            mapped = build_legacy_tbbh_mapping([parsed_fid], map_fid_to_tbbh)[parsed_fid]
            if mapped != resolved_tbbh:
                raise ValueError(
                    f"历史记录 TBBH 与 map_fid 冲突: tbbh={resolved_tbbh}, map_fid={legacy_fid}, mapped={mapped}"
                )
    legacy_fid = row.get("mine_fid")
    if legacy_fid not in (None, ""):
        parsed_fid = _parse_legacy_map_fid(legacy_fid)
        mapped = build_legacy_tbbh_mapping([parsed_fid], map_fid_to_tbbh)[parsed_fid]
        if resolved_tbbh is not None and resolved_tbbh != mapped:
            raise ValueError(
                f"历史记录 TBBH 与 map_fid 冲突: tbbh={resolved_tbbh}, map_fid={legacy_fid}, mapped={mapped}"
            )
        resolved_tbbh = mapped
    return resolved_tbbh


def _fetch_dicts(connection, table_name):
    cursor = connection.execute(f"SELECT * FROM {table_name}")
    columns = [item[0] for item in cursor.description]
    rows = cursor.fetchall()
    if rows and isinstance(rows[0], dict):
        return rows
    return [dict(zip(columns, row)) for row in rows]


def _fetch_dicts_mysql(connection, table_name):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM `{table_name}`")
        return list(cursor.fetchall())


def _collect_rows(connection, map_fid_to_tbbh, tbbh_to_map_fid):
    tables = {name: _fetch_dicts(connection, name) for name in (
        "project_mine_binding", "project_dataset", "jiangxi_mine_plot"
    )}
    bindings = []
    for row in tables["project_mine_binding"]:
        tbbh = _legacy_tbbh(row, map_fid_to_tbbh, tbbh_to_map_fid)
        if tbbh is None:
            raise ValueError(f"项目绑定缺少可迁移身份: id={row.get('id')}")
        bindings.append((row, tbbh))
    binding_keys = {(row.get("project_id"), tbbh) for row, tbbh in bindings}

    datasets = []
    for row in tables["project_dataset"]:
        tbbh = _legacy_tbbh(row, map_fid_to_tbbh, tbbh_to_map_fid)
        if tbbh is not None and (row.get("project_id"), tbbh) not in binding_keys:
            raise ValueError(f"数据集没有对应项目绑定: id={row.get('id')}, tbbh={tbbh}")
        datasets.append((row, tbbh))

    plots = []
    for row in tables["jiangxi_mine_plot"]:
        tbbh = _legacy_tbbh(row, map_fid_to_tbbh, tbbh_to_map_fid)
        if tbbh is None:
            raise ValueError(f"图斑缺少可迁移身份: id={row.get('id')}")
        if (row.get("project_id"), tbbh) not in binding_keys:
            raise ValueError(f"图斑没有对应项目绑定: id={row.get('id')}, tbbh={tbbh}")
        plots.append((row, tbbh))
    return tables, bindings, datasets, plots


def _validate_sqlite_tbbh_state(connection, required):
    for table_name in required:
        columns = _table_columns(connection, table_name)
        if "tbbh" not in columns or any(old in columns for old in ("mine_fid", "subject_code")):
            raise ValueError(f"数据库字段仍不符合 TBBH 契约: {table_name}: {columns}")
        if table_name != "project_dataset":
            invalid_count = connection.execute(
                f"SELECT COUNT(*) FROM {table_name} WHERE tbbh IS NULL OR TRIM(tbbh) = ''"
            ).fetchone()[0]
            if invalid_count:
                raise ValueError(f"数据库存在空 TBBH: {table_name}={invalid_count}")
    duplicate_binding = connection.execute(
        "SELECT 1 FROM project_mine_binding GROUP BY project_id, tbbh HAVING COUNT(*) > 1 LIMIT 1"
    ).fetchone()
    if duplicate_binding:
        raise ValueError("数据库存在重复项目绑定 (project_id, tbbh)")
    duplicate_plot = connection.execute(
        "SELECT 1 FROM jiangxi_mine_plot GROUP BY project_id, tbbh, plot_code "
        "HAVING COUNT(*) > 1 LIMIT 1"
    ).fetchone()
    if duplicate_plot:
        raise ValueError("数据库存在重复图斑 (project_id, tbbh, plot_code)")
    orphan_plot = connection.execute(
        "SELECT 1 FROM jiangxi_mine_plot p LEFT JOIN project_mine_binding b "
        "ON b.project_id = p.project_id AND b.tbbh = p.tbbh "
        "WHERE b.id IS NULL LIMIT 1"
    ).fetchone()
    if orphan_plot:
        raise ValueError("数据库存在没有项目绑定的图斑")
    orphan_binding = connection.execute(
        "SELECT 1 FROM project_mine_binding b LEFT JOIN project p ON p.id = b.project_id "
        "WHERE p.id IS NULL LIMIT 1"
    ).fetchone()
    if orphan_binding:
        raise ValueError("数据库存在没有项目的绑定")
    orphan_dataset = connection.execute(
        "SELECT 1 FROM project_dataset d LEFT JOIN project_mine_binding b "
        "ON b.project_id = d.project_id AND b.tbbh = d.tbbh "
        "WHERE d.tbbh IS NOT NULL AND b.id IS NULL LIMIT 1"
    ).fetchone()
    if orphan_dataset:
        raise ValueError("数据库存在没有项目绑定的数据集")


def _validate_project_references(project_ids, *table_rows):
    for table_name, rows in table_rows:
        for row in rows:
            if row.get("project_id") not in project_ids:
                raise ValueError(
                    f"{table_name} 存在没有对应项目的记录: id={row.get('id')}, project_id={row.get('project_id')}"
                )


def _validate_mapped_rows(bindings, datasets, plots):
    binding_keys = [(row.get("project_id"), tbbh) for row, tbbh in bindings]
    if len(binding_keys) != len(set(binding_keys)):
        raise ValueError("迁移后项目绑定存在重复 (project_id, tbbh)")
    plot_keys = [(row.get("project_id"), tbbh, row.get("plot_code")) for row, tbbh in plots]
    if len(plot_keys) != len(set(plot_keys)):
        raise ValueError("迁移后图斑存在重复 (project_id, tbbh, plot_code)")
    binding_key_set = set(binding_keys)
    for row, tbbh in datasets:
        if tbbh is not None and (row.get("project_id"), tbbh) not in binding_key_set:
            raise ValueError(f"数据集没有对应项目绑定: id={row.get('id')}, tbbh={tbbh}")


def _create_new_tables(connection):
    connection.executescript(
        """
        CREATE TABLE project_mine_binding_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES project(id),
            tbbh VARCHAR(128) NOT NULL,
            mine_name_snapshot VARCHAR(255),
            city_snapshot VARCHAR(255),
            area_snapshot FLOAT,
            status_snapshot VARCHAR(255),
            sort_order INTEGER NOT NULL DEFAULT 0,
            create_time DATETIME NOT NULL,
            update_time DATETIME NOT NULL,
            CONSTRAINT uq_project_mine_binding_project_tbbh UNIQUE (project_id, tbbh)
        );
        CREATE TABLE project_dataset_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES project(id),
            dataset_kind VARCHAR(64) NOT NULL,
            display_name VARCHAR(255) NOT NULL,
            file_path VARCHAR(1024) NOT NULL,
            source_format VARCHAR(64),
            tbbh VARCHAR(128),
            year_start INTEGER,
            year_end INTEGER,
            slice_config_json TEXT NOT NULL DEFAULT '{}',
            create_time DATETIME NOT NULL,
            update_time DATETIME NOT NULL
        );
        CREATE TABLE jiangxi_mine_plot_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES project(id),
            tbbh VARCHAR(128) NOT NULL,
            city VARCHAR(255),
            county VARCHAR(255),
            location_text VARCHAR(1024),
            plot_code VARCHAR(128) NOT NULL,
            restored_plot_code VARCHAR(128),
            plot_category VARCHAR(255),
            repair_status VARCHAR(255),
            repair_mode VARCHAR(255),
            completed_at VARCHAR(64),
            area FLOAT,
            untreated_area FLOAT,
            center_lng FLOAT,
            center_lat FLOAT,
            closed_year VARCHAR(64),
            plot_attr VARCHAR(64),
            create_time DATETIME NOT NULL,
            update_time DATETIME NOT NULL,
            CONSTRAINT uq_jiangxi_plot_project_tbbh_plot UNIQUE (project_id, tbbh, plot_code)
        );
        """
    )


def _insert_rows(connection, bindings, datasets, plots):
    for row, tbbh in bindings:
        connection.execute(
            """INSERT INTO project_mine_binding_new
            (id, project_id, tbbh, mine_name_snapshot, city_snapshot, area_snapshot,
             status_snapshot, sort_order, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (row["id"], row["project_id"], tbbh, row.get("mine_name_snapshot"), row.get("city_snapshot"),
             row.get("area_snapshot"), row.get("status_snapshot"), row.get("sort_order") or 0,
             row["create_time"], row["update_time"]),
        )
    for row, tbbh in datasets:
        connection.execute(
            """INSERT INTO project_dataset_new
            (id, project_id, dataset_kind, display_name, file_path, source_format, tbbh,
             year_start, year_end, slice_config_json, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (row["id"], row["project_id"], row["dataset_kind"], row["display_name"], row["file_path"],
             row.get("source_format"), tbbh, row.get("year_start"), row.get("year_end"),
             row.get("slice_config_json") or "{}", row["create_time"], row["update_time"]),
        )
    for row, tbbh in plots:
        connection.execute(
            """INSERT INTO jiangxi_mine_plot_new
            (id, project_id, tbbh, city, county, location_text, plot_code, restored_plot_code,
             plot_category, repair_status, repair_mode, completed_at, area, untreated_area,
             center_lng, center_lat, closed_year, plot_attr, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (row["id"], row["project_id"], tbbh, row.get("city"), row.get("county"), row.get("location_text"),
             row["plot_code"], row.get("restored_plot_code"), row.get("plot_category"), row.get("repair_status"),
             row.get("repair_mode"), row.get("completed_at"), row.get("area"), row.get("untreated_area"),
             row.get("center_lng"), row.get("center_lat"), row.get("closed_year"), row.get("plot_attr"),
             row["create_time"], row["update_time"]),
        )


def migrate_sqlite(sqlite_path, manifest_path, apply=False):
    sqlite_path = Path(sqlite_path).expanduser().resolve()
    manifest_path = Path(manifest_path).expanduser().resolve()
    if not sqlite_path.is_file():
        raise ValueError(f"SQLite 数据库不存在: {sqlite_path}")
    tbbh_to_map_fid, map_fid_to_tbbh = load_manifest_mapping(manifest_path)
    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    backup_path = None
    try:
        required = ("project_mine_binding", "project_dataset", "jiangxi_mine_plot")
        missing = [name for name in required if not _table_columns(connection, name)]
        if missing:
            raise ValueError("数据库缺少表: " + ", ".join(missing))
        project_columns = _table_columns(connection, "project")
        if not project_columns:
            raise ValueError("数据库缺少表: project")
        project_count = connection.execute("SELECT COUNT(*) FROM project").fetchone()[0]
        output_columns = _table_columns(connection, "project_export_record")
        output_record_count = (
            connection.execute("SELECT COUNT(*) FROM project_export_record").fetchone()[0]
            if output_columns
            else 0
        )
        columns = {name: _table_columns(connection, name) for name in required}
        if all("tbbh" in columns[name] for name in required) and not any(
            old in columns[name] for name in required for old in ("mine_fid", "subject_code")
        ):
            _validate_sqlite_tbbh_state(connection, required)
            return {"status": "already_migrated", "changed": False, "backup": None}
        tables, bindings, datasets, plots = _collect_rows(
            connection, map_fid_to_tbbh, tbbh_to_map_fid
        )
        project_ids = {
            row[0] for row in connection.execute("SELECT id FROM project").fetchall()
        }
        _validate_project_references(
            project_ids,
            ("project_mine_binding", tables["project_mine_binding"]),
            ("project_dataset", tables["project_dataset"]),
            ("jiangxi_mine_plot", tables["jiangxi_mine_plot"]),
        )
        _validate_mapped_rows(bindings, datasets, plots)
        report = {
            "status": "validated",
            "changed": bool(apply),
            "counts": {
                "project": project_count,
                **{name: len(rows) for name, rows in tables.items()},
                "project_export_record": output_record_count,
            },
            "tbbh_counts": {"bindings": len(bindings), "datasets": len(datasets), "plots": len(plots)},
            "manifest": str(manifest_path),
            "output_record_count": output_record_count,
            "project_count": project_count,
        }
        if not apply:
            return report

        backup_path = sqlite_path.with_name(
            f"{sqlite_path.name}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        shutil.copy2(sqlite_path, backup_path)
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN")
        _create_new_tables(connection)
        _insert_rows(connection, bindings, datasets, plots)
        connection.executescript(
            """
            DROP TABLE project_mine_binding;
            ALTER TABLE project_mine_binding_new RENAME TO project_mine_binding;
            DROP TABLE project_dataset;
            ALTER TABLE project_dataset_new RENAME TO project_dataset;
            DROP TABLE jiangxi_mine_plot;
            ALTER TABLE jiangxi_mine_plot_new RENAME TO jiangxi_mine_plot;
            CREATE INDEX ix_project_mine_binding_project_id ON project_mine_binding(project_id);
            CREATE INDEX ix_project_mine_binding_tbbh ON project_mine_binding(tbbh);
            CREATE INDEX ix_project_dataset_project_id ON project_dataset(project_id);
            CREATE INDEX ix_project_dataset_tbbh ON project_dataset(tbbh);
            CREATE INDEX ix_jiangxi_mine_plot_project_id ON jiangxi_mine_plot(project_id);
            CREATE INDEX ix_jiangxi_mine_plot_tbbh ON jiangxi_mine_plot(tbbh);
            CREATE INDEX ix_jiangxi_mine_plot_plot_code ON jiangxi_mine_plot(plot_code);
            """
        )
        connection.commit()
        connection.execute("PRAGMA foreign_keys=ON")
        for table_name, expected_rows in (
            ("project_mine_binding", bindings),
            ("project_dataset", datasets),
            ("jiangxi_mine_plot", plots),
        ):
            actual_count = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            if actual_count != len(expected_rows):
                raise ValueError(
                    f"迁移后记录数不一致: {table_name}={actual_count}, expected={len(expected_rows)}"
                )
        migrated_project_count = connection.execute("SELECT COUNT(*) FROM project").fetchone()[0]
        if migrated_project_count != report["project_count"]:
            raise ValueError(
                f"迁移后项目数不一致: {migrated_project_count}, expected={report['project_count']}"
            )
        output_record_count = (
            connection.execute("SELECT COUNT(*) FROM project_export_record").fetchone()[0]
            if output_columns
            else 0
        )
        if output_record_count != report["output_record_count"]:
            raise ValueError(
                f"迁移后输出记录数不一致: {output_record_count}, expected={report['output_record_count']}"
            )
        for table_name in required:
            columns = _table_columns(connection, table_name)
            if "mine_fid" in columns or "subject_code" in columns or "tbbh" not in columns:
                raise ValueError(f"迁移后字段仍不符合 TBBH 契约: {table_name}: {columns}")
        report.update({"status": "applied", "backup": str(backup_path)})
        return report
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _parse_mysql_url(database_url):
    parsed = urlparse(str(database_url))
    if parsed.scheme not in {"mysql", "mysql+pymysql"}:
        raise ValueError("MySQL URL 必须使用 mysql:// 或 mysql+pymysql://")
    if not parsed.hostname or not parsed.path.strip("/"):
        raise ValueError("MySQL URL 缺少主机或数据库名")
    return {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": parsed.path.strip("/"),
    }


def _mysql_backup(connection_options, database_url):
    dump_command = shutil.which("mysqldump")
    if not dump_command:
        raise RuntimeError("--apply MySQL 迁移前必须提供 mysqldump，当前 PATH 未找到")
    backup_path = Path.cwd() / (
        f"jiangxi-mysql-{datetime.now().strftime('%Y%m%d%H%M%S')}.sql"
    )
    env = os.environ.copy()
    if connection_options["password"]:
        env["MYSQL_PWD"] = connection_options["password"]
    command = [
        dump_command,
        "--single-transaction",
        "--routines",
        "--triggers",
        "-h",
        connection_options["host"],
        "-P",
        str(connection_options["port"]),
        "-u",
        connection_options["user"],
        connection_options["database"],
    ]
    with backup_path.open("wb") as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.PIPE, env=env)
    if result.returncode != 0:
        backup_path.unlink(missing_ok=True)
        raise RuntimeError(f"mysqldump 失败: {result.stderr.decode(errors='replace')[:500]}")
    return backup_path


def migrate_mysql(database_url, manifest_path, apply=False):
    try:
        import pymysql
    except ModuleNotFoundError as exc:
        raise RuntimeError("MySQL 迁移需要 PyMySQL") from exc

    options = _parse_mysql_url(database_url)
    tbbh_to_map_fid, map_fid_to_tbbh = load_manifest_mapping(manifest_path)
    connection = pymysql.connect(**options, cursorclass=pymysql.cursors.DictCursor, autocommit=False)
    backup_path = None
    required = ("project_mine_binding", "project_dataset", "jiangxi_mine_plot")
    try:
        project_columns = _mysql_table_columns(connection, "project")
        if not project_columns:
            raise ValueError("数据库缺少表: project")
        columns = {name: _mysql_table_columns(connection, name) for name in required}
        missing = [name for name in required if not columns[name]]
        if missing:
            raise ValueError("数据库缺少表: " + ", ".join(missing))
        if all("tbbh" in columns[name] for name in required) and not any(
            old in columns[name] for name in required for old in ("mine_fid", "subject_code")
        ):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM project_mine_binding GROUP BY project_id, tbbh "
                    "HAVING COUNT(*) > 1 LIMIT 1"
                )
                if cursor.fetchone():
                    raise ValueError("数据库存在重复项目绑定 (project_id, tbbh)")
                cursor.execute(
                    "SELECT 1 FROM jiangxi_mine_plot GROUP BY project_id, tbbh, plot_code "
                    "HAVING COUNT(*) > 1 LIMIT 1"
                )
                if cursor.fetchone():
                    raise ValueError("数据库存在重复图斑 (project_id, tbbh, plot_code)")
                cursor.execute(
                    "SELECT 1 FROM project_mine_binding b LEFT JOIN project p ON p.id = b.project_id "
                    "WHERE p.id IS NULL LIMIT 1"
                )
                if cursor.fetchone():
                    raise ValueError("数据库存在没有项目的绑定")
                cursor.execute(
                    "SELECT 1 FROM jiangxi_mine_plot plot LEFT JOIN project_mine_binding b "
                    "ON b.project_id = plot.project_id AND b.tbbh = plot.tbbh "
                    "WHERE b.id IS NULL LIMIT 1"
                )
                if cursor.fetchone():
                    raise ValueError("数据库存在没有项目绑定的图斑")
                cursor.execute(
                    "SELECT 1 FROM project_dataset d LEFT JOIN project_mine_binding b "
                    "ON b.project_id = d.project_id AND b.tbbh = d.tbbh "
                    "WHERE d.tbbh IS NOT NULL AND b.id IS NULL LIMIT 1"
                )
                if cursor.fetchone():
                    raise ValueError("数据库存在没有项目绑定的数据集")
            return {"status": "already_migrated", "changed": False, "backup": None}

        tables = {
            name: _fetch_dicts_mysql(connection, name)
            for name in ("project_mine_binding", "project_dataset", "jiangxi_mine_plot")
        }
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS count FROM project")
            project_count = int(cursor.fetchone()["count"])
        bindings = []
        for row in tables["project_mine_binding"]:
            tbbh = _legacy_tbbh(row, map_fid_to_tbbh, tbbh_to_map_fid)
            if tbbh is None:
                raise ValueError(f"项目绑定缺少可迁移身份: id={row.get('id')}")
            bindings.append((row, tbbh))
        binding_keys = {(row.get("project_id"), tbbh) for row, tbbh in bindings}
        datasets = [
            (row, _legacy_tbbh(row, map_fid_to_tbbh, tbbh_to_map_fid))
            for row in tables["project_dataset"]
        ]
        plots = []
        for row in tables["jiangxi_mine_plot"]:
            tbbh = _legacy_tbbh(row, map_fid_to_tbbh, tbbh_to_map_fid)
            if tbbh is None:
                raise ValueError(f"图斑缺少可迁移身份: id={row.get('id')}")
            if (row.get("project_id"), tbbh) not in binding_keys:
                raise ValueError(f"图斑没有对应项目绑定: id={row.get('id')}, tbbh={tbbh}")
            plots.append((row, tbbh))
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM project")
            project_ids = {row["id"] for row in cursor.fetchall()}
        _validate_project_references(
            project_ids,
            ("project_mine_binding", tables["project_mine_binding"]),
            ("project_dataset", tables["project_dataset"]),
            ("jiangxi_mine_plot", tables["jiangxi_mine_plot"]),
        )
        _validate_mapped_rows(bindings, datasets, plots)
        output_record_count = 0
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS count FROM project_export_record")
            output_record_count = int(cursor.fetchone()["count"])
        report = {
            "status": "validated",
            "changed": bool(apply),
            "counts": {
                "project": project_count,
                **{name: len(rows) for name, rows in tables.items()},
                "project_export_record": output_record_count,
            },
            "tbbh_counts": {"bindings": len(bindings), "datasets": len(datasets), "plots": len(plots)},
            "output_record_count": output_record_count,
            "project_count": project_count,
            "manifest": str(Path(manifest_path).resolve()),
        }
        if not apply:
            return report

        backup_path = _mysql_backup(options, database_url)
        with connection.cursor() as cursor:
            for table_name, table_columns in columns.items():
                if "tbbh" not in table_columns:
                    cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `tbbh` VARCHAR(128) NULL")
            for row, tbbh in bindings:
                cursor.execute(
                    "UPDATE project_mine_binding SET tbbh=%s WHERE id=%s", (tbbh, row["id"])
                )
            for row, tbbh in datasets:
                cursor.execute(
                    "UPDATE project_dataset SET tbbh=%s WHERE id=%s", (tbbh, row["id"])
                )
            for row, tbbh in plots:
                cursor.execute(
                    "UPDATE jiangxi_mine_plot SET tbbh=%s WHERE id=%s", (tbbh, row["id"])
                )
            cursor.execute(
                "SELECT project_id, tbbh, COUNT(*) AS count FROM project_mine_binding "
                "GROUP BY project_id, tbbh HAVING COUNT(*) > 1"
            )
            if cursor.fetchall():
                raise ValueError("迁移后项目绑定存在重复 (project_id, tbbh)")
            cursor.execute(
                "SELECT project_id, tbbh, plot_code, COUNT(*) AS count FROM jiangxi_mine_plot "
                "GROUP BY project_id, tbbh, plot_code HAVING COUNT(*) > 1"
            )
            if cursor.fetchall():
                raise ValueError("迁移后图斑存在重复 (project_id, tbbh, plot_code)")

            for table_name in required:
                index_rows = []
                cursor.execute(f"SHOW INDEX FROM `{table_name}`")
                index_rows.extend(cursor.fetchall())
                drop_indexes = sorted({
                    row["Key_name"] for row in index_rows
                    if row["Column_name"] in {"mine_fid", "subject_code"}
                    and row["Key_name"] != "PRIMARY"
                })
                for index_name in drop_indexes:
                    cursor.execute(f"ALTER TABLE `{table_name}` DROP INDEX `{index_name}`")
                for old_column in ("mine_fid", "subject_code"):
                    if old_column in _mysql_table_columns(connection, table_name):
                        cursor.execute(f"ALTER TABLE `{table_name}` DROP COLUMN `{old_column}`")

            cursor.execute(
                "ALTER TABLE project_mine_binding MODIFY tbbh VARCHAR(128) NOT NULL, "
                "ADD CONSTRAINT uq_project_mine_binding_project_tbbh UNIQUE (project_id, tbbh)"
            )
            cursor.execute(
                "ALTER TABLE jiangxi_mine_plot MODIFY tbbh VARCHAR(128) NOT NULL, "
                "ADD CONSTRAINT uq_jiangxi_plot_project_tbbh_plot UNIQUE (project_id, tbbh, plot_code)"
            )
        connection.commit()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS count FROM project")
            if int(cursor.fetchone()["count"]) != report["project_count"]:
                raise ValueError("迁移后项目数不一致")
            for table_name, expected_count in (
                ("project_mine_binding", len(bindings)),
                ("project_dataset", len(datasets)),
                ("jiangxi_mine_plot", len(plots)),
            ):
                cursor.execute(f"SELECT COUNT(*) AS count FROM `{table_name}`")
                if int(cursor.fetchone()["count"]) != expected_count:
                    raise ValueError(f"迁移后记录数不一致: {table_name}")
            for table_name in required:
                final_columns = _mysql_table_columns(connection, table_name)
                if "tbbh" not in final_columns or any(
                    old in final_columns for old in ("mine_fid", "subject_code")
                ):
                    raise ValueError(f"迁移后字段仍不符合 TBBH 契约: {table_name}")
        report.update({"status": "applied", "backup": str(backup_path)})
        return report
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _build_parser():
    parser = argparse.ArgumentParser(description="将江西项目旧 mine_fid 迁移为 TBBH")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--sqlite-path", default=str(_default_sqlite_path()))
    parser.add_argument("--mysql-url", default=None, help="可选 mysql+pymysql://... 数据库 URL")
    parser.add_argument("--manifest", default=str(_default_manifest()))
    parser.add_argument("--report", default=None)
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        if args.mysql_url:
            result = migrate_mysql(args.mysql_url, args.manifest, apply=args.apply)
        else:
            result = migrate_sqlite(args.sqlite_path, args.manifest, apply=args.apply)
    except Exception as exc:
        result = {"status": "failed", "error": str(exc)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    if args.report:
        report_path = Path(args.report).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
