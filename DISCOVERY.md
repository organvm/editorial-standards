# Discovery: organvm/editorial-standards

**Date:** 2026-06-22
**Verdict:** REAL LATENT VALUE — promote to ranked tier.

## Value Thesis

`editorial-standards` is not a documentation backwater — it is the only place in
the estate where "what makes writing good" is expressed as a **machine-readable,
versioned contract** rather than tribal habit. It already ships six YAML schemas
(`frontmatter-schema`, `quality-rubric`, `category-taxonomy`, `tag-governance`,
`log-schema`, `reader-mode-rubric`), six publication templates, and a calibrated
100-point quality rubric that
the `essay-pipeline` consumes to validate, route, and publish every essay in
`public-process`. That makes it a live upstream dependency with real, present
value. Its *highest latent* value, though, is that the rubric and frontmatter
schema are a **reusable documentation-quality standard the entire eight-organ
estate could adopt** (89 active repos, 0 with a codified docs bar today). The one
thing blocking that reuse: the schema is declarative-only — the actual enforcement
logic lives downstream inside `essay-pipeline`, so no other repo can enforce the
contract without re-implementing it. Extracting that enforcement into a small,
dependency-light validator that lives *with* the schema turns this repo from a
passive spec into a drop-in, estate-wide capability: any repo could gate its docs
on the same quality contract in CI. That is the build-out path, and it is concrete,
low-cost, and high-leverage.

## What it is (honest account)

- Pure docs + YAML governance repo, with no reusable validation package or CLI.
  Workflow-embedded CI parses every schema mapping; verifies the fixed publication
  and reader-template inventories, headings, and frontmatter contracts; compares
  the README field table with the schema; and checks the required repository files.
- Active consumers: `essay-pipeline` (enforces frontmatter schema), `public-process`
  (uses templates + naming conventions). Directional contract: standards define →
  pipeline enforces → public-process displays.
- The earlier README/schema drift is now repaired: the README documents the
  authoritative 12-field contract, and CI checks every essay template and the
  human-readable field table against `schemas/frontmatter-schema.yaml`. A reusable
  validator remains the next step for checking completed essays across repositories.

## Single best concrete first task

**Ship a standalone, dependency-light frontmatter + quality validator in this repo**
(a small `validate.py` CLI + a reusable GitHub composite action `action.yml`) that
reads `schemas/frontmatter-schema.yaml` and checks a target Markdown file/dir
against it, building on the README/template parity now enforced in CI. This co-locates
enforcement with the contract, lets `essay-pipeline` call one canonical validator
instead of duplicating logic, and lets any of the estate's repos adopt the docs
quality bar by dropping the action into their CI. It converts the schema from a
spec other repos *read* into a capability other repos *run*.
