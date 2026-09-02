# RC6 C17 preregistration — CFL Data/Mesh comparison

C16 is an independently audited physical failure. Lowering only CFL from 2.0
to 1.0 improved cup-solid intrusion but moved volume and fragmentation failure
much earlier and nearly restored the original catastrophic expansion. That is
enough to close CFL tuning, but not enough to identify the per-step cause.

C17 makes no new physical change. It creates one fresh complete copy of the 108
immutable C16 cache files and reads that copy with the accepted engine Python
and OpenVDB module. It measures particle and velocity occupied support, retained
Mesh volume, topology thresholds, cup intrusion and saved terminal-substep
metadata on all 36 frames. Every C16 row is compared with the retained C14 rows
already independently bound by C15.

The classifier is frozen before the copy exists. It can report prior cup
intrusion, Data-at-or-before-Mesh expansion, stable Data with Mesh-only
expansion, or an inconclusive order. Occupied voxels are not exact mass, and a
saved terminal `dt` is not a complete step roster.

Attempt-89 permits two engine-Python processes including audit, one copied
cache, and zero Blender starts, bakes, renders, saves, network calls or retained
root writes. No second CFL, higher maximum-step value, Mesh tuning, threshold
change or render may follow before this result is retained.
