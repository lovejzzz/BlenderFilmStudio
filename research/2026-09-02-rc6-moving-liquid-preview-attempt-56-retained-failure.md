# RC6 moving-liquid Preview attempt-56 retained failure

Date: 2026-09-02

Status: retained scientific `FAIL`, independently closed 23/23

Attempt-56 ran the exact preregistered C5F96 slow-tip trajectory for frames
1–24 at Preview resolution 96. It consumed one Blender start, one 0.034-second
Bullet bake, one 277.86-second Mantaflow Data bake and one 2.88-second Mesh
bake. Total Blender wall time was 282.82 seconds. It performed zero renders,
`.blend` saves, network calls or engine writes.

The causal and geometric parts worked. The cup matched all 24 accepted C5F96
transforms exactly, reached 14.4155°, and held its hinge pivot within 0.00022 mm.
The liquid moved 35.84 mm relative to the cup. Every frame contained exactly one
positive liquid body, zero non-manifold edges, zero radial exterior vertices,
zero below-floor vertices and zero above-rim vertices. The cache roster is the
exact 24 config + 24 Data + 24 Mesh files.

The volume result failed. Frame 1 reconstructed within 3.94% of the frozen
source, but volume then declined almost monotonically. By frame 24 it was
36.82% below the source and 34.23% below frame 1, exceeding the frozen 25% and
15% limits. The result therefore passed 15/17 checks and remains
`FAIL_MOVING_LIQUID_PREVIEW`; visual containment cannot substitute for mass
conservation.

The scene wrote its self-hashed failure and then raised the frozen threshold
exception. Blender background mode nevertheless returned exit code zero, so the
base runner stopped before receipt creation on a result/process mismatch. C1
performed no Blender work and closed both facts independently at 23/23. Failure
receipt self hash is `2c2f547a…`; audit self hash is `556d44f8…`. Existing
attempt files and the retained static cache remained exact.

The next gate must diagnose simulation particles separately from surface
reconstruction before changing a parameter. Repeat the same immutable physics
in a fresh Data-only instrumented run that exposes the full FLIP particle roster
at all 24 frames and records active-particle count, cup-local containment and a
particle-distribution volume proxy. Do not tune `mesh_particle_radius`, weaken
the volume gates, begin real impact or render before that diagnosis.
