# B19 Fast GI × TAA reprojection factorial result

Executed: 2026-08-26 with real Blender 5.2.0 LTS build `fbe6228777e7` on Apple M4 Max.

Status: **NO_SUFFICIENT_INTERVENTION**

The 2×2 protocol was frozen in commit `7c5894e` before the B19 configurator, runner or frames existed. Tool implementation was frozen in `03300d6`. Eight clean Blender processes rendered 1,152 frames in the pre-registered order.

## Primary result

| Cell | Fast GI | TAA reprojection | Decoded exact | Failed pixels | Maximum error | PNG byte exact |
|---|:---:|:---:|---:|---:|---:|---:|
| G1-R1 | on | on | 131/144 | 97 | 0.003921598196029663 | 0/144 |
| G0-R1 | off | on | 135/144 | 50 | 0.003921568393707275 | 0/144 |
| G1-R0 | on | off | 133/144 | 96 | 0.003921598196029663 | 0/144 |
| G0-R0 | off | off | 131/144 | 73 | 0.003921598196029663 | 0/144 |

All four cells remained non-exact. The frozen decision is `NO_SUFFICIENT_INTERVENTION`.

Disabling Fast GI did not restore strict equality, disabling temporal reprojection did not restore it, and disabling both together did not restore it. The lower failed-pixel count in one GI-off pair is descriptive only; two stochastic pairs do not estimate an improvement effect.

## What was actually controlled

Before every run, the B19 configurator verified source dither 1.0, Fast GI on and TAA reprojection on. It then set dither to 0 and explicitly set both factor values—even for the on/on baseline—without saving the source `.blend`. The frozen renderer observed 32 samples, and each camera/timeline snapshot remained invariant.

The result therefore falsifies these two user-exposed switches as individually or jointly sufficient fixes under this profile. It does not prove that Fast GI or reprojection make no contribution to error frequency, and it does not identify hidden renderer state.

## Integrity

- 14/14 negative cases reached their intended stable reason;
- all eight runs produced exactly 144 frame names and self-hashed manifests;
- all four OIIO reports bind both sequence hashes and every input frame hash;
- source `.blend` SHA remained `2a505360…11b0b`;
- maximum error remained approximately one 8-bit code value in every cell;
- render times stayed roughly 24–27 seconds per sequence, with no pre-registered performance claim.

## Next falsifiable boundary

The next experiment should isolate process history and renderer state. B15–B19 render all 144 frames sequentially inside each Blender process. A pre-registered sentinel-frame design can compare repeated renders within one process against the same frames rendered from fresh Blender processes, using recurrent frames such as 9, 20, 83, 91, 103, 104, 110 and 144. That can distinguish per-process/frame-history state from cross-process GPU evaluation variability without pretending an unexposed seed exists.

Artifacts:

- `experiments/eevee-gi-reprojection-factorial-v0-1/results.json`
- `experiments/eevee-gi-reprojection-factorial-v0-1/evidence/`
- `specs/eevee-gi-reprojection-factorial-spec.v0.1.json`
- `research/2026-08-26-b19-gi-reprojection-factorial-protocol.md`

