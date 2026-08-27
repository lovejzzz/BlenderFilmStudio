# B46 — exact bounded float sequence and fresh-attempt recovery result

Date: 2026-08-26

Status: `B44_BLEND_TO_BOUNDED_SEQUENCE_EXACT_WITH_RECOVERY`

Preregistration commit: `259cf3071b8ccd3884ecb3154a2dcc99380dec7b`

Tool-freeze commit: `6895092342afae5c3860a2a7b62142f7de5c088f`

Evidence SHA-256: `5781211095a441760a2878a3578cfab8f080d99ac881740aa8015e76e0c87f4b`

## Result

B46 passed its preregistered bounded-sequence gate. Four fresh Blender 5.2 Linux/amd64 Cycles CPU containers opened the four B44 `.blend` files directly and rendered two ordered eight-frame intervals at 128×72 and eight samples. The independent audit re-read all output reports and milestones, re-decoded all 32 primary EXRs plus eight recovery EXRs, re-probed all four review carriers and recomputed every frame, transition and sequence comparison.

- `TABLETOP-A1` and `TABLETOP-A2`: 8/8 cross-build frame hashes exact and 7/7 float32 temporal-delta hashes exact. Every transition had more than zero changed components, as required for the moving-camera treatment. Both complete sequence hashes were `6dcea8c9edaafb9905322f27223279add62aeccc47543b3ff481fc79b147496c`.
- `INTERIOR-A1` and `INTERIOR-A2`: 8/8 cross-build frame hashes exact and 7/7 float32 temporal-delta hashes exact. Every transition had exactly zero changed components, as required for the static control. Both complete sequence hashes were `334bdd26f42182fb46f4cc446bdc8716a7661dd8c38939b58d718501c06e28c5`.
- Overall pair gate: 16/16 frame comparisons and 14/14 transition comparisons exact.
- All four H.264 review carriers probed as eight-frame 128×72 `yuv420p` video at 24 fps with zero audio streams. These lossy files were navigation aids only and did not enter the exactness decision.
- All 21 adversarial attacks were rejected for their preregistered reason.

## Controlled failure and recovery

A fifth worker rendered TABLETOP frame 21, wrote the EXR, PNG and durable `FRAME_COMPLETED` milestone, then terminated through the preregistered `os._exit(86)` fault. It had exactly one completed frame, no final sequence report and was non-promotable.

A sixth worker used a different container name and a new empty output root. It rendered all eight TABLETOP frames. Its eight frame hashes, seven transition hashes and complete sequence hash exactly matched primary `TABLETOP-A1`. This supports a narrow recovery policy: discard the partial attempt as a promotable result and retry into a new empty attempt. It does not prove recovery from host loss, OOM, power failure or a distributed scheduler fault.

## Runtime and cost boundary

The primary containers took 15.374–16.668 seconds each; the successful retry took 15.362 seconds. The formal run executed exactly six Docker runs, 40 successful host EXR analyses, four review encodes, one image inspect and one final running-container check. It used no video-generation model and made no model or Codex API call inside the measured render boundary. The host disk guard preserved the 100 GiB reserve under a frozen 1 GiB projected write.

These times are observed on this specific ARM64 macOS host through the pinned Linux/amd64 Colima worker and are not a production-throughput estimate.

## What is now supported

For the two frozen B44 scenes and frame intervals, different `.blend` container bytes can produce exact ordered decoded float32 frames and exact float32 frame-to-frame deltas under the pinned Cycles CPU worker. A controlled partial process exit is prevented from promotion, and a new-container/new-empty-root retry reproduces the primary sequence exactly.

## What remains open

B46 does not establish complete shots, cinematic motion, perceptual flicker freedom, higher-sample quality, denoising, motion blur, layered EXR/AOV correctness, 4K mastering, character performance, GPU/Eevee operation, cross-host reproducibility, arbitrary prompt coverage, arbitrary scenes or production cost.

The next evidence-supported gap is a production-representation and quality ladder: freeze a short motion interval and test multilayer EXR/AOV/Vector outputs, motion blur, sample count and denoising as separate interventions, with an explicit image-quality metric and render-cost curve. Human claims such as “cinematic” remain outside machine promotion until a blinded review protocol exists.

## Artifacts

- `specs/codex-worker-sequence-promotion.v0.1.json`
- `research/2026-08-26-b46-codex-worker-sequence-promotion-protocol.md`
- `experiments/codex-worker-sequence-promotion-v0-1/results.json`
- `experiments/codex-worker-sequence-promotion-v0-1/audit.json`
- `experiments/codex-worker-sequence-promotion-v0-1/runs/`
- `experiments/codex-worker-sequence-promotion-v0-1/recovery/`
