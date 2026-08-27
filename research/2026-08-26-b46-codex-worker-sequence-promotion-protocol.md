# B46 — B44 `.blend` → bounded continuous sequence protocol

Date frozen: 2026-08-26

Status at freeze: `PREREGISTERED_BEFORE_RUNNER`

## Question

B45-C1 proved two isolated representative frames. B46 asks whether the same four B44 `.blend` files reproduce ordered eight-frame scene-linear float sequences, including the frame-to-frame delta arrays, and whether a deliberately interrupted partial attempt can recover only through a new container and empty output root.

## Frozen cells

TABLETOP renders frames 21–28 and is the moving-camera cell; its canonical structure contains a linear camera push, so all seven adjacent transitions must change at least one float component. INTERIOR renders frames 9–16 and is the static control; its canonical structure contains no animation, so all seven adjacent transitions must contain zero changed float components. Each `.blend` replicate runs all eight frames in ascending order inside one fresh Blender process.

The intervention is Cycles CPU at 128×72, eight samples, the compiled shot seed, animated seed off, denoising off, motion blur off, persistent data off, four fixed threads, compositing off and sequencer off. Eight samples are exactly eight times B45's count but are not a perceptual-quality claim.

## Pixel and temporal decision domains

Every Render Result is saved as single-layer RGBA32 ZIP OpenEXR and RGBA8 PNG. The frozen host decoder canonicalizes each EXR as little-endian C-order BGRA float32 bytes. Sixteen cross-build frame pairs must be byte-exact in that decoded domain.

For each adjacent pair, NumPy subtracts the previous float32 array from the next using float32 output. The canonical delta hash binds the ordered frame pair and delta bytes. All fourteen cross-build transition pairs must be exact. Motion/non-motion gates prevent a trivially duplicated sequence from passing.

Four H.264 MP4 files are encoded from the primary PNG sequences at 24 fps for navigation and human inspection. They must probe as eight-frame 128×72 carriers, but they are lossy and never enter the scene-linear exactness decision.

## Fault injection and recovery

A fifth container opens `TABLETOP-A1`, completes frame 21, saves its two files and milestone, then exits immediately with frozen code 86. It must have exactly one partial frame, no successful sequence report and `promotable=false`.

A sixth, explicitly scheduled recovery attempt uses a different container name and a new empty output root. It renders frames 21–28 and must match the primary `TABLETOP-A1` decoded frame and transition hashes exactly. The runner does not automatically reuse or promote the partial directory. This is a controlled process-failure test, not a host-crash or distributed-scheduler claim.

## Resource and authority boundary

The image, network-none/non-root/read-only worker policy and 100 GiB disk reserve remain unchanged. The per-container wall limit is preregistered at 120 seconds because each successful container now renders eight frames. The projected write remains 1 GiB. Exactly six Docker runs, forty successful EXR host decodes, four review encodes, one image inspect and one cleanup check are allowed. The source-hash negative control still launches zero containers. Build, pull, download, Codex, model and video-generation API calls are forbidden.

## Promotion rule

B46 passes only if all primary, temporal-role, carrier, failure, recovery, cleanup, operation and identity gates pass; 21/21 attacks reject with their frozen first reason; the evidence self-hash matches; and an independent audit re-decodes every successful EXR and re-probes every review carrier.

Passing would close one bounded multi-frame worker handoff with a narrow clean-retry recovery claim. It would not establish complete shots, cinematic motion, invisible flicker, motion blur, denoising, 4K mastering, GPU/Eevee, cross-host behavior, arbitrary scenes, production throughput or human preference.
