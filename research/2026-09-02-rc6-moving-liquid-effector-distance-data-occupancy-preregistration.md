# RC6 moving-liquid effector-distance Data occupancy preregistration

Date: 2026-09-02

Status: preregistered before attempt-60 root creation

Attempt-59 improved the bound Mesh temporal loss from 34.23% to 23.03% by
changing only the cup effector distance from 2.5 to 2.0 cells, but the exact
15% moving-liquid gate still failed. No second distance value is allowed.

Attempt-60 performs no Blender run, bake, render or scene save. It copies the
complete immutable attempt-59 cache into one fresh bounded root, reads all 24
`particles` and `velocity` VDB metadata records using the exact product Python
and OpenVDB runtime, and independently compares the 2.0-cell Data occupied-
voxel curve with attempt-58's 2.5-cell curve and both bound Mesh curves.

The classification is frozen before reading any attempt-59 VDB endpoint. If
Data support and Mesh both still shrink beyond 15% with correlation at least
0.8, the remaining defect stays in or before Data. If Data support stays within
15% while Mesh does not, surface reconstruction becomes the leading suspect.
All other outcomes remain inconclusive. Occupied sparse voxels are never called
exact mass.
