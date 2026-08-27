# B52-D11.1-C1 — Audit NumPy boolean serialization correction

Date: 2026-08-27

Status: `PREREGISTERED_AFTER_AUDIT_EXCEPTION_BEFORE_CORRECTION_TOOL`

## Retained failure

The single immutable B52-D11.1 formal matrix completed and wrote:

- `run.receipt.json` SHA-256 `643717651d4dafb48c87c0527d682ea224e8ab80f6a81a8d153e8c4d1ec8a9fc5`;
- `results.json` SHA-256 `dd08142a2af855ddc287eecb84f5de722afb03a9ae6aef8a33fd3279d660329f`;
- result verdict `BLENDER_NEAREST_INTEGER_TEMPORAL_RECOVERY_HOLDOUT_SUPPORTED` with 71/71 registered attacks and 81/81 unique child PIDs.

The Git-frozen audit tool SHA-256 `feb1214b00b16e833db2e65f38308d4c82b76f8952aadf62ad0a72670fbabb4a` then replayed the retained files but stopped before writing `audit.json`:

```text
TypeError: Object of type bool is not JSON serializable
```

The exception arose while hashing the audit body. The `quantizerExact` value copied into a human-readable replay row retained NumPy's scalar `bool_` type from an `np.all(...)` expression. Every decision value had already been reduced through Python `all(...)`; the crash is an output-interface defect, not a failed experimental gate. No audit file exists at correction preregistration.

## Only permitted correction

Create a new tool path, `scripts/audit-b52-d11-1-nearest-integer-recovery-c1.py`, from the frozen audit bytes and change only:

1. the replay-only `quantizerExact` field to `bool(quantizer_checks[-1])` before JSON serialization;
2. the report schema suffix from the original audit schema to `...AuditC1.v0.1`;
3. a correction-provenance object binding this protocol, the original frozen audit SHA-256, the C1 tool Git commit and the two immutable formal input hashes.

The original audit tool must remain byte-identical. C1 may not change quantization, accumulation, semantic, control, process, diagnostic, evidence, base-failure or verdict logic. It may not render, regenerate a cell, rewrite `results.json` or `run.receipt.json`, mutate a diagnostic, relax a gate, change an attack, or create a second formal root.

## Execution and decision

The C1 tool must be committed before execution. It then reads the existing formal root once and writes only the previously absent `audit.json`. PASS requires:

- both immutable formal input hashes above remain exact;
- the original thirteen-tool accepted preflight remains exact;
- the original audit file still has SHA-256 `feb1214b...`;
- independent replay agrees with every result evidence value, verdict and base failure;
- all 48 PNG/sidecar pairs and all 81 process identities pass;
- the C1 provenance block matches its Git-frozen source.

If C1 fails for any other reason, retain the failure and preregister another correction. Do not edit or rerun B52-D11.1.

## Pre-tool state

At this preregistration commit, `scripts/audit-b52-d11-1-nearest-integer-recovery-c1.py` and the formal `audit.json` are absent.
