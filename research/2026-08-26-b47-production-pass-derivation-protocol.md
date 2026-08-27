# B47-D1 — worker production-pass pack derivation protocol

Date: 2026-08-26

Status: frozen exploratory derivation; no promotion verdict

## Question

What multipart OpenEXR structure does the B44 TABLETOP scene actually produce in the pinned Blender 5.2 Linux/amd64 Cycles CPU worker when its compiled production passes are preserved at the B46 frame and cost scale?

## Frozen probe

- source: B44 `TABLETOP-A1` `.blend`, SHA-256 `9c4f9cc26e213c0b4de0462f7ad6878cabf27a2204ec1448e98e93aed36bd1f0`;
- frame: 22;
- worker and containment: the B46 pinned Linux/amd64 image and container contract;
- render: Cycles CPU, 128×72, 8 samples, compiled shot seed, animated seed off, denoise off, motion blur off, persistent data off and four fixed threads;
- enabled output passes: Combined, Depth, Normal, Vector and Object Cryptomatte at depth 6 with accurate mode retained;
- output: one RGBA32 ZIP `OPEN_EXR_MULTILAYER` saved from one Render Result;
- host inspection: Blender 5.2 bundled Python, OpenImageIO 3.1.13.1 and NumPy; enumerate multipart names/channels/attributes, canonical float32 pass hashes, finite/NaN/infinity counts and non-zero component counts.

The probe writes to `experiments/codex-worker-production-pack-derivation-v0-1/`. Its renderer and analyzer must be committed before execution. The result may choose B47's formal pass roster, non-finite policy and semantic controls, but it cannot pass B47 or prove production readiness.

## Questions the derivation must answer

1. Which multipart subimages and channel names are actually serialized?
2. Does Depth contain infinity for background, requiring a pass-specific non-finite rule?
3. Does the moving-camera Vector pass contain non-zero values while motion blur is disabled?
4. Which Cryptomatte metadata and object IDs are present?
5. Are all production passes small enough to support a multi-container formal pair experiment within the existing disk reserve?

## Non-claims

This one-file probe does not test A/B reproducibility, a static control, temporal pass semantics, motion blur, denoising, sample quality, 4K, throughput, perceptual quality or a complete shot. Any formal threshold must be written only after this output is inspected and before the B47 formal renderer is implemented.
