# RC6 slow-tip Bullet screen C5-C1 preregistration

Date: 2026-09-02
Status: preregistered before attempt-53 root creation

C5 attempt-52 completed the first Bullet bake but stopped before measuring it
because the inherited base loop still referenced the removed legacy
`separation` variable. No motorized physical result was written.

C5-C1 changes exactly one generated-source line: after computing hinge-pivot
drift it defines `separation = math.inf`. This makes the obsolete inherited
`separation <= 0.01` contact branch deterministically unreachable, matching
C5's already-frozen `motorActuationFrame` semantics. The value is not recorded
or used by any C5 metric or acceptance check.

All motor, hinge, axis, limit, damping, speed, maximum-impulse, domain,
surface, response and resource fields remain exact. Attempt-52 remains
immutable; attempt-53 uses fresh roots and the same four cells.
