# B13 verifiable CompileReceipt protocol

Date frozen: 2026-08-26, before modifying the scene manifest or implementing receipt generation.

Status: **PRE-REGISTERED / NOT YET EXECUTED**

## Observed gap

`BFS_SCENE_MANIFEST` v0.1 records semantic structure and telemetry but does not bind the output to the BuildPlan hash, Blender build, compiler source, budget supervisor or OCIO bytes. B12 records a budget profile and command, but its process report is not a complete artifact receipt.

## Question

Can one independently verifiable receipt bind the exact BuildPlan, trusted local toolchain, real Blender 5.2 runtime, OCIO config, budget report, scene manifest and saved `.blend`, while preserving the published B01/B02 structure hashes across two clean builds?

## Receipt model v0.1

The receipt will contain repository-relative URIs and SHA-256 values for:

- BuildPlan file plus its verified embedded `planHash`;
- `blender/compile_scene.py`;
- restricted CLI and budget supervisor source;
- restricted budget profile;
- exact OCIO config;
- Blender executable bytes, reported version and build hash;
- Node executable bytes and reported version;
- budget-process report;
- `scene.manifest.json`;
- `scene.blend`.

`executionIdentityHash` is the SHA-256 of canonical JSON containing only immutable plan/tool/runtime/config identities. It excludes paths that vary by run, wall-clock timestamps, telemetry and output artifact hashes.

`receiptHash` is the SHA-256 of canonical JSON for the complete receipt body with the `receiptHash` field omitted. The canonicalizer sorts object keys recursively and preserves array order.

`BFS_SCENE_MANIFEST` v0.2 will add the verified BuildPlan hash, source SceneSpec canonical hash, Blender version/build hash and OCIO hash outside the existing `structure` object. Therefore the published semantic `structureHash` must remain unchanged.

## Frozen positive matrix

Run B01 and B02 twice each through the real restricted CLI and real Blender 5.2 binary.

Formal positive requirements:

- four receipts pass the independent verifier;
- B01 A/B share one `executionIdentityHash`;
- B02 A/B share one `executionIdentityHash`;
- B01 and B02 execution identities differ because their BuildPlans differ;
- B01 A/B structure hash remains `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`;
- B02 A/B structure hash remains `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`;
- output `.blend` byte hashes and receipt hashes are recorded but are not required to match across clean runs;
- every manifest plan/runtime/config binding agrees with the receipt.

## Frozen negative matrix

Harmless receipt copies will be mutated and, where needed, re-canonicalized so each check reaches the intended layer:

1. `N_RECEIPT_SELF_HASH`: body changed without updating `receiptHash`;
2. `N_PLAN_FILE_SHA`: declared BuildPlan file hash changed and receipt rehashed;
3. `N_PLAN_HASH_BINDING`: embedded receipt plan hash changed and receipt rehashed;
4. `N_COMPILER_SHA`: compiler source hash changed and receipt rehashed;
5. `N_BUDGET_PROFILE_SHA`: budget profile hash changed and receipt rehashed;
6. `N_OCIO_SHA`: OCIO hash changed and receipt rehashed;
7. `N_BLENDER_BINARY_SHA`: Blender executable hash changed and receipt rehashed;
8. `N_MANIFEST_SHA`: scene manifest hash changed and receipt rehashed;
9. `N_BLEND_SHA`: saved `.blend` hash changed and receipt rehashed;
10. `N_MANIFEST_PLAN_BINDING`: a copied manifest and receipt are internally rehashed but the manifest plan hash no longer matches the receipt.

Each negative must fail with its intended stable reason, not merely “invalid JSON.” No production asset, tool, config or Blender installation will be modified.

## Acceptance gate

Formal B13 is true only if all positive requirements and 10/10 negative cases pass, B01/B02 published structure hashes remain unchanged, exact tool/runtime hashes are published, and the journal records both observations and non-claims.

## Explicit non-claims

- An unkeyed SHA-256 receipt is not a digital signature.
- A user who can replace the receipt, verifier and every referenced file can forge a new internally consistent package.
- The receipt does not prove secure boot, notarization, trusted time, code-signing identity, malware absence or remote execution isolation.
- Blender executable hashing identifies exact bytes; it does not certify those bytes as safe.
- Two clean `.blend` binaries are not expected to be byte-identical.
- Receipt verification does not replace human review of cinematic or physical quality.

Signature, transparency-log or remote-attestation work must be a later, separately falsified layer.
