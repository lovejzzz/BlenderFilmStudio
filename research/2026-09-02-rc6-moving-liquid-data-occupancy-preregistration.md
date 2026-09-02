# RC6 moving-liquid Data occupancy preregistration

Date: 2026-09-02

Status: preregistered before attempt-58 root creation

Zero-bake capability discovery found the exact Film Studio Engine Python 3.13
and OpenVDB 13 module. Mantaflow's retained Data VDB files contain `particles`
PointDataGrid and `velocity` Vec3SGrid metadata, but no `phi`, `liquid` or
`flags` grid. A disclosed endpoint probe saw 1,227 particle-occupied voxels at
frame 1 and 874 at frame 24; no formal 24-frame result is claimed from that
probe.

Attempt-58 copies the exact 48-file attempt-57 cache once, verifies source and
copy manifests, and uses the bundled Python/OpenVDB runtime without Blender to
read every frame. It computes occupied sparse-voxel volume, compares the full
series to attempt-56 Mesh volume and attempt-57 ALIVE counts, and freezes a
Pearson-correlation interpretation. A second exact engine-Python process
independently rereads all metadata.

Occupied voxel support is explicitly not exact liquid mass or signed level-set
volume. The run permits zero Blender starts, bakes, saves, renders, network calls
or retained-root writes and cannot authorize parameter tuning by itself.
