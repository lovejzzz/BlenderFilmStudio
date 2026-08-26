# BlenderFilmStudio real-Blender lab journal

This is a continuous laboratory record for experiments executed against the actual local Blender binary. Retrospective entries are reconstructed only from committed machine-readable evidence; live entries are written before or during the experiment.

The persistent method for this goal is versioned in `research/RESEARCH_CHARTER.md`. The charter requires real Blender execution, pre-registered gates, negative cases, preserved falsification, machine-readable evidence, explicit non-claims and public verification.

## Laboratory environment

- Blender: `5.2.0 LTS`
- Blender build hash: `fbe6228777e7`
- Blender build branch: `blender-v5.2-release`
- Blender platform: `Darwin`, `arm64`
- Host: macOS `26.5.1` (`25F80`)
- CPU: Apple M4 Max
- Memory: `51,539,607,552 B` (48 GiB)
- Node: `v26.5.0`
- OCIO: ACES 2 CG config SHA-256 `24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15`

No serial number, account identifier or secret is recorded in this journal.

## J-001 · SceneSpec → BuildPlan → real Blender compiler

Type: retrospective, reconstructed from `experiments/compiler-v0-1/results.json`.

Hypothesis: a canonical SceneSpec can compile to one immutable BuildPlan, and two clean Blender processes can create semantically identical scenes.

Real execution: Blender 5.2 loaded the pinned B01/B02 `.blend` libraries, authored cameras/lights/render settings and saved new `scene.blend` files twice per benchmark.

Observation:

- B01 plan: `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`
- B01 structure: `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`
- B02 plan: `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`
- B02 structure: `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`
- both A/B structure comparisons passed;
- both A/B `.blend` byte hashes differed;
- tampered BuildPlans were rejected.

Verdict: semantic structure reproducibility passed; `.blend` binary reproducibility was falsified and is not used as the semantic gate.

## J-002 · Actor, contact and articulated grasp

Type: retrospective, reconstructed from B03–B05 experiment artifacts.

Real execution: Blender opened the B03/B04 character rigs, evaluated gaze, face Shape Keys, foot/contact samples, armature constraints and two-finger IK, then compiled B05 through the same scene compiler.

Observation:

- B03 structure: `96041c22a6626b4c5aceff3cc74155d5be411cfe0142f3025ecdf2d86d84d5ff`
- B05 structure: `a21c1e8944c50e528270cc314afbfe186a8d727ab5fb0dd0b4a8b078b4d315df`
- B05 automation: 8/8 negative cases passed;
- human perceptual gates remain separate from geometric automation.

Verdict: typed rig/contact/grasp compilation is technically executable, but “natural acting” and photoreal skin/contact remain unproven.

## J-003 · Physics solve versus immutable replay

Type: retrospective, reconstructed from B06–B08 artifacts.

Hypothesis: one rigid-body solve might reproduce exactly in repeated Blender runs.

Observation: B06 falsified exact source-solve reproducibility. B07 therefore froze an individually evaluated trajectory, and B08 compiled it as immutable kinematic replay.

- B08 plan: `7a4bccb640130db2dbf5c315907f81d5462605b6939b00a9df672c362d544dd9`
- B08 structure: `46898404f12905d9fb1c31b7a3694a41b1d951cb688a15654a4dae084fe3077d`
- 132 frames: position error `0`, rotation error `0`;
- 8/8 trajectory tamper cases rejected.

Verdict: source physics remains a reviewed upstream process; deterministic compilation consumes the approved trajectory rather than silently re-solving it.

## J-004 · Path and appended-asset security

Type: retrospective, reconstructed from B10/B11 attack JSON.

Real execution: harmless symlink/path escape cases were presented to the Node compiler, and hash-valid `.blend` fixtures carrying Blender drivers, Shape Key drivers, constraints, rigid bodies, actions, linked libraries and overrides were appended by Blender 5.2.

Observation:

- B10 first run exposed six path/symlink escapes; after remediation 8/8 cases were rejected;
- B11 first run compiled hidden evaluation behavior;
- after typed post-append inspection, 9/9 B11 cases were rejected;
- nine existing assets were inventoried; six exact B03/B04 head/gaze rig constraints form the narrow allowlist.

Verdict: byte hash, path identity and Blender evaluation structure are three separate integrity layers.

## J-005 · Restricted process resource budget

Type: live experiment completed 2026-08-26; evidence in `experiments/resource-budget-v0-1/results.json`.

Hypothesis: a local Codex/CLI supervisor can fail closed on measured resource budgets without changing B01 semantics.

