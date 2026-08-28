# B52-D12.12-D1 Material-owner one-sided curvature derivation result

Date: 2026-08-28

Status: post-hoc candidate derived; fresh holdout required

New Blender renders: 0 (parent evidence: 16 real Blender 5.2 Cycles CPU renders)

## Question

On the immutable D12.11 Material Index arrays, can a one-sided second-difference rule safely recover a preregistered portion of the 146 sweep and 152 parallax pixels whose four bilinear taps belong to one owner but whose symmetric 4×4 curvature stencil crosses an owner/alpha boundary?

## Frozen experiment identity

| Item | Identity |
|---|---|
| Preregistration commit | `9b327eaed462f3872c4fb354a4daeab9342198e4` |
| Specification SHA-256 | `f179b4cea6c8d3bc19b4cf2534055ef98b3fa8dac9954bfeae28bc2a237dd640` |
| Tool-freeze commit | `c91869a371bb78ca9df40ab4eb558531ebc19f06` |
| Formal root commit | `5eb87b6d44de71a1df1f2207664253ec4ac2309d` |
| Formal root Git tree | `608ced9edeab16c55f99ca60063ad49432c6667e` |
| Parent D12.11 formal tree before/after | `d1d50c211d4a94321ef7c051e9b066ff700a36d8` / same |
| Result SHA-256 / self-hash | `4c68f0fad380e0362b3913c0f08f009aa009a620d8e718520a73319edd4e98e2` / `eba522125663564ee3d1cb6cb53fe3d0207fd3b32aa35160dba6fc481da6a841` |
| Audit SHA-256 / self-hash | `5418414190a1f945ecc7a2d6069bbf8139898630eb54b2cb325332cbfb544615` / `a33ddf28b4eed72f37938c0bb334c23a3149f92cbe69d1596b0e673ac454cef1` |
| Receipt SHA-256 / self-hash | `29749a31ad573a0ef8226534da4deb601b772bb0681d4b0068b122613ab129c8` / `87ce924b6d4cc212b9a49e43475bdd4334564e6b1a2e42e67db9f689f33a7bd9` |

## Frozen rule

The candidate keeps the D12.11 Material Index structural domain, radius-2 current interior, Q30/Q24 arithmetic, four-tap bilinear reconstruction, inclusive 131072 risk threshold and exact current-RGBA fallback.

For each of the two bilinear rows, it computes the left and/or right previous-frame second difference when the required outer tap has the same Material Index and valid alpha. When both exist, it retains the D12.11 maximum. When only one exists, it multiplies that difference by the tested inflation factor. The two bilinear columns use the analogous top/bottom rule. A row or column with neither side available is rejected.

The factor family was frozen to `1, 2, 4, 8, 16, 32, 64`; the smallest factor passing every gate had to be selected mechanically.

## Result

Verdict: `MATERIAL_OWNER_ONE_SIDED_CURVATURE_CANDIDATE_DERIVED`

Selected factor: **1**

Analyzer: **13/13**

Independent audit: **21/21 baseline gates; 64/64 concrete attacks**

Factor 1 was the smallest passing factor. Factors 1, 2 and 4 met the frozen derivation gates; factor 8 and above failed the ≥50% opportunity-acceptance gate, first on parallax.

| Primary fixture (each repeat) | Localized opportunity | Eligible | Newly accepted | Opportunity accepted | Accepted / radius-2 before → after |
|---|---:|---:|---:|---:|---:|
| Rotated sweep | 146 | 146 | 136 | 93.15% | 94.558% → 95.875% |
| Camera parallax | 152 | 152 | 144 | 94.74% | 97.735% → 98.672% |

Both clean repeats were byte exact. Across all selected-factor eligible RGB samples, measured risk underbounds were 0. The global accepted RGB maximum was `3.0308961868286133e-05`, below the frozen `3.0517578125e-05` gate; RMSE was `1.0527398680313309e-05`. False invalid-history accepts and registered Material aliases were both 0. Static accepted delta was 0; full symmetric-stencil risk, accepted and reconstruction arrays were byte exact to D12.11 for every factor.

The same-index control moved from 13,003 to 13,165 accepted because 162 Material-valid one-sided samples were recovered. All 13,165 radius-2 pixels were accepted, while the original Object Index alias class remained accepted at 0. Only 162/490 of the older true-owner extra-stencil class was Material-structurally reachable; this difference is expected after D12.11 replaced shared Object Index with distinct Material identity.

## Coverage boundary remains

The sweep foreground-owner retention rose from `0.9415061296` to `0.9502626970`, crossing its frozen 0.95 owner gate. However, sweep cell retention reached only `0.9587489106`, below the frozen 0.97 cell gate. The derivation therefore removes the localized support bottleneck but does not solve the remaining risk-rejection bottleneck.

This is the preregistered counterexample to an overbroad success claim: recovering 136 of 146 support rejects is real, yet the overall cell still fails.

## Audit scope

The two consumers independently recomputed the structural/radius-2/bilinear domains from D12.11 adapter arrays and emitted all seven factor arrays. Python and Node outputs were byte exact across all fixtures, factors and repeats. The independent auditor did not import either consumer or the runner. Its 64 real in-memory attacks changed bound parents, Material adapter bytes, accepted masks, full-stencil risks, support partitions, fallback pixels, self-consistently rehashed result semantics, cross-language payloads and repeat payloads. Every attack triggered at least one named gate.

No Blender process, render, model call or network call occurred in D12.12-D1. Sixteen consumer, one analyzer and one audit child process were unique and exited zero. Available disk after projected write remained above the frozen 100 GiB reserve.

## Claim boundary

Measured fact: on the D12.11 real-render arrays, factor 1 safely recovered most preregistered sweep/parallax one-sided opportunities under the frozen empirical risk and quality gates.

Inference: the symmetric 4×4 requirement was unnecessarily conservative on these two boundary families.

Unknown: a factor of 1 may fail on unseen signals because a single neighboring second difference is not a mathematical upper bound for arbitrary rendered functions. The zero-underbound result is empirical and post-hoc.

Not claimed: production readiness, perceptual importance, arbitrary-scene error bounds, cinematic quality, deforming geometry, transparency, motion blur, depth of field or denoising safety.

## Next falsifiable boundary

Preregister D12.12-H1 before creating any new source/render tool. Use unseen Blender 5.2 fixtures with separately frozen left/right and top/bottom one-sided boundaries plus a neither-side negative control. Freeze factor 1, Material Index identity, Q30/Q24 arithmetic, original coverage denominators and all quality/fallback gates. Require two clean-process render repeats, independent cross-language consumers and semantic attacks. Do not use the current D12.11 arrays as H1 measurements.
