# B05 compiled articulated-grasp benchmark protocol

Status: pre-registered before the first SceneSpec v0.4 clean build.

## Question

Can the restricted BFS compiler transform a hash-pinned SceneSpec v0.4 plus GraspSpec v0.1 into a reproducible Blender 5.2 scene in which two independently articulated finger chains acquire, carry, and release a prop without a shared carrier shortcut?

This benchmark tests deterministic kinematic compilation. It does not test force closure, frictional stability, soft tissue, collision response, dynamics, photoreal human hands, or semantic performance authored by a humanoid ActorSpec.

## Frozen positive fixture

- SceneSpec: `specs/benchmarks/B05.scene.json`
- GraspSpec: `specs/benchmarks/B05.grasp.json`
- technical character asset: `assets/characters/B05-gripper.blend`
- prop asset: `library/props/B05-prop.blend`
- Blender target: 5.2.0
- clean builds: two factory-startup processes from the same immutable BuildPlan

The GraspSpec declares two two-bone chains, two opposed contact patches, PoseBone IK limits, no stretch, closure 37–48, hold 49–108, release 109–120, and a 0.3 m hold transport.

## Machine gates

All gates below must pass for `AUTOMATION_PASS`:

1. SceneSpec v0.4 and embedded GraspSpec v0.1 validate before compilation.
2. The BuildPlan verifies all local hashes and authorizes `CREATE_GRASP` without network access or arbitrary Python from the input.
3. Two clean Blender builds produce identical structural hashes. Binary `.blend` equality is recorded but is not a pass requirement.
4. Exactly two IK constraints exist on the declared terminal bones, use the declared two-bone chain lengths, and disable stretch.
5. Every declared joint uses only its declared rotation axis; maximum evaluated joint-limit violation is at most 0.1 degrees.
6. Maximum bone-length ratio error is at most 0.0001.
7. Closure error is monotonically non-increasing within 0.0001 m numerical tolerance.
8. Across every HOLD frame, both contacts are active; each tip-to-declared-surface separation is within 0.001–0.003 m.
9. The declared opposing contact-normal angle is at least 150 degrees.
10. Maximum HOLD contact-relative drift is at most 0.003 m.
11. Prop transport from frame 49 to 108 is at least 0.299 m.
12. Attachment switch position pop at acquire and release is at most 0.001 m.
13. The prop and gripper do not share an object parent or a common non-scene carrier. Transport targets follow an independent frame; the prop follows the palm only through the declared keyed Child Of constraint.
14. Runtime evaluator exits non-zero whenever any gate fails.

Visual audit amendment, added after the first authored-camera preview exposed a pose/render mismatch:

15. Every evaluated visible finger-segment centroid must remain within 0.001 m of its corresponding evaluated pose-bone midpoint. The pre-amendment automation result is preserved as `experiments/grasp-v0-2/B05.pre-visual-audit-results.json`; it must not be cited as the final result.

## Pre-registered negative cases

The test harness must prove rejection of at least these eight defect classes:

- N01: unsupported generic joint-limit source;
- N02: invalid joint range;
- N03: contact normals that do not meet the opposition threshold;
- N04: missing declared finger bone;
- N05: unauthorized `CREATE_GRASP` operation;
- N06: stretch enabled after compilation;
- N07: one IK contact disabled during HOLD;
- N08: one target displaced during HOLD, producing excessive contact drift.

Schema/semantic negatives may be rejected before BuildPlan generation. Blender-structure negatives must fail compilation. Runtime mutations must fail the evaluator. A negative counts only when the expected layer and expected failing check are observed.

## Human and visibility gate

The contract requires visibility and human review, but neither may be inferred from structural or kinematic checks. Preview frames and a separate camera-visibility report must pass before a human-review packet is opened. The benchmark remains incomplete while genuine independent responses are fewer than three.

## Decision labels

- `AUTOMATION_PASS`: all machine gates and all eight negatives pass.
- `AUTOMATION_FAIL`: at least one frozen machine gate or negative fails.
- `HUMAN_PENDING`: automation may pass, but fewer than three authentic independent reviews exist.
- `BENCHMARK_COMPLETE`: automation passes, visibility passes, and the required human responses meet their rubric.
