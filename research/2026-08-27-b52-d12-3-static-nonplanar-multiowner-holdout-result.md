# B52-D12.3 static nonplanar and multi-owner holdout result

Date: 2026-08-27

Verdict: `BLENDER_STATIC_NONPLANAR_MULTIOWNER_INTERIOR_WITHIN_REGISTERED_TOLERANCE`

Exactness observation: `INTERIOR_EXACT_ZERO_FALSIFIED`

## Execution

The single-use matrix completed 55/55 unique child processes: twelve real Blender 5.2 Cycles sources, six adapters, twelve Python/Node owner-aware consumers, twenty-four typed-envelope encoders and one independent analyzer. All 27 registered attacks passed. Model and network calls were zero.

Python and Node reconstructed RGBA, owner-interior mask and boundary mask payloads matched byte-for-byte in all six cells. Both typed-envelope implementations matched for all twelve producer reports. Within-fixture source and consumer repeats were exact.

## Interior measurements

| Fixture | Owners | Registered px | Interior px | Boundary px | Vector max | Interior RGB max | Interior RMSE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| curved sphere + torus | 2 | 3,566 | 2,598 | 968 | `1.52587890625e-5 px` | `7.74860382080e-7` | `4.06746012168e-8` |
| occluding grid + cube | 2 | 8,676 | 7,265 | 1,411 | `2.288818359375e-5 px` | `1.9073486328125e-6` | `2.47008319468e-8` |
| depth stack + thin rod | 3 | 3,266 | 2,437 | 829 | `2.288818359375e-5 px` | `5.96046447754e-7` | `4.99128975317e-8` |

All counts and values reproduced exactly in repeat 2. Every registered owner pixel was classified into exactly one of interior or boundary; mask overlap was zero.

The registered interior gates passed, but one result is critical: the occluding-plane fixture's maximum RGB error is exactly the frozen upper limit `1/524288`. The formal `≤` condition is satisfied with zero numeric headroom. Therefore the result supports the frozen boundary but does not support calling it robust across further unseen geometry.

## Boundary diagnostics

Boundary magnitude did not decide the formal verdict, as preregistered. It was nevertheless measured in full:

| Fixture | Boundary RGB max | Boundary RMSE |
| --- | ---: | ---: |
| curved sphere + torus | `7.33137130737e-6` | `4.84007728217e-7` |
| occluding grid + cube | `5.24520874023e-6` | `3.18002781380e-7` |
| depth stack + thin rod | `9.89437103271e-6` | `1.07493909300e-6` |

The largest boundary error is approximately 5.19 times the interior maximum gate. This is direct evidence for fail-closed history rejection at owner discontinuities. It is not evidence that boundary reuse is safe.

## Interpretation

The D12.2 static tolerance generalizes narrowly from single planes to owner-interior pixels on the three tested nonplanar/multi-owner scenes. The owner-aware erosion/tap rule prevents cross-owner blending and gives deterministic Python/Node payloads.

The exact threshold hit changes the next research question. It would be scientifically weak to increase the threshold after observing this fixture. The next step should instead localize the maximum-error pixels by owner, curvature, silhouette distance, Vector quantum and bilinear weight, then preregister a fresh resolution/geometry holdout or a mechanistic correction. Boundary pixels remain rejected.

## Non-claims

- No robustness margin beyond the exact registered threshold has been established.
- No moving, deforming, transparent, volumetric, hair, particle, motion-blurred or disoccluded content is covered.
- No temporal reuse across owner boundaries is authorized.
- The result is not a perceptual or cinematic-quality claim.
- The observed Vector quanta are not asserted to reveal Blender's internal implementation.

## Evidence identities

- `results.json` SHA-256: `1f41d437539e28e62446215a7b1ad16e5ffa56ea9e9eaaaecf07d64999f2988d`
- result internal hash: `0422bd06fbbd327fc4a98231c3815fe6b13de1ab1611e725064baca2ae3eeebe`
- `receipt.json` SHA-256: `080669fb36c286186ead1ad28e23f351d05d2f17167901bfc72339f937af84d3`
- receipt internal hash: `fe2f4ab08547166e815f87c828060ddf890440d7a076494abd84c2c0d91196fc`
- `execution.json` SHA-256: `05c897ff5466bdbf0663339652570d2999d7a8de56f764d1f731169a6c5b585b`
- execution internal hash: `063cfb6ec37a4b67dc5f8681aa13ee7a5f4a45e2338622a45e61ba8755c8c13d`

Artifact root: `experiments/blender-static-nonplanar-multiowner-holdout-v0-1/`.
