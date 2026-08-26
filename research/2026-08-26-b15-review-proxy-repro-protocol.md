# B15 same-source review-proxy reproducibility protocol

Date frozen: 2026-08-26, before implementing the sequence comparator and before rendering run B.

Status: **EXECUTED / FORMAL EXACT FALSIFIED**

## Triggering observation

B14 required three candidate full-sequence runs because inspection changed the OCIO assertion and then removed local absolute paths from public evidence. Their sequence hashes differed, but tool identity changed between candidates. That observation cannot establish nondeterminism. A controlled same-source A/B comparison is required.

## Question and primary hypothesis

When the exact B14 ReviewRenderSpec, receipt-bound `.blend`, Blender/OCIO runtime and `blender/render_review_sequence.py` bytes are held constant, do two clean 144-frame Eevee proxy renders produce:

1. byte-identical PNG files; and
2. pixel-identical decoded RGBA images?

The primary exact-pixel hypothesis is frozen at `maxAbsoluteError = 0`, `failurePixels = 0` for every frame. The threshold will not be relaxed after observing the result. If it fails, B15 is formally completed as a falsification, and any later bounded-tolerance policy must be separately pre-registered.

## Frozen run-A identity

- source B14 evidence hash: `c5fb0c835c4d0d70172e7aca40e8f97078e721d3144c3486cb102bb6c083380c`;
- A sequence hash: `a52903fc327139ae41ed08f2d257d704b7977e9fda060138b106ceb56dbd56e4`;
- A sequence-manifest file SHA: `c86cc14940a4d82771c72052c5bac69c2ab4ebef709f76fe56cbf2d7af24122b`;
- A render-report file SHA: `5c82a375a260e5574fa8de8f27c5fb1547e9dfbffd3f90835a9153c22dd8c73a`;
- renderer SHA: `b969e267db7b73eb7b6f8ea17abf09b2e129b9fce2e706fec950c5bb5e5eda5c`;
- ReviewRenderSpec SHA: `65db6ca29fc1deb6c6e6b3927152794ca14ca09cbcc921db912fc2b5aecd9553`;
- B02 scene, receipt, Blender binary and OCIO identities remain exactly those frozen by B14.

Run A is the still-present B14 local formal sequence. The B15 runner must verify every A PNG against the tracked B14 sequence manifest before launching run B.

## Frozen positive/control gate

1. B14 evidence and its complete local A sequence pass `verify-review-dailies` before run B.
2. Renderer, spec, receipt, `.blend`, Blender binary and OCIO hashes match the frozen identities.
3. Run B starts in a missing or empty directory and uses the same Blender command except for output/report destinations.
4. Run B produces exactly `frame-0001.png` through `frame-0144.png` and its own self-hashed manifest.
5. A and B names, dimensions and RGBA channel layouts match for all 144 frames.
6. PNG byte equality is reported per frame and as an exact count; it is not assumed.
7. Blender-bundled OpenImageIO decodes and compares all 144 pairs with zero warning and failure thresholds, recording mean, RMS, maximum absolute error, failure count and largest-difference coordinates.
8. The result explicitly classifies `CONTAINER_EXACT`, `DECODED_PIXEL_EXACT`, or `DECODED_PIXEL_DIFFERENT` without hiding a weaker outcome.
9. Frames 1, 72 and 144 receive full comparison records; aggregate extrema identify the worst observed frame.
10. Exact runtime/tool identities, timings and machine-readable comparison artifacts are retained.

## Frozen negative matrix

Copied/disposable artifacts will exercise at least these eight checks:

1. `N_A_MANIFEST_SHA`: altered frozen A manifest identity;
2. `N_RENDERER_SHA`: altered renderer identity;
3. `N_A_MISSING_FRAME`: missing A frame;
4. `N_B_MISSING_FRAME`: missing B frame;
5. `N_B_EXTRA_FRAME`: extra B frame 145;
6. `N_A_FRAME_SHA`: A bytes no longer match the B14 manifest;
7. `N_B_FRAME_SHA`: B bytes no longer match the B manifest;
8. `N_ALIAS_RUNS`: A and B resolve to the same directory.

Each attack must fail with its intended stable reason. Authoritative B14 evidence and sequences are never modified.

## Decision rule

- `FORMAL EXACT TRUE`: all controls and attacks pass, 144/144 PNG byte pairs match and 144/144 decoded image pairs have zero error.
- `FORMAL PIXEL TRUE / CONTAINER FALSE`: all controls and attacks pass, decoded pixels are exact but one or more PNG byte hashes differ.
- `FORMAL EXACT FALSIFIED`: all controls and attacks pass but one or more decoded image pairs differ.
- `INVALID EXPERIMENT`: a control/identity/attack gate fails.

Falsification is a completed scientific result, not a failed task.

## Post-freeze execution notes

The first launch failed before Blender because `realpath` came from the wrong Node module. A later complete candidate remained invalid because two SHA fixtures used a temporary `.png` name and triggered the extra-frame gate first (6/8 attacks). After changing only the fixture extension to `.tmp`, run B and comparison were regenerated. The authoritative experiment passed 8/8 attacks and falsified exact decoded equality: 127/144 exact frames, 114 failed pixels, maximum channel error `0.003921583294868469`.

## Explicit non-claims

- Exact 8-bit Eevee proxy behavior does not establish Cycles EXR or master-render behavior.
- Same-machine results do not establish cross-device or cross-version behavior.
- Pixel equality does not prove cinematic quality; pixel difference does not by itself imply a visible defect.
- No perceptual threshold is selected in B15.
- PNG byte mismatch can come from pixels or container metadata; only decoded comparison distinguishes them.
