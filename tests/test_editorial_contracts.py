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
