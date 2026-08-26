# Blender 5.2 Eevee reproducibility control inventory

Executed: 2026-08-26 against the receipt-bound B02 `.blend` with real Blender 5.2.0 LTS build `fbe6228777e7`.

Classification: **EXPLORATORY RNA AUDIT — NOT A CAUSAL RESULT**

## Why this audit exists

B18 produced a non-monotonic exactness vector `[F,T,F,F,F,F]` across samples 1/2/4/8/16/32, while maximum error generally shrank as sample count increased. Before choosing another intervention, this audit enumerates the controls actually exposed and enabled in the exact B02 scene.

## Valid identity

- source `.blend` SHA-256: `2a5053601cbd98d7b404069454ff7b2b710aa885541c4972b5d3f6c216511b0b`;
- OCIO SHA-256: `24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15`;
- loaded OCIO name: `cg-config-v4.0.0_aces-v2.0_ocio-v2.5`;
- inventory script SHA-256: `fa19043eb6e5f252dd8ca077782ac2b6d7458f813b7e0fff50f2bd24c11137b0`;
- result SHA-256: `abab0692823d13741ab9ff77fd67b904bcbc32b9b41d1f99af8c47a5068b1115`.

## Measured controls

### Enabled candidates

- `scene.eevee.use_fast_gi = true`;
- `fast_gi_ray_count = 2` and `fast_gi_step_count = 8`;
- `scene.eevee.use_taa_reprojection = true`, described by Blender RNA as temporal-reprojection denoising;
- source `taa_render_samples = 64`, overridden by the frozen renderer to each experiment's sample level;
- `scene.render.threads_mode = FIXED`, `threads = 8`;
- `scene.render.dither_intensity = 1.0`, already isolated by B16/B17.

### Disabled or weaker candidates

- Eevee ray tracing module: `use_raytracing = false`;
- camera bokeh jitter: `use_bokeh_jittered = false`;
- the only area light, `KEY_WINDOW_DATA`, has `use_shadow_jitter = false`;
- renderer motion blur is disabled by ReviewRenderSpec;
- volumetric shadows are disabled;
- no property whose identifier exposes a clear render `seed` or `random` control was found in the matched SceneEevee/RenderSettings/Light RNA.

Blender RNA notes that viewport shadow jitter is separate and jittered shadows are enabled for final renders, but the only light's own shadow-jitter switch is false. Property presence and descriptions do not prove runtime causality.

## Invalid attempts retained

1. The first run used a relative OCIO path and assumed every RNA property exposed `is_array`. Blender could not load OCIO and the script raised on an EnumProperty. No result was accepted.
2. The second run fixed RNA access but pointed OCIO to a nonexistent absolute path. The script exited zero while Blender logged an OCIO error and loaded fallback color management. That candidate was rejected despite its successful exit code.
3. The accepted run used the exact receipt URI and SHA, verified the loaded config name, and removed the local absolute scene path from the artifact.

## Next intervention

The strongest enabled candidates are Fast GI sampling and TAA temporal reprojection. A 2×2 B19 factorial at 32 samples/dither 0 can compare Fast GI on/off × TAA reprojection on/off in the same batch. It should include a fresh on/on baseline and two full sequence replicates per cell. Possible outcomes must distinguish single-factor support, joint/interaction support, no sufficient intervention and baseline instability.

The inventory cannot prove that either control caused B15–B18 differences; it only justifies which variables are tested next.

