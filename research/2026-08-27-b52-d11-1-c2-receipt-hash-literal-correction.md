# B52-D11.1-C2 — Receipt SHA-256 literal correction

Date: 2026-08-27

Status: `PREREGISTERED_AFTER_C1_IDENTITY_REJECTION_BEFORE_C2_TOOL`

## Retained C1 rejection

B52-D11.1-C1 was frozen at commit `e7a8ef5cb59e89f0fbc4462a032bf58adcdaf33c`. Its tool SHA-256 is `3acce75131ccbbe8c240d1e8dcd362a7743d41f90340e1ed98739f2c557f90f6`.

C1 stopped before loading result JSON, replaying any cell or writing `audit.json`:

```text
RuntimeError: B52-D11.1-C1 immutable formal input identity mismatch
```

The cause is a preregistration transcription error. C1 froze a purported receipt SHA-256 with 65 hexadecimal characters:

```text
643717651d4dafb48c87c0527d682ea224e8ab80f6a81a8d153e8c4d1ec8a9fc5
```

A SHA-256 digest must contain exactly 64 hexadecimal characters. The immutable formal files were rehashed independently with macOS `shasum -a 256`, OpenSSL `dgst -sha256` and Blender's bundled Python `hashlib`; all three implementations agreed:

- `results.json`: `dd08142a2af855ddc287eecb84f5de722afb03a9ae6aef8a33fd3279d660329f`;
- `run.receipt.json`: `643717651d4dafb48c87a5925391f06ef30ce97f62a8ab321d4c4aba62d0f443`.

Both are 64 characters. File modification times remain those of the one formal run. No audit file exists at C2 preregistration.

## Only permitted correction

Create `scripts/audit-b52-d11-1-nearest-integer-recovery-c2.py` from the exact frozen C1 bytes and change only:

1. `RECEIPT_SHA256` to the independently converged 64-character digest above;
2. correction identifiers from C1 to C2: tool path, protocol path/hash/commit, report schema suffix and provenance labels.

The C1 native-boolean cast and every replay, gate, evidence, process, diagnostic, base-failure and verdict expression remain byte-for-byte otherwise. The original audit and C1 tool remain immutable. C2 may not render, regenerate, rewrite or delete any formal artifact.

## Decision

Commit the C2 tool before execution. It may write only the absent `audit.json`. PASS requires its own Git identity, this protocol's Git identity, both original audit identities, both immutable formal input hashes, 48 diagnostic pairs, 81 process identities, evidence equality and verdict consistency.

Any further failure is retained and requires another preregistered correction. The formal experiment is never rerun.

## Pre-tool state

At this commit, `scripts/audit-b52-d11-1-nearest-integer-recovery-c2.py` and formal `audit.json` are absent.
