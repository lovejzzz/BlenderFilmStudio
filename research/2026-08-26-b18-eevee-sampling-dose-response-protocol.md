# B18 Eevee sampling dose-response protocol

Date frozen: 2026-08-26, before implementing the B18 runner and before rendering any B18 frame.

Status: **EXECUTED / NON_MONOTONIC_OR_UNSTABLE**

## Evidence-supported question

B17 found that both one-sample cells were 144/144 decoded-pixel exact while both fresh 32-sample cells were non-exact, independently of output dither 0 or 1. The one-sample images were visibly noisy. B17 therefore located a causal control but did not find the useful-quality boundary or a Blender internal mechanism.

B18 asks where exact reproducibility changes over the powers-of-two sample grid 1, 2, 4, 8, 16 and 32 at fixed dither 0.

## Frozen design

The machine-readable contract is `specs/eevee-sampling-dose-response-spec.v0.1.json`.

Each sample level receives two new clean 144-frame runs. Twelve Blender processes render 1,728 frames in the frozen interleaved order. Dither is fixed at 0.0 through the exact B17 configurator, which first verifies that the source scene still opens at 1.0.

The exact B14 renderer and B15 comparator remain unchanged. Per-level ReviewRenderSpecs are derived mechanically from the frozen 32-sample ReviewRenderSpec by replacing only `proxy.renderSamples`, serializing with two-space JSON indentation and one final LF. The expected byte SHA for all six derived specs is frozen in the machine contract before the B18 runner exists.

## Primary response

Within each sample level, A/B is exact only if all three are true:

- 144/144 decoded RGBA frames exact;
- maximum absolute error 0;
- total failed pixels 0.

The six booleans form the exactness vector ordered `[1,2,4,8,16,32]`.

## Frozen decisions

- `ONLY_SINGLE_SAMPLE_EXACT`: vector `[T,F,F,F,F,F]`;
- `MONOTONIC_BOUNDARY_FOUND`: an exact prefix and non-exact suffix, with at least one exact level above 1 and at least one higher non-exact level;
- `ALL_LEVELS_EXACT_BASELINE_UNSTABLE`: every level exact despite B17's fresh 32-sample negative control;
- `NON_MONOTONIC_OR_UNSTABLE`: sample 1 fails to replicate or the vector toggles after becoming non-exact;
- `INVALID_EXPERIMENT`: any identity, materialization, invariant, binding or attack fails.

No alternative tolerance-based verdict may be added after seeing results.

## Controls and attacks

Every run must bind the dose spec, base spec, derived spec, renderer, comparator, configurator, Blender binary, OCIO and source `.blend`; observe dither 1→0 and the requested render sample count; retain camera/timeline identity; produce exactly 144 named and hashed frames; and use distinct A/B directories.

Each comparison must bind both exact sequence hashes and all per-frame A/B hashes. At least 13 negative cases cover dose-spec identity, base/derived spec identity, three tool identities, fixed dither, observed sample count, alias directories, missing/extra/mutated frames and comparison binding.

## Boundary and non-claims

A monotonic boundary narrows the next experiment but does not identify Blender source code or guarantee unsampled integer levels. An `ONLY_SINGLE_SAMPLE_EXACT` result would make exactness unusable as the current production invariant because sample 1 is visibly noisy; the next intervention would target evaluation/scheduling while preserving samples. Two runs per level do not estimate a mismatch probability, and no result extends to Cycles, EXR, another device or another Blender version.

## Execution result

All 12 clean Blender runs completed and 13/13 attacks reached their frozen reasons. The exactness vector was `[false,true,false,false,false,false]`: sample 1 reached 143/144 exact frames, sample 2 reached 144/144, and samples 4/8/16/32 reached 140/137/137/133 respectively. The frozen decision is `NON_MONOTONIC_OR_UNSTABLE`.

The maximum errors at samples 1/4/8/16/32 were approximately 30/7/4/2/1 eight-bit code values. This is compatible with stochastic contributions being averaged, but it is not source-level mechanism proof. B18 does not promote sample 2 as deterministic from one A/B pair.
