from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from validate_editorial_contracts import (  # noqa: E402
    _find_backtick_run,
    _strip_html_comments_from_line,
    validate,
)


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

    def test_rejects_wrong_or_duplicate_frontmatter_table_header(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        header = "| Field | Type | Core constraint |"
        self.assertEqual(1, original.splitlines().count(header))

        path.write_text(
            original.replace(header, "| Field | Kind | Constraint |", 1),
            encoding="utf-8",
        )
        self.assert_contract_error("frontmatter table header must be exactly")

        path.write_text(
            original.replace(header, f"{header}\n{header}", 1),
            encoding="utf-8",
        )
        self.assert_contract_error("frontmatter table header must appear exactly once")

    def test_rejects_frontmatter_table_cell_drift_from_schema(self) -> None:
        readme_path = self.fixture_root / "README.md"
        schema_path = self.fixture_root / "schemas/frontmatter-schema.yaml"
        original_readme = readme_path.read_text(encoding="utf-8")
        original_schema = schema_path.read_text(encoding="utf-8")
        mutations = (
            (
                readme_path,
                "| `word_count` | integer | minimum 500 |",
                "| `word_count` | string | minimum 500 |",
            ),
            (schema_path, "    min: 500\n", "    min: 750\n"),
            (
                schema_path,
                "enum: [CRITICAL, HIGH, MEDIUM]",
                "enum: [CRITICAL, HIGH]",
            ),
        )
        for path, current, replacement in mutations:
            with self.subTest(path=path.name, replacement=replacement):
                original = path.read_text(encoding="utf-8")
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("frontmatter table/schema cells mismatch")
                readme_path.write_text(original_readme, encoding="utf-8")
                schema_path.write_text(original_schema, encoding="utf-8")

    def test_rejects_frontmatter_table_field_reordering(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        first = "| `layout` | string | `essay` |"
        second = "| `title` | string | 10–200 characters |"
        self.assertIn(f"{first}\n{second}", original)
        path.write_text(
            original.replace(f"{first}\n{second}", f"{second}\n{first}", 1),
            encoding="utf-8",
        )

        self.assert_contract_error("frontmatter table/schema field order mismatch")

    def test_rejects_unrepresented_additive_frontmatter_rule(self) -> None:
        path = self.fixture_root / "schemas/frontmatter-schema.yaml"
        original = path.read_text(encoding="utf-8")
        self.assertIn("    min: 500\n", original)
        path.write_text(
            original.replace("    min: 500\n", "    min: 500\n    max: 1000\n", 1),
            encoding="utf-8",
        )

        self.assert_contract_error("renderer does not cover schema rules")

    def test_validates_optional_frontmatter_rules_without_template_values(self) -> None:
        path = self.fixture_root / "schemas/frontmatter-schema.yaml"
        original = path.read_text(encoding="utf-8")
        optional_start = original.index("optional_fields:")

        malformed = original.replace(
            "  word_count_policy:\n",
            "  word_count_policy: broken\n  ignored_policy:\n",
            1,
        )
        path.write_text(malformed, encoding="utf-8")
        self.assert_contract_error("rules for 'word_count_policy' are not a mapping")

        invalid_type = (
            original[:optional_start]
            + original[optional_start:].replace(
                "    type: string", "    type: boolean", 1
            )
        )
        path.write_text(invalid_type, encoding="utf-8")
        self.assert_contract_error("declare unsupported type 'boolean'")

        invalid_bound = original.replace(
            "    min_length: 20\n", "    min_length: -1\n", 1
        )
        path.write_text(invalid_bound, encoding="utf-8")
        self.assert_contract_error("min_length must be a nonnegative integer")

        incompatible_constraint = original.replace(
            "    min_length: 20\n", "    min_items: 20\n", 1
        )
        path.write_text(incompatible_constraint, encoding="utf-8")
        self.assert_contract_error("contain unsupported keys for 'string'")

        invalid_pattern = original.replace(
            "    min_length: 20\n", "    min_length: 20\n    pattern: '['\n", 1
        )
        path.write_text(invalid_pattern, encoding="utf-8")
        self.assert_contract_error("has invalid pattern")

        duplicate_scope = original.replace(
            "optional_fields:\n",
            "optional_fields:\n  title:\n    type: string\n"
            "    description: duplicate scope\n",
            1,
        )
        path.write_text(duplicate_scope, encoding="utf-8")
        self.assert_contract_error("fields cannot be both required and optional")
        path.write_text(original, encoding="utf-8")

    def test_requires_nonempty_string_schema_field_and_property_keys(self) -> None:
        frontmatter_path = self.fixture_root / "schemas/frontmatter-schema.yaml"
        original_frontmatter = frontmatter_path.read_text(encoding="utf-8")
        for key in ("7", "true", "null", '""'):
            with self.subTest(scope="optional_fields", key=key):
                injected = (
                    "optional_fields:\n"
                    f"  {key}:\n"
                    "    type: string\n"
                    "    description: Invalid field key.\n"
                )
                frontmatter_path.write_text(
                    original_frontmatter.replace(
                        "optional_fields:\n", injected, 1
                    ),
                    encoding="utf-8",
                )
                self.assert_contract_error("keys must be nonempty strings")
                frontmatter_path.write_text(original_frontmatter, encoding="utf-8")

        log_path = self.fixture_root / "schemas/log-schema.yaml"
        original_log = log_path.read_text(encoding="utf-8")
        properties = "    properties:\n"
        self.assertIn(properties, original_log)
        log_path.write_text(
            original_log.replace(
                properties,
                properties
                + "      7:\n"
                + "        type: string\n"
                + "        description: Invalid property key.\n",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("properties: keys must be nonempty strings")

    def test_reports_malformed_rule_keys_types_and_list_items_without_crashing(self) -> None:
        schema_path = self.fixture_root / "schemas/frontmatter-schema.yaml"
        template_path = self.fixture_root / "templates/guide.md"
        original_schema = schema_path.read_text(encoding="utf-8")
        original_template = template_path.read_text(encoding="utf-8")

        rule_anchor = "  layout:\n    type: string\n"
        self.assertIn(rule_anchor, original_schema)
        schema_path.write_text(
            original_schema.replace(
                rule_anchor,
                "  layout:\n    type: string\n    7: invalid-rule-key\n",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("keys must be nonempty strings")

        for malformed_type in ("[string]", "{kind: string}"):
            with self.subTest(type=malformed_type):
                schema_path.write_text(
                    original_schema.replace(
                        rule_anchor,
                        f"  layout:\n    type: {malformed_type}\n",
                        1,
                    ),
                    encoding="utf-8",
                )
                self.assert_contract_error("declare unsupported type")

        schema_path.write_text(
            original_schema.replace(
                "optional_fields:\n",
                "optional_fields:\n"
                "  unsafe_items:\n"
                "    type: list\n"
                "    item_type: \"\"\n"
                "    item_pattern: '^x$'\n"
                "    description: Malformed item rule.\n",
                1,
            ),
            encoding="utf-8",
        )
        template_path.write_text(
            original_template.replace(
                "references: []\n", "references: []\nunsafe_items: [1]\n", 1
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("declare unsupported item_type")
        self.assert_contract_error("item_pattern requires item_type 'string'")

    def test_enforces_integer_enums_for_essay_and_log_values(self) -> None:
        schema_path = self.fixture_root / "schemas/frontmatter-schema.yaml"
        template_path = self.fixture_root / "templates/guide.md"
        original_schema = schema_path.read_text(encoding="utf-8")
        original_template = template_path.read_text(encoding="utf-8")
        schema_path.write_text(
            original_schema.replace(
                "optional_fields:\n",
                "optional_fields:\n"
                "  edition:\n"
                "    type: integer\n"
                "    enum: [1]\n"
                "    description: Exact edition.\n",
                1,
            ),
            encoding="utf-8",
        )
        template_path.write_text(
            original_template.replace("references: []\n", "references: []\nedition: 2\n", 1),
            encoding="utf-8",
        )
        self.assert_contract_error("field 'edition' has value 2 outside the schema enum")

        log_schema_path = self.fixture_root / "schemas/log-schema.yaml"
        log_template_path = self.fixture_root / "templates/log.md"
        original_log_schema = log_schema_path.read_text(encoding="utf-8")
        original_log_template = log_template_path.read_text(encoding="utf-8")
        log_schema_path.write_text(
            original_log_schema.replace(
                "      commits:\n        type: integer\n        min: 0\n",
                "      commits:\n        type: integer\n        enum: [1]\n        min: 0\n",
                1,
            ),
            encoding="utf-8",
        )
        log_template_path.write_text(
            original_log_template.replace(
                "mood: focused\n",
                "mood: focused\n"
                "activity:\n"
                '  since: "2026-09-01"\n'
                "  commits: 2\n"
                "  repos_active: 0\n"
                "  files_changed: 0\n",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error(
            "field 'activity.commits' has value 2 outside the schema enum"
        )

    def test_enforces_nested_essay_object_required_and_known_keys(self) -> None:
        schema_path = self.fixture_root / "schemas/frontmatter-schema.yaml"
        template_path = self.fixture_root / "templates/guide.md"
        schema = schema_path.read_text(encoding="utf-8")
        template = template_path.read_text(encoding="utf-8")
        schema_path.write_text(
            schema.replace(
                "optional_fields:\n",
                "optional_fields:\n"
                "  provenance:\n"
                "    type: object\n"
                "    required_keys: [source]\n"
                "    properties:\n"
                "      source:\n"
                "        type: string\n"
                "    description: Bounded source record.\n",
                1,
            ),
            encoding="utf-8",
        )
        template_path.write_text(
            template.replace(
                "references: []\n",
                "references: []\nprovenance:\n  unauthorized: true\n",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("field 'provenance' is missing required keys")
        self.assert_contract_error("field 'provenance' has unknown keys")

    def test_rejects_gap_before_frontmatter_table_data(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        delimiter = "|---|---|---|\n"
        self.assertIn(delimiter, original)
        for gap in ("\n", "Detached table guidance.\n"):
            with self.subTest(gap=gap):
                path.write_text(
                    original.replace(delimiter, delimiter + gap, 1),
                    encoding="utf-8",
                )
                self.assert_contract_error(
                    "frontmatter table data rows must start immediately"
                )
        path.write_text(original, encoding="utf-8")

    def test_rejects_frontmatter_table_rendered_only_as_code(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        lines = original.splitlines()
        header_index = lines.index("| Field | Type | Core constraint |")
        table_end = header_index + 1
        while table_end + 1 < len(lines) and lines[table_end + 1].startswith("|"):
            table_end += 1
        lines.insert(header_index, "```markdown")
        lines.insert(table_end + 2, "```")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        self.assert_contract_error("frontmatter table header must appear exactly once")

    def test_rejects_frontmatter_table_rendered_as_indented_code(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        lines = original.splitlines()
        header_index = lines.index("| Field | Type | Core constraint |")
        table_end = header_index + 1
        while table_end + 1 < len(lines) and lines[table_end + 1].startswith("|"):
            table_end += 1

        for indentation in ("    ", "\t", " \t", "   \t"):
            with self.subTest(indentation=repr(indentation)):
                mutated = lines.copy()
                mutated[header_index : table_end + 1] = [
                    indentation + line
                    for line in mutated[header_index : table_end + 1]
                ]
                path.write_text("\n".join(mutated) + "\n", encoding="utf-8")
                self.assert_contract_error(
                    "frontmatter table header must appear exactly once"
                )
        path.write_text(original, encoding="utf-8")

    def test_rejects_incomplete_root_readme_orientation(self) -> None:
        path = self.fixture_root / "templates/repository-readme-v2.md"
        original = path.read_text(encoding="utf-8")
        required_lines = (
            "> [One ordinary-language sentence: what this is, what it does, and why it exists.]",
            "Keep only verified, enabled destinations in both the following hero row and the",
            "[View the project] · [See a demonstration] · [Technical documentation] ·",
        )
        for line in required_lines:
            with self.subTest(line=line):
                self.assertIn(line, original)
                path.write_text(original.replace(line, "", 1), encoding="utf-8")
                self.assert_contract_error("missing required template marker")
                path.write_text(original, encoding="utf-8")

    def test_rejects_at_a_glance_table_outside_its_section(self) -> None:
        path = self.fixture_root / "templates/repository-readme-v2.md"
        original = path.read_text(encoding="utf-8")
        lines = original.splitlines()
        header = "| | |"
        canonical = "## Canonical project documentation"
        header_index = lines.index(header)
        row_end = header_index + 2
        while row_end < len(lines) and lines[row_end].startswith("|"):
            row_end += 1
        table = lines[header_index:row_end]
        del lines[header_index:row_end]
        canonical_index = lines.index(canonical)
        lines[canonical_index + 1:canonical_index + 1] = [""] + table
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        self.assert_contract_error("required template markers are out of order")

        path.write_text(
            original.replace(
                "## Project at a glance\n\n| | |",
                "## Project at a glance\n\n## Intervening section\n\n| | |",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("must remain within section")

    def test_binds_every_required_reader_table_to_its_section(self) -> None:
        mutations = (
            (
                "docs/reader-mode-documentation.md",
                "## Reader questions\n\n| Reader mode | First question | Foreground |",
                "## Reader questions\n\n## Detached reader questions\n\n"
                "| Reader mode | First question | Foreground |",
            ),
            (
                "docs/reader-mode-documentation.md",
                "## Repository classes\n\nClass controls documentation breadth. It is not a prestige grade.\n\n"
                "| Class | Repository function | Required documentation |",
                "## Repository classes\n\nClass controls documentation breadth. It is not a prestige grade.\n\n"
                "## Detached classes\n\n"
                "| Class | Repository function | Required documentation |",
            ),
            (
                "templates/repository-readme-v2.md",
                "## Choose your reading path\n\n| I am reading as… | Start here |",
                "## Choose your reading path\n\n## Detached route table\n\n| I am reading as… | Start here |",
            ),
            (
                "templates/evidence.md",
                "## Assertion evidence\n\n| ID | Claim | Claim posture | Assertion class | Verification state | Evidence | Freshness |",
                "## Assertion evidence\n\n## Detached assertions\n\n| ID | Claim | Claim posture | Assertion class | Verification state | Evidence | Freshness |",
            ),
            (
                "templates/evidence.md",
                "## Project limitations\n\n| ID | Limitation | Related assertion |",
                "## Project limitations\n\n## Detached limitations\n\n| ID | Limitation | Related assertion |",
            ),
        )
        for relative_path, current, replacement in mutations:
            with self.subTest(path=relative_path, replacement=replacement):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("must remain within section")
                path.write_text(original, encoding="utf-8")

    def test_requires_every_reader_question_and_repository_class_row(self) -> None:
        path = self.fixture_root / "docs/reader-mode-documentation.md"
        original = path.read_text(encoding="utf-8")
        row_labels = (
            "General",
            "Technical",
            "Humanities",
            "Business",
            "Evaluator",
            "A — Flagship system",
            "B — Major project",
            "C — Supporting component",
            "D — Deployment artifact",
            "E — Research/theory",
            "F — Archive/reference",
        )
        for label in row_labels:
            with self.subTest(label=label):
                row = next(
                    line
                    for line in original.splitlines()
                    if line.startswith(f"| {label} |")
                )
                path.write_text(original.replace(f"{row}\n", "", 1), encoding="utf-8")
                self.assert_contract_error("row labels/order mismatch")
                path.write_text(original, encoding="utf-8")

        header = "| Class | Repository function | Required documentation |"
        self.assertIn(header, original)
        path.write_text(original.replace(header, "", 1), encoding="utf-8")
        self.assert_contract_error("required table header")

        for label in row_labels:
            with self.subTest(label=label, mutation="normative-cell"):
                row = next(
                    line
                    for line in original.splitlines()
                    if line.startswith(f"| {label} |")
                )
                cells = row.split("|")
                self.assertGreaterEqual(len(cells), 5)
                cells[-2] = " Reversed or unverified guidance "
                replacement = "|".join(cells)
                path.write_text(
                    original.replace(row, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("canonical rows mismatch")
                path.write_text(original, encoding="utf-8")

    def test_pins_complete_root_readme_sequence_in_its_section(self) -> None:
        path = self.fixture_root / "docs/reader-mode-documentation.md"
        original = path.read_text(encoding="utf-8")
        entries = (
            "1. project name;",
            "2. one ordinary-language sentence stating what it is, what it does, and why;",
            "3. verified links to the artifact, demo, or inspection path;",
            "4. a short “What am I looking at?” explanation;",
            "5. an audience-route table;",
            "6. project status, primary users, authorship, evidence, and limitations at a glance.",
        )
        for entry in entries:
            with self.subTest(entry=entry, mutation="deleted"):
                self.assertIn(entry, original)
                path.write_text(
                    original.replace(f"{entry}\n", "", 1), encoding="utf-8"
                )
                self.assert_contract_error("root README sequence mismatch")
                path.write_text(original, encoding="utf-8")

        path.write_text(
            original.replace(
                f"{entries[0]}\n{entries[1]}",
                f"{entries[1]}\n{entries[0]}",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("root README sequence mismatch")

        ordered_list = "\n".join(entries)
        path.write_text(
            original.replace(ordered_list, f"```text\n{ordered_list}\n```", 1),
            encoding="utf-8",
        )
        self.assert_contract_error("root README sequence mismatch")
        path.write_text(original, encoding="utf-8")

    def test_rejects_empty_reader_contract_table_cells(self) -> None:
        path = self.fixture_root / "docs/reader-mode-documentation.md"
        original = path.read_text(encoding="utf-8")
        mutations = (
            (
                "| General | What is this, and why should I care? | Recognition, example, current state |",
                "| General | | Recognition, example, current state |",
            ),
            (
                "| F — Archive/reference | Superseded or preserved material | Archive notice, provenance, immutable status, correct redirect |",
                "| F — Archive/reference | Superseded or preserved material | |",
            ),
        )
        for current, replacement in mutations:
            with self.subTest(replacement=replacement):
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("has empty values")
                path.write_text(original, encoding="utf-8")

    def test_requires_populated_evidence_and_limitation_rows(self) -> None:
        path = self.fixture_root / "templates/evidence.md"
        original = path.read_text(encoding="utf-8")
        rows = (
            next(
                line
                for line in original.splitlines()
                if line.startswith("| [claim-id] |")
            ),
            next(
                line
                for line in original.splitlines()
                if line.startswith("| [limitation-id] |")
            ),
        )
        for row in rows:
            cells = row[1:-1].split("|")
            for index in range(1, len(cells)):
                with self.subTest(row=cells[0].strip(), empty_column=index):
                    mutated_cells = cells.copy()
                    mutated_cells[index] = " "
                    mutated_row = "|" + "|".join(mutated_cells) + "|"
                    path.write_text(
                        original.replace(row, mutated_row, 1), encoding="utf-8"
                    )
                    self.assert_contract_error("has empty values")
                    path.write_text(original, encoding="utf-8")

        empty_assertion = "|" + "|".join(" " for _ in range(7)) + "|"
        path.write_text(original.replace(rows[0], empty_assertion, 1), encoding="utf-8")
        self.assert_contract_error("row labels/order mismatch")
        path.write_text(original, encoding="utf-8")

    def test_pins_every_evidence_and_limitation_placeholder_cell(self) -> None:
        path = self.fixture_root / "templates/evidence.md"
        original = path.read_text(encoding="utf-8")
        rows = (
            next(
                line
                for line in original.splitlines()
                if line.startswith("| [claim-id] |")
            ),
            next(
                line
                for line in original.splitlines()
                if line.startswith("| [limitation-id] |")
            ),
        )
        for row in rows:
            cells = [cell.strip() for cell in row[1:-1].split("|")]
            for index in range(len(cells)):
                with self.subTest(row=cells[0], column=index):
                    mutated_cells = cells.copy()
                    mutated_cells[index] = f"[noncanonical-{index}]"
                    mutated_row = "| " + " | ".join(mutated_cells) + " |"
                    path.write_text(
                        original.replace(row, mutated_row, 1), encoding="utf-8"
                    )
                    self.assert_contract_error("canonical rows mismatch")
                path.write_text(
                    original,
                    encoding="utf-8",
                )

    def test_pins_every_audience_route_row_and_destination(self) -> None:
        path = self.fixture_root / "templates/repository-readme-v2.md"
        original = path.read_text(encoding="utf-8")
        rows = (
            "| A general reader | [Two-minute explanation](docs/audiences/general.md) |",
            "| A software engineer | [Technical architecture](docs/audiences/technical.md) |",
            "| A humanities scholar | [Conceptual and cultural framing](docs/audiences/humanities.md) |",
            "| An industry practitioner | [Operational applications](docs/audiences/business.md) |",
            "| A hiring manager or evaluator | [Contribution and evidence](docs/audiences/evaluator.md) |",
        )
        for row in rows:
            with self.subTest(row=row, mutation="deleted"):
                self.assertIn(row, original)
                path.write_text(
                    original.replace(f"{row}\n", "", 1), encoding="utf-8"
                )
                self.assert_contract_error("row labels/order mismatch")
                path.write_text(original, encoding="utf-8")

            with self.subTest(row=row, mutation="destination drift"):
                path.write_text(
                    original.replace(
                        row,
                        row.replace("docs/audiences/", "docs/disabled/"),
                        1,
                    ),
                    encoding="utf-8",
                )
                self.assert_contract_error("canonical rows mismatch")
                path.write_text(original, encoding="utf-8")

        path.write_text(
            original.replace(
                f"{rows[0]}\n{rows[1]}",
                f"{rows[1]}\n{rows[0]}",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("row labels/order mismatch")

    def test_requires_every_at_a_glance_row_contiguously(self) -> None:
        path = self.fixture_root / "templates/repository-readme-v2.md"
        original = path.read_text(encoding="utf-8")
        row_labels = (
            "What it is",
            "Problem addressed",
            "Current state",
            "Primary users",
            "What Anthony built",
            "Evidence",
            "Known limitations",
        )
        for label in row_labels:
            with self.subTest(label=label):
                lines = original.splitlines()
                row = next(line for line in lines if line.startswith(f"| **{label}** |"))
                path.write_text(original.replace(f"{row}\n", "", 1), encoding="utf-8")
                self.assert_contract_error("row labels/order mismatch")
                path.write_text(original, encoding="utf-8")

        first_row = "| **What it is** | [Canonical definition] |\n"
        self.assertIn(first_row, original)
        path.write_text(
            original.replace(first_row, first_row + "Detached guidance.\n", 1),
            encoding="utf-8",
        )
        self.assert_contract_error("row labels/order mismatch")

        path.write_text(
            original.replace(
                "| **Evidence** | [Tests, source, demo, deployment record, or case study] |",
                "| **Evidence** | |",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("has empty values")

    def test_rejects_noncanonical_seed_or_generated_owner(self) -> None:
        mutations = (
            (
                "seed.yaml",
                "org: organvm",
                "org: organvm-v-logos",
                "organvm-v-logos",
            ),
            (
                "seed.yaml",
                "Automation Contract for organvm/editorial-standards",
                "Automation Contract for other/editorial-standards",
                "canonical identity line",
            ),
            (
                "CLAUDE.md",
                "**Org:** `organvm`",
                "**Org:** `organvm-v-logos`",
                "organvm-v-logos",
            ),
            (
                "GEMINI.md",
                "**Org:** `organvm`",
                "**Org:** `organvm-v-logos`",
                "organvm-v-logos",
            ),
            (
                "ecosystem.yaml",
                "repo: editorial-standards",
                "repo: wrong-repository",
                "ecosystem.yaml: expected repo",
            ),
            (
                "ecosystem.yaml",
                "organ: V",
                "organ: VI",
                "ecosystem.yaml: expected organ",
            ),
        )
        for relative_path, canonical, replacement, expected_error in mutations:
            with self.subTest(path=relative_path):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertIn(canonical, original)
                path.write_text(
                    original.replace(canonical, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error(expected_error)
                path.write_text(original, encoding="utf-8")

    def test_rejects_arbitrary_noncanonical_identity_references(self) -> None:
        mutations = (
            (
                "CHANGELOG.md",
                "github.com/organvm/editorial-standards/compare",
                "github.com/other/editorial-standards/compare",
            ),
            (
                "DISCOVERY.md",
                "# Discovery: organvm/editorial-standards",
                "# Discovery: other/editorial-standards",
            ),
            (
                "README.md",
                "https://github.com/organvm)",
                "https://github.com/orgnvm)",
            ),
            (
                "README.md",
                "https://github.com/organvm/public-process",
                "https://github.com/other/public-process",
            ),
            (
                "schemas/frontmatter-schema.yaml",
                "organvm/public-process/_posts/",
                "other/public-process/_posts/",
            ),
            (
                "schemas/log-schema.yaml",
                "organvm/public-process/_logs/",
                "other/public-process/_logs/",
            ),
            (
                "value-repos.json",
                '"repo": "organvm/editorial-standards"',
                '"repo": "other/editorial-standards"',
            ),
        )
        for relative_path, canonical, replacement in mutations:
            with self.subTest(path=relative_path):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertIn(canonical, original)
                path.write_text(
                    original.replace(canonical, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("canonical identity line")
                path.write_text(original, encoding="utf-8")

        readme_path = self.fixture_root / "README.md"
        original_readme = readme_path.read_text(encoding="utf-8")
        readme_path.write_text(
            original_readme
            + "\ngit clone https://github.com/other/editorial-standards.git\n",
            encoding="utf-8",
        )
        self.assert_contract_error("canonical identity lines for prefix")

        readme_path.write_text(
            original_readme
            + "\nSee https://github.com/other/editorial-standards/issues/1.\n",
            encoding="utf-8",
        )
        self.assert_contract_error("noncanonical GitHub owner")

    def test_requires_a_parseable_value_registry_mapping(self) -> None:
        path = self.fixture_root / "value-repos.json"
        original = path.read_text(encoding="utf-8")
        mutations = (
            (
                original.replace(
                    '"schema_version": "1.0",',
                    '"schema_version": "1.0",,',
                    1,
                ),
                "invalid JSON",
            ),
            (
                original.replace(
                    '"schema_version": "1.0",',
                    '"schema_version": "1.0",\n  "schema_version": "1.0",',
                    1,
                ),
                "duplicate key 'schema_version'",
            ),
            ("[]\n", "registry root must be a JSON mapping"),
            ('{"value_repos": {}}\n', "value_repos must be a JSON list"),
            (
                '{"value_repos": ["organvm/editorial-standards"]}\n',
                "value_repos entries must be JSON mappings",
            ),
            (
                '{"value_repos": [{"repo": "other/repository"}]}\n',
                "expected exactly one canonical registry entry",
            ),
            (
                '{"value_repos": ['
                '{"repo": "organvm/editorial-standards"}, '
                '{"repo": "organvm/editorial-standards"}]}\n',
                "found 2",
            ),
        )
        for content, expected_error in mutations:
            with self.subTest(expected_error=expected_error):
                path.write_text(content, encoding="utf-8")
                self.assert_contract_error(expected_error)
        path.write_text(original, encoding="utf-8")

    def test_pins_every_canonical_registry_entry_field(self) -> None:
        path = self.fixture_root / "value-repos.json"
        original = path.read_text(encoding="utf-8")
        mutations = (
            ('"tier": "ranked"', '"tier": "unranked"'),
            ('"discovered": "2026-06-22"', '"discovered": "unknown"'),
            (
                '"value_thesis": "Only repo in the estate',
                '"value_thesis": "Unreviewed replacement',
            ),
            (
                '"first_task": "Ship a standalone',
                '"first_task": "Ignore the executable plan',
            ),
            ('"discovery_doc": "DISCOVERY.md"', '"discovery_doc": "MISSING.md"'),
            (
                '"tier": "ranked",',
                '"tier": "ranked",\n      "unreviewed": true,',
            ),
        )
        for current, replacement in mutations:
            with self.subTest(replacement=replacement):
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("canonical registry entry must match")
        path.write_text(original, encoding="utf-8")

    def test_rejects_missing_or_unclassified_schema_files(self) -> None:
        required_schema_files = (
            "category-taxonomy.yaml",
            "frontmatter-schema.yaml",
            "log-schema.yaml",
            "quality-rubric.yaml",
            "reader-mode-rubric.yaml",
            "tag-governance.yaml",
        )
        for filename in required_schema_files:
            with self.subTest(missing=filename):
                path = self.fixture_root / "schemas" / filename
                original = path.read_text(encoding="utf-8")
                path.unlink()
                self.assert_contract_error("schema inventory mismatch")
                path.write_text(original, encoding="utf-8")

        extra = self.fixture_root / "schemas/unclassified.yaml"
        extra.write_text("schema_version: '1.0'\n", encoding="utf-8")
        self.assert_contract_error("schema inventory mismatch")

        extra.unlink()
        nested = self.fixture_root / "schemas/nested/unclassified.yml"
        nested.parent.mkdir()
        nested.write_text("schema_version: '1.0'\n", encoding="utf-8")
        self.assert_contract_error("schema inventory mismatch")

    def test_rejects_every_unclassified_or_symlinked_template_artifact(self) -> None:
        for relative_path in (
            "templates/audiences/rogue.markdown",
            "templates/audiences/rogue.mdx",
            "templates/rogue.txt",
        ):
            with self.subTest(path=relative_path):
                path = self.fixture_root / relative_path
                path.write_text("Conflicting ungoverned template.\n", encoding="utf-8")
                self.assert_contract_error("unclassified template files")
                path.unlink()

        path = self.fixture_root / "templates/guide.md"
        original = path.read_text(encoding="utf-8")
        path.unlink()
        path.symlink_to("/etc/passwd")
        self.assert_contract_error("required contained regular publication template")
        path.unlink()
        path.write_text(original, encoding="utf-8")

    def test_rejects_empty_required_schema(self) -> None:
        path = self.fixture_root / "schemas/reader-mode-rubric.yaml"
        path.write_text("", encoding="utf-8")

        self.assert_contract_error("schema must be a YAML mapping")

    def test_rejects_schema_metadata_drift(self) -> None:
        path = self.fixture_root / "schemas/reader-mode-rubric.yaml"
        original = path.read_text(encoding="utf-8")
        path.write_text(
            original.replace('schema_version: "1.0"', 'schema_version: "2.0"', 1),
            encoding="utf-8",
        )
        self.assert_contract_error("schema_version must be '1.0'")

        path.write_text(
            original.replace("description: >-", 'description: ""\nignored: >-', 1),
            encoding="utf-8",
        )
        self.assert_contract_error("schema needs a nonempty description")

    def test_requires_exact_unique_rendered_readme_h2_sections(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        headings = (
            "## Essay Categories",
            "## Quality Rubric",
            "## Frontmatter Schema",
            "## Development",
        )
        for heading in headings:
            self.assertEqual(1, original.splitlines().count(heading))
            for replacement in (
                f"Not a heading: {heading}",
                f"{heading} amended",
                f"{heading}\n{heading}",
                f"<!--\n{heading}\n-->",
                f"```markdown\n{heading}\n```",
            ):
                with self.subTest(heading=heading, replacement=replacement):
                    path.write_text(
                        original.replace(heading, replacement, 1),
                        encoding="utf-8",
                    )
                    self.assert_contract_error(
                        f"heading {heading!r} must appear exactly once"
                    )
                    path.write_text(original, encoding="utf-8")

    def test_ignores_fake_development_commands_inside_raw_html(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        heading = "## Development"
        start = original.index(heading)
        end = original.index("\n## Contributing", start)
        fake_section = original[start:end]
        install = (
            "python3 -m pip install --require-hashes --only-binary=:all: "
            "-r requirements-ci.txt"
        )
        self.assertEqual(1, original.count(install))
        attacked = (
            "<div>\n"
            + fake_section
            + "\n</div>\n\n"
            + original.replace(install, "python3 -m pip --version", 1)
        )
        path.write_text(attacked, encoding="utf-8")

        self.assert_contract_error("missing local CI reproduction command")

    def test_rejects_missing_local_ci_reproduction_command(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        commands = (
            "python3 scripts/validate_editorial_contracts.py",
            "python3 -m unittest discover -s tests -v",
            "git diff --check",
        )
        for command in commands:
            with self.subTest(command=command, mutation="deleted"):
                self.assertIn(command, original)
                path.write_text(original.replace(command, "", 1), encoding="utf-8")
                self.assert_contract_error("missing local CI reproduction command")
                path.write_text(original, encoding="utf-8")
            with self.subTest(command=command, mutation="commented"):
                path.write_text(
                    original.replace(command, f"# {command}", 1), encoding="utf-8"
                )
                self.assert_contract_error("missing local CI reproduction command")
                path.write_text(original, encoding="utf-8")

    def test_requires_license_and_fail_closed_structure_checks(self) -> None:
        license_path = self.fixture_root / "LICENSE"
        license_content = license_path.read_text(encoding="utf-8")
        self.assertTrue(license_path.is_file())
        license_path.unlink()
        self.assert_contract_error("canonical license file is missing")
        license_path.write_text(license_content, encoding="utf-8")

        license_path.unlink()
        license_path.symlink_to("/etc/passwd")
        self.assert_contract_error("canonical license file is missing")
        license_path.unlink()
        license_path.write_text(license_content, encoding="utf-8")

        license_path.write_text("", encoding="utf-8")
        self.assert_contract_error("canonical license file is missing")
        license_path.write_text(license_content + "\n", encoding="utf-8")
        self.assert_contract_error("canonical license file is missing")
        license_path.write_text(license_content, encoding="utf-8")

        readme_path = self.fixture_root / "README.md"
        workflow_path = self.fixture_root / ".github/workflows/ci.yml"
        readme = readme_path.read_text(encoding="utf-8")
        workflow = workflow_path.read_text(encoding="utf-8")
        command = (
            'test -f "LICENSE" && ! test -L "LICENSE" && test -s "LICENSE" && '
            'python3 -c "import hashlib,pathlib,sys; p=pathlib.Path(\'LICENSE\'); '
            "sys.exit(0 if hashlib.sha256(p.read_bytes()).hexdigest() == "
            "'65bfcf3e7864ed904700d0f80159399d07faf071600c194f0c9152d653012f3d' "
            'else 1)" && echo '
            '"::notice::License file found" || exit 1'
        )
        self.assertIn(command, readme)
        self.assertIn(command, workflow)

        readme_path.write_text(readme.replace(command, "", 1), encoding="utf-8")
        self.assert_contract_error("missing local CI reproduction command")
        readme_path.write_text(readme, encoding="utf-8")

        workflow_path.write_text(
            workflow.replace(
                command,
                'test -f "LICENSE" || echo "::warning::No license file found"',
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("structure validation command must fail closed")

    def test_rejects_symlinked_workflow_and_schema_trust_inputs(self) -> None:
        cases = (
            (".github/workflows/ci.yml", "workflow-copy.yml"),
            ("schemas/frontmatter-schema.yaml", "frontmatter-copy.yaml"),
        )
        for relative_path, backup_name in cases:
            with self.subTest(path=relative_path):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                backup = self.fixture_root / backup_name
                backup.write_text(original, encoding="utf-8")
                path.unlink()
                path.symlink_to(backup)
                self.assert_contract_error("required contained regular YAML file")
                path.unlink()
                path.write_text(original, encoding="utf-8")
                backup.unlink()

    def test_requires_local_ci_commands_once_and_in_hosted_order(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        install = (
            "python3 -m pip install --require-hashes --only-binary=:all: "
            "-r requirements-ci.txt"
        )
        unit_tests = "python3 -m unittest discover -s tests -v"

        reordered = (
            original.replace(install, "__INSTALL_COMMAND__", 1)
            .replace(unit_tests, install, 1)
            .replace("__INSTALL_COMMAND__", unit_tests, 1)
        )
        path.write_text(reordered, encoding="utf-8")
        self.assert_contract_error("must follow hosted CI order")

        path.write_text(
            original.replace(f"{install}\n", f"{install}\n{install}\n", 1),
            encoding="utf-8",
        )
        self.assert_contract_error("duplicate local CI reproduction command")
        path.write_text(original, encoding="utf-8")

    def test_rejects_unclassified_or_bypassed_local_recipe_commands(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        validation = "python3 scripts/validate_editorial_contracts.py"
        mutations = (
            original.replace(
                validation,
                "git checkout origin/main -- scripts tests\n" + validation,
                1,
            ),
            original.replace(validation, validation + " || true", 1),
            original.replace(
                "Before committing, also run",
                "```bash\ngit status --short\n```\n\nBefore committing, also run",
                1,
            ),
            original.replace(
                "Before committing, also run",
                "```sh\ngit checkout origin/main -- scripts tests\n```\n\n"
                "Before committing, also run",
                1,
            ),
            original.replace(
                "Before committing, also run",
                "```\ngit checkout origin/main -- scripts tests\n```\n\n"
                "Before committing, also run",
                1,
            ),
            original.replace(
                "Before committing, also run",
                "    git checkout origin/main -- scripts tests\n\n"
                "Before committing, also run",
                1,
            ),
            original.replace(
                "Before committing, also run",
                "<pre><code>git checkout origin/main -- scripts tests"
                "</code></pre>\n\nBefore committing, also run",
                1,
            ),
            original.replace(
                "Before committing, also run",
                "<details>\n<summary>Alternate recipe</summary>\n"
                "<pre><code>git checkout origin/main -- scripts tests"
                "</code></pre>\n</details>\n\nBefore committing, also run",
                1,
            ),
            original.replace(
                "Before committing, also run",
                "```text\n## Escape\n```\n"
                "<pre><code>git checkout origin/main -- scripts tests"
                "</code></pre>\n\nBefore committing, also run",
                1,
            ),
            original.replace(
                "Before committing, also run",
                "~~~text\n## Escape\n~~~\n"
                "<pre><code>git checkout origin/main -- scripts tests"
                "</code></pre>\n\nBefore committing, also run",
                1,
            ),
            original.replace(
                "Before committing, also run",
                "`\n## Escape\n`\n"
                "<pre><code>git checkout origin/main -- scripts tests"
                "</code></pre>\n\nBefore committing, also run",
                1,
            ),
        )
        for mutated in mutations:
            with self.subTest(mutation=mutated[len(original) : len(original) + 80]):
                path.write_text(mutated, encoding="utf-8")
                self.assert_contract_error(
                    "Development"
                )
                path.write_text(original, encoding="utf-8")

        path.write_text(
            original.replace(validation, "# exact-head validation\n" + validation, 1),
            encoding="utf-8",
        )
        self.assertEqual([], validate(self.fixture_root))

    def test_binds_complete_multiline_yaml_command_to_hosted_ci(self) -> None:
        readme_path = self.fixture_root / "README.md"
        workflow_path = self.fixture_root / ".github/workflows/ci.yml"
        original_readme = readme_path.read_text(encoding="utf-8")
        original_workflow = workflow_path.read_text(encoding="utf-8")
        command_lines = (
            "data = yaml.safe_load(open(f))",
            "if not isinstance(data, dict):",
            "if errors:\n    sys.exit(1)",
            "print(f'All {len(glob.glob(\\\"schemas/*.yaml\\\"))} schema files valid')",
        )
        for command_line in command_lines:
            with self.subTest(readme_line=command_line):
                self.assertIn(command_line, original_readme)
                readme_path.write_text(
                    original_readme.replace(command_line, "removed", 1),
                    encoding="utf-8",
                )
                self.assert_contract_error(
                    "local multiline YAML command must exactly reproduce hosted CI"
                )
                readme_path.write_text(original_readme, encoding="utf-8")

        self.assertIn("data = yaml.safe_load(open(f))", original_workflow)
        workflow_path.write_text(
            original_workflow.replace(
                "data = yaml.safe_load(open(f))", "data = {}", 1
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("drifted from the canonical mapping check")

        readme_path.write_text(
            original_readme.replace(
                "data = yaml.safe_load(open(f))", "data = {}", 1
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("drifted from the canonical mapping check")
        self.assert_contract_error(
            "local multiline YAML command must exactly reproduce hosted CI"
        )
        readme_path.write_text(original_readme, encoding="utf-8")
        workflow_path.write_text(original_workflow, encoding="utf-8")

    def test_pins_hosted_contract_and_regression_steps(self) -> None:
        path = self.fixture_root / ".github/workflows/ci.yml"
        original = path.read_text(encoding="utf-8")
        steps = (
            (
                "Validate editorial contracts",
                "python3 scripts/validate_editorial_contracts.py",
            ),
            (
                "Run adversarial contract regressions",
                "python3 -m unittest discover -s tests -v",
            ),
        )
        blocks: list[str] = []
        for name, command in steps:
            block = f"      - name: {name}\n        run: {command}\n"
            blocks.append(block)
            self.assertIn(block, original)
            with self.subTest(name=name, mutation="deleted"):
                path.write_text(original.replace(block, "", 1), encoding="utf-8")
                self.assert_contract_error(
                    f"hosted CI step {name!r} must appear exactly once"
                )
            with self.subTest(name=name, mutation="bypassed"):
                path.write_text(
                    original.replace(command, f"{command} || true", 1),
                    encoding="utf-8",
                )
                self.assert_contract_error(f"hosted CI step {name!r} must run exactly")
            with self.subTest(name=name, mutation="duplicated"):
                path.write_text(
                    original.replace(block, f"{block}\n{block}", 1),
                    encoding="utf-8",
                )
                self.assert_contract_error(
                    f"hosted CI step {name!r} must appear exactly once"
                )
            with self.subTest(name=name, mutation="duplicate invocation"):
                duplicate_invocation = (
                    "      - name: Duplicate protected command\n"
                    f"        run: {command}\n"
                )
                path.write_text(
                    original.replace(
                        block,
                        f"{block}\n{duplicate_invocation}",
                        1,
                    ),
                    encoding="utf-8",
                )
                self.assert_contract_error(
                    f"hosted CI command {command!r} must be invoked exactly once"
                )
            path.write_text(original, encoding="utf-8")

        reordered = (
            original.replace(blocks[0], "__FIRST_HOSTED_STEP__\n", 1)
            .replace(blocks[1], blocks[0], 1)
            .replace("__FIRST_HOSTED_STEP__\n", blocks[1], 1)
        )
        path.write_text(reordered, encoding="utf-8")
        self.assert_contract_error("hosted contract checks must remain in canonical order")

    def test_pins_hosted_pull_request_trigger_and_step_inventory(self) -> None:
        path = self.fixture_root / ".github/workflows/ci.yml"
        original = path.read_text(encoding="utf-8")
        trigger = (
            "  pull_request:\n"
            "    branches: [ main, master, develop ]\n"
        )
        self.assertIn(trigger, original)
        trigger_mutations = (
            "",
            "  pull_request:\n    branches: [ develop ]\n",
            "  pull_request:\n    branches-ignore: [ main ]\n",
            "  pull_request:\n"
            "    branches: [ main, master, develop ]\n"
            "    paths: [ docs/** ]\n",
            "  pull_request:\n"
            "    branches: [ main, master, develop ]\n"
            "    paths-ignore: [ scripts/**, tests/** ]\n",
            "  pull_request:\n"
            "    branches: [ main, master, develop ]\n"
            "    types: [ opened ]\n",
        )
        for replacement in trigger_mutations:
            with self.subTest(trigger=replacement.strip() or "deleted"):
                path.write_text(
                    original.replace(trigger, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("workflow triggers must be exactly")
                path.write_text(original, encoding="utf-8")

        push_trigger = "  push:\n    branches: [ main, master, develop ]\n"
        self.assertIn(push_trigger, original)
        for replacement in (
            "",
            "  push:\n    branches: [ develop ]\n",
            "  push:\n"
            "    branches: [ main, master, develop ]\n"
            "    paths-ignore: [ scripts/**, tests/** ]\n",
        ):
            with self.subTest(push_trigger=replacement.strip() or "deleted"):
                path.write_text(
                    original.replace(push_trigger, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("workflow triggers must be exactly")
                path.write_text(original, encoding="utf-8")

        path.write_text(
            original.replace("  workflow_dispatch:\n", "", 1), encoding="utf-8"
        )
        self.assert_contract_error("workflow triggers must be exactly")

        step_names = (
            "Checkout code",
            "Set up Python",
            "Install dependencies",
            "Validate YAML schemas",
            "Validate editorial contracts",
            "Run adversarial contract regressions",
            "Validate structure",
            "Success",
        )
        for name in step_names:
            marker = f"      - name: {name}\n"
            self.assertIn(marker, original)
            with self.subTest(name=name, mutation="renamed"):
                path.write_text(
                    original.replace(marker, f"      - name: {name} renamed\n", 1),
                    encoding="utf-8",
                )
                self.assert_contract_error("step inventory/order mismatch")
                path.write_text(original, encoding="utf-8")

        success_block = (
            "      - name: Success\n"
            "        run: echo \"::notice::Editorial Standards CI passed\"\n"
        )
        self.assertIn(success_block, original)
        path.write_text(original.replace(success_block, "", 1), encoding="utf-8")
        self.assert_contract_error("step inventory/order mismatch")

        extra_step = (
            "      - name: Rewrite protected sources\n"
            "        run: git checkout origin/main -- scripts tests\n\n"
        )
        path.write_text(
            original.replace(success_block, f"{extra_step}{success_block}", 1),
            encoding="utf-8",
        )
        self.assert_contract_error("step inventory/order mismatch")

        path.write_text(
            original.replace(
                "  validate:\n    runs-on: ubuntu-latest\n",
                "  validate:\n"
                "    name: redirected-check\n"
                "    runs-on: ubuntu-latest\n",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("validate job mapping must contain exactly")

    def test_pins_hosted_workflow_trust_envelope_and_job_inventory(self) -> None:
        path = self.fixture_root / ".github/workflows/ci.yml"
        original = path.read_text(encoding="utf-8")
        permissions = "permissions:\n  contents: read\n"
        self.assertIn(permissions, original)
        mutations = (
            (permissions, ""),
            (permissions, "permissions: write-all\n"),
            (permissions, "permissions:\n  contents: write\n"),
            (
                permissions,
                "permissions:\n  contents: read\n  pull-requests: write\n",
            ),
            ("on:\n", "true:\n"),
            ("name: Editorial Standards CI", "name: Redirected check"),
            ("jobs:\n", "concurrency: bypass\njobs:\n"),
            (
                "jobs:\n  validate:\n",
                "jobs:\n  bypass:\n    runs-on: ubuntu-latest\n"
                "    steps: []\n  validate:\n",
            ),
        )
        for current, replacement in mutations:
            with self.subTest(replacement=replacement.strip() or "deleted"):
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                errors = validate(self.fixture_root)
                self.assertTrue(
                    any(
                        marker in error
                        for marker in (
                            "workflow mapping must contain exactly",
                            "source top-level keys/order must be exactly",
                            "workflow name must be exactly",
                            "workflow permissions must be exactly",
                            "job inventory must contain exactly",
                        )
                        for error in errors
                    ),
                    errors,
                )
                path.write_text(original, encoding="utf-8")

    def test_pins_every_hosted_step_mapping_and_preparation_action(self) -> None:
        path = self.fixture_root / ".github/workflows/ci.yml"
        original = path.read_text(encoding="utf-8")
        checkout = (
            "      - name: Checkout code\n"
            "        uses: actions/checkout@"
            "9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0\n"
        )
        setup = (
            "      - name: Set up Python\n"
            "        uses: actions/setup-python@"
            "5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0\n"
            "        with:\n"
            "          python-version: \"3.12\"\n"
        )
        install = (
            "      - name: Install dependencies\n"
            "        run: 'python3 -m pip install --require-hashes "
            "--only-binary=:all: -r requirements-ci.txt'\n"
        )
        mutations = (
            (
                checkout,
                checkout + "        with:\n          ref: main\n",
            ),
            (
                checkout,
                checkout + "        with:\n          path: trusted\n",
            ),
            (
                checkout,
                checkout + "        with:\n          fetch-depth: 0\n",
            ),
            (
                checkout,
                checkout.replace(
                    "9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0",
                    "v7",
                ),
            ),
            (
                setup,
                setup.replace('python-version: "3.12"', 'python-version: "3.13"'),
            ),
            (
                setup,
                setup + "          cache: pip\n",
            ),
            (
                install,
                install.replace("--require-hashes ", ""),
            ),
            (
                install,
                install.replace("-r requirements-ci.txt", "PyYAML"),
            ),
        )
        for current, replacement in mutations:
            with self.subTest(replacement=replacement):
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error(
                    "steps must match the exact canonical mappings"
                )
                path.write_text(original, encoding="utf-8")

    def test_requires_exact_hash_verified_ci_dependency_lock(self) -> None:
        lock_path = self.fixture_root / "requirements-ci.txt"
        original = lock_path.read_text(encoding="utf-8")
        self.assertIn("PyYAML==6.0.3", original)
        self.assertIn("--hash=sha256:", original)
        mutations = (
            original.replace("PyYAML==6.0.3", "PyYAML==6.0.2", 1),
            original.replace("    --hash=sha256:", "    # hash removed: ", 1),
            original + "requests==2.32.5\n",
        )
        for mutated in mutations:
            with self.subTest(mutation=mutated.splitlines()[-1]):
                lock_path.write_text(mutated, encoding="utf-8")
                self.assert_contract_error(
                    "dependency lock must exactly pin the canonical PyYAML artifacts"
                )
                lock_path.write_text(original, encoding="utf-8")

        lock_path.unlink()
        self.assert_contract_error("required contained regular CI dependency lock")

        lock_path.symlink_to("/etc/passwd")
        self.assert_contract_error("required contained regular CI dependency lock")

    def test_rejects_protected_hosted_ci_execution_controls(self) -> None:
        path = self.fixture_root / ".github/workflows/ci.yml"
        original = path.read_text(encoding="utf-8")
        protected_steps = (
            "Validate editorial contracts",
            "Run adversarial contract regressions",
        )
        step_controls = (
            "        if: ${{ false }}\n",
            "        continue-on-error: true\n",
            "        working-directory: bypass\n",
            "        shell: bash {0} || true\n",
            "        env:\n          PYTHONPATH: bypass\n",
            "        timeout-minutes: 1\n",
        )
        for name in protected_steps:
            marker = f"      - name: {name}\n"
            self.assertIn(marker, original)
            for control in step_controls:
                with self.subTest(name=name, control=control.strip()):
                    path.write_text(
                        original.replace(marker, f"{marker}{control}", 1),
                        encoding="utf-8",
                    )
                    self.assert_contract_error("must contain only canonical keys")
                    self.assert_contract_error("execution controls are forbidden")
                    path.write_text(original, encoding="utf-8")

        workflow_controls = (
            "env:\n  PYTHONPATH: bypass\n",
            "defaults:\n  run:\n    shell: bash {0} || true\n",
        )
        for control in workflow_controls:
            with self.subTest(scope="workflow", control=control.splitlines()[0]):
                path.write_text(
                    original.replace("jobs:\n", f"{control}\njobs:\n", 1),
                    encoding="utf-8",
                )
                self.assert_contract_error("workflow-level execution controls")
                path.write_text(original, encoding="utf-8")

        job_controls = (
            "    if: ${{ false }}\n",
            "    continue-on-error: true\n",
            "    defaults:\n      run:\n        working-directory: bypass\n",
            "    env:\n      PYTHONPATH: bypass\n",
            "    timeout-minutes: 1\n",
            "    strategy:\n      matrix:\n        os: [ubuntu-latest]\n",
        )
        job_marker = "  validate:\n"
        for control in job_controls:
            with self.subTest(scope="job", control=control.strip().splitlines()[0]):
                path.write_text(
                    original.replace(job_marker, f"{job_marker}{control}", 1),
                    encoding="utf-8",
                )
                self.assert_contract_error("validate job execution controls")
                path.write_text(original, encoding="utf-8")

        path.write_text(
            original.replace(
                "  validate:\n    runs-on: ubuntu-latest\n",
                "  validate:\n"
                "    strategy:\n"
                "      matrix:\n"
                "        os: [ubuntu-latest]\n"
                "    runs-on: ${{ matrix.os }}\n",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("validate job runner must be exactly")

        path.write_text(
            original.replace(
                "  validate:\n    runs-on: ubuntu-latest\n",
                "  validate:\n"
                "    strategy:\n"
                "      matrix:\n"
                "        command: [python3 scripts/validate_editorial_contracts.py]\n"
                "    runs-on: ubuntu-latest\n",
                1,
            ).replace(
                "run: python3 scripts/validate_editorial_contracts.py",
                "run: ${{ matrix.command }}",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("validate job execution controls")
        self.assert_contract_error("must run exactly")

    def test_rejects_fenced_reader_structure_and_canonical_link(self) -> None:
        path = self.fixture_root / "templates/audiences/general.md"
        original = path.read_text(encoding="utf-8")
        lines = original.splitlines()
        self.assertTrue(lines[0].startswith("# "))
        fenced = "\n".join((lines[0], "", "```markdown", *lines[1:], "```", ""))
        path.write_text(fenced, encoding="utf-8")

        errors = validate(self.fixture_root)
        self.assertTrue(any("missing required template marker" in error for error in errors))
        self.assertTrue(any("missing canonical project link" in error for error in errors))

    def test_rejects_backticks_in_backtick_fence_info_strings(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        opening = "```bash\n"
        self.assertIn(opening, original)
        path.write_text(
            original.replace(opening, "```bash `not-commonmark`\n", 1),
            encoding="utf-8",
        )
        self.assert_contract_error(
            "Development bash recipe must match the exact canonical executable blocks"
        )

    def test_rejects_html_commented_reader_structure_and_canonical_link(self) -> None:
        path = self.fixture_root / "templates/audiences/general.md"
        original = path.read_text(encoding="utf-8")
        lines = original.splitlines()
        self.assertTrue(lines[0].startswith("# "))
        commented = "\n".join((lines[0], "", "<!--", *lines[1:], "-->", ""))
        path.write_text(commented, encoding="utf-8")

        errors = validate(self.fixture_root)
        self.assertTrue(any("missing required template marker" in error for error in errors))
        self.assertTrue(any("missing canonical project link" in error for error in errors))

    def test_ignores_html_comment_tokens_inside_fenced_code(self) -> None:
        paths = (
            self.fixture_root / "README.md",
            self.fixture_root / "docs/reader-mode-documentation.md",
            self.fixture_root / "templates/audiences/general.md",
        )
        for path in paths:
            original = path.read_text(encoding="utf-8")
            for opening, closing in (("```html", "```"), ("~~~html", "~~~")):
                with self.subTest(path=path.name, opening=opening):
                    path.write_text(
                        original
                        + f"\n{opening}\n<!-- unmatched example token\n{closing}\n",
                        encoding="utf-8",
                    )
                    self.assertEqual([], validate(self.fixture_root))
            path.write_text(
                original + "\nInline code preserves `<!-- unmatched example token`.\n",
                encoding="utf-8",
            )
            self.assertEqual([], validate(self.fixture_root))
            path.write_text(original, encoding="utf-8")

    def test_escaped_backtick_cannot_hide_an_html_comment_opener(self) -> None:
        path = self.fixture_root / "templates/audiences/general.md"
        original = path.read_text(encoding="utf-8")
        lines = original.splitlines()
        self.assertTrue(lines[0].startswith("# "))
        hidden = "\n".join(
            (
                lines[0],
                "",
                r"\`<!--`",
                *lines[1:],
                "-->",
                "",
            )
        )
        path.write_text(hidden, encoding="utf-8")

        errors = validate(self.fixture_root)
        self.assertTrue(any("missing required template marker" in e for e in errors))
        self.assertTrue(any("missing canonical project link" in e for e in errors))

    def test_multiline_inline_code_cannot_supply_reader_contract_markers(self) -> None:
        path = self.fixture_root / "templates/repository-readme-v2.md"
        original = path.read_text(encoding="utf-8")
        hero = (
            "[View the project] · [See a demonstration] · [Technical documentation] ·\n"
            "[Humanities interpretation] · [Business applications] · [Evidence]"
        )
        self.assertIn(hero, original)
        for delimiter, embedded in (("`", ""), ("``", "`\n")):
            with self.subTest(delimiter=delimiter):
                path.write_text(
                    original.replace(
                        hero,
                        f"{delimiter}\n{embedded}{hero}\n{delimiter}",
                        1,
                    ),
                    encoding="utf-8",
                )
                self.assert_contract_error("missing required template marker")

        path.write_text(
            original + "\n`\n<!-- remains literal inside multiline code\n`\n",
            encoding="utf-8",
        )
        self.assertEqual([], validate(self.fixture_root))

        path.write_text(original + "\n`\nunclosed span\n", encoding="utf-8")
        self.assert_contract_error("unclosed Markdown inline-code span")

    def test_block_html_comment_suffix_cannot_supply_markdown_contracts(self) -> None:
        mutations = (
            (
                "templates/audiences/general.md",
                "## What is this?",
                "<!-- hidden -->## What is this?",
                "missing required template marker",
            ),
            (
                "templates/repository-readme-v2.md",
                "| **What it is** | [Canonical definition] |",
                "<!-- hidden -->| **What it is** | [Canonical definition] |",
                "has no data rows",
            ),
            (
                "templates/audiences/general.md",
                "- [Canonical README](../../README.md)",
                "<!-- hidden -->- [Canonical README](../../README.md)",
                "missing canonical project link",
            ),
            (
                "templates/audiences/general.md",
                "## What is this?",
                "<!-- hidden\n-->## What is this?",
                "missing required template marker",
            ),
        )
        for relative_path, current, replacement, expected in mutations:
            with self.subTest(path=relative_path, replacement=replacement):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error(expected)
                path.write_text(original, encoding="utf-8")

        path = self.fixture_root / "templates/audiences/general.md"
        original = path.read_text(encoding="utf-8")
        path.write_text(
            original + "\nOrdinary prose <!-- explanatory note --> remains prose.\n",
            encoding="utf-8",
        )
        self.assertEqual([], validate(self.fixture_root))

    def test_backtick_run_search_does_not_slice_rejected_suffixes(self) -> None:
        class NoSliceString(str):
            def __getitem__(self, key: object) -> str:
                if isinstance(key, slice):
                    raise AssertionError("backtick search sliced an input suffix")
                return super().__getitem__(key)

        adversarial = NoSliceString("`` " * 100_000)
        self.assertEqual(-1, _find_backtick_run(adversarial, 0, 1))

    def test_many_inline_code_spans_do_not_rescan_for_absent_comments(self) -> None:
        class CommentScanCountingString(str):
            comment_search_suffix = 0

            def find(
                self,
                sub: str,
                start: int = 0,
                end: int | None = None,
            ) -> int:
                if sub == "<!--":
                    effective_end = len(self) if end is None else end
                    self.comment_search_suffix += effective_end - start
                if end is None:
                    return super().find(sub, start)
                return super().find(sub, start, end)

        adversarial = CommentScanCountingString("`x`a" * 50_000)
        rendered, in_comment, inline_length = _strip_html_comments_from_line(
            adversarial,
            False,
            0,
        )
        self.assertEqual(adversarial, rendered)
        self.assertFalse(in_comment)
        self.assertEqual(0, inline_length)
        self.assertEqual(0, adversarial.comment_search_suffix)

    def test_many_inline_triple_backticks_do_not_slice_growing_prefixes(self) -> None:
        class NoGrowingPrefixSliceString(str):
            def __getitem__(self, key: object) -> str:
                if (
                    isinstance(key, slice)
                    and key.start is None
                    and isinstance(key.stop, int)
                    and key.stop > 3
                ):
                    raise AssertionError("Markdown scan sliced a growing prefix")
                return super().__getitem__(key)

        adversarial = NoGrowingPrefixSliceString("a```x```" * 50_000)
        rendered, in_comment, inline_length = _strip_html_comments_from_line(
            adversarial,
            False,
            0,
        )
        self.assertEqual(adversarial, rendered)
        self.assertFalse(in_comment)
        self.assertEqual(0, inline_length)

    def test_multiline_inline_code_suffix_cannot_supply_block_structure(self) -> None:
        mutations = (
            (
                "templates/audiences/general.md",
                "## What is this?",
                "`\n`## What is this?",
                "missing required template marker",
            ),
            (
                "templates/repository-readme-v2.md",
                "| I am reading as… | Start here |",
                "`\n`| I am reading as… | Start here |",
                "missing required template marker",
            ),
            (
                "docs/reader-mode-documentation.md",
                "1. project name;",
                "`\n`1. project name;",
                "root README sequence mismatch",
            ),
        )
        for relative_path, current, replacement, expected_error in mutations:
            with self.subTest(path=relative_path):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error(expected_error)

    def test_rejects_reader_contracts_hidden_in_raw_html_blocks(self) -> None:
        path = self.fixture_root / "templates/audiences/general.md"
        original = path.read_text(encoding="utf-8")
        lines = original.splitlines()
        self.assertTrue(lines[0].startswith("# "))
        literal_blocks = (
            ('<script type="text/plain">', "</script>"),
            ("<style>", "</style>"),
            ("<pre>", "</pre>"),
            ("<textarea>", "</textarea>"),
        )
        for opening, closing in literal_blocks:
            with self.subTest(opening=opening):
                hidden = "\n".join((lines[0], "", opening, *lines[1:], closing, ""))
                path.write_text(hidden, encoding="utf-8")
                errors = validate(self.fixture_root)
                self.assertTrue(
                    any("missing required template marker" in error for error in errors)
                )
                self.assertTrue(
                    any("missing canonical project link" in error for error in errors)
                )

        visible_contract = [line for line in lines[1:] if line.strip()]
        generic_blocks = (
            ("<div>", "</div>"),
            ("<x-hidden>", "</x-hidden>"),
            ('<x-hidden data=">">', "</x-hidden>"),
            ("<x-hidden data='<'>", "</x-hidden>"),
            ('<x-hidden data = ">" disabled>', "</x-hidden>"),
        )
        for opening, closing in generic_blocks:
            with self.subTest(opening=opening):
                hidden = "\n".join(
                    (lines[0], "", opening, *visible_contract, closing, "")
                )
                path.write_text(hidden, encoding="utf-8")
                self.assert_contract_error("missing required template marker")
        path.write_text(original, encoding="utf-8")

    def test_rejects_tag_governance_drift(self) -> None:
        path = self.fixture_root / "schemas/tag-governance.yaml"
        original = path.read_text(encoding="utf-8")
        mutations = (
            ("max_per_essay: 8", "max_per_essay: 9"),
            ("min_per_essay: 2", "min_per_essay: 1"),
            (
                'pattern: "^[a-z0-9]+(-[a-z0-9]+)*$"',
                'pattern: "^[A-Za-z0-9-]+$"',
            ),
            (
                "format: \"lowercase, hyphenated (e.g. 'building-in-public', not 'Building In Public')\"",
                'format: "free-form tags"',
            ),
        )
        for current, replacement in mutations:
            with self.subTest(replacement=replacement):
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("tag governance/frontmatter mismatch")
                path.write_text(original, encoding="utf-8")

    def test_rejects_category_taxonomy_drift(self) -> None:
        path = self.fixture_root / "schemas/category-taxonomy.yaml"
        original = path.read_text(encoding="utf-8")
        self.assertIn("  guide:\n", original)
        path.write_text(
            original.replace("  guide:\n", "  tutorial:\n", 1), encoding="utf-8"
        )

        self.assert_contract_error("category taxonomy/frontmatter/template mismatch")
        path.write_text(original, encoding="utf-8")

        readme_path = self.fixture_root / "README.md"
        readme = readme_path.read_text(encoding="utf-8")
        readme_path.write_text(
            readme.replace("### Guide", "### Tutorial", 1), encoding="utf-8"
        )
        self.assert_contract_error("missing required template marker")

    def test_rejects_missing_or_hidden_publication_template_bodies(self) -> None:
        publication_templates = (
            "case-study.md",
            "guide.md",
            "log.md",
            "meta-system.md",
            "methodology.md",
            "retrospective.md",
        )
        for filename in publication_templates:
            with self.subTest(filename=filename, mutation="missing"):
                path = self.fixture_root / "templates" / filename
                original = path.read_text(encoding="utf-8")
                parts = original.split("---", 2)
                self.assertEqual(3, len(parts))
                path.write_text(f"---{parts[1]}---\n", encoding="utf-8")
                self.assert_contract_error("missing required template marker")
                path.write_text(original, encoding="utf-8")

        guide_path = self.fixture_root / "templates/guide.md"
        guide = guide_path.read_text(encoding="utf-8")
        parts = guide.split("---", 2)
        for opening, closing in (("```markdown", "```"), ("<!--", "-->")):
            with self.subTest(template="guide.md", opening=opening):
                guide_path.write_text(
                    f"---{parts[1]}---\n{opening}\n{parts[2]}\n{closing}\n",
                    encoding="utf-8",
                )
                self.assert_contract_error("missing required template marker")
        guide_path.write_text(guide, encoding="utf-8")

    def test_requires_standalone_publication_frontmatter_delimiters(self) -> None:
        publication_templates = (
            "case-study.md",
            "guide.md",
            "log.md",
            "meta-system.md",
            "methodology.md",
            "retrospective.md",
        )
        for filename in publication_templates:
            path = self.fixture_root / "templates" / filename
            original = path.read_text(encoding="utf-8")
            with self.subTest(filename=filename, delimiter="closing"):
                self.assertIn("references: []\n---\n", original)
                path.write_text(
                    original.replace("references: []\n---\n", "references: []---\n", 1),
                    encoding="utf-8",
                )
                self.assert_contract_error("requires standalone '---' delimiters")
            with self.subTest(filename=filename, delimiter="opening"):
                path.write_text(original.replace("---\n", "--- \n", 1), encoding="utf-8")
                self.assert_contract_error("requires standalone '---' delimiters")
            path.write_text(original, encoding="utf-8")

    def test_rejects_duplicate_publication_frontmatter_keys(self) -> None:
        publication_templates = (
            "case-study.md",
            "guide.md",
            "log.md",
            "meta-system.md",
            "methodology.md",
            "retrospective.md",
        )
        for filename in publication_templates:
            with self.subTest(filename=filename):
                path = self.fixture_root / "templates" / filename
                original = path.read_text(encoding="utf-8")
                title_line = next(
                    line for line in original.splitlines() if line.startswith("title:")
                )
                path.write_text(
                    original.replace(
                        f"{title_line}\n",
                        f"{title_line}\ntitle: duplicate key must fail\n",
                        1,
                    ),
                    encoding="utf-8",
                )
                self.assert_contract_error("found duplicate key 'title'")

        schema_path = self.fixture_root / "schemas/log-schema.yaml"
        schema = schema_path.read_text(encoding="utf-8")
        schema_path.write_text(
            schema.replace(
                'schema_version: "1.0"\n',
                'schema_version: "1.0"\nschema_version: "2.0"\n',
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("found duplicate key 'schema_version'")

    def test_rejects_incomplete_reader_rubric_contract(self) -> None:
        path = self.fixture_root / "schemas/reader-mode-rubric.yaml"
        original = path.read_text(encoding="utf-8")
        mutations = (
            ("  maximum: 4", "  maximum: 5", "expected scoring scale"),
            (
                "dimensions:\n  orientation:",
                "dimensions: {}\nremoved_dimensions:\n  orientation:",
                "dimension set mismatch",
            ),
            (
                '      4: "The first screen also routes distinct audiences without blocking the canonical depth."',
                "",
                "anchor set mismatch",
            ),
            (
                '      0: "No usable root README."',
                '      0: ""',
                "has empty anchors",
            ),
        )
        for current, replacement, expected_error in mutations:
            with self.subTest(replacement=replacement):
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error(expected_error)
                path.write_text(original, encoding="utf-8")

    def test_rejects_boolean_reader_and_quality_rubric_anchor_keys(self) -> None:
        mutations = (
            (
                "schemas/reader-mode-rubric.yaml",
                "  minimum: 0",
                "  minimum: false",
                "expected scoring scale",
            ),
            (
                "schemas/reader-mode-rubric.yaml",
                '      0: "No usable root README."',
                '      false: "No usable root README."',
                "anchor keys must be integers",
            ),
            (
                "schemas/quality-rubric.yaml",
                '      0: "No comprehensible argument or usable structure."',
                '      false: "No comprehensible argument or usable structure."',
                "scoring anchor keys must be integers",
            ),
        )
        for relative_path, current, replacement, expected_error in mutations:
            with self.subTest(path=relative_path):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error(expected_error)
                path.write_text(original, encoding="utf-8")

    def test_rejects_nonstring_taxonomy_and_rubric_dimension_keys(self) -> None:
        mutations = (
            (
                "schemas/category-taxonomy.yaml",
                "categories:\n",
                "categories:\n  7:\n    description: Invalid category.\n",
                "categories: keys must be nonempty strings",
            ),
            (
                "schemas/reader-mode-rubric.yaml",
                "dimensions:\n",
                "dimensions:\n  7:\n    question: Invalid dimension.\n",
                "dimensions: keys must be nonempty strings",
            ),
            (
                "schemas/quality-rubric.yaml",
                "dimensions:\n",
                "dimensions:\n  7:\n    max_points: 0\n",
                "dimensions: keys must be nonempty strings",
            ),
        )
        for relative_path, anchor, replacement, expected_error in mutations:
            with self.subTest(path=relative_path):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertIn(anchor, original)
                path.write_text(
                    original.replace(anchor, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error(expected_error)
                path.write_text(original, encoding="utf-8")

    def test_rejects_incomplete_or_hidden_reader_mode_standard(self) -> None:
        path = self.fixture_root / "docs/reader-mode-documentation.md"
        original = path.read_text(encoding="utf-8")
        path.write_text("# Reader-mode repository documentation\n", encoding="utf-8")
        self.assert_contract_error("missing required template marker")

        lines = original.splitlines()
        path.write_text(
            "\n".join((lines[0], "", "<!--", *lines[1:], "-->", "")),
            encoding="utf-8",
        )
        self.assert_contract_error("missing required template marker")

        path.write_text(
            original.replace(
                "technical\ndepth, conceptual depth",
                "technical\ndepth and conceptual depth",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("reader rubric dimension sentence is missing or stale")

        rubric_link = (
            "[`schemas/reader-mode-rubric.yaml`](../schemas/reader-mode-rubric.yaml)"
        )
        self.assertIn(rubric_link, original)
        path.write_text(
            original.replace(rubric_link, f"`{rubric_link}`", 1),
            encoding="utf-8",
        )
        self.assert_contract_error("canonical reader rubric link")

    def test_binds_no_silent_claim_drift_policies(self) -> None:
        mutations = (
            (
                "docs/reader-mode-documentation.md",
                "They may not silently change those facts.",
                "They may silently change those facts.",
            ),
            (
                "templates/evidence.md",
                "may not change an\nassertion's statement",
                "may change an\nassertion's statement",
            ),
        )
        for relative_path, current, inverted in mutations:
            path = self.fixture_root / relative_path
            original = path.read_text(encoding="utf-8")
            self.assertIn(current, original)
            for replacement in ("", inverted, f"<!--\n{current}\n-->"):
                with self.subTest(path=relative_path, replacement=replacement):
                    path.write_text(
                        original.replace(current, replacement, 1), encoding="utf-8"
                    )
                    self.assert_contract_error("canonical claim-boundary policy")
                    path.write_text(original, encoding="utf-8")

        moved_policies = (
            (
                "docs/reader-mode-documentation.md",
                "Audience pages may change order, terminology, examples, assumed "
                "knowledge, and\nthe evidence they foreground. They may not silently "
                "change those facts.",
                "Audience pages may change order, terminology, examples, assumed "
                "knowledge, and\nthe evidence they foreground. They may silently "
                "change those facts.",
            ),
            (
                "templates/evidence.md",
                "Audience pages may foreground different rows but may not change an\n"
                "assertion's statement, class, verification state, freshness, or evidence.",
                "Audience pages may foreground different rows and may change an\n"
                "assertion's statement, class, verification state, freshness, or evidence.",
            ),
        )
        for relative_path, canonical, inverted in moved_policies:
            with self.subTest(path=relative_path, mutation="moved-decoy"):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertIn(canonical, original)
                path.write_text(
                    original.replace(canonical, inverted, 1)
                    + f"\n## Unrelated decoy\n\n{canonical}\n",
                    encoding="utf-8",
                )
                self.assert_contract_error("canonical claim-boundary policy")
                path.write_text(original, encoding="utf-8")

                path.write_text(
                    original.replace(canonical, inverted, 1)
                    + f"\n`{canonical.replace(chr(10), ' ')}`\n",
                    encoding="utf-8",
                )
                self.assert_contract_error("canonical claim-boundary policy")
                path.write_text(original, encoding="utf-8")

        additive_inversions = (
            (
                "docs/reader-mode-documentation.md",
                "They may not silently change those facts.",
                "Audience pages may silently change those facts.",
            ),
            (
                "templates/evidence.md",
                "assertion's statement, class, verification state, freshness, or evidence.",
                "Audience pages may change an assertion's statement, class, "
                "verification state, freshness, or evidence.",
            ),
        )
        for relative_path, anchor, contradiction in additive_inversions:
            with self.subTest(path=relative_path, mutation="additive-contradiction"):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertIn(anchor, original)
                path.write_text(
                    original.replace(anchor, f"{anchor} {contradiction}", 1),
                    encoding="utf-8",
                )
                self.assert_contract_error("contradictory claim-boundary policy")

    def test_pins_normative_schema_links_to_the_reviewed_merge(self) -> None:
        mutations = (
            (
                "README.md",
                "schemas/project-record-v1.schema.json",
                "schemas/does-not-exist.schema.json",
            ),
            (
                "docs/reader-mode-documentation.md",
                "schemas/assertion-evidence.v1.schema.json",
                "schemas/does-not-exist.schema.json",
            ),
            (
                "docs/reader-mode-documentation.md",
                "github.com/organvm-iv-taxis/schema-definitions",
                "github.com/meta-organvm/schema-definitions",
            ),
            (
                "README.md",
                "blob/2c2b7c8b0e841a4abde82230be88524d43f9b3c2/",
                "blob/main/",
            ),
        )
        for relative_path, current, replacement in mutations:
            with self.subTest(path=relative_path, replacement=replacement):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("canonical schema URL inventory mismatch")
                path.write_text(original, encoding="utf-8")

        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        canonical_url = (
            "https://github.com/organvm-iv-taxis/schema-definitions/blob/"
            "2c2b7c8b0e841a4abde82230be88524d43f9b3c2/"
            "schemas/project-record-v1.schema.json"
        )
        canonical_link = f"[project-record schema]({canonical_url})"
        self.assertIn(canonical_link, original)
        path.write_text(
            original.replace(
                canonical_link,
                "[project-record schema](https://evil.example/redirect)",
                1,
            )
            + f"\nCanonical-looking plain-text decoy: {canonical_url}\n",
            encoding="utf-8",
        )
        self.assert_contract_error("canonical schema link must appear exactly once")

        for decoy in (
            f"`{canonical_link}`",
            f"!{canonical_link}",
            f"\\{canonical_link}",
            f'<span data-link="{canonical_link}">decoy</span>',
            f'<span title="> {canonical_link}">decoy</span>',
            f'[outer](https://example.com "{canonical_link}")',
            f"![prefix {canonical_link} suffix](image.png)",
        ):
            with self.subTest(decoy=decoy[:20]):
                path.write_text(
                    original.replace(
                        canonical_link,
                        "[project-record schema](https://evil.example/redirect)",
                        1,
                    )
                    + f"\n{decoy}\n",
                    encoding="utf-8",
                )
                self.assert_contract_error(
                    "canonical schema link must appear exactly once"
                )

    def test_rejects_incomplete_quality_rubric_contract(self) -> None:
        path = self.fixture_root / "schemas/quality-rubric.yaml"
        original = path.read_text(encoding="utf-8")
        mutations = (
            ("total_points: 100", "total_points: 99", "total_points must be 100"),
            (
                "  clarity:\n",
                "  substance:\n",
                "dimension set mismatch",
            ),
            ("    max_points: 20", "    max_points: 19", "max_points must be 20"),
            (
                '      0: "No comprehensible argument or usable structure."',
                "",
                "scoring anchors mismatch",
            ),
            (
                "  flagship_candidate: 80",
                "  flagship_candidate: 81",
                "thresholds mismatch",
            ),
        )
        for current, replacement, expected_error in mutations:
            with self.subTest(replacement=replacement):
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error(expected_error)
                path.write_text(original, encoding="utf-8")

    def test_rejects_quality_rubric_readme_heading_drift(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        heading = "### Insight Density (20 points)"
        self.assertIn(heading, original)
        path.write_text(
            original.replace(heading, "### Substance (20 points)", 1),
            encoding="utf-8",
        )

        self.assert_contract_error("missing required template marker")

    def test_binds_every_readme_quality_band_to_the_quality_schema(self) -> None:
        path = self.fixture_root / "README.md"
        original = path.read_text(encoding="utf-8")
        clarity_bands = (
            "- **16-20:** Clear, well-organized, with minimal jargon or jargon "
            "well-defined.\n"
            "- **11-15:** Generally clear with occasional dense passages.\n"
            "- **6-10:** Requires significant effort to follow; restructuring is "
            "needed.\n"
            "- **1-5:** Unclear and in need of a major rewrite.\n"
            "- **0:** No comprehensible argument or usable structure."
        )
        self.assertIn(clarity_bands, original)
        mutations = (
            (clarity_bands, ""),
            ("- **16-20:**", "- **17-20:**"),
            (
                "Clear, well-organized, with minimal jargon or jargon well-defined.",
                "Looks polished.",
            ),
            (
                "- **0:** No comprehensible argument or usable structure.",
                "",
            ),
        )
        for current, replacement in mutations:
            with self.subTest(replacement=replacement):
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("quality rubric bands for 'clarity'")
                path.write_text(original, encoding="utf-8")

        schema_path = self.fixture_root / "schemas/quality-rubric.yaml"
        schema = schema_path.read_text(encoding="utf-8")
        schema_path.write_text(
            schema.replace(
                "Generally clear with occasional dense passages.",
                "Clear enough after one revision.",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("quality rubric bands for 'clarity'")

    def test_reports_malformed_related_repository_pattern(self) -> None:
        path = self.fixture_root / "schemas/frontmatter-schema.yaml"
        original = path.read_text(encoding="utf-8")
        self.assertIn("    item_pattern: >-\n", original)
        path.write_text(
            original.replace(
                "    item_pattern: >-\n      ^(?:organvm|",
                "    item_pattern: '[unterminated'\n    ignored_pattern: >-\n      ^(?:organvm|",
                1,
            ),
            encoding="utf-8",
        )

        self.assert_contract_error("invalid related_repos item_pattern")

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

    def test_reports_scalar_enums_without_crashing_value_validation(self) -> None:
        mutations = (
            (
                "schemas/frontmatter-schema.yaml",
                "    enum: [essay]\n",
                "    enum: 7\n",
            ),
            (
                "schemas/log-schema.yaml",
                "    enum: [focused, exploratory, reflective, frustrated, "
                "breakthrough, routine]\n",
                "    enum: 7\n",
            ),
        )
        for relative_path, current, replacement in mutations:
            with self.subTest(path=relative_path):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("enum must be a nonempty list")
                path.write_text(original, encoding="utf-8")

    def test_applies_log_integer_maximum_and_handles_invalid_bounds(self) -> None:
        schema_path = self.fixture_root / "schemas/log-schema.yaml"
        template_path = self.fixture_root / "templates/log.md"
        original_schema = schema_path.read_text(encoding="utf-8")
        original_template = template_path.read_text(encoding="utf-8")
        commits_rule = "      commits:\n        type: integer\n        min: 0\n"
        activity = (
            "activity:\n"
            '  since: "2026-09-01"\n'
            "  commits: 1\n"
            "  repos_active: 0\n"
            "  files_changed: 0\n"
        )
        self.assertIn(commits_rule, original_schema)
        self.assertIn("mood: focused\n", original_template)
        template_path.write_text(
            original_template.replace(
                "mood: focused\n",
                "mood: focused\n" + activity,
                1,
            ),
            encoding="utf-8",
        )

        schema_path.write_text(
            original_schema.replace(
                commits_rule,
                commits_rule + "        max: 0\n",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("field 'activity.commits' is above")

        schema_path.write_text(
            original_schema.replace(
                commits_rule,
                commits_rule + "        max: invalid\n",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("max must be a nonnegative integer")

    def test_validates_every_log_schema_rule_without_template_usage(self) -> None:
        path = self.fixture_root / "schemas/log-schema.yaml"
        original = path.read_text(encoding="utf-8")
        mutations = (
            (
                "        min: 0\n",
                "        min: invalid\n",
                "min must be a nonnegative integer",
            ),
            (
                "  links:\n    type: list\n    item_type: string\n",
                "  links:\n    type: list\n    item_type: boolean\n",
                "declare unsupported item_type 'boolean'",
            ),
            (
                "  references:\n    type: list\n",
                "  references:\n    type: list\n    min_length: 1\n",
                "contain unsupported keys for 'list'",
            ),
        )
        for current, replacement, expected_error in mutations:
            with self.subTest(replacement=replacement):
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error(expected_error)
                path.write_text(original, encoding="utf-8")

        path.write_text(
            original.replace(
                "optional_fields:\n",
                "optional_fields:\n  title:\n    type: string\n"
                "    description: duplicate scope\n",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("fields cannot be both required and optional")

    def test_rejects_any_audience_template_without_canonical_project_link(self) -> None:
        link = "[Canonical README](../../README.md)"
        audience_templates = (
            "business.md",
            "evaluator.md",
            "general.md",
            "humanities.md",
            "technical.md",
        )
        for filename in audience_templates:
            with self.subTest(filename=filename):
                path = self.fixture_root / "templates/audiences" / filename
                content = path.read_text(encoding="utf-8")
                self.assertIn(link, content)
                path.write_text(
                    content.replace(f"- {link}\n", "", 1), encoding="utf-8"
                )
                self.assert_contract_error(
                    f"templates/audiences/{filename}: missing canonical project link"
                )
                path.write_text(content, encoding="utf-8")

    def test_rejects_missing_reader_template_structure(self) -> None:
        required_markers = {
            "templates/repository-readme-v2.md": "| I am reading as… | Start here |",
            "templates/evidence.md": "## Project limitations",
            "templates/audiences/business.md": "## Current deployment status",
            "templates/audiences/evaluator.md": "## Evidence for each material claim",
            "templates/audiences/general.md": "## What exists now",
            "templates/audiences/humanities.md": "## Ethical tensions",
            "templates/audiences/technical.md": "## Tests and verification",
        }
        for relative_path, marker in required_markers.items():
            with self.subTest(path=relative_path):
                path = self.fixture_root / relative_path
                content = path.read_text(encoding="utf-8")
                self.assertIn(marker, content)
                path.write_text(
                    content.replace(marker, f"Removed {marker}", 1),
                    encoding="utf-8",
                )
                self.assert_contract_error(
                    f"{relative_path}: missing required template marker {marker!r}"
                )
                path.write_text(content, encoding="utf-8")

    def test_rejects_malformed_required_reader_table_delimiters(self) -> None:
        required_tables = (
            (
                "templates/repository-readme-v2.md",
                "| I am reading as… | Start here |",
            ),
            ("templates/repository-readme-v2.md", "| | |"),
            (
                "templates/evidence.md",
                "| ID | Claim | Claim posture | Assertion class | "
                "Verification state | Evidence | Freshness |",
            ),
            ("templates/evidence.md", "| ID | Limitation | Related assertion |"),
        )
        for relative_path, header in required_tables:
            for replacement in ("", "| not-a-delimiter |"):
                with self.subTest(
                    path=relative_path,
                    header=header,
                    replacement=replacement,
                ):
                    path = self.fixture_root / relative_path
                    original = path.read_text(encoding="utf-8")
                    lines = original.splitlines()
                    header_index = lines.index(header)
                    self.assertTrue(lines[header_index + 1].startswith("|---"))
                    lines[header_index + 1] = replacement
                    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

                    self.assert_contract_error("has an invalid delimiter")
                    path.write_text(original, encoding="utf-8")

    def test_rejects_required_reader_table_rows_with_wrong_column_count(self) -> None:
        required_tables = (
            (
                "templates/repository-readme-v2.md",
                "| I am reading as… | Start here |",
            ),
            ("templates/repository-readme-v2.md", "| | |"),
            (
                "templates/evidence.md",
                "| ID | Claim | Claim posture | Assertion class | "
                "Verification state | Evidence | Freshness |",
            ),
            ("templates/evidence.md", "| ID | Limitation | Related assertion |"),
        )
        for relative_path, header in required_tables:
            with self.subTest(path=relative_path, header=header):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                lines = original.splitlines()
                header_index = lines.index(header)
                row_index = header_index + 2
                cells = lines[row_index].strip()[1:-1].split("|")
                self.assertGreater(len(cells), 1)
                lines[row_index] = "|" + "|".join(cells[:-1]) + "|"
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")

                self.assert_contract_error("columns; expected")
                path.write_text(original, encoding="utf-8")

    def test_rejects_reordered_reader_template_markers(self) -> None:
        reordered_markers = {
            "templates/repository-readme-v2.md": (
                "## What am I looking at?",
                "## Canonical project documentation",
            ),
            "templates/evidence.md": (
                "## Assertion evidence",
                "## Project limitations",
            ),
            "templates/audiences/business.md": (
                "## Existing operational problem",
                "## Technical appendix and evidence",
            ),
            "templates/audiences/evaluator.md": (
                "## Initial condition",
                "## Inspection map",
            ),
            "templates/audiences/general.md": (
                "## What is this?",
                "## Where to go next",
            ),
            "templates/audiences/humanities.md": (
                "## Central question",
                "## Further reading and evidence",
            ),
            "templates/audiences/technical.md": (
                "## Implementation status",
                "## Inspection paths",
            ),
        }
        for relative_path, (first, last) in reordered_markers.items():
            with self.subTest(path=relative_path):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                lines = original.splitlines()
                first_index = lines.index(first)
                last_index = lines.index(last)
                lines[first_index], lines[last_index] = lines[last_index], lines[first_index]
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")

                self.assert_contract_error("required template markers are out of order")
                path.write_text(original, encoding="utf-8")

    def test_rejects_duplicate_reader_template_marker(self) -> None:
        path = self.fixture_root / "templates/audiences/general.md"
        content = path.read_text(encoding="utf-8")
        marker = "## What is this?"
        self.assertEqual(1, content.splitlines().count(marker))
        path.write_text(content + f"\n{marker}\n", encoding="utf-8")

        self.assert_contract_error("duplicate required template marker")

    def test_rejects_scalar_instead_of_essay_list(self) -> None:
        path = self.fixture_root / "templates/guide.md"
        content = path.read_text(encoding="utf-8")
        self.assertIn("tags: [guide]", content)
        path.write_text(
            content.replace("tags: [guide]", "tags: guide", 1), encoding="utf-8"
        )

        self.assert_contract_error("field 'tags' must have type 'list'")

    def test_rejects_string_instead_of_essay_integer(self) -> None:
        path = self.fixture_root / "templates/guide.md"
        content = path.read_text(encoding="utf-8")
        self.assertIn("word_count: 0", content)
        path.write_text(
            content.replace("word_count: 0", 'word_count: "0"', 1),
            encoding="utf-8",
        )

        self.assert_contract_error("field 'word_count' must have type 'integer'")

    def test_validates_populated_publication_scalar_constraints(self) -> None:
        path = self.fixture_root / "templates/guide.md"
        original = path.read_text(encoding="utf-8")
        mutations = (
            (
                'author: "@4444J99"',
                'author: "4444J99"',
                "does not match the schema pattern",
            ),
            (
                'author: "@4444J99"',
                'author: ""',
                "does not match the schema pattern",
            ),
            (
                'date: "YYYY-MM-DD"',
                'date: "September 1"',
                "does not match the schema pattern",
            ),
            (
                'date: "YYYY-MM-DD"',
                'date: ""',
                "does not match the schema pattern",
            ),
            ('title: ""', 'title: "short"', "is shorter than allowed"),
            ('excerpt: ""', 'excerpt: "short"', "is shorter than allowed"),
            (
                'portfolio_relevance: ""',
                'portfolio_relevance: "LOW"',
                "outside the schema enum",
            ),
            (
                'reading_time: ""',
                'reading_time: "soon"',
                "does not match the schema pattern",
            ),
            ("word_count: 0", "word_count: 1", "below the schema minimum"),
        )
        for current, replacement, expected_error in mutations:
            with self.subTest(field=current.split(":", 1)[0], value=replacement):
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error(expected_error)
                path.write_text(original, encoding="utf-8")

    def test_enforces_publication_list_bounds_with_exact_seed_placeholders(
        self,
    ) -> None:
        mutations = (
            (
                "templates/guide.md",
                "tags: [guide]",
                "tags: [one, two, three, four, five, six, seven, eight, nine]",
                "field 'tags' has too many items",
            ),
            (
                "templates/guide.md",
                "tags: [guide]",
                "tags: [different]",
                "field 'tags' has too few items",
            ),
            (
                "templates/case-study.md",
                "tags: []",
                "tags: [different]",
                "field 'tags' has too few items",
            ),
        )
        for relative_path, current, replacement, expected_error in mutations:
            with self.subTest(path=relative_path, replacement=replacement):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertIn(current, original)
                path.write_text(
                    original.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error(expected_error)

                path.write_text(original, encoding="utf-8")

    def test_external_word_count_policy_requires_a_valid_override_reason(self) -> None:
        path = self.fixture_root / "templates/guide.md"
        original = path.read_text(encoding="utf-8")
        anchor = "word_count: 0\n"
        self.assertIn(anchor, original)

        path.write_text(
            original.replace(
                anchor,
                anchor + "word_count_policy: external\n",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error(
            "word_count_policy 'external' requires word_count_override_reason"
        )

        path.write_text(
            original.replace(
                anchor,
                anchor
                + "word_count_policy: external\n"
                + "word_count_override_reason: too short\n",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_contract_error("field 'word_count_override_reason' is shorter")

        path.write_text(
            original.replace(
                anchor,
                anchor
                + "word_count_policy: external\n"
                + "word_count_override_reason: Counts include generated appendices.\n",
                1,
            ),
            encoding="utf-8",
        )
        self.assertEqual([], validate(self.fixture_root))

    def test_requires_exact_schema_dependency_and_generated_context(self) -> None:
        seed_path = self.fixture_root / "seed.yaml"
        original_seed = seed_path.read_text(encoding="utf-8")
        seed_mutations = (
            (
                "source: organvm-iv-taxis/schema-definitions",
                "source: meta-organvm/schema-definitions",
            ),
            ("  - type: schema\n", "  - type: contract\n"),
            (
                "consumes:\n"
                "  - type: schema\n"
                "    source: organvm-iv-taxis/schema-definitions\n"
                '    description: "Consumes the canonical project-record and '
                'assertion-evidence schemas"\n',
                "consumes: []\n",
            ),
        )
        for current, replacement in seed_mutations:
            with self.subTest(seed_replacement=replacement):
                self.assertIn(current, original_seed)
                seed_path.write_text(
                    original_seed.replace(current, replacement, 1), encoding="utf-8"
                )
                self.assert_contract_error("seed.yaml: expected consumes=")
                seed_path.write_text(original_seed, encoding="utf-8")

        generated_lines = (
            (
                "AGENTS.md",
                "- **Consume** `schema` from "
                "[`organvm-iv-taxis/schema-definitions`]"
                "(../../organvm-iv-taxis/schema-definitions/CLAUDE.md)",
            ),
            (
                "CLAUDE.md",
                "- **Consumes** ← `organvm-iv-taxis/schema-definitions`: schema",
            ),
            (
                "GEMINI.md",
                "- **Consumes** ← `organvm-iv-taxis/schema-definitions`: schema",
            ),
        )
        for relative_path, canonical in generated_lines:
            with self.subTest(path=relative_path):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertEqual(1, original.splitlines().count(canonical))
                path.write_text(
                    original.replace(
                        canonical,
                        canonical.replace(
                            "organvm-iv-taxis/schema-definitions",
                            "meta-organvm/schema-definitions",
                        ),
                        1,
                    ),
                    encoding="utf-8",
                )
                self.assert_contract_error("canonical identity line")
                path.write_text(original, encoding="utf-8")

                path.write_text(
                    original.replace(canonical, f"{canonical}\n{canonical}", 1),
                    encoding="utf-8",
                )
                self.assert_contract_error("found 2")
                path.write_text(original, encoding="utf-8")

                for opening, closing in (("<!--", "-->"), ("```markdown", "```")):
                    with self.subTest(path=relative_path, hidden_by=opening):
                        path.write_text(
                            original.replace(
                                canonical,
                                f"{opening}\n{canonical}\n{closing}",
                                1,
                            ),
                            encoding="utf-8",
                        )
                        self.assert_contract_error("canonical identity line")
                        path.write_text(original, encoding="utf-8")

    def test_pins_seed_production_edges_and_generated_edge_parity(self) -> None:
        seed_path = self.fixture_root / "seed.yaml"
        original_seed = seed_path.read_text(encoding="utf-8")
        produces_start = original_seed.index("produces:\n")
        consumes_start = original_seed.index("consumes:\n")
        production_block = original_seed[produces_start:consumes_start]
        mutations = (
            "produces: []\n\n",
            production_block.replace("editorial-governance", "unknown-contract", 1),
            production_block.replace("public-process", "unreviewed-consumer", 1),
            production_block.replace("defines-schema-for", "advises", 1),
        )
        for replacement in mutations:
            with self.subTest(seed_replacement=replacement):
                seed_path.write_text(
                    original_seed.replace(production_block, replacement, 1),
                    encoding="utf-8",
                )
                self.assert_contract_error("seed.yaml: expected produces=")
        seed_path.write_text(original_seed, encoding="utf-8")

        generated_lines = (
            ("AGENTS.md", "- **Produce** `editorial-governance` for ORGAN-V"),
            ("AGENTS.md", "- **Produce** `frontmatter-schema` for ORGAN-V"),
            ("AGENTS.md", "- **Produce** `essay-templates` for ORGAN-V"),
            (
                "CLAUDE.md",
                "- **Produces** → `ORGAN-V`: editorial-governance",
            ),
            (
                "CLAUDE.md",
                "- **Produces** → `ORGAN-V`: frontmatter-schema",
            ),
            ("CLAUDE.md", "- **Produces** → `ORGAN-V`: essay-templates"),
            (
                "GEMINI.md",
                "- **Produces** → `ORGAN-V`: editorial-governance",
            ),
            (
                "GEMINI.md",
                "- **Produces** → `ORGAN-V`: frontmatter-schema",
            ),
            ("GEMINI.md", "- **Produces** → `ORGAN-V`: essay-templates"),
        )
        for relative_path, canonical in generated_lines:
            with self.subTest(path=relative_path, edge=canonical):
                path = self.fixture_root / relative_path
                original = path.read_text(encoding="utf-8")
                self.assertEqual(1, original.splitlines().count(canonical))
                path.write_text(
                    original.replace(canonical, "- **Produces** hidden drift", 1),
                    encoding="utf-8",
                )
                self.assert_contract_error("canonical identity line")
                path.write_text(original, encoding="utf-8")

    def test_rejects_string_instead_of_essay_list(self) -> None:
        path = self.fixture_root / "templates/guide.md"
        content = path.read_text(encoding="utf-8")
        self.assertIn("references: []", content)
        path.write_text(
            content.replace("references: []", 'references: ""', 1),
            encoding="utf-8",
        )

        self.assert_contract_error("field 'references' must have type 'list'")


if __name__ == "__main__":
    unittest.main()
