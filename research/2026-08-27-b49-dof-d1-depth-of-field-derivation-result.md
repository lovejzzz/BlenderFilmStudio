# B49-DOF-D1 — depth-of-field derivation result

Date: 2026-08-27

Status: `DEPTH_OF_FIELD_DERIVATION_USABLE`

## Runtime and evidence identity

Seven fresh Blender 5.2.0 LTS Linux/amd64 Cycles CPU workers rendered the preregistered 256×144, 256-spp depth-separated emission fixture. Every worker used the pinned image `sha256:c4b0f6…35b1`, four CPUs, 8 GiB memory, read-only repository input, disabled network, non-root UID/GID, all capabilities dropped and a 180 s hard boundary. No experiment container remained.

The operative C2 preregistration commit is `9eef748598a8ec1dfd320eac846eb03a492d9831`; the tool-freeze commit is `a9431447d992f1638063780857ad7257bc3be156`. The run receipt, results and audit hashes are `b358f7d2…37d3`, `f4c56b7e…8c44` and `a35990a1…a88c`. Evidence-core hash: `f5c945a9…2ddd`.

## Focus selectivity followed all three interventions

At f/1.4, the target with the highest frozen-ROI modulation followed the requested focus distance in all three cells:

| Focus | Near target | Mid target | Far target | Highest |
| --- | ---: | ---: | ---: | --- |
| 3 m | 0.953453 | 0.900735 | 0.758421 | Near |
| 5 m | 0.900735 | 0.953453 | 0.945772 | Mid |
| 8 m | 0.758049 | 0.945772 | 0.953453 | Far |

This supports the narrow statement that Blender 5.2 Cycles' numeric focus distance moves the maximum local stripe contrast to the corresponding 3/5/8 m plane in this controlled fixture. It does not establish artistic focus choice.

## Aperture dose behaved locally, not globally

With focus fixed at 5 m, the mid-plane modulation and horizontal-gradient RMS remained exact across DOF off, f/16, f/4 and f/1.4. The near-plane gradient RMS fell from 0.446355 off to 0.445986 at f/16, 0.437917 at f/4 and 0.384485 at f/1.4. The far-plane value fell from 0.446475 to 0.446380, 0.443654 and 0.424574.

The local, depth-labelled metric is coherent under aperture dose. This is materially stronger than the global edge-energy proxy falsified by B49-MB-D1, but it remains a fixture diagnostic rather than a general aesthetic score.

## Focus object override was exact

The focus-object cell left numeric `focus_distance` deliberately poisoned at 99 m while assigning an on-axis empty exactly 5 m from the camera. All seven decoded passes were float32 exact against the numeric-5 m cell; Combined hash was `8afb98e6…c5e2` on both. The focus object therefore overrode the numeric distance exactly in this bounded representation.

## DOF changes more than Combined

Comparing DOF off to 5 m f/1.4 changed 33,819 Combined float components, 136 Depth components, 1,573 Normal components and 1,892 components in `CryptoObject00`. Vector and the two unused higher Cryptomatte layers remained exact. The large generic RMSE values for Depth background sentinels and Cryptomatte ID bit patterns are not perceptual magnitudes and must not be interpreted as such.

This falsifies a tempting compositor assumption that DOF is only a beauty-pass blur while auxiliary geometry/ID passes remain pinhole-exact. The production manifest must bind pass semantics to DOF mode, and downstream tools must treat identifiers by exact/hash/coverage logic rather than numeric RMSE.

## Cost and integrity

The DOF-off render took 6.126 s. DOF-on cells took 6.781–6.936 s, approximately 1.107–1.132× the off operator time; fresh-container wall moved from 16.250 s to 16.861–17.060 s. Peak self RSS remained 505,956–508,128 KiB.

All 15 frozen attacks were rejected. The independent audit reran the analyzer and reproduced `results.json` byte for byte.

## Claim boundary and next experiment

B49-DOF-D1 does not establish the correct narrative focus, human cinematic preference, focus-pull temporal quality, anamorphic/polygonal bokeh, complex transparency/hair, 2K/4K cost, GPU/Eevee behavior, native x86/cloud throughput or dollar cost.

The next formal holdout should use previously unseen frames from both promoted real scenes. For each scene, three independent 512-spp DOF-on references establish a local numerical floor; same-seed 128-spp DOF-on and DOF-off cells test whether the compiled f/4 focus setting remains within the frozen floor and moves toward its own high-sample reference. That gate can establish bounded numerical adequacy and pass-domain behavior, but artistic focus intent still belongs to blinded human review.
