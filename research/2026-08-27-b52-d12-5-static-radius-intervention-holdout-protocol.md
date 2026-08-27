# B52-D12.5 static owner-erosion radius intervention holdout protocol

Date: 2026-08-27

Status: preregistered before formal tools or output

## Why this experiment exists

D12.3 supported the unchanged static reconstruction tolerance inside same-owner regions, but one occluding-plane sample landed exactly on the inclusive RGB-maximum gate. D12.4 replayed that sample without new renders: it was the unique global maximum, lay at Chebyshev silhouette distance 3 and combined a `-2^-17 px` horizontal Vector residue with large same-owner blue-channel contrast. Filtering the already observed arrays to distance 4 or greater left a cross-fixture maximum equal to 25% of the gate.

That observation makes erosion radius 3 a plausible intervention. It is not validation. D12.5 freezes the intervention and its failure conditions before any new fixture is rendered.

## Fresh paired design

Three new opaque static multi-owner fixtures use fresh rasters, optics, transforms, pass indices, topology and procedural material parameters:

1. a wavy rear panel occluded by a beveled triangular wedge at `109×67`;
2. a stretched rear sphere occluded by a tilted foreground ring at `137×89`;
3. a rear icosphere crossed by two independently owned beveled rods at `149×97`.

Each fixture has two fresh repeats and two rendered frames, for twelve real Blender 5.2 Cycles source renders. The exact same adapted source arrays feed radius 2 and radius 3. Radius is therefore a paired consumer intervention, not a render confound.

## Control and intervention

The radius-2 control is the D12.3 owner-interior rule: current owner and alpha must remain valid throughout a Chebyshev-radius-2 neighborhood; all four previous bilinear taps must have that same owner and opaque alpha.

The radius-3 intervention changes only the current-owner erosion neighborhood to radius 3. Reconstruction arithmetic, source arrays, previous-tap checks, numeric thresholds and fail-closed boundary behavior do not change. Every radius-3 interior pixel must be a radius-2 interior pixel. Every radius-2-only pixel must be on silhouette-distance ring 3.

Radius 2 is not required to fail. It is a paired control that estimates what the intervention changed.

## Frozen numeric and coverage gates

The D12.2 production tolerance remains unchanged for radius 3:

- Vector component maximum ≤ `1/4096 px`;
- reconstruction RGB maximum ≤ `1/524288`;
- reconstruction RGB RMSE ≤ `1/1048576`.

The confirmatory intervention claim is intentionally stronger than mere tolerance. Every radius-3 cell must keep RGB maximum ≤ `1/1048576`, giving at least twofold headroom beneath the production maximum gate.

Success cannot be bought by masking most of the image. Per cell, radius 3 must retain at least 800 interior pixels and at least 80% of radius-2 total interior coverage. Every registered owner must retain at least 64 radius-3 pixels; owners with at least 100 radius-2 pixels must retain at least 60%. Both radii must expose at least 50 rejected boundary pixels.

## Outcomes

`RADIUS3_INTERVENTION_SUPPORTED_WITH_REGISTERED_HEADROOM_AND_COVERAGE` requires every identity, subset, ownership, static-source, production-tolerance, twofold-headroom, coverage and attack gate to pass in all six fresh cells.

If radius 3 remains inside the unchanged production tolerance but misses the stronger headroom or coverage requirement, the bounded outcome is `RADIUS3_WITHIN_PRODUCTION_TOLERANCE_BUT_HEADROOM_OR_COVERAGE_NOT_SUPPORTED`.

Any radius-3 production-tolerance, identity, ownership, subset, execution or audit-totality failure yields `RADIUS3_INTERVENTION_NOT_SUPPORTED`.

No threshold or coverage floor may be revised after output inspection.

## Evidence and process boundary

The formal matrix contains twelve Blender renders, six adapters, twelve dual-radius consumers, twenty-four typed-envelope encoders and one independent analyzer: exactly 55 unique child processes. Python and Node must emit byte-identical reconstruction and mask payloads; both frozen typed-envelope implementations must agree per document; the analyzer must recompute decisions from arrays without trusting producer metrics. At least thirty registered mutation attacks must pass.

The single-use formal root is `experiments/blender-static-radius-intervention-holdout-v0-1`. The preflight root, formal root and all seven formal tool paths were absent at preregistration. A 20 MiB projected write must leave the unchanged 100 GiB disk reserve. Model and network calls are zero.

## Non-claims

D12.5 cannot revise D12.3, establish Blender's undocumented internal mechanism or authorize reuse across owner boundaries. Even a supported result would apply only to these opaque static owner interiors. Motion, deformation, transparency, hair, particles, volumes, motion blur, disocclusion, perceptual quality, cinematic quality and render throughput remain outside this test.

Machine-readable contract: `specs/blender-static-radius-intervention-holdout.v0.1.json`.
