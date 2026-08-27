# B52-D12 · Perspective/subpixel reconstruction development probe

Date: 2026-08-27  
Status: `DEVELOPMENT_ONLY`  
Scientific verdict: none

## Why this probe exists

D11.1 supports only motion components within `1/1024` pixel of an integer. Its next declared boundary is a separately preregistered perspective/subpixel reconstruction contract with an explicit sample-coordinate rule, resampling kernel, metadata policy and falsifiable image-quality gate.

This probe is calibration evidence before that preregistration. Its names, 101×61 resolution, 50 mm camera, material frequencies and trajectory are permanently excluded from the future formal holdout.

## Retained failure

The first Blender 5.2 process stopped before rendering because `ShaderNodeCombineColor` has no `Alpha` input. The empty output root was retained with `FAILED_BEFORE_RENDER`; the correction removed only that nonexistent assignment and used a new `v0-2` root.

## Real Blender setup

- Blender 5.2.0 LTS, build `fbe6228777e7`;
- Cycles CPU, one sample, fixed four threads;
- perspective camera, 50 mm lens, 36 mm horizontal sensor;
- one opaque tessellated plane with a continuous, low-frequency, object-local emission material;
- plane trajectory `(-0.040,+0.030,0.000) → (+0.015,-0.025,0.180) → (+0.060,+0.020,0.360)`;
- two independent fresh renders for previous/current multipart EXRs;
- Vector, Depth and Object Index read from the current frame.

The actual Vector field is not near-integer data: all 12,322 moving XY components lie farther than `1/1024` pixel from an integer, median fractional distance is `0.2575163841`, and maximum fractional distance is `0.4984893799` pixel.

## Independent projection oracle

The analyzer does not ask Blender to explain its Vector pass. It independently casts a pinhole ray through each current pixel center, intersects the current rigid plane, maps the recovered local point through the previous object transform, and projects that world point through the previous camera.

For top-left decoded arrays the observed Blender endpoint convention is:

```text
q_x = x + Vector.X
q_y = y - Vector.Y
```

Across 6,161 moving owner pixels, Blender Vector agreed with that analytic projective endpoint to:

| endpoint measurement | observed |
|---|---:|
| maximum absolute error | `2.6787651905e-5 px` |
| p99 absolute error | `2.2820366752e-5 px` |
| RMSE | `1.2918756652e-5 px` |

This is development evidence for the coordinate formula, not a general Vector-pass claim.

## Reconstruction measurements

The external consumer used clip-boundary bilinear sampling over previous linear RGBA. Measurement excludes a three-pixel border and requires the declared owner and alpha. The current real Blender beauty is the target.

| consumer | RMSE | p99 | maximum | PSNR, unit range |
|---|---:|---:|---:|---:|
| correct projective bilinear | `6.10225e-5` | `1.45853e-4` | `1.46240e-4` | `84.29 dB` |
| correct endpoint, nearest | `2.79617e-3` | `6.32870e-3` | `6.52459e-3` | `51.07 dB` |
| wrong-sign bilinear | `1.55352e-2` | `3.84273e-2` | `3.85106e-2` | `36.17 dB` |

Correct bilinear RMSE was about 45.8× smaller than nearest and 254.6× smaller than wrong-sign bilinear on this probe. That separation is large enough to preregister relative sensitivity gates without fitting a formal fixture.

## Depth counterexample and design consequence

Directly comparing sampled previous depth with current depth is invalid under rigid dolly motion. The current surface depth was about `9.82`, while the corresponding previous surface depth was about `10.00`. The measured absolute difference was `0.1800003052`, versus a D9-style identity tolerance of at most `0.0095898435`.

Therefore a direct current-depth/previous-depth equality test rejected all 5,225 evaluated pixels even though the history correspondence was correct. The next contract must instead predict the current surface point's **previous-camera depth** from frozen camera/object transforms and compare sampled previous depth to that predicted value. This is not threshold relaxation; it is a different physical quantity.

## What may be used for D12 design

The fresh holdout may preregister:

1. the top-left endpoint formula above;
2. an independent rigid-plane pinhole oracle;
3. clip-boundary bilinear sampling;
4. same-owner/four-tap alpha validity;
5. transform-predicted previous depth rather than direct depth identity;
6. absolute reconstruction gates plus relative superiority over wrong-sign and nearest controls.

The formal fixtures must use new resolution, lens, sensor, transforms, mesh names, material frequencies and phases. Tool implementations, formal output and thresholds must be frozen only after the new protocol is committed.

## Non-claims

This probe does not establish a formal D12 verdict. It does not cover occlusion, disocclusion, multiple owners, transparency, deformation, hair, volumes, motion blur, depth of field, noisy path-traced lighting, arbitrary textures, temporal accumulation, cinematic quality or human preference.

## Evidence identity

- source report SHA-256: `2e1a8414b8fd70b725f375fc02717cec63f1dbeff029e0417a8fd329bd05f524`
- previous EXR SHA-256: `d7944d1b5a1db1a862546d6a9ecce843397d33848475c5e64c4e7ada9eee7bd7`
- current EXR SHA-256: `8c009079348878a35a24fd6860e0d7ac458acc60a85f3ccbef5b293cac4ac298`
- final development analysis: `experiments/blender-projective-subpixel-development-probe-v0-2/analysis-with-oracle-depth.json`

