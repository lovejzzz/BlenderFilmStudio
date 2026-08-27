# B47 — reproducible multipart production-pass handoff result

Date: 2026-08-26

Status: `B44_BLEND_TO_MULTIPART_PRODUCTION_PASSES_EXACT`

Preregistration commit: `c93ef549982fcf55cb53a4c3383b145cb14d20a4`

Tool-freeze commit: `93ee9aeb2a5e0093021158fcd8e7ffda78c5e845`

Evidence SHA-256: `7e8139e710dee9e4f75f333f22bf58ffa9045767d5d843e6581b25198bbbbc02`

## Result

B47 passed its preregistered production-representation boundary. Four fresh Blender 5.2 Linux/amd64 Cycles CPU containers opened the four B44 `.blend` files directly. Each rendered two ordered frames and saved each Render Result once as a 32-bit ZIP multipart OpenEXR containing exactly seven float subimages: Combined, Depth, Normal, Vector and CryptoObject00–02.

The independent audit reopened all eight EXRs with Blender 5.2's bundled OpenImageIO 3.1.13.1, reconstructed all 56 subimage observations and passed.

- TABLETOP frames 21–22: 14/14 cross-build pass pairs exact.
- INTERIOR frames 9–10: 14/14 cross-build pass pairs exact.
- Overall: 28/28 canonical float32 pass pairs exact.
- Every subimage had the frozen multipart name, channel layout and float format. No decoded component was NaN or infinity.
- Combined was non-empty; Depth was positive and used the observed `1e10` far-background sentinel; Normal stayed inside [-1,1].
- Both TABLETOP Vector passes contained more than 32,000 non-zero finite components while motion blur remained disabled.
- Cryptomatte declared `MurmurHash3_32`, `uint32_to_float32`, the frozen `BFS_MASTER.CryptoObject` layer, a parseable manifest, every required asset object and exact A/B manifests.
- Moving TABLETOP: Combined, Depth, Normal and Vector changed between frames 21 and 22 in both builds.
- Static INTERIOR: all seven pass hashes remained unchanged between frames 9 and 10 in both builds.
- All 18 attacks rejected for their preregistered reason.

## Important byte/content distinction

The eight OpenEXR container SHA-256 values were all different, including the two static INTERIOR frames whose seven decoded pass arrays were identical. B47 therefore confirms the same evidence-layer distinction seen earlier: multipart container bytes are not the production-content identity. Promotion is based on the canonical decoded float arrays, channel layout and semantic metadata.

## Runtime and cost boundary

The four containers took 10.679, 10.713, 11.012 and 10.706 seconds. The run executed exactly four Docker containers, eight frame renders and eight host inspections, with no review encode, download, build, pull, Codex/model call or video-generation API. The 100 GiB disk reserve remained enforced under a 1 GiB projected write.

This is an observed bounded cost on the current ARM64 macOS host through Colima/qemu, not a production throughput forecast.

## What is now supported

For the two frozen B44 scenes and two-frame intervals, different `.blend` container bytes reproduce the complete seven-subimage production pass pack exactly at the decoded float32 level. The pass layout is stable, Depth/Normal/Vector semantics satisfy the frozen predicates, Object Cryptomatte manifests bind the expected objects, and moving/static temporal controls behave as declared.

## What remains open

B47 does not prove cinematic image quality, motion-blur quality, denoising quality, high-sample convergence, 4K mastering, downstream compositing quality, character performance, GPU/Eevee behavior, cross-host reproducibility, complete-shot throughput, arbitrary scenes or human preference.

The next evidence-supported gap is B48: a preregistered quality/cost ladder that treats sampling, denoising and motion blur as separate interventions over the now-verified production representation. A visual-quality conclusion will require an explicit reference/error metric and later blinded human review; it cannot be inferred from pass reproducibility.

## Artifacts

- `specs/codex-worker-production-pass-promotion.v0.1.json`
- `research/2026-08-26-b47-codex-worker-production-pass-promotion-protocol.md`
- `experiments/codex-worker-production-pass-promotion-v0-1/results.json`
- `experiments/codex-worker-production-pass-promotion-v0-1/audit.json`
- `experiments/codex-worker-production-pass-promotion-v0-1/runs/`
