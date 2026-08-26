# B13 verifiable CompileReceipt result

Date: 2026-08-26

Classification: **FORMAL B13 TRUE / EXACT LOCAL RECEIPT / UNSIGNED**

## Positive result

B01 and B02 were each compiled twice from empty output directories through the restricted CLI and the real Blender 5.2.0 LTS binary. Every run produced:

- `scene.blend`;
- `scene.manifest.json` v0.2;
- `scene.structure.canonical.json` written by Blender/Python;
- `budget.report.json`;
- `compile.receipt.json`.

The independent Node verifier performed 19 checks over receipt self-hash, execution identity, trusted URIs, BuildPlan, compiler/supervisor/receipt sources, budget profile, OCIO, Blender/Node binaries, budget report, manifest, canonical structure and `.blend`.

All four receipts passed. Blender then reopened all four `.blend` files with auto-execute disabled and confirmed their embedded planHash, source SceneSpec hash, structureHash and manifest version.

## Clean-build identities

| Run | Execution identity | Receipt hash | Structure hash |
|---|---|---|---|
| B01-A | `798a9006…563b8` | `85da35ed…3f77f` | `c699fc27…b7f0b` |
| B01-B | `798a9006…563b8` | `be0288c6…49641` | `c699fc27…b7f0b` |
| B02-A | `a85a7280…036a4` | `dbd11906…8b803` | `025c6fa5…fa856` |
| B02-B | `a85a7280…036a4` | `e08306e1…53678` | `025c6fa5…fa856` |

Execution identity is stable within a benchmark because plan/tool/runtime/config identities are the same. Receipt hashes differ because run paths, metrics and exact output artifact hashes differ. B01 and B02 identities differ because their BuildPlans differ.

The published B01/B02 semantic structure hashes remained unchanged:

- B01: `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`
- B02: `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`

As in B01/B02’s original compiler experiment, A/B `.blend` byte hashes differed. The receipt records exact bytes per run; it does not redefine binary identity as semantic reproducibility.

## Runtime and tool identity

- Blender: `5.2.0 LTS`, build `fbe6228777e7`
- Blender executable SHA-256: `60ba7a9b6743f7acf101274361fa76409e382ae07cd2007ce07dea30f6b129f2`
- Node: `v26.5.0`
- Node executable SHA-256: `70851490e028b3d699a8d6d4e1de909af2a989359ae807974c92af9c6580a8e8`
- scene compiler SHA-256: `25ebfdfcd5d34a3dac9d74676a90ad8c095a96fd35fa0d4663b844f743f58240`
- restricted CLI SHA-256: `4cd49d91e7f396f04876b8fcb14ac3a10ff19fbba11309cae1cdc6911740b2af`
- budget profile SHA-256: `9203aba815c5a1b9063c288219219df1d4801eec598aa6cb1dc01729ff32eebe`
- OCIO SHA-256: `24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15`

## Negative result matrix

The 10 pre-registered cases were rejected with their intended stable reasons:

`RECEIPT_SELF_HASH`, `PLAN_FILE_SHA`, `PLAN_HASH_BINDING`, `COMPILER_SHA`, `BUDGET_PROFILE_SHA`, `OCIO_SHA`, `BLENDER_BINARY_SHA`, `MANIFEST_SHA`, `BLEND_SHA`, `MANIFEST_PLAN_BINDING`.

Two post-freeze supplementary cases also passed:

- canonical structure hash tamper → `STRUCTURE_CANONICAL_SHA`;
- non-empty output directory → stopped before Blender with `Restricted compile output must be empty`.

## Falsified implementation assumptions

1. JavaScript `localeCompare` is not the BuildPlan’s canonical key ordering. It initially produced the wrong plan hash.
2. Parsed numeric equality is insufficient to reconstruct cross-language canonical JSON bytes: Python `0.0` became Node `0`.
3. Reusing an output directory can create unbound Blender backup artifacts such as `scene.blend1`.

All three failures changed the implementation and remain in the journal.

## Boundary

The receipt is an unkeyed SHA-256 integrity graph. It is not a signature, trusted timestamp, notarization, secure-boot measurement, transparency log or remote attestation. An actor who can replace every file plus the verifier can construct another internally consistent receipt. Cinematic quality, physical realism and human review remain separate gates.

## Artifacts

- `research/2026-08-26-b13-compile-receipt-protocol.md`
- `experiments/compile-receipt-v0-1/results.json`
- `experiments/compile-receipt-v0-1/evidence/B01-A/compile.receipt.json`
- `experiments/compile-receipt-v0-1/evidence/B01-B/compile.receipt.json`
- `experiments/compile-receipt-v0-1/evidence/B02-A/compile.receipt.json`
- `experiments/compile-receipt-v0-1/evidence/B02-B/compile.receipt.json`
- `scripts/verify-compile-receipt.mjs`
- `blender/audit_compiled_artifact.py`
