# B06 contact-driven rigid-body support protocol

Status: pre-registered before the first Blender rigid-body run.

## Question

Can a Blender 5.2 active rigid-body prop be lifted 0.30 m against gravity by two independently animated opposing colliders, with no parenting, Child Of, rigid-body constraint, transform copy, or shared carrier applied to the prop?

This is a narrow Bullet rigid-body feasibility benchmark. It does not model human fingers, deformable skin, pressure distribution, tendon forces, learned grasp planning, measured material coefficients, or real-world force closure.

## Positive fixture

- prop: 0.10 × 0.12 × 0.14 m box, 0.25 kg, active rigid body;
- two side colliders: independently animated passive/kinematic boxes;
- gravity: Blender scene gravity, `(0, 0, -9.81)` m/s²;
- closure: frames 37–48;
- prop changes from animated/kinematic to dynamic at frame 49;
- transport: colliders move 0.30 m upward during frames 49–108;
- release: colliders separate during frames 109–112; observation ends at frame 132;
- collision shape: BOX; scale applied; declared margin and friction recorded;
- solver settings and Blender version recorded in the manifest.

## Frozen positive gates

1. The prop has no object parent, animation constraint, rigid-body constraint, driver, or transform keyframe during the dynamic HOLD window.
2. The prop is active and non-kinematic throughout frames 49–132.
3. Both finger colliders are distinct rigid-body objects with independently authored animation curves.
4. Prop vertical transport from frame 49 to 108 is at least 0.25 m.
5. Maximum prop-centre drift from the two-collider midpoint during HOLD is at most 0.03 m.
6. Prop rotation change during HOLD is at most 10 degrees.
7. The prop remains between the two opposing inner faces throughout HOLD without a centre-axis escape greater than 0.02 m.
8. After release, the prop falls at least 0.03 m by frame 132.
9. Two factory-startup builds produce identical declared scene-structure hashes; evaluated trajectories are compared separately with maximum position divergence at most 0.001 m.
10. The evaluator exits non-zero if any gate fails.

Configuration gate added before the second negative run: the maximum collision margin must not exceed the declared 0.001 m contact gap. This makes N07 a configuration rejection even if Bullet happens to return a plausible trajectory.

Input-motion gate added after the fast-transport negative demonstrated a false pass: maximum collider displacement is 0.01 m per frame. Output plausibility alone cannot legitimize a kinematic collider that teleports 3 m in one frame and returns in the next.

## Pre-registered negative classes

- N01 zero friction;
- N02 only one collider active;
- N03 insufficient closure distance;
- N04 prop remains kinematic during HOLD;
- N05 forbidden Child Of or shared-parent shortcut;
- N06 transport too fast for the declared solver budget;
- N07 collision margin larger than the declared contact gap;
- N08 solver substeps below the declared minimum.

The first feasibility spike may execute only the positive case plus a small diagnostic subset. A formal B06 claim requires all eight negatives, two clean trajectories, a versioned PhysicsSpec/BuildPlan path, visibility, and human review.

## Interpretation

PASS would show only that this explicit Blender/Bullet configuration can produce contact-driven rigid-body transport under declared numerical assumptions. It would not validate the friction coefficient, prove physical realism, generalize to arbitrary shapes, or replace a force/torque grasp analysis.
