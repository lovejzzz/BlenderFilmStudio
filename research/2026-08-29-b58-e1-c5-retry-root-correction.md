# B58-E1-C5 · Retained-failure retry-root correction

Date: 2026-08-29
Status: PREREGISTERED AFTER OFFICIAL PREFLIGHT REJECTION, BEFORE RETRY OUTPUT

## Counterexample

The first official B58 preflight invocation submitted `c8647647743e5e0ba55eb94b4b330ee693d8997a` instead of the actual tool-freeze commit `c86476405af442b419141e69609bfaed59c7f3cd`. The first B57 child correctly returned a self-hashed `REJECTED / RELEASE_COMMIT` receipt before any Blender process. C4 then stopped the sequence and preserved the diagnostic; no outer accepted receipt, attempt root or formal root exists.

The failed receipt is frozen at `experiments/restart-safe-production-orchestrator-preflight-v0-1/production-preflights/BASELINE_B01/preflight.json`, SHA-256 `5b49bd337055e088efa091dba3228b4296c66861108294e0d86d0cd28ec8cec5`, self-hash `151776edd83415305481eb9e19a7e5386fbb8d54e657309a2dcd98a045e427a9`. This is an operator input error, not evidence against B57 or C4, and it must not be deleted or overwritten.

## Frozen correction

The v0.1 preflight root is permanently non-promotable. One retry is authorized only at the three fresh, disjoint v0.2 roots:

- `experiments/restart-safe-production-orchestrator-preflight-v0-2`
- `experiments/restart-safe-production-orchestrator-attempt-v0-2`
- `experiments/restart-safe-production-orchestrator-v0-2`

Before v0.2 preflight, the caller must prove the v0.1 failure receipt byte hash, self-hash, status, reason, submitted bad commit and zero-Blender operations. Before formal materialization, runner and independent auditor must reopen the same retained failure and require exact v0.2 root bindings. Any reuse of v0.1 or disappearance/mutation of its receipt fails closed.

C5 changes no production compiler, job ledger, DAG, process count, fault injection, recovery rule, disk threshold, formal gate denominator or verdict threshold. It adds two attacks for failed-evidence mutation/removal and v0.1 root reuse.
