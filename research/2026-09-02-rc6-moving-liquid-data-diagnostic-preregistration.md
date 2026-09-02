# RC6 moving-liquid Data diagnostic preregistration

Date: 2026-09-02

Status: preregistered before attempt-57 root creation

Attempt-56 retained a clean causal trajectory and liquid containment/topology,
but its reconstructed Mesh volume drifted 34.23%. Attempt-57 changes no physics
input. It repeats exact C5F96 frames 1–24 at Preview-96 with the same APIC,
particle radius, obstacle distance and subframe count, disables only Mesh bake,
and exposes 100% of the evaluated FLIP particle roster in the same process.

The diagnostic records all particle state counts, ALIVE count ratio, cup-local
containment, centroid/bounds and RNA speeds at every frame. Count is treated only
as a constant-per-particle mass proxy, never exact geometric volume. More than
1% one-voxel exterior particles classifies containment failure; otherwise more
than 15% ALIVE-count drift is a Data-layer signal; otherwise the retained Mesh
reconstruction becomes the first suspect.

The one run permits one Blender start, one Bullet bake, one Data bake and zero
Mesh, render, save, network or engine-write operations. Any classification is a
valid diagnostic result and does not itself authorize parameter mutation.
