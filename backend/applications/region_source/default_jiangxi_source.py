import os
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

DEFAULT_JIANGXI_KMZ_PATH = Path(
    os.getenv("MINER_DEFAULT_KMZ_PATH") or "/app/runtime_data/Jiangxi_NaturalMine.kmz"
)


def resolve_default_jiangxi_kmz(candidate=None) -> Path:
    if candidate:
        return Path(candidate)
    return DEFAULT_JIANGXI_KMZ_PATH


def extract_kml_bytes_from_kmz(kmz_path: Path) -> bytes:
    with ZipFile(kmz_path, "r") as archive:
        kml_names = [name for name in archive.namelist() if name.lower().endswith(".kml")]
        if not kml_names:
            raise FileNotFoundError(f"No KML entry found in {kmz_path}")
        return archive.read(kml_names[0])


def load_kml_root(source_path) -> ET.Element:
    path_obj = Path(source_path)
    if path_obj.suffix.lower() == ".kmz":
        return ET.parse(BytesIO(extract_kml_bytes_from_kmz(path_obj))).getroot()
    return ET.parse(path_obj).getroot()
