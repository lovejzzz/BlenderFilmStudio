# B54-E1 · Admission-gated native Blender 5.2 compiler integration protocol

Date: 2026-08-28

Type: real native compiler integration experiment

Status at protocol creation: preregistration only

## Research question

Can the B53-E1 formal admission module guard the real restricted `SceneSpec → immutable BuildPlan → Blender 5.2 → CompileReceipt` workflow without changing current compiler tools, while a relative CLI invocation still reproduces the frozen B01/B02 plan and canonical structure identities across two fresh builds per benchmark?

## Why this is the next gap

B53-E1 supported a deliberately isolated infrastructure claim: relative, dot-segment and absolute path representations converged on one canonical evidence identity; fourteen frozen violations rejected with exact reasons; every rejection retained a self-hashed failure and receipt before formal work. It did not run Blender, modify production orchestration or show that adoption preserves compiler behavior.

The core compiler evidence separately remains valid: 22/22 SceneSpec fixtures, deterministic B01/B02 BuildPlans, four native CompileReceipts and eight native/Linux canonical structure streams all revalidated. Joining those two evidence chains is therefore the smallest next intervention. Replacing the legacy `run-compiler-experiment.mjs` is not the target because that script deletes and reuses fixed output directories. The target is a new single-use wrapper around the current restricted compiler and receipt path; existing production files remain unchanged.

## Frozen sequence

1. Commit and push this spec/protocol before any B54 tool exists.
2. Create exactly three new tools: zero-Blender preflight, admission-gated formal runner and independent auditor.
3. Commit and push exact tools as the tool-freeze.
4. Run one zero-Blender preflight. It must re-run the 22-case SceneSpec suite, compile B01/B02 twice in memory, verify frozen plan hashes, validate tracked/pushed identities, exercise a relative-path admission-shaped component boundary without creating formal roots, and retain at least 100 GiB after a 512 MiB projection.
5. Commit and push the accepted preflight root. Only then call the formal runner once with repository-relative preflight, attempt and formal-root spellings.
6. The runner creates the separate attempt root and writes `attempt.json` before `admitFormalRun()`. On acceptance it writes `admission.json` and `receipt.json`; only then may it create the formal root or launch compiler work.
7. From current B01/B02 SceneSpecs, compile each BuildPlan twice and require canonical wrapper byte identity plus frozen plan hashes. Write one formal plan per benchmark.
8. Run B01-A, B01-B, B02-A and B02-B through the unchanged restricted compile CLI into four never-before-existing output directories.
9. Spawn the independent auditor. It invokes the current CompileReceipt verifier externally for all four receipts, reopens canonical structure bytes/manifests, audits all four `.blend` embedded markers with Blender 5.2, performs at least 24 in-memory one-field attacks and derives the outcome-neutral verdict.
10. Preserve all outputs. Any exception or process failure invalidates B54-E1 with `scientificVerdict=null`; same-ID repair or rerun is forbidden.

## Acceptance identities

| Benchmark | SceneSpec SHA-256 | BuildPlan hash | canonical structure SHA-256 |
|---|---|---|---|
| B01 | `1e3192aff070ac244f89b2cef96078e0d88c93a0d043e679e45f210f8d3cfde4` | `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` | `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b` |
| B02 | `774415a396bec91598ea8fac407443f04b6a630bdee046b15a14fae5fcad6c16` | `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687` | `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856` |

Acceptance uses byte identity of `scene.structure.canonical.json` within each A/B pair and exact frozen hashes. `.blend` hashes are recorded but are not required to match. No render operation is authorized.

## Process evidence boundary

The runner must record exact direct child PIDs, arguments, exit codes, stdout/stderr hashes and elapsed time for four restricted compiler children and the one independent auditor. The auditor must do the same for four current-verifier children and four Blender artifact-audit children. Each budget report binds the native compile Blender PID and resource metrics.

The unchanged receipt generator and verifier also call Blender `--version`; their eight identity probes are frozen semantic invocations but their PIDs are not exposed by the existing APIs. The result must state this limitation rather than claiming complete OS-process attestation.

## Claim boundary

Support means the new admission-gated wrapper preserved the minimal native compiler contract under one frozen relative-path formal invocation. It does not repair H2, render a frame, prove `.blend` byte determinism, cover later character/simulation workflows or make local Git hashes into remote attestation. Exposing the wrapper as the preferred public compiler entry remains a separate release step.
