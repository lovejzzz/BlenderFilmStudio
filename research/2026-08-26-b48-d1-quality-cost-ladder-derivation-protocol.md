# B48-D1 — Cycles CPU quality/cost ladder derivation protocol

Date: 2026-08-26

Status: exploratory protocol frozen before renderer or analyzer implementation

## Question

B47 established a reproducible seven-subimage production pack, but it held image quality at 128×72, eight samples, denoising off and motion blur off. B48-D1 asks how numerical distance to a high-sample reference and measured worker time change when sampling and Blender's production denoiser are varied while the source scene, frame, seed, resolution, renderer, CPU allocation, OCIO configuration and EXR representation remain fixed.

## Frozen source and runtime

- Source: B44 `TABLETOP-A1` `.blend`, SHA-256 `9c4f9cc26e213c0b4de0462f7ad6878cabf27a2204ec1448e98e93aed36bd1f0`.
- Frame: 22.
- Worker image: `sha256:c4b0f6bebe77e9bd10b4875aaf0500d798de081259397c525f923f7a9eea35b1`.
- Blender: 5.2.0 LTS Linux/amd64, Cycles CPU, four fixed render threads.
- Resolution: 128×72.
- Seed: the source `bfs_shot_seed`, animated seed disabled.
- Motion blur and persistent data: disabled.
- Output: RGBA32 ZIP `OPEN_EXR_MULTILAYER` with the B47 Combined, Depth, Normal, Vector and Object Cryptomatte pass contract.
- Container: network none, read-only root, repository read-only, dedicated writable output mount, dropped capabilities and no-new-privileges.

## Frozen cells and execution order

One exploratory container opens the source once and renders these cells in this exact order:

1. `S008_RAW`: 8 spp, denoising off.
2. `S008_OIDN`: 8 spp, OpenImageDenoise on, `RGB_ALBEDO_NORMAL`, accurate prefilter.
3. `S032_RAW`: 32 spp, denoising off.
4. `S032_OIDN`: 32 spp, the same denoiser settings.
5. `S128_RAW`: 128 spp, denoising off.
6. `S128_OIDN`: 128 spp, the same denoiser settings.
7. `S512_REFERENCE`: 512 spp, denoising off.

The single-process ordered design is deliberately cheap and suitable only for deriving metrics and candidate thresholds. It confounds cell with render order and warm state. Any formal B48 promotion must use fresh workers and a frozen order/randomization policy.

## Frozen measurements

For every cell, record Blender render-operator wall time, total cell save time, EXR byte size, file SHA-256 and canonical Combined float32 SHA-256. Reopen every EXR with the worker-bundled OpenImageIO and reject missing/non-finite Combined data.

Compare RGB values against `S512_REFERENCE` using:

- scene-linear RMSE and RMSE normalized by reference RMS;
- scene-linear MAE, p95 absolute error and maximum absolute error;
- log-luminance RMSE using `log2(1 + max(Y, 0))` and ACEScg/AP1 luminance coefficients;
- edge-region RGB RMSE on the top 10% of reference luminance-gradient pixels, selected by exact top-k rather than a tied quantile threshold;
- render-time ratio and EXR-byte ratio relative to `S008_RAW`.

No perceptual, cinematic or economic threshold is frozen in D1. The output is descriptive. It may identify non-monotonic behavior, and that result must be retained.

## Non-claims

B48-D1 cannot establish a production operating point, human preference, denoiser temporal stability, motion-blur quality, depth-of-field quality, 2K/4K behavior, GPU behavior, native x86 throughput, cross-host reproducibility, cloud cost or complete-shot cost. A 512-spp image is a numerical reference for this bounded frame, not ground truth and not proof of artistic quality.

## Stop conditions

Stop without a quality conclusion if the source or runtime identity differs, a cell fails, a Combined pass is absent or non-finite, the output root is non-empty, an unexpected extra container is required, or the 100 GiB host-disk reserve would be violated.
