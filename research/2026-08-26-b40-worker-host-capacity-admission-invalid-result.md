# B40 attempt 1 · Worker host capacity admission invalid result

Verdict: `EMULATOR_GATE`  
Status: `INVALID_TOOL_PARSER`  
Runtime operations: `0`

## Frozen ancestry

Protocol commit: `8c39b715e7e2bacae81ca1ab9b2570472cf73fde`  
Tool freeze commit: `3df41bc3b176a08ee0f65f2fb65e91e46f66a3a5`  
Spec SHA-256: `fd21c27801a83f542a4aaa498fbc61867b3116509bb6e43769d83873146850ca`

## Observed classification

Four preregistered capacity blockers reproduced:

- `HOST_DISK_RESERVE`;
- `VM_MEMORY_CAPACITY`;
- `VM_CPU_CAPACITY`;
- `DOCKER_STORAGE_CAPACITY`.

The runner unexpectedly added `X64_EMULATOR`. Inspection of the raw read-only probe showed:

```text
enabled
interpreter /usr/bin/qemu-x86_64
flags: POCF
```

The frozen parser looked for a whitespace-delimited key named `flags`, but the kernel binfmt record uses the literal key `flags:`. It therefore stored `flags=""` and falsely blocked the emulator gate.

## Decision

This attempt is invalid because the measured source and parsed observation disagree. The four capacity blockers are not promoted as an accepted B40 verdict from this run, even though they matched expectation. The result remains `EMULATOR_GATE`, and the independent audit correctly fails because the base analysis failed and its recomputed 14-attack vector cannot match the empty accepted-run attack vector.

Result SHA-256: `7233f2782032bb9dd1370eaaa1558be10f0cdb861fc83582af40832066a9e5e0`  
Audit SHA-256: `dc067337e1e47d66792c5d3b60101f02801668fe7b620d286514c26f6a1b38d5`

## Correction boundary

B40-C1 must bind this failed result and change only the binfmt parser grammar from a whitespace-only `flags` key to the exact literal `flags:` key. All capacity thresholds, expected blockers, evidence ancestry, probes, zero-runtime boundary and attacks remain unchanged.

No Colima mutation, container lifecycle operation, Blender launch, image/archive download or cleanup occurred.
