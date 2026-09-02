# RC6 moving-liquid effector-distance attempt-59 result

Date: 2026-09-02

Verdict: retained physical `FAIL`; independent audit `16/16 PASS`

Attempt-59 changed exactly one frozen variable from attempt-56: the moving
cup's Mantaflow `surface_distance` was reduced from 2.5 to 2.0 base cells. The
exact C5F96 Bullet trajectory, Preview-96 tier, APIC solve, particle and Mesh
settings, frame range and all scientific thresholds stayed unchanged.

The change was directionally useful but insufficient. Maximum source-relative
Mesh-volume error improved from 36.82% to 24.00%, crossing the unchanged 25%
gate. Temporal loss from frame 1 to frame 24 improved from 34.23% to 23.03%,
but still exceeded the unchanged 15% ceiling. The remaining 16 of 17 physical
checks passed: the exact solver trajectory, 14.42-degree frame-24 cup tilt,
35.30 mm cup-local liquid motion, one positive manifold liquid body, zero
radial/floor/rim escape and the exact 72-file cache roster.

Data and Mesh took 251.55 and 2.89 seconds respectively. The process performed
one Blender start, one Bullet bake, one Data bake and one Mesh bake, with zero
render, save, network or engine-write operations. Blender again returned exit
zero after writing the explicit self-hashed `FAIL` result and printing the
threshold traceback; the outer runner correctly retained the scientific
failure and completed its receipt and independent audit before returning
nonzero.

Result, receipt and independent-audit self hashes are respectively
`ccb16ddd6e36c50ce4009e9a36afb3b249a6d9ff2715521129142588a3b3f2cb`,
`62316a54d14b3f2c4b79d62c1800f63f43a6a93dc1c332fc63496ee29ce2b20f`
and `95b7f021bf66cf6decb08ea141d0014ef3d9cd184ab8ea9221019162421b7ae1`.

The 2.0-cell result is retained and no second `surface_distance` value may be
added. Before selecting a different physical degree of freedom, the next gate
is a zero-Blender, zero-bake copied-cache comparison of attempt-59 Data occupied
voxel support against attempt-58 and the two bound Mesh-volume curves.
