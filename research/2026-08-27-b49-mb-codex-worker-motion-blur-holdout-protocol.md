# B49-MB — reference-calibrated motion-blur holdout protocol

Date: 2026-08-27

Status: preregistered before formal renderer, runner, analyzer, attack suite or output

## Question

Does B48's selected 128-spp raw operating point remain numerically adequate when Blender 5.2 Cycles performs a centered half-frame camera exposure, and is the resulting blur-on candidate more faithful to an independent blur-on reference ensemble than an otherwise identical blur-off control?

The TABLETOP holdout is frame 37. It was used previously without blur but has not been rendered by a blur experiment, so the temporal integration result remains unobserved at preregistration. INTERIOR frame 19 is the static pass-domain control.

## Eight frozen workers

TABLETOP receives:

- three independent 512-spp raw references with motion blur on, centered shutter 0.5 and seed offsets 314159, 424243 and 535529;
- one 128-spp raw candidate with the same blur settings and seed offset 647647;
- one same-seed 128-spp blur-off negative control;
- one same-seed 128-spp blur-on/shutter-zero mode control.

INTERIOR receives same-seed 128-spp raw blur-off and centered-shutter-0.5 cells. Every worker uses 128×72, four fixed CPU threads, ACES 2, denoising off, persistent data off and the seven-subimage multipart EXR production pack.

## Reference-floor quality gate

The analyzer forms a float64 mean of the three blur-on references. As in B48, it calculates linear RGB NRMSE, log-luminance RMSE and top-10%-edge linear RMSE. Each metric's local floor is the maximum deviation of one reference from the three-reference mean.

`T_C128_ON` must remain within 3× the local reference floor on all three metrics. To support the stronger motion-blur operating-point verdict, it must also be strictly closer to the blur reference than `T_C128_OFF` on at least two of the three metrics. No metric can compensate for a candidate quality-gate failure.

The outcomes are deliberately plural:

- `B49_MOTION_BLUR_OPERATING_POINT_SUPPORTED` when the candidate passes all three floor gates and beats off on at least two metrics;
- `B49_MOTION_BLUR_POINT_PASSES_BUT_OFF_NOT_DISTINGUISHED` when it passes the floor gate but does not beat off on two metrics;
- `B49_MOTION_BLUR_128_REJECTED` when it fails any floor gate;
- `B49_MOTION_BLUR_INVALID_EVIDENCE` for identity, representation, pass-domain, attack, operation or replay failure.

## Pass-domain gate derived before the holdout

B49-MB-D1 showed that Vector changes merely from enabling blur, including at zero shutter and on a static scene. Cryptomatte IDs cannot be scored as continuous colour error. The formal gate therefore freezes three domains:

- image-continuous: Combined, Depth and Normal;
- identifier/coverage: the three Cryptomatte subimages;
- mode-dependent: Vector.

Moving zero-shutter versus off and static blur-on versus off must keep all image-continuous and identifier passes exact, while Vector must differ. This is a representation binding, not an image-quality preference.

## Promotion and boundary

The result is valid only when all eight fresh workers complete, source/runtime/containment identities match, the pass pack is finite and complete, all three reference hashes are distinct, the metric and verdict replay, all 19 attacks reject for their declared reason, cleanup is zero and an independent audit reproduces the result byte for byte.

Passing does not select a human-preferred shutter, prove complete-shot temporal stability, cover deformation/particle/rolling-shutter blur, establish depth of field, high-resolution cost, GPU/Eevee behavior, native x86/cloud throughput or dollar cost. Human “cinematic” claims remain a blinded-review problem.
