# B62-Q1-D5-C2 · Retire contaminated D3 geometry baseline

Date: 2026-08-29  
Status: PREREGISTERED — v0.2 retained; no C2 tool change exists yet

## The correction exposed an older defect

C1 did exactly what it was allowed to do: one view-layer synchronization in each Blender implementation. In fresh v0.2, the two implementations still agreed, and `RS_S200_E200` reproduced every D4 corrected-geometry field on frames 193/204/228/252/276/288. The remaining 30 baseline mismatches all belong to D3 frames 216/240/264.

This localizes the contradiction. D3's two search implementations shared the same stale probe-camera evaluation order. Their mutual agreement therefore did not establish correct candidate geometry or uniqueness. That historical evidence remains in the repository but is no longer admissible as a baseline truth source.

## Why D5 can continue narrowly

D4 did not reuse D3's temporary probe matrix. It baked the declared transform across 96 integer frames into a new camera, saved a fresh `.blend`, independently reopened it, verified the bake, measured six corrected frames and produced six corrected/control Cycles pairs. Those D4 records show that the actual −45°, scale-2, 65 mm camera improves five frames and fails one. That is sufficient to motivate a bounded radial-scale compensation study, but not to claim the D3 grid was optimized correctly.

## New baseline contract

Each D5 observation may add only two pose fields to its existing nine derivation rows: post-synchronization evaluated camera location and quaternion. For constant `RS_S200_E200`, these must match the corresponding rows in the frozen D4 96-frame build bake within the existing `1e-9` tolerance. Geometry must still match D4's six independent corrected rows exactly/tolerantly. D3 geometry is checked only to preserve an explicit contamination finding; it is not an acceptance reference.

The eight validation frames remain sealed for geometry and rendering. Although D4's old bake already contains their camera transforms, the C2 auditor must select only the nine exposed derivation rows.

## Non-claims

C2 does not validate D3's “unique candidate” claim, does not broaden the camera family, and does not change a single feasibility threshold or selection rule. Any v0.3 candidate is only a candidate inside the D4-demonstrated motion-aware family and must still face fresh paired Cycles validation on the eight sealed frames.
