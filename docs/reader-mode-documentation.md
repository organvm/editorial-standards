# Reader-mode repository documentation

## Decision

ORGANVM repositories use one canonical factual record and, when their class
requires it, several audience-specific editions. These editions are routes
through one project, not independent stories about it.

The following facts are invariant across every route:

- project and implementation status;
- authorship and contribution boundaries;
- capabilities and limitations;
- deployment, adoption, and outcome claims;
- evidence references;
- the distinction between existing, partial, proposed, and retired work in
  reader-facing prose, without treating those scope boundaries as evidence
  verification states.

Audience pages may change order, terminology, examples, assumed knowledge, and
the evidence they foreground. They may not silently change those facts.

## Reader questions

| Reader mode | First question | Foreground |
|---|---|---|
| General | What is this, and why should I care? | Recognition, example, current state |
| Technical | How is it built, and does it work? | Architecture, execution, tests, boundaries |
| Humanities | What ideas and cultural problems does it engage? | Genealogy, form, interpretation, stakes |
| Business | What operational problem does this change? | Workflow, integration, risk, evidence |
| Evaluator | What did the author specifically do? | Initial state, contribution, proof, limits |

## Repository classes

Class controls documentation breadth. It is not a prestige grade.

| Class | Repository function | Required documentation |
|---|---|---|
| A — Flagship system | Mature project spanning several audiences | README v2, all five audience editions, evidence record, project record |
| B — Major project | Substantial project with two or three real audiences | README v2, 2–3 audience editions, evidence record, project record |
| C — Supporting component | Library, service, schema, or infrastructure component | Technical README/edition, status, interfaces, evidence, project record |
| D — Deployment artifact | Player, compiled build, mirror, or delivery shell | Minimal use-oriented README, canonical-project redirect, status |
| E — Research/theory | Scholarship, artistic research, or conceptual corpus | Scholarly-first README/edition, sources, provenance, evidence record, project record |
| F — Archive/reference | Superseded or preserved material | Archive notice, provenance, immutable status, correct redirect |

Classify by the repository's actual function. Do not inflate a deployment shell
into a flagship because it is public, or demote a theory repository because it
does not ship conventional software.

## Required root README sequence

For classes A and B, the first screen establishes:

1. project name;
2. one ordinary-language sentence stating what it is, what it does, and why;
3. verified links to the artifact, demo, or inspection path;
4. a short “What am I looking at?” explanation;
5. an audience-route table;
6. project status, primary users, authorship, evidence, and limitations at a glance.

The existing long-form README continues beneath this orientation layer. The
reader-mode contract controls sequence, not intellectual density.

Classes C–F use the same principle at reduced breadth. A class D player page,
for example, should explain how to use the artifact and where its canonical
development record lives; it should not reproduce the development repository.

## Canonical layout

```text
README.md
project-record.yml
docs/
├── audiences/
│   ├── general.md
│   ├── technical.md
│   ├── humanities.md
│   ├── business.md
│   └── evaluator.md
├── evidence/
│   └── README.md
├── architecture/
├── concepts/
└── industries/
```

Only create pages justified by the repository class and evidence. Empty SEO
pages and speculative industry catalogs are contract violations, not coverage.

## Canonical project record

