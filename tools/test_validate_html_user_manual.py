import subprocess
import sys
import tempfile
import unittest
import re
from pathlib import Path

from tools.validate_html_user_manual import UNSAFE_LITERALS, validate_manual


REQUIRED_SECTIONS = (
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

BUSINESS_SECTIONS = (
    "mine-map",
    "project-workspace",
    "roi-inference",
    "land-cover",
    "spectral-index",
)

WORKFLOW_HEADINGS = (
    "何时使用",
    "前置条件",
    "操作步骤",
    "成功标志",
    "注意事项与失败处理",
)

SCRIPT = Path(__file__).with_name("validate_html_user_manual.py")
PROJECT_ROOT = SCRIPT.parent.parent
ACTUAL_MANUAL = PROJECT_ROOT / "docs" / "manual" / "index.html"
ACTUAL_ASSET_LEDGER = PROJECT_ROOT / "docs" / "manual" / "assets" / "README.md"


class ValidateHtmlUserManualTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.manual_root = self.root / "docs" / "manual"
        (self.manual_root / "assets").mkdir(parents=True)
        (self.manual_root / "assets" / "guide.png").write_bytes(b"not-a-real-png")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write_manual(self, body, include_interaction=True):
        interaction_markup = "" if not include_interaction else """
  <button type="button" data-manual-nav-toggle>目录</button>
  <p id="manual-progress">阅读进度</p>
  <button type="button" data-zoomable>放大图片</button>
  <button type="button" data-copy-button>复制命令</button>
  <div id="image-lightbox"></div>
  <style>@media (prefers-reduced-motion: reduce) {} @media print {}</style>
"""
        document = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="assets/manual.css">
</head>
<body>
  <a href="#quick-start">开始使用</a>
  {body}
  <img src="assets/guide.png" alt="操作示意图">
  {interaction_markup}
  <script src="assets/manual.js"></script>
</body>
</html>
""".format(
            body=body,
            interaction_markup=interaction_markup,
        )
        (self.manual_root / "index.html").write_text(document, encoding="utf-8")

    def valid_sections(self):
        return "\n".join(self.section_markup(section_id) for section_id in REQUIRED_SECTIONS)

    def section_markup(self, section_id, headings=WORKFLOW_HEADINGS, content=""):
        workflow_attribute = ""
        heading_markup = ""
        if section_id in BUSINESS_SECTIONS:
            workflow_attribute = " data-workflow"
            heading_markup = "".join(f"<h3>{heading}</h3>" for heading in headings)
        return f'<section id="{section_id}"{workflow_attribute}><h2>手册章节</h2>{heading_markup}{content}</section>'

    def sections_with_replacements(self, replacements):
        sections = []
        for section_id in REQUIRED_SECTIONS:
            sections.append(replacements.get(section_id, self.section_markup(section_id)))
        return "\n".join(sections)

    def run_validator(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_valid_minimal_manual_passes(self):
        self.write_manual(self.valid_sections())

        self.assertEqual(validate_manual(self.root), [])
        result = self.run_validator()

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "HTML user manual: PASS")
        self.assertEqual(result.stderr, "")

    def test_missing_interaction_and_accessibility_contract_is_reported(self):
        self.write_manual(self.valid_sections(), include_interaction=False)

        self.assertEqual(
            validate_manual(self.root),
            [
                "ERROR: missing interaction marker: data-manual-nav-toggle",
                "ERROR: missing required id: manual-progress",
                "ERROR: missing required id: image-lightbox",
                "ERROR: missing interaction marker: data-zoomable",
                "ERROR: missing interaction marker: data-copy-button",
                "ERROR: missing accessibility marker: prefers-reduced-motion",
                "ERROR: missing print marker: @media print",
            ],
        )

    def test_structural_interaction_contract_does_not_require_implementation_tokens(self):
        self.write_manual(self.valid_sections())

        self.assertEqual(validate_manual(self.root), [])

    def test_zoomable_screenshot_figure_requires_callout_annotation(self):
        screenshot = """
<figure data-zoomable tabindex="0" role="button">
  <img src="assets/guide.png" alt="操作截图">
</figure>
"""
        self.write_manual(self.valid_sections() + screenshot)

        self.assertEqual(
            validate_manual(self.root),
            [
                "ERROR: data-zoomable screenshot figure must have data-callout",
                "ERROR: data-zoomable screenshot figure must contain image-callout marker",
            ],
        )

    def test_missing_index_html_returns_clear_error(self):
        errors = validate_manual(self.root)
        result = self.run_validator()

        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("ERROR: HTML user manual not found:"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR: HTML user manual not found:", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_utf8_returns_clear_error_without_traceback(self):
        (self.manual_root / "index.html").write_bytes(b"\xff")

        errors = validate_manual(self.root)
        result = self.run_validator()

        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("ERROR: cannot read HTML user manual as UTF-8:"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR: cannot read HTML user manual as UTF-8:", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_required_section_is_reported(self):
        body = self.valid_sections().replace(' id="faq-glossary"', ' id="other-section"')
        self.write_manual(body)

        errors = validate_manual(self.root)

        self.assertTrue(any("missing required section id: faq-glossary" in error for error in errors))

    def test_business_section_requires_data_workflow(self):
        before, mine_map_section = self.valid_sections().split(
            '<section id="mine-map" data-workflow>', 1
        )
        mine_map_content, after = mine_map_section.split("</section>", 1)
        body = (
            before
            + '<section id="mine-map"><div class="data-workflow">'
            + mine_map_content
            + "</div></section>"
            + after
        )
        self.write_manual(body)

        errors = validate_manual(self.root)

        self.assertTrue(any("mine-map" in error and "data-workflow" in error for error in errors))

    def test_business_workflow_requires_all_headings(self):
        body = self.valid_sections().replace("<h3>成功标志</h3>", "", 1)
        self.write_manual(body)

        errors = validate_manual(self.root)

        self.assertTrue(any("mine-map" in error and "成功标志" in error for error in errors))

    def test_void_element_does_not_keep_business_section_active(self):
        mine_map_headings = tuple(heading for heading in WORKFLOW_HEADINGS if heading != "成功标志")
        body = self.sections_with_replacements(
            {
                "mine-map": self.section_markup(
                    "mine-map",
                    mine_map_headings,
                    '<img src="assets/guide.png" alt="流程图片">',
                )
            }
        )
        self.write_manual(body)

        errors = validate_manual(self.root)

        self.assertTrue(any("mine-map" in error and "成功标志" in error for error in errors))

    def test_nested_business_section_headings_do_not_satisfy_outer_section(self):
        mine_map_headings = tuple(heading for heading in WORKFLOW_HEADINGS if heading != "成功标志")
        nested_project = self.section_markup("project-workspace")
        outer_mine_map = self.section_markup("mine-map", mine_map_headings, nested_project)
        body = self.sections_with_replacements(
            {
                "mine-map": outer_mine_map,
                "project-workspace": "",
            }
        )
        self.write_manual(body)

        errors = validate_manual(self.root)

        self.assertTrue(any("mine-map" in error and "成功标志" in error for error in errors))

    def test_business_section_errors_follow_required_section_order(self):
        self.write_manual(self.valid_sections().replace(" data-workflow", ""))

        errors = validate_manual(self.root)

        self.assertEqual(
            [error for error in errors if "must contain data-workflow" in error],
            [f"ERROR: section {section_id} must contain data-workflow" for section_id in BUSINESS_SECTIONS],
        )

    def test_image_requires_nonempty_chinese_alt_text(self):
        self.write_manual(self.valid_sections() + '<img src="assets/guide.png" alt="guide">')

        errors = validate_manual(self.root)

        self.assertTrue(any("img alt" in error for error in errors))

    def test_image_source_must_be_existing_relative_asset(self):
        self.write_manual(self.valid_sections() + '<img src="assets/missing.png" alt="缺失图片">')

        errors = validate_manual(self.root)

        self.assertTrue(any("img src" in error and "does not exist" in error for error in errors))

    def test_image_source_requires_assets_prefix(self):
        self.write_manual(self.valid_sections() + '<img src="images/guide.png" alt="普通图片">')

        errors = validate_manual(self.root)

        self.assertTrue(any("img src must be a relative assets/... path" in error for error in errors))

    def test_image_source_must_resolve_inside_assets_directory(self):
        self.write_manual(self.valid_sections() + '<img src="assets/../index.html" alt="越界图片">')

        errors = validate_manual(self.root)

        self.assertTrue(any("img src resolves outside assets directory" in error for error in errors))

    def test_http_resource_path_is_rejected(self):
        self.write_manual(self.valid_sections() + '<script src="http://example.com/manual.js"></script>')

        errors = validate_manual(self.root)

        self.assertTrue(any("resource path in script src" in error for error in errors))

    def test_backslash_root_resource_path_is_rejected(self):
        self.write_manual(self.valid_sections() + '<link rel="stylesheet" href="\\assets\\manual.css">')

        errors = validate_manual(self.root)

        self.assertTrue(any("resource path in link href" in error for error in errors))

    def test_other_forbidden_resource_paths_are_rejected(self):
        body = self.valid_sections() + """
<script src="https://example.com/manual.js"></script>
<link rel="stylesheet" href="//example.com/manual.css">
<img src="C:\\Users\\Alice\\guide.png" alt="中文图片">
<script src="/assets/other.js"></script>
"""
        self.write_manual(body)

        errors = validate_manual(self.root)

        self.assertGreaterEqual(len([error for error in errors if "resource path" in error]), 4)

    def test_base_and_non_relative_resource_paths_are_rejected(self):
        body = self.valid_sections() + r"""
<base href="assets/">
<script src="file:///tmp/manual.js"></script>
<link rel="stylesheet" href="ftp://example.invalid/manual.css">
<iframe src="javascript:alert(1)"></iframe>
<source src="https:\example.invalid\manual.mp4">
<script src="C:assets/manual.js"></script>
<script src="assets\manual.js"></script>
<source src="data:audio/mp4;base64,AA==">
"""
        self.write_manual(body)

        errors = validate_manual(self.root)

        self.assertEqual(
            [
                error
                for error in errors
                if error.startswith("ERROR: base href") or "resource path in" in error
            ],
            [
                "ERROR: base href is not allowed",
                "ERROR: resource path in script src must be relative: file:///tmp/manual.js",
                "ERROR: resource path in link href must be relative: ftp://example.invalid/manual.css",
                "ERROR: resource path in iframe src must be relative: javascript:alert(1)",
                "ERROR: resource path in source src must be relative: https:\\example.invalid\\manual.mp4",
                "ERROR: resource path in script src must be relative: C:assets/manual.js",
            ],
        )

    def test_windows_drive_relative_resource_path_is_rejected(self):
        self.write_manual(self.valid_sections() + '<script src="C:assets/manual.js"></script>')

        errors = validate_manual(self.root)

        self.assertIn(
            "ERROR: resource path in script src must be relative: C:assets/manual.js",
            errors,
        )

    def test_ascii_control_characters_in_regular_resource_attributes_are_rejected(self):
        resource_attributes = (
            ("script", "src", "</script>"),
            ("image", "href", "</image>"),
        )
        character_references = ("&#x09;", "&#x0D;", "&#x0A;")

        for tag, attribute, closing_tag in resource_attributes:
            for character_reference in character_references:
                with self.subTest(tag=tag, attribute=attribute, control=character_reference):
                    self.write_manual(
                        self.valid_sections()
                        + f'<{tag} {attribute}="ht{character_reference}tps://example.invalid/manual.js">{closing_tag}'
                    )

                    errors = validate_manual(self.root)

                    self.assertIn(
                        f"ERROR: resource path in {tag} {attribute} contains ASCII control characters",
                        errors,
                    )

    def test_css_background_image_remote_url_is_rejected(self):
        self.write_manual(
            self.valid_sections()
            + "<style>.screenshot { background-image: url('https://example.invalid/x.png'); }</style>"
        )

        errors = validate_manual(self.root)

        self.assertIn(
            "ERROR: resource path in CSS url(...) must be relative: https://example.invalid/x.png",
            errors,
        )

    def test_css_font_face_remote_url_is_rejected(self):
        self.write_manual(
            self.valid_sections()
            + '<style>@font-face { src: url(//example.invalid/font.woff2); }</style>'
        )

        errors = validate_manual(self.root)

        self.assertIn(
            "ERROR: resource path in CSS url(...) must be relative: //example.invalid/font.woff2",
            errors,
        )

    def test_img_srcset_remote_candidate_is_rejected(self):
        self.write_manual(
            self.valid_sections()
            + '<img src="assets/guide.png" srcset="assets/guide.png 1x, https://example.invalid/x.png 2x" alt="候选图片">'
        )

        errors = validate_manual(self.root)

        self.assertIn(
            "ERROR: resource path in img srcset must be relative: https://example.invalid/x.png",
            errors,
        )

    def test_srcset_data_candidate_does_not_hide_adjacent_remote_candidate(self):
        safe_body = self.valid_sections() + (
            '<img src="assets/guide.png" srcset="data:image/png;base64,AA==" alt="内联图片">'
        )
        self.write_manual(safe_body)

        self.assertEqual(validate_manual(self.root), [])

        self.write_manual(
            self.valid_sections()
            + '<img src="assets/guide.png" srcset="data:image/png;base64,AA==,https://example.invalid/x.png 2x" alt="内联图片">'
        )
        errors = validate_manual(self.root)

        self.assertIn(
            "ERROR: resource path in img srcset must be relative: https://example.invalid/x.png",
            errors,
        )

    def test_non_base64_srcset_data_candidate_does_not_hide_adjacent_remote_candidate(self):
        safe_body = self.valid_sections() + (
            '<img src="assets/guide.png" srcset="data:image/svg+xml,%3Csvg%3E" alt="内联图片">'
        )
        self.write_manual(safe_body)

        self.assertEqual(validate_manual(self.root), [])

        self.write_manual(
            self.valid_sections()
            + '<img src="assets/guide.png" srcset="data:image/svg+xml,%3Csvg%3E, https://example.invalid/x.png 2x" alt="内联图片">'
        )
        errors = validate_manual(self.root)

        self.assertIn(
            "ERROR: resource path in img srcset must be relative: https://example.invalid/x.png",
            errors,
        )

    def test_svg_resource_hrefs_are_checked_and_safe_references_are_allowed(self):
        self.write_manual(
            self.valid_sections()
            + """
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <path id="arrow"></path>
  <use href="#arrow"></use>
  <image href="assets/guide.png"></image>
  <image xlink:href="data:image/png;base64,AA=="></image>
</svg>
"""
        )

        self.assertEqual(validate_manual(self.root), [])

        self.write_manual(
            self.valid_sections()
            + """
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <image href="https://example.invalid/x.png"></image>
  <image xlink:href="https://example.invalid/xlink.png"></image>
  <feImage href="https://example.invalid/filter.png"></feImage>
  <use href="https://example.invalid/icons.svg#id"></use>
</svg>
"""
        )

        errors = validate_manual(self.root)

        self.assertEqual(
            [error for error in errors if "resource path in" in error],
            [
                "ERROR: resource path in image href must be relative: https://example.invalid/x.png",
                "ERROR: resource path in image xlink:href must be relative: https://example.invalid/xlink.png",
                "ERROR: resource path in feimage href must be relative: https://example.invalid/filter.png",
                "ERROR: resource path in use href must be relative: https://example.invalid/icons.svg#id",
            ],
        )

    def test_picture_source_remote_src_and_srcset_are_rejected(self):
        self.write_manual(
            self.valid_sections()
            + """
<picture>
  <source srcset="https://example.invalid/picture.avif 1x">
  <source src="https://example.invalid/picture.mp4">
  <img src="assets/guide.png" alt="图片后备内容">
</picture>
"""
        )

        errors = validate_manual(self.root)

        self.assertIn(
            "ERROR: resource path in source srcset must be relative: https://example.invalid/picture.avif",
            errors,
        )
        self.assertIn(
            "ERROR: resource path in source src must be relative: https://example.invalid/picture.mp4",
            errors,
        )

    def test_ascii_control_characters_in_srcset_are_rejected_before_tokenization(self):
        character_references = ("&#x09;", "&#x0D;", "&#x0A;")

        for tag in ("img", "source"):
            for character_reference in character_references:
                with self.subTest(tag=tag, control=character_reference):
                    srcset = f"ht{character_reference}tps://example.invalid/picture.avif 1x"
                    if tag == "img":
                        body = (
                            self.valid_sections()
                            + f'<img src="assets/guide.png" srcset="{srcset}" alt="候选图片">'
                        )
                    else:
                        body = self.valid_sections() + f'<source srcset="{srcset}">'
                    self.write_manual(body)

                    errors = validate_manual(self.root)

                    self.assertEqual(
                        [error for error in errors if error.startswith("ERROR: resource path in")],
                        [f"ERROR: resource path in {tag} srcset contains ASCII control characters"],
                    )

    def test_business_workflow_requires_visible_h3_headings(self):
        non_heading_workflow_text = """
<section id="mine-map" data-workflow>
  <h2>手册章节</h2>
  <p>何时使用；前置条件。</p>
  <script>const workflow = "操作步骤；成功标志";</script>
  <style>.workflow::after { content: "注意事项与失败处理"; }</style>
</section>
"""
        body = self.sections_with_replacements({"mine-map": non_heading_workflow_text})
        self.write_manual(body)

        errors = validate_manual(self.root)

        self.assertEqual(
            [error for error in errors if "section mine-map data-workflow is missing heading" in error],
            [
                f"ERROR: section mine-map data-workflow is missing heading: {heading}"
                for heading in WORKFLOW_HEADINGS
            ],
        )

    def test_self_closing_nonvoid_containers_do_not_expose_workflow_h3s(self):
        fake_headings = "".join(f"<h3>{heading}</h3>" for heading in WORKFLOW_HEADINGS)
        expected_errors = [
            f"ERROR: section mine-map data-workflow is missing heading: {heading}"
            for heading in WORKFLOW_HEADINGS
        ]

        for container in ("script", "style"):
            with self.subTest(container=container):
                workflow = f"""
<section id="mine-map" data-workflow>
  <h2>手册章节</h2>
  <{container}/>
  {fake_headings}
  </{container}>
</section>
"""
                body = self.sections_with_replacements({"mine-map": workflow})
                self.write_manual(body)

                errors = validate_manual(self.root)

                self.assertEqual(
                    [
                        error
                        for error in errors
                        if "section mine-map data-workflow is missing heading" in error
                    ],
                    expected_errors,
                )

    def test_nested_section_h3s_do_not_satisfy_outer_workflow(self):
        nested_headings = "".join(f"<h3>{heading}</h3>" for heading in WORKFLOW_HEADINGS)
        outer_workflow = f"""
<section id="mine-map" data-workflow>
  <h2>手册章节</h2>
  <section class="workflow-details">{nested_headings}</section>
</section>
"""
        body = self.sections_with_replacements({"mine-map": outer_workflow})
        self.write_manual(body)

        errors = validate_manual(self.root)

        self.assertEqual(
            [error for error in errors if "section mine-map data-workflow is missing heading" in error],
            [
                f"ERROR: section mine-map data-workflow is missing heading: {heading}"
                for heading in WORKFLOW_HEADINGS
            ],
        )

    def test_template_h3s_do_not_satisfy_outer_workflow(self):
        template_headings = "".join(f"<h3>{heading}</h3>" for heading in WORKFLOW_HEADINGS)
        outer_workflow = f"""
<section id="mine-map" data-workflow>
  <h2>手册章节</h2>
  <template>{template_headings}</template>
</section>
"""
        body = self.sections_with_replacements({"mine-map": outer_workflow})
        self.write_manual(body)

        errors = validate_manual(self.root)

        self.assertEqual(
            [error for error in errors if "section mine-map data-workflow is missing heading" in error],
            [
                f"ERROR: section mine-map data-workflow is missing heading: {heading}"
                for heading in WORKFLOW_HEADINGS
            ],
        )

    def test_business_workflow_requires_separate_h3_for_each_heading(self):
        combined_heading = "；".join(WORKFLOW_HEADINGS)
        combined_heading_workflow = f"""
<section id="mine-map" data-workflow>
  <h2>手册章节</h2>
  <h3>{combined_heading}</h3>
</section>
"""
        body = self.sections_with_replacements({"mine-map": combined_heading_workflow})
        self.write_manual(body)

        errors = validate_manual(self.root)

        self.assertEqual(
            [error for error in errors if "section mine-map data-workflow is missing heading" in error],
            [
                f"ERROR: section mine-map data-workflow is missing heading: {heading}"
                for heading in WORKFLOW_HEADINGS
            ],
        )

    def test_safe_localhost_links_relative_assets_and_data_urls_are_allowed(self):
        self.write_manual(
            self.valid_sections()
            + """
<a href="http://127.0.0.1:4173/">打开矿山地图</a>
<style>.icon { background-image: url("data:image/png;base64,AA=="); }</style>
<picture>
  <source src="assets/manual.mp4" srcset="assets/guide.png 1x, data:image/png;base64,AA== 2x">
  <img src="assets/guide.png" alt="安全图片">
</picture>
"""
        )

        self.assertEqual(validate_manual(self.root), [])

    def test_unclosed_style_and_inline_style_resource_urls_are_rejected(self):
        self.write_manual(
            self.valid_sections()
            + """
<div style="background-image: url('https://example.invalid/inline.png')"></div>
<style>.remote { background-image: url('https://example.invalid/unclosed.png'); }
""",
            include_interaction=False,
        )

        errors = validate_manual(self.root)

        self.assertIn(
            "ERROR: resource path in CSS url(...) must be relative: https://example.invalid/inline.png",
            errors,
        )
        self.assertIn(
            "ERROR: resource path in CSS url(...) must be relative: https://example.invalid/unclosed.png",
            errors,
        )

    def test_css_import_url_is_rejected(self):
        self.write_manual(self.valid_sections() + "<style>@import url('assets/other.css');</style>")

        errors = validate_manual(self.root)

        self.assertTrue(any("CSS @import url" in error for error in errors))

    def test_quoted_css_import_is_rejected(self):
        self.write_manual(
            self.valid_sections() + '<style>@import "https://example.invalid/manual.css";</style>'
        )

        errors = validate_manual(self.root)

        self.assertIn("ERROR: CSS @import url(...) is not allowed", errors)

    def test_css_backslash_escape_sequences_are_rejected(self):
        self.write_manual(
            self.valid_sections()
            + r"""
<style>
  .escaped-name { background-image: u\72l("https://example.invalid/name.png"); }
  .escaped-scheme { background-image: url(https\3a//example.invalid/scheme.png); }
</style>
"""
        )

        errors = validate_manual(self.root)

        self.assertIn("ERROR: CSS escape sequences are not allowed", errors)

    def test_internal_anchor_requires_existing_unique_id(self):
        body = self.valid_sections() + '<area href="#not-present">无效链接</area>'
        self.write_manual(body)

        errors = validate_manual(self.root)

        self.assertTrue(any("#not-present" in error for error in errors))

    def test_duplicate_ids_are_rejected(self):
        self.write_manual(self.valid_sections() + '<div id="quick-start">重复</div>')

        errors = validate_manual(self.root)

        self.assertTrue(any("duplicate id: quick-start" in error for error in errors))

    def test_each_unsafe_literal_pattern_is_independently_detected(self):
        samples = {
            "mine_fid": "mine_fid",
            "CPU": "CPU",
            "device=cpu": "device=cpu",
            "--device cpu": "--device cpu",
            "geoview-jiangxi:cpu": "geoview-jiangxi:cpu",
            "docker compose.*cpu": "docker compose build cpu",
            "SECRET_KEY": "SECRET_KEY",
            "MYSQL_PASSWORD": "MYSQL_PASSWORD",
            "MYSQL_ROOT_PASSWORD": "MYSQL_ROOT_PASSWORD",
            "123456": "123456",
            "Windows user drive path": "C:\\Users\\Alice\\manual",
        }
        expected_matches = {
            "Windows user drive path": "C:\\Users\\",
        }
        self.assertEqual({name for name, _ in UNSAFE_LITERALS}, set(samples))

        for name, sample in samples.items():
            with self.subTest(pattern=name):
                self.write_manual(self.valid_sections() + f"<p>{sample}</p>")

                errors = validate_manual(self.root)

                expected_match = expected_matches.get(name, sample)
                self.assertIn(f"ERROR: unsafe literal: {expected_match}", errors)

    def test_localhost_app_links_are_allowed_but_not_resource_attributes(self):
        body = self.valid_sections() + """
<p>访问 http://127.0.0.1:4173/、http://127.0.0.1:4174/ 或 http://127.0.0.1:5178/。</p>
<a href="http://127.0.0.1:4173/">打开矿山地图</a>
"""
        self.write_manual(body)

        self.assertEqual(validate_manual(self.root), [])

        self.write_manual(body + '<script src="http://127.0.0.1:4173/app.js"></script>')
        errors = validate_manual(self.root)

        self.assertTrue(any("resource path" in error for error in errors))

    def test_each_violation_is_emitted_as_an_error_line(self):
        self.write_manual(self.valid_sections().replace(' id="faq-glossary"', ' id="missing-section"'))

        result = self.run_validator()

        lines = [line for line in result.stdout.splitlines() if line]
        self.assertEqual(result.returncode, 1)
        self.assertTrue(lines)
        self.assertTrue(all(line.startswith("ERROR: ") for line in lines))

    def test_actual_admin_baseline_example_includes_status_and_geojson_count(self):
        manual = ACTUAL_MANUAL.read_text(encoding="utf-8")
        admin_section = re.search(
            r'<section id="admin-maintenance">(.*?)</section>',
            manual,
            flags=re.DOTALL,
        )

        self.assertIsNotNone(admin_section)
        baseline_example = re.search(
            r"本次交付的当前基线示例为：(.*?)</li>",
            admin_section.group(1),
            flags=re.DOTALL,
        )

        self.assertIsNotNone(baseline_example)
        baseline_text = baseline_example.group(1)
        self.assertIn("<code>status ok</code>", baseline_text)
        self.assertIn("<code>geojson_count 348</code>", baseline_text)
        self.assertIn("当前部署基线", baseline_text)
        self.assertIn("永久通用保证", baseline_text)

    def test_actual_screenshot_ledger_matches_visible_callouts_and_figure_notes(self):
        manual = ACTUAL_MANUAL.read_text(encoding="utf-8")
        ledger = ACTUAL_ASSET_LEDGER.read_text(encoding="utf-8")
        expected_annotations = {
            "login-current.png": ("账号与密码输入区", "登录按钮"),
            "map-overview.png": ("筛选查询区", "地图定位区", "右侧统计与详情区"),
            "project-workspace-current.png": (
                "顶部筛选区",
                "左侧项目列表",
                "项目概览区",
                "矿山图斑绑定区",
            ),
            "project-workspace-actions-current.png": ("项目数据集区", "导出与备份区"),
        }
        circled_numbers = "①②③④⑤⑥⑦⑧⑨"
        figures = re.findall(r"<figure\b[^>]*>.*?</figure>", manual, flags=re.DOTALL)

        for filename, annotation_names in expected_annotations.items():
            with self.subTest(screenshot=filename):
                row = next((line for line in ledger.splitlines() if f"`{filename}`" in line), None)
                self.assertIsNotNone(row)
                cells = [cell.strip() for cell in row.split("|")[1:-1]]
                expected_ledger = "；".join(
                    f"{circled_numbers[index - 1]} {name}"
                    for index, name in enumerate(annotation_names, start=1)
                )
                self.assertEqual(cells[-1], expected_ledger)

                figure = next(
                    (
                        candidate
                        for candidate in figures
                        if re.search(rf'\bsrc=["\']assets/{re.escape(filename)}["\']', candidate)
                    ),
                    None,
                )
                self.assertIsNotNone(figure)
                self.assertEqual(
                    re.findall(r'data-callout-label="(\d+)"', figure),
                    [str(index) for index in range(1, len(annotation_names) + 1)],
                )
                notes = re.search(r'<ol class="notes">(.*?)</ol>', figure, flags=re.DOTALL)
                self.assertIsNotNone(notes)
                note_names = [
                    re.sub(r"<[^>]+>", "", item).strip().split("：", 1)[0]
                    for item in re.findall(r"<li>(.*?)</li>", notes.group(1), flags=re.DOTALL)
                ]
                self.assertEqual(note_names, list(annotation_names))

    def test_actual_manual_uses_native_zoom_triggers_and_progressive_copy_controls(self):
        manual = ACTUAL_MANUAL.read_text(encoding="utf-8")
        zoomable_figures = re.findall(
            r"<figure\b(?=[^>]*\bdata-zoomable\b)[^>]*>.*?</figure>",
            manual,
            flags=re.DOTALL,
        )

        self.assertTrue(zoomable_figures)
        for figure in zoomable_figures:
            opening_tag = figure.split(">", 1)[0] + ">"
            self.assertNotRegex(opening_tag, r"\s(?:role|tabindex|aria-label)=")
            image_stage = re.search(
                r'<div class="image-stage">(.*)</div>\s*<figcaption',
                figure,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(image_stage)
            self.assertRegex(
                image_stage.group(1),
                r'<button type="button" data-zoom-trigger aria-label="放大查看[^\"]+"></button>',
            )
        self.assertIn('document.documentElement.classList.add("js");', manual)
        self.assertIn("html:not(.js) [data-copy-button]", manual)
        self.assertIn("html:not(.js) .copy-status", manual)
        self.assertIn("html:not(.js) [data-zoom-trigger] { display: none; }", manual)
        self.assertIn(
            ".js .image-stage [data-zoom-trigger] { position: absolute; inset: 0; z-index: 2; width: 100%; height: 100%; padding: 0; border: 0; background: transparent; cursor: zoom-in; }",
            manual,
        )
        self.assertNotIn(".js [data-zoomable]", manual)
        self.assertRegex(manual, r"@media print[\s\S]*?\.js nav \{ display: block; \}")

        zoom_setup = manual.index('document.querySelectorAll("[data-zoom-trigger]").forEach((trigger) => {')
        click_binding = manual.index('trigger.addEventListener("click"', zoom_setup)
        figure_lookup = 'const figure = trigger.closest("figure[data-zoomable]");'
        self.assertLess(manual.index(figure_lookup, zoom_setup), click_binding)
        self.assertLess(manual.index('document.documentElement.classList.add("js");'), zoom_setup)
        self.assertIn("function openLightbox(figure, trigger)", manual)
        self.assertIn("openLightbox(figure, trigger)", manual)
        self.assertIn("lastZoomTrigger = trigger;", manual)
        self.assertIn("if (lastZoomTrigger) lastZoomTrigger.focus();", manual)
        self.assertNotIn('trigger.setAttribute("role", "button");', manual)
        self.assertNotIn('trigger.setAttribute("tabindex", "0");', manual)
        self.assertNotIn('trigger.setAttribute("aria-label", "放大查看" + image.alt);', manual)
        self.assertNotIn('trigger.addEventListener("keydown"', manual)
        self.assertIn("navigator.clipboard.writeText(command)", manual)

    def test_actual_faq_covers_user_actions_and_technical_terms(self):
        manual = ACTUAL_MANUAL.read_text(encoding="utf-8")
        faq = re.search(
            r'<section id="faq-glossary">(.*?)</section>',
            manual,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(faq)
        faq_content = faq.group(1)
        expected_entries = {
            "登录后出现 401 或共享会话失效怎么办？": ("重新登录", "页面提示"),
            "TBBH 存在但没有历史结果怎么办？": ("查询条件", "维护人员"),
            "map_fid 映射缺失怎么办？": ("记录 TBBH", "技术定位映射"),
            "数据文件损坏怎么办？": ("停止使用", "维护人员"),
            "地物分类结果加载失败怎么办？": ("任务信息", "影像来源"),
            "manifest（资产清单）是什么？": ("运行数据资产", "来源", "版本", "校验摘要"),
            "GPU Worker 是什么？": ("后台工作进程", "地物分类推理"),
            "map_fid 是什么？": ("技术定位", "历史输出", "TBBH 是业务主键"),
        }

        for question, required_terms in expected_entries.items():
            with self.subTest(question=question):
                answer = re.search(
                    rf"<h3>{re.escape(question)}</h3>\s*<p>(.*?)</p>",
                    faq_content,
                    flags=re.DOTALL,
                )
                self.assertIsNotNone(answer)
                answer_text = re.sub(r"<[^>]+>", "", answer.group(1))
                for term in required_terms:
                    self.assertIn(term, answer_text)

        manifest_answer = re.search(
            r"<h3>manifest（资产清单）是什么？</h3>\s*<p>(.*?)</p>",
            faq_content,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(manifest_answer)
        self.assertNotIn("模型资产", re.sub(r"<[^>]+>", "", manifest_answer.group(1)))

        for unsafe_text in (
            "CPU",
            "mine_fid",
            "密码",
            "SECRET_KEY",
            "MYSQL_PASSWORD",
            "MYSQL_ROOT_PASSWORD",
            "123456",
        ):
            self.assertNotIn(unsafe_text, faq_content)
        self.assertNotRegex(faq_content, r"[A-Za-z]:[\\/]")


if __name__ == "__main__":
    unittest.main()
