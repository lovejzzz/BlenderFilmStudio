# B07 immutable baked-trajectory protocol

Status: pre-registered before the first replay build.

## Question

Can one explicitly selected B06 rigid-body trajectory be converted into a hash-pinned, versioned per-frame transform artifact and replayed identically in two physics-disabled Blender 5.2 builds?

This experiment addresses deterministic downstream playback. It does not make Bullet deterministic, validate the selected physical trajectory, or replace visual/human approval of the source solve.

## Artifact contract

TrajectorySpec v0.1 must include:

- a stable ID and target object ID;
- exact source structure hash, evaluation URI and evaluation byte hash;
- 24 fps, frames 1–132, and exactly one ordered sample for every frame;
- world-space location in metres;
- normalized world-space quaternion in WXYZ order;
- explicit replay tolerances and selection status;
- no network access or executable code.

## Positive gates

1. The TrajectorySpec validates and its file SHA-256 matches the replay request.
2. Source evaluation bytes match the declared source hash.
3. Samples are continuous, ordered, unique, finite, and cover frames 1–132 exactly.
4. Quaternions are normalized within `1e-6`.
5. Two factory-startup replay builds produce the same structural hash.
6. Every replay frame matches the declared location within `1e-7 m`.
7. Every replay frame matches the declared rotation within `1e-5 deg`.
8. The replay prop has no rigid body, parent, constraint, or driver.
9. Replay evaluation reports the exact pinned trajectory SHA-256.

## Initial negative classes

- wrong trajectory file hash;
- missing frame sample;
- duplicate/out-of-order sample;
- non-normalized quaternion;
- source evaluation hash mismatch;
- replay object with a rigid body shortcut;
- replay transform key mutation;
- undeclared target object.

Formal B07 additionally requires all eight negatives, an immutable BuildPlan integration, public evidence, and an explicit distinction between source-solve acceptance and playback acceptance.

## Nonclaim

The initial source is a technical canonical candidate chosen only because its individual B06 machine gates passed. It has not passed B06 cross-process reproducibility, active-camera approval, or authentic human review. B07 must preserve that status rather than laundering it into “approved physics.”
