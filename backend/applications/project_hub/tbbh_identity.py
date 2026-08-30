from __future__ import annotations

from collections import Counter


MAX_TBBH_LENGTH = 128


def normalize_tbbh(value) -> str:
    """Normalize a TBBH without changing its business identity."""
    if value is None:
        raise ValueError("TBBH 不能为空")
    text = str(value).strip()
    if not text:
        raise ValueError("TBBH 不能为空")
    if len(text) > MAX_TBBH_LENGTH:
        raise ValueError(f"TBBH 长度不能超过 {MAX_TBBH_LENGTH} 个字符")
    return text


def _parse_map_fid(value) -> int:
    if value is None or str(value).strip() == "":
        raise ValueError("map_fid 不能为空")
    try:
        number_float = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"map_fid 不是合法整数: {value}") from exc
    if number_float != number_float or not number_float.is_integer():
        raise ValueError(f"map_fid 不是合法整数: {value}")
    number = int(number_float)
    if number <= 0:
        raise ValueError(f"map_fid 必须为正整数: {number}")
    return number


def build_tbbh_map_fid_mapping(rows, tbbh_field="TBBH", map_fid_field="map_fid"):
    mapping = {}
    reverse = {}
    for row_number, row in enumerate(rows or [], start=1):
        try:
            tbbh = normalize_tbbh(row.get(tbbh_field))
        except (AttributeError, ValueError) as exc:
            raise ValueError(f"第 {row_number} 行 TBBH 无效: {exc}") from exc
        try:
            map_fid = _parse_map_fid(row.get(map_fid_field))
        except ValueError as exc:
            raise ValueError(f"第 {row_number} 行 map_fid 无效: {exc}") from exc
        if tbbh in mapping:
            raise ValueError(f"TBBH 重复: {tbbh}")
        if map_fid in reverse:
            raise ValueError(f"map_fid 重复: {map_fid}")
        mapping[tbbh] = map_fid
        reverse[map_fid] = tbbh
    return mapping


def validate_tbbh_sets(named_sets):
    normalized = {
        name: [normalize_tbbh(value) for value in values]
        for name, values in (named_sets or {}).items()
    }
    counters = {name: Counter(values) for name, values in normalized.items()}
    sets = {name: set(values) for name, values in normalized.items()}
    intersection = set.intersection(*sets.values()) if sets else set()
    missing = {
        name: sorted(values - intersection)
        for name, values in sets.items()
    }
    return {
        "sets": {name: sorted(values) for name, values in sets.items()},
        "duplicates": {
            name: sorted(value for value, count in counter.items() if count > 1)
            for name, counter in counters.items()
        },
        "intersection": sorted(intersection),
        "missing": missing,
    }
