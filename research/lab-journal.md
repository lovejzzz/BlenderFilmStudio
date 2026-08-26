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

## J-013 · Fast GI × TAA reprojection factorial freeze

Type: live pre-experiment freeze, 2026-08-26.

The accepted real-Blender control inventory narrowed the enabled candidates to Fast GI sampling and TAA temporal reprojection. B19 therefore freezes a 2×2 on/off factorial at 32 samples and dither 0, with two complete 144-frame runs per cell and a fresh on/on baseline.

Seven outcome labels distinguish Fast GI support, reprojection support, joint-disable support, either-disable support, no sufficient intervention, baseline/mixed instability and invalid execution. Fourteen negative cases are fixed before the configurator or runner exists.

Protocol: `research/2026-08-26-b19-gi-reprojection-factorial-protocol.md`.

Status at freeze: no B19 configurator, runner or render exists.

Formal execution observation:

- eight clean Blender processes rendered 1,152 frames in the frozen order;
- on/on: 131/144 exact, 97 failed pixels;
- GI off/reprojection on: 135/144 exact, 50 failed pixels;
- GI on/reprojection off: 133/144 exact, 96 failed pixels;
- both off: 131/144 exact, 73 failed pixels;
- every cell retained approximately one 8-bit code maximum error;
- 14/14 attacks reached the frozen reason;
- all source, tool and OCIO identities remained fixed.

Verdict: `NO_SUFFICIENT_INTERVENTION`. Disabling Fast GI or TAA reprojection separately or together does not restore strict pixel equality. The smaller failed-pixel count in one cell is not promoted as improvement from one stochastic pair. The next isolation boundary is process/frame-history state versus fresh-process rendering.

Artifacts: `experiments/eevee-gi-reprojection-factorial-v0-1/results.json`, `experiments/eevee-gi-reprojection-factorial-v0-1/evidence/` and `research/2026-08-26-b19-gi-reprojection-factorial-result.md`.

## J-014 · Eevee process-history isolation freeze

Type: live pre-experiment freeze, 2026-08-26.

B15-B19 all rendered complete timelines inside one Blender process. Since dither, sample count, Fast GI and TAA reprojection did not yield a production-quality exact setting, B20 moves the isolation boundary to prior-frame/process state.

Sentinels are not selected by visual preference: frame 1 is the startup anchor, and the other eleven frames are every frame that failed at least four of seven frozen 32-sample, dither-zero comparisons from B16-B19. The frozen set is `[1, 5, 20, 35, 38, 47, 83, 93, 103, 110, 114, 144]`.

Three `HISTORY` replicates each render 1-144 in one process. Three `FRESH` replicates render each sentinel in its own new process. All three within-mode pairs and all nine cross-mode pairs are compared for every sentinel with a zero-tolerance gate. The design totals 39 Blender processes and 468 frames; 17 negative cases and six decision labels are frozen before the B20 renderer, comparator or runner exists.

Protocol: `research/2026-08-26-b20-eevee-process-history-isolation-protocol.md`.

Status at freeze: no B20 tool or render exists. A favorable fresh-process result would locate an engineering boundary, not yet prove an internal Blender mechanism or a viable production workaround.

Formal execution observation:

- all 39 planned render processes had unique observed PIDs and produced 468 frames;
- HISTORY: 18/36 sentinel-pair comparisons exact, 118 failed pixels;
- FRESH: 26/36 exact, 56 failed pixels;
- cross-mode: 61/108 exact, 320 failed pixels;
- all three gates retained maximum error approximately one 8-bit code value;
- 18/18 implemented attacks reached their intended reason.

Verdict: `PROCESS_ISOLATION_NOT_SUFFICIENT`. A new Blender process for every frame did not restore strict equality: frames 5, 35, 47, 103 and 110 still split across the three FRESH replicates. The smaller descriptive FRESH count is not promoted to a probability claim. The next isolation boundary is the scene-linear in-memory Render Result versus display transform / PNG8 output.

Artifacts: `experiments/eevee-process-history-isolation-v0-1/results.json`, `experiments/eevee-process-history-isolation-v0-1/evidence/` and `research/2026-08-26-b20-eevee-process-history-isolation-result.md`.

## J-015 · Render Result / float-output interface inventory

Type: live exploratory real-Blender audit, 2026-08-26.

B20 moved the next boundary to scene-linear/high-precision output versus PNG8. The first probe used a wrong `.blend` path and Blender rejected it. The second rendered successfully but failed because it assumed `Render Result.pixels` was populated in background mode. That assumption was false.

The accepted probe used one real render call, then saved the same Render Result twice: PNG RGBA8 and ZIP OpenEXR RGBA32. Blender-bundled OIIO decoded the EXR as 960×540 RGBA float. The `Render Result` data-block itself reported `has_data=true`, but exposed zero size/channels/depth and an empty `pixels` sequence through this background RNA path.

Therefore B21 must not claim direct in-memory pixel access. It should pre-register a same-Render-Result dual-file experiment, verify exactly one render and two saves, and compare decoded EXR32 and PNG8 separately. The official Blender 5.2 color-management contract and the pinned B02 BuildPlan support treating the EXR path as scene-linear ACEScg output, while the actual exactness decision remains empirical.

Artifacts: `experiments/render-result-float-inventory-v0-1/results.json`, `experiments/render-result-float-inventory-v0-1/evidence/` and `research/2026-08-26-render-result-float-inventory.md`.

## J-016 · Same-Render-Result dual-output freeze

Type: live pre-experiment freeze, 2026-08-26.

The accepted J-015 probe changes the next question from an unsafe “read memory pixels” claim to a verified dual-save boundary. B21 carries all twelve B20 sentinels forward, with A/B/C fresh-process replicates per frame. Each of 36 processes must render exactly once and save that same Render Result as both PNG RGBA8 and ZIP OpenEXR RGBA32.

OIIO will compare all three pairs per frame separately for each format: 36 decoded comparisons per format, exact only at maximum error zero and zero failed pixels. Four valid labels distinguish PNG-path support, pre-PNG variation, PNG masking float variation and failure to reproduce; a fifth invalid label covers any control failure. Twenty-one negative categories are frozen.

Protocol: `research/2026-08-26-b21-dual-output-localization-protocol.md`.

Status at freeze: the formal B21 renderer, comparator and runner do not exist; no B21 frame has been rendered. Direct `Image.pixels` access remains explicitly excluded.

Three candidates were rejected before the accepted run. Two incorrectly required `Render Result.has_data=true` before the first save; the second also disproved a tentative filepath explanation. The third produced correct files but a Node validator compared serialized object key order instead of fields. All three stopped without an accepted result; the frozen gates did not change.

Formal execution observation:

- 36 unique Blender PIDs made exactly 36 render calls and 72 saves;
- EXR32 scene-linear: 21/36 decoded pairs exact, 328 failed pixels, maximum error `0.00634765625` linear units;
- PNG8 display output: 21/36 exact, 94 failed pixels, maximum error approximately one code value;
- all 36 EXR exact/non-exact pair labels matched the corresponding PNG labels;
- 21/21 attacks reached their frozen reason.

Verdict: `PRE_PNG_VARIATION_SUPPORT`. Variation is already present at the scene-linear float EXR boundary; the ACES display transform / PNG8 output path is not its sufficient origin. High bit depth preserves more differences but does not create determinism. The next causal candidate is the exposed fixed render-thread count, with an explicit caveat that Eevee GPU evaluation may not obey it.

Artifacts: `experiments/dual-output-localization-v0-1/results.json`, `experiments/dual-output-localization-v0-1/evidence/` and `research/2026-08-26-b21-dual-output-localization-result.md`.

## J-017 · Eevee fixed-thread-count freeze

Type: live pre-experiment freeze, 2026-08-26.

B21 proves that the variation already exists at the scene-linear EXR32 boundary. The accepted RNA inventory identifies one remaining exposed concurrency control: `scene.render.threads_mode=FIXED`, `threads=8`.

B22 freezes T01 versus T08 with three fresh-process replicates per cell across all twelve carried-forward sentinels. The interleaved design totals 72 Blender processes and 72 RGBA32 float EXRs. Each cell passes only at 36/36 exact decoded comparisons. Five decision labels and nineteen negative categories are fixed before any formal B22 tool exists.

The protocol explicitly warns that Blender's render-thread property may not serialize Eevee GPU work. Therefore a both-nonexact result would reject only this exposed control as sufficient, not concurrency in general.

