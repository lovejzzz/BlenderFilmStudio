# B59-G0-R6-C1 · Span-normalized A09 correction protocol

Date: 2026-08-29
Status: COMPLETE — ADMITTED
Parent evidence: B59-G0-R6 `INVALID_UNATTENDED_RETENTION`

## Counterexample being corrected

R6 froze five natural launchd samples spanning 3,600.821 seconds. All 11 producer gates and all nine independent integrity/live checks passed, but A09 was not rejected. The original mutation subtracted a fixed `maximumDiskLossRateBytesPerHour + 1` from the first sample. Since the actual span was longer than one hour, dividing that fixed loss by the real duration produced a rate slightly below the frozen hourly ceiling. The fourth-to-fifth step also remained below the independent single-interval ceiling.

This invalidates the audit control, not the healthy host observation. The original evidence and final verdict remain unchanged.

## Frozen correction

C1 uses a fresh formal root and snapshots the complete source history present at execution. It retains every R6 production threshold, source, runtime identity, gate, attack ID, byte ceiling and prohibited-resource rule.

The only allowed semantic correction is A09's mutation magnitude:

`breachLossBytes = floor(maximumDiskLossRateBytesPerHour * actualSpanMs / 3,600,000) + 1`

The candidate last available value becomes `first.availableBytes - breachLossBytes`. The auditor must independently prove that the recomputed positive hourly loss is strictly greater than the frozen ceiling before counting the attack. No epsilon, threshold relaxation or favorable history subset is permitted.

## Execution discipline

- The existing runner and auditor gain an explicit safe repository-relative `--spec specs/name.json` selector; omission continues to select the immutable original R6 spec.
- The C1 formal root must not exist before execution.
- Parent R6 results and audit hashes must match the preregistered INVALID evidence.
- The live history must still satisfy at least five samples, at least 3,600 seconds, 600–1,200 second cadence and latest age at most 1,200 seconds.
- Runner admission still requires all 11 pre-audit gates. Auditor admission still requires all 12 gates and 15/15 attack rejections.

Passing C1 establishes `ONE_HOUR_UNATTENDED_RETENTION_ADMITTED` for the full frozen C1 history. It supplies one required input to Gate 0 closeout; it does not itself close Gate 0 or authorize B58.

## Recorded outcome

C1 froze the same complete five-sample history as R6, preserving the 3,600.821-second observation and all healthy host metrics. The runner passed 11/11 pre-audit gates. The independent auditor passed all nine integrity/live checks and rejected 15/15 attacks, including the corrected span-normalized A09. Final verdict: `ONE_HOUR_UNATTENDED_RETENTION_ADMITTED`.

Results and audit SHA-256 are `f0c246f1b2f295cbf07b0a2dc1f3e948677f2a16c213142551582355b5a81045` and `0643f75e223f35be81dfa11f4255d54044b369dc85da3fcb3bc3dd46565598db`. The original R6 INVALID evidence remains unchanged.
