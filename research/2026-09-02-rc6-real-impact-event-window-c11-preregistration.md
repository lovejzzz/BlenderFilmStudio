# RC6 real-impact event-window C11 preregistration

Date: 2026-09-02

C10's full 48-frame verdict remains `FAIL`. C11 does not change it. It reads
the immutable R40 samples and asks a narrower product-design question: can a
Preview fluid experiment cover the complete pre-impact approach through the
first solver-owned 70° cup frame without exceeding eight effector subframes or
enlarging the domain?

The window begins at frame 1 and ends at the first retained tilt >=70°. Contact,
end frame, maximum surface motion and bounds are derived, not typed after
review. Domain dimensions stay 0.90×0.50×0.58 m; only its center candidate moves
to x=0.57. One full voxel margin is required.

This audit uses zero Blender, Bullet, liquid, render, save and network calls. A
PASS only makes a later event-window liquid Preview admissible. It does not
claim that all liquid has spilled by 70° or that the full 48-frame trajectory
passes.
