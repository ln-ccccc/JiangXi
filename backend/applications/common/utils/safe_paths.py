import re
from pathlib import Path
from urllib.parse import unquote


class PathValidationError(ValueError):
    pass


def _positive_identifier(value, label):
    text = str(value or "").strip()
    if not re.fullmatch(r"[1-9]\d*", text):
        raise PathValidationError(f"{label}必须为正整数")
    return text


def validate_positive_identifier(value, label="FID"):
    return _positive_identifier(value, label)


def _managed_root(root):
    return Path(root).expanduser().resolve()


def _path_inside_root(root, *parts):
    root_path = _managed_root(root)
    candidate = root_path.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise PathValidationError("文件路径超出受控目录") from exc
    return candidate


def resolve_output_directory(root, identifier):
    # U 前缀为非联动推理产物命名空间（单段、无路径分隔符，穿越安全）
    text = str(identifier or "").strip()
    if not re.fullmatch(r"U[1-9][0-9]*|[1-9][0-9]*", text):
        raise PathValidationError("标识必须为正整数或 U 前缀未联动标识")
    return _path_inside_root(root, text)


def resolve_managed_file(root, filename, allowed_suffixes):
    filename_text = str(filename or "").strip()
    decoded_name = unquote(filename_text)
    if not filename_text or Path(filename_text).name != filename_text or Path(decoded_name).name != decoded_name:
        raise PathValidationError("文件名不合法")

    suffix = Path(filename_text).suffix.lower()
    if suffix not in {item.lower() for item in allowed_suffixes}:
        raise PathValidationError("文件类型不允许")

    return _path_inside_root(root, filename_text)


def resolve_output_file(root, fid, filename, allowed_suffixes):
    return resolve_managed_file(resolve_output_directory(root, _positive_identifier(fid, "FID")), filename, allowed_suffixes)
