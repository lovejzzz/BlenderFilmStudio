# B62-Q1-D1 camera-quality geometric diagnostic protocol

Date: 2026-08-29  
Status before tool creation: **PREREGISTERED**

## Why this diagnostic exists

B62 Phase 0 proved that the asset, timeline, three-camera edit, low-cost animatic, three Cycles calibration renders and independent reopen audit can complete. It did not prove that the shots communicate their intended content. The retained frame `CLOSE_REFLECTION-0240.png` is almost entirely a smooth non-semantic surface, while the WIDE and MEDIUM controls remain visually readable.

The next action is not to move the close camera by eye. D1 first asks a narrower causal question in the real `.blend`: is the close failure explained by a reproducible near-field first-hit obstruction that suppresses the intended semantic anchors?

## Frozen method

Two fresh Blender 5.2 processes open the exact B62 v0.4 master read-only with factory startup and auto-execution disabled. They do not render or save. At frames 48, 144 and 240 they independently:

1. verify the active named camera and record its evaluated optical state;
2. cast a 64×36 pixel-center ray grid through that camera;
3. record the exact first-hit object and distance for every ray;
4. measure the dominant first-hit share, near-field share within 0.5 m, median hit distance and center ray;
5. ray-test the evaluated bounding-box center of visor, eye slit, chest light, right hand and core;
6. project all evaluated character vertices to obtain union bounds and on-screen fraction.

The primary and independent Blender tools are separate files and may not import each other. Their integer rosters must be exact; floating measurements must agree within `1e-9`. A separate Node auditor does not import either runner or Blender tool and validates hashes, process receipts, resource ceilings, the comparison and outcome-neutral verdict mapping.

## Diagnostic signature

The already-observed close failure is localized only if frame 240 simultaneously has:

- one dominant first-hit object covering at least 90% of the grid;
- at least 90% of all grid rays first hitting geometry within 0.5 m of the camera;
- at most one of five exact semantic anchors visible;
- and neither readable control satisfies all three conditions.

These are deliberately diagnosis-specific thresholds selected before reading Blender geometry. They cannot be copied forward as a universal definition of composition or film quality.

## Budgets and fail-closed behavior

The run permits two Blender starts, zero renders, one independent Node auditor, at most 120 seconds and 2 GiB peak RSS per Blender child, at most 64 MiB writes, and at least 100 GiB free-space reserve after projected writes. Model, network, Docker and Colima operations are zero.

Admission is durable before either Blender child starts. The output root is single-use and every partial result remains on failure. A tool, input, runtime, process, resource or output mismatch invalidates the run with no scientific verdict.

## What may happen next

If the diagnostic localizes the obstruction, a separate preregistration may adjust only the close-camera transform/lens using frame 240 as the disclosed derivation frame. That correction must then be tested on uninspected temporal holdout frames across the close shot and must preserve asset, motion, contact, state and edit identities. D1 itself changes nothing and authorizes no full-sequence Cycles render.

Machine-readable contract: `specs/b62-camera-quality-geometric-diagnostic.v0.1.json`.
