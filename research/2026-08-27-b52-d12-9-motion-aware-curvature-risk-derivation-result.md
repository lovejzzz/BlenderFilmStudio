# B52-D12.9-D1 · Motion-aware curvature risk derivation

Date: 2026-08-27

Derivation verdict: `MOTION_AWARE_CURVATURE_RISK_CANDIDATE_DERIVED`

Status: exploratory, post-hoc on D12.8. This is not a fresh holdout and does not authorize production.

## Why the previous rule failed

D12.8 showed that the frozen D12.7 risk treated first-order transported color change as interpolation uncertainty. Correct projective motion therefore caused the rule to reject 83–100% of otherwise valid radius-2 history. The failure suggested a different measurable quantity: bilinear interpolation error is driven by local curvature, not by the magnitude of the local gradient itself.

## Candidate

For every D12.8 radius-2 pixel, the candidate inspects a 4×4 previous-frame support around the bilinear cell. It rejects support that crosses Object Index, alpha or raster bounds. RGB is converted exactly to signed Q30 integers and the fractional sample coordinate to Q24 integers.

For each color channel, `Mx` and `My` are the maximum absolute horizontal and vertical second differences around the four bilinear taps. The canonical risk is:

```text
riskNumerator = 2 × (Fx × (2²⁴ − Fx) × Mx + Fy × (2²⁴ − Fy) × My)
riskQ30       = ceil(riskNumerator / 2⁴⁸) + 512
accept        = riskQ30 ≤ 131072
```

The factor represented by the leading `2` is a four-times calibration of the standard half-curvature interpolation remainder. The 512 Q30-unit allowance covers four full float32 ULPs over the declared `[0,1]` domain. The candidate decision reads previous RGB, previous owner/alpha and current Vector, but not current RGB. Current RGB is used only by the independent analyzer to measure error.

## Measured derivation result

| D12.8 fixture | Old accepted | Q30 accepted | Q30 / radius 2 | Accepted RGB max |
|---|---:|---:|---:|---:|
| Rigid sweep / disocclusion | 1,498 | 8,646 | 97.994% | `1.866657e-5` |
| Camera dolly / parallax | 0 | 13,853 | 98.374% | `1.793410e-5` |
| Same-index depth reveal | 1,560 | 11,544 | 97.475% | `1.465026e-5` |
| Static multi-owner control | 9,045 | 9,045 | 100% | `6.610617e-8` |

Every analytic owner with at least 100 radius-2 pixels retained at least 97.092%. The same-index fixture rejected 97 eligible pixels on curvature risk and another 202 on support. Across all eligible RGB samples, measured reconstruction error never exceeded the Q30 risk. Accepted reconstruction maximum and RMSE stayed below the separate `2^-15` quality ceiling.

Python and Node produced byte-identical `eligible.u8`, `accepted.u8` and `risk.q30.u32` payloads for all four fixtures. An independent Python analyzer replayed every integer decision. The derivation passed 10/10 checks with three unique processes and zero model or network calls.

## Interpretation

Measured fact: on the already observed D12.8 evidence, the Q30 curvature candidate recovers most useful motion history without exceeding the chosen scene-linear quality ceiling.

Inference: second differences are a more appropriate proxy for bilinear interpolation uncertainty than tap-to-current absolute contrast in this analytic rigid-motion domain.

Unknown: whether the calibration factor and thresholds generalize to unseen resolutions, material frequencies, transforms and disocclusion geometry. Finite differences are not proved to upper-bound arbitrary rendered signals.

## Required next test

`B52-D12.9-H1` must be preregistered before any new formal render. It must use unseen Blender 5.2 fixtures and recompute structural validity. The Q30 formula, factor, risk threshold and quality threshold are now frozen. Valid-history depth accuracy and expected depth rejection must be measured in separate typed domains. Every moving owner needs non-empty useful coverage; false invalid-history acceptance and inexact fallback remain hard failures.

## Immutable identities

- Spec SHA-256: `1d6ee83130a6df4c6273e865f0889cbeb32a6931b8645edb42c6841499b1e5f9`
- Result SHA-256: `e78ddf4d447b46398dc0ad314ee81e55c7bf2e22744ab57a2a2c7cbb8833438c`
- Result hash: `33ce6da55b8f602e3a4819b903d81586e67a49f90796239828ca4649d943596b`
- Evidence hash: `ea7ad8f269016ee01a42a9e42558f727f73cb979f50fbd6ccc92301de1fa3ac1`
- Receipt hash: `78188333858c398804105891afb200762185655e6e28bf69ceb3f224c8253566`

## Non-claims

This derivation does not revise D12 or D12.8, validate a fresh holdout, prove a universal interpolation bound, or cover curved/deforming geometry, skinning, transparency, hair, particles, volumes, motion blur, depth of field, noisy path tracing, denoising, cinematic quality, character consistency or production use.