Protocol: `research/2026-08-26-b22-eevee-thread-count-factorial-protocol.md`.

Status at freeze: no B22 configurator, renderer, comparator, runner or output exists.

The first post-freeze tool candidate (`780e470`) failed on its first real process. It assumed the source `.blend` already had dither 0, but the source correctly reported dither 1: the earlier B21 configurator had changed dither only in memory. The accepted candidate (`3db8467`) records the source thread state and explicitly fixes dither 0, Fast GI on and TAA reprojection on before rendering. No frozen gate changed.

Formal execution observation:

- all 72 planned render processes had unique observed PIDs;
- every process made one render call and one EXR32 save;
- T01 (`FIXED/1`): 19/36 exact, 364 failed pixels, maximum error `0.005615234375`;
- T08 (`FIXED/8`): 22/36 exact, 346 failed pixels, maximum error `0.00634765625`;
- 19/19 attacks reached their frozen reason.

Verdict: `THREAD_COUNT_NOT_SUFFICIENT`. One exposed render thread does not restore strict cross-process float equality. The observed 19-versus-22 difference is not an effect estimate, and this result does not show that concurrency is irrelevant: Blender's CPU-facing render-thread property may not serialize Eevee/Metal GPU execution.

Artifacts: `experiments/eevee-thread-count-factorial-v0-1/results.json`, `experiments/eevee-thread-count-factorial-v0-1/evidence/` and `research/2026-08-26-b22-eevee-thread-count-factorial-result.md`.

## J-018 · Same-process repeated-render boundary

Type: next hypothesis selected from B22, 2026-08-26.

B20 established that one fresh process per frame is not sufficient. B22 established that reducing the exposed render-thread count to one is not sufficient. The remaining experimental ambiguity is whether the float variation is introduced once during new-process/GPU initialization or can recur between repeated render calls inside the same initialized process.

The next protocol should compare repeated renders of the same twelve sentinels inside persistent Blender processes against fresh-process observations, retaining scene-linear RGBA32 EXR, zero tolerance and explicit render-call/file binding. A stable within-process cell plus unstable cross-process cell would support an initialization boundary; within-process non-exactness would move the boundary to each render invocation or later GPU work.

Status: hypothesis selected; protocol not yet frozen.

## J-019 · Same-process repeated-render protocol freeze

Type: live pre-experiment freeze, 2026-08-26.

B23 turns the J-018 hypothesis into a three-gate experiment. For every one of the twelve carried sentinels and A/B/C process replicate, a PERSIST process renders the same held frame three consecutive times without reloading the blend; an interleaved FRESH process renders it once. The frozen design totals 72 Blender processes, 144 render calls and 144 float EXRs.

Within-PERSIST contributes 108 same-PID comparisons. PERSIST cross-process contributes 108 same-ordinal comparisons, and FRESH contributes 36 cross-process comparisons. Five outcome labels distinguish process-initialization support, per-render recurrence, failure to reproduce, a mixed cross-process pattern and invalid execution. Twenty negative categories are fixed before any formal B23 renderer, comparator or runner exists.

Protocol: `research/2026-08-26-b23-eevee-repeated-render-boundary-protocol.md`.

Status at freeze: the B22 configurator is reused by frozen hash; no B23 renderer, comparator, runner or output exists.

Formal execution observation:

- all 72 planned Blender processes had unique observed PIDs;
- PERSIST made three same-frame render calls per PID and FRESH made one, totaling 144 RGBA32 EXRs;
- WITHIN_PERSIST: 59/108 exact, 3,630 failed pixels, maximum error `0.00634765625`;
- PERSIST_CROSS: 64/108 exact, 974 failed pixels, maximum error `0.00634765625`;
- FRESH_CROSS: 25/36 exact, 300 failed pixels, maximum error `0.005615234375`;
- frame 5 contributed 2,704 within-process failed pixels, while frame 114 was 9/9 exact;
- 20/20 attacks reached their frozen reason.

Verdict: `PER_RENDER_VARIATION_SUPPORT`. Strict float variation recurs between renders inside one initialized Blender process while the frame remains fixed. Process initialization is therefore not a sufficient origin. The result does not identify a race, GPU scheduling mechanism or perceptual defect.

Artifacts: `experiments/eevee-repeated-render-boundary-v0-1/results.json`, `experiments/eevee-repeated-render-boundary-v0-1/evidence/` and `research/2026-08-26-b23-eevee-repeated-render-boundary-result.md`.

## J-020 · Split exact provenance from perceptual production gates

Type: research-direction decision, 2026-08-26.

B15-B23 have falsified strict Eevee pixel determinism at 32 samples across dither, sample-factor experiments, Fast GI, reprojection, frame/process history, PNG versus EXR, exposed CPU thread count, process initialization and repeated render calls. Continuing to search for a favorable exact setting risks optimizing the benchmark rather than the filmmaking workflow.

The next study should preserve exact SceneSpec, BuildPlan, asset, runtime and structural hashes as the provenance gate, but evaluate new holdout renders under independently frozen numeric and perceptual pixel gates. B23 may nominate metrics and stress frames; it must not both choose and validate thresholds. Human visibility and production impact remain separate from bitwise identity.

Status: direction selected; threshold derivation and holdout protocol not yet frozen.

## J-021 · Production-repeatability envelope derivation and holdout freeze

Type: derivation audit plus live pre-experiment freeze, 2026-08-26.

The B24 derivation tool consumed 288 pre-holdout scene-linear EXR pairs, 36 PNG pairs and 36 auxiliary OIIO Yee comparisons. It selected simple outward ceilings containing every derivation pair: EXR maximum error 1/128, RMS 1/65536 and at most 512 zero-threshold changed pixels; PNG maximum error 0.003922, RMS 1/65536, at most 16 changed pixels and zero Yee failure pixels at explicitly recorded 100 cd/m² / 45° inputs.

The artifact is labeled `DERIVATION_ONLY_NOT_VALIDATION`. The holdout is selected arithmetically before rendering: all 24 frames where `frame mod 6 = 4`, none overlapping the twelve earlier sentinels. A/B/C fresh-process replicates yield 72 processes, one render and two saves each, and 72 pair comparisons per format.

All pairs must remain inside every ceiling; aggregate averages cannot hide an exceedance. Twenty-two negative categories and five decisions are frozen. A pass validates only this scene/profile's numeric repeatability envelope, not bitwise identity, human invisibility or a universal Blender tolerance.

Protocol: `research/2026-08-26-b24-production-tolerance-holdout-protocol.md`.

Status at freeze: the configurator and dual-output renderer are reused by hash; no B24 comparator, runner or holdout output exists.

The first formal tool candidate (`0a69c1c`) rendered all 72 processes and found both formats 72/72 inside the envelope, but the experiment correctly classified itself invalid: the runner implemented 23 negative attacks while the frozen contract required 22. The unregistered extra PID attack was removed, producing accepted tool commit `d60c749`; all holdout renders were then rerun rather than promoting the invalid outputs.

Accepted formal execution observation:

- 72/72 unique Blender PIDs, 72 render calls and 144 same-Render-Result saves;
- EXR32: 72/72 envelope pass, 70/72 strict exact, maximum error `0.0068359375`, maximum RMS `0.000012102088061225292`, maximum 17 changed pixels;
- PNG8: 72/72 envelope pass, 70/72 strict exact, maximum error `0.003921568393707275`, maximum RMS `0.0000072052046660281146`, maximum 5 changed pixels;
- OIIO Yee: zero failure pixels across all 72 PNG holdout pairs at the frozen nominal inputs;
- only frame 10 A-B and A-C were non-exact; B-C was exact in both formats;
- 22/22 attacks reached their frozen reason.

Verdict: `PRODUCTION_REPEATABILITY_ENVELOPE_SUPPORT`. The derivation envelope generalized to every independent holdout pair without threshold revision, while strict pixel identity remained 70/72. This supports a numeric static-frame repeatability contract for this scene/profile, not calibrated invisibility, temporal stability or universal Blender behavior.

Artifacts: `experiments/production-tolerance-holdout-v0-1/results.json`, `experiments/production-tolerance-holdout-v0-1/evidence/` and `research/2026-08-26-b24-production-tolerance-holdout-result.md`.

## J-022 · Temporal presentation and human review boundary

Type: next hypothesis selected from B24, 2026-08-26.

