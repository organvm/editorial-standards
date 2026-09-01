# [Project]: evidence record

## Assertion evidence

| ID | Claim | Claim posture | Assertion class | Verification state | Evidence | Freshness |
|---|---|---|---|---|---|---|
| [claim-id] | [Bounded factual claim] | [implemented / partial / proposed / unknown / contradicted] | [external_fact / operator_directive / current_state / inference / historical_record / ratified_axiom] | [unverified / verified / stale / disputed] | [Inspectable reference and digest] | [fresh / stale / not_applicable, when required] |

Use the exact `claim_posture` from the project-record claim reference and the
exact `assertion_class`, `verification_state`, and freshness values from each
referenced `assertion-evidence.v1` record. Claim posture is a structured
reader-facing scope axis; it is not a `verification_state` value.

## Project limitations

| ID | Limitation | Related assertion |
|---|---|---|
| [limitation-id] | [Material boundary from project-record.yml] | [Optional assertion_ref] |

Populate the assertion table from the `assertion-evidence.v1` records referenced
by `project-record.yml`, and the limitations table from the project record's
separate `limitations` entries. The assertion schema has no per-claim limitation
field. Audience pages may foreground different rows but may not change an
assertion's statement, class, verification state, freshness, or evidence.
