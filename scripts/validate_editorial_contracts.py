#!/usr/bin/env python3
"""Validate the repository's editorial schemas, templates, and README contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml


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
EVALUATOR_TEMPLATE = Path("templates/audiences/evaluator.md")
CANONICAL_README_LINK = "[Canonical README](../../README.md)"


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
        if pattern and value != placeholder and re.fullmatch(pattern, value) is None:
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
            elif item_pattern and re.fullmatch(item_pattern, item) is None:
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


def _validate_readme(
    root: Path, required_fields: set[str], errors: list[str]
) -> None:
    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
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
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if re.match(r"^\s*\|\s*Field\s*\|", line)
        ),
        None,
    )
    if header_index is None or header_index + 1 >= len(lines):
        errors.append("README.md: missing frontmatter field table")
        return

    header_cells = _table_cells(lines[header_index])
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
    invalid_rows: list[str] = []
    expected_columns = len(header_cells) if header_cells is not None else 0
    for line in lines[header_index + 2 :]:
        if not line.lstrip().startswith("|"):
            if table_fields or invalid_rows:
                break
            continue
        cells = _table_cells(line)
        if cells is None or len(cells) != expected_columns:
            invalid_rows.append(line.strip())
            continue
        field_match = re.fullmatch(r"`([^`]+)`", cells[0])
        if field_match is None:
            invalid_rows.append(line.strip())
        else:
            table_fields.append(field_match.group(1))

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


def validate(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []

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
        for field, expected in {"layout": "essay", "category": expected_category}.items():
            actual = frontmatter.get(field)
            if actual != expected:
                errors.append(f"{path}: expected {field}={expected!r}, found {actual!r}")

    related_rules = required_map.get("related_repos", {})
    related_pattern = re.compile(related_rules.get("item_pattern", r"(?!)"))
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
    _validate_readme(root, required_fields, errors)

    for relative_path in sorted(READER_MODE_TEMPLATES):
        path = root / relative_path
        if not path.is_file():
            errors.append(f"{relative_path}: required reader-mode template missing")
            continue
        content = path.read_text(encoding="utf-8")
        if not content.lstrip().startswith("# "):
            errors.append(f"{relative_path}: must start with a level-one heading")
        if relative_path == EVALUATOR_TEMPLATE and CANONICAL_README_LINK not in content:
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
