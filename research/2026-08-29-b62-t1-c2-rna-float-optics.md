# B62-T1-E1-C2 · Blender RNA float optical comparison

Date: 2026-08-29  
Status: PREREGISTERED — v0.2 retained; no C2 tool change or v0.3 root exists

## Retained failure

The C1 retry passed dual BuildPlan compilation and the real Blender compile, producing a 337,418-byte derived scene. The independent Blender reopened that exact scene but stopped at the optical scalar predicate before pose, preservation or Node audit. No render occurred. The v0.2 root is frozen as 9 files, 651,534 bytes and tree SHA-256 `3ed5e9d0…`.

## Root cause

The plan expresses `clipStart=0.05`. Blender's camera RNA stores that field as float32, so both the compiler's post-assignment observation and the reopened scene report `0.05000000074505806`. The absolute difference is about `7.45e-10`. Lens 65 mm and clip end 200 m remain exact.

The independent auditor incorrectly used decimal equality between the JSON binary64 value and Blender's float32 value. This is a representation contract bug, not a camera mutation.

## Authorized correction

C2 changes only the independent optical predicate. Lens, clip start and clip end must be within `1e-6` of the BuildPlan and within `1e-9` of the compiler's observed post-assignment values. The independent report must expose each observed value and error. Runner and Node auditor bind this correction, the retained v0.2 tree, and use only fresh v0.3.

The BuildPlan compiler and Blender compiler remain byte-identical. Camera values, 96 pose samples, pose tolerance, assembled identity correction, 20 gates, 12 attacks, process/resource budgets and supported verdict do not change.
