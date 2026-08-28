# B52-D12.11-I1-A1 result: semantic adversarial audit accepted

Date: 2026-08-28  
Verdict: **MATERIAL_INDEX_OWNER_INTERVENTION_ADVERSARIAL_AUDIT_ACCEPTED**

## Outcome

The no-render adversarial audit independently accepted all 19 baseline gates and all 56 preregistered concrete attacks. It imported none of the frozen D12.11 analyzer, audit, consumer or Blender modules, made zero Blender/render/model/network calls, and left the committed formal root Git tree unchanged at `d1d50c211d4a94321ef7c051e9b066ff700a36d8`.

The audit replayed the primary endpoint directly from H1 accepted masks, C1 true-owner masks and D12.11 consumer payloads:

| Cell | H1 registered accepted aliases | Material accepted aliases | New accepted vs H1 | H1 accepted | Material accepted |
| --- | ---: | ---: | ---: | ---: | ---: |
| SAME_INDEX_DEPTH_CROSSING / R1 | 15 | 0 | 0 | 13,717 | 13,003 |
| SAME_INDEX_DEPTH_CROSSING / R2 | 15 | 0 | 0 | 13,717 | 13,003 |

## Concrete attack coverage

The 56 attacks were isolated in-memory mutations, not hash nonces:

- 8 parent-byte flips;
- 4 source-report self-hash breaks;
- 8 paired adapter-byte changes;
- 2 self-consistent Object-Index-for-Material-Index substitutions;
- 4 token-contract mutations: zero, reuse, out-of-range and swap;
- 4 self-consistent Object Index negative-control changes;
- 2 registered-alias acceptance flips;
- 8 new accepted-coordinate injections;
- 4 self-consistent fallback payload corruptions;
- 4 self-consistent coverage-result edits;
- one verdict promotion, one result-hash mutation, one repaired audit mutation and one repaired receipt mutation;
- 2 self-consistent Q30 threshold crossings;
- 2 self-consistent Vector-X sign flips.

Every attack failed all of its named expected gates. Attacks that repaired local payload/report self-hashes were still rejected by semantic or paired-identity gates, which closes the promotion gap documented after the formal run.

## Promoted engineering conclusion

Within the exact paired H1 matrix, compiler-assigned Material Index tokens are accepted as the owner-identity input for the frozen temporal candidate:

- the 15 observed Object Index accepted aliases per repeat were eliminated;
- no new accepted coordinate appeared anywhere;
- non-owner render channels stayed byte-identical to H1;
- Python and Node consumers remained byte-identical;
- accepted-quality, Q30 conservatism and exact fallback gates passed.

The promoted conclusion remains **bounded**, not fully supported. `ROTATED_SWEEP_HIGH_FREQUENCY_157X103` still fails the unchanged coverage gate at accepted/radius2 `0.9455795488`, and its foreground-owner retention remains `0.9415061296`. The separate 146/152 one-sided stencil opportunities are still unresolved.

## Evidence identity

- Adversarial result SHA-256: `b38666b6a6ebc234b0f41311d376875f6d980404afcd6e1f4eaf9d710e78e22c`
- Adversarial audit hash: `a75ee65dbd3255c565ca2531a08f0d395248ea369a716f16c6952fcd275345f7`
- Baseline gates: 19/19
- Concrete attacks: 56/56
- New Blender renders: 0
- Formal root Git tree before/after: `d1d50c211d4a94321ef7c051e9b066ff700a36d8`

## Next boundary

The next experiment must not revisit the solved same-index alias. It should target the already localized one-sided extra-stencil coverage loss: 146 pixels in the moving sweep and 152 pixels in camera parallax per repeat. Any intervention must preserve exact owner safety and Q30 quality while recovering coverage without accepting pixels outside true-owner bilinear support.
