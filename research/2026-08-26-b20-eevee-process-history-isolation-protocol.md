# B20 Eevee process-history isolation protocol

Date frozen: 2026-08-26, before implementing the B20 renderer, selected-frame comparator or runner and before rendering any B20 frame.

Status: **PRE-REGISTERED / NOT EXECUTED**

## Why this boundary is next

B15-B19 repeatedly found sparse one-code-value Eevee differences, while sample count, output dither, Fast GI and TAA reprojection did not yield a production-quality exact setting. Every formal sequence so far rendered frames 1-144 inside one Blender process. The next evidence-supported boundary is therefore not another guessed visual control: it is whether prior renders in the same process affect a later frame.

## Sentinel selection frozen from prior evidence

The machine contract is `specs/eevee-process-history-isolation-spec.v0.1.json`.

Seven already-frozen comparisons share the relevant 32-sample, dither-zero profile: B16 D0, B17 S32-D0, B18 S32 and all four B19 cells. The selection rule is mechanical: include every frame that failed in at least four of those seven comparisons, then add frame 1 as the process-start anchor.

The resulting frozen set is:

`[1, 5, 20, 35, 38, 47, 83, 93, 103, 110, 114, 144]`

This prevents choosing new frames after seeing B20.

## Two modes, three independent replicates

At 32 samples, dither 0, Fast GI on and TAA reprojection on:

- `HISTORY`: H-A, H-B and H-C each launch a new Blender process and render the full 1-144 sequence in ascending order inside that process. The twelve sentinel images are primary; all 144 outputs remain evidence.
- `FRESH`: F-A, F-B and F-C each contain twelve sentinel observations, but every individual observation launches a new Blender process, renders exactly one frame and exits.

The frozen block order is H-A, all F-A sentinels, H-B, all F-B sentinels, H-C, all F-C sentinels. Planned work is 39 Blender processes and 468 rendered frames.

One post-freeze renderer implementation must serve both modes. Every process must verify the same receipt, source `.blend`, Blender, OCIO and render profile; apply the same fixed controls in memory; record process/invocation identity; and never save the source.

## Exact comparison graph

For each sentinel and each mode, compare all three replicate pairs: A-B, A-C and B-C. Also compare all nine HISTORY-to-FRESH replicate pairs. A pair passes only at maximum error zero and zero failed pixels.

A mode passes only if all 36 of its primary sentinel-pair comparisons pass. The cross-mode gate passes only if all 108 comparisons pass. No tolerance or majority vote may be introduced after execution.

Frozen decisions:

- `FRESH_PROCESS_RESTORES_EXACTNESS`: FRESH passes and HISTORY fails;
- `HISTORY_PROCESS_ONLY_EXACT`: HISTORY passes and FRESH fails;
- `NO_HISTORY_EFFECT_DETECTED`: both modes and the cross-mode gate pass;
- `DETERMINISTIC_HISTORY_EFFECT`: both modes pass internally but their outputs differ across modes;
- `PROCESS_ISOLATION_NOT_SUFFICIENT`: neither mode passes;
- `INVALID_EXPERIMENT`: any control, process, evidence, binding or attack gate fails.

## Attacks and non-claims

At least 17 negative cases are frozen, covering identities, all fixed controls, history order/completeness, single-frame process scope, process aliasing, missing or mutated sentinel files and comparison binding.

This is a same-machine Eevee PNG8 microbenchmark. It can locate a process-history boundary, not a Blender source line, a general failure probability, perceptual acceptability or a Cycles/EXR production rule.

## Freeze statement

At this commit, the B20 renderer, selected-frame comparator and runner do not exist; no B20 output has been rendered. Tool identities will be recorded after implementation, but the design, selection rule, run order, exact gates, decision labels and non-claims are fixed now.
