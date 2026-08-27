# B52-D12.7 · Formal audit failure and C1 correction protocol

Date: 2026-08-27

State: `FORMAL_MATRIX_COMPLETE_AUDIT_FAILED · C1_PREREGISTERED`

## Immutable formal outcome

The single-use runner completed all 12 Blender renders, 6 adapters, 12 dual consumers, 24 typed-envelope encoders and the frozen analyzer. The analyzer emitted the bounded verdict `ADAPTIVE_GATE_WITHIN_TOLERANCE_BUT_STRESS_OR_COVERAGE_NOT_SUPPORTED` with 20/21 checks and 30/30 analyzer guard mutations. Its only false check was `RADIUS3_PRODUCTION`. The adaptive candidate itself passed production, twofold headroom, risk conservatism, stress, total/per-owner retention and every registered coverage comparison.

The independent audit reproduced every canonical payload, measurement, identity, check and verdict, and process totality was true. It nevertheless rejected the run because only 28/30 repaired-self-hash attacks were caught. The runner therefore stopped before writing a receipt and preserved `run.failure.json`.

## Audit-only defect

`M10` and `M25` perform the same mutation cycle: set `result.mutationAttacks[0].passed` to false and recompute `evidenceHash`. The audit first semantically verifies that the analyzer mutation roster is complete, unique and true, but `validate()` omitted the roster array from the expected result projection. The mutated document therefore retained the expected counts and escaped. No source, array, metric, check or verdict was implicated.

## Sole permitted C1 change

C1 may copy the frozen audit into a new path and add exactly two protected expected fields: `analyzerPid` and the already semantically validated `mutationAttacks` array. It must bind the correction spec, immutable execution, result, failed audit, failure record and original tool Git blob before replay. It may write only `audit.c1.json` and `receipt.c1.json` and must reject 30/30 attacks.

No Blender, adapter, consumer, envelope or analyzer process may run. C1 cannot change the bounded verdict, the false radius-3 comparator check, any threshold, any measurement, or the absence of the original runner receipt.

Machine-readable protocol: `specs/blender-static-adaptive-risk-gate-audit-c1.v0.1.json`.
