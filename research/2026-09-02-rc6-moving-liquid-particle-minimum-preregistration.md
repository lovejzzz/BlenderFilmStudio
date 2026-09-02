# RC6 moving-liquid minimum particles-per-cell preregistration

Date: 2026-09-02

Status: preregistered before attempt-67 root creation

Bound source inspection shows that `particle_number` controls initial level-set
sampling, while `particle_min`/`particle_max` drive continuing `adjustNumber`
reseeding. Attempt-67 therefore preserves initial particle number 2 and changes
only the ongoing minimum from 8 to the single midpoint 12; maximum remains 16.

The complete attempt-65 configuration is otherwise frozen: simulation radius
1.8, minimum timesteps 2, maximum timesteps 4, CFL 2.0, surface distance 2.0,
one effector subframe, APIC, resolution 96, exact 24-frame C5F96 trajectory and
unchanged Mesh settings and physical thresholds.

The run permits exactly one Blender start, one Bullet bake, one Data bake and
one Mesh bake under the existing 2 GiB workspace and 64 MiB evidence ceilings.
It permits zero render, save, network, native-build or engine-write operations.
Pass, physical failure and harness failure are all retained. No second minimum,
particle maximum, initial particle-number, Mesh, impact or render change follows
from observing this run.
