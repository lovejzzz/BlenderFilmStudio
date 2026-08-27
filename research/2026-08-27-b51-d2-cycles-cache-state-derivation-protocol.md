# B51-D2 · Cycles cold / warm cache-state derivation protocol

Date: 2026-08-27

Status at freeze: `PREREGISTERED_DERIVATION · NO CACHE INTERVENTION EXECUTED`

## Why this experiment exists

B51-D1's first native Metal cell took 109.534 seconds and recorded 108.31 seconds of Cycles synchronization. Later fresh processes took 0.574–0.717 seconds. A post-run inventory found 79 recently modified files / 74 MiB under `~/.cache/cycles/kernels/Apple_M4_Max`, but D1 did not freeze the cache state before execution. It therefore cannot identify cache preparation as the cause.

B51-D2 separates **fresh process** from **fresh Cycles cache** while preserving the user's existing cache exactly.

## Reversible intervention

The runner must reject before mutation unless the exact original path `/Users/tianxing/.cache/cycles` exists as a real directory, the exact sibling quarantine path does not exist, the ignored generated-cache retention path does not exist, and all paths are on the same filesystem.

Before the first rename it records a canonical tree manifest: sorted relative path, POSIX mode, byte count and SHA-256 for every regular file; mtimes are excluded. It then performs only atomic directory renames:

1. original cache → exact sibling quarantine;
2. after three renders, newly generated test cache → ignored experiment retention;
3. quarantined original → original path.

No cache file or directory may be deleted. Restoration runs in `finally` even when Blender, parsing or analysis fails. The final original cache tree hash must equal the preflight hash and the quarantine path must be absent.

## Frozen cells

All three cells use TABLETOP frame 37 with the exact B51-D1 512×288, 128-spp raw, ACES 2, seven-pass Metal profile. Each cell launches a fresh Blender process.

- `COLD_R1`: cache path absent at process start;
- `WARM_R1`: cache created by `COLD_R1` remains present;
- `WARM_R2`: same cache after `WARM_R1` remains present.

The runner records a generated-cache tree manifest after every cell. This allows the experiment to distinguish cache population from process identity without inferring from time alone.

## Evidence and failure rules

The derivation is usable only if all three renders complete with exact source/device/profile/pass identity, all Combined arrays are finite, the cache-state sequence is observed, all artifacts match their reports, the original cache is restored exactly, independent replay is byte exact and all eighteen attacks fail closed.

Any Blender/render/analyzer failure remains a failed attempt. A restore failure is a safety incident and has priority over the analytical verdict. The runner must report the exact remaining paths and must not try deletion as recovery.

## Decision boundary

The strongest possible verdict is `CYCLES_CACHE_STATE_DERIVATION_USABLE`. It can support a causal cold/warm cache interpretation for this machine/build/workload and freeze the next holdout. It cannot select a production backend, establish universal cold-start time, or claim 2K/4K, long-sequence, memory-stress, containment, perceptual or dollar-cost performance.

Machine-readable contract: `specs/native-cycles-cache-state-derivation.v0.1.json`.
