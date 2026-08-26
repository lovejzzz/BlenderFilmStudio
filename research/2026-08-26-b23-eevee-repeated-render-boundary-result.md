# B23 Eevee repeated-render boundary result

Date executed: 2026-08-26

Pre-registration commit: `71af367`

Tool commit: `9a65ddb`

Decision: **`PER_RENDER_VARIATION_SUPPORT`**

## Result

| Frozen gate | Exact decoded pairs | Failed pixels | Maximum absolute error |
|---|---:|---:|---:|
| WITHIN_PERSIST | 59 / 108 | 3,630 | 0.00634765625 |
| PERSIST_CROSS | 64 / 108 | 974 | 0.00634765625 |
| FRESH_CROSS | 25 / 36 | 300 | 0.005615234375 |

All 72 planned processes had unique observed PIDs. PERSIST processes each loaded the source once, held one sentinel frame and made three consecutive render calls; FRESH processes made one. The accepted run produced 144 scene-linear RGBA32 ZIP OpenEXRs. All 20 frozen attacks reached their intended rejection reason.

Because WITHIN_PERSIST failed its 108/108 zero-tolerance gate, the first applicable pre-registered label is `PER_RENDER_VARIATION_SUPPORT`. Strict float variation can recur between render invocations without restarting Blender or changing the frame.

## Frame-level observation

Within-process exact counts ranged from 1/9 at frame 103 to 9/9 at frame 114. Frame 5 contributed 2,704 of the 3,630 failed pixels. These are descriptive observations, not a post-hoc subgroup gate or probability estimate.

## Interpretation boundary

Supported: process initialization is not a sufficient origin for the observed variation. The recurrence boundary is each render invocation or later Eevee/Metal work.

Not supported: that a source-level race exists, that GPU scheduling is the cause, or that the variation is perceptually visible. Exact float equality is a provenance/reproducibility property, not automatically a cinematic-quality requirement.

## Evidence

- `experiments/eevee-repeated-render-boundary-v0-1/results.json`
- `experiments/eevee-repeated-render-boundary-v0-1/evidence/process-ledger.json`
- `experiments/eevee-repeated-render-boundary-v0-1/evidence/PERSIST.manifest.json`
- `experiments/eevee-repeated-render-boundary-v0-1/evidence/FRESH.manifest.json`
- `experiments/eevee-repeated-render-boundary-v0-1/evidence/comparisons/`

## Next research boundary

B15-B23 have now falsified strict Eevee pixel determinism under the production-quality 32-sample profile across dither, sampling, GI, reprojection, process history, output format, exposed CPU thread count, process initialization and repeated render calls. The next useful question is no longer another post-hoc exactness switch. It is a separately pre-registered production reproducibility contract using new holdout renders: structural identity remains exact, while pixel variation is evaluated with independently frozen numeric and perceptual gates. The current B23 observations may motivate candidate metrics but must not set and validate their thresholds on the same data.
