# RC6 C18 source inspection — fractional-obstacle threshold

Date: 2026-09-02

The bound Blender 5.2 source exposes `fractions_threshold` with a default of
`0.05`, a legal range `0.001–1.0` and UI step `0.05`. Its RNA description says
higher values tag a boundary cell as an obstacle more readily and reduce the
boundary-smoothing effect.

Mantaflow routes this value as `fracThreshold` into `updateFractions` before
obstacle flags are assigned. The same liquid step then subtracts the current
obstacle level set, advects particles, pushes them out of fractional and full
obstacles, rebuilds the particle level set and runs `adjustNumber`. Source also
contains a warning that a disabled obstacle-flags check had produced unstable
particle behavior; that comment is evidence that obstacle classification and
particle stability interact, not proof that threshold `0.10` is correct.

C17 shows C16's lower-CFL regression begins in Data/Mesh together at frame 24
without prior >1% cup intrusion. C18 therefore does not stack another timestep
change. It returns to C14 (`cfl_condition=2`, timesteps `2/8`) and selects one
distinct collision-layer hypothesis: `fractions_threshold 0.05 → 0.10`, the
first exact UI step. Every trajectory, geometry, domain, source, particle,
surface and 27-check threshold remains C14-exact.

The test may show improvement, regression or no effect. A failure closes this
threshold value. It does not authorize a second threshold, another CFL or step
value, Mesh tuning, rendering or threshold relaxation.
