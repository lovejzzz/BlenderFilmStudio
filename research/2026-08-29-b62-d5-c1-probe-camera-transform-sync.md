# B62-Q1-D5-C1 · Probe-camera transform synchronization correction

Date: 2026-08-29  
Status: PREREGISTERED — written after retaining v0.1 and before changing any D5 tool

## What failed

The v0.1 run did not produce a scientific result. Both fresh Blender processes completed the full 14×9 search and agreed within the frozen tolerance, but the constant `RS_S200_E200` baseline did not reproduce retained D3/D4 geometry. The Node auditor therefore failed exactly one of 19 checks and left the scientific verdict null.

The apparent v0.1 count of six feasible candidates and apparent selection `RS_S200_E250` are explicitly non-evidence. They may not be copied into or used to narrow the retry.

## Diagnosis

Both implementations updated the evaluated dependency graph before assigning the temporary probe camera's new location and quaternion. They then measured through `camera.matrix_world` without synchronizing the view layer after that assignment. Blender can therefore expose the prior evaluated matrix during the current measurement. The mismatch pattern is consistent with this ordering defect: the first baseline frame carries state from the preceding candidate, followed by frame-to-frame lag.

D3 did not expose the problem because its three-frame search was internally self-consistent and had no retained transform baseline. D5 deliberately introduced the baseline-reproduction gate, and that gate caught the defect before candidate promotion.

## Only authorized repair

Each independently authored Blender tool may insert `bpy.context.view_layer.update()` immediately after configuring its probe camera and before calling geometry measurement. Nothing else in traversal, projection, material classification, candidate construction, frames, thresholds, path math or selection may change.

The runner and Node auditor may change only to bind this correction, bind the immutable v0.1 tree and use fresh root `experiments/b62-camera-quality-motion-aware-search-v0-2`. The retry must rerun both Blender processes from the master scene. Reusing v0.1 observations is forbidden.

## Acceptance

The constant-scale baseline must now reproduce all retained D3 selected-candidate rows at frames 216/240/264 and the retained D4 corrected rows at frames 193/204/228/252/276/288 under the original exact/tolerance contract. Only after that gate passes may the unchanged D5 family yield either the preregistered FOUND or NOT_FOUND verdict. The eight validation frames remain sealed.
