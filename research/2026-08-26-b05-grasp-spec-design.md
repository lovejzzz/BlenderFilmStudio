# B05 articulated grasp — design baseline

Date: 2026-08-26

Status: contract validator executed; Blender benchmark not yet run

## Why B04 is insufficient

B04 proves that a rigid hand proxy and a prop can share a deterministic attachment, avoid volumetric overlap and remain visible to a review camera. It does not represent finger articulation, multiple contact patches, opposing normals, joint limits, closure timing or any force model.

The next contract therefore separates three claims:

1. **Kinematic validity:** declared finger joints stay within explicit limits and do not stretch.
2. **Geometric contact:** multiple fingertip patches approach declared prop surface patches without material penetration.
3. **Grasp plausibility proxy:** contact normals oppose one another sufficiently to resist at least one declared task direction under an explicitly assumed friction coefficient.

Only the first two can be treated as direct Blender geometry/animation evidence. The third is a simplified analytic proxy and must never be reported as measured real-world force.

## Blender 5.2 intervention points

- `PoseBone.matrix` exposes the final constrained pose matrix in armature space.
- `PoseBone` exposes per-axis IK minimum/maximum values, locks, stiffness and stretch controls.
- Bone constraints can compile declared IK targets and chain lengths.
- `Scene.frame_set()` updates the dependency graph for deterministic frame evaluation.
- `Scene.ray_cast()` operates on evaluated world-space geometry and reports the first hit object and evaluated face data.
- `Mesh.calc_loop_triangles()` makes the evaluated surface tessellation explicit for distance and intersection tests.

The Blender 5.2 manual warns that a normal Limit Rotation constraint does not constrain bones affected by IK. GraspSpec therefore requires `POSE_BONE_IK_LIMITS` and forbids treating a generic Limit Rotation constraint as the finger-chain safety gate.

## GraspSpec v0.1 fields

- actor, prop and palm socket references;
- two to five semantic finger chains;
- one to four bones per chain, each with one declared primary rotation axis, min/max/rest angle and IK stiffness;
- at least two fingertip contact patches with prop-local point, unit normal, separation interval and friction assumption;
- explicit approach, closure, hold and release windows;
- solver policy with no stretch and no scripted drivers;
- automatic thresholds for joint violation, penetration, contact count, opposing-normal angle, HOLD drift and camera visibility;
- mandatory human review.

## Contract-level execution

The v0.1 JSON Schema and semantic validator accept the frozen `B05.grasp.json` fixture and reject all eight synthesized contract mutations: wrong IK limit source, reversed joint range, rest angle outside limits, non-unit normal, parallel contact normals, missing finger reference, overlapping phases and enabled stretch.

- Schema SHA-256: `d89e4958bcf56c93c9166144a7e1ca78e2e00336450f9d9802eba29c1c6033c0`
- Fixture SHA-256: `0f7dbc3cfaca98c2dff6d2cb575fb41a19a846233fa18f25e645f74190fa1360`
- Self-test report SHA-256: `91bedb2fa64b3d105d9850af75ab1c011354bb687e1927e7d3b190da437d6121`

This only proves that the contract rejects these structural errors. No B05 armature, IK solve, contact geometry, transport or render has been executed yet.

## Planned B05 benchmark

The smallest executable benchmark should use an independently generated two-finger technical gripper and a convex prop. It must not reuse B04's box hand as proof of finger support.

### Positive fixture

- two articulated chains, two joints each;
- thumb and index target opposite prop faces;
- monotonic closure over 12 frames;
- at least two active contact patches during HOLD;
- zero stretch, joint violation and material penetration;
- stable prop-relative contact frames during a 0.30 m transport;
- review camera passes the existing visibility diagnostic.

### Preregistered negatives

1. generic Limit Rotation used on an IK-driven finger;
2. joint angle exceeds declared maximum by 10°;
3. two contacts occur on nearly parallel rather than opposing faces;
4. fingertip penetrates the prop by 8 mm;
5. only one contact remains active during HOLD;
6. solver stretch changes a phalanx length;
7. geometric contacts pass but the review camera hides one finger;
8. prop is parented to the palm while declared fingertip patches drift.

## Stopping gate

B05 may be described as an *articulated grasp proxy* only after two clean builds reproduce the same normalized structure, the positive fixture passes every frozen automatic gate, all eight negatives are rejected, and at least three blinded reviewers pass the visible interaction. It still may not be described as a biomechanically or physically correct human grasp.

## Primary references

- Blender 5.2 `PoseBone`: https://docs.blender.org/api/5.2/bpy.types.PoseBone.html
- Blender 5.2 scene evaluation and ray cast: https://docs.blender.org/api/5.2/bpy.types.Scene.html
- Blender 5.2 mesh tessellation: https://docs.blender.org/api/5.2/bpy.types.Mesh.html
- Blender 5.2 Limit Rotation constraint caveat: https://docs.blender.org/manual/en/5.2/animation/constraints/transform/limit_rotation.html
- NIST, *Multi-Fingered Robotic Grasping: A Primer*: https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=919752

Robotic force-closure literature is used only to define falsifiable contact-normal proxies. It is not evidence that a rendered human hand experiences real forces.
