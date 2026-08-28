# B52-D12.10-P1 formal analysis failure

Date: 2026-08-28  
Status: retained formal analysis-tool failure; no P1 verdict promoted  
Real Blender renders: 8 successful source renders

## What completed

All eight preregistered Blender 5.2 Cycles CPU source processes completed with distinct PIDs and exit code zero. Every cell wrote a multipart float32 EXR containing exactly one `Combined`, `Object Index`, `Material Index` and `OwnerToken` part. Source reports passed runtime, scene assignment, pass-state, EXR SHA and self-hash checks. The three tested data-pass arrays were byte-identical across display transforms and clean-process repeats.

## Failure

The frozen analyzer wrote a result and exited one. It reported 8/9 internal checks and 24/24 mutations; the only failed check was `PROJECTION_REPLAY`. The runner retained the formal root and wrote `run.failure.json`; the independent audit was not launched.

The emitted `NO_TESTED_OWNER_TOKEN_PASS_VIABLE` label is invalid as a mechanism verdict because the analytic stable-background mask used the wrong Blender orthographic camera convention.

## Localized defects

### 1. Orthographic view extent was transposed

For this landscape render, Blender's `Camera.ortho_scale = 8` is the visible horizontal width. The correct view extent is:

```text
worldWidth  = orthoScale = 8
worldHeight = orthoScale * renderHeight / renderWidth = 8 * 127 / 193
```

The analyzer instead treated 8 as visible height and expanded the horizontal extent by the aspect ratio. Its foreground mask was therefore much too small. The raw Material Index pass independently exposes the actual foreground rectangle at x `[43,131]` and y `[23,97]`, or 89×75 pixels. Those dimensions match the corrected projection:

```text
3.7 / 8 * 193 ≈ 89.26 pixels
3.1 / (8 * 127 / 193) * 127 ≈ 74.79 pixels
```

Because the erroneous background mask included real foreground, the first F0 cell counted 3,100 Material Index 23 pixels and 3,433 AOV 0.75 pixels as background-token failures. Foreground-interior samples themselves were exact.

### 2. Projection validator encoded an outcome

`projection_ok` required both Material Index and custom AOV to be viable. A projection validator should check measurement and decision consistency for any of the four frozen verdict labels, including a valid negative result. This defect alone made `PROJECTION_REPLAY` false whenever either candidate failed.

## Preserved identities

- Analyzer result SHA-256: `e5916494d80dca03b6ba039817c49ad42a4365e67473f7afdb0ef77c622ae903`
- Analyzer declared evidence hash: `7eb268708ca919b09be301c83ea2c247a11421a8b3e095edf89f157ed3b01326`
- Failure receipt SHA-256: `e6b5f47cf46a61c36acff3ab0a8d3f55c0929e2fe3f43eb22273939f62696591`
- Failure hash: `45eb5d34ed973402b316eb52ed9b550de58b0d2d16739dd60a733a247625733b`
- Execution SHA-256: `effdb704faf3d0324d48a9b2ae4151c718cc4698df1e3d911ad50b1034882dd2`

## Correction boundary

The entire formal root remains immutable. A correction must be preregistered before any new analyzer, audit or output exists. It may only:

1. use the landscape orthographic extent above;
2. make projection validation outcome-neutral while preserving the frozen four-label mapping;
3. read the same eight EXRs and source reports without any new Blender render;
4. emit to a fresh correction root and run an independent raw-EXR audit.

It may not change the scene, samples, margins, token values, pass data, interior minimum, display/repeat requirements or candidate gates.

## Non-claims

- This failure does not establish that either mechanism is viable or non-viable.
- The observed exact foreground values and byte determinism are partial measurements, not a promoted P1 result.
- No D12.9-H1 verdict or temporal reconstruction claim changes.
