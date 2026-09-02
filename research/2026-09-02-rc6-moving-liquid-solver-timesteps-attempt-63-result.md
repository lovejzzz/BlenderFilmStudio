# RC6 moving-liquid solver minimum-timesteps attempt-63 result

Date: 2026-09-02

Verdict: retained physical `FAIL`; independent audit `16/16 PASS`

Attempt-63 returned to the better attempt-59 configuration and changed only
fluid-domain `timesteps_min` from 1 to 2. Surface distance stayed 2.0 cells,
effector subframes stayed 1, maximum timesteps stayed 4 and CFL stayed 2.0.

The extra minimum solver step was directionally useful but insufficient.
Maximum temporal Mesh loss improved from 23.03% to 21.70% (1.33 percentage
points), and maximum source-relative error improved from 24.00% to 22.97%.
Temporal loss still exceeded the unchanged 15% ceiling, so 16 of 17 physical
checks passed. Exact motion, one positive manifold liquid body, zero radial/
floor/rim escape, 33.72 mm cup-local liquid motion and the exact 72-file cache
all remained valid.

Data time increased from 251.55 to 270.74 seconds (`+7.63%`); Mesh took 2.93
seconds. Process counts remained one Blender, one Bullet, one Data and one Mesh
bake with zero render, save, network or engine write. Result, receipt and audit
self hashes are
`2b671ca4406a5c2b934f303aa394691738a2a53ad9be0b55df1f841e284c1e1c`,
`d2ae5e4e4618fa8830ed42c62ff2aebf1a541aa065204530897e6f8cdc129439`
and `26d9a50f0c6ed91334dfc01fa169b79e5927102fc125ae26e7fb247abbb8f44b`.

No `timesteps_min=3`, CFL or maximum-timestep change is allowed. Before
selecting simulation particle radius as the next different physical degree of
freedom, a zero-Blender copied-cache comparison must determine whether the
small improvement is already present in Data support.
