# RC6 C23 preregistration — impact-liquid particle ceiling

## Frozen question

On the exact retained C18 high-speed basketball/cup impact, does changing only
Mantaflow `particle_maximum` from 16 to 12 reduce the same-transition Data/Mesh
expansion enough to pass the unchanged physical gate?

This is a falsifiable density-ceiling test, not a claim that fewer particles
must be better. Blender's bound `adjustNumber` logic exempts the protected
surface region when deleting excess particles, so the value may improve the
result, regress it, or have no visible downstream effect.

## Frozen causal baseline and single change

- Return to exact C18: simulation radius 1.8, particle minimum 8, particle band
  width 4, fractional-obstacle threshold/distance 0.10/0.25, CFL 2 and adaptive
  timesteps 2/8.
- Change only `particleMaximum 16 → 12`, the integer midpoint above the
  unchanged minimum 8.
- Preserve exact retained R40 Bullet motion, frames 1–36, Preview resolution
  96, APIC, Mesh settings, domain, flow/effector geometry and all 27 physical
  checks.
- C21 is binding evidence that the rejected C20 radius 1.6 run amplified the
  same velocity/Mesh/particle onset frames 24/24/25 rather than advancing them.
  C22 binds the Blender source path that selected this separate Data-layer
  degree of freedom.

## Frozen execution and resources

Use exactly one Blender start, one bounded Bullet bake, one fluid Data bake and
one fluid Mesh bake in fresh attempt-101 roots. Use the accepted existing
binary; do not build. The work/evidence ceilings remain 2 GiB / 64 MiB with a
100 GiB free-space reserve. Render, `.blend` save, network access, engine-source
edit and engine remote write counts are all zero.

The independent auditor recomputes all physical checks, exact cache roster,
trajectory identity, configuration, process argv/logs, frozen lineage, root
manifests and resource ceilings. Its `2e-8 m` centroid replay tolerance is the
already validated serialization tolerance from C20 C5; the physical centroid
motion requirement remains unchanged at 0.025 m.

## Stop rule and claim ceiling

Run once and retain PASS, physical FAIL or harness failure. Do not test another
particle maximum/minimum, stack the rejected radius change, tune after looking,
relax a physical threshold or render unless all 27 physical checks pass.

At most this run can establish one 36-frame Preview-96 R40 impact-liquid result
for the single `particle_maximum 16 → 12` change. It cannot establish full
landing, persistence, final-resolution liquid, film quality, deformation or a
general-purpose fluid solution.
