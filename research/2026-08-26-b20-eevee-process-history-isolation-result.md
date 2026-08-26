# B20 Eevee process-history isolation result

Date executed: 2026-08-26.

Frozen protocol: `research/2026-08-26-b20-eevee-process-history-isolation-protocol.md`
Machine result: `experiments/eevee-process-history-isolation-v0-1/results.json`

Status: **FORMAL / VALID / PROCESS_ISOLATION_NOT_SUFFICIENT**

## Outcome

The pre-registered claim that a new Blender process per frame might restore strict decoded-pixel reproducibility was falsified.

| Gate | Exact sentinel pairs | Failed pixels | Maximum error | Exact gate |
|---|---:|---:|---:|:---:|
| HISTORY: full 1-144 in one process | 18 / 36 | 118 | 0.0039215982 | fail |
| FRESH: one new process per sentinel | 26 / 36 | 56 | 0.0039215982 | fail |
| HISTORY × FRESH cross-mode | 61 / 108 | 320 | 0.0039215982 | fail |

All 39 planned render processes had distinct observed PIDs. They rendered 468 frames and reported 82.815872 seconds of render-call time: 73.281909 seconds in the three complete HISTORY sequences and 9.533963 seconds across the 36 FRESH single-frame calls. This excludes process-startup wall time and must not be used as a total cost estimate.

The frozen decision is `PROCESS_ISOLATION_NOT_SUFFICIENT` because neither within-mode gate passed. FRESH produced more exact pairs and fewer failed pixels in this run, but the experiment did not pre-register a probabilistic improvement test. Those counts remain descriptive and are not relabeled as a successful intervention.

## Frame-level observation

Under FRESH, frames 1, 20, 38, 83, 93, 114 and 144 were exact in all three replicate pairs. Frames 5, 35, 47, 103 and 110 each split into two identical outputs and one differing output. Frame 110 had 10 failed pixel observations across the three FRESH pairs; F-A/F-B were exact while F-A/F-C and F-B/F-C each differed at five pixels.

HISTORY was non-exact even at frame 1, which was the first actual render of each process. Together with the five FRESH failures, this rules out accumulated prior-frame history as a sufficient explanation. It does not identify whether GPU scheduling, sample reduction, float render buffers, color management or encoding is the remaining boundary.

## Identity and controls

- Blender 5.2.0 LTS build `fbe6228777e7`, binary SHA-256 `60ba7a9…129f2`;
- source B02 `.blend` SHA-256 `2a50536…11b0b`;
- ACES 2 OCIO SHA-256 `24ec818…ad15`;
- B20 preregistration SHA-256 `b59908f…fbedf`;
- renderer `6c1bb9b…35265`, comparator `3e6f0a9…069ed`, runner `963d442…8a2f`;
- 32 Eevee samples, dither 0, Fast GI on, TAA reprojection on, PNG RGBA8 at 960×540;
- source `.blend` never saved by an intervention.

## Negative evidence

All 18 implemented attacks reached their intended reason. They cover the 17 frozen categories plus an explicit configurator-SHA attack: spec, ReviewRenderSpec, Blender, OCIO, scene, renderer, configurator and comparator identities; samples, dither, GI and reprojection; HISTORY order; FRESH scope; PID aliasing; missing and mutated sentinel files; and comparison-manifest binding.

The accepted process ledger contains 39 unique invocation IDs and 39 unique observed PIDs. Six manifests bind the selected image hashes. Fifteen selected-frame comparisons bind both manifests and both decoded-image hashes.

## What was falsified

- Restarting Blender for every frame is not sufficient for strict same-machine Eevee PNG8 reproducibility.
- Prior rendered-frame history is not the sole sufficient explanation for the B15-B19 drift.
- A smaller mismatch count in one three-replicate treatment is not a production reliability estimate.

## Next boundary

The current evidence does not locate whether the one-code-value variation exists in Blender's scene-linear render result before file output, or is introduced by display transform / PNG8 quantization. The next experiment should capture and hash the in-memory float Render Result and the PNG8 output from the same render, with frozen channel order, float serialization and exact/metric decisions. That boundary is closer to the project's high-bit-depth EXR master requirement than another post-hoc visual switch.

## Non-claims

This diagnostic subset does not estimate all-frame or all-scene failure probability. It does not locate a Blender source line, prove a GPU race, generalize to Cycles or OpenEXR, or show that the observed differences are perceptually important. It establishes only that per-frame process isolation is not a strict reproducibility fix for this frozen profile.
