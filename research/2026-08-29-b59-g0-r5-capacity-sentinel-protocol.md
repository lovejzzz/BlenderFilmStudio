# B59-G0-R5 · Active host-capacity sentinel protocol

Date: 2026-08-29
Status: PREREGISTERED — TOOL AND INSTALLATION ABSENT
Parent commit: `5f1515cab482b5339084ae3ca5f1a16ae37fbc43`

## Gap

The existing fail-closed disk guard protects most experiment commands and the production Blender compiler at job admission. It preserves a 100 GiB reserve after projected writes, but it does not observe the machine between jobs and cannot warn about a rapid background loss such as R3's 3.33 GB in six minutes.

R5 adds a separate passive sentinel. It does not weaken or replace the existing per-job guard. Its purpose is early warning, bounded trend evidence and an explicit recovery checkpoint before the production workflow resumes.

## Frozen behavior

A user LaunchAgent runs every 900 seconds and at load. Each invocation reads only:

- APFS available bytes for `/`;
- allocated bytes and entry count of the Codex browser temporary filesystem;
- logical and allocated bytes plus device/inode identity for the two active Colima sparse disks;
- its own prior bounded state.

It performs no Docker command, Blender process, network/model call, cleanup, deletion, compaction or service restart. It atomically replaces `latest.json`, `history.json` and, when needed, `alert.json` under one exact state root. History is capped at 192 samples, representing 48 hours at the nominal interval, and each state file is capped at 256 KiB. Temporary replacement files use exact state-root paths and are renamed atomically; they are not allowed to escape the root.

The LaunchAgent and state are user-scoped and reversible. Uninstall may boot out only label `com.blenderfilmstudio.capacity-sentinel` and remove only its exact plist. Historical state is retained by default; deleting it requires a separate explicit request.

## Frozen classifier

Severity is the highest applicable condition:

1. `SENSOR_ERROR`: a required observation or prior-state validation fails.
2. `EMERGENCY_CAPACITY`: available bytes below 140 GiB, or browser temp at/above 1 GiB.
3. `CRITICAL_CAPACITY`: available bytes below 180 GiB.
4. `WARNING_CAPACITY`: available bytes below 250 GiB.
5. `WARNING_RAPID_LOSS`: at least 10 GiB loss across a prior sample 10–30 minutes old, or at least 25 GiB loss across a prior sample 18–30 hours old, or browser temp at/above 64 MiB.
6. `HEALTHY` otherwise.

At `WARNING_RAPID_LOSS` or worse, the recorded production recommendation is fail-closed: do not begin a new Blender/worker job, preserve evidence, remeasure and attribute before any cleanup. The sentinel may issue a local macOS notification only on severity transition or after six hours at the same non-healthy severity. Notification failure is recorded but cannot change the scientific classifier.

## Recovery boundary

R5 never tries to make a warning disappear automatically. Recovery means:

1. production remains paused by policy;
2. exact high-growth sources are identified read-only;
3. any cleanup or service transition requires a separately authorized exact target;
4. the sentinel subsequently records two `HEALTHY` samples at least 15 minutes apart;
5. the existing production disk guard independently passes its projected-write check.

D2 demonstrates that exact Colima stop/start restoration can be guarded when separately authorized, but it is not installed as an automatic remedy.

## Verification

Before installation, pure self-tests must cover every capacity boundary, rapid/long loss, stale history, browser thresholds, 192-sample truncation and state-size ceiling. The independent auditor must reject all 15 registered mutations. A dry installation audit must match label, interval, absolute runtime paths, arguments and state root exactly.

After tools and template are committed and pushed, the installer may place the one exact plist in `~/Library/LaunchAgents`, bootstrap it into `gui/501`, trigger one live sample and verify the launchd service, state self-hashes, file bounds and zero prohibited actions. Passing R5 establishes an active capacity warning mechanism; it does not by itself prove long-term retention or close Gate 0.
