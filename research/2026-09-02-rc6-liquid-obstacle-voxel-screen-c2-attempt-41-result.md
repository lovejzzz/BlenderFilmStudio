# RC6 obstacle-voxel screen C2 attempt-41 result

Status: **PASS AUDIT 18/18 / INCONCLUSIVE_LOWER_TIERS_CONTAINED**

The corrected three-cell Data-only screen completed without Mesh bake, scene save, render, network call or engine write. Independent audit passed all 18 checks.

## Measured result

| Cell | Resolution | Cup effector surface distance | Maximum one-cell-envelope outliers | Data wall time |
|---|---:|---:|---:|---:|
| Preview baseline | 96 | 1.5 cells | 0 | 94.439646 s |
| Preview +1-cell effector | 96 | 2.5 cells | 0 | 91.802223 s |
| Review baseline | 128 | 1.5 cells | 0 | 271.792086 s |

All seven frames in all three cells contained every exposed FLIP particle inside the raw cup interior as well as the one-current-cell envelope. No outlier physical region or floor penetration existed at either lower tier.

This does **not** prove the Final-resolution defect fixed itself. The accepted resolution-192 evidence contains nine active particles embedded 13.96487–20.23688 mm into the modeled solid floor. The lower tiers therefore lack observability for this failure. The next experiment must bind that immutable Final baseline and bake only one fresh resolution-192 `surface_distance=2.5` Data cell. Repeating the existing 192 baseline is unnecessary.

## Product lesson

A cheaper tier may correctly validate broad motion while failing to expose a resolution-specific collision classification defect. The pipeline needs an observability escalation rule: when an accepted higher-tier receipt contains a failure absent from Preview/Review, a lower-tier zero is `INCONCLUSIVE`, not `PASS`; run the smallest paired higher-tier diagnostic that changes one physical variable.

## Binding

- Execution receipt hash: `1ea60739c3684cebbc6de68c9ac4e9d98119a37116df5d106657869b9ad64eac`
- Receipt file SHA-256: `12397d6da4879073614ea9f3d680166ec046ddc1025ccf183ebac9644b412331`
- Independent audit hash: `12b147b5466d92755eb2f609a361ed4ab2b3684c3d9a31c5758b492d96266e8d`
- Independent audit file SHA-256: `142fedc2b53237a9f92a610f126b383ab66ebaab5ad384cbb38427601ffbd002`

Claim ceiling: this is a lower-tier obstacle/resolution screen only. It does not establish a Final-resolution correction, reconstructed-surface quality, slow tip, impact, render or finished-film quality.
