# B25 temporal residual envelope derivation

Date: 2026-08-26

Status: **DERIVATION ONLY / NOT VALIDATION**

## Question and metric

For two complete renders A and B, define the signed cross-run residual as `R_t = A_t - B_t`. Define temporal residual delta as:

`T_t = R_t - R_(t-1) = (A_t - A_(t-1)) - (B_t - B_(t-1))`.

The second form makes the purpose explicit: motion shared by both runs cancels, while frame-to-frame change in their disagreement remains. Metrics use decoded RGB from the ACES 2 SDR PNG8 review output. Alpha is excluded.

## Derivation corpus

Four retained, complete 144-frame pairs were selected because all use the candidate profile: 32 render samples, dither intensity 0, Fast GI enabled and temporal reprojection enabled.

- B16 `D0-A` / `D0-B`;
- B17 `S32-D0-A` / `S32-D0-B`;
- B18 `S32-A` / `S32-B`;
- B19 `G1-R1-A` / `G1-R1-B`.

That produces 572 adjacent-frame transitions and binds 1,152 input files by SHA-256 in `experiments/temporal-residual-derivation-v0-1/results.json`.

## Observed maxima and candidate envelope

Observed over all derivation transitions:

- maximum absolute residual delta: `0.003921598196029663` (approximately one PNG8 code value);
- maximum RMS residual delta: `0.000018064404099505213`;
- maximum changed spatial pixels: `26`;
- maximum changed RGB channels: `33`.

Candidate envelope for a future independent holdout:

- maximum absolute residual delta at most `2/255`;
- RMS residual delta at most `1/32768`;
- changed spatial pixels at most `64`.

Every transition must pass every ceiling; aggregate averaging cannot hide a failure.

## Boundary

This metric is a numerical temporal proxy, not proof that flicker is invisible and not a cinematic-quality score. Human viewing must remain a separate protocol with randomized labels and recorded display/player conditions. Thresholds must be committed before any new B25 holdout render and cannot be widened after observing it.
