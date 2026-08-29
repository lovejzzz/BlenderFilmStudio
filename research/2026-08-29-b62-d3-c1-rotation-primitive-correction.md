# B62-Q1-D3-C1 rotation-primitive correction

Date: 2026-08-29  
State: **PREREGISTERED before retry-tool modification**

Both D3 Blender processes completed all 96 candidates × 3 derivation frames and independently selected the same sole feasible cell. That agreement is informative but cannot override the frozen audit: 91 projected-area floats differed by more than `1e-9`, so v0.1 is invalidated and has no scientific verdict.

The mismatch is computational, not a threshold dispute. Primary used Blender `mathutils.Matrix.Rotation`; independent expanded the same Z rotation with `math.sin/cos`. Small float differences propagated through camera projection to roughly `1e-7` area differences. C1 permits the independent tool to use Blender's frozen matrix primitive. It remains a separate implementation of ray traversal, anchors, projection, feasibility and selection.

No candidate, frame, holdout, lens, scale, angle, threshold, ordering or tolerance changes. Primary bytes remain exact. The v0.1 root is immutable; the retry must use v0.2 and re-run both Blender processes from scratch.
