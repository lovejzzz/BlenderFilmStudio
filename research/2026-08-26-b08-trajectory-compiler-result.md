# B08 immutable trajectory-compiler result

Date: 2026-08-26

Environment: Blender 5.2.0 LTS `fbe6228777e7`, macOS arm64, Node v26.5.0

Classification: **FORMAL B08 TRUE / COMPILER INTEGRATION PASS / SOURCE PHYSICS NOT HUMAN APPROVED**

## Result

The frozen B07 TrajectorySpec now enters the formal data-only chain:

`SceneSpec v0.5 → immutable BuildPlan v0.5 → Blender 5.2 compiler → .blend + manifest → runtime evaluator`

- BuildPlan SHA-256: `7a4bccb640130db2dbf5c315907f81d5462605b6939b00a9df672c362d544dd9`
- TrajectorySpec file SHA-256: `c4efaf29535ca926a5e07014d50d1d4be2007fd5075b148687cb2e81e3caf146`
- pinned source-evaluation SHA-256: `90dee5925b528454e90b84d1bef66519224f9ab8e409cf814b3161c9d3dbe4bd`
- clean-build structural SHA-256 A/B: `46898404f12905d9fb1c31b7a3694a41b1d951cb688a15654a4dae084fe3077d`
- canonical BuildPlan recompilation: identical
- clean evaluation reports A/B: identical
- 132 evaluated frames: maximum position error `0 m`; maximum rotation error `0°`
- compiler-authored animation: seven transform curves, 132 linear keys per curve
- runtime shortcuts: no rigid body, constraint, or driver
- negative tests: 8/8 rejected at the registered layer

The two compressed `.blend` byte hashes differed. That observation was pre-registered as a non-gate because Blender container serialization can include nondeterministic metadata; the semantic structure and full runtime evaluation were identical.

## Security and provenance result

The immutable BuildPlan does not merely copy a URI. It verifies and embeds:

- the PROP library byte hash;
- the TrajectorySpec byte and canonical hashes;
- the source B06 evaluation byte hash;
- exact agreement between every exported trajectory sample and the pinned source evaluation;
- shot range and frame-rate agreement;
- binding ID, asset type and target-object agreement;
- explicit `CREATE_TRAJECTORY_REPLAY` authority;
- `disablePhysics: true` and `BAKED_WORLD_TRANSFORM` application mode.

The compiled object preserves `TECHNICAL_CANONICAL_CANDIDATE_NOT_HUMAN_APPROVED`. The pipeline therefore makes the playback reproducible without laundering its source status.

## Negative evidence

The compiler or evaluator rejected:

1. trajectory file hash drift;
2. source evaluation hash drift;
3. missing trajectory authority;
4. binding/TrajectorySpec target disagreement;
5. a hash-valid PROP library lacking the declared target object;
6. a missing trajectory frame;
7. a mutated compiled transform key, with non-zero evaluator exit;
8. a reintroduced rigid body, with non-zero evaluator exit.

## Interpretation

B08 closes the B07 immutable-BuildPlan integration gap. It proves that a selected per-frame motion artifact can be carried through the same restricted compiler used for cameras, lights, assets, actors, contacts and grasps.

It does **not** prove that the original B06 Bullet solve is deterministic, physically correct, visually cinematic, or human approved. That source-acceptance gate remains open and separate.

## Artifacts

- `specs/scene-spec.v0.5.schema.json`
- `specs/benchmarks/B08.scene.json`
- `experiments/trajectory-v0-2/B08.build-plan.json`
- `experiments/trajectory-v0-2/B08.manifest.json`
- `experiments/trajectory-v0-2/B08.evaluation.json`
- `experiments/trajectory-v0-2/results.json`
- `research/2026-08-26-b08-trajectory-compiler-protocol.md`
