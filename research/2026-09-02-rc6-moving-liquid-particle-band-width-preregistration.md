# RC6 moving-liquid particle-band-width preregistration

Date: 2026-09-02

Status: preregistered before attempt-70 root creation

Attempt-68 reduced temporal Mesh loss to 15.443274% with zero containment or
topology failures, only 0.443274 percentage points above the unchanged 15%
gate. Attempt-69 then confirmed that its improvement begins in Data support.
Bound source shows that `particle_band_width` controls the narrow band used by
ongoing particle resampling and that a higher value produces a thicker band
with more particles. Attempt-70 therefore changes only this value from the DNA
default 3.0 to 4.0, exactly one base-grid cell wider.

Fractional-obstacle distance 0.25, simulation particle radius 1.8, particle
number/minimum/maximum 2/8/16, minimum/maximum timesteps 2/4, CFL 2.0, surface
distance 2.0, one effector subframe, APIC, resolution 96, exact 24-frame C5F96
trajectory, Mesh settings and all physical thresholds remain unchanged.

The run permits exactly one Blender start, one Bullet bake, one Data bake and
one Mesh bake under the existing 2 GiB workspace and 64 MiB evidence ceilings.
It permits zero render, save, network, native-build or engine-write operations.
Pass, physical failure and harness failure are all retained. No second
particle-band-width value, impact, render or visual adjustment follows merely
from observing this run.
