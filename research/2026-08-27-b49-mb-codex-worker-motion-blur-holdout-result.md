# B49-MB — reference-calibrated motion-blur holdout result

Date: 2026-08-27

Verdict: `B49_MOTION_BLUR_OPERATING_POINT_SUPPORTED`

Preregistration commit: `ef309564d63bc7f4f40a1ed5db467e63d1632baa`

Tool-freeze commit: `03296b2348be0490485a8a58118a1544cac3e0a9`

Run-receipt SHA-256: `5fc37ad303f538ccf355c493c59cfbd1e9f3abcaf2905d16ac8adaa5a3ab7999`

Results SHA-256: `6fb46a8aecedf810cf9cb977349522345dafb043bfb62064ee03269f14088496`

Audit SHA-256: `fc20ec3509b83f3451188f722020fc5102d0ee7a8ffac7fbb530bd892d02b06c`

Evidence-core hash: `2b1d351935efb8dc8a9f1f1d2f7afe1b960c2ff975be9612fcbaa781faca8524`

## Result

Eight fresh Blender 5.2 Linux/amd64 Cycles CPU workers rendered the preregistered holdout. TABLETOP frame 37 received three independent 512-spp centered-half-frame blur references, a 128-spp blur-on candidate, a same-seed blur-off negative control and a same-seed zero-shutter mode control. Static INTERIOR frame 19 received same-seed blur-off and blur-on cells. Every output used 128×72 raw scene-linear data, ACES 2, four fixed threads and the exact seven-subimage multipart EXR pack.

All three reference Combined hashes were distinct. The float64 ensemble and per-metric local reference floor were established before scoring the candidate.

| Metric | Reference floor | 128 blur-on | On / floor | 128 blur-off | Off / floor | On improvement vs off |
|---|---:|---:|---:|---:|---:|---:|
| Linear NRMSE | 0.021190 | 0.050662 | 2.3908× | 0.050853 | 2.3998× | 0.376% |
| Log-luminance RMSE | 0.010406 | 0.025344 | 2.4356× | 0.025430 | 2.4439× | 0.339% |
| Edge linear RMSE | 0.050351 | 0.114105 | 2.2662× | 0.114625 | 2.2765× | 0.453% |

The 128-spp blur-on candidate remained below the frozen 3× floor limit on all three metrics and was strictly closer than the same-seed blur-off control on all three. This satisfies the exact preregistered accepted verdict.

The effect size is small. Blur off would also have remained within 3× the blur-reference floor. The supported claim is therefore that 128-spp raw remains an adequate numerical operating point for this centered half-frame exposure and that blur-on moves consistently toward the blur reference—not that blur is perceptually obvious or that off is numerically unacceptable at this motion/resolution.

## Cost

| Cell | Blender render | Fresh worker wall | EXR bytes | Peak self RSS |
|---|---:|---:|---:|---:|
| 512 blur reference A/B/C | 28.97–29.17 s | 38.65–38.78 s | 168,268–168,505 | 506,260–507,308 KiB |
| 128 blur on | 9.981 s | 19.615 s | 160,705 | 506,428 KiB |
| 128 blur off | 9.857 s | 19.666 s | 278,195 | 506,832 KiB |
| 128 zero shutter | 9.834 s | 19.480 s | 158,731 | 507,632 KiB |
| static 128 off / on | 12.130 / 11.917 s | 21.814 / 21.579 s | 237,682 / 174,553 | 504,356 / 504,296 KiB |

On this bounded cell, centered half-frame motion blur added 0.124 Blender render seconds relative to off, while fresh-worker wall was effectively unchanged. Enabling blur materially changed ZIP-compressed EXR size because Vector representation changed; size is not a visual-quality proxy.

## Pass-domain result

The formal holdout reproduced B49-MB-D1's representation counterexample on unseen frames:

- moving zero-shutter versus off: Combined, Depth, Normal and all three Cryptomatte subimages were exact; Vector changed 33,190 float components;
- static blur-on versus off: Combined, Depth, Normal and all three Cryptomatte subimages were exact; Vector changed 36,348 float components.

The production contract must bind motion-blur mode when consuming Vector. Cryptomatte is treated as identifier/coverage representation and is never ranked through generic float RMSE.

## Integrity

All eight workers completed, all representations were finite and complete, all 19 frozen attacks rejected for their declared reason, no experiment container remained, and the independent audit reopened every EXR and reproduced `results.json` byte for byte.

## Supported claim

For the frozen linear camera push at frame 37, 128×72, centered shutter 0.5 and the pinned four-vCPU Linux/amd64 qemu worker, B48's selected 128-spp raw point remains within 3× an independent three-reference motion-blur floor and is consistently closer to that blur reference than a same-seed blur-off control. Static image/identifier passes remain exact under the blur switch; Vector is mode-dependent.

## Non-claims and next intervention

B49-MB does not establish human cinematic preference, a universally correct shutter, perceptual visibility of this small numerical advantage, full-shot temporal stability, deformation/particle/rolling-shutter blur, depth of field, 2K/4K blur cost, GPU/Eevee behavior, native x86/cloud throughput or dollar cost.

Motion blur's bounded machine gate is now closed. The next single-variable intervention is depth of field: first derive Blender 5.2 focus/aperture semantics on a deliberately depth-separated fixture, then build a reference-calibrated holdout. The later blinded human review must compare shutter/DOF treatments at a viewable resolution; it cannot inherit a subjective conclusion from these 128×72 metrics.

## Artifacts

- `specs/codex-worker-motion-blur-holdout.v0.1.json`
- `research/2026-08-27-b49-mb-codex-worker-motion-blur-holdout-protocol.md`
- `blender/render_b49_motion_blur_holdout.py`
- `scripts/run-b49-motion-blur-holdout.mjs`
- `scripts/analyze-b49-motion-blur-holdout.py`
- `scripts/audit-b49-motion-blur-holdout.py`
- `experiments/codex-worker-motion-blur-holdout-v0-1/`
