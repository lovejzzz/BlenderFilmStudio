# B08 immutable trajectory-compiler protocol

Status: pre-registered before the first SceneSpec v0.5 build.

## Question

Can the already frozen B07 TrajectorySpec enter the formal SceneSpec → immutable BuildPlan → Blender 5.2 compiler without executable input, hidden physics, hash drift, or loss of its unapproved-source status?

B08 tests compiler integration and deterministic replay. It does not establish that the source B06 rigid-body solve is physically correct, cross-process reproducible, visually convincing, or human approved.

## Positive gates

1. SceneSpec v0.5 and its embedded TrajectorySpec pass schema and semantic validation.
2. BuildPlan verifies and pins the trajectory bytes, source-evaluation bytes, PROP asset bytes, and required `CREATE_TRAJECTORY_REPLAY` authority.
3. Recompiling one SceneSpec produces byte-identical canonical BuildPlans.
4. Two Blender 5.2 factory-startup builds produce one structural hash.
5. All 132 compiled world-space samples match position within `1e-7 m` and rotation within `1e-5 deg`.
6. The replay target has no rigid body, constraints, drivers, or pre-existing animation; only compiler-authored transform keys are permitted.
7. The compiled scene and reports preserve `TECHNICAL_CANONICAL_CANDIDATE_NOT_HUMAN_APPROVED`.
8. The two clean evaluation reports are identical after excluding run-path and timestamp metadata.
9. A failing runtime check exits non-zero.

Binary `.blend` byte equality is recorded but is not an acceptance gate because Blender containers may contain nondeterministic serialization metadata.

## Frozen negative classes

- N01 trajectory file hash mismatch — reject during BuildPlan resolution;
- N02 source-evaluation hash mismatch — reject during BuildPlan resolution;
- N03 missing trajectory authority — reject before BuildPlan emission;
- N04 binding/TrajectorySpec target mismatch — reject during BuildPlan resolution;
- N05 verified PROP collection lacks the declared target object — reject inside Blender compilation;
- N06 missing or malformed frame sample — reject by TrajectorySpec validation;
- N07 compiled transform-key mutation — reject during runtime evaluation;
- N08 rigid-body injection — reject during runtime evaluation.

## Success interpretation

Passing B08 proves a narrow property: a selected, immutable per-frame transform artifact can be compiled and replayed reproducibly through the formal data-only pipeline. It does not turn the selected source trajectory into approved physics or approved cinema.

Formal B08 remains false until all gates and all eight negatives execute. Even if formal B08 becomes true, source-solve human approval remains a separate open dependency.
