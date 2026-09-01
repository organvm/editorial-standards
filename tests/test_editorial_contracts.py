from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from validate_editorial_contracts import validate  # noqa: E402


class EditorialContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.fixture_root = Path(self.temporary_directory.name) / "repository"
        shutil.copytree(
            REPO_ROOT,
            self.fixture_root,
            ignore=shutil.ignore_patterns(".git", "__pycache__"),
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def assert_contract_error(self, expected: str) -> None:
        errors = validate(self.fixture_root)
        self.assertTrue(
            any(expected in error for error in errors),
            f"Expected {expected!r} in contract errors: {errors}",
        )

    def test_repository_satisfies_complete_editorial_contract(self) -> None:
        self.assertEqual([], validate(self.fixture_root))

    def test_rejects_readme_table_with_non_delimiter_cell(self) -> None:
        path = self.fixture_root / "README.md"
        original = "|---|---|---|"
        malformed = "|---| Type |---|"
        content = path.read_text(encoding="utf-8")
        self.assertIn(original, content)
        path.write_text(content.replace(original, malformed, 1), encoding="utf-8")

        self.assert_contract_error("invalid frontmatter table delimiter")

    def test_rejects_log_template_missing_schema_required_field(self) -> None:
        path = self.fixture_root / "templates/log.md"
        content = path.read_text(encoding="utf-8")
        self.assertIn("mood: focused\n", content)
        path.write_text(content.replace("mood: focused\n", "", 1), encoding="utf-8")

        self.assert_contract_error("missing required log fields: ['mood']")

    def test_rejects_log_template_value_outside_schema_enum(self) -> None:
        path = self.fixture_root / "templates/log.md"
        content = path.read_text(encoding="utf-8")
        self.assertIn("mood: focused", content)
        path.write_text(
            content.replace("mood: focused", "mood: triumphant", 1),
            encoding="utf-8",
        )

        self.assert_contract_error("outside the schema enum")

    def test_rejects_evaluator_template_without_canonical_project_link(self) -> None:
        path = self.fixture_root / "templates/audiences/evaluator.md"
        link = "[Canonical README](../../README.md)"
        content = path.read_text(encoding="utf-8")
        self.assertIn(link, content)
        path.write_text(content.replace(f"- {link}\n", "", 1), encoding="utf-8")

        self.assert_contract_error("missing canonical project link")


if __name__ == "__main__":
    unittest.main()
