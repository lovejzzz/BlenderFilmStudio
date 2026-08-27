# B45 — B44 `.blend` → real float pixels promotion protocol

Date frozen: 2026-08-26

Status at freeze: `PREREGISTERED_BEFORE_RENDERER_RUNNER_OR_OUTPUT`

## Question

B44 produced two pairs of `.blend` files whose bytes differ but whose canonical scene structures match. When each file is opened independently in the exact Blender 5.2 Linux/amd64 worker, does each pair produce byte-exact decoded scene-linear float pixels at a frozen representative frame?

## Frozen design

`SHOT_109` uses frame 24 of 1–48; `SHOT_110` uses frame 12 of 1–24. Every B44 `.blend` receives one fresh worker container. The render intervention is fixed at Cycles CPU, 128×72, one sample, four fixed threads, the compiled shot seed, animated seed off, denoising off, compositing off and sequencer off.

Each process calls the render operator exactly once. The same Render Result is saved twice:

- OpenEXR RGBA, 32-bit float, ZIP, scene-linear ACEScg;
- PNG RGBA, 8-bit, through the compiled ACES SDR review view.

The EXR files are decoded on the host with the frozen Python/OpenCV/NumPy runtime. The canonical pixel hash binds shape, dtype and BGRA channel order before hashing little-endian float32 bytes. Acceptance requires every component to be finite and the two decoded float arrays for each shot to be byte-exact. EXR and PNG container hashes are recorded but are not acceptance thresholds.

## Negative path

A fifth declared input points to the real `TABLETOP-A1` source but declares a zero SHA-256. The preflight must return `SOURCE_BLEND_HASH_MISMATCH` and launch no container. The total Docker run count is therefore exactly four.

## Why this is not a quality gate

The frozen low resolution and single sample make the experiment affordable and falsifiable on the CPU-only worker. They deliberately sacrifice visual quality. Passing B45 would prove that the B44 semantic scene result reaches real high-bit pixels and that `.blend` byte differences do not alter this bounded pixel result. It would not establish 4K mastering, temporal stability, cinematic lighting, performance, human preference or production cost.

## Next boundary if accepted

Freeze a small set of start/middle/end frames at a reviewable sampling level, then test a continuous low-resolution shot with temporal receipts. Human cinematic review begins only after that technical sequence gate.
