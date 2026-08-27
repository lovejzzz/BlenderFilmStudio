# B52-D12.8-C1 · Projective motion/disocclusion adaptive-risk result

Date: 2026-08-27

Formal verdict: `PROJECTIVE_MOTION_DISOCCLUSION_ADAPTIVE_GATE_NOT_SUPPORTED`

Corrected audit: `B52-D12.8-AUDIT-C2 · PASS · 16/16 · 40/40 mutations`

## What was tested

The unchanged D12.7 candidate—radius-2 interior plus an inclusive `1/1048576` local RGB risk gate—was tested on four unseen Blender 5.2 perspective scenes: a moving foreground owner with disocclusion, camera dolly/yaw with parallax and bounds loss, a same-Object-Index depth-reveal trap, and a static multi-owner control. Transform-aware owner, bounds, alpha and depth checks ran before the risk gate. Invalid or risk-rejected history had to copy current float32 RGBA exactly.

The formal root contains 16 real Cycles source renders, eight adapters, 16 dual consumers, 32 typed-envelope encoders, one independent analyzer and the original independent audit. The original 74 PIDs are immutable. C2 added one read-only audit PID and no new render, adapter, consumer, envelope or analyzer process.

## Primary measurements

| Fixture | Vector endpoint max | Depth relative max | Radius 2 | Adaptive | Retention | Risk rejected | Adaptive RGB max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Rigid owner sweep / disocclusion | `8.399316e-5 px` | `4.129935e-7` | 8,823 | 1,498 | 16.978% | 7,325 | `0` |
| Camera dolly/yaw / parallax | `5.902389e-5 px` | `4.426309e-7` | 14,082 | 0 | 0% | 14,082 | empty domain |
| Same-index depth reveal | `6.749752e-5 px` | `2.892713e-1`* | 11,843 | 1,560 | 13.172% | 10,283 | `2.980232e-8` |
| Static multi-owner control | `2.288818e-5 px` | `2.029757e-7` | 9,045 | 9,045 | 100% | 0 | `5.960465e-8` |

`*` The frozen analyzer included correctly rejected `INVALID_DEPTH` pixels in this aggregate. The check remains false; the domain defect is recorded rather than repaired post hoc.

All eight cells had zero risk-underbound RGB samples and exact current-RGBA fallback. Structural stress was real: the moving sweep produced 2,332 `INVALID_OWNER` and 2,400 `INVALID_BOUNDS` pixels; camera motion produced 984 `INVALID_BOUNDS`; the same-index trap produced 3,678 `INVALID_DEPTH` pixels. No false invalid-history acceptance was observed.

## Why the candidate failed

The static risk formula measures weighted tap-to-current color disagreement. In a static scene this identifies only a small arithmetic tail. Under real object or camera motion, correct history can differ substantially from the current pixel even when the projective correspondence is structurally valid. The same frozen threshold therefore rejects most or all of the useful moving history. This is not a render-quality failure; it is a mismatch between a static local-contrast bound and a moving correspondence domain.

`ADAPTIVE_QUALITY` is also false because the preregistered rule required every cell to contain accepted samples. The camera-motion cell accepted zero. `COVERAGE` is independently false. The rejected verdict does not depend on the radius-3 comparator, which remained report-only as preregistered.

## Exact cross-language boundary

Python and Node were byte-identical for all eight decision/reconstruction payloads in every cell. Only `risk.rgb64` differed in the six moving cells:

| Fixture / repeat | Differing float64 scalars | Maximum absolute difference | Decision differences |
|---|---:|---:|---:|
| Rigid sweep R1 / R2 | 46 / 46 | `2.168404344971009e-19` | 0 / 0 |
| Camera parallax R1 / R2 | 88 / 88 | `4.336808689942018e-19` | 0 / 0 |
| Same-index depth R1 / R2 | 16 / 16 | `2.168404344971009e-19` | 0 / 0 |
| Static control R1 / R2 | 0 / 0 | `0` | 0 / 0 |

Exact raw identity therefore remains false even though the discrete decisions agree. A future protocol needs a canonical numerical representation—such as a frozen fixed-point risk encoding or a precisely specified binary64 operation graph—before cross-language identity can be promoted.

## Audit history

The original audit passed 9/10 checks and failed only `DUAL_PAYLOAD_IDENTITY`. That check incorrectly required the failed scientific identity condition itself to pass, rather than verifying that the immutable result faithfully recorded the raw divergence. The runner correctly retained `run.failure.json` and wrote no receipt.

The preregistered C2 audit used one new Python process, spawned no scientific subprocess, bound its own and the original audit's Git blobs, verified every immutable top-level identity, replayed the original five false and nine true result checks, accounted for the original 74 PIDs plus its own PID, and recomputed the complete 300-scalar difference roster. It passed 16/16 checks and 40/40 mutation attacks. The negative verdict and every formal byte remain unchanged.

## Next falsifiable experiment

A future D12.9 must use new fixtures and be preregistered from scratch. It should:

1. replace absolute tap-to-current disagreement with a motion-aware error bound that separates expected transported signal change from interpolation uncertainty;
2. define a canonical cross-language risk representation before any implementation;
3. compute depth-oracle agreement only on the declared structurally valid domain while separately checking expected depth rejection;
4. retain the transform-aware structural gate and exact fallback behavior, which passed here;
5. require useful motion coverage, not merely low error on a surviving empty or tiny domain.

## Immutable identities

- Corrected spec SHA-256: `d7e7c0ee0bd7f512766188eabda9fa0dccb098a0729b26487aa38bee97d6aea6`
- Formal result SHA-256: `0a621b87b3565b3106b11ab1c9cef705f16ab3701c02d9deef5e730bee2992f1`
- Formal evidence hash: `8e0d17403cac74cdd51dcbb3d78a2e4a6864ee8fdd53b3c6d567179ab77bf76e`
- Original failed audit SHA-256: `015353cef9dc8a3005ff7df432bd14c4e3ca77e0389e4d025c58ef8df30d01da`
- C2 audit SHA-256: `0dd3a31e7244a76167ee8c61e690fa2e1bd38ba1089351e6088192c7fb6df7d8`
- C2 audit hash: `872ebf57332da68bc18453a5747e47326e97dc2aeff85d84bc4f72c88f1d01b5`
- Site-proxy manifest SHA-256: `eddcb08fda68b13090a698f19710a2cf440cfbd99af2eecd8d8ae0a0be199c12`

## Non-claims

This experiment does not validate curved or deforming surfaces, skinned characters, transparency, hair, particles, volumes, motion blur, depth of field, noisy path-traced lighting, temporal denoising, perceptual stability, cinematic quality, character consistency, production rendering or cross-platform equivalence. The diagnostic PNGs are navigation proxies; formal decisions derive only from the immutable scene-linear arrays.