B24 closes the static numeric holdout question for this profile but does not answer the film question: whether sparse run-to-run differences become detectable flicker or motion instability during continuous playback. Static OIIO Yee comparisons with nominal viewing inputs cannot stand in for a calibrated moving-image review.

The next protocol should retain exact provenance/structure and the validated static envelope, then evaluate continuous full-sequence replicates with a frozen temporal-difference metric and blinded human playback review. Metric derivation and review acceptance must be separated from holdout validation, and reviewer disagreement must remain evidence.

Status: direction selected; temporal/reviewer protocol not yet frozen.

## J-023 · Complete-sequence temporal residual holdout

Type: derivation audit, live pre-registration and formal real-Blender holdout, 2026-08-26.

The temporal proxy defines signed cross-run residual `R_t = A_t - B_t`, then temporal residual delta `T_t = R_t - R_(t-1)`. This cancels motion shared by the two runs and measures how their disagreement changes from frame to frame. It remains a numerical proxy, not a visibility or cinematic-quality judgment.

Four retained 144-frame pairs at the candidate profile supplied 572 derivation transitions. Observed maxima were approximately one PNG8 code value, RMS `0.000018064404099505213` and 26 changed spatial pixels. Before any new holdout render, B25 froze ceilings of `2/255`, `1/32768` and 64 pixels, plus the previously validated B24 static PNG8 ceilings.

The formal holdout launched A, B and C as three unique Blender processes. Each rendered frames 1-144 sequentially, totaling 432 new render calls. Three pairings yielded 432 static frames and 429 adjacent transitions. Nineteen frozen negative categories all reached their intended reason.

Formal observation:

- temporal residual: 429/429 envelope pass, 354/429 strict exact, worst max delta `0.003921598196029663`, worst RMS `0.000015081015555200999`, worst 17 changed pixels;
- static B24 envelope: 430/432 pass, 394/432 strict exact;
- both static failures were frame 38: A-B and A-C each had the same 17-pixel cluster, while B-C was decoded-pixel exact at that frame;
- the cluster spans rows 112-117 and columns 267-272;
- human review remained `PENDING` by contract.

Verdict: `STATIC_ONLY_ENVELOPE_FAIL`. The temporal sub-gate passed every held-out transition, but the combined pre-registered gate failed because the static spatial ceiling was 16 pixels and two observations reached 17. The threshold was not widened. The next work is a frozen anonymized playback review plus a separate pre-registered isolation of the A-associated frame-38 event.

Artifacts: `experiments/temporal-residual-derivation-v0-1/results.json`, `experiments/temporal-residual-holdout-v0-1/results.json`, `experiments/temporal-residual-holdout-v0-1/evidence/`, `research/2026-08-26-b25-temporal-residual-holdout-protocol.md` and `research/2026-08-26-b25-temporal-residual-holdout-result.md`.

## J-024 · Lossless blinded temporal-review package

Type: live pre-registration, carrier experiment and interface audit, 2026-08-26.

B26 separates three layers that had previously been easy to conflate: playback-carrier integrity, observer-interface validity and actual human perception. The frozen protocol follows the current ITU-R BT.500-15 boundary: normally at least 15 observers, fewer explicitly informal, and people directly involved in development excluded from the formal sample. The balanced BFS target is 18 independent valid observers, with the six A/B/C permutations repeated three times.

Ordinary lossy H.264 was rejected as a formal carrier because compression could exceed the Blender residual being studied. An exploratory A-only lossless VP9 test first exposed an RGBA-versus-RGB comparator layout error; RGB was accepted only after verifying every source alpha sample was exactly opaque.

Formal package observation:

- A/B/C were independently encoded as VP9 Profile 1 `gbrp`, 960×540, 24 fps, six seconds, no audio;
- all three decoded to 144/144 exact RGB source frames, maximum error 0 and zero changed RGB pixels;
- carrier sizes were 27,496,119 / 27,510,630 / 27,492,939 bytes;
- 18 observer sessions were generated, with six permutations repeated exactly three times;
- observer-visible files use only `CLIP-01/02/03`; mappings remain sealed in git-ignored local work;
- overall salted mapping commitment: `540cc4c76193fc460945968e6919e5684d8a45fee58c5f8dcbcdfdee15a4379b`;
- 20/20 package attacks reached their intended reason.

A real in-app-browser audit found all three videos at ready state 4, 960×540 and six seconds, with no native controls or mapping tokens. One automated interface playback advanced only the 0/2→1/2 counter and left ratings disabled; the page was reloaded without creating a response.

Verdict: package `CARRIER_AND_INTERFACE_READY`; human status `PENDING`, formal responses 0, pilot responses 0. The owner may use OBS-01 only as an interface pilot and may not enter the formal N. Independent recruitment can proceed while B27 isolates the frame-38 history boundary.

Artifacts: `experiments/blind-temporal-review-v0-1/results.json`, `experiments/blind-temporal-review-v0-1/evidence/`, `research/2026-08-26-b26-blind-temporal-review-protocol.md` and `research/2026-08-26-b26-blind-temporal-review-package-result.md`.

## J-025 · Frame-38 direct-versus-history isolation

Type: live pre-registration, formal real-Blender intervention and post-hoc spatial localization, 2026-08-26.

B25 left one narrow mechanistic ambiguity: its A-associated 17-pixel failure occurred during a complete 1-144 render sequence, so earlier render calls might have caused or amplified the event. B27 froze two cells before any new output: twelve HISTORY processes rendering 1-38 in order and twelve DIRECT processes rendering only frame 38. A fixed interleaved schedule controlled coarse time order. The B25-B frame-38 PNG was selected as reference before execution because B and C had been decoded-pixel exact.

Formal observation:

- 24/24 unique Blender PIDs, 468 render calls and 468 output PNGs;
- HISTORY fixed-reference failures: 2/12; DIRECT failures: 3/12;
- two-sided Fisher exact `p=0.9999999999999999`, risk difference HISTORY−DIRECT `−0.08333333333333334`;
- HISTORY exact 10/12; DIRECT exact 9/12;
- 23/23 attacks reached their frozen reason.

Verdict: `FAILURE_REPRODUCED_NO_SIGNIFICANT_HISTORY_ASSOCIATION`. Rendering frames 1-37 first is not a sufficient explanation: three DIRECT processes produced the same failure without an earlier render call.

Post-hoc localization found exactly two decoded RGB modes. Every failing B27 target was bitwise equal after decode to B25-A frame 38; every passing target matched the fixed B25-B/C mode. The modes differ by the same 17 pixels at x 267-272 / y 112-117, each changed RGB channel +1 code and alpha unchanged. This localization is explicitly exploratory and does not alter the frozen primary decision.

The next machine boundary is same-PID repeated render at fixed frame 38, classifying every invocation against the two already-known mode hashes. Human review remains a separate B26 gate at 0/18 formal observers.

Artifacts: `experiments/frame-history-isolation-v0-1/results.json`, `experiments/frame-history-isolation-v0-1/evidence/`, `experiments/frame-history-isolation-v0-1/variant-analysis.json`, `research/2026-08-26-b27-frame-history-isolation-protocol.md` and `research/2026-08-26-b27-frame-history-isolation-result.md`.

## J-026 · Same-PID repeated frame-38 mode switching

Type: live pre-registration and formal real-Blender intervention, 2026-08-26.

B28 froze two decoded RGB modes from B27 before any new render. Twelve fresh persistent Blender processes each set frame 38 exactly once, then made twelve consecutive `bpy.ops.render.render(write_still=True)` calls without changing the frame, scene or source `.blend`. The primary unit was one PID, not one correlated image pair; support required known-mode switching in at least two independent PIDs. A third decoded hash would have expanded the mode space instead of being coerced.

Formal observation:

- 12/12 unique Blender PIDs and 144/144 render calls/output PNGs;
- all 12 PIDs contained both frozen REFERENCE and ALTERNATE modes;
- REFERENCE 116/144 and ALTERNATE 28/144;
- 42/132 adjacent calls changed mode: 22 REFERENCE→ALTERNATE and 20 ALTERNATE→REFERENCE;
- zero novel decoded RGB hashes;
- 23/23 attacks reached their frozen reason.

Verdict: `WITHIN_PID_MODE_SWITCH_SUPPORT`. Process initialization cannot be a sufficient mode-locking boundary for this event. The recurrence now sits at the render-invocation boundary or below. The result does not identify a particular Eevee, Metal, rasterization, TAA or GPU-scheduling mechanism and says nothing by itself about visibility or cinematic quality.

