# RC6 real-impact friction C8 attempt-80 result

Date: 2026-09-02

C8 is a retained physical `FAIL` with an independent 23/23 audit. It returned
to attempt-77's lower-motion I09 impact and changed only cup friction from 0.75
to 0.80. Bullet's exact cup-floor product therefore changed from 0.435 to
0.464, crossing the simple 0.441 tip-before-slide estimate.

- contact remained frame 19;
- peak tilt changed only 2.67° to 2.98°;
- maximum origin travel improved from 30.42 to 29.64 mm/frame;
- maximum surface motion increased from 34.66 to 36.46 mm/frame;
- the derived Preview-96 requirement remained four subframes;
- floor and domain containment remained PASS.

The source-derived friction change slightly reduced slide but did not create a
useful angular response. The analytic boundary was useful for selecting the
test, not sufficient to predict Bullet's transient multi-contact solve. Close
cup-friction tuning; do not increase it again and do not start liquid.

The next causal layer is contact moment arm. Preserve I09, 2 mm cup margin and
the original 0.75 cup friction. Inspect the exact horizontal lane end, ball
radius and cup rim geometry, then preregister one passive ramp geometry that
lets Bullet lift the rolling ball into a higher cup contact. The ramp must own
the path; do not key the ball vertically or author any outcome.

Counts were one Blender start, one Bullet bake and zero liquid, render, save,
build, network and engine-write operations. Result/receipt/audit self hashes
are `4b3ce9e3...` / `a5129454...` / `c1d25684...`.
