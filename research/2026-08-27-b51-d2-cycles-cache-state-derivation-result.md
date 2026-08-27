# B51-D2 · Cycles cold / warm cache-state derivation result

Date: 2026-08-27

Verdict: `CYCLES_CACHE_STATE_DERIVATION_USABLE`

Preregistration commit: `90d73be7b73cb15e6f9a15f7fc5f3d72b6af2595`

Tool-freeze commit: `5bdb19dc47078a3e45f1d00e54dfa179d5d45397`

Duration-parser correction commit: `9fca2d603ea08488d77f6e5cf2465bfec5f16daa`

Run-receipt SHA-256: `c72bc695411891ea957ec27087470b35ae11e1d0d1711e7a541c036547b8ed53`

Results SHA-256: `dcb01aaa4bcb2d69bc7dd12359a693812709539860bf6d45543e85bbe87bc74b`

Corrected audit SHA-256: `692d0c7198a63dbc727858dc883cf2d7d5dfb03f4bcf73225b0ca16addb79848`

## Safety result first

The exact original `/Users/tianxing/.cache/cycles` tree contained 79 files and 77,737,584 bytes with content-tree SHA-256 `fc6bc6f949f6c1a2953b94e1176cbfcd27fcd4274b49c6d6b91ba06853f02f11`.

The runner atomically renamed that directory to the frozen sibling quarantine, verified the source path was absent and the quarantined tree hash matched, ran three fresh Blender processes, moved the newly generated 75-file / 75,627,472-byte test cache into the ignored experiment retention path, and atomically restored the original. The final original tree hash matched preflight exactly; the quarantine path is absent. No cache was deleted or overwritten.

## Timing result

| Cell | Cache at process start | Blender render operator | Fresh process wall | EXR Cycles render | EXR synchronization |
|---|---|---:|---:|---:|---:|
| `COLD_R1` | path absent | 0.789983 s | 1.404792 s | 0.42 s | 0.34 s |
| `WARM_R1` | generated cache present | 0.578154 s | 1.138991 s | 0.41 s | 0.13 s |
| `WARM_R2` | same generated cache present | 0.569390 s | 1.125405 s | 0.40 s | 0.13 s |

Removing the exact Cycles disk cache increased render-operator time by 1.366× and the reported synchronization component by 2.615× relative to `WARM_R1`. The absolute cold penalty was about 0.21 seconds—not 108 seconds.

Therefore the 74 MiB `~/.cache/cycles` tree observed after B51-D1 is **not a sufficient explanation** for D1's 108.31-second synchronization event. That event may depend on an OS/Metal pipeline cache, driver process, first host-session initialization or another state outside this directory; B51-D2 does not distinguish those candidates.

## Pixel boundary

Cold versus warm and warm versus warm reproduced the B51-D1 Metal pass-domain pattern:

- Depth and all three Cryptomatte layers were decoded-float exact;
- Combined, Normal and Vector were not exact;
- maximum Combined difference was `1.144409e-5` in both comparisons.

Cache absence therefore did not restore strict Metal repeat identity. These differences remain numerical measurements without a perceptual claim.

## Analyzer failure retained

All three renders and the safety restore completed before the frozen analyzer failed on Blender's `MM:SS.xx` EXR duration format. It expected `HH:MM:SS.xx`. C1 retained the exception, added two-field parsing without rerendering or moving caches, bound the correction in the result and verified every original frozen tool through its Git blob.

The corrected independent audit passed: result replay was byte exact, current original and retained generated cache trees matched the receipt, the original tool set matched the freeze commit and 18/18 attacks passed.

## Supported claim and next gate

On this M4 Max / Blender 5.2 workload, the exact user-level Cycles disk cache has a measurable but small cold penalty and cannot account for the earlier 108.31-second synchronization outlier. Fresh process and fresh Cycles cache are now experimentally separated.

The next production step is not destructive OS-cache clearing. It is an unseen-frame warm-state holdout with an explicit pre-job Metal canary: production timing starts only after the canary reports bounded synchronization, while cold-host readiness is recorded as a separate job-start metric. The holdout must add long-sequence throughput, thermal/power observation, memory-stress scenes and numerical tolerances. macOS containment remains an independent gate.

## Artifacts

- `specs/native-cycles-cache-state-derivation.v0.1.json`
- `research/2026-08-27-b51-d2-cycles-cache-state-derivation-protocol.md`
- `research/2026-08-27-b51-d2-c1-duration-parser-correction.md`
- `experiments/native-cycles-cache-state-derivation-v0-1/`
- `scripts/run-b51-cycles-cache-state-derivation.py`
- `scripts/analyze-b51-cycles-cache-state-derivation.py`
- `scripts/audit-b51-cycles-cache-state-derivation.py`
