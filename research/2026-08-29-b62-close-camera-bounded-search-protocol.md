# B62-Q1-D3 bounded close-camera search protocol

Date: 2026-08-29  
State: **PREREGISTERED before tool creation**  
Purpose: find whether a small, explicit camera intervention family can remove the D2 failure without rendering or touching later holdout frames.

## Intervention family

The original CLOSE camera is evaluated only at frames 216, 240 and 264. Relative to its frozen look-at target `(0, 0.67, 1.72)`, D3 crosses eight world-Z azimuth rotations, three radial distance scales and four lenses: 96 candidates. Each candidate continues to look at the same target. No asset, rig, action, light, material, world, render setting or other camera may change.

The grid includes the original `(0°, 1.0×, 100 mm)` as a negative baseline. Frames 193, 204, 228, 252, 276 and 288 are sealed; D3 tools may not set or measure them. They are reserved before any candidate result exists.

## Engineering feasibility, not taste

At all three derivation frames a candidate must expose both visor and eye-slit anchors, keep helmet blockers at or below 70%, keep character blockers between 20% and 90%, place 10%–60% of evaluated character vertices on screen, keep clamped character bounds between 35% and 90% of frame area, and show at least two of five semantic anchors. The original baseline must fail.

These bounds define a restrained close-shot template and negate the already measured extreme state. They are normative engineering constraints, not audience-derived evidence. Among feasible cells, the winner is chosen first by smallest normalized intervention, then semantic visibility, helmet share, face visibility and candidate ID. D3 can nominate a candidate for rendering; it cannot approve a shot.

## Reproducibility boundary

Two unrelated Blender Python implementations must each search all 288 candidate-frame cells using 32×18 material-aware rays, exact anchor traces and evaluated character projection. Candidate roster, integers and selection must match exactly; floats use `1e-9`. The budget is two Blender starts, zero renders, zero model/network/Docker calls, and 128 MiB projected evidence. Any holdout access or traversal exhaustion invalidates the run.
