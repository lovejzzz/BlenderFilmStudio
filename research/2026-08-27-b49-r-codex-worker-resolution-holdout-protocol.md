# B49-R — preregistered 512×288 cross-scene resolution holdout

Date: 2026-08-27

Status: preregistered before formal renderer, runner, analyzer or audit

## Question

B49-D1 observed a render-time pixel exponent of 0.980–0.990 through 384×216 on TABLETOP. B49-R asks whether the B48-selected 128-spp raw operating point remains approximately pixel-linear at an unseen 512×288 point—16× the B48 pixel count—and whether that relation holds on both TABLETOP and INTERIOR.

## Formal cells

Exactly two fresh Blender 5.2 Linux/amd64 Cycles CPU workers render the already frozen B48 holdout frames:

- TABLETOP frame 37 at 512×288.
- INTERIOR frame 19 at 512×288.

Both use 128 spp raw, the B48 candidate seed offset 647647, four fixed threads, motion blur off, denoising off, persistent data off, the fixed ACES 2 OCIO configuration and the B47 seven-subimage multipart EXR pack. Each writes to a new empty output root under the established network-none, read-only, non-root, capability-dropped worker boundary.

## Frozen gates

Each shot is compared with its already committed B48 128×72 selected-cell baseline. With a pixel ratio of exactly 16:

- effective render-time exponent must be in [0.95, 1.05];
- effective EXR-byte exponent must be in [0.75, 1.05];
- self-reported process peak RSS must not exceed 2,097,152 KiB;
- the output must be 512×288, finite float32 Combined, and exactly the seven raw production subimages;
- source, scene, plan, structure, seed, samples, runtime, image, OCIO, containment, operation count and disk reserve must match the spec.

The exponent interval was frozen from D1 before the 512×288 outputs existed. Failure on either scene rejects the cross-scene scaling hypothesis; the interval cannot be widened after observation.

## Projection boundary

If the holdout passes, the analyzer may calculate labelled 2K and 4K model projections using each shot's committed 128×72 render time and an exponent uncertainty band [0.95, 1.05]. It reports per-frame and 240-frame ranges. These numbers must carry both labels `MODEL_PROJECTION_NOT_MEASURED` and `CURRENT_QEMU_CPU_WORKER_ONLY`.

No projected value may be called a measured 2K/4K render, a cloud price or a complete-shot run. Dollar cost is forbidden. The wide band is part of the result, not an inconvenience to hide.

## Promotion

B49-R passes only when both real workers complete, every representation/resource/exponent gate holds, all 15 frozen attacks reject for their declared reason, no experiment container remains, and an independent audit reopens both EXRs and byte-exactly replays the analyzer result.

Passing establishes a bounded cross-scene resolution-scaling model through 512×288 on the current CPU/qemu worker. It does not establish human cinematic quality, motion blur, depth of field, complex character/texture memory, GPU behavior, native x86/cloud throughput or dollar cost. Those remain separate next interventions.
