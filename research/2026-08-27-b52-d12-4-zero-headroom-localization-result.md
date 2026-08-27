# B52-D12.4 zero-headroom localization result

Date: 2026-08-27

Verdict: `ZERO_HEADROOM_PIXEL_LOCALIZED_WITHOUT_FORMAL_REVISION`

Audit: `AUDIT_MATCH` — 15/15 base checks and 15/15 registered mutation attacks passed.

Decision role: post-hoc development diagnostic. D12.3 remains `BLENDER_STATIC_NONPLANAR_MULTIOWNER_INTERIOR_WITHIN_REGISTERED_TOLERANCE`; its threshold and zero-headroom interpretation are unchanged.

## Execution

The formal localizer and independent audit each ran once against the committed D12.3 evidence tree. They started zero Blender processes, performed zero renders and made zero model or network calls. The localizer passed 16/16 identity, replay and localization checks. The audit independently reproduced every fixture maximum, the global maximum, the tied coordinate roster and every reconstructed float32 byte, then rejected all fifteen registered in-memory mutations.

## Unique global maximum

Exactly one interior RGB sample equals the frozen inclusive limit `1/524288`:

| Field | Measured value |
| --- | --- |
| Fixture | `STATIC_OCCLUDING_PLANES_119X73` |
| Owner | `FRONT_OCCLUDER`, pass index `10454` |
| Pixel / channel | `(x=56, y=38)`, blue |
| Chebyshev silhouette distance | `3 px` |
| Raw Vector | `(-7.62939453125e-6, 0) px` |
| Vector bits | `b7000000`, `00000000` |
| Ratio to `2^-17` | `(-1, 0)` |
| Previous sample coordinate | `(55.99999237060547, 38)` |
| Horizontal weights | `2^-17`, `1 - 2^-17` |
| Current-center blue | `0.6667997241020203` |
| Left-tap blue | `0.41712620854377747` |
| Local four-tap blue range | `0.2496735155582428` |
| Weighted tap contribution | `-1.9048577541980194e-6` |
| Pre-cast reconstruction | `0.6667978192442661` |
| Final float32 reconstruction | `0.6667978167533875` |
| Signed formal error | `-1.9073486328125e-6` |

The weighted local contrast accounts for nearly all of the error. The final float32 cast contributes the remaining approximately `-2.4908786e-9`, moving the stored difference onto the exact frozen threshold.

This pixel is not an owner mismatch: all radius-2 current neighbors and all four previous bilinear taps have the same owner and opaque alpha. It is exactly three pixels from the nearest owner discontinuity, the closest distance eligible under the frozen radius-2 erosion rule.

## Tail localization

The zero-headroom value is not a broad floor across the occluding-plane image:

- all 32 highest-error samples in that fixture belong to `FRONT_OCCLUDER`;
- 15/32 are at silhouette distance 3;
- the rear tilted grid's maximum is only `2.9802322387695312e-8`;
- at distance 3 the fixture maximum is the full gate, while at distances 4 and greater it falls to `2.9802322387695312e-7` or lower;
- the top 32 local tap ranges span `0.0184203982` to `0.2877697945`, so the tail is associated with nontrivial within-owner color variation rather than a flat field.

The other fixtures show the same directional concentration without reaching the gate. Their maxima occur at distance 3. If the already observed D12.3 arrays are filtered post hoc to distance 4 or greater, the largest remaining error across all three fixtures is `4.76837158203125e-7`, exactly 25% of the frozen gate.

## Interpretation

Measured fact: a unique first-eligible-ring pixel combines a one-quantum horizontal static Vector residue with a large same-owner blue-channel neighbor difference; the frozen bilinear arithmetic and final float32 cast reproduce the formal threshold hit exactly.

Inference: increasing owner erosion from radius 2 to radius 3 is a plausible correction because it would reject the localized tail while retaining a fourfold margin on these reused arrays. This is a post-hoc derivation, not validation. D12.5 must freeze radius 3 before rendering new resolutions and geometry, retain radius 2 as a control, and require explicit retained-pixel coverage so that success cannot be purchased by masking almost everything.

Unknown: the D12.4 Depth Laplacian is a local image-space proxy only. It does not establish that geometry curvature, Blender's Vector implementation or any undocumented internal quantization caused the residual.

## Non-claims

- D12.4 is not a holdout and does not strengthen the D12.3 generalization claim.
- The D12.3 threshold is not widened or revised.
- Radius 3 is not yet a supported production setting.
- Moving, deforming, transparent, volumetric, hair, particle, motion-blurred and disoccluded content remain out of scope.
- No perceptual or cinematic-quality claim is made.

## Evidence identities

- `results.json` SHA-256: `ba251ebe6262b85a9f12fcef1829a2556d9513a8014bf845da24e983c2430a89`
- result internal hash: `9bd402b0417902b628ff74b85ea754d35827c28e4b94ec6bc40e01ee251dff67`
- `audit.json` SHA-256: `26055eb706a76fbf7fda3c326ee70d49c70b9b58d62c4b28a101815fc0b0f8ee`
- audit internal hash: `13fe58b25372b4def27b177e39a72690a1b4ef611d4ae09c60c3a26c6972cc05`
- frozen tool commit: `d72ede30ec88d73c1154be2f723f73eb1ab8f494`

Artifact root: `experiments/blender-static-zero-headroom-localization-v0-1/`.
