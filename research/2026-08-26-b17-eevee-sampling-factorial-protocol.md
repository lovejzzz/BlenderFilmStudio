# B17 Eevee sampling × output-dither factorial protocol

Date frozen: 2026-08-26, before implementing the B17 configurator/runner and before rendering any B17 sequence.

Status: **PRE-REGISTERED / NOT EXECUTED**

## Evidence-supported question

B15 falsified exact decoded-pixel reproducibility at 32 Eevee render samples and source dither intensity 1.0. B16 changed only output dither to 0.0 and remained non-exact. Both experiments showed sparse differences of roughly one 8-bit code value; several differing frames and nearby pixel coordinates recurred.

That evidence rejects output dither as a sufficient explanation. It does not yet separate multi-sample accumulation/evaluation behavior from output quantization. B17 therefore tests the next measured Blender control, `scene.eevee.taa_render_samples`, without changing the frozen renderer.

## Frozen design

The machine-readable contract is `specs/eevee-sampling-factorial-spec.v0.1.json`.

B17 is a complete 2×2 factorial:

| Cell | Eevee render samples | output dither | Clean runs |
|---|---:|---:|---|
| S01-D0 | 1 | 0.0 | A, B |
| S01-D1 | 1 | 1.0 | A, B |
| S32-D0 | 32 | 0.0 | A, B |
| S32-D1 | 32 | 1.0 | A, B |

All eight runs render frames 1–144 from independent empty directories. The order is frozen in the JSON contract before execution to avoid choosing a favorable ordering after seeing results.

The exact frozen B14 renderer remains unchanged. Two tracked ReviewRenderSpec files differ at exactly one field: `proxy.renderSamples`, 1 versus 32. A B17-only configurator, implemented only after this freeze, must pass every cell through the same code path, verify source dither is 1.0, set the requested frozen level (including the 1.0 no-op control), report before/requested/after, and never save the source `.blend`.

## Primary gate and decision matrix

Each cell compares its A/B sequences with Blender-bundled OpenImageIO at warning threshold 0 and failure threshold 0. Exact success is all three at once:

- 144/144 decoded frames exact;
- maximum absolute error 0;
- total failed pixels 0.

The overall decision is frozen:

- `SAMPLING_CAUSAL_SUPPORT`: both sample-1 cells exact and both fresh sample-32 cells non-exact;
- `SAMPLING_NOT_SUFFICIENT`: both sample-1 cells non-exact and both fresh sample-32 cells non-exact;
- `MIXED_OR_BASELINE_UNSTABLE`: only one sample-1 cell is exact, or either new sample-32 cell unexpectedly becomes exact;
- `INVALID_EXPERIMENT`: any identity, invariant, binding or negative test fails.

PNG byte equality, failed-pixel count and maximum error remain descriptive. No tolerance or weaker label may be invented after execution.

## Controls

Every run must prove:

1. exact Blender binary/build, OCIO config, source `.blend`, receipt and embedded scene identities;
2. exact factor spec, selected ReviewRenderSpec and frozen renderer bytes;
3. observed Eevee render sample count equals its cell;
4. observed dither before is 1.0 and after equals the requested factor level;
5. camera/timeline state is unchanged after rendering;
6. exactly 144 expected filenames exist, with no extras;
7. every frame byte hash matches a self-hashed sequence manifest;
8. A and B resolve to distinct real directories;
9. the OIIO comparison covers and binds the two exact sequence hashes.

## Required attacks

At least twelve disposable negative cases must reach stable reasons for: factorial-spec identity, ReviewRenderSpec identity, renderer identity, comparator identity, configurator identity, invalid dither level, wrong observed render sample count, aliased A/B directories, missing frame, extra frame, mutated frame bytes and comparison/sequence binding mismatch.

## Falsification boundaries

- If sample 1 remains non-exact, the hypothesis that multi-sample accumulation is a sufficient cause is falsified for this profile. The next candidate must come from measured renderer/evaluation or scheduling controls.
- If sample 1 becomes exact in both dither cells while fresh sample 32 remains non-exact, the sampling factor has causal support. This still does not identify an internal Blender race or prove general Eevee determinism.
- If dither changes exact/non-exact status at sample 1, the result is interaction evidence requiring replication, not permission to choose the favorable cell as a universal fix.
- If fresh sample-32 behavior does not reproduce, the result is labeled unstable rather than forcing the historical baseline into a convenient story.

## Explicit non-claims

- sample-1 visual quality is not accepted by this experiment;
- no cinematic, photoreal, acting or human-review claim is tested;
- no result is generalized to Cycles, EXR masters, other Blender versions or other hardware;
- two sequence replicates per cell do not estimate a general mismatch probability;
- output containers may remain byte-different even when decoded pixels are exact.

