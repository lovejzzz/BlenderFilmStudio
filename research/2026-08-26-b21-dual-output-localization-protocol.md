# B21 same-Render-Result dual-output localization protocol

Date frozen: 2026-08-26, before implementing the formal B21 renderer, comparator or runner and before rendering any B21 frame.

Status: **PRE-REGISTERED / NOT EXECUTED**

## Question

Does the B20 one-code-value variation already exist in scene-linear RGBA32 float OpenEXR output, or does it first remain observable only after the ACES 2 display transform / PNG8 output path?

The machine contract is `specs/dual-output-localization-spec.v0.1.json`.

## Why this experiment is operationally valid

The exploratory real-Blender inventory rejected direct `Render Result.pixels` access: the background `Render Result` data-block had data but exposed an empty RNA pixel sequence. It did prove a narrower, auditable path. One render call can be followed by two `Render Result.save_render` operations: PNG RGBA8 first, then ZIP OpenEXR RGBA32 after changing only file-output settings. Bundled OIIO decoded the EXR as 960×540 RGBA float.

The Blender 5.2 manual defines OpenEXR as a high-precision scene-linear intermediate and distinguishes render-view display output from linear storage. The B02 BuildPlan further freezes ACEScg as scene-linear encoding and pins the ACES 2 OCIO bytes.

This is therefore a same-Render-Result **dual-file** experiment. It does not claim direct memory-buffer access.

## Frozen design

Carry all twelve B20 sentinels forward without reselection: `[1, 5, 20, 35, 38, 47, 83, 93, 103, 110, 114, 144]`.

For every frame, launch A, B and C as three new Blender processes in immediate frame blocks. Each of 36 processes must:

1. verify receipt, source `.blend`, Blender, OCIO and fixed 32-sample Eevee controls;
2. call `bpy.ops.render.render` exactly once;
3. save PNG RGBA8 under `sRGB - Display` / `ACES 2.0 - SDR 100 nits (Rec.709)`;
4. change only output-file settings;
5. save ZIP OpenEXR RGBA32 from the same Render Result without rerendering;
6. record the process, render-call, save, layout and file hashes and never save the source `.blend`.

The planned result is 36 processes, 36 rendered frames and 72 output files.

## Exact gates and decisions

Within each format, compare A-B, A-C and B-C for all twelve frames using bundled OIIO at maximum error zero and failure pixels zero. A format passes only at 36/36 exact decoded pairs. File-container equality remains descriptive.

- EXR exact / PNG non-exact → `DISPLAY_PNG_PATH_SUPPORT`;
- EXR non-exact / PNG non-exact → `PRE_PNG_VARIATION_SUPPORT`;
- EXR non-exact / PNG exact → `PNG_QUANTIZATION_MASKS_FLOAT_VARIATION`;
- both exact → `VARIATION_NOT_REPRODUCED`;
- any control failure → `INVALID_EXPERIMENT`.

No post-hoc tolerance, majority vote or nearest-story label is allowed.

## Attacks and non-claims

At least 21 negative cases are frozen across prior-result identities, source/runtime/tools, all four Eevee constants, exactly-one-render/two-save scope, both decoded layouts/types, partner files, mutated bytes and comparison binding.

If EXR differs, B21 localizes variation to at or before the scene-linear EXR save boundary; it does not identify a shader, reducer, driver or GPU race. If only PNG differs, it supports the display/output path without uniquely identifying a transform or quantizer. Nothing generalizes to Cycles, multilayer/AOV EXR or another device.

## Freeze statement

At this commit, `blender/render_dual_output_localization.py`, `blender/compare_dual_outputs.py` and `scripts/run-b21-dual-output-localization-experiment.mjs` do not exist, and no B21 frame has been rendered. Their future hashes must be recorded, while this design, order, gates, decisions and non-claims remain fixed.
