# B52-D1 · native CPU adaptive quality–cost derivation protocol

Status: preregistered before the B52-D1 renderer, runner, analyzer, audit or formal output.

Frozen spec: `specs/native-cpu-adaptive-quality-cost-derivation.v0.1.json`, SHA-256 `b327ffebdcd0e959a9ca612401ac9aaaaae05bafdba159de6225ac828e2ebcca`.

## Why this replaces H2

B51-D5 found an exact CPU data floor of 128 spp. B51-D6 then decoded Cryptomatte mattes and task-relevant Depth, but the production-semantic floor also remained 128 spp. A split route would therefore pay for a complete CPU data render, then add Metal beauty and merge work. Its cost hypothesis is closed.

B52-D1 tests a different mechanism inside the one backend that already owns the complete production contract: Cycles adaptive sampling on native CPU. Blender's manual states that adaptive sampling stops refining pixels whose estimated noise is below a threshold, while Min Samples delays that decision. The official Sample Count pass reports samples per pixel divided by max samples and makes the intervention directly observable.

Sources:

- [Blender 5.2 Sampling](https://docs.blender.org/manual/en/latest/render/cycles/render_settings/sampling.html)
- [Blender 5.2 Render Passes](https://docs.blender.org/manual/en/latest/render/layers/passes.html)
- [Cycles sampling implementation](https://developer.blender.org/docs/features/cycles/sampling_patterns/)

## Real-Blender RNA preflight

The first zero-render probe incorrectly guessed `view_layer.use_pass_debug_sample_count` and raised `AttributeError`. The corrected Blender 5.2 scope is `view_layer.cycles.pass_debug_sample_count`. The failure is retained at `experiments/native-cpu-adaptive-quality-cost-rna-probe-failure-v0-1/failure.json`; neither probe opened a `.blend` or rendered a frame.

The corrected probe also froze the installed defaults: adaptive enabled, threshold approximately `0.01`, min samples `0`, max samples `4096`, denoising enabled. Formal cells override every relevant value explicitly and keep denoising off.

An 8×8, 4-spp factory-startup micro-render then confirmed that the property creates a one-channel `<view-layer>.Debug Sample Count` EXR subimage. Its normalized values were all `1.0`; this only validates API/roster wiring, not adaptive savings. The temporary 1,671-byte EXR was discarded after its SHA and decoded observation were retained at `experiments/native-cpu-adaptive-quality-cost-preflight-v0-1/observation.json`.

## Frozen matrix

Reuse the exact two D5 compositions and operations at 512×288 on native four-thread CPU.

- Three independent fixed 512-spp raw references per variant, using the validated B48 seed offsets `314159`, `424243`, `535529`.
- Six 128-spp profiles per variant, two fresh-process repeats each: fixed control; automatic threshold/min 0; threshold `0.01` with min 0/32; threshold `0.001` with min 0/32.
- Candidate seed offset remains `647647`, so the new fixed control must reproduce D5's frozen seven data/image passes exactly.
- Total: 30 fresh Blender 5.2 CPU processes and 30 renders.
- Output: the seven production subimages plus `BFS_MASTER.Debug Sample Count`, float32 ZIP multipart EXR.

## Passing one adaptive profile

All requirements are conjunctive on both variants and both repeats:

1. Beauty remains within 3× the local three-reference floor for linear NRMSE, log-luminance RMSE and top-10%-edge RMSE.
2. Depth and decoded Cryptomatte pass the exact D6 production-semantic thresholds.
3. Normal and Vector remain float32-exact to the same-seed fixed 128 control.
4. Sample Count is finite, in `[0,1]`, shows at least one adaptively stopped pixel and reports its full distribution.
5. Median render-operator time improves at least 20% relative to fixed 128.
6. Same-cell repeats are exact across all eight decoded parts, all identities and settings pass, all 20 attacks reach their intended reason, and independent replay is byte-exact.

The selected profile is the passing adaptive profile with lowest cross-variant median render time. If none qualifies, the valid negative verdict is `NATIVE_CPU_ADAPTIVE_PRODUCTION_POINT_NOT_FOUND`; thresholds will not be relaxed after observation.

## Capacity and interpretation

The formal write budget is 256 MiB and free space after projection must remain at least 100 GiB. Each Blender process has a 60-second ceiling, uses CPU only, no persistent data, no network, no denoising and an empty per-cell output directory. Source `.blend` and parent EXRs are identity-bound and read-only.

A positive known-scene result would justify a separately preregistered unseen holdout, not production promotion. A negative result would mean that this strict complete-pass profile did not find an adaptive CPU discount. It would not reject adaptive sampling for preview, beauty-only, denoised, character, 2K/4K or human-perceptual uses.
