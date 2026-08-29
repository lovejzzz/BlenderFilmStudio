# B59-G0-R2 · Post-restart Codex host readmission protocol

Date: 2026-08-28
Status: COMPLETED — ADMITTED FOR LIGHTWEIGHT WORK
Parent commit: `6e02fc2e7729ecfd57380adf27953350f95e2270`

## Purpose

R1 proved that cache remediation restored the disk gate, but the current long-lived Codex process tree still exceeded the 4 GiB ceiling. R2 tests a user-performed full Codex restart without reusing the R1 root or treating a new turn as proof of restart.

## Frozen restart boundary

The pre-restart Codex main process is PID 92848, launched locally at `Fri Aug 28 10:55:25 2026`. R2 requires exactly one current main process, a PID different from 92848 and complete absence of PID 92848. Merely lowering RSS in the old process, opening a new turn or relaunching a renderer is insufficient.

The runner records current main PIDs and a restart-boundary verdict. The existing `CODEX_MAIN_PROCESS_COUNT` gate now also requires this boundary when the selected spec contains `restartBoundary`. The auditor independently replays the current PID set. New attack A25 reseals a candidate that claims the old PID as current; it must be rejected. Baseline and R1 specs retain their original 24 attacks and behavior.

## Preregistered correction C1: runtime version transition

The restart installed Codex `26.825.32147 (7303)`, while the crash report remains evidence about `26.820.80927 (7271)`. Treating those two identities as equal would reject a valid upgrade and conflate crash provenance with the runtime under test.

Before any formal R2 root existed, C1 added `currentRuntimeExpectation` to the R2 spec. `CRASH_SIGNATURE_EXACT` remains bound to the immutable crash-report version. `CURRENT_CODEX_VERSION_EXACT` is now bound to the separately frozen post-restart runtime version. Baseline and R1 omit the new field and therefore retain their original behavior. Attack A08 still mutates the observed current version and must be rejected.

The current runtime expectation is also bound to `/Applications/ChatGPT.app/Contents/Info.plist`, SHA-256 `4d8b6390cf82eec96777e5cdd22993536f7fc5ef0b44809a6e1c377d0f563ce7`, and bundle identifier `com.openai.codex` as observed at `2026-08-29T04:02:47Z`. This correction changes no resource threshold and grants no admission.

## Unchanged gates

R2 preserves the same 20 gates, disk/memory/renderer/RSS ceilings, bounded output, parent-evidence binding and zero-operation ceilings. It targets only fresh root `experiments/codex-host-stability-post-restart-readmission-v0-1`. It starts no Blender, browser automation, network, model, Docker, cleanup or signal operation.

Before the formal run, an exact browser temporary-filesystem remediation may be performed under the separately preregistered C1 remediation record. The formal runner must observe the resulting host state; cleanup remains outside the formal experiment and does not alter its zero-operation ceiling.

## Decision

`ADMITTED_FOR_LIGHTWEIGHT_WORK` requires 20/20 gates, 25/25 attacks, exact old-PID absence, a valid synthetic control and complete independent replay. Admission permits only the next preregistered repeated-observation phase; it does not close Gate 0 or authorize B58.

## Formal result

The single-use formal R2 run was captured at `2026-08-29T04:06:48.122Z` and independently audited without rerun or overwrite.

- Final verdict: `ADMITTED_FOR_LIGHTWEIGHT_WORK`
- Gates: `20/20`
- Registered attacks rejected: `25/25`
- Failed gates: none
- Current Codex: `26.825.32147 (7303)`, main PID `26962`
- Previous PID `92848`: absent
- Codex-tree RSS: `3,917,627,392` bytes
- Maximum renderer RSS: `845,479,936` bytes across four renderers
- Available disk: `153,949,310,976` bytes
- Disk headroom above the frozen threshold: `41,743,290,368` bytes
- System-wide memory free: `85%`
- `results.json` SHA-256: `2bb7ecc7be213dac754d2c81a19da24630659b0d34cba53d308ac424056c4519`
- `audit.json` SHA-256: `02a28904b285348c20fe6e24c14c57e127c5cc59e736d40b01e430e5294f8810`

This result opens only the preregistered repeated-observation phase. It does not establish long-horizon RSS stability, prevent recurrence of browser temporary-file leakage, or authorize Blender/B58 execution.
