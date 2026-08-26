# B40-C1 · Corrected parser result rejected by serialization aliasing

Runner verdict: `WORKER_HOST_CAPACITY_BLOCKED_CORRECTED_PARSER`  
Independent audit: `FAIL`  
Status: `REJECTED_IN_MEMORY_ALIASING`

## What passed

The literal binfmt parser correction worked: `flags: POCF` became `flags="POCF"`, the emulator gate passed, and the four preregistered capacity blockers remained:

- `HOST_DISK_RESERVE`;
- `VM_MEMORY_CAPACITY`;
- `VM_CPU_CAPACITY`;
- `DOCKER_STORAGE_CAPACITY`.

The in-memory runner reported 14/14 attacks and zero runtime operations.

## Why the independent audit failed

The capacity classifier stored the emulator observation object directly inside the decision object. In memory:

```text
observations.vm.emulator
decision.gates.x64Emulator.observed
```

were two references to the same object. The “fabricate emulator registration” attack mutated the observation and unintentionally mutated the recorded decision at the same time, so the runner observed only `EMULATOR_REGISTRATION`.

JSON serialization does not preserve that cross-tree alias. After the audit loaded the result file, the same attack changed only the observation. The unchanged decision then also failed canonical recomputation, producing:

```text
EMULATOR_REGISTRATION
CAPACITY_DECISION
```

All 14 audit attacks still rejected their candidates, but the replay vector differed at attack 11. Therefore `recordedAttacksMatch=false` and the audit correctly returned `FAIL`.

Result SHA-256: `a59acf6fdea2bd2d82ad6f18b9ee5d7aa9f632202f4c96dd1d61c1487b10d1d3`  
Audit SHA-256: `8a05a54f99cb63b7f7408c5171dbac2d6b80f7c3cd0586ed267803c67be629ac`

## Correction boundary

B40-C2 must make gate `observed` and `required` records value copies, not shared references, and must require the full 14-attack vector to be byte-identical before and after `JSON.stringify`/`JSON.parse`. Capacity policies, raw observations and the four-blocker decision remain unchanged.

The B40-C1 runner verdict is not promoted. No runtime operation occurred.
