# B59-G0-R3-C1 · Actual-capture timing correction

Date: 2026-08-29
Status: IMPLEMENTED — timing and A05 validated; independent control blocked by separately preregistered C2
Formal R3 root at registration: absent

## Failed rehearsal evidence

A disposable four-sample rehearsal reduced only the timing interval from 120 seconds to one second and total span from 360 seconds to three seconds. It returned `BLOCKED_HOST_STABILITY`: 13/14 pre-audit gates, 13/15 final gates and 19/20 attacks.

Observed capture intervals were `998`, `1008` and `994` ms. Total span was exactly 3,000 ms. Each sample was only 32–40 ms late relative to its fixed scheduled slot, but the late completion of one sample shortened the next actual interval. This proves the fixed-slot scheduler does not enforce the declared actual-capture interval.

A05 also failed to reject because its hard-coded forged interval was exactly 1,000 ms, equal to the rehearsal minimum rather than below it.

- Rehearsal `results.json` SHA-256: `d7c99fe5b8c06b8614e8519ffad4177c6ac2f36d31fae04299cbbdc13927c097`
- Rehearsal `audit.json` SHA-256: `4ea9e43eb5ea254b8332c0ce48b553d93c8052a0a66e6d9be946fa8c022933d3`
- Rehearsal spec SHA-256: `089c6917ab88aa5fc55921d22bb3b7f948106ff715b40810a3fd0e5e630aba07`
- Base formal spec SHA-256: `7a32911b87487dc1cb9f8d261931f6c23f7c9e5222b681412106f7b2606326da`
- Tool commit: `f2a3c8dc24597d5901263d5b6959a8eabc97e8b8`

The failed rehearsal files are retained under `experiments/codex-host-stability-longitudinal-rehearsal-v0-1`; they are not admission evidence.

## Frozen correction

For sample 1, due time remains the experiment start. For every later sample, due time becomes:

`max(start + (index - 1) × minimumInterval, previousActualCapture + minimumInterval)`

The runner records this corrected due time as `scheduledAt`; lateness remains actual capture minus corrected due time. Resume behavior reads and verifies the prior immutable sample before calculating the next due time.

A05 must forge the second sample at exactly `minimumIntervalMilliseconds - 1` after the first sample. It must be rejected for every positive configured interval, including the shortened rehearsal variant.

No sample count, production interval, total span, lateness, resource threshold, process threshold, crash rule or admission rule changes. A second disposable rehearsal must pass 15/15 gates and 20/20 attacks before formal R3 may start.
