# RC6 moving-liquid simulation particle-radius preregistration

Date: 2026-09-02

Status: preregistered before attempt-65 root creation

Attempt-64 proved that the small `timesteps_min=2` improvement is present in
Data but is too weak to justify another timestep. The next distinct physical
degree of freedom is Mantaflow simulation `particle_radius`, which Blender
defines separately from reconstructed `mesh_particle_radius`.

Attempt-65 preserves the exact attempt-63 two-step baseline and changes only
simulation particle radius from 1.6 to 1.8. The selected 1.8 value is the single
midpoint of the already measured static 1.6–2.0 interval; this is one
confirmatory value, not a result-driven scan. Exact C5F96 motion, resolution 96,
24-frame cache, APIC, particle number 2, Mesh radius 2.5, surface distance 2.0,
one effector subframe, CFL 2.0, maximum timesteps 4 and every scientific
threshold remain unchanged.

The run allows one Blender start, one Bullet bake, one Data bake and one Mesh
bake under the existing 2 GiB workspace and 64 MiB evidence ceilings. It allows
zero render, save, network, native-build or engine-write operations. Pass,
physical failure and harness failure are all retained. No second radius value,
Mesh tuning, impact or render follows from observing this run.
