# B22 Eevee fixed-thread-count factorial result

Date executed: 2026-08-26

Pre-registration commit: `66c9778`

Accepted tool commit: `3db8467`

Decision: **`THREAD_COUNT_NOT_SUFFICIENT`**

## Result

The frozen T01 and T08 cells both failed strict scene-linear EXR32 reproducibility:

| Cell | Exposed Blender state | Exact decoded pairs | Failed pixels | Maximum absolute error |
|---|---|---:|---:|---:|
| T01 | `FIXED / 1` | 19 / 36 | 364 | 0.005615234375 |
| T08 | `FIXED / 8` | 22 / 36 | 346 | 0.00634765625 |

All 72 observations ran in distinct Blender processes. Each process rendered exactly once and saved exactly one 960×540 RGBA float ZIP OpenEXR. All 19 frozen negative categories reached their intended rejection reason.

The pre-registered sufficient-cause test therefore fails: setting the exposed render-thread count to one does not restore strict cross-process equality. The difference between 19 and 22 exact pairs is descriptive only; this design did not pre-register an effect-size or probability comparison.

## Rejected implementation assumption

The first post-freeze implementation (`780e470`) assumed the source `.blend` already contained the B21 dither intervention. The first real Blender process reported source dither `1.0`, so the renderer rejected the observation before producing an accepted result. B21 had set dither to zero only in memory through its own configurator.

The accepted configurator (`3db8467`) therefore records source thread state first, then explicitly fixes dither 0, Fast GI on and TAA reprojection on together with the requested thread state. The protocol and decision gates were not changed.

## What this does and does not establish

Supported: Blender's exposed `scene.render.threads=1` control is not sufficient to eliminate the observed Eevee EXR32 variation on this Apple M4 Max / Blender 5.2 profile.

Not supported: that concurrency is irrelevant, that a source-level race exists, or that the render-thread setting serializes Metal/Eevee GPU shader execution. The property is CPU-facing and may not govern GPU scheduling or sample reduction.

## Evidence

- `experiments/eevee-thread-count-factorial-v0-1/results.json`
- `experiments/eevee-thread-count-factorial-v0-1/evidence/process-ledger.json`
- `experiments/eevee-thread-count-factorial-v0-1/evidence/run-order.json`
- `experiments/eevee-thread-count-factorial-v0-1/evidence/T01-*.manifest.json`
- `experiments/eevee-thread-count-factorial-v0-1/evidence/T08-*.manifest.json`
- `experiments/eevee-thread-count-factorial-v0-1/evidence/comparisons/`

## Next falsifiable boundary

Separate per-render variation from process-initialization variation. A next experiment should compare repeated renders of the same sentinel inside one Blender process against the already-observed fresh-process design, while holding EXR32, sample count and all exposed controls fixed. This can distinguish “new process / GPU initialization” from “each render invocation” without claiming an internal mechanism.
