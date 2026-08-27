# B52-D12.6-C2 static interior risk localization result

Date: 2026-08-27

Verdict: `STATIC_INTERIOR_EXTREMA_LOCALIZED_AND_LOCAL_RISK_BOUND_CONSERVATIVE`

## What the formal replay established

The corrected frozen localizer reproduced both radius consumers byte-for-byte, verified every bound parent/report/payload identity, enumerated every tied maximum, and evaluated 92,763 radius-interior RGB samples across six fixture/radius cells. The preregistered local contrast plus one-ULP bound underestimated zero samples. The independent process reproduced the records and aggregates and rejected 18/18 mutations.

The extrema are local-gradient arithmetic, not a universal silhouette ring:

- Wedge/panel radius 2 and 3 each have two tied B-channel maxima of 1.2516975402832031e-6 on rear owner 11117, at distances 17 and 11. The distance-17 pixel is dominated by a 2.2888e-5 weight on an x+1 tap whose B value differs from center by about 0.04794, plus a smaller above-row term.
- Nested curves radius 2 has one R maximum of 4.76837158203125e-7 at distance 3. Radius 3 has three tied maxima of 3.5762786865234375e-7 at distances 4, 5 and 6 across both owners.
- Crossing rods radius 2 and 3 retain the same G maximum of 1.1324882507324219e-6 on descending rod owner 11791 at distance 4. Its dominant term is the 3.05175e-5 x weight multiplied by a local G contrast of about -0.03036.

## Is the bound useful, not merely safe?

Yes on this development set, with the required caveat that this is not yet a holdout. Per-cell Spearman association between pixel risk and actual pixel error ranges from 0.8944 to 0.9281. Among nonzero RGB errors, the median bound/actual ratio ranges from 1.60 to 1.69 and p95 from 2.41 to 2.50.

At the unchanged production gate, neither actual error nor the bound selects any pixel. At the stricter half-gate, radius 2 contains 7 actual-positive pixels and the bound selects 12 of 16,428 pixels with 100% recall; radius 3 contains 6 actual-positive pixels and the bound selects 7 of 14,493 pixels with 100% recall. Thus a candidate adaptive rule can reject only a tiny arithmetic-risk tail rather than globally eroding another owner ring.

## Decision

D12.6-C2 supports preregistering a fresh adaptive-risk holdout. It does not validate that production rule: the bound and threshold were derived and inspected on D12.5-C2 evidence. The next experiment must use unseen Blender fixtures and compare radius 2 plus the frozen local-risk rejection against global radius 3, measuring tolerance, half-gate headroom and per-owner coverage without changing the rule after rendering.

Machine-readable evidence: `experiments/blender-static-interior-risk-localization-c2-v0-1/results.json`, `audit.json`, and `receipt.json`.
