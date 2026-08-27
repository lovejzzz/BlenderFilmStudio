# B49-DOF — two-scene depth-of-field holdout result

Date: 2026-08-27

Verdict: `B49_DEPTH_OF_FIELD_OPERATING_POINT_SUPPORTED`

## Runtime and identity

Ten fresh Blender 5.2.0 LTS Linux/amd64 Cycles CPU workers rendered the two preregistered real-scene cells. Each used pinned image `sha256:c4b0f6…35b1`, exact promoted `.blend` identity, ACES 2, 128×72 raw multilayer EXR, CENTER 0.5-frame motion blur, denoising off, four threads, read-only repository input, disabled network, non-root execution and the frozen CPU/RAM/PID/time boundary.

Preregistration commit: `7b5ed4d75cdfd428fdf816ca30d328844e216988`. Tool-freeze commit: `2f358db834d85e958af97ca53004e9e3acdaac63`. Run receipt, result and audit SHA-256: `5983ad74…ca97`, `c11bf111…6b74`, `7b8279eb…ae3e`. Evidence-core hash: `6d40b928…d2e0`.

## Both scenes passed the reference-floor gate

Each shot used three independent 512-spp DOF-on references. The 128-spp DOF-on candidate had to remain within 3× the maximum individual-reference deviation from the three-reference mean in linear RGB NRMSE, log-luminance RMSE and exact-top-10%-edge RMSE.

| Shot | Linear / floor | Log-Y / floor | Edge / floor | Candidate closer than OFF |
| --- | ---: | ---: | ---: | ---: |
| TABLETOP frame 43 | 2.785777× | 2.496550× | 2.856265× | 3/3 |
| INTERIOR frame 23 | 1.789957× | 1.798302× | 2.186421× | 3/3 |

TABLETOP's DOF-on improvement over same-seed off was small: 0.529% linear, 0.570% log-luminance and 0.465% edge. INTERIOR's effect was much larger: 45.264%, 48.518% and 64.131%. Both scenes nevertheless satisfied the same preregistered rule: all three candidate metrics passed the floor and were strictly closer than off.

This supports a bounded numerical operating point. It does not mean that the INTERIOR camera is focused on the narratively correct subject; the current 3.2 m focus favors its window region rather than its 5.7–7.0 m chair.

## Pass-domain result reproduced D1 on real scenes

DOF-on versus off changed 22,427 Combined float components on TABLETOP and 27,637 on INTERIOR. It also changed Depth, Normal and active Cryptomatte layers on both scenes. Vector remained float32 exact on both because motion-blur mode and scene motion were held constant.

The production EXR contract must therefore bind Depth/Normal/Cryptomatte edge behavior to DOF mode. Cryptomatte ID payloads remain an exact/hash/coverage domain, not a generic numeric-RMSE domain.

## Cost

TABLETOP 128-spp render time was 10.033 s DOF-on versus 9.938 s off, a 1.0095× ratio; fresh wall was 19.409 versus 19.361 s. INTERIOR was 12.172 s versus 11.820 s, a 1.0298× ratio; fresh wall was 21.741 versus 21.333 s. Peak self RSS stayed approximately 492–495 MiB.

The three 512-spp TABLETOP references rendered in 29.548–30.056 s; INTERIOR references rendered in 23.479–23.822 s. These are current qemu CPU-worker observations, not native x86/GPU/cloud or dollar-cost claims.

## Integrity and remaining gate

All ten workers completed, no experiment container remained, 21/21 frozen attacks were rejected and the independent audit reproduced `results.json` byte for byte.

B49-DOF does not establish artistically correct focus, human-visible superiority, cinematic preference, focus-pull temporal quality, bokeh aesthetics, transparency/hair behavior, 2K/4K cost, GPU/Eevee behavior, native x86/cloud throughput or dollar cost.

The bounded machine gates for resolution, motion blur and DOF are now closed. The next gate is viewable-resolution, delayed-disclosure human review. It must expose the window-versus-chair focus choice as an actual blinded comparison rather than inheriting the machine verdict as an aesthetic answer.
