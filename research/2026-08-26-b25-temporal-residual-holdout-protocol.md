# B25 temporal residual holdout protocol

Date frozen: 2026-08-26, after derivation and before implementing the formal B25 comparator/runner or rendering any B25 holdout sequence.

Status: **PRE-REGISTERED / NOT EXECUTED**

## Question

Do three newly rendered, complete 144-frame Blender sequences remain inside both the previously validated B24 static PNG8 envelope and a temporal residual envelope independently derived from B16-B19?

The machine-readable contract is `specs/temporal-residual-holdout-spec.v0.1.json`. The derivation artifact is `experiments/temporal-residual-derivation-v0-1/results.json`, explicitly labeled derivation-only.

## Frozen design

Render A, B and C in that order. Each replicate launches one fresh Blender process and renders frames 1-144 sequentially in the same process. Thus the holdout has:

- 3 unique Blender processes;
- 432 render calls and 432 PNG8 files;
- 3 replicate pairs × 144 frames = 432 static comparisons;
- 3 replicate pairs × 143 transitions = 429 temporal comparisons.

No output file from B16-B19 is reused as holdout data.

## Frozen metrics

Static frame difference reuses the validated B24 PNG8 ceilings:

- maximum absolute error at most `0.003922`;
- RMS error at most `1/65536`;
- zero-threshold failed spatial pixels at most `16`.

For two runs A and B, signed residual is `R_t = A_t - B_t`. Temporal residual delta is `T_t = R_t - R_(t-1)`, over decoded RGB. Each transition must satisfy:

- maximum absolute residual delta at most `2/255`;
- RMS residual delta at most `1/32768`;
- changed spatial pixels at most `64`.

Every individual observation must pass every ceiling. Means and percentiles cannot hide one failing frame or transition.

## Frozen decision

- static 432/432 and temporal 429/429 → `TEMPORAL_RESIDUAL_ENVELOPE_SUPPORT`;
- static passes, temporal fails → `TEMPORAL_ONLY_ENVELOPE_FAIL`;
- both fail → `STATIC_AND_TEMPORAL_ENVELOPE_FAIL`;
- temporal passes, static fails → `STATIC_ONLY_ENVELOPE_FAIL`;
- any contract failure → `INVALID_EXPERIMENT`.

## Subjective-review boundary

Automation cannot promote a numeric pass into “no visible flicker” or “cinematic quality”. ITU-R BT.500-15 is the current in-force reference for controlled subjective television-image assessment and requires the viewing system and conditions to be reported. B25 therefore freezes `humanReview = PENDING`; a later blind-review package must record anonymization, player, display, viewing distance/conditions and reviewer responses.

Reference: <https://www.itu.int/rec/R-REC-BT.500-15-202305-I/en>

## Controls and attacks

Source `.blend`, plan/structure hashes, ReviewRenderSpec, Blender, OCIO, the B24 result, derivation artifact and reused configurator/renderer are frozen. Nineteen negative categories cover identities, controls, process/replicate binding, frame order/count, layout, file mutation, comparison binding, envelope mutation and accidental fabrication of a human-review result.

## Freeze statement

At this commit, `blender/compare_b25_temporal_residual.py` and `scripts/run-b25-temporal-residual-holdout.mjs` do not exist. No B25 holdout frame has been rendered.
