# RC6 real-impact event-window C11 attempt-83 result

Date: 2026-09-02

C11 passes 16/16 with zero Blender, Bullet, fluid, render, save and network
operations. It preserved the immutable attempt-82 root and its original
full-window physical `FAIL` exactly.

The independently recomputed Preview candidate is:

- frame start: 1;
- derived contact: frame 19;
- derived end: first cup tilt >=70°, frame 36;
- cumulative maximum cup-surface motion: 0.07210387 m/frame;
- required Preview-96 effector subframes: 8;
- swept cup bounds: x=0.17000→0.96482 m;
- domain dimensions: unchanged at 0.90×0.50×0.58 m;
- candidate domain center: x=0.57 m;
- one-voxel containment: PASS.

This proves only that a bounded real-impact liquid Preview can now be attempted.
It does not prove liquid conservation, spill visibility, completion by frame36,
or finished-film quality. The next tool must integrate the actual R40 Bullet
ramp trajectory and accepted attempt-70 APIC/liquid settings in the same solve;
it must not substitute the prior hinge/motor slow-tip rig or replay authored cup
poses.

Audit self hash: `96a159ccbcb418df15eeba0af1e54c4bd8ba98c326824b8b319fcc0e0f427891`.
