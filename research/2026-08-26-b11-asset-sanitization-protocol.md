# B11 appended-asset sanitization protocol

Status: pre-registered before generating or compiling the adversarial asset.

## Question

Can a hash-valid `.blend` asset introduce undeclared evaluation behavior through drivers, constraints, rigid bodies or linked external libraries when appended by the restricted compiler?

B11 uses no malicious executable code. The adversarial structures only create visible/inspectable Blender dependencies so the integrity boundary can be tested safely.

## Expected asset boundary

An asset declared as data-only may contain geometry, materials, armatures and explicitly supported modifiers. It must not silently introduce:

- object or datablock drivers;
- pre-existing object, pose-bone or other constraints outside a typed SceneSpec operation;
- rigid bodies or rigid-body constraints;
- pre-existing animation actions outside ActorSpec/action resolution;
- linked external Blender libraries or library overrides;
- auto-run scripts.

The compiler itself may add typed constraints, animation and physics only after verified BuildPlan authorization. The sanitization point is immediately after append and before any such compiler-authored behavior.

## Frozen experiment

1. Audit every currently pinned B01–B08 asset for the forbidden structures.
2. Generate a hash-valid SET asset containing a hidden object driver, constraint and rigid body.
3. Compile a valid SceneSpec that points to this asset and records its exact hash.
4. Preserve whether the first run incorrectly emits a scene.
5. Add a deterministic post-append asset audit and reject the same asset before save.
6. Re-run B01, B05 and B08 positive controls and their frozen hashes/evaluations.

## Initial negative classes

- object driver;
- object constraint;
- rigid body;
- pre-existing transform action;
- linked-library dependency;
- library override;
- auto-execute preference enabled;
- missing sanitizer report or mismatch between imported collection and audit.

Formal B11 requires the combined adversarial asset plus isolated negative fixtures to be rejected, clean assets to remain accepted, and all observations to be published. It does not establish that every Blender modifier/node can never contain unsafe or nondeterministic behavior.

## Post-freeze execution note

The sanitizer was implemented as an in-process audit over the live appended Blender IDs. It does not consume a separately generated sanitizer report; therefore a “missing report” cannot be a bypass input and is not counted as an attack case. The isolated matrix does include a real library override and a shape-key datablock driver in addition to the combined first-run fixture.
