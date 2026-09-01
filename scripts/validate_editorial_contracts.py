#!/usr/bin/env python3
"""Validate the repository's editorial schemas, templates, and README contract."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that fails closed when a mapping repeats a key."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


CANONICAL_ORGANIZATION = "organvm"
CANONICAL_REPOSITORY = "editorial-standards"
CANONICAL_SCHEMA_MERGE_SHA = "2c2b7c8b0e841a4abde82230be88524d43f9b3c2"
CANONICAL_LICENSE_SHA256 = (
    "65bfcf3e7864ed904700d0f80159399d07faf071600c194f0c9152d653012f3d"
)
CANONICAL_SCHEMA_DEPENDENCY = {
    "type": "schema",
    "source": "organvm-iv-taxis/schema-definitions",
    "description": (
        "Consumes the canonical project-record and assertion-evidence schemas"
    ),
}
CANONICAL_PRODUCTION_EDGES = [
    {
        "type": "editorial-governance",
        "format": "markdown",
        "consumers": [
            {
                "organ": "ORGAN-V",
                "repos": ["essay-pipeline", "public-process"],
                "relationship": "governs",
            }
        ],
    },
    {
        "type": "frontmatter-schema",
        "format": "yaml",
        "consumers": [
            {
                "organ": "ORGAN-V",
                "repos": ["essay-pipeline"],
                "relationship": "defines-schema-for",
            }
        ],
    },
    {
        "type": "essay-templates",
        "format": "markdown",
        "consumers": [
            {
                "organ": "ORGAN-V",
                "repos": ["public-process"],
                "relationship": "provides-templates-for",
            }
        ],
    },
]
CANONICAL_REGISTRY_ENTRY = {
    "repo": "organvm/editorial-standards",
    "tier": "ranked",
    "discovered": "2026-06-22",
    "value_thesis": (
        "Only repo in the estate expressing documentation quality as a "
        "machine-readable, versioned contract (6 YAML schemas + 100-point "
        "rubric + 6 publication templates), already consumed by essay-pipeline "
        "and public-process. Highest latent value: a reusable docs-quality "
        "standard the whole eight-organ estate could adopt once enforcement "
        "is co-located with the schema."
    ),
    "first_task": (
        "Ship a standalone, dependency-light frontmatter + quality validator "
        "(validate.py CLI + reusable GitHub composite action) that reads "
        "schemas/frontmatter-schema.yaml, building on the README/template parity "
        "already enforced in CI, so any estate repo can gate its docs on the "
        "same contract."
    ),
    "discovery_doc": "DISCOVERY.md",
}
CANONICAL_REGISTRY_ENVELOPE = {
    "schema_version": "1.0",
    "description": (
        "Ranked-tier registry of repos with discovered latent value. Build-out "
        "follows promotion into this list."
    ),
}
CANONICAL_IDENTITY_LINES = {
    Path("AGENTS.md"): (
        "- **Produce** `editorial-governance` for ORGAN-V",
        "- **Produce** `frontmatter-schema` for ORGAN-V",
        "- **Produce** `essay-templates` for ORGAN-V",
        "- **Consume** `schema` from "
        "[`organvm-iv-taxis/schema-definitions`]"
        "(../../organvm-iv-taxis/schema-definitions/CLAUDE.md)",
    ),
    Path("CHANGELOG.md"): (
        "[Unreleased]: https://github.com/organvm/editorial-standards/compare/v0.1.0...HEAD",
        "[0.1.0]: https://github.com/organvm/editorial-standards/releases/tag/v0.1.0",
    ),
    Path("CLAUDE.md"): (
        "**Org:** `organvm` | **Repo:** `editorial-standards`",
        "- **Produces** → `ORGAN-V`: editorial-governance",
        "- **Produces** → `ORGAN-V`: frontmatter-schema",
        "- **Produces** → `ORGAN-V`: essay-templates",
        "- **Consumes** ← `organvm-iv-taxis/schema-definitions`: schema",
    ),
    Path("DISCOVERY.md"): (
        "# Discovery: organvm/editorial-standards",
    ),
    Path("GEMINI.md"): (
        "**Org:** `organvm` | **Repo:** `editorial-standards`",
        "- **Produces** → `ORGAN-V`: editorial-governance",
        "- **Produces** → `ORGAN-V`: frontmatter-schema",
        "- **Produces** → `ORGAN-V`: essay-templates",
        "- **Consumes** ← `organvm-iv-taxis/schema-definitions`: schema",
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
    Path("AGENTS.md"): ("- **Produce** ", "- **Consume** `schema` from "),
    Path("CHANGELOG.md"): ("[Unreleased]:", "[0.1.0]:"),
    Path("CLAUDE.md"): ("**Org:**", "- **Produces** → ", "- **Consumes** ← "),
    Path("DISCOVERY.md"): ("# Discovery:",),
    Path("GEMINI.md"): ("**Org:**", "- **Produces** → ", "- **Consumes** ← "),
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
REQUIRED_CLAIM_BOUNDARY_POLICIES = {
    Path("docs/reader-mode-documentation.md"): {
        "## Decision": (
            "Audience pages may change order, terminology, examples, assumed "
            "knowledge, and the evidence they foreground. They may not silently "
            "change those facts.",
        ),
    },
    Path("templates/evidence.md"): {
        "## Project limitations": (
            "Audience pages may foreground different rows but may not change an "
            "assertion's statement, class, verification state, freshness, or evidence.",
        ),
    },
}
FORBIDDEN_CLAIM_BOUNDARY_POLICIES = {
    Path("docs/reader-mode-documentation.md"): {
        "## Decision": (
            "They may silently change those facts.",
            "Audience pages may silently change those facts.",
        ),
    },
    Path("templates/evidence.md"): {
        "## Project limitations": (
            "Audience pages may change an assertion's statement, class, "
            "verification state, freshness, or evidence.",
            "They may change an assertion's statement, class, verification "
            "state, freshness, or evidence.",
        ),
    },
}
REQUIRED_CLAIM_BOUNDARY_LINE_SEQUENCES = {
    Path("docs/reader-mode-documentation.md"): {
        "## Decision": (
            "Audience pages may change order, terminology, examples, assumed knowledge, and",
            "the evidence they foreground. They may not silently change those facts.",
        ),
    },
    Path("templates/evidence.md"): {
        "## Project limitations": (
            "field. Audience pages may foreground different rows but may not change an",
            "assertion's statement, class, verification state, freshness, or evidence.",
        ),
    },
}
CANONICAL_SCHEMA_LINKS = {
    Path("README.md"): {
        "## Reader-mode repository documentation": (
            "[canonical project-record example](https://github.com/"
            "organvm-iv-taxis/schema-definitions/blob/"
            f"{CANONICAL_SCHEMA_MERGE_SHA}/examples/project-record-v1-example.yaml)",
            "[project-record schema](https://github.com/"
            "organvm-iv-taxis/schema-definitions/blob/"
            f"{CANONICAL_SCHEMA_MERGE_SHA}/schemas/project-record-v1.schema.json)",
        ),
    },
    Path("docs/reader-mode-documentation.md"): {
        "## Canonical project record": (
            "[`project-record-v1.schema.json`](https://github.com/"
            "organvm-iv-taxis/schema-definitions/blob/"
            f"{CANONICAL_SCHEMA_MERGE_SHA}/schemas/project-record-v1.schema.json)",
            "[`assertion-evidence.v1`](https://github.com/"
            "organvm-iv-taxis/schema-definitions/blob/"
            f"{CANONICAL_SCHEMA_MERGE_SHA}/schemas/assertion-evidence.v1.schema.json)",
        ),
    },
}
CANONICAL_SCHEMA_LINK_LINE_SEQUENCES = {
    Path("README.md"): {
        "## Reader-mode repository documentation": (
            "Start with the [canonical project-record example](https://github.com/"
            "organvm-iv-taxis/schema-definitions/blob/"
            f"{CANONICAL_SCHEMA_MERGE_SHA}/examples/project-record-v1-example.yaml),",
            "[README v2 template](templates/repository-readme-v2.md), and",
            "[project-record schema](https://github.com/"
            "organvm-iv-taxis/schema-definitions/blob/"
            f"{CANONICAL_SCHEMA_MERGE_SHA}/schemas/project-record-v1.schema.json).",
        ),
    },
    Path("docs/reader-mode-documentation.md"): {
        "## Canonical project record": (
            "`project-record.yml` is the shared factual substrate. It is validated by the",
            "canonical",
            "[`project-record-v1.schema.json`](https://github.com/"
            "organvm-iv-taxis/schema-definitions/blob/"
            f"{CANONICAL_SCHEMA_MERGE_SHA}/schemas/project-record-v1.schema.json)",
            "contract. Material claims resolve to separate",
            "[`assertion-evidence.v1`](https://github.com/"
            "organvm-iv-taxis/schema-definitions/blob/"
            f"{CANONICAL_SCHEMA_MERGE_SHA}/schemas/assertion-evidence.v1.schema.json)",
            "records rather than duplicating mutable claim text and verification state.",
        ),
    },
}
REQUIRED_CI_REQUIREMENTS = """PyYAML==6.0.3 \\
    --hash=sha256:7f047e29dcae44602496db43be01ad42fc6f1cc0d8cd6c83d342306c32270196 \\
    --hash=sha256:fc09d0aa354569bc501d4e787133afc08552722d3ab34836a80547331bb5d4a0 \\
    --hash=sha256:9149cad251584d5fb4981be1ecde53a1ca46c891a79788c0df828d2f166bda28 \\
    --hash=sha256:5fdec68f91a0c6739b380c83b951e2c72ac0197ace422360e6d5a959d8d97b2c \\
    --hash=sha256:ba1cc08a7ccde2d2ec775841541641e4548226580ab850948cbfda66a1befcdc \\
    --hash=sha256:8dc52c23056b9ddd46818a57b78404882310fb473d63f17b07d5c40421e47f8e \\
    --hash=sha256:41715c910c881bc081f1e8872880d3c650acf13dfa8214bad49ed4cede7c34ea \\
    --hash=sha256:96b533f0e99f6579b3d4d4995707cf36df9100d67e0c8303a0c55b27b5f99bc5 \\
    --hash=sha256:5fcd34e47f6e0b794d17de1b4ff496c00986e1c83f7ab2fb8fcfe9616ff7477b \\
    --hash=sha256:64386e5e707d03a7e172c0701abfb7e10f0fb753ee1d773128192742712a98fd
