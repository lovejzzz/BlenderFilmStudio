# B04 contact benchmark — executed result

Date: 2026-08-26  
Environment: Blender 5.2.0 LTS (`fbe6228777e7`), macOS arm64  
Status: automated evidence passed; human review pending; experiment incomplete

## Question

Can a deterministic Blender compiler make a visible actor proxy approach, acquire, transport, and release a real prop while preserving an editable constraint chain and measurable contact state?

## Implemented contract

SceneSpec v0.3 adds only the capabilities required by B04:

1. asset-bound sockets (`assetRef`, `objectRef`, local transform);
2. restricted `CHILD_OF` attachment instructions;
3. deterministic `MATCH_AT_ACQUIRE` inverse handling;
4. constant influence keys for parent switching;
5. declared evaluated-geometry pairs and five contiguous phases;
6. `CREATE_CONSTRAINT` and `EVALUATE_GEOMETRY` permissions.

ActorSpec remained v0.1. Its existing `PALM_R` socket and `GRASP` window were sufficient, so no ActorSpec v0.2 was invented merely to match the preregistration's candidate label.

## Locked inputs

- SceneSpec: `specs/benchmarks/B04.scene.json`
- ActorSpec SHA-256: `bd50540949f6a7b1bdcbeb0ad92908c364df939f18d55c66789b0674e15c702e`
- actor asset SHA-256: `b8684d757db22287aa2bbc0d2d6a919a4cfd1a72ebc4d5d6df782712b797eb6c`
- prop asset SHA-256: `786f01eccb3ccf6f0e322d5655efa42b3a62108fb1eb4b3f3b38182f064215c6`
- action SHA-256: `0eebd23d58ac3668bc27d60b4f361ee8275ead6d6ee80c90508e52caaf471411`
- BuildPlan SHA-256: `bb9e4ff1484d448868ec5a55a6830e353a17d3eb787cbda6d247a96abf545b08`

## First run: falsified

The first end-to-end run passed 7/10 checks. It proved that a numerically stable parent switch was insufficient:

- acquire discontinuity: approximately `8.9e-8 m`;
- release discontinuity: approximately `1.2e-7 m`;
- grip rotation error: `90°` — failed;
- frame-1 proximity sample: `0.004439652 m` — failed;
- APPROACH and RETREAT BVH overlap pairs: nonzero — failed.

The failure was corrected by moving the acquire pose farther from the initial hand, retreating during the RELEASE window, and aligning the prop's authored rotation with the palm socket. The Action and dependent ActorSpec/SceneSpec hashes were regenerated.

## Corrected automated result

Two factory-started builds produced the same normalized structure hash:

`7fd1a426dacbdf1e7bba8a1f94fc327677c9036d7e3576eace707c5a56e63757`

The two `.blend` files were not byte-identical. Binary identity remains a recorded observation, not the structural acceptance criterion.

All 10 evaluated checks passed:

| Check | Result | Threshold |
| --- | ---: | ---: |
| constraint binding | `CHILD_OF → RIG_LEAD.hand.R` | exact |
| influence states | `0 / 0 / 1 / 1 / 1 / 0 / 0` | exact |
| final 12 approach distances | monotonic net decrease | required |
| HOLD maximum position error | `1.6e-7 m` | `≤ 0.005 m` |
| HOLD maximum rotation error | `0°` | `≤ 3°` |
| relative position drift | `3.18e-7 m` | `≤ 0.005 m` |
| relative rotation drift | `0°` | `≤ 3°` |
| HOLD transport | `0.480552181 m` | `≥ 0.30 m` |
| acquire/release step | `1.33e-7 / 1.30e-7 m` | `≤ 0.01 m` |
| clear-phase BVH overlap | `0 / 0` max pairs | exact zero |
| endpoint proximity samples | `0.144780189 / 0.605083704 m` | `≥ 0.05 m` |

HOLD overlap peaked at 11 triangle pairs and is recorded only as a count. It is not penetration depth, pressure, contact area, or evidence of an anatomically plausible grasp.

## Negative fixtures

All eight preregistered categories failed for the intended reason:

1. missing prop object — Blender compile rejection;
2. missing actor socket — Blender compile rejection;
3. missing `CREATE_CONSTRAINT` — BuildPlan rejection;
4. influence stuck at zero — semantic rejection;
5. one-metre release pop — evaluator failure;
6. approach overlap — evaluator failure;
7. static fake target marker — HOLD position evaluator failure (`1.646958987 m`);
8. original rather than evaluated geometry — schema rejection.

## Regression

- B01 structure hash remains `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`.
- B02 structure hash remains `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`.
- B03 evaluation remains 5/5; its corrected manifest now includes actor and target reports and therefore has a new structure hash `96041c22a6626b4c5aceff3cc74155d5be411cfe0142f3025ecdf2d86d84d5ff`.

## Human gate and explicit nonclaims

The rendered proxy is intentionally crude. Automatic checks cannot establish:

- finger closure or grasp region;
- pressure, force, mass, momentum, or believable weight;
- soft-tissue or cloth response;
- absence of visually distracting intersection;
- performance quality.

Human review is still `PENDING`; therefore `experimentComplete` is `false`. The next step is a blinded review package with fixed questions and failure labels, followed by a comparison of BVH pairs against a stronger signed-distance or contact representation if reviewers identify errors the current metrics miss.
