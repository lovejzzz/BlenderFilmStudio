# B22 Eevee fixed-thread-count factorial protocol

Date frozen: 2026-08-26, before implementing the B22 configurator, EXR renderer, comparator or runner and before rendering any B22 frame.

Status: **PRE-REGISTERED / NOT EXECUTED**

## Question

B21 located strict variation at or before the scene-linear EXR32 boundary. The earlier real-Blender RNA inventory reports `threads_mode=FIXED` and `threads=8`. Is that exposed thread count a sufficient cause of variation relative to one fixed thread?

The machine contract is `specs/eevee-thread-count-factorial-spec.v0.1.json`.

## Frozen design

Carry all twelve B20/B21 sentinels forward. At every frame, interleave six new processes in the order T01-A, T08-A, T01-B, T08-B, T01-C, T08-C. T01 fixes one render thread; T08 is a fresh observed-source control with eight. All other settings remain 32 Eevee samples, dither 0, Fast GI on, TAA reprojection on and 960×540 scene-linear ACEScg RGBA32 ZIP OpenEXR.

The design totals 72 Blender processes and 72 rendered EXRs. Within each cell, compare A-B, A-C and B-C for all twelve sentinels. A cell is exact only at 36/36 decoded float comparisons, max error zero and zero failed pixels.

Frozen decisions:

- T01 exact / T08 non-exact → `THREAD_COUNT_CAUSAL_SUPPORT`;
- both non-exact → `THREAD_COUNT_NOT_SUFFICIENT`;
- both exact → `VARIATION_NOT_REPRODUCED`;
- T01 non-exact / T08 exact → `REVERSE_OR_MIXED_THREAD_PATTERN`;
- any control failure → `INVALID_EXPERIMENT`.

No tolerance or probability story may be added after execution.

## Critical caveat

This control is exposed under `scene.render`, but Eevee on Apple Silicon performs substantial work on the GPU. The experiment must therefore avoid claiming that `threads=1` serializes GPU shader execution. A both-nonexact result means only that the exposed CPU-facing control is insufficient. It does not eliminate hidden GPU scheduling or sample-reduction concurrency.

## Controls and attacks

Every intervention must first observe source `FIXED/8`, set `FIXED/1` or `FIXED/8` in memory, report the resulting values and never save the source `.blend`. At least 19 negative categories cover prior-result/tool identities, source and requested thread states, all render constants, one-render scope, float EXR layout, files and comparison binding.

## Freeze statement

At this commit, `blender/configure_eevee_threads.py`, `blender/render_thread_factorial_exr.py`, `blender/compare_thread_factorial_exr.py` and `scripts/run-b22-thread-count-factorial-experiment.mjs` do not exist. No B22 output has been rendered.