Real execution: Blender sleep/log fixtures and the real B01 compiler were launched as OS child processes. Local Node fixtures exercised file-count, output-byte, RSS and non-zero-exit cases.

Observation:

- six pre-registered cases produced `WALL_TIME`, `LOG_BYTES`, `OUTPUT_FILES`, `OUTPUT_BYTES`, `RSS_BYTES` and `CHILD_FAILED` as expected;
- five over-budget processes received SIGTERM and were awaited;
- final B13-era regression: B01 restricted compile `568 ms`, sampled peak RSS `253,837,312 B`, log `1,109 B`, three outputs totalling `129,032 B`;
- B01 structure remained `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`;
- BuildPlan symlink, external output and external report regressions passed 3/3.

Verdict: formal B12 true as a soft watchdog. It is not an OS sandbox or kernel hard quota.

## J-006 · Compile receipt gap audit

Type: live pre-experiment audit, 2026-08-26.

Question: can an observer independently bind a saved `.blend` and manifest to the exact BuildPlan, compiler, Blender binary, budget profile and OCIO config?

Observation:

- `scene.manifest.json` v0.1 contains structure, structure hash, warnings and telemetry;
- it does not contain the BuildPlan hash or runtime/toolchain identity;
- B12 records budget-profile identity but does not bind every input/tool/output into one self-verifying artifact;
- current local SHA-256 values include compiler `3b73b281…bea51`, restricted runner `f93798b3…86b3`, budget profile `9203aba8…eebe`, OCIO `24ec8184…ad15`;
- the Blender executable is a real `183,237,520 B` binary with build hash `fbe6228777e7`.

Decision: pre-register B13 CompileReceipt before implementation. The receipt hash is tamper evidence, not a cryptographic signature or remote attestation.

First implementation observation: using JavaScript `localeCompare` for receipt key ordering produced B01 plan hash `d418c4024317995238c7ce29d2ea17666f33ba9be85f182c0c3eea27fcc3645f`, contradicting the authoritative BuildPlan hash `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`. The receipt canonicalizer was corrected to the compiler's explicit code-point comparison. “Canonical JSON” is not an adequate specification without the exact ordering rule.

Second implementation observation: the first real B01 receipt smoke stopped with `CompileReceipt manifest structure self-hash mismatch`. Python preserved numeric lexemes such as `0.0`; after JSON parsing, Node serialized the same value as `0`. The parsed structures were numerically equal but their canonical bytes differed (`3130` Python bytes versus `3006` Node bytes). The design was changed so Blender writes its exact `scene.structure.canonical.json` bytes and both manifest and receipt bind that artifact. Cross-language verification no longer pretends it can reconstruct lost number-type lexemes.

Third implementation observation: reusing the smoke output directory caused Blender to preserve the previous scene as an unbound `scene.blend1` backup. A receipt for the main `scene.blend` is not a closed clean-build package if undeclared leftovers share the directory. The restricted CLI now requires a missing or empty output directory before launching Blender; formal B13 runs start from four separate empty directories.

Formal execution observation:

- B01-A/B execution identity: `798a90068c5d8c29394a15d304aacc215c4eff08af82d37edd4e416eb52563b8`;
- B02-A/B execution identity: `a85a728079af1fe93e6fe20eb4ee69bf82618ad5cdea3eec44f2e1d9a3e036a4`;
- four run-specific receipt hashes and four `.blend` hashes differed as expected;
- all four receipts passed 19 verifier checks;
- Blender reopened all four `.blend` files and reported the receipt planHash, structureHash and manifest v0.2 from embedded scene properties;
- 10/10 pre-registered receipt attacks and 2/2 post-freeze supplementary attacks produced their intended reasons;
- exact Blender binary SHA-256: `60ba7a9b6743f7acf101274361fa76409e382ae07cd2007ce07dea30f6b129f2`.

Verdict: formal B13 true for local, exact-byte, self-hashed compile receipts. The receipt remains unsigned and is not remote attestation.

## J-007 · Complete-shot review dailies gap

Type: live pre-experiment audit, 2026-08-26.

Question: does the receipt-bound B02 scene survive its entire 144-frame timeline and become a complete, playable, auditable review video?

Observation before execution:

