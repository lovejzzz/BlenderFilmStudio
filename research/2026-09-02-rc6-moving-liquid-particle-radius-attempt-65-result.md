# RC6 moving-liquid simulation particle-radius attempt-65 result

Date: 2026-09-02

Verdict: retained physical `FAIL`; independent audit `16/16 PASS`

Attempt-65 preserved the complete attempt-63 two-step baseline and changed only
Mantaflow simulation `particle_radius` from 1.6 to the preregistered midpoint
1.8. Mesh particle radius remained 2.5, surface distance remained 2.0 cells,
the cup used one effector subframe, and C5F96 motion remained exact.

The change produced the strongest moving-liquid improvement so far. Maximum
temporal Mesh loss fell from 21.70% to 17.05% (4.65 percentage points), while
maximum source-relative error improved from 22.97% to 22.10%. The unchanged
15% temporal ceiling still failed, so 16 of 17 physical checks passed. All 24
frames remained one positive manifold liquid body with zero radial, floor or
rim escape; cup-local liquid centroid motion remained measurable at 26.23 mm.

Data and Mesh took 265.50 and 2.92 seconds. Process counts were exactly one
Blender, one Bullet, one Data and one Mesh bake with zero render, save, network
or engine write. Result, receipt and independent-audit self hashes are
`687a2796f7b79878648419cd8efa943e667c83b2039bb9e6f9cc04d018a01d52`,
`f3a741cca5aaa9bbc1dd66344845b4548c5a70d8c9e43e4863ed7b60e89d82ad`
and `a5b23c9fab6d5bf53f1b1a6302aa4c1155d6c7aa7215b630617ca2c83030ae41`.

No second particle-radius value is allowed. Before selecting another distinct
simulation property, copy and compare this immutable Data cache against
attempt-63/64 to determine whether the 4.65-point Mesh response begins before
surface reconstruction.
