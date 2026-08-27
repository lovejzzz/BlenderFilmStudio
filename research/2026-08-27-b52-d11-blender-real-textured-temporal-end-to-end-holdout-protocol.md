# B52-D11 — Real textured Blender temporal end-to-end holdout protocol

Date: 2026-08-27
Status: `PREREGISTERED_NO_FORMAL_TOOLS_OR_OUTPUT`

## Question

Can the already promoted narrow contracts compose without an unregistered repair?

```text
fresh real Blender textured multipart EXR
  → D10.1 raw pass adapter
  → D9.1 truncate-toward-zero integer temporal accumulation
  → D8 Raw RGBA32 EXR bridge
```

The experiment covers opaque orthographic integer-motion fixtures only. It must reject a layer discontinuity, a same-Object-Index depth discontinuity and out-of-bounds history, and it must preserve a fully static control.

## Why this experiment is necessary

D10.1 proved that Blender 5.2 Vector, Depth and Object Index can be extracted reproducibly into seven canonical arrays. D9.1 proved an external integer-motion accumulator on analytic arrays. D8 proved a Raw float32 compositor bridge. None of those experiments proved that their exact interfaces compose.

The sharpest open contract is motion integerization. D10.1 intentionally preserves raw Blender float32 Vector values. D9.1 converts motion with Python `int()`, which truncates toward zero. A theoretically integral 13-pixel displacement observed as `12.99999` would therefore become 12, even though it passed D10.1's subpixel endpoint-error gate. D11 freezes the inherited truncation behavior unchanged and tests it explicitly. Adding `round()`, snapping or an epsilon after seeing D11 would invalidate the experiment.

## Fresh fixtures

All four fixtures use 197×113, orthographic scale 19.7 and nominal 10 pixels per world unit. Resolution, scale, names, IDs, mesh geometry, materials and trajectories are disjoint from D9–D10.1.

Surfaces are real generated mesh textures: each surface is one tessellated plane mesh, and alternating polygons receive fixed high-contrast emission materials. There are no image textures or external assets. Semantic probes sit at least two pixels away from object and material-cell boundaries.

1. `REAL_OCCLUSION_DISOCCLUSION_OBJECT_XY_197X113`
   - moving foreground: expected Vector XY `[-13,+7]`, ZW `[-17,+9]`;
   - expected D9 motion `[+13,-7]`;
   - one 3×3 valid mover probe and one 3×3 layer-disocclusion rejection probe.
2. `REAL_CAMERA_BOUNDS_197X113`
   - moving camera: expected Vector XY `[+11,-8]`, ZW `[+16,-13]`;
   - expected D9 motion `[-11,+8]`;
   - one 3×3 valid interior probe and one 3×3 out-of-bounds rejection probe.
3. `REAL_SAME_ID_DEPTH_DISCLOSURE_197X113`
   - foreground and background intentionally share Object Index 6606;
   - expected Vector XY `[-14,+7]`, ZW `[-14,-8]`;
   - one 3×3 revealed-background probe must pass layer equality and fail depth only.
4. `REAL_TEXTURED_STATIC_CONTROL_197X113`
   - no animation and expected motion `[0,0]`;
   - all 22,261 pixels must be valid and resolved RGBA must equal current RGBA exactly.

Exact geometry, probe centers, material values and animation values are normative in `specs/blender-real-textured-temporal-end-to-end-holdout.v0.1.json`.

## Frozen contracts

### Source render

- real Blender 5.2.0 LTS `fbe6228777e7`;
- Cycles CPU, one sample, fixed seed 521101, adaptive sampling off, denoising off;
- motion blur, depth of field and persistent data off;
- multipart float32 ZIP EXR with Combined, Depth, Vector and Object Index;
- every previous/current frame and repeat launches in a fresh Blender process.

### Typed structure

