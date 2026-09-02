# RC6 slow-tip Bullet screen C5 preregistration

Date: 2026-09-02
Status: preregistered before attempt-52 root creation

C4 proved that the corrected frame-1 hinge, angular damping and physical stop
work. It also proved that a prescribed kinematic collider is not a controlled
slow cause merely because its keyframes are farther apart: the collider entered
the evaluated cup surface by almost 58 mm and released a hard-contact impulse.

C5 replaces that contact path with a motorized physical test rig. The existing
HINGE continues to own the pivot, one rotational degree of freedom and
`-60°/+5°` stop. A separate Blender Bullet MOTOR constraint shares the same
world axis and provides only angular target velocity with maximum impulse
`1.0`. This two-constraint design follows the inspected Blender implementation:
motor setters affect only MOTOR constraints, and the Bullet bridge drives the
MOTOR constraint's local X axis while leaving its other axes unlocked.

The four cells target the 60-degree stop nominally at frames 48/60/72/96. The
greatest passing frame is therefore the slowest accepted motor trajectory. The
cup and ball retain zero animation, the former pusher has no animation and is
kept away from the cup, and every cup transform remains Bullet-owned.

C4's exact sweep also showed that the future candidate domain missed its upper
one-voxel margin by 1–2 mm. C5 adds 20 mm only to domain height while retaining
resolution 96 and the same 9.375 mm base voxel/margin. All other response,
floor, sampling, physical-stop and authority gates remain unchanged. No fluid,
render or save is admitted by this screen.