`project-record.yml` is the shared factual substrate. It is validated by the
canonical
[`project-record-v1.schema.json`](https://github.com/organvm-iv-taxis/schema-definitions/blob/2c2b7c8b0e841a4abde82230be88524d43f9b3c2/schemas/project-record-v1.schema.json)
contract. Material claims resolve to separate
[`assertion-evidence.v1`](https://github.com/organvm-iv-taxis/schema-definitions/blob/2c2b7c8b0e841a4abde82230be88524d43f9b3c2/schemas/assertion-evidence.v1.schema.json)
records rather than duplicating mutable claim text and verification state.
At minimum it records:

- name, repository, class, status, and last verification date;
- ordinary-language definition, problem, and primary users;
- authorship and contribution boundaries;
- capability status;
- assertion-evidence references and limitations;
- enabled audience routes;
- evidence-bounded industry applications and concept terms;
- verified project, demo, deployment, and documentation links.

Generated factual blocks should identify their source and must not be edited by
hand. Hand-written analysis surrounds those blocks.

## Audience edition contracts

### General

Answer, in order: what it is; the problem that led to it; what happens when it
is used; one concrete example; why it matters; what exists now; where to go
next. Define repository terms without infantilizing the reader.

### Technical

Foreground architecture, component boundaries, data flow, interfaces,
dependencies, setup, execution, tests, observability, failure modes, security,
human approval boundaries, implementation status, and debt. Conceptual framing
may remain, but it cannot block the executable inspection path.

### Humanities

Treat the project as a formal and cultural object. Address intellectual
genealogy, aesthetics, media form, epistemology, narrative, authorship,
institutional context, ethics, pedagogy, and interpretation where relevant.
Connect mechanisms to conceptual consequences rather than merely removing
technical terms.

### Business

Begin with the existing workflow: problem, actor, current workaround, changed
workflow, inputs/outputs, integration, risks, constraints, deployment status,
and evidence versus projected value. Create a domain page only when there is a
specific and substantive mapping.

### Evaluator

Record the initial condition, Anthony's role, personally designed or implemented
work, outcomes supported by evidence, incomplete work, collaborative/generated/
inherited inputs, and exact inspection paths. Do not turn contribution evidence
into biography or promotional copy.

## Evidence rules

Every material claim resolves to an `assertion-evidence.v1` record. Its
machine-readable `verification_state` is exactly one of:

- **unverified** — the record does not yet establish the claim;
- **verified** — the cited evidence establishes the bounded statement;
- **stale** — the evidence is no longer fresh enough for the claim;
- **disputed** — current evidence or authorities conflict.

Do not write `implemented`, `partial`, `proposed`, `unknown`, or `contradicted`
into `verification_state`. Each project-record claim reference instead carries
one of those values as its required `claim_posture`. Posture is the structured
reader-facing scope axis; the assertion's verification state records whether its
bounded factual statement is supported. In particular, a proposed application
is ordinarily represented as a labeled `inference`, and conflicting evidence is
represented by `disputed`; neither mapping should be inferred silently by an
audience page.

Evidence sources may include source modules, tests, demos, deployments, revision
history, project documents, or external records. A source path alone is not proof
of adoption, performance, or business outcome. Limitations are separate entries
in `project-record.yml`; `assertion-evidence.v1` has no per-claim limitation
field. A project limitation may include an `assertion_ref` when it bounds a
specific assertion. Audience prose may restate that boundary but may not mutate
the assertion record.

## Search-topic clusters

Optimize for reader intent, not keyword repetition. Legitimate routes include:

- informational questions;
- a concrete operational problem;
- technical implementation;
- comparison or evaluation;
- research and interpretation;
- a verified commercial workflow;
- hiring and contribution inspection.

Each page must answer its target question, link to the canonical project, and
avoid duplicating another page's prose. Lateral cross-repository links must name
the relationship (dependency, implementation, theory, deployment, extension, or
related method) so the result functions as a knowledge graph rather than a link
dump.

## Audit and conversion priority

Score the current public documentation from 0–4 across orientation, technical
depth, conceptual depth, commercial relevance, evidence, SEO surface, and
cross-linking. Use
[`schemas/reader-mode-rubric.yaml`](../schemas/reader-mode-rubric.yaml).

Rank conversion work using three separate signals:

1. **value** — importance, current activity, audience breadth, and evidence;
2. **documentation gap** — the distance between current documentation and the
   contract appropriate to its class;
3. **conversion leverage** — expected reuse, discoverability, portfolio value,
   and ability to establish a pattern for other repositories.

Do not rank solely by lowest score; a dormant stub can be worse documented and
still be a poor first investment. Rank mirrors, deployments, archives, and
vendor/contribution repositories in their own queues.

## CI contract

Repository documentation CI should fail on factual integrity problems and warn
on editorial opportunity. Failures include:

- invalid `project-record.yml`;
- a required audience path missing for the declared class;
- duplicate evidence IDs or audience modes;
- a deployed/piloted industry claim without evidence references;
- missing local files referenced by the record;
- invalid status vocabulary;
- a generated factual block that differs from the project record.

Warnings include thin orientation, orphan documentation, duplicated prose,
missing semantic cross-links, and low rubric dimensions. Rubric scores remain
diagnostic; they are not a substitute for human review.

## Migration protocol

1. Classify the repository and identify its canonical relationship to mirrors,
   deployments, archives, and parent systems.
2. Audit the existing README and docs without rewriting them.
3. Create and verify `project-record.yml`.
4. Add the orientation layer to the README.
5. Create only the required audience routes.
6. Move claim-level detail into the evidence record; preserve source links.
7. Add typed vertical and lateral links.
8. Run structural, schema, link, and drift checks.
9. Review the diff for factual change. Reader-mode migration must not silently
   upgrade status, adoption, authorship, or outcomes.
