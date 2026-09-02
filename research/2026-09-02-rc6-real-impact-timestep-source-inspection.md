# RC6 real-impact liquid timestep source inspection

Date: 2026-09-02

This is a read-only selection record for the first post-C13 Data-layer variable.
No Blender process, cache copy, bake, render or source mutation was performed.

## Bound source and configuration

The inspected source checkout is clean at film-engine commit
`8e18c82548f8716c415e6e1b69fdbbdeef1f1900`. Relevant file identities are:

- `intern/mantaflow/intern/strings/fluid_script.h`:
  `b8c1fce0ba31e506e01c1133f267175511216608c1fde1f32bdd81db126e16d8`
- `intern/mantaflow/intern/strings/liquid_script.h`:
  `b526a55e9ba35d5ba41ef53dc5d027e9e13831a32a2862c424752b616a10392b`
- `source/blender/blenkernel/intern/fluid.cc`:
  `63a7a3e1affe7809ea935e184dea992754655796a9631e0eadb2060d72dfa20f`
- `source/blender/makesrna/intern/rna_fluid.cc`:
  `a2ca40cda63b5a6ab77a78d8ee14d039abbf0577f82c7f1904879fac777643d4`

C12 enabled adaptive timesteps with `timesteps_min=2`, `timesteps_max=4` and
`CFL=2.0`. The bound source sets the solver's minimum timestep to
`frameLength / timestepsMax`, obtains maximum grid velocity, and calls
`adaptTimestep(maxVel)`. Blender's RNA description identifies CFL as maximum
velocity per cell and says larger values minimize steps and cost.

The exact R40 cup surface moves at most `0.0721038718 m` per frame, or about
`7.69` Preview voxels. Eight effector subframes are therefore required, while
the fluid solver is currently permitted at most four steps. The retained
configuration files store a final `dt` near `0.026141746` from frame 23 onward,
approximately one quarter of a 24 fps fluid frame. This stored value alone is
not a complete substep trace, but it is consistent with the four-step ceiling
being the relevant high-speed limit when C13 observes Data expansion.

## Selected single variable

Change only `timesteps_max` from 4 to 8. Keep `timesteps_min=2`, `CFL=2.0`,
APIC, particle settings, obstacle settings, eight effector subframes, R40
Bullet trajectory, geometry, domain, source, Preview resolution, Mesh settings
and all 27 physical checks unchanged.

Eight is selected because it permits a solver step floor of one eighth frame
and matches the independently derived eight effector samples; at the measured
peak this corresponds to roughly one voxel of cup-surface travel per potential
solver step instead of roughly two. This is a bounded stability hypothesis,
not a prediction of PASS. Do not lower CFL, switch FLIP/APIC, change particle
band width or tune the Mesh in the same attempt.
