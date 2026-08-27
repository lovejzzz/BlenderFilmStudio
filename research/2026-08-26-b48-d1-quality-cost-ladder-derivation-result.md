# B48-D1 — Cycles CPU quality/cost ladder derivation result

Date: 2026-08-26

Status: `DERIVATION_COMPLETE_FORMAL_GATE_NOT_SET`

Protocol commit: `ed39580fa2a6814b28f9d981289e32d74ee6f60f`

Tool-freeze commit: `a48caada5d6db80c499a47f62fcd0ddd40805528`

Report SHA-256: `336ac860b13ff298f9eb745ae69d9ee202802766b503a4761301975e271193a6`

Analysis SHA-256: `f2469f764dbcd5bd7510bb892e9092312d59d1c991a759a513eebd1680fc745d`

## Observed ladder

One real Blender 5.2 Linux/amd64 Cycles CPU worker opened the frozen B44 TABLETOP-A1 `.blend` and rendered frame 22 seven times in the preregistered order. The source, frame, 128×72 resolution, seed, four threads, OCIO configuration, production-pass roster and container boundary remained fixed. Motion blur and persistent data remained disabled.

| Cell | Render seconds | Time × 8-raw | Linear NRMSE | Log-luma RMSE | Edge RMSE | EXR subimages |
|---|---:|---:|---:|---:|---:|---:|
| 8 spp raw | 0.807 | 1.00× | 0.266374 | 0.089041 | 0.665474 | 7 |
| 8 spp OIDN | 17.350 | 21.50× | 0.220933 | 0.041648 | 0.594920 | 8 |
| 32 spp raw | 2.537 | 3.14× | 0.111562 | 0.048134 | 0.268268 | 7 |
| 32 spp OIDN | 19.209 | 23.80× | 0.155707 | 0.028166 | 0.418719 | 8 |
| 128 spp raw | 9.558 | 11.84× | 0.058355 | 0.025424 | 0.139622 | 7 |
| 128 spp OIDN | 26.316 | 32.61× | 0.087483 | 0.017907 | 0.233056 | 8 |
| 512 spp raw reference | 27.460 | 34.03× | 0 | 0 | 0 | 7 |

All EXRs reopened successfully with Blender's OpenImageIO 3.1.13.1, and every Combined component was finite. The exact-top-k edge mask contained 922 pixels. Replaying the frozen analyzer produced a byte-identical analysis file.

## Counterintuitive result retained

OIDN did not dominate raw sampling. It reduced log-luminance error at every matched sample count. At 8 spp it also reduced linear and edge error, but it cost 21.5× the 8-spp raw render on this worker. At 32 and 128 spp it improved log-luminance error while increasing both scene-linear NRMSE and edge RMSE relative to the same-sample raw cell. The 128-spp raw cell finished in 9.558 seconds—substantially faster than every denoised cell—and had lower linear and edge error than all denoised cells against this reference.

This is a multi-objective result, not evidence that denoising is globally worse. A denoiser intentionally trades stochastic noise for bias/smoothing; the current metrics expose different parts of that trade. Human perception and temporal behavior remain unmeasured.

## Representation effect

Each denoised EXR contained an eighth `BFS_MASTER.Noisy Image` RGBA subimage in addition to the seven B47 production passes. The denoised files were 353,936–378,199 bytes versus 242,603–273,624 bytes for raw cells. A formal production pack must therefore version the denoised roster rather than assuming B47's exact seven-subimage layout remains unchanged.

## Why no formal threshold is promoted yet

The 512-spp reference is one finite-sample realization using the same seed as the candidates. It is not noiseless ground truth, and shared-seed sample-prefix behavior may make raw candidate comparisons optimistic. The one-process execution order also confounds cell with worker warm state. These limitations were preregistered for D1 and prevent a production decision.

The next required derivation is independent-reference calibration: render at least one high-sample reference with a different seed in a fresh worker, measure reference-to-reference disagreement, and decide whether a single reference, a two-reference mean or a higher sample count is needed before freezing B48's formal thresholds. Formal cells must then use fresh workers and isolate sampling, denoising and motion blur rather than collapsing them into one score.

## Non-claims

No cell is declared cinematic, production-ready or perceptually superior. These timings are observed on an ARM64 macOS host running the Linux/amd64 image through Colima/qemu, not a native x86 or cloud-cost forecast. D1 does not test temporal denoising stability, motion blur, depth of field, 2K/4K, GPU, long shots, characters or human preference.

## Artifacts

- `research/2026-08-26-b48-d1-quality-cost-ladder-derivation-protocol.md`
- `blender/derive_b48_quality_cost_ladder.py`
- `scripts/analyze-b48-quality-cost-ladder.py`
- `experiments/codex-worker-quality-cost-ladder-derivation-v0-1/render.report.json`
- `experiments/codex-worker-quality-cost-ladder-derivation-v0-1/analysis.json`
- `experiments/codex-worker-quality-cost-ladder-derivation-v0-1/*.exr`
