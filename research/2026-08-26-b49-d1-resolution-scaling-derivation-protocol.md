# B49-D1 — selected-point resolution scaling derivation protocol

Date: 2026-08-26

Status: exploratory protocol frozen before renderer, runner or analyzer implementation

## Question

B48 selected 128 spp raw as the cheapest tested numerical point passing both 128×72 holdouts. That does not reveal how render time, peak resident memory or multipart EXR size scale with spatial resolution. B49-D1 asks for the first measured resolution curve while keeping the selected sampling point and every other rendering variable fixed.

## Frozen source and cells

- Source: B44 TABLETOP-A1 `.blend`, SHA-256 `9c4f9cc26e213c0b4de0462f7ad6878cabf27a2204ec1448e98e93aed36bd1f0`.
- Frame: 37, the TABLETOP B48 formal holdout.
- Samples: 128 raw; OIDN, motion blur and persistent data disabled.
- Seed offset: 647647, identical to B48's selected candidate. The 128×72 Combined array must reproduce B48 `TABLETOP-C128_RAW` exactly.
- Pass pack: B47 seven-subimage RGBA32 ZIP multipart EXR.
- Cells, each in a fresh worker and empty output root:
  1. `R1_128X72`: 128×72, 9,216 pixels.
  2. `R2_256X144`: 256×144, 36,864 pixels (4×).
  3. `R3_384X216`: 384×216, 82,944 pixels (9×).

## Runtime boundary

Use the pinned Blender 5.2 Linux/amd64 Cycles CPU image with four fixed threads, fixed source/plan/structure/OCIO identities and the existing read-only/network-none/non-root/capability-dropped worker boundary. The wall timeout may be 240 seconds per cell because R3 has nine times the baseline pixel count. Exactly three Docker runs and three host EXR inspections are allowed. Build, pull, download, model and video-model calls are forbidden.

The renderer records Blender render-operator seconds, save seconds and Linux `resource.getrusage(RUSAGE_SELF).ru_maxrss` in KiB after the EXR save. The host records fresh-container wall time and EXR bytes. Peak RSS is process-level self-reported high-water memory, not container-total memory or GPU memory.

## Frozen measurements

- Require every Combined array to have the declared shape, four channels and finite float32 values.
- Require the exact B47 raw seven-subimage roster at every resolution.
- Require R1 canonical Combined SHA-256 to equal the already committed B48 TABLETOP-C128_RAW hash.
- Measure render-time, peak-RSS and EXR-byte ratios relative to R1 at 4× and 9× pixels.
- Compute pairwise effective exponents `log(metric ratio) / log(pixel ratio)` for positive time, RSS and byte metrics.
- Report fresh-container wall time separately from Blender render time.
- Replay the analyzer byte-exactly.

## Decision and non-claims

D1 is usable to design a formal resolution gate if all three cells complete, R1 reproduces B48, representations are valid, all ratios/exponents are finite, the disk reserve remains above 100 GiB and analyzer replay is exact. It may reveal super-linear, sub-linear or non-monotonic scaling; no exponent is assumed in advance.

D1 cannot establish 2K/4K cost, complete-shot throughput, native x86/GPU/cloud performance, motion-blur or DOF cost, perceptual detail, cinematic quality or human preference. Extrapolation beyond 384×216 is forbidden as a measured claim. B49 motion blur and DOF remain separate later interventions so their target image changes are not mistaken for resolution error.
