"""Validate the offline HTML user manual without third-party dependencies."""

from __future__ import annotations

import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


REQUIRED_SECTION_IDS = (
    "quick-start",
    "login-security",
    "mine-map",
    "project-workspace",
    "roi-inference",
    "land-cover",
    "spectral-index",
    "result-reading",
    "admin-maintenance",
    "faq-glossary",
)

BUSINESS_SECTION_IDS = (
    "mine-map",
    "project-workspace",
    "roi-inference",
    "land-cover",
    "spectral-index",
)

VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

WORKFLOW_HEADINGS = (
    "何时使用",
    "前置条件",
    "操作步骤",
    "成功标志",
    "注意事项与失败处理",
)

INTERACTION_ATTRIBUTE_MARKERS = (
    "data-manual-nav-toggle",
    "data-zoomable",
    "data-copy-button",
)

INTERACTION_REQUIRED_IDS = (
    "manual-progress",
    "image-lightbox",
)

UNSAFE_LITERALS = (
    ("CPU", re.compile(r"\bCPU\b", re.IGNORECASE)),
    ("mine_fid", re.compile(r"mine_fid", re.IGNORECASE)),
    ("device=cpu", re.compile(r"device=cpu", re.IGNORECASE)),
    ("--device cpu", re.compile(r"--device\s+cpu", re.IGNORECASE)),
    ("geoview-jiangxi:cpu", re.compile(r"geoview-jiangxi:cpu", re.IGNORECASE)),
    ("docker compose.*cpu", re.compile(r"docker\s+compose[^\r\n]*cpu", re.IGNORECASE)),
    ("SECRET_KEY", re.compile(r"SECRET_KEY", re.IGNORECASE)),
    ("MYSQL_PASSWORD", re.compile(r"MYSQL_PASSWORD", re.IGNORECASE)),
    ("MYSQL_ROOT_PASSWORD", re.compile(r"MYSQL_ROOT_PASSWORD", re.IGNORECASE)),
    ("123456", re.compile(r"123456")),
    ("Windows user drive path", re.compile(r"[A-Za-z]:[\\/]+Users[\\/]", re.IGNORECASE)),
)

RESOURCE_ATTRIBUTES = {
    "audio": ("src",),
    "embed": ("src",),
    "feimage": ("href", "xlink:href"),
    "frame": ("src",),
    "iframe": ("src",),
    "image": ("href", "xlink:href"),
    "img": ("src", "srcset"),
    "input": ("src",),
    "link": ("href", "imagesrcset"),
    "object": ("data",),
    "script": ("src",),
    "source": ("src", "srcset"),
    "track": ("src",),
    "use": ("href", "xlink:href"),
    "video": ("src", "poster"),
}

CSS_URL_PATTERN = re.compile(
    r"url\s*\(\s*(?:'([^']*)'|\"([^\"]*)\"|([^\s)]+))\s*\)",
    re.IGNORECASE,
)

CSS_IMPORT_URL_PATTERN = re.compile(r"@import\b", re.IGNORECASE)
RESOURCE_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
ASCII_CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]")


def _contains_ascii_control_character(value: str) -> bool:
    return ASCII_CONTROL_CHARACTER_PATTERN.search(value) is not None


def _is_forbidden_resource_path(value: str) -> bool:
    if _contains_ascii_control_character(value):
        return True
    value = value.strip()
    lower_value = value.lower()
    if lower_value.startswith("data:"):
        return False
    return value.startswith(("/", "\\")) or RESOURCE_SCHEME_PATTERN.match(value) is not None


def _srcset_comma_starts_forbidden_path(value: str, position: int) -> bool:
    position += 1
    while position < len(value) and value[position].isspace():
        position += 1
    start = position
    while position < len(value) and not value[position].isspace() and value[position] != ",":
        position += 1
    return _is_forbidden_resource_path(value[start:position])


def _iter_srcset_paths(value: str):
    position = 0
    while position < len(value):
        while position < len(value) and (value[position].isspace() or value[position] == ","):
            position += 1
        if position >= len(value):
            return

        start = position
        is_data_url = value[start : start + 5].lower() == "data:"
        data_url_is_base64 = False
        data_separator_seen = False
        if is_data_url:
            data_separator = value.find(",", position)
            if data_separator != -1:
                data_url_is_base64 = ";base64" in value[position:data_separator].lower()

        while position < len(value) and not value[position].isspace():
            if value[position] == ",":
                if not is_data_url:
                    break
                if data_separator_seen and (
                    data_url_is_base64
                    or _srcset_comma_starts_forbidden_path(value, position)
                ):
                    break
                data_separator_seen = True
            position += 1
        path = value[start:position]
        if path:
            yield path

        while position < len(value) and value[position] != ",":
            position += 1
        if position < len(value):
            position += 1


