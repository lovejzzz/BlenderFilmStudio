# RC6 slow-tip Bullet screen C2 attempt-49 result

Date: 2026-09-02  
Verdict: `FAIL_BULLET_SCREEN`; execution and independent audit valid

Attempt-49 completed the passive toe-stop matrix with receipt hash
`11f6791636bd6f57ebf616a566066511de989ec03c1f5712c6375501cb65d155`.
The independent audit passed 18/18 with audit hash
`e82f09858352c81f47f333af4dfd302f08cb2d41abcb3c4f8cc534a9c204f92b`.
All forbidden fluid, render, save, network and engine-write counts remained
zero.

The measured initial stop gap was `0.00500003 m` in all four cells and stop
contact occurred. The stop therefore created real tipping torque, but not a
stable planar pivot:

- C2D16 crossed 45 degrees at frame 16 and peaked at `95.5444951°`, but left
  the candidate domain, reached `-15.28 mm` surface z and required 32 effector
  subframes after a `0.2994792 m` one-frame surface displacement.
- C2D20 and C2D24 peaked at `44.84579432°` and `44.98714778°`, respectively,
  then rebounded. They remain below the unchanged 45-degree gate.
- C2D28 peaked at `44.56847301°` and required 12 subframes.

The failure is discontinuous: the fast drive launches the unconstrained cup,
while the slower drives reverse just below the required response. Moving the
stop or lowering the threshold would tune the observed outcome rather than
teach a stable rule.

C3 must replace the collision-only toe stop with an explicit Bullet hinge whose
axis and pivot are frozen from the cup geometry. The unchanged slow actuator
still supplies the force; the hinge owns the permitted degree of freedom and
prevents translational launch. Cup angle, surface displacement, floor/domain
bounds and zero animation authority remain independently measured. Attempt-49
is immutable.
