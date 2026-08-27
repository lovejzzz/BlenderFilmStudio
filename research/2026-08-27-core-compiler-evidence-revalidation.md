# Core compiler evidence revalidation

Date: 2026-08-27

Scope: read-only revalidation of the published SceneSpec → immutable BuildPlan → Blender 5.2 B01/B02 claim

New Blender renders: 0

## Question

Does the repository still contain self-consistent, independently auditable evidence for the active goal's minimum compiler boundary, or has later pixel research obscured an incomplete core result?

## Checks executed

1. Recomputed SHA-256 directly from all eight retained `scene.structure.canonical.json` byte streams: four native macOS clean builds and four clean Linux/amd64 worker builds.
2. Compared every recomputed digest with its adjacent manifest and with the frozen B01/B02 expected digest.
3. Compared the plan hash recorded by every manifest with the benchmark's immutable BuildPlan identity.
4. Inspected the retained Linux/amd64 independent audit and the Codex-to-worker promotion result/audit identities.
5. Re-ran the current SceneSpec validator over its complete valid/invalid fixture roster.
6. Requested the published compiler evidence route over HTTPS.

## Measured result

All eight structure files matched their manifests and the expected benchmark identities:

- B01 structure: `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`
- B01 plan: `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`
- B02 structure: `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`
- B02 plan: `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`

The current SceneSpec suite passed 22/22 fixtures. The Linux/amd64 audit remains `passed: true`; its file SHA-256 is `46579e29a27a3ab9937b88e290a83fe2143600772982274be1e94f9239b85834`. The corrected Linux/amd64 result remains `LINUX_AMD64_COMPILER_REPRODUCIBLE_AFTER_MOUNT_CORRECTION`; its file SHA-256 is `c9a55fb87bf1115960c3c82bfe5eb71b14f4f0ec0df7059e57b842b52160a1a4`.

The Codex-to-worker promotion result remains `CODEX_TO_BLENDER_WORKER_PROMOTION_REPRODUCIBLE`, file SHA-256 `9e5d02c055dce8e05b73588d0e39c4ad3823277b1437aec20b110ace30d4776a`; its audit remains `passed: true`, file SHA-256 `7b5fd2487d3a5ac613bcc249c484c6758acee730b8faf80eb5e94c7ce8e10c81`.

The public compiler route returned HTTP 200 at `https://lovejzzz.github.io/BlenderFilmStudio/compiler-v0-1/`.

## Interpretation

The active goal's minimum B01/B02 compiler boundary is closed at the semantic-structure level. This revalidation did not rely only on summary JSON: it recomputed the canonical structure hashes from the retained byte streams.

## Non-claims

- This does not make `.blend` files byte-identical; the retained native experiment explicitly records that they differ.
- This does not establish arbitrary-scene compiler coverage.
- This does not establish cinematic quality, perceptual preference, calibrated display output or production throughput.
- This did not rerender Blender pixels and cannot replace the later pixel, temporal, pass, quality or human-review experiments.

## Next unresolved boundary

D12.1 showed that cross-language evidence has three separable identities: exact payload arrays, per-document self-integrity and decision metrics. The next experiment must measure Blender's static Vector/reconstruction floating floor independently and design a three-layer evidence contract without requiring bit-exact producer reductions.