class _ManualParser(HTMLParser):
    def __init__(self, manual_root: Path):
        super().__init__(convert_charrefs=True)
        self.manual_root = manual_root.resolve()
        self.assets_root = (self.manual_root / "assets").resolve()
        self.errors: list[str] = []
        self.id_counts: Counter[str] = Counter()
        self.anchors: list[str] = []
        self.interaction_attributes: set[str] = set()
        self.elements: list[tuple[str, int]] = []
        self.next_element_token = 0
        self.zoomable_screenshot_figures: list[dict[str, int | bool]] = []
        self.active_zoomable_screenshot_figures: list[dict[str, int | bool]] = []
        self.business_sections: dict[str, list[tuple[bool, list[str]]]] = {
            section_id: [] for section_id in BUSINESS_SECTION_IDS
        }
        self.active_business_sections: list[tuple[int, list[str]]] = []
        self.active_workflow_headings: list[tuple[int, int, list[str], list[str]]] = []
        self.css_sources: list[str] = []
        self.active_style_blocks: list[tuple[int, list[str]]] = []

    def close(self) -> None:
        super().close()
        self.css_sources.extend("".join(style_text) for _, style_text in self.active_style_blocks)
        self.active_style_blocks.clear()

    def _nearest_section_token(self) -> int | None:
        return next(
            (token for tag, token in reversed(self.elements) if tag == "section"),
            None,
        )

    def _has_excluded_workflow_ancestor(self) -> bool:
        return any(tag in {"script", "style", "template"} for tag, _ in self.elements)

    def _check_resource_path(self, attribute: str, value: str | None) -> None:
        if not value:
            return

        if _contains_ascii_control_character(value):
            self.errors.append(
                f"ERROR: resource path in {attribute} contains ASCII control characters"
            )
            return

        paths = _iter_srcset_paths(value) if attribute.endswith("srcset") else (value,)
        for path in paths:
            if _is_forbidden_resource_path(path):
                self.errors.append(f"ERROR: resource path in {attribute} must be relative: {path}")

    def _check_image(self, attributes: dict[str, str | None]) -> None:
        alt = attributes.get("alt")
        if not alt or not alt.strip() or not re.search(r"[\u4e00-\u9fff]", alt):
            self.errors.append("ERROR: img alt must be nonempty and contain Chinese text")

        source = attributes.get("src")
        if not source or not source.startswith("assets/"):
            self.errors.append("ERROR: img src must be a relative assets/... path")
            return

        asset_path = (self.manual_root / source).resolve()
        if not asset_path.is_relative_to(self.assets_root):
            self.errors.append(f"ERROR: img src resolves outside assets directory: {source}")
        elif not asset_path.is_file():
            self.errors.append(f"ERROR: img src does not exist: {source}")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        self.interaction_attributes.update(
            marker for marker in INTERACTION_ATTRIBUTE_MARKERS if marker in attributes
        )
        element_id = attributes.get("id")
        if element_id is not None:
            self.id_counts[element_id] += 1

        href = attributes.get("href")
        if tag == "base" and "href" in attributes:
            self.errors.append("ERROR: base href is not allowed")
        elif href and href.startswith("#"):
            self.anchors.append(href[1:])

        for attribute in RESOURCE_ATTRIBUTES.get(tag, ()):
            self._check_resource_path(f"{tag} {attribute}", attributes.get(attribute))
        if tag == "img":
            self._check_image(attributes)

        element_token = None
        if tag not in VOID_ELEMENTS:
            self.next_element_token += 1
            element_token = self.next_element_token
            self.elements.append((tag, element_token))

        if tag == "section" and element_id in BUSINESS_SECTION_IDS:
            section_headings: list[str] = []
            self.business_sections[element_id].append(("data-workflow" in attributes, section_headings))
            if element_token is not None:
                self.active_business_sections.append((element_token, section_headings))

        if (
            tag == "h3"
            and self.active_business_sections
            and element_token is not None
            and not self._has_excluded_workflow_ancestor()
        ):
            section_token, section_headings = self.active_business_sections[-1]
            if self._nearest_section_token() == section_token:
                self.active_workflow_headings.append(
                    (element_token, section_token, section_headings, [])
                )

        style_value = attributes.get("style")
        if style_value:
            self.css_sources.append(style_value)
        if tag == "style" and element_token is not None:
            self.active_style_blocks.append((element_token, []))

        if tag == "figure" and "data-zoomable" in attributes:
            screenshot_figure = {
                "token": element_token,
                "has_data_callout": "data-callout" in attributes,
                "has_image_callout": False,
            }
            self.zoomable_screenshot_figures.append(screenshot_figure)
            self.active_zoomable_screenshot_figures.append(screenshot_figure)

        if "image-callout" in attributes.get("class", "").split():
            for screenshot_figure in self.active_zoomable_screenshot_figures:
                screenshot_figure["has_image_callout"] = True

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        matching_index = next(
            (index for index in range(len(self.elements) - 1, -1, -1) if self.elements[index][0] == tag),
            None,
        )
        if matching_index is None:
            return

        closed_tokens = {token for _, token in self.elements[matching_index:]}
        closed_workflow_headings = [
            heading
            for heading in self.active_workflow_headings
            if heading[0] in closed_tokens
        ]
        for _, _, section_headings, heading_text in closed_workflow_headings:
            heading = re.sub(r"\s+", "", "".join(heading_text))
            if heading:
                section_headings.append(heading)
        self.active_workflow_headings = [
            heading
            for heading in self.active_workflow_headings
            if heading[0] not in closed_tokens
        ]
        closed_style_blocks = [
            block for block in self.active_style_blocks if block[0] in closed_tokens
        ]
        self.css_sources.extend("".join(style_text) for _, style_text in closed_style_blocks)
        self.active_style_blocks = [
            block for block in self.active_style_blocks if block[0] not in closed_tokens
        ]
        self.active_business_sections = [
            section
            for section in self.active_business_sections
            if section[0] not in closed_tokens
        ]
        self.active_zoomable_screenshot_figures = [
            figure
            for figure in self.active_zoomable_screenshot_figures
            if figure["token"] not in closed_tokens
        ]
        del self.elements[matching_index:]

    def handle_data(self, data: str) -> None:
        if self.active_workflow_headings and self.active_business_sections:
            _, section_token, _, heading_text = self.active_workflow_headings[-1]
            if (
                self._nearest_section_token() == section_token
                and not self._has_excluded_workflow_ancestor()
                and not any(tag == "p" for tag, _ in self.elements)
            ):
                heading_text.append(data)
        if self.active_style_blocks:
            self.active_style_blocks[-1][1].append(data)


