# B21 same-Render-Result dual-output localization result

Date executed: 2026-08-26.

Frozen protocol: `research/2026-08-26-b21-dual-output-localization-protocol.md`

Status: **FORMAL / VALID / PRE_PNG_VARIATION_SUPPORT**

## Outcome

Scene-linear float OpenEXR output was already non-exact. The ACES display transform / PNG8 path is therefore not a sufficient explanation for the B15-B20 drift.

| Same-Render-Result output | Exact decoded pairs | Failed pixels | Maximum error | Gate |
|---|---:|---:|---:|:---:|
| RGBA32 float OpenEXR, scene-linear ACEScg | 21 / 36 | 328 | 0.00634765625 | fail |
| RGBA8 PNG, ACES 2 SDR display output | 21 / 36 | 94 | 0.0039215982 | fail |

All 36 planned render processes had unique observed PIDs. They made exactly 36 render-operator calls and 72 saves, totaling 10.113137 seconds of measured render-and-save time excluding Blender startup. All 21 negative cases reached their frozen reason.

The frozen decision is `PRE_PNG_VARIATION_SUPPORT`: both output domains are non-exact under a valid experiment.

## Strong paired observation

The exact/non-exact Boolean pattern was identical between EXR and PNG for every one of the 36 A-B/A-C/B-C frame pairs. Five frames—5, 38, 47, 110 and 114—were exact in all three pairs in both formats. Frame 103 was non-exact in all three pairs in both formats. The remaining six frames split into two identical replicates and one differing replicate in both formats.

This paired pattern is stronger than merely observing two non-exact totals. It shows the same cross-process render outcomes propagating into both file paths. PNG8 reduces or masks many individual float differences—94 failed pixels versus 328—but does not create the non-exact pair classification.

The EXR maximum is expressed in scene-linear ACEScg numeric units, not display code values, and should not be compared directly with 1/255 as a perceptual magnitude.

## Candidate failures retained

Three implementation candidates were rejected before the accepted run:

1. Candidate 1 required `Render Result.has_data=true` before the first save. Real Blender returned false and the candidate stopped at process one.
2. Candidate 2 prepared the PNG filepath/settings before render but retained the same false pre-save `has_data` requirement. It failed again, disproving the tentative filepath explanation.
3. Candidate 3 successfully produced correct 960×540 RGBA float/uint8 files, but the Node validator compared JSON object serialization and rejected identical fields whose key order differed after Python `sort_keys`. The layout data passed manual inspection; the validator was corrected to compare fields.

Candidate 4 completed the frozen 36-process order and all attacks. The decision gates were never changed.

## Identity and evidence

- B21 spec SHA-256 `3f7aa6b…2cda6`;
- Blender `60ba7a9…129f2`, B02 `.blend` `2a50536…11b0b`, OCIO `24ec818…ad15`;
- accepted renderer `b853d12…fb207`, comparator `bd7c418…ab88e`, runner `71d9704…cb657`;
- process ledger: 36 invocation IDs / 36 PIDs;
- three dual-output manifests, six OIIO comparisons and six comparison bindings;
- machine result: `experiments/dual-output-localization-v0-1/results.json`.

## What was falsified

- PNG8 quantization or the ACES display transform is not the origin of the strict non-exact classification.
- Writing a 32-bit float scene-linear EXR does not make Eevee output bit-exact across new processes.
- High bit depth preserves more of the variation; it is a fidelity property, not automatically a determinism property.

## Next boundary

The next causal candidate should be evaluation/sampling concurrency rather than another file format. The accepted Blender RNA inventory reports fixed render threads = 8, while B17-B21 tie the variation to multi-sample scene-linear output. A pre-registered 1-thread versus 8-thread EXR32 experiment can test whether exposed CPU scheduling is sufficient, while explicitly acknowledging that Eevee GPU work may ignore this control.

## Non-claims

B21 does not directly read internal render-memory pixels, locate a Blender source line, prove a GPU race, define a perceptual tolerance, or generalize to Cycles/multilayer EXR/AOV/cross-device rendering. It localizes the observed variation to at or before the scene-linear EXR save boundary under this exact profile.
