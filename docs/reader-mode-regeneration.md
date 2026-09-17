# Reader-mode context regeneration

Owner: Editorial PR #12. Generated instruction files must come from the
accepted Engine generator and accepted registry bytes.

## Source prerequisites

Run `python3 scripts/check_reader_upstreams.py` from this repository. Exit 77
means source evidence is missing. Do not regenerate from open candidates. Exit 0
supplies immutable merge/default refs; it does not establish CI or deployment.

Use clean checkouts of the reported Engine and registry default refs. Verify their
heads and registry schema. Copy Editorial's original instruction files and seed
into an owned staging workspace containing only this repository, under Engine's
`REGISTRY_KEY_MAP["ORGAN-V"]` directory. Preserve the originals.

## Scoped generation

Import `sync_all` from the exact accepted Engine checkout:

```python
result = sync_all(
    workspace=isolated_workspace,
    registry_path=str(accepted_registry_file),
    dry_run=True,
    organs=["ORGAN-V"],
    additional_workspace_roots=[],
)
```

The empty additional-root list prevents ambient workspace discovery. An unresolved
seed identity is a failed prerequisite; do not substitute a similarly named repo.
Review errors and changed paths before repeating with `dry_run=False` in staging.
Copy back only the intended repository `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`
outputs. Check preservation of manually authored content. Do not copy generated
organ-level or workspace-level files back into this repository.

## Acceptance receipt

Record upstream repository IDs and exact heads, complete input and output digests,
original instruction digests, the invocation, and errors/result counts. Section
hashes alone do not prove whole-file custody. Private input bytes stay in their
authorized custody home; tracked evidence uses appropriate redacted references.

Run the owning editorial contract suite under required host admission after copying
reviewed outputs into the isolated PR worktree. Bind the receipt to its final head
and use the declared integration rail once. Generation, source landing, default
verification, and runtime adoption remain separate outcomes.

Apply the prepared About correction only after its upstream acceptance condition
is satisfied, then read it back through the repository API. A prepared value or
metadata capability alone does not prove that the correction was applied.
