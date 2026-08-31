# PB.1 validation-only C1 tool freeze v0.5

Date: 2026-08-31

Status: tools frozen; formal attempt-02 remains unauthorized

The C1 runner accepts an explicit versioned execution contract through `--contract`.
With the current v0.4 authorization request it is fail-closed: `authorization.granted`
is not true and no attempt-02 root can be created. A later owner grant must be captured
in a new v0.5 execution contract; the runner and auditor need not be edited after the
authorization decision.

The runner fixes only the two retained harness defects:

- it verifies the F0 parent through 14 frozen textual paths (`837/64`) plus two exact
  former-LFS pointer object transitions, independent of active worktree attributes;
- it creates a fresh local LFS storage and places only its `objects` symlink on the retained
  immutable object subtree, so checkout temp files remain inside attempt-02.

The command surface contains no public engine network clone and no engine push/ref/tag,
LFS network transfer, release, signing, notarization, DMG or PB.2–PB.7 operation. Formal
counters require exactly one local engine clone, one objects symlink, one additional local
materialization, one dependency clone, one build, two zero-render starts and zero forbidden
operations.

Frozen tool hashes:

- runner: `8b9489d625a5865f3e4304c01480dbcc966ab033e69a80054fe9ab87cf94ec9c`
- independent auditor: `58b1b3b0971d22a31d113de8a25384be3e8807e4d99a0f74739a54caede9ec7c`

Runner self-test is 9/9 PASS and auditor self-test is 5/5 PASS. Node syntax and ESLint
checks pass. No attempt-02 external/evidence root, clone, symlink, materialization, dependency,
build or product start was created while freezing these tools.
