# B51-D5 · native CPU data-pass sample/cost derivation protocol

Status: preregistered before D5 renderer, runner, analyzer, audit or output.

Frozen spec: `specs/native-cpu-data-pass-sample-cost-derivation.v0.1.json`, SHA-256 `66f64e05f51c0398c53352eabf5db601c976c672fae7b1244ba3c094f8d713e5`.

## Why H2 cannot start yet

D4-C3 can deterministically merge Metal Combined/Normal/Vector with CPU Depth/Cryptomatte. Its CPU inputs, however, are complete 128-spp Cycles renders. A split path that pays for the unchanged CPU full render and then adds a Metal render cannot support a cost advantage. Before an unseen H2, the CPU data path needs a measured sample floor rather than an assumed one.

## Falsifiable question

Across the known `TABLETOP_WIDE` and `INTERIOR_CHAIR` H1 compositions, is there any sample count below 128 at which native four-thread Cycles CPU reproduces the frozen 128-spp parent's Depth plus all three object Cryptomatte float arrays exactly? What render/process wall-time curve accompanies each dose?

## Frozen matrix

- Variants: `TABLETOP_WIDE`, `INTERIOR_CHAIR` with the exact H1 source identities and operation lists.
- Samples: `1, 2, 4, 8, 16, 32, 64, 128`.
- Repeats: two fresh Blender 5.2 processes for every variant × sample cell.
- Total: 32 native CPU Blender processes and 32 renders.
- Profile: 512×288, fixed seed offset `647647`, four CPU threads, raw Cycles, no denoise, no motion blur, no persistent data, seven-subimage 32-bit ZIP multipart EXR.
- Data domain: Depth plus CryptoObject00/01/02. Combined/Normal/Vector are retained and validated for roster/finite values but cannot determine the data sample floor.

## Decision rule

The derivation is valid only if both new 128-spp repeats reproduce each frozen H1 CPU parent's four data passes exactly; both repeats at every lower dose reproduce each other exactly; all 32 artifacts and operations pass; all 18 attacks reach their intended reason; and independent analysis replay is byte-exact.

`exactDataSampleFloor` is the lowest ladder dose for which both repeats and both variants match all four parent data arrays exactly. A floor below 128 yields `EXACT_CPU_DATA_SAMPLE_REDUCTION_OBSERVED`. If only 128 qualifies, or no lower dose qualifies, the valid negative verdict is `EXACT_CPU_DATA_SAMPLE_REDUCTION_NOT_OBSERVED`. Non-exact lower-dose results are measured but cannot be promoted by an ad hoc tolerance.

## Capacity and safety

The frozen write budget is 128 MiB. Admission requires projected free space to remain at least 100 GiB. Each process uses `--background --disable-autoexec --offline-mode`, an isolated temporary/config/scripts root and a 30-second ceiling. Source `.blend` and parent EXRs are read-only by contract. There are no Metal renders, cache moves, Docker runs, downloads, model calls or video-model calls.

## Interpretation boundary

A lower exact floor on these two known compositions would justify a candidate CPU data profile for a separately preregistered unseen H2; it would not itself prove the profile generalizes. A negative result would mean exact split data has no demonstrated sample-cost saving under this render path. Neither outcome evaluates beauty quality, non-exact Cryptomatte semantics, Depth compositing tolerance, long-sequence thermals or human perception.
