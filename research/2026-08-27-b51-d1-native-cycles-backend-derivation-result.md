# B51-D1 · Native Cycles CPU / Metal backend derivation result

Date: 2026-08-27

Verdict: `NATIVE_CYCLES_BACKEND_DERIVATION_USABLE`

Preregistration commit: `57ae67254c0c269c283acd7e280654a74316442e`

Tool-freeze commit: `2e3df9e948e0d925b846b230801303bea5860e8b`

Audit-correction commit: `54ecc8b4691377a56cde0ba49cb532d231a2d981`

Run-receipt SHA-256: `e4a98e29857b72dd6b1e073cd99dd65b05d8822bf4b09a3c48a04ce6a3db9bce`

Results SHA-256: `c6d9c0d1cea1b622092860b1b7db4361fd763a8e83da439d84b2d1b1fb356bb8`

Corrected audit SHA-256: `e75523ff1c1f94a5e76744314a3874442507d3628332a7aa61e869e692eb0fde`

## Result

The installed official Blender 5.2.0 LTS arm64 build enumerated the Apple M4 Max CPU and `METAL_Apple M4 Max (GPU - 40 cores)`. Eight fresh Blender processes rendered the exact two B49-R scenes, frames, 512×288 resolution, 128 raw samples, seed, ACES 2 configuration and seven-subimage production EXR roster. Both backends completed all cells.

| Scene | qemu CPU parent | Native CPU runs | Metal runs | Native CPU / warm Metal |
|---|---:|---:|---:|---:|
| TABLETOP | 151.992 s | 4.112 / 4.122 s | **109.534 / 0.574 s** | 7.17× using warm R2 |
| INTERIOR | 191.877 s | 5.090 / 5.029 s | 0.717 / 0.695 s | 7.17× using median |

Native CPU was about 36.9–37.9× faster than the emulated qemu CPU parent on this bounded workload. Warm Metal was about 7.17× faster than native four-thread CPU and about 265–272× faster than qemu. These are render-operator ratios for two simple 512×288 frames, not production projections.

The first Metal cell is the counterexample that matters. Its EXR metadata partitions 109.53 seconds into about 1.17 seconds of Cycles render time and **108.31 seconds of synchronization**, compared with 0.40 seconds render and 0.13 seconds synchronization in the later TABLETOP Metal cell. A post-run read-only inventory found 79 files / 74 MiB under `~/.cache/cycles/kernels/Apple_M4_Max`, all recently modified. This is consistent with cold kernel/cache preparation, but the run did not freeze a pre-run cache-tree digest, so B51-D1 does not claim the cache caused every synchronization second.

## Pixel and container boundary

Both native CPU repeats reproduced every decoded float component in all seven passes exactly on both scenes. Their EXR bytes still differed because the Combined header recorded `Date`, `RenderTime` and Cycles timing attributes. This again rejects `.exr` byte identity as a proxy for decoded production-pass identity.

Metal repeats were not strict-float deterministic:

- TABLETOP changed 95,039 Combined components (maximum `1.144409e-5`), 3,724 Normal components and 10,551 Vector components; Depth and all three Cryptomatte layers were exact.
- INTERIOR changed 109,410 Combined components (maximum `4.768372e-7`), 612 Normal components and two Vector components; Depth and all three Cryptomatte layers were exact.

CPU–Metal paired Combined NRMSE was `0.00023794` on TABLETOP and `0.00322042` on INTERIOR when normalized by the native CPU mean RMS. The larger single-component CPU–Metal deviations occur on sparse boundaries. No perceptual threshold was frozen, so these values are descriptive and cannot establish visible equivalence.

## Audit failure retained, correction bounded

The initial independent audit crashed while hashing itself because it passed the `__file__` string to a helper expecting `Path`. `audit.initial-failure.json` preserves the exception. B51-C1 changed only that audit boundary, added direct verification of both qemu EXRs and their legacy B49 canonical Combined hashes, and checked every original frozen tool against its exact Git blob. It did not rerender or rewrite the receipt/result.

The corrected audit passed: analyzer replay was byte exact, frozen tools matched, qemu parent identities matched and all 14/14 mutation attacks passed.

## Supported claim

This machine's official native Blender 5.2 build can execute the frozen B49-R Cycles production-pass profile on both four-thread CPU and 40-core Metal. The measurements are trustworthy enough to design the next backend holdout. Warm Metal has a large throughput advantage, while cold synchronization and non-strict float repeatability are now explicit production variables.

## Non-claims and next gate

B51-D1 does not select a production worker. It does not test macOS containment, recovery, 2K/4K frames, long sequences, characters, hair, texture or volume memory, power/thermal saturation, human image equivalence, cloud cost or dollar cost.

Next is B51-D2: preregister an atomic, reversible Cycles cache-sequester/restore intervention. It must hash the cache tree before and after, preserve rather than delete the user's cache, compare cold and warm Metal synchronization, and separate fresh process from fresh cache. Only after that derivation may an unseen-frame production holdout freeze throughput and numerical-tolerance gates.

## Artifacts

- `specs/native-cycles-backend-derivation.v0.1.json`
- `research/2026-08-27-b51-d1-native-cycles-backend-derivation-protocol.md`
- `research/2026-08-27-b51-c1-native-backend-audit-correction.md`
- `experiments/native-cycles-backend-derivation-v0-1/`
- `scripts/run-b51-native-cycles-backend-derivation.py`
- `scripts/analyze-b51-native-cycles-backend-derivation.py`
- `scripts/audit-b51-native-cycles-backend-derivation.py`
