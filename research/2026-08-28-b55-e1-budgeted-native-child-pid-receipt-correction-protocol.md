# B55-E1 budgeted native child PID receipt correction protocol

Date frozen: 2026-08-28, before changing `scripts/lib/budgeted-process.mjs`, creating any B55 tool byte, running any PID probe, or creating any B55 output root.

## Why this experiment exists

B54-E1 did not fail at SceneSpec, BuildPlan, Blender compilation, CompileReceipt verification, canonical structure reproducibility or `.blend` binding. Four of four native compiles passed, all four current verifiers returned 19 checks, and both B01/B02 A/B structure pairs were byte-identical at their frozen hashes. The independent result was nevertheless `REJECTED` because the budget supervisor returned only `exitCode`, `signal` and `spawnError`; it did not persist `child.pid`. Exactly one of 18 gates was false.

B55-E1 tests the smallest correction that can address that observation without rewriting history or widening the compiler change surface. The only existing production file allowed to change is `scripts/lib/budgeted-process.mjs`. SceneSpec, the immutable BuildPlan compiler, restricted CLI, Blender compiler, CompileReceipt generator/format/verifier, budget profile and B01/B02 inputs remain controls.

## Frozen intervention

The supervisor currently has SHA-256 `0c4cc332139d7e11bd33dccb0c340a3947851907fc02ab68b57be5275ec5ec40` and emits `BFS_BUDGETED_PROCESS_RESULT@0.1.0`. The correction must:

1. capture the spawned `child.pid` immediately after `spawn()`;
2. return that value as `child.pid` when it is a positive safe integer, otherwise return exactly `null`;
3. advance the result schema version to `0.2.0`;
4. leave budget validation, RSS/output/log monitoring, termination, outcome mapping and all prior fields semantically unchanged.

No PID may be inferred later from command text, timestamps, Blender output, PID arithmetic or a process-table search. The value under test is the PID returned by Node's spawn operation.

## Child-authored corroboration before Blender authorization

The single official preflight runs four zero-Blender cases through the corrected supervisor:

- a passing Node child writes its own PID and PPID, then exits 0;
- a failing Node child writes its own PID and PPID, then exits 7;
- a wall-time child writes its own PID and PPID, remains alive past a deliberately low wall budget, and is terminated and awaited;
- a nonexistent executable produces a spawn error and exactly `child.pid: null`.

For the first three cases, the child-authored PID must equal the supervisor report and the child-authored PPID must equal the preflight process PID. These probes make an accidental constant, parent PID, post-hoc lookup or arbitrary positive integer falsifiable. They do not make the supervisor trustworthy against malicious source, so exact frozen tool bytes remain part of the claim.

The preflight starts no Blender process. It also revalidates the B54 single-gap observation, unchanged production hashes, SceneSpec 22/22, two in-memory BuildPlan compilations per benchmark, frozen plan hashes, path admission and the 100 GiB reserve after a 512 MiB projection. Accepted evidence must be committed and pushed before formal authorization.

## Formal native regression

After relative-path admission and durable attempt/admission receipts, the single-use formal runner performs four fresh restricted compiles: B01-A, B01-B, B02-A and B02-B. Each budget report must be `BFS_BUDGETED_PROCESS_RESULT@0.2.0`, PASS, name the frozen Blender executable and contain a positive safe-integer `child.pid`; exit must be zero, signal/spawn error null and termination unrequested. Each native PID must differ from its simultaneously live restricted-wrapper parent PID. Values from non-overlapping runs are not required to be globally unique because an operating system may legitimately recycle a PID after exit.

The current CompileReceipt verifier remains unchanged and must return exactly 19 checks for every run. Because each CompileReceipt binds the complete `budget.report.json` by SHA-256, the PID-bearing file is immutable under that receipt; B55's independent auditor, not the current verifier, supplies the explicit PID schema/semantic check.

B01/B02 BuildPlan hashes remain `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` and `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`. Canonical structure hashes remain `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b` and `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`. A/B canonical bytes must match per benchmark. `.blend` container bytes may differ.

## Independent audit and decision rule

The auditor may not import the B55 preflight or runner. It independently reopens B54 evidence, the official PID probes, BuildPlans, budget reports, CompileReceipts, manifests, canonical structures and `.blend` files; externally invokes the unchanged current receipt verifier and Blender artifact auditor; and rejects at least 32 one-field attacks. Required PID attacks include missing, null, string, fractional and non-positive PIDs, a native PID equal to its corresponding live wrapper PID, a wrong budget-result version, and a PID-bearing report changed without the CompileReceipt file hash following it.

All 22 gates must pass for `BUDGETED_NATIVE_CHILD_PID_RECEIPT_CORRECTION_SUPPORTED`. A completed run with any false gate is `...REJECTED`. A frozen tool/process exception yields a null scientific verdict, preserves partial evidence and permanently closes B55-E1 without repair or rerun.

## Claim boundary

This is supervisor-local spawn evidence, not cryptographic or remote process attestation. Operating systems may recycle a PID after exit. The claim is that the frozen supervisor persisted the PID it received for the observed child-spawn event, corroborated by controlled child self-reporting, and that native compiler regression remained exact. B54-E1 remains immutable and rejected; B55 cannot retroactively turn a missing historical field into evidence.
