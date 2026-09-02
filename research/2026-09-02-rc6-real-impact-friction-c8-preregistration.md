# RC6 real-impact friction C8 preregistration

Date: 2026-09-02

## Physical question

Can the corrected, lower-motion I09 basketball impact tip the free cup when one
small, source-derived floor-contact change converts impulse into moment instead
of slide?

Bullet source multiplies the two bodies' friction values. The exact cup/floor
pair is `0.75 × 0.58 = 0.435`. For the frozen 150 mm cup-base radius and 340 mm
ball impact height, the simple tip-before-slide comparison is
`radius / height = 0.4412`. The current pair sits about 1.4% below it.

C8 changes only cup friction from `0.75` to `0.80`; combined friction becomes
`0.464`, about 5.2% above the simple boundary. This is one modest value, not a
scan. Drive-end returns to attempt-77's frame 9, explicit cup margin stays 2 mm,
and every other physical field and threshold remains exact.

## Stop rule

Run F80 exactly once. Retain PASS or FAIL. The gate requires derived contact,
at least 45° solver-owned tilt by frame 48, no authored cup/ball outcome,
visible floor and domain containment, and no more than eight voxel-derived
Preview-96 effector subframes. Process ceilings are one Blender start, one
Bullet bake and zero liquid, render, save, build, network or engine-write
operations. Do not start liquid after a failure.
