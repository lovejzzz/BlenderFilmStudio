# RC6 moving-liquid particle-band-width attempt-70 result

Date: 2026-09-02

Verdict: `PASS_MOVING_LIQUID_PREVIEW`; independent audit `16/16 PASS`

Attempt-70 changed exactly one physical setting from attempt-68:
`particle_band_width` increased from the bound default `3.0` to `4.0`. The
exact C5F96 Bullet trajectory, fractional-obstacle distance 0.25, simulation
particle radius 1.8, particle density 2/8/16, timesteps 2/4, CFL 2.0, cup
effector distance 2.0, one effector subframe, APIC, Preview-96 tier, Mesh
settings and every scientific threshold remained frozen.

The one-cell thicker resampling band closed the moving-liquid gate decisively:

- maximum temporal Mesh-volume drift improved from `0.15443274` to
  `0.06901662`;
- maximum source-relative volume error improved from `0.18811981` to
  `0.10442088`;
- all 24 frames retained exactly one positive liquid body, zero non-manifold
  edges and zero radial, below-floor or above-rim violations;
- minimum largest-component fraction improved from `0.68653906` to
  `0.80845392`;
- cup-local liquid centroid motion remained physical at `0.022591745 m`;
- the accepted Bullet trajectory was byte-for-measurement exact and hinge
  pivot drift remained only `0.0000002196 m`.

Data and Mesh bakes took `273.764829 s` and `2.960743 s`, respectively, under
the 2 GiB work ceiling. The exact cache roster is 72 files: one config, Data
and Mesh file for each frame 1–24. The run used one Blender start, one Bullet
bake, one Data bake and one Mesh bake, with zero render, save, native-build,
network or engine-write operations. The retained resolution-192 static cache
remained byte-exact.

Bindings:

- spec self hash: `df1e8515e070de1f710a0660f5909adabaab2d310b58a542d66ed9dd480e23b8`
- result self hash: `c2752a44dbec5304b5c540951de96abe62a7182dd9ba983e4c06cb800faa4e38`
- receipt self hash: `a1a4218bc659bacee2f8a01d07f804865853973c9a92a2f800fe6e73eea26b74`
- independent-audit self hash: `cf814e45cab3016ac7b0ee12f6d8f7d8116279ae29408d1013f617fd0909e97f`

This closes only the 24-frame Preview-96 slow moving-container liquid gate.
It does not prove basketball impact, full tip/spill, persistence, final
resolution, rendered appearance or film quality. The next gate may design the
real basketball-impact Bullet trajectory, but must measure that trajectory
without baking liquid before committing a bounded impact-fluid experiment.
