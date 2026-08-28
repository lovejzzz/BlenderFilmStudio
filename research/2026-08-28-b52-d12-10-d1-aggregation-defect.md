# B52-D12.10-D1 · Aggregation defect retained

Date: 2026-08-28

Status: **INVALID LOCALIZATION RESULT — TOOL AGGREGATION DEFECT**

The preregistered D12.10-D1 scalar owner oracle and three-way classification executed once and emitted `TEMPORAL_OWNER_SUPPORT_ALIAS_LOCALIZED`, 9/9 checks and 24/24 mutation records. Parent identities, current-owner oracle identity, classification partition and repeat payload identities were valid.

Review of the emitted measurements found an invalid ratio definition in the implementation. For `acceptedToTrueOwnerBilinear` and `acceptedToTrueOwnerFullStencil`, the script divided the total accepted count by each true-owner denominator instead of intersecting accepted with that denominator first. The same-index primary cell contains 15 accepted pixels outside true-owner bilinear compatibility; consequently the background owner reported `acceptedToTrueOwnerBilinear = 1.006846...`, and the cell reported `acceptedToTrueOwnerFullStencil = 1.004761...`. A set-retention fraction above one is proof that the aggregation is wrong.

The underlying observation is important but cannot rescue the report: 17 same-index radius-2 pixels have four previous taps from a different analytic owner token, and 15 of those were accepted by the Object Index/Q30 candidate. D12.10-D1 therefore exposed both the intended Object Index alias and an analyzer measurement defect. Its verdict and aggregate fractions are invalid and must not be cited as accepted localization evidence.

The original tool and output are preserved without overwrite:

- Tool SHA-256: `90d7a0bc639999d5c5c1bcfda65d7edaaefabbc1fa37f8592206eb8460662be2`
- Result SHA-256: `9cb5a01d7dbeba357e8a371be0f5b75e5837291ef6d6cc829b74eb425a7e08d4`
- Emitted analysis hash: `9868072e5bb214241e75957332bc78e4eed1b5c9ccfdb4db3dc1f78b61b5960e`

C1 may change only the two accepted-domain numerators to explicit set intersections, add ratio-bound/decomposition checks, use a fresh tool path and output root, and retain all original oracle, classification, parent, operation and verdict semantics.
