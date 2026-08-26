# B40-C3 · Failure-code projection correction protocol

Status: `PREREGISTERED_FAILURE_PROJECTION_CORRECTION_BEFORE_TOOLING_OR_OUTPUT`  
Date: 2026-08-26  
Parent failure: B40-C2 `INVALID_FAILURE_CODE_PROJECTION`

## Exact correction

When the base capacity analyzer fails, B40-C3 must append every ordered code from `baseAnalysis.failures` to the wrapper failure list, followed by the summary code `BASE_ANALYSIS`. When the base analyzer passes, neither base-specific codes nor the summary may be added.

An attack passes only when its preregistered primary code appears in this projected wrapper list.

## Unchanged evidence contract

B40-C2 already proved JSON round-trip stability but failed to expose specific codes. Its value-copy decision records, pre/post-JSON equality gates, capacity policy, four blockers, raw observations, flags parser, 14 attacks, probe boundary and zero runtime operations remain unchanged.

The correction binds the C2 spec, result and audit by SHA-256. It does not retroactively accept any prior attempt.

## Accepted verdict

The strongest accepted verdict is `WORKER_HOST_CAPACITY_BLOCKED_REPLAY_STABLE`: the host remains ineligible, and persisted evidence must reproduce all 14 expected attack reasons exactly.
