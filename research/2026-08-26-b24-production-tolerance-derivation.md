# B24 production-repeatability tolerance derivation

Date: 2026-08-26

Status: **DERIVATION ONLY / NOT VALIDATION**

## Why this stage exists

B15-B23 falsified strict 32-sample Eevee pixel determinism under multiple explicit interventions. That does not establish that the variation is visible or production-blocking. B24 therefore separates two contracts:

1. provenance and structure remain exact by hash;
2. pixels are tested against a numeric envelope frozen before independent holdout rendering.

The derivation artifact is `experiments/production-tolerance-derivation-v0-1/results.json`.

## Evidence used

- 288 scene-linear EXR32 pairs: 36 B21 pairs plus all 252 B23 pairs;
- 36 B21 display PNG8 pairs;
- the same 36 PNG pairs under OpenImageIO `compare_Yee` at its explicitly recorded 100 cd/m² and 45° inputs.

No future B24 holdout frame participates in threshold selection. The holdout frame rule is an arithmetic sequence chosen before rendering: frames 4 through 142 where `frame mod 6 = 4`, yielding 24 frames that do not overlap the twelve B20-B23 sentinels.

## Observed derivation maxima

| Domain | Maximum absolute error | Maximum RMS error | Maximum zero-threshold failed pixels |
|---|---:|---:|---:|
| EXR32 scene-linear | 0.00634765625 | 0.000012749754260918356 | 459 |
| PNG8 display | 0.003921598196029663 | 0.0000108932507121085 | 11 |

All 36 PNG derivation pairs returned zero Yee failure pixels under the recorded default-like viewing inputs.

## Candidate envelope frozen for holdout

| Domain | Max error | RMS error | Changed pixels | Auxiliary Yee |
|---|---:|---:|---:|---:|
| EXR32 | ≤ 1/128 = 0.0078125 | ≤ 1/65536 | ≤ 512 | n/a |
| PNG8 | ≤ 0.003922 | ≤ 1/65536 | ≤ 16 | 0 failure pixels |

The ceilings are simple outward grid values, not fitted percentiles. Every derivation pair fits, which is required but is not evidence that holdout will fit.

## Metric semantics and non-claims

OpenImageIO numerical comparison reports mean, RMS, maximum error and failure counts. The zero-threshold failure-pixel ceiling is retained as a spatial-sparsity descriptor even though strict equality already failed. Blender's color-management contract distinguishes scene-linear OpenEXR from display-transformed PNG output, so the two domains must not share an unqualified error interpretation.

The Yee auxiliary metric is not a calibrated cinema study. Its luminance and field-of-view inputs are recorded, but it does not replace a controlled display, audience distance, temporal presentation or human blind review. B24 can validate a numeric repeatability envelope only.

## Holdout rule

B24 must render `[4, 10, 16, 22, 28, 34, 40, 46, 52, 58, 64, 70, 76, 82, 88, 94, 100, 106, 112, 118, 124, 130, 136, 142]` in three fresh-process replicates A/B/C. Each process renders once and saves the same Render Result as EXR32 and PNG8. All three replicate pairs must pass both envelopes for every holdout frame. Thresholds cannot be revised after execution.
