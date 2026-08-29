# B59-G0-R6 · Unattended capacity-retention protocol

Date: 2026-08-29
Status: PREREGISTERED — OBSERVATION ACCUMULATING
Parent commit: `8bee7c6a4ed0172a7be13a1c29ee0317cdf9840a`

## Question

After the active sentinel has run independently for at least one hour, does its complete, non-cherry-picked history show healthy capacity retention, bounded browser and Colima allocation, correct launchd cadence, and continued Codex runtime/crash stability?

## Eligibility before evidence creation

The runner must first inspect the live state read-only. It returns `WAIT_UNATTENDED_RETENTION` and creates no formal root until all of these are true:

- at least five samples exist;
- first-to-last span is at least 3,600 seconds;
- latest sample is no more than 1,200 seconds old;
- the launchd service remains loaded.

Once eligible, the runner snapshots the entire history, not a favorable subset. Subsequent samples cannot be appended to that immutable snapshot. The source history may continue running normally.

## Frozen gates

- Every adjacent sample interval must be 600–1,200 seconds.
- Every sample must independently recompute to `HEALTHY`; warning, critical, emergency and sensor-error samples all fail.
- Available bytes must remain at or above 250 GiB.
- Positive first-to-last host loss, normalized per elapsed hour, must not exceed 1 GiB/hour; no single interval may lose more than 1 GiB.
- Browser temporary allocation must remain below 64 MiB and first-to-last growth below 64 MiB.
- Positive combined Colima sparse-disk allocation growth, normalized per elapsed hour, must not exceed 1 GiB/hour.
- All recorded prohibited-action counters must be zero.
- The installed plist must remain byte-exact, launchd must report interval 900 seconds, run count at least the snapshotted sample count and last exit 0.
- Codex must still have exactly one main process at PID 26962, the same app version/hash/bundle identity, a process start preceding the first sample, and zero new `ChatGPT*.ips` reports since the first sample.

The current-process/start-time check plus absence of a crash report is stronger than a final PID snapshot alone, but it cannot prove every possible unreported transient. That limitation remains explicit.

## Evidence and interpretation

The runner writes a byte-exact source snapshot plus self-hashed start/results receipts into a fresh formal root. The auditor does not import the runner; it recomputes the history, process, crash and launchd gates and must reject all 15 registered attacks.

Passing R6 establishes `ONE_HOUR_UNATTENDED_RETENTION_ADMITTED`. It is a required Gate 0 closeout input, not the final closeout itself and not permission to skip B58 preflight. A failed gate is retained without relaxing thresholds or selecting a different time slice.
