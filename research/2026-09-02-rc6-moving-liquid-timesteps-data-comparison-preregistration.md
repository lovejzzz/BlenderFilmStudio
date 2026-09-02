# RC6 moving-liquid timesteps Data comparison preregistration

Date: 2026-09-02

Status: preregistered before attempt-64 root creation

Attempt-63 changed only minimum fluid timesteps from 1 to 2 and improved Mesh
temporal loss by 1.33 percentage points without passing. Attempt-64 determines
whether that small response is already present in Data.

The frozen run copies the exact immutable attempt-63 cache into one fresh root
and binds it as `timesteps-min-2` against attempt-60's `timesteps-min-1` Data
curve. It reuses the generic copied-VDB comparison implementation; versioned
runner and auditor adapters bind the exact roots, input hashes, surface
distance 2.0, subframes 1, labels, VDB roster and voxel scale.

No Blender, bake, render, save, network or retained-root write is allowed.
Occupied voxels remain a spatial-support proxy, not exact mass. No timestep 3,
CFL change or maximum-timestep change follows this diagnostic.
