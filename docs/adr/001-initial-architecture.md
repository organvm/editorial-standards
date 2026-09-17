# ADR-001: Initial Architecture Decisions

**Status:** Accepted
**Date:** 2026-02-17
**Context:** LOGOS Sprint — establishing editorial-standards as the governance layer for ORGAN-V writing

**Implementation update (2026-09-09):** The format and repository decisions below remain in effect. The original schema had 11 required fields; the current frontmatter contract has 12 required fields and 2 optional fields. Repository-local validation now runs `python3 scripts/validate_editorial_contracts.py` and the adversarial contract regressions in CI. It checks schema and template consistency, canonical policy and repository identity, reader structure, and navigation. Validation of individual published essays remains a downstream responsibility of essay-pipeline.

## Decision Drivers

ORGAN-V (Logos / Public Process) needs a codified set of editorial rules — voice, structure, quality, metadata — that governs all published essays. The question is not whether these rules should exist (they must) but how they should be represented and where they should live.

Three architectural decisions were made simultaneously during the initial design:

1. What format for the editorial standards themselves?
2. What format for the frontmatter schema?
3. Should editorial governance live with or apart from the essay content?

## Decision 1: Markdown for Editorial Standards

### Context

The editorial standards — voice specification, document type definitions, review process, naming conventions — need to be readable by humans, versionable by git, and accessible without specialized tooling.

### Considered Options

**Option A: Custom CMS.** Build or adopt a content management system with structured fields for each standard. Standards would be edited through a web interface and stored in a database.

**Option B: Structured database.** Define standards as rows in a relational or document database, with a schema enforcing field types and constraints.

**Option C: Markdown files in a git repository.** Write standards as plain Markdown, version them with git, and review changes through pull requests.

### Decision

**Option C: Markdown in git.**

### Rationale

- **Zero tooling overhead.** Every contributor already has a text editor and git. No database to provision, no CMS to maintain, no web interface to secure.
- **Native to the workflow.** The essays themselves are Markdown. The standards that govern them should use the same format. This eliminates format translation friction.
- **Pull request review.** Changes to editorial standards are consequential — they affect every future essay. Git pull requests provide line-level review, discussion, and an immutable audit trail of what changed and why.
- **Portability.** Markdown files can be read on any platform, rendered by any static site generator, and understood without specialized knowledge.

### Rejected Alternatives

A custom CMS introduces infrastructure, maintenance, and access-control complexity disproportionate to the problem. The editorial standards are a small, slowly-changing corpus — they do not need the machinery of a CMS.

A structured database provides strong typing but sacrifices readability and accessibility. Editorial standards need to be read and discussed by humans, not queried by machines. The database approach optimizes for the wrong consumer.

## Decision 2: YAML for Frontmatter Schema

### Context

At the initial decision, the frontmatter schema defined 11 required metadata fields for every essay. This schema needs to be both human-readable (authors reference it when writing frontmatter) and machine-consumable (the essay-pipeline validates against it).

### Considered Options

**Option A: JSON Schema.** Use the JSON Schema specification to define field types, constraints, and validation rules. Full tooling ecosystem available.

**Option B: YAML with prose descriptions.** Define the schema in YAML (matching the frontmatter format itself) with human-readable descriptions of constraints, supplemented by prose in the README.

**Option C: TypeScript interfaces.** Define the schema as TypeScript types, leveraging the type system for validation.

### Decision

**Option B: YAML with prose descriptions.**

### Rationale

- **Format alignment.** Essay frontmatter is written in YAML. Defining the schema in the same format means authors see the exact syntax they need to produce. There is no translation step between "what the schema says" and "what I type."
- **Dual readability.** YAML is readable by both humans and machines. Authors can scan the schema and understand it immediately. The essay-pipeline can parse it programmatically for validation.
- **Simplicity.** JSON Schema is powerful but verbose. For the initial 11 fields with straightforward constraints, the expressiveness of JSON Schema was unnecessary overhead. The constraints (character limits, enum values, conditional requirements) are easily expressed in YAML with prose annotations.
- **Ecosystem fit.** The broader organvm system uses YAML extensively (seed.yaml, GitHub Actions workflows, configuration files). YAML is the lingua franca of the system's declarative layer.

### Rejected Alternatives

JSON Schema provides formal validation semantics but introduces a cognitive burden disproportionate to the schema's complexity. Authors would need to understand JSON Schema syntax to read the schema, which defeats the purpose of a human-readable specification.

TypeScript interfaces couple the schema to a specific language runtime. The essay-pipeline may be written in Python, TypeScript, or a shell script — the schema should not assume the consumer's language.

## Decision 3: Separate Repository for Editorial Governance

### Context

Editorial governance (voice, structure, quality, metadata rules) could live in the same repository as the essay content (public-process) or in a dedicated repository (editorial-standards).

### Considered Options

**Option A: Governance in public-process.** Add a `_standards/` or `docs/` directory to the public-process repository containing the editorial rules alongside the essays they govern.

**Option B: Governance in a dedicated repository.** Create editorial-standards as a standalone repo that public-process and essay-pipeline depend on.

### Decision

**Option B: Dedicated repository.**

### Rationale

- **Separation of concerns.** The rules that govern writing and the writing itself have different change frequencies, different reviewers, and different purposes. Mixing them in one repository conflates governance with content.
- **Multiple consumers.** The editorial standards are consumed by at least two downstream repositories: essay-pipeline (for validation) and public-process (for templates and structure). A dedicated repository provides a single source of truth that both can reference.
- **Change management.** Changes to editorial standards are high-impact — they potentially affect every essay. These changes deserve their own pull request history, their own review process, and their own versioning. Burying them in the essay repository makes them harder to track and easier to overlook.
- **System architecture alignment.** The eight-organ system separates concerns at the repository level. Each repository has a single, well-defined purpose. editorial-standards governs writing. public-process publishes writing. essay-pipeline validates writing. Clean boundaries produce clean systems.

### Rejected Alternatives

Colocating governance with content is simpler initially but creates problems at scale. When a reviewer sees a PR that changes both an essay and a governance rule, it is unclear which change is consequential. Separate repositories force separate PRs, which force separate reviews.

## Consequences

### Positive

- Low barrier to contribution: Markdown + git is universal.
- Clean dependency graph: editorial-standards -> essay-pipeline -> public-process.
- Changes to governance are visible, reviewable, and versioned independently.
- Schema format matches the content format, reducing cognitive overhead for authors.

### Negative

- Cross-repository coordination is required when schema changes need corresponding pipeline updates.
- Repository-local contract validation and downstream essay validation must evolve together when editorial policy changes.
- Contributors must know to look in a separate repository for the rules, rather than finding them alongside the content.

### Mitigations

- The README cross-references essay-pipeline and public-process explicitly.
- The seed.yaml automation contract declares the producer-consumer relationships.
- Schema changes will include a note in the PR description about required downstream updates.
