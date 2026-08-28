# B52-D12.10-C1 temporal owner-support localization result

Date: 2026-08-28  
Status: corrected post-hoc localization accepted; no candidate promotion  
New Blender renders: 0

## Question

After mechanically correcting the two invalid D12.10-D1 numerators to explicit accepted/domain intersections, where do the immutable H1 support losses and Object Index aliases occur?

## Frozen identities

| Artifact | SHA-256 / self-hash |
|---|---|
| C1 specification | `2ba1edd74fef18eacfa1c170cab4e35f80afc575eaef1ffe3500428553555403` |
| C1 analyzer | `112aaf92866062549e8a8f95528a3374c75d5d8e0ee032afd3d7fce34fcfc4db` |
| C1 result file | `90e8a4d72c0224e4195cd6a52ea193d93211d6dfe368ed7efdd1c3d421d393c8` |
| C1 analysis hash | `e0f9c8417357ef0d08a75c45ce108d650fe8df22b7a6f3140ea4c3e787ddc719` |
| Corrected independent Node auditor | `4c63613707252be78ffe89dd951f51dbe60f58ab7430ec8081496f64218e0615` |
| Corrected audit file | `7bea1f8db8bf15a41384fa3b1e9a8be5bc44b35ce71b34f18ea51e7549f705c2` |
| Corrected audit hash | `88c4f6081b80e2b62b535e7d4bb364a3b52c45d8b23ded48e30b69060e338e57` |

The invalid D1 analyzer, result and payloads remain byte-preserved. Its failed first Node audit is separately retained and explained in `2026-08-28-b52-d12-10-c1-audit-d1-failure.md`.

## Execution and audit

The C1 analyzer ran once under Blender 5.2's bound Python 3.13 / NumPy 2.3.4 runtime. It performed no Blender render, model call or network call. It passed 16/16 frozen checks and 30/30 targeted mutations.

The first independent Node audit failed because its cross-language JSON self-hash assumption and one pseudo-attack were invalid. That failure was committed before correction. The new-path auditor binds the exact result file SHA, independently replays set/ratio equations, compares all payload bytes and D1 classification fields, and uses semantically rehashed mutations. It passed 10/10 gates and 11/11 independent attacks. All 40 generated payload files are byte-identical to D1 and match all 40 declared payload hashes.

## Corrected primary measurements

| Fixture | Radius-2 | Bilinear mismatch | Extra 4×4 mismatch | Full 4×4 | Accepted ∩ bilinear | Accepted ∩ full | Accepted ∩ extra | Accepted outside bilinear |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Rotated sweep | 10,327 | 0 | 146 | 10,181 | 9,765 | 9,765 | 0 | 0 |
| Camera parallax | 15,366 | 0 | 152 | 15,214 | 15,018 | 15,018 | 0 | 0 |
| Same-index crossing | 14,159 | 17 | 490 | 13,652 | 13,702 | 13,652 | 50 | 15 |
| Static control | 10,065 | 0 | 0 | 10,065 | 10,065 | 10,065 | 0 | 0 |

Every cell and analytic owner satisfies both frozen identities:

```text
accepted = acceptedWithinTrueOwnerBilinear + acceptedOutsideTrueOwnerBilinear
acceptedWithinTrueOwnerBilinear = acceptedWithinTrueOwnerFullStencil + acceptedWithinTrueOwnerExtraStencilMismatch
```

Every non-null retention ratio is in `[0,1]`. For same-index primary, the formerly impossible aggregate is corrected to:

```text
13,717 accepted = 13,702 within true-owner bilinear + 15 outside
13,702 within true-owner bilinear = 13,652 within full stencil + 50 within extra-stencil mismatch
accepted / true-owner-bilinear = 0.9688870032527224
accepted-within-full / true-owner-full = 1.0
```

## Interpretation

Measured fact: rotated sweep and camera parallax have zero true-owner bilinear mismatch. Their 146 and 152 owner-support losses occur only in the extra portion of the symmetric 4×4 curvature stencil; all are support-rejected. A future one-sided or owner-clipped curvature estimator therefore has a real recovery opportunity, but its safety is untested.

Measured fact: same-index crossing contains 17 pixels where Object Index says the reprojection owner matches but the analytic owner does not. Fifteen of those pixels are accepted by H1. This proves Object Index is not a sufficient temporal identity token when two analytic owners deliberately share the same pass index.

Measured fact: all 13,652 same-index pixels with a full true-owner 4×4 stencil are accepted; 50 additional accepted pixels lie in the true-owner bilinear domain but not the full symmetric stencil. The other extra-stencil pixels split between 192 support rejections and 248 risk rejections.

Inference: the next intervention should separate two mechanisms instead of hiding both behind a threshold:

1. a compiler-controlled per-owner token emitted by real Blender, tested against same-index aliasing;
2. an owner-aware curvature support rule tested against the moving one-sided opportunities.

Material Index or a discrete custom AOV is the leading Blender-side token mechanism, but its exact pass semantics, anti-aliasing behavior, color-management path and EXR readback identity must be measured before selection.

## Verdict

`TEMPORAL_OWNER_SUPPORT_ALIAS_LOCALIZED_C1`

This is a corrected post-hoc localization result. It does not change the bounded H1 verdict, validate a new reconstruction candidate, establish perceptual impact, or prove that a one-sided stencil is safe.

## Next falsifiable boundary

Run a real Blender 5.2 pass-semantics probe with two visible analytic owners that deliberately share Object Index but have distinct compiler-assigned owner tokens. Compare Object Index, Material Index and custom AOV readback at interiors and subpixel boundaries, repeat from clean processes, and reject any mechanism that is color-managed, non-discrete at stable interiors, nondeterministic, unavailable through multilayer EXR, or unable to distinguish the same-index owners.
