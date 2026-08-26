# B23 Eevee repeated-render boundary protocol

Date frozen: 2026-08-26, before implementing the B23 renderer, comparator or runner and before rendering any B23 frame.

Status: **PRE-REGISTERED / NOT EXECUTED**

## Question

B22 showed that the exposed `FIXED/1` thread intervention is not sufficient. At the accepted T08 scene-linear EXR32 profile, does strict variation recur between repeated renders of the same frame inside one initialized Blender process, or only across process initialization?

The machine contract is `specs/eevee-repeated-render-boundary-spec.v0.1.json`.

## Frozen design

All twelve B20-B22 sentinels remain fixed. For every sentinel and replicate A/B/C, interleave one PERSIST process and one FRESH process. A PERSIST process loads the source once, holds one frame constant and invokes render three times consecutively without reloading the blend. A FRESH process invokes render once. All outputs are scene-linear ACEScg RGBA32 ZIP OpenEXR at fixed T08, 32 samples, dither 0, Fast GI on and TAA reprojection on.

The design totals 72 unique Blender processes, 144 render calls and 144 EXRs.

Three zero-tolerance gates are frozen:

- within PERSIST: R1-R2, R1-R3 and R2-R3 inside every persistent process, 108 comparisons;
- PERSIST cross-process: A-B, A-C and B-C at each render ordinal, 108 comparisons;
- FRESH cross-process: A-B, A-C and B-C, 36 comparisons.

## Frozen decisions

- within PERSIST exact, both cross-process gates non-exact → `PROCESS_INITIALIZATION_BOUNDARY_SUPPORT`;
- within PERSIST non-exact → `PER_RENDER_VARIATION_SUPPORT`;
- all three gates exact → `VARIATION_NOT_REPRODUCED`;
- within PERSIST exact but the two cross-process gates disagree → `MIXED_CROSS_PROCESS_PATTERN`;
- any control failure → `INVALID_EXPERIMENT`.

No tolerance, probability claim or favorable subgroup may be added after execution.

## Interpretation boundary

PERSIST deliberately renders the same frame repeatedly, so it removes prior-frame timeline history from the question. If those repeats are stable while independent processes disagree, the experiment supports an initialization boundary only. It cannot identify whether the source is a Metal driver, shader compilation/cache, allocation layout, GPU scheduling or Blender code. If same-process repeats disagree, the recurrence boundary moves to each render invocation or later GPU work, but still does not prove a race.

## Controls and attacks

The accepted B22 configurator is frozen by hash and establishes `FIXED/8`, dither 0, Fast GI on and reprojection on in memory. Twenty negative categories cover upstream/tool identities, source/request states, cell and PID binding, the 3-versus-1 call contract, same-frame ordinals, unique process count, EXR layout/files and both within/cross-process comparison bindings.

## Freeze statement

At this commit, `blender/render_repeated_process_exr.py`, `blender/compare_repeated_process_exr.py` and `scripts/run-b23-repeated-render-boundary-experiment.mjs` do not exist. No B23 output has been rendered.
