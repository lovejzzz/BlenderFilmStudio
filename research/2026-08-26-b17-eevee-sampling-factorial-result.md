# B17 Eevee sampling × output-dither factorial result

Executed: 2026-08-26 with real Blender 5.2.0 LTS build `fbe6228777e7` on Apple M4 Max.

Status: **SAMPLING_CAUSAL_SUPPORT**

The experiment was pre-registered in commit `8cffc7a`, before the B17 configurator/runner existed and before any B17 frame was rendered. Tool implementation was then frozen in commit `7cb8daa`. Eight clean Blender processes rendered a total of 1,152 frames in the pre-registered order.

## Primary result

| Cell | Samples | Dither | Decoded exact | Failed pixels | Maximum error | PNG byte exact |
|---|---:|---:|---:|---:|---:|---:|
| S01-D0 | 1 | 0.0 | **144/144** | **0** | **0** | 0/144 |
| S01-D1 | 1 | 1.0 | **144/144** | **0** | **0** | 0/144 |
| S32-D0 | 32 | 0.0 | 132/144 | 88 | 0.003921598196029663 | 0/144 |
| S32-D1 | 32 | 1.0 | 126/144 | 113 | 0.003921583294868469 | 0/144 |

Both sample-1 cells met the exact zero-tolerance gate regardless of dither. Both fresh sample-32 cells reproduced the non-exact pattern seen historically in B15/B16. The pre-registered decision is therefore `SAMPLING_CAUSAL_SUPPORT`.

This is causal support for the tested Blender control: changing the sample count changed reproducibility status while the receipt-bound source, renderer, Blender, OCIO, dimensions, timeline, color transform and comparison method remained fixed. It does **not** identify a specific internal Blender race, accumulation algorithm or thread-scheduling mechanism.

## Visual-quality boundary

The sample-1 frame is visibly much noisier than the sample-32 frame. Exact reproducibility at sample 1 is therefore a diagnostic result, not a production recommendation. The experiment establishes that the multi-sample path participates in the observed sparse nondeterminism; it does not solve the requirement for a clean, high-quality and reproducible review render.

## Integrity and attacks

- 12/12 pre-registered negative cases reached the intended stable reason;
- every cell used distinct A/B directories and 144 exact filenames;
- every frame was bound by SHA-256 to a self-hashed sequence manifest;
- each OIIO report was bound back to both sequence hashes and all 288 per-frame input hashes;
- the source B02 `.blend` remained SHA-256 `2a505360…11b0b`;
- the exact Blender binary remained SHA-256 `60ba7a9b…129f2`;
- source dither was observed as 1.0 before every run, including the 1.0 no-op control;
- observed `scene.eevee.taa_render_samples` matched every cell.

PNG containers remained 0/144 byte-identical even in the two pixel-exact sample-1 cells. This independently confirms that file-byte identity and decoded-pixel identity are different claims.

## Next falsifiable boundary

B18 should map the sample-count dose response at 1, 2, 4, 8, 16 and 32 samples while holding dither fixed, then test whether a determinism boundary appears at a particular accumulation depth. If every value above 1 is non-exact, the next intervention should target renderer evaluation/scheduling rather than inventing a pixel tolerance. Visual quality must remain a separate measured output.

Artifacts:

- `experiments/eevee-sampling-factorial-v0-1/results.json`
- `experiments/eevee-sampling-factorial-v0-1/evidence/`
- `specs/eevee-sampling-factorial-spec.v0.1.json`
- `research/2026-08-26-b17-eevee-sampling-factorial-protocol.md`

