# B40-C2 · Capacity-evidence serialization stability protocol

Status: `PREREGISTERED_SERIALIZATION_CORRECTION_BEFORE_TOOLING_OR_OUTPUT`  
Date: 2026-08-26  
Parent failure: B40-C1 `recordedAttacksMatch=false`

## Frozen defect

B40-C1's in-memory evidence contained a cross-tree object alias between the emulator observation and the decision gate's observed record. `structuredClone` preserved that alias; JSON serialization did not. The fabricated-registration attack therefore produced different failure vectors before and after persistence.

## Exact correction

B40-C2 permits four linked implementation changes only:

1. every gate `observed` value is a structured value copy;
2. every gate `required` value is a structured value copy;
3. base analysis and decision must remain identical across a JSON round trip;
4. all 14 attacks, including their ordered failure arrays, must remain identical across the same round trip.

The protocol binds B40, the B40-C1 parser correction and the rejected C1 result/audit by SHA-256. It freezes the exact divergent attack and both prior failure vectors.

## Unchanged boundary

All capacity thresholds, four expected blockers, raw observations, `flags:` parser, evidence ancestry, probe trace, forbidden operations, attack names, primary failure codes and zero-runtime boundary remain unchanged.

## Accepted verdict

The strongest accepted verdict is `WORKER_HOST_CAPACITY_BLOCKED_SERIALIZATION_STABLE`. This means a persisted receipt can be independently replayed to the same blocked decision and attack vector. It does not admit B41 or authorize any external-state change.
