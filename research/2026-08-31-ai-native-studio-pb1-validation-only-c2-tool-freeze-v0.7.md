# PB.1 validation-only C2 tool freeze v0.7

Date: 2026-08-31

Status: tools frozen; formal attempt-03 unauthorized

Attempt-02 is retained as a harness-ordering failure. C2 changes only the position of
fresh LFS `objects` symlink installation: after the no-checkout local clone and before
publication checkout. It does not delete or alter either retained attempt.

Frozen hashes:

- authorization request:
  `2c1747ef1b70c73b4fa3ec24b744c77afaa93d5b25e853602f22e99bbf77b3fb`
- runner:
  `b4169ab6e97b8caef412afedbd8cee9381db70ea95f319a9cd34aa3e2e9fdd50`
- independent auditor:
  `c4b43343d59639cb8ddf4f0360cdddee2971cdce4ccfa0069b7d997c8d78c7b9`

Runner self-test is 10/10 `PASS`; the added test proves the symlink statement precedes
the publication-checkout command in the frozen source. Auditor self-test is 6/6 `PASS`
and recomputes the same ordering independently. Node syntax, ESLint and diff checks pass.

The command surface still contains no public engine network clone, engine push/ref/tag,
LFS network transfer, release, signing, notarization, DMG or PB.2-PB.7 action. Formal
counters remain exactly one local engine clone, one objects symlink, one local LFS
materialization, one local dependency clone, one native build, two zero-render product
starts and zero forbidden operations.

No attempt-03 external/evidence root, clone, symlink, materialization, dependency, build
or product start was created while preparing or freezing C2. A future execution contract
must use schema `bfs.pb1ValidationOnlyC2Execution.v0.7`, record the exact v0.6 owner text,
and be committed/pushed before the runner's preflight can become `ACCEPTED`.
