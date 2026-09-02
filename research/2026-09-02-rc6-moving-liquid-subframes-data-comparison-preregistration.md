# RC6 moving-liquid subframes Data comparison preregistration

Date: 2026-09-02

Status: preregistered before attempt-62 root creation

Attempt-61 showed that increasing moving-effector subframes from 1 to 2 raised
Data cost by 14.63% and slightly worsened reconstructed temporal volume loss.
Before selecting a solver-timestep variable, attempt-62 tests whether that
non-improvement is already present in Data.

The run copies the exact immutable attempt-61 cache into one fresh bounded root
and uses the product OpenVDB runtime to compare all 24 particle occupied-voxel
records against attempt-60's subframes-1 records. A reusable analyzer binds the
current and baseline result hashes, 2.0-cell surface distance, subframes value,
labels, VDB roster and voxel scale. An independent implementation recomputes
all rows and metrics.

No Blender process, bake, render, save, network call or retained-root write is
allowed. Occupied voxels remain a spatial-support proxy, not exact mass. No
third subframe value follows this diagnostic.
