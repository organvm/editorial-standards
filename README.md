[![ORGAN-V: Logos](https://img.shields.io/badge/ORGAN--V-Logos-0d47a1?style=flat-square)](https://github.com/organvm-v-logos)
[![CI](https://github.com/organvm/editorial-standards/actions/workflows/ci.yml/badge.svg)](https://github.com/organvm/editorial-standards/actions/workflows/ci.yml)
[![Tier: Standard](https://img.shields.io/badge/tier-standard-2196f3?style=flat-square)](https://github.com/organvm/editorial-standards)

# editorial-standards

_Voice, quality, and structure governance for the ORGAN-V discourse layer_

---

## Overview

editorial-standards is the governance layer for everything ORGAN-V publishes. It codifies the rules that determine what makes a piece of writing ready for the public process — the voice it should carry, the structure it should follow, the quality bar it must clear, and the metadata it must declare before it enters the pipeline.

This repository does not contain essays. It contains the rules that essays must obey.

The distinction matters. In a system that produces writing at scale — meta-system essays, case studies, retrospectives, post-mortems, methodology explorations — the editorial governance must live separately from the editorial content. Otherwise the rules drift with every new piece, standards become implicit, and quality becomes a matter of whoever last touched the file. editorial-standards makes the implicit explicit. It is the constitution for the discourse layer.

Concretely, this repository provides:

- **A voice specification** — the tonal and rhetorical identity that all ORGAN-V writing must express.
- **Essay category definitions** — the canonical set of essay categories, each with its own structural template and purpose.
- **A frontmatter schema** — the 12 required metadata fields that every essay must declare, with types, constraints, and validation rules.
- **A quality rubric** — a 100-point advisory scoring system across five dimensions, used during review to surface weak spots before publication.
- **Naming conventions** — deterministic rules for file names, series identifiers, and tag taxonomy, so that the essay-pipeline can process content without ambiguity.
- **A review process** — the pre-publish checklist and human synthesis gate that stands between a draft and a deployed essay.
- **A reader-mode repository contract** — one canonical project record expressed through audience-specific editions without factual drift.

Everything here is consumed downstream. The essay-pipeline reads the frontmatter schema to validate incoming drafts. The public-process repository is where validated essays land. editorial-standards sits upstream of both, defining the contract they depend on.

## Reader-mode repository documentation

Substantial repositories should not force general, technical, humanities,
business, and evaluator readers through the same rhetorical sequence. ORGANVM's
[reader-mode documentation standard](docs/reader-mode-documentation.md) defines:

- repository classes A–F, based on function rather than prestige;
- a README v2 orientation layer that preserves existing long-form depth;
- audience-edition contracts and templates;
- the normative editorial contract and audience templates around the canonical, evidence-bounded `project-record.yml` schema;
- a seven-dimension audit rubric for conversion planning;
- factual CI failures versus editorial warnings.

Start with the [canonical project-record example](https://github.com/organvm-iv-taxis/schema-definitions/blob/main/examples/project-record-v1-example.yaml),
[README v2 template](templates/repository-readme-v2.md), and
[project-record schema](https://github.com/organvm-iv-taxis/schema-definitions/blob/main/schemas/project-record-v1.schema.json).

## The Voice

ORGAN-V writes for an audience that builds things. The voice is substantive, honest, technical-but-accessible, and process-oriented. It does not perform expertise — it demonstrates it through specificity. It does not hide uncertainty — it names what is unknown and explains why.

The core principles of the ORGAN-V voice:

**Substantive over performative.** Every sentence should carry information. Introductions that exist only to "set the stage" without contributing content are cut. If a paragraph can be removed without the reader losing anything, it should be removed.

**Honest over polished.** The writing acknowledges false starts, dead ends, and things that did not work. The process is the product. A retrospective that only describes successes is not a retrospective — it is marketing. ORGAN-V does not do marketing.

**Technical but accessible.** The writing assumes an intelligent reader who may not share the author's specific domain expertise. Jargon is used when precise, defined when first introduced, and avoided when a plain word will do. The goal is to be understood on first read, not to signal membership in a community.

**Process-oriented.** ORGAN-V is interested in how things are built, not just what was built. The method matters. The sequence matters. The decisions that shaped the outcome — including the decisions that were wrong — matter. Writing that presents only the final artifact without explaining the path to it is incomplete.

**Structurally transparent.** The reader should always know where they are in a piece. Headings are descriptive, not clever. Section order follows logical dependency (context before analysis, analysis before conclusion). The structure itself is an argument about what matters.

These principles are not optional stylistic preferences. They are the editorial standard. Writing that violates them is sent back for revision.

## Essay Categories

ORGAN-V recognizes five canonical essay categories. Each serves a distinct purpose and carries its own structural expectations.

### Meta-System Essay

The flagship form. Meta-system essays explore how the eight-organ system works, why it is designed the way it is, and what principles govern its operation. They are the primary output of ORGAN-V and the most common content in public-process.

**Structure:** Introduction (context + thesis), body sections (each advancing the argument), cross-references to other organs and repos, conclusion (synthesis + forward-looking implications).

**Length:** 3,000-6,000 words.

**Examples:** "01-orchestrate," "02-governance," "05-five-years" in the public-process essays collection.

### Case Study

A detailed examination of a specific project, feature, or system component. Case studies are empirical — they describe what happened, not what should happen. They follow the arc of a problem through its resolution (or its failure to resolve). Post-mortems use the `case-study` category and apply its evidence standard to a failed or degraded outcome.

**Structure:** Context (what existed before), challenge (what needed to change), approach (what was tried), outcome (what resulted), reflection (what was learned).

**Length:** 2,000-4,000 words.

### Retrospective

A time-bounded look back at a sprint, phase, or milestone. Retrospectives are honest about what went well and what did not. They are not victory laps — they are diagnostic instruments.

**Structure:** Scope (what period/milestone is covered), objectives (what was intended), execution (what actually happened), delta analysis (gaps between intent and outcome), lessons (what changes going forward).

**Length:** 1,500-3,000 words.

### Guide

A prescriptive, instructional explanation of how to complete a task or apply an approach. Guides are concrete and sequential: they teach the reader what to do, identify prerequisites, and expose the trade-offs and verification steps.

**Structure:** Audience and prerequisites, core idea, step-by-step procedure, examples, trade-offs, and verification or next steps.

**Length:** 1,000-3,000 words.

### Methodology Essay

An explanation of a process, framework, or approach used within the system. Methodology essays are instructional — they describe how to do something, and why that approach was chosen over alternatives.

**Structure:** Motivation (why this method exists), prior art (what alternatives exist), the method (step-by-step), trade-offs (what this method sacrifices), application (where it has been used).

**Length:** 2,000-5,000 words.

## Frontmatter Schema

The machine-readable
[`schemas/frontmatter-schema.yaml`](schemas/frontmatter-schema.yaml) file is the
source of truth. It currently requires 12 fields:

| Field | Type | Core constraint |
|---|---|---|
| `layout` | string | `essay` |
| `title` | string | 10–200 characters |
| `author` | string | GitHub handle with `@` prefix |
| `date` | string | `YYYY-MM-DD` |
| `tags` | list | 2–8 lowercase, hyphenated tags |
| `category` | enum | `meta-system`, `case-study`, `retrospective`, `guide`, or `methodology` |
| `excerpt` | string | 50–400 characters |
| `portfolio_relevance` | enum | `CRITICAL`, `HIGH`, or `MEDIUM` |
| `related_repos` | list | GitHub `org/repo` references |
| `reading_time` | string | e.g. `12 min` |
| `word_count` | integer | minimum 500 |
| `references` | list | citations, or an explicit empty list |

Optional word-count policy fields support externally computed aggregate counts.
Downstream validators and templates must change in the same pull request as this
schema; prose descriptions never override it.

## Quality Rubric

The quality rubric is a 100-point advisory scoring system. It is not a gate — essays are not blocked from publication based on their score. It is a diagnostic tool that surfaces weak spots during review so that authors can address them before publication.

The rubric has five dimensions, each worth 20 points:

### Clarity (20 points)

How easily can the reader understand the essay on first read? Clarity scores assess sentence structure, paragraph organization, jargon management, and logical flow. A 20/20 clarity score means a competent reader outside the author's specific domain can follow the argument without re-reading.

- **16-20:** Clear, well-organized, minimal jargon or jargon well-defined.
- **11-15:** Generally clear with occasional dense passages.
- **6-10:** Requires significant effort to follow; restructuring needed.
- **1-5:** Unclear; major rewrite required.

### Accuracy (20 points)

Are the claims correct? Are the technical details right? Accuracy scores assess factual correctness, proper use of terminology, and whether code samples, configuration examples, or system descriptions match the actual implementation.

- **16-20:** All claims verifiable; technical details correct.
- **11-15:** Minor inaccuracies that do not affect the argument.
- **6-10:** Contains errors that could mislead the reader.
- **1-5:** Fundamentally inaccurate; requires fact-checking pass.

### Insight Density (20 points)

Does the essay reward the reader's time? Insight density measures the ratio of novel or useful information to total word count. High insight density means the essay is tightly written — every section advances the reader's understanding. Low density means the essay is padded with filler, repetition, or obvious observations.

- **16-20:** Nearly every paragraph offers something new or useful.
- **11-15:** Strong core insights with some padding.
- **6-10:** Insight buried under excessive context or repetition.
- **1-5:** Little new information; could be reduced to a fraction of its length.

### Cross-Referencing (20 points)

Does the essay connect to the broader system? Cross-referencing scores assess how well the essay links to other organs, repos, essays, and system concepts. ORGAN-V writing does not exist in isolation — it exists to document a system, and that system context must be present.

- **16-20:** Rich, meaningful connections to other system components.
- **11-15:** Some cross-references; could be better integrated.
- **6-10:** Minimal system context; reads as standalone.
- **1-5:** No cross-references; disconnected from the system.

### Portfolio Relevance (20 points)

Does this essay belong in the public process? Portfolio relevance assesses whether the essay contributes to the system's public narrative. It asks: if someone is reading the public-process collection to understand this system, does this essay help? Or is it internal documentation that does not serve an external reader?

- **16-20:** Essential reading for understanding the system.
- **11-15:** Useful but not critical; adds depth.
- **6-10:** Marginal relevance; might be better as internal documentation.
- **1-5:** Does not belong in the public collection.

### Scoring Guidelines

Scores are assigned by the reviewer during the review process. The total score is the sum of all five dimensions (0-100). Scores are advisory — they inform the author, they do not block publication. However, essays scoring below 60 are flagged for revision, and essays below 40 are returned to draft status with specific feedback.

The rubric is intentionally calibrated to be difficult. A score of 80+ represents genuinely excellent work. A score of 60-79 represents solid work that meets the standard. The system does not grade on a curve.

## Naming Conventions

### File Naming (_posts/)

All essays in public-process follow the Jekyll `_posts/` convention:

```
YYYY-MM-DD-slug.md
```

- **Date prefix:** ISO 8601 date, matching the `date` frontmatter field.
- **Slug component:** Lowercase, hyphenated, 3-80 characters. It is derived from the filename; there is no separate `slug` frontmatter field.
- **Extension:** Always `.md`.

Examples:
- `2026-02-17-editorial-governance.md`
- `2026-01-15-orchestration-patterns.md`
- `2026-03-01-five-year-roadmap-retrospective.md`

### Series Naming

Series identifiers are lowercase, hyphenated strings that group related essays:

```
meta-system-foundations
building-in-public
organ-deep-dives
```

Series names should be descriptive and stable. Once published, a series name should not change (it is used in URLs and cross-references).

### Tag Taxonomy

Tags must satisfy the format and count rules in
[`schemas/tag-governance.yaml`](schemas/tag-governance.yaml). Its curated list is
advisory: authors should prefer those tags, while deliberate new lowercase,
hyphenated tags remain valid. Examples organized by use include:

- **System tags:** `meta-system`, `orchestration`, `governance`, `architecture`, `infrastructure`
- **Organ tags:** `organ-i`, `organ-ii`, `organ-iii`, `organ-iv`, `organ-v`, `organ-vi`, `organ-vii`, `organ-viii`
- **Process tags:** `building-in-public`, `retrospective`, `post-mortem`, `methodology`, `case-study`
- **Domain tags:** `creative-coding`, `audio-synthesis`, `generative-art`, `web-development`, `devops`, `documentation`
- **Quality tags:** `flagship`, `deep-dive`, `introduction`, `reference`

New tags can be proposed via pull request to this repository. Tags must be lowercase, hyphenated, and descriptive. The tag vocabulary is intentionally constrained to prevent tag sprawl.

## Review Process

### Pre-Publish Checklist

Before an essay enters review, the author must verify:

1. **Frontmatter complete.** All 12 required fields are present and valid: `layout`, `title`, `author`, `date`, `tags`, `category`, `excerpt`, `portfolio_relevance`, `related_repos`, `reading_time`, `word_count`, and `references`.
2. **Filename canonical.** The filename follows `YYYY-MM-DD-slug.md`; its date prefix matches the `date` field, and its derived slug is lowercase, hyphenated, and 3–80 characters.
3. **Word count in range.** `word_count` is at least 500 and meets the applicable category guidance; any externally computed aggregate count declares both optional policy fields.
4. **No broken internal links.** All cross-references to other repos, essays, or system components resolve.
5. **Excerpt bounded.** `excerpt` is a one-paragraph summary between 50 and 400 characters.
6. **Tags valid.** `tags` contains 2–8 lowercase, hyphenated values; curated tags are preferred, and any new tag is deliberate.
7. **Repository references accurate.** `related_repos` uses canonical repository references and matches the repositories actually discussed.
8. **Enumerations valid.** `layout` is `essay`; `category` and `portfolio_relevance` use values admitted by the schema.
9. **Reading time valid.** `reading_time` uses the `<integer> min` format.
10. **References explicit.** `references` is a list, including `[]` when the essay has no external citations.
11. **Code samples tested.** Any code, configuration, or command-line examples have been verified.
12. **No secrets or credentials.** The essay does not contain API keys, tokens, or sensitive information.
13. **Spell check passed.** The essay has been checked for typos and grammatical errors.

### Human Synthesis Gate

The human synthesis gate is the final step before publication. It is not automated and cannot be automated. A human reviewer reads the essay and assesses:

- Does this essay say something worth saying?
- Is the argument honest?
- Would I send this to someone I respect?

If the answer to all three is yes, the essay is published. If not, it goes back to the author with specific feedback.

The human synthesis gate exists because quality rubrics can be gamed and checklists can be satisfied mechanically. The final judgment about whether a piece of writing is ready for the public process must be made by a human who cares about the work.

## How It Fits the System

editorial-standards is part of ORGAN-V (Logos / Public Process), the discourse and documentation organ of the eight-organ creative-institutional system.

Within ORGAN-V, it connects to:

- **[essay-pipeline](https://github.com/organvm/essay-pipeline)** — the automated pipeline that validates, transforms, and deploys essays. essay-pipeline consumes the frontmatter schema and document type definitions from this repository to validate incoming drafts.
- **[public-process](https://github.com/organvm-vi-koinonia/public-process)** — the publication venue where validated essays are deployed. public-process uses the templates and naming conventions defined here.

The relationship is directional: editorial-standards defines the rules, essay-pipeline enforces them, and public-process displays the results. Changes to editorial standards flow downstream through the pipeline to the publication layer.

Beyond ORGAN-V, editorial-standards influences how documentation is written across the entire system. While each organ has its own documentation practices, the voice principles and quality rubric defined here serve as the reference standard that other organs can adopt or adapt.

## Development

### Prerequisites

No build tools are required. editorial-standards is a documentation-and-schema repository. All content is Markdown and YAML.

### Local Development

```bash
git clone https://github.com/organvm/editorial-standards.git
cd editorial-standards
```

To validate YAML files locally:

```bash
python3 -c "
import yaml, glob, sys
errors = 0
for f in glob.glob('**/*.yaml', recursive=True) + glob.glob('**/*.yml', recursive=True):
    try:
        yaml.safe_load(open(f))
    except Exception as e:
        print(f'ERROR: {f}: {e}')
        errors += 1
sys.exit(1 if errors else 0)
"
```

### Repository Structure

```
editorial-standards/
  README.md              # This file
  LICENSE                # MIT License
  seed.yaml              # Automation contract
  CHANGELOG.md           # Release history
  .github/
    workflows/
      ci.yml             # Minimal CI validation
  docs/
    reader-mode-documentation.md
    adr/
      001-initial-architecture.md
      002-quality-rubric-design.md
  schemas/
    reader-mode-rubric.yaml
  templates/
    repository-readme-v2.md
    audiences/
```

## Contributing

Contributions to editorial-standards affect the governance rules for all ORGAN-V writing. Changes should be proposed via pull request with a clear rationale for why the standard needs to change.

For voice or rubric changes, include examples of how the change would affect existing published essays. For schema changes, coordinate with the essay-pipeline repository to ensure validation logic is updated in parallel.

See the [ORGANVM contributing guidelines](https://github.com/organvm/.github/blob/main/CONTRIBUTING.md) for general contribution practices.

## License

[MIT](LICENSE) -- 2026 [@4444J99](https://github.com/4444j99)

---

<sub>editorial-standards — ORGAN V: Logos — part of the eight-organ creative-institutional system — [@4444j99](https://github.com/4444j99) — LOGOS Sprint 2026-02-17</sub>
