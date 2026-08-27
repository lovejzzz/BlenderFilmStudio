# B49-D1 — selected-point resolution scaling derivation result

Date: 2026-08-27

Status: `RESOLUTION_SCALING_DERIVATION_USABLE`

Protocol commit: `2e02a6f6baf03cd38e4f59ace03c75677f729a62`

Tool-freeze commit: `48c2d705f4a5a39205bc92b926100707519afc51`

Run-receipt SHA-256: `c8ad4309dd44a7d50e1fff3cf7e680550d4c62acb1b52bff6532c749b042dc70`

Analysis SHA-256: `57a0f31232dbb45aa5a2064d9a75aee3c8c3d5631fdf5f301cf15fc07e3edbca`

## Result

Three fresh Blender 5.2 Linux/amd64 Cycles CPU workers rendered the B48-selected 128-spp raw TABLETOP frame 37 at 128×72, 256×144 and 384×216. Samples, seed, scene, pass pack, threads, OCIO and containment remained fixed. All EXRs reopened with the exact seven-subimage B47 roster and finite Combined arrays.

The 128×72 Combined canonical float32 SHA-256 was `4e255e4fa7fdfac9c61d5cfa72d86525714203b7e0b9f1b8be9d99bd26d3dddd`, exactly reproducing B48's committed TABLETOP selected cell in a new worker.

| Resolution | Pixels | Render s | Fresh wall s | Peak self RSS | EXR bytes |
|---|---:|---:|---:|---:|---:|
| 128×72 | 9,216 | 9.816 | 19.553 | 504,588 KiB | 278,195 |
| 256×144 | 36,864 (4×) | 38.181 (3.890×) | 47.941 (2.452×) | 512,720 KiB (1.016×) | 986,391 (3.546×) |
| 384×216 | 82,944 (9×) | 86.434 (8.806×) | 96.214 (4.921×) | 526,068 KiB (1.043×) | 2,140,180 (7.693×) |

The render-time effective pixel exponents were 0.9798 at 4× pixels and 0.9901 at 9× pixels: nearly linear in pixel count over this bounded range. EXR-byte exponents were 0.9130 and 0.9286, slightly sub-linear under ZIP compression. Peak-self-RSS exponents were only 0.0115 and 0.0190 because the Blender/scene base footprint dominated these small frames.

Fresh-container wall scaling was lower—effective exponents 0.647 and 0.725—because roughly 9–10 seconds of scene/startup overhead is amortized as render work grows. This is why the site must keep render-operator time and fresh-container wall time separate.

The frozen analyzer replay produced a byte-identical result. No experiment container remained, and the 100 GiB disk reserve held.

## Supported claim

For this simple TABLETOP scene, selected 128-spp raw setting, pinned CPU worker and 128×72→384×216 range, Blender render time scales approximately linearly with pixel count while the measured process high-water RSS changes little. This is a measured local curve, not a universal Cycles law.

## Non-claims and next step

D1 does not measure 2K or 4K, complete sequences, native x86/GPU/cloud throughput, complex geometry/texture memory, motion blur, depth of field, characters, hair or human quality. Peak `ru_maxrss` is self-process memory, not container-total or GPU memory.

The next resolution holdout should test an unseen 512×288 point (16× baseline pixels) on both TABLETOP and INTERIOR and preregister a prediction interval from D1 rather than refitting after observation. Only after that point validates or falsifies the near-linear curve should the cost model publish a bounded 2K extrapolation. Motion blur and DOF must remain separate B49 interventions because they change the target image, not merely its sampling density.

## Artifacts

- `research/2026-08-26-b49-d1-resolution-scaling-derivation-protocol.md`
- `blender/derive_b49_resolution_scaling.py`
- `scripts/run-b49-resolution-scaling-derivation.mjs`
- `scripts/analyze-b49-resolution-scaling.py`
- `experiments/codex-worker-resolution-scaling-derivation-v0-1/`