- PixelSpec v0.1 rendered B02 frames 1, 72 and 144 twice, but never rendered frames 2–71 or 73–143;
- existing B04/B05/B09 review clips demonstrate short video review mechanics for other experiments, but they are not bound to the B02 CompileReceipt;
- measured B02 4K/512-sample Cycles frames take roughly 302–328 seconds each on this host, so a serial 144-frame master is approximately 12–15 hours;
- Blender 5.2 reports the renderer identifier `BLENDER_EEVEE` and exposes `scene.eevee.taa_render_samples`; the frozen proxy uses that actual API rather than guessing a newer identifier;
- local FFmpeg and ffprobe are both 8.1.2; their exact binary SHA-256 values are frozen in ReviewRenderSpec v0.1;
- the B02-A receipt file SHA (`bdaa81e0…c1ff3`) and its internal receipt hash (`dbd11906…53678`) are separate integrity claims and are both frozen.

Decision: pre-register B14 as a `REVIEW_PROXY_NOT_MASTER` experiment. The 960×540/32-sample Eevee sequence is a dailies gate for completeness, provenance and human review access. It cannot satisfy or weaken the existing 4K/512-sample Cycles master contract.

Protocol: `research/2026-08-26-b14-review-dailies-protocol.md`.

First execution observation: the complete sequence rendered and passed the initial automation, but inspection found a tautological Blender-local OCIO assertion (`cache ID == itself`). The outer verifier already enforced the exact OCIO file SHA, so the run did not accept a different config, but the local check had no evidence value. Promotion stopped. The assertion was changed to compare the loaded config name with the receipt-verified BuildPlan and the entire shot was rerun.

Formal execution observation:

- 144/144 exact frame names, no gaps or extras;
- real Blender render time `28.324786 s`, mean `0.196700 s/frame`;
- 144 local PNG files totalled `83,216,547 B`;
- sequence hash `a52903fc327139ae41ed08f2d257d704b7977e9fda060138b106ceb56dbd56e4`;
- H.264 review file `438,567 B`, SHA-256 `e9f52ad3dc497fbb2e6074c2f79df2fa0c365235c5713a9f29e1ead927b340b8`;
- ffprobe independently reported yuv420p, 960×540, 24/1 fps, 144 declared/decoded frames, 6 seconds and no audio;
- render-before/render-after camera and timeline snapshots matched exactly;
- 10/10 pre-registered attacks failed at their intended layer;
- human review remains `PENDING`.

The stopped pre-correction run had sequence hash `4584715f31efcde8c8e88d23d29b7b6d97088707bdea067a320b99360544f014` and video hash `1cbecb1dc1d446daaf599b75cff10fb4a34879a99c7f098bcf8e3eeba6f8780c`. A second corrected candidate passed, but evidence inspection found absolute local paths in its recorded FFmpeg command and log tail. Promotion stopped again; the runner was changed to emit `<REPO>` placeholders and the full shot was regenerated. Because tool identity changed across candidates, their differing sequence hashes are not a controlled determinism result. They create the next question: identical-source A/B comparison of PNG bytes and decoded pixels.

Verdict: formal B14 automation true for a receipt-bound complete review proxy. It is explicitly not the 4K Cycles master, and cinematic/human acceptance has not passed.

Artifacts: `experiments/review-dailies-v0-1/results.json`, `experiments/review-dailies-v0-1/evidence/`, `public/review-dailies-v0-1/` and `research/2026-08-26-b14-review-dailies-result.md`.

## J-008 · Same-source proxy reproducibility freeze

Type: live pre-experiment audit, 2026-08-26.

Question: with the exact B14 renderer, spec, receipt, `.blend`, Blender binary and OCIO bytes held constant, are two complete Eevee proxy sequences identical as PNG containers and as decoded RGBA pixels?

Run A is frozen by B14 evidence hash `c5fb0c83…3380c`, sequence hash `a52903fc…d56e4`, renderer SHA `b969e267…eda5c` and ReviewRenderSpec SHA `65db6ca2…9553`. The runner must reverify all 144 A frame bytes before producing run B.

Decision: exact decoded equality is the primary hypothesis: 144/144 frames with maximum absolute error zero and zero failed pixels. No perceptual tolerance will be invented after looking at the data. A decoded difference will complete B15 as `FORMAL EXACT FALSIFIED`, not as an invalid run.

Protocol: `research/2026-08-26-b15-review-proxy-repro-protocol.md`.

Status at freeze: not executed. Comparator and B15 runner do not yet exist; run B has not started.

First execution failures: Node stopped before Blender because `realpath` was imported from `node:path`. After correction, a complete candidate measured 126/144 exact decoded frames, but two SHA attacks left `copy.png`, so the earlier extra-frame gate fired and only 6/8 attacks reached their intended reason. That candidate was `INVALID EXPERIMENT`.

