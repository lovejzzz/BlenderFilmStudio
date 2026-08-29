# B59-G0-R6 · Unattended capacity-retention protocol

Date: 2026-08-29
Status: COMPLETE — INVALID AUDIT CONTROL, HOST OBSERVATION PRESERVED
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

## Recorded outcome

The full five-sample source history spanned 3,600.821 seconds. The runner passed all 11 pre-audit gates with `ADMITTED_PENDING_AUDIT`; host disk loss was 294,092,800 bytes (294,025,745.795 bytes/hour), browser growth was zero, combined Colima allocation growth was 602,112 bytes, all prohibited actions were zero, the required PID remained live and no new crash report appeared.

The independent audit verified every file-integrity and live-continuity check but rejected only 14/15 registered attacks. `A09_DISK_RATE_BREACH` incorrectly used a fixed loss of `maximumDiskLossRateBytesPerHour + 1`; because the real span was slightly longer than one hour, its normalized loss rate remained below the frozen hourly ceiling and its final single-interval loss also remained below the separate 1 GiB limit. The final verdict is therefore `INVALID_UNATTENDED_RETENTION`, not a host failure and not admission. The immutable evidence remains under `experiments/host-capacity-retention-v0-1`.

Any correction must use a fresh formal root and preregister a span-normalized A09 mutation. It may not alter the production thresholds, remove this failed audit, or select a more favorable source-history subset.
