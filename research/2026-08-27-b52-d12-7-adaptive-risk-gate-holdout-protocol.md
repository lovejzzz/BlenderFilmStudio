# B52-D12.7 adaptive local-risk gate holdout protocol

Date: 2026-08-27

Status: preregistered before D12.7 tools, probes, renders or output

Spec SHA-256: `c51d0d83afd30b479bf3e7109c31110133649ee3d65a04d677dbe236b8075ed0`.

## Confirmatory question

D12.5 falsified global radius 3 as a general route to twofold headroom and fair owner coverage. D12.6 then derived a conservative local arithmetic bound on the same development arrays. D12.7 is the first independent test: can radius 2 plus that frozen risk rule remain below the half-gate while retaining more total and per-owner coverage than radius 3 on unseen Blender geometry?

The candidate is fixed as `radius2Interior && max(rgbRisk) <= 1/1048576`. Each channel risk is the four bilinear weights times absolute previous-tap-to-current-center contrast, plus one complete float32 ULP at the final reconstruction magnitude. Equality is retained. No coefficient, learned parameter, silhouette-distance feature or post-render threshold search exists.

## Fresh evidence

Three new fixtures introduce a dual-ripple backdrop with rounded box, a superellipse prism occluded by an offset torus, and a squashed sphere crossed by a frustum and cylinder. All IDs, pass indices, rasters, optics, transforms, geometry parameters, material parameters and output paths are new. Two independent static repeats render previous/current frames through Blender 5.2 Cycles CPU.

D12.5 and D12.6 artifacts are parents only. Their EXRs, arrays, masks and per-pixel records are forbidden as measurements. Repeat 1 is primary; repeat 2 proves byte identity.

## Gates

The adaptive domain must have zero risk underbounds and maximum RGB error at or below 1/1048576. It must retain at least 98% of radius-2 pixels overall and 95% per sufficiently large owner, keep at least 800 pixels per cell and 64 per owner, contain at least 3% more pixels than radius 3 in every cell, and meet or exceed radius-3 coverage for every owner. Each fixture must expose at least one risk-rejected primary pixel so a no-op cannot pass.

Production Vector, RGB maximum and RMSE gates remain unchanged. Radius 3 is a paired comparator, not a strawman required to fail.

## Evidence boundary

The formal matrix contains 12 fresh Blender renders and 56 unique child processes, dual Python/Node consumers and typed envelopes, one independent analyzer, one independent audit and at least 30 registered mutation attacks. Model and network calls remain zero. A 24 MiB projection must leave the 100 GiB disk reserve intact.

Passing validates only opaque static owner interiors. Motion, transparency, hair, particles, volumes, deformation, disocclusion and perceptual quality remain open.

Machine-readable contract: `specs/blender-static-adaptive-risk-gate-holdout.v0.1.json`.
