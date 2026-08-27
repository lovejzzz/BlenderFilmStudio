# B48-D2 — independent high-sample reference calibration protocol

Date: 2026-08-26

Status: exploratory protocol frozen before renderer, runner or analyzer implementation

## Why D2 is required

B48-D1 measured six candidate cells against one 512-spp raw image using the same Cycles seed. That reference is one finite Monte Carlo realization, not ground truth. A shared seed may also make same-seed raw candidates look artificially close if their samples are nested prefixes. No formal B48 quality threshold can be frozen until the reference-to-reference disagreement is measured.

## Frozen source and runtime

D2 uses the same B44 TABLETOP-A1 `.blend`, source SHA, frame 22, pinned Blender 5.2 Linux/amd64 image, Cycles CPU backend, 128×72 resolution, fixed four threads, ACES 2 OCIO configuration, B47 production-pass roster, motion-blur-off state and worker containment contract as D1. Denoising is disabled. Each reference runs in a fresh container and empty output directory.

## Frozen reference replicas

The source scene seed is `24082643`. Three 512-spp raw cells are rendered:

1. `R512-A`: offset 0, seed `24082643`.
2. `R512-B`: offset 104729, seed `24187372`.
3. `R512-C`: offset 209759, seed `24292402`.

The offsets are fixed before tool implementation. The runner may execute only these three Docker containers. It may not build, pull, download, call a model or use a video-generation API.

## Frozen checks and measurements

- Reopen all three multipart EXRs with Blender-bundled OpenImageIO and require finite RGBA Combined arrays with the B47 seven-subimage roster.
- Canonicalize Combined as little-endian float32 using the same metadata-bound method as D1.
- Require `R512-A` to match D1's `S512_REFERENCE` canonical Combined hash exactly. A mismatch is retained and stops reference promotion.
- Require B and C canonical hashes to differ from A and from each other; equal hashes would mean the seed intervention did not create independent realizations.
- Measure all three unordered pairwise disagreements using linear RMSE/NRMSE, log-luminance RMSE and exact-top-10%-edge RMSE.
- Form a float64 arithmetic mean of A/B/C. Measure each replica's deviation from that mean and recompute every D1 candidate's metrics against the mean.
- Record render time, EXR size, file hash, canonical hash, source/runtime identity and exact Docker argv for every replica.
- Replay the analyzer and require a byte-identical analysis result.

## Decision rule

D2 is calibration, not a production gate. It is usable for formal B48 design only if all three workers complete, A exactly reproduces D1's same-seed high-sample array, the two seed interventions produce distinct finite arrays, all pairwise and ensemble metrics are finite, and analysis replay is byte-identical.

Formal B48 must use candidate seeds not present in A/B/C and compare against the frozen three-reference mean or a stronger reference justified by D2. Thresholds must account for the observed reference floor and must remain multi-objective; D2 cannot collapse linear, log-luminance and edge behavior into an unvalidated scalar.

## Non-claims

Three 512-spp images do not become physical ground truth. D2 does not establish human preference, cinematic quality, temporal stability, 2K/4K behavior, motion blur, depth of field, characters, GPU behavior, native x86 throughput or cloud cost. The arithmetic mean is a lower-variance numerical target for this bounded frame only.
