from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_editorial_contracts import (
    _count_visible_markdown_destination,
    _markdown_contract_view,
    validate,
)


class ReaderAcceptanceContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repository"
        shutil.copytree(
            REPO_ROOT, self.root,
            ignore=shutil.ignore_patterns(".git", "__pycache__"),
        )

    def tearDown(self):
        self.temp.cleanup()

    def assert_error(self, text):
        errors = validate(self.root)
        self.assertTrue(any(text in error for error in errors), errors)

    def test_retained_blocks_cannot_join_image_labels(self):
        path = self.root / "templates/audiences/general.md"
        original = path.read_text()
        for boundary in ("***", "* * *", "---", "___", "===", "### Heading",
                         "- New item", "> New quote"):
            with self.subTest(boundary=boundary):
                path.write_text(original + "\n![decoy\n" + boundary + "\n"
                                '<a href="../../README.md">Project home</a>](image.png)\n')
                self.assert_error("duplicate canonical project link")

    def test_nested_link_invalidates_its_outer_link(self):
        path = self.root / "templates/audiences/general.md"
        original = path.read_text()
        for duplicate in (
            "[outer [Project](../../README.md)](https://example.com)",
            "[outer [Project][home]](https://example.com)\n\n[home]: ../../README.md",
            "[outer [Project](../../README.md)][elsewhere]\n\n[elsewhere]: elsewhere.md",
        ):
            with self.subTest(duplicate=duplicate):
                path.write_text(original + "\n" + duplicate + "\n")
                self.assert_error("duplicate canonical project link")

    def test_valid_inline_continuations_and_link_suffixes_remain_hidden(self):
        for content in (
            '![decoy\n<a href="../../README.md">Project home</a>](image.png)',
            '> ![decoy\n> <a href="../../README.md">Project home</a>](image.png)',
            '- ![decoy\n  <a href="../../README.md">Project home</a>](image.png)',
            '[Other](elsewhere.md "[Project](../../README.md)")',
            '[![Project](../../README.md)](elsewhere.md)',
            '[Other](elsewhere.md "<a href=\'../../README.md\'>") '
            '![decoy <a href="../../README.md">](image.png)',
            '[Project](\n2. ../../README.md)',
        ):
            with self.subTest(content=content):
                errors = []
                lines, _fences = _markdown_contract_view(Path("sample.md"), content, errors)
                self.assertEqual([], errors)
                self.assertEqual(0, _count_visible_markdown_destination(lines, "../../README.md"))

    def test_nested_link_stack_handles_many_balanced_outer_openers(self):
        content = "[outer " * 5000 + "[Project](../../README.md)" + "](elsewhere.md)" * 5000
        self.assertEqual(1, _count_visible_markdown_destination([content], "../../README.md"))

    def test_reader_rubric_dimension_order_is_canonical(self):
        path = self.root / "schemas/reader-mode-rubric.yaml"
        rubric = yaml.safe_load(path.read_text())
        rubric["dimensions"] = dict(reversed(list(rubric["dimensions"].items())))
        path.write_text(yaml.safe_dump(rubric, sort_keys=False))
        self.assert_error("canonical reader dimension order")

    def test_seed_schema_version_is_canonical(self):
        path = self.root / "seed.yaml"
        original = path.read_text()
        for version in ("2.0", 1.0, None):
            with self.subTest(version=version):
                value = yaml.safe_dump(version, default_flow_style=True).splitlines()[0]
                path.write_text(original.replace('schema_version: "1.0"', f"schema_version: {value}"))
                self.assert_error("expected schema_version='1.0'")

    def test_category_descriptions_are_canonical(self):
        path = self.root / "schemas/category-taxonomy.yaml"
        original = yaml.safe_load(path.read_text())
        for category in original["categories"]:
            with self.subTest(category=category):
                taxonomy = yaml.safe_load(path.read_text())
                taxonomy["categories"] = {
                    key: dict(value) for key, value in original["categories"].items()
                }
                taxonomy["categories"][category]["description"] = "Anything belongs here."
                path.write_text(yaml.safe_dump(taxonomy, sort_keys=False))
                self.assert_error("canonical category description")


if __name__ == "__main__":
    unittest.main()
