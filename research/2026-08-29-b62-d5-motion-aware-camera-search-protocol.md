# B62-Q1-D5 · Motion-aware camera search protocol

Date: 2026-08-29  
Status: PREREGISTERED — no D5 tool or formal root existed when this protocol was written

## Research question

D4 proved two things simultaneously: the original close camera is catastrophically occluded, and the only static bounded correction found by D3 is not stable across the entire moving shot. The correction passes five of six sealed frames but grows to a clamped character area of 0.933787 at frame 288, above the unchanged 0.90 maximum.

D5 asks one narrower question: can the same −45° azimuth, 65 mm lens and fixed look-at target be retained while radial distance increases smoothly through the shot, compensating for the observed subject-scale growth?

## Frozen candidate family

For every integer frame 193–288, normalized time is `u=(frame-193)/95` and the interpolation weight is `3u²−2u³`. Radial scale moves from a grid-selected start value to a grid-selected end value. Start values are 1.75, 2.0 and 2.25; end values are 2.0, 2.25, 2.5, 2.75 and 3.0; only end ≥ start is admitted, producing exactly 14 candidates.

The source-camera position is transformed around the frozen target with Blender `Matrix.Rotation(-45°, Z)`, multiplied by the current scale, and tracked back to the target with −Z/Y-up. Lens, sensor, shift, clipping and every non-camera scene value remain untouched. The scale path must be monotonic and may change by no more than 0.02 per adjacent integer frame.

## Derivation and holdout separation

Search may use only nine already exposed frames: 193, 204, 216, 228, 240, 252, 264, 276 and 288. The constant-scale baseline `RS_S200_E200` must first reproduce D3 and D4 retained geometry within the frozen exact/tolerance contract. This prevents a new implementation from quietly changing the measurement primitive.

Eight previously unevaluated frames are sealed now: 198, 210, 222, 234, 246, 258, 270 and 282. D5 tools may not project, ray-cast, render or classify them. If D5 finds a candidate, only a later preregistered fresh-scene paired Cycles experiment may unseal those frames.

## Acceptance

The geometry template is byte-for-byte unchanged in meaning from D3/D4: visor and eye must both be visible; helmet blocker ≤0.70; character blocker 0.20–0.90; on-screen vertices 0.10–0.60; clamped area 0.35–0.90; at least two semantic anchors visible.

Two independently authored Blender 5.2 processes must search all 14×9 candidate-frame cells without rendering. Candidate roster, feasibility, selection and discrete evidence must agree exactly; finite floats must agree within 1e-9. Feasible candidates are selected by minimum start deviation from 2.0, then minimum end deviation, mean per-frame deviation and lexical ID.

Finding a candidate supports only `B62_CLOSE_CAMERA_MOTION_AWARE_BOUNDED_CANDIDATE_FOUND`. It does not promote a camera or authorize final rendering. Finding none yields the equally valid scientific rejection `B62_CLOSE_CAMERA_MOTION_AWARE_BOUNDED_CANDIDATE_NOT_FOUND`.

## Operation boundary

The formal experiment permits two Blender starts, one Node auditor, zero render/model/network/Docker calls, at most 128 MiB projected writes and a 100 GiB free-space reserve. Any sealed-frame access, scene save, candidate omission, baseline mismatch or independent disagreement invalidates the run rather than changing the family or threshold.