The ordinal ALTERNATE counts were 2, 1, 0, 1, 4, 2, 2, 2, 5, 3, 2 and 4. They remain descriptive because no ordinal-effect model was pre-registered. The next machine experiment must freeze a lower-level intervention before using these outcomes; B26 human review remains independently `PENDING`.

Artifacts: `experiments/repeated-frame-mode-switch-v0-1/results.json`, `experiments/repeated-frame-mode-switch-v0-1/evidence/`, `research/2026-08-26-b28-repeated-frame-mode-switch-protocol.md` and `research/2026-08-26-b28-repeated-frame-mode-switch-result.md`.

## J-027 · Pass-domain exploratory localization

Type: source-guided exploratory derivation, 2026-08-26.

The Blender 5.2 release source shows that each image render creates and later deletes a new Eevee `Instance`; image samples use index-driven Halton dimensions, and Metal/Vulkan performs a GPU flush/render step between samples. The Film documentation separately states that final film samples are weighted while data passes retain only the closest sample. These facts selected a pass-domain pilot; they did not predetermine its result.

One real Blender PID rendered frame 38 twelve times. Every invocation saved PNG8 and EXR32 multilayer from the same Render Result. Call 12 reproduced the frozen B28 ALTERNATE PNG. Its scene-linear Combined pass changed at 26 pixels in the same x 267-272 / y 112-117 cluster, and CryptoObject00 coverage changed at seven nested pixels. The cryptomatte IDs remained `BACK_WALL` and `FLOOR`; only their coverage weights changed. Depth, Normal and Position were 12/12 float exact.

Vector exposed a separate first-call transient across 518,255 pixels, then remained exact for calls 2-12. That transient did not change Combined or PNG mode, so it must not be conflated with the B28 event.

Status: `EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`. One PID and one coupled ALTERNATE event nominate a formal B29; they do not prove a film-resampling or rasterization mechanism. The confirmatory protocol must freeze the pass hashes, wall-floor coverage coupling, novel-mode behavior and an independent-PID support threshold before any formal output.

Artifacts: `experiments/pass-domain-pilot-v0-1/evidence/pilot.json`, `experiments/pass-domain-pilot-v0-1/pass-analysis.json` and `research/2026-08-26-b29-pass-domain-exploratory-pilot.md`.

## J-028 · Formal pass-domain localization and decoupling counterexamples

Type: pre-registered formal real-Blender confirmation attempt, 2026-08-26.

B29 froze the pilot-derived PNG, Combined, CryptoObject00, Depth, Normal, Position and secondary pass hashes before any formal renderer, classifier or runner existed. Twelve fresh PIDs each rendered frame 38 twelve times and saved PNG8 plus EXR32 multilayer from every single Render Result.

The first formal tool candidate completed all renders but correctly refused promotion: its report contained nine explicit pass-state fields while the validator mistakenly expected eight. The spec and scientific gates were unchanged; after a one-line validator correction, the entire first batch was discarded and all 144 renders were rerun in twelve new PIDs.

Accepted formal observation:

- 103/144 COUPLED_REFERENCE, 38/144 COUPLED_ALTERNATE and 3/144 DECOUPLED_PASS_PATTERN;
- 10/12 PIDs contained both coupled modes;
- the three decoupled calls were P01/04, P03/08 and P04/05;
- every decoupled call had REFERENCE PNG + REFERENCE Combined + ALTERNATE CryptoObject00;
- Depth, Normal and Position were 144/144 exact; no novel primary hash occurred;
- the frozen Vector call-1 transient reproduced in 12/12 PIDs; CryptoObject01/02 remained stable;
- 25/25 attacks reached their frozen reason.

Verdict: `DECOUPLED_PASS_PATTERN`. Although the supporting-PID count exceeded the frozen threshold, decoupling had explicit precedence. Crypto wall/floor coverage can enter its second mode without a Combined/PNG switch, so the pilot's one-to-one coverage-coupling hypothesis is falsified. All 38 Combined alternate calls did carry Crypto alternate, but the three Crypto-only events show that coverage alternate is not sufficient in this dataset.

PNG and scene-linear Combined labels still agreed 144/144, and the closest-sample geometry passes stayed stable. This narrows the observation without naming film resampling, rasterization, Metal, TAA or GPU scheduling as causal.

Next: derive a mechanism probe around Blender 5.2's hidden `override_pixel_jitter_sample` scene property, then freeze a natural-versus-fixed jitter holdout. Fixed jitter changes sampling quality, so it is an intervention, not yet a production remedy.

Artifacts: `experiments/pass-domain-localization-v0-1/results.json`, `experiments/pass-domain-localization-v0-1/evidence/`, `research/2026-08-26-b29-pass-domain-localization-protocol.md` and `research/2026-08-26-b29-pass-domain-localization-result.md`.

## J-029 · Fixed filter-jitter exploratory intervention

Type: source-guided exploratory derivation, 2026-08-26.

B29 left a render-invocation-level PNG/Combined mode switch and a partially decoupled CryptoObject00 coverage mode. Blender 5.2's hidden `override_pixel_jitter_sample` property supplied a lower-level intervention candidate, but fixing it changes the image-sampling target and therefore cannot be presumed to be a quality-preserving remedy.

Four fresh Blender PIDs each rendered frame 38 twelve times: NATURAL, CENTER `[0,0]`, POS_QUARTER `[0.25,0.25]` and NEG_QUARTER `[-0.25,-0.25]`. NATURAL reproduced both frozen decoded modes, seven REFERENCE and five ALTERNATE. Each fixed cell was 12/12 internally exact and produced its own new decoded RGB hash.

The prewritten exploratory selection rule nominates CENTER for a formal natural-versus-fixed intervention. Its stability observation has a large explicit cost: against the natural REFERENCE output, CENTER changes 131,779 of 518,400 pixels across the full frame, with maximum 46 PNG code values and normalized RMS about `0.00369689`. The other fixed points also differ across the full frame. This is a different sampling result, not a 17-pixel repair.

Status: `EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`. One PID per cell cannot establish cross-process stability or a causal mechanism, and no anti-aliasing, visibility or cinematic-quality claim is made. The next protocol must freeze independent PID counts, exact CENTER identity, natural recurrence, novel-mode handling and failure precedence before formal tools or outputs exist.

Artifacts: `experiments/fixed-jitter-derivation-v0-1/results.json`, `experiments/fixed-jitter-derivation-v0-1/analysis.json` and `research/2026-08-26-b30-fixed-jitter-derivation.md`.

## J-030 · Formal natural-versus-CENTER jitter intervention

Type: pre-registered formal real-Blender intervention, 2026-08-26.

B30 froze CENTER `[0,0]`, its derivation decoded hash, two natural hashes, a 24-process interleaved schedule and failure precedence before the formal renderer, classifier or runner existed. Twenty-four fresh Blender PIDs then executed 288 renders: twelve NATURAL and twelve CENTER processes, twelve repeated frame-38 calls each.

Formal observation:

- CENTER: 12/12 exact PIDs and 144/144 calls at the frozen CENTER hash; no novel hash or transition;
- NATURAL: 10/12 switching PIDs, 125 REFERENCE and 19 ALTERNATE calls;
- NATURAL adjacent transitions: 30/132, split 15 in each direction;
- no novel decoded hash in either cell;
- 24/24 unique PIDs and 25/25 negative attacks.

Verdict: `FIXED_JITTER_STRICT_STABILITY_SUPPORT`. A factory-startup independent classifier rerun reproduced the accepted classification byte-for-byte. The result supports strict CENTER identity on this scene/frame/build/backend/machine while the active control reproduces the natural switching event.

The frozen intervention cost remains central: CENTER changes 131,779 of 518,400 decoded pixels relative to natural REFERENCE, over the full frame, with maximum 46 PNG code values. The property also drives more than filter U/V dimensions in Blender source. Therefore this is a sufficient intervention for the observed instability, not a single-variable causal proof or a production-quality recommendation.

Next: derive and pre-register a high-sample/spatial-reference quality experiment that separates repeatability from aliasing, scene-linear error and temporal perception. B26 human review remains `PENDING`.

Artifacts: `experiments/fixed-jitter-intervention-v0-1/results.json`, `experiments/fixed-jitter-intervention-v0-1/evidence/` and `research/2026-08-26-b30-fixed-jitter-intervention-result.md`.