"""
REQUIRED_CI_INSTALL_COMMAND = (
    "python3 -m pip install --require-hashes --only-binary=:all: "
    "-r requirements-ci.txt"
)
REQUIRED_LOCAL_CI_PREREQUISITES = ("Python 3.12", "PyYAML")
REQUIRED_LOCAL_CI_COMMANDS = (
    REQUIRED_CI_INSTALL_COMMAND,
    'python3 -c "',
    "for f in glob.glob('schemas/*.yaml'):",
    "python3 scripts/validate_editorial_contracts.py",
    "python3 -m unittest discover -s tests -v",
    'test -f "README.md" && ! test -L "README.md" && echo '
    '"::notice::README.md found" || exit 1',
    'test -f "LICENSE" && ! test -L "LICENSE" && test -s "LICENSE" && '
    'python3 -c "import hashlib,pathlib,sys; p=pathlib.Path(\'LICENSE\'); '
    "sys.exit(0 if hashlib.sha256(p.read_bytes()).hexdigest() == "
    f"'{CANONICAL_LICENSE_SHA256}' else 1)\" && echo "
    '"::notice::License file found" || exit 1',
    'test -f "requirements-ci.txt" && ! test -L "requirements-ci.txt" && echo '
    '"::notice::CI requirements lock found" || exit 1',
    'test -f "docs/reader-mode-documentation.md" && '
    '! test -L "docs/reader-mode-documentation.md" && echo '
    '"::notice::Reader-mode standard found" || exit 1',
    "python3 -m py_compile scripts/validate_editorial_contracts.py tests/test_editorial_contracts.py",
    "git diff --check",
)
REQUIRED_HOSTED_CI_COMMAND_STEPS = (
    (
        "Validate editorial contracts",
        "python3 scripts/validate_editorial_contracts.py",
    ),
    (
        "Run adversarial contract regressions",
        "python3 -m unittest discover -s tests -v",
    ),
)
REQUIRED_HOSTED_CI_RUNNER = "ubuntu-latest"
REQUIRED_HOSTED_CI_NAME = "Editorial Standards CI"
REQUIRED_HOSTED_CI_PERMISSIONS = {"contents": "read"}
REQUIRED_HOSTED_CI_JOB_KEYS = {"runs-on", "steps"}
REQUIRED_HOSTED_CI_STEP_NAMES = (
    "Checkout code",
    "Set up Python",
    "Install dependencies",
    "Validate YAML schemas",
    "Validate editorial contracts",
    "Run adversarial contract regressions",
    "Validate structure",
    "Success",
)
REQUIRED_PULL_REQUEST_BRANCHES = ("main", "master", "develop")
PROTECTED_HOSTED_CI_STEP_KEYS = {"name", "run"}
FORBIDDEN_HOSTED_CI_WORKFLOW_CONTROL_KEYS = {"defaults", "env"}
FORBIDDEN_HOSTED_CI_JOB_CONTROL_KEYS = {
    "continue-on-error",
    "defaults",
    "env",
    "if",
    "strategy",
    "timeout-minutes",
}
FORBIDDEN_HOSTED_CI_STEP_CONTROL_KEYS = {
    "continue-on-error",
    "env",
    "if",
    "shell",
    "timeout-minutes",
    "working-directory",
}
REQUIRED_YAML_VALIDATION_COMMAND = "\n".join(
    (
        'python3 -c "',
        "import yaml, glob, sys",
        "errors = 0",
        "for f in glob.glob('schemas/*.yaml'):",
        "    try:",
        "        data = yaml.safe_load(open(f))",
        "        if not isinstance(data, dict):",
        "            print(f'::error file={f}::Not a valid YAML mapping')",
        "            errors += 1",
        "        else:",
        "            print(f'::notice file={f}::Valid ({len(data)} top-level keys)')",
        "    except Exception as e:",
        "        print(f'::error file={f}::{e}')",
        "        errors += 1",
        "if errors:",
        "    sys.exit(1)",
        "print(f'All {len(glob.glob(\\\"schemas/*.yaml\\\"))} schema files valid')",
        '"',
    )
)
REQUIRED_STRUCTURE_VALIDATION_COMMAND = "\n".join(
    (
        'test -f "README.md" && ! test -L "README.md" && echo '
        '"::notice::README.md found" || exit 1',
        'test -f "LICENSE" && ! test -L "LICENSE" && test -s "LICENSE" && '
        'python3 -c "import hashlib,pathlib,sys; p=pathlib.Path(\'LICENSE\'); '
        "sys.exit(0 if hashlib.sha256(p.read_bytes()).hexdigest() == "
        f"'{CANONICAL_LICENSE_SHA256}' else 1)\" && echo "
        '"::notice::License file found" || exit 1',
        'test -f "requirements-ci.txt" && ! test -L "requirements-ci.txt" && echo '
        '"::notice::CI requirements lock found" || exit 1',
        'test -f "docs/reader-mode-documentation.md" && '
        '! test -L "docs/reader-mode-documentation.md" && echo '
        '"::notice::Reader-mode standard found" || exit 1',
    )
)
REQUIRED_LOCAL_FAIL_FAST_COMMAND = "set -euo pipefail"
REQUIRED_LOCAL_CI_BASH_BLOCKS = (
    (
        REQUIRED_LOCAL_FAIL_FAST_COMMAND,
        "git clone https://github.com/organvm/editorial-standards.git",
        "cd editorial-standards",
    ),
    (REQUIRED_LOCAL_FAIL_FAST_COMMAND, REQUIRED_CI_INSTALL_COMMAND),
    (REQUIRED_LOCAL_FAIL_FAST_COMMAND,)
    + tuple(line.strip() for line in REQUIRED_YAML_VALIDATION_COMMAND.splitlines())
    + (
        "python3 scripts/validate_editorial_contracts.py",
        "python3 -m unittest discover -s tests -v",
    )
    + tuple(line.strip() for line in REQUIRED_STRUCTURE_VALIDATION_COMMAND.splitlines()),
    (
        REQUIRED_LOCAL_FAIL_FAST_COMMAND,
        "python3 -m py_compile scripts/validate_editorial_contracts.py "
        "tests/test_editorial_contracts.py",
        "git diff --check",
    ),
)
REQUIRED_REPOSITORY_STRUCTURE_BLOCK = (
    "editorial-standards/",
    "README.md              # This file",
    "LICENSE                # MIT License",
    "requirements-ci.txt    # Exact hash-verified CI dependency lock",
    "seed.yaml              # Automation contract",
    "CHANGELOG.md           # Release history",
    ".github/",
    "workflows/",
    "ci.yml             # Schema and editorial-contract validation",
    "docs/",
    "reader-mode-documentation.md",
    "adr/",
    "001-initial-architecture.md",
    "002-quality-rubric-design.md",
    "schemas/",
    "category-taxonomy.yaml",
    "frontmatter-schema.yaml",
    "log-schema.yaml",
    "quality-rubric.yaml",
    "reader-mode-rubric.yaml",
    "tag-governance.yaml",
    "scripts/",
    "validate_editorial_contracts.py",
    "templates/",
    "repository-readme-v2.md",
    "audiences/",
    "tests/",
    "test_editorial_contracts.py",
)
REQUIRED_HOSTED_CI_STEPS = (
    {
        "name": "Checkout code",
        "uses": "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
    },
    {
        "name": "Set up Python",
        "uses": "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
        "with": {"python-version": "3.12"},
    },
    {
        "name": "Install dependencies",
        "run": REQUIRED_CI_INSTALL_COMMAND,
    },
    {
        "name": "Validate YAML schemas",
        "run": REQUIRED_YAML_VALIDATION_COMMAND + "\n",
    },
    {
        "name": "Validate editorial contracts",
        "run": "python3 scripts/validate_editorial_contracts.py",
    },
    {
        "name": "Run adversarial contract regressions",
        "run": "python3 -m unittest discover -s tests -v",
    },
    {
        "name": "Validate structure",
        "run": REQUIRED_STRUCTURE_VALIDATION_COMMAND + "\n",
    },
    {
        "name": "Success",
        "run": 'echo "::notice::Editorial Standards CI passed"',
    },
)
CANONICAL_MAPPING_IDENTITIES = {
    Path("seed.yaml"): {
        "org": CANONICAL_ORGANIZATION,
        "repo": CANONICAL_REPOSITORY,
        "produces": CANONICAL_PRODUCTION_EDGES,
        "consumes": [CANONICAL_SCHEMA_DEPENDENCY],
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
    r"(?P<owner>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]*[A-Za-z0-9_-])",
    re.IGNORECASE,
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
REQUIRED_PUBLICATION_BODY_MARKERS = {
    Path("templates/case-study.md"): (
        "# [Title]",
        "## Overview",
        "## Context and Motivation",
        "## Architecture and Implementation",
        "## Results and Metrics",
        "## Lessons Learned",
        "## Relationship to the Organ System",
        "## References",
    ),
    Path("templates/guide.md"): (
        "# [Title]",
        "## Who This Is For",
        "## The Core Idea",
        "## Step-by-Step",
        "## Worked Example",
        "## Common Pitfalls",
        "## Further Reading",
        "## References",
    ),
    Path("templates/meta-system.md"): (
        "# [Title]",
        "## The Problem / Context",
        "## How the System Handles It",
        "## What This Reveals About the Meta-System",
        "## What Doesn't Work Yet",
        "## Implications",
        "## References",
    ),
    Path("templates/methodology.md"): (
        "# [Title]",
        "## The Method in One Paragraph",
        "## Theoretical Basis",
        "## How It Works",
        "## Application in the Organ System",
        "## Limitations and Boundaries",
        "## Comparison to Alternatives",
        "## References",
    ),
    Path("templates/retrospective.md"): (
        "# [Title]",
        "## What Happened",
        "## What Went Well",
        "## What Went Wrong",
        "## What We Learned",
        "## What Changed as a Result",
        "## References",
    ),
    Path("templates/log.md"): (
        "## Précis",
        "## Descriptive Summary",
        "## Analytical Summary",
        "## The Voices",
        "## Workspace Activity",
        "## Behind the Scenes",
    ),
}
READER_RUBRIC_DIMENSIONS = (
    "orientation",
    "technical_depth",
    "conceptual_depth",
    "commercial_relevance",
    "evidence",
    "seo_surface",
    "cross_linking",
)
READER_RUBRIC_ANCHORS = {0, 1, 2, 3, 4}
QUALITY_RUBRIC_DIMENSIONS = (
    "clarity",
    "accuracy",
    "insight_density",
    "cross_referencing",
    "portfolio_relevance",
)
QUALITY_RUBRIC_ANCHORS = {0, 5, 10, 15, 20}
QUALITY_RUBRIC_THRESHOLDS = {
    "publish": 60,
    "flagship_candidate": 80,
    "exemplar": 90,
}
QUALITY_RUBRIC_README_HEADINGS = (
    "### Clarity (20 points)",
    "### Accuracy (20 points)",
    "### Insight Density (20 points)",
    "### Cross-Referencing (20 points)",
    "### Portfolio Relevance (20 points)",
    "### Scoring Guidelines",
)
QUALITY_RUBRIC_README_TITLES = {
    "clarity": "Clarity",
    "accuracy": "Accuracy",
    "insight_density": "Insight Density",
    "cross_referencing": "Cross-Referencing",
    "portfolio_relevance": "Portfolio Relevance",
}
CATEGORY_README_HEADINGS = (
    "### Meta-System Essay",
    "### Case Study",
    "### Retrospective",
    "### Guide",
    "### Methodology Essay",
)
REQUIRED_READER_MODE_DOC_MARKERS = (
    "# Reader-mode repository documentation",
    "## Decision",
    "## Reader questions",
    "## Repository classes",
    "## Required root README sequence",
    "## Canonical layout",
    "## Canonical project record",
    "## Audience edition contracts",
    "### General",
    "### Technical",
    "### Humanities",
    "### Business",
    "### Evaluator",
    "## Evidence rules",
    "## Search-topic clusters",
    "## Audit and conversion priority",
    "## CI contract",
    "## Migration protocol",
)
REQUIRED_ROOT_README_SEQUENCE = (
    "1. project name;",
    "2. one ordinary-language sentence stating what it is, what it does, and why;",
    "3. verified links to the artifact, demo, or inspection path;",
    "4. a short “What am I looking at?” explanation;",
    "5. an audience-route table;",
    "6. project status, primary users, authorship, evidence, and limitations at a glance.",
)
READER_RUBRIC_DOC_SENTENCE = (
    "Score the current public documentation from 0–4 across orientation, "
    "technical depth, conceptual depth, commercial relevance, evidence, SEO "
    "surface, and cross-linking."
)
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
    Path("docs/reader-mode-documentation.md"): (
        ("Reader mode", "First question", "Foreground"),
        ("Class", "Repository function", "Required documentation"),
    ),
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
    (
        Path("docs/reader-mode-documentation.md"),
        ("Reader mode", "First question", "Foreground"),
    ): ("General", "Technical", "Humanities", "Business", "Evaluator"),
    (
        Path("docs/reader-mode-documentation.md"),
        ("Class", "Repository function", "Required documentation"),
    ): (
        "A — Flagship system",
        "B — Major project",
        "C — Supporting component",
        "D — Deployment artifact",
        "E — Research/theory",
        "F — Archive/reference",
    ),
    (Path("templates/repository-readme-v2.md"), ("", "")): (
        "**What it is**",
        "**Problem addressed**",
        "**Current state**",
        "**Primary users**",
        "**What Anthony built**",
        "**Evidence**",
        "**Known limitations**",
    ),
    (
        Path("templates/repository-readme-v2.md"),
        ("I am reading as…", "Start here"),
    ): (
        "A general reader",
        "A software engineer",
        "A humanities scholar",
        "An industry practitioner",
        "A hiring manager or evaluator",
    ),
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
    ): ("[claim-id]",),
    (
        Path("templates/evidence.md"),
        ("ID", "Limitation", "Related assertion"),
    ): ("[limitation-id]",),
}
REQUIRED_READER_TABLE_ROWS = {
    (
        Path("docs/reader-mode-documentation.md"),
        ("Reader mode", "First question", "Foreground"),
    ): (
        (
            "General",
            "What is this, and why should I care?",
            "Recognition, example, current state",
        ),
        (
            "Technical",
            "How is it built, and does it work?",
            "Architecture, execution, tests, boundaries",
        ),
        (
            "Humanities",
            "What ideas and cultural problems does it engage?",
            "Genealogy, form, interpretation, stakes",
        ),
        (
            "Business",
            "What operational problem does this change?",
            "Workflow, integration, risk, evidence",
        ),
        (
            "Evaluator",
            "What did the author specifically do?",
            "Initial state, contribution, proof, limits",
        ),
    ),
    (
        Path("docs/reader-mode-documentation.md"),
        ("Class", "Repository function", "Required documentation"),
    ): (
        (
            "A — Flagship system",
            "Mature project spanning several audiences",
            "README v2, all five audience editions, evidence record, project record",
        ),
        (
            "B — Major project",
            "Substantial project with two or three real audiences",
            "README v2, 2–3 audience editions, evidence record, project record",
        ),
        (
            "C — Supporting component",
            "Library, service, schema, or infrastructure component",
            "Technical README/edition, status, interfaces, evidence, project record",
        ),
        (
            "D — Deployment artifact",
            "Player, compiled build, mirror, or delivery shell",
            "Minimal use-oriented README, canonical-project redirect, status",
        ),
        (
            "E — Research/theory",
            "Scholarship, artistic research, or conceptual corpus",
            "Scholarly-first README/edition, sources, provenance, evidence record, "
            "project record",
        ),
        (
            "F — Archive/reference",
            "Superseded or preserved material",
            "Archive notice, provenance, immutable status, correct redirect",
        ),
    ),
    (
        Path("templates/repository-readme-v2.md"),
        ("I am reading as…", "Start here"),
    ): (
        (
            "A general reader",
            "[Two-minute explanation](docs/audiences/general.md)",
        ),
        (
            "A software engineer",
            "[Technical architecture](docs/audiences/technical.md)",
        ),
        (
            "A humanities scholar",
            "[Conceptual and cultural framing](docs/audiences/humanities.md)",
        ),
        (
            "An industry practitioner",
            "[Operational applications](docs/audiences/business.md)",
        ),
        (
            "A hiring manager or evaluator",
            "[Contribution and evidence](docs/audiences/evaluator.md)",
        ),
    ),
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
    ): (
        (
            "[claim-id]",
            "[Bounded factual claim]",
            "[implemented / partial / proposed / unknown / contradicted]",
            "[external_fact / operator_directive / current_state / inference / "
            "historical_record / ratified_axiom]",
            "[unverified / verified / stale / disputed]",
            "[Inspectable reference and digest]",
            "[fresh / stale / not_applicable, when required]",
        ),
    ),
    (
        Path("templates/evidence.md"),
        ("ID", "Limitation", "Related assertion"),
    ): (
        (
            "[limitation-id]",
            "[Material boundary from project-record.yml]",
            "[Optional assertion_ref]",
        ),
    ),
}
REQUIRED_READER_TABLE_SECTIONS = {
    (
        Path("docs/reader-mode-documentation.md"),
        ("Reader mode", "First question", "Foreground"),
    ): "## Reader questions",
    (
        Path("docs/reader-mode-documentation.md"),
        ("Class", "Repository function", "Required documentation"),
    ): "## Repository classes",
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
SUPPORTED_STRING_FORMAT_PATTERNS = {"YYYY-MM-DD": DATE_PATTERN}
TAG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
TAG_GOVERNANCE_FORMAT = (
    "lowercase, hyphenated (e.g. 'building-in-public', not 'Building In Public')"
)
READING_TIME_PATTERN = r"^\d+ min$"
PUBLICATION_TEMPLATE_SCALAR_PLACEHOLDERS = {
    "title": ("",),
    "date": ("YYYY-MM-DD",),
    "excerpt": ("",),
    "portfolio_relevance": ("",),
    "reading_time": ("",),
    "word_count": (0,),
}
PUBLICATION_TEMPLATE_LIST_PLACEHOLDERS = {
    (Path("templates/case-study.md"), "tags"): (),
    (Path("templates/guide.md"), "tags"): ("guide",),
    (Path("templates/meta-system.md"), "tags"): ("meta-system",),
    (Path("templates/methodology.md"), "tags"): ("methodology",),
    (Path("templates/retrospective.md"), "tags"): ("retrospective",),
}
RELATED_REPOSITORY_PATTERN = (
    r"^(?:organvm|organvm-(?:i|ii|iii|iv|v|vi|vii|viii)-[a-z0-9]+"
    r"(?:-[a-z0-9]+)*|meta-organvm(?:-[a-z0-9]+)*)/"
    r"(?![.]{1,2}$)[A-Za-z0-9._-]{1,100}$"
)


def _load_yaml(path: Path, errors: list[str]) -> Any:
    if not _is_contained_regular_file(path):
        errors.append(f"{path}: required contained regular YAML file is missing")
        return None
    try:
        return yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=_UniqueKeyLoader,
        )
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"{path}: invalid YAML: {exc}")
        return None


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build one JSON object while rejecting ambiguous duplicate keys."""
    mapping: dict[str, Any] = {}
    for key, value in pairs:
        if key in mapping:
            raise ValueError(f"duplicate key {key!r}")
        mapping[key] = value
    return mapping


