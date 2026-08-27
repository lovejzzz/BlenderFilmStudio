# B52-D12.4 zero-headroom localization protocol

Date frozen: 2026-08-27, before implementing the D12.4 localizer or inspecting per-pixel extrema beyond the already published D12.3 aggregate measurements.

Status: preregistered post-hoc development diagnostic; zero new Blender renders.

## Why this study exists

D12.3 carried the D12.2 static reconstruction tolerance unchanged into three nonplanar and multi-owner scenes. All owner-interior gates passed, but `STATIC_OCCLUDING_PLANES_119X73` produced an interior RGB maximum exactly equal to the frozen inclusive limit `1/524288`. That is a valid formal pass with zero numeric headroom. It is not evidence of robustness.

Changing the threshold after seeing that value would destroy the original holdout logic. D12.4 therefore asks a narrower question: where are all tied maximum-error samples, and how do their owner identity, distance from an owner discontinuity, raw Vector bits, bilinear weights, source-tap contrast and local Depth planarity relate arithmetically to the observed error?

## Frozen evidence boundary

D12.4 may read only the already committed D12.3 spec, results, receipt, execution record, source EXRs, adapter arrays/reports and Python/Node consumer arrays/reports. Their top-level file and internal identities are frozen in `specs/blender-static-zero-headroom-localization.v0.1.json`. Every lower-level payload must be verified through the hashes already bound by the D12.3 reports.

The primary analysis uses repeat 1. Repeat 2 is an identity control and must match every read payload byte-for-byte. No Blender process, render, adapter, consumer or envelope encoder may be rerun. D12.3 files are read-only.

## Frozen measurements

For every owner-interior RGB sample, the localizer ranks absolute reconstruction error. For the top 32 samples per fixture and every sample tied at the global maximum it records:

1. pixel coordinate, RGB channel and owner pass index;
2. Chebyshev distance to the nearest current-frame pixel outside the same opaque owner, treating the image exterior as outside-owner;
3. raw Vector float32 values, uint32 bit patterns and ratio to `2^-17`;
4. projective sample coordinate, four taps and the exact float64 weights used by the frozen consumer;
5. source-tap colors, per-channel local range and signed weighted contributions relative to the current center pixel;
6. a local Depth four-neighbor Laplacian only where all four neighbors belong to the same owner.

The localizer must independently reproduce every formal reconstructed float32 byte before interpreting any error. Arithmetic decomposition is descriptive: it can show that the stored pixels account for the result, but it cannot reveal an undocumented Blender implementation or establish causality.

## Decision rule

Return `ZERO_HEADROOM_PIXEL_LOCALIZED_WITHOUT_FORMAL_REVISION` only if every frozen input identity verifies; repeat payloads match; recomputation reproduces the formal consumer bytes; the global maximum and every tied coordinate are enumerated with all registered fields; and a separately frozen audit independently reproduces the global maximum, ties and byte identity.

Otherwise return `ZERO_HEADROOM_PIXEL_NOT_LOCALIZED` with a stable failure reason. Either result leaves the D12.3 verdict and threshold unchanged.

## Registered failure surfaces

Fifteen negative surfaces are frozen: the seven top-level D12.3 file/internal identities, adapter and consumer report identity, payload identity, repeat payload identity, reconstruction byte identity, global maximum identity, tied-coordinate totality and output self-hash.

## What comes after

If localization succeeds, its measurements may motivate a fresh preregistered resolution/geometry holdout or a mechanistic correction. D12.4 itself cannot promote either. If localization fails, the missing field or identity becomes the next engineering defect; the tolerance still must not be widened.