## J-031 · Fixed-jitter scene-linear quality-cost derivation

Type: exploratory real-Blender quality derivation, 2026-08-26.

B30 supported strict CENTER stability but left a full-frame sampling change. B31 rendered NATURAL32 A/B, CENTER32 A/B and NATURAL1024 A/B on frames 37, 72 and 103 in six fresh Blender PIDs. The pixelwise mean of the two 1024-sample EXRs is explicitly a reference proxy, not truth; a rejected 2×/256 spatial pilot cost 73.61 seconds for one frame, so the accepted proxy truthfully records that it has no spatial supersampling.

The edge rule was written before analysis output: top 5% of RGB Euclidean central-difference magnitude in the dual-reference mean. CENTER/NATURAL edge RMSE ratios were `2.2360`, `2.1876` and `2.2623`; global ratios were `1.4673`, `1.4211` and `1.4215`. Non-edge ratios stayed near `1.08–1.09`.

The dual 1024 reference was exact on two frames and had edge A/B RMSE about `0.00000566` on frame 72, far below candidate errors around `0.012–0.032`. CENTER32 A/B was float exact on all three frames; NATURAL32 had one very small A/B difference. This separates two properties that must not be conflated: CENTER is more repeatable but has materially larger edge-reference error in every derivation frame.

Status: `EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`. No perceptual, temporal, aliasing-visibility or cinematic-quality claim is made. The nominated holdout uses unseen frames 10, 44, 86 and 120; a dual-reference reliability gate of 5% of NATURAL error; and a conservative all-frame CENTER/NATURAL edge RMSE ratio gate of 1.5, frozen before formal outputs.

Artifacts: `experiments/sampling-quality-derivation-v0-1/results.json`, `experiments/sampling-quality-derivation-v0-1/analysis.json` and `research/2026-08-26-b31-sampling-quality-derivation.md`.

## J-032 · Formal fixed-jitter edge-reference cost holdout

Type: pre-registered formal real-Blender quality-proxy holdout, 2026-08-26.

B31 froze four unseen frames, six fresh cell/replicate PIDs, a dual NATURAL1024 reference proxy, top-5-percent RGB-gradient edge masks, a 5% reference reliability ceiling and an all-frame CENTER/NATURAL edge RMSE ratio gate of 1.5 before formal tools or outputs existed.

Formal observation:

- six unique PIDs, 24 EXR32 renders and 23/23 attacks;
- reference reliability ratios `0`, `0.00045276`, `0`, `0.00055488`, all below `0.05`;
- CENTER/NATURAL edge RMSE ratios `2.8636`, `2.3717`, `2.1693`, `2.4743`;
- 4/4 frames exceeded 1.5 and no frame reversed below 1.0;
- global ratios `1.4005–1.5581`; non-edge ratios `1.0767–1.0907`;
- CENTER32 A/B float exact on every frame.

Verdict: `EDGE_REFERENCE_COST_SUPPORT`. A fresh factory-startup analyzer rerun reproduced the accepted analysis byte-for-byte. This confirms a scene-linear high-gradient reference-error cost on the frozen holdout, not a calibrated visible-quality multiplier.

The engineering implication is that single-point CENTER should not become a production default merely because it is stable. The next candidate is a deterministic multi-jitter ensemble: several stable fixed-offset renders averaged in scene-linear space, explicitly trading 4×/8× render cost for restored subpixel coverage. It must receive its own derivation, holdout, temporal and human gates.

Artifacts: `experiments/sampling-quality-holdout-v0-1/results.json`, `experiments/sampling-quality-holdout-v0-1/evidence/` and `research/2026-08-26-b31-sampling-quality-holdout-result.md`.

## J-033 · Deterministic four-point jitter quadrature derivation

Type: exploratory real-Blender engineering derivation, 2026-08-26.

B32 replaced the single CENTER point with four symmetric fixed offsets at every combination of ±0.25, rendered each in a fresh process and averaged equal weights in scene-linear RGB. A/B used eight unique PIDs and 24 new EXR renders on B31 derivation frames 37, 72 and 103.

The composite A/B outputs were float exact on all three frames. Q4/NATURAL edge-reference RMSE ratios were `1.2509`, `1.1887` and `1.2751`; Q4/CENTER ratios were `0.5594`, `0.5434` and `0.5636`. Global Q4/NATURAL ratios were only `1.0224–1.0512`. Observed render time was `4.093×` NATURAL32.

A fresh factory-startup Blender analyzer rerun reproduced `analysis.json` byte-for-byte. Three negative boundary attacks were rejected: invalid point `Q9`, changed frame set `37/72/104`, and a non-empty output directory. These checks support artifact reproducibility and input freezing; they do not add perceptual evidence.

Status: `EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`. Four points recover much of CENTER's edge-reference loss while retaining deterministic A/B outputs, but remain 19–28% above NATURAL32 edge error and cost roughly four renders. No unseen-frame, temporal or perceptual claim is made.

Next: compare a preselected uniform 8-point stratified candidate on the same derivation frames. Candidate selection must include both numerical gain and measured 4×/8× cost before any formal holdout.

Artifacts: `experiments/quadrature-derivation-v0-1/results.json`, `experiments/quadrature-derivation-v0-1/analysis.json` and `research/2026-08-26-b32-quadrature-derivation.md`.

## J-034 · Deterministic eight-point stratified derivation

Type: preregistered exploratory real-Blender cost–quality derivation, 2026-08-26.

Before new tools or outputs existed, B32.1 froze a center-symmetric eight-point checkerboard candidate, equal scene-linear weights, frames 37/72/103, 16 fresh A/B PIDs, an exact-repeatability gate, a per-frame non-regression gate, a 10% mean Q8-over-Q4 improvement gate, and a per-frame Q8/NATURAL ceiling of 1.10 for the near-natural label.

The real Blender 5.2 run completed 48 EXR32 renders in 16 unique PIDs. Q8 A/B composites were float exact on all three frames. Q8/NATURAL edge-reference ratios were `0.9409`, `0.9260` and `0.9478`; Q8/Q4 ratios were `0.7521`, `0.7790` and `0.7433`. Mean Q8/Q4 was `0.75816`, while observed render time was `1.9545×` Q4 and `7.9996×` NATURAL32.

The preregistered decision is `PROMOTE_Q4_Q8_COST_CURVE_NEAR_NATURAL`. A fresh factory-startup analysis rerun was byte exact. Five boundary attacks rejected an invalid point, changed frames, non-empty output, tampered weight and duplicate PID.

Status remains `EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`. Ratios below one against the proxy do not establish superior visible quality, and the reused derivation frames cannot confirm generalization. Q4 and Q8 now require a new-frame formal holdout that preserves the explicit 4×/8× cost axis.

Artifacts: `experiments/stratified8-derivation-v0-1/results.json`, `experiments/stratified8-derivation-v0-1/analysis.json`, `research/2026-08-26-b32-stratified8-derivation-protocol.md` and `research/2026-08-26-b32-stratified8-derivation-result.md`.

## J-035 · Formal quadrature cost holdout attempt 1 invalidated by a mask tie

Type: preregistered formal real-Blender failure, 2026-08-26.

The first B32 formal run completed all 28 unique render PIDs and 112 EXR32 outputs for frames 22, 59, 97 and 136. The analyzer then stopped before any candidate metric decision because the preregistered edge-mask contract required exactly 25,920 pixels, while frame 22's `quantile(0.95)` plus `>=` selected 25,921.

Post-failure diagnosis found 25,919 values strictly above the cutoff and two values exactly tied at it. The other three frames had exactly 25,920. This falsifies the hidden assumption that a quantile threshold plus `>=` always produces exact top-k cardinality.

Verdict: `IDENTITY_OR_DESIGN_INVALID`; status `FORMAL_ATTEMPT_INVALID_BEFORE_METRIC_DECISION`. No Q4/Q8 quality conclusion was emitted, and the completed renders are not relabeled as a confirmation. The runner had not reached its formal attack stage.

Next: preregister v0.2 with a deterministic exact top-k rule ordered by gradient descending and flattened pixel index ascending. The v0.1 failure and all execution evidence remain preserved.

Artifacts: `experiments/quadrature-cost-holdout-v0-1/results.json`, `experiments/quadrature-cost-holdout-v0-1/evidence/edge-mask-tie-diagnostic.json` and `research/2026-08-26-b32-quadrature-cost-holdout-invalid-attempt.md`.