D10.1's typed oracle is inherited: only explicitly enumerated RNA float paths receive an IEEE-754 binary32 round-trip. Names, enums, integer IDs, topology, polygon material indices, Action structure, render state and operation counts remain exact. No global epsilon is permitted.

### Adapter

The adapter writes the seven D9.1 arrays. Motion is raw float32 `[-Vector.X,-Vector.Y]`. The adapter may not round, snap, clamp or repair it.

### Accumulator

Two new generic implementations—scalar Python and scalar Node—read the adapter arrays independently. Both use:

```text
ix = truncTowardZero(rawMotionX)
iy = truncTowardZero(rawMotionY)
q  = (x - ix, y + iy)
```

History is valid only when q is in bounds, Object Index matches, depth differs by at most `max(1,currentDepth)/1024`, and both alpha values are positive. Valid pixels receive one final float32 cast of the 0.5/0.5 average; invalid pixels remain current exactly.

Python and Node validity masks and resolved RGBA must be byte-identical. The formal result also records a round-to-nearest counterfactual, but it cannot satisfy the truncation gate or repair the verdict.

### Raw EXR bridge

Only after Python and Node resolved bytes agree does the Python path enter a Raw RGBA32 ZIP EXR. Two fresh Blender compositor processes per encoded cell must reproduce the decoded float32 bytes exactly. EXR container-byte equality is not required.

## Semantic and sensitivity gates

- Every frozen 3×3 probe must have the declared reason: VALID, INVALID_BOUNDS, INVALID_LAYER or INVALID_DEPTH.
- The same-ID depth probe must pass ownership equality and fail depth; it cannot be classified as a layer rejection.
- On declared moving-owner interior pixels, inherited truncation must yield the analytic integer motion exactly. Static pixels must truncate to zero.
- The raw Vector endpoint gates remain D10.1's p99 ≤ 1/4096 px and maximum ≤ 1/1024 px.
- Removing layer/depth rejection must change at least 32 pixels with maximum absolute difference ≥0.125 on both applicable fixtures.
- Reversing the motion sign must meet the same sensitivity floor on all three moving fixtures.
- Static must be 22,261/22,261 valid and resolved=current exact.

## Formal process boundary

| Stage | Processes | Blender renders |
|---|---:|---:|
| Source previous/current, 4 fixtures × 2 repeats | 16 | 16 Cycles |
| Multipart adapter | 8 | 0 |
| Python accumulator | 8 | 0 |
| Node accumulator | 8 | 0 |
| Resolved EXR encoder | 8 | 0 |
| Blender bridge, two repeats per encoded cell | 16 | 16 compositor |
| Independent analyzer | 1 | 0 |
| **Total** | **65 unique PIDs** | **32** |

Formal model calls and network calls are zero. Projected write is 64 MiB, admitted only when projected free space stays above the frozen 100 GiB reserve.

## Decision

`BLENDER_REAL_TEXTURED_TEMPORAL_END_TO_END_HOLDOUT_SUPPORTED` requires every gate and every attack to pass.

Any failure preserves all completed evidence and produces `BLENDER_REAL_TEXTURED_TEMPORAL_END_TO_END_HOLDOUT_NOT_SUPPORTED` with the earliest frozen base-failure label. If the failure is `MOTION_INTEGERIZATION`, the only allowed next step is a separately preregistered D11.1 nearest-integer quantizer recovery on new fixtures. D11 itself may not be changed or rerun.

## Non-claims

D11 does not cover perspective, subpixel/deformation motion, transparency, Cryptomatte, volumetrics, hair, motion blur, depth of field, cross-platform equivalence, temporal image-quality improvement, cinematic quality, character consistency or human preference.

## Pre-tool state

At preregistration, all eleven planned formal tool paths and the formal output root are absent. No D11 render, adapter array, accumulator output or diagnostic exists.

Frozen spec SHA-256: `f1505c42426e8e286ee1584de3df12fb33b7db57518d6d91e1fd93aa3bed5a5f`.