Formal execution after fixing the fixture extension and regenerating run B:

- 0/144 PNG files byte-identical;
- 127/144 decoded RGBA frames pixel-exact;
- 17 frames and 114 of 74,649,600 pixels differed (`0.0001527%`);
- maximum channel difference `0.003921583294868469`, about one 8-bit code value;
- worst frame 94 had 14 failed pixels;
- A sequence `a52903fc…d56e4`, B sequence `ad3b8930…27139`;
- 8/8 attacks returned the frozen reason.

Verdict: `FORMAL EXACT FALSIFIED`. No perceptual tolerance was pre-registered, so B15 does not call the tiny magnitude a bounded pass. Exact Eevee proxy determinism is not a valid invariant here.

Artifacts: `experiments/review-proxy-repro-v0-1/results.json`, `experiments/review-proxy-repro-v0-1/evidence/` and `research/2026-08-26-b15-review-proxy-repro-result.md`.

## J-009 · Output-dither causal isolation freeze

Type: live pre-experiment audit, 2026-08-26.

B15's maximum difference was approximately one 8-bit code value. A real Blender query of the exact B02 `.blend` reported `scene.render.dither_intensity = 1.0`; the frozen B14 renderer leaves that value untouched. This makes output dithering the next evidence-supported candidate.

Hypothesis: setting only dither intensity to zero before the exact frozen renderer runs will restore 144/144 decoded pixel equality across two new complete sequences.

Exact success remains max error zero and zero failed pixels. No tolerance will be chosen after execution. A dither-zero exact result supports a causal factor but does not prove disabling dither is artistically preferable or eliminate every other source of nondeterminism.

Protocol: `research/2026-08-26-b16-dither-isolation-protocol.md`.

Status at freeze: configurator and runner do not exist; D0-A and D0-B have not started.

Formal execution observation:

- both runs verified before `1.0`, requested/after `0.0`, and did not save the source `.blend`;
- D0-A/B: 130/144 decoded frames exact;
- 14 frames contained 69 failed pixels; maximum channel error `0.003921598196029663`;
- 0/144 PNG containers byte-identical;
- D0-A `23.801723 s`, D0-B `23.682913 s`;
- 8/8 negative cases reached their intended reason.

Verdict: `DITHER_NOT_SUFFICIENT`. Turning output dithering off does not restore exact Eevee sequence reproducibility. The reduced count relative to B15 is not promoted as an improvement because these are independent runs. Repeated differing frames and nearby coordinates point next toward render sampling or evaluation order.

Artifacts: `experiments/dither-isolation-v0-1/results.json`, `experiments/dither-isolation-v0-1/evidence/` and `research/2026-08-26-b16-dither-isolation-result.md`.

## J-010 · Eevee sampling × dither factorial freeze

Type: live pre-experiment audit, 2026-08-26.

B16 proved that disabling output dither is not sufficient: 14/144 frames still differed at 32 Eevee samples. The sparse one-code-value pattern and recurring frame/coordinate neighborhoods support testing render sampling/evaluation next, but do not prove it is the cause.

Hypothesis: reducing `scene.eevee.taa_render_samples` from 32 to 1 will restore exact within-cell decoded-pixel reproducibility independent of whether output dither is 0.0 or 1.0.

B17 freezes a full 2×2 design with two clean 144-frame sequences per cell—1/32 samples × 0/1 dither—rather than reusing only the favorable historical condition. All eight new runs, their order, exact zero-tolerance gate, four-outcome decision matrix and twelve negative cases are fixed before implementation or rendering.

Protocol: `research/2026-08-26-b17-eevee-sampling-factorial-protocol.md`.

Status at freeze: B17 configurator and runner do not exist; no B17 frames have been rendered. The sample-1 ReviewRenderSpec differs from the frozen sample-32 spec at exactly `proxy.renderSamples` and has SHA-256 `0d5857e2…c2dd`.

Formal execution observation:

- eight clean Blender processes rendered 1,152 frames in the frozen order;
- S01-D0: 144/144 decoded exact, max error 0, failed pixels 0;
- S01-D1: 144/144 decoded exact, max error 0, failed pixels 0;
- S32-D0: 132/144 decoded exact, 88 failed pixels, max error `0.003921598196029663`;
- S32-D1: 126/144 decoded exact, 113 failed pixels, max error `0.003921583294868469`;
- all four cells remained 0/144 PNG-byte exact;
- 12/12 negative cases reached the frozen reason;
- source `.blend`, Blender, renderer, comparator, ReviewRenderSpecs and OCIO identities remained fixed.

