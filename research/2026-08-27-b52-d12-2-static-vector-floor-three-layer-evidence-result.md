# B52-D12.2 static Vector floor and three-layer evidence result

Date: 2026-08-27

Verdict: `BLENDER_STATIC_VECTOR_FLOOR_WITHIN_REGISTERED_TOLERANCE`

Orthogonal exactness observation: `STATIC_EXACT_ZERO_FALSIFIED`

## What was executed

The preregistered single-use matrix launched 55 unique child processes:

- 12 real Blender 5.2.0 LTS Cycles source renders;
- 6 multipart EXR adapters;
- 6 Python and 6 Node scalar bilinear consumers;
- 12 Python and 12 Node typed-envelope encoders;
- 1 independent analyzer.

All processes exited successfully. There were zero model and network calls. The result passed 24/24 registered attacks.

## Measured floating floor

The authored object and camera transforms were identical at frames 0, 1 and 2. Previous/current source RGB arrays were exact in every cell. Blender's decoded current Vector was nevertheless nonzero in every fixture and repeat.

| Fixture | Valid pixels | Max absolute Vector component | Max reconstruction RGB error | Reconstruction RMSE |
| --- | ---: | ---: | ---: | ---: |
| `STATIC_WIDE_83X53` | 3,375 | `7.62939453125e-6 px` | `8.94069671631e-8` | `3.73466072609e-9` |
| `STATIC_TELE_113X71` | 6,615 | `1.52587890625e-5 px` | `1.19209289551e-7` | `1.77593347129e-8` |
| `STATIC_NORMAL_127X79` | 8,449 | `2.288818359375e-5 px` | `1.78813934326e-7` | `2.06624478826e-8` |

Both repeats produced the same measurements and exact source/reconstruction array identities. The largest observed Vector residual is exactly three times `2^-17 px`; the three maxima form `1×`, `2×` and `3×` that quantum. This is a measured numerical pattern, not yet a claim about Blender's internal implementation.

The frozen engineering bounds all passed:

- Vector component maximum ≤ `1/4096 px`;
- reconstruction RGB maximum ≤ `1/524288`;
- reconstruction RGB RMSE ≤ `1/1048576`;
- source static RGB maximum = `0`;
- within-fixture repeats exact.

At the worst cell, the registered Vector and maximum-RGB bounds retain approximately 10.67× headroom; the RMSE bound retains approximately 46.16× headroom.

## Three-layer evidence outcome

### 1. Payload identity

Python and Node reconstructed RGBA and valid-mask byte streams matched in all 6/6 cells. This is the strongest cross-language algorithm claim in the experiment: the consumer outputs themselves are identical.

### 2. Document integrity

Each of the twelve producer reports was independently normalized by both frozen D12.1 typed-envelope implementations. All 12/12 Python/Node envelope pairs matched byte-for-byte. Report identity no longer depends on native decimal exponent spelling.

### 3. Decision metrics

The independent analyzer imported neither consumer and ignored producer metrics; producers emitted none. It recomputed Vector and RGB measurements directly from immutable adapter and reconstruction payloads in one frozen scalar order. This avoids requiring Python and JavaScript reduction implementations to return bit-identical binary64 summaries.

## Interpretation

For the exact Blender 5.2/Cycles/static-planar boundary tested here, treating static motion as a small bounded numerical residual is supported, while treating it as mathematical zero is falsified. A temporal consumer should therefore use a preregistered finite tolerance at the semantic gate and preserve the raw Vector payload for evidence; it should not silently snap arbitrary motion to zero.

The evidence architecture is also supported at this boundary: payload equality, document integrity and decision metrics can be tested independently without weakening any of them.

## Non-claims and next boundary

- The measured `2^-17 px` pattern is not proven to be Blender's universal quantization rule.
- The result does not cover moving geometry, deformation, transparency, disocclusion, multi-owner filtering or nonplanar depth.
- It is not a perceptual or cinematic-quality claim.
- The typed envelope is project-local and is not claimed to implement RFC 8785/JCS.
- The next experiment should test whether the registered static bound survives opaque nonplanar geometry and multiple ownership boundaries before it is promoted beyond planar fixtures.

## Evidence identities

- `results.json` SHA-256: `948ffe7f6b18bc7a5458352c545570ec1a15f9975c2ae8250de3670ac7cf3036`
- result internal evidence hash: `9ee3fcbaee29d84034292a67ba87ceac715f29b983da099fc786e24d6d0edc14`
- `receipt.json` SHA-256: `aa675e9d2cefb9e7ce3b8f53dc98437ddb393ae95b7d5cdb8773d71bee10ee5f`
- receipt internal hash: `ab07380896f683a3f08a95f8a2ce7e595afdbccbaa1468b5f74ed6b24acf0a23`
- `execution.json` SHA-256: `f6394366e73fe2fff4890b3735363dbfa68566bab3dac060b48ddc8f6cca38e8`
- execution internal hash: `2bd1557ba6510693e3098f1f2a7df9c0548ae408bb49138138b3ed2205bf5f43`

Artifact root: `experiments/blender-static-vector-floor-three-layer-evidence-holdout-v0-1/`.
