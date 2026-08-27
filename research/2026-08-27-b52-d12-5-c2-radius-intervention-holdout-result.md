# B52-D12.5-C2 radius intervention holdout result

Date: 2026-08-27

Verdict: `RADIUS3_WITHIN_PRODUCTION_TOLERANCE_BUT_HEADROOM_OR_COVERAGE_NOT_SUPPORTED`

Process/audit result: 55/55 unique child processes completed; 21/23 registered decision checks and 30/30 mutation attacks passed.

## What is supported

Radius 3 stayed inside every unchanged D12.2 production bound in all six fresh cells:

- Vector component maximum was at most `3.0517578125e-5 px`, eightfold below `1/4096 px`;
- RGB maximum was at most `1.2516975402832031e-6`, below `1/524288`;
- RGB RMSE was at most `9.777643256720761e-8`, below `1/1048576`;
- previous/current source RGB was exact;
- Python/Node payloads, typed envelopes and both repeats were exact;
- radius 3 was a subset of radius 2 in every cell, and every removed pixel was on silhouette-distance ring 3;
- total radius-3 coverage retained `83.324%` to `89.943%` of radius 2 and every cell retained more than 3,100 interior pixels.

This supports radius 3 as a bounded static owner-interior setting under the existing production tolerance. It does not support the stronger confirmatory intervention claim.

## Why the intervention claim failed

Two preregistered checks failed.

### Twofold headroom failed

The required radius-3 RGB maximum was `≤ 1/1048576` (`9.5367431640625e-7`). Two fixtures exceeded it while remaining below the production gate:

| Fixture | Radius 2 max | Radius 3 max | Production-gate fraction | Max location group |
| --- | ---: | ---: | ---: | --- |
| Beveled wedge / panel | `1.2516975403e-6` | `1.2516975403e-6` | `65.625%` | rear panel, distance 17 |
| Nested curved occlusion | `4.7683715820e-7` | `3.5762786865e-7` | `18.750%` | front ring, distance 4 |
| Crossing rods / sphere | `1.1324882507e-6` | `1.1324882507e-6` | `59.375%` | descending rod, distance 4 |

Radius 3 removed the radius-2 maximum only in the nested curved fixture. It did nothing to the other two maxima because those maxima were not on distance ring 3. The wedge maximum was deep inside the rear owner at distance 17; the crossing-rod maximum was already at distance 4.

Measured consequence: D12.4 correctly localized one first-eligible-ring failure mode, but that mode is not the universal cause of the fresh static tail. A global erosion-radius increase cannot guarantee the registered twofold margin.

### Per-owner coverage retention failed

The foreground tilted ring retained `202/402 = 50.249%` of its radius-2 interior pixels, below the frozen 60% per-owner floor. Overall coverage for that fixture still passed at `83.324%`, and the owner retained more than the 64-pixel absolute minimum. The failure therefore exposes a topology-specific cost that an aggregate coverage ratio would have hidden.

## Paired effect

- Wedge/panel: maximum unchanged; total coverage `89.375%`; RMSE increased slightly because removed pixels were not the dominant-error population.
- Nested curves: maximum fell 25%; total coverage `83.324%`; the thin foreground ring lost nearly half its eligible pixels.
- Crossing rods: maximum unchanged; total coverage `89.943%`; RMSE fell about 5.5%.

The intervention is selective rather than uniformly beneficial. It removes exactly ring-3 pixels as designed, but error extrema can live farther inside an owner and thin/annular owners can pay disproportionate coverage cost.

## Interpretation and next boundary

Measured fact: radius 3 is safe under the existing tolerance on these fresh static fixtures, but fails the stronger margin and per-owner retention contract.

Inference: a single global erosion radius is too coarse as the next production abstraction. The evidence now points toward a local risk gate that combines owner topology with Vector magnitude and same-owner color gradient, or toward keeping radius 2/3 as conservative domain masks while separately bounding reconstruction risk.

Next experiment should be diagnostic before confirmatory: localize the wedge distance-17 and rod distance-4 maxima using the D12.4 arithmetic decomposition, compare their Vector quanta and local gradient terms, and derive a risk score without changing D12.5. Only then should a fresh adaptive-gate holdout be preregistered.

## Non-claims

- D12.5-C2 does not support the registered twofold-headroom intervention claim.
- It does not prove radius 3 is universally safe or optimal.
- It does not revise D12.3 or identify Blender's undocumented internal cause.
- Boundary reuse remains rejected.
- Motion, deformation, transparency, hair, particles, volumes, motion blur, disocclusion, perceptual quality and production throughput remain out of scope.

## Evidence identities

- `results.json` SHA-256: `b3f70d11311fef9f3edf53bcfac511e256359e9b67971c94db89e2b0d323cdc7`
- result internal hash: `e2a7ea77e5bde2e4aa5a846feba35edce143a2898ef9e1320ddc1230930635cc`
- `receipt.json` SHA-256: `a77350c5e6a7589b7ace39da56509156b810e19221a8d1e3f0e8a7f750767d40`
- receipt internal hash: `6023b119149ffe3dc4f2c5dc59966f95386272bdd2e23ac9b7f7672b0a9f0111`
- `execution.json` SHA-256: `4d55a48f8baef9adfa5b3601fc5e8108faf53f5f5234c5472f8b5a5086f5ebdb`
- frozen tool commit: `a817ed9f4bc8d1c47def8123447576797d87f92f`

Artifact root: `experiments/blender-static-radius-intervention-holdout-c2-v0-1/`.
