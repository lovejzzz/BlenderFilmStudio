# B48-D2 — independent high-sample reference calibration result

Date: 2026-08-26

Status: `REFERENCE_CALIBRATION_USABLE_FOR_FORMAL_DESIGN`

Protocol commit: `132b6417cde5ad8b95f61e5e77d35a2fa2453ca4`

Tool-freeze commit: `c8e0bb9ac628ef876a90851a33ed3cb8485e5ae1`

Run-receipt SHA-256: `0ba81994fb4d17d1129896a1fb4320ffa11a567a392cb841c004bb9d85992ddf`

Analysis SHA-256: `88563fd043f2be35b216ed46b562c0da4a522ad8c5e47893b553bb95ef9fe213`

## Result

Three fresh Blender 5.2 Linux/amd64 Cycles CPU containers rendered frame 22 at 512 spp raw with the frozen seed offsets. Render times were 27.540, 27.458 and 27.318 seconds. All multipart EXRs contained exactly the seven B47 subimages and finite 72×128×4 Combined arrays.

`R512-A` used the original shot seed and reproduced D1's `S512_REFERENCE` canonical Combined hash exactly: `6cabf4abaedcd39663367242a5fb1bcca32e1f7f99b663a73e80be36ed64164c`. This is a clean-worker same-seed high-sample reproduction result. The B and C seed interventions produced distinct canonical hashes, so all three reference realizations were different as required.

## Measured reference floor

| Pair | Linear NRMSE | Log-luma RMSE | Edge RMSE |
|---|---:|---:|---:|
| A ↔ B | 0.033108 | 0.016657 | 0.073420 |
| A ↔ C | 0.033246 | 0.016995 | 0.072621 |
| B ↔ C | 0.035242 | 0.017365 | 0.078448 |

The three-reference float64 arithmetic mean has SHA-256 `acb9c551c28d2895639805cf256ecd081993b61b98cccb5daa1b58a6ab50a4df`. Individual-reference deviation from the mean was 0.018740–0.019996 linear NRMSE, 0.009618–0.010008 log-luminance RMSE and 0.041061–0.044491 edge RMSE. A single 512-spp image therefore has a material numerical floor on this scene and cannot be treated as noiseless ground truth.

## D1 ranking under the calibrated ensemble

Recomputing the D1 candidates against the three-reference mean preserved the important multi-objective result:

| Cell | Linear NRMSE | Log-luma RMSE | Edge RMSE |
|---|---:|---:|---:|
| 8 raw | 0.268682 | 0.088194 | 0.664001 |
| 8 OIDN | 0.218022 | 0.039744 | 0.586527 |
| 32 raw | 0.113872 | 0.047046 | 0.273626 |
| 32 OIDN | 0.154298 | 0.026494 | 0.415030 |
| 128 raw | 0.054981 | 0.023888 | 0.130464 |
| 128 OIDN | 0.083315 | 0.015219 | 0.222967 |

OIDN remains best on log-luminance at a matched sample count but worse on linear and edge metrics at 32/128 spp. The 128-raw cell remains the only D1 candidate close to three times the largest individual-reference deviation on all three metrics. This observation motivates a holdout rule; it does not pass that future rule retroactively.

## Formal-design consequence

B48 formal will render fresh independent references and candidates on unseen frames. For each frame it will derive a local three-reference mean and local reference floor. A candidate is numerically near-reference only if its linear NRMSE, log-luminance RMSE and edge RMSE are each no more than 3× the largest same-frame individual-reference deviation from the ensemble. The multiplier, candidate roster, holdout frames, seed offsets and selection rule must be frozen before formal tools.

This is a numerical operating-point criterion, not a human cinematic-quality threshold. The eventual website and cost model must keep those claims separate.

## Audit and boundary

The analyzer replay was byte-identical. Exactly three experiment containers ran, and none remained afterward. D2 used no build, pull, download, model call or video-generation API.

D2 does not establish human preference, temporal denoiser behavior, motion blur, 2K/4K scaling, GPU behavior, native x86 throughput, cloud price or complete-shot cost. It only makes the next quality/cost holdout scientifically defensible.

## Artifacts

- `research/2026-08-26-b48-d2-independent-reference-calibration-protocol.md`
- `blender/derive_b48_reference_replica.py`
- `scripts/run-b48-reference-calibration-derivation.mjs`
- `scripts/analyze-b48-reference-calibration.py`
- `experiments/codex-worker-reference-calibration-derivation-v0-1/`
