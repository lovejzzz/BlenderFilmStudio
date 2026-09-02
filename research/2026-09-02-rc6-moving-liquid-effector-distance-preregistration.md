# RC6 moving-liquid effector-distance preregistration

Date: 2026-09-02

Status: preregistered before attempt-59 root creation

Attempts 56–58 show a contained single-body liquid whose Mesh volume and Data
occupied-voxel support shrink together while raw FLIP count grows. Blender's
official semantics define `surface_distance` as expanding the obstacle in grid
cells. The next physical test therefore changes exactly that one degree of
freedom: cup effector distance `2.5 → 2.0` cells.

Attempt-59 repeats exact C5F96 frames 1–24 at Preview-96 with unchanged APIC,
particle radius 1.6, mesh radius 2.5, one effector subframe and all original
volume/topology/containment thresholds. It permits one Blender start, one Bullet
bake, one Data bake and one Mesh bake, with zero render, save, network or engine
write operations.

The result is retained whether it passes or fails. No second value may be added
after observing it, and neither impact nor visual rendering begins before a
moving-liquid gate passes.
