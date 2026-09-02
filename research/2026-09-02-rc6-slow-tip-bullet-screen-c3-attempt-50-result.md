# RC6 slow-tip Bullet screen C3 attempt-50 result

Date: 2026-09-02
Verdict: `FAIL_BULLET_SCREEN`; execution and independent audit valid

Attempt-50 completed the explicit-hinge matrix with receipt hash
`8b422857c326c11170b19f4169a40f2af94f9388faf667915fe80a4ddb6ac412`.
The independent audit passed 18/18 with audit hash
`5bf296d356c0e14a55c7be659b391af3908ef3a8011d57e8a0378212da3cad3a`.
No fluid, render, save, network or engine mutation occurred.

All four cells reached at least 45 degrees and stayed planar. Their final
sideways cup center near `(0.69, 0, 0.15)` exactly matches a 90-degree rotation
of the initial center `(0.32, 0, 0.22)` around the registered hinge point
`(0.47, 0, 0)`. The hinge was therefore physically active.

The reported `0.35592267 m` pivot drift is a harness-order failure. The source
blend opens on frame 15; C3 derived `hinge_pivot_cup_local` before freeing the
retained rigid cache and returning to frame 1. Every cell already reports the
same approximately `0.3559 m` value before actuator contact. C4 must derive the
local pivot only after cache reset and frame-1 evaluation.

The unlimited hinge also lets gravity accelerate the cup from the controlled
45-degree passage to a 90-degree fall. Maximum one-frame surface displacement
was `0.123–0.170 m`, requiring 14–19 Preview effector subframes and slightly
exceeding the candidate domain near the fully horizontal state.

C4 must preserve the same geometry-derived pivot/axis while adding a physical
angular stop and damping appropriate to a slow validation fixture. The
positive world-Y cup rotation is negative around the hinge's world-negative-Y
axis, so the frozen hinge limits are `-60°` and `+5°`. Cup angular damping is
frozen at `0.8`, and the four drives extend to 28/32/36/40 frames. No angular
key, motor, threshold change or fluid run is allowed. Attempt-50 is immutable.
