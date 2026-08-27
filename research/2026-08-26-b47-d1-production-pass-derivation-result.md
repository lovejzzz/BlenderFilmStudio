# B47-D1 — real worker multipart production-pass derivation result

Date: 2026-08-26

Status: exploratory derivation complete; no B47 promotion verdict

Tool-freeze commit: `ade1000d528f4194693f190fa2a9c3e0e3a5da9f`

## Observation

One pinned Blender 5.2 Linux/amd64 Cycles CPU worker opened the frozen B44 `TABLETOP-A1` `.blend`, verified its source/plan/SceneSpec/structure/OCIO bindings, rendered frame 22 at the B46 128×72, 8-sample control and saved one RGBA32 ZIP multipart OpenEXR. The EXR SHA-256 is `b4e8491a2964ba115404669b68143216db1156630ae35858715e10b0d1dc1b45` and its size is 242,603 bytes.

Blender 5.2's bundled Python 3.13.13, OpenImageIO 3.1.13.1 and NumPy 2.3.4 decoded seven float subimages:

1. `BFS_MASTER.Combined` — RGBA, all 36,864 components finite;
2. `BFS_MASTER.Depth` — Z, all 9,216 components finite, range 6.8897614 to exactly `1e10`;
3. `BFS_MASTER.Normal` — XYZ, all finite, range -1 to 1;
4. `BFS_MASTER.Vector` — XYZW, all finite, 32,244 non-zero components even though motion blur was disabled;
5. `BFS_MASTER.CryptoObject00` — RGBA float identity/coverage pairs;
6. `BFS_MASTER.CryptoObject01` — RGBA float identity/coverage pairs;
7. `BFS_MASTER.CryptoObject02` — RGBA float identity/coverage pairs, zero for this frame.

No subimage contained NaN or infinity. Depth therefore needs no permitted-Inf exception at this boundary, but `1e10` must be treated as Blender's observed far-background sentinel rather than a measured scene distance.

The Cryptomatte attributes declared `MurmurHash3_32`, `uint32_to_float32`, the layer name `BFS_MASTER.CryptoObject` and a parseable manifest containing the scene mesh names plus visible camera/light objects. Cryptomatte identity floats have very large signed numeric magnitudes; formal validation must interpret the manifest and pair layout, not treat the ID lanes as ordinary color magnitudes.

## Formal B47 implications

The formal experiment can freeze exactly seven subimages and their channel layouts, require float32 canonical pass hashes, require all components finite, constrain Normal to [-1,1], require non-zero TABLETOP Vector content, verify Cryptomatte algorithm/conversion/manifest semantics and compare every subimage across B44 A/B builds. Two frames per scene allow a moving-camera temporal check and a static-control temporal check without yet changing samples, denoising or motion blur.

Quality interventions should remain a separate B48 experiment. B47 should first establish that the production representation itself is complete, semantically interpretable and reproducible.

## Artifacts

- `research/2026-08-26-b47-production-pass-derivation-protocol.md`
- `experiments/codex-worker-production-pack-derivation-v0-1/production-pack.exr`
- `experiments/codex-worker-production-pack-derivation-v0-1/render.report.json`
- `experiments/codex-worker-production-pack-derivation-v0-1/inspection.json`
