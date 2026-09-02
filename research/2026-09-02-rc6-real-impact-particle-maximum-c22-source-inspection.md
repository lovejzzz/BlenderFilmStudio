# RC6 C22 source inspection — particle maximum after same-onset amplification

Date: 2026-09-02
Status: read-only source-led selection; zero scene mutation

Bound product source is `lovejzzz/film-engine` at RC5 commit
`8e18c82548f8716c415e6e1b69fdbbdeef1f1900`. C21 accepted that reducing only
simulation particle radius `1.8→1.6` leaves velocity/Mesh/particle expansion
onsets unchanged at frames `24/24/25` while multiplying all three amplitudes.
The radius scalar is therefore closed.

Blender RNA describes `particle_max` as the maximum number of particles per
cell and resets the liquid Data cache when it changes. DNA defaults are minimum
8 and maximum 16. The generated liquid step passes both values into every
`adjustNumber` call after pressure and obstacle-boundary work.

The bound Mantaflow implementation first counts active particles by cell. It
deletes particles outside the domain, outside liquid or outside the narrow band.
It then deletes excess particles only when the running count is greater than
`maxParticles` and the sample is not within the radius-derived protected surface
region. Cells below `minParticles` are reseeded later. Surface particles are
explicitly exempt from the maximum deletion rule.

This selects one falsifiable C23 value: return to exact C18 radius1.8 and change
only `particle_maximum 16→12`, the integer midpoint between current minimum8
and maximum16. Minimum8, initial particle number2, band width4, fractional
obstacle threshold0.10/distance0.25, CFL2, timesteps2/8, APIC, Mesh settings,
exact R40 motion and all27 gates remain frozen.

The hypothesis is limited: a lower non-surface ceiling may reduce post-impact
particle/level-set amplification. It may also do nothing if the problematic
samples remain surface-protected. Do not claim that occupied-voxel growth proves
per-cell overpopulation, do not stack radius1.6, and do not scan another maximum
or minimum after observing C23. Retain every result and compare Data/Mesh onset
before any later parameter choice. Rendering remains forbidden until all
physical gates pass.

Bound implementation hashes:

- `rna_fluid.cc`: `a2ca40cda63b5a6ab77a78d8ee14d039abbf0577f82c7f1904879fac777643d4`
- `DNA_fluid_types.h`: `356a47d3c8d1c0800ef72fa55bb2d1b1bde8112014cb8f625868276c8aeceead`
- `liquid_script.h`: `b526a55e9ba35d5ba41ef53dc5d027e9e13831a32a2862c424752b616a10392b`
- Mantaflow `flip.cpp`: `83bc8bb4f4af7bbbeee88c3760c32dae687c80c1e2d1f7eb64a1169fa69dc332`