def _load_json(path: Path, errors: list[str]) -> Any:
    if not _is_contained_regular_file(path):
        errors.append(f"{path}: required contained regular JSON file is missing")
        return None
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return None


def _publication_sections(content: str) -> tuple[list[str], list[str]] | None:
    """Split a publication only when both YAML delimiters are standalone lines."""
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        closing_delimiter = lines.index("---", 1)
    except ValueError:
        return None
    return lines[1:closing_delimiter], lines[closing_delimiter + 1 :]


def _frontmatter(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{path}: cannot read template: {exc}")
        return None

    sections = _publication_sections(content)
    if sections is None:
        errors.append(
            f"{path}: publication frontmatter requires standalone '---' delimiters"
        )
        return None
    try:
        data = yaml.load("\n".join(sections[0]), Loader=_UniqueKeyLoader)
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


def _is_nonnegative_integer(value: Any) -> bool:
    """Return whether a schema bound is safe to apply to a value."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_contained_regular_file(path: Path) -> bool:
    """Reject missing files and tracked symlinks that escape the repository."""
    return path.is_file() and not path.is_symlink()


def _string_keyed_mapping(
    mapping: dict[Any, Any],
    context: str,
    errors: list[str],
) -> dict[str, Any]:
    """Report and remove non-string/empty keys before sorted set operations."""
    invalid_keys = [
        key for key in mapping if not isinstance(key, str) or not key.strip()
    ]
    if invalid_keys:
        errors.append(
            f"{context}: keys must be nonempty strings: "
            f"{sorted(map(repr, invalid_keys))}"
        )
    return {
        key: value
        for key, value in mapping.items()
        if isinstance(key, str) and key.strip()
    }


def _valid_enum(rules: dict[str, Any], expected_type: str) -> list[Any] | None:
    """Return an enum only when its definition is safe to apply to a value."""
    enum = rules.get("enum")
    if (
        not isinstance(enum, list)
        or not enum
        or not all(_matches_type(value, expected_type) for value in enum)
    ):
        return None
    return enum


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
        compiled = re.compile(pattern)
    except re.error as exc:
        errors.append(f"{context}: invalid schema regex pattern: {exc}")
        return None
    # Frontmatter scalar strings are physical single-line values. Reject line
    # breaks before matching so Python's ``$`` anchor cannot accept a trailing
    # newline, while preserving intentional prefix rules such as ``^@``.
    if "\n" in value or "\r" in value:
        return False
    return compiled.search(value) is not None


def _validate_rule_definition(
    schema_path: Path,
    field: str,
    rules: Any,
    errors: list[str],
    *,
    require_description: bool = True,
) -> None:
    """Validate every schema rule, even when no template instantiates the field."""
    context = f"{schema_path}: rules for {field!r}"
    if not isinstance(rules, dict):
        errors.append(f"{context} are not a mapping")
        return
    rules = _string_keyed_mapping(rules, context, errors)

    expected_type = rules.get("type")
    supported_types = {"string", "integer", "list", "object"}
    if not isinstance(expected_type, str) or expected_type not in supported_types:
        errors.append(f"{context} declare unsupported type {expected_type!r}")

    allowed_rule_keys = {"type", "description", "enum"}
    type_rule_keys = {
        "string": {"min_length", "max_length", "pattern", "format"},
        "integer": {"min", "max"},
        "list": {"min_items", "max_items", "item_type", "item_pattern"},
        "object": {"properties", "required_keys"},
    }
    if isinstance(expected_type, str):
        allowed_rule_keys.update(type_rule_keys.get(expected_type, set()))
    unsupported_rule_keys = sorted(set(rules) - allowed_rule_keys)
    if unsupported_rule_keys:
        errors.append(
            f"{context} contain unsupported keys for {expected_type!r}: "
            f"{unsupported_rule_keys}"
        )

    description = rules.get("description")
    if require_description and (
        not isinstance(description, str) or not description.strip()
    ):
        errors.append(f"{context} need a nonempty description")
    elif description is not None and not isinstance(description, str):
        errors.append(f"{context} description must be a string")

    enum = rules.get("enum")
    if enum is not None:
        if not isinstance(enum, list) or not enum:
            errors.append(f"{context} enum must be a nonempty list")
        elif isinstance(expected_type, str) and expected_type in supported_types:
            invalid_values = [
                value for value in enum if not _matches_type(value, expected_type)
            ]
            if invalid_values:
                errors.append(
                    f"{context} enum values do not match type {expected_type!r}: "
                    f"{invalid_values}"
                )
            if len({repr(value) for value in enum}) != len(enum):
                errors.append(f"{context} enum contains duplicate values")

    for lower_key, upper_key in (
        ("min_length", "max_length"),
        ("min_items", "max_items"),
        ("min", "max"),
    ):
        lower = rules.get(lower_key)
        upper = rules.get(upper_key)
        for key, value in ((lower_key, lower), (upper_key, upper)):
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 0
            ):
                errors.append(f"{context} {key} must be a nonnegative integer")
        if (
            isinstance(lower, int)
            and not isinstance(lower, bool)
            and isinstance(upper, int)
            and not isinstance(upper, bool)
            and lower > upper
        ):
            errors.append(f"{context} {lower_key} exceeds {upper_key}")

    for pattern_key in ("pattern", "item_pattern"):
        pattern = rules.get(pattern_key)
        if pattern is None:
            continue
        if not isinstance(pattern, str) or not pattern:
            errors.append(
                f"{context} {pattern_key} must be a nonempty string"
            )
            continue
        try:
            re.compile(pattern)
        except re.error as exc:
            errors.append(f"{context} has invalid {pattern_key}: {exc}")

    schema_format = rules.get("format")
    if schema_format is not None:
        if not isinstance(schema_format, str):
            errors.append(f"{context} format must be a string")
        elif expected_type != "string":
            errors.append(f"{context} format requires type 'string'")
        elif schema_format not in SUPPORTED_STRING_FORMAT_PATTERNS:
            errors.append(f"{context} declare unsupported format {schema_format!r}")
        elif rules.get("pattern") != SUPPORTED_STRING_FORMAT_PATTERNS[schema_format]:
            errors.append(
                f"{context} format {schema_format!r} requires canonical pattern "
                f"{SUPPORTED_STRING_FORMAT_PATTERNS[schema_format]!r}"
            )

    if (
        schema_path
        in {Path("schemas/frontmatter-schema.yaml"), Path("schemas/log-schema.yaml")}
        and field == "date"
        and (
            schema_format != "YYYY-MM-DD"
            or rules.get("pattern") != DATE_PATTERN
        )
    ):
        errors.append(
            f"{context} must retain the canonical YYYY-MM-DD format and "
            f"pattern {DATE_PATTERN!r}"
        )

    if expected_type == "list":
        item_type = rules.get("item_type")
        if not isinstance(item_type, str) or item_type not in supported_types:
            errors.append(f"{context} declare unsupported item_type {item_type!r}")
        if "item_pattern" in rules and item_type != "string":
            errors.append(f"{context} item_pattern requires item_type 'string'")
    elif expected_type == "object":
        properties = rules.get("properties")
        required_keys = rules.get("required_keys", [])
        if not isinstance(properties, dict):
            errors.append(f"{context} properties must be a mapping")
        else:
            valid_properties = _string_keyed_mapping(
                properties,
                f"{context} properties",
                errors,
            )
            for child_field, child_rules in valid_properties.items():
                _validate_rule_definition(
                    schema_path,
                    f"{field}.{child_field}",
                    child_rules,
                    errors,
                    require_description=False,
                )
        if not isinstance(required_keys, list) or not all(
            isinstance(key, str) and bool(key.strip()) for key in required_keys
        ):
            errors.append(
                f"{context} required_keys must be a list of nonempty strings"
            )
        elif isinstance(properties, dict):
            property_keys = {
                key
                for key in properties
                if isinstance(key, str) and key.strip()
            }
            unknown_required = sorted(set(required_keys) - property_keys)
            if unknown_required:
                errors.append(
                    f"{context} required_keys reference unknown properties: "
                    f"{unknown_required}"
                )


def _validate_frontmatter_rule_definition(
    field: str,
    rules: Any,
    errors: list[str],
) -> None:
    _validate_rule_definition(
        Path("schemas/frontmatter-schema.yaml"),
        field,
        rules,
        errors,
    )


def _validate_declared_type(
    value: Any,
    rules: dict[str, Any],
    path: Path,
    field: str,
    errors: list[str],
) -> None:
    """Validate populated template values while preserving explicit placeholders."""
    expected_type = rules.get("type")
    if not isinstance(expected_type, str) or not _matches_type(value, expected_type):
        errors.append(f"{path}: field {field!r} must have type {expected_type!r}")
        return

    if expected_type == "string":
        is_placeholder = value in PUBLICATION_TEMPLATE_SCALAR_PLACEHOLDERS.get(
            field, ()
        )
        if is_placeholder:
            return
        minimum = rules.get("min_length")
        maximum = rules.get("max_length")
        if _is_nonnegative_integer(minimum) and len(value) < minimum:
            errors.append(f"{path}: field {field!r} is shorter than allowed")
        if _is_nonnegative_integer(maximum) and len(value) > maximum:
            errors.append(f"{path}: field {field!r} is longer than allowed")
        enum = _valid_enum(rules, expected_type)
        if enum is not None and value not in enum:
            errors.append(
                f"{path}: field {field!r} has value {value!r} outside the schema enum"
            )
        pattern = rules.get("pattern")
        if pattern:
            matched = _matches_pattern(
                pattern,
                value,
                f"{path}: field {field!r}",
                errors,
            )
            if matched is False:
                errors.append(
                    f"{path}: field {field!r} value {value!r} does not match "
                    "the schema pattern"
                )
    elif expected_type == "integer":
        if value in PUBLICATION_TEMPLATE_SCALAR_PLACEHOLDERS.get(field, ()):
            return
        enum = _valid_enum(rules, expected_type)
        if enum is not None and value not in enum:
            errors.append(
                f"{path}: field {field!r} has value {value!r} outside the schema enum"
            )
        minimum = rules.get("min")
        maximum = rules.get("max")
        if _is_nonnegative_integer(minimum) and value < minimum:
            errors.append(f"{path}: field {field!r} is below the schema minimum")
        if _is_nonnegative_integer(maximum) and value > maximum:
            errors.append(f"{path}: field {field!r} is above the schema maximum")
    elif expected_type == "list":
        placeholder = PUBLICATION_TEMPLATE_LIST_PLACEHOLDERS.get((path, field))
        is_placeholder = placeholder is not None and tuple(value) == placeholder
        enum = _valid_enum(rules, expected_type)
        if not is_placeholder and enum is not None and value not in enum:
            errors.append(
                f"{path}: field {field!r} has value {value!r} outside the schema enum"
            )
        minimum = rules.get("min_items")
        maximum = rules.get("max_items")
        if (
            not is_placeholder
            and _is_nonnegative_integer(minimum)
            and len(value) < minimum
        ):
            errors.append(f"{path}: field {field!r} has too few items")
        if _is_nonnegative_integer(maximum) and len(value) > maximum:
            errors.append(f"{path}: field {field!r} has too many items")
        item_type = rules.get("item_type")
        item_pattern = rules.get("item_pattern")
        valid_item_type = (
            item_type if isinstance(item_type, str) and item_type in {
                "string", "integer", "list", "object"
            } else None
        )
        for index, item in enumerate(value):
            if valid_item_type is not None and not _matches_type(item, valid_item_type):
                errors.append(
                    f"{path}: field {field}[{index}] must have type {item_type!r}"
                )
            elif (
                valid_item_type == "string"
                and isinstance(item, str)
                and item_pattern
            ):
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
        enum = _valid_enum(rules, expected_type)
        if enum is not None and value not in enum:
            errors.append(
                f"{path}: field {field!r} has value {value!r} outside the schema enum"
            )
        properties_value = rules.get("properties", {})
        properties = (
            {
                key: child_rules
                for key, child_rules in properties_value.items()
                if isinstance(key, str) and key.strip()
            }
            if isinstance(properties_value, dict)
            else {}
        )
        required_value = rules.get("required_keys", [])
        required_keys = (
            {
                key
                for key in required_value
                if isinstance(key, str) and key.strip()
            }
            if isinstance(required_value, list)
            else set()
        )
        object_value = _string_keyed_mapping(
            value,
            f"{path}: field {field!r}",
            errors,
        )
        missing_keys = sorted(required_keys - set(object_value))
        unknown_keys = sorted(set(object_value) - set(properties))
        if missing_keys:
            errors.append(
                f"{path}: field {field!r} is missing required keys: {missing_keys}"
            )
        if unknown_keys:
            errors.append(
                f"{path}: field {field!r} has unknown keys: {unknown_keys}"
            )
        for key in sorted(set(object_value) & set(properties)):
            child_rules = properties[key]
            if isinstance(child_rules, dict):
                _validate_declared_type(
                    object_value[key], child_rules, path, f"{field}.{key}", errors
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

    enum = _valid_enum(rules, expected_type)
    if enum is not None and value not in enum:
        errors.append(
            f"templates/log.md: field {field!r} has value {value!r} outside "
            "the schema enum"
        )

    if expected_type == "string":
        minimum = rules.get("min_length")
        maximum = rules.get("max_length")
        if _is_nonnegative_integer(minimum) and len(value) < minimum:
            errors.append(f"templates/log.md: field {field!r} is shorter than allowed")
        if _is_nonnegative_integer(maximum) and len(value) > maximum:
            errors.append(f"templates/log.md: field {field!r} is longer than allowed")
        pattern = rules.get("pattern")
        is_canonical_date_placeholder = (
            field == "date"
            and value == "YYYY-MM-DD"
            and rules.get("format") == "YYYY-MM-DD"
            and pattern == DATE_PATTERN
        )
        if pattern and not is_canonical_date_placeholder:
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
        minimum = rules.get("min")
        maximum = rules.get("max")
        if _is_nonnegative_integer(minimum) and value < minimum:
            errors.append(f"templates/log.md: field {field!r} is below the schema minimum")
        if _is_nonnegative_integer(maximum) and value > maximum:
            errors.append(f"templates/log.md: field {field!r} is above the schema maximum")

    elif expected_type == "list":
        minimum = rules.get("min_items")
        maximum = rules.get("max_items")
        if _is_nonnegative_integer(minimum) and len(value) < minimum:
            errors.append(f"templates/log.md: field {field!r} has too few items")
        if _is_nonnegative_integer(maximum) and len(value) > maximum:
            errors.append(f"templates/log.md: field {field!r} has too many items")
        item_type = rules.get("item_type")
        item_pattern = rules.get("item_pattern")
        valid_item_type = (
            item_type if isinstance(item_type, str) and item_type in {
                "string", "integer", "list", "object"
            } else None
        )
        for index, item in enumerate(value):
            item_field = f"{field}[{index}]"
            if valid_item_type is not None and not _matches_type(item, valid_item_type):
                errors.append(
                    f"templates/log.md: field {item_field!r} must have type "
                    f"{item_type!r}"
                )
            elif (
                valid_item_type == "string"
                and isinstance(item, str)
                and item_pattern
            ):
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
        properties_value = rules.get("properties", {})
        properties = (
            {
                key: child_rules
                for key, child_rules in properties_value.items()
                if isinstance(key, str) and key.strip()
            }
            if isinstance(properties_value, dict)
            else {}
        )
        required_value = rules.get("required_keys", [])
        required_keys = (
            {
                key
                for key in required_value
                if isinstance(key, str) and key.strip()
            }
            if isinstance(required_value, list)
            else set()
        )
        object_value = _string_keyed_mapping(
            value,
            f"templates/log.md: field {field!r}",
            errors,
        )
        missing_keys = sorted(required_keys - set(object_value))
        unknown_keys = sorted(set(object_value) - set(properties))
        if missing_keys:
            errors.append(
                f"templates/log.md: field {field!r} is missing required keys: "
                f"{missing_keys}"
            )
        if unknown_keys:
            errors.append(
                f"templates/log.md: field {field!r} has unknown keys: {unknown_keys}"
            )
        for key in sorted(set(object_value) & set(properties)):
            child_rules = properties[key]
            if isinstance(child_rules, dict):
                _validate_schema_value(
                    object_value[key], child_rules, f"{field}.{key}", errors
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

    definition_error_count = len(errors)
    required = _string_keyed_mapping(
        required,
        "schemas/log-schema.yaml: required_fields",
        errors,
    )
    optional = _string_keyed_mapping(
        optional,
        "schemas/log-schema.yaml: optional_fields",
        errors,
    )
    frontmatter = _string_keyed_mapping(
        frontmatter,
        "templates/log.md: frontmatter",
        errors,
    )
    duplicate_schema_fields = sorted(set(required) & set(optional))
    if duplicate_schema_fields:
        errors.append(
            "schemas/log-schema.yaml: fields cannot be both required and optional: "
            f"{duplicate_schema_fields}"
        )
    for field, rules in (*required.items(), *optional.items()):
        _validate_rule_definition(
            Path("schemas/log-schema.yaml"),
            field,
            rules,
            errors,
        )

    missing = sorted(set(required) - set(frontmatter))
    unknown = sorted(set(frontmatter) - set(required) - set(optional))
    if missing:
        errors.append(f"templates/log.md: missing required log fields: {missing}")
    if unknown:
        errors.append(f"templates/log.md: unknown log fields: {unknown}")

    if len(errors) != definition_error_count:
        return

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


def _is_indented_code_line(line: str) -> bool:
    """Return whether CommonMark treats a leading whitespace run as code."""
    column = 0
    for character in line:
        if character == " ":
            column += 1
        elif character == "\t":
            column += 4 - (column % 4)
        else:
            break
        if column >= 4:
            return True
    return False


RAW_HTML_LITERAL_TAGS = ("pre", "script", "style", "textarea")
RAW_HTML_BLOCK_TAGS = (
    "address",
    "article",
    "aside",
    "base",
    "basefont",
    "blockquote",
    "body",
    "caption",
    "center",
    "col",
    "colgroup",
    "dd",
    "details",
    "dialog",
    "dir",
    "div",
    "dl",
    "dt",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "frame",
    "frameset",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "head",
    "header",
    "hr",
    "html",
    "iframe",
    "legend",
    "li",
    "link",
    "main",
    "menu",
    "menuitem",
    "nav",
    "noframes",
    "ol",
    "optgroup",
    "option",
    "p",
    "param",
    "search",
    "section",
    "summary",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "title",
    "tr",
    "track",
    "ul",
)
RAW_HTML_LITERAL_START = re.compile(
    rf"^[ ]{{0,3}}<(?P<tag>{'|'.join(RAW_HTML_LITERAL_TAGS)})(?=[\s>])",
    re.IGNORECASE,
)
RAW_HTML_BLOCK_START = re.compile(
    rf"^[ ]{{0,3}}</?(?:{'|'.join(RAW_HTML_BLOCK_TAGS)})(?=[\s/>])",
    re.IGNORECASE,
)
RAW_HTML_ATTRIBUTE_NAME = r"[A-Za-z_:][A-Za-z0-9_.:-]*"
RAW_HTML_ATTRIBUTE_VALUE = r'''(?:[^\s"'=<>`]+|'[^']*'|"[^"]*")'''
RAW_HTML_ATTRIBUTE = (
    rf"[ \t]+{RAW_HTML_ATTRIBUTE_NAME}"
    rf"(?:[ \t]*=[ \t]*{RAW_HTML_ATTRIBUTE_VALUE})?"
)
RAW_HTML_GENERIC_START = re.compile(
    rf"^[ ]{{0,3}}(?:"
    rf"<[A-Za-z][A-Za-z0-9-]*(?:{RAW_HTML_ATTRIBUTE})*[ \t]*/?>"
    rf"|</[A-Za-z][A-Za-z0-9-]*[ \t]*>"
    rf")[ \t]*$"
)
RAW_HTML_H1_START = re.compile(r"^[ ]{0,3}<h1(?=[\s/>])", re.IGNORECASE)
COMMONMARK_CONTAINER_PREFIX = re.compile(
    r"^[ ]{0,3}(?:>[ \t]?|(?:[-+*]|\d{1,9}[.)])[ \t]+)"
)


def _is_backslash_escaped(text: str, index: int) -> bool:
    """Return whether the character at index has an odd backslash prefix."""
    backslashes = 0
    index -= 1
    while index >= 0 and text[index] == "\\":
        backslashes += 1
        index -= 1
    return backslashes % 2 == 1


def _find_unescaped_token(text: str, token: str, start: int) -> int:
    """Locate a CommonMark token whose first character is not escaped."""
    position = text.find(token, start)
    while position >= 0 and _is_backslash_escaped(text, position):
        position = text.find(token, position + len(token))
    return position


def _find_backtick_run(text: str, start: int, expected_length: int) -> int:
    """Locate the next backtick run with exactly the requested length."""
    position = text.find("`", start)
    while position >= 0:
        run_end = position + 1
        while run_end < len(text) and text[run_end] == "`":
            run_end += 1
        run_length = run_end - position
        if run_length == expected_length:
            return position
        position = text.find("`", run_end)
    return -1


def _inline_code_ranges(text: str) -> list[tuple[int, int]]:
    """Return closed single-line CommonMark code-span ranges."""
    ranges: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(text):
        start = text.find("`", cursor)
        if start < 0:
            break
        run_end = start + 1
        while run_end < len(text) and text[run_end] == "`":
            run_end += 1
        run_length = run_end - start
        close = _find_backtick_run(text, run_end, run_length)
        if close < 0:
            break
        end = close + run_length
        ranges.append((start, end))
        cursor = end
    return ranges


def _without_inline_code(text: str) -> str:
    """Remove code spans so they cannot supply normative prose contracts."""
    ranges = _inline_code_ranges(text)
    if not ranges:
        return text
    visible: list[str] = []
    cursor = 0
    for start, end in ranges:
        visible.append(text[cursor:start])
        cursor = end
    visible.append(text[cursor:])
    return "".join(visible)


def _inline_html_tag_ranges(text: str) -> list[tuple[int, int]]:
    """Return quote-aware inline HTML tag ranges for contract-token filtering."""
    ranges: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(text):
        start = text.find("<", cursor)
        if start < 0:
            break
        quote: str | None = None
        end = start + 1
        while end < len(text):
            character = text[end]
            if quote is None and character in {'"', "'"}:
                quote = character
            elif quote == character:
                quote = None
            elif quote is None and character == ">":
                end += 1
                break
            end += 1
        ranges.append((start, end))
        cursor = end
    return ranges


def _count_visible_markdown_link(lines: list[str], expected: str) -> int:
    """Count exact rendered links, excluding code, images, escapes, and tags."""
    count = 0
    for line in lines:
        code_ranges = _inline_code_ranges(line)
        html_ranges = _inline_html_tag_ranges(line)
        position = line.find(expected)
        while position >= 0:
            hidden = any(start <= position < end for start, end in code_ranges)
            hidden = hidden or any(
                start <= position < end for start, end in html_ranges
            )
            escaped = _is_backslash_escaped(line, position)
            image = (
                position > 0
                and line[position - 1] == "!"
                and not _is_backslash_escaped(line, position - 1)
            )
            if not hidden and not escaped and not image:
                count += 1
            position = line.find(expected, position + len(expected))
    return count


def _count_exact_line_sequence(lines: list[str], expected: tuple[str, ...]) -> int:
    """Count one contiguous, physically exact rendered Markdown sequence."""
    if not expected or len(expected) > len(lines):
        return 0
    return sum(
        tuple(lines[index : index + len(expected)]) == expected
        for index in range(len(lines) - len(expected) + 1)
    )


def _strip_html_comments_from_line(
    line: str,
    in_comment: bool,
    inline_code_length: int,
) -> tuple[str, bool, int]:
    """Strip comments while scanning each physical-line character at most once."""
    visible: list[str] = []
    cursor = 0
    chunk_start = 0

    if in_comment:
        comment_end = line.find("-->")
        if comment_end < 0:
            return "", True, inline_code_length
        # A carried comment keeps its closing-line suffix in an existing
        # block/inline context.  Prevent that suffix from becoming a new block.
        visible.append("[html comment]")
        cursor = comment_end + 3
        chunk_start = cursor
        in_comment = False

    if inline_code_length:
        code_end = _find_backtick_run(line, cursor, inline_code_length)
        if code_end < 0:
            return "".join(visible), in_comment, inline_code_length
        # A carried code span likewise makes its closing-line suffix paragraph
        # content rather than an independently rendered Markdown block.
        visible.append("[inline code]")
        cursor = code_end + inline_code_length
        chunk_start = cursor
        inline_code_length = 0

    while cursor < len(line):
        if (
            line.startswith("<!--", cursor)
            and not _is_backslash_escaped(line, cursor)
        ):
            block_comment_start = (
                cursor <= 3
                and not line[:cursor].strip()
                and not _is_indented_code_line(line)
            )
            if block_comment_start:
                # A CommonMark block-position HTML comment consumes its entire
                # physical closing line, including any same-line suffix.
                comment_end = line.find("-->", cursor + 4)
                return "", comment_end < 0, inline_code_length

            visible.append(line[chunk_start:cursor])
            comment_end = line.find("-->", cursor + 4)
            if comment_end < 0:
                return "".join(visible), True, inline_code_length
            cursor = comment_end + 3
            chunk_start = cursor
            continue

        if line[cursor] == "`" and not _is_backslash_escaped(line, cursor):
            run_end = cursor + 1
            while run_end < len(line) and line[run_end] == "`":
                run_end += 1
            code_length = run_end - cursor
            possible_fence = (
                cursor <= 3
                and code_length >= 3
                and not line[:cursor].strip()
                and not _is_indented_code_line(line)
            )
            if possible_fence:
                visible.append(line[chunk_start:])
                return "".join(visible), in_comment, inline_code_length

            visible.append(line[chunk_start:cursor])
            code_end = _find_backtick_run(line, run_end, code_length)
            if code_end < 0:
                return "".join(visible), in_comment, code_length
            code_end += code_length
            visible.append(line[cursor:code_end])
            cursor = code_end
            chunk_start = cursor
            continue

        cursor += 1

    visible.append(line[chunk_start:])
    return "".join(visible), in_comment, inline_code_length


def _markdown_contract_view(
    path: Path, content: str, errors: list[str]
) -> tuple[list[str], list[tuple[str | None, str, str]]]:
    """Return rendered contract lines and visible fenced blocks in one pass."""
    rendered: list[str] = []
    fenced_blocks: list[tuple[str | None, str, str]] = []
    fence_character: str | None = None
    fence_length = 0
    fence_info = ""
    fence_owner_h2: str | None = None
    fence_lines: list[str] = []
    current_h2: str | None = None
    in_comment = False
    inline_code_length = 0
    raw_html_end: re.Pattern[str] | None = None
    raw_html_until_blank = False

    for line in content.splitlines():
        if fence_character is not None:
            stripped = line.lstrip()
            fence = None if _is_indented_code_line(line) else re.match(
                r"(`{3,}|~{3,})", stripped
            )
            if (
                fence is not None
                and fence.group(1)[0] == fence_character
                and len(fence.group(1)) >= fence_length
                and not stripped[len(fence.group(1)) :].strip()
            ):
                fenced_blocks.append(
                    (fence_owner_h2, fence_info, "\n".join(fence_lines))
                )
                fence_character = None
                fence_length = 0
                fence_info = ""
                fence_owner_h2 = None
                fence_lines = []
            else:
                fence_lines.append(line)
            continue

        if raw_html_end is not None:
            if raw_html_end.search(line):
                raw_html_end = None
            continue
        if raw_html_until_blank:
            if not line.strip():
                raw_html_until_blank = False
            continue

        line, in_comment, inline_code_length = _strip_html_comments_from_line(
            line,
            in_comment,
            inline_code_length,
        )
        if not line.strip():
            rendered.append(line)
            continue

        if current_h2 == "## Development" and re.search(
            r"<\?|<!\[CDATA\[|<![A-Z]|</?[A-Za-z]",
            _without_inline_code(line),
        ):
            # Preserve a parser-state-aware signal for raw HTML that could
            # render an executable recipe while evading fenced-block inventory.
            fenced_blocks.append((current_h2, "raw-html", line.strip()))

        stripped = line.lstrip()
        if _is_indented_code_line(line):
            fenced_blocks.append((current_h2, "indented", stripped))
            continue
        fence = re.match(r"(`{3,}|~{3,})", stripped)
        if fence is not None:
            candidate = fence.group(1)
            candidate_info = stripped[len(candidate) :].strip()
            if candidate[0] == "`" and "`" in candidate_info:
                # CommonMark forbids backticks in a backtick fence's info
                # string.  Treat this as ordinary rendered text rather than
                # promoting the following lines into a canonical code block.
                rendered.append(line)
                continue
            fence_character = candidate[0]
            fence_length = len(candidate)
            fence_info = candidate_info.lower()
            fence_owner_h2 = current_h2
            continue

        raw_special: tuple[re.Match[str], re.Pattern[str]] | None = None
        for start_pattern, end_pattern in (
            (r"^[ ]{0,3}<\?", re.compile(r"\?>")),
            (r"^[ ]{0,3}<!\[CDATA\[", re.compile(r"\]\]>")),
            (r"^[ ]{0,3}<![A-Z]", re.compile(r">")),
        ):
            start_match = re.match(start_pattern, line)
            if start_match is not None:
                raw_special = (start_match, end_pattern)
                break
        if raw_special is not None:
            start_match, closing = raw_special
            if not closing.search(line, start_match.end()):
                raw_html_end = closing
            continue

        literal_start = RAW_HTML_LITERAL_START.match(line)
        if literal_start is not None:
            tag = literal_start.group("tag")
            closing = re.compile(rf"</{re.escape(tag)}\s*>", re.IGNORECASE)
            if closing.search(line, literal_start.end()):
                continue
            raw_html_end = closing
            continue
        if RAW_HTML_BLOCK_START.match(line) or RAW_HTML_GENERIC_START.match(line):
            if RAW_HTML_H1_START.match(line):
                # Raw HTML headings render as document titles even though the
                # rest of a raw block is intentionally excluded from prose
                # contract matching.
                rendered.append(line)
            raw_html_until_blank = True
            continue

        rendered.append(line)
        if re.fullmatch(r"## [^#].*", line):
            current_h2 = line

    if fence_character is not None:
        errors.append(f"{path}: unclosed Markdown code fence")
    if in_comment:
        errors.append(f"{path}: unclosed HTML comment")
    if inline_code_length:
        errors.append(f"{path}: unclosed Markdown inline-code span")
    return rendered, fenced_blocks


def _rendered_markdown_lines(
    path: Path, content: str, errors: list[str]
) -> list[str]:
    """Remove rendered-invisible blocks from Markdown contracts."""
    return _markdown_contract_view(path, content, errors)[0]


def _exact_rendered_section(
    path: Path,
    lines: list[str],
    heading: str,
    errors: list[str],
) -> list[str] | None:
    """Return one exact rendered H2 section without substring promotion."""
    occurrences = [index for index, line in enumerate(lines) if line == heading]
    if len(occurrences) != 1:
        errors.append(
            f"{path}: heading {heading!r} must appear exactly once; "
            f"found {len(occurrences)}"
        )
        return None
    start = occurrences[0] + 1
    end = next(
        (
            index
            for index in range(start, len(lines))
            if re.fullmatch(r"## [^#].*", lines[index])
        ),
        len(lines),
    )
    return lines[start:end]


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
        empty_labels = [
            row[0] for row in data_rows if any(not cell for cell in row[1:])
        ]
        if empty_labels:
            errors.append(
                f"{path}: required table {label!r} has empty values for "
                f"{empty_labels}"
            )

    required_rows = REQUIRED_READER_TABLE_ROWS.get((path, header))
    if required_rows is not None:
        actual_rows = tuple(tuple(row) for row in data_rows)
        if actual_rows != required_rows:
            errors.append(
                f"{path}: required table {label!r} canonical rows mismatch: "
                f"expected={list(required_rows)}, actual={list(actual_rows)}"
            )


def _rendered_level_one_headings(lines: list[str]) -> list[str]:
    """Return CommonMark ATX and setext level-one headings from visible lines."""
    normalized_lines: list[str] = []
    for line in lines:
        normalized = line
        while (prefix := COMMONMARK_CONTAINER_PREFIX.match(normalized)) is not None:
            normalized = normalized[prefix.end() :]
        normalized_lines.append(normalized)

    headings: list[str] = []
    for index, line in enumerate(normalized_lines):
        if re.fullmatch(r"[ ]{0,3}#(?:[ \t]+.*)?", line):
            headings.append(line)
        if RAW_HTML_H1_START.match(line):
            headings.append(line)
        if (
            index > 0
            and normalized_lines[index - 1].strip()
            and re.fullmatch(r"[ ]{0,3}=+[ \t]*", line)
        ):
            headings.append(
                f"{normalized_lines[index - 1].strip()}\n{line.strip()}"
            )
    return headings


def _validate_reader_structure(
    path: Path,
    lines: list[str],
    markers: tuple[str, ...],
    errors: list[str],
) -> None:
    """Require reader markers exactly once and in their declared sequence."""
    if markers and re.fullmatch(r"# [^#].*", markers[0]):
        canonical_h1 = markers[0]
        first_nonblank = next((line for line in lines if line.strip()), None)
        rendered_h1s = _rendered_level_one_headings(lines)
        if first_nonblank != canonical_h1 or rendered_h1s != [canonical_h1]:
            errors.append(
                f"{path}: canonical level-one heading must be the sole document "
                f"title and first rendered content: expected={canonical_h1!r}, "
                f"actual={rendered_h1s!r}"
            )

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


def _validate_publication_body(
    path: Path, content: str, errors: list[str]
) -> None:
    sections = _publication_sections(content)
    if sections is None:
        return
    body_lines = _rendered_markdown_lines(path, "\n".join(sections[1]), errors)
    _validate_reader_structure(
        path,
        body_lines,
        REQUIRED_PUBLICATION_BODY_MARKERS.get(path, ()),
        errors,
    )


def _validate_reader_mode_documentation(root: Path, errors: list[str]) -> None:
    relative_path = Path("docs/reader-mode-documentation.md")
    path = root / relative_path
    if not _is_contained_regular_file(path):
        errors.append(
            f"{relative_path}: required contained regular reader-mode standard missing"
        )
        return
    content = path.read_text(encoding="utf-8")
    rendered_lines = _rendered_markdown_lines(relative_path, content, errors)
    _validate_reader_structure(
        relative_path,
        rendered_lines,
        REQUIRED_READER_MODE_DOC_MARKERS,
        errors,
    )
    sequence_heading = "## Required root README sequence"
    try:
        sequence_start = rendered_lines.index(sequence_heading)
    except ValueError:
        sequence_start = -1
    if sequence_start >= 0:
        sequence_end = next(
            (
                index
                for index in range(sequence_start + 1, len(rendered_lines))
                if rendered_lines[index].startswith("## ")
            ),
            len(rendered_lines),
        )
        actual_sequence = tuple(
            line
            for line in rendered_lines[sequence_start + 1 : sequence_end]
            if re.fullmatch(r"\d+\.\s+.+", line)
        )
        if actual_sequence != REQUIRED_ROOT_README_SEQUENCE:
            errors.append(
                f"{relative_path}: root README sequence mismatch: "
                f"expected={list(REQUIRED_ROOT_README_SEQUENCE)}, "
                f"actual={list(actual_sequence)}"
            )
    normalized = re.sub(r"\s+", " ", "\n".join(rendered_lines)).strip()
    if READER_RUBRIC_DOC_SENTENCE not in normalized:
        errors.append(
            f"{relative_path}: reader rubric dimension sentence is missing or stale"
        )
    rubric_link = (
        "[`schemas/reader-mode-rubric.yaml`](../schemas/reader-mode-rubric.yaml)"
    )
    if rendered_lines.count(f"{rubric_link}.") != 1:
        errors.append(
            f"{relative_path}: canonical reader rubric link must appear exactly once"
        )


def _validate_claim_boundary_policies(root: Path, errors: list[str]) -> None:
    """Bind the minimal no-silent-factual-drift policy across reader routes."""
    for relative_path, section_policies in REQUIRED_CLAIM_BOUNDARY_POLICIES.items():
        path = root / relative_path
        if not _is_contained_regular_file(path):
            errors.append(f"{relative_path}: required claim-boundary policy is missing")
            continue
        rendered = _rendered_markdown_lines(
            relative_path,
            path.read_text(encoding="utf-8"),
            errors,
        )
        prose_lines = [_without_inline_code(line) for line in rendered]
        whole_document = re.sub(r"\s+", " ", "\n".join(prose_lines)).strip()
        for heading, policies in section_policies.items():
            rendered_section = _exact_rendered_section(
                relative_path,
                rendered,
                heading,
                errors,
            )
            section = [
                _without_inline_code(line) for line in (rendered_section or ())
            ]
            normalized_section = re.sub(
                r"\s+", " ", "\n".join(section or ())
            ).strip()
            expected_lines = REQUIRED_CLAIM_BOUNDARY_LINE_SEQUENCES[
                relative_path
            ][heading]
            exact_sequences = _count_exact_line_sequence(
                rendered_section or [], expected_lines
            )
            if exact_sequences != 1:
                errors.append(
                    f"{relative_path}: canonical claim-boundary lines must "
                    f"appear exactly once in {heading!r}; found {exact_sequences}"
                )
            for policy in policies:
                section_occurrences = normalized_section.count(policy)
                document_occurrences = whole_document.count(policy)
                if section_occurrences != 1 or document_occurrences != 1:
                    errors.append(
                        f"{relative_path}: canonical claim-boundary policy must "
                        f"appear exactly once in {heading!r}; found "
                        f"section={section_occurrences}, "
                        f"document={document_occurrences}: {policy!r}"
                    )
            for forbidden in FORBIDDEN_CLAIM_BOUNDARY_POLICIES.get(
                relative_path, {}
            ).get(heading, ()):
                if forbidden in normalized_section:
                    errors.append(
                        f"{relative_path}: contradictory claim-boundary policy "
                        f"appears in {heading!r}: {forbidden!r}"
                    )


def _validate_canonical_schema_links(root: Path, errors: list[str]) -> None:
    """Pin normative schema links to the reviewed foundation merge."""
    schema_url_pattern = re.compile(
        r"https://github\.com/[^/\s)]+/schema-definitions/blob/[^\s)]+"
    )
    for relative_path, section_links in CANONICAL_SCHEMA_LINKS.items():
        path = root / relative_path
        if not _is_contained_regular_file(path):
            continue
        rendered_lines = _rendered_markdown_lines(
            relative_path,
            path.read_text(encoding="utf-8"),
            errors,
        )
        expected_urls: list[str] = []
        for heading, expected_links in section_links.items():
            section = _exact_rendered_section(
                relative_path,
                rendered_lines,
                heading,
                errors,
            )
            expected_lines = CANONICAL_SCHEMA_LINK_LINE_SEQUENCES[
                relative_path
            ][heading]
            exact_sequences = _count_exact_line_sequence(
                section or [], expected_lines
            )
            if exact_sequences != 1:
                errors.append(
                    f"{relative_path}: canonical schema link prose must appear "
                    f"exactly once in {heading!r}; found {exact_sequences}"
                )
            for expected_link in expected_links:
                occurrences = _count_visible_markdown_link(
                    section or [], expected_link
                )
                if occurrences != 1:
                    errors.append(
                        f"{relative_path}: canonical schema link must appear "
                        f"exactly once in {heading!r}; found {occurrences}: "
                        f"{expected_link!r}"
                    )
                expected_urls.extend(schema_url_pattern.findall(expected_link))
        rendered = "\n".join(rendered_lines)
        actual_urls = tuple(schema_url_pattern.findall(rendered))
        if actual_urls != tuple(expected_urls):
            errors.append(
                f"{relative_path}: canonical schema URL inventory mismatch: "
                f"expected={expected_urls}, actual={list(actual_urls)}"
            )


def _validate_readme(
    root: Path, required_map: dict[str, Any], errors: list[str]
) -> None:
    readme_path = root / "README.md"
    if not _is_contained_regular_file(readme_path):
        errors.append("README.md: required contained regular file is missing")
        return
    raw_readme = readme_path.read_text(encoding="utf-8")
    raw_lines = raw_readme.splitlines()
    raw_development_headings = [
        index for index, line in enumerate(raw_lines) if line == "## Development"
    ]
    if len(raw_development_headings) != 1:
        errors.append(
            "README.md: raw Development heading must appear exactly once so "
            "hidden executable blocks cannot redirect the local recipe"
        )
    else:
        raw_start = raw_development_headings[0] + 1
        raw_end = next(
            (
                index
                for index in range(raw_start, len(raw_lines))
                if re.fullmatch(r"## [^#].*", raw_lines[index])
            ),
            len(raw_lines),
        )
        fence_character: str | None = None
        fence_length = 0
        for line in raw_lines[raw_start:raw_end]:
            stripped = line.lstrip()
            fence = re.match(r"(`{3,}|~{3,})", stripped)
            if fence_character is not None:
                if (
                    fence is not None
                    and fence.group(1)[0] == fence_character
                    and len(fence.group(1)) >= fence_length
                    and not stripped[len(fence.group(1)) :].strip()
                ):
                    fence_character = None
                    fence_length = 0
                continue
            if fence is not None:
                candidate = fence.group(1)
                candidate_info = stripped[len(candidate) :]
                if not (candidate[0] == "`" and "`" in candidate_info):
                    fence_character = candidate[0]
                    fence_length = len(candidate)
                    continue
            if re.search(r"<!--|<\?|<!\[CDATA\[|<![A-Z]|</?[A-Za-z]", line):
                errors.append(
                    "README.md: raw HTML is forbidden in Development so it "
                    "cannot supply an unclassified executable recipe"
                )
                break
    rendered_lines, fenced_blocks = _markdown_contract_view(
        Path("README.md"), raw_readme, errors
    )
    rendered_readme = "\n".join(rendered_lines)
    required_fields = set(required_map)
    development_lines = _exact_rendered_section(
        Path("README.md"), rendered_lines, "## Development", errors
    )
    rendered_development_section = "\n".join(development_lines or ())
    bash_blocks = [
        body
        for owner_h2, info, body in fenced_blocks
        if owner_h2 == "## Development" and info.partition(" ")[0] == "bash"
    ]
    development_executable_blocks = tuple(
        (info, executable_lines)
        for owner_h2, info, body in fenced_blocks
        if owner_h2 == "## Development"
        if (
            executable_lines := tuple(
                line.strip()
                for line in body.splitlines()
                if line.strip()
                and (
                    info.partition(" ")[0] != "bash"
                    or not line.lstrip().startswith("#")
                )
            )
        )
    )
    executable_bash_lines = [
        line.strip()
        for block in bash_blocks
        for line in block.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    executable_bash_blocks = tuple(
        executable_lines
        for block in bash_blocks
        if (
            executable_lines := tuple(
                line.strip()
                for line in block.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            )
        )
    )
    expected_development_blocks = tuple(
        ("bash", block) for block in REQUIRED_LOCAL_CI_BASH_BLOCKS
    ) + (("", REQUIRED_REPOSITORY_STRUCTURE_BLOCK),)
    if (
        executable_bash_blocks != REQUIRED_LOCAL_CI_BASH_BLOCKS
        or development_executable_blocks != expected_development_blocks
    ):
        errors.append(
            "README.md: Development bash recipe must match the exact canonical "
            "executable blocks and order"
        )
    for prerequisite in REQUIRED_LOCAL_CI_PREREQUISITES:
        if prerequisite not in rendered_development_section:
            errors.append(
                "README.md: missing local CI reproduction prerequisite: "
                f"{prerequisite}"
            )
    command_positions: list[int] = []
    complete_command_sequence = True
    for command in REQUIRED_LOCAL_CI_COMMANDS:
        positions = [
            index
            for index, executable_line in enumerate(executable_bash_lines)
            if executable_line == command
        ]
        if not positions:
            errors.append(
                f"README.md: missing local CI reproduction command: {command}"
            )
            complete_command_sequence = False
        elif len(positions) > 1:
            errors.append(
                f"README.md: duplicate local CI reproduction command: {command}"
            )
            complete_command_sequence = False
        else:
            command_positions.append(positions[0])
    if complete_command_sequence and command_positions != sorted(command_positions):
        errors.append(
            "README.md: local CI reproduction commands must follow hosted CI order"
        )

    workflow_path = root / ".github/workflows/ci.yml"
    try:
        workflow_source = workflow_path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f".github/workflows/ci.yml: cannot inspect source keys: {exc}")
        workflow_source = ""
    source_top_level_keys = tuple(
        match.group(1)
        for line in workflow_source.splitlines()
        if (match := re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(?:\s+.*)?", line))
    )
    expected_source_top_level_keys = ("name", "on", "permissions", "jobs")
    if source_top_level_keys != expected_source_top_level_keys:
        errors.append(
            ".github/workflows/ci.yml: source top-level keys/order must be "
            f"exactly {list(expected_source_top_level_keys)}; found "
            f"{list(source_top_level_keys)}"
        )

    workflow = _load_yaml(workflow_path, errors)
    if isinstance(workflow, dict):
        trigger_key: str | bool = True if True in workflow else "on"
        expected_workflow_keys = {"name", trigger_key, "permissions", "jobs"}
        if set(workflow) != expected_workflow_keys:
            errors.append(
                ".github/workflows/ci.yml: workflow mapping must contain exactly "
                f"{sorted(map(str, expected_workflow_keys))}; found "
                f"{sorted(map(str, workflow))}"
            )
        if workflow.get("name") != REQUIRED_HOSTED_CI_NAME:
            errors.append(
                ".github/workflows/ci.yml: workflow name must be exactly "
                f"{REQUIRED_HOSTED_CI_NAME!r}"
            )
        if workflow.get("permissions") != REQUIRED_HOSTED_CI_PERMISSIONS:
            errors.append(
                ".github/workflows/ci.yml: workflow permissions must be exactly "
                f"{REQUIRED_HOSTED_CI_PERMISSIONS!r}"
            )
        workflow_controls = sorted(
            FORBIDDEN_HOSTED_CI_WORKFLOW_CONTROL_KEYS & set(workflow)
        )
        if workflow_controls:
            errors.append(
                ".github/workflows/ci.yml: workflow-level execution controls "
                f"are forbidden for protected checks: {workflow_controls}"
            )
        workflow_triggers = workflow.get("on")
        if workflow_triggers is None and True in workflow:
            # PyYAML's YAML 1.1 resolver parses the plain key ``on`` as True.
            workflow_triggers = workflow[True]
        expected_workflow_triggers = {
            "push": {"branches": list(REQUIRED_PULL_REQUEST_BRANCHES)},
            "pull_request": {"branches": list(REQUIRED_PULL_REQUEST_BRANCHES)},
            "workflow_dispatch": None,
        }
        if workflow_triggers != expected_workflow_triggers:
            errors.append(
                ".github/workflows/ci.yml: workflow triggers must be exactly "
                f"{expected_workflow_triggers!r}; found {workflow_triggers!r}"
            )
    jobs = workflow.get("jobs") if isinstance(workflow, dict) else None
    if isinstance(jobs, dict) and set(jobs) != {"validate"}:
        errors.append(
            ".github/workflows/ci.yml: job inventory must contain exactly "
            "['validate']"
        )
    validate_job = jobs.get("validate") if isinstance(jobs, dict) else None
    if isinstance(validate_job, dict):
        job_controls = sorted(
            FORBIDDEN_HOSTED_CI_JOB_CONTROL_KEYS & set(validate_job)
        )
        if job_controls:
            errors.append(
                ".github/workflows/ci.yml: validate job execution controls "
                f"are forbidden: {job_controls}"
            )
        if validate_job.get("runs-on") != REQUIRED_HOSTED_CI_RUNNER:
            errors.append(
                ".github/workflows/ci.yml: validate job runner must be exactly "
                f"{REQUIRED_HOSTED_CI_RUNNER!r}"
            )
        if set(validate_job) != REQUIRED_HOSTED_CI_JOB_KEYS:
            errors.append(
                ".github/workflows/ci.yml: validate job mapping must contain "
                f"exactly {sorted(REQUIRED_HOSTED_CI_JOB_KEYS)}; found "
                f"{sorted(map(str, validate_job))}"
            )
    workflow_steps = (
        validate_job.get("steps") if isinstance(validate_job, dict) else None
    )
    if not isinstance(workflow_steps, list):
        workflow_steps = []
    actual_step_names = tuple(
        step.get("name") if isinstance(step, dict) else None
        for step in workflow_steps
    )
    if actual_step_names != REQUIRED_HOSTED_CI_STEP_NAMES:
        errors.append(
            ".github/workflows/ci.yml: validate job step inventory/order mismatch: "
            f"expected={list(REQUIRED_HOSTED_CI_STEP_NAMES)}, "
            f"actual={list(actual_step_names)}"
        )
    if workflow_steps != list(REQUIRED_HOSTED_CI_STEPS):
        errors.append(
            ".github/workflows/ci.yml: validate job steps must match the exact "
            "canonical mappings, action pins, configuration, and commands"
        )
    for index, step in enumerate(workflow_steps):
        if not isinstance(step, dict):
            continue
        step_controls = sorted(
            FORBIDDEN_HOSTED_CI_STEP_CONTROL_KEYS & set(step)
        )
        if step_controls:
            errors.append(
                ".github/workflows/ci.yml: validate job step "
                f"{index + 1} execution controls are forbidden: {step_controls}"
            )

    hosted_command_positions: list[int] = []
    hosted_command_sequence_complete = True
    for step_name, expected_command in REQUIRED_HOSTED_CI_COMMAND_STEPS:
        matching_steps = [
            (index, step)
            for index, step in enumerate(workflow_steps)
            if isinstance(step, dict) and step.get("name") == step_name
        ]
        if len(matching_steps) != 1:
            errors.append(
                ".github/workflows/ci.yml: hosted CI step "
                f"{step_name!r} must appear exactly once"
            )
            hosted_command_sequence_complete = False
            continue
        index, step = matching_steps[0]
        step_keys = set(step)
        if step_keys != PROTECTED_HOSTED_CI_STEP_KEYS:
            errors.append(
                ".github/workflows/ci.yml: hosted CI step "
                f"{step_name!r} must contain only canonical keys "
                f"{sorted(PROTECTED_HOSTED_CI_STEP_KEYS)}; "
                f"found {sorted(map(str, step_keys))}"
            )
        command_invocations = [
            candidate
            for candidate in workflow_steps
            if isinstance(candidate, dict)
            and candidate.get("run") == expected_command
        ]
        if len(command_invocations) != 1:
            errors.append(
                ".github/workflows/ci.yml: hosted CI command "
                f"{expected_command!r} must be invoked exactly once"
            )
        if step.get("run") != expected_command:
            errors.append(
                ".github/workflows/ci.yml: hosted CI step "
                f"{step_name!r} must run exactly {expected_command!r}"
            )
        hosted_command_positions.append(index)
    if (
        hosted_command_sequence_complete
        and hosted_command_positions != sorted(hosted_command_positions)
    ):
        errors.append(
            ".github/workflows/ci.yml: hosted contract checks must remain in "
            "canonical order"
        )

    hosted_yaml_commands = [
        step.get("run")
        for step in workflow_steps
        if isinstance(step, dict) and step.get("name") == "Validate YAML schemas"
    ]
    if len(hosted_yaml_commands) != 1 or not isinstance(hosted_yaml_commands[0], str):
        errors.append(
            ".github/workflows/ci.yml: expected exactly one multiline YAML "
            "validation command"
        )
    else:
        hosted_yaml_command = hosted_yaml_commands[0].strip("\n")
        if hosted_yaml_command != REQUIRED_YAML_VALIDATION_COMMAND:
            errors.append(
                ".github/workflows/ci.yml: multiline YAML validation command "
                "drifted from the canonical mapping check"
            )
        local_yaml_prefix = (
            f"{REQUIRED_LOCAL_FAIL_FAST_COMMAND}\n"
            f"{REQUIRED_YAML_VALIDATION_COMMAND}"
        )
        exact_hosted_prefixes = [
            block
            for block in bash_blocks
            if block == local_yaml_prefix
            or block.startswith(f"{local_yaml_prefix}\n")
        ]
        if len(exact_hosted_prefixes) != 1:
            errors.append(
                "README.md: local multiline YAML command must exactly reproduce "
                "hosted CI"
            )
    hosted_structure_commands = [
        step.get("run")
        for step in workflow_steps
        if isinstance(step, dict) and step.get("name") == "Validate structure"
    ]
    if (
        len(hosted_structure_commands) != 1
        or not isinstance(hosted_structure_commands[0], str)
        or hosted_structure_commands[0].strip("\n")
        != REQUIRED_STRUCTURE_VALIDATION_COMMAND
    ):
        errors.append(
            ".github/workflows/ci.yml: structure validation command must fail "
            "closed for every required file"
        )
    obsolete_field_guidance = (
        "Must match the `slug` frontmatter field",
        "No markdown in the abstract field",
        "The `organs_referenced` array",
    )
    for phrase in obsolete_field_guidance:
        if phrase in rendered_readme:
            errors.append(f"README.md: obsolete frontmatter guidance: {phrase}")

    expected_count_phrases = (
        f"the {len(required_fields)} required metadata fields",
        f"All {len(required_fields)} required fields",
    )
    for phrase in expected_count_phrases:
        if phrase not in rendered_readme:
            errors.append(f"README.md: missing schema-derived field count: {phrase}")

    category_lines = _exact_rendered_section(
        Path("README.md"), rendered_lines, "## Essay Categories", errors
    )
    if category_lines is not None:
        _validate_reader_structure(
            Path("README.md"),
            category_lines,
            CATEGORY_README_HEADINGS,
            errors,
        )

    quality_lines = _exact_rendered_section(
        Path("README.md"), rendered_lines, "## Quality Rubric", errors
    )
    if quality_lines is not None:
        _validate_reader_structure(
            Path("README.md"),
            quality_lines,
            QUALITY_RUBRIC_README_HEADINGS,
            errors,
        )
        _validate_quality_rubric_readme(root, rendered_readme, errors)

    section_lines = _exact_rendered_section(
        Path("README.md"), rendered_lines, "## Frontmatter Schema", errors
    )
    if section_lines is None:
        return

    lines = section_lines
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
        actual_rule_keys = {
            key for key in rules if isinstance(key, str) and key.strip()
        } - {"description"}
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
            continue
        if schema.get("schema_version") != "1.0":
            errors.append(f"{relative_path}: schema_version must be '1.0'")
        description = schema.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{relative_path}: schema needs a nonempty description")


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


def _validate_category_taxonomy(
    root: Path, frontmatter_category_rules: Any, errors: list[str]
) -> None:
    taxonomy_path = Path("schemas/category-taxonomy.yaml")
    taxonomy = _load_yaml(root / taxonomy_path, errors)
    if not isinstance(taxonomy, dict) or not isinstance(
        frontmatter_category_rules, dict
    ):
        errors.append(
            "category taxonomy/frontmatter mismatch: both contracts must be mappings"
        )
        return
    categories = taxonomy.get("categories")
    enum = frontmatter_category_rules.get("enum")
    if not isinstance(categories, dict) or not isinstance(enum, list) or not all(
        isinstance(category, str) for category in enum
    ):
        errors.append(
            "category taxonomy/frontmatter mismatch: categories and enum must be "
            "structured collections"
        )
        return
    categories = _string_keyed_mapping(
        categories,
        "schemas/category-taxonomy.yaml: categories",
        errors,
    )

    taxonomy_categories = set(categories)
    frontmatter_categories = set(enum)
    template_categories = set(ESSAY_CATEGORIES.values())
    if (
        len(enum) != len(frontmatter_categories)
        or taxonomy_categories != frontmatter_categories
        or template_categories != frontmatter_categories
    ):
        errors.append(
            "category taxonomy/frontmatter/template mismatch: "
            f"taxonomy={sorted(taxonomy_categories)}, "
            f"frontmatter={sorted(frontmatter_categories)}, "
            f"templates={sorted(template_categories)}"
        )

    for category, details in categories.items():
        if not isinstance(details, dict):
            errors.append(
                f"schemas/category-taxonomy.yaml: category {category!r} "
                "must be a mapping"
            )
            continue
        description = details.get("description")
        examples = details.get("examples")
        typical_count = details.get("typical_count")
        if not isinstance(description, str) or not description.strip():
            errors.append(
                f"schemas/category-taxonomy.yaml: category {category!r} "
                "needs a description"
            )
        if not isinstance(examples, list) or not examples or not all(
            isinstance(example, str) and example.strip() for example in examples
        ):
            errors.append(
                f"schemas/category-taxonomy.yaml: category {category!r} "
                "needs nonempty examples"
            )
        if (
            not isinstance(typical_count, int)
            or isinstance(typical_count, bool)
            or typical_count < 0
        ):
            errors.append(
                f"schemas/category-taxonomy.yaml: category {category!r} "
                "needs a nonnegative integer typical_count"
            )

    deprecated = taxonomy.get("deprecated_categories")
    if not isinstance(deprecated, dict) or any(
        not isinstance(source, str)
        or not isinstance(target, str)
        or source in frontmatter_categories
        or target not in frontmatter_categories
        for source, target in (deprecated.items() if isinstance(deprecated, dict) else ())
    ):
        errors.append(
            "schemas/category-taxonomy.yaml: deprecated categories must map "
            "noncanonical names to canonical categories"
        )


def _validate_reader_rubric(root: Path, errors: list[str]) -> None:
    rubric_path = Path("schemas/reader-mode-rubric.yaml")
    rubric = _load_yaml(root / rubric_path, errors)
    if not isinstance(rubric, dict):
        errors.append(f"{rubric_path}: rubric must be a YAML mapping")
        return

    scale = rubric.get("scale")
    expected_scale = {"minimum": 0, "maximum": 4}
    scale_values_are_integers = isinstance(scale, dict) and all(
        type(value) is int for value in scale.values()
    )
    if not scale_values_are_integers or scale != expected_scale:
        errors.append(
            f"{rubric_path}: expected scoring scale {expected_scale}, found {scale!r}"
        )

    dimensions = rubric.get("dimensions")
    if not isinstance(dimensions, dict):
        errors.append(f"{rubric_path}: dimensions must be a YAML mapping")
        return
    dimensions = _string_keyed_mapping(
        dimensions,
        f"{rubric_path}: dimensions",
        errors,
    )
    actual_dimensions = set(dimensions)
    expected_dimensions = set(READER_RUBRIC_DIMENSIONS)
    if actual_dimensions != expected_dimensions:
        errors.append(
            f"{rubric_path}: dimension set mismatch: "
            f"expected={list(READER_RUBRIC_DIMENSIONS)}, "
            f"actual={sorted(actual_dimensions)}"
        )

    for dimension in sorted(expected_dimensions & actual_dimensions):
        details = dimensions[dimension]
        if not isinstance(details, dict):
            errors.append(f"{rubric_path}: dimension {dimension!r} must be a mapping")
            continue
        question = details.get("question")
        if not isinstance(question, str) or not question.strip():
            errors.append(
                f"{rubric_path}: dimension {dimension!r} needs a question"
            )
        anchors = details.get("anchors")
        if not isinstance(anchors, dict):
            errors.append(
                f"{rubric_path}: dimension {dimension!r} anchors must be a mapping"
            )
            continue
        anchor_keys_are_integers = all(type(anchor) is int for anchor in anchors)
        if not anchor_keys_are_integers:
            errors.append(
                f"{rubric_path}: dimension {dimension!r} anchor keys must be "
                "integers (booleans are invalid)"
            )
        elif set(anchors) != READER_RUBRIC_ANCHORS:
            errors.append(
                f"{rubric_path}: dimension {dimension!r} anchor set mismatch: "
                f"expected={sorted(READER_RUBRIC_ANCHORS)}, "
                f"actual={sorted(anchors, key=str)}"
            )
        empty_anchors = [
            anchor
            for anchor, description in anchors.items()
            if not isinstance(description, str) or not description.strip()
        ]
        if empty_anchors:
            errors.append(
                f"{rubric_path}: dimension {dimension!r} has empty anchors: "
                f"{sorted(empty_anchors, key=str)}"
            )

    scoring_rules = rubric.get("scoring_rules")
    if not isinstance(scoring_rules, list) or not scoring_rules or not all(
        isinstance(rule, str) and rule.strip() for rule in scoring_rules
    ):
        errors.append(f"{rubric_path}: scoring_rules must be nonempty strings")


def _validate_quality_rubric(root: Path, errors: list[str]) -> None:
    rubric_path = Path("schemas/quality-rubric.yaml")
    rubric = _load_yaml(root / rubric_path, errors)
    if not isinstance(rubric, dict):
        errors.append(f"{rubric_path}: rubric must be a YAML mapping")
        return
    if rubric.get("total_points") != 100:
        errors.append(f"{rubric_path}: total_points must be 100")

    dimensions = rubric.get("dimensions")
    if not isinstance(dimensions, dict):
        errors.append(f"{rubric_path}: dimensions must be a YAML mapping")
        return
    dimensions = _string_keyed_mapping(
        dimensions,
        f"{rubric_path}: dimensions",
        errors,
    )
    actual_dimensions = set(dimensions)
    expected_dimensions = set(QUALITY_RUBRIC_DIMENSIONS)
    if actual_dimensions != expected_dimensions:
        errors.append(
            f"{rubric_path}: dimension set mismatch: "
            f"expected={list(QUALITY_RUBRIC_DIMENSIONS)}, "
            f"actual={sorted(actual_dimensions)}"
        )

    total_dimension_points = 0
    for dimension in sorted(expected_dimensions & actual_dimensions):
        details = dimensions[dimension]
        if not isinstance(details, dict):
            errors.append(f"{rubric_path}: dimension {dimension!r} must be a mapping")
            continue
        max_points = details.get("max_points")
        if max_points != 20:
            errors.append(
                f"{rubric_path}: dimension {dimension!r} max_points must be 20"
            )
        else:
            total_dimension_points += max_points
        description = details.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(
                f"{rubric_path}: dimension {dimension!r} needs a description"
            )
        scoring = details.get("scoring")
        if not isinstance(scoring, dict):
            errors.append(
                f"{rubric_path}: dimension {dimension!r} scoring must be a mapping"
            )
            continue
        anchor_keys_are_integers = all(type(anchor) is int for anchor in scoring)
        if not anchor_keys_are_integers:
            errors.append(
                f"{rubric_path}: dimension {dimension!r} scoring anchor keys "
                "must be integers (booleans are invalid)"
            )
        elif set(scoring) != QUALITY_RUBRIC_ANCHORS:
            errors.append(
                f"{rubric_path}: dimension {dimension!r} scoring anchors mismatch: "
                f"expected={sorted(QUALITY_RUBRIC_ANCHORS)}, "
                f"actual={sorted(scoring, key=str)}"
            )
        empty_anchors = [
            anchor
            for anchor, description in scoring.items()
            if not isinstance(description, str) or not description.strip()
        ]
        if empty_anchors:
            errors.append(
                f"{rubric_path}: dimension {dimension!r} has empty scoring "
                f"anchors: {sorted(empty_anchors, key=str)}"
            )
    if total_dimension_points != 100:
        errors.append(
            f"{rubric_path}: dimension points must sum to 100, "
            f"found {total_dimension_points}"
        )

    if rubric.get("thresholds") != QUALITY_RUBRIC_THRESHOLDS:
        errors.append(
            f"{rubric_path}: thresholds mismatch: "
            f"expected={QUALITY_RUBRIC_THRESHOLDS}, "
            f"actual={rubric.get('thresholds')!r}"
        )


def _validate_quality_rubric_readme(
    root: Path,
    rendered_readme: str,
    errors: list[str],
) -> None:
    """Bind every rendered README score band to its machine-readable anchor."""
    rubric_path = Path("schemas/quality-rubric.yaml")
    rubric = _load_yaml(root / rubric_path, errors)
    dimensions = rubric.get("dimensions") if isinstance(rubric, dict) else None
    if not isinstance(dimensions, dict):
        return

    for dimension in QUALITY_RUBRIC_DIMENSIONS:
        title = QUALITY_RUBRIC_README_TITLES[dimension]
        details = dimensions.get(dimension)
        if not isinstance(details, dict):
            continue
        max_points = details.get("max_points")
        scoring = details.get("scoring")
        if (
            type(max_points) is not int
            or not isinstance(scoring, dict)
            or not all(type(anchor) is int for anchor in scoring)
            or set(scoring) != QUALITY_RUBRIC_ANCHORS
        ):
            continue

        heading = f"### {title} ({max_points} points)"
        heading_parts = rendered_readme.split(heading)
        if len(heading_parts) != 2:
            errors.append(
                f"README.md: quality rubric heading {heading!r} must appear "
                "exactly once"
            )
            continue
        section_lines = heading_parts[1].split("\n### ", 1)[0].splitlines()
        actual_bands = tuple(
            line
            for line in section_lines
            if re.fullmatch(r"- \*\*(?:0|\d+-\d+):\*\* .+", line)
        )

        anchors = sorted(scoring)
        expected_bands: list[str] = []
        for index, anchor in reversed(list(enumerate(anchors))):
            description = scoring[anchor]
            if not isinstance(description, str) or not description.strip():
                expected_bands = []
                break
            if anchor == 0:
                label = "0"
            else:
                label = f"{anchors[index - 1] + 1}-{anchor}"
            expected_bands.append(f"- **{label}:** {description}")

        if expected_bands and actual_bands != tuple(expected_bands):
            errors.append(
                f"README.md: quality rubric bands for {dimension!r} do not "
                f"match {rubric_path}: expected={expected_bands}, "
                f"actual={list(actual_bands)}"
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

    registry_path = Path("value-repos.json")
    registry = _load_json(root / registry_path, errors)
    if registry is not None and not isinstance(registry, dict):
        errors.append(f"{registry_path}: registry root must be a JSON mapping")
    elif isinstance(registry, dict):
        expected_root_keys = {*CANONICAL_REGISTRY_ENVELOPE, "value_repos"}
        if set(registry) != expected_root_keys:
            errors.append(
                f"{registry_path}: registry root keys must be exactly "
                f"{sorted(expected_root_keys)!r}"
            )
        for field, expected in CANONICAL_REGISTRY_ENVELOPE.items():
            if registry.get(field) != expected:
                errors.append(
                    f"{registry_path}: expected root {field}={expected!r}, "
                    f"found {registry.get(field)!r}"
                )
        entries = registry.get("value_repos")
        if not isinstance(entries, list):
            errors.append(f"{registry_path}: value_repos must be a JSON list")
        elif not all(isinstance(entry, dict) for entry in entries):
            errors.append(f"{registry_path}: value_repos entries must be JSON mappings")
        else:
            canonical_slug = f"{CANONICAL_ORGANIZATION}/{CANONICAL_REPOSITORY}"
            canonical_entries = [
                entry for entry in entries if entry.get("repo") == canonical_slug
            ]
            if len(canonical_entries) != 1:
                errors.append(
                    f"{registry_path}: expected exactly one canonical registry "
                    f"entry for {canonical_slug!r}; found {len(canonical_entries)}"
                )
            elif canonical_entries[0] != CANONICAL_REGISTRY_ENTRY:
                errors.append(
                    f"{registry_path}: canonical registry entry must match the "
                    "exact reviewed identity and planning fields"
                )

    rendered_identity_paths = {Path("AGENTS.md"), Path("CLAUDE.md"), Path("GEMINI.md")}
    for relative_path, expected_lines in CANONICAL_IDENTITY_LINES.items():
        path = root / relative_path
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{relative_path}: cannot audit repository identity: {exc}")
            continue
        lines = (
            _rendered_markdown_lines(relative_path, content, errors)
            if relative_path in rendered_identity_paths
            else content.splitlines()
        )
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
        normalized_targets = {
            repository.casefold(): owner
            for repository, owner in target_owners.items()
        }
        for match in GITHUB_REPOSITORY_URL.finditer(content):
            repository = match.group("repo").casefold().removesuffix(".git")
            expected_owner = normalized_targets.get(repository)
            actual_owner = match.group("owner")
            if (
                expected_owner is not None
                and actual_owner.casefold() != expected_owner.casefold()
            ):
                errors.append(
                    f"{relative_path}: noncanonical GitHub owner for "
                    f"{repository!r}: expected={expected_owner!r}, "
                    f"actual={actual_owner!r}"
                )


def validate(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []

    license_path = root / "LICENSE"
    license_valid = _is_contained_regular_file(license_path)
    if license_valid:
        license_valid = (
            license_path.stat().st_size > 0
            and hashlib.sha256(license_path.read_bytes()).hexdigest()
            == CANONICAL_LICENSE_SHA256
        )
    if not license_valid:
        errors.append(
            "LICENSE: canonical license file is missing, empty, symlinked, or changed"
        )

    requirements_path = root / "requirements-ci.txt"
    if not _is_contained_regular_file(requirements_path):
        errors.append(
            "requirements-ci.txt: required contained regular CI dependency lock missing"
        )
    else:
        requirements = requirements_path.read_text(encoding="utf-8")
        if requirements != REQUIRED_CI_REQUIREMENTS:
            errors.append(
                "requirements-ci.txt: dependency lock must exactly pin the "
                "canonical PyYAML artifacts"
            )

    _validate_schema_inventory(root, errors)
    _validate_reader_mode_documentation(root, errors)
    _validate_claim_boundary_policies(root, errors)
    _validate_canonical_schema_links(root, errors)

    overlap = PUBLICATION_TEMPLATES & READER_MODE_TEMPLATES
    if overlap:
        errors.append(f"template contracts overlap: {sorted(map(str, overlap))}")
    declared = PUBLICATION_TEMPLATES | READER_MODE_TEMPLATES
    discovered = {
        path.relative_to(root)
        for path in (root / "templates").rglob("*")
        if path.is_file() or path.is_symlink()
    }
    unclassified = sorted(discovered - declared)
    if unclassified:
        errors.append(f"unclassified template files: {list(map(str, unclassified))}")
    publication_marker_contract_gap = sorted(
        PUBLICATION_TEMPLATES ^ set(REQUIRED_PUBLICATION_BODY_MARKERS)
    )
    if publication_marker_contract_gap:
        errors.append(
            "publication body contracts do not match declared templates: "
            f"{list(map(str, publication_marker_contract_gap))}"
        )
    marker_contract_gap = sorted(
        READER_MODE_TEMPLATES ^ set(REQUIRED_READER_MARKERS)
    )
    if marker_contract_gap:
        errors.append(
            "reader-mode marker contracts do not match declared templates: "
            f"{list(map(str, marker_contract_gap))}"
        )
    table_contract_paths = READER_MODE_TEMPLATES | {
        Path("docs/reader-mode-documentation.md")
    }
    table_contract_gap = sorted(set(REQUIRED_READER_TABLES) - table_contract_paths)
    if table_contract_gap:
        errors.append(
            "reader-mode table contracts reference undeclared templates: "
            f"{list(map(str, table_contract_gap))}"
        )

    frontmatters: dict[Path, dict[str, Any]] = {}
    for relative_path in sorted(PUBLICATION_TEMPLATES):
        path = root / relative_path
        if not _is_contained_regular_file(path):
            errors.append(
                f"{relative_path}: required contained regular publication "
                "template missing"
            )
            continue
        data = _frontmatter(path, errors)
        if data is not None:
            frontmatters[relative_path] = data
        _validate_publication_body(
            relative_path,
            path.read_text(encoding="utf-8"),
            errors,
        )

    frontmatter_schema = _load_yaml(root / "schemas/frontmatter-schema.yaml", errors)
    if not isinstance(frontmatter_schema, dict):
        return errors
    required_map = frontmatter_schema.get("required_fields", {})
    optional_map = frontmatter_schema.get("optional_fields", {})
    if not isinstance(required_map, dict) or not isinstance(optional_map, dict):
        errors.append("schemas/frontmatter-schema.yaml: fields must be YAML mappings")
        return errors
    required_map = _string_keyed_mapping(
        required_map,
        "schemas/frontmatter-schema.yaml: required_fields",
        errors,
    )
    optional_map = _string_keyed_mapping(
        optional_map,
        "schemas/frontmatter-schema.yaml: optional_fields",
        errors,
    )
    duplicate_schema_fields = sorted(set(required_map) & set(optional_map))
    if duplicate_schema_fields:
        errors.append(
            "schemas/frontmatter-schema.yaml: fields cannot be both required and "
            f"optional: {duplicate_schema_fields}"
        )
    for field, rules in (*required_map.items(), *optional_map.items()):
        _validate_frontmatter_rule_definition(field, rules, errors)
    required_fields = set(required_map)
    allowed_fields = required_fields | set(optional_map)
    _validate_tag_governance(root, required_map.get("tags"), errors)
    _validate_category_taxonomy(root, required_map.get("category"), errors)
    _validate_reader_rubric(root, errors)
    _validate_quality_rubric(root, errors)

    for path, expected_category in sorted(ESSAY_CATEGORIES.items()):
        frontmatter = frontmatters.get(path)
        if frontmatter is None:
            continue
        frontmatter = _string_keyed_mapping(
            frontmatter,
            f"{path}: frontmatter",
            errors,
        )
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
        if (
            frontmatter.get("word_count_policy") == "external"
            and "word_count_override_reason" not in frontmatter
        ):
            errors.append(
                f"{path}: word_count_policy 'external' requires "
                "word_count_override_reason"
            )
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
        if not _is_contained_regular_file(path):
            errors.append(
                f"{relative_path}: required contained regular reader-mode "
                "template missing"
            )
            continue
        content = path.read_text(encoding="utf-8")
        content_lines = _rendered_markdown_lines(relative_path, content, errors)
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
