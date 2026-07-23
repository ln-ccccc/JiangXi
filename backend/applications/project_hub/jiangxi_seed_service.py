import csv
import json
import locale
import re
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook

from applications.extensions import db
from applications.models.analysis import Analysis
from applications.models.jiangxi_seed import JiangxiMinePlot
from applications.models.project import (
    Project,
    ProjectActivityLog,
    ProjectBackupRecord,
    ProjectDataset,
    ProjectExportRecord,
    ProjectMineBinding,
)

DEFAULT_JIANGXI_PROJECT_NAME = "江西矿山生态修复监测项目"
DEFAULT_JIANGXI_REGION = "江西省"
DEFAULT_JIANGXI_REMARK = "system_seed:jiangxi_mine_csv"
DEFAULT_MONITOR_START_YEAR = 2017
DEFAULT_MONITOR_END_YEAR = 2025
REQUIRED_COLUMNS = ("主体编号", "地市", "区县", "矿山位置", "Area")
WORKBOOK_REQUIRED_COLUMNS = ("FID", "TBBH", "SHI", "XIAN", "面积", "矿山位置_")
WORKBOOK_MONITOR_START_YEAR = 2013
WORKBOOK_MONITOR_END_YEAR = 2025


def _normalize_text(value):
    text = str(value or "").strip()
    return text or None


def _extract_year(value):
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"(19|20)\d{2}", text)
    if not match:
        return None
    return int(match.group(0))


def _parse_float(value, *, field_name):
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} 不是合法数值: {text}") from exc


def _candidate_encodings():
    preferred = locale.getpreferredencoding(False) or "gbk"
    return [preferred, "gbk", "gb18030", "utf-8-sig", "utf-8"]


def _read_csv_with_detected_encoding(path_obj):
    errors = []
    for encoding in _candidate_encodings():
        try:
            with path_obj.open("r", encoding=encoding, newline="") as fp:
                reader = csv.DictReader(fp)
                rows = list(reader)
                return rows, reader.fieldnames or [], encoding
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
    raise ValueError(f"Mine.csv 编码无法读取: {'; '.join(errors)}")


def _validate_required_columns(fieldnames):
    missing = [name for name in REQUIRED_COLUMNS if name not in (fieldnames or [])]
    if missing:
        raise ValueError(f"Mine.csv 缺失关键字段: {', '.join(missing)}")


def _status_summary(statuses):
    values = sorted({item for item in statuses if item})
    return " / ".join(values) if values else None


def _build_subject_record(subject_code, rows, mine_fid):
    first_row = rows[0]
    city = _normalize_text(first_row.get("地市"))
    county = _normalize_text(first_row.get("区县"))
    location_text = _normalize_text(first_row.get("矿山位置"))
    warnings = []

    for row in rows[1:]:
        if _normalize_text(row.get("地市")) not in (None, city):
            warnings.append(f"{subject_code}: 地市存在不一致，按首条主值保留")
            break
    for row in rows[1:]:
        if _normalize_text(row.get("区县")) not in (None, county):
            warnings.append(f"{subject_code}: 区县存在不一致，按首条主值保留")
            break
    for row in rows[1:]:
        if _normalize_text(row.get("矿山位置")) not in (None, location_text):
            warnings.append(f"{subject_code}: 矿山位置存在不一致，按首条主值保留")
            break

    plots = []
    statuses = []
    start_year_candidates = []
    end_year_candidates = []
    for row in rows:
        plot = {
            "plot_code": _normalize_text(row.get("图斑编号")) or "",
            "restored_plot_code": _normalize_text(row.get("修复图斑编号")),
            "plot_category": _normalize_text(row.get("图斑小类")),
            "repair_status": _normalize_text(row.get("修复状态")),
            "repair_mode": _normalize_text(row.get("修复模式")),
            "completed_at": _normalize_text(row.get("完成时间")),
            "area": _parse_float(row.get("Area"), field_name="Area"),
            "untreated_area": _parse_float(row.get("未治理面积"), field_name="未治理面积"),
            "center_lng": _parse_float(row.get("中心经度") or row.get("Lon"), field_name="经度"),
            "center_lat": _parse_float(row.get("中心纬度") or row.get("Lat"), field_name="纬度"),
            "closed_year": _normalize_text(row.get("关闭年度")),
            "plot_attr": _normalize_text(row.get("图斑属性")),
            "city": city,
            "county": county,
            "location_text": location_text,
        }
        plots.append(plot)
        if plot["repair_status"]:
            statuses.append(plot["repair_status"])
        closed_year = _extract_year(plot["closed_year"])
        completed_year = _extract_year(row.get("填报日期")) or _extract_year(plot["completed_at"])
        if closed_year:
            start_year_candidates.append(closed_year)
        if completed_year:
            end_year_candidates.append(completed_year)
        elif closed_year:
            end_year_candidates.append(closed_year)

    return {
        "mine_fid": mine_fid,
        "subject_code": subject_code,
        "city": city,
        "county": county,
        "location_text": location_text,
        "plot_count": len(plots),
        "area_total": sum(item["area"] for item in plots),
        "untreated_area_total": sum(item["untreated_area"] for item in plots),
        "status_summary": _status_summary(statuses),
        "plots": plots,
        "start_year": min(start_year_candidates) if start_year_candidates else None,
        "end_year": max(end_year_candidates) if end_year_candidates else None,
        "warnings": warnings,
    }


