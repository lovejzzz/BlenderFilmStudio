# PB.1 validation-only attempt-01 retained failure

Date: 2026-08-31

Gate: PB.1 Repository and source identity

Verdict: `FAIL` before dependency clone, native build, or product start

## What passed

The authorized public read-only clone resolved exact
`lovejzzz/film-engine main=4061e12bd45a2bec83e68d0cf49abbf56d4738f6`, tree
`5f0cb3eb…`, sole parent `fa1b578b…`, merge base `9e2066ae…`, five fork commits and
162,918 reachable commits. The checkout is non-shallow and a full strict `git fsck`
passed. C1 changed exactly the frozen `.gitattributes`, icon and splash paths; the complete
publication range remained 17 paths, 839 textual additions, 64 deletions and two binary
paths. Nine negative controls passed before the external root existed.

One local-only LFS checkout materialized 6,669 paths / 812,388,053 bytes with exact
content hashes. It made no LFS network download or upload. Live GitHub remained the same
public `blender/blender` fork with one exact `main`, zero tags, PRs and releases.

## Why the runner stopped

The v0.3 contract reused the retained F0 worktree statistic `841 additions / 68 deletions`
as though it were independent of Git attribute context. Under the C1 publication worktree,
the two former LFS pointer paths have exact-path `-diff/-text` overrides and are therefore
classified as binary. The same exact F0 parent tree reports `837 / 64 + two binary paths`.
The four/four line delta is exactly the two old two-line LFS pointers. No source object,
commit, path or product code changed; the metric was underspecified.

The runner correctly wrote `FAIL` and stopped. Counters at stop were public read-only clone
`1`, local materialization `1`, dependency clone/build/product start/render `0/0/0/0`, and
all engine remote writes, ref updates, LFS network transfers, releases, signing, notarization,
DMG and PB.2–PB.7 mutations `0`.

## Retained auditor failure and C1 correction

The first failure auditor passed 41/42 checks but compared the entire retained LFS storage
tree. Directly binding `lfs.storage` caused `git lfs checkout` to leave 3,918 zero-byte files
under retained `tmp/`. All 6,488 immutable object files, 810,236,112 object bytes, mtimes and
object manifest hash remained exact. The failed audit is retained unchanged.

The independent C1 failure audit scopes immutability to the object subtree, records the tmp
side effect, rehashes all materialized content, rechecks the live remote and passes 29/29.
Its receipt hash is
`e0fb3dd1758d0a9dc462acd618f0b95089abfea67f46f2a35e29e07342d82222`.

## Correction boundary

A corrected attempt must use a fresh immutable root, cross-bind both retained failures,
freeze an attribute-context-independent parent metric, and keep materialization tmp files in
fresh local storage while linking only the retained immutable objects. The authorized one
public network clone and one materialization have already been consumed, so no correction
run may start without a new exact owner authorization. PB.1 remains open; PB.2–PB.7 remain
unauthorized.
