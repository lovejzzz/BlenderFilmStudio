# ActorSpec v0.1 — Blender 5.2 character-system experiment

Date: 2026-08-26  
Status: executed on Blender 5.2.0 LTS, macOS arm64  
Scope: technical mannequin, rig identity, Action Slot, Shape Keys, gaze constraints, socket slip, and unsafe Driver rejection

## Question

Can the character-facing part of a Blender film workflow be expressed as bounded, auditable data instead of arbitrary scene scripting—and can Blender 5.2 evaluate that data predictably?

This experiment does **not** ask whether the result looks like a real human. It asks whether the minimum control substrate is explicit enough to compile, inspect, reject when unsafe, and measure after Blender's dependency graph evaluates it.

## Blender 5.2 boundary

The following mechanisms are directly addressable through Blender data:

- Armatures, rest bones, pose bones, per-bone rotation modes, vertex groups, and Armature modifiers.
- Constraints such as IK, Damped Track, Limit Rotation, Child Of, and Copy Transforms.
- Shape Keys and animated Shape Key values.
- Actions, Action Slots, F-Curves, and interpolation modes.
- Named bone sockets represented by semantic bone mapping plus local offsets.
- Drivers, but with an important security boundary.

Blender Drivers are not uniformly safe data. A scripted Driver that is not a simple expression can invoke Python. ActorSpec v0.1 therefore requires `BUILTIN_OR_SIMPLE_ONLY`, `allowFullPython: false`, and a runtime audit of Blender's `is_simple_expression` result. A JSON Schema alone cannot inspect the internals of an imported `.blend` asset.

## Contract

ActorSpec v0.1 freezes:

1. Actor asset URI and exact binary SHA-256.
2. Semantic bone map and normalized rest-pose SHA-256.
3. Mesh topology and Shape Key set hashes.
4. Armature modifier policy and allowed constraints.
5. Socket names and local transforms.
6. Performance layer order: `BODY → BREATH → GAZE → FACIAL → CONTACT`.
7. Action libraries, facial channel curves, gaze keys, contact windows, and numerical tolerances.
8. Security roots, network denial, and arbitrary-Python denial.

The schema and semantic validator contain 16 fixtures: three valid cases and thirteen invalid cases. All 16 behaved as expected.

## Project-owned B03 asset

The experiment generates a deliberately simple technical mannequin:

- 10 semantic bones.
- 4 armature-bound meshes.
- 4 Shape Keys: Basis, jaw open, left blink, right blink.
- Two eye Damped Track constraints and one head Limit Rotation constraint.
- One Blender 5.2 Action Slot with four F-Curves.
- Four measurable sockets: left/right palm and left/right sole.

Pinned chosen asset SHA-256:

`10feb54a274ea6601f18379ee01964fbfda02d8cc0360b0efe3df3908ef4378f`

Normalized semantic identity SHA-256:

`a923c92b979ff9bb68087e72284a9ba4024241af563579ce22f65500b0efb1e7`

Motion library SHA-256:

`165ea0b9867e20f7948c3d1be15a77ef77f7badc2addcf5e8054cafe2b1da994`

## Structural audit

The Blender-side audit ran 13 checks and passed all 13:

- exact asset hash;
- armature existence;
- semantic bone map;
- rotation mode;
- normalized rest-pose hash;
- per-mesh topology hashes;
- Armature modifier and preserve-volume policy;
- Shape Key set hash;
- socket resolution;
- constraint allowlist;
- Driver policy;
- external Action library hash and F-Curve structure;
- aggregate identity lock.

Two negative runtime tests also passed:

1. A schema-valid asset copy with the non-simple Driver expression `[frame][0]` was rejected at `A11_DRIVER_POLICY`.
2. A schema-valid ActorSpec with a changed rest-pose hash was rejected at `A05_REST_POSE_HASH`.

This proves why validation must happen at both the document layer and the evaluated Blender-asset layer.

## Evaluated performance

The evaluator loaded the chosen asset and motion library into a factory-started Blender process, assigned the Action Slot, authored facial F-Curves, animated the gaze target, stepped the dependency graph, and sampled the resulting pose and sockets.

| Check | Result | Measurement |
| --- | --- | --- |
| Body Action evaluated | PASS | Head quaternion delta `0.079934043` |
| Authored facial values | PASS | 9/9 authored key values, max absolute error `0.0` |
| Eye gaze | PASS | Maximum angular error `0.0°`; threshold `2°` |
| Left foot socket slip | PASS | `0.0 m` across 72 samples; threshold `0.01 m` |
| Right foot socket slip | PASS | `0.0 m` across 72 samples; threshold `0.01 m` |

