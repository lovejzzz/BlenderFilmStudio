# B62-Q1-D2 material-aware framing diagnostic protocol

Date: 2026-08-29  
State: **PREREGISTERED before tool creation**  
Scope: one disclosed failed derivation frame and two disclosed readable controls; no camera correction and no render.

## Why D1 was scientifically rejected

D1 executed correctly, but its preregistered near-occlusion explanation did not survive its own controls. `CLOSE_REFLECTION` had no first hit inside the frozen 0.5 m boundary, while `WIDE_APPROACH` falsely satisfied the complete signature because ordinary mesh ray casting treated the closed `B62_ATMOSPHERE` volume boundary as opaque. The failed hypothesis and its immutable evidence remain part of the record.

The useful residual signal is different: all 2,304 CLOSE rays hit `B62_HELMET`; only 7.55% of evaluated character vertices project on screen, yet the clamped character bounds cover the whole frame. D2 asks whether that extreme-framing signal remains exact after a material-aware traversal removes the known volume-only confound.

## Frozen material rule

A hit owner is skipped only when every populated material slot is node based, has a linked Material Output `Volume` input, and has no linked Material Output `Surface` input. Everything else blocks the diagnostic ray. A skipped hit advances the origin by exactly 10 μm in the unchanged world-space ray direction; more than 64 intersections invalidates the run. This is an auditable visibility approximation, not a renderer or physical-volume calculation.

Both independent Blender programs must disclose the relevant material graph roster and independently prove that `B62_ATMOSPHERE` / `MAT_B62_VOLUME` meets the rule. They repeat the same 64×36 grid, five anchors and evaluated character projection at frames 48, 144 and 240.

## Frozen derivation signature

The failed CLOSE frame is localized only if all of these are true:

- the first visual blocker is dominated by `B62_HELMET` at ≥ 95%;
- character objects account for ≥ 95% of visual-blocker rays;
- ≤ 10% of evaluated character vertices project on screen;
- the clamped character projection bounds cover ≥ 95% of the frame;
- no more than one of five semantic anchors is exactly visible;
- neither readable control satisfies the whole conjunction.

These values were selected after disclosure of D1 measurements. Passing therefore supports a causal localization and a subsequent correction experiment, but is not independent evidence of general composition quality. A later correction must use temporal frames not used for adjustment and separately frozen production thresholds.

## Execution and evidence

The runner permits exactly two fresh Blender 5.2 processes and one Node auditor, with zero render, model, network and Docker/Colima activity. Source `.blend` bytes and state must remain unchanged. Primary and independent rosters must match exactly and floats within `1e-9`. Admission is written before child launch, all process receipts are retained, and any failed root is immutable.
