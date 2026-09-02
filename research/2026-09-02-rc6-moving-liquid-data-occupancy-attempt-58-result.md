# RC6 moving-liquid Data occupancy attempt-58 result

Date: 2026-09-02

Status: `PASS_DIAGNOSTIC`, classification `DATA_SPATIAL_SUPPORT_SHRINKS_WITH_MESH`

Attempt-58 copied the exact immutable 48-file attempt-57 Data cache and used
the Film Studio Engine bundled Python 3.13/OpenVDB 13 runtime. It started zero
Blender processes and performed zero bakes, saves, renders, network calls or
retained-root writes. The analyzer took 0.04 seconds; the second exact runtime
independently reopened all 24 frames and passed 19/19. Receipt/audit self hashes
are `33ec1fcf…` / `f2d76906…`.

The Data files expose `particles` PointDataGrid and `velocity` Vec3SGrid, but no
`phi`, `liquid` or `flags` grid. Particle occupied-voxel support fell from 1,227
to 874 (`−28.77%`) while attempt-56 Mesh volume fell `−34.23%`. Their full
24-frame Pearson correlation is `0.98427`. Occupancy correlated inversely with
the growing ALIVE particle roster (`−0.95368`).

This is strong evidence against a pure surface-reconstruction explanation, but
occupied sparse voxels are still not exact mass. The moving obstacle/solver
layer should be tested first. The next single-variable gate should reduce only
the cup effector's implicit `surface_distance` from 2.5 to 2.0 cells: Blender's
official semantics say this setting expands the obstacle, and the current
motion loses spatial support while retaining zero particle/mesh escape. Keep
all trajectory, APIC, particle, mesh, subframe, volume, topology and containment
settings/thresholds unchanged. Do not render or begin real impact.