The zero foot-slip result only proves that each socket remained stationary during its declared window. No external floor target exists in ActorSpec alone, so target-relative contact position and rotation errors remain unmeasured.

## Falsified implementation: correct angle, invisible eyes

The first visible evaluation exposed a subtle failure. Both eye constraints reported a `0.0°` target error, yet the rendered eye meshes were behind the head.

Cause: the Damped Track constraint aimed local negative Y at the target while the visible eye geometry extended beyond the bone tail on local positive Y. The constraint was mathematically satisfied, but the mesh moved in the opposite direction.

Correction: align the constraint axis with the geometry's rest-space direction (`TRACK_Y`). The angular error remained `0.0°`, and the eye geometry became visible and moved between the two target positions.

This result is important: a constraint-error scalar is insufficient unless the contract also fixes bone-axis and geometry conventions or includes a visual/geometry observability test.

## Binary regeneration result

The actor generator was run twice with the same Blender build and the same output path:

- run A asset SHA: `a1a626484ee16f963560f384afe5ae8da70dd39a8d73886f68966fc519157fa2`
- run B asset SHA: `c72713bc9f579c7b19c298e34911609dd7ca04520f1b893912697316304cc2a9`
- raw `.blend` asset SHA equality: **false**
- normalized semantic identity equality: **true**
- motion library SHA equality: **true**

Therefore a Blender library file is not treated as its own canonical semantic identity. ActorSpec pins the exact chosen binary for immutable builds, while regeneration equivalence is evaluated with normalized rest-pose, topology, Shape Key, motion, and aggregate identity hashes.

## What is now technically supported

- A bounded character contract can describe and validate a project-owned rig, deformation channels, performance layers, sockets, and asset provenance.
- Blender 5.2 Action Slots and Shape Keys can be populated and evaluated without arbitrary Python inside the asset.
- Imported asset internals can be audited before use.
- Non-simple scripted Drivers can be rejected even when the surrounding ActorSpec is valid.
- Gaze angular error and socket slip can be measured from evaluated Blender state.
- Exact binary pinning and semantic regeneration identity can coexist as two different contracts.

## What remains unsupported

- Photoreal skin, eyes, teeth, tongue, hair, cloth, muscle, and soft-tissue deformation.
- Natural acting, speech performance, lip synchronization, emotion, or micro-expression quality.
- Retargeting from arbitrary external rigs.
- Mesh-level hand/finger contact and collision-safe grasping.
- Contact error against a scene-owned target, because ActorSpec is not yet embedded in SceneSpec.
- Cross-shot identity under changing costumes, lighting, lenses, and asset versions.
- Human perceptual acceptance and cinema-quality judgment.

## Next falsifiable benchmark

Embed ActorSpec into SceneSpec and compile B03 as a close-up with scene-owned gaze targets, then compile B04 as a full-body prop interaction. The next validator must measure:

- scene-target-relative gaze error;
- target-relative foot and palm position/rotation error;
- foot sliding across every planted frame;
- Action/Shape Key layer provenance in the compiled `.blend`;
- identity hashes before and after each shot build;
- human review of close-up facial readability and contact plausibility.

## Evidence

- `specs/actor-spec.v0.1.schema.json`
- `specs/benchmarks/B03.actor.json`
- `specs/fixtures/actor-spec-fixtures.v0.1.json`
- `experiments/actor-v0-1/asset-generation.json`
- `experiments/actor-v0-1/audit.json`
- `experiments/actor-v0-1/results.json`
- `experiments/actor-v0-1/performance-evaluation.json`
- `experiments/actor-v0-1/regeneration.json`

## Primary references

- [Blender 5.2 Animation & Rigging release notes](https://developer.blender.org/docs/release_notes/5.2/animation_rigging/)
- [Blender 5.2 PoseBone API](https://docs.blender.org/api/5.2/bpy.types.PoseBone.html)
- [Blender 5.2 Constraint API](https://docs.blender.org/api/5.2/bpy.types.Constraint.html)
- [Blender 5.2 ShapeKey API](https://docs.blender.org/api/5.2/bpy.types.ShapeKey.html)
- [Blender 5.2 Key API](https://docs.blender.org/api/5.2/bpy.types.Key.html)
- [Blender 5.2 ActionSlot API](https://docs.blender.org/api/5.2/bpy.types.ActionSlot.html)
- [Blender 5.2 Driver API](https://docs.blender.org/api/5.2/bpy.types.Driver.html)
- [Blender manual — Armature modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/armature.html)
- [Blender manual — Drivers introduction and security](https://docs.blender.org/manual/en/5.2/animation/drivers/introduction.html)
