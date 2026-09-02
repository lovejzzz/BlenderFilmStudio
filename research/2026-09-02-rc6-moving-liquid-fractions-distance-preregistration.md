# RC6 moving-liquid fractional-obstacle distance preregistration

Date: 2026-09-02

Status: preregistered before attempt-68 root creation

Attempt-67 proved that increasing ongoing particle density changes Data bytes
without changing the liquid Mesh. Bound source shows that positive
`fractions_distance` instead pushes particles away from the moving obstacle on
every liquid step. Attempt-68 therefore returns to exact attempt-65 and changes
only this distance from the default 0.5 to the single midpoint 0.25.

Simulation particle radius 1.8, particle number/minimum/maximum 2/8/16,
minimum/maximum timesteps 2/4, CFL 2.0, surface distance 2.0, one effector
subframe, APIC, resolution 96, exact 24-frame C5F96 trajectory, Mesh settings
and all physical thresholds remain unchanged.

The run permits exactly one Blender start, one Bullet bake, one Data bake and
one Mesh bake under the existing 2 GiB workspace and 64 MiB evidence ceilings.
It permits zero render, save, network, native-build or engine-write operations.
Pass, physical failure and harness failure are all retained. No second
fractional distance, obstacle threshold, Mesh, impact or render change follows
from observing this run.
