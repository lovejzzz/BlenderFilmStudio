# BlenderFilmStudio experimental charter

This charter is a persistent execution constraint for the BlenderFilmStudio goal. It applies to every technical claim, implementation phase and published research page.

## Objective with experimental spirit

Continuously advance BlenderFilmStudio by implementing and testing the SceneSpec → immutable BuildPlan → real Blender 5.2 workflow. Reproduce B01/B02 semantic structure across clean builds, publish falsifiable evidence, and continue to the next evidence-supported gap. Do this as an experimental research program rather than a feature-demo program.

## Active goal: three workflow gates

The active goal is judged through three explicit, falsifiable gates. A partial result must not be promoted to an end-to-end workflow pass.

1. **Worker build gate.** Build and identity-pin a real Blender 5.2 Linux/amd64 worker through buildx. The platform, official archive, Blender executable, image, build transport and retained receipts must be independently auditable.
2. **Runtime canary gate.** Exercise real Blender inside the worker and test the declared render backend, read-only input, writable output, network isolation, non-root execution, capability removal, CPU/memory/PID limits and TERM → KILL timeout behavior. A backend that does not complete must remain an explicit open boundary rather than being silently replaced by a weaker claim.
3. **End-to-end reproduction gate.** Run `SceneSpec → immutable BuildPlan → Blender compiler` for B01 and B02 from clean worker invocations twice each; compare canonical scene structure, `.blend` and compile receipts, camera, lighting, materials and topology, then retain adversarial integrity controls, independent audit, journal and published evidence.

### Evidence status at the 2026-08-26 checkpoint

- **Gate 1 — closed after documented corrections.** The retained image is Linux/amd64 and binds the official Blender 5.2 executable identity. Earlier legacy-builder and cross-platform identity failures remain in the record.
- **Gate 2 — resolved only to a bounded CPU-worker result.** Real Blender, containment, forced timeout and Cycles CPU rendering were observed. Headless Eevee did not complete on this ARM64 Colima/qemu host; the Eevee/GPU route remains open and must not be described as passed.
- **Gate 3 — closed for B01/B02 only.** Four clean compiler containers reproduced both canonical structure hashes and a fifth tampered-plan container failed closed. This does not establish arbitrary-scene coverage, pixel quality, production throughput or `.blend` byte identity.

Crossing these gates establishes the minimum controlled compiler workflow at its stated backend boundary. It does not establish the larger creative workflow. B43 then closed a narrow subscription-authenticated Codex CLI intent boundary, and B44 promoted its saved accepted proposals through the deterministic adapter into four real worker builds while the rejected proposal launched no container. B45's first pixel attempt was invalidated by a single-layer EXR media-type mismatch and null-report analysis crash; both failures remain preserved. The preregistered B45-C1 correction then rendered all four B44 `.blend` files in real Blender 5.2 workers and reproduced both decoded scene-linear float32 pixel arrays exactly under an independent audit. The next active evidence gap is a short continuous-shot promotion from those same scenes, with frozen temporal, quality, cost and interruption-recovery gates before any cinematic-quality or production-throughput claim.

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
