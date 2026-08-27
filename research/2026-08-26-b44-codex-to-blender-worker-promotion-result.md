# B44 — Codex proposal → Blender worker promotion result

Date: 2026-08-26

## Verdict

`CODEX_TO_BLENDER_WORKER_PROMOTION_REPRODUCIBLE`

The preregistered B44 chain passed its complete boundary. Two immutable proposals saved by the B43 subscription-authenticated Codex holdout crossed the frozen deterministic adapter into their exact SceneSpecs and BuildPlans. Each plan compiled in two fresh Blender 5.2 Linux/amd64 worker containers. The unauthorized proposal stopped before Docker.

## Observations

| Input | Decision | SceneSpec | BuildPlan | Containers | Canonical structure |
| --- | --- | ---: | ---: | ---: | --- |
| `TABLETOP-A` | ACCEPT | 1 | 1 | 2 | `6a71287aed7c982ed6ca1889858b43eafa5012708ce5f577abd2ee872345e82e` in 2/2 runs |
| `INTERIOR-A` | ACCEPT | 1 | 1 | 2 | `56d32ed8a8813c3365852a9ab52660b81e09eb5887daed4fa41f5459f3a6d954` in 2/2 runs |
| `UNAUTHORIZED-A` | REJECT | 0 | 0 | 0 | not applicable |

All four Blender processes exited 0 in 10,228–10,423 ms. Every manifest bound the frozen plan hash, the plan’s source-scene canonical hash and the structure file written beside it. Both within-scene canonical structure pairs were byte-identical. The `.blend` pairs were not byte-identical, so B44 does not claim Blender container-byte determinism.

The runtime operation trace contained exactly one image inspection, four Docker runs and one final running-container check. It contained no build, pull or download. The worker retained the B42-C1 boundary: Linux/amd64, network none, uid/gid 65532, all capabilities removed, no-new-privileges, read-only root and repository, one writable output mount, 256 PIDs, 8 GiB memory, 4 CPUs, 1 GiB shared memory and a 30-second wall timeout. Zero named experiment containers remained after the run.

Twelve of twelve adversarial mutations reached the frozen rejection reason. The independent audit re-read all parent evidence, tools, proposals, SceneSpecs, BuildPlans, assets, manifests, structures and `.blend` files; all checks passed.

## Identity

- Preregistration commit: `f44e16404df18af67f46533778b4cce367b5fc91`
- Spec SHA-256: `5c07d0b1f9b29f6791bc19c75ebe2311012b78e3fd51ed2294fc9c137124a88c`
- Tool freeze commit: `0577232a0bdb6ccb34b49e739ceda730da7b02a5`
- Worker image: `sha256:c4b0f6bebe77e9bd10b4875aaf0500d798de081259397c525f923f7a9eea35b1`
- Blender: `5.2.0 LTS`, build `fbe6228777e7`
- Result file SHA-256: `9e5d02c055dce8e05b73588d0e39c4ad3823277b1437aec20b110ace30d4776a`
- Evidence self-hash: `18f496cb11111e48c20fdd8b5bb4b1eca04f19b13def4cf0c743509f9021510e`
- Audit file SHA-256: `7b5fd2487d3a5ac613bcc249c484c6758acee730b8faf80eb5e94c7ce8e10c81`

## Claim boundary

B44 supports one narrow end-to-end engineering claim: under these frozen inputs, two accepted Codex preset proposals reproducibly promote to the same canonical Blender scene structures, and one unauthorized proposal has no Blender execution authority.

B44 does not make a live model call, render final pixels, establish cinematic quality, prove `.blend` byte identity, establish Eevee/GPU availability, cover arbitrary prompts or scenes, measure production throughput, provide remote attestation, or guarantee subscription price or usage limits.

## Next open boundary

The chain now ends at compiled `.blend` files. B45 must begin from the B44 outputs and test real pixel production: frozen representative frames first, with exact renderer, sampling, color and output receipts; only after that gate passes should the experiment expand to a continuous shot and temporal review.
