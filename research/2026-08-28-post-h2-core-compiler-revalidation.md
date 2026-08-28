# Post-H2 core compiler revalidation

Date: 2026-08-28  
Scope: current retained evidence for `SceneSpec → immutable BuildPlan → Blender 5.2 compiler`  
New Blender renders: 0  
New Blender compilations: 0

## Question

After the D12.14-H2 formal invocation was invalidated by a frozen runner admission defect, does the repository still contain sufficient current evidence for the primary B01/B02 compiler objective, or did the algorithm investigation substitute for an incomplete compiler milestone?

## Current observations

| Requirement | Direct check on 2026-08-28 | Observation |
|---|---|---|
| SceneSpec accept/reject contract | `node scripts/validate-scene-spec.mjs` | 22/22 fixtures matched their expected valid/invalid outcome |
| Immutable BuildPlan determinism | `compileBuildPlan()` called twice in one fresh Node process for each benchmark; canonical wrapper bytes compared | B01 and B02 were byte exact within each pair |
| B01 BuildPlan identity | recomputed current compiler output | `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` |
| B02 BuildPlan identity | recomputed current compiler output | `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687` |
| Native Blender 5.2 clean-build receipts | current verifier reopened all four retained receipt graphs | B01-A/B and B02-A/B: 4/4 `PASS OK`, 19 checks each |
| Cross-environment canonical structure | SHA-256 recomputed from eight retained canonical byte streams and compared with each adjacent manifest | 8/8 exact across native macOS and corrected Linux/amd64 worker roots |
| B01 fixed structure identity | eight-stream recomputation | `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b` |
| B02 fixed structure identity | eight-stream recomputation | `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856` |

The eight-stream check parsed every `scene.structure.canonical.json`, required deep equality with the adjacent manifest `structure`, and required the byte digest to equal both `manifest.structureHash` and `manifest.structureCanonical.sha256`. The four native receipts additionally bind the BuildPlan, compiler source, restricted CLI, budget supervisor, receipt tooling, budget profile, OCIO configuration, Blender binary, Node binary, budget report, scene manifest, canonical structure bytes and `.blend` artifact.

## Verdict

`CORE_SCENESPEC_BUILDPLAN_BLENDER52_B01_B02_REPRODUCIBILITY_REVALIDATED`

The active goal's minimum compiler boundary is supported by retained, current-verifier-compatible evidence. D12.14-H2 did not replace or weaken it. No new compilation was necessary because the question was whether the retained evidence still verifies against the current trusted files and runtime; all direct checks passed.

## Non-claims

- `.blend` container bytes are not deterministic and are not used as the semantic reproducibility criterion.
- B01/B02 do not represent full actor performance, production lighting complexity or all later SceneSpec versions.
- Receipt verification is exact local identity, not cryptographic signing or remote attestation.
- This revalidation does not turn the invalidated H2 invocation into a scientific result.

## Next evidence-supported gap

The immediate open engineering boundary is formal-run admission reliability. H2's accepted preflight did not exercise the exact relative-path CLI shape later passed to its frozen runner; the runner then failed before its own failure-finally boundary. A reusable admission contract must therefore test semantically equivalent relative and absolute repository paths, path containment, fresh-root behavior, pushed-evidence lookup and failure-receipt reachability before future one-shot formal tool freezes. This should be a new experiment and must not repair or rerun `B52-D12.14-H2`.
