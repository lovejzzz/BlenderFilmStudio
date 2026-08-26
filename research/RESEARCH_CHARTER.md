# BlenderFilmStudio experimental charter

This charter is a persistent execution constraint for the BlenderFilmStudio goal. It applies to every technical claim, implementation phase and published research page.

## Objective with experimental spirit

Continuously advance BlenderFilmStudio by implementing and testing the SceneSpec → immutable BuildPlan → real Blender 5.2 workflow. Reproduce B01/B02 semantic structure across clean builds, publish falsifiable evidence, and continue to the next evidence-supported gap. Do this as an experimental research program rather than a feature-demo program.

## Non-negotiable method

1. **Use real Blender.** A Blender-facing claim must be exercised against the installed Blender binary and real `.blend` data unless explicitly labelled as a design-only hypothesis.
2. **Freeze the gate first.** Write the question, success criteria, negative cases and non-claims before implementing the experiment when the result could otherwise influence the gate.
3. **Attack the claim.** Every formal gate needs positive controls and relevant negative cases. “No exception occurred” is not enough.
4. **Preserve falsification.** First-run failures, byte nondeterminism, physical-review failures and unsupported boundaries remain in the record; they are not rewritten as success.
5. **Separate evidence layers.** Byte integrity, path identity, semantic structure, pixels, perception, physics and execution isolation are different claims and require different evidence.
6. **Prefer machine-readable artifacts.** Store exact hashes, manifests, receipts, metrics, tool/runtime identities and stable failure reasons alongside prose.
7. **Maintain the journal.** Record hypothesis, frozen gate, real runtime, observation, verdict, artifact paths and next open boundary for every promoted result.
8. **Publish non-claims.** State what the experiment does not prove, especially when a soft watchdog, geometric proxy or deterministic replay could be mistaken for a stronger result.
9. **Do not stop at a green test.** Audit whether the test covers the actual claim, inspect the generated artifacts, verify the public page, then continue to the next evidence-supported gap.
10. **Never fabricate missing evidence.** Human review, physical calibration, external authority and unavailable measurements remain pending until real evidence exists.

## Promotion rule

A result may be labelled `FORMAL TRUE` only when:

- its pre-registered positive and negative gates pass;
- the real runtime and exact inputs are identified;
- authoritative artifacts are stored and independently inspectable;
- known contradictions are resolved or explicitly narrow the claim;
- the journal and research page state the remaining boundary;
- the public artifact has been fetched and verified after deployment.

Otherwise the result remains `HYPOTHESIS`, `EXPERIMENTAL`, `FALSIFIED`, `AUTOMATION PASS / HUMAN PENDING`, or another narrower status supported by the evidence.
