# B52-D12.9-H1 · Fresh motion-aware curvature-risk holdout

Date: 2026-08-28

Runtime: Blender 5.2.0 LTS (`fbe6228777e7`) · Cycles CPU · Blender Python 3.13 · Node 26.5.0

Scientific status: **SAFE BUT COVERAGE NOT SUPPORTED**

## Frozen question

On four unseen opaque, rigid, planar, multi-owner Blender scenes, can the D12.9-D1 previous-frame-only Q30 curvature candidate simultaneously:

1. preserve structural validity under projective motion and same-index disocclusion;
2. bound accepted bilinear RGB error with zero measured underbound;
3. keep accepted RGB maximum and RMSE at or below `2^-15`;
4. retain at least 97% of every cell's radius-2 domain and at least 95% of each sufficiently populated analytic owner;
5. reproduce source, adapter, Python/Node consumer and decision payloads exactly across two clean repeats?

The scene parameters, formula, thresholds, typed depth domains, process matrix and verdict mapping were frozen in spec SHA-256 `c2756a20e314cf470698ef7af6160154b8d7e2d5e8531ce6591b2509a8730dbc` before formal output. Tool-freeze commit was `76ac7a1431d90d0785afcaec8253a3d040bbca9d`.

## Formal result

Verdict: `MOTION_AWARE_CURVATURE_RISK_SAFE_BUT_COVERAGE_NOT_SUPPORTED`.

- Scientific checks: **13 / 14**; only `COVERAGE` failed.
- Mutation attacks: **48 / 48**.
- Independent raw-payload audit: **9 / 9**.
- Processes: **74 / 74 unique**, all exit zero.
- Real Cycles source renders: **16**.
- Python ↔ Node payload identity: **80 / 80 canonical consumer arrays** in the independent audit.
- Model calls: 0; network calls: 0.
- Repeat 1 and repeat 2 source, adapter and consumer identities: exact in every fixture.

| Primary fixture | Radius-2 | Accepted | Retention | Support reject | Risk reject | Accepted RGB max | Frozen state |
|---|---:|---:|---:|---:|---:|---:|---|
| Rotated sweep / high frequency | 10,327 | 9,765 | 94.558% | 146 | 416 | `3.030896e-5` | coverage fail |
| Camera truck / pitch / parallax | 15,366 | 15,018 | 97.735% | 152 | 196 | `3.024936e-5` | pass |
| Same-index depth crossing | 14,159 | 13,717 | 96.878% | 192 | 250 | `2.887845e-5` | coverage fail |
| Static frequency control | 10,065 | 10,065 | 100% | 0 | 0 | `1.490116e-7` | pass |

Every accepted cell had zero measured Q30 risk underbound samples. Every non-accepted pixel copied current float32 RGBA exactly. Vector endpoint maxima were `5.43e-5–1.09e-4 px` for moving fixtures, comfortably inside the frozen maximum. Valid-history depth agreement was non-empty in every cell and remained below `1/1024`. The same-index fixture separately exposed and rejected 4,169 expected depth-invalid pixels; none entered the valid-history depth aggregate.

## Exact coverage failure

The sweep foreground owner retained 8,064 / 8,565 radius-2 pixels, or **94.151%**, below the frozen 95% owner gate. Its 501 losses split into 85 incomplete previous-support pixels and 416 Q30 curvature-risk rejections. The sweep background retained 96.538%.

The same-index foreground retained 11,511 / 11,953, or 96.302%, but the total cell retained 96.878%, just below the frozen 97% per-cell gate. Its 442 losses split into 192 support rejects and 250 risk rejects. The same-index background retained 100%.

The camera owners retained 99.097% and 97.258%; both gates passed. Both static owners retained 100%.

## Why threshold relaxation is not a valid repair

This section is post-hoc interpretation, not part of the frozen verdict.

For the sweep cell, accepting enough risk-rejected pixels to reach 97% total coverage requires a Q30 threshold of at least `140559` (`1.309058e-4`). The resulting accepted RGB maximum becomes `3.260374e-5`, above the frozen `2^-15 = 3.051758e-5` quality ceiling.

For the same-index cell, support loss leaves only 18 additional accepted pixels needed for 97%. Those pixels do not appear until Q30 threshold `31569966` (`2.940182e-2`); the resulting maximum error is `1.230001e-3`, roughly 40× the quality ceiling. This is a true owner-boundary/curvature event, not a harmless threshold margin.

Therefore no scalar relaxation demonstrated here satisfies both frozen coverage and frozen quality. The bounded verdict is not an artifact of empty coverage, bad Vector, cross-language drift, depth-domain pollution or audit failure.

## Interpretation

The Q30 candidate generalizes the central claim from D12.9-D1: previous-frame curvature is materially more useful than static tap-to-current contrast, and its accepted domain remained measurably safe. It does **not** generalize the selected 97% coverage target on unseen high-frequency rotated motion and same-index owner boundaries.

The next design should not merely increase the threshold. It should separate three typed quantities:

1. structural transport validity at the target sample;
2. true-owner support availability around the previous sample;
3. curvature-conditioned reconstruction acceptance inside that support.

Object Index alone cannot distinguish two analytic owners that deliberately share the same pass index. A future compiler-controlled temporal identity channel, or an equivalent exact owner token, is a stronger intervention than retuning Q30 risk. Coverage must then be reported both against registered history and against true-owner support, so excluding boundaries cannot manufacture a production claim.

## Non-claims

- This result does not validate arbitrary rendered signals, curved surfaces, deformation, characters, transparency, hair, volumes, noisy lighting, depth of field or motion blur.
- It does not prove finite second differences are a universal mathematical error bound.
- It does not revise the negative D12/D12.8 results or turn the post-hoc D12.9-D1 derivation into a holdout pass.
- It does not authorize production deployment or a cinematic-quality claim.

## Evidence identities

- Result SHA-256: `23cc449e6d1c83e06c8f5a80335ead42ec37cc433eee70c54cb4d9fef308d8ee`
- Evidence hash: `cb9f68251a0016634a0580decc5f898732172eee9eddd560a42dccb493490f16`
- Audit SHA-256: `160c194ddaaa4bb727328371de8e8f538af3b0935a4f65ec33e3e10821b46bb8`
- Audit hash: `46635a9777885a690961cf070ddbd2a7bb1ab97d996f772a3010e52f61ec0943`
- Receipt SHA-256: `9d774b40fe41b2008d4d103a6f45b7f15afa324d8e2bd024d88cd112c7631d9f`
- Receipt hash: `c794bd2c79a584b6ade138d8b09d4bc516f68778c1bf8f6c6d29926424cf3fe8`

Machine evidence: `experiments/blender-motion-aware-curvature-risk-holdout-v0-1/`.

Post-hoc coverage analysis: `experiments/blender-motion-aware-curvature-risk-holdout-coverage-analysis-v0-1/results.json`; analysis hash `56a04de570ca33dc271bc7d4a62400bb0fa98bcb3760885435c77df3ae79d516`.