def _load_csv_rows(csv_path):
    path_obj = Path(csv_path).expanduser().resolve()
    if not path_obj.exists():
        raise ValueError(f"Mine.csv 不存在: {path_obj}")
    rows, fieldnames, _encoding = _read_csv_with_detected_encoding(path_obj)
    _validate_required_columns(fieldnames)
    return path_obj, rows


def reset_project_domain_tables():
    db.session.query(JiangxiMinePlot).delete()
    db.session.query(ProjectBackupRecord).delete()
    db.session.query(ProjectExportRecord).delete()
    db.session.query(ProjectActivityLog).delete()
    db.session.query(ProjectDataset).delete()
    db.session.query(ProjectMineBinding).delete()
    db.session.query(Project).delete()
    db.session.query(Analysis).delete()
    db.session.commit()


def aggregate_subject_rows(csv_path):
    _path_obj, rows = _load_csv_rows(csv_path)
    grouped = defaultdict(list)
    skipped = 0
    warnings = []

    for row in rows:
        subject_code = _normalize_text(row.get("主体编号"))
        if not subject_code:
            skipped += 1
            warnings.append("存在主体编号为空的记录，已跳过")
            continue
        try:
            _parse_float(row.get("Area"), field_name="Area")
            _parse_float(row.get("未治理面积"), field_name="未治理面积")
            _parse_float(row.get("中心经度") or row.get("Lon"), field_name="经度")
            _parse_float(row.get("中心纬度") or row.get("Lat"), field_name="纬度")
        except ValueError as exc:
            skipped += 1
            warnings.append(f"{subject_code}: {exc}，已跳过该行")
            continue
        grouped[subject_code].append(row)

    sorted_items = sorted(
        grouped.items(),
        key=lambda item: (
            _normalize_text(item[1][0].get("地市")) or "",
            _normalize_text(item[1][0].get("区县")) or "",
            item[0],
        ),
    )

    subjects = []
    for mine_fid, (subject_code, subject_rows) in enumerate(sorted_items, start=1):
        subject = _build_subject_record(subject_code, subject_rows, mine_fid)
        warnings.extend(subject["warnings"])
        subjects.append(subject)
    return subjects, skipped, warnings, len(rows)


def _read_workbook_rows(workbook_path):
    path_obj = Path(workbook_path).expanduser().resolve()
    if not path_obj.exists():
        raise ValueError(f"江西图斑工作簿不存在: {path_obj}")

    workbook = load_workbook(path_obj, read_only=True, data_only=True)
    try:
        worksheet = workbook.active
        headers = [str(value or "").strip() for value in next(worksheet.iter_rows(values_only=True))]
        missing = [name for name in WORKBOOK_REQUIRED_COLUMNS if name not in headers]
        if missing:
            raise ValueError(f"江西图斑工作簿缺少关键字段: {', '.join(missing)}")
        return [dict(zip(headers, row)) for row in worksheet.iter_rows(min_row=2, values_only=True)]
    finally:
        workbook.close()


