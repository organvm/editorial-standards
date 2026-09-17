# Reader-mode upstream acceptance

Owner: Editorial PR #12, Codex gap-filling-20260915.

Add a read-only prerequisite resolver for schema #19, registry #553 and Engine #175. Require a true merged flag, valid immutable merge/default SHAs, default ancestry, and unchanged default readback. Return usable input refs only for accepted source ancestry; never infer CI, generation or runtime health. Failures are redacted and do not prevent inspection of independent inputs. No generated instruction files are edited.

Historical checkpoint (September 16, 2026; before identity hardening): five focused tests passed for accepted refs, unmerged/nonboolean state, divergent defaults, unavailable evidence with continued inspection, and default movement. Diff hygiene passed. The live read at that checkpoint exited 77: schema and registry were unmerged; Engine merge/default both bd223cfc9f2ee90782d6182101e849a6f97e0c99.

This checkpoint is not a current test count or upstream-state observation. The companion `2026-09-16-reader-upstream-identity.md` records the subsequent eight-test identity-hardening suite; later acceptance evidence must name its own tested revision.

Next command after accepted upstream landing: python3 scripts/check_reader_upstreams.py. Use its immutable accepted inputs for broker-driven context regeneration and retain the separate input/output custody receipt. Existing source contract receipts remain evidence for unchanged files; this check does not satisfy downstream acceptance by itself.
