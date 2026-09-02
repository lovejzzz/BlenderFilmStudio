# RC6 moving-liquid particle-radius Data comparison attempt-66 result

Date: 2026-09-02

Verdict: `PASS_DIAGNOSTIC`; independent audit `19/19 PASS`

Attempt-66 copied the exact immutable attempt-65 cache and compared all 24
particle occupied-voxel supports with attempt-64's analysis of the
particle-radius-1.6 attempt-63 cache. It performed zero Blender, bake, render,
save, network or retained-root write operations.

At particle radius 1.8, occupied Data support fell from 1,235 to 878
(`-28.91%`). This is 2.82 percentage points worse than the 1.6 baseline's final
`-26.09%` even though retained Mesh temporal loss improved 4.65 points to
17.05%. Current occupancy and Mesh still correlate over time (`r=0.95531`), but
their changes versus baseline correlate only moderately (`r=0.47650`). The
frozen classification remains `DATA_SPATIAL_SUPPORT_SHRINK_PERSISTS`.

Result, receipt and independent-audit self hashes are
`832155637cb263fbff93f46f3e258329c0576b2a65f4062e28ca997d4fde7af5`,
`04b7099160ca2cb7a9b26a6b8b0111116d6c78809d59aa3d33b788bdbb90c105`
and `aed82a88ddef0e6fddcf010d990c1511357f759712f0888bfa46acad2a927c0a`.

This is direct evidence that occupied support is not a conserved-mass metric
and cannot by itself explain the particle-radius Mesh improvement. Radius
tuning remains closed. The next distinct simulation property may increase
`particle_number` from 2 to 3 on the exact attempt-65 configuration, while
keeping particle radius 1.8 and all Mesh, motion and threshold fields fixed.