## J-036 · Formal exact-top-k quadrature cost–quality holdout

Type: preregistered formal real-Blender holdout after preserved invalid attempt, 2026-08-26.

Before v0.2 tooling or outputs existed, a new protocol froze frames 31/67/109/143 and replaced the ambiguous quantile mask with an exact total order: gradient descending, flattened pixel index ascending, first 25,920 pixels. No v0.1 output or frame was reused. The quality gates stayed unchanged.

The clean v0.2 run completed 28 unique render PIDs, 112 EXR32 outputs and 29/29 attacks. Reference reliability ratios were at most `0.00052768`. Q4 and Q8 composite A/B RMSE were float exact on every frame.

Q4/NATURAL edge ratios were `1.2456–1.3010` with mean `1.27059`. Q8/NATURAL edge ratios were `0.9448–0.9574` with mean `0.95102`. Q8/Q4 ratios were `0.7359–0.7644` with mean `0.74868`. Observed render-time ratios were `4.065×` for Q4 and `8.142×` for Q8 relative to NATURAL32.

All five component gates passed, so the preregistered decision is `COST_QUALITY_CURVE_SUPPORT`. A fresh factory-startup analyzer rerun reproduced the accepted analysis byte-for-byte.

The support is limited to scene-linear reference-proxy error on four new frames. It does not establish visible superiority, temporal stability, motion-blur correctness, cinematic acceptability or optimal quadrature. The next boundary is a consecutive-frame temporal and blind-human evaluation retaining the 4×/8× cost axis.

Artifacts: `experiments/quadrature-cost-holdout-v0-2/results.json`, `experiments/quadrature-cost-holdout-v0-2/evidence/quality-analysis.json` and `research/2026-08-26-b32-quadrature-cost-holdout-v02-result.md`.

## J-037 · Consecutive-frame Q4/Q8 temporal-error derivation

Type: preregistered exploratory real-Blender temporal derivation, 2026-08-26.

B33 froze frame 121–128, 28 fresh cell-replicate processes, 224 scene-linear EXR renders, three temporal-error domains and exact-top-k total ordering before its renderer, analyzer or runner existed. Temporal error delta was defined as the frame-to-frame change in candidate-minus-reference error, so shared scene motion is not mistaken for flicker by directly differencing pictures.

All derivation-validity gates passed: 28 unique PIDs, 224/224 outputs, 10/10 attacks, finite positive denominators, Q4/Q8 frame and transition A/B float exactness, and maximum REFERENCE1024 reliability ratio `0.00794548` below the frozen `0.10` ceiling. A factory-startup independent analyzer rerun was byte exact.

Q4/NATURAL mean temporal RMSE ratios were `1.4340` global, `1.7211` on the spatial-edge union and `1.8231` on reference-motion top-k. Q8/NATURAL means were `0.8177`, `0.9053` and `0.9480`; Q8 maxima were `0.8344`, `0.9425` and `0.9885`. Q8/Q4 means were `0.5704`, `0.5261` and `0.5202`. Observed render-time ratios were `3.985×` Q4 and `8.008×` Q8 relative to NATURAL32.

Decision: `TEMPORAL_DERIVATION_USABLE_FOR_THRESHOLD_FREEZE`, with status `EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`. Q4 is a useful counterexample to “more deterministic renders automatically improve time quality”: four times the render cost increased this proxy on the derivation interval. Q8 is a formal candidate, not yet confirmed; no visible-flicker, human-preference, motion-blur or cinematic claim is made.

Next: freeze a disjoint eight-frame formal holdout and conservative per-transition Q8/NATURAL plus Q8/Q4 gates before formal tooling or output. Human review remains independently pending.

Artifacts: `experiments/quadrature-temporal-derivation-v0-1/results.json`, `experiments/quadrature-temporal-derivation-v0-1/evidence/temporal-analysis.json`, `research/2026-08-26-b33-quadrature-temporal-derivation-protocol.md` and `research/2026-08-26-b33-quadrature-temporal-derivation-result.md`.

## J-038 · Formal Q8 consecutive-frame temporal-proxy holdout

Type: preregistered formal real-Blender temporal-proxy holdout, 2026-08-26.

After B33 derivation was committed, the formal protocol froze a disjoint frame 74–81 interval and round ceilings before formal tooling or output: Q8/NATURAL every-transition maxima of 1.00 global and 1.10 for edge/motion; Q8/Q4 maximum 0.75 per observation and mean 0.65 per domain; reference reliability 0.05; exact frame/temporal A/B repeatability.

The real Blender 5.2 run completed 28 unique PIDs, 224 new EXR32 renders and 12/12 attacks. The independent factory-startup analyzer rerun was byte exact. Maximum reference reliability ratio was `0.00118050`; all Q4/Q8 frame composites and temporal deltas were A/B float exact.

Q8/NATURAL means were `0.8231` global, `0.9023` spatial-edge and `0.9497` reference-motion. Maxima were `0.8856`, `0.9832` and `1.0397`; only motion transition 75→76 exceeded NATURAL, while remaining below the frozen 1.10 gate. Q8/Q4 means were `0.6289`, `0.6000` and `0.5950`; maximum `0.7386`, `0.7233` and `0.7224`. Q4/NATURAL means remained above one in every domain. Cost ratios were `4.009×` Q4 and `7.996×` Q8 relative to NATURAL32.

Verdict: `Q8_TEMPORAL_PROXY_HOLDOUT_SUPPORT`. The result is intentionally reported with its narrow margins: global Q8/Q4 max was only `0.01144` below its 0.75 ceiling, and motion Q8/NATURAL rose above one on one transition. This supports the frozen proxy envelope, not universal temporal superiority.

No visible-flicker, human-preference, motion-blur, codec or cinematic claim is promoted. Next: publish the B33 evidence and move to an independently completed anonymized human review rather than treating automation as the viewer.

Artifacts: `experiments/quadrature-temporal-holdout-v0-1/results.json`, `experiments/quadrature-temporal-holdout-v0-1/evidence/temporal-analysis.json`, `research/2026-08-26-b33-quadrature-temporal-holdout-protocol.md` and `research/2026-08-26-b33-quadrature-temporal-holdout-result.md`.

## J-039 · NATURAL / Q4 / Q8 independent-human review package

Type: preregistered real-Blender carrier, blinding and response-chain experiment, 2026-08-26.

B34 froze a six-second frame 1–144 source interval, 13-process NATURAL/Q4/Q8 schedule, scene-linear equal-weight compositing, pinned ACES 2 display transform, lossless RGB-exact carrier rule, 18-observer six-permutation schedule, response hash/ledger/unblind order and formal decision gates before any B34 tooling or output.

The real Blender 5.2 run completed 13 unique source PIDs, 1,872 renders and 1,872 fresh float32 EXR. It then produced 432 scene-linear composite EXR and 432 display PNG. All three VP9 Profile 1 `gbrp` carriers decoded 144/144 RGB frames exactly, with maximum error and changed-pixel count both zero. Twenty-four of twenty-four frozen attacks rejected.

Independent audit did not pass on its first invocation: a report-only variable-name error raised `ReferenceError` after file checks and before output. The failure was retained, the audit tool was fixed in commit `00cc6a6`, and a clean rerun checked 1,872 source files, 432 composites, 432 display PNG, 432 decoded frames and 18 sessions. A separate factory-startup Blender audit recomputed all 432 float composites at maximum error `0.0`; a second run was byte exact. Fresh carrier re-decodes also reproduced the three formal roundtrip reports byte-for-byte.

A 1920×1080 real-browser interface pilot confirmed 960×540 video geometry, no native controls, no mapping strings, zero console errors and two complete CLIP-01 plays at decoded 144 / dropped 0 each. Rating remained locked until the second ended event. Because the operator is a developer, this is interface evidence only.

Status: `CARRIER_AND_INTERFACE_READY`; human status: `HUMAN_REVIEW_PENDING`, 0/18. Synthetic analyzer fixtures are labeled attack-test-only and cannot be counted as observers. No Q8 preference, no visible no-difference result and no cinematic-quality claim has been emitted.

Artifacts: `experiments/human-quadrature-review-v0-1/results.json`, `experiments/human-quadrature-review-v0-1/evidence/`, `research/2026-08-26-b34-human-quadrature-review-protocol.md` and `research/2026-08-26-b34-human-quadrature-review-package-result.md`.

