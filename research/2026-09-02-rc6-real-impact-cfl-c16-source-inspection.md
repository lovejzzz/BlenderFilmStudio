# RC6 C16 source inspection — select one CFL change

The bound Blender 5.2 source defines `cfl_condition` as the maximum velocity per
cell and explicitly states that larger values minimize simulation steps and
computation time. Mantaflow's `FluidSolver::adaptTimestep` multiplies the current
step by `CFL / max_velocity_per_step`, then clamps that value between the
configured minimum and maximum step lengths.

C15 shows the residual C14 failure is preceded by velocity-support expansion:
cup-solid intrusion begins at frame 31, velocity support crosses 25% at frame
34, Mesh/conservation fails at frame 35, and particle support crosses 25% at
frame 36. The saved terminal substep at frame 36 is close to the eight-step
floor, but it is not the full step history.

C16 therefore changes exactly one field: `cfl_condition` from 2.0 to 1.0. It
keeps `timesteps_min=2`, `timesteps_max=8`, APIC, eight derived effector
subframes, R40 Bullet motion, all geometry, source, domain, Mesh settings and
all 27 physical gates exact. The value is the single source-led midpoint between
the current CFL and the one-cell-per-step interpretation; it is not a parameter
scan or a threshold-seeking nudge.

If the unchanged gates still fail, the result is retained. No second CFL value,
additional maximum-step change, Mesh tuning or render follows from a failure.
