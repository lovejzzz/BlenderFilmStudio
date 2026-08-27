# B51-D1 · Native Cycles CPU / Metal backend derivation protocol

Date: 2026-08-27

Status at freeze: `PREREGISTERED_DERIVATION · NO B51 OUTPUT EXISTS`

## Why this experiment exists

B49-R measured 151.992 s and 191.877 s per 512×288 frame on the current four-vCPU Linux/amd64 worker running through ARM64 Colima/qemu. That worker is useful as a contained evidence backend, but its measured cost is not a credible production-render estimate. The installed official Blender 5.2 build now reports two real local Cycles devices: the Apple M4 Max CPU and the 40-core Apple M4 Max Metal GPU.

B51-D1 asks the narrower question that must come first: can both native devices complete the *same frozen B49-R production-pass workload*, and what effect sizes are observed before a formal production-backend gate is chosen?

## Frozen intervention

The two previously frozen B49-R scenes and holdout frames are reused without editing:

- `TABLETOP`, frame 37;
- `INTERIOR`, frame 19.

Both native backends receive the same 512×288, 128-spp raw Cycles profile, seed offset 647647, ACES 2 OCIO configuration, motion blur off, denoising off, persistent data off and seven-subimage production EXR roster. CPU uses four fixed threads to match the qemu worker's declared CPU budget. Metal uses the enumerated `METAL_Apple M4 Max (GPU - 40 cores)` device.

There are two fresh Blender processes per scene/device cell, eight processes total. Order is balanced as `CPU → Metal` and `Metal → CPU` across scenes and repeats. This does not eliminate thermal, cache or system-load effects; it prevents one backend from always occupying the same ordinal position.

## Evidence gate

The derivation is usable only if:

1. the B49-R result/audit, Blender executable, source `.blend` files and OCIO configuration retain their frozen hashes;
2. the output root is absent or empty before execution and the disk projection preserves 100 GiB free;
3. exactly eight fresh Blender 5.2 processes run with `--background --disable-autoexec --offline-mode`;
4. every process reports the requested Cycles device and the frozen render profile;
5. all eight EXRs reopen as finite 512×288 Combined arrays with the exact seven-subimage roster;
6. the recorded EXR hashes, sizes and report bindings match the files on disk;
7. an independent analyzer rebuilds the published result from the frozen receipt and EXRs;
8. all fourteen mutation attacks fail for their declared reason.

Within-device repeat equality, CPU–Metal divergence and speed ratios are *measurements*, not validity gates. A non-exact Metal repeat is evidence to retain, not a reason to discard the experiment.

## Measurements

- render-operator and fresh-process wall time for every cell;
- median native CPU / Metal speed ratio and qemu CPU / native ratios by scene;
- within-device repeat byte identity and canonical float32 identity;
- CPU–Metal and native–qemu scene-linear RGB, log-luminance and edge NRMSE;
- EXR bytes, pass roster, finite-value checks, process peak RSS and device roster.

Native CPU and qemu CPU are comparison surfaces, not image-quality ground truth. Cross-platform divergence is descriptive until a separately frozen numerical and perceptual tolerance exists.

## Decision boundary

The strongest possible B51-D1 verdict is `NATIVE_CYCLES_BACKEND_DERIVATION_USABLE`. It means the local CPU/Metal measurements are trustworthy enough to design a holdout. It does **not** select Metal or macOS as the production worker.

A production promotion still requires a new preregistration with unseen frames, multiple independent repetitions, a threshold derived from B51-D1 rather than chosen after the holdout, explicit failure/recovery behavior, memory stress representative of characters/hair/textures, and a worker-containment design. Human cinematic quality remains a separate gate.

## Non-claims

This experiment cannot establish 2K/4K or complete-shot throughput, character/volume memory sufficiency, macOS sandboxing, cloud cost, dollar cost, universal determinism, cross-machine generalization or perceptual equivalence. It makes no video-model call and downloads no model or runtime.

Frozen machine-readable contract: `specs/native-cycles-backend-derivation.v0.1.json`.