Verdict: `SAMPLING_CAUSAL_SUPPORT`. Reducing Eevee render samples from 32 to 1 restored strict decoded-pixel equality under both dither levels, while both fresh 32-sample controls remained non-exact. The one-sample images are visibly noisy, so this locates a causal factor but is not a production-quality solution. It does not identify a Blender internal race or generalize beyond this profile.

Artifacts: `experiments/eevee-sampling-factorial-v0-1/results.json`, `experiments/eevee-sampling-factorial-v0-1/evidence/` and `research/2026-08-26-b17-eevee-sampling-factorial-result.md`.

## J-011 · Eevee sampling dose-response freeze

Type: live pre-experiment audit, 2026-08-26.

B17 supplied causal support for render sample count: both sample-1 cells were exact and both sample-32 cells non-exact across two dither levels. Visual inspection also showed that sample 1 is strongly noisy, so “use one sample” is not a production solution.

Question: at fixed dither 0, where does strict decoded-pixel reproducibility change across samples 1, 2, 4, 8, 16 and 32?

B18 freezes 12 fresh Blender runs, 1,728 planned frames, an interleaved run order, exact zero-tolerance per-level gates, a monotonic-boundary decision matrix and 13 negative cases before its runner exists. All six ReviewRenderSpecs are mechanically derived from the same frozen base by changing one integer; their expected byte hashes are precomputed and frozen.

Protocol: `research/2026-08-26-b18-eevee-sampling-dose-response-protocol.md`.

Status at freeze: no B18 runner or B18 render exists.

Formal execution observation:

- 12 clean Blender processes rendered 1,728 frames in the frozen order;
- exactness vector for samples `[1,2,4,8,16,32]`: `[F,T,F,F,F,F]`;
- exact frames: `143,144,140,137,137,133` of 144;
- failed pixels: `6,0,54,76,58,67`;
- maximum errors: approximately `30,0,7,4,2,1` eight-bit code values;
- every PNG pair remained byte-non-identical despite the decoded-exact sample-2 cell;
- 13/13 attacks reached their frozen reasons;
- source `.blend` and all frozen tool/config identities remained unchanged.

Verdict: `NON_MONOTONIC_OR_UNSTABLE`. Sample 1 failed to replicate B17 exactness, sample 2 happened to be exact, and higher levels were non-exact. The simple deterministic-threshold hypothesis is not supported. The inverse-like maximum-error ladder is consistent with sample averaging, but does not prove an internal mechanism. The next experiment needs more independent replicates at samples 1 and 2, not a favorable setting chosen from one pair.

Artifacts: `experiments/eevee-sampling-dose-response-v0-1/results.json`, `experiments/eevee-sampling-dose-response-v0-1/evidence/` and `research/2026-08-26-b18-eevee-sampling-dose-response-result.md`.

## J-012 · Eevee reproducibility-control inventory

Type: live exploratory real-Blender audit, 2026-08-26.

B18 falsified a simple sample-count boundary. Before selecting the next causal factor, a Blender 5.2 RNA inventory queried the exact receipt-bound B02 scene for sample, seed, random, noise, jitter, temporal, TAA, reprojection, shadow, ray, thread, GI, motion and dither controls.

The first attempt failed on a relative OCIO path and an invalid assumption that every RNA property exposes `is_array`. The second script run exited zero but Blender had rejected the specified OCIO file and fallen back; it was rejected as invalid. The accepted third run used the receipt-bound OCIO path/SHA and removed absolute local paths from its artifact.

Observation:

- Fast GI is enabled with 2 GI rays and 8 steps per ray;
- TAA temporal reprojection is enabled;
- fixed render threads report 8;
- Eevee ray tracing, camera bokeh jitter, light shadow jitter and volumetric shadows are disabled;
- the only area light has `use_shadow_jitter = false`;
- no explicit render seed/random control was exposed by the queried RNA domains.

This is an inventory, not a causal result. It makes Fast GI and TAA reprojection the next evidence-supported intervention pair. B19 should pre-register a 2×2 on/off factorial with a fresh on/on baseline.

Artifacts: `experiments/eevee-control-inventory-v0-1/results.json` and `research/2026-08-26-eevee-control-inventory.md`.

## Journal rule for future work

Every promoted result must record:

1. hypothesis or question;
2. frozen gate before execution;
3. exact real-Blender/runtime identity;
4. positive and negative observations;
5. falsified assumptions and non-claims;
6. machine-readable artifact paths;
7. the next unresolved boundary.
