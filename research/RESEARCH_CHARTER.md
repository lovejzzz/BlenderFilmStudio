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

Crossing these gates establishes the minimum controlled compiler workflow at its stated backend boundary. It does not establish the larger creative workflow. B43 then closed a narrow subscription-authenticated Codex CLI intent boundary, and B44 promoted its saved accepted proposals through the deterministic adapter into four real worker builds while the rejected proposal launched no container. B45's first pixel attempt was invalidated by a single-layer EXR media-type mismatch and null-report analysis crash; both failures remain preserved. The preregistered B45-C1 correction then rendered all four B44 `.blend` files in real Blender 5.2 workers and reproduced both decoded scene-linear float32 pixel arrays exactly under an independent audit. B46 extended those same scenes to two ordered eight-frame intervals: 16/16 cross-build frame hashes and 14/14 float32 temporal-delta hashes were exact, the moving-camera and static-control relations both held, and a one-frame interrupted attempt recovered exactly only through a new container and empty output root. B47 then reproduced 28/28 cross-build Combined/Depth/Normal/Vector/Cryptomatte pass pairs, validated pass-specific semantics and exact moving/static temporal controls under an independent audit. B48-D1 measured a first real sampling/denoising ladder and falsified any simple assumption that OIDN dominates raw sampling: it improved log-luminance error but could worsen scene-linear and edge error, added a production subimage and imposed large fixed cost on the current worker. B48-D2 reproduced the same-seed 512-spp float array exactly in a new worker while measuring a material 0.033–0.035 pairwise NRMSE across independent high-sample seeds. Formal B48 then tested two unseen frames with 14 fresh workers and selected 128-spp raw as the only cell keeping linear, log-luminance and edge error within 3× each local three-reference floor on both scenes. B49-D1 next measured near-linear render-time scaling (effective pixel exponent 0.980–0.990) through 384×216 while reproducing the B48 baseline exactly. Formal B49-R then validated the preregistered curve at an unseen 512×288 point on both scenes: the two render-time pixel exponents were 0.985980 and 0.996206, all 15 attacks passed and the independent analyzer replay was byte-exact. B49-MB-D1 then derived real Cycles shutter semantics across eleven workers: moving image passes responded to shutter duration, nominally equivalent exposure windows decoded exactly, static image passes stayed exact, and Vector changed solely from enabling blur even at zero shutter or with no scene motion. Formal B49-MB subsequently established that 128-spp half-frame blur remained within 3× a fresh three-reference floor and was closer than blur-off on all three metrics, while preserving the Vector mode counterexample; the measured advantage was only 0.34–0.45% and is not promoted to a perceptual claim. B49-DOF-D1 then made focus semantics falsifiable on three depth-separated targets: 3/3 focus interventions moved the maximum local modulation to the requested plane, an on-axis focus object exactly overrode a poisoned numeric distance, and DOF unexpectedly changed Depth, Normal and active Cryptomatte edge samples while leaving Vector exact. Formal B49-DOF subsequently passed all three reference-floor metrics on both real scenes and was closer than DOF-off in 3/3 metrics on both while reproducing the auxiliary-pass boundary. B50 packages the original window-depth focus and a chair-object focus as eighteen balanced, delayed-disclosure 960×540 review sessions. Its exact published source/build scan passed with zero sensitive matches, but human evidence remains 0/18 and external collection is not yet open. B51-D1 then executed eight native Blender 5.2 processes on Apple M4 Max CPU and Metal against the frozen B49-R profile. Native CPU was about 37× faster than qemu and warm Metal about 7.17× faster than native four-thread CPU, but the first Metal cell spent 108.31 seconds in reported synchronization and Metal repeats were not strict-float exact. The corrected independent audit retained its initial tool exception, replayed results byte-exactly and passed 14/14 attacks. The active production gap is now a reversible cold-cache versus warm-cache intervention before any native backend promotion; B50's human gate remains independently pending.

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
