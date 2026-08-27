# B49-MB-D1 — motion-blur semantics and cost derivation protocol

Date: 2026-08-27

Status: frozen before renderer, runner, analyzer or output

## Question

B49-R closed a bounded resolution-scaling gap while motion blur remained disabled. B49-MB-D1 asks what Blender 5.2 Cycles actually changes when motion blur is enabled on the existing linear camera push, whether a static scene remains invariant, how shutter duration affects decoded pass data and cost, and whether nominally equivalent exposure windows are operationally equivalent.

This is a derivation experiment for choosing a later formal motion-quality gate. It does not preselect the shutter that looks most cinematic.

## Runtime semantics frozen from Blender 5.2

The Blender 5.2 manual and RNA define `motion_blur_shutter` as exposure time in frames, with `START`, `CENTER` and `END` positioning relative to the current frame. A shutter of 0.5 therefore spans half a frame; interpreting it as a conventional 180-degree shutter is an inference, not a Blender quality guarantee.

Local Blender 5.2 inspection established before this protocol:

- TABLETOP uses perspective camera `CAM_B43_A`; it is the only animated object, has one action over frames 1–48 and every keyframe segment is `LINEAR`.
- INTERIOR uses perspective camera `CAM_B43_B`, has no animated objects, and its camera matrices are identical at frames 8.5, 9, 9.5, 10, 10.5 and 11.
- Camera-motion blur's orthographic-camera limitation therefore does not apply. The documented moving-light limitation is not invoked because the camera moves while the lights remain fixed.

## Eleven frozen cells

Every cell runs in a fresh, isolated Blender 5.2 Linux/amd64 Cycles CPU worker at 128×72, 128 spp raw, seed offset 647647, four threads, ACES 2, denoising off, persistent data off and the exact seven-subimage production pack.

TABLETOP moving-camera cells:

1. blur off, frame 22;
2. blur on, centered shutter 0.0, frame 22;
3. blur on, centered shutter 0.5, frame 22;
4. blur on, centered shutter 1.0, frame 22;
5. blur on, start shutter 1.0, frame 22—nominal window `[22,23]`;
6. blur on, end shutter 1.0, frame 23—nominal window `[22,23]`.

INTERIOR static-control cells:

7. blur off, frame 10;
8. centered shutter 0.5, frame 10;
9. centered shutter 1.0, frame 10;
10. start shutter 1.0, frame 10;
11. end shutter 1.0, frame 11.

## Frozen comparisons

The analyzer reopens every multipart EXR and reports canonical per-pass hashes, changed float-component counts, linear RMSE/MAE/max error, scene-linear luminance edge energy, render time, fresh-worker wall time, peak self RSS and EXR bytes.

It evaluates five relations without revising them after seeing output:

- zero-width enabled shutter versus blur-off on the moving frame;
- centered half-frame shutter versus blur-off on the moving frame;
- zero/half/full centered duration dose response;
- `START 1.0 @ frame 22` versus `END 1.0 @ frame 23`, which nominally cover the same time window;
- all static cells versus the static blur-off baseline.

Exact equality is measured, not assumed. If an apparently equivalent pair differs, the difference remains a result rather than being hidden as noise. D1 is usable when all eleven valid representations complete inside the frozen boundary, every relation is emitted, cleanup is zero and independent analyzer replay is byte exact. D1 may be usable even when a semantic equality hypothesis is falsified; those outcomes determine the formal B49-MB gate.

## Claim boundary

D1 cannot select a physically correct or artistically preferred shutter, establish full-shot temporal quality, validate deformation/particle/rolling-shutter blur, establish depth of field, high-resolution cost, GPU/Eevee behavior, native x86/cloud throughput or dollar cost. A later formal holdout must use unseen moving frames and a high-sample local reference strategy, and subjective “cinematic” preference still requires blinded human observers.
