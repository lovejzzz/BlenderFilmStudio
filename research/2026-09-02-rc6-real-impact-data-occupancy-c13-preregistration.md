# RC6 real-impact Data occupancy C13 preregistration

Date: 2026-09-02

The retained C12 liquid Mesh remains coherent through frame 22 and expands
catastrophically from frame 23. Before changing physics, this diagnostic asks
whether the copied immutable Mantaflow Data particle support expands at or
before that Mesh failure, or whether Data remains bounded and only surface
reconstruction fails.

Read-only capability discovery found only `particles` and `velocity` grids.
Frame 22 has 1,554 occupied particle voxels and frame 23 has 2,973; velocity
support rises 17,829→76,749. Across frames 20–36, particle occupancy and Mesh
volume correlate at about 0.976. These observations select the formal question;
they are not exact liquid-mass evidence.

Attempt-85 will make one complete fresh copy of all 108 retained cache files,
measure all frames 1–36 with the accepted engine's OpenVDB runtime, and compare
the independently reopened Data support against the immutable C12 Mesh result.
It allows two engine-Python processes including audit, but zero Blender starts,
bakes, renders, saves, network calls or retained-root writes. Every outcome is
retained. No new physical parameter may be chosen before the audit closes.
