# B49-R — 512×288 cross-scene resolution holdout result

Date: 2026-08-27

Verdict: `B49_RESOLUTION_SCALING_HOLDOUT_SUPPORTED`

Preregistration commit: `fe2f857abeac9116d01d589fcf5f4cc3532d3f9a`

Tool-freeze commit: `581c7e1d6761be306f894980a7f76db4c6614c89`

Run-receipt SHA-256: `a3761703fad65f5bcfe6c8900e5d3a3acb81d9f5a96c3b72f327e9f254ce636b`

Results SHA-256: `feae838494de10b024f9186bd81aa9c9657a21fb14cf48748ce623e8f9148a42`

Audit SHA-256: `9e3e6572211f3b910e85a0c9a7c8ba38545a10e107a5148c0554a41ca6f399a4`

Evidence-core hash: `0b8199d48cc18c8f03b47f6763be705e5f6c0a655b62d293e5977b72db2a2c9e`

## Result

Two fresh Blender 5.2 Linux/amd64 Cycles CPU workers rendered the previously frozen B48 holdout frames at 512×288, sixteen times the committed 128×72 baseline pixel count. Both used the B48-selected 128-spp raw setting, seed offset 647647, four fixed CPU threads, motion blur off, denoising off, persistent data off, ACES 2 OCIO and the B47 seven-subimage production EXR pack.

| Shot | Measured render | Fresh worker wall | Render ratio | Render pixel exponent | EXR bytes | EXR pixel exponent | Peak self RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| TABLETOP · frame 37 | 151.992 s | 161.733 s | 15.390× | 0.985980 | 3,541,488 | 0.917547 | 541,200 KiB |
| INTERIOR · frame 19 | 191.877 s | 201.652 s | 15.833× | 0.996206 | 3,360,262 | 0.955367 | 541,336 KiB |

Both render-time exponents fall inside the preregistered `[0.95, 1.05]` interval. Both EXR-size exponents fall inside `[0.75, 1.05]`, both peak self RSS observations remain below 2,097,152 KiB, both EXRs reopen as finite 512×288 float32 Combined arrays with the exact seven-pass roster, and no experiment container remained.

The formal analyzer rejected all 15 frozen attacks for their declared reason. The independent audit reopened both real EXRs, replayed the complete analyzer and reproduced `results.json` byte for byte.

## Supported claim

For these two simple frozen scenes, the selected 128-spp raw configuration and the current four-vCPU Linux/amd64 worker running under ARM64 Colima/qemu, Blender render-operator time scales approximately linearly with pixel count from the committed 128×72 baselines through an unseen 512×288 holdout. This is a bounded cross-scene result, not a universal Cycles performance law.

## Labelled model projection

The protocol permits a projection from each committed 128×72 baseline using the frozen exponent band `[0.95, 1.05]`. These ranges are deliberately wide and carry both labels `MODEL_PROJECTION_NOT_MEASURED` and `CURRENT_QEMU_CPU_WORKER_ONLY`.

| Shot | 2K per frame | 2K · 240 frames | 4K per frame | 4K · 240 frames |
|---|---:|---:|---:|---:|
| TABLETOP | 28.25–48.55 min | 113.0–194.2 h | 1.76–3.47 h | 421.7–832.6 h |
| INTERIOR | 34.67–59.58 min | 138.7–238.3 h | 2.16–4.26 h | 517.5–1,021.7 h |

These are not measured 2K/4K renders, complete-shot timings, native x86/GPU/cloud throughput or dollar prices. They expose how unsuitable the current emulated CPU worker is for high-resolution production and give a falsifiable range for a later backend measurement.

## Non-claims and next intervention

B49-R does not establish human cinematic quality, spatial-detail adequacy, motion-blur quality, depth-of-field quality, character/hair/texture memory, full-sequence cache behavior, GPU or Eevee performance, native x86/cloud speed or dollar cost. `ru_maxrss` is the Blender process high-water mark, not total container, host or GPU memory.

Resolution-only scaling is now supported through 512×288. The next B49 intervention must change one cinema feature at a time—motion blur first, then depth of field—while retaining the selected sampling point, the two-scene structure, independent high-sample references and explicit human-review boundary.

## Artifacts

- `specs/codex-worker-resolution-holdout.v0.1.json`
- `research/2026-08-27-b49-r-codex-worker-resolution-holdout-protocol.md`
- `blender/render_b49_resolution_holdout.py`
- `scripts/run-b49-resolution-holdout.mjs`
- `scripts/analyze-b49-resolution-holdout.py`
- `scripts/audit-b49-resolution-holdout.py`
- `experiments/codex-worker-resolution-holdout-v0-1/`