Note: responsive browser recheck after the superseding finding confirmed the desktop page at 1440 × 1000 with no horizontal overflow. The requested 390 × 844 temporary viewport override did not change the live viewport (it remained 1440 × 1000), so no mobile-browser pass is claimed from that run; the static responsive breakpoint remains build-checked only.

## J-040 · Public carrier-hash join falsifies B34 blinding sufficiency

Type: post-package adversarial blinding audit, 2026-08-26.

Before distributing B34, a new audit tested whether “no source labels in the observer package” remained sufficient after package evidence was committed publicly. It used no sealed mapping, salt or analyzer output. The public manifest supplied method → carrier SHA; each observer HTML supplied CLIP label → the same carrier SHA.

The join recovered NATURAL32, QUADRATURE4 and STRATIFIED8 for all 18/18 sessions. Verdict: `PUBLIC_HASH_JOIN_UNBLINDS_ALL_SESSIONS`; disposition: `DO_NOT_COLLECT_FORMAL_HUMAN_RESPONSES_FROM_B34_PUBLIC_EVIDENCE_STATE`.

This does not invalidate B34's 1,872 source renders, 432 exact composites, three RGB-exact carriers, UI telemetry or response-chain engineering. It invalidates the assumption that these already-public carrier identities can support a repo-aware blind human study. B34 formal human count remains 0/18.

Next: a new visual realization must be generated. Protocol and non-unblinding tooling may remain public, but method-labelled output/carrier/decoded-frame/pixel hashes must be withheld until all 18 preregistered responses are hash-locked. A public precollection commitment may bind the withheld package without revealing those identities.

Artifact: `experiments/human-quadrature-review-v0-1/evidence/public-hash-unblinding-audit.json`.

## J-041 · B35 delayed-disclosure human review preregistration

Type: preregistered blinding repair and new-realization experiment, 2026-08-26.

Before any B35 tool or output existed, commit `eff96fa` froze spec SHA-256 `2a6af8e5d084b29dd51fc69acb3a96223cae477c85c815ea48c2667781ebf83f`. B35 keeps the 18-observer balanced NATURAL/Q4/Q8 decision rules, but creates a method-symmetric new visual realization by requiring the active camera's original 50.0 mm lens and setting it to 52.0 mm in memory in every fresh process.

The central intervention is disclosure order. All method-labelled source/output/carrier/decoded/display identities, mappings, session bindings and open-collection responses remain in ignored private work. Before collection and before every accepted response, a sensitive-hash registry must have zero matches in the tracked/public tree. Any pre-close method-to-CLIP join invalidates the whole study.

The spec distinguishes measured engineering facts, inference, independent-human judgment and unknowns. It explicitly does not claim operator double-blinding, BT.500 laboratory compliance or cinematic quality.

Artifacts: `specs/human-quadrature-review-spec.v0.2.json` and `research/2026-08-26-b35-delayed-disclosure-human-review-protocol.md`.

## J-042 · B34 raw-work deletion rejected; evidence retained

Type: destructive-action preflight and negative operation result, 2026-08-26.

The only proposed deletion target was preregistered at commit `e8406a9`: B34's ignored `experiments/human-quadrature-review-v0-1/work`, measured at 4,714,288 KiB and 3,247 files. The first deletion command was rejected before execution by the machine safety layer because `rm -rf` style commands are not permitted.

No file was deleted, moved or modified, and no equivalent bypass was attempted. Available space remained 15,340,596 KiB, above B35's frozen 8 GiB preflight threshold, so B34 raw work is retained. This is an operation failure/constraint, not a completed cleanup.

Artifact: `research/2026-08-26-b34-raw-work-cleanup.md`.

## J-043 · B35 real-Blender private package and zero-leak public commitment

Type: preregistered real-Blender delayed-disclosure package experiment, 2026-08-26.

After preregistration commit `eff96fa` and tool-freeze commit `430a05c`, B35 ran 13 unique Blender 5.2 source PIDs and 1,872 renders under the shared 50.0→52.0 mm in-memory lens intervention. It produced 432 scene-linear composites, 432 display PNG and three lossless carriers. All 432 decoded carrier frames were RGB exact; all 432 display identities and all three carrier identities differed from B34.

Sixteen of sixteen frozen attacks passed. The sensitive registry contained 3,226 values. An injected sensitive value was detected on the attack public surface, while the clean tracked/public state had zero matches and zero tracked private paths. The public artifact itself also matched zero registry values.

Independent Node audit rebound 1,872 source EXR, 432 composites, 432 display PNG, 432 decoded frames and 18 sessions. Two factory-startup Blender processes independently recomputed all 432 float composites with maximum error 0.0 and produced byte-identical reports.

Only salted package commitment `5ab10b6e97fa1fda1480b48582d7b723cce651aa8bf34f8d5e2e20365c8b5001` and registry commitment `c1ce83b0a168327b01738a3cd8db1074952cc0bd3804f43fec690ae85b9ea2e9` are public. Method-labelled identities remain private. Status: `PRIVATE_PACKAGE_VALIDATED_COLLECTION_NOT_OPEN`; human evidence remains 0/18; cinematic evidence is not tested.

Artifacts: `experiments/human-quadrature-review-v0-2/precollection-commitment.json` and `research/2026-08-26-b35-delayed-disclosure-package-result.md`. Full evidence remains in ignored private work until collection close or frozen abort.

## J-044 · B35 real-browser observer-interface pilot

Type: developer-operated interface and playback-gate pilot, 2026-08-26.

The ignored private `OBS-01` session was served from a local HTTP origin and opened in the real in-app browser at a measured 1440-pixel desktop viewport. The page exposed no native video controls, no repository links and none of the forbidden method or mapping strings. The rendered video rectangle measured exactly 960 × 540 CSS pixels.

All three anonymized clips reached 2/2 complete plays. The interface-wide dropped-frame counter remained 0, the completed active clip reported 144 decoded frames and 0 dropped frames, and the play button remained disabled after the second completion. On the first CLIP-01 run, telemetry observed after decoding had already begun reported 140 decoded frames; the frozen validity rule requires a positive decoded-frame delta and zero dropped frames, not an exact 144 counter, so this is retained rather than normalized away.

No rating, observer metadata or pairwise judgment was entered. The response remained `UNLOCKED · HUMAN RESULT PENDING`, so human count stays 0/18. Because the operator directly develops BFS, this is an interface pilot only and cannot contribute to any visual-stability or preference decision.

Status: `INTERFACE_PILOT_PASS`; human evidence: `HUMAN_REVIEW_PENDING`, 0/18. The remaining precollection operation is to publish the exact final source state and rerun the 3,226-value public-surface leak audit before any private session is distributed.

## J-045 · B36 first real-Blender run invalidated by an analyzer identity bug

Type: preregistered real-Blender invalid attempt, 2026-08-26.

B36 preregistered six unique Blender processes around one controlled `Text.use_module = true` canary: two `--enable-autoexec`, two `--disable-autoexec` and two factory-startup defaults. The first real run observed the intended side-effect pattern, but the frozen analyzer stopped before attacks because it expected `bpy.app.version_string == "5.2.0"`; Blender returned `"5.2.0 LTS"`, which was also the exact value frozen in the spec.

The runner emitted `IDENTITY_OR_DESIGN_INVALID`, and no support verdict was promoted. The six-process artifact was renamed and retained with SHA-256 `e5e8f17ec7d8b4f245175f641c6cea10a5616ad0b384c157359936d9e301ca18`. The repair changed only the analyzer's expected version string to the preregistered value.

Artifact: `experiments/autoexec-boundary-v0-1/attempt-1-invalid.json`.

## J-046 · B36 registered-Text autoexec flag boundary

Type: repaired full rerun of a preregistered real-Blender security-boundary experiment, 2026-08-26.

After the one-line identity repair was committed separately, six new unique Blender 5.2 PIDs ran from a fresh work directory. ENABLE_A/B both executed the registered Text and wrote the exact non-secret marker before the trusted probe. DISABLE_A/B and both factory-default cells wrote no marker, while all six command-line trusted probes ran and exited 0. The four blocked cells reported `bpy.app.autoexec_fail == true`; the enabled cells reported false.

The source `.blend` was byte unchanged, 7/7 analyzer attacks were rejected, and an independent audit recomputed source identity, all gates and all attacks. Verdict: `REGISTERED_TEXT_AUTOEXEC_FLAG_BOUNDARY_SUPPORT`.