def build_map_aligned_records(workbook_path):
    records = []
    seen_fids = set()
    seen_tbbh = set()

    for row_number, row in enumerate(_read_workbook_rows(workbook_path), start=2):
        fid_value = row.get("FID")
        fid_text = "" if fid_value is None else str(fid_value).strip()
        try:
            mine_fid = int(fid_text)
        except ValueError as exc:
            raise ValueError(f"第 {row_number} 行 FID 非法: {fid_text}") from exc
        if mine_fid < 0:
            raise ValueError(f"第 {row_number} 行 FID 必须为非负整数: {mine_fid}")

        tbbh = _normalize_text(row.get("TBBH"))
        if not tbbh:
            raise ValueError(f"第 {row_number} 行 TBBH 为空")
        if mine_fid in seen_fids or tbbh in seen_tbbh:
            raise ValueError(f"第 {row_number} 行 FID 或 TBBH 重复: {mine_fid} / {tbbh}")
        seen_fids.add(mine_fid)
        seen_tbbh.add(tbbh)

        area_hectare = _parse_float(row.get("面积"), field_name="面积") / 10000.0
        records.append(
            {
                "mine_fid": mine_fid,
                "tbbh": tbbh,
                "mine_name": _normalize_text(row.get("矿山位置_")) or f"图斑 {mine_fid}",
                "city": _normalize_text(row.get("SHI")) or _normalize_text(row.get("地市")),
                "county": _normalize_text(row.get("XIAN")) or _normalize_text(row.get("区县")),
                "area_hectare": area_hectare,
                "repair_status": _normalize_text(row.get("修复状态")),
                "repair_mode": _normalize_text(row.get("修复模式")),
                "completed_at": _normalize_text(row.get("完成时间")),
                "plot_category": _normalize_text(row.get("图斑小类")),
                "untreated_area": _parse_float(row.get("未治理面积"), field_name="未治理面积") / 10000.0,
                "center_lng": _parse_float(row.get("中心经度_"), field_name="中心经度"),
                "center_lat": _parse_float(row.get("中心纬度_"), field_name="中心纬度"),
            }
        )

    if not records:
        raise ValueError("江西图斑工作簿没有有效记录")
    return sorted(records, key=lambda item: item["mine_fid"])


def _replace_project_with_map_aligned_records(project, records):
    db.session.query(JiangxiMinePlot).filter_by(project_id=project.id).delete(
        synchronize_session="fetch"
    )
    db.session.query(ProjectMineBinding).filter_by(project_id=project.id).delete(
        synchronize_session="fetch"
    )
    db.session.flush()

    for sort_order, record in enumerate(records, start=1):
        db.session.add(
            ProjectMineBinding(
                project_id=project.id,
                mine_fid=record["mine_fid"],
                mine_name_snapshot=record["mine_name"],
                city_snapshot=record["city"],
                area_snapshot=record["area_hectare"],
                status_snapshot=record["repair_status"],
                sort_order=sort_order,
            )
        )
        db.session.add(
            JiangxiMinePlot(
                project_id=project.id,
                mine_fid=record["mine_fid"],
                subject_code=record["tbbh"],
                city=record["city"],
                county=record["county"],
                location_text=record["mine_name"],
                plot_code=record["tbbh"],
                restored_plot_code=record["tbbh"],
                plot_category=record["plot_category"],
                repair_status=record["repair_status"],
                repair_mode=record["repair_mode"],
                completed_at=record["completed_at"],
                area=record["area_hectare"],
                untreated_area=record["untreated_area"],
                center_lng=record["center_lng"],
                center_lat=record["center_lat"],
                closed_year=None,
                plot_attr=None,
            )
        )

    project.monitor_start_year = WORKBOOK_MONITOR_START_YEAR
    project.monitor_end_year = WORKBOOK_MONITOR_END_YEAR


def sync_jiangxi_project_from_workbook(workbook_path, actor="system"):
    records = build_map_aligned_records(workbook_path)
    project = Project.query.filter_by(
        remark=DEFAULT_JIANGXI_REMARK,
        deleted_at=None,
    ).first()
    if not project:
        raise ValueError("未找到可对齐的江西默认项目")

    existing_fids = {
        row.mine_fid
        for row in ProjectMineBinding.query.filter_by(project_id=project.id).all()
    }
    expected_fids = {record["mine_fid"] for record in records}
    existing_plot_rows = JiangxiMinePlot.query.filter_by(project_id=project.id).all()
    existing_plot_keys = {(row.mine_fid, row.subject_code) for row in existing_plot_rows}
    expected_plot_keys = {(record["mine_fid"], record["tbbh"]) for record in records}
    if (
        existing_fids == expected_fids
        and existing_plot_keys == expected_plot_keys
        and project.monitor_start_year == WORKBOOK_MONITOR_START_YEAR
        and project.monitor_end_year == WORKBOOK_MONITOR_END_YEAR
    ):
        return {
            "project_id": project.id,
            "mine_count": len(records),
            "plot_count": len(records),
            "changed": False,
        }

    _replace_project_with_map_aligned_records(project, records)
    db.session.add(
        ProjectActivityLog(
            project_id=project.id,
            event_type="jiangxi_map_alignment_synced",
            actor=actor,
            payload_json=json.dumps(
                {
                    "source": Path(workbook_path).name,
                    "mine_count": len(records),
                    "monitor_start_year": WORKBOOK_MONITOR_START_YEAR,
                    "monitor_end_year": WORKBOOK_MONITOR_END_YEAR,
                },
                ensure_ascii=False,
            ),
        )
    )
    db.session.commit()
    return {
        "project_id": project.id,
        "mine_count": len(records),
        "plot_count": len(records),
        "changed": True,
    }


