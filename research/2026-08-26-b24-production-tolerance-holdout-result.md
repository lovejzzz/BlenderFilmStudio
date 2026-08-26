# B24 production-repeatability envelope holdout result

Date executed: 2026-08-26

Pre-registration commit: `4f4ec04`

First tool candidate: `0a69c1c` — rejected by attack-count gate

Accepted tool commit: `d60c749`

Decision: **`PRODUCTION_REPEATABILITY_ENVELOPE_SUPPORT`**

## Result

| Domain | Holdout envelope pass | Strict decoded exact | Maximum error | Maximum RMS | Maximum changed pixels | Maximum Yee failures |
|---|---:|---:|---:|---:|---:|---:|
| EXR32 scene-linear | 72 / 72 | 70 / 72 | 0.0068359375 | 0.000012102088061225292 | 17 | n/a |
| PNG8 display | 72 / 72 | 70 / 72 | 0.003921568393707275 | 0.0000072052046660281146 | 5 | 0 |

All 72 holdout render processes had unique observed PIDs. Every process rendered once and saved the same Render Result twice, producing 72 float EXRs and 72 display PNGs. All 22 frozen negative categories reached their intended reason.

Only frame 10 was non-exact: A differed from both B and C, while B-C was exact, in both output domains. Both non-exact pairs remained inside every frozen envelope ceiling. No threshold was revised.

## Rejected candidate

The first formal execution produced the same high-level 72/72 envelope result but was classified `INVALID_EXPERIMENT`. The runner implemented 23 attacks while the pre-registration required exactly 22, so the count gate rejected it. The extra synthetic PID attack was removed, the tool identity changed, and all 72 render processes were rerun. The failed candidate remains identifiable by commit.

## Interpretation

Supported: the numeric repeatability envelope derived from B21/B23 generalized to all 72 pairwise comparisons on 24 algorithmically selected frames from the same frozen scene and machine profile. Exact provenance, structure, runtime and control identities also held.

Not supported: universal Blender tolerance, bitwise determinism, calibrated cinema invisibility, temporal video stability or human-quality acceptance. OIIO Yee at 100 cd/m² and 45° returned zero failures, but those nominal inputs do not constitute a cinema viewing study.

## Evidence

- `experiments/production-tolerance-holdout-v0-1/results.json`
- `experiments/production-tolerance-holdout-v0-1/evidence/process-ledger.json`
- `experiments/production-tolerance-holdout-v0-1/evidence/A.manifest.json`
- `experiments/production-tolerance-holdout-v0-1/evidence/B.manifest.json`
- `experiments/production-tolerance-holdout-v0-1/evidence/C.manifest.json`
- `experiments/production-tolerance-holdout-v0-1/evidence/comparisons/`

## Next boundary

B24 establishes a static-frame numeric envelope for one scene/profile. The next filmmaking-relevant boundary is temporal presentation: whether the sparse per-frame differences create any detectable cross-run flicker or motion inconsistency during continuous playback, and whether calibrated human reviewers agree. That requires a separately frozen temporal metric/review protocol rather than relabeling the static Yee result as “invisible.”
