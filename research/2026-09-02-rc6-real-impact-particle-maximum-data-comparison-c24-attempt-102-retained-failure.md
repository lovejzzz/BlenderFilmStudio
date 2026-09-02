# RC6 C24 attempt-102 — retained analyzer-binding failure

C24 attempt-102 is an immutable harness `FAIL 7/8`, not a diagnostic verdict.
It copied all 108 C23 cache files and measured all 36 frames with the exact
OpenVDB runtime, then rejected its own result because one adapted binding still
expected the old parameter token:

- frozen expectation: `FAIL_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C23`
- actual C23 verdict: `FAIL_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23`

The sole false check is `attempt101FailureBound`. Cache identity, complete frame
measurement, grid roster, voxel size, C19 binding, coherent baseline and onset
derivation all passed. The analyzer wrote self-hashed result
`d0390c99fa5c6e6eef324904169d71920d286a0056c2a60a444c416021e407c1`
and exited one before the runner could write a receipt or invoke the independent
auditor. Blender, bake, render, save, network and retained-root-write counts are
zero.

Do not edit, complete or rerun attempt-102. C1 may change exactly that expected
verdict token in a versioned analyzer, bind the retained failure and use fresh
attempt-103 roots. Classification logic, measurements, thresholds and physical
inputs must remain unchanged.
