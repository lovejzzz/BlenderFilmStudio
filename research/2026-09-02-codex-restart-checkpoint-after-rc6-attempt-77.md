# Codex restart checkpoint after RC6 attempt-77

Date: 2026-09-02

This checkpoint is a handoff only. It does not authorize or preregister a new
experiment, start Blender, bake Bullet or liquid, render media, or mutate the
engine repository.

## Durable repository state

- Research `main` is committed and pushed through
  `5ab446259c4f2cecbacd6e8c2bb7b2730839152d`.
- The active long-running goal remains: build a complete real project, improve
  it through screenshot-led visual judgment, teach the product reusable film
  rules, and accumulate those rules in the physical-film-direction skill.
- Exact accepted source scene remains
  `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend`,
  SHA-256 `9ac79c9c3c0d13273ac20804a3af99884f9465534800c3d9ca2ae8121499e644`.
- Latest preflight reported about 155 GiB free, below the conservative 160 GiB
  clean-native-build threshold. Existing accepted binaries may run within the
  standing 2 GiB work/evidence and 100 GiB reserve bounds; do not admit another
  clean native build without a fresh passing preflight.

## Latest closed physical result

RC6 C6 attempt-77 is retained as a physical `FAIL` with a clean independent
23/23 audit. It changed exactly one value: the cup's Bullet cylinder margin
from the implicit 40 mm envelope to the product's explicit 2 mm envelope.

- floor penetration: 16.57 mm -> 0.15 mm;
- maximum cup-surface displacement: 96.84 mm/frame -> 34.66 mm/frame;
- derived Preview-96 effector subframes: 11 -> 4;
- domain containment: fail -> pass;
- peak cup tilt under the same I09 impact: 90.00 degrees -> 2.67 degrees.

The old dramatic tip was therefore a collision-scale artifact. Preserve the
2 mm margin as the corrected baseline. Never restore 40 mm merely to recover
drama, and never author the cup's post-impact pose or velocity. Evidence root:
`experiments/physical-richness/RC6-2026-09-02-real-impact-cup-margin-c6-attempt-77`.
Receipt/audit self hashes are `e04832b1...` / `5ae53476...`.

## Performance and fluid research recovered from the completed subagent

- The observed first-ten-frame cost of about 32 minutes is consistent with the
  retained Final-192 Mantaflow measurements (about 192-208 seconds/frame). It
  is not evidence that the M2 Max is malfunctioning; almost all of the cost is
  Data/Mesh baking rather than rendering.
- Doubling the longest-axis resolution from 96 to 192 increases the base voxel
  count by roughly eight times before particle, pressure-solve, meshing and I/O
  multipliers. Final-192 is acceptable as a final validation tier, not as a
  parameter-search tier.
- Keep Preview-96 modular Data and Mesh stages for development. A 24-frame
  moving-effector preview should remain in the minutes-scale range; a return to
  roughly three minutes/frame should trigger a pipeline audit before blaming
  the computer.
- Derive moving-effector subframes from measured maximum surface displacement
  divided by voxel size, then validate penetration, volume and containment.
- Keep simulation `particle_radius` separate from reconstruction
  `mesh_particle_radius`; physical-input changes invalidate Data + Mesh,
  surface-only changes invalidate Mesh, and camera/light/material changes
  invalidate neither cache.
- For slow cup motion, APIC is a justified candidate because the shot needs a
  stable continuous body of liquid; it is not a universal realism claim.

The relevant official references are Blender's Fluid Effector, Domain Cache,
Domain Settings and Liquid Mesh manuals plus the Blender Python API for
`FluidDomainSettings` and `FluidEffectorSettings`.

## Exact restart order

1. Read `AGENTS.md`, `START_HERE.md`, the handoff JSON and this checkpoint.
2. Run the read-only host preflight. Do not start a clean native build while it
   remains below the 160 GiB threshold.
3. Inspect the corrected 2 mm collision/contact geometry read-only and choose
   exactly one solver-owned physical degree of freedom for the next gate.
4. The nearest causal candidate is impact impulse under the corrected margin:
   test only one preregistered value, preferably the already bounded I08
   launcher timing, before considering contact height or friction. This is a
   next-step hypothesis, not a frozen experiment.
5. Require derived contact, continuous transforms, floor/domain containment,
   tilt and voxel-derived subframe cost to pass before starting any liquid.
6. Only after a real Bullet trajectory passes, bind the exact attempt-70 liquid
   settings, bake Preview-96, inspect selected frames visually, and revise the
   software rule from measured evidence.

Do not start liquid, Final-192, or a beauty render from the current 2.67-degree
trajectory. There are no uncommitted research-repository changes expected at
this checkpoint.