This is a narrow CLI control, not an OS sandbox. It does not prove untrusted `.blend` parsing safe and does not isolate files, network, subprocesses, memory, GPU, syscalls or secrets. Next: an OS-worker containment canary or an explicit macOS-platform limitation.

Artifacts: `experiments/autoexec-boundary-v0-1/results.json`, `experiments/autoexec-boundary-v0-1/audit.json` and `research/2026-08-26-b36-autoexec-boundary-result.md`.

## J-047 · B37 deprecated SBPL containment and inherited-environment counterexample

Type: preregistered real-Blender OS-capability canary, 2026-08-26.

The platform preflight recorded macOS 26.5.1 build 25F80, a byte-pinned `/usr/bin/sandbox-exec`, its system-man-page deprecation, and the absence of an App Sandbox entitlement from the signed Blender 5.2 app. B37 therefore froze a prototype claim only, never a production sandbox claim.

Six unique Blender PIDs ran the same trusted Python canary. The two unsandboxed baselines demonstrated all 12 expected capabilities. In four sandboxed processes, worker-local report writes remained 6/6 available, while sibling control read/write, loopback and `/usr/bin/touch` exec were blocked 16/16 with `PermissionError`. Only the two unsandboxed loopback nonces reached the independent local server.

The frozen counterexample also appeared: both SBPL processes that inherited the fixed fake secret could read it. When the launcher removed that variable before exec, visibility fell to 0/2. OS capability policy cannot sanitize data already inherited from the parent.

Nine of nine analyzer attacks were rejected and an independent audit reproduced every gate. Verdict: `DEPRECATED_SBPL_CANARY_SUPPORT_WITH_ENV_COUNTEREXAMPLE`.

This does not promote deprecated `sandbox-exec` to a supported worker backend. The profile intentionally starts from `allow default`; parser memory safety, GPU, DoS, broad IPC/syscalls, real secrets and external networking remain untested. Next: freeze a supported worker-backend decision between a disposable VM/container and a signed App Sandbox host.

Artifacts: `experiments/worker-containment-v0-1/results.json`, `experiments/worker-containment-v0-1/audit.json` and `research/2026-08-26-b37-worker-containment-result.md`.

## J-048 · B38 backend-agnostic worker launch contract

Type: preregistered pure contract compiler/analyzer experiment, 2026-08-26.

After B36 established the explicit `--disable-autoexec` boundary and B37 retained both deprecated-SBPL capability blocks and the inherited-environment counterexample, B38 froze the launcher semantics that every future backend must preserve. It deliberately launched no Blender process and no container.

Three WorkerRequests and deep-reordered clones produced 3/3 equal canonical request hashes and 3/3 equal self-hashed WorkerLaunchPlans. Every plan contained exactly 11 allowlisted environment keys and excluded the parent fake-secret canary. The frozen command contract used no shell, pinned the Blender identity, required background/factory/disable-autoexec/offline/Python-failure flags, and allowed only one read-only input plus one writable output mount.

The future-container policy is now data-bound to digest-only image identity, pull-never, read-only rootfs, network none, non-root, drop-all caps, no-new-privileges and PID/memory/CPU limits. This is contract evidence only; none of those controls was claimed as runtime-enforced.

Synthetic admissions accepted 140 GiB minus 20 GiB but blocked a dirty output root and 119 GiB minus 20 GiB. The actual host observation was also `BLOCKED`: 24,230,027,264 B available minus 21,474,836,480 B projected left only 2,755,190,784 B, below the 100 GiB reserve. No override was applied.

Only the `SUCCEEDED` receipt was promotable; nonzero, timeout and cancelled receipts were not. Twenty-five of twenty-five attacks passed, and an independent audit reproduced all plans, admissions, receipts and attacks exactly.

Verdict: `WORKER_LAUNCH_CONTRACT_LOGIC_SUPPORT_ONLY`. Next: preregister a real disposable-Linux backend canary only after disk admission recovers. Existing Colima/images are a candidate testbed, not evidence of Blender compatibility or containment.

Artifacts: `experiments/worker-launch-contract-v0-1/results.json`, `experiments/worker-launch-contract-v0-1/audit.json`, `specs/worker-launch-contract.v0.1.json` and `research/2026-08-26-b38-worker-launch-contract-result.md`.

## J-049 · B39 architecture preflight rejects a false index-cardinality assumption

Type: preregistered read-only architecture/artifact preflight, 2026-08-26.

B39 asked whether the local ARM64 Colima host has an official native Blender 5.2 Linux artifact route and, if not, whether the official x64 route is sufficiently identified to justify a later best-effort emulation canary. The protocol froze eight read-only probes, zero runtime operations, the official filename/byte/hash identity, host architectures, security-option metadata, disk admission and 15 attacks before tooling.

The official x64 filename appeared twice in the raw directory-index HTML, not once as preregistered. Its byte count (`384441228`) and SHA-256 (`96f6c181…351c48`) matched; the Linux ARM64 filename and checksum remained absent; host/Colima/Docker reported `arm64/aarch64/aarch64`; and the real disk gate was blocked. Inspection showed the two raw occurrences are the hyperlink target and its visible text.

Verdict: `X64_INDEX_IDENTITY`; status `REJECTED_PROTOCOL_ASSUMPTION`. The analyzer therefore did not record an accepted attack set. The independent audit reproduced the two base failures and correctly failed `recordedAttacksMatch`, even though its 15 mutated candidates were individually rejected. No container or Blender process ran.

This failure remains immutable. A correction must separately freeze raw occurrences (`2`) and exact hyperlink-target occurrences (`1`) while retaining every other gate. It may not relabel the first run as accepted.

Artifacts: `experiments/linux-worker-architecture-preflight-v0-1/results.json`, `experiments/linux-worker-architecture-preflight-v0-1/audit.json` and `research/2026-08-26-b39-linux-worker-architecture-preflight-result.md`.

## J-050 · B39-C1 structure-aware parser correction

Type: preregistered correction and independent replay, 2026-08-26.

The correction spec binds the rejected B39 result and audit by SHA-256 and changes only one assumption: the official x64 filename must occur twice as raw HTML text but exactly once as a quoted hyperlink target. All other source, artifact, host, Docker, disk, route and zero-runtime gates remained frozen.

The corrected run measured `raw=2`, `href=1`, byte count `384441228` and the frozen official SHA-256. The expected Linux ARM64 filename had zero raw, href and checksum occurrences. Host/Colima/Docker remained `arm64/aarch64/aarch64`; the native route was rejected narrowly, while x64 was classified `EXPERIMENT_ONLY_BEST_EFFORT_EMULATION` and `IDENTIFIED_BUT_RUNTIME_BLOCKED`.

Fifteen of fifteen freshly self-hashed attacks were rejected and the independent audit reproduced the exact vector. Real available bytes were `19705393152`; the 20 GiB projection already exceeded that, so the 100 GiB reserve remained fail-closed. Runtime operation count was zero.

Verdict: `ARCHITECTURE_PREFLIGHT_CORRECTION_SUPPORT_RUNTIME_BLOCKED`. The first B39 failure remains published. B40 still requires recovered disk admission and separate preregistration before any image build, container or Blender launch.

Artifacts: `experiments/linux-worker-architecture-preflight-v0-2/results.json`, `experiments/linux-worker-architecture-preflight-v0-2/audit.json` and `research/2026-08-26-b39-c1-index-parser-correction-result.md`.

## Active goal experimental contract

This contract is part of the active BlenderFilmStudio goal and applies to every subsequent stage:

1. preregister the falsifiable question, variables, controls, thresholds and rejection conditions before creating the tested tool or output;
2. test with real Blender when the claim concerns Blender, and record the exact runtime, hardware-relevant environment, input identity, process identity and randomness controls;
3. retain failed runs, counterexamples, negative observations and boundary conditions instead of rewriting the history around the successful path;
4. label statements as measured fact, inference, subjective judgment or unknown, and never promote one category into another;
5. require a clean reproduction plus adversarial/attack tests before promoting an engineering result;
6. require independent human observers for subjective visual claims; developer pilots and synthetic fixtures remain interface/attack evidence only;
7. publish machine-readable artifacts, hashes, non-claims and the next unresolved boundary, except when delayed disclosure is itself required to preserve a preregistered blind experiment.
