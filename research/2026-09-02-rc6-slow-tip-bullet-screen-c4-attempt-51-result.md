# RC6 slow-tip Bullet screen C4 attempt-51 result

Date: 2026-09-02
Verdict: `FAIL_BULLET_SCREEN`; execution and independent audit valid

Attempt-51 completed all four limited, damped hinge cells with receipt hash
`729a1a65de486794e934da48394310f31c480f3b45c7265b59c5a68066c3b7b4`.
The independent audit passed 18/18 with audit hash
`5dc0e42a1534c4003e4ef887bcdfeb09567d44c04630e0a85c0e26cfcb6f30c8`.
There were four Blender starts and four Bullet bakes, with zero fluid, render,
save, network or engine-write operations.

The C4 corrections worked where intended. All four cells reached 45 degrees,
spanned 9–13 frames from 5 to 45 degrees and stopped at
`60.0027–60.0029°`. Maximum hinge-pivot drift was `2.54–3.47 mm`, below the
frozen 5 mm gate, and exact cup-surface minima stayed between `-0.61` and
`-1.15 mm`, above the `-5 mm` floor gate.

The retained direct kinematic pusher remained the wrong slow-tip cause. In
cell C4D40 its visible surface separation decreased to `-57.85 mm` before the
cup jumped from `37.47°` to `51.92°` at frame 40. The maximum exact surface
displacement was therefore `126.96–142.80 mm/frame`, requiring 14–16 Preview
effector subframes rather than at most 10. Slowing the prescribed pusher path
did not remove the stored hard-contact impulse.

The candidate domain also missed its unchanged one-voxel upper margin by only
about 1–2 mm: maximum cup z was `0.53164–0.53255 m`, while the current upper
admissible surface was `0.530625 m`. The radial, lateral and floor bounds were
otherwise inside the candidate domain.

C5 must stop treating a penetrating kinematic collider as a slow controlled
cause. It should use Bullet's hinge motor with bounded angular target velocity
and maximum impulse, retain the physical `-60°/+5°` stop, and keep every cup
transform solver-owned. The candidate domain may gain only the measured 20 mm
height correction while preserving the same one-voxel margin and 96-resolution
sampling rule. Real collision impact remains a later, separate gate.
