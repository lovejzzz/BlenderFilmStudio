# B58-E1-C6 · Runtime child-parent preparation correction

Date: 2026-08-29
Status: PREREGISTERED AFTER FORMAL V0.2 FAILURE, BEFORE V0.3 OUTPUT

## Formal counterexample

The v0.2 formal runner passed evidence admission and durably completed `PLAN_BIND`. It spawned the npm production-compiler wrapper and recorded wrapper PID 9206, but recorded no `NATIVE_PROCESS_OBSERVED` event, production attempt root, production output root, audit or outer result receipt. The runner then failed closed with `Native Blender completed or failed before durable process identity observation`.

An isolated fresh-clone replay of the exact B57 production command exited in 0.31 seconds with `ENOENT` while creating the nested production-attempt final root. Therefore Blender was not short-lived: it was never started. B58 prepared the formal and attempt roots but not their immediate `outputs` and `production-attempts` parents, while the B57 durable directory contract intentionally creates only the final root. B58 also discarded the wrapper terminal text when native observation was absent, causing a misleading classification.

The retained v0.2 attempt/formal tree contains 13 files and has canonical tree SHA-256 `ac13387581ecdd0293fe8b16e7e579fe1f32ab02207657d90d284171797b5b72`. Its last event file SHA/event hash are `118f91d384c59b5f8359ecbf9c85d0c1d6e450fe14cfda767a33b5ff638ffd12` / `456d11d33b36a1af17cb49a4f4c3ad6b44a4c8b05128d4b31dee348a474358b4`. The tree is non-promotable and must remain byte-exact.

## Frozen correction

After candidate freshness and overlap validation, B58 must durably create exactly `dirname(candidate.productionAttemptRoot)` and `dirname(candidate.outputRoot)` before spawning the B57 wrapper. Each candidate final root remains absent and is still exclusively created by B57. B57 bytes are unchanged.

If the wrapper exits before a native identity is observed, B58 must first persist a non-promotable `FAILED` attempt receipt containing the bounded wrapper terminal record, then surface the failure. A successful wrapper still requires a native Blender identity; the correction does not permit post-hoc success without process evidence.

The v0.2 roots are permanently failed. One retry is authorized only at fresh, disjoint v0.3 preflight, attempt and formal roots. Preflight, runner and independent auditor must retain and reopen both the v0.1 wrong-commit rejection and the 13-file v0.2 runtime failure. Five C6 attacks cover failure-tree mutation, both missing parents, terminal-retention bypass and v0.2 root reuse.

C6 changes no render/model/network/Docker policy, Blender count ceiling, DAG, controlled interruption, restart decision, gate denominator or verdict threshold.
