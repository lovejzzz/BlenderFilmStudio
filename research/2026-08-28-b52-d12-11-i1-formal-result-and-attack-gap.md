# B52-D12.11-I1 formal result: Material Index eliminates the registered aliases, but semantic attack coverage remains pending

Date: 2026-08-28  
Status: **FORMAL MEASUREMENT COMPLETE; PROMOTION HELD FOR ADVERSARIAL-AUDIT GAP**

## Measured result

The preregistered paired intervention completed 16 new Blender 5.2 Cycles CPU renders and 74/74 unique child processes. The frozen analyzer returned `MATERIAL_INDEX_OWNER_INTERVENTION_SAFE_BUT_COVERAGE_NOT_SUPPORTED` with 18/19 gates; the independent raw audit returned 9/9.

The primary endpoint passed in both clean repeats of `SAME_INDEX_DEPTH_CROSSING_179X113`:

- the bound H1 accepted-alias set contained 15 pixels per repeat;
- Material Index accepted 0 of those 15 pixels;
- accepted pixels outside true-owner bilinear support fell from 15 to 0;
- new accepted coordinates relative to H1 were 0 across all eight cells;
- false accepted invalid-history pixels were 0 across all eight cells.

The causal pairing also passed: new Combined, Depth, Vector and Object Index canonical arrays were byte-identical to H1. The three noncritical fixtures retained exactly the H1 accepted counts. The critical fixture changed from 13,717 to 13,003 accepted pixels and moved the prior wrong-history branch from depth-late rejection to owner-early rejection: `INVALID_OWNER=4,187`, `INVALID_DEPTH=0`.

Quality and fallback stayed within the frozen limits. The critical accepted RGB maximum was `2.8878450393676758e-5`, risk underbounds were 0, and every nonaccepted pixel copied current RGBA exactly. Coverage remained unsupported because `ROTATED_SWEEP_HIGH_FREQUENCY_157X103` stayed at accepted/radius2 `0.9455795488`, with foreground-owner retention `0.9415061296`, below the unchanged 0.97/0.95 gates.

## Why promotion is held

The formal result records 56/56 mutation attacks, but inspection after the run found that the frozen analyzer implements those rows as canonical-hash sensitivity checks with a `mutationNonce`. They bind the result projection to a changed byte string, but they do **not** execute the preregistered semantic mutations such as substituting Object Index for Material Index, reusing an owner token, changing shared 14555, flipping an alias acceptance bit, or hiding a coverage loss.

The 9/9 audit does independently replay raw payload invariants, H1 pairing, dual-consumer identity, measurements and verdict mapping. Therefore the formal measurements above remain evidence, and the root must be retained unchanged. However, the spec's semantic attack-coverage claim is not yet proven. The tool-produced verdict is not promoted as the final D12.11 engineering conclusion until a separately preregistered, no-render adversarial audit performs real mutations against immutable copies and demonstrates the expected gate failures.

## Bound artifacts

- Spec SHA-256: `89dd3637ffe5af3544e8cd8aca8869eedd8b1a1867d41e08a354e5cd0c3b2a0e`
- Preflight hash: `d4a8db392659b557fca6eea9842dbcf87a81be0814e03a3b643adb03ba998b3a`
- Result SHA-256: `3eaa1461a7fa8b9f74e3320e19e56efa1cde3e0ea05618c1e04239d082b88457`
- Evidence hash: `2cabaed16827e9d2c4a0baf2d02ee79ff20efb27f3d303045127a20a9e6acbac`
- Audit SHA-256: `0133d69d4c5c0a9f1edf8bcb1b7d003d98e477c2390de733986e1f2d21edced6`
- Audit hash: `e1e49a0d06ebf3b3f46721f06d5857c105f1feee0127934a5ca57c234b054b12`
- Execution SHA-256: `fe945e4591152f432be93d4b2a0f0f47ce54ae3e3c0f3fadfbfdc9205b392f58`
- Receipt SHA-256: `0c05da327f8d8113d1f4e233222cf1df906635d7334629af05530e5381bfc12e`
- Receipt hash: `843ce7bc952a211cafb49e2f8ba1580a614144070b079a72a9bcc398fd15065e`

## Next falsifiable step

Preregister a no-Blender-render adversarial audit bound to this immutable formal root. It must execute at least 56 concrete mutations across parent/source/payload/channel/token/alias/coverage/verdict classes, require each mutation to fail one or more named gates, independently recheck the 15-to-0 endpoint from raw masks, and write a separate output root.
