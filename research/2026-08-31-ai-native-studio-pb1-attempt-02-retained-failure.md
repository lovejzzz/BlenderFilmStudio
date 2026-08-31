# PB.1 validation-only C1 attempt-02 retained failure

Date: 2026-08-31

Status: `FAIL` retained; stop rule preserved

Gate: PB.1 Repository and source identity, validation-only

## Result

The exact owner authorization was captured in
`specs/ai-native-studio-pb1-validation-only-c1-execution.v0.5.json` and pushed at
research commit `02672681d1bb1c984be3cb77952d7feccc54a47c`. Its authorization text was
byte-exact with the frozen v0.4 request. The formal preflight was `ACCEPTED` and all
nine negative controls passed.

The runner then completed exactly one authorized local-only Git clone from retained
attempt-01. It disabled the clone's push URL and LFS network URL, checked out exact
publication HEAD `4061e12bd45a2bec83e68d0cf49abbf56d4738f6`, and stopped at
`FRESH_LOCAL_LFS_MATERIALIZATION` with
`FRESH_LFS_OBJECTS_PATH_NOT_ABSENT`.

This is a harness-ordering failure. The no-checkout clone itself did not require an LFS
object directory. The subsequent skip-smudge publication checkout ran before the fresh
`objects` symlink was installed and created 6,424 empty hash directories under
`.git/lfs/objects`. They contain zero object files, zero object bytes and zero symlinks.
The runner correctly refused to replace that path and did not run `git lfs checkout`.

## Immutable evidence bindings

- evidence root:
  `experiments/ai-native-studio-phase-b/PB.1-2026-08-31-mac-m2max-attempt-02`
- execution contract SHA-256:
  `69faa7f9699a96745b1da2bce234cef3fcd97da44ad28ee36fb4b841c0aee912`
- preflight receipt hash:
  `e054081931560d3fa4ac316d832432be9a79514700402dfbd9f62ffb7a7ca7b3`
- negative-controls receipt hash:
  `70aa994ad417b0e4f3c0dd38dda06cb207fda7d91f5ca3d2a068a7e81067c5d7`
- failure receipt hash:
  `9df179aded8181e770d13ad83b1985c56dc562e601b46051de6658e3bdb6d654`
- verdict receipt hash:
  `2ab9aeb68184c06c23d2d05501c3a7e57eeda3faa267543f94372284957b3f74`
- runner SHA-256:
  `8b9489d625a5865f3e4304c01480dbcc966ab033e69a80054fe9ab87cf94ec9c`

The first independent failure audit is retained as 29/30 `FAIL`, receipt hash
`7dcc68e07355d85a6dd14abc9f17fd68daec09d72ba4fc88b6a3739949f634ec`.
Its sole failure was an auditor scope defect: it treated the tracked empty gitlink
worktree directory `lib/macos_arm64` as a completed dependency clone. The directory had
no `.git` and no files; its Git index entry was the expected gitlink at
`a76ef917b4849ba2b1b1deb1a643e131a884a63b`.

The C1 independent failure audit corrected only that scope and passed 24/24. Its receipt
hash is `f8c5b4d04e9aa2ddff5cd3a28c0c49a5fd7675b2d14675cfeb63e7cdd8b7baec`;
auditor SHA-256 is
`e0e2de7ad1056e0f9ffba7f92038e80f023a4af38a9db6ba9969cfe5a0004fee`.

## Preserved side-effect boundary

Observed formal counts were:

- local engine clones: 1
- fresh objects symlinks: 0
- local LFS materializations: 0
- dependency clones: 0
- native builds: 0
- product starts: 0
- renders: 0
- public engine network clones: 0
- engine remote writes/ref updates: 0
- LFS downloads/uploads: 0
- releases/signing/notarization/DMG/PB.2-PB.7/model calls: 0

The retained LFS storage remained byte/mtime exact with 10,406 files and 810,236,112
bytes. Its immutable objects subtree remains 6,488 files / 810,236,112 bytes with
manifest `f392cbbc4e6db312a0c1ee704bf24080e18a02889bf6ef02f619e21f2910cafd`.
The 3,918 retained zero-byte tmp files remain unchanged. Live `lovejzzz/film-engine`
still has only `main=4061e12bd45a2bec83e68d0cf49abbf56d4738f6`, with zero tags, PRs and
releases.

## Required correction

A versioned C2 runner must make only one ordering change: after the no-checkout local
clone, it must assert `.git/lfs/objects` absent and create the exact retained-objects
symlink before checking out publication HEAD. It must not delete or repair attempt-02
and must retain every other threshold, counter and prohibition.

Attempt-02 consumed its one local clone. A fresh attempt-03 root, another local clone,
another materialization, dependency clone, build or product start is not authorized by
the attempt-02 grant. Formal attempt-03 requires a new exact owner authorization.
