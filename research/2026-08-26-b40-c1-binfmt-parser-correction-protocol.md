# B40-C1 · binfmt parser correction protocol

Status: `PREREGISTERED_TOOL_CORRECTION_BEFORE_CORRECTED_TOOLING_OR_OUTPUT`  
Date: 2026-08-26  
Parent attempt: B40 `EMULATOR_GATE · INVALID_TOOL_PARSER`

## Frozen correction

B40 attempt 1 read the correct kernel record but parsed its flags incorrectly. The only implementation change permitted by B40-C1 is:

- old grammar: `^flags\s+(.+)$`;
- corrected grammar: `^flags:\s+(.+)$`;
- expected raw line: `flags: POCF`;
- expected parsed value: `POCF`.

The correction spec binds the original B40 protocol and preregistration plus the invalid result and audit by SHA-256.

## Everything else remains frozen

Host disk, 10 GiB VM memory admission, five-CPU admission, 8 GiB Docker-storage floor, zero swap, zero competing containers, x64 emulator identity, nine read-only probe classes, four expected blockers, 14 attacks and zero runtime operations remain byte-for-byte inherited from B40.

The corrected tool must produce a new evidence file and audit. It may not edit or overwrite the v0.1 invalid attempt.

## Accepted result

The strongest accepted verdict is `WORKER_HOST_CAPACITY_BLOCKED_CORRECTED_PARSER`. Passing the corrected experiment means the capacity classifier correctly reproduces a blocked host; it does not make the host eligible for B41.

No Colima configuration or lifecycle change, Docker lifecycle operation, Blender process, download, cleanup or reserve override is authorized.
