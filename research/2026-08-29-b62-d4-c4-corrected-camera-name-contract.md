# B62-Q1-D4-C4 · Corrected-camera name contract

Date: 2026-08-29  
Status: PREREGISTERED — no C4 tool change or v0.5 root existed when this protocol was written

## Retained failure

The C3 retry at `experiments/b62-camera-quality-holdout-render-v0-4` ran one fresh BUILD Blender, twelve paired Cycles CPU renders and one independent Blender reopen. All six original/corrected Combined pixel pairs differed, and every render row recorded `SHOT_CLOSE_REFLECTION` with the camera used for its condition. The Node audit nevertheless failed its single new routing check and therefore wrote a null scientific verdict.

The failure is a duplicated-name contract error in the Node auditor. Its local table expects `CAM_CLOSE_REFLECTION_CORRECTED`, while the already frozen base spec, builder, render tool and independent audit all name the derived camera `CAM_CLOSE_REFLECTION_CORRECTED_D4`. Every corrected v0.4 render row records that authoritative name for both `camera` and `timelineMarkerCamera`.

v0.4 remains immutable failed evidence: 35 files, 54,119,323 bytes, tree SHA-256 `365b4bc64267575bbdbcb92f7390c9690f18514e5c08c10bcc56f584003e885e`. It may be used only as the retained failure bound by C4.

## Sole authorized semantic repair

The Node auditor may replace its duplicated expected-camera literals with:

- ORIGINAL → `spec.selectedIntervention.sourceCamera`
- CORRECTED → `spec.selectedIntervention.correctedCamera`

The runner and auditor may bind this C4 spec, protocol and retained v0.4 tree and change the formal root to `experiments/b62-camera-quality-holdout-render-v0-5`.

No Blender Python byte may change. The retry must create a new derived scene, perform all twelve Cycles renders, independently reopen the scene and decode all outputs again. Reusing v0.4 images or reports is forbidden.

## Frozen scientific boundary

The six holdout frames, camera transform, 96-frame bake, geometry template, 0.90 clamped-area maximum, 960×540 Cycles CPU 16 spp settings, render count, resource ceilings and verdict mapping remain unchanged.

The invalid v0.4 independent observation is diagnostic only but predicts the unchanged mapping: original failed 6/6; corrected passed frames 193, 204, 228, 252 and 276; corrected frame 288 failed only because its clamped union area was 0.93378717684983. A technically valid v0.5 is therefore expected to produce `B62_CLOSE_CAMERA_CORRECTION_FAILS_FROZEN_HOLDOUT`. That is a valid scientific rejection, not an implementation failure.

Human review remains separate and must not override the frozen machine verdict.
