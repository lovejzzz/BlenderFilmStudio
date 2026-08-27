# B51-D6 · native CPU data-pass semantic-equivalence derivation protocol

Status: preregistered before the D6 analyzer, audit or output is implemented or executed.

Frozen spec: `specs/native-cpu-data-pass-semantic-equivalence-derivation.v0.1.json`, SHA-256 `db821a92a7ba35546217e20208f7ed39296fcabdd5a28972d7a71da8f1b1cc2d`.

## Why D6 exists

D5 produced a valid negative exactness result: only 128 spp reproduced the frozen CPU Depth and three object-Cryptomatte float arrays exactly. That makes a full 128-spp CPU data render plus a Metal beauty render an additive cost, not a demonstrated saving. Raw float inequality, however, does not by itself answer whether the decoded masks and task-relevant depth remain operationally equivalent. D6 tests that narrower claim without rendering again.

## Normative decoding

The Blender 5.2 manual describes each numbered Cryptomatte image as two ranked object contributions per pixel. The Cryptomatte 1.2.0 specification fixes the channel order as ID/coverage pairs: `00.r/g`, `00.b/a`, then the same pattern in `01` and `02`. It also fixes `MurmurHash3_32`, `uint32_to_float32`, little-endian ID representation, normalized coverage and descending coverage rank.

D6 therefore never compares Cryptomatte ID floats numerically. It compares their 32-bit payloads, decodes the manifest's eight-digit hex IDs, and reconstructs each object matte by summing coverage for matching IDs across all six ranks. Zero-coverage IDs are ignored.

Normative sources:

- Blender 5.2 LTS Manual, [Render Layers / Passes](https://docs.blender.org/manual/en/latest/render/layers/passes.html).
- Psyop, [Cryptomatte Specification 1.2.0](https://raw.githubusercontent.com/Psyop/Cryptomatte/master/specification/cryptomatte_specification.pdf), frozen PDF SHA-256 `43b85ea8d611ad9c7dbbd557519f71a335f16179d25e45066309e67ad1584af1`.

## Frozen input matrix

- Reuse all 32 retained D5 EXRs: two compositions × eight sample doses (`1, 2, 4, 8, 16, 32, 64, 128`) × two exact same-dose repeats.
- Use each variant's `S128_R1` as the semantic reference; D5 already proved both new 128-spp repeats exactly reproduce their frozen H1 CPU parent.
- Verify every EXR against the D5 receipt before reading measurements.
- Perform zero new Blender processes, zero renders and zero EXR writes.

## Cryptomatte production-semantic profile

Every input must retain the frozen metadata key, name, hash, conversion and per-variant manifest. Ranked coverage must be finite, within `[0, 1]`, non-increasing, free of duplicate nonzero IDs and sum to at most `1 + 1e-6`; every nonzero ranked ID must resolve through the manifest.

For every object visible in the 128-spp reference:

- the binary matte at alpha `0.5` must have zero mismatched pixels;
- parent-confident pixels, whose dominant coverage is at least `0.5`, must have zero dominant-ID mismatches;
- maximum matte alpha error must not exceed one 8-bit code (`1/255`);
- p99 matte alpha error must not exceed one 10-bit code (`1/1023`);
- whole-frame matte RMSE must not exceed one 12-bit code (`1/4095`).

These thresholds are an explicit BlenderFilmStudio production profile, not a proposed universal Cryptomatte standard.

## Depth production-semantic profile

Values at or above `1e9` are classified as background sentinel. Candidate and parent foreground masks must be pixel-exact. Numeric depth is evaluated only on stable surfaces: parent foreground pixels whose dominant Cryptomatte coverage is at least `0.999` and whose candidate dominant ID agrees with the parent. This excludes mixed-object antialiasing boundaries where a single Z value is not a stable object-depth statement.

On stable surfaces, p99 absolute error must be at most `0.001 m`, maximum absolute error at most `0.01 m`, and p99 relative error at most `1e-4`.

## Decision rule

The semantic sample floor is the lowest dose at which both repeats of both variants pass every frozen Cryptomatte and Depth threshold. A floor below 128 yields `CPU_DATA_SEMANTIC_SAMPLE_REDUCTION_OBSERVED`; otherwise the valid negative verdict is `CPU_DATA_SEMANTIC_SAMPLE_REDUCTION_NOT_OBSERVED`.

Validity additionally requires all D5 bindings and 32 artifacts to retain identity, 128-spp references and same-dose repeats to retain exactness, every measurement cell to be present, all 16 attacks to reach their intended reason, and an independent analyzer replay to be byte-exact. No threshold may be adjusted after observing D6 results.

## Interpretation boundary

A positive result would identify a known-scene candidate dose for a separately preregistered unseen H2. It would not promote split rendering by itself. A negative result would close the current low-sample split-backend cost hypothesis and retain Metal as a preview/beauty-only acceleration path. D6 does not claim unseen-scene, motion-blur, transparency, depth-of-field, 2K/4K, long-sequence or human-perceptual generalization.