def validate_manual(root: Path) -> list[str]:
    """Return all validation errors for ``root/docs/manual/index.html``."""
    manual_root = root / "docs" / "manual"
    index_path = manual_root / "index.html"
    if not index_path.is_file():
        return [f"ERROR: HTML user manual not found: {index_path}"]

    try:
        document = index_path.read_text(encoding="utf-8")
    except UnicodeError as error:
        return [f"ERROR: cannot read HTML user manual as UTF-8: {error}"]
    except OSError as error:
        return [f"ERROR: cannot read HTML user manual: {error}"]

    parser = _ManualParser(manual_root)
    try:
        parser.feed(document)
        parser.close()
    except Exception as error:  # HTMLParser can raise for malformed declarations.
        return [f"ERROR: cannot parse HTML user manual: {error}"]

    for css_source in parser.css_sources:
        if "\\" in css_source:
            parser.errors.append("ERROR: CSS escape sequences are not allowed")
        for match in CSS_URL_PATTERN.finditer(css_source):
            url = next(value for value in match.groups() if value is not None)
            parser._check_resource_path("CSS url(...)", url)
        for _ in CSS_IMPORT_URL_PATTERN.finditer(css_source):
            parser.errors.append("ERROR: CSS @import url(...) is not allowed")

    errors = parser.errors
    for section_id in REQUIRED_SECTION_IDS:
        if parser.id_counts[section_id] == 0:
            errors.append(f"ERROR: missing required section id: {section_id}")

    for section_id in BUSINESS_SECTION_IDS:
        sections = parser.business_sections[section_id]
        workflows = [section_text for has_workflow, section_text in sections if has_workflow]
        if not workflows:
            errors.append(f"ERROR: section {section_id} must contain data-workflow")
            continue
        if not any(all(heading in workflow for heading in WORKFLOW_HEADINGS) for workflow in workflows):
            for heading in WORKFLOW_HEADINGS:
                if not any(heading in workflow for workflow in workflows):
                    errors.append(f"ERROR: section {section_id} data-workflow is missing heading: {heading}")

    toggle_marker = INTERACTION_ATTRIBUTE_MARKERS[0]
    if toggle_marker not in parser.interaction_attributes:
        errors.append(f"ERROR: missing interaction marker: {toggle_marker}")
    for element_id in INTERACTION_REQUIRED_IDS:
        if parser.id_counts[element_id] == 0:
            errors.append(f"ERROR: missing required id: {element_id}")
    for marker in INTERACTION_ATTRIBUTE_MARKERS[1:]:
        if marker not in parser.interaction_attributes:
            errors.append(f"ERROR: missing interaction marker: {marker}")
    for screenshot_figure in parser.zoomable_screenshot_figures:
        if not screenshot_figure["has_data_callout"]:
            errors.append("ERROR: data-zoomable screenshot figure must have data-callout")
        if not screenshot_figure["has_image_callout"]:
            errors.append("ERROR: data-zoomable screenshot figure must contain image-callout marker")
    if "prefers-reduced-motion" not in document:
        errors.append("ERROR: missing accessibility marker: prefers-reduced-motion")
    if "@media print" not in document:
        errors.append("ERROR: missing print marker: @media print")

    for element_id, count in parser.id_counts.items():
        if count > 1:
            errors.append(f"ERROR: duplicate id: {element_id}")
    for anchor in parser.anchors:
        if parser.id_counts[anchor] != 1:
            errors.append(f"ERROR: internal anchor #{anchor} must match exactly one id")

    for _, pattern in UNSAFE_LITERALS:
        match = pattern.search(document)
        if match:
            errors.append(f"ERROR: unsafe literal: {match.group(0)}")
    return errors


def main() -> int:
    errors = validate_manual(Path.cwd())
    if errors:
        print("\n".join(errors))
        return 1
    print("HTML user manual: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
