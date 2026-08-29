# B58-E1-C7 · Immutable-evidence re-audit correction

Date: 2026-08-29
Status: PREREGISTERED AFTER COMPLETE BOUNDED FORMAL, BEFORE RE-AUDIT OUTPUT

## Complete formal observation

The v0.3 formal matrix completed all intended work with seven real Blender 5.2 starts: four native compiles, including one retained controlled interruption and one retry, plus three preferred artifact audits. Three native compiles succeeded. Render, model, network and Docker operations remained zero. Exit-86 recovery skipped the completed compile, the interrupted attempt was non-promotable and retained, and the live-process case refused a duplicate spawn.

The old independent audit returned 31/34 gates and 71/72 original attacks. All C1-C6 correction attacks passed. The immutable attempt/formal tree contains 141 files with canonical tree SHA-256 `c7f5ed6bddd030be24d86a8592e5dd80e24832de0ac72e0cd6fad1cf87bbae89`.

## Two verifier defects

All three completed jobs have valid, self-hashed `PASS` final receipts. Their terminal `JOB_FINALIZED` events store the binding at `payload.receipt.receiptHash`. The auditor instead reads `payload.finalReceipt.receiptHash`; that nonexistent field makes `row.exact` false and fails `BASELINE_B01_COMPLETE`, `RECOVERY_FINAL_RECEIPT_VALID` and `B02_RECOVERY_COMPILE_AND_VERIFY_VALID` together.

Attack A64 replaces an observed log hash with 64 zeroes. The accounting validator checks only the 64-hex shape, so the mutation remains syntactically valid. It must also require equality with the immutable observed log hash.

## Frozen correction

C7 may change only the independent auditor and add a re-audit runner. It must not rewrite, regenerate or append inside either v0.3 evidence root and must start zero Blender processes. The corrected auditor binds the actual `payload.receipt` field and binds `logSha256` to an `expectedLogSha256` copied from immutable evidence. Two explicit C7 attacks mutate those bindings independently.

The re-audit runner must first prove the 141-file tree hash and old audit/results/receipt hashes, then run the corrected independent auditor into the fresh output root `experiments/restart-safe-production-orchestrator-c7-reaudit-v0-1`. Admission requires 34/34 gates, 72/72 original attacks, 2/2 C7 attacks, all prior correction attacks and `RESTART_SAFE_PRODUCTION_ORCHESTRATOR_SUPPORTED`.
