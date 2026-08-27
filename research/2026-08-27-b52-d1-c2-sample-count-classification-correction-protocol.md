# B52-D1-C2 · Sample Count classification correction protocol

Status: frozen after the C1 analyzer produced a rejected invalid result and before the C2 result was produced.

## Failure

C1 repaired attack execution and reached a complete result, but classified six finite, in-range adaptive cells as invalid because they sampled every pixel to the 128-sample maximum. Those cells are legitimate observations: they simply fail the preregistered passing-profile requirement to demonstrate early stopping.

The rejected C1 result is retained byte-for-byte as `results.invalid-analysis-c1.json`; its interpretation failure is bound by `analysis.semantic-classification.failure.json`.

## Permitted correction

Split one Boolean into two explicit meanings:

- `valid`: Sample Count is finite and in `[0,1]`; a non-adaptive cell must additionally be exactly 1 everywhere.
- `gatePassed`: the measurement is valid and an adaptive candidate stops at least one pixel before max.

Candidate eligibility uses `gatePassed`. Experiment validity uses `valid`. No measurement, threshold, quality equation, semantic decoder, cost rule, matrix cell, render artifact or timing value may change.

C2 must bind the full failure chain, reuse all 30 renders without rerendering, pass 20/20 attacks, and reproduce byte-for-byte under independent audit. Otherwise the experiment remains invalid.
