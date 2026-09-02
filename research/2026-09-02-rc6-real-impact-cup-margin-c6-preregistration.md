# RC6 real-impact cup collision-margin C6 preregistration

Date: 2026-09-02

## Bound source finding

The RC6 scene helper creates rigid bodies but never sets `use_margin` or
`collision_margin`. Bound Blender source initializes margin to `0.04 m`, and
`RBO_GET_MARGIN` returns that 40 mm default for a CYLINDER when custom margin is
off. The exact cup radius is 150 mm, so its implicit margin is 26.67% of radius
and 4.27 Preview-96 voxels. The reusable product physics compiler already sets
all bodies to explicit `0.002 m` margin.

## Frozen test

Attempt-77 keeps exact I09, the source scene, all masses, friction, solver,
domain, contact/tilt/floor and eight-subframe thresholds unchanged. It changes
only the cup collision-margin configuration from implicit 40 mm to explicit
2 mm. The scene process must first assert the saved source values, then perform
one 48-frame Bullet bake. One Blender start is allowed; liquid, render, save,
build, network and engine-write counts remain zero.

This test asks whether a scale-congruent collision shape fixes the 16.57 mm
visible floor penetration and changes the derived surface-motion/domain result.
It does not authorize a fluid bake or a larger domain.
