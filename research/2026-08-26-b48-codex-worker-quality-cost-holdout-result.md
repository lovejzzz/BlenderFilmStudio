# B48 — numerical quality/cost holdout result

Date: 2026-08-26

Status: `B48_NUMERICAL_QUALITY_COST_POINT_SELECTED`

Selected cell: `C128_RAW`

Preregistration commit: `aef1344e6908167b18a80b3969dfe4eacda5d87a`

Tool-freeze commit: `ca52dd0330c39e87c3b4b502b144c744a2669394`

Evidence-core SHA-256: `445e75332645a0700bcef2b7ecbf9eb1d22c2356d2d3cc597e1b11e9d8ddfd0e`

Results SHA-256: `2d7155f38c79640daa45c72fc4e8e1b924825bbdac1c87ebcd2e8bdcba5a66d3`

Audit SHA-256: `5c759711f880ff873a9afebcc42bb1cf73bae8226b09d903b5292e472538124d`

## Formal result

Fourteen fresh Blender 5.2 Linux/amd64 Cycles CPU workers rendered two B48 holdout frames: TABLETOP 37 and INTERIOR 19. Each frame received three independent 512-spp raw references and four candidates: 32 raw, 32 OIDN, 128 raw and 128 OIDN. All source, runtime, containment, OCIO, seed-offset, sample, denoiser and production-pass checks held. Every Combined value was finite; raw cells contained the frozen seven subimages and OIDN cells contained the expected eighth `Noisy Image` subimage.

For each holdout, the analyzer formed the preregistered three-reference mean and local Monte Carlo floor. A candidate had to keep linear NRMSE, log-luminance RMSE and exact-top-10%-edge RMSE at or below 3× the corresponding floor on both scenes.

`C128_RAW` was the only candidate to pass both holdouts:

| Holdout | Linear floor × | Log-luma floor × | Edge floor × | Result |
|---|---:|---:|---:|---|
| TABLETOP frame 37 | 2.342 | 2.438 | 2.206 | pass |
| INTERIOR frame 19 | 1.767 | 1.771 | 2.066 | pass |

The 32-raw cell failed both shots. The 32-OIDN and 128-OIDN cells passed INTERIOR but failed TABLETOP because their linear and edge errors exceeded the frozen multiplier even while their log-luminance error was lower. This confirms that OIDN's smoothing/bias trade depends materially on scene content and cannot be promoted from one metric or one scene.

## Observed bounded cost

| Candidate | Eligible | Mean render seconds/frame | Mean fresh-container wall seconds | 240-frame render projection | 240-frame EXR projection |
|---|---|---:|---:|---:|---:|
| 32 raw | no | 3.067 | 12.732 | 736 s / 12.3 min | 57.5 MB |
| 32 OIDN | no | 20.018 | 29.906 | 4,804 s / 80.1 min | 84.2 MB |
| 128 raw | **yes** | **10.998** | **21.011** | **2,639 s / 44.0 min** | **61.9 MB** |
| 128 OIDN | no | 27.948 | 37.574 | 6,707 s / 111.8 min | 88.6 MB |

The 240-frame figures are mechanical projections from the two observed still-frame render times and mean EXR sizes. They are not a rendered shot and do not include one-container sequence amortization, retries, temporal effects, asset loading variation, storage replication, electricity or cloud price. Fresh-container wall time is reported separately because it includes roughly 8–10 seconds of Blender/scene startup per cell.

## Audit

All 18 preregistered attacks reached their frozen rejection reason. The independent audit reran the frozen analyzer, reopened all 14 EXRs, recomputed both ensemble means, floors, candidate metrics, cost projections, selection and evidence hash, and produced a byte-exact result replay. No experiment container remained.

## Supported claim

For the two frozen 128×72 holdout stills on this bounded CPU worker, 128 spp raw is the cheapest tested cell whose three numerical error metrics remain within 3× the locally measured independent-512-spp reference floor. This is a defensible numerical operating point for the next engineering stage.

## Non-claims and next boundary

B48 does not establish human cinematic quality, perceptual preference, temporal denoiser stability, motion blur, depth of field, 2K/4K scaling, characters, hair, GPU/Eevee behavior, native x86 throughput, cloud price or complete-shot execution.

The next evidence gap is B49: resolution and cinema-feature scaling. It should hold the selected 128-raw baseline, separately intervene on spatial resolution and motion blur/depth of field, measure time/memory/output scaling, and only then prepare a blinded human review. Dollar cost must remain an explicit projection from a measured compute backend, not a claim inferred from local runtime.

## Artifacts

- `specs/codex-worker-quality-cost-holdout.v0.1.json`
- `research/2026-08-26-b48-codex-worker-quality-cost-holdout-protocol.md`
- `experiments/codex-worker-quality-cost-holdout-v0-1/results.json`
- `experiments/codex-worker-quality-cost-holdout-v0-1/audit.json`
- `experiments/codex-worker-quality-cost-holdout-v0-1/run.receipt.json`
- `experiments/codex-worker-quality-cost-holdout-v0-1/*/production.exr`
