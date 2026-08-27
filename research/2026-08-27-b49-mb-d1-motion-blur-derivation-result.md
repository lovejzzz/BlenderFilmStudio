# B49-MB-D1 — motion-blur semantics and cost derivation result

Date: 2026-08-27

Status: `MOTION_BLUR_DERIVATION_USABLE`

Preregistration commit: `0281a0e66a1fef12fd60a0e685325032a0865585`

Tool-freeze commit: `ec106a96bded5b7376605d8f10f6bd7543db2f91`

Run-receipt SHA-256: `4ddf5af41e105c8bdd2f2b973dec1fb1975c0712167e14e7ea840ee20b8bbdc7`

Analysis SHA-256: `9edfec279be387b3a51dcc6496303e215fac1f5fb3ebdf4f6484d7edf32a3e81`

Audit SHA-256: `e60c1b3bfd63c604dd1a0ba61c91707adb70a0deb0f76ebb66d54e39c5a6fad5`

Evidence-core hash: `625260982a32fabeebdb2205bbe122877d820b09d538d8e914dc681f39fbd34c`

## Result

Eleven fresh Blender 5.2 Linux/amd64 Cycles CPU workers rendered the frozen 128×72, 128-spp raw cells. Six cells exercised TABLETOP's linear perspective-camera push; five exercised the completely static INTERIOR control. Every worker completed inside the declared boundary, every EXR reopened with finite arrays and the exact seven-subimage production roster, no experiment container remained, and the independent analyzer replay was byte exact.

### Moving camera

| Cell | Blender render | Combined edge RMS | EXR bytes | Peak self RSS |
|---|---:|---:|---:|---:|
| blur off · frame 22 | 9.331 s | 0.386486 | 266,846 | 506,600 KiB |
| blur on · shutter 0 | 9.240 s | 0.386486 | 152,261 | 507,244 KiB |
| center · shutter 0.5 | 9.407 s | 0.387748 | 154,779 | 506,332 KiB |
| center · shutter 1.0 | 9.448 s | 0.387156 | 155,800 | 506,580 KiB |
| start · shutter 1.0 · frame 22 | 9.577 s | 0.387590 | 155,801 | 507,008 KiB |
| end · shutter 1.0 · frame 23 | 9.585 s | 0.387590 | 155,801 | 506,548 KiB |

Relative to blur off, centered 0.5 and 1.0 shutter changed 21,133 and 21,247 Combined float components. Their Combined RMSE values were 0.008706 and 0.013087. Depth and Normal also changed, and the number of changed Normal components increased from 2,893 to 3,818 as shutter widened. Cryptomatte coverage/ID fields changed on moving silhouette boundaries.

The global luminance-edge RMS did not behave like a monotonic blur score: it increased 0.326% at shutter 0.5 and 0.173% at shutter 1.0 relative to off. This falsifies using one global edge-energy reduction as the formal quality gate. Camera integration can move high-contrast boundaries and specular energy while blurring them locally.

Motion blur added little measured render cost on this bounded worker: centered 0.5 and 1.0 were 1.008× and 1.013× the off render time. This is not a general production-cost claim.

### Representation counterexample

Turning motion blur on with a zero-width shutter preserved the decoded Combined, Depth, Normal and all three Cryptomatte subimages exactly, but changed 32,552 Vector float components. On the static scene, every blur-on cell likewise preserved Combined, Depth, Normal and Cryptomatte exactly while changing 36,348 Vector float components by a small amount.

Therefore Vector is not a passive colour-like AOV under the blur switch. It has mode-dependent semantics and must be validated in its own domain. Cryptomatte ID channels are encoded identifiers/coverage values; their raw float magnitudes are not meaningful continuous quantities, so the large numeric RMSE printed by the generic derivation comparator must not be interpreted as image error. Formal tooling must use exact/hash and coverage-aware checks for these passes.

Enabling blur also reduced ZIP-compressed multipart EXR size substantially even when Combined was exact. File size therefore cannot serve as a proxy for visible blur strength.

### Exposure-window oracle

`START 1.0 @ frame 22` and `END 1.0 @ frame 23` nominally cover the same `[22,23]` exposure interval. All seven decoded pass arrays matched exactly, their edge energies and EXR byte counts matched, and their Blender render times differed by only 0.008 seconds. The two EXR container SHA-256 values still differed, preserving the established distinction between decoded semantic identity and container-byte identity.

### Static control

Across blur off, centered 0.5/1.0, start 1.0 and end 1.0 on the static scene, Combined, Depth, Normal and all Cryptomatte subimages were exact. This supports the expected temporal-integration semantics for image passes while simultaneously preserving the Vector counterexample above.

## Supported claim

For the frozen linear camera push, Blender 5.2 Cycles motion blur changes the decoded moving-scene image and geometry-related passes in a shutter-dose-sensitive way, preserves nominally equivalent exposure windows exactly at the decoded-pass level, and leaves static image passes exact. The blur switch changes Vector representation even at zero shutter or with no scene motion. The incremental render-time cost at this small CPU cell is negligible relative to the off baseline.

## Non-claims and next experiment

D1 does not select a physically correct or artistically preferred shutter, prove full-shot temporal stability, validate object deformation/particle/rolling-shutter blur, establish depth of field, high-resolution cost, GPU/Eevee behavior, native x86/cloud throughput or dollar cost.

The formal B49-MB holdout must use a previously untested blur frame, three independent 512-spp blur-on references, a 128-spp blur-on candidate and same-seed blur-off negative control. It must reuse the B48 reference-floor logic for Combined quality, require the blur-on candidate to remain within the frozen local floor multiple, separately report whether the blur-off control is distinguishable, and validate static Combined/Depth/Normal/Cryptomatte invariance while treating Vector as a mode-dependent pass. Human preference between shutter durations remains a later blinded review.

## Artifacts

- `specs/codex-worker-motion-blur-derivation.v0.1.json`
- `research/2026-08-27-b49-mb-d1-motion-blur-derivation-protocol.md`
- `blender/derive_b49_motion_blur.py`
- `scripts/run-b49-motion-blur-derivation.mjs`
- `scripts/analyze-b49-motion-blur-derivation.py`
- `scripts/audit-b49-motion-blur-derivation.py`
- `experiments/codex-worker-motion-blur-derivation-v0-1/`