def _summarize_monitor_years(subjects):
    start_candidates = [item["start_year"] for item in subjects if item.get("start_year")]
    end_candidates = [item["end_year"] for item in subjects if item.get("end_year")]
    start_year = min(start_candidates) if start_candidates else DEFAULT_MONITOR_START_YEAR
    end_year = max(end_candidates) if end_candidates else DEFAULT_MONITOR_END_YEAR
    if end_year < start_year:
        return DEFAULT_MONITOR_START_YEAR, DEFAULT_MONITOR_END_YEAR
    return start_year, end_year


def seed_jiangxi_project_from_csv(csv_path, actor="system", workbook_path=None):
    path_obj, _rows = _load_csv_rows(csv_path)
    reset_project_domain_tables()
    if workbook_path:
        records = build_map_aligned_records(workbook_path)
        project = Project(
            name=DEFAULT_JIANGXI_PROJECT_NAME,
            region=DEFAULT_JIANGXI_REGION,
            manager="admin",
            remark=DEFAULT_JIANGXI_REMARK,
            status="active",
            monitor_start_year=WORKBOOK_MONITOR_START_YEAR,
            monitor_end_year=WORKBOOK_MONITOR_END_YEAR,
        )
        db.session.add(project)
        db.session.flush()
        _replace_project_with_map_aligned_records(project, records)
        db.session.add(
            ProjectActivityLog(
                project_id=project.id,
                event_type="jiangxi_seed_completed",
                actor=actor,
                payload_json=json.dumps(
                    {
                        "source": Path(workbook_path).name,
                        "mine_count": len(records),
                        "plot_count": len(records),
                    },
                    ensure_ascii=False,
                ),
            )
        )
        db.session.commit()
        return {
            "project_id": project.id,
            "project_name": project.name,
            "project_count": 1,
            "subject_count": len(records),
            "plot_count": len(records),
            "skipped_count": 0,
            "monitor_start_year": WORKBOOK_MONITOR_START_YEAR,
            "monitor_end_year": WORKBOOK_MONITOR_END_YEAR,
        }

    subjects, skipped, warnings, total_rows = aggregate_subject_rows(path_obj)
    monitor_start_year, monitor_end_year = _summarize_monitor_years(subjects)

    project = Project(
        name=DEFAULT_JIANGXI_PROJECT_NAME,
        region=DEFAULT_JIANGXI_REGION,
        manager="admin",
        remark=DEFAULT_JIANGXI_REMARK,
        status="active",
        monitor_start_year=monitor_start_year,
        monitor_end_year=monitor_end_year,
    )
    db.session.add(project)
    db.session.flush()

    total_plot_count = 0
    for subject in subjects:
        db.session.add(
            ProjectMineBinding(
                project_id=project.id,
                mine_fid=subject["mine_fid"],
                mine_name_snapshot=subject["location_text"],
                city_snapshot=subject["city"],
                area_snapshot=subject["area_total"],
                status_snapshot=subject["status_summary"],
                sort_order=subject["mine_fid"],
            )
        )
        for plot in subject["plots"]:
            total_plot_count += 1
            db.session.add(
                JiangxiMinePlot(
                    project_id=project.id,
                    mine_fid=subject["mine_fid"],
                    subject_code=subject["subject_code"],
                    city=plot["city"],
                    county=plot["county"],
                    location_text=plot["location_text"],
                    plot_code=plot["plot_code"],
                    restored_plot_code=plot["restored_plot_code"],
                    plot_category=plot["plot_category"],
                    repair_status=plot["repair_status"],
                    repair_mode=plot["repair_mode"],
                    completed_at=plot["completed_at"],
                    area=plot["area"],
                    untreated_area=plot["untreated_area"],
                    center_lng=plot["center_lng"],
                    center_lat=plot["center_lat"],
                    closed_year=plot["closed_year"],
                    plot_attr=plot["plot_attr"],
                )
            )

    payload = {
        "source": "Mine.csv",
        "source_path": str(path_obj),
        "raw_count": total_rows,
        "plot_count": total_plot_count,
        "subject_count": len(subjects),
        "skipped_count": skipped,
        "warnings": warnings[:20],
    }
    db.session.add(
        ProjectActivityLog(
            project_id=project.id,
            event_type="jiangxi_seed_completed",
            actor=actor,
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
    )
    db.session.commit()

    return {
        "project_id": project.id,
        "project_name": project.name,
        "project_count": 1,
        "subject_count": len(subjects),
        "plot_count": total_plot_count,
        "skipped_count": skipped,
        "monitor_start_year": monitor_start_year,
        "monitor_end_year": monitor_end_year,
    }
