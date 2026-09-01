#!/usr/bin/env python3
"""Validate the repository's editorial schemas, templates, and README contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml


CANONICAL_ORGANIZATION = "organvm"
CANONICAL_REPOSITORY = "editorial-standards"
CANONICAL_IDENTITY_LINES = {
    Path("CHANGELOG.md"): (
        "[Unreleased]: https://github.com/organvm/editorial-standards/compare/v0.1.0...HEAD",
        "[0.1.0]: https://github.com/organvm/editorial-standards/releases/tag/v0.1.0",
    ),
    Path("CLAUDE.md"): (
        "**Org:** `organvm` | **Repo:** `editorial-standards`",
    ),
    Path("DISCOVERY.md"): (
        "# Discovery: organvm/editorial-standards",
    ),
    Path("GEMINI.md"): (
        "**Org:** `organvm` | **Repo:** `editorial-standards`",
    ),
    Path("ecosystem.yaml"): (
        "repo: editorial-standards",
        "organ: V",
    ),
    Path("README.md"): (
        "[![ORGAN-V: Logos](https://img.shields.io/badge/ORGAN--V-Logos-0d47a1?style=flat-square)](https://github.com/organvm)",
        "[![CI](https://github.com/organvm/editorial-standards/actions/workflows/ci.yml/badge.svg)](https://github.com/organvm/editorial-standards/actions/workflows/ci.yml)",
        "[![Tier: Standard](https://img.shields.io/badge/tier-standard-2196f3?style=flat-square)](https://github.com/organvm/editorial-standards)",
        "- **[public-process](https://github.com/organvm/public-process)** — the publication venue where validated essays are deployed. public-process uses the templates and naming conventions defined here.",
        "git clone https://github.com/organvm/editorial-standards.git",
    ),
    Path("schemas/frontmatter-schema.yaml"): (
        "# Governs: All essays in organvm/public-process/_posts/",
    ),
    Path("schemas/log-schema.yaml"): (
        "# Governs: All logs in organvm/public-process/_logs/",
    ),
    Path("seed.yaml"): (
        "# seed.yaml — Automation Contract for organvm/editorial-standards",
    ),
    Path("value-repos.json"): (
        '      "repo": "organvm/editorial-standards",',
    ),
}
IDENTITY_LINE_PREFIXES = {
    Path("CHANGELOG.md"): ("[Unreleased]:", "[0.1.0]:"),
    Path("CLAUDE.md"): ("**Org:**",),
    Path("DISCOVERY.md"): ("# Discovery:",),
    Path("GEMINI.md"): ("**Org:**",),
    Path("ecosystem.yaml"): ("repo:", "organ:"),
    Path("README.md"): (
        "[![ORGAN-V: Logos]",
        "[![CI]",
        "[![Tier: Standard]",
        "- **[public-process](https://github.com/",
        "git clone https://github.com/",
    ),
    Path("schemas/frontmatter-schema.yaml"): ("# Governs:",),
    Path("schemas/log-schema.yaml"): ("# Governs:",),
    Path("seed.yaml"): ("# seed.yaml — Automation Contract for ",),
    Path("value-repos.json"): ('"repo":',),
}
REQUIRED_SCHEMA_FILES = {
    Path("schemas/category-taxonomy.yaml"),
    Path("schemas/frontmatter-schema.yaml"),
    Path("schemas/log-schema.yaml"),
    Path("schemas/quality-rubric.yaml"),
    Path("schemas/reader-mode-rubric.yaml"),
    Path("schemas/tag-governance.yaml"),
}
REQUIRED_LOCAL_CI_PREREQUISITES = ("Python 3.12", "PyYAML")
REQUIRED_LOCAL_CI_COMMANDS = (
    "python3 -m pip install pyyaml",
    'python3 -c "',
    "for f in glob.glob('schemas/*.yaml'):",
    "python3 scripts/validate_editorial_contracts.py",
    "python3 -m unittest discover -s tests -v",
    "test -f README.md",
    "test -f LICENSE",
    "test -f docs/reader-mode-documentation.md",
    "python3 -m py_compile scripts/validate_editorial_contracts.py tests/test_editorial_contracts.py",
    "git diff --check",
)
CANONICAL_MAPPING_IDENTITIES = {
    Path("seed.yaml"): {
        "org": CANONICAL_ORGANIZATION,
        "repo": CANONICAL_REPOSITORY,
    },
    Path("ecosystem.yaml"): {
        "repo": CANONICAL_REPOSITORY,
        "organ": "V",
    },
}
IDENTITY_URL_TARGETS = {
    Path("CHANGELOG.md"): {CANONICAL_REPOSITORY: CANONICAL_ORGANIZATION},
    Path("CLAUDE.md"): {CANONICAL_REPOSITORY: CANONICAL_ORGANIZATION},
    Path("DISCOVERY.md"): {CANONICAL_REPOSITORY: CANONICAL_ORGANIZATION},
    Path("GEMINI.md"): {CANONICAL_REPOSITORY: CANONICAL_ORGANIZATION},
    Path("README.md"): {
        CANONICAL_REPOSITORY: CANONICAL_ORGANIZATION,
        "public-process": CANONICAL_ORGANIZATION,
    },
    Path("ecosystem.yaml"): {CANONICAL_REPOSITORY: CANONICAL_ORGANIZATION},
    Path("schemas/frontmatter-schema.yaml"): {
        "public-process": CANONICAL_ORGANIZATION,
    },
    Path("schemas/log-schema.yaml"): {"public-process": CANONICAL_ORGANIZATION},
    Path("seed.yaml"): {CANONICAL_REPOSITORY: CANONICAL_ORGANIZATION},
    Path("value-repos.json"): {CANONICAL_REPOSITORY: CANONICAL_ORGANIZATION},
}
GITHUB_REPOSITORY_URL = re.compile(
    r"https?://(?:www\.)?github\.com/"
    r"(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)"
)
FRONTMATTER_README_RULE_KEYS = {
    "layout": {"type", "enum"},
    "title": {"type", "min_length", "max_length"},
    "author": {"type", "pattern"},
    "date": {"type", "format", "pattern"},
    "tags": {"type", "min_items", "max_items", "item_type", "item_pattern"},
    "category": {"type", "enum"},
    "excerpt": {"type", "min_length", "max_length"},
    "portfolio_relevance": {"type", "enum"},
    "related_repos": {"type", "item_type", "item_pattern"},
    "reading_time": {"type", "pattern"},
    "word_count": {"type", "min"},
    "references": {"type", "min_items", "item_type"},
}
ESSAY_CATEGORIES = {
    Path("templates/case-study.md"): "case-study",
    Path("templates/guide.md"): "guide",
    Path("templates/meta-system.md"): "meta-system",
    Path("templates/methodology.md"): "methodology",
    Path("templates/retrospective.md"): "retrospective",
}
PUBLICATION_TEMPLATES = set(ESSAY_CATEGORIES) | {Path("templates/log.md")}
READER_MODE_TEMPLATES = {
    Path("templates/repository-readme-v2.md"),
    Path("templates/evidence.md"),
    Path("templates/audiences/business.md"),
    Path("templates/audiences/evaluator.md"),
    Path("templates/audiences/general.md"),
    Path("templates/audiences/humanities.md"),
    Path("templates/audiences/technical.md"),
}
AUDIENCE_TEMPLATES = {
    path
    for path in READER_MODE_TEMPLATES
    if path.parent == Path("templates/audiences")
}
CANONICAL_README_LINK = "[Canonical README](../../README.md)"
REQUIRED_READER_MARKERS = {
    Path("templates/repository-readme-v2.md"): (
        "# [Project name]",
        "> [One ordinary-language sentence: what this is, what it does, and why it exists.]",
        "Keep only verified, enabled destinations in both the following hero row and the",
        "audience table. Remove disabled entries; do not leave placeholders or dead links.",
        "[View the project] · [See a demonstration] · [Technical documentation] ·",
        "[Humanities interpretation] · [Business applications] · [Evidence]",
        "## What am I looking at?",
        "## Choose your reading path",
        "| I am reading as… | Start here |",
        "## Project at a glance",
        "| | |",
        "## Canonical project documentation",
    ),
    Path("templates/evidence.md"): (
        "# [Project]: evidence record",
        "## Assertion evidence",
        "| ID | Claim | Claim posture | Assertion class | Verification state | Evidence | Freshness |",
        "## Project limitations",
        "| ID | Limitation | Related assertion |",
    ),
    Path("templates/audiences/business.md"): (
        "# [Project]: operational edition",
        "## Existing operational problem",
        "## Who experiences it",
        "## Current workaround",
        "## Changed workflow",
        "## Inputs and outputs",
        "## Integration requirements",
        "## Risks and constraints",
        "## Current deployment status",
        "## Evidence versus projected value",
        "## Technical appendix and evidence",
    ),
    Path("templates/audiences/evaluator.md"): (
        "# [Project]: contribution and evaluation record",
        "## Initial condition",
        "## Anthony's role",
        "## Personally designed or implemented",
        "## What changed",
        "## Evidence for each material claim",
        "## Incomplete work and known limits",
        "## Collaborative, generated, inherited, or externally supplied work",
        "## Inspection map",
    ),
    Path("templates/audiences/general.md"): (
        "# [Project]: a two-minute explanation",
        "## What is this?",
        "## What problem led to it?",
        "## What happens when someone uses it?",
        "## A concrete example",
        "## Why it matters",
        "## What exists now",
        "## Where to go next",
    ),
    Path("templates/audiences/humanities.md"): (
        "# [Project]: humanities edition",
        "## Central question",
        "## Intellectual and artistic genealogy",
        "## Medium and formal choices",
        "## Authorship, agency, and interpretation",
        "## Cultural and institutional context",
        "## Ethical tensions",
        "## How computation changes the question",
        "## Further reading and evidence",
    ),
    Path("templates/audiences/technical.md"): (
        "# [Project]: technical edition",
        "## Implementation status",
        "## System architecture",
        "## Components and boundaries",
        "## Data flow and interfaces",
        "## Dependencies and requirements",
        "## Install and run",
        "## Tests and verification",
        "## Observability and failure modes",
        "## Security and human-approval boundaries",
        "## Known technical debt",
        "## Inspection paths",
    ),
}
REQUIRED_READER_TABLES = {
    Path("templates/repository-readme-v2.md"): (
        ("I am reading as…", "Start here"),
        ("", ""),
    ),
    Path("templates/evidence.md"): (
        (
            "ID",
            "Claim",
            "Claim posture",
            "Assertion class",
            "Verification state",
            "Evidence",
            "Freshness",
        ),
        ("ID", "Limitation", "Related assertion"),
    ),
}
REQUIRED_READER_TABLE_ROW_LABELS = {
    (Path("templates/repository-readme-v2.md"), ("", "")): (
        "**What it is**",
        "**Problem addressed**",
        "**Current state**",
        "**Primary users**",
        "**What Anthony built**",
        "**Evidence**",
        "**Known limitations**",
    ),
}
REQUIRED_READER_TABLE_SECTIONS = {
    (
        Path("templates/repository-readme-v2.md"),
        ("I am reading as…", "Start here"),
    ): "## Choose your reading path",
    (
        Path("templates/repository-readme-v2.md"),
        ("", ""),
    ): "## Project at a glance",
    (
        Path("templates/evidence.md"),
        (
            "ID",
            "Claim",
            "Claim posture",
            "Assertion class",
            "Verification state",
            "Evidence",
            "Freshness",
        ),
    ): "## Assertion evidence",
    (
        Path("templates/evidence.md"),
        ("ID", "Limitation", "Related assertion"),
    ): "## Project limitations",
}
TABLE_DELIMITER_CELL = re.compile(r"^:?-{3,}:?$")
FRONTMATTER_TABLE_HEADER = ("Field", "Type", "Core constraint")
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
TAG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
TAG_GOVERNANCE_FORMAT = (
    "lowercase, hyphenated (e.g. 'building-in-public', not 'Building In Public')"
)
READING_TIME_PATTERN = r"^\d+ min$"
RELATED_REPOSITORY_PATTERN = (
    r"^(?:organvm|organvm-(?:i|ii|iii|iv|v|vi|vii|viii)-[a-z0-9]+"
    r"(?:-[a-z0-9]+)*|meta-organvm(?:-[a-z0-9]+)*)/"
    r"(?![.]{1,2}$)[A-Za-z0-9._-]{1,100}$"
)


def _load_yaml(path: Path, errors: list[str]) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"{path}: invalid YAML: {exc}")
        return None


def _frontmatter(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{path}: cannot read template: {exc}")
        return None

    parts = content.split("---", 2)
    if not content.startswith("---") or len(parts) < 3:
        errors.append(f"{path}: missing or incomplete publication frontmatter")
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        errors.append(f"{path}: invalid frontmatter YAML: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path}: frontmatter is not a mapping")
        return None
    return data


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "list":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


def _matches_pattern(
    pattern: Any,
    value: str,
    context: str,
    errors: list[str],
) -> bool | None:
    """Return a regex match while turning malformed schema regexes into diagnostics."""
    if not isinstance(pattern, str):
        errors.append(f"{context}: schema pattern must be a string")
        return None
    try:
        return re.fullmatch(pattern, value) is not None
    except re.error as exc:
        errors.append(f"{context}: invalid schema regex pattern: {exc}")
        return None


def _validate_declared_type(
    value: Any,
    rules: dict[str, Any],
    path: Path,
    field: str,
    errors: list[str],
) -> None:
    """Validate template structure without applying publish-time value bounds."""
    expected_type = rules.get("type")
    if not isinstance(expected_type, str) or not _matches_type(value, expected_type):
        errors.append(f"{path}: field {field!r} must have type {expected_type!r}")
        return

    if expected_type == "list":
        item_type = rules.get("item_type")
        item_pattern = rules.get("item_pattern")
        for index, item in enumerate(value):
            if item_type and not _matches_type(item, item_type):
                errors.append(
                    f"{path}: field {field}[{index}] must have type {item_type!r}"
                )
            elif item_pattern:
                matched = _matches_pattern(
                    item_pattern,
                    item,
                    f"{path}: field {field}[{index}]",
                    errors,
                )
                if matched is False:
                    errors.append(
                        f"{path}: field {field}[{index}] does not match "
                        "the schema pattern"
                    )
    elif expected_type == "object":
        properties = rules.get("properties", {})
        if isinstance(properties, dict):
            for key in sorted(set(value) & set(properties)):
                child_rules = properties[key]
                if isinstance(child_rules, dict):
                    _validate_declared_type(
                        value[key], child_rules, path, f"{field}.{key}", errors
                    )


def _validate_schema_value(
    value: Any,
    rules: dict[str, Any],
    field: str,
    errors: list[str],
) -> None:
    expected_type = rules.get("type")
    if not isinstance(expected_type, str) or not _matches_type(value, expected_type):
        errors.append(
            f"templates/log.md: field {field!r} must have type {expected_type!r}"
        )
        return

    if expected_type == "string":
        if "min_length" in rules and len(value) < rules["min_length"]:
            errors.append(f"templates/log.md: field {field!r} is shorter than allowed")
        if "max_length" in rules and len(value) > rules["max_length"]:
            errors.append(f"templates/log.md: field {field!r} is longer than allowed")
        if "enum" in rules and value not in rules["enum"]:
            errors.append(
                f"templates/log.md: field {field!r} has value {value!r} outside "
                f"the schema enum"
            )
        pattern = rules.get("pattern")
        placeholder = rules.get("format")
        if pattern and value != placeholder:
            matched = _matches_pattern(
                pattern,
                value,
                f"templates/log.md: field {field!r}",
                errors,
            )
            if matched is False:
                errors.append(
                    f"templates/log.md: field {field!r} value {value!r} does not "
                    "match the schema pattern"
                )

    elif expected_type == "integer":
        if "min" in rules and value < rules["min"]:
            errors.append(f"templates/log.md: field {field!r} is below the schema minimum")

    elif expected_type == "list":
        if "min_items" in rules and len(value) < rules["min_items"]:
            errors.append(f"templates/log.md: field {field!r} has too few items")
        if "max_items" in rules and len(value) > rules["max_items"]:
            errors.append(f"templates/log.md: field {field!r} has too many items")
        item_type = rules.get("item_type")
        item_pattern = rules.get("item_pattern")
        for index, item in enumerate(value):
            item_field = f"{field}[{index}]"
            if item_type and not _matches_type(item, item_type):
                errors.append(
                    f"templates/log.md: field {item_field!r} must have type "
                    f"{item_type!r}"
                )
            elif item_pattern:
                matched = _matches_pattern(
                    item_pattern,
                    item,
                    f"templates/log.md: field {item_field!r}",
                    errors,
                )
                if matched is False:
                    errors.append(
                        f"templates/log.md: field {item_field!r} does not match "
                        "the schema pattern"
                    )

    elif expected_type == "object":
        properties = rules.get("properties", {})
        required_keys = set(rules.get("required_keys", []))
        missing_keys = sorted(required_keys - set(value))
        unknown_keys = sorted(set(value) - set(properties))
        if missing_keys:
            errors.append(
                f"templates/log.md: field {field!r} is missing required keys: "
                f"{missing_keys}"
            )
        if unknown_keys:
            errors.append(
                f"templates/log.md: field {field!r} has unknown keys: {unknown_keys}"
            )
        for key in sorted(set(value) & set(properties)):
            _validate_schema_value(
                value[key], properties[key], f"{field}.{key}", errors
            )


def _validate_log_template(root: Path, errors: list[str]) -> None:
    schema_path = root / "schemas/log-schema.yaml"
    template_path = root / "templates/log.md"
    schema = _load_yaml(schema_path, errors)
    frontmatter = _frontmatter(template_path, errors)
    if not isinstance(schema, dict) or frontmatter is None:
        return

    required = schema.get("required_fields", {})
    optional = schema.get("optional_fields", {})
    if not isinstance(required, dict) or not isinstance(optional, dict):
        errors.append("schemas/log-schema.yaml: fields must be YAML mappings")
        return

    missing = sorted(set(required) - set(frontmatter))
    unknown = sorted(set(frontmatter) - set(required) - set(optional))
    if missing:
        errors.append(f"templates/log.md: missing required log fields: {missing}")
    if unknown:
        errors.append(f"templates/log.md: unknown log fields: {unknown}")

    for field in sorted(set(frontmatter) & (set(required) | set(optional))):
        rules = required.get(field, optional.get(field))
        if not isinstance(rules, dict):
            errors.append(f"schemas/log-schema.yaml: rules for {field!r} are not a mapping")
            continue
        _validate_schema_value(frontmatter[field], rules, field, errors)


def _table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _rendered_markdown_lines(
    path: Path, content: str, errors: list[str]
) -> list[str]:
    """Remove fenced code so literals cannot satisfy rendered-page contracts."""
    rendered: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line in content.splitlines():
        stripped = line.lstrip()
        if len(line) - len(stripped) > 3:
            if fence_character is None:
                rendered.append(line)
            continue
        fence = re.match(r"(`{3,}|~{3,})", stripped)
        if fence_character is None:
            if fence is None:
                rendered.append(line)
            else:
                fence_character = fence.group(1)[0]
                fence_length = len(fence.group(1))
            continue
        if (
            fence is not None
            and fence.group(1)[0] == fence_character
            and len(fence.group(1)) >= fence_length
            and not stripped[len(fence.group(1)) :].strip()
        ):
            fence_character = None
            fence_length = 0
    if fence_character is not None:
        errors.append(f"{path}: unclosed Markdown code fence")
    return rendered


def _format_enum(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "invalid enum"
    rendered = [f"`{value}`" for value in values]
    if len(rendered) == 1:
        return rendered[0]
    if len(rendered) == 2:
        return f"{rendered[0]} or {rendered[1]}"
    return ", ".join(rendered[:-1]) + f", or {rendered[-1]}"


def _expected_frontmatter_readme_cells(
    field: str, rules: dict[str, Any]
) -> tuple[str, str]:
    """Render the human table cells from the executable field rules."""
    enum_values = rules.get("enum")
    type_cell = "enum" if isinstance(enum_values, list) and len(enum_values) > 1 else str(
        rules.get("type")
    )

    if field == "layout":
        constraint = _format_enum(enum_values)
    elif field in {"title", "excerpt"}:
        constraint = (
            f"{rules.get('min_length')}–{rules.get('max_length')} characters"
        )
    elif field == "author" and rules.get("pattern") == "^@":
        constraint = "GitHub handle with `@` prefix"
    elif (
        field == "date"
        and rules.get("format") == "YYYY-MM-DD"
        and rules.get("pattern") == DATE_PATTERN
    ):
        constraint = "`YYYY-MM-DD`"
    elif field == "tags" and rules.get("item_pattern") == TAG_PATTERN:
        constraint = (
            f"{rules.get('min_items')}–{rules.get('max_items')} lowercase, "
            "hyphenated tags"
        )
    elif field in {"category", "portfolio_relevance"}:
        constraint = _format_enum(enum_values)
    elif (
        field == "related_repos"
        and rules.get("type") == "list"
        and rules.get("item_type") == "string"
        and rules.get("item_pattern") == RELATED_REPOSITORY_PATTERN
    ):
        constraint = (
            "Canonical ORGANVM `owner/repository` slugs, such as "
            "`organvm/essay-pipeline`"
        )
    elif field == "reading_time" and rules.get("pattern") == READING_TIME_PATTERN:
        constraint = "e.g. `12 min`"
    elif field == "word_count" and rules.get("type") == "integer":
        constraint = f"minimum {rules.get('min')}"
    elif (
        field == "references"
        and rules.get("type") == "list"
        and rules.get("item_type") == "string"
        and rules.get("min_items") == 0
    ):
        constraint = "citations, or an explicit empty list"
    else:
        constraint = f"schema rules `{rules!r}`"
    return type_cell, constraint


def _validate_required_reader_table(
    path: Path,
    lines: list[str],
    header: tuple[str, ...],
    errors: list[str],
) -> None:
    """Validate one required Markdown table without interpreting its prose."""
    matching_headers = [
        index for index, line in enumerate(lines) if _table_cells(line) == list(header)
    ]
    label = " | ".join(header)
    if len(matching_headers) != 1:
        errors.append(
            f"{path}: required table header {label!r} must appear exactly once"
        )
        return

    header_index = matching_headers[0]
    owning_section = REQUIRED_READER_TABLE_SECTIONS.get((path, header))
    if owning_section is not None:
        section_indices = [
            index for index, line in enumerate(lines) if line == owning_section
        ]
        if len(section_indices) == 1:
            section_index = section_indices[0]
            next_section_index = next(
                (
                    index
                    for index in range(section_index + 1, len(lines))
                    if lines[index].startswith("## ")
                ),
                len(lines),
            )
            if not section_index < header_index < next_section_index:
                errors.append(
                    f"{path}: required table {label!r} must remain within "
                    f"section {owning_section!r}"
                )
    if header_index + 1 >= len(lines):
        errors.append(f"{path}: required table {label!r} is missing its delimiter")
        return

    delimiter_cells = _table_cells(lines[header_index + 1])
    delimiter_valid = (
        delimiter_cells is not None
        and len(delimiter_cells) == len(header)
        and all(TABLE_DELIMITER_CELL.fullmatch(cell) for cell in delimiter_cells)
    )
    if not delimiter_valid:
        errors.append(f"{path}: required table {label!r} has an invalid delimiter")

    data_rows: list[list[str]] = []
    for row_number, line in enumerate(lines[header_index + 2 :], start=1):
        if not line.lstrip().startswith("|"):
            break
        cells = _table_cells(line)
        if cells is None or len(cells) != len(header):
            actual_columns = len(cells) if cells is not None else 0
            errors.append(
                f"{path}: required table {label!r} row {row_number} has "
                f"{actual_columns} columns; expected {len(header)}"
            )
            continue
        data_rows.append(cells)

    if not data_rows:
        errors.append(f"{path}: required table {label!r} has no data rows")

    required_row_labels = REQUIRED_READER_TABLE_ROW_LABELS.get((path, header))
    if required_row_labels is not None:
        actual_row_labels = tuple(row[0] for row in data_rows)
        if actual_row_labels != required_row_labels:
            errors.append(
                f"{path}: required table {label!r} row labels/order mismatch: "
                f"expected={list(required_row_labels)}, "
                f"actual={list(actual_row_labels)}"
            )
        empty_labels = [row[0] for row in data_rows if not row[1]]
        if empty_labels:
            errors.append(
                f"{path}: required table {label!r} has empty values for "
                f"{empty_labels}"
            )


def _validate_reader_structure(
    path: Path,
    lines: list[str],
    markers: tuple[str, ...],
    errors: list[str],
) -> None:
    """Require reader markers exactly once and in their declared sequence."""
    positions: list[int] = []
    complete = True
    for marker in markers:
        occurrences = [index for index, line in enumerate(lines) if line == marker]
        if not occurrences:
            errors.append(f"{path}: missing required template marker {marker!r}")
            complete = False
        elif len(occurrences) > 1:
            errors.append(f"{path}: duplicate required template marker {marker!r}")
            complete = False
        else:
            positions.append(occurrences[0])

    if complete and any(left >= right for left, right in zip(positions, positions[1:])):
        errors.append(f"{path}: required template markers are out of order")

    for header in REQUIRED_READER_TABLES.get(path, ()):
        _validate_required_reader_table(path, lines, header, errors)


def _validate_readme(
    root: Path, required_map: dict[str, Any], errors: list[str]
) -> None:
    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    required_fields = set(required_map)
    development_parts = readme.split("## Development", 1)
    development_section = (
        development_parts[1].split("\n## ", 1)[0]
        if len(development_parts) == 2
        else ""
    )
    bash_blocks = re.findall(
        r"```bash\s*\n(.*?)\n```", development_section, re.DOTALL
    )
    executable_bash_lines = {
        line.strip()
        for block in bash_blocks
        for line in block.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    for prerequisite in REQUIRED_LOCAL_CI_PREREQUISITES:
        if prerequisite not in development_section:
            errors.append(
                "README.md: missing local CI reproduction prerequisite: "
                f"{prerequisite}"
            )
    for command in REQUIRED_LOCAL_CI_COMMANDS:
        if command not in executable_bash_lines:
            errors.append(
                f"README.md: missing local CI reproduction command: {command}"
            )
    obsolete_field_guidance = (
        "Must match the `slug` frontmatter field",
        "No markdown in the abstract field",
        "The `organs_referenced` array",
    )
    for phrase in obsolete_field_guidance:
        if phrase in readme:
            errors.append(f"README.md: obsolete frontmatter guidance: {phrase}")

    expected_count_phrases = (
        f"the {len(required_fields)} required metadata fields",
        f"All {len(required_fields)} required fields",
    )
    for phrase in expected_count_phrases:
        if phrase not in readme:
            errors.append(f"README.md: missing schema-derived field count: {phrase}")

    section_parts = readme.split("## Frontmatter Schema", 1)
    if len(section_parts) != 2:
        errors.append("README.md: missing Frontmatter Schema section")
        return

    section = section_parts[1].split("\n## ", 1)[0]
    lines = section.splitlines()
    header_candidates = [
        index
        for index, line in enumerate(lines)
        if (cells := _table_cells(line)) is not None and cells[:1] == ["Field"]
    ]
    if len(header_candidates) != 1:
        errors.append(
            "README.md: frontmatter table header must appear exactly once"
        )
        return
    header_index = header_candidates[0]
    if header_index + 1 >= len(lines):
        errors.append("README.md: missing frontmatter field table")
        return

    header_cells = _table_cells(lines[header_index])
    if header_cells != list(FRONTMATTER_TABLE_HEADER):
        errors.append(
            "README.md: frontmatter table header must be exactly "
            f"{list(FRONTMATTER_TABLE_HEADER)}"
        )
    delimiter_cells = _table_cells(lines[header_index + 1])
    delimiter_cell = re.compile(r"^:?-{3,}:?$")
    delimiter_valid = (
        header_cells is not None
        and delimiter_cells is not None
        and len(delimiter_cells) == len(header_cells)
        and all(delimiter_cell.fullmatch(cell) for cell in delimiter_cells)
    )
    if not delimiter_valid:
        errors.append("README.md: invalid frontmatter table delimiter")

    table_fields: list[str] = []
    table_rows: dict[str, tuple[str, str]] = {}
    invalid_rows: list[str] = []
    expected_columns = len(header_cells) if header_cells is not None else 0
    table_lines = lines[header_index + 2 :]
    if not table_lines or not table_lines[0].lstrip().startswith("|"):
        errors.append(
            "README.md: frontmatter table data rows must start immediately "
            "after the delimiter"
        )
    for line in table_lines:
        if not line.lstrip().startswith("|"):
            break
        cells = _table_cells(line)
        if cells is None or len(cells) != expected_columns:
            invalid_rows.append(line.strip())
            continue
        field_match = re.fullmatch(r"`([^`]+)`", cells[0])
        if field_match is None:
            invalid_rows.append(line.strip())
        else:
            field = field_match.group(1)
            table_fields.append(field)
            table_rows[field] = (cells[1], cells[2])

    if invalid_rows:
        errors.append(
            "README.md: invalid frontmatter table rows; field names must be "
            f"backtick-wrapped and rows must match the header: {invalid_rows}"
        )
    duplicate_fields = sorted(
        field for field in set(table_fields) if table_fields.count(field) > 1
    )
    if duplicate_fields:
        errors.append(f"README.md: duplicate frontmatter table fields: {duplicate_fields}")
    table_field_set = set(table_fields)
    if table_field_set != required_fields:
        missing = sorted(required_fields - table_field_set)
        extra = sorted(table_field_set - required_fields)
        errors.append(
            "README.md: frontmatter table/schema mismatch: "
            f"missing={missing}, extra={extra}"
        )
    expected_order = list(required_map)
    if table_fields != expected_order:
        errors.append(
            "README.md: frontmatter table/schema field order mismatch: "
            f"expected={expected_order}, actual={table_fields}"
        )
    renderer_fields = set(FRONTMATTER_README_RULE_KEYS)
    if renderer_fields != required_fields:
        errors.append(
            "README.md: frontmatter renderer/schema field mismatch: "
            f"missing={sorted(required_fields - renderer_fields)}, "
            f"extra={sorted(renderer_fields - required_fields)}"
        )
    for field in sorted(required_fields & table_field_set):
        rules = required_map.get(field)
        if not isinstance(rules, dict):
            errors.append(
                f"schemas/frontmatter-schema.yaml: rules for {field!r} "
                "are not a mapping"
            )
            continue
        actual_rule_keys = set(rules) - {"description"}
        expected_rule_keys = FRONTMATTER_README_RULE_KEYS.get(field, set())
        if actual_rule_keys != expected_rule_keys:
            errors.append(
                "README.md: frontmatter table renderer does not cover schema "
                f"rules for {field!r}: expected={sorted(expected_rule_keys)}, "
                f"actual={sorted(actual_rule_keys)}"
            )
            continue
        expected_cells = _expected_frontmatter_readme_cells(field, rules)
        actual_cells = table_rows[field]
        if actual_cells != expected_cells:
            errors.append(
                f"README.md: frontmatter table/schema cells mismatch for {field!r}: "
                f"expected={expected_cells}, actual={actual_cells}"
            )


def _validate_schema_inventory(root: Path, errors: list[str]) -> None:
    discovered = {
        path.relative_to(root)
        for path in (root / "schemas").rglob("*")
        if path.is_file()
    }
    missing = sorted(REQUIRED_SCHEMA_FILES - discovered)
    unclassified = sorted(discovered - REQUIRED_SCHEMA_FILES)
    if missing or unclassified:
        errors.append(
            "schema inventory mismatch: "
            f"missing={list(map(str, missing))}, "
            f"unclassified={list(map(str, unclassified))}"
        )
    for relative_path in sorted(REQUIRED_SCHEMA_FILES & discovered):
        schema = _load_yaml(root / relative_path, errors)
        if not isinstance(schema, dict):
            errors.append(f"{relative_path}: schema must be a YAML mapping")


def _validate_tag_governance(
    root: Path, frontmatter_tag_rules: Any, errors: list[str]
) -> None:
    governance_path = Path("schemas/tag-governance.yaml")
    governance = _load_yaml(root / governance_path, errors)
    if not isinstance(governance, dict) or not isinstance(frontmatter_tag_rules, dict):
        errors.append(
            "tag governance/frontmatter mismatch: both tag contracts must be mappings"
        )
        return
    governance_rules = governance.get("rules")
    if not isinstance(governance_rules, dict):
        errors.append("schemas/tag-governance.yaml: rules must be a YAML mapping")
        return

    expected_governance = {
        "min_per_essay": frontmatter_tag_rules.get("min_items"),
        "max_per_essay": frontmatter_tag_rules.get("max_items"),
        "format": TAG_GOVERNANCE_FORMAT,
        "pattern": frontmatter_tag_rules.get("item_pattern"),
    }
    actual_governance = {
        key: governance_rules.get(key) for key in expected_governance
    }
    if actual_governance != expected_governance:
        errors.append(
            "tag governance/frontmatter mismatch: "
            f"expected={expected_governance}, actual={actual_governance}"
        )

    preferred_tags = governance.get("preferred_tags")
    if not isinstance(preferred_tags, list) or not all(
        isinstance(tag, str) for tag in preferred_tags
    ):
        errors.append(
            "schemas/tag-governance.yaml: preferred_tags must be a list of strings"
        )
        return
    duplicates = sorted(
        tag for tag in set(preferred_tags) if preferred_tags.count(tag) > 1
    )
    if duplicates:
        errors.append(
            f"schemas/tag-governance.yaml: duplicate preferred tags: {duplicates}"
        )
    pattern = governance_rules.get("pattern")
    for tag in preferred_tags:
        matched = _matches_pattern(
            pattern,
            tag,
            "schemas/tag-governance.yaml: preferred_tags",
            errors,
        )
        if matched is False:
            errors.append(
                "schemas/tag-governance.yaml: preferred tag does not match "
                f"the governed pattern: {tag!r}"
            )


def _validate_repository_identity(root: Path, errors: list[str]) -> None:
    """Keep the machine-readable owner and generated contexts canonical."""
    for relative_path, expected_fields in CANONICAL_MAPPING_IDENTITIES.items():
        data = _load_yaml(root / relative_path, errors)
        if not isinstance(data, dict):
            errors.append(f"{relative_path}: identity document must be a YAML mapping")
            continue
        for field, expected in expected_fields.items():
            actual = data.get(field)
            if actual != expected:
                errors.append(
                    f"{relative_path}: expected {field}={expected!r}, found {actual!r}"
                )

    for relative_path, expected_lines in CANONICAL_IDENTITY_LINES.items():
        path = root / relative_path
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            errors.append(f"{relative_path}: cannot audit repository identity: {exc}")
            continue
        for expected_line in expected_lines:
            occurrences = lines.count(expected_line)
            if occurrences != 1:
                errors.append(
                    f"{relative_path}: canonical identity line must appear exactly "
                    f"once: {expected_line!r}; found {occurrences}"
                )
        for prefix in IDENTITY_LINE_PREFIXES[relative_path]:
            actual_prefixed = [
                line.strip() for line in lines if line.strip().startswith(prefix)
            ]
            expected_prefixed = [
                line.strip()
                for line in expected_lines
                if line.strip().startswith(prefix)
            ]
            if actual_prefixed != expected_prefixed:
                errors.append(
                    f"{relative_path}: canonical identity lines for prefix "
                    f"{prefix!r} mismatch: expected={expected_prefixed}, "
                    f"actual={actual_prefixed}"
                )

    legacy_owner = "organvm-v-logos"
    for relative_path in CANONICAL_IDENTITY_LINES:
        path = root / relative_path
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{relative_path}: cannot audit repository identity: {exc}")
            continue
        if legacy_owner in content:
            errors.append(
                f"{relative_path}: stale legacy repository owner {legacy_owner!r}"
            )

    for relative_path, target_owners in IDENTITY_URL_TARGETS.items():
        try:
            content = (root / relative_path).read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{relative_path}: cannot audit repository URLs: {exc}")
            continue
        for match in GITHUB_REPOSITORY_URL.finditer(content):
            repository = match.group("repo").removesuffix(".git")
            expected_owner = target_owners.get(repository)
            actual_owner = match.group("owner")
            if expected_owner is not None and actual_owner != expected_owner:
                errors.append(
                    f"{relative_path}: noncanonical GitHub owner for "
                    f"{repository!r}: expected={expected_owner!r}, "
                    f"actual={actual_owner!r}"
                )


def validate(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []

    _validate_schema_inventory(root, errors)

    overlap = PUBLICATION_TEMPLATES & READER_MODE_TEMPLATES
    if overlap:
        errors.append(f"template contracts overlap: {sorted(map(str, overlap))}")
    declared = PUBLICATION_TEMPLATES | READER_MODE_TEMPLATES
    discovered = {
        path.relative_to(root) for path in (root / "templates").rglob("*.md")
    }
    unclassified = sorted(discovered - declared)
    if unclassified:
        errors.append(f"unclassified template files: {list(map(str, unclassified))}")
    marker_contract_gap = sorted(
        READER_MODE_TEMPLATES ^ set(REQUIRED_READER_MARKERS)
    )
    if marker_contract_gap:
        errors.append(
            "reader-mode marker contracts do not match declared templates: "
            f"{list(map(str, marker_contract_gap))}"
        )
    table_contract_gap = sorted(set(REQUIRED_READER_TABLES) - READER_MODE_TEMPLATES)
    if table_contract_gap:
        errors.append(
            "reader-mode table contracts reference undeclared templates: "
            f"{list(map(str, table_contract_gap))}"
        )

    frontmatters: dict[Path, dict[str, Any]] = {}
    for relative_path in sorted(PUBLICATION_TEMPLATES):
        path = root / relative_path
        if not path.is_file():
            errors.append(f"{relative_path}: required publication template missing")
            continue
        data = _frontmatter(path, errors)
        if data is not None:
            frontmatters[relative_path] = data

    frontmatter_schema = _load_yaml(root / "schemas/frontmatter-schema.yaml", errors)
    if not isinstance(frontmatter_schema, dict):
        return errors
    required_map = frontmatter_schema.get("required_fields", {})
    optional_map = frontmatter_schema.get("optional_fields", {})
    if not isinstance(required_map, dict) or not isinstance(optional_map, dict):
        errors.append("schemas/frontmatter-schema.yaml: fields must be YAML mappings")
        return errors
    required_fields = set(required_map)
    allowed_fields = required_fields | set(optional_map)
    _validate_tag_governance(root, required_map.get("tags"), errors)

    for path, expected_category in sorted(ESSAY_CATEGORIES.items()):
        frontmatter = frontmatters.get(path)
        if frontmatter is None:
            continue
        fields = set(frontmatter)
        missing = sorted(required_fields - fields)
        unknown = sorted(fields - allowed_fields)
        if missing:
            errors.append(f"{path}: missing required frontmatter fields: {missing}")
        if unknown:
            errors.append(f"{path}: unknown frontmatter fields: {unknown}")
        for field in sorted(fields & allowed_fields):
            rules = required_map.get(field, optional_map.get(field))
            if not isinstance(rules, dict):
                errors.append(
                    f"schemas/frontmatter-schema.yaml: rules for {field!r} "
                    "are not a mapping"
                )
                continue
            _validate_declared_type(frontmatter[field], rules, path, field, errors)
        for field, expected in {"layout": "essay", "category": expected_category}.items():
            actual = frontmatter.get(field)
            if actual != expected:
                errors.append(f"{path}: expected {field}={expected!r}, found {actual!r}")

    related_rules = required_map.get("related_repos", {})
    related_pattern_text = (
        related_rules.get("item_pattern") if isinstance(related_rules, dict) else None
    )
    try:
        if not isinstance(related_pattern_text, str):
            raise TypeError("item_pattern must be a string")
        related_pattern = re.compile(related_pattern_text)
    except (TypeError, re.error) as exc:
        errors.append(
            "schemas/frontmatter-schema.yaml: invalid related_repos item_pattern: "
            f"{exc}"
        )
        related_pattern = None
    valid_related_repos = (
        "organvm/essay-pipeline",
        "organvm/editorial-standards",
        "organvm/.github",
        "organvm-iv-taxis/schema-definitions",
        "organvm-i-theoria/4-ivi374-F0Rivi4",
        "organvm-vi-koinonia/public-process",
        "organvm-viii-operations/future-project",
        "meta-organvm/organvm-corpvs-testamentvm",
    )
    invalid_related_repos = (
        "essay-pipeline",
        "github.com/organvm/essay-pipeline",
        "other/essay-pipeline",
        "4444j99/portfolio",
        "local/_portal",
        "organvm-evil/essay-pipeline",
        "organvm/",
        "organvm/.",
        "organvm/..",
        "organvm//essay-pipeline",
        "organvm/../essay-pipeline",
        "organvm/essay pipeline",
        "organvm/essay-pipeline/readme",
        "organvm/essay-pipeline?tab=readme",
    )
    if related_pattern is not None:
        for slug in valid_related_repos:
            if related_pattern.fullmatch(slug) is None:
                errors.append(
                    "schemas/frontmatter-schema.yaml: rejected canonical "
                    f"related_repos slug: {slug}"
                )
        for slug in invalid_related_repos:
            if related_pattern.fullmatch(slug) is not None:
                errors.append(
                    "schemas/frontmatter-schema.yaml: accepted invalid "
                    f"related_repos slug: {slug}"
                )

    _validate_log_template(root, errors)
    _validate_readme(root, required_map, errors)
    _validate_repository_identity(root, errors)

    for relative_path in sorted(READER_MODE_TEMPLATES):
        path = root / relative_path
        if not path.is_file():
            errors.append(f"{relative_path}: required reader-mode template missing")
            continue
        content = path.read_text(encoding="utf-8")
        content_lines = _rendered_markdown_lines(relative_path, content, errors)
        rendered_content = "\n".join(content_lines)
        if not rendered_content.lstrip().startswith("# "):
            errors.append(f"{relative_path}: must start with a level-one heading")
        _validate_reader_structure(
            relative_path,
            content_lines,
            REQUIRED_READER_MARKERS.get(relative_path, ()),
            errors,
        )
        if (
            relative_path in AUDIENCE_TEMPLATES
            and f"- {CANONICAL_README_LINK}" not in content_lines
        ):
            errors.append(
                f"{relative_path}: missing canonical project link "
                f"{CANONICAL_README_LINK!r}"
            )

    return errors


def main() -> int:
    errors = validate(Path.cwd())
    for error in errors:
        print(f"::error::{error}")
    if errors:
        return 1
    print(
        f"Validated {len(PUBLICATION_TEMPLATES)} publication templates and "
        f"{len(READER_MODE_TEMPLATES)} reader-mode templates"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
