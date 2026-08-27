# B52-D11 — Real textured composition development smoke

Date: 2026-08-27

Status: `DEVELOPMENT_ONLY_NOT_FORMAL_EVIDENCE`

## Outcome

The first real Blender implementation smoke found both an ordinary code defect and the exact scientific risk D11 was designed to test.

The first attempt stopped before rendering because a Python `dict.get` fallback expression eagerly accessed `locationByFrame` on a static object. No source EXR or formal output was created. The implementation was changed to an explicit branch and the development cell was rerun.

The corrected smoke used two fresh Blender 5.2 Cycles processes for frame 0 and frame 1 of `REAL_OCCLUSION_DISOCCLUSION_OBJECT_XY_197X113`, one multipart adapter process, and independent Python and Node accumulator processes. The EXR pass roster and channel layout matched exactly. Both frozen 3×3 probes in this fixture produced their declared reasons: 9/9 `VALID` for the mover interior and 9/9 `INVALID_LAYER` for the disocclusion.

## Composition counterexample signal

Python and Node produced byte-identical validity, reason, resolved, naive, wrong-sign and round-nearest diagnostic arrays. Both reported 21,668 valid and 593 invalid pixels.

The raw Blender motion field contained analytically integral owner motion on most pixels, but boundary/filter samples included values such as:

```text
raw (12.999996185302734, -7.0) → truncation (12, -7)
raw (13.0, -6.999996185302734) → truncation (13, -6)
```

The preregistered inherited truncation result differed from the round-nearest diagnostic in 87 float32 scalars. The round-nearest result equaled the current RGBA bytes exactly (`8afc2cff…`); the truncation result did not (`85fb98ef…`). Validity was unchanged, so this cell isolates an image-coordinate error rather than a rejection-mask difference.

This is strong development evidence for a `MOTION_INTEGERIZATION` failure, but it is not the formal D11 verdict. The tools are not frozen, only one fixture/repeat ran, the Raw EXR bridge has not run, and none of the 56 attacks or the independent audit has run.

## Durable artifact

Machine-readable observation: `experiments/blender-real-textured-temporal-end-to-end-development-smoke-v0-1/observation.json`.

Next: implement and test the Raw EXR encoder/Blender bridge, analyzer, runner, audit, preflight and contract suite; then freeze all eleven tools before any formal output exists.
