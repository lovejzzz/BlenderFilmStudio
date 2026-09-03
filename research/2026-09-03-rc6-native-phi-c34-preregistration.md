# RC6 C34 preregistration — uninterrupted native-phi Data diagnostic

Date: 2026-09-03

## Question

On the exact retained C29 R40 basketball-impact configuration, does enabling
Blender's native resumable Data export preserve the complete common particle
state (`P`, point velocity and `U`) and dense velocity grid for all 36 frames,
while exposing finite `phi`, `phi_particles` and `phi_previous` fields?

This is an observation-method test before it is a liquid interpretation. The
only changed runtime setting is `cache_resumable=false→true`. The bake is
uninterrupted and Data-only. It performs no Mesh bake, render, save, pause,
resume, engine build, source edit or network operation.

## Frozen decisions

- Reuse exact C29 R40/Preview-96/APIC inputs: particle band width 3, radius
  1.8, fractions threshold/distance 0.10/0.25, CFL 2, timesteps 2/8, the same
  moving cup, passive ramp and frames 1–36.
- One fresh workspace and evidence root, one Blender start, one rigid-body
  bake and one fluid Data bake. Retain every outcome.
- Require exact C29 rigid-body samples before and after Data.
- Decode every Data VDB with the accepted C33 helper. Require the actual field
  roster, type, finite dimensions, transform-derived voxel size and precision
  on every frame.
- Strong passivity means byte-independent decoded equality against C29 for all
  particle rows (`P`, velocity, `U`) and every dense velocity value, together
  with exact type, dimensions, voxel size and precision on all 36 frames.
- If a common field differs, classify `OBSERVED_PASSIVITY_UNPROVEN`; do not use
  the native phi curve to explain C29. If common fields are exact, classification
  may be `PASS_NATIVE_EXPORT_STRONG_COMMON_FIELD_EQUIVALENCE`, limited to this
  exact same-host uninterrupted Data path.
- For each native phi field, count finite-domain cells below zero and multiply
  by voxel volume. This is numerical negative-levelset occupancy—not exact
  liquid mass. Current phi, pre-resampling particle phi and previous-frame phi
  retain different meanings and are never substituted for one another.
- The accepted C29 physical verdict remains FAIL25/27 regardless of C34.

## Resource and claim ceiling

Reserve at least 100 GiB free. Workspace is capped at 4 GiB, evidence at 64
MiB, the single Blender process at 3600 seconds and each reader call at 30
seconds. No clean engine build is allowed because host free space remains below
the separate 160 GiB build threshold.

C34 cannot claim exact mass, a repaired simulation, a responsible Mantaflow
operation, a product default, film quality or permission to generate Mesh or
render. Visual work remains gated by physical acceptance. The owner's latest
review—realism is promising but lighting needs stronger hierarchy—is recorded
as the later visual-stage acceptance target: directional key, controlled fill,
background separation, contact shadow and event emphasis will be judged from
fresh screenshots only after the physical gate permits rendering.
