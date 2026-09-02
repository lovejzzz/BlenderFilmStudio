# RC6 moving-liquid particle-radius Data comparison preregistration

Date: 2026-09-02

Status: preregistered before attempt-66 root creation

Attempt-65 changed only simulation particle radius 1.6→1.8 and improved
temporal Mesh loss by 4.65 percentage points without passing. Attempt-66 tests
whether that response begins in Data support before Mesh reconstruction.

The frozen run copies the exact immutable attempt-65 cache into one fresh root
and binds it as `particle-radius-1p8` against attempt-64's analysis of the
attempt-63 `particle-radius-1p6` Data cache. It reuses the exact generic copied-
VDB analyzer and binds all 24 frames, result/audit hashes, surface distance 2.0,
one effector subframe, exact VDB roster and voxel scale.

No Blender, bake, render, save, network or retained-root write is allowed.
Occupied voxels remain a spatial-support proxy, not exact mass. No second
particle radius, Mesh tuning, impact or render follows this diagnostic.
