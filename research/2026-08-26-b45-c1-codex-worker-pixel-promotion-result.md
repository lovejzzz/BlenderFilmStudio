# B45-C1 — B44 `.blend` → exact decoded float pixels result

Date: 2026-08-26

Verdict: `B44_BLEND_TO_FLOAT_PIXELS_EXACT_AFTER_MEDIA_TYPE_CORRECTION`

## Result

B45-C1 passed its preregistered boundary. Four fresh Blender 5.2 Linux/amd64 Cycles CPU containers opened the four B44 `.blend` files directly, rendered one frozen frame each and saved the same Render Result as single-layer RGBA32 ZIP OpenEXR and RGBA8 PNG. The independent audit re-read every artifact, re-decoded every EXR and passed.

| shot | frame | runs | canonical decoded float-pixel SHA-256 | exact pair |
| --- | ---: | ---: | --- | --- |
| `SHOT_109` / TABLETOP | 24 | 2 | `b45f5424cce4982bc698dc31cef1e2731a22c1073c4795767de0f95140ce7dbd` | yes |
| `SHOT_110` / INTERIOR | 12 | 2 | `0dd7514f888d1db4a5602defc55d6aeda6caf8226667c908d4ce1d6dbab6544b` | yes |

The four processes exited 0 in 9,690–10,258 ms. Every decode contained 9,216 pixels and 36,864 finite little-endian float32 components in BGRA order. The result passed 14/14 original attacks, 2/2 correction attacks, the null-report totality self-test and the independent output audit. The final evidence self-hash is `6de9efa3e58ec19beccd650d5082e13dcc5c328ee64285192d193dfce7768c5d`.

## Preserved invalid attempt

The first B45 execution remains classified `INVALID_TOOL_INTERFACE_NO_PIXEL_DECISION`. All four containers reached `RENDER_STARTED`, then Blender rejected `OPEN_EXR` because the compiled scene still had `image_settings.media_type=MULTI_LAYER_IMAGE`. No pixels or reports were written. The runner then exposed a separate null-report attack-generator crash.

The failure, raw logs and their hashes were committed before C1. C1 permitted only two changes: assign `media_type=IMAGE` before the already frozen single-layer EXR save, and make analysis/attacks total over missing reports. Frames, renderer, one-sample setting, seeds, exact pixel threshold, worker containment, four-run count and disk policy did not change.

## Container bytes are not the pixel claim

The TABLETOP pair had different EXR and PNG SHA-256 values even though its decoded scene-linear float array was byte-exact. The INTERIOR pair happened to be exact at both container and decoded-pixel layers. This supports the preregistered decision to compare canonical decoded float arrays and to record container identity without requiring it.

## What is now supported

For these two frozen B43 proposals and their B44 worker builds, the chain now reaches real, finite, high-bit scene-linear pixels:

`saved Codex proposal → deterministic adapter → SceneSpec → immutable BuildPlan → Blender 5.2 worker compile → .blend → Cycles CPU render → decoded float pixels`

## Non-claims and next boundary

The 128×72, one-sample frames are diagnostic canaries. They do not demonstrate cinematic quality, denoising, 4K mastering, continuous-shot temporal stability, motion blur, human preference, production throughput, GPU/Eevee parity, cross-host reproducibility, arbitrary prompts or arbitrary scenes.

The next evidence-supported gap is a short continuous-shot promotion from the same B44 scenes. It must freeze a multi-frame interval, temporal comparison domain, quality intervention, wall-clock/disk budget and interruption recovery before execution. Cross-host/GPU reproduction remains a separate later boundary.

## Artifacts

- `experiments/codex-worker-pixel-promotion-v0-1/failure.json`
- `experiments/codex-worker-pixel-promotion-c1-v0-1/results.json`
- `experiments/codex-worker-pixel-promotion-c1-v0-1/audit.json`
- `specs/codex-worker-pixel-promotion.v0.1.json`
- `specs/codex-worker-pixel-promotion-media-type-correction.v0.1.json`
- tool freeze commit `26271a8696466c54d99286d769eec2c2f369816e`
