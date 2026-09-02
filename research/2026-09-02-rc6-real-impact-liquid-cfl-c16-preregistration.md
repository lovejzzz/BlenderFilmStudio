# RC6 C16 preregistration — one CFL test

C15 passed its independent audit but deliberately remained classification-
inconclusive. The residual sequence is nevertheless specific: cup-solid
intrusion begins at frame 31, velocity support crosses its comparison line at
frame 34, Mesh/conservation/positive-body checks fail at frame 35, and particle
support plus connected-component count fail at frame 36.

Bound Blender/Mantaflow source selects one new degree of freedom. C16 lowers
only `cfl_condition` from 2.0 to 1.0. Blender defines CFL as maximum velocity
per cell; Mantaflow uses it to adapt `dt` before clamping to the configured step
bounds. `timesteps_min=2` and `timesteps_max=8` remain exact C14.

Everything else is frozen: exact same-solve R40 Bullet motion, frames 1–36,
Preview-96 domain, APIC, particle 2/8/16, simulation radius 1.8, band width 4.0,
fractional obstacle distance 0.25, eight measured effector subframes, all Mesh
settings, and all 27 physical gates. The only authored rigid motion remains the
striker; the ball, cup and liquid outcome remain solver-owned.

Attempt-88 permits one Blender start, one Bullet bake, one Data bake and one
Mesh bake under the existing 2 GiB bound. It permits no render, save, build,
network call or engine mutation. PASS, physical FAIL or harness failure is
retained. A failure does not authorize another CFL value, a higher timestep
ceiling, Mesh tuning, threshold relaxation or rendering.
