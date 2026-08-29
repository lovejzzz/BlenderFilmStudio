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

## J-051 · B40 attempt 1 binfmt parser invalidation

Type: preregistered read-only host-capacity admission, invalid tool attempt, 2026-08-26.

B40 froze host disk, VM memory/CPU, Docker storage, swap, emulator and competing-container gates before tooling. Four expected capacity blockers reproduced, but the runner added `X64_EMULATOR` even though the raw kernel record showed `enabled`, interpreter `/usr/bin/qemu-x86_64` and `flags: POCF`.

The tool had frozen a whitespace-only parser for `flags`; the actual binfmt grammar uses the literal key `flags:`. It stored an empty flag string and falsely blocked the emulator. Verdict: `EMULATOR_GATE`; status `INVALID_TOOL_PARSER`. The independent audit correctly failed base acceptance and recorded-attack equality. Runtime operations remained zero.

The attempt stays immutable. B40-C1 must bind its hashes and change only the exact key grammar; capacity thresholds and the expected four blockers remain unchanged.

Artifacts: `experiments/worker-host-capacity-admission-v0-1/results.json`, `experiments/worker-host-capacity-admission-v0-1/audit.json` and `research/2026-08-26-b40-worker-host-capacity-admission-invalid-result.md`.

## J-052 · B40-C1 in-memory aliasing breaks independent replay

Type: preregistered parser correction, rejected by serialization-stability audit, 2026-08-26.

B40-C1 correctly parsed `flags: POCF`, accepted the emulator gate and reproduced four capacity blockers. Its in-memory runner reported 14/14 attacks. The independent audit nevertheless failed exact replay at the fabricated-emulator attack.

The classifier had stored the same emulator object under both observation and decision. In-memory mutation changed both references; JSON round-trip broke the alias, so the audit additionally detected `CAPACITY_DECISION`. All candidates were rejected, but the failure vector was not reproducible and `recordedAttacksMatch=false`.

Status: `REJECTED_IN_MEMORY_ALIASING`. B40-C2 must value-copy gate records and freeze pre/post-JSON attack-vector equality. No runtime operation occurred.

Artifacts: `experiments/worker-host-capacity-admission-v0-2/results.json`, `experiments/worker-host-capacity-admission-v0-2/audit.json` and `research/2026-08-26-b40-c1-aliasing-audit-failure.md`.

## J-053 · B40-C2 round-trip passes but specific attack codes are lost

Type: preregistered serialization correction, invalid wrapper projection, 2026-08-26.

B40-C2 removed the observation/decision alias: base analysis, decision, evidence hash and attack vectors were stable across JSON round-trip. But its wrapper exposed only `BASE_ANALYSIS` for every mutated candidate instead of carrying through the base analyzer's specific failure codes.

All 14 candidates were rejected, yet none matched its preregistered primary code, so the formal vector was 0/14. Runner and audit both failed while round-trip equality passed. Status: `INVALID_FAILURE_CODE_PROJECTION`.

B40-C3 must change only ordered failure-code projection; the serialization correction, four capacity blockers, thresholds and zero-runtime boundary remain unchanged.

Artifacts: `experiments/worker-host-capacity-admission-v0-3/results.json`, `experiments/worker-host-capacity-admission-v0-3/audit.json` and `research/2026-08-26-b40-c2-failure-code-projection-invalid.md`.

## J-054 · B40-C3 projection identity crash before result

Type: preregistered failure-projection correction, no-result tool crash, 2026-08-26.

The frozen C3 helper tried to read the C2 experiment's own preregistration identity from a nonexistent nested spec field and raised a `TypeError` before creating evidence, attacks or audit input. Status: `NO_RESULT_TOOL_CRASH`; no capacity decision exists for this invocation.

B40-C4 may change only the identity source to the frozen C2 library constants. No runtime operation occurred.

Artifact: `research/2026-08-26-b40-c3-no-result-tool-crash.md`.

## J-055 · B40-C4 replay passes but final field escapes evidence hash

Type: preregistered identity correction, rejected persisted self-hash, 2026-08-26.

B40-C4 reached four exact blockers, 14/14 attacks and replay PASS. Audit attack vectors matched, but the runner had added `replayPassed=true` only after evidence hashing. The persisted file therefore contained an unhashed decision field, and audit correctly failed `IDENTITY_EVIDENCE_SELF_HASH`.

Status: `REJECTED_RESULT_FIELD_OUTSIDE_HASH`. B40-C5 must place the replay result inside evidence before hashing and attacks. No runtime operation occurred.

Artifacts: `experiments/worker-host-capacity-admission-v0-5/results.json`, `experiments/worker-host-capacity-admission-v0-5/audit.json` and `research/2026-08-26-b40-c4-result-field-hash-failure.md`.

## J-056 · B40-C5 replay-stable blocked host admission

Type: preregistered result-field correction and independently replayed capacity admission, 2026-08-26.

B40-C5 placed the replay result inside hashed evidence before attacks. It reproduced four exact blockers: host disk reserve, VM memory, VM CPU and Docker storage. Actual values were about 19.67 GB host-free, 6.20 GB VM `MemTotal`, four CPUs and 4.64 GB Docker-free versus frozen admission requirements of 100 GiB after a 20 GiB projection, 10 GiB VM memory, five CPUs and 8 GiB Docker-free.

Zero swap, zero running containers and enabled `qemu-x86_64` with `POCF` flags passed. Fourteen of fourteen primary attack reasons survived JSON round-trip and independent audit exactly. Runtime operations remained zero.

Verdict: `WORKER_HOST_CAPACITY_BLOCKED_REPLAY_STABLE`. B41 requires external disk/Colima/Docker capacity changes, a clean admission rerun and separate preregistration.

Artifacts: `experiments/worker-host-capacity-admission-v0-6/results.json`, `experiments/worker-host-capacity-admission-v0-6/audit.json` and `research/2026-08-26-b40-c5-worker-host-capacity-result.md`.

## J-057 · Authorized cleanup, Colima expansion and rejected B40-R1 replay

Type: external-state intervention plus preregistered post-intervention re-admission, rejected replay result, 2026-08-26.

The user explicitly authorized cleanup and Colima expansion, then explicitly added LTX model data to the deletion scope. Six exact non-symlink paths were removed: CourseMapper cache, npm cache, LTXDesktop application support, and three LTX updater/cache directories. Personal video, Blender experiment data and GPT Bot Pilots were not touched. Host free space increased from about 20 GiB to 129 GiB and utilization fell from 98% to 86%; the removed data is not locally recoverable but was classified as re-downloadable cache/model content.

With no running containers, the existing default Colima profile was stopped and resized without deleting it. It restarted under Apple Virtualization Framework as aarch64/Docker with 6 CPU, 12 GiB configured memory and a 20 GiB disk. Direct checks reported six online CPUs, `12513595392` bytes Docker-visible memory, zero swap and `14767869952` bytes free on `/var/lib/docker`.

B40-R1 then measured all seven unchanged capacity gates as accepted and produced the 16/16 expected attack rejections. It nevertheless reported replay failure before persistence. The runner set the hashed replay field to false, emitted `WORKER_HOST_CAPACITY_READMISSION_FAILED`, and the independent audit failed at `REPLAY_RESULT_RECORDED`. The original tool did not preserve a component-level replay delta, so the transient mismatch cannot be reconstructed from the persisted receipt.

Status: `REJECTED_REPLAY_DIAGNOSTIC_GAP`. B40-R2 may change only replay snapshotting, canonical comparison and component-level diagnostics. No container or Blender runtime operation occurred.

Artifacts: `experiments/worker-host-capacity-readmission-v0-1/attempt-1-results.json`, `experiments/worker-host-capacity-readmission-v0-1/attempt-1-audit.json` and `research/2026-08-26-b40-r1-replay-diagnostic-failure.md`.

## J-058 · B40-R2 replay-stable host admission after intervention

Type: preregistered narrow replay correction and independently audited capacity re-admission, 2026-08-26.

B40-R2 changed no policy, probe, expected capacity state, attack or runtime boundary. It canonicalized the tested evidence before analysis and stored separate evidence, analysis and attack-vector replay booleans inside the hashed receipt.

The host exposed `139029028864` bytes available and `117554192384` bytes after the frozen 20 GiB projection, above the 100 GiB reserve. Colima exposed `12513595392` bytes memory, six CPUs, zero swap and enabled `qemu-x86_64` with `/usr/bin/qemu-x86_64` plus `POCF`. `/var/lib/docker` exposed `14767869952` bytes available and Docker reported zero running containers.

All seven gates were accepted with no blocked reasons. Sixteen of sixteen attacks produced their expected primary failure, all three replay diagnostics were true, and the independent audit reproduced the analysis and exact attack vector.

Verdict: `WORKER_HOST_CAPACITY_ACCEPTED_REPLAY_STABLE`. The host is eligible only for a separately preregistered B41 linux/amd64 Blender 5.2 canary; no runtime claim was made here.

Artifacts: `experiments/worker-host-capacity-readmission-v0-2/results.json`, `experiments/worker-host-capacity-readmission-v0-2/audit.json` and `research/2026-08-26-b40-r2-worker-host-capacity-readmission-result.md`.

## J-059 · B41 Docker architecture alias crash before runtime

Type: preregistered real-runtime canary, no-result identity parser crash, 2026-08-26.

The disk guard accepted B41 with `134689046528` bytes available. Before creating an output directory or downloading anything, the runner queried the explicitly bound Colima Docker socket. Docker server JSON returned `Arch=arm64`, while the preregistered canonical Colima/Docker architecture was `aarch64`. The runner had frozen no alias normalization and stopped at `B41 Docker server architecture differs`.

Status: `NO_RESULT_DOCKER_ARCHITECTURE_ALIAS_CRASH`. B41-C1 may map Docker API `arm64` to canonical `aarch64` and change nothing else. No archive download, build, image, container or Blender process occurred.

Artifact: `research/2026-08-26-b41-docker-architecture-alias-crash.md`.

## J-060 · B41-C1 archive verified; build CLI and receipt rejected

Type: preregistered architecture correction, failed image build and invalid receipt tooling, 2026-08-26.

B41-C1 passed disk admission, normalized raw Docker `arm64` to canonical `aarch64`, and downloaded the official Blender archive. The observed `384441228` bytes and SHA-256 `96f6c181a30f4950607839dc84d42a354b250d8a0231b098b59b7bc69c351c48` matched exactly.

The Docker CLI selected its legacy builder and rejected the BuildKit-only `--progress` flag with exit 125 before reading the Dockerfile. No image, container or Blender process was created. The temporary archive/build root was removed.

The failure receipt independently exposed three tool defects: self-hash projection included `evidenceHash`; locale path sorting disagreed with the frozen bytewise OCIO manifest; and correction hashes were attached to parent tool URIs. Status: `REJECTED_BUILD_CLI_AND_RECEIPT_TOOLING`.

B41-C2 may change only those four proven defects. Artifact identity, disk gate, image specification, isolation, render, timeout, decision and non-claim boundaries remain frozen.

Artifacts: `experiments/linux-amd64-blender-runtime-canary-v0-2/` and `research/2026-08-26-b41-c1-build-cli-and-receipt-failure.md`.

## J-061 · B41-C2 receipt valid; legacy builder produces ARM64 layers

Type: preregistered tooling correction, valid failed build receipt, 2026-08-26.

B41-C2 corrected the unsupported progress flag, self-hash projection, OCIO byte ordering and correction tool URIs. Official archive identity, OCIO identity, tool hashes and evidence hash all passed.

The legacy Docker builder then executed the nominal `linux/amd64` Dockerfile using ARM64 packages. Its apt trace contained `:arm64`, and Docker rejected the intermediate image because it did not provide the requested amd64 platform. Build exit was one; no final image, container or Blender process existed.

A read-only probe found buildx `v0.34.1` inside the Colima VM. Status: `REJECTED_LEGACY_BUILDER_PLATFORM_MISMATCH`. B41-C3 may change only the build transport to guest buildx with `--platform linux/amd64 --load`.

Artifacts: `experiments/linux-amd64-blender-runtime-canary-v0-3/` and `research/2026-08-26-b41-c2-legacy-builder-platform-failure.md`.

## J-062 · B41-C3 proves amd64 transport and falsifies cross-platform binary identity

Type: preregistered build-transport correction, valid pre-runtime rejection with failed frozen audit, 2026-08-26.

Colima guest buildx `v0.34.1` and BuildKit `v0.30.0` executed the same Dockerfile as `linux/amd64`. The apt trace now installed `:amd64` packages, and the official `384441228`-byte archive passed its frozen SHA-256 check inside the build.

The next check compared the extracted Linux executable with `60ba7a9b…129f2`, which is the local macOS Blender executable identity inherited from B38. The check correctly failed. No final image, container or Blender process existed, so neither runtime canary ran.

The frozen independent audit matched all tool hashes but reported artifact mismatch because it requires PNG and `.blend` objects even for a build-stage rejection. That audit remains failed. Status: `REJECTED_CROSS_PLATFORM_BINARY_IDENTITY_AND_AUDIT_PRE_RUNTIME_ASSUMPTION`.

Next: preregister a read-only Linux binary identity derivation from the already authenticated official archive, then bind that derived identity in a narrow runtime correction. The B38 macOS identity remains unchanged.

Artifacts: `experiments/linux-amd64-blender-runtime-canary-v0-4/` and `research/2026-08-26-b41-c3-linux-binary-identity-failure.md`.

## J-063 · B41-D1 host identity candidate rejected by empty guest stream

Type: preregistered archive-member derivation, rejected cross-method agreement, 2026-08-26.

The exact official archive passed byte and SHA identity. Host bsdtar found the member once and produced an ELF64 x86-64 candidate of `174666336` bytes with SHA-256 `83e8261e…acf27`. The Colima guest produced empty-stream SHA-256 and zero bytes because GNU tar's `-J` requires an absent external `xz` executable, while the frozen POSIX shell pipeline lacked `pipefail` and masked tar's failure.

The candidate was not promoted. Base analysis failed `DERIVATION_AGREEMENT`; independent audit reproduced only 5/8 attacks because the base failure shadowed three later mutations. No Blender, image build or container operation occurred.

Status: `REJECTED_GUEST_DECOMPRESSOR_AND_PIPELINE_FAILURE`. B41-D1-C1 may change only the guest member reader to installed Python 3 standard-library `lzma`/`tarfile` with structured fail-closed output.

Artifacts: `experiments/linux-amd64-blender-binary-identity-derivation-v0-1/` and `research/2026-08-26-b41-d1-guest-empty-stream-failure.md`.

## J-064 · B41-D1-C1 derives and audits the Linux executable identity

Type: preregistered guest-reader correction and independently audited identity derivation, 2026-08-26.

The exact `384441228`-byte official archive matched SHA-256 `96f6c181…351c48`, and the executable member appeared once. Host bsdtar/Node and Colima Python 3.12.3 `tarfile/lzma` independently streamed the member. Both measured `174666336` bytes and SHA-256 `83e8261eace07a5337f71b52d156c1eece1a6ba913403cc6406182ae58bacf27`.

The ELF header was ELF64, little-endian, x86-64. The archive was removed, no Blender/image/container operation occurred, 8/8 attacks produced their expected primary reason, and independent audit passed tool identity and exact replay.

Verdict: `LINUX_AMD64_BLENDER_EXECUTABLE_IDENTITY_DERIVED`. This is an identity result only. A separate B41 runtime correction must bind it before any launch, render, containment or timeout claim.

Artifacts: `experiments/linux-amd64-blender-binary-identity-derivation-v0-2/` and `research/2026-08-26-b41-d1-c1-linux-binary-identity-result.md`.

## J-065 · B41-C4 builds and launches amd64 Blender; canary enum is invalid

Type: preregistered platform-binary correction, real Blender/container rejection, 2026-08-26.

Buildx completed a `linux/amd64` image (`sha256:0ca8ce…1941b`). The constrained success container launched Blender 5.2.0 LTS build `fbe6228777e7`, loaded the frozen OCIO config and entered the mounted canary as uid 65532. It exited one because Blender 5.2 exposes render engines `BLENDER_EEVEE`, `BLENDER_WORKBENCH` and `CYCLES`; the canary used invalid `BLENDER_EEVEE_NEXT`.

The independent timeout container reached READY, received TERM at about 30.0 seconds, recorded SIGTERM, received KILL at about 35.0 seconds and exited 137 as non-promotable. Cleanup left zero experiment containers. Audit matched tools/artifact absence and timeout state but correctly failed the overall success claim.

A nonfatal PulseAudio warning also showed `/work/tmp` absent; it is recorded but was not the exit cause and will not be combined with the next correction. Status: `REJECTED_BLENDER_5_2_EEVEE_ENUM_MISMATCH`.

Artifacts: `experiments/linux-amd64-blender-runtime-canary-v0-5/` and `research/2026-08-26-b41-c4-eevee-enum-failure.md`.

## J-066 · B41-C5 saves the scene but Eevee exceeds the success timeout

Type: preregistered Blender 5.2 enum correction, real render-boundary rejection, 2026-08-26.

The corrected `BLENDER_EEVEE` assignment passed. The constrained success container created its write probe and saved a `95641`-byte `.blend`, then emitted three `EGL_BAD_MATCH` messages and produced no PNG/report before 30 seconds. TERM at `30002 ms` ended Blender with exit 143 at `30096 ms`; KILL was unnecessary.

The separate timeout canary again reached READY, recorded TERM, received KILL and exited 137 as non-promotable. Independent audit matched tools and the partial artifact set but correctly failed success.

Status: `REJECTED_EEVEE_HEADLESS_OR_EMULATION_TIMEOUT`. The observation does not yet distinguish slow QEMU execution from a headless EGL backend failure. Next is a preregistered diagnostic with render milestones, a fixed time ladder and an explicit software-headless environment factor; it cannot promote B41 by itself.

Artifacts: `experiments/linux-amd64-blender-runtime-canary-v0-6/` and `research/2026-08-26-b41-c5-eevee-headless-timeout.md`.

## J-067 · B41-D2 rejects four headless Eevee configurations

Type: preregistered non-promotable 2×2 diagnostic, independently audited, 2026-08-26.

The exact C5 image ran default versus explicit OpenGL crossed with default versus Mesa software/surfaceless environment. All four cells configured the scene, saved `.blend`, failed the pre-render GPU query because the gpu module was not initialized, emitted the same three `EGL_BAD_MATCH` messages and remained at `RENDER_STARTED` until the 90-second ceiling. TERM produced exit 143 in every cell; no PNG/report or KILL was required.

The diagnostic completed validly with classification `NO_COMPLETION_WITHIN_DIAGNOSTIC_CEILING`, 0/4 completion and no promotion authority. Audit matched tools, milestones, partial artifacts and classification exactly.

This rejects only the four tested configurations on ARM64 Colima/qemu. Next research must separately test a display-service route or a Vulkan software device, or decide that this host can support a CPU Cycles canary but not the frozen Eevee gate.

Artifacts: `experiments/linux-amd64-eevee-headless-diagnostic-v0-1/` and `research/2026-08-26-b41-d2-eevee-headless-diagnostic-result.md`.

## J-068 · B41-D3 confirms a real CPU render worker and isolates Eevee

Type: preregistered non-promotable renderer controls, independently audited, 2026-08-26.

The exact constrained image completed a Blender 5.2 Cycles CPU 32×32/1-sample render in `11039 ms`, exit 0, producing a valid `2515`-byte PNG and `95671`-byte `.blend`. The forced-Vulkan Eevee control saved its scene but remained at `RENDER_STARTED` for `90084 ms`, then exited 143 after TERM with no PNG.

Both controls saw Mesa EGL. Neither saw the preregistered lavapipe library/ICD paths or `/dev/dri`; the probed llvmpipe filename was also absent, though that path alone does not exhaust Debian software-OpenGL packaging. Audit matched tools, milestones, artifacts and classification.

Classification: `CPU_ONLY_WORKER_CONFIRMED_EEVEE_GPU_ROUTE_ABSENT`. The current image may proceed under a separately preregistered compile-only/Cycles CPU boundary. The Eevee gate remains open and requires a GPU-backed worker or a separately built and tested software-Vulkan stack.

Artifacts: `experiments/linux-amd64-render-backend-control-v0-1/` and `research/2026-08-26-b41-d3-render-backend-control-result.md`.

## J-069 · B42 failure retained; B42-C1 closes the compiler reproducibility gate

Type: preregistered worker compiler experiment, retained launch failure, narrow correction and independent audit, 2026-08-26.

B42 regenerated both B01 and B02 BuildPlans twice with exact frozen byte identities, but all five containers exited 125 before Blender because OCI could not create an absent nested mountpoint inside the read-only `/repo` bind. Its analyzer then threw on the absent observations. The generated plans, logs and `failure.json` were committed; no acceptance result was fabricated.

B42-C1 preregistered only a tracked empty `/repo/worker-output` mountpoint and failure-total analysis. The four clean Blender 5.2 Linux/amd64 compilations exited zero in 9,361–9,776 ms. B01 reproduced structure hash `c699fc27…b7f0b`; B02 reproduced `025c6fa5…fa856`. Their `.blend` bytes differed, as explicitly allowed. The fifth container rejected a zeroed top-level `planHash`, exited 1 and wrote no scene artifacts.

Independent audit passed tool hashes, regenerated plan files and direct output observations. Verdict: `LINUX_AMD64_COMPILER_REPRODUCIBLE_AFTER_MOUNT_CORRECTION`. This closes the two-scene compile gate, not pixel quality, Eevee/GPU, arbitrary-scene coverage, `.blend` byte identity or remote attestation.

Artifacts: `experiments/linux-amd64-compiler-repro-v0-1/`, `experiments/linux-amd64-compiler-repro-c1-v0-1/`, `research/2026-08-26-b42-nested-mountpoint-failure.md`, and `research/2026-08-26-b42-c1-linux-amd64-compiler-repro-result.md`.

## J-070 · B43-D1 derives the model-independent intent adapter oracle

Type: preregistered deterministic derivation, no model or Blender execution, 2026-08-26.

B43-D1 froze three DirectorIntents, an enum-only ShotProposal schema, a preset catalog, the prompt template, exact proposal answers and every technical SceneSpec replacement value before implementing the adapter. The model-facing object has no path, hash, numeric transform, Blender command or arbitrary-code field.

The formal derivation produced two valid SceneSpecs and byte-identical double-compiled BuildPlans: `SHOT_109` plan hash `60e4cdf7…cb275e` and `SHOT_110` plan hash `9c8cb0e0…d46401`. The unauthorized network/Python brief produced a strict rejection and zero SceneSpec/BuildPlan artifacts. Eight of eight attacks reached the preregistered reason. Independent audit matched frozen inputs, tools, all artifacts, replay and evidence self-hash.

Verdict: `CODEX_SCENESPEC_ADAPTER_GOLDENS_DERIVED`. Operation counts were Codex 0, model 0, Blender 0, container 0 and network 0. This is an answer-key and adapter result, not evidence of model reliability. Next: preregister the exact subscription-authenticated `codex exec` holdout and compare its outputs to these pre-existing oracles without permitting tool calls.

Artifacts: `experiments/codex-scenespec-adapter-derivation-v0-1/`, `specs/codex-scenespec-adapter-derivation.v0.1.json`, `research/2026-08-26-b43-d1-codex-scenespec-adapter-derivation-protocol.md` and `research/2026-08-26-b43-d1-codex-scenespec-adapter-derivation-result.md`.

## J-071 · B43 closes the subscription-authenticated intent gate

Type: preregistered Codex CLI holdout, six fresh model invocations, independently audited, 2026-08-26.

The exact Codex CLI `0.149.1` executable ran `gpt-5.6-luna` at low reasoning through saved ChatGPT authentication, with both API-key variables absent. Six ephemeral, read-only, ignore-config/ignore-rules processes used six empty non-repository directories. Each JSONL stream contained only thread start, turn start, one agent message and turn completion; there were zero command, file, MCP, web or plan items.

All six proposals were canonical-exact with the B43-D1 oracles created before the model run. Both replicates agreed for all three briefs. The two unauthorized-download/Python cases returned strict rejection with four `NONE` presets. Runtime was 5,278–5,996 ms per invocation; usage receipts totalled 92,336 input, 696 output and 154 reasoning-output tokens. No video model or API key was used.

Twelve of twelve evidence attacks passed. Independent audit reconstructed prompts, reparsed events, revalidated proposals, matched tools/artifacts and recomputed the self-hash. Verdict: `CODEX_SUBSCRIPTION_INTENT_HOLDOUT_PASSED`.

This proves only a narrow subscription-authenticated proposal gate, not arbitrary filmmaking reliability or zero total cost. Next: promote the two accepted model outputs through the frozen adapter into the exact golden SceneSpecs/BuildPlans, compile each twice in the B42 Linux/amd64 worker, and prove the rejected output launches no container.

Artifacts: `experiments/codex-scenespec-holdout-v0-1/`, `specs/codex-scenespec-holdout.v0.1.json`, `research/2026-08-26-b43-codex-subscription-intent-holdout-protocol.md` and `research/2026-08-26-b43-codex-subscription-intent-holdout-result.md`.

## J-072 · B44 closes the saved Codex proposal → real Blender compile chain

Type: preregistered promotion holdout, four real Linux/amd64 Blender worker invocations, independently audited, 2026-08-26.

B44 consumed three immutable outputs from the already completed B43 Codex holdout rather than calling the model again. `TABLETOP-A` and `INTERIOR-A` passed the frozen adapter and matched the exact golden SceneSpecs and immutable BuildPlans. `UNAUTHORIZED-A` remained a strict rejection with zero SceneSpecs, zero BuildPlans and zero container launches.

The two accepted plans each entered two fresh Blender 5.2 Linux/amd64 containers under the unchanged B42-C1 isolation contract. All four processes exited 0 in 10,228–10,423 ms. `SHOT_109` reproduced canonical structure hash `6a71287a…5e82e` in 2/2 runs; `SHOT_110` reproduced `56d32ed8…6d954` in 2/2. The `.blend` byte hashes differed within both pairs, so semantic structure reproducibility passed while `.blend` byte identity remained explicitly unclaimed.

The operation trace contained exactly four Docker runs and no build, pull or download. Twelve of twelve attacks passed, zero experiment containers remained, and the independent audit matched parents, tools, inputs, proposals, outputs, attacks and the evidence self-hash. Verdict: `CODEX_TO_BLENDER_WORKER_PROMOTION_REPRODUCIBLE`.

This closes the narrow saved-proposal-to-compiled-scene chain for two preset-bound shots. It does not establish arbitrary prompt coverage or final pixels. Next: preregister B45 to render frozen representative frames directly from the B44 `.blend` outputs before attempting a complete sequence.

Artifacts: `experiments/codex-to-blender-worker-promotion-v0-1/`, `specs/codex-to-blender-worker-promotion.v0.1.json`, `research/2026-08-26-b44-codex-to-blender-worker-promotion-protocol.md` and `research/2026-08-26-b44-codex-to-blender-worker-promotion-result.md`.

## J-073 · B45 failure retained; B45-C1 reaches exact decoded float pixels

Date: 2026-08-26

B45 preregistered a one-frame pixel promotion directly from each of the four B44 `.blend` outputs. The first command retained the 100 GiB disk reserve but stopped because the common wrapper projected 20 GiB instead of the frozen 1 GiB. Re-running with `BFS_PROJECTED_WRITE_GIB=1` aligned the wrapper with the frozen projection. All four containers then verified the source and scene bindings and reached `RENDER_STARTED`, but Blender rejected the single-layer `OPEN_EXR` enum while `image_settings.media_type` still held `MULTI_LAYER_IMAGE`. No EXR, PNG or report existed. The runner then exposed a second defect by dereferencing a null report during attack generation. This attempt is retained as `INVALID_TOOL_INTERFACE_NO_PIXEL_DECISION` rather than interpreted as a renderer or pixel result.

The raw failure, exact artifact hashes and a correction protocol were committed before implementation. B45-C1 permitted only `media_type=IMAGE` before the already frozen EXR save and total analysis/attacks over null reports; it preserved the two frames, Cycles CPU, 128×72, one sample, four threads, shot seeds, no denoise, exact float-pixel gate, four-container count, worker isolation, 100 GiB reserve and 1 GiB projected write.

Four new Blender 5.2 Linux/amd64 containers then completed in 9,690–10,258 ms. TABLETOP A1/A2 decoded to `b45f5424cce4982bc698dc31cef1e2731a22c1073c4795767de0f95140ce7dbd`; INTERIOR A1/A2 decoded to `0dd7514f888d1db4a5602defc55d6aeda6caf8226667c908d4ce1d6dbab6544b`. Each output contained 9,216 pixels and 36,864 finite little-endian float32 BGRA components. The independent audit re-decoded all four EXRs and passed 14/14 base attacks, 2/2 correction attacks, correction-parent identity, self-hash and null-totality replay.

TABLETOP's EXR and PNG container hashes differed across A/B while its decoded float arrays were exact. INTERIOR happened to match at both levels. This confirms that container-byte identity and pixel-content identity are separate evidence layers. The two 1-sample frames are diagnostic canaries, not image-quality exhibits.

Verdict: `B44_BLEND_TO_FLOAT_PIXELS_EXACT_AFTER_MEDIA_TYPE_CORRECTION`.

Next: preregister a bounded short continuous-shot promotion from the same B44 scenes. Freeze the frame interval, temporal comparison domain, quality intervention, runtime/disk ceiling and interrupted-run recovery before rendering. Do not infer cinematic quality, 4K throughput, GPU/Eevee parity, cross-host reproducibility or arbitrary-scene coverage from B45-C1.

Artifacts: `experiments/codex-worker-pixel-promotion-v0-1/failure.json`, `experiments/codex-worker-pixel-promotion-c1-v0-1/`, `specs/codex-worker-pixel-promotion.v0.1.json`, `specs/codex-worker-pixel-promotion-media-type-correction.v0.1.json`, `research/2026-08-26-b45-invalid-media-type-and-null-analysis.md` and `research/2026-08-26-b45-c1-codex-worker-pixel-promotion-result.md`.

## J-074 · B44 `.blend` reaches exact bounded sequences and fresh-attempt recovery

Date: 2026-08-26 · Type: LIVE EXPERIMENT · Runtime: Blender 5.2 Linux/amd64 Cycles CPU worker

B46 was preregistered at commit `259cf3071b8ccd3884ecb3154a2dcc99380dec7b`, before its renderer, analyzer, runner or audit existed. The frozen intervention used the four B44 `.blend` outputs, two ordered eight-frame intervals, 128×72, eight samples, fixed shot seed and four CPU threads. Motion blur, denoising, animated seed, persistent data, compositing and sequencer were disabled. The tool set was frozen at `6895092342afae5c3860a2a7b62142f7de5c088f` before the first formal container.

All four primary containers completed. TABLETOP-A1/A2 produced the same complete sequence hash `6dcea8c9…496c`; all 8 cross-build frame hashes and all 7 float32 temporal-delta hashes were exact, while each moving-camera transition changed 20,600–21,010 components. INTERIOR-A1/A2 produced the same complete sequence hash `334bdd26…e28c5`; all 8 frames and 7 transition hashes were exact, and the static control changed exactly zero components in every transition. Overall: 16/16 frame pairs and 14/14 temporal-delta pairs exact.

The fifth container completed TABLETOP frame 21, durably recorded it, then exited 86 at the preregistered fault point. It left exactly one frame and no final report, so it was not promotable. The sixth container wrote to a new empty output root and reproduced all eight primary TABLETOP frames, all seven temporal deltas and the complete sequence hash exactly. This is evidence for a narrow discard-and-fresh-retry policy, not in-place resume or host-failure recovery.

The independent audit re-decoded 40 successful EXRs, re-probed four eight-frame H.264 navigation carriers, reconstructed both pair comparisons and recovery comparison, and passed 21/21 attacks. Verdict: `B44_BLEND_TO_BOUNDED_SEQUENCE_EXACT_WITH_RECOVERY`. Evidence hash: `5781211095a441760a2878a3578cfab8f080d99ac881740aa8015e76e0c87f4b`.

Next: preregister a production-representation and quality ladder. Separate multilayer EXR/AOV/Vector correctness, motion blur, sampling, denoising and render cost rather than bundling them into one “cinematic” claim. B46 does not establish complete shots, perceptual temporal quality, 4K, characters, GPU/Eevee, cross-host reproducibility, arbitrary scenes or production throughput.

Artifacts: `specs/codex-worker-sequence-promotion.v0.1.json`, `experiments/codex-worker-sequence-promotion-v0-1/`, `research/2026-08-26-b46-codex-worker-sequence-promotion-protocol.md` and `research/2026-08-26-b46-codex-worker-sequence-promotion-result.md`.

## J-075 · B47-D1 derives the real multipart production-pass boundary

Date: 2026-08-26 · Type: LIVE DERIVATION · Runtime: Blender 5.2 Linux/amd64 Cycles CPU worker

The B47-D1 probe was frozen at `ade1000d528f4194693f190fa2a9c3e0e3a5da9f` before execution. One TABLETOP frame was rendered from the B44 `.blend` at 128×72 and eight samples, with Combined, Depth, Normal, Vector and Object Cryptomatte enabled. The resulting 242,603-byte RGBA32 ZIP multipart EXR contained seven float subimages: Combined, Depth, Normal, Vector and CryptoObject00–02.

All decoded components were finite. Depth used exactly `1e10` as the far-background value rather than infinity. The moving-camera Vector pass contained 32,244 non-zero components even with motion blur disabled. Cryptomatte declared MurmurHash3_32 / uint32-to-float32 and carried a parseable object manifest; its identity lanes cannot be judged by ordinary color-magnitude rules.

This is derivation evidence only. It freezes the formal B47 pass roster and semantic rules but does not establish A/B pass reproducibility or production readiness. B47 will compare two frames from both TABLETOP builds and both INTERIOR builds: 28 cross-build pass pairs, moving/static temporal controls, manifest semantics and an independent audit. Sampling, denoising and motion blur remain isolated for B48.

Artifacts: `experiments/codex-worker-production-pack-derivation-v0-1/`, `research/2026-08-26-b47-production-pass-derivation-protocol.md` and `research/2026-08-26-b47-d1-production-pass-derivation-result.md`.

## J-076 · B47 closes the bounded multipart production-pass handoff

Date: 2026-08-26 · Type: LIVE EXPERIMENT · Runtime: Blender 5.2 Linux/amd64 Cycles CPU worker

B47 was preregistered at `c93ef549982fcf55cb53a4c3383b145cb14d20a4` after D1 fixed the real pass layout and before the formal renderer, runner or audit existed. The tools were frozen at `93ee9aeb2a5e0093021158fcd8e7ffda78c5e845`. Four fresh workers rendered TABLETOP frames 21–22 and INTERIOR frames 9–10 at 128×72, eight samples, fixed shot seed, denoise off and motion blur off.

All eight multipart OpenEXRs contained exactly Combined, Depth, Normal, Vector and CryptoObject00–02 with the frozen channels and float format. Across the two B44 semantic build pairs, all 28 frame/pass comparisons were canonical float32 exact. Every value was finite; Depth stayed positive with the `1e10` far sentinel; Normal stayed inside [-1,1]; the moving TABLETOP Vector passes contained more than 32,000 non-zero components. Both Cryptomatte manifests were A/B exact and included every frozen asset object.

The moving-camera control changed Combined, Depth, Normal and Vector across frames in both builds. The static control kept all seven pass hashes unchanged in both builds. All eight EXR container hashes differed—including static frames with identical decoded passes—so byte identity was again kept separate from content identity.

The independent audit reopened every EXR, reconstructed 56 observations and 28 pass pairs, verified temporal relations and passed 18/18 attacks. Verdict: `B44_BLEND_TO_MULTIPART_PRODUCTION_PASSES_EXACT`. Evidence hash: `7e8139e710dee9e4f75f333f22bf58ffa9045767d5d843e6581b25198bbbbc02`.

Next: preregister B48 as a quality/cost ladder. Sampling, denoising and motion blur must be isolated rather than bundled. Pass reproducibility does not establish cinematic quality, 4K, complete-shot throughput or human preference.

Artifacts: `specs/codex-worker-production-pass-promotion.v0.1.json`, `experiments/codex-worker-production-pass-promotion-v0-1/`, `research/2026-08-26-b47-codex-worker-production-pass-promotion-protocol.md` and `research/2026-08-26-b47-codex-worker-production-pass-promotion-result.md`.

## J-077 · B48-D1 reveals a multi-objective sampling/denoising cost curve

Date: 2026-08-26 · Type: LIVE DERIVATION · Runtime: Blender 5.2 Linux/amd64 Cycles CPU worker

B48-D1 froze its seven-cell order at `ed39580fa2a6814b28f9d981289e32d74ee6f60f` and its tools at `a48caada5d6db80c499a47f62fcd0ddd40805528`. One worker rendered the same B44 TABLETOP-A1 frame at 8/32/128 spp raw, the same three sample counts with OpenImageDenoise, and 512 spp raw as a numerical reference. Source, frame, seed, 128×72 resolution, four threads, ACES 2 OCIO, production-pass roster, motion-blur-off state and container boundary remained fixed.

Raw render time rose from 0.807 seconds at 8 spp to 2.537 at 32, 9.558 at 128 and 27.460 at 512. OIDN cells took 17.350, 19.209 and 26.316 seconds: on this worker, denoiser overhead dominated low-sample render cost. OIDN improved log-luminance RMSE at every sample count, but at 32 and 128 spp it increased both scene-linear normalized RMSE and top-10%-edge RMSE relative to the matched raw cell. The 128-spp raw cell was faster than every denoised cell and had lower linear/edge error than all of them against the current reference.

Denoising also changed the production representation: the EXR gained an eighth `Noisy Image` subimage and grew from the raw 242–274 KB range to 354–378 KB. All Combined arrays were finite, and a replay of the frozen analyzer produced the same SHA-256 `f2469f76…745d`.

No production point is promoted. The single 512-spp reference shares a seed with candidates and is not noiseless ground truth; the one-process run also confounds order with warm state. Next: render independent high-sample references in fresh workers, measure the reference floor, then freeze a multi-objective formal gate instead of inventing one scalar “cinematic” score.

Artifacts: `experiments/codex-worker-quality-cost-ladder-derivation-v0-1/`, `research/2026-08-26-b48-d1-quality-cost-ladder-derivation-protocol.md` and `research/2026-08-26-b48-d1-quality-cost-ladder-derivation-result.md`.

## J-078 · B48-D2 measures the high-sample reference floor

Date: 2026-08-26 · Type: LIVE DERIVATION · Runtime: three fresh Blender 5.2 Linux/amd64 Cycles CPU workers

D2 froze three 512-spp raw reference seeds before its renderer, runner and analyzer. R512-A/B/C completed in 27.540, 27.458 and 27.318 render seconds. All produced the exact B47 seven-subimage roster with finite Combined data. The original-seed A replica reproduced D1's canonical float32 Combined hash exactly in a clean worker. The two new seed interventions produced different hashes from A and each other.

The three references were not numerically identical: pairwise normalized linear RMSE was 0.033108–0.035242, log-luminance RMSE 0.016657–0.017365 and edge RMSE 0.072621–0.078448. Individual deviation from their float64 ensemble mean was 0.018740–0.019996 NRMSE, 0.009618–0.010008 log-luminance and 0.041061–0.044491 edge RMSE. This directly falsifies treating one 512-spp realization as noiseless truth.

Re-evaluating D1 against the three-reference mean preserved the ranking conflict: 128 raw had lower linear and edge error than every denoised cell, while 128 OIDN had lower log-luminance error. The analyzer replay was byte-identical; calibration status is `usableForFormalDesign=true`.

Next: freeze unseen frames, candidate seeds and a per-frame three-reference rule. A candidate will need all three metrics within a fixed multiple of the local reference floor; the cheapest cell passing every holdout becomes the bounded numerical operating point. Human cinematic quality remains a separate later gate.

Artifacts: `experiments/codex-worker-reference-calibration-derivation-v0-1/`, `research/2026-08-26-b48-d2-independent-reference-calibration-protocol.md` and `research/2026-08-26-b48-d2-independent-reference-calibration-result.md`.

## J-079 · B48 selects a bounded 128-spp raw numerical operating point

Date: 2026-08-26 · Type: FORMAL HOLDOUT · Runtime: 14 fresh Blender 5.2 Linux/amd64 Cycles CPU workers

B48 froze TABLETOP frame 37 and INTERIOR frame 19 before formal tools. Each shot received three new 512-spp raw reference seeds plus 32 raw/OIDN and 128 raw/OIDN candidates using a fourth seed. For each frame, a candidate had to keep linear NRMSE, log-luminance RMSE and top-10%-edge RMSE within 3× the largest individual-reference deviation from the three-reference mean. All three metrics had to pass on both scenes.

Only `C128_RAW` passed both holdouts. Its floor multiples were 2.342/2.438/2.206 on TABLETOP and 1.767/1.771/2.066 on INTERIOR. Both OIDN cells passed INTERIOR but failed TABLETOP linear/edge gates; 32 raw failed both. This preserves the scene-dependent denoiser counterexample instead of choosing by log-luminance alone.

The selected cell averaged 10.998 Blender render seconds and 21.011 fresh-container wall seconds per 128×72 frame. A mechanical 240-frame projection is 2,639 render seconds (44.0 minutes) and 61.9 MB of multipart EXR data. It is not a complete-shot execution or a high-resolution/cloud-cost forecast.

All 14 workers completed, all 18 attacks passed, no container remained, and the independent audit reopened every EXR and produced a byte-exact results replay. Verdict: `B48_NUMERICAL_QUALITY_COST_POINT_SELECTED`. Evidence-core hash: `445e7533…dfd0e`.

Next: B49 must separately scale resolution and cinema features from this selected baseline, then use blinded humans for perceptual cinematic-quality claims.

Artifacts: `experiments/codex-worker-quality-cost-holdout-v0-1/`, `specs/codex-worker-quality-cost-holdout.v0.1.json`, `research/2026-08-26-b48-codex-worker-quality-cost-holdout-protocol.md` and `research/2026-08-26-b48-codex-worker-quality-cost-holdout-result.md`.

## J-080 · B49-D1 measures near-linear pixel-cost scaling through 384×216

Date: 2026-08-27 · Type: LIVE DERIVATION · Runtime: three fresh Blender 5.2 Linux/amd64 Cycles CPU workers

B49-D1 held B48's selected TABLETOP 128-spp raw cell fixed and changed only resolution: 128×72, 256×144 and 384×216, or 1×/4×/9× pixels. The new 128×72 Combined float32 hash exactly reproduced B48's selected holdout artifact.

Render time was 9.816, 38.181 and 86.434 seconds. Relative to pixels, the 4× and 9× time ratios were 3.890× and 8.806×, yielding effective exponents 0.980 and 0.990. EXR bytes scaled 3.546× and 7.693×. Self-reported peak RSS moved only from 504,588 to 526,068 KiB, so this simple scene/range is compute-dominated rather than memory-dominated.

Fresh-container wall time scaled only 2.452× and 4.921× because roughly 9–10 seconds of Blender/scene startup is amortized. The analyzer replay was byte-exact and no container remained.

This does not measure 2K/4K. Next: freeze an unseen 512×288 (16× pixels) validation on both scenes and a prediction interval before execution. Motion blur and DOF remain separate target-changing interventions.

Artifacts: `experiments/codex-worker-resolution-scaling-derivation-v0-1/`, `research/2026-08-26-b49-d1-resolution-scaling-derivation-protocol.md` and `research/2026-08-27-b49-d1-resolution-scaling-derivation-result.md`.

## J-081 · B49-R validates near-linear resolution cost on two unseen 512×288 cells

Date: 2026-08-27 · Type: FORMAL HOLDOUT · Runtime: two fresh Blender 5.2 Linux/amd64 Cycles CPU workers

B49-R froze an unseen 512×288 point—16× the committed 128×72 pixel count—before the formal tools existed. TABLETOP frame 37 and INTERIOR frame 19 each retained B48's selected 128-spp raw point, seed offset 647647, four threads, ACES 2, motion blur off, denoising off and the seven-subimage production EXR pack.

TABLETOP rendered in 151.992 seconds, 15.390× its committed baseline, for an effective pixel exponent of 0.985980. INTERIOR rendered in 191.877 seconds, 15.833× baseline, for an exponent of 0.996206. Both fell inside the preregistered `[0.95,1.05]` gate. EXR byte exponents were 0.917547 and 0.955367; peak self RSS was approximately 541 MiB on both and remained below the 2 GiB gate.

Both EXRs reopened as finite 512×288 float32 Combined arrays with the exact seven-pass roster. All 15 attacks passed, no container remained, and the independent audit reproduced the full result byte for byte. Verdict: `B49_RESOLUTION_SCALING_HOLDOUT_SUPPORTED`.

The frozen `[0.95,1.05]` model band projects roughly 28–60 minutes per 2K frame and 1.76–4.26 hours per 4K frame across the two baselines on this current qemu CPU worker. Those are explicitly `MODEL_PROJECTION_NOT_MEASURED` and `CURRENT_QEMU_CPU_WORKER_ONLY`, not measured high-resolution renders or dollar costs.

Next: keep resolution fixed and separately preregister motion-blur and depth-of-field interventions. Human cinematic quality, characters/hair and a production GPU backend remain open.

Artifacts: `experiments/codex-worker-resolution-holdout-v0-1/`, `specs/codex-worker-resolution-holdout.v0.1.json`, `research/2026-08-27-b49-r-codex-worker-resolution-holdout-protocol.md` and `research/2026-08-27-b49-r-codex-worker-resolution-holdout-result.md`.

## J-082 · B49-MB-D1 derives motion-blur semantics and a Vector-pass counterexample

Date: 2026-08-27 · Type: LIVE DERIVATION · Runtime: eleven fresh Blender 5.2 Linux/amd64 Cycles CPU workers

B49-MB-D1 froze eleven 128×72, 128-spp raw cells before its tools: six on TABLETOP's linear camera push and five on static INTERIOR. The moving cells isolated blur off, enabled shutter zero, centered shutter 0.5/1.0 and a nominally identical `[22,23]` interval expressed as START at frame 22 versus END at frame 23.

Zero shutter preserved moving Combined/Depth/Normal/Cryptomatte exactly relative to off, but changed 32,552 Vector float components. Centered 0.5 and 1.0 shutter changed 21,133 and 21,247 Combined components with RMSE 0.008706 and 0.013087. Global edge energy did not decrease monotonically, falsifying a proposed one-number blur-quality proxy.

START 1.0 at frame 22 and END 1.0 at frame 23 reproduced all seven decoded passes exactly, despite different EXR container hashes. On static INTERIOR, every blur-on cell preserved Combined/Depth/Normal/Cryptomatte exactly while Vector changed by a small amount. Vector must therefore be treated as mode-dependent representation rather than a passive image pass; Cryptomatte ID floats must not be interpreted through generic RMSE.

Centered shutter 0.5/1.0 cost only 1.008×/1.013× the off Blender render time in this bounded cell. All eleven workers completed, cleanup was zero and the independent analyzer replay was byte exact. Status: `MOTION_BLUR_DERIVATION_USABLE`.

Next: a formal unseen-frame holdout with three independent 512-spp blur references, 128-spp on/off candidates, reference-floor quality gates and pass-domain-specific static controls. Human shutter preference remains outside machine promotion.

Artifacts: `experiments/codex-worker-motion-blur-derivation-v0-1/`, `specs/codex-worker-motion-blur-derivation.v0.1.json`, `research/2026-08-27-b49-mb-d1-motion-blur-derivation-protocol.md` and `research/2026-08-27-b49-mb-d1-motion-blur-derivation-result.md`.

## J-083 · B49-MB validates the 128-spp raw point under half-frame camera exposure

Date: 2026-08-27 · Type: FORMAL HOLDOUT · Runtime: eight fresh Blender 5.2 Linux/amd64 Cycles CPU workers

B49-MB used TABLETOP frame 37, previously unobserved with blur. Three independent 512-spp centered-shutter-0.5 references established a local blur floor. A 128-spp blur-on candidate and same-seed blur-off control were compared through linear NRMSE, log-luminance RMSE and top-10%-edge RMSE. Static INTERIOR frame 19 and moving zero-shutter cells enforced the pass-domain rules derived in D1.

The blur-on candidate's floor multiples were 2.3908× linear, 2.4356× log-luminance and 2.2662× edge, all below the frozen 3× limit. It was closer than off on all three metrics, satisfying `B49_MOTION_BLUR_OPERATING_POINT_SUPPORTED`. The relative improvements were small—0.376%, 0.339% and 0.453%—and blur off would also have remained within 3× floor. This supports numerical adequacy and a consistent direction toward the blur reference, not obvious perceptual superiority.

The 128-spp blur-on render took 9.981 seconds versus 9.857 seconds off; fresh-worker wall was 19.615 versus 19.666 seconds. Moving zero-shutter and static on/off comparisons preserved Combined/Depth/Normal/Cryptomatte exactly while Vector changed 33,190 and 36,348 components. The production representation must bind Vector to blur mode.

All eight workers completed, 19/19 attacks passed, cleanup was zero and independent analysis replay was byte exact. Motion blur's bounded machine gate is closed; depth of field is next. Human preference remains a separate viewable-resolution blind review.

Artifacts: `experiments/codex-worker-motion-blur-holdout-v0-1/`, `specs/codex-worker-motion-blur-holdout.v0.1.json`, `research/2026-08-27-b49-mb-codex-worker-motion-blur-holdout-protocol.md` and `research/2026-08-27-b49-mb-codex-worker-motion-blur-holdout-result.md`.

## J-084 · B49-DOF-D1 separates focus semantics and exposes auxiliary-pass changes

Date: 2026-08-27 · Type: LIVE DERIVATION · Runtime: seven fresh Blender 5.2 Linux/amd64 Cycles CPU workers

B49-DOF-D1 first inspected the promoted scenes and found that DOF was already enabled: TABLETOP's 8.2 m focus lies inside its 7.13–10.21 m subject band, while INTERIOR's 3.2 m focus favors the 2.74–4.89 m window region rather than the 5.71–6.98 m chair. A deterministic 256×144, 256-spp fixture then placed equal projected-size stripe targets at 3, 5 and 8 m.

At f/1.4, maximum local modulation followed the requested near/mid/far focus plane in 3/3 cells. With 5 m focus fixed, the mid-plane metric remained exact as the aperture opened while near/far horizontal-gradient RMS decreased coherently. An on-axis 5 m focus object overrode a deliberately poisoned 99 m numeric distance and reproduced all seven decoded passes exactly against numeric 5 m.

DOF off versus 5 m f/1.4 changed Combined, Depth, Normal and the active Cryptomatte layer; Vector remained exact. This rejects the assumption that auxiliary geometry/ID passes remain pinhole-exact when beauty DOF is enabled. Identifier floats and far-background Depth sentinels are not generic RMSE domains.

DOF-on operator time was 1.107–1.132× off in this fixture. All seven workers completed, 15/15 attacks passed, cleanup was zero and the independent analyzer replay was byte exact. Status: `DEPTH_OF_FIELD_DERIVATION_USABLE`.

Next: freeze a two-scene, unseen-frame formal holdout with three 512-spp DOF references and paired 128-spp on/off candidates. Human focus intent and cinematic preference remain a separate blind-review gate.

Artifacts: `experiments/codex-worker-depth-of-field-derivation-v0-1/`, `specs/codex-worker-depth-of-field-derivation.v0.1.json`, `research/2026-08-27-b49-dof-d1-depth-of-field-derivation-protocol.md` and `research/2026-08-27-b49-dof-d1-depth-of-field-derivation-result.md`.

## J-085 · B49-DOF closes the two-scene machine gate but not focus intent

Date: 2026-08-27 · Type: FORMAL HOLDOUT · Runtime: ten fresh Blender 5.2 Linux/amd64 Cycles CPU workers

B49-DOF kept the promoted CENTER 0.5-frame motion blur enabled and changed only DOF. TABLETOP frame 43 and INTERIOR frame 23 each received three independent 512-spp DOF-on references plus same-seed 128-spp DOF-on/off candidates.

TABLETOP's candidate floor multiples were 2.785777× linear, 2.496550× log-luminance and 2.856265× edge. INTERIOR's were 1.789957×, 1.798302× and 2.186421×. All six values passed the frozen 3× gate, and DOF-on was closer than off in all three metrics on both scenes. The relative advantage was only 0.47–0.57% on TABLETOP but 45–64% on INTERIOR.

Both scenes reproduced D1's pass-domain boundary: Combined, Depth, Normal and active Cryptomatte layers changed; Vector stayed exact because motion-blur mode was fixed. DOF-on cost 1.0095× off render time on TABLETOP and 1.0298× on INTERIOR.

All ten workers completed, 21/21 attacks passed, cleanup was zero and independent analysis replay was byte exact. Verdict: `B49_DEPTH_OF_FIELD_OPERATING_POINT_SUPPORTED`.

This closes the bounded DOF machine gate, not artistic focus. INTERIOR's 3.2 m setting favors its window rather than the chair. Next: a viewable-resolution delayed-disclosure human review must test focus intent and cinematic preference directly.

Artifacts: `experiments/codex-worker-depth-of-field-holdout-v0-1/`, `specs/codex-worker-depth-of-field-holdout.v0.1.json`, `research/2026-08-27-b49-dof-codex-worker-depth-of-field-holdout-protocol.md` and `research/2026-08-27-b49-dof-codex-worker-depth-of-field-holdout-result.md`.

## J-086 · B50 packages the first viewable focus-intent blind review

Date: 2026-08-27 · Type: DELAYED-DISCLOSURE HUMAN PACKAGE · Runtime: two fresh Blender 5.2 Linux/amd64 Cycles CPU workers

B50 froze the exact chair-portrait brief, source scene, 960×540 render pair, 18-observer 9/9 order schedule, response schema and symmetric decision thresholds before tool implementation. A read-only real-Blender derivation measured the compiled 3.2 m focus inside the 2.74–4.89 m window range, while the semantic `PROP_CHAIR` root was at 6.452064 m and the chair-back center at 6.459178 m.

The first execution stopped before any container because projected free space missed the frozen 100 GiB reserve by about 674 MB. Removing only a 1.62 GB reconstructible Codex runtime cache allowed the unchanged gate to pass. Two fresh workers then rendered the original numeric-focus and chair-object-focus cells at 960×540, 128 raw samples. Their walls were 670.342 and 667.678 seconds. Only `camera.data.dof.focus_object` differed.

Both seven-subimage EXRs and ACES 2 review PNGs reopened successfully. The pair changed 1,553,929 scene-linear RGB values and 373,958 PNG channel values. Eighteen private anonymous sessions were generated with exact 9/9 order balance. All 21 attacks passed; an independent 29-check audit scanned 3,616 tracked/public files against the private sensitive registry and found zero matches.

A real browser pilot confirmed native/CSS 960×540 display, correct A/B switching, zero condition/repository leakage and zero console errors. It did not submit or download a response. Status: `PACKAGE_READY_HUMAN_PENDING`; human evidence remains exactly 0/18 and collection remains closed until the exact published public state passes a final leak audit.

Artifacts: `experiments/focus-intent-human-review-v0-1/`, `specs/focus-intent-human-review-spec.v0.1.json`, `research/2026-08-27-b50-focus-intent-human-review-protocol.md` and `research/2026-08-27-b50-focus-intent-package-result.md`.

## J-087 · B51-D1 exposes native Metal's warm speed and cold synchronization boundary

Date: 2026-08-27 · Type: LIVE BACKEND DERIVATION · Runtime: eight fresh native Blender 5.2 arm64 processes

B51-D1 reused the exact two B49-R 512×288 / 128-spp / seven-pass scenes in a balanced two-repeat CPU × Metal matrix. The installed Blender enumerated the Apple M4 Max CPU and 40-core Metal GPU. Both devices completed every cell.

Native four-thread CPU rendered TABLETOP in 4.112/4.122 seconds and INTERIOR in 5.090/5.029 seconds, about 36.9–37.9× faster than the qemu CPU parents. Warm Metal rendered the scenes in 0.574 and 0.695–0.717 seconds, about 7.17× faster than native CPU and 265–272× faster than qemu.

The first Metal cell instead took 109.534 seconds. Its EXR metadata reported 108.31 seconds of Cycles synchronization; a later TABLETOP Metal process reported 0.13 seconds. A post-run inventory found 79 recently modified files / 74 MiB in `~/.cache/cycles/kernels/Apple_M4_Max`. This is consistent with cold cache preparation but remains posthoc because no pre-run cache tree hash was frozen.

CPU repeat EXRs differed in container bytes only through time/date metadata while all seven decoded passes were exact. Metal repeats changed Combined, Normal and Vector floats while Depth and all Cryptomatte layers stayed exact; maximum Combined repeat difference was `1.144409e-5` on TABLETOP and `4.768372e-7` on INTERIOR.

The first audit crashed on a `str`/`Path` helper mismatch. C1 retained that exception, changed no render/result bytes, verified the original frozen tool blobs and qemu parent EXRs, and replayed the analyzer byte-exactly. Verdict: `NATIVE_CYCLES_BACKEND_DERIVATION_USABLE`, 14/14 attacks—not production promotion.

Next: freeze an atomic cache-sequester/restore experiment that distinguishes fresh process from fresh Cycles cache without deleting the user's 74 MiB cache. Then use unseen frames to set formal throughput and numerical-tolerance gates.

Artifacts: `experiments/native-cycles-backend-derivation-v0-1/`, `specs/native-cycles-backend-derivation.v0.1.json`, `research/2026-08-27-b51-d1-native-cycles-backend-derivation-protocol.md`, `research/2026-08-27-b51-c1-native-backend-audit-correction.md` and `research/2026-08-27-b51-d1-native-cycles-backend-derivation-result.md`.

## J-088 · B51-D2 falsifies the user Cycles cache as the 108-second cause

Date: 2026-08-27 · Type: REVERSIBLE CACHE INTERVENTION · Runtime: three fresh native Blender 5.2 Metal processes

B51-D2 hashed the exact 79-file / 77,737,584-byte `~/.cache/cycles` tree, atomically sequestered it without deletion, launched Metal with the path absent, retained the newly generated 75-file test cache and restored the original to the exact preflight tree hash. The quarantine path is absent; the generated test cache remains ignored for audit.

The cache-absent cell took 0.789983 seconds in Blender and 1.404792 seconds wall, with 0.34 seconds of EXR-reported synchronization. The two cache-present fresh processes took 0.578154/0.569390 seconds and 0.13 seconds synchronization each. Cache absence imposed a measurable 0.21-second penalty but did not reproduce D1's 108.31-second event. The exact user-level Cycles cache is therefore not a sufficient cause.

Cold/warm and warm/warm Metal comparisons again changed Combined, Normal and Vector while Depth and three Cryptomatte layers stayed exact; maximum Combined delta remained `1.144409e-5`.

The first analyzer failed after safe restore because Blender wrote `MM:SS.xx` while the parser required three fields. C1 retained the failure, added two-field parsing only, reran no Blender and moved no cache. Corrected replay was byte exact; current original/retained trees matched the receipt; original frozen tools matched their Git blobs; 18/18 attacks passed. Verdict: `CYCLES_CACHE_STATE_DERIVATION_USABLE`.

Next: use a pre-job Metal synchronization canary and unseen frames to freeze warm-state throughput and numerical tolerance. Treat host-session cold readiness as a separate metric; do not clear OS/Metal caches destructively to chase the 108-second event.

Artifacts: `experiments/native-cycles-cache-state-derivation-v0-1/`, `specs/native-cycles-cache-state-derivation.v0.1.json`, `research/2026-08-27-b51-d2-cycles-cache-state-derivation-protocol.md`, `research/2026-08-27-b51-d2-c1-duration-parser-correction.md` and `research/2026-08-27-b51-d2-cycles-cache-state-derivation-result.md`.

## J-089 · B51-H1 rejects a single cross-backend production contract

Date: 2026-08-27 · Type: FORMAL NATIVE BACKEND HOLDOUT · Runtime: thirteen fresh native Blender 5.2 arm64 processes

B51-H1 froze a fail-closed Metal canary and four deterministic compositions that had never been rendered in D1/D2. The canary passed before the matrix at 0.396386 seconds render, 0.14 seconds synchronization and 1.164752 seconds process wall. Each unseen composition then received one native CPU reference and two Metal candidates at the unchanged 512×288 / 128-spp / seven-pass profile.

All eight Metal candidates rendered in 0.525–0.751 seconds and their within-Metal Combined NRMSE was only `5.4e−8–1.1e−7`. Warm readiness, timing and repeatability therefore passed.

The image contract did not. CPU–Metal Depth was non-exact in all four compositions, and at least one active Cryptomatte layer was non-exact in every composition. This invalidates the inference from D1/D2's same-backend exactness to cross-backend exactness. `INTERIOR_CHAIR` also exceeded the frozen Combined limits: linear NRMSE `0.012599 > 0.0065`, log-luminance RMSE `0.003519 > 0.0016`, and edge RMSE `0.011479 > 0.0060`.

The first analysis correctly returned a negative verdict but only 18/21 attacks because the real exact-pass failure masked later injected failures. C1 isolated attack baselines without changing evidence or thresholds. The first independent replay then exposed an output/evidence-root path coupling; C2 retained that failure and bound EXR lookup to the receipt directory. Corrected audit is PASS, 21/21 attacks and byte-exact replay. Verdict: `NATIVE_METAL_PRODUCTION_HOLDOUT_NOT_SUPPORTED`.

Next: B51-D3 must localize changed Depth/Cryptomatte components and the `INTERIOR_CHAIR` beauty outlier from the retained EXRs without rerendering. Long-sequence stress is blocked until beauty and data-pass backend contracts are separated or newly justified.

Artifacts: `experiments/native-metal-production-holdout-v0-1/`, `specs/native-metal-production-holdout.v0.1.json`, `research/2026-08-27-b51-h1-native-metal-production-holdout-protocol.md`, `research/2026-08-27-b51-h1-native-metal-production-holdout-result.md`, `research/2026-08-27-b51-h1-c1-negative-baseline-audit-correction.md` and `research/2026-08-27-b51-h1-c2-audit-evidence-root-correction.md`.

## J-090 · B51-D3 separates sparse Crypto boundaries from broad low-amplitude Depth drift

Date: 2026-08-27 · Type: ZERO-RERENDER DERIVATION · Runtime: Blender 5.2 Python 3.13 / OpenImageIO 3.1.13.1

B51-D3 reopened the twelve retained H1 EXRs without launching Blender or changing source evidence. It froze pass-specific four-neighbor boundary rules, one-pixel data dilation, a 95% localization classifier, a two-pixel beauty-association mask and five diagnostic PNG mappings before the analysis tools existed.

Every changed Cryptomatte pixel was inside the frozen boundary neighborhood. Active-layer changes were sparse—4, 8, 136 and 15 pixels across the four compositions—and the same locations recurred in both Metal replicates. This is spatial classification only; identifier floats cannot be interpreted as ordinary continuous error, and semantic matte equivalence remains untested.

Depth behaved differently. CPU–Metal non-exact values covered 33.51%, 47.71%, 69.68% and 80.19% of the image; only 6.06%, 3.75%, 21.37% and 80.24% of those pixels were boundary-localized. Interior absolute differences remained small at roughly `3.34e−6–4.77e−6`, but their wide spatial support falsifies the blanket claim that all data-pass mismatch is edge noise.

The `INTERIOR_CHAIR` Combined outlier had 1,971 pixels above `1e−3` max-channel error, 829 four-connected components and a maximum channel error of `0.347776`. All `6.236593` units of squared-error energy fell inside the two-pixel-dilated data-disagreement mask, giving an association fraction of `1.0`. This supports spatial association, not a causal mechanism.

The independent audit reproduced receipt, result and five PNGs byte-exactly and passed 11/11 attacks. Verdict: `METAL_PASS_LOCALIZATION_USABLE`, evidence-core hash `9fc4b2a3…0c82`.

Next: preregister B51-H2 as a split-backend holdout. Metal beauty and CPU Depth/Cryptomatte must be merged only if cross-backend alignment, multipart representation, reproducibility and total wall cost pass new frozen gates. Otherwise Metal remains preview/beauty-only and the production data path stays CPU.

Artifacts: `experiments/native-metal-pass-localization-v0-1/`, `specs/native-metal-pass-localization.v0.1.json`, `research/2026-08-27-b51-d3-native-metal-pass-localization-protocol.md` and `research/2026-08-27-b51-d3-native-metal-pass-localization-result.md`.

## J-091 · B51-D4 exposes wall-clock metadata as the first split-assembly blocker

Date: 2026-08-27 · Type: ZERO-RERENDER ENGINEERING DERIVATION · Runtime: Blender 5.2 Python 3.13 / OpenImageIO 3.1.13.1

D4 routed Metal Combined/Normal/Vector and CPU Depth/Cryptomatte from four retained H1 EXRs into four seven-part production candidates without launching Blender. All output pixel arrays matched their selected source exactly; roster, provenance and finite-value gates passed.

The derivation remains invalid. TABLETOP_WIDE's two merge replicates differed at seven bytes—one per subimage—even though their decoded arrays were exact. Binary inspection identified the sole difference as OpenEXR `capDate`: the writes crossed from second `47` to `48`. INTERIOR_CHAIR's two writes occurred within second `48` and were byte-exact. OpenImageIO's writer source confirms that absent OIIO `DateTime` metadata is replaced with current local time and mapped to OpenEXR `capDate`.

Base status is `MERGE_REPLICATE_BYTE_IDENTITY`; only 13/15 attacks reached their intended reason because the real base failure masked two later mutations. Independent replay is `FAIL`, 1/6 byte-exact, while both frozen tool blobs still match. This is a retained negative result, not production promotion.

Two pre-result failures were also retained. A nonexistent full preregistration SHA stopped the first tool before output; C1 changed exactly that literal. The corrected tool then stopped at the 100 GiB disk reserve. Removing only 1.6 GiB of previously authorized, reconstructible Playwright cache allowed the unchanged gate to admit the formal run.

Next: preregister a narrow `Date` → `DateTime` normalization correction, rerun assembly without Blender, require all four outputs and independent replay byte-exact, then—and only then—design B51-H2 on unseen renders.

Artifacts: `experiments/native-split-backend-assembly-derivation-v0-1/`, `experiments/native-split-backend-assembly-derivation-preflight-failure-v0-1/`, `experiments/native-split-backend-assembly-derivation-capacity-failure-v0-1/`, `research/2026-08-27-b51-d4-native-split-backend-assembly-invalid-result.md`, `research/2026-08-27-b51-d4-c1-preregistration-sha-correction-protocol.md` and `research/2026-08-27-b51-d4-c2-capacity-readmission-protocol.md`.

## J-092 · B51-D4-C3 makes known-pair split assembly reproducible

Date: 2026-08-27 · Type: PREREGISTERED METADATA CORRECTION · Runtime: Blender 5.2 Python 3.13 / OpenImageIO 3.1.13.1

C3 changed only the missing output `DateTime` rule. It required each pair's frozen Metal Combined `Date`, converted the date separators from slash to colon, and applied that capture value to every output subimage. All pixel, routing, metadata, provenance, disk and operation boundaries remained frozen.

TABLETOP_WIDE's two corrected multipart EXRs now share SHA-256 `8157aab6…729de9`; INTERIOR_CHAIR's share `cbd80be0…cf9cc`. All 28 reopened subimages carry the expected pair-specific `DateTime`. Every selected float array remains exact to its CPU/Metal source.

All 15 original attacks and four correction attacks passed. Independent replay reproduced receipt, result and four EXRs byte-for-byte; both frozen tool blobs matched. Verdict: `NATIVE_SPLIT_BACKEND_ASSEMBLY_CAPDATE_CORRECTION_USABLE`.

This closes only the known-input assembly engineering gate. Next is a separately preregistered B51-H2 with unseen Blender renders, total split-vs-CPU wall cost and clean-replicate evidence. Human B50 remains 0/18.

Artifacts: `experiments/native-split-backend-assembly-capdate-correction-v0-1/`, `specs/native-split-backend-assembly-capdate-correction.v0.1.json`, `research/2026-08-27-b51-d4-c3-capdate-normalization-correction-protocol.md` and `research/2026-08-27-b51-d4-c3-capdate-normalization-correction-result.md`.

## J-093 · B51-D5 finds no exact CPU data-pass sample discount

Date: 2026-08-27 · Type: REAL BLENDER DOSE–RESPONSE · Runtime: 32 fresh native Blender 5.2 CPU processes

D5 held two H1 compositions, seed, camera/geometry/light operations, 512×288 profile and seven-pass EXR contract constant while varying Cycles samples through 1/2/4/8/16/32/64/128, with two fresh-process repeats per cell.

All 32 renders completed, and every same-dose repeat reproduced the four data passes exactly. Both new 128-spp repeats also reproduced the frozen H1 CPU parent exactly. No lower dose did so on both variants. The exact floor is therefore 128 spp and the valid verdict is `EXACT_CPU_DATA_SAMPLE_REDUCTION_NOT_OBSERVED`.

At 64 spp, TABLETOP Depth changed on 63.26% of pixels and INTERIOR_CHAIR on 100%; CryptoObject00 changed on roughly 2.8–3.0%. These measurements do not establish semantic failure because background sentinels and Cryptomatte ID/coverage encoding make raw absolute error misleading. D5 deliberately promotes no tolerance.

The analyzer passed 18/18 attacks. Independent replay was byte-exact, all four frozen tool blobs matched and 32/32 EXR identities matched. Two zero-render preflight identity failures—wrong OCIO path, then wrong Blender executable binding—remain published with narrow C1/C2 corrections.

Next: B51-D6 must evaluate task-relevant Depth regions and decoded Cryptomatte mattes before any non-exact sample reduction can enter H2. Under the current exact contract, split rendering has no demonstrated cost advantage because it still pays for a full 128-spp CPU render plus Metal.

Artifacts: `experiments/native-cpu-data-pass-sample-cost-derivation-v0-1/`, `experiments/native-cpu-data-pass-sample-cost-preflight-failure-v0-1/`, `experiments/native-cpu-data-pass-sample-cost-blender-identity-failure-v0-1/`, `research/2026-08-27-b51-d5-native-cpu-data-pass-sample-cost-derivation-result.md`, `research/2026-08-27-b51-d5-c1-ocio-identity-correction-protocol.md` and `research/2026-08-27-b51-d5-c2-blender-identity-correction-protocol.md`.

## J-094 · B51-D6 closes the low-sample split-production hypothesis

Date: 2026-08-27 · Type: ZERO-RERENDER SEMANTIC DERIVATION · Runtime: Blender Python 3.13 / OpenImageIO 3.1.13.1

D6 reused all 32 retained D5 EXRs and decoded CryptoObject00/01/02 as six ranked ID/coverage pairs under the Cryptomatte 1.2.0 contract. It reconstructed manifest-addressed object mattes instead of treating ID floats as continuous error. Depth was separated into foreground topology and stable, non-transition surfaces.

The production-semantic profile froze exact 0.5 hard mattes, exact dominant IDs on parent-confident pixels, 8/10/12-bit alpha error bounds, exact foreground topology and 1 mm p99 / 1 cm max stable-surface depth bounds before analyzer implementation.

No 1–64 spp dose passed both variants and repeats. At 64 spp, TABLETOP and INTERIOR had 10/102 confident dominant-ID mismatches, 53/205 total hard-matte mismatches and worst matte alpha errors of 0.09375/0.15625. TABLETOP stable Depth p99 was 2.802 mm with 56 foreground-mask mismatches; INTERIOR p99 was 73.200 mm and max 182.019 mm. Both semantic floors remained 128 spp.

All 32 EXR identities and metadata contracts matched; unresolved IDs, coverage-range/sum faults, rank inversions and duplicate active IDs were zero. The first analysis result was rejected before audit because its provided full tool-freeze SHA did not resolve; C1 changed only that identity. Corrected audit is PASS, analyzer replay byte-exact, 16/16 attacks, 2/2 frozen tools and 32/32 artifacts.

Verdict: `CPU_DATA_SEMANTIC_SAMPLE_REDUCTION_NOT_OBSERVED`. H2 is no longer justified as a cost-saving split-production route. Metal remains preview/lookdev or beauty-only evidence; production cost work pivots to the single native CPU path. B50 remains independently 0/18 human pending.

Artifacts: `experiments/native-cpu-data-pass-semantic-equivalence-derivation-v0-1/`, `experiments/native-cpu-data-pass-semantic-equivalence-tool-identity-failure-v0-1/`, `specs/native-cpu-data-pass-semantic-equivalence-derivation.v0.1.json`, `research/2026-08-27-b51-d6-native-cpu-data-pass-semantic-equivalence-derivation-result.md` and `research/2026-08-27-b51-d6-c1-tool-freeze-identity-correction-protocol.md`.

## J-095 · B52-D1 exposes inherited adaptive sampling in the supposed fixed parent

Date: 2026-08-27 · Type: INVALID FORMAL DERIVATION + ZERO-RENDER ROOT-CAUSE DIAGNOSIS · Runtime: thirty fresh native Blender 5.2 CPU render processes plus two read-only Blender probes

B52-D1 froze three independent 512-spp references and six 128-spp profiles across TABLETOP_WIDE and INTERIOR_CHAIR. Every cell emitted Combined, Depth, Normal, Vector, three Cryptomatte ranks and Debug Sample Count. All 30 processes completed, all twelve repeated candidate cells reproduced eight decoded parts exactly, and both three-reference groups were distinct.

The experiment is invalid rather than positive or negative. Its true non-adaptive FIXED_128 control reproduced only 3/7 D5 parent passes on TABLETOP and 2/7 on INTERIOR. Combined, Normal, Vector and active Cryptomatte layers changed; Depth remained exact. The preregistered `FIXED128_PARENT_CONTROL` therefore failed before candidate selection.

Two zero-render Blender probes found `use_adaptive_sampling=True`, threshold approximately `0.01` and min samples `0` in both exact source `.blend` files. The frozen D5 renderer never assigned or reported those properties. B52's explicit `ADAPT_T010_M0` reproduced both D5 parents across all seven passes, proving that D5/D6 used an inherited adaptive-max-128 parent rather than a non-adaptive fixed baseline.

The failure chain is retained. The first analyzer attempt reached attack A16 after all renders and failed on a no-argument dictionary `pop`; C1 fixed only that mutation. C1 then misclassified six finite/in-range candidates that reached max everywhere as invalid experiment inputs; its 10/20 result remains byte-preserved. C2 separated measurement validity from candidate eligibility and exposed the real parent-control failure. The final independent replay is byte-exact and matches 30/30 artifacts, every input and frozen tool, but audit status remains FAIL and attacks 11/20 because the base gate is genuinely false.

Descriptively, every adaptive candidate passed beauty, but the largest per-scene render savings were only 14.67% and 9.62%, below the frozen 20%, and no adaptive profile passed the complete data/auxiliary/sample/cost conjunction. These values cannot be promoted from an invalid experiment.

Next: B52-D2 must explicitly define the actual production baseline as adaptive `0.01/min0/max128`, use fresh seeds and test looser thresholds. D5/D6 remain max-sample evidence only inside their inherited adaptive configuration.

Artifacts: `experiments/native-cpu-adaptive-quality-cost-derivation-v0-1/`, `specs/native-cpu-adaptive-quality-cost-derivation.v0.1.json`, `research/2026-08-27-b52-d1-native-cpu-adaptive-quality-cost-derivation-result.md`, `research/2026-08-27-b52-d1-c1-analysis-tool-correction-protocol.md` and `research/2026-08-27-b52-d1-c2-sample-count-classification-correction-protocol.md`.

## J-096 · B52-D1 evidence reaches both production publications

Date: 2026-08-27 · Type: EXACT-SOURCE PUBLICATION + DELAYED-DISCLOSURE AUDIT · Runtime: GitHub Pages and owner-only Sites

The B52-D1 result, failure chain, sample-count visualization and upstream-control diagnosis were published from exact source commit `c044d3a31ceecf53a6e201ad70f306102f19a3ab`. GitHub Pages completed both build and deploy jobs. The owner-only Sites publication saved the same commit as version 46 and deployed it successfully; browser verification found the B52-D1 and INVALID content on the production route.

The Sites source Git service returned HTTP 500 for the initial approximately 91 MiB evidence pack. No success was inferred from Git's trailing text: `ls-remote` proved the branch was still old. The immutable blobs were then transferred through eight temporary 7.4–12.9 MB staging commits, the exact source HEAD was pushed, its remote SHA was verified and the temporary branch was deleted. The public source history was not rewritten.

The B50 exact-public-state audit then scanned the exact Git HEAD plus static build: 4,098 files, zero sensitive-registry matches and human responses still 0/18. Status: `BFS_B50_EXACT_PUBLIC_STATE_PASS`. This closes publication isolation only; it does not manufacture human evidence or open collection by itself.

Published routes: `https://lovejzzz.github.io/BlenderFilmStudio/adaptive-cpu-v0-1/` and `https://blender-film-studio-research.skylab.chatgpt.site/adaptive-cpu-v0-1/`.

## J-097 · B52-D2 freezes the real production adaptive baseline

Date: 2026-08-27 · Type: CONFIRMATORY HOLDOUT PREREGISTRATION · Runtime: zero D2 renders

B52-D2 explicitly defines the production CPU control as `adaptive=true, threshold=0.01, min=0, max=128`. It does not relabel the invalid D1 experiment. The protocol discloses that all D1 candidate measurements were already observed and uses them only to choose a new hypothesis grid.

The holdout freezes eight looser candidates—thresholds 0.015/0.02/0.03/0.05 crossed with min samples 0/32—against the production control. Two compositions × nine profiles × three repeats require 54 fresh Blender processes. Every new cell uses the previously unused `seedOffset=758759`; only the six immutable D1 512-spp reference EXRs are reused.

A candidate must pass every beauty, decoded Depth/Cryptomatte, exact Normal/Vector, Sample Count mechanism and per-variant 20% median render-saving gate. Fresh-process wall is recorded but not promoted as marginal render cost. Failure of baseline validity makes the experiment INVALID; an intact baseline with no eligible candidate yields NOT_SUPPORTED.

The exact auxiliary-pass requirement is deliberately conservative because no downstream task-specific Normal/Vector tolerance has been validated. A candidate blocked only there cannot be posthoc promoted; it would justify a separately preregistered semantic derivation.

Artifacts: `specs/native-cpu-adaptive-production-holdout.v0.1.json` and `research/2026-08-27-b52-d2-native-cpu-adaptive-production-holdout-protocol.md`.

## J-098 · B52-D2 tools freeze with zero formal renders

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Runtime: host Python plus one zero-render Blender 5.2 process

The D2 renderer, runner, analyzer, independent audit and synthetic analysis-contract test were frozen at commit `d0e6e157c83aa72e77bce560caf9d42974b42d3a`. The receipt also binds the reused D1 renderer/analyzer libraries, so imported code cannot escape the frozen-tool audit.

The frozen runner resolved seven parent identities, two source `.blend` files plus OCIO, six immutable references, seven tool blobs and the exact Blender executable. It expanded the preregistered matrix to 54 cells and admitted the projected 384 MiB write while preserving the 100 GiB reserve: 108,337,467,392 bytes free before projection and 107,934,814,208 after projection.

A real Blender 5.2 process loaded TABLETOP, replayed four registered scene operations, selected only the Apple M4 Max CPU and observed the explicit production control as adaptive true, max 128, threshold `0.009999999776...`, min 0, four threads and Sample Count enabled. It performed zero renders and wrote no formal output.

Four synthetic contract tests passed under Blender's Python/OpenImageIO runtime. They prove that the validator distinguishes a valid positive from a valid no-selection negative, classifies baseline failure as INVALID, catches cost-field tampering and routes all 22 injected attacks to their expected failure reasons. These tests validate decision logic, not image quality.

The formal D2 output root remains absent. Next is the unchanged 54-process run, followed by analyzer replay and independent audit before any production claim.

Artifact: `experiments/native-cpu-adaptive-production-preflight-v0-1/observation.json`.

## J-099 · B52-D2 finds a real cost curve but no production-safe global point

Date: 2026-08-27 · Type: CONFIRMATORY NATIVE CPU HOLDOUT · Runtime: 54 fresh Blender 5.2 processes

D2 replaced the invalid fixed control with the explicitly configured production baseline `adaptive=true / threshold=0.01 / min=0 / max=128`. Six baseline cells passed beauty, Sample Count, Cryptomatte structure and three-repeat exactness. All 54 processes completed with unique PIDs and zero timeouts; all 18 profile × variant groups reproduced eight decoded parts across three repeats exactly.

The cost mechanism is real. Every candidate reduced median mean effective samples on both scenes. Five of eight profiles saved at least 20% render time on both scenes; the highest worst-scene saving was 44.79% at 0.05/min32.

No profile passed the joint production contract. TABLETOP beauty passed through threshold 0.03, but INTERIOR failed from the mildest 0.015 profile onward. Depth passed all 48 candidate cells with zero measured difference under the D6 domains. Cryptomatte passed 0/48: even 0.015/min0 produced 7 TABLETOP hard-matte mismatches and 15 INTERIOR confident-ID / 30 hard-matte mismatches. Normal and Vector were non-exact in 48/48 cells.

The result is a valid negative: `NATIVE_CPU_ADAPTIVE_PRODUCTION_HOLDOUT_NOT_SUPPORTED`, selected profile null, base failure null, 22/22 attacks. The independent audit reproduced results byte-exactly and matched seven frozen tools, every bound input and 54/54 EXRs.

Next: a zero-rerender B52-D3 must derive task-specific Crypto/Normal/Vector semantics from the retained EXRs without retroactively promoting D2. A separate fresh-seed experiment may then test a scene-conditioned fine threshold curve; INTERIOR beauty prevents any current global promotion.

Artifacts: `experiments/native-cpu-adaptive-production-holdout-v0-1/`, `research/2026-08-27-b52-d2-native-cpu-adaptive-production-holdout-result.md` and `specs/native-cpu-adaptive-production-holdout.v0.1.json`.

## J-100 · B52-D3 freezes a zero-rerender payload task-semantics derivation

Date: 2026-08-27 · Type: PREREGISTERED DERIVATION · Formal renders: 0

D3 is explicitly downstream of fully observed D2 evidence. It cannot relabel D2's valid negative, select thresholds as if they were unseen, or claim production safety. Its only permitted output is a falsifiable candidate contract for a later fresh-seed holdout.

The frozen input binds the exact D2 spec, 54-run receipt, result and audit hashes. All 54 retained EXRs must be reverified, all 18 profile × variant three-repeat groups must remain exact across eight decoded parts, and only then may repeat 1 represent the 16 candidate–baseline pairs. Blender processes, renders, network calls and model calls are all frozen at zero.

The baseline-only spatial contract separates one-pixel-dilated Cryptomatte boundaries from confident stable interiors. Cryptomatte is measured as per-object matte error and two unit-contrast composites; Normal as angular error plus five Lambertian probes; Vector as two unnamed endpoint pairs without asserting previous/next direction. Three frozen profiles × two variants × three pass maps produce exactly 18 diagnostic PNGs. Thirteen attacks cover parent/artifact identity, pass and repeat rosters, all task measurements, diagnostic totality, decision replay, operation boundary and self-hash.

The first machine-readable preregistration had SHA-256 `a1bec59991eac984cdfd17659e5353e705b95ccf4e24b83935f65b6c10eb541a`. Before any D3 measurement or analyzer implementation, a recorded amendment froze the missing diagnostic visualization contract: fixed clip maxima `0.05`, `2°` and `1/64`, fixed RGB8 `(t, t², 0)` encoding, and canonical sidecar identities. The amended spec SHA-256 is `88f9284e014a5c4020aed374eef306cf22ed1c1badf5e680d93a919038526b7d`. Next: freeze the analyzer and independent audit before reading any derived measurement. A usable derivation may still select no future profile; no outcome can promote D2 retroactively.

Artifacts: `specs/adaptive-payload-semantics-derivation.v0.1.json` and `research/2026-08-27-b52-d3-adaptive-payload-semantics-derivation-protocol.md`.

## J-101 · B52-D3 is usable, with zero future holdout candidates

Date: 2026-08-27 · Type: ZERO-RERENDER DERIVATION · Blender processes: 0

The D3 tools were frozen at commit `189857f2a74e235862006b542f6b6bf5087aff1d` after six synthetic tests passed, including all 13 attack routes and byte-deterministic PNG/sidecar generation. Only then did the formal analyzer open the 54 retained D2 EXRs.

All 54 artifacts, eight-part rosters, two Cryptomatte manifests and 18 three-repeat groups passed identity and exactness checks. The analyzer measured 16 candidate–baseline pairs and wrote 18 fixed-scale diagnostic PNGs plus 18 canonical sidecars without launching Blender or rendering.

Cryptomatte passed only TABLETOP `0.015/min0` and `0.02/min0`. Every pair had zero stable-interior dominant-ID mismatch, zero stable-interior hard-matte mismatch and 100% changed-alpha boundary localization, but INTERIOR and wider profiles exceeded the frozen composite/outlier amplitude limits. Normal and Vector passed 0/16. Normal maximum angle was 3.55–11.65 degrees and Lambertian maximum error 0.0599–0.1518. Vector endpoint magnitudes were far below their gates, yet INTERIOR had 530–890 stable-interior support mismatches and all changed-pixel localization fractions were only 3.19–6.61%.

The formal verdict is `ADAPTIVE_PAYLOAD_SEMANTICS_DERIVATION_USABLE` with an empty future-candidate list. The independent audit replayed the result byte-exactly, matched 54/54 EXRs, 36/36 diagnostic artifacts, five frozen tools and 13/13 attacks. D2 remains a valid negative.

Next: B52-D4 should preregister magnitude-weighted Normal/Vector localization and a deterministic downstream Vector Blur/warp task on the retained EXRs. It may propose a later holdout but cannot revise D2 or bypass the still-failing INTERIOR beauty gate.

Artifacts: `experiments/adaptive-payload-semantics-derivation-v0-1/` and `research/2026-08-27-b52-d3-adaptive-payload-semantics-derivation-result.md`.

## J-102 · B52-D4 freezes a real Blender 5.2 Vector Blur task

Date: 2026-08-27 · Type: PREREGISTERED COMPOSITOR DERIVATION · Formal outputs: 0

D3 left one narrow ambiguity. Candidate Vector endpoint errors were far below the frozen p99 and maximum limits, but exact nonzero-support counts and changed-pixel localization rejected every pair. D4 asks whether those small payload differences materially change Blender's designated downstream Vector Blur task when baseline Combined and Depth are held fixed.

Five zero-render interface probes preceded preregistration and are explicitly exploratory. The first preserved failure is important: the Blender 4.x `Scene.node_tree` path no longer exists in Blender 5.2. The valid API creates an independent `CompositorNodeTree`, binds it through `Scene.compositing_node_group`, addresses Vector Blur inputs by `Image`, `Speed`, `Z`, `Samples` and `Shutter` identifiers, and terminates at Group Output. The retained D2 multipart EXR exposes the expected Combined, Depth and Vector sockets. Factory compositor execution defaults to GPU, so the formal contract explicitly uses CPU and four fixed threads.

The frozen matrix is two variants × baseline plus eight candidates × two fresh processes: 36 Blender 5.2 compositor outputs. Every graph receives baseline Combined and baseline Depth; only the Vector source varies. Samples are 32 and Shutter is 0.5. Each process starts from factory state, opens no source `.blend`, writes one RGBA32 ZIP EXR and counts its render call honestly, while Cycles ray renders remain zero.

Input Vector and output RGB errors use squared-energy localization inside a motion-radius-dilated Cryptomatte boundary. The output gates are fixed before output exists: p99 `1/1024`, maximum `1/255`, RMSE `1/4096`, alpha maximum `1/65536`, at least 95% input/output error energy inside the influence domain and zero outside-domain pixels above `1/4096`. A profile must pass both variants and exact decoded repeats. Passing can only propose a Vector contract; it cannot revise D2/D3, Normal, Crypto or INTERIOR beauty.

The first formal D4 compositor output does not yet exist. Next: freeze runner, Blender graph compiler, analyzer, independent audit and synthetic attacks before executing the 36-process matrix.

Artifacts: `specs/adaptive-vector-blur-semantics-derivation.v0.1.json`, `experiments/adaptive-vector-blur-semantics-preflight-v0-1/observation.json` and `research/2026-08-27-b52-d4-adaptive-vector-blur-semantics-derivation-protocol.md`.

## J-103 · B52-D4 tools freeze after a retained Blender counterexample

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs: 0

The D4 Blender worker, matrix runner, analyzer, independent audit and six-test synthetic contract suite were frozen and pushed at commit `842af415f7a29393a81ac94b24744f05d440baa5`. The frozen receipt binds seven tool blobs because the analyzer also imports the D2 common library and D3 spatial analyzer.

Three non-formal real-Blender worker probes were retained rather than silently discarded. The first failed before rendering because Blender 5.2 exposes the Group Output socket with visible name `Image` but internal identifier `Socket_0`; the draft graph contract had incorrectly expected the identifier to equal the name. After correcting and testing that exact boundary, two fresh CPU/four-thread Blender processes each evaluated the real four-node compositor and wrote RGBA32 EXRs. Their container hashes differed, but both decoded to the same bit-exact pixel hash `ec74fd9a12e86150b458a8a54c83de939f14af8ebc77ba191ca29d33d89da631`. This confirms why the preregistered repeat gate compares decoded pixels rather than mutable EXR container bytes. These scratch outputs are development evidence only and cannot be promoted into D4 measurements.

The post-freeze zero-formal-output preflight then matched all seven frozen tools, five parent files, 54 parent EXRs, Blender executable and OCIO identities. It performed zero Blender processes, zero render calls and zero formal measurements; the formal output root remained absent. Disk admission passed narrowly: 107,916,320,768 bytes were free, and the projected 256 MiB write left 107,647,885,312 bytes, still above the frozen 100 GiB reserve.

Next: execute the unchanged 36-process matrix, retain any failed cell, analyze only after all outputs exist, and run byte-exact independent replay before publishing a claim.

Artifacts: `experiments/adaptive-vector-blur-semantics-preflight-v0-1/worker-smoke-observation.json` and `experiments/adaptive-vector-blur-semantics-preflight-v0-1/frozen-tool-preflight.json`.

## J-104 · B52-D4 is invalid because the designated task does not move enough

Date: 2026-08-27 · Type: REAL BLENDER COMPOSITOR DERIVATION · Blender processes: 36

All 36 fresh Blender 5.2 CPU compositor processes succeeded with unique PIDs, zero timeouts and 36 finite RGBA32 EXRs. Eighteen two-process groups reproduced decoded pixels exactly. Parent/source identity, the four-node graph and the Blender 5.2 RNA contract all held.

The experiment nevertheless failed its earliest semantic gate. Baseline Vector Blur changed no RGB pixel by more than the preregistered `1/65536` minimum on either scene. TABLETOP's maximum change was `3.814697e-6`; INTERIOR's was `1.192093e-7`. Candidate blur outputs were decoded-identical to their baseline outputs, but that equality is not evidence of safety because the chosen task first failed to demonstrate sensitivity.

The first frozen analysis attempt also produced a retained software failure after all compositor outputs existed: a NumPy boolean was not strict-JSON serializable. The original receipt and traceback remain published. A post-output amendment frozen at `6d64a5ca2f2b4a83bc9f51fa2054133639c3e762` only casts NumPy booleans, adds one regression test and audits the old/new receipt boundary. It changed no gate and reused all 36 EXRs without rerendering.

The final result is `ADAPTIVE_VECTOR_BLUR_SEMANTICS_DERIVATION_INVALID`, base failure `BASELINE_EFFECT`, candidates empty and attacks 12/19 because the real early failure masks seven later attack routes. Independent replay is byte-exact and every artifact identity check passes, but the audit correctly returns `FAIL`: the record is reproducible, while the intended inference is not established.

Next: preregister D5 as a baseline-only controlled-motion calibration followed by a fresh animated holdout. It must establish a non-trivial task response before inspecting candidate equivalence; otherwise Blender Vector Blur should be retired as the oracle for this question.

Artifacts: `experiments/adaptive-vector-blur-semantics-derivation-v0-1/` and `research/2026-08-27-b52-d4-adaptive-vector-blur-semantics-derivation-result.md`.

## J-105 · Controlled motion proves the Blender node is responsive

Date: 2026-08-27 · Type: EXPLORATORY REAL-BLENDER TASK CALIBRATION · Formal claims: 0

D4 could not distinguish candidate Vector outputs because its retained scenes produced too little effective motion. A new non-formal fixture therefore used an orthographic camera, a high-contrast moving plane, a static foreground occluder and known linear keyframes at frames 0/1/2. No adaptive candidate was opened.

Two failures remain part of the record. Attempt 0 used the rejected `BLENDER_EEVEE_NEXT` enum; Blender 5.2 exposed `BLENDER_EEVEE`, `BLENDER_WORKBENCH` and `CYCLES`. Attempt 1 then hit the Blender 5.2 layered Action migration: `Action.fcurves` is absent, while keyframe curves live under `Action.layers[].strips[].channelbags[].fcurves[]`. Both failures occurred before rendering.

Attempt 2 used real Blender EEVEE; attempt 3 repeated the fixture with Cycles CPU at 16 fixed samples. Cycles produced a maximum Vector magnitude of 51.200012 pixels. Real Blender Vector Blur at shutters 0.25, 0.5 and 1.0 changed 15,375–15,390 pixels above `1/65536`; RGB maximum error rose from 0.872852 to 0.985832 to 1.039586, and RMSE rose from 0.042492 to 0.060361 to 0.086440. Maximum and RMSE were both strictly dose ordered.

This is exploratory support that Blender 5.2 Vector Blur is not universally inert. It does not validate an adaptive profile or become a holdout. The next formal question can now freeze controlled object motion, controlled camera motion and a static negative control before implementing the formal tool.

Artifacts: `blender/probe_b52_d5_controlled_motion.py`, `scripts/analyze-b52-d5-controlled-motion-preflight.py` and `experiments/controlled-motion-vector-blur-preflight-v0-1/`.

## J-106 · B52-D5 freezes task validity before a formal tool exists

Date: 2026-08-27 · Type: CONFIRMATORY TASK-CALIBRATION PREREGISTRATION · Formal outputs: 0

D5 separates task validity from adaptive-profile evaluation. It freezes two generated moving fixtures—object translation across a static occluder and orthographic camera translation over layered geometry—plus a no-keyframe negative control. No source `.blend`, external asset or adaptive candidate is permitted.

Each fixture requires two fresh Cycles CPU source renders and four shutter settings through two fresh compositor repeats. The resulting boundary is 30 unique Blender 5.2 processes, six multipart sources, 24 RGBA compositor outputs and 30 render calls. All eight decoded source parts and all 12 compositor repeat pairs must reproduce exactly.

The task must distinguish motion from stasis before it can be used as an oracle. Both moving fixtures need non-trivial Vector magnitude, shutter-zero identity, a material shutter-0.5 response and strict 0.25→0.5→1.0 maximum/p99/RMSE dose ordering. The static control must retain near-zero Vector and pixel identity at every shutter. Nine fixed-scale diagnostics and 20 adversarial attacks are preregistered.

All bound D4, exploratory-observation, Blender executable and OCIO hashes were rechecked before this entry. The formal output root was absent. The preregistered spec SHA-256 is `5c2e6564650d6ab6d98f6bb7d91da4304c1cfeece4601871ed74fe5fd5521e01`; the protocol SHA-256 is `33411d6348554470fb70a4c69ff985d47b3396b007f56e2268cfb8fa09b149c2`.

Passing permits only a separately frozen fresh adaptive-Vector holdout. Failure retires Blender Vector Blur as this branch's oracle and moves the next falsifiable test to deterministic warp or independent optical flow. Neither outcome can revise D2, D3 or D4.

Artifacts: `specs/controlled-motion-vector-blur-calibration.v0.1.json` and `research/2026-08-27-b52-d5-controlled-motion-vector-blur-calibration-protocol.md`.

## J-107 · B52-D5 tools freeze with a narrow but valid disk admission

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs: 0

The generated-scene worker, Blender 5.2 compositor worker, matrix runner, analyzer, independent audit and five-test contract suite were frozen and pushed at commit `19e96dc99bd117bfcadaf6d82ea9e0237a814c85`. All 20 attacks route from an independent synthetic-valid evidence base, so an early scientific failure cannot mask later validator checks. Audit integrity is also separated from the scientific verdict: intact INVALID evidence may audit PASS.

Before freezing, real Blender development smoke covered all three fixtures and all four shutters. Both moving fixtures passed the intended sensitivity and dose behavior. The static fixture retained pixel identity at every shutter but exposed Vector p99 noise of about `1.90735e−5`, slightly above the already frozen `1/65536` static gate. That observation did not change the preregistered threshold. A separate pair of fresh static processes reproduced 8/8 multipart source arrays and the shutter-0.5 compositor output exactly.

The post-freeze preflight matched six Git-frozen tool blobs, seven parent records, Blender and OCIO identities. It launched zero Blender processes, performed zero renders and confirmed that the formal output root was absent. Disk admission was narrow: 107,645,112,320 bytes free before a projected 134,217,728-byte write, leaving 107,510,894,592 bytes above the frozen 100 GiB reserve. The preflight SHA-256 is `4934d69cd76ffe4e766bef96133c7d35a53554007fee8ecc6c33f6e92fe582a4`.

Next: run the unchanged 30-process matrix. A static-control failure is a valid calibration result, not permission to relax the gate.

Artifact: `experiments/controlled-motion-vector-blur-calibration-preflight-v0-1/frozen-tool-preflight.json`.

## J-108 · B52-D5 retires Vector Blur as this branch's oracle

Date: 2026-08-27 · Type: CONFIRMATORY REAL-BLENDER TASK CALIBRATION · Blender processes: 30

All six fresh Cycles sources and 24 fresh compositor cells completed with 30 unique PIDs. The three fixtures reproduced 24/24 decoded multipart pass pairs and 12/12 decoded compositor pairs exactly. The contract suite passed 20/20 attacks without early-failure masking.

Both moving fixtures passed. Object translation produced a 51.200012 px Vector maximum and shutter 0.25/0.5/1.0 RMSE of 0.042265/0.060391/0.086485. Camera translation produced a 25.600033 px maximum and RMSE of 0.035245/0.051398/0.074459. Their maximum, p99 and RMSE sequences were strictly increasing; shutter-zero changed no pixel above `1/65536`.

The static negative control failed one frozen gate. Its Vector maximum was only `2.67029e−5` px, but p99 was `1.90735e−5`, above `1/65536`. This floor was decoded-repeat-exact. All four static compositor outputs nevertheless stayed below the pixel threshold, with RGB maximum `2.38419e−7` and zero changed pixels above `1/65536`.

Verdict: `CONTROLLED_VECTOR_BLUR_TASK_CALIBRATION_INVALID`, base failure `STATIC_NEGATIVE_CONTROL`. The audit is independently `PASS`: result replay byte-exact, 6/6 source artifacts, 24/24 compositor artifacts, 30/30 reports, 18/18 diagnostic artifacts and all frozen inputs/tools matched. Audit PASS means the invalid evidence is intact; it does not reverse the scientific result.

Per the preregistered decision rule, no adaptive-Vector holdout will be created. The next task oracle will be a separately preregistered deterministic warp or independent optical-flow task; the preferred first route is a CPU reference warp with explicit coordinates, sampling kernel and occlusion policy.

Artifacts: `experiments/controlled-motion-vector-blur-calibration-v0-1/` and `research/2026-08-27-b52-d5-controlled-motion-vector-blur-calibration-result.md`.

## J-109 · B52-D6 freezes an independent pixel-warp oracle

Date: 2026-08-27 · Type: PREREGISTERED DETERMINISTIC-WARP CALIBRATION · Formal outputs: 0

D5 retired Blender Vector Blur as this branch's oracle, so D6 moves the definition of correctness outside Blender. Official 5.2 documentation and real RNA agree that Displace now consumes a two-dimensional pixel displacement directly and exposes interpolation plus per-axis extension; the legacy Scale X/Y inputs and `Scene.node_tree` path are absent.

Three exploratory boundaries are retained. A mutation-heavy multi-node RNA comprehension crashed one zero-render process with exit 139, while fresh single-node read-only probes succeeded. The first pixel probe then failed before rendering because the bound ACES 2.0 configuration has no `Non-Color` enum; `Raw` is the valid data space. The final 8×6 real-compositor probe executed seven cases and found zero decoded float32 error for zero/integer/subpixel displacement, a destination-sampled step field, Clip/Extend/Repeat and changing alpha.

Those observations freeze, but cannot satisfy, the formal contract. In top-left decoded coordinates the independent source lookup is `(u,v)=(x-dx,y+dy)`. Seven 64×48 analytic fixtures cover zero, positive/negative integer, binary-exact subpixel bilinear, a two-axis destination step field and both non-Clip extension modes. Each receives two fresh Blender processes: 14 unique PIDs, 14 compositor calls and zero Cycles ray renders. The Blender result and independent NumPy float32 reference must have identical canonical array hashes, and each nonzero task must separately pass a sensitivity gate.

The formal output root is absent. The preregistered spec SHA-256 is `28d3c0b292b89d5d056d5521aececbfb6d88b70971d2b500fbff69d2498703be`; protocol SHA-256 is `ba567ec8c66094874b6d8304f0d40d1456bf2b5e19be84cd80088461b9e2b874`. Passing will validate only the tested 2D sampling primitive and permit a separate depth/layer-aware temporal experiment; it will not validate occlusion, motion blur, Vector, adaptive sampling or cinematic quality.

Artifacts: `specs/deterministic-displace-calibration.v0.1.json`, `research/2026-08-27-b52-d6-deterministic-displace-calibration-protocol.md`, `blender/probe_b52_d6_displace_semantics.py` and `experiments/deterministic-warp-preflight-v0-1/`.

## J-110 · B52-D6 tools freeze with a preserved Bilinear counterexample

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs: 0

The independent reference, Blender worker, runner, analyzer, audit and seven-test contract suite were frozen and pushed at commit `764ad216a77748026aca340a9a5e8f02fa544ccd`. All 20 attacks route independently from synthetic-valid evidence. A synthetic receipt built from the real smoke outputs also reaches the frozen `REFERENCE_MATCH` failure instead of crashing the analyzer.

Seven pre-freeze real Blender worker smokes covered every fixture. Zero, both signed integer Clip cases, the destination-sampled step field, Extend and Repeat matched the independent float32 reference exactly. The Bilinear fixture did not: its maximum absolute error was `1.7583370208740234e-6`, RMSE `4.569772209229176e-8`. This is below `1/65536` but violates the already frozen exact-array gate, so the smoke was retained and no threshold was changed.

The first frozen preflight was correctly blocked because free space had fallen below the 100 GiB reserve. Only explicitly authorized regenerable caches were removed: 845 MiB of `/tmp/bfs-*` scratch artifacts and 317 MiB of Colima cache; no repository evidence or user file was deleted. The second preflight matched six frozen tools, six parents, Blender and OCIO, then ran one real Blender 5.2 RNA/graph process with zero render calls. It admitted the 16 MiB projection with 107,447,611,392 bytes free and 107,430,834,176 projected after the write, above the 107,374,182,400-byte reserve.

The formal root remained absent and formal operation counts remained zero. The frozen preflight SHA-256 is `0a78a457f8d58b0324a74deb791edab4a1a9823b19abd556a0a5305106a55aa0`. Next: execute the unchanged 14-process matrix. The expected Bilinear failure remains a falsifiable prediction, not permission to skip the run.

Artifact: `experiments/deterministic-displace-calibration-preflight-v0-1/frozen-tool-preflight.json`.

## J-111 · B52-D6 supports six exact primitives but rejects the full set

Date: 2026-08-27 · Type: CONFIRMATORY REAL-BLENDER DISPLACE CALIBRATION · Blender processes: 14

All 14 fresh Blender 5.2 CPU compositor processes completed with unique PIDs and zero timeouts. Every fixture's two decoded RGBA outputs reproduced exactly. The independent audit replayed the analyzer and all 35 derived reference/diagnostic files byte-exactly, matched 14/14 run artifacts, six frozen tools, six parents and all 20 attacks.

Six of seven fixtures matched the independent destination-sampled float32 reference exactly: zero, both signed integer Clip translations, a two-axis destination step field, Extend and Repeat. Every nonzero fixture changed 3,071 or 3,072 pixels above the sensitivity threshold and reached a maximum change of 0.58203125–1.0.

The subpixel Bilinear fixture was decoded-repeat-exact but not reference-exact. Its maximum error was `1.7583370208740234e-6`, RMSE `4.569772209229176e-8`, and no pixel exceeded `1/65536`. There were 341 nonzero scalar differences across 188 pixels; alpha remained exact. This is consistent with a small deterministic filtering-precision or operation-order difference, but D6 does not claim a cause.

Verdict: `DETERMINISTIC_DISPLACE_CALIBRATION_NOT_SUPPORTED`, base failure `REFERENCE_MATCH`; audit `PASS`. Per the frozen rule, the full set cannot be promoted and the exactness gate cannot be relaxed after inspection. Next is a fresh, preregistered, tolerance-bounded Bilinear holdout with unseen displacements, alpha/frequency patterns and multiple resolutions. Only after that may the work proceed to depth/layer-aware temporal accumulation.

Artifacts: `experiments/deterministic-displace-calibration-v0-1/` and `research/2026-08-27-b52-d6-deterministic-displace-calibration-result.md`.

## J-112 · B52-D7 freezes a fresh dual-reference Bilinear holdout

Date: 2026-08-27 · Type: FRESH-HOLDOUT PREREGISTRATION · Formal outputs: 0

D6 remains `DETERMINISTIC_DISPLACE_CALIBRATION_NOT_SUPPORTED`; its bit-exact gate is not relaxed. D7 instead freezes a new tolerance-bounded question before any D7 worker or output exists. It reuses neither the D6 displacement pair nor its rendered/reference arrays.

Six unseen Bilinear fixtures span 63×47 and 127×73 rasters, low-frequency alpha ramps, high-frequency alpha checkers, Clip/Extend/Repeat and constant plus destination-varying fields. Each has non-integer binary-exact displacement components. One scalar Python process and one independently coded Node process must produce byte-identical canonical reference arrays before two fresh Blender outputs may be judged. The full boundary is 24 unique child PIDs, 12 Blender compositor renders and zero Cycles ray renders.

The maximum error gate remains the pre-existing `1/65536`. Fresh distribution gates are p99 and RMSE ≤`1/1048576`, absolute mean signed error per channel ≤`1/1048576`, alpha maximum ≤`1/65536`, and zero pixels above the maximum. Every task must also change at least half the raster and reach 0.125 maximum change. Twenty-three attacks cover three runtimes, dual-reference agreement, Blender graph/RNA, repeat, tolerance, bias, sensitivity, diagnostics and self-hash.

The formal root is absent. Spec SHA-256: `f102a969cb59d92b0103c6807f20ca5436978504aafadd14a9b0353709ea0df5`; protocol SHA-256: `5dcf859bbdea1125a0654bf58e8e1414e5b02f7a795ecfb4bdb2d10fddead378`. Passing can promote only the tolerance-bounded Bilinear primitive; depth/layer-aware temporal accumulation remains a separate experiment.

Artifacts: `specs/subpixel-bilinear-tolerance-holdout.v0.1.json` and `research/2026-08-27-b52-d7-subpixel-bilinear-tolerance-holdout-protocol.md`.

## J-113 · B52-D7 tools freeze without hiding the predicted tail failure

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs: 0

The scalar Python reference, independent Node reference, Blender 5.2 worker, runner, analyzer, audit and four-test contract suite were frozen and pushed at commit `6d7c7b0933b40eb995facf940f15f7f1af988a3b`. The analyzer now binds every receipt PID, fixture, repeat and operation count back to its self-hashed child report; duplicated or relabeled reports therefore fail `PROCESS_ROSTER` instead of being accepted as separate processes.

Before the freeze, 18 development-smoke child processes exercised all six fixtures: six Python references, six Node references and six real Blender compositor renders. Python and Node were byte-identical for 6/6 fixtures. All six Blender outputs stayed below the pre-existing `1/65536` maximum-error boundary with zero pixels above it, and every per-channel signed mean remained below `1/1048576`.

The already frozen distribution gate was not revised after inspection. Four fixtures exceeded the p99 `1/1048576` limit; `HF_127X73_EXTEND_MIX` also exceeded the RMSE limit at `1.0071396468059945e-6`. The development smoke therefore predicts the formal first failure `TOLERANCE_DISTRIBUTION`. A synthetic full receipt constructed from those retained outputs reached exactly that failure while the other 22 evidence fields passed.

The post-freeze preflight matched seven Git-frozen tool blobs, three D6 parents, Blender, bundled Python, Node and OCIO identities. It used two reference processes and one real Blender 5.2 RNA/graph probe, but made zero formal child processes, zero render calls and zero formal measurements. Runtime observations preserved their true absolute executable paths. The formal output root remained absent.

Disk admission remained extremely narrow: 107,442,343,936 bytes free before a projected 16,777,216-byte write, leaving 107,425,566,720 bytes above the frozen 107,374,182,400-byte reserve. The frozen preflight SHA-256 is `91dd1803dd4a3574fae2f4744e8d76cebcb4ca2d7a379b2aee45563305e1fe56`; its canonical self-hash is `0e02c61913c00217bed074d78ad68a00cc70daa7e267cb85f6d4ab46e0dbd0be`.

Next: execute the unchanged 24-process matrix. A distribution failure is the preregistered scientific outcome, not permission to relax p99 or RMSE after seeing the data.

Artifacts: `experiments/subpixel-bilinear-tolerance-preflight-v0-1/` and `experiments/subpixel-bilinear-tolerance-holdout-preflight-v0-1/frozen-tool-preflight.json`.

## J-114 · B52-D7 rejects the general Blender Bilinear consumer

Date: 2026-08-27 · Type: CONFIRMATORY FRESH HOLDOUT · Child processes: 24

All six scalar Python references, six independently coded Node references and twelve fresh Blender 5.2 compositor cells completed with 24 unique PIDs and zero timeouts. Python and Node agreed byte-for-byte for 6/6 fixtures. Blender's two decoded outputs per fixture reproduced exactly for 6/6. Runtime identity, source/displacement formulas, graph/RNA, operation counts, output hashes, task sensitivity, signed bias and the maximum-error boundary all passed.

The full primitive nevertheless failed its preregistered distribution gate. `LF_63X47_REPEAT_FIELD` and all three high-frequency fixtures exceeded p99 `1/1048576`; `HF_127X73_EXTEND_MIX` also exceeded RMSE at `1.0071396468059945e-6`. All six stayed below maximum `1/65536`, with zero pixels above it. The largest observed error was `7.62939453125e-6`, exactly half that maximum boundary.

Verdict: `SUBPIXEL_BILINEAR_TOLERANCE_HOLDOUT_NOT_SUPPORTED`, base failure `TOLERANCE_DISTRIBUTION`. The independent audit is `PASS`: 24/24 runs, 12/12 regenerated references, 24/24 diagnostics, byte-exact analyzer replay, seven frozen tools, three parents, four runtimes and all 23 attacks matched.

The low-frequency Clip/Extend subset passed, but excluding high-frequency boundaries would remove the cases most relevant to occlusion edges. It will not be promoted as a general temporal primitive. Next: preregister an external canonical warp consumer and prove that its Raw float32 EXR survives Blender ingestion without decoded-array change; depth/layer-aware temporal accumulation remains a later, separate gate.

Artifacts: `experiments/subpixel-bilinear-tolerance-holdout-v0-1/` and `research/2026-08-27-b52-d7-subpixel-bilinear-tolerance-holdout-result.md`.

## J-115 · B52-D8 moves the warp consumer outside Blender

Date: 2026-08-27 · Type: EXTERNAL-CANONICAL-BRIDGE PREREGISTRATION · Formal outputs: 0

D7 rejected Blender's general Bilinear consumer at the frozen distribution gate, so D8 does not relax the threshold or ask Blender to resample pixels. It freezes a narrower systems question: can an independently computed canonical float32 warp survive Raw EXR encoding, Blender 5.2 ingestion, a one-link CPU compositor graph and RGBA32 EXR output with every decoded channel bit unchanged?

A development-only real-Blender probe preceded the formal protocol. A 37×23 external RGBA raster containing negative RGB, values above 1 and non-opaque alpha was encoded as FLOAT/ZIP/Raw EXR and passed through `Image → Group Output`. All 3,404 decoded float32 scalars remained exact; changed scalar count and maximum error were both zero. The retained probe is design evidence only and cannot satisfy a formal gate.

The formal matrix freezes three unseen warps: signed HDR + Clip, high-frequency HDR + Extend and unique edge sentinels + destination-varying Repeat. Independent scalar Python and Node producers must first emit byte-identical top-left RGBA little-endian float32 arrays. Six separate OpenImageIO encoder processes must preserve those arrays through EXR encode/decode. Each producer-fixture EXR then receives two fresh Blender processes, for 24 unique child PIDs total, 12 compositor renders and zero Cycles ray renders.

Every producer, encoder and Blender output is exact-only: no tolerance is allowed. Negative, above-one, alpha and orientation sentinels must remain present and position-exact. Twenty-four attacks bind parents, runtimes, all reports and artifacts, graph/RNA, repeat, producer-path convergence, diagnostics and result self-hash. Container-byte equality is explicitly outside scope; decoded canonical float32 identity is the measurement.

The formal output root is absent. Spec SHA-256: `6fb141b459e7f5d1b98021c843b28e80f19c36172c7a9466d9bb08cc72c0089f`; protocol SHA-256: `fc861d1cbb45ab86529a4bd51d4992d65c92192ac360c5aea249a9f449681853`. Passing permits only a separately preregistered layer/depth-aware external temporal accumulator. Failure keeps final pixel compositing and master EXR outside Blender.

Artifacts: `specs/external-canonical-warp-bridge.v0.1.json`, `research/2026-08-27-b52-d8-external-canonical-warp-bridge-protocol.md` and `experiments/external-canonical-warp-bridge-development-smoke-v0-1/`.

## J-116 · B52-D8 repairs mechanical preregistration omissions before tool work

Date: 2026-08-27 · Type: PRE-FORMAL-IMPLEMENTATION PROTOCOL AMENDMENT · Formal outputs: 0

Review of the first committed D8 spec found four mechanical omissions needed by the frozen runner: the formal output path, projected write, disk reserve and literal pass/fail verdict labels. No formal D8 tool had been implemented and the formal root remained absent, so the spec was amended before tool work rather than allowing the runner to hide constants in code.

The fixture roster, 24-process matrix, exact gates, 24 attacks, decision boundary and non-claims are unchanged. The amendment binds the previous spec hash `6fb141b459e7f5d1b98021c843b28e80f19c36172c7a9466d9bb08cc72c0089f` and explains the change in-machine. Amended spec SHA-256: `94a58f4e3c36b1828cb7e1bc4d5646cd577fac1afd411685235185590644a6a5`; amended protocol SHA-256: `d9ca793aa32705ee7f5f690611c79973f705329874802b72e58399b3451b2d25`.

Next: commit this amendment separately, then implement formal tools against only the amended identity.

## J-117 · B52-D8 tools freeze with an exact end-to-end development path

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs: 0

Eight formal tools were frozen at commit `dd924ab37e4353e8941f73c39347e2b6cc44a988`: two independent producers, EXR encoder, Blender worker, runner, analyzer, audit and four-test contract suite. Python and Node produced byte-identical canonical warps for all three fixtures. A pre-freeze real-Blender tool smoke also passed the signed-HDR fixture end to end; input and output shared canonical hash `09c2d182b27d0d0b7568ffa3626b939df469929b3007df58b883873be28c22a1`, with zero changed scalars.

The frozen preflight matched all eight Git blobs, three D7 parent files and four runtime identities. It ran both producer paths and both encoders in temporary storage, confirmed byte-exact producer convergence and encode/decode identity, then opened one generated EXR in a real Blender 5.2 process to verify the frozen two-node/one-link graph with zero render calls. The formal root remained absent and formal child processes, renders and measurements remained zero.

Disk admission was again narrow but valid after removing only two regenerable temporary directories created by this work. Free space was 107,429,011,456 bytes; after the frozen 16,777,216-byte projection it remains 107,412,234,240 bytes, above the 107,374,182,400-byte reserve. No repository evidence or user file was deleted.

Frozen preflight SHA-256: `25886acd2d3344c583323e1abeaab56ad3befa59f12b2e2ca40f1faed377e7a4`. Next: execute the unchanged 24-process formal matrix and preserve any exactness counterexample.

## J-118 · B52-D8 proves the external canonical warp bridge is exact

Date: 2026-08-27 · Type: CONFIRMATORY REAL-BLENDER BRIDGE HOLDOUT · Child processes: 24

All three Python producers, three independently implemented Node producers, six EXR encoders and twelve fresh Blender 5.2 compositor cells completed with 24 unique PIDs. Python and Node canonical arrays agreed byte-for-byte for all three unseen warps. Every Raw FLOAT EXR decoded back to its source raw exactly before Blender.

All twelve Blender outputs then decoded exactly to their canonical raw inputs. This includes negative RGB, RGB above one, non-opaque alpha, high-frequency structure and distinct orientation corners. Both clean Blender repeats and both producer paths converged for every fixture. Across the full matrix maximum absolute error was zero and changed scalar count was zero.

Verdict: `EXTERNAL_CANONICAL_WARP_BRIDGE_SUPPORTED`, base failure `null`, attacks 24/24. Independent audit `PASS`: producer replay 6/6, encoder decoded replay 6/6, formal artifacts 24/24, analyzer and 12 diagnostics byte-exact, with all parent/runtime/tool/self-hash and operation-count checks intact.

This closes a concrete architectural gap: Blender need not be trusted as the high-frequency Bilinear consumer. Codex-side deterministic code can compute canonical pixels, write Raw float32 EXR, and use Blender's frozen pass-through without a decoded pixel change. The next unresolved boundary is B52-D9 layer/depth-aware external temporal accumulation—especially occlusion, disocclusion and history validity—not transport.

Artifacts: `experiments/external-canonical-warp-bridge-v0-1/` and `research/2026-08-27-b52-d8-external-canonical-warp-bridge-result.md`.

## J-119 · B52-D9 freezes ownership/depth history validity before Blender Vector

Date: 2026-08-27 · Type: LAYER/DEPTH TEMPORAL CALIBRATION PREREGISTRATION · Formal outputs: 0

D8 closes exact transport but not temporal correctness. D9 therefore freezes an analytic integer-motion calibration before connecting production Blender passes. This separation is deliberate: Blender 5.2 Vector contains previous/next screen-space pairs, D5 observed a reproducible static Vector floor, and D7 rejected the general Blender Bilinear consumer. Mixing sign/component calibration, subpixel filtering and occlusion in one experiment would make a failure uninterpretable.

Four unseen two-layer fixtures cover foreground crossing, two-axis camera pan, out-of-bounds history, a same-ID/depth-swap attack and a static all-valid control. Current→previous motion is explicitly `q=(x−dx,y+dy)`. History validity requires bounds, exact layer ID, positive depth agreement within `max(1,z)/1024` and nonzero alpha. Valid output is an exact 0.5 current/history average; invalid output is current exactly.

Ground truth comes directly from layer trajectories. Valid pixels receive complementary binary-exact noise so the correct average equals a clean target; invalid current pixels already equal that target. Unconditional history and wrong-sign motion are frozen sensitivity controls, each required to create at least 32 wrong pixels and 0.25 maximum error on applicable moving fixtures.

The formal boundary is 4 Python + 4 Node accumulator processes, 8 EXR encoders and 16 fresh Blender D8-style pass-through processes: 32 unique PIDs, 16 compositor renders and 0 Cycles ray renders. Validity masks, resolved pixels and every decoded bridge output are exact-only. Twenty-nine attacks cover parents, ground truth, controls, transport and replay.

The formal root is absent. Spec SHA-256: `72ce27443350ef2abb1b45a7630b5c9beee09025103ce690bc523421d9f6dc27`; protocol SHA-256: `4c42278636b211d3278786cb665be6f11cd974fd5375e4899863a95fe442242d`. Passing permits only a separate real Blender multipart Vector/Depth adapter holdout.

Artifacts: `specs/layer-depth-temporal-accumulation-calibration.v0.1.json` and `research/2026-08-27-b52-d9-layer-depth-temporal-accumulation-calibration-protocol.md`.

## J-120 · B52-D9 removes an impossible sensitivity requirement before tool work

Date: 2026-08-27 · Type: PRE-FORMAL-IMPLEMENTATION PROTOCOL AMENDMENT · Formal outputs: 0

Design review found that CAMERA_PAN translates both visible layers by the same vector. Its only invalid history is out of bounds, and the frozen naive control already retains bounds rejection while omitting only ID/depth checks. Requiring 32 naive-history errors on that fixture was therefore logically impossible and would measure a contradiction rather than algorithm sensitivity.

No D9 formal tool existed and the formal root remained absent. The amendment now explicitly applies naive-history sensitivity to FOREGROUND_CROSSING and DEPTH_SWAP_SAME_ID, the two fixtures containing ownership/depth rejection. Wrong-sign motion still applies to all three moving fixtures. Coordinates, threshold values, fixture geometry, process counts, exact gates, 29 attacks and verdict rules are unchanged.

The previous spec hash `72ce27443350ef2abb1b45a7630b5c9beee09025103ce690bc523421d9f6dc27` remains bound in the amended file. Amended spec SHA-256: `d02986d1e682f0a945c68b307a993452de59e0ac4f4ecf769b002c9e2de51030`; amended protocol SHA-256: `19435d66549872365cfa07c81e78726fd00ddb51209bf20208fd3cd4753fa726`.

Next: freeze tools only against the amended identity; no hidden fallback or fixture-specific threshold is permitted.

## J-121 · B52-D9 stops before formal output because wrong-sign control is underpowered

Date: 2026-08-27 · Type: DEVELOPMENT-SMOKE DESIGN INVALIDATION · Formal outputs: 0

Four scalar Python and four independent Node processes agreed byte-for-byte on all ten arrays for every D9 fixture. The correct validity mask and resolved RGBA matched analytic ground truth 4/4; invalid pixels equaled current exactly, valid pixels equaled the clean target exactly, and the static control retained 2,993/2,993 valid histories.

The frozen wrong-sign control nevertheless failed its magnitude requirement on two moving fixtures. FOREGROUND changed 496 pixels and CAMERA changed 2,026, but both reached only 0.0625 maximum error rather than 0.25. DEPTH_SWAP passed at 184 pixels and 0.640625. Both applicable naive-history controls passed at 248/0.71875 and 552/1.015625.

Cause: the first two fixtures use constant color within each layer. Wrong-sign lookup often remains inside the same ownership/depth region, so the only error is the ±1/16 complementary noise. The task can count a direction change but cannot meet its own frozen material-error magnitude. Lowering the threshold or silently adding texture after seeing this output would rewrite the experiment.

D9 is therefore `B52_D9_DESIGN_INVALID_BEFORE_FORMAL_OUTPUT`. No encoder, Blender formal worker, runner, audit or formal root was created. The two development implementations and observation remain as a counterexample. Next: preregister D9.1 with fully specified surface-local spatial texture and entirely fresh resolution/trajectory before implementing its tools.

Artifacts: `experiments/layer-depth-temporal-accumulation-development-smoke-v0-1/` and `research/2026-08-27-b52-d9-temporal-accumulation-design-invalid-result.md`.

## J-122 · B52-D9.1 freezes fresh spatial texture without lowering the failed gate

Date: 2026-08-27 · Type: TEXTURED TEMPORAL FRESH-HOLDOUT PREREGISTRATION · Formal outputs: 0

D9.1 keeps the failed 0.25 wrong-sign magnitude gate. It replaces the underpowered constant-color task with four never-run rasters, boxes and trajectories whose surface-local checker/stripe functions are completely specified before tool implementation. D9 arrays, resolutions, boxes, motion vectors and constant-color surfaces are forbidden inputs.

The new fixtures are 103×63 foreground crossing at 9 px, 107×61 two-axis camera pan at (7,−4), 89×49 same-ID depth swap at −5 px and a 71×43 static control. Moving-surface local offsets are frozen so correct `q=(x−dx,y+dy)` selects the same texel, while wrong-sign motion selects a different checker/stripe phase even when layer and depth still agree.

Python and Node must agree on all ten arrays, analytic validity and resolved RGBA; exact accumulation must hit the clean target with zero changed scalar. Naive ownership/depth omission applies to two fixtures; wrong-sign applies to all three moving fixtures, each at ≥32 wrong pixels and ≥0.25 maximum error. Eight encoder and sixteen real Blender pass-through processes extend the boundary to 32 unique PIDs and 30 attacks.

The formal root is absent. Spec SHA-256: `669077423e0101dd5600576d295c0b7a62189a30b18c1dd6ab18a3b5257cd28f`; protocol SHA-256: `a97d40f06057f6d01a04d23dff40f9d73626d7f10a3fc15b54b8048ab2968e69`. Passing permits only a separate real Blender multipart Vector/Depth adapter holdout.

Artifacts: `specs/layer-depth-temporal-accumulation-holdout.v0.1.json` and `research/2026-08-27-b52-d9-1-layer-depth-temporal-accumulation-holdout-protocol.md`.

## J-123 · D9.1 development implementation survives the frozen sensitivity gates and real Blender transport

Date: 2026-08-27 · Type: PRE-FREEZE DEVELOPMENT VALIDATION · Formal outputs: 0

The new scalar Python and independent Node producers ran as eight fresh processes across all four D9.1 fixtures. Every one of the ten emitted arrays matched byte-for-byte between languages. An independently implemented analyzer reconstructed the texture, motion, layer, depth, analytic validity, complementary noise and resolved target without importing either producer; all reconstructed arrays matched both producer paths.

The preregistered controls now have material power without changing the failed D9 threshold. Wrong-sign motion produced 816 pixels / 1.125 maximum error for foreground crossing, 4,453 / 1.125 for camera pan and 270 / 1.140625 for the same-ID depth swap. Naive history produced 306 / 1.015625 and 729 / 1.140625 on its two applicable fixtures. The static control remained 3,053/3,053 valid with zero wrong-sign error. All values exceed the frozen ≥32 pixel and ≥0.25 maximum-error gates where applicable.

A separate development bridge smoke encoded the 103×63 resolved array as Raw float32 ZIP EXR and passed it through a real Blender 5.2.0 LTS compositor render. All 25,956 decoded RGBA scalars remained exact and maximum error was zero. This run exposed a concrete API mismatch in the first worker draft: Blender 5.2 accepts the engine enum `BLENDER_EEVEE`, not `BLENDER_EEVEE_NEXT`. The failed launch was retained in the working transcript, the worker was corrected before tool freeze, and the successful rerun used the same producer array and gate.

Eight formal-tool candidates now exist: two producers, encoder, Blender worker, independent analyzer, runner, independent replay audit and contract tests. Contract tests pass 5/5. Development temporary outputs were deleted after measurement; the D9.1 formal root remains absent. Next: freeze these exact tools, run a zero-formal-output component/identity/disk preflight, and only then admit the 32-process formal matrix.

Artifacts: `scripts/reference-b52-d9-1-temporal.py`, `scripts/reference-b52-d9-1-temporal.mjs`, `scripts/encode-b52-d9-1-resolved.py`, `blender/render_b52_d9_1_temporal_passthrough.py`, `scripts/analyze-b52-d9-1-temporal-holdout.py`, `scripts/run-b52-d9-1-temporal-holdout.py`, `scripts/audit-b52-d9-1-temporal-holdout.py`, and `tests/test_b52_d9_1_temporal_holdout_contract.py`.

## J-124 · Frozen D9.1 tools pass zero-formal-output admission

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs: 0

The eight candidate tools were frozen in commit `0f476ac`. A post-freeze preflight re-hashed every current tool against its Git blob, verified all five parent artifacts, the Blender/Python/Node/OCIO runtimes and the retained D9 invalidation, and confirmed that both the D9 root and the D9.1 formal root remained absent.

The component probe used five unique child PIDs: two producer processes, two EXR encoder processes and one real Blender 5.2 process. Python and Node matched across all ten arrays; both EXR reopen checks were exact; Blender constructed the frozen two-node Raw compositor graph with zero render calls. These probe values are explicitly not formal measurements.

The host initially sat below the preregistered 100 GiB reserve. Under the user's prior cache-cleanup authorization, 117 explicitly named `/private/tmp/bfs-*` staging items totaling approximately 872 MiB were deleted; no repository, evidence or user-document path was touched. Frozen admission then observed 108,117,323,776 available bytes and projected 108,083,769,344 after the 32 MiB experiment, above the 107,374,182,400-byte reserve.

Preflight file SHA-256: `89cc434f2b6c4c8113f2008a6a3f2fda23c02e77a61d5bd472e56be715337fce`; internal canonical preflight hash: `39fe43b468d1d40627d6483e965f7c2e94578056b74e451f5d5405d85ea2574c`. Admission status: `ACCEPTED`. Next: commit the immutable preflight, then create the formal root exactly once and run the 32-process matrix without tool changes.

Artifact: `experiments/layer-depth-temporal-accumulation-holdout-preflight-v0-1/frozen-tool-preflight.json`.

## J-125 · D9.1 formally supports exact external layer/depth temporal accumulation

Date: 2026-08-27 · Type: FORMAL HOLDOUT + INDEPENDENT REPLAY AUDIT · Blender: 5.2.0 LTS `fbe6228777e7`

The immutable D9.1 matrix completed once: 4 Python accumulator processes, 4 Node accumulator processes, 8 Raw float32 EXR encoders and 16 real Blender compositor renders, with 32 unique child PIDs, 16 render calls and zero Cycles ray renders. Python and Node matched on all ten arrays for every fixture. Independently reconstructed validity and clean targets matched exactly.

Foreground crossing had 6,183/6,489 valid histories; its naive and wrong-sign attacks produced 306/1.015625 and 816/1.125. Camera pan had 5,700/6,527 valid histories and its wrong-sign attack produced 4,453/1.125. Same-ID depth swap had 3,632/4,361 valid histories; naive and wrong-sign attacks produced 729/1.140625 and 270/1.140625. Static retained 3,053/3,053 valid histories and zero control error.

All eight EXR decode checks, sixteen Blender decoded outputs, eight Blender repeat pairs and four producer-path comparisons were exact. Maximum resolved error was zero and changed resolved scalar count was zero. Formal verdict: `LAYER_DEPTH_TEMPORAL_ACCUMULATION_HOLDOUT_SUPPORTED`, base failure `null`, attacks 30/30.

Independent audit `PASS`: formal artifacts 32/32, producer replay 8/8, encoder replay 8/8, diagnostics 40/40, and analyzer output byte-exact. Receipt SHA-256: `5086d4ba55c3bc5f80dea1c190e1c11f387bd09965fbc4e14bb2449ba7d982a6`; result SHA-256: `a8e41983a5ec02df8977c44d76413b11cb0f63f2249941d5663875d30c28e7f1`; audit file SHA-256: `6213aebcdb3364a60f2d256b0ba7c9ee66344b281a9e528f9b39feb594ebb83b`; audit self-hash: `b855009838e6726f7d8296951377200748b21d2e3e3866193f26c86f037383cf`.

This supports the external integer-motion layer/depth accumulator and Blender Raw output bridge only. It does not validate Blender Vector component order/sign or production pass extraction. Next: preregister a real Blender multipart Vector/Depth/ownership adapter holdout.

Artifacts: `experiments/layer-depth-temporal-accumulation-holdout-v0-1/` and `research/2026-08-27-b52-d9-1-layer-depth-temporal-accumulation-holdout-result.md`.

## J-126 · D10 derives the real Blender 5.2 multipart adapter mapping

Date: 2026-08-27 · Type: DEVELOPMENT-ONLY REAL-BLENDER DERIVATION · Formal outputs: 0

D9.1 deliberately stopped before production-pass extraction. D10 therefore rendered three generated 192×108 Cycles fixtures in three fresh Blender 5.2 processes: asymmetric object XY motion, asymmetric camera XY motion and a static depth/ownership control. Asymmetry was necessary because D5's previous/current/next trajectories made the two Vector pairs algebraically indistinguishable.

The first analyzer attempt expected the historical internal name `BFS_MASTER.IndexOB` and correctly stopped with no observation. The real Blender 5.2 multilayer file instead exposed `BFS_MASTER.Object Index.X`; the development analyzer was corrected before any formal spec or root existed. The complete observed roster is Combined RGBA, Depth Z, Vector XYZW and Object Index X.

Across nine visible object/fixture rows, the unique minimum mapping is `Vector.XY = previous_screen − current_screen` and `Vector.ZW = current_screen − next_screen`. The maximum per-pixel endpoint errors for those mappings were `1.5686782979579906e-5` and `2.1542276378777538e-5` pixels. Depth matched analytic camera-space distances 10/9/8 with zero error, and Object Index matched opaque IDs 11/22/33 exactly. The static fixture was zero in this run, but D5's retained `2.6702880859375e-5` static counterexample forbids an exact-zero formal gate.

For D9.1's `q=(x−dx,y+dy)` convention, the candidate adapter writes `motion=(-Vector.X,-Vector.Y)`: Blender's X is screen-right and Y screen-up, while the decoded raster row axis is down. This is a derived candidate only. The projection oracle came from Blender itself and all fixtures are now seen; none may be promoted to holdout evidence.

Observation SHA-256: `303718b7d16f1a088c4c2d7f9d51e9cf66d178b5e00047843415388ae6f28693`. Next: preregister unseen resolution/trajectory, two fresh repeats, independent analytic projection, pass-roster and mapping attacks, then implement the frozen adapter.

Artifacts: `experiments/layer-depth-pass-adapter-development-v0-1/` and `research/2026-08-27-b52-d10-pass-adapter-development-derivation.md`.

## J-127 · D10 freezes the unseen Blender multipart adapter holdout

Date: 2026-08-27 · Type: REAL-BLENDER ADAPTER PREREGISTRATION · Formal outputs: 0

The development mapping is now separated from a fresh formal question. D10 freezes an unseen 173×97 orthographic scene at exactly 10 pixels per world unit, new asymmetric object and camera trajectories, new IDs 101/202/303/404/505 and five binary-exact camera depths. The 192×108 development EXRs, pass indices and trajectories are forbidden formal inputs.

An independent standard-library projection oracle—not `bpy`, `bpy_extras`, `mathutils` or renderer-reported coordinates—predicts XY as previous minus current and ZW as current minus next. Correct endpoint error must remain below p99 `1/4096 px` and maximum `1/1024 px`; the nearest wrong component/sign candidate must remain at least 4 px away. Static uses the same tolerance, not exact zero, preserving D5's retained `2.6702880859375e-5` counterexample.

Each previous/current frame and repeat gets a fresh Blender process: 3 fixtures × 2 repeats × 2 frames = 12 Cycles renders. Six fresh adapter processes must write seven D9.1-format raw arrays with `motion=(-Vector.X,-Vector.Y)`. One independent analyzer reconstructs every array for byte-exact comparison. Total formal boundary: 19 unique child PIDs, 12 ray renders, 12 diagnostics plus sidecars and 34 attacks.

The EXR roster is frozen to Combined, Depth, Vector and the observed Blender 5.2 name `Object Index`; accepting the stale `IndexOB` name is an attack failure. Analytic 3×3 owner probes, five depths and asymmetric top/bottom markers bind ownership and raster orientation.

Formal root and formal tools are absent. Spec SHA-256: `147338ae39b9c025a8f2a4921da55b15f8c16f339f34c711502dc3c94ca03566`. Next: commit the preregistration before implementing any formal tool.

Artifacts: `specs/blender-multipart-temporal-adapter-holdout.v0.1.json` and `research/2026-08-27-b52-d10-blender-multipart-temporal-adapter-holdout-protocol.md`.

## J-128 · Frozen D10 tools pass zero-formal-output admission

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs: 0

Seven D10 tools were frozen at commit `c290360723d9eed0bc740eb411842ae52b172213`: source renderer, canonical adapter, independent analyzer, runner, audit, preflight and five-test standard-library contract suite. The preflight matched every working file to its Git blob, all D9.1/D5/development parents, Blender/Python/OCIO runtimes and the frozen spec.

The independent analyzer's AST imported neither `bpy`, `bpy_extras` nor `mathutils` and contained no renderer-projection payload dependency. Freshness checks confirmed unseen resolution, ortho scale, trajectories and disjoint pass IDs. Contract tests passed 5/5. A real Blender 5.2 process confirmed the four required ViewLayer API properties with zero render calls and zero Cycles ray renders.

The formal root remained absent before and after preflight; formal child processes and measurements stayed at zero. Disk admission observed 107,858,395,136 available bytes and projected 107,841,617,920 after the 16 MiB experiment, above the 107,374,182,400-byte reserve.

Preflight file SHA-256: `853ad3b15e4952749897f5bbd0a892828c5e7531a2ef4150bed78acf6d7ce484`; internal canonical hash: `dd34c79de3b0aee6d086ab72695eeadff447ad27c31828fb60060b698bf0f6ed`. Admission status: `ACCEPTED`. Next: commit this immutable admission and execute the unchanged 19-process matrix once.

Artifact: `experiments/blender-multipart-temporal-adapter-holdout-preflight-v0-1/frozen-tool-preflight.json`.

## J-129 · D10 retains a verifier-contract failure despite passing payload measurements

Date: 2026-08-27 · Type: FORMAL HOLDOUT NEGATIVE RESULT + INDEPENDENT FAILURE AUDIT · Blender: 5.2.0 LTS `fbe6228777e7`

The immutable D10 matrix ran once: 12 fresh Blender Cycles source processes, six adapter processes and one analyzer process, with 19 unique child PIDs and 12 ray renders. Source EXR passes reproduced exactly across repeats; all seven canonical adapter arrays reconstructed byte-for-byte and repeated exactly. Depth passed 60/60 measured owner rows with zero maximum error, ownership probes passed 60/60, and raster orientation passed.

The observed Vector payload also passed every frozen numerical gate. Object XY/ZW endpoint maxima were `7.62939453125e-6` and `8.529922399520072e-6` pixels; camera worst-case maximum was `3.0517578125e-5`; nearest wrong candidates remained 4.472 or 8.062 pixels away. Static XY/ZW maximum was `3.0517578125e-5`, inside the preregistered nonzero boundary.

Formal verdict nevertheless remains `BLENDER_MULTIPART_TEMPORAL_ADAPTER_HOLDOUT_NOT_SUPPORTED`, base failure `SCENE_STRUCTURE`, with `ANIMATION_STRUCTURE=false`. The frozen verifier compared JSON double literals directly with Blender RNA float32 readbacks: for example 17.3 versus 17.299999237060547, −0.7 versus −0.699999988079071, and 1.1 versus 1.100000023841858. Keyframe values showed the same representation effect. This is a verifier-contract counterexample, not permission to add a post-hoc epsilon or rerun D10.

Because the base contract failed before attack replay, attacks are 0/34 and the independent audit correctly reports `FAIL`, while separately confirming 12/12 source artifacts, 6/6 adapter replays, 42/42 reconstructed arrays and 12/12 diagnostics. Result SHA-256: `0d28fb0d520a9f1ca493e952d492642698c72591e9d328dba7a71498dc3be8a1`; audit file SHA-256: `c47a74042e27716ab1fbac9f78aaf53f12fb631038f79d683710de7d1162ad5e`.

Next: preregister D10.1 with an explicit IEEE-754 binary32 canonical structural representation and entirely unseen resolution, ortho scale, IDs, geometry and trajectories. Names, enums, integers, topology and operation counts remain exact, and a one-ULP canonical-value attack must fail. D10 evidence is retained only as design evidence; production pass promotion remains closed.

Artifacts: `experiments/blender-multipart-temporal-adapter-holdout-v0-1/` and `research/2026-08-27-b52-d10-blender-multipart-temporal-adapter-holdout-invalid-result.md`.

## J-130 · D10.1 preregisters typed float32 structure on entirely unseen fixtures

Date: 2026-08-27 · Type: VERIFIER-RECOVERY FRESH-HOLDOUT PREREGISTRATION · Formal outputs: 0

D10 remains `BLENDER_MULTIPART_TEMPORAL_ADAPTER_HOLDOUT_NOT_SUPPORTED`; its analyzer and 173×97 output are not revised or rerun. D10.1 freezes a new question: can an explicitly typed structural oracle represent Blender RNA float storage correctly while the complete real-pass adapter contract independently survives unchanged payload thresholds?

Only declared RNA float paths are canonicalized through an IEEE-754 binary32 pack/unpack before exact comparison. Names, enums, integers, pass indices, topology, action roster, render/pass state, identities and operation counts remain exact. Three frozen sensitivity controls require raw 18.1 to differ when canonicalization is skipped, a one-ULP canonical ortho-scale mutation to fail, and a pass-index increment to fail. Global epsilon and decimal rounding are forbidden.

Fresh fixtures use 181×103, ortho scale 18.1, new object names and geometry, IDs 111/222/333/444/555, object pairs (−11,+7)/(−18,+11), camera pairs (+9,−6)/(+20,−12), and a static control. All D10 Vector, static, Depth, ownership, repeat, adapter, process and diagnostic gates remain unchanged. The boundary is again 12 real Cycles Blender processes, six adapters and one independent analyzer: 19 unique child PIDs and 37 attacks.

The formal root and all seven D10.1 tool paths are absent. Passing may promote only the opaque orthographic integer-motion adapter and open a separately preregistered real textured end-to-end temporal experiment. Failure remains a new counterexample; it is not permission to revise D10.1 after output.

Spec SHA-256: `11686c5e796c7bc1b4e45cf137c3d98347bc65bfec428f9d19545b55430f584b`.

Artifacts: `specs/blender-multipart-temporal-adapter-f32-holdout.v0.1.json` and `research/2026-08-27-b52-d10-1-blender-multipart-temporal-adapter-f32-holdout-protocol.md`.

## J-131 · D10.1 pre-freeze smoke matches Blender RNA binary32 exactly

Date: 2026-08-27 · Type: DEVELOPMENT-ONLY REAL-BLENDER IMPLEMENTATION SMOKE · Formal outputs: 0

Six fresh Blender 5.2 processes rendered previous/current frames of all three preregistered 181×103 fixtures, followed by three fresh adapter processes. The reported ortho scale was `18.100000381469727`, exactly the IEEE-754 binary32 round-trip of 18.1. Canonical scene and layered Action structures matched exactly in 6/6 source cells; the raw JSON doubles did not where applicable. A one-ULP ortho-scale mutation and pass-index +1 mutation were rejected in 6/6.

The new `BFS_F32_MASTER` multipart roster and channels matched. All 15 fixture-owner rows were visible, all analytic 3×3 probes were exact and every Depth maximum was zero. Object XY/ZW maxima were `3.814697265625e-6` / `8.529922399520072e-6`; camera worst-case XY/ZW maxima were `3.0755072587198445e-5` / `3.145679951185349e-5`; static maximum was `3.0517578125e-5`. All three adapters emitted seven canonical arrays with self-valid reports.

This is API and implementation evidence only. It uses preregistered fixtures before tool freeze and cannot satisfy clean-repeat, frozen-tool, attack, audit or promotion gates. Observation internal hash: `31627cf6eb892d2f3f0fef1e749b81a53f7c34bfdae1ebe4692f99dbe11de682`.

Artifacts: `experiments/blender-multipart-temporal-adapter-f32-development-smoke-v0-1/` and `research/2026-08-27-b52-d10-1-f32-adapter-development-smoke.md`.

## J-132 · Frozen D10.1 tools pass zero-formal-output admission

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs: 0

The seven D10.1 tools were frozen and pushed at commit `efd68ec1b1d2029c2526232290d8eadbe81972c7`. Post-freeze preflight matched all seven current files byte-for-byte to their Git blobs, all nine parent artifacts, Blender/Python/OCIO identities and the frozen spec. Freshness checks confirmed new resolution, ortho scale, object names, pass IDs and object/camera trajectories relative to D10.

The analyzer AST imported none of `bpy`, `bpy_extras` or `mathutils`, and the independent projection path did not consume renderer coordinates. The seven-test contract suite passed, including binary32 canonical structure, adjacent-ULP rejection and non-float exactness. A fresh real Blender 5.2 process confirmed the four required ViewLayer pass API properties with zero render calls and zero ray renders.

The D10.1 formal root remained absent before and after admission. Formal child processes, Blender processes, adapters, render calls, ray renders and measurements were all zero. Disk admission observed 107,816,214,528 available bytes and projected 107,799,437,312 after the frozen 16 MiB write, above the 107,374,182,400-byte reserve.

Preflight file SHA-256: `a2b9ad8f279d00d7f19a5dd3cda83b3434949084acb2f89e5228dc43fe32ad52`; internal canonical hash: `a8293e5672aed374caab49b8aa31b6780e19ffa3b27cd6fa6a45fc5c177874d8`. Admission: `ACCEPTED`. Next: commit this immutable admission, then create the formal root exactly once and execute the unchanged 19-process matrix.

Artifact: `experiments/blender-multipart-temporal-adapter-f32-holdout-preflight-v0-1/frozen-tool-preflight.json`.

## J-133 · D10.1 formally supports the real Blender multipart adapter

Date: 2026-08-27 · Type: CONFIRMATORY REAL-BLENDER HOLDOUT + INDEPENDENT REPLAY AUDIT · Blender: 5.2.0 LTS `fbe6228777e7`

The immutable D10.1 matrix completed exactly once: 12 fresh Blender Cycles source processes, six adapter processes and one independent analyzer, with 19 unique child PIDs and 12 ray renders. All 37 base checks passed and all 37 mutation attacks returned their preregistered failure labels. Source Combined/Depth/Vector/Object Index passes reproduced exactly across both repeats, and all seven canonical adapter arrays repeated exactly for all three fixtures.

Typed structural comparison closed D10's verifier defect without changing D10. Twelve of twelve source cells matched scene and layered Action structure after explicit IEEE-754 binary32 round-trip. Raw JSON doubles, a one-ULP ortho-scale mutation and pass-index +1 were all rejected. D10 remains NOT_SUPPORTED with FAIL audit; D10.1 is a separate result.

Object XY/ZW maxima were `3.814697265625e-6` / `8.529922399520072e-6` pixels and its nearest wrong candidate was 8.062 pixels away. Camera worst-case XY/ZW maxima were `3.0755072587198445e-5` / `3.145679951185349e-5`, with nearest wrong at least 12.529 pixels. Static XY/ZW maximum was `3.0517578125e-5`, inside the frozen nonzero boundary. Depth passed 60/60 rows with zero maximum error; ownership probes passed 60/60 and orientation passed.

Verdict: `BLENDER_MULTIPART_TEMPORAL_ADAPTER_F32_HOLDOUT_SUPPORTED`, base failure `null`, attacks 37/37. Independent audit `PASS`: 12/12 source artifacts, 6/6 adapter replay cells, 42/42 arrays and 12/12 diagnostics, with frozen-tool, parent, runtime, self-hash and operation identities intact.

Receipt SHA-256: `703f0d37c7b5cda800a57a70221596ba68ceb61af99ae46664da378ae68b0128`; result SHA-256: `c0f94547b432159772029f67abe70da12ff0f236707d7f92896c75ee664ebc60`; audit SHA-256: `f6ef6b2236aa8501ef533c88f5f1e9604f71b259d4beffc90825b14afdb52328`.

This promotes only the opaque orthographic integer-motion production-pass adapter. Next: preregister B52-D11, a fresh real textured render → D10.1 adapter → D9.1 accumulator → D8 Raw EXR end-to-end holdout with occlusion, disocclusion, bounds, same-ID depth rejection and static controls.

Artifacts: `experiments/blender-multipart-temporal-adapter-f32-holdout-v0-1/` and `research/2026-08-27-b52-d10-1-blender-multipart-temporal-adapter-f32-holdout-result.md`.

## J-134 · D11 freezes the raw-float-to-integer composition risk before tool work

Date: 2026-08-27 · Type: REAL-TEXTURED END-TO-END PREREGISTRATION · Formal outputs: 0

D8, D9.1 and D10.1 each passed their narrow formal gates, but their composition has not been tested. The most specific open interface is now explicit: D10.1 preserves raw Blender float32 motion while D9.1 uses `int()` truncation toward zero. A theoretically integral displacement observed just below that integer can silently become a one-pixel error even while satisfying D10.1's subpixel endpoint tolerance.

D11 freezes the parent behavior unchanged. The adapter may not round or snap. A round-to-nearest counterfactual is recorded only as a diagnostic and is forbidden from repairing the verdict. Every moving-owner interior pixel must both remain within D10.1's raw endpoint tolerance and truncate to the preregistered integer motion; failure is `MOTION_INTEGERIZATION`.

Four entirely fresh 197×113 real-Blender mesh-textured fixtures cover layer disocclusion, camera bounds, same-Object-Index depth rejection and an all-valid static control. Exact 3×3 semantic probes bind each rejection reason away from raster/material edges. High-contrast per-face emission patterns preserve the D9.1 wrong-sign and naive-history sensitivity requirements without using external textures.

The formal boundary is 65 unique child PIDs: 16 real Cycles source processes, eight adapters, eight Python plus eight Node accumulators, eight Raw EXR encoders, 16 real Blender compositor bridge processes and one independent analyzer. It contains 32 Blender renders, zero model/network calls, a 64 MiB projection and the frozen 100 GiB disk reserve.

All eleven formal tool paths and the formal root are absent. Passing would promote only opaque orthographic integer-motion composition. A motion-integerization failure permits only a fresh D11.1 quantizer preregistration; D11 cannot be revised or rerun. Frozen spec SHA-256: `f1505c42426e8e286ee1584de3df12fb33b7db57518d6d91e1fd93aa3bed5a5f`.

Artifacts: `specs/blender-real-textured-temporal-end-to-end-holdout.v0.1.json` and `research/2026-08-27-b52-d11-blender-real-textured-temporal-end-to-end-holdout-protocol.md`.

## J-135 · D11 development smoke observes the preregistered integerization risk

Date: 2026-08-27 · Type: DEVELOPMENT-ONLY REAL-BLENDER COMPOSITION SMOKE · Formal outputs: 0

The first implementation attempt stopped before rendering: an eagerly evaluated `dict.get` fallback tried to read `locationByFrame` on a static object. The failure was retained, the branch was made explicit, and no source EXR existed from that attempt.

The corrected development cell launched two real Blender 5.2 Cycles source processes, one multipart adapter, one scalar Python accumulator and one independent scalar Node accumulator for the 197×113 object-motion fixture. The multipart roster matched, both 3×3 semantic probes were exact, and Python/Node produced byte-identical validity, reason, resolved, naive, wrong-sign and round-nearest diagnostic arrays.

The inherited truncation path yielded 21,668 valid and 593 invalid pixels. Raw values included `12.999996185302734 → 12` and `−6.999996185302734 → −6`. The round-nearest diagnostic changed no validity pixels but changed 87 resolved float32 scalars; it equaled current RGBA exactly (`8afc2cff…`), while truncation did not (`85fb98ef…`). This is a direct development signal for the frozen `MOTION_INTEGERIZATION` risk, not a formal verdict.

The four initial formal tools and a machine-readable observation are now durable. The smoke has only one fixture/repeat, occurs before tool freeze and includes no Raw EXR bridge, attack replay or independent audit. Next: implement the remaining seven frozen tools, run contract tests and zero-output preflight, then freeze before any formal root is created.

Artifacts: `experiments/blender-real-textured-temporal-end-to-end-development-smoke-v0-1/observation.json` and `research/2026-08-27-b52-d11-real-textured-development-smoke.md`.

## J-136 · D11 development Raw EXR bridge preserves the observed counterexample bytes

Date: 2026-08-27 · Type: DEVELOPMENT-ONLY REAL-BLENDER BRIDGE SMOKE · Formal outputs: 0

The Python truncation result from J-135 was encoded as a 197×113 Raw RGBA float32 ZIP EXR. OIIO decode reproduced the input hash `85fb98ef…` exactly. A fresh Blender 5.2 compositor process then opened that EXR as Raw and used only `BFS_D11_EXTERNAL_SOURCE.Image→BFS_D11_GROUP_OUTPUT.Socket_0`; its decoded output again reproduced `85fb98ef…` exactly even though container hashes differed as allowed.

The frozen bridge graph and RNA checks passed, with one compositor render and zero Cycles rays. The initial five-test contract suite also passed, covering spec/process identity, toward-zero versus nearest integerization, scalar coordinate/float32 behavior, rejection priority and the narrow adapter/bridge contract.

Seven of eleven formal tool paths now have implementations. This remains pre-freeze development evidence: one encoder cell and one bridge repeat cannot satisfy the eight encoders, sixteen bridge processes, clean repeats, attacks or audit required by D11.

Artifact: `experiments/blender-real-textured-temporal-end-to-end-development-smoke-v0-1/bridge-observation.json`.

## J-137 · Frozen D11 tools pass zero-formal-output admission

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs: 0

All eleven D11 formal tools were frozen and pushed at commit `d3bdfe4b543566f6e37305d18b9fb8a7d2485f36`. Preflight matched every working file byte-for-byte to its Git blob, all eleven parent artifacts, Blender/Python/Node/OCIO runtimes and the preregistered spec.

Eight contract tests passed. The independent analyzer imports none of `bpy`, `bpy_extras` or `mathutils` and does not import either tested accumulator. A fresh Blender 5.2 process confirmed the four production-pass properties and exact two-node bridge graph with zero render calls and zero Cycles rays.

The formal root remained absent before and after admission. Disk admission observed 107,501,121,536 available bytes and projected 107,434,012,672 after the frozen 64 MiB write, above the 107,374,182,400-byte reserve. This is a narrow 59,830,272-byte post-projection margin, so no unrelated large artifact may be created during the run.

Preflight file SHA-256: `6f0ec142494047142bc621f89d52e1b75b8599d793fbf9d3d12cb413e8cda9b3`; internal canonical hash: `f6b22020a40371d170192e08e98107e8de0691d7825b1c3d337b09cdc3b027a7`. Admission: `ACCEPTED`. Next: commit the immutable admission, then create the formal root exactly once and execute the unchanged 65-process matrix.

Artifact: `experiments/blender-real-textured-temporal-end-to-end-holdout-preflight-v0-1/frozen-tool-preflight.json`.

## J-138 · D11 formally rejects the unmodified real-textured composition

Date: 2026-08-27 · Type: CONFIRMATORY REAL-BLENDER END-TO-END NEGATIVE RESULT + INDEPENDENT REPLAY AUDIT · Blender: 5.2.0 LTS `fbe6228777e7`

The immutable D11 matrix completed exactly once with 65 unique child PIDs: 16 real Cycles sources, eight adapters, eight Python and eight Node accumulators, eight Raw EXR encoders, 16 Blender compositor bridges and one analyzer. All 56 registered attacks passed, 40 diagnostic PNGs plus 40 sidecars were bound, and every base gate except motion integerization passed.

Raw Vector endpoint error was tiny—moving-fixture p99 at most `8.529922399520072e-6` pixels and maximum `1.0789593218788873e-5`—but toward-zero conversion still changed near-integers to adjacent pixels. Owner-interior mismatches repeated exactly: object 211/1,120, camera 449/21,645, same-ID depth 86/1,120 per repeat, and static 0/21,645. The formal total was 1,492 mismatched owner-interior pixels across eight cells.

Verdict: `BLENDER_REAL_TEXTURED_TEMPORAL_END_TO_END_HOLDOUT_NOT_SUPPORTED`; base failure: `MOTION_INTEGERIZATION`. Python and Node remained byte-identical, all semantic probes and controls passed, static was 22,261/22,261 valid, and the Raw EXR/Blender bridge remained decoded-float32 exact. The round-nearest diagnostic changed 87, 318 and 129 resolved scalars per moving-fixture repeat but was not allowed to repair D11.

Independent replay audit: `PASS`. Its 85,550-pixel broad sentinel includes background/static owners and is only a nonzero consistency check; the preregistered owner-interior measurement is 1,492. Receipt SHA-256: `dd75ba0e2f4a4b0ee950f9e12e84dc3f12265fe743a89370fb4f15f2643fc689`; result SHA-256: `490c569c4d12fe82ef49ff3d82d657512dbe297c69fd7f8f34df9b7daeeb31c8`; audit SHA-256: `4bd0e2081b831c75e5572c48c3b281e4a440e8d8f108fc50e1d774a878df6c2b`.

D8, D9.1 and D10.1 retain their narrow individual results; their unmodified composition is rejected. Per the frozen decision rule, next is a fresh D11.1 preregistration with an explicit nearest-integer quantizer. D11 will not be revised or rerun.

Artifacts: `experiments/blender-real-textured-temporal-end-to-end-holdout-v0-1/` and `research/2026-08-27-b52-d11-blender-real-textured-temporal-end-to-end-result.md`.

## J-139 · D11.1 preregisters a bounded dual-implementation motion quantizer

Date: 2026-08-27 · Type: INTEGERIZATION-RECOVERY FRESH-HOLDOUT PREREGISTRATION · Formal outputs: 0

D11 remains `BLENDER_REAL_TEXTURED_TEMPORAL_END_TO_END_HOLDOUT_NOT_SUPPORTED`; no D11 tool, result or output is revised or rerun. D11.1 freezes the only recovery permitted by that result: an explicit nearest-integer conversion between the raw adapter and the inherited toward-zero accumulator semantics.

The quantizer is deliberately narrower than unconditional rounding. Each finite raw float32 component receives the language-independent candidate `v>=0 ? floor(v+0.5) : ceil(v-0.5)` and is accepted only when its distance to that integer is at most `1/1024` pixel inclusive—the pre-existing D10.1 absolute endpoint-error ceiling, not a threshold fitted to D11. Any out-of-domain component rejects the complete array and produces no output. Half-integers, NaN, infinities, partial output, clamping, fixture lookup, global epsilon and post-output radius widening are forbidden. Zero must serialize as positive float32 zero.

Independent Python and Node quantizers must bind the same raw adapter bytes and produce byte-identical integral float32 motion. Their matching-language accumulators retain `int()` / `Math.trunc()` so the downstream integerization is an identity rather than a second repair. The analyzer independently recomputes the quantizer, and 71 registered mutations cover radius boundaries, signed zero, nonfinite and half-integer rejection, alternate integerizers, idempotence, report binding and the complete inherited temporal/bridge chain.

Four fresh 199×109 scenes with orthographic scale 19.9 use new names, pass IDs 7101–7707, divisible 0.8/0.6-world mesh grids, material values and trajectories. They cover object occlusion, camera bounds, same-ID depth disocclusion and a 21,691-pixel all-valid static control. Frozen motion pairs include both signs: `[+16,−11]`, `[−13,+12]`, `[+17,−8]` and `[+0,+0]` after quantization.

The formal boundary is 81 unique child PIDs: 16 Cycles sources, eight adapters, 16 quantizers, 16 accumulators, eight encoders, 16 compositor bridges and one analyzer. Projected write is 72 MiB and must leave the frozen 100 GiB reserve. All thirteen formal tool paths and the formal root are absent at preregistration.

Frozen spec SHA-256: `c4cb343672f53660d7c4ab69ccd489e00bb211e4aa1f489429f7a626ee48c42a`. Passing would support only declared orthographic integer-motion input; the next boundary would be a new perspective/subpixel reconstruction contract, not a wider rounding radius.

Artifacts: `specs/blender-nearest-integer-temporal-recovery-holdout.v0.1.json` and `research/2026-08-27-b52-d11-1-nearest-integer-temporal-recovery-holdout-protocol.md`.

## J-140 · D11.1 development smoke crosses the real Blender bridge exactly

Date: 2026-08-27 · Type: PRE-FREEZE DEVELOPMENT TOOLCHAIN SMOKE · Formal outputs: 0

Thirteen D11.1 formal-tool candidates now implement the preregistered 81-process boundary. The new interface is explicit: the unchanged raw multipart adapter feeds independent scalar Python and Node nearest-integer quantizers; matching-language accumulators then retain `int()` / `Math.trunc()` over exact integral float32 motion. The analyzer and audit independently reconstruct quantization and accumulation rather than importing either tested implementation.

Ten zero-formal-output contract tests passed. They exercised inclusive `1/1024` acceptance, the first representable float32 outside the radius, exact and adjacent half-integers, NaN and infinities, signed-zero canonicalization, idempotence, alternative integerizers, whole-array atomic rejection and Python/Node CLI byte identity. A development rejection containing one `0.25` component left neither output payload nor success report for both languages.

A separate nine-process real-Blender smoke used only `QUANTIZED_OCCLUSION_OBJECT_XY_199X109`: two fresh Cycles source renders, one adapter, two quantizers, two accumulators, one EXR encoder and one Blender compositor bridge. Python and Node produced the same quantized-motion SHA-256 `ee367cf33a216c8f266cd6ce1a58e0a676e8b0e4de8b46553b670f0d34b0123a` and the same five accumulator arrays. The resolved canonical array SHA-256 was `85f7994bb2b508c6f5e0ca3d90b83c078aa29cdb4d552a238232114355e48b6a`, with 20,763 valid pixels. Blender bridge decode changed zero float32 scalars.

The smoke occupied approximately 3.9 MB and was deleted after measurement. It is design evidence only: it contains one fixture, one source repeat and one bridge repeat, so it cannot satisfy any D11.1 formal gate. Blender 5.2 also emitted two Blender-6.0 deprecation warnings for `World.use_nodes` and `Material.use_nodes`; they did not change exit status or bytes and are retained as a future migration concern.

Next: freeze the exact thirteen tools in Git, run the zero-formal-output identity/API/disk preflight against that commit, and admit the 81-process matrix only if the unchanged 100 GiB reserve passes.

Artifacts: `blender/render_b52_d11_1_textured_source.py`, `scripts/quantize-b52-d11-1-motion.py`, `scripts/quantize-b52-d11-1-motion.mjs`, `scripts/analyze-b52-d11-1-nearest-integer-recovery.py` and the remaining paths frozen by `formalToolPaths` in the D11.1 spec.

## J-141 · D11.1 frozen preflight passes after a retained disk rejection

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT + AUTHORIZED REGENERABLE-CACHE CLEANUP · Formal outputs: 0

The exact thirteen D11.1 tools were frozen at commit `8d94d677b9c8c266ccdf4532f3e74dd84f91fc00`. The first post-freeze preflight matched all thirteen Git blobs, sixteen parent artifacts, Blender, bundled Python, Node and OCIO; freshness, ten contract tests, analyzer import independence and a real Blender 5.2 API/graph probe also passed. The probe created the exact `BFS_D111_EXTERNAL_SOURCE.Image→BFS_D111_GROUP_OUTPUT.Socket_0` link with zero render calls.

That first receipt remained `REJECTED` only at disk admission: 107,323,805,696 bytes were available, and the 72 MiB projection would leave 107,248,308,224 bytes—below the frozen 100 GiB reserve. It is retained as `frozen-tool-preflight.rejected-disk.json`; no formal root or measurement existed.

Under the user's prior cache-cleanup authorization, only `/Users/tianxing/.npm/_cacache` was removed: approximately 181 MiB of reconstructible package cache, recoverable by npm refetch. No repository path, experimental evidence or personal document was deleted. The unchanged preflight then observed 107,460,284,416 bytes available and projected 107,384,786,944 after the experiment, 10,604,544 bytes above the same reserve. Status became `ACCEPTED`; all formal operation counts remained zero and the formal root stayed absent.

Accepted preflight file SHA-256: `6a61e41a3a328072f7eab922d2a934a4ae4fe535f51185f198a7416e09001093`. Rejected preflight file SHA-256: `3b865363b37809695a09e333a4aece2a66804e408414db9cfba06e77d43b08de`.

Next: commit both immutable preflight receipts, then run the admitted 81-process formal matrix exactly once. Do not rerun D11.1 after its formal root exists.

Artifacts: `experiments/blender-nearest-integer-temporal-recovery-holdout-preflight-v0-1/`.

## J-142 · D11.1 formal matrix supports recovery; the frozen audit hits a replay-only type defect

Date: 2026-08-27 · Type: SINGLE FORMAL EXECUTION + INVALID AUDIT ATTEMPT · Runtime: 81 unique formal child PIDs

The admitted D11.1 matrix completed exactly once: sixteen fresh Cycles sources, eight adapters, sixteen Python/Node quantizers, sixteen matching-language accumulators, eight Raw EXR encoders, sixteen fresh Blender compositor bridges and one analyzer. All 71 registered attacks passed, all fourteen ordered base gates were true and the result verdict was `BLENDER_NEAREST_INTEGER_TEMPORAL_RECOVERY_HOLDOUT_SUPPORTED`.

Every real raw motion component fell inside the frozen `1/1024` domain. The largest raw-to-integer error was `7.62939453125e-6` px, roughly 128 times smaller than the radius. Python and Node quantized bytes matched in 8/8 cells; every declared moving-owner interior pixel equaled analytic integer motion. The quantizer repaired 397, 661 and 359 pixels respectively in the three moving fixtures where inherited truncation would select a different integer; the static fixture remained 21,691/21,691 valid with positive-zero motion. Layer, bounds and same-ID depth probes passed 16/16, and every Raw EXR Blender bridge decoded exactly.

The frozen audit then completed its data replay but crashed before writing JSON because a replay-only `quantizerExact` field retained NumPy `bool_`. The exact exception is retained; `audit.json` remains absent. Formal receipt SHA-256 is `643717651d4dafb48c87c0527d682ea224e8ab80f6a81a8d153e8c4d1ec8a9fc5`, result SHA-256 is `dd08142a2af855ddc287eecb84f5de722afb03a9ae6aef8a33fd3279d660329f`, and original frozen audit-tool SHA-256 is `feb1214b00b16e833db2e65f38308d4c82b76f8952aadf62ad0a72670fbabb4a`.

C1 is preregistered before its tool exists. It permits a new audit-only path with one explicit native-boolean cast plus correction provenance; it forbids any formal rerender, data rewrite, gate change or original-tool mutation.

Artifacts: `experiments/blender-nearest-integer-temporal-recovery-holdout-v0-1/` and `research/2026-08-27-b52-d11-1-c1-audit-numpy-bool-correction.md`.

## J-143 · D11.1-C1 correctly rejects a malformed 65-character receipt hash

Date: 2026-08-27 · Type: INVALID CORRECTION ATTEMPT + PRE-TOOL C2 PREREGISTRATION · Formal rerenders: 0

C1 was frozen at `e7a8ef5cb59e89f0fbc4462a032bf58adcdaf33c`, but its new identity guard stopped before replay because the preregistered receipt hash literal contained 65 hexadecimal characters. No formal file changed and `audit.json` remained absent. This is a correction-provenance transcription defect, not an experimental result.

The receipt and result were then hashed by `shasum`, OpenSSL and Blender's bundled Python. All three agreed on the 64-character receipt SHA-256 `643717651d4dafb48c87a5925391f06ef30ce97f62a8ab321d4c4aba62d0f443` and result SHA-256 `dd08142a2af855ddc287eecb84f5de722afb03a9ae6aef8a33fd3279d660329f`.

C2 is preregistered before its tool exists. It may copy the exact C1 tool and change only that receipt literal plus C2 provenance identifiers; the native-boolean cast and all replay logic remain frozen. Formal render, analyzer, receipt, result and diagnostics remain immutable.

Artifacts: `research/2026-08-27-b52-d11-1-c2-receipt-hash-literal-correction.md`.

## J-144 · D11.1-C2 independently supports bounded integer-motion recovery

Date: 2026-08-27 · Type: CORRECTED INDEPENDENT REPLAY AUDIT + CONFIRMATORY RESULT · Formal rerenders: 0

The C2 audit tool was frozen and pushed at `add84222c218f27be772db3632c090127888c65f`, then run exactly against the immutable D11.1 formal root. It passed result, receipt, spec, preflight, process, diagnostic, evidence and verdict checks; independently replayed all eight cells; reconstructed all fourteen evidence gates; and accounted for all 71 registered attacks. No Blender process, render, adapter, quantizer, accumulator or encoder was rerun.

The formal verdict is therefore auditable as `BLENDER_NEAREST_INTEGER_TEMPORAL_RECOVERY_HOLDOUT_SUPPORTED`, with `baseFailure=null`. Eighty-one formal child PIDs were unique. Python and Node were byte-identical for quantization and accumulation in 8/8 cells; maximum observed quantization error was `7.62939453125e-6` px; and the explicit bounded quantizer recovered 397, 661 and 359 pixels per repeat from the inherited toward-zero error in the three moving fixtures. The static control remained 21,691/21,691 valid. Sixteen semantic probe patches and sixteen real Blender Raw EXR bridges were exact.

The correction history remains part of the evidence. The original audit crashed on replay-only NumPy `bool_` serialization. C1 added the preregistered native-boolean cast but stopped on a malformed 65-character receipt hash literal. C2 changed only that literal and correction provenance. Neither correction changed or reran the formal matrix. C2 audit file SHA-256 is `35ef7e30f0f231262e58ee307cac4050e5e0137cbc1af209ac5d2ab7b1cb552f`; its internal canonical hash is `c7fdf2f467e92c94cfd59a96881509b1fd87fc49d57a7e5d15f36b8be0570d40`.

This does not erase D11's rejection and does not authorize arbitrary rounding. Support applies only when every finite component lies within the frozen inclusive `1/1024`-pixel domain. Perspective, subpixel, deformation, transparency, multi-owner coverage and perceived quality remain untested. The next boundary is a separately preregistered perspective/subpixel reconstruction contract, not radius widening.

Artifacts: `experiments/blender-nearest-integer-temporal-recovery-holdout-v0-1/` and `research/2026-08-27-b52-d11-1-nearest-integer-temporal-recovery-holdout-result.md`.

## J-145 · Real Blender perspective probe identifies the correct subpixel endpoint and a depth-identity counterexample

Date: 2026-08-27 · Type: DEVELOPMENT-ONLY PROJECTIVE/SUBPIXEL CALIBRATION · Formal outputs: 0

The first D12 development process stopped before rendering because Blender 5.2's `ShaderNodeCombineColor` has no Alpha input. That empty attempt is retained as `FAILED_BEFORE_RENDER`; the one-line graph correction ran in a new root.

The corrected probe rendered two real 101×61 Cycles multipart EXRs from an opaque, continuously textured plane moving laterally and toward a 50 mm perspective camera. All 12,322 moving Vector XY components were genuinely outside D11.1's `1/1024` near-integer domain; median distance from an integer was `0.2575163841` pixel.

An independent pinhole ray/plane/projective oracle established the top-left decoded endpoint formula `q=(x+Vector.X, y−Vector.Y)`. Blender's maximum endpoint error over 6,161 moving-owner pixels was `2.6787651905e-5` pixel. External bilinear reconstruction achieved RMSE `6.10225e-5` and 84.29 dB unit-range PSNR against the current real Blender beauty, versus RMSE `2.79617e-3` for nearest and `1.55352e-2` for the wrong-sign control.

The probe also falsified direct cross-frame depth identity for perspective/dolly history validation. Correct corresponding surface samples differed by `0.1800003052` depth units, while the inherited identity tolerance was only `0.0095898435`; all 5,225 measured pixels would be wrongly rejected. D12 must compare previous Depth against a transform-predicted previous-camera depth of the current rigid surface point, not against current Depth.

This is calibration evidence only. The formal holdout must use fresh resolution, lens, transforms, material spectrum and identifiers, and must freeze the projection oracle, bilinear kernel, transform-aware depth rule, absolute quality gates, nearest/wrong-sign controls, process identity and attacks before its tools or output exist.

Artifacts: `experiments/blender-projective-subpixel-development-probe-v0-1/`, `experiments/blender-projective-subpixel-development-probe-v0-2/` and `research/2026-08-27-b52-d12-projective-subpixel-development-probe.md`.

## J-146 · D12 freezes a transform-aware projective subpixel holdout before formal tools

Date: 2026-08-27 · Type: PROJECTIVE/SUBPIXEL FRESH-HOLDOUT PREREGISTRATION · Formal outputs: 0

D12 does not widen D11.1's near-integer radius. It freezes a separate float-motion contract for four entirely fresh 107×67 perspective fixtures: rigid object dolly/translation, rigid object yaw/pitch, camera dolly/yaw and a static control. The 47 mm camera, 35 mm sensor, scene identifiers, pass IDs, trajectories and continuous object-local emission spectrum are disjoint from the 101×61 development probe.

The independent oracle casts a current pixel-center ray, intersects the current rigid plane, recovers its local point, applies the previous object transform and projects through the previous camera. The decoded top-left sample coordinate is frozen as `q=(x+Vector.X, y−Vector.Y)`. A separate transform-aware depth oracle predicts that same point's previous-camera depth; direct `previousDepth≈currentDepth` is forbidden and retained only as a diagnostic counterexample.

The consumer is clip-boundary bilinear with four owner/alpha taps, float64 accumulation in fixed order and one final float32 cast. Python and Node must produce byte-identical reconstruction, validity and predicted-depth arrays. Moving RGB gates are maximum ≤1/512, p99 ≤1/1024, RMSE and per-channel absolute bias ≤1/4096, PSNR ≥72 dB, plus at least 4× RMSE improvement over nearest and 10× over wrong-sign. The static reconstruction must be exact.

The formal boundary is 65 unique child PIDs: 16 real Cycles sources, eight adapters, sixteen independent reconstructors, eight encoders, sixteen Blender compositor bridges and one analyzer. Fifty-seven attacks cover identity, freshness, projection convention, subpixel domain, kernel, metadata, depth physics, quality controls, bridge and self-hashes. The 64 MiB projection must leave the unchanged 100 GiB reserve.

All eleven formal tool paths, the preflight root and the formal root are absent. Frozen spec SHA-256: `dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2`. Next: commit the preregistration, implement the exact tools, freeze them in a second commit, and admit formal output only through a zero-output identity/API/disk preflight.

Artifacts: `specs/blender-projective-subpixel-reconstruction-holdout.v0.1.json` and `research/2026-08-27-b52-d12-projective-subpixel-reconstruction-holdout-protocol.md`.

## J-147 · Frozen D12 tools pass zero-formal-output admission

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs: 0

All eleven D12 formal tools were frozen and pushed at `37fb06e68c7761dc432fa48b9287e78f7a427f24`. Preflight matched every working file byte-for-byte to its Git blob, all parent artifacts, Blender/Python/Node/OCIO runtimes and the preregistered spec.

Eleven contract tests passed, including an end-to-end synthetic static CLI comparison in which the scalar Python and Node reconstructors produced byte-identical reconstruction, validity, projective endpoint, predicted-depth, nearest, wrong-sign and direct-depth-control arrays. The analyzer contains no Blender/mathutils or tested-reconstructor import.

Two fresh Blender 5.2 processes performed zero-render probes. The source probe constructed the frozen 47 mm perspective camera, 3,080-vertex/2,967-polygon surface, twenty-node continuous emission graph and four production passes with zero Cycles rays. The bridge probe opened a generated 107×67 Raw EXR and built exactly `BFS_D12_EXTERNAL_SOURCE.Image→BFS_D12_GROUP_OUTPUT.Socket_0`, again with zero render calls.

Disk admission observed 107,548,725,248 available bytes and projected 107,481,616,384 after the frozen 64 MiB write, above the unchanged 107,374,182,400-byte reserve. The formal root remained absent before and after preflight. Status: `ACCEPTED`; preflight file SHA-256: `fb2205ec6a0486b37df3689a2567ccb85fe714fec71af3709f5cb235c5059e6f`; internal hash: `9582a44251b43dd712461ab9c0af6bdce25c1f7259a052fce9e8d0ca2a01257e`.

Next: commit this immutable admission, then create the formal root exactly once and execute the unchanged 65-process matrix. Formal fixture renders have not yet occurred.

Artifact: `experiments/blender-projective-subpixel-reconstruction-holdout-preflight-v0-1/frozen-tool-preflight.json`.

## J-148 · D12 formal execution is invalidated by a frozen Node parent-directory defect

Date: 2026-08-27 · Type: INVALID FORMAL EXECUTION · Scientific verdict: none

The admitted D12 runner created its formal root once. Sixteen real Blender 5.2 Cycles source processes, the first adapter and the first Python reconstructor completed with eighteen unique reported PIDs. The first Node reconstruction process then exited before output because `fs.mkdirSync(outputDir,{recursive:false})` could not create `arrays/` while its parent cell directory was absent.

The failure is retained at `RECONSTRUCTOR_NODE / node_PROJECTIVE_OBJECT_DOLLY_TRANSLATE_107X67_R1`. No encoder, bridge, analyzer, attack replay or audit ran; no receipt or results file exists. D12 therefore has no scientific verdict.

The completed Python cell observed 5,841 valid pixels, endpoint maximum `2.21729e-5` px and correct-bilinear RMSE `5.04537e-5`, but those are partial invalid-run measurements and cannot be promoted. The frozen thresholds and science logic will not be changed in response.

The next legal step is a pre-tool C1 protocol. It may correct only nested output-directory materialization and correction/new-root provenance, must add the missing-parent contract test, must rerun all 65 successful processes from scratch in a new root, and must not reuse any failed-root source or array as measurement input. `run.failure.json` SHA-256: `ccb05339ec16b9d92350ad53552ae7368d2536e6e023bd0f1660ed9f7b67ec34`.

Artifacts: `experiments/blender-projective-subpixel-reconstruction-holdout-v0-1/` and `research/2026-08-27-b52-d12-formal-execution-invalid-result.md`.

## J-149 · D12-C1 preregisters one infrastructure-only Node correction

Date: 2026-08-27 · Type: PRE-TOOL INFRASTRUCTURE-CORRECTION PREREGISTRATION · C1 formal outputs: 0

The original D12 science specification, admitted tools and failed formal root remain immutable. C1 permits exactly one scientific-tool behavior change in a new Node file: replace the single nonrecursive output-directory creation with recursive creation so that a previously absent cell parent can be materialized. A new contract must invoke that tool with both the cell parent and `arrays/` absent and require a successful byte-identical Python/Node result.

No fixture, transform, camera parameter, material, projection formula, Vector convention, bilinear arithmetic, validity rule, threshold, control, attack, diagnostic or decision rule may change. The first invalid execution's partial Python metrics cannot be used for tuning. Every unchanged scientific tool must continue to match the original `37fb06e68c7761dc432fa48b9287e78f7a427f24` freeze.

C1 must start from the absent root `experiments/blender-projective-subpixel-reconstruction-holdout-c1-v0-1/`, rerender all sixteen source frames and complete all 65 successful unique child processes. It may not copy, link or consume failed-root EXRs, arrays or reports as measurement inputs. The failed root remains bound by `run.failure.json` SHA-256 `ccb05339ec16b9d92350ad53552ae7368d2536e6e023bd0f1660ed9f7b67ec34`.

Frozen correction-spec SHA-256: `f540b6a2ee0bb7b2e149c795b89adbc5ab24355750f73392f21ca65c40020a79`. If any later C1 stage fails, that attempt must be retained rather than patched or resumed in place. Only a complete new-root matrix plus the inherited independent audit can authorize a D12 scientific verdict.

Artifacts: `specs/blender-projective-subpixel-reconstruction-node-parent-correction.v0.1.json` and `research/2026-08-27-b52-d12-c1-node-parent-directory-correction.md`.

## J-150 · Frozen D12-C1 tools pass missing-parent and zero-render admission

Date: 2026-08-27 · Type: CORRECTION-DELTA + FROZEN-TOOL PREFLIGHT · C1 formal outputs: 0

The four C1 files were frozen and pushed at `cd363c9`. Preflight matched all four C1 blobs to that commit and all seven unchanged scientific tools to the original D12 tool freeze `37fb06e68c7761dc432fa48b9287e78f7a427f24`. The original Node file still matched SHA-256 `e74471901441e478526f65946b43c6d1f31d274fc8928fd8229008b4337456f9`; the corrected copy was exactly the original bytes with the single registered `recursive:false` to `recursive:true` replacement.

Twelve contracts passed. The eleven inherited contracts ran from a temporary byte-for-byte materialization of the original frozen-tool commit so their preregistered old-root-absence assertion remained evaluated at its intended historical boundary. The new C1 regression began with both `node-cell/` and `arrays/` absent, completed successfully and matched all eight Python output payloads byte-for-byte.

Two real Blender 5.2 API probes again built the exact source pass state and compositor bridge graph with zero renders. Parent identities, runtime identities, analyzer independence, invalid-root retention and new-root freshness all passed. The failed D12 `run.failure.json` still matched its registered hash, and the C1 runner contained no failed-root measurement path.

Disk admission observed 107,509,596,160 available bytes. The registered 64 MiB projection leaves 107,442,487,296 bytes, 68,304,896 bytes above the unchanged 100 GiB reserve. Status: `ACCEPTED`. Receipt SHA-256: `09b193b4a97b45884bc381b13df5ed5983c2403bbbffdbcce90bca558b293f8c`; internal hash: `4a7268dcd9562bee6b4368bce48a72061c7e13e253801e14034131b3292cfd9c`.

Next: commit this immutable admission, then create the fresh C1 root once and execute all 65 child processes from scratch. No C1 formal render or measurement exists yet.

Artifact: `experiments/blender-projective-subpixel-reconstruction-holdout-c1-preflight-v0-1/frozen-tool-preflight.json`.

## J-151 · D12-C1 completes; frozen contract rejects report identity and static exactness

Date: 2026-08-27 · Type: COMPLETE REAL-BLENDER FORMAL MATRIX + RETAINED FAILED AUDIT · Runtime: 65 unique formal child PIDs

C1 completed all registered work from a fresh root: sixteen Cycles sources, eight adapters, eight Python and eight corrected Node reconstructors, eight Raw EXR encoders, sixteen Blender compositor bridges and one analyzer. The corrected infrastructure therefore worked. Receipt SHA-256 is `8c78b88ef512a5f7aa39554fced1067c12a5a0036c4c8231964b544da146ea4b`.

The frozen analyzer returned `BLENDER_PROJECTIVE_SUBPIXEL_RECONSTRUCTION_HOLDOUT_NOT_SUPPORTED`, earliest base failure `DUAL_RECONSTRUCTION_IDENTITY`. Python and Node arrays were nevertheless byte-identical in all eight cells and both matched the analyzer's independent arrays. The failed identity is the Node report self-hash: JavaScript canonical serialization emits small values as decimals while Python emits exponent notation, so all eight Node reports fail the Python `valid_report()` hash check.

All three moving fixtures passed the projective endpoint, fractional-domain, transform-depth, absolute quality and control gates. Their correct RMSE values were `5.0454e-5`, `4.5846e-5` and `3.9260e-5`, with 85.94–88.12 dB PSNR; nearest RMSE was 45–60 times larger. Direct depth identity rejected 96.39–100% of valid moving pixels, reaffirming the transform-aware rule.

The static exact gate independently failed. Blender's static Vector residual was at most `1.5258789e-5 px`; bilinear reconstruction then differed by at most `1.4901161e-7` RGB, while the preregistered static threshold was exactly zero. This is small but genuinely outside the frozen claim.

The first frozen audit is retained as `FAIL`. Its relative formal-root invocation made diagnostic sidecar replay compare relative URIs against stored absolute URIs. A temporary absolute-root diagnostic replay passed evidence replay and all identity checks, but the audit still rejected because its `attackTotality` check requires 57/57 attacks to pass even for a legitimate negative result. The temporary probe was deleted; it is not formal evidence.

Result SHA-256: `a411948ec8854029d199786bbf0a81565bc91099e2f973a2311b7513c2d07d82`; failed-audit SHA-256: `f090b7667f7ea882cc45df694f0d1dd0e39a2ead3bc83cde268b7990a64f832d`; result attacks: 47/57. Next is a preregistered audit-only C2 with no rerender or formal data rewrite.

Artifacts: `experiments/blender-projective-subpixel-reconstruction-holdout-c1-v0-1/` and `research/2026-08-27-b52-d12-c1-formal-result-and-audit-failure.md`.

## J-152 · D12-C2 preregisters an audit-only negative-verdict replay correction

Date: 2026-08-27 · Type: PRE-TOOL AUDIT-CORRECTION PREREGISTRATION · Formal rerenders/data rewrites: 0/0

C1's receipt, result, diagnostics and failed audit remain immutable at commit `7afb2c0b4c0dd9d0276b80f25d2c6aced7a9b1e4`. C2 cannot modify the 47/57 attack values, negative verdict, `DUAL_RECONSTRUCTION_IDENTITY` base failure, Node report hashes, static zero threshold or any measurement.

The corrected audit may normalize the formal root to an absolute path before replay, bind every immutable input identity and replace the logically invalid “all attacks true” audit test with a totality test over exact roster/order, boolean type, true-count consistency and nonempty methods. A diagnostic absolute-root replay already exited zero and reproduced the evidence, but its temporary output was deleted and has no formal authority.

The new tool and `audit.c2.json` do not yet exist. C2 permits only one inherited analyzer `verify` subprocess and zero Blender, adapter, reconstructor, encoder or bridge processes. Passing will confirm the frozen negative result; it cannot convert it to support.

Frozen C2 spec SHA-256: `e9a19e608de800121da0aec460bc514f6f62d51acd80dd56236adababa05cf44`.

Artifacts: `specs/blender-projective-subpixel-reconstruction-audit-c2.v0.1.json` and `research/2026-08-27-b52-d12-c2-audit-negative-verdict-correction.md`.

## J-153 · D12-C2 independently confirms the frozen negative result

Date: 2026-08-27 · Type: CORRECTED INDEPENDENT REPLAY AUDIT · Formal rerenders/data rewrites: 0/0

The C2 audit tool was frozen and pushed at `1a2220c`, then executed once. It bound the C2 spec, original C1 preflight, receipt, result, failed audit and its own Git blob before replay. All ten checks passed: spec, preflight, result, receipt, process, attack totality, diagnostic, tool, evidence replay and verdict consistency.

The inherited analyzer verify subprocess exited zero and exactly reproduced evidence, measurements, 24 diagnostic identities, operation counts, all 57 registered attack rows, the 47 passed count, `BLENDER_PROJECTIVE_SUBPIXEL_RECONSTRUCTION_HOLDOUT_NOT_SUPPORTED` verdict and `DUAL_RECONSTRUCTION_IDENTITY` base failure. C2 ran zero Blender processes and rewrote no formal input.

This confirms, rather than repairs, the negative result. Eight Node reports still fail Python canonical self-hash despite byte-identical Python/Node arrays, and static reconstruction still exceeds the frozen exact-zero threshold by `1.4901161e-7` RGB. Three moving projective fixtures retain their strong positive numeric measurements, but D12 as registered is not supported.

C2 audit SHA-256: `8496c264fff4f9eca48ab9ac2bdb751b9d39f7124215da856829104550cb0481`; internal audit hash: `603c5b31ddb9e9530dc993bb3cd043dce3a3e75d4736821949a093e015f13865`.

Artifact: `experiments/blender-projective-subpixel-reconstruction-holdout-c1-v0-1/audit.c2.json`.

## J-154 · D12.1-DEV preregisters a typed cross-language evidence envelope

Date: 2026-08-27 · Type: ALGORITHM DEVELOPMENT PREREGISTRATION · Blender/model/network calls: 0/0/0

D12's 8/8 Python/Node array identities remain positive, while all eight Node report native self-hashes remain invalid under Python's decimal canonical dump. D12.1-DEV asks whether the language-dependent decimal number representation can be removed from the evidence hash without hiding numeric differences.

Every JSON number will be replaced by a typed `{"$f64be":"..."}` object containing its IEEE-754 binary64 network-order bytes as sixteen lowercase hexadecimal digits. Both signed zeros canonicalize to positive zero; nonfinite values, integer-valued numbers outside ±(2^53−1) and unpaired surrogates reject. Objects sort keys, arrays preserve order and the final compact UTF-8 JSON receives SHA-256.

Independent Python and Node CLIs plus a third analyzer path are absent at preregistration. Passing requires byte/hash identity for all sixteen retained report bodies, exact normalized measurement identity for all eight corresponding cells, all sixteen adversarial cases and zero source modification. The output is development-only and cannot revise D12 or claim RFC 8785/JCS compliance.

Frozen development spec SHA-256: `8bd219570e0c7ec922a671919d680787caf55b2ba7d8a631ed5bc995ab24f116`.

Artifacts: `specs/blender-cross-language-evidence-envelope-development.v0.1.json` and `research/2026-08-27-b52-d12-1-cross-language-evidence-envelope-development-protocol.md`.

## J-155 · D12.1-DEV separates document hashing from reduction identity

Date: 2026-08-27 · Type: DUAL-LANGUAGE ALGORITHM DEVELOPMENT NEGATIVE RESULT · Encoder processes: 50 Python + 50 Node

The typed IEEE-754 envelope passed all sixteen adversarial cases and produced byte-identical Python/Node envelopes for every one of the sixteen retained report bodies. Each language can therefore validate the exact same document without depending on decimal exponent spelling.

The preregistered outcome is nevertheless `DEVELOPMENT_TYPED_EVIDENCE_ENVELOPE_NOT_COMPATIBLE`, gates 10/11. Only four of eight corresponding producer measurement envelopes were exact. Camera wrong-sign RMSE differed by `1.50227e-15` and derived PSNR by `5.15143e-13 dB`; static endpoint p99 differed by one binary64 ULP (`1.69407e-21 px`). Both repeats reproduced each difference.

This localizes a second issue beyond JSON formatting: Python/NumPy and JavaScript reductions can produce distinct binary64 metrics over byte-identical float32 arrays. Future evidence must separate payload identity, document self-integrity and independent decision metrics. Producer metric equality needs a frozen reduction or registered tolerance; it cannot stand in for array identity.

No source report changed and no Blender, model or network process ran. Result SHA-256: `4fc177c51060d035b02384c4d7aa1c9e427394c5589e7bddfd9102553008ce07`; internal hash: `ec8b57dcacde07c5741b3ec5d5a300551ec4557e18a72106bae467a54f8826de`.

Artifacts: `experiments/blender-cross-language-evidence-envelope-development-v0-1/results.json` and `research/2026-08-27-b52-d12-1-cross-language-evidence-envelope-development-result.md`.

## J-156 · Core compiler evidence survives direct byte-stream revalidation

Date: 2026-08-27 · Type: READ-ONLY CORE ACCEPTANCE AUDIT · New Blender renders: 0

The active goal's minimum compiler boundary was re-audited so later pixel research could not substitute for an incomplete SceneSpec → BuildPlan → Blender result. SHA-256 was recomputed directly from all eight retained canonical structure byte streams: B01-A/B and B02-A/B in both the native receipt root and the corrected clean Linux/amd64 worker root. Every digest matched its adjacent manifest and the frozen benchmark identity.

B01 remains `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b` under plan `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`; B02 remains `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856` under plan `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`. The current SceneSpec suite passed 22/22 valid/invalid fixtures. The Linux/amd64 audit remains pass, Codex-to-worker promotion remains reproducible with a passing audit, and the published compiler route returned HTTP 200.

This closes only the semantic-structure boundary already stated by the charter. `.blend` bytes remain non-identical, and no arbitrary-scene, cinematic-quality, calibrated-display or throughput claim follows. No evidence file was rewritten and no Blender render was launched.

Artifact: `research/2026-08-27-core-compiler-evidence-revalidation.md`.

## J-157 · D12.2 preregisters static floating-floor and three-layer evidence holdout

Date: 2026-08-27 · Type: FRESH-HOLDOUT PREREGISTRATION · Formal outputs: 0

D12.2 freezes three never-rendered static perspective fixtures at 83×53, 113×71 and 127×79, with fresh lens, sensor, pose, pass identity and output paths. Twelve real Blender 5.2 Cycles sources will test whether exactly unchanged transforms nevertheless produce a bounded Vector/reconstruction residue. The production tolerance is distinct from exactness: Vector component maximum ≤1/4096 px, reconstruction RGB maximum ≤1/524288 and RMSE ≤1/1048576. Exact-zero is an orthogonal reported observation, not a hidden acceptance condition.

The evidence contract is split into three layers. Python/Node reconstructed payloads must be byte-identical; each producer report must receive identical typed-envelope bytes from both frozen D12.1 encoders; and one independent analyzer must recompute all decision metrics from payload arrays while ignoring producer metrics. This directly incorporates the D12.1 counterexample instead of loosening a report hash or rounding away a difference.

The formal boundary is 55 unique child processes, zero model/network calls and a single-use fresh root. A 32 MiB projection must leave the unchanged 100 GiB reserve. All seven formal tools, preflight root and formal root are absent at preregistration.

Artifacts: `specs/blender-static-vector-floor-three-layer-evidence-holdout.v0.1.json` and `research/2026-08-27-b52-d12-2-static-vector-floor-three-layer-evidence-protocol.md`.

## J-158 · Frozen D12.2 tools pass dual-consumer, Blender and disk admission

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs/renders: 0/0

All seven D12.2 formal tools were frozen and pushed at `7b431bb5b1a57a61c2c08f645f7d2116c4637648`. The accepted preflight matched each working file byte-for-byte to its Git blob, bound the preregistered spec and Blender/Python/Node/OCIO runtimes, parsed every tool and verified the independent analyzer imports neither consumer.

A synthetic 83×53 static cell containing a `1/65536`-pixel Vector residue passed both real Python and Node CLIs; reconstructed RGBA and valid-mask payloads matched byte-for-byte. A fresh Blender 5.2 process then constructed the registered Cycles scene, three-frame static actions and Combined/Depth/Vector/Object Index pass state with zero render calls.

All 13 preflight tests passed. Disk admission observed 107,466,350,592 bytes available; the frozen 32 MiB projection leaves 107,432,796,160 bytes, 58,613,760 bytes above the unchanged 100 GiB reserve. The formal root remained absent. Preflight file SHA-256: `ddc6008eadb600d5cfa5ecf5e9187f327e51d877010c7c08b8ec6c45e8b70dbe`; internal hash: `973b5f238a6fee8897dcb2b20f1f07597d713492eaa36d79aa34b1cbabb68593`.

Next: commit this immutable admission, then create the formal root exactly once and execute the registered 55 child processes.

Artifact: `experiments/blender-static-vector-floor-three-layer-evidence-holdout-preflight-v0-1/frozen-tool-preflight.json`.

## J-159 · D12.2 supports bounded static residue and falsifies exact zero

Date: 2026-08-27 · Type: COMPLETE REAL-BLENDER FRESH HOLDOUT · Runtime: 55 unique child PIDs

The single-use D12.2 matrix completed all twelve real Blender 5.2 Cycles sources, six adapters, twelve independent consumers, twenty-four typed-envelope encoders and one analyzer. Every child PID was unique, every process exited zero and all 24 registered attacks passed. No model or network call occurred.

Previous/current source RGB arrays were exact under identical authored transforms, but all six static cells contained nonzero Vector components and nonzero bilinear reconstruction error. Across the three fresh fixtures, maximum Vector magnitude per component was `7.62939453125e-6`, `1.52587890625e-5` and `2.288818359375e-5 px`; maximum RGB error was `8.94069671631e-8`, `1.19209289551e-7` and `1.78813934326e-7`. Both repeats were exact. The largest values retain approximately 10.67× headroom under the registered Vector and RGB-maximum tolerances.

The formal verdict is `BLENDER_STATIC_VECTOR_FLOOR_WITHIN_REGISTERED_TOLERANCE`; the orthogonal classification is `STATIC_EXACT_ZERO_FALSIFIED`. This supports a bounded semantic tolerance and directly rejects a universal exact-zero gate.

The three-layer evidence design also held: Python/Node reconstruction payloads matched 6/6, both frozen typed-envelope encoders matched for every one of twelve producer documents, and the independent analyzer recomputed all decision metrics from arrays while producers emitted no metrics. Result file SHA-256 is `948ffe7f6b18bc7a5458352c545570ec1a15f9975c2ae8250de3670ac7cf3036`; receipt file SHA-256 is `aa675e9d2cefb9e7ce3b8f53dc98437ddb393ae95b7d5cdb8773d71bee10ee5f`.

The next boundary is fresh opaque nonplanar/multi-owner static geometry. The observed `1×/2×/3× 2^-17 px` maxima are a measured pattern only and must not be promoted to an internal Blender quantization claim without a separate experiment.

Artifacts: `experiments/blender-static-vector-floor-three-layer-evidence-holdout-v0-1/` and `research/2026-08-27-b52-d12-2-static-vector-floor-three-layer-evidence-result.md`.

## J-160 · D12.3 preregisters nonplanar and multi-owner static boundary

Date: 2026-08-27 · Type: FRESH-HOLDOUT PREREGISTRATION · Formal outputs: 0

D12.2's bounded static result is carried forward without widening its thresholds. D12.3 freezes three new opaque scenes: a scaled UV sphere with torus, an occluding tilted-grid/beveled-cube pair, and an icosphere behind a thin cylinder plus small sphere. Rasters, lenses, sensors, owner IDs, transforms, topology and materials are fresh.

Formal tolerance applies only to owner-interior pixels: a registered current owner with alpha >0.999, a same-owner radius-2 current neighborhood and four same-owner previous bilinear taps. Cross-owner taps fail closed. Excluded registered-owner pixels form a mandatory boundary diagnostic set whose count, owner roster, Vector maximum and reconstruction error must be reported but cannot leak into the interior verdict.

The D12.2 bounds remain exactly `1/4096 px` Vector maximum, `1/524288` reconstruction RGB maximum and `1/1048576` RMSE. Six cells must each contain at least 800 interior and 50 boundary pixels. The three-layer payload/document/decision evidence contract and 55-process boundary remain unchanged. The smaller 16 MiB projection must leave the same 100 GiB reserve.

All seven formal tool paths, preflight root and formal root are absent. Next: commit this preregistration before implementing any formal tool.

Artifacts: `specs/blender-static-nonplanar-multiowner-holdout.v0.1.json` and `research/2026-08-27-b52-d12-3-static-nonplanar-multiowner-holdout-protocol.md`.

## J-161 · Frozen D12.3 tools pass owner-boundary and real-geometry admission

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs/renders: 0/0

All seven D12.3 tools were frozen and pushed at `dfbcb50d90b780ee0bbdf728a0706749b3aa8541`. Preflight matched every working file to its Git blob, bound the preregistration and runtime identities, parsed all tools and verified analyzer import independence.

The synthetic two-owner cell placed a hard Object Index split through a continuous image and injected a `1/65536`-pixel static Vector residue. Python and Node produced byte-identical reconstruction, owner-interior and boundary payloads; both masks were nonempty and their intersection was empty. A real Blender 5.2 zero-render probe constructed the fresh scaled UV sphere and tilted torus, their procedural materials, three-frame static actions and four-pass Cycles view layer.

All 13 tests passed. Disk admission observed 107,422,646,272 bytes available; the 16 MiB projection leaves 107,405,869,056 bytes, 31,686,656 bytes above the unchanged 100 GiB reserve. Formal root remained absent. Preflight file SHA-256: `bce826c2adf9b43898d09e5ae1408c8e18165408eb7a5df5bb402b171f92186a`; internal hash: `a4628792e805a8e9cfc350ad80ed2066ca6bd7894479365ae433e1c4b300b223`.

Next: commit this immutable admission, then run the single-use 55-process real-Blender matrix.

Artifact: `experiments/blender-static-nonplanar-multiowner-holdout-preflight-v0-1/frozen-tool-preflight.json`.

## J-162 · D12.3 passes at owner interiors, with one exact threshold hit

Date: 2026-08-27 · Type: COMPLETE REAL-BLENDER FRESH HOLDOUT · Runtime: 55 unique child PIDs

D12.3 completed twelve real Blender 5.2 sources, six adapters, twelve owner-aware consumers, twenty-four typed-envelope encoders and one independent analyzer. All 55 child PIDs were unique, all processes exited zero and all 27 attacks passed. Python/Node reconstruction, interior and boundary payloads matched 6/6; twelve documents matched under both typed-envelope implementations; repeats were exact.

The formal verdict is `BLENDER_STATIC_NONPLANAR_MULTIOWNER_INTERIOR_WITHIN_REGISTERED_TOLERANCE`; exact zero is again falsified. Curved-pair, occluding-plane and thin-depth-stack fixtures retained 2,598, 7,265 and 2,437 owner-interior pixels respectively while reporting 968, 1,411 and 829 boundary pixels. Every registered owner pixel entered exactly one mask and there was zero overlap.

The occluding-plane interior maximum RGB error was exactly `1.9073486328125e-6`, the frozen `1/524288` upper limit. The `≤` gate therefore passes with zero headroom. Boundary RGB maxima were `7.33137e-6`, `5.24521e-6` and `9.89437e-6`; the largest is approximately 5.19 times the interior gate. Boundary magnitudes did not affect the preregistered verdict and do not authorize boundary reuse.

This is a narrow support result with an exposed fragility, not a reason to widen the threshold. Next: localize the exact-threshold pixels by owner, curvature/silhouette distance, raw Vector quantum and bilinear weights before any fresh generalization holdout.

Result file SHA-256: `1f41d437539e28e62446215a7b1ad16e5ffa56ea9e9eaaaecf07d64999f2988d`; receipt file SHA-256: `080669fb36c286186ead1ad28e23f351d05d2f17167901bfc72339f937af84d3`.

Artifacts: `experiments/blender-static-nonplanar-multiowner-holdout-v0-1/` and `research/2026-08-27-b52-d12-3-static-nonplanar-multiowner-holdout-result.md`.

## J-163 · D12.4 freezes zero-render localization before inspecting extrema

Date: 2026-08-27 · Type: POST-HOC DEVELOPMENT PREREGISTRATION · New Blender renders: 0

D12.3 passed its inclusive interior gate while the occluding-plane RGB maximum landed exactly on `1/524288`. D12.4 does not change that verdict and may not widen the gate. It freezes a read-only diagnostic over the already committed D12.3 source EXRs, adapter arrays and dual-consumer outputs.

The primary analysis uses repeat 1 while repeat 2 is a byte-identity control. Before interpretation, the future localizer must verify the D12.3 spec, results, receipt, execution record, all bound reports and payloads, then reproduce every formal reconstructed float32 byte. For the global maximum and top 32 samples per fixture it will record owner, Chebyshev silhouette distance, raw Vector float32 bits and `2^-17` ratio, exact bilinear taps/weights, signed tap contributions, local RGB range and a same-owner Depth Laplacian proxy.

Success only means that every tied maximum pixel was enumerated and arithmetically accounted for under independent replay. It remains a post-hoc development diagnostic, not a holdout, causal claim or permission to revise D12.3.

Artifacts: `specs/blender-static-zero-headroom-localization.v0.1.json` and `research/2026-08-27-b52-d12-4-zero-headroom-localization-protocol.md`.

## J-164 · Frozen D12.4 localizer passes zero-render admission

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · New Blender renders: 0

The analyzer, independent audit and preflight were frozen at `d72ede30ec88d73c1154be2f723f73eb1ab8f494`. Preflight verified all three working files against their Git blobs, parsed the tools, confirmed the audit does not import the analyzer, and rejected Blender/subprocess surfaces from the two evidence readers.

A disposable read-only smoke run reproduced the D12.3 float32 consumer bytes, the exact global maximum and its tied coordinates. The independent audit passed all 15 base checks and rejected all 15 registered in-memory mutations. The formal D12.4 root remained absent.

All 12 admission checks passed. Disk admission observed 107,589,361,664 bytes available; the 4 MiB projection leaves 107,585,167,360 bytes, 210,984,960 bytes above the unchanged 100 GiB reserve. Preflight file SHA-256: `a6ab1fad53932e23142e65937cfd0cd7030a20b476a879d2cd6bb820d3d55396`; internal hash: `345980f162ea5ba60daff15f2a7fbd053c6aea7ebead84e95b862105e94703af`.

Next: commit the immutable admission, create the formal output root once, then run one localizer process and one independent audit process without invoking Blender.

Artifact: `experiments/blender-static-zero-headroom-localization-preflight-v0-1/frozen-tool-preflight.json`.

## J-165 · D12.4 localizes the unique threshold pixel without revising D12.3

Date: 2026-08-27 · Type: COMPLETE POST-HOC DEVELOPMENT DIAGNOSTIC · New Blender renders: 0

The formal localizer passed 16/16 checks and the independent audit passed 15/15 base checks plus 15/15 registered mutation attacks. Every D12.3 input identity, report binding, payload hash, repeat payload and reconstructed float32 byte was reproduced. No Blender, model or network call occurred.

The global threshold is reached by exactly one sample: blue channel `(56,38)` on `FRONT_OCCLUDER` owner `10454`. It lies at Chebyshev silhouette distance 3, the first eligible ring under radius-2 erosion. Raw Vector is `(-2^-17, 0)` pixels. That gives the left neighbor weight `2^-17`; its blue value differs from the center by approximately `-0.249674`, producing a signed contribution `-1.9048577542e-6`. The final float32 cast changes the stored error to exactly `-1.9073486328125e-6`, the frozen gate.

All 32 highest-error samples in the occluding fixture belong to the front occluder and 15 are at distance 3. The rear plane maximum is only `2.98023223877e-8`. On the already observed arrays, requiring distance at least 4 lowers the maximum across all three fixtures to `4.76837158203e-7`, one quarter of the gate. That makes radius 3 a plausible post-hoc correction candidate, not a validated setting.

Next: preregister a fresh D12.5 radius-2 versus radius-3 holdout with new geometry/resolutions, unchanged numeric gates and explicit coverage retention. D12.3 remains formally passed with zero headroom.

Result file SHA-256: `ba251ebe6262b85a9f12fcef1829a2556d9513a8014bf845da24e983c2430a89`; audit file SHA-256: `26055eb706a76fbf7fda3c326ee70d49c70b9b58d62c4b28a101815fc0b0f8ee`.

Artifacts: `experiments/blender-static-zero-headroom-localization-v0-1/` and `research/2026-08-27-b52-d12-4-zero-headroom-localization-result.md`.

## J-166 · D12.5 freezes radius 2 versus radius 3 before fresh renders

Date: 2026-08-27 · Type: FRESH INTERVENTION HOLDOUT PREREGISTRATION · Formal outputs: 0

D12.4 made radius 3 a plausible intervention only on reused arrays. D12.5 now freezes a paired confirmatory test on three never-rendered opaque static scenes: a wavy panel with beveled wedge at 109×67, nested curved occlusion at 137×89 and a sphere behind two independently owned crossing rods at 149×97. Rasters, optics, transforms, owner identities, topology, materials and output paths are fresh.

The same twelve Blender source renders feed both consumers. Radius 2 is the unchanged control; radius 3 changes only current-owner erosion. The production limits remain `1/4096 px` Vector maximum, `1/524288` RGB maximum and `1/1048576` RMSE. The stronger intervention verdict additionally requires radius-3 RGB maximum ≤`1/1048576`, at least twofold headroom.

Masking cannot purchase success. Radius 3 must retain at least 800 interior pixels and 80% of total radius-2 coverage per cell; every owner retains at least 64 pixels, and owners with at least 100 control pixels retain at least 60%. Radius 3 must be a strict subset-compatible mask, with removed pixels confined to silhouette-distance ring 3.

The formal boundary is 55 unique child processes, at least 30 registered attacks, zero model/network calls and a 20 MiB projection above the unchanged 100 GiB reserve. All seven formal tool paths, preflight root and formal root were absent. No D12.5 output has been produced or inspected.

Artifacts: `specs/blender-static-radius-intervention-holdout.v0.1.json` and `research/2026-08-27-b52-d12-5-static-radius-intervention-holdout-protocol.md`.

## J-167 · D12.5-C1 binds the referenced typed-envelope parents

Date: 2026-08-27 · Type: PREREGISTRATION EVIDENCE-BINDING CORRECTION · Formal outputs/tools: 0/0

The first D12.5 JSON listed both frozen D12.1 envelope encoders in its seven-tool roster but omitted their parent URI/SHA bindings and the typed-envelope spec binding needed by the future runner. Before any formal tool path existed and before any render, adapter, consumer or analyzer output, C1 adds exactly those three already established identities.

No fixture, radius rule, numeric threshold, coverage gate, decision outcome, process count or non-claim changed. The corrected spec SHA-256 is `b24aa05aeb1ab7a33e8fc57afc646308b5454eb0a5c5bf77dbbf8cc33f2ed5f2`. This correction remains visible rather than rewriting J-166.

## J-168 · Frozen D12.5 paired-radius tools pass zero-render admission

Date: 2026-08-27 · Type: FROZEN-TOOL PREFLIGHT · Formal outputs/renders: 0/0

The D12.5 source builder, adapter, paired Python/Node consumers and independent analyzer were frozen at `ac74808725569a0c7ddfb5dcdcda26ae2a617ed0`. Preflight matched all seven formal paths to their Git blobs, bound Blender/Python/Node/OCIO plus the three typed-envelope parents, parsed every tool and confirmed the analyzer imports neither consumer.

A synthetic hard owner split passed byte-exact Python/Node reconstruction for both radii. Radius 3 was a nonempty subset of radius 2 and removed a nonempty ring. Three independent Blender 5.2 zero-render probes then constructed every new geometry family—including the wavy subdivided panel, beveled prism, nested sphere/torus and beveled crossing rods—with correct owner rosters and no render calls.

All 14 admission tests passed. Disk admission observed 107,590,574,080 bytes available; the frozen 20 MiB projection leaves 107,569,602,560 bytes, 195,420,160 bytes above the unchanged 100 GiB reserve. The formal root remained absent. Preflight file SHA-256: `e4ec7025d1a949d3552bff5b2525d377422c367ec4a75f9ac886c46a41cb200e`.

Next: commit this immutable admission, create the formal root exactly once and execute the 55-process paired-radius matrix.

Artifact: `experiments/blender-static-radius-intervention-holdout-preflight-v0-1/frozen-tool-preflight.json`.

## J-169 · D12.5 first formal run is invalid; no pixels promoted

Date: 2026-08-27 · Type: INVALID INFRASTRUCTURE RUN · Runtime: 55 unique child PIDs

The first D12.5 single-use root completed 12 Blender renders, six adapters, twelve paired-radius consumers and 24 envelope encoders across 54 successful unique children. The independent analyzer was the 55th unique child and exited 1 before writing `results.json`.

Diagnosis read only the traceback, execution counts and file presence. A radius-subset comparison remained a NumPy `bool_`; standard JSON serialization rejected it during evidence-hash construction. No measurement, threshold outcome or fixture pixel value was inspected. The root is retained, cannot be resumed and carries no scientific verdict.

D12.5-C2 is limited to casting that subset flag to built-in `bool` plus fresh experiment/root identities. Geometry, radii, thresholds, coverage gates, decisions and attacks remain frozen. Failure file SHA-256: `e90d0e26d936e35c6882a04863d2bd1e406b65db3899ca77df58a904c02ebc61`.

Artifact: `research/2026-08-27-b52-d12-5-first-formal-run-invalid.md`.

## J-170 · D12.5-C2 freezes one serialization cast and a fresh root

Date: 2026-08-27 · Type: INFRASTRUCTURE CORRECTION PREREGISTRATION · New outputs: 0

C2 is registered after retaining the invalid first root and before changing the analyzer. The only scientific-code delta allowed is `subset = bool(...)`, converting the NumPy comparison result into a standard JSON-serializable boolean. Tool/spec labels and preflight/formal roots must change to bind a genuinely fresh run.

The complete 55-process matrix must rerender all twelve sources; no EXR, adapter array or consumer payload from the invalid root may be reused. Fixtures, scene construction, reconstruction arithmetic, radii, production thresholds, twofold-headroom requirement, coverage gates, decision logic, attack minimum and non-claims remain byte-for-byte or semantically unchanged as specified.

C2 spec SHA-256 is `d9bdfa0d39d98b7bee74caad334d6ff0ce793aec68641b13f008c33e5a2c6a3d`. Both `experiments/blender-static-radius-intervention-holdout-c2-preflight-v0-1` and `experiments/blender-static-radius-intervention-holdout-c2-v0-1` were absent.

Next: commit C2 before editing tools, then freeze the exact delta and rerun preflight.

## J-171 · D12.5-C2 exact-delta preflight is accepted

Date: 2026-08-27 · Type: CORRECTED FROZEN-TOOL PREFLIGHT · Formal outputs/renders: 0/0

The corrected tools were frozen at `a817ed9f4bc8d1c47def8123447576797d87f92f`. Relative to the invalid-run analyzer, the scientific code delta is exactly the registered built-in `bool` cast; the remaining edits bind the C2 spec identity. The new preflight again passed all 14 runtime, frozen-blob, syntax, analyzer-independence, synthetic paired-radius, three-fixture zero-render and root-freshness checks.

Disk admission observed 107,569,524,736 bytes available; the 20 MiB projection leaves 107,548,553,216 bytes, 174,370,816 bytes above the unchanged reserve. Both C2 roots were fresh at admission. Preflight file SHA-256: `e848e30c03aa0af3db0e6c8ebd24c8e8eb05d90b813ced48b65b5428e2ef4c9e`.

Next: commit this admission, then rerun all 55 processes from the C2 root without reusing invalid-run artifacts.

## J-172 · Radius 3 stays within tolerance but fails the stronger intervention claim

Date: 2026-08-27 · Type: COMPLETE REAL-BLENDER FRESH INTERVENTION HOLDOUT · Runtime: 55 unique child PIDs

D12.5-C2 rerendered all twelve fresh Blender sources and completed the full paired-radius matrix. All 55 child PIDs were unique; all processes exited zero; Python/Node payloads, typed envelopes and repeats were exact; 30/30 mutation attacks passed. The formal outcome is `RADIUS3_WITHIN_PRODUCTION_TOLERANCE_BUT_HEADROOM_OR_COVERAGE_NOT_SUPPORTED`, with 21/23 decision checks passing.

Radius 3 satisfied the unchanged production Vector, RGB-maximum and RMSE gates in every cell. It was always a subset of radius 2, removed only silhouette-distance ring-3 pixels, retained 83.324%–89.943% total coverage and left more than 3,100 interior pixels per cell.

The stronger twofold-headroom gate failed. Wedge/panel and crossing-rods maxima remained unchanged at `1.2516975403e-6` and `1.1324882507e-6`, respectively 65.625% and 59.375% of the production limit. Their maxima were at distance 17 and 4, so a radius-3 erosion could not remove them. Only the nested-curves maximum fell, from `4.7683715820e-7` to `3.5762786865e-7`.

The per-owner coverage gate also failed: the tilted foreground ring retained `202/402 = 50.249%`, below the frozen 60% floor even though aggregate coverage passed. This falsifies the stronger claim that a single global radius increase delivers both twofold numerical margin and topology-fair coverage.

Next: perform a zero-render arithmetic localization of the fresh distance-17 and distance-4 maxima, then derive—but do not yet validate—a local Vector × same-owner-gradient risk gate.

Result SHA-256: `b3f70d11311fef9f3edf53bcfac511e256359e9b67971c94db89e2b0d323cdc7`; receipt SHA-256: `a77350c5e6a7589b7ace39da56509156b810e19221a8d1e3f0e8a7f750767d40`.

Artifacts: `experiments/blender-static-radius-intervention-holdout-c2-v0-1/` and `research/2026-08-27-b52-d12-5-c2-radius-intervention-holdout-result.md`.

## J-173 · D12.6 freezes arithmetic localization before adaptive design

Date: 2026-08-27 · Type: POST-HOC DEVELOPMENT PREREGISTRATION · New Blender renders: 0

D12.5-C2 proved that global radius 3 removes ring-3 pixels but leaves fresh extrema at distance 17 and 4. D12.6 therefore freezes a read-only arithmetic diagnostic over the committed valid root before proposing an adaptive rule. Repeat 1 is primary and repeat 2 remains an identity control; invalid-run and D12.3 arrays are forbidden.

Every fixture/radius tied maximum and top 64 tail samples must record owner, distance, Vector float32 bits, bilinear taps/weights, signed contributions, pre-cast value, final float32 bits and formal error. The candidate local bound sums absolute weighted tap-to-center differences and one full float32 ULP. It must underbound zero interior RGB samples; tightness, rank association and threshold selectivity remain report-only.

The formal boundary is one localizer plus one independent audit, zero Blender/model/network calls, at least 18 mutation attacks and a 4 MiB projection above the unchanged 100 GiB reserve. This is derivation, not a fresh adaptive-gate validation.

Artifacts: `specs/blender-static-interior-risk-localization.v0.1.json` and `research/2026-08-27-b52-d12-6-static-interior-risk-localization-protocol.md`.

## J-174 · D12.6 preflight accepts the frozen zero-render tools

Date: 2026-08-27 · Type: PREFLIGHT · Blender renders: 0

The D12.6 preflight passed 10/10 checks and 259 synthetic risk-bound cases before the formal root existed. It bound the three formal tools to commit `95389441e66aff5e6e5547fbab0bc593d5b790cb`, verified every named D12.5-C2 parent identity, confirmed independent audit imports and admitted the 4 MiB projected write above the unchanged 100 GiB reserve. No formal D12.6 measurement was run or inspected.

Artifacts: `experiments/blender-static-interior-risk-localization-preflight-v0-1/preflight.json` and `research/2026-08-27-b52-d12-6-interior-risk-localization-preflight.md`.

## J-175 · First D12.6 formal run is retained as invalid

Date: 2026-08-27 · Type: INVALID FORMAL RUN · Blender renders: 0

The frozen localizer exited before writing a result because an edge pixel entered the bilinear tap reader before its coordinates were rejected, producing an x=109 out-of-bounds access in the 109-pixel-wide fixture. No D12.6 measurement was emitted or inspected. The root is retained permanently; a correction requires a new experiment identity and fresh preflight/formal roots.

Artifacts: `experiments/blender-static-interior-risk-localization-v0-1/failure.json` and `research/2026-08-27-b52-d12-6-first-formal-run-invalid.md`.

## J-176 · D12.6-C2 freezes the sole edge-order correction

Date: 2026-08-27 · Type: CORRECTED PREREGISTRATION · New Blender renders: 0

D12.6-C2 is registered before changing the frozen tool. Its only permitted scientific-code delta is to test bilinear sample-coordinate bounds before the helper reads taps during reconstruction replay. All evidence inputs, arithmetic, samples, report-only statistics, thresholds and decisions remain unchanged; the invalid D12.6 root is forbidden for measurement and C2 receives fresh preflight/formal roots. Corrected spec SHA-256: `9ae043172e3d126d590b6be7942de759a503eee3c76cf4b96062e92285691fe5`.

Artifacts: `specs/blender-static-interior-risk-localization.v0.1.json` and `research/2026-08-27-b52-d12-6-static-interior-risk-localization-protocol.md`.

## J-177 · D12.6-C2 preflight accepts the corrected frozen tools

Date: 2026-08-27 · Type: CORRECTED PREFLIGHT · Blender renders: 0

The corrected preflight passed 10/10 checks and the same 259 synthetic bound cases before the fresh C2 formal root existed. It binds the tools to commit `b9718ce083fd3501c6c4a4a87c171b42497dbe1c`, includes the retained invalid-run identity, and admits the projected write above the unchanged reserve. No formal measurement was run or inspected.

Artifacts: `experiments/blender-static-interior-risk-localization-c2-preflight-v0-1/preflight.json` and `research/2026-08-27-b52-d12-6-c2-preflight.md`.

## J-178 · Local arithmetic risk replaces distance as the next hypothesis

Date: 2026-08-27 · Type: FORMAL POST-HOC DIAGNOSTIC · Blender renders: 0

D12.6-C2 passed: 92,763 interior RGB samples produced zero local-bound underestimates, all eight formal checks passed, and an independent process rejected 18/18 mutations. The fresh maxima are explained by tiny Vector weights multiplied by local color contrast: the wedge ties occur at silhouette distances 17 and 11, while the rods maximum remains at distance 4. Distance alone is not the common mechanism.

The bound is promising rather than merely conservative. Cell Spearman association is 0.8944–0.9281; at the half-gate, radius 2 selects 12/16,428 pixels to capture all 7 actual positives, while radius 3 selects 7/14,493 to capture all 6. This licenses a new unseen-fixture adaptive-risk holdout, not deployment.

Artifacts: `experiments/blender-static-interior-risk-localization-c2-v0-1/`, `research/2026-08-27-b52-d12-6-c2-interior-risk-localization-result.md`.

## J-179 · D12.7 freezes an adaptive local-risk holdout

Date: 2026-08-27 · Type: CONFIRMATORY PREREGISTRATION · New Blender renders: 0

D12.7 moves the D12.6 arithmetic bound onto three unseen opaque static geometries. The candidate is frozen as radius-2 interior plus an inclusive 1/1048576 local-risk gate; radius 3 is the paired global-erosion comparator. Success requires zero underbounds, half-gate maximum, real risk rejection, at least 98% total radius-2 retention, at least 95% per-owner retention, at least 3% more total coverage than radius 3 and no owner below its radius-3 count. Spec SHA-256: `c51d0d83afd30b479bf3e7109c31110133649ee3d65a04d677dbe236b8075ed0`.

The formal matrix registers 12 fresh Blender renders, 56 unique child processes, dual consumers, an independent audit and at least 30 mutations. No D12.5/D12.6 pixel artifact may enter the measurement domain.

Artifacts: `specs/blender-static-adaptive-risk-gate-holdout.v0.1.json` and `research/2026-08-27-b52-d12-7-adaptive-risk-gate-holdout-protocol.md`.

## J-180 · D12.7 frozen tools pass zero-output admission

Date: 2026-08-27 · Type: PREFLIGHT · Blender renders: 0

The D12.7 preflight passed 17/17 checks before the formal root existed. It binds all ten tools to commit `006d3934b3cf625e9f7e85bd837f0f5889d2be45`, verifies every runtime and parent identity, obtains byte-identical Python/Node results for all eleven synthetic payloads, exercises accepted/rejected adaptive pixels and all subset/partition branches, and passes 259 arithmetic-bound cases.

Three fresh Blender 5.2 processes constructed all seven new geometry types with zero render calls and no EXR. Disk admission left `141344768` bytes above the unchanged 100 GiB reserve after the 24 MiB projection. No D12.7 formal pixel or decision has been created or inspected.

Artifacts: `experiments/blender-static-adaptive-risk-gate-holdout-preflight-v0-1/frozen-tool-preflight.json` and `research/2026-08-27-b52-d12-7-adaptive-risk-gate-preflight.md`.

## J-181 · D12.7 matrix completes; audit mutation projection fails

Date: 2026-08-27 · Type: FORMAL RESULT + AUDIT FAILURE · Blender renders: 12

All 54 production children and the analyzer completed. The frozen result is `ADAPTIVE_GATE_WITHIN_TOLERANCE_BUT_STRESS_OR_COVERAGE_NOT_SUPPORTED`, 20/21 checks: the adaptive candidate passed every identity, production, headroom, conservatism, stress and coverage gate; only paired `RADIUS3_PRODUCTION` failed. The independent audit reproduced payloads, measurements and 56-process totality, but caught only 28/30 repaired-self-hash mutations because its expected projection omitted the analyzer mutation roster itself. The runner correctly wrote `run.failure.json` and no receipt.

Audit-only C1 is preregistered before its tool exists. It may protect `analyzerPid` and the already semantically checked `mutationAttacks` array, bind all immutable parents, and write only a new audit and correction receipt. It cannot rerun or change any scientific artifact or verdict.

Artifacts: `experiments/blender-static-adaptive-risk-gate-holdout-v0-1/`, `specs/blender-static-adaptive-risk-gate-audit-c1.v0.1.json`, and `research/2026-08-27-b52-d12-7-formal-audit-failure-and-c1-protocol.md`.

## J-182 · D12.7 C1 validates a bounded but technically strong candidate

Date: 2026-08-27 · Type: AUDIT-ONLY CORRECTION + FORMAL INTERPRETATION · New Blender renders: 0

The frozen result remains `ADAPTIVE_GATE_WITHIN_TOLERANCE_BUT_STRESS_OR_COVERAGE_NOT_SUPPORTED`. Adaptive retained 99.60%–99.86% of radius 2, exceeded radius-3 coverage by 10.47%–26.70%, rejected 11/7/26 high-risk pixels in the three primary fixtures, kept every owner above 95% radius-2 retention and above its radius-3 count, produced zero risk underbounds, and stayed below the `1/1048576` half-gate. Only `RADIUS3_PRODUCTION` failed: one comparator cell reached `2.1457672e-6`, above `1/524288`.

The C1 audit bound every immutable parent, reran one independent Python process, reproduced the same result and rejected 30/30 repaired-self-hash mutations. No scientific process or artifact changed. Corrected audit SHA-256: `fe77a26135d8021db6eb52f6e310392efd1a155f5712c99cd9dddbc1925708ee`; correction receipt SHA-256: `12677054b85a325b803e6d59166d756306497c7b2e4159ae93bffe7f554f36a0`.

The next holdout must preregister comparator decision semantics before new fixtures and add real rigid motion/disocclusion. D12.7 remains a static candidate, not a production temporal policy.

Artifact: `research/2026-08-27-b52-d12-7-adaptive-risk-gate-holdout-result.md`.

## J-183 · D12.8 freezes real motion and disocclusion before tool work

Date: 2026-08-27 · Type: CONFIRMATORY PREREGISTRATION · New Blender renders: 0

D12.8 separates history reuse into two ordered decisions on four entirely fresh perspective fixtures: transform-aware structural validity first, then the unchanged D12.7 radius-2 plus inclusive `1/1048576` local-risk gate. The fixtures introduce moving-owner reveal, camera dolly/yaw parallax with bounds loss, a same-Object-Index depth trap, and a multi-owner static control. Invalid history and risk-rejected history must both copy current float32 RGBA exactly.

Comparator semantics are now explicit before new evidence: radius 3 is report-only and cannot affect the candidate verdict. The candidate still must satisfy zero false acceptance, zero risk underbounds, the D12.7 half-gate, 98% total radius-2 retention, 95% per-owner retention, real risk stress and cross-language/repeat/process/audit identity. A safe candidate with inadequate coverage receives a distinct bounded label rather than support.

The formal matrix is frozen at 74 unique child processes including audit, 16 fresh Blender Cycles source renders, zero model/network calls and a 64 MiB projection above the 100 GiB reserve. At preregistration time both output roots and all eight new tool paths are absent. Spec SHA-256: `67722b1c8fafa0b83518e6e467de1adb9ca88bd32b7145f15be2d5627767b4d4`.

Artifacts: `specs/blender-projective-motion-disocclusion-adaptive-risk-holdout.v0.1.json` and `research/2026-08-27-b52-d12-8-projective-motion-disocclusion-adaptive-risk-holdout-protocol.md`.

## J-184 · D12.8 source construction passes four real Blender zero-render probes

Date: 2026-08-27 · Type: TOOL DEVELOPMENT · Formal Blender renders: 0

After preregistration commit `7f62162`, the source renderer and multipart adapter were implemented without changing the frozen spec. Four fresh Blender 5.2 processes constructed the four registered scenes at current frame 1 with zero render calls. Every scene exposed two analytic owners, the background/occluder polygon counts were exactly 3,168/768, all unique-ID fixtures reported their frozen pass-index pairs, and the same-index depth trap preserved `[13505,13505]` exactly. Combined, Depth, Vector and Object Index were enabled on `BFS_D128_MASTER` in every probe.

Both Python files compile under Blender Python 3.13. The adapter has not consumed a formal fixture EXR: doing so during development would expose the fresh holdout before tool freeze. Its first real multipart execution remains behind the frozen preflight/formal boundary. The observed Blender 6.0 deprecation warnings for `use_nodes` are non-fatal 5.2 API warnings and are retained as a future-version boundary, not a 5.2 failure.

Artifacts: `blender/render_b52_d12_8_motion_disocclusion_source.py` and `scripts/adapt-b52-d12-8-motion-disocclusion-source.py`.

## J-185 · Dual consumer smoke removes non-normative projection bytes

Date: 2026-08-27 · Type: TOOL DEVELOPMENT COUNTEREXAMPLE + CORRECTION · Formal Blender renders: 0

The first synthetic two-owner smoke compared 12 Python/Node payloads. Eleven were byte-exact: adaptive reconstruction, accepted/rejected masks, analytic-owner mask, structural reason/valid masks, radius-2/radius-3 masks, both predicted-depth arrays and the float64 risk array. Only consumer-emitted `expectedVector.xy32` differed, exposing a last-bit cross-language trigonometric diagnostic rather than a decision difference.

The frozen spec requires cross-language identity for reconstructed, reason, mask and risk payloads, while the independent analyzer owns the projection oracle. Before tool freeze, both consumers therefore stopped exporting non-normative projection/depth diagnostic arrays; their calculations remain internal to structural decisions and the analyzer will recompute projection independently. A second clean synthetic run produced byte-identical hashes for all nine remaining canonical payloads.

This smoke is not scientific evidence: it used generated constant-color arrays, no Blender render and no formal fixture measurement. It is retained as a contract-design counterexample.

Artifacts: `scripts/reconstruct-b52-d12-8-motion-disocclusion.py` and `scripts/reconstruct-b52-d12-8-motion-disocclusion.mjs`.

## J-186 · D12.8-C1 binds the missing typed-envelope spec before formal output

Date: 2026-08-27 · Type: MECHANICAL PREREGISTRATION CORRECTION · Formal Blender renders: 0

Runner implementation exposed an incomplete dependency graph: the two frozen D12.1 envelope encoders require the D12.1 machine spec, but original D12.8 froze only the encoder files. No undeclared input is allowed into a formal evidence chain.

C1 adds only that spec URI/SHA, changes the experiment and output roots to fresh C1 identities, and updates embedded corrected-spec hashes. The question, fixtures, transforms, validity/risk algorithms, thresholds, comparator role, process matrix and verdicts do not change. Original preregistration commit `7f62162` and SHA `67722b1c…7b4d4` remain the immutable historical boundary; corrected spec SHA is `d7e7c0ee…6aea6`.

Artifact: `research/2026-08-27-b52-d12-8-c1-typed-envelope-parent-correction.md`.

## J-187 · D12.8-C1 preflight development exposes Node parent-directory failure

Date: 2026-08-27 · Type: PREFLIGHT TOOL FAILURE · Formal Blender renders: 0

The first zero-output preflight development invocation reached the synthetic consumer stage but raised `FileNotFoundError` because the preflight attempted to read a missing Node report without surfacing child stderr. After adding failure propagation, a second invocation exposed the real cause: Node used non-recursive `mkdir` for the nested consumer array directory and exited with `ENOENT`.

No preflight JSON, C1 formal root, source EXR, adapter payload, measurement or verdict was created. The correction is limited to recursive parent materialization after the existing non-existence guard, plus explicit child stdout/stderr propagation in preflight. Consumer arithmetic and every frozen scientific rule remain unchanged. Both failed invocations are retained in this journal rather than promoted into an accepted preflight.

Artifacts: `scripts/reconstruct-b52-d12-8-motion-disocclusion.mjs` and `scripts/preflight-b52-d12-8-motion-disocclusion.py`.

## J-188 · D12.8-C1 frozen tools pass zero-formal-output admission

Date: 2026-08-27 · Type: CORRECTED PREFLIGHT · Formal Blender renders: 0

At tool-freeze commit `462937751d6375784ae63968e6614ccf85f53215`, the corrected preflight passed 11/11 checks. Four real Blender 5.2 processes reconstructed all fresh scenes with zero render calls; the same-index fixture retained `[13505,13505]`. Every parent, runtime and Git blob identity matched.

The synthetic branch suite exercised `INVALID_CURRENT_ORACLE`, `INVALID_BOUNDS`, `INVALID_OWNER`, `INVALID_ALPHA`, `INVALID_DEPTH` and `VALID`, plus 16 adaptive risk rejections. Python and Node produced byte-identical hashes for all nine canonical payloads. Analyzer imports remained independent of both consumers and Blender geometry modules.

Disk admission measured 107,490,267,136 available bytes; after the frozen 64 MiB projection, 107,423,158,272 bytes remain, only 48,975,872 bytes above the 100 GiB reserve. The C1 formal root remained absent. Preflight hash: `1e0c99b14221a362ebaf2e6f6ce96ad3215d896db7fd6c6139093551cd532289`.

Artifact: `experiments/blender-projective-motion-disocclusion-adaptive-risk-holdout-c1-preflight-v0-1/frozen-tool-preflight.json`.

## J-189 · D12.8-C1 rejects motion generalization; C2 freezes audit-state semantics

Date: 2026-08-27 · Type: FORMAL NEGATIVE RESULT + AUDIT-ONLY PREREGISTRATION · Blender renders: 16

The single formal matrix completed 72 production children, one analyzer and one audit. The immutable result is `PROJECTIVE_MOTION_DISOCCLUSION_ADAPTIVE_GATE_NOT_SUPPORTED`, 9/14 checks, with 40/40 analyzer mutations. Structural rejection, fallback, risk conservatism, static control, registered stress and comparator exclusion passed. The unchanged D12.7 risk threshold retained only 16.98%, 0%, and 13.17% of radius-2 history on the three moving fixtures, falsifying production coverage.

Python and Node differed only in `risk.rgb64`: 46/88/16 scalars per moving fixture and repeat, at no more than `4.336808689942018e-19`; all eight decision/reconstruction payloads, both repeats and every adaptive decision agreed. Exact cross-language identity therefore remains false. `VECTOR_DEPTH_ORACLE` also remains false; the frozen analyzer included expected depth-rejected pixels in its aggregate depth maximum, and no post-hoc correction is allowed.

The original audit reproduced the evidence but failed 9/10 because it required the already-failed scientific dual-payload gate to pass. C2 is preregistered before its tool exists. One new read-only Python process may verify that the raw divergence exactly matches the negative result, while preserving every formal byte, false check, verdict and the absence of an original receipt.

Artifacts: `experiments/blender-projective-motion-disocclusion-adaptive-risk-holdout-c1-v0-1/`, `specs/blender-projective-motion-disocclusion-adaptive-risk-audit-c2.v0.1.json`, and `research/2026-08-27-b52-d12-8-formal-negative-and-c2-audit-protocol.md`.

## J-190 · D12.8 C2 validates the immutable negative state

Date: 2026-08-27 · Type: AUDIT-ONLY CORRECTION + RESULT INTERPRETATION · New Blender renders: 0

The one permitted C2 Python process passed 16/16 checks and 40/40 mutation attacks. It spawned no Blender, adapter, consumer, envelope or analyzer process; verified the original 74 unique PIDs plus its own PID; bound the correction spec and both audit tools to frozen Git blobs; and reproduced the immutable rejected verdict with the exact five false and nine true scientific checks.

From raw Python/Node payloads it reproduced 300 float64 risk differences across the six moving cells, per-cell maxima no larger than `4.336808689942018e-19`, exact repeat summaries, all 64 non-risk payload identities and zero derived adaptive-decision differences. The risk bytes therefore remain scientifically non-identical while the audit now correctly accepts that the negative result reports this state faithfully.

The motion result is decisive for the next design: static tap-to-current contrast is safe on accepted samples but catastrophically conservative after correct projective transport. Moving fixtures retained 16.98%, 0%, and 13.17% of radius-2 history, while the static control retained 100%. D12.9 must preregister a motion-aware uncertainty term, canonical risk serialization and a valid-history-only depth metric on fresh fixtures.

C2 audit SHA-256: `0dd3a31e7244a76167ee8c61e690fa2e1bd38ba1089351e6088192c7fb6df7d8`; audit hash: `872ebf57332da68bc18453a5747e47326e97dc2aeff85d84bc4f72c88f1d01b5`.

Artifact: `research/2026-08-27-b52-d12-8-projective-motion-disocclusion-adaptive-risk-result.md`.

## J-191 · Q30 二阶差分风险从 D12.8 失败数据中恢复运动覆盖

Date: 2026-08-27 · Type: POST-HOC CANDIDATE DERIVATION · New Blender renders: 0

D12.9-D1 明确把 D12.8 当作已观察的派生集，而不是新 holdout。候选不再对 previous taps 与 current RGB 做绝对差；它只读取 previous RGB / owner / alpha 与 current Vector，以 4×4 previous support 的水平、垂直二阶差分估计双线性插值余项。颜色以 Q30、运动小数以 Q24 表示，风险输出为 little-endian uint32；current RGB 只由独立 analyzer 用于测量，不参与 accept / reject。

Python 与 Node 对四个 fixture 的 `eligible.u8`、`accepted.u8`、`risk.q30.u32` 全部逐字节一致，独立整数重放一致，三个进程唯一，10/10 checks 通过。三组 moving fixture 的 radius-2 retention 从旧规则的 16.98%、0%、13.17% 提升到 97.994%、98.374%、97.475%；所有有至少 100 个样本的 analytic owner retention 均不低于 97.092%。accepted RGB maximum 为 `1.866657e-5`，低于冻结的 `2^-15` quality ceiling；所有 eligible RGB 样本 risk underbound 为 0。static control 保留 100%，same-index fixture 仍有 97 个 curvature-risk rejection。

这只是 post-hoc candidate selection。有限差分不是任意 rendered signal 的数学上界；factor 4、Q30 allowance 与两个 threshold 都是在看过 D12.8 后选定，必须在任何新 render 之前冻结进 D12.9-H1。下一步必须使用新 resolution、transform、material frequency 与 disocclusion geometry，并把 valid-history depth agreement 与 expected depth rejection 分成两个 typed domain。

Result SHA-256: `e78ddf4d447b46398dc0ad314ee81e55c7bf2e22744ab57a2a2c7cbb8833438c`; evidence hash: `ea7ad8f269016ee01a42a9e42558f727f73cb979f50fbd6ccc92301de1fa3ac1`; receipt hash: `78188333858c398804105891afb200762185655e6e28bf69ceb3f224c8253566`.

Artifact: `research/2026-08-27-b52-d12-9-motion-aware-curvature-risk-derivation-result.md`.

## J-192 · D12.9-H1 留出协议冻结，正式测量尚未开始

Date: 2026-08-27 · Type: PREREGISTRATION + TOOL DEVELOPMENT · Formal Blender renders: 0

D12.9-H1 已在 commit `ac4d7cd` 预登记：四个未见 fixture 使用新的 raster、47 mm lens、camera/owner trajectory、pass index、material coefficients/frequencies/phases 与独立 formal root。Q30/Q24 风险公式、`131072` inclusive risk threshold、`2^-15` quality ceiling、per-cell/per-owner coverage、typed depth domains、same-index depth/curvature stress、74-process matrix、至少 48 个攻击以及三档 verdict mapping 均已在任何正式工具输出或 render 之前冻结。Spec SHA-256 为 `c2756a20e314cf470698ef7af6160154b8d7e2d5e8531ce6591b2509a8730dbc`。

工具开发阶段用真实 Blender 5.2 分别构建了四个新场景，每次都得到两个 analytic owner、零 render call 并正常退出；这些是 probe-only API/scene-construction 证据，不是 holdout measurement。探针后的临时 `jq` 汇总表达式存在优先级错误并打印解析错误，但四份 Blender report 均已生成且进程 exit 0；该 reporting defect 不影响 Blender probe，也不被隐藏。

Python/Node consumer 已在合成静态数组上对十个 canonical output payload 全部逐字节一致。第一版合成 stress 把颜色变化放在整数采样坐标，正确地没有触发 curvature risk，暴露了测试设计缺陷：整数位置的双线性余项为零。冻结前的 preflight 实现因此改为使用 Q24-exact 的 `(0.5,0.5)` fractional sample 与 4×4 Q30 checker support，要求 `supportEligible=1` 且 `riskRejected=1`。这项新版 preflight 尚未运行。

源场景、adapter、双语言 consumer、独立 scalar analyzer、raw-payload audit、zero-formal-output preflight 与 single-use runner 均已实现，并通过 Blender Python 3.13 `py_compile` / Node syntax check。正式 root 与 preflight root 仍不存在，正式 Blender renders 仍为 0；因此当前状态只能写作 **TOOLS IMPLEMENTED, HOLDOUT NOT RUN**。磁盘最近测得约 102.3 GiB 可用，扣除冻结的 80 MiB projection 后仍在 100 GiB reserve 之上，但余量很小，重启后必须重新做 admission check。

Artifacts: `specs/blender-motion-aware-curvature-risk-holdout.v0.1.json`, `blender/render_b52_d12_9_motion_aware_source.py`, and `scripts/*b52-d12-9-motion-aware*`.

## J-193 · D12.9-H1 冻结工具通过零正式输出准入

Date: 2026-08-28 · Type: PREREGISTERED PREFLIGHT · Formal Blender renders: 0

重启后重新核对 commit `76ac7a1431d90d0785afcaec8253a3d040bbca9d`、Blender 5.2、Blender Python 3.13、Node 26.5.0、OCIO、所有 parent 与 tool blob 身份，全部匹配预登记值。正式 root 在预检开始和结束时都不存在。

一次冻结 preflight 通过 10/10 checks。四个真实 Blender 5.2 子进程分别构建 `ROTATED_SWEEP_HIGH_FREQUENCY_157X103`、`CAMERA_TRUCK_PITCH_PARALLAX_167X109`、`SAME_INDEX_DEPTH_CROSSING_179X113` 与 `STATIC_FREQUENCY_CONTROL_131X89`；每份自哈希 report 均有效、owner count 均为 2、render call 均为 0。独立 analyzer 的 import graph 不含 consumer、`bpy` 或 `mathutils`。

合成分支测试以 Q24-exact `(0.5,0.5)` fractional sample 和 4×4 Q30 checker support 命中 `supportEligible=1`、`riskRejected=1`，其余 accepted pixels 为 9,870。Python 与 Node 均 exit 0、report self-hash 有效、十个 canonical payload 全部逐字节一致。该测试只证明冻结工具能识别预定分支，不是 holdout quality evidence。

磁盘准入测得 `110369837056` available bytes；扣除冻结的 80 MiB projection 后为 `110285950976` bytes，高于 100 GiB reserve。Preflight hash: `6f1e1ad65a17ab09d1f80a0b3d25a915313c649e2765919178b36ad9e9f1b4be`。下一步只允许一次 fresh formal root creation；任何 child failure 都必须保留原始 root 与 failure receipt。

Artifact: `experiments/blender-motion-aware-curvature-risk-holdout-preflight-v0-1/frozen-tool-preflight.json`.

## J-194 · D12.9-H1 安全成立，但新鲜覆盖门未成立

Date: 2026-08-28 · Type: FORMAL BOUNDED RESULT · Blender renders: 16

一次性 formal matrix 在 66.34 秒内完成 72 个生产 children、一个独立 analyzer 与一个 raw-payload audit。74 个 PID 全部唯一且 exit zero；Python/Node 的 80 个 canonical consumer payload audit checks 全部 byte exact；48/48 mutation attacks 与 9/9 audit checks 通过。正式 verdict 为 `MOTION_AWARE_CURVATURE_RISK_SAFE_BUT_COVERAGE_NOT_SUPPORTED`，科学门 13/14，唯一 false check 为 `COVERAGE`。

已接受域仍满足安全主张：每个 cell 的 risk underbound 为 0，accepted RGB max/RMSE 低于 `2^-15`，false invalid accept 为 0，所有 fallback 精确复制 current float32 RGBA。Vector endpoint、typed valid-history depth、same-index expected depth rejection、stress 与 static control 全部通过。same-index 场景把 4,169 个同 pass index 但错误深度的 history 正确分离到 `INVALID_DEPTH`，没有污染 valid-history depth maximum。

覆盖在两个新鲜 moving fixture 失守。Rotated sweep 接受 9,765 / 10,327（94.558%），前景 owner 为 8,064 / 8,565（94.151%）；Same-index crossing 接受 13,717 / 14,159（96.878%）。Camera parallax 为 97.735%，static control 为 100%。损失同时来自 incomplete 4×4 support 与真实 curvature rejection。

后验阈值检查否定了“只差一点所以调大阈值”：sweep 达到 97% 至少需 Q30 `140559`，但 max error 变成 `3.260374e-5`，超过质量门；same-index 达到 97% 需 Q30 `31569966`，max error `1.230001e-3`，约为质量门的 40 倍。下一干预必须把 target validity、true-owner support 与 interior curvature acceptance 分成 typed domains，并研究 compiler-controlled temporal owner identity；不能事后把 97% denominator 改成更容易通过的集合。

Evidence hash: `cb9f68251a0016634a0580decc5f898732172eee9eddd560a42dccb493490f16`; audit hash: `46635a9777885a690961cf070ddbd2a7bb1ab97d996f772a3010e52f61ec0943`; receipt hash: `c794bd2c79a584b6ade138d8b09d4bc516f68778c1bf8f6c6d29926424cf3fe8`.

Artifact: `research/2026-08-28-b52-d12-9-h1-motion-aware-curvature-risk-holdout-result.md`.

## J-195 · 标量阈值反事实不能同时修复覆盖与质量

Date: 2026-08-28 · Type: POST-HOC FAILURE LOCALIZATION · New Blender renders: 0

独立脚本绑定正式 result/audit/receipt SHA 后，从 R1 raw adapter 与 Q30 payload 重算每个 support-eligible pixel 的 bilinear error，并寻找每个 cell 刚好达到 97% coverage 的最小 counterfactual threshold。该分析只解释正式失败，不改 verdict、不选择新阈值，也不把 H1 数据重新称为 holdout。

Rotated sweep 需要再接纳 253 个 risk-rejected pixels，最小 Q30 threshold `140559`，但 accepted RGB max 随即达到 `3.260374e-5`，超过冻结的 `2^-15`。Same-index crossing 只差 18 pixels，却要到 Q30 `31569966` 才达到 97%；RGB max 为 `1.230001e-3`，约 40 倍质量上限。Camera 与 static 在原阈值已经通过。

因此当前证据反对“调大一个 scalar threshold”这条修复。下一假设转向 compiler-controlled temporal owner identity 与 target/support/interior 三个 typed domains；同时保留 accepted/registered 总覆盖，防止缩小 denominator 后虚构成功。Analysis hash: `56a04de570ca33dc271bc7d4a62400bb0fa98bcb3760885435c77df3ae79d516`。

Artifact: `experiments/blender-motion-aware-curvature-risk-holdout-coverage-analysis-v0-1/results.json`.

## J-196 · D12.10-D1 预登记 true-owner support 定位

Date: 2026-08-28 · Type: POST-HOC LOCALIZATION PREREGISTRATION · New Blender renders: 0

H1 指向的下一变量被限制为 owner identity 与 support geometry，不再允许继续调 scalar threshold。D12.10-D1 在 analyzer 与 output root 都不存在时冻结：以独立 scalar ray-plane oracle 分别重建 frame 0 / frame 1 的 analytic owner token；在 H1 radius-2 域中把像素严格分成 four-tap true-owner mismatch、four taps 正确但额外 4×4 symmetric stencil 跨 owner、full true-owner stencil 三类。

协议会分别报告 Object Index bilinear alias、curvature-support alias、one-sided stencil opportunity、full-support 内的 Q30 risk rejection，以及任何 accepted-but-true-owner-mismatch 像素。repeat 2 只做 token/classification byte identity；所有 H1 formal bytes 只读，禁止 Blender render、模型与网络。same-index alias 和 moving one-sided opportunity 都必须非空，否则定位 verdict 失败。

该分析明确是 post-hoc，不允许生成新 threshold、supported candidate 或新的 coverage denominator，也不允许把 H1 的 bounded verdict 改写。Spec SHA-256: `ac507754a47496a7b9f4f29e1d3313738c12580d0f10e19ef42301f2f4892a7b`。

Artifact: `specs/blender-temporal-owner-support-localization.v0.1.json`.

## J-197 · D12.10-D1 定位输出因比例聚合错误作废

Date: 2026-08-28 · Type: TOOL/MEASUREMENT FAILURE · New Blender renders: 0

D12.10-D1 首次 analyzer 输出表面通过 9/9 checks 与 24/24 mutations，独立 frame-1 owner token 也与 H1 analytic-owner payload exact；但人工复核发现 `acceptedToTrueOwnerBilinear` 与 `acceptedToTrueOwnerFullStencil` 使用了全体 accepted 作分子，而不是 accepted 与各自 domain 的交集。

same-index primary 中恰有 15 个 accepted pixels 落在 true-owner bilinear domain 外，因此 background owner ratio 变成 `1.006846...`，cell 的 full-stencil ratio 变成 `1.004761...`。任何 set retention 大于 1 都直接证明聚合错误。原始 tool、payload 与结果不覆盖、不删除；D1 emitted verdict 作废。

与此同时，原始分类暴露的 17 个 same-index bilinear owner aliases 和其中 15 个 accepted aliases 是必须进一步核验的安全边界。C1 只允许把两个 numerator 改成显式 set intersection，并新增 ratio ∈ [0,1] 与 accepted decomposition checks；必须使用新 tool path 和 fresh output root。

Artifact: `research/2026-08-28-b52-d12-10-d1-aggregation-defect.md`.

## J-198 · D12.10-C1 冻结机械聚合修正

Date: 2026-08-28 · Type: CORRECTION PREREGISTRATION · New Blender renders: 0

D12.10-D1 的错误结果、工具和五类派生 payload 保持原样；C1 在新 analyzer 与新 output root 均不存在时冻结。允许的修正仅限把两个错误 numerator 改成 accepted 与对应 true-owner domain 的显式交集，并增加 cell/owner 两层 set decomposition、ratio ∈ [0,1]、D1 payload/classification identity 与至少 28 个 mutation attacks。

C1 禁止改变 ray-plane oracle、owner token、tap/stencil、三类 support classification、Q30 risk、阈值或 H1 verdict，也禁止隐藏 same-index primary 中已经观察到的 15 个 accepted-outside-true-owner-bilinear pixels。它仍是 post-hoc failure localization，不是新 holdout、候选算法或生产安全证明。

冻结时确认 corrected tool `scripts/analyze-b52-d12-10-c1-temporal-owner-support.py` 与 corrected output root `experiments/blender-temporal-owner-support-localization-c1-v0-1` 均不存在。Spec SHA-256: `2ba1edd74fef18eacfa1c170cab4e35f80afc575eaef1ffe3500428553555403`。

Artifact: `specs/blender-temporal-owner-support-localization-c1.v0.1.json`.

## J-199 · C1 内部通过，但首次独立审计器失败

Date: 2026-08-28 · Type: RETAINED AUDIT-TOOL FAILURE · New Blender renders: 0

C1 analyzer 一次运行得到 16/16 checks、30/30 targeted mutations 与 `TEMPORAL_OWNER_SUPPORT_ALIAS_LOCALIZED_C1`。40 个派生 payload 与 D1 byte exact；same-index primary 的正确分解为 accepted `13,717 = 13,702 within-bilinear + 15 outside-bilinear`，而 `13,702 = 13,652 full-stencil + 50 extra-stencil`。所有修正比例均在 `[0,1]`。

首次独立 Node audit 只通过 7/10、独立攻击 11/12，因此结果暂不推广。复核定位到两个 audit-tool 缺陷：Node `JSON.stringify` 不能复现 Python 对 `1.0` 等数值的 canonical bytes；“analysis hash attack”又在篡改后重新计算了合法 hash，因此它不是攻击。其余 payload byte identity、D1 classification identity、set/ratio replay、formal attack roster 与 zero-operation gates 均通过。

失败 audit 与 tool 已用 SHA 固定并保留。下一步只允许新 audit tool path 与 `audit-c1.json`；不得改变 C1 analyzer、result、payload 或 measurement。Failure audit SHA-256: `3597bddced17737a78fc3e64627fcc7f07c4938aaeb598eda34018aee616d90a`。

Artifact: `research/2026-08-28-b52-d12-10-c1-audit-d1-failure.md`.

## J-200 · C1 修正审计通过，owner alias 与 stencil loss 已分离

Date: 2026-08-28 · Type: CORRECTED POST-HOC LOCALIZATION RESULT · New Blender renders: 0

新路径 Node auditor 绑定 C1 result file SHA，不再假设 Python/JavaScript 数值 JSON 是同一 canonical format；它独立重放所有 set/ratio 方程、逐字节比较 40 个 payload、核对 D1 classification identity，并以 11 个语义 mutation 重验边界。结果 10/10 checks、11/11 attacks，通过；失败的首次 audit 继续保留。

Rotated sweep 与 camera parallax 的 true-owner bilinear mismatch 都是 0；其 146 / 152 个 support losses 全在对称 4×4 stencil 的 extra-owner 区域。Same-index crossing 有 17 个 Object Index bilinear aliases，其中 15 个被 H1 接受；正确分解为 `13,717 = 13,702 within-bilinear + 15 outside`，且 `13,702 = 13,652 full-stencil + 50 extra-stencil`。所有 ratio 都落在 `[0,1]`。

因此下一干预被拆成两条独立、可证伪路径：真实 Blender 的 compiler-controlled per-owner token 负责 same-index identity；owner-aware/one-sided curvature support 负责 moving stencil opportunity。前者先测 Material Index 与 custom AOV 的离散性、EXR 读回、边缘语义和净进程复现，不直接假定任一路径可用。

Result SHA-256: `90e8a4d72c0224e4195cd6a52ea193d93211d6dfe368ed7efdd1c3d421d393c8`; analysis hash: `e0f9c8417357ef0d08a75c45ce108d650fe8df22b7a6f3140ea4c3e787ddc719`; corrected audit SHA-256: `7bea1f8db8bf15a41384fa3b1e9a8be5bc44b35ce71b34f18ea51e7549f705c2`; audit hash: `88c4f6081b80e2b62b535e7d4bb364a3b52c45d8b23ded48e30b69060e338e57`。

Artifact: `research/2026-08-28-b52-d12-10-c1-temporal-owner-support-localization-result.md`.

## J-201 · D12.10-P1 预登记真实 Blender owner-token pass probe

Date: 2026-08-28 · Type: REAL-BLENDER INTERVENTION PREREGISTRATION · Formal Blender renders: 0

C1 将 same-index owner alias 与 moving 4×4 stencil loss 分离后，下一实验只处理第一项：Blender 是否能把 compiler-assigned analytic-owner token 作为可审计数据 pass 传进 multilayer EXR。P1 在五个新工具、preflight root 与 formal root 全部不存在时冻结。

正式矩阵固定为 193×127、Cycles CPU、32 samples、两个 motion frames、ACES SDR / Un-tone-mapped 两个显示设置、两个净进程 repeats，共 8 次真实 render。背景与前景故意共享 Object Index 7，同时分别赋 Material Index 11/23 与 Value AOV 0.25/0.75。独立正交投影只在三像素 stable interiors 判定 exact token；边缘只测量、不挪进内域 denominator。

候选必须同时通过 EXR 可用、finite、每 owner 至少 256 interior pixels、float32 exact token、same-index 区分、display-invariant bytes 与 clean-repeat bytes。Object Index 必须按预登记成为 negative control。Material Index 与 custom AOV 分别给出 viability，不允许把 pass probe 直接称为 temporal reconstruction 成功。

Spec SHA-256: `7eb76c00baad8cbc4f996ec7a139e6a3cb1fd90c1c02391a531d8c2637abd4be`。

Artifact: `specs/blender-owner-token-pass-probe.v0.1.json`.

## J-202 · P1 预登记后零渲染 Blender RNA 开发探针

Date: 2026-08-28 · Type: DEVELOPMENT API OBSERVATION · Blender renders: 0

一个 factory-startup Blender 5.2 进程在绑定 OCIO 下只查询 RNA，没有建 formal root 或写实验 artifact。实测 `ViewLayer.use_pass_material_index` 与 `ViewLayer.aovs` 存在，AOV collection 暴露 `add/remove`，`ShaderNodeOutputAOV` 存在且输入为 `Color/Value`；新增 AOV 默认 type 为 `COLOR`，可显式设为 `VALUE`。`Material.pass_index` 的 hard range 为 0–32767。

该观察只用于把已经预登记的 source tool 写到真实 API，不是 pass transport 证据。五个新工具随后通过 system Python 与 Blender Python 的 syntax compilation；尚未运行 preflight 或 render。下一步先把工具 bytes 固定到 Git commit，再允许 preflight 产生首个 output root。

## J-203 · P1 零渲染 preflight 通过并准入 formal

Date: 2026-08-28 · Type: PREREGISTERED PREFLIGHT · Formal Blender renders: 0

工具在 commit `646bfc8c4a11d0fc013b2860e41b3e705173f731` 冻结后运行一次 preflight。它反查 spec 最后修改 commit `a70676cae1794703915cb8dfc5b11a518e8a4f4c`，证明五个工具在预登记 commit 中都不存在，并逐个验证 working bytes 与 freeze commit blob 相同。

两个独立 Blender 5.2 PID 分别重建 ACES SDR 与 Un-tone-mapped cell，均为 zero-render probe。12/12 checks 通过：display round-trip、Material Index API、AOV add/remove 与 VALUE registration、Output AOV node、0–32767 material index range、7/7 shared Object Index、11/23 Material Index、0.25/0.75 AOV assignments 全部匹配。stderr 只有 Blender 6.0 预告性质的 `use_nodes` deprecation warning。

磁盘准入测得 `110300434432` available bytes；扣除 128 MiB projection 后为 `110166216704`，高于 100 GiB reserve。Formal root 在 preflight 前后都不存在。Preflight hash: `71c5de8fcf6d19e6022f366a19f37c7e6b928d5303773170d79210ec334302a7`; file SHA-256: `e2aa0b7e590e1c4cdbe7e4deb60fa9105dfcbd758db4a1f3ff8053d4bd9e250b`。

Artifact: `experiments/blender-owner-token-pass-probe-preflight-v0-1/preflight.json`.

## J-204 · P1 八次 render 成功，但冻结 analyzer 的正交投影错误

Date: 2026-08-28 · Type: RETAINED FORMAL ANALYSIS FAILURE · Real Blender renders: 8

八个 Blender 5.2 Cycles CPU source children 全部 exit zero，四个预期 EXR parts 都存在，data-pass arrays 在显示设置与净进程 repeats 间 byte exact。第九个 child analyzer 写出 8/9、24/24 的结果后 exit one；runner 因而保留 formal root 与 failure receipt，未启动 audit。

失败不是 pass 缺失，而是 analyzer 把 landscape orthographic `ortho_scale=8` 错当可见高度。Blender 的实际可见宽度为 8、高度为 `8×127/193`；raw Material Index 的真实前景 bbox 是 x `[43,131]`、y `[23,97]`，即 89×75 pixels，精确符合修正公式。错误 background mask 因此吞入 F0 的 3,100 个 Material Index 23 pixels 与 3,433 个 AOV 0.75 pixels。

第二个工具缺陷是 `projection_ok` 把“两个机制都 viable”写成 measurement consistency 条件，使任何单候选或负 verdict 都无法通过。原 result 的 `NO_TESTED_OWNER_TOKEN_PASS_VIABLE` 不可推广。下一步必须先提交整个失败 root，再以新 spec/tool/output 做只读机械修正；禁止重渲染或改变任何 gate。

Result SHA-256: `e5916494d80dca03b6ba039817c49ad42a4365e67473f7afdb0ef77c622ae903`; failure SHA-256: `e6b5f47cf46a61c36acff3ab0a8d3f55c0929e2fe3f43eb22273939f62696591`; failure hash: `45eb5d34ed973402b316eb52ed9b550de58b0d2d16739dd60a733a247625733b`。

Artifact: `research/2026-08-28-b52-d12-10-p1-formal-analysis-failure.md`.

## J-205 · P1-C1 冻结正交投影与 outcome-neutral validator 修正

Date: 2026-08-28 · Type: CORRECTION PREREGISTRATION · New Blender renders: 0

在三个 corrected tool paths 与 corrected root 全部不存在时，P1-C1 绑定原 spec、execution、invalid result、failure、invalid analyzer、failure note，并逐项冻结八份 source report/EXR SHA。允许的 measurement 修正只有 landscape camera 的 `worldWidth=orthoScale`、`worldHeight=orthoScale×height/width`；validator 则必须按原四标签映射核验任何结果，禁止要求特定候选通过。

C1 必须重新从同一八份 EXR 提取 24 个 float32 arrays，并同时与 raw parts 和失败 P1 已保存 arrays byte exact。三像素 margin、256 minimum、7/7、11/23、0.25/0.75、所有 mechanism gates、boundary/display/repeat measurements 均不可改变。新 runner 只允许一个 analyzer 和一个独立 audit process，Blender/model/network/render 全为零。

该修正已经看过失败数据，明确是 post-hoc，不得称为 fresh holdout。Spec SHA-256: `5805af301077a8b3ae18892e3c4c2c5a2ad646a7e8b3cdddd762c39d22293a77`。

Artifact: `specs/blender-owner-token-pass-probe-c1.v0.1.json`.

## J-206 · Material Index 与 Value AOV 均可传 owner token，但边界语义不同

Date: 2026-08-28 · Type: CORRECTED POST-HOC PASS RESULT · New Blender renders: 0

P1-C1 runner 在 freeze commit `07eba7d` 后创建 fresh correction root；analyzer 与独立 audit 两个新 PID 均 exit zero。结果 12/12、28/28，audit 14/14；24 个 corrected arrays 同时与 raw EXR 和失败 P1 arrays byte exact。正式 verdict 为 `MATERIAL_INDEX_AND_CUSTOM_AOV_OWNER_TOKENS_VIABLE`。

修正 mask 每 cell 有 background 16,816、foreground 5,727、boundary 1,968 pixels。八个 cell 的 stable interiors 全部 exact：Object Index 7/7，Material Index 11/23，Value AOV 0.25/0.75；三种 pass 都 display-invariant、clean-repeat byte exact。Object Index 按预登记不能区分 owners。

边界语义出现关键分叉：Material Index 在全部 1,968 个 boundary pixels 中只出现 11/23；Value AOV 在 F0/F1 分别有 658/652 个 mixed pixels、20 个 unique values，步长 0.015625，与 32 samples 对 0.5 token delta 的采样混合一致。因此第一条 fresh integration 候选优先 Material Index exact identity；AOV mixture 必须另行 typed-invalid 或作为 coverage evidence，不能直接当 categorical scalar key。

这仍是 post-hoc transport evidence。下一实验必须保持 H1 的 depth/alpha/vector/risk/coverage/quality gates 不变，只把 same-index ownership 换成 compiler-assigned Material Index，并证明原 15 个 accepted aliases 被消除且不产生新 false accepts。Result SHA-256: `3210641459a978e18cb2f71a2cd12b43e820edcd7bd4a1fe5d774e1f8179d3b0`; evidence hash: `8de2871e551de8bbac1a87080042ba577735c6068b0e1850effbdd03cf4f02a2`; audit hash: `8b35f791c9eb7dacb6fbb4327c266bdb33870b8c41d6f6d4a19e61005fc9a202`; receipt hash: `11895973dcff014e317ad70e141e2b248a1efeda4202afea9ccae01e85ae5cfb`。

Artifact: `research/2026-08-28-b52-d12-10-p1-c1-owner-token-pass-result.md`.

## J-207 · P1-C1 证据代理与研究页面固化

Date: 2026-08-28 · Type: PUBLICATION CHECKPOINT · New Blender renders: 0

从已接受 P1-C1 arrays 只读导出三张展示代理：共享 Object Index、离散 Material Index 与 filtered custom AOV。代理不作为新增测量，也不替代 EXR/NPY 原始证据；它们只把“无法区分、精确分类、边界混合”三种 pass 语义放进可审阅页面。Manifest SHA-256 为 `725893efcb13b72556b62f54dee3e4bd2c2ed5c3303a212433c1a7714536c003`，manifest hash 为 `b7746bfbd233a024f74854c2395f66f4d4ef9930e13852d57f7e0fa1a10e6650`。

新增 `/blender-owner-token-pass-v0-1/` 研究 tab，明确保留原 P1 analyzer failure、P1-C1 post-hoc 限制、Material Index 0–32767 范围与 shared-material duplication 约束。全仓 lint 为 0 errors；新增页面定向 lint 为 0 errors / 0 warnings，补丁 whitespace check 通过。下一恢复点不是继续润色页面，而是预登记 fresh Material Index ownership integration：保持 H1 的 depth/alpha/vector/Q30/coverage/quality gates 不变，目标是把已定位的 15 个 same-index accepted aliases 降为 0，且不得产生新 false accepts。

Artifacts: `public/evidence/b52-d12-10-p1-c1/manifest.json`; `app/blender-owner-token-pass-v0-1/page.tsx`.

## J-208 · D12.11-I1 Material Index owner integration 预登记

Date: 2026-08-28 · Type: PAIRED INTERVENTION PREREGISTRATION · New formal Blender renders: 0

D12.11-I1 被固定为配对的 post-hoc 因果干预，而不是新场景 holdout。它逐项继承 H1 的四个 fixture、两次 clean repeats、两帧、Cycles CPU、相机、几何、Object Index、Combined/Depth/Vector、投影 oracle、结构判定、Q30/Q24 算法、131072 inclusive threshold、quality/coverage/fallback/static gates；唯一语义变化是给八个 analytic owners 分配 shot-local Material Index 21101–21402，并让原 equality predicates 读取 Material Index。Object Index 继续输出并作为负对照，关键两 owner 仍共享 14555。

Primary endpoint 在看见任何新 tool/render 前绑定到 C1 已登记集合：SAME_INDEX_DEPTH_CROSSING 每 repeat 有 17 个 Object Index bilinear aliases，其中 15 个被 H1 接受。成功要求新的 accepted-outside-true-owner-bilinear 与 accepted-on-registered-15 都为 0；全八 cell 不得出现任何 H1 之外的新 accepted coordinate，analytic invalid-history false accepts 也必须为 0。Combined、Depth、Vector 与 Object Index canonical arrays 必须逐字节等于 H1，避免把结果归因于场景或 render 变化。覆盖率阈值没有放宽，alias 消失不能掩盖 coverage failure。

Formal matrix 预登记为 16 次新 Blender 5.2 Cycles CPU renders、74 个唯一 child processes、Python/Node dual consumers、typed envelopes、independent analyzer/audit 和至少 56 个 mutation attacks。Formal/preflight roots 与八个新工具路径在本条记录前均不存在；磁盘准入保留 100 GiB reserve。Spec SHA-256: `89dd3637ffe5af3544e8cd8aca8869eedd8b1a1867d41e08a354e5cd0c3b2a0e`。

Artifact: `specs/blender-material-index-owner-integration.v0.1.json`.

## J-209 · D12.11-I1 零渲染 preflight 准入

Date: 2026-08-28 · Type: PREREGISTERED PREFLIGHT · New formal Blender renders: 0

八个 formal tools 在 commit `402957afdcc23a595d08b1482b942f692ff17e17` 冻结；preflight 反查 spec commit `eac5af41f11aaf9f90b49c919c23d07f24a98b39`，证明当时八个路径全部不存在。11/11 checks 通过：parent/runtime/tool identity、formal root absence、100 GiB disk reserve、analyzer import independence、四个 fixture 的 factory-startup scene construction，以及 Python/Node synthetic branch identity。

四个 Blender 5.2 probes 均为 zero-render。它们保留 H1 Object Index `14111/14222`、`14333/14444`、critical `14555/14555`、`14666/14777`，同时实测 Material Index 分别为 `21101/21102`、`21201/21202`、`21301/21302`、`21401/21402`。Synthetic dual consumer payload byte exact，产生 9,870 accepted pixels并命中 1 个预定 risk-rejection branch。磁盘测得 projected write 后 `110121951232` bytes free，高于 `107374182400` reserve。

Preflight hash: `d4a8db392659b557fca6eea9842dbcf87a81be0814e03a3b643adb03ba998b3a`; file SHA-256: `c0c7da22ae0a6aa00c5deac0667d457f8b60b8f93771c5d372c910aca39e09ac`。

Artifact: `experiments/blender-material-index-owner-integration-preflight-v0-1/frozen-tool-preflight.json`.

## J-210 · Material Index 把登记 alias 从 15 降到 0，但语义攻击审计待补

Date: 2026-08-28 · Type: FORMAL RESULT WITH PROMOTION HOLD · Real Blender renders: 16

D12.11-I1 在 66.44 秒内完成 74/74 unique children：16 source renders、8 adapters、16 dual consumers、32 typed envelopes、analyzer 与 audit 全部 exit zero。Tool-produced verdict 为 `MATERIAL_INDEX_OWNER_INTERVENTION_SAFE_BUT_COVERAGE_NOT_SUPPORTED`，18/19；raw audit 9/9。

Primary endpoint 两次重复一致：critical fixture 的 H1 registered accepted-alias set 为 15，Material Index 接受其中 0；accepted-outside-true-owner-bilinear 为 0；全八 cell new accepted coordinates 为 0、false accepted invalid history 为 0。Combined/Depth/Vector/Object Index 与 H1 canonical arrays byte exact。Critical accepted 从 13,717 降至 13,003，`INVALID_OWNER` 从 0 变 4,187、`INVALID_DEPTH` 从 4,169 变 0；其他三个 fixtures 的 accepted counts 完全不变。Coverage 仍因 sweep 的 0.94558 cell ratio 与 0.94151 foreground retention 未过原门。

收尾审查发现 formal analyzer 的 56 mutation rows 只做 `mutationNonce` 后的 canonical-hash sensitivity，并未真的执行 spec 预登记的 channel swap、token reuse、alias bit flip 等语义攻击。因此原始 measurements 与独立 raw audit 保留有效，但 56/56 的广义攻击覆盖声明尚未证明，结果暂不 promotion。下一步是先绑定整个 immutable root，再预登记独立 no-render adversarial audit；不得修改或重跑本 root。

Result SHA-256: `3eaa1461a7fa8b9f74e3320e19e56efa1cde3e0ea05618c1e04239d082b88457`; evidence hash: `2cabaed16827e9d2c4a0baf2d02ee79ff20efb27f3d303045127a20a9e6acbac`; audit hash: `e1e49a0d06ebf3b3f46721f06d5857c105f1feee0127934a5ca57c234b054b12`; receipt hash: `843ce7bc952a211cafb49e2f8ba1580a614144070b079a72a9bcc398fd15065e`。

Artifact: `research/2026-08-28-b52-d12-11-i1-formal-result-and-attack-gap.md`.

## J-211 · D12.11-I1-A1 真实语义攻击审计预登记

Date: 2026-08-28 · Type: ADVERSARIAL AUDIT PREREGISTRATION · New Blender renders: 0

在新 audit tool 与 output root 均不存在时，I1-A1 绑定 formal commit `ec6305a7d125d4f857450b8c431ef379214f45bf`、root Git tree `d1d50c211d4a94321ef7c051e9b066ff700a36d8`、result/audit/execution/receipt 与 promotion-hold note。基线 validator 固定 19 个 raw/identity/semantic gates，并必须从 C1 truth 与 consumer masks 独立重算两次 `15→0`、全八 cell new accepted=0。

攻击 roster 精确冻结为 56 个实际 mutation：8 parent bytes、4 source reports、8 paired adapter bytes、2 owner-channel substitutions、4 token contract、4 Object Index controls、2 registered alias accepts、8 new accepted coordinates、4 fallback bytes、4 coverage-result edits、verdict/result/audit/receipt 各 1、2 Q30 threshold crossings、2 Vector sign flips。每个攻击都在隔离的 in-memory copy 上执行，必要时同步修复被攻击 artifact 的局部 self-hash，以避免所有测试退化成 hash-only；必须击中预登记的 named gate。`mutationNonce` 不被允许计数。

Audit 不导入原 analyzer/audit/consumer 或 Blender modules，不启动 Blender/render/model/network，并要求 formal Git tree 攻击前后不变。Spec SHA-256: `bc1f6c9e171d009bedd6041e53aa7e3580185e72897800efe5b06e1ed25cad22`。

Artifact: `specs/blender-material-index-owner-integration-adversarial-audit.v0.1.json`.

## J-212 · 56 个真实 mutation 全过，Material Index integration 解除 promotion hold

Date: 2026-08-28 · Type: ACCEPTED ADVERSARIAL AUDIT · New Blender renders: 0

I1-A1 独立 validator baseline 19/19、concrete attacks 56/56，正式 verdict `MATERIAL_INDEX_OWNER_INTERVENTION_ADVERSARIAL_AUDIT_ACCEPTED`。它从 raw H1 accepted、C1 true-owner 与 I1 consumer masks 重算两次 critical endpoint：registered H1 aliases 15，Material accepted aliases 0，new accepted vs H1 0，13,717→13,003。Formal Git tree 前后均为 `d1d50c211d4a94321ef7c051e9b066ff700a36d8`。

56 个攻击实际修改隔离副本，覆盖 parent/source/adapter、self-consistent channel substitution、token zero/reuse/out-of-range/swap、Object Index negative control、alias/new-accept injection、fallback、coverage、verdict/result/audit/receipt、Q30 threshold 与 Vector sign。必要的局部 report/self-hash 被同步修复后，semantic gates 仍全部拒绝；不再是 `mutationNonce` hash sensitivity。

因此 J-210 的 promotion hold 解除：在这组 paired H1 matrix 内，compiler-assigned Material Index 被接受为 frozen temporal candidate 的 owner identity input。结论仍为 bounded，因为 sweep coverage 0.94558 与 foreground retention 0.94151 未过原门；146/152 one-sided extra-stencil opportunities 仍是下一技术缺口。

Result SHA-256: `b38666b6a6ebc234b0f41311d376875f6d980404afcd6e1f4eaf9d710e78e22c`; adversarial audit hash: `a75ee65dbd3255c565ca2531a08f0d395248ea369a716f16c6952fcd275345f7`。

Artifact: `research/2026-08-28-b52-d12-11-i1-adversarial-audit-result.md`.

## Active goal experimental contract

This contract is part of the active BlenderFilmStudio goal and applies to every subsequent stage:

1. preregister the falsifiable question, variables, controls, thresholds and rejection conditions before creating the tested tool or output;
2. test with real Blender when the claim concerns Blender, and record the exact runtime, hardware-relevant environment, input identity, process identity and randomness controls;
3. retain failed runs, counterexamples, negative observations and boundary conditions instead of rewriting the history around the successful path;
4. label statements as measured fact, inference, subjective judgment or unknown, and never promote one category into another;
5. require a clean reproduction plus adversarial/attack tests before promoting an engineering result;
6. require independent human observers for subjective visual claims; developer pilots and synthetic fixtures remain interface/attack evidence only;
7. publish machine-readable artifacts, hashes, non-claims and the next unresolved boundary, except when delayed disclosure is itself required to preserve a preregistered blind experiment.

## J-213 · D12.11-I1 重启前证据代理检查点

Date: 2026-08-28 · Type: RECOVERABLE PUBLICATION CHECKPOINT · New Blender renders: 0

从已冻结的 D12.11-I1、H1 与 C1 arrays 只读导出四张最近邻放大的分类代理：共享 Object Index、分离 Material Index、干预前后 accepted delta，以及尚未解决的 sweep coverage boundary。导出器先通过 Blender 5.2 bundled Python syntax compilation，再成功生成 4/4 outputs；人工检查确认图像可读，且没有插值创造的新像素类别。

代理被明确标记为 `SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE`：颜色仅是解释性分类映射，不是 Blender 显示变换；图像不能替代绑定的 EXR/NPY 与正式审计。Manifest 重新绑定正式 result SHA `3eaa1461a7fa8b9f74e3320e19e56efa1cde3e0ea05618c1e04239d082b88457`、adversarial result SHA `b38666b6a6ebc234b0f41311d376875f6d980404afcd6e1f4eaf9d710e78e22c`，并记录 `15→0` aliases、13,717→13,003 accepted、146 support rejects 与 416 risk rejects。Manifest internal hash 为 `9333159908c8fa8573d662e4ea1b4d5fdaaab02295272529cf3d5bc07699fae9`，文件 SHA-256 为 `a593a9bf63c3c999331f537648ab46c163156b42dd6c13d52fa23d5d526268d9`。

本检查点为 Codex 升级重启而建立。恢复后的下一条确定路径是：新增 `/blender-material-index-owner-integration-v0-1/` tab，链接正式与 adversarial artifacts，执行 lint/build，然后同时发布 GitHub Pages 与 owner-only Sites。发布完成后，下一技术实验固定在 one-sided extra-stencil coverage gap（sweep 146、parallax 152），不得回头修改 D12.11-I1 的 frozen artifacts。

Artifacts: `scripts/export-b52-d12-11-i1-site-proxies.py`; `public/evidence/b52-d12-11-i1/manifest.json`.

## J-214 · D12.11-I1 研究页通过双构建门

Date: 2026-08-28 · Type: PUBLICATION VALIDATION · New Blender renders: 0

新增 `/blender-material-index-owner-integration-v0-1/` tab，将 `15→0` primary endpoint、四通道 byte-exact negative controls、四 fixture 配对矩阵、formal mutation gap、独立 56/56 semantic attacks，以及仍未通过的 coverage 门放在同一叙事链。四张 evidence proxies 均通过 Next Image 以原始分类像素的 nearest-neighbor 语义展示；页面明确标注它们不参与 verdict。

定向 ESLint 对新增页、D12.10 导航与首页导航为 0 errors / 0 warnings；全仓 ESLint 为 0 errors，保留 30 个历史 warnings。Vinext/Sites production build 成功并识别 78 条 routes；GitHub Pages 的 Next static build 成功生成 80/80 pages，新增 route 被确认 static。开发服务器对精确 route 返回 HTTP 200，未进行未请求的浏览器 DOM 或截图 QA。

下一恢复点是提交并推送这份 exact validated source，然后只在确认 Sites access 仍为 owner-only 后部署同一 commit；GitHub Pages 也必须等待对应 workflow 成功，不能以本地 build 代替公开可访问性证据。

Artifact: `app/blender-material-index-owner-integration-v0-1/page.tsx`.

## J-215 · D12.11-I1 双站点发布完成

Date: 2026-08-28 · Type: PUBLICATION COMPLETE · New Blender renders: 0

Validated source commit `fb30cafa5cb9c6774e84a09821c3b5f175e06c80` 已推送。GitHub Pages workflow `33152100294` completed/success；公开 D12.11 route 返回 HTTP 200。Sites 在发布前重新核验 access：current user role 为 owner、mode 为 custom、allowed account user 恰为 1、external visitors 为 0、workspace/tenant groups 均为空；随后从同一 commit 的本地成功 build 保存 version 71，并以 private deployment 成功发布。匿名 HTTP 请求返回 401，符合 owner-only 边界。

公开 route: `https://lovejzzz.github.io/BlenderFilmStudio/blender-material-index-owner-integration-v0-1/`。Owner-only route: `https://blender-film-studio-research.skylab.chatgpt.site/blender-material-index-owner-integration-v0-1/`。

## J-216 · D12.12-D1 one-sided curvature derivation 预登记

Date: 2026-08-28 · Type: POST-HOC CANDIDATE PREREGISTRATION · New Blender renders: 0

在四个新工具路径与输出 root 全部不存在时，D12.12-D1 绑定 D12.11 formal tree `d1d50c211d4a94321ef7c051e9b066ff700a36d8`、formal/adversarial result、C1 support localization、coverage diagnostic 与两份 frozen consumers。问题被限制为：能否只用 previous-frame Material Index、alpha、RGB 与已冻结的 Q30/Q24 输入，对 146 sweep / 152 parallax symmetric-stencil losses 建立 one-sided second-difference candidate。

候选族冻结为 inflation factors `1,2,4,8,16,32,64`。每个 bilinear row/column 若左右或上下 second difference 都可用则保持 D12.11 max；若只剩一侧则乘 factor；两侧都不可用必须拒绝。选择规则是通过全部门的最小 factor。门包括：Python/Node 全数组 byte exact、两次 repeat exact、full-stencil 路径与 D12.11 byte exact、factor risk 单调/accepted 集合嵌套、risk underbound=0、accepted maximum/RMSE 均不超过 `3.0517578125e-05`、false invalid accept=0、Material alias accept=0、两组 primary fixture 的 localized opportunity eligibility ≥80% 且 acceptance ≥50%、fallback exact，以及独立至少 64 个真实 semantic attacks。

这是 post-hoc derivation，预登记同时写死一条反成功叙事：即使 146 个 sweep support rejects 全部恢复，仍不足以单独达到原 97% cell gate，risk rejects 必须作为独立机制处理。D1 不启动 Blender/render/model/network；只有未来另行预登记的 D12.12-H1 才能测试泛化。Spec SHA-256: `f179b4cea6c8d3bc19b4cf2534055ef98b3fa8dac9954bfeae28bc2a237dd640`。

Artifact: `specs/blender-material-owner-one-sided-curvature-derivation.v0.1.json`.

## J-217 · D12.12-D1 四工具实现待冻结

Date: 2026-08-28 · Type: IMPLEMENTATION FREEZE CHECKPOINT · Formal outputs: 0

预登记 commit `9b327ea` 之后才创建四个工具：独立 scalar Python/Node consumers、带独立 analyzer mode 的 runner，以及不 import consumers/runner 的 NumPy auditor。两套 consumers 都从 D12.11 adapter 的 Material Index、Depth、Vector、previous RGB/alpha 与 H1 analytic projection 重算 structural/radius2/bilinear domains；C1 classification 只作为 measurement mask，不参与决定。

每个 consumer 一次处理七个 frozen factors，full symmetric stencil 不使用 factor，one-sided row/column 才应用 inflation。输出包含 control masks 与每 factor 的 eligible/unavailable/accepted/risk/reconstruction arrays。Runner 预定 16 consumer + 1 analyzer + 1 audit child processes；auditor 对 parent/adapter/raw decisions/risk/support/fallback/result/cross-language/repeat 执行 64 个真实 in-memory mutations，不允许 `mutationNonce` 计数。

四工具已分别通过 Blender 5.2 bundled Python syntax compilation 或 Node syntax check，补丁 whitespace check 通过；尚未创建 formal root，也没有运行任何 consumer。下一动作必须先把这些 exact bytes 提交为 tool-freeze commit，再允许 runner 创建第一份 D12.12 output。

## J-218 · D12.12-D1 one-sided curvature candidate 通过推导门，但未通过完整 sweep coverage 门

Date: 2026-08-28 · Type: POST-HOC DERIVATION ACCEPTED / FRESH HOLDOUT REQUIRED · New Blender renders: 0

在预登记 commit `9b327ea`、工具冻结 commit `c91869a` 之后，formal root commit `5eb87b6` 保留了 16 个独立 consumer、1 个 analyzer 与 1 个 independent audit 子进程的完整输出；所有进程唯一且退出码为 0，父 D12.11 formal tree 在实验前后均为 `d1d50c211d4a94321ef7c051e9b066ff700a36d8`。

冻结的七因子族 `[1,2,4,8,16,32,64]` 按机械规则选出最小通过者 **factor 1**。Analyzer 为 13/13，独立 audit baseline 为 21/21，64/64 个真实 semantic mutations 全部被命名门拒绝。Python/Node 全数组 byte exact、两次 repeat byte exact、full-symmetric-stencil 路径与 D12.11 byte exact；selected factor 的 measured risk underbound、false invalid-history accept、Material alias accept 与 static accepted delta 均为 0。

Rotated sweep 的 146 个 localized opportunities 中 146 个 eligible、136 个新增 accepted，coverage 从 `0.9455795488` 升至 `0.9587489106`；foreground-owner retention 从 `0.9415061296` 升至 `0.9502626970`。因此 owner gate 已过，但原 0.97 cell gate **仍未通过**。Camera parallax 的 152 个 opportunities 中 144 个新增 accepted，coverage 从 `0.9773526` 升至 `0.986723936`。全局 accepted RGB maximum 为 `3.0308961868286133e-05`，RMSE 为 `1.0527398680313309e-05`。

结论被限制为 post-hoc candidate：在 D12.11 已有 Blender 5.2 real-render arrays 上，symmetric 4×4 curvature support 对这两个边界族过于保守；但 factor 1 对任意 rendered function 并无数学上界保证，且 sweep 仍暴露独立 risk-rejection bottleneck。重启后的第一动作不是改写现有结果，而是先为 D12.12-H1 预登记全新的 Blender 5.2 holdout：冻结 factor 1，覆盖 left/right、top/bottom one-sided boundaries 与 neither-side negative control，再创建 source/render 工具；在此之前可先完成 source-bound evidence proxies 与研究网站 tab。

Result file SHA-256 / self-hash: `4c68f0fad380e0362b3913c0f08f009aa009a620d8e718520a73319edd4e98e2` / `eba522125663564ee3d1cb6cb53fe3d0207fd3b32aa35160dba6fc481da6a841`。Audit file SHA-256 / self-hash: `5418414190a1f945ecc7a2d6069bbf8139898630eb54b2cb325332cbfb544615` / `a33ddf28b4eed72f37938c0bb334c23a3149f92cbe69d1596b0e673ac454cef1`。Receipt file SHA-256 / self-hash: `29749a31ad573a0ef8226534da4deb601b772bb0681d4b0068b122613ab129c8` / `87ce924b6d4cc212b9a49e43475bdd4334564e6b1a2e42e67db9f689f33a7bd9`。

Artifact: `research/2026-08-28-b52-d12-12-d1-one-sided-curvature-derivation-result.md`.

## J-219 · D12.12-D1 source-bound 代理图与研究 tab 实现检查点

Date: 2026-08-28 · Type: RECOVERABLE PUBLICATION CHECKPOINT · New Blender renders: 0

新增只读导出器，将 D12.11 baseline accepted 与 D12.12-D1 的 radius-2、localized opportunity、factor-1 accepted 和 Q30 risk arrays 映射为两张最近邻分类图。导出器由 Blender 5.2 bundled Python 3.13 与 OpenImageIO 3.1.13.1 实际执行；sweep 图重算得到 radius 10,327、baseline accepted 9,765、candidate accepted 9,901、new accepted 136、remaining risk 426、opportunity rejected 10，parallax 图重算得到 15,366、15,018、15,162、144、204、8，均与 formal result 绑定数字一致。

两图人工检查可读：绿色为旧 accepted、黄色为新恢复、洋红为 remaining risk、红色为存在单侧机会但仍拒绝的反例。分类固定为 `SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE`，不充当 Blender display transform，也不替代 raw arrays 或未来 fresh holdout。Manifest internal hash 为 `37a8f49aa598fe234d48a84fecc33efee4a7a4efdb7009acc07695841915356c`，文件 SHA-256 为 `fa2bcfc4bc259305b77845cd66e046c559efe2d44e8dd1daaeadeb9a246fe929`；sweep / parallax PNG SHA-256 分别为 `47981400c60cb8b3786bbd0a0d8ed11c492cf2335fc42f407d3e58148acd0dc6` / `a4f1c8064260730ea6c42aa7d972966a929105f6475b3505a784e7daa7c0ef7d`。

新增 `/blender-material-owner-one-sided-curvature-v0-1/` tab，并把 D12.11、首页导航接入新的研究链。页面将 factor-1 局部恢复、七因子机械选择、13/13 analyzer、21/21 baseline audit、64/64 attacks 与 sweep 仍低于 0.97 的反例放在同一叙事中；明确标记 post-hoc candidate 不能进入 production compiler，D12.12-H1 必须另行预登记。此时尚未执行 lint/build 或发布，下一动作是先通过 React 定向检查与双构建门。

Artifacts: `scripts/export-b52-d12-12-d1-site-proxies.py`; `public/evidence/b52-d12-12-d1/manifest.json`; `app/blender-material-owner-one-sided-curvature-v0-1/page.tsx`.

## J-220 · D12.12-D1 研究 tab 通过 React 与双构建门

Date: 2026-08-28 · Type: PUBLICATION VALIDATION · New Blender renders: 0

本地开发服务器对精确 route `/blender-material-owner-one-sided-curvature-v0-1/` 成功编译并返回 HTTP 200，随后按 Sites 规则将同一 coherent preview 送入 Codex 面板；未执行未请求的浏览器 DOM、截图或交互 QA。React 定向检查覆盖新增页、D12.11 导航与首页导航，结果为 0 errors / 0 warnings；新增页保持 Server Component，静态数组在模块级，使用 Next Image，没有 client state、数据 waterfall 或不必要 bundle。

全仓 ESLint 为 0 errors / 31 warnings。30 个属于此前路径；第 31 个来自已冻结 D12.12 Node consumer 的 expression warning，不能为了 lint 数字改写实验工具字节。Vinext/Sites production build 成功，识别 79 条 routes 并包含 D12.12；GitHub Pages Next static build 成功生成 81/81 pages，并将新增 route 明确认定为 static。

下一动作是只提交本轮 exporter、代理图/manifest、研究页、CSS、两处导航与 J-219/J-220；不得包含 README 或三份用户未提交研究稿。推送后必须等待 GitHub Pages 对 exact commit 成功，并在 Sites 发布前重新核验 owner-only access。

## J-221 · D12.12-D1 双站点发布完成

Date: 2026-08-28 · Type: PUBLICATION COMPLETE · New Blender renders: 0

Validated source commit `5ebd3bfc449d4e3e798320fa9496cd4dc623c518` 已推送。GitHub Pages workflow `33154307777` completed/success 且绑定同一 head SHA；公开精确 route 返回 HTTP 200。Sites 发布前重新核验 current user 为 owner、access mode 为 custom、唯一 allowed account user 为当前 owner、external visitors 为 0、workspace/tenant groups 均为空；从 exact source commit 重建并保存 version 72 后完成 private deployment，匿名精确 route 返回 401。

公开 route: `https://lovejzzz.github.io/BlenderFilmStudio/blender-material-owner-one-sided-curvature-v0-1/`。Owner-only route: `https://blender-film-studio-research.skylab.chatgpt.site/blender-material-owner-one-sided-curvature-v0-1/`。

## J-222 · D12.12-H1 directional one-sided curvature 新鲜 holdout 预登记

Date: 2026-08-28 · Type: CONFIRMATORY HOLDOUT PREREGISTRATION · Formal tools/renders: 0

在新 spec、八个 formal/preflight 工具路径与两份输出 root 全部不存在时，D12.12-H1 冻结六个 unseen Blender 5.2 fixtures：四个单向 projective-expansion cells 分别测试 `LEFT_MISSING_RIGHT_AVAILABLE`、`RIGHT_MISSING_LEFT_AVAILABLE`、`TOP_MISSING_BOTTOM_AVAILABLE`、`BOTTOM_MISSING_TOP_AVAILABLE`；一个大角度刚体旋转 cell 要求 common bilinear Material support 存在但 horizontal 两侧 second difference 都不可用且 accepted=0；一个 static cell 要求 full-stencil byte identity 与 accepted delta=0。

六个 raster、相机、owner transforms、Generated emission 系数、共享 Object Index 负对照与 12 个 compiler-assigned Material Index tokens 全部写死。Factor 固定为 1，不允许搜索；D12.11 Material identity、Q30/Q24、131072 inclusive threshold、3.0517578125e-5 maximum/RMSE、exact fallback 与原 0.97 cell / 0.95 per-owner coverage denominators 保持不变。四个 primary directional fixture 每个至少需要 8 个严格方向 witnesses、1 个 accepted、≥50% directional acceptance；neither-side 至少需要 1 个 witness 且 accepted 必须为 0。

Formal matrix 冻结为 6 fixtures × 2 frames × 2 clean repeats = 24 个新 Cycles CPU renders，总计 110 个唯一 child processes；要求 source、adapter、Python/Node every-array、decision 与 repeats byte exact，并由不 import pipeline 的 auditor 执行至少 80 个真实 semantic attacks。即使全部通过，也只允许进入另行预登记的 nonplanar/lit holdout，不能进入 production compiler。

预登记时 observed free bytes 为 110,389,080,064；projected write 201,326,592 bytes 后仍高于冻结的 100 GiB reserve。Spec SHA-256: `b0defadbd120f77dfe81bfa16d9dfd4e3a4d4a15ad1c8ddd1176d21f2e13b648`。

Artifact: `specs/blender-material-owner-one-sided-curvature-holdout.v0.1.json`.

## J-223 · D12.12-H1 三工具可恢复实现检查点

Date: 2026-08-28 · Type: IMPLEMENTATION CHECKPOINT / NOT A FORMAL RESULT · New Blender renders: 0

预登记 commit `ff093a5` 之后才创建 Blender source、OpenImageIO adapter 与第一套 scalar Python consumer；三者以独立 checkpoint commit `21941f2d775b10666ea1ab1a0cfecaf6697ef4bb` 推送到 `main`。Blender 5.2 bundled Python 3.13 对三个文件的语法编译均通过；这只证明工具可被解释器加载，不证明场景、pass 语义、方向门或数值结论正确。

Source 已实现六个冻结 fixture 的 Cycles CPU 场景、Generated emission、Material/Object pass indices 与 probe-only 路径；adapter 已实现 multipart EXR roster、10 个数组、Material token domain 和共享 Object Index 负对照；Python consumer 已实现 analytic projection/visibility、symmetric 与 one-sided support、Q30 risk、exact fallback 和冻结的方向 control masks。文件 SHA-256 依次为 `352e4f30569e8966b01ac638e79f54e0ac1973da9fdbf065312230e8b0c78188`、`bf5b9e72c27d2c8fd5aedad0cdaea4a7fda077543123e4ff644f96c85e24ce99`、`42a654afc729e66db2627e48f7ff153048e21d06e29506501fe4484d5341db25`。

停止点被明确冻结：Node 独立 consumer、analyzer、independent auditor、preflight 和 110-process runner 尚未创建；formal/preflight output roots 尚未生成；24 个 Blender renders 尚未启动；因此 directional acceptance、coverage、risk underbound、RGB maximum/RMSE 与 holdout pass/fail 全部未知。重启后的第一动作是实现 Node consumer 并要求 every-array byte exact，随后才实现 analyzer/auditor/preflight/runner；八工具全部冻结并通过 zero-render preflight 之前，不得创建 formal root 或宣称 H1 通过。

## J-224 · D12.12-H1 八工具冻结

Date: 2026-08-28 · Type: FORMAL TOOL FREEZE · New Blender renders: 0

Commit `8a7dc9e02ec63f9b15f742d0213c0c6f7cdc8026` 将八个预登记 formal tool path 的最终状态冻结并推送。新增的独立 Node consumer 不调用 Python consumer；analyzer 第三次重算 analytic projection/visibility、结构域、四种方向、neither-side、Q30 risk、reason 与 reconstruction；auditor 不 import source/adapter/consumer/analyzer/runner，并准备 92 个隔离的真实 payload/semantic mutations；runner 固定 24 Blender + 12 adapter + 12 Python + 12 Node + 24 Python envelope + 24 Node envelope + 1 analyzer + 1 audit = 110 个子进程。

八工具 SHA-256（按 spec 顺序）为 `efdebaf2a6ba153bded03c2d28a5151ad196392952c2fde71e57a227d188e2ba`、`bf5b9e72c27d2c8fd5aedad0cdaea4a7fda077543123e4ff644f96c85e24ce99`、`42a654afc729e66db2627e48f7ff153048e21d06e29506501fe4484d5341db25`、`9fa6b68d6fabf0fbab3a341cc3c43e6422fe1ae14cb07106e43ad6682994f8fd`、`f519ef952b04385b5c9440067912a56c294d32a63b37412d3f3802b06d6e9954`、`086455e1ed0a156b1c2da2905a17413ebc91c7fe6261fd14cbae929f9168b1ad`、`a01b04134816973aa46d1525a764e7a23ccd499839b46c3c6c7047ab39237e41`、`8e1a5acb3712f07a7b6340c7e4e3d0f699cc4a966127be849c5913bd185e77e9`。固定 Blender Python 对七个 Python 工具的 syntax compile、固定 Node 对 `.mjs` 的 syntax check、六类合成方向分支和一个 Q30 算术例均通过；仍未创建 preflight/formal root，正式 holdout 结论继续保持未知。

## J-225 · D12.12-H1 zero-render preflight 通过

Date: 2026-08-28 · Type: PREFLIGHT ACCEPTED · New Blender renders: 0

在 tool-freeze commit `8a7dc9e02ec63f9b15f742d0213c0c6f7cdc8026` 后创建预登记 preflight root。六个 fixture 分别由真实 Blender 5.2 clean process 构造 frame 1 场景，逐一确认两位 owner、12 个 Material tokens 的 fixture 子集、每 fixture 共享 Object Index、Combined/Depth/Vector/Object Index/Material Index passes 与 probe-only operation count；没有执行 `bpy.ops.render`，root 内 EXR 文件数为 0。

14/14 checks 通过：spec/tools/runtimes/OCIO、parent bytes/两棵 formal Git trees、固定解释器 syntax、六场景 RNA、zero-render、六类合成方向与 Q30 示例、current-RGB decision isolation、disk reserve、formal-root absence、model/network zero。Preflight process count 为 8（2 syntax + 6 Blender probes），preflight hash `da081ce7def449eaa90b0df6f232fab6eb4b5d0705757b8820ae14b3b4817648`，receipt hash `f2c83ff907d5d35b20516c30859bae196a758882ac924dcb6e587733fa1c73e3`。此结果只授权启动冻结的 24-render formal matrix，不是 holdout measurement 或 candidate 通过声明。

## J-226 · D12.12-H1 证据链通过审计，factor-1 holdout 被拒绝

Date: 2026-08-28 · Type: CONFIRMATORY HOLDOUT REJECTED / AUDIT ACCEPTED · New Blender renders: 24

冻结 formal matrix 完整执行 110 个唯一 PID，全部退出 0；D12.11 与 D12.12-D1 parent trees 前后不变。Python/Node every-array、两次 adapter/consumer repeat、typed envelopes、第三 analyzer replay 全部 exact；独立 auditor baseline 21/21、concrete semantic attacks 93/93，最终 evidence receipt 有效。但 result verdict 为 `MATERIAL_OWNER_ONE_SIDED_CURVATURE_HOLDOUT_REJECTED`，不能提升 candidate。

三个独立反例：其一，neither fixture 的最坏 accepted RGB error `6.693601608276367e-05` 超过 `3.0517578125e-05`；对应 risk `125489 Q30` 正确上界实际误差但仍低于冻结 `131072` acceptance threshold，说明 threshold/quality policy 本身不闭合。其二，LEFT/RIGHT 分别形成 89/91 个 primary witnesses 并 100% accepted，但 TOP/BOTTOM 均为 0 witness，radius-2 域全部退化为 full stencil。其三，neither fixture 形成 0 个 neither-horizontal witness，而是在 region 中形成 297 个 right-missing cells。

Raw EXR repeat SHA 不同亦触发 hard gate；10 个 canonical pixel arrays 则全部 repeat byte exact。OpenImageIO metadata diff 将 container 差异定位为动态 `Date`、含 repeat 名称的 `Scene`，以及一个 frame 的 `RenderTime`。这要求未来把 pixel determinism 与 metadata-normalized container determinism 分层，不能事后放宽本次 raw-byte gate。

Result / audit / execution / receipt file SHA-256 分别为 `175c6c568b60b29332954c9bd3f24634c4028aaf8a5c221fd999ad01acc9c0a7` / `d983482d6d0d752e268273487592a42a7700b121c8769195d49001bb2742c4e1` / `babddc5c9849004c901d99d0c86f8b09d7d5696ad3b9149d5b5a5c99bcc6c935` / `9b692d8945821c2458a41952cc3cecde73066703d603455a484d9d4d8b7d9b14`；对应 self-hash 为 `c3c84f825b78ff4302fc6e65ff04956ac783a65dcc5ccf99fc1688bd5d15fdee` / `bc7e90af03a631c6ae799581ff3e84a855f149bab28e1ba59fc43c709e922ab4` / `0798b9edf859d9e5cc19a9b5b5190383737e272388cf716be5fca0ef63c747ee` / `55c122a7ecd748b07cf2803b4694ba05d77b1f0833d9c4295d2fbbdc4d5a6830`。

Artifact: `research/2026-08-28-b52-d12-12-h1-one-sided-curvature-holdout-result.md`.

## J-227 · D12.12-H1 rejection tab 与 source-bound 反例图通过构建门

Date: 2026-08-28 · Type: PUBLICATION VALIDATION · New Blender renders: 0

新增 `/blender-material-owner-one-sided-curvature-holdout-v0-1/`，首屏明确区分 `evidence receipt valid` 与 `candidate rejected`。页面将三类失败同时呈现：risk threshold 与 quality gate 的 4× policy gap、TOP/BOTTOM/NEITHER fixture 未形成目标 stress domain、raw EXR container metadata 不确定性；并保留 20/23 hard checks、24 renders、110 processes、21/21 audit baseline 与 93/93 attacks 等通过证据，避免把 reject 描述为坏实验。

只读 exporter 从已提交 R1 arrays 生成方向 2×2 matrix 与 neither quality counterexample 两张 nearest-neighbor 分类图。Manifest internal hash `f24511e8f2bd2ff80fcc7d067fcc8cd587f2f38222492c82c377b01ba11436fc`，文件 SHA-256 `4b706ef2840480be23a0e0921207babec234d5cb7e2dd8d43360e5a3da8c293f`；direction / quality PNG SHA-256 为 `08d78466e557df2ce2da976edd95d04d129f35d6a85b27d3a9f52eec3d7d75fd` / `40947278064494b4a45fcef44eeb9e1167430f935490048415354f720da82aa0`。分类固定为 `SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE`。

精确 local route 返回 HTTP 200；定向 ESLint 为 0/0，完整 lint 为 0 errors / 31 个既有 warnings。Vinext/Sites production build 成功并发现 80 个 warmup paths；GitHub Pages Next static build 成功生成 82/82 pages，并把新 route 明确认定为 static。没有执行未请求的截图、DOM 或交互 QA。下一动作是只提交 exporter、manifest/PNGs、新页、CSS、导航与本 journal entry，随后等待公开 Pages exact commit 成功，并在 owner-only Sites access 复核后发布同一 source commit。

## J-228 · D12.12-H1 rejection tab 双站点发布完成

Date: 2026-08-28 · Type: PUBLICATION COMPLETE · New Blender renders: 0

Validated source commit `8426ce43bb31c766da08adb910d00bea3d98340c` 已推送。GitHub Pages workflow `33157542705` completed/success，公开精确 route 返回 HTTP 200。Sites 发布前复核 current user 为 owner、access mode 为 custom、唯一 allowed account user 为当前 owner、external visitors 为 0、workspace/tenant groups 均为空；随后从 exact source commit 保存 version 73 并完成 private deployment，匿名精确 route 返回 401。

公开 route: `https://lovejzzz.github.io/BlenderFilmStudio/blender-material-owner-one-sided-curvature-holdout-v0-1/`。Owner-only route: `https://blender-film-studio-research.skylab.chatgpt.site/blender-material-owner-one-sided-curvature-holdout-v0-1/`。

## J-229 · D12.13-D1 quality-coupled threshold derivation 预登记

Date: 2026-08-28 · Type: POST-HOC DERIVATION PREREGISTRATION · New Blender renders: 0

在四个新工具路径与输出 root 均不存在时，冻结 `B52-D12.13-D1`。本实验只读取 D12.12-H1 已提交且不可变的 Blender 5.2 arrays，不启动 Blender render、模型或网络调用；它不能修改或推翻已经被拒绝的 H1，只用于导出或拒绝一个供未来 fresh holdout 检验的全局 threshold candidate。

预登记固定原始 `131072 Q30` 为诊断基线、`32768 Q30 = 3.0517578125e-5` 为精确 quality gate，并按 `[32768, 24576, 16384, 8192, 4096]` 的降序机械选择最大合格阈值。每个 candidate 必须同时满足零 risk underbound、accepted maximum/RMSE quality、0.97 primary cell coverage、0.95 per-Material-owner retention、static/repeat/cross-language exactness 与 fallback/current-RGB decision isolation；任一 coverage 或 safety gate 不通过就不能被导出。TOP/BOTTOM/NEITHER directional masks 仅 report，因为 H1 已证明这些 fixtures 没有形成预期 stress domain。

父 spec/result/audit/receipt 文件 SHA-256、H1 formal commit/tree、固定 Python/Node executable SHA 与版本已逐项复核；四个 tool paths 和 output root 仍不存在。预登记 spec SHA-256 为 `e9d79a2ec54acaf36a0df1168ea71102b0b94ab66f4e10f1cda56dbd1ea70c00`。重启后的下一动作是从此已推送 spec 实现两个独立 consumer、analyzer、mutation auditor 与 26-process runner；在 tool-freeze commit 之前不得创建 output root 或观察 threshold 结果。

## J-230 · D12.13-D1 四工具冻结

Date: 2026-08-28 · Type: FORMAL TOOL FREEZE · New Blender renders: 0

Commit `59945d9` 冻结并推送四个预登记工具：独立 Python consumer、独立 Node consumer、runner/第三 analyzer 与不 import 其余工具的 mutation auditor。Runner 固定 12 Python + 12 Node + 1 analyzer + 1 audit = 26 个唯一子进程；analyzer/auditor 在同一 immutable execution plan 中各自绑定真实 PID 后才允许产生 result/audit。所有路径保持 Blender render、model、network operation count 为 0。

四工具 SHA-256（按 spec 顺序）为 `b70c7e963788d41de9ff956df800ccf21ed7fb00fe81cd499600bee0e374b33a`、`4b642014ef63d6d4e6765f1e6bfbe8e53c0703a87d6ba01bf88a718f85e5645c`、`2b25adbecf346cc95a083d794c6a6743879f83105b7ab88f995588ab5f3e2952`、`4dbc1415f7b29ccdccef57dc282c2334a0c48ff6bc6f86e0eedcd9a2274740dd`。固定解释器 Python syntax、Node syntax 与 formal-root absence gate 通过。

一次性 `/tmp` smoke 对 LEFT/R1 的 2 个 shared arrays 和 5×2 threshold arrays 完成 12/12 Python/Node byte identity 后已清除。该预正式自检按冻结阈值得到 accepted counts `13668 / 11742 / 9482 / 6810 / 5333`；其中最大阈值 `32768 Q30` 的 13668/16892 retention 已明显低于 0.97 gate。这不是正式六-fixture结论，也不得据此修改阈值族或 coverage gate；下一动作仍是从 frozen commit 启动完整 26-process derivation，让“无 candidate”作为合法可证伪结果被审计。

## J-231 · D12.13-D1 证据链通过，global threshold candidate 未导出

Date: 2026-08-28 · Type: POST-HOC DERIVATION NOT DERIVED / AUDIT ACCEPTED · New Blender renders: 0

第一次 26-process run 的 analyzer hard checks 19/19 且已经给出 no-candidate，但 independent auditor 为 baseline 19/19、attacks 87/88，runner 因而拒绝创建 evidence receipt。失败并非 threshold 科学结果：`FALLBACK_FROM_H1` attack 在 fixture loop 后误用了最后一个 STATIC cell，其 current/reconstruction 按设计 byte identical，所以没有实际 mutation。完整 attempt 保存在 `experiments/blender-material-owner-quality-coupling-derivation-v0-1-attempt0-audit-tool-bug/`。Commit `bbc8192` 只把 witness 固定到非静态 LEFT/R1；没有改 threshold、gate、input、metric 或 verdict。

修复后从空 formal root 重跑：26/26 unique child processes exit 0，analyzer hard checks 19/19，auditor baseline 19/19、semantic attacks 88/88，receipt hash `984ed1922979face344d6d387a835bc565f5c69d9519c8c88d83f544e16703f2`。Python/Node every-array、repeat、fallback 与 H1 eligible/risk binding 均 exact；Blender render/model/network calls 仍为 0。Attempt 0 与 rerun 排除 process/tool identity 后的全部 candidate metrics/cells exact。

五档 threshold 均通过 safety/quality，但均失败 primary cell coverage 与 owner retention，因此 verdict 为 `MATERIAL_OWNER_QUALITY_COUPLED_THRESHOLD_CANDIDATE_NOT_DERIVED`。`32768 Q30` 的 accepted RGB max 仅 `7.510185241699219e-06`，但最低 cell coverage 只有 `0.6472908000648263`，最低 owner retention 只有 `0.5340755013202027`；更小阈值只继续恶化 coverage。结论：H1 risk upper bound 可保持安全，却对全局 quality-coupled acceptance 过于保守；只调一个 global threshold 无法同时满足 quality 与 coverage。

Result / audit / execution / receipt file SHA-256 为 `66a1598e2b4f0dee1ee7773b566c1bf5085a2a02fc911e050b873bdcfa28ca19` / `cc761d726c409d54cbf84faa07a7a600e35a2ab5d65e58dadee50fb9f6d0d988` / `206b69e5e2ba9d52d79b6dcd709a88f5c62a0683766173c970b4fd7dd0cf8009` / `a7448121ef15947edd2beed24f2222792672b43a06afcd67e7807b68d10c0caa`；对应 self-hash 为 `c0e43d0acac844939457f0fdec0b8eda7fa850d0fed26720b873401aa88a4737` / `fcbd74e2ae5b2dc62e226b24b58c45b2c5753c35aff1058829055f0445f6579a` / `8bca7f38c5907d9097691db443ab943bfc074b705b92405a40554226ebdd4545` / `984ed1922979face344d6d387a835bc565f5c69d9519c8c88d83f544e16703f2`。

Artifact: `research/2026-08-28-b52-d12-13-d1-quality-coupled-threshold-derivation-result.md`。下一动作是在不修改本结果的前提下，分别预登记 directional fixture calibration 与 risk-tightness decomposition；前者修复实验域，后者研究机制而非继续调 threshold。

## J-232 · D12.13-D1 no-candidate tab 通过双构建门

Date: 2026-08-28 · Type: PUBLICATION VALIDATION · New Blender renders: 0

新增 `/blender-material-owner-quality-coupling-derivation-v0-1/`。页面首屏把 `evidence receipt valid` 与 `zero candidate derived` 分开；threshold frontier 直接从已提交 `results.json` 构建五档 quality/cell-coverage/owner-retention 对照，不复制另一套手写 measurement source。四个 primary fixtures、NEITHER/STATIC controls、attempt0 87/88 failure、`bbc8192` scoped repair、formal rerun 88/88 与两个独立 next tracks 均被显式披露。

精确 local route 返回 HTTP 200；新页、首页与 H1 邻接页定向 ESLint 为 0 errors。Vinext/Sites production build 成功并发现 81 个 warmup paths；GitHub Pages static build 成功生成 83/83 pages，新 route 明确认定为 static。没有执行未请求的截图、DOM 或交互 QA。下一动作只提交新页、CSS、首页/H1 导航与本 journal entry，然后等待 GitHub Pages exact commit 成功，并在 owner-only Sites access 复核后发布相同 source commit。

## J-233 · D12.13-D1 no-candidate tab 双站点发布完成

Date: 2026-08-28 · Type: PUBLICATION COMPLETE · New Blender renders: 0

Validated source commit `b7370f639de43a5042c9bbcd65ee3154809e37e9` 已推送。首次 GitHub Pages workflow `33159699179` 因 sparse checkout 未包含页面直接导入的三份 experiment JSON 而失败；修复只把 `results.json`、`audit.json`、`execution.json` 加入部署 workflow 的精确 checkout allowlist，没有改写实验数据或页面判断。修复后的 workflow `33159797638` completed/success，公开精确 route 返回 HTTP 200。

Sites 发布前复核 current user 为 owner、access mode 为 custom、唯一 allowed account user 为当前 owner、external visitors 为 0、workspace/tenant groups 均为空；随后将 exact source commit 推送到受控 source repository，从成功的本地 build archive 保存 version 74，并完成 private deployment `appgdep_6a91568537448191824ad8018cfb477d`。匿名精确 route 返回 401，本地开发服务已关闭。

公开 route: `https://lovejzzz.github.io/BlenderFilmStudio/blender-material-owner-quality-coupling-derivation-v0-1/`。Owner-only route: `https://blender-film-studio-research.skylab.chatgpt.site/blender-material-owner-quality-coupling-derivation-v0-1/`。

重启后的下一条技术路径保持不变：先独立预登记 directional fixture calibration，以 zero-render analytic oracle 修复 TOP/BOTTOM/NEITHER stress-domain 构造；完成后再另行预登记 risk-tightness decomposition。不得继续在 D12.13-D1 已拒绝的 global-threshold family 内调参。

## J-234 · D12.14-C1 directional fixture calibration 预登记

Date: 2026-08-28 · Type: POST-FAILURE FIXTURE CALIBRATION PREREGISTRATION · New Blender renders: 0

在新 spec、五个 tool paths 与 formal root 均不存在时，冻结 `B52-D12.14-C1`。它只处理 D12.12-H1 已暴露的实验域缺口：TOP 的 17,325 个 radius-2 cells 与 BOTTOM 的 18,511 个 radius-2 cells 全部仍是 full stencil，目标 witnesses 都为 0；NEITHER 的目标 witnesses 为 0，却形成 565 个 global right-missing cells。该 calibration 明确为 post-hoc development work，不能修复 H1，也不读取 H1 RGB/depth/vector/risk/reconstruction arrays。

搜索域冻结为投影矩形上的两套独立 scalar raster oracle：TOP/BOTTOM 各 1,050 个候选，NEITHER 1,800 个候选。像素中心、edge inclusion、radius-2、bilinear floor、四类 outer taps、目标纯度、相邻 phase robustness 与机械 tie-break 全部写死。Python/Node 必须对 candidate roster、metrics、selected masks 逐字节一致；每个选中目标再由独立 Blender 5.2 factory-empty process 构造相机与双帧平面，只检查 world-to-camera 投影，不调用 render。总矩阵为 2 个 oracle + 3 个 Blender probes + 1 个 independent audit = 6 个唯一子进程，formal root 必须保持 0 EXR、0 render、0 model、0 network。

成功只允许导出三个供未来 fresh-render holdout 预登记使用的 fixture candidates；它不验证 factor 1，不触碰 D12.13-D1 no-candidate 结论，也不进入 production compiler。正式输出允许合法返回 `CANDIDATES_NOT_DERIVED`。预登记时可用空间为 110,202,679,296 bytes，冻结最大写入 67,108,864 bytes 后仍高于 100 GiB reserve。Spec SHA-256: `fd3fe2808346c49a87183b3ed215b07abcbaf4058df13d055cc893b482ae30f5`。

Artifact: `specs/blender-material-owner-directional-fixture-calibration.v0.1.json`。下一动作必须先提交并推送 exact spec；之后才允许实现五个工具，且 tool-freeze commit 之前不得创建 formal root。

## J-235 · D12.14-C1 在 formal root 前被 Blender 投影精度门证伪

Date: 2026-08-28 · Type: PREFORMAL DESIGN FALSIFICATION · New Blender renders: 0

预登记 commit `9b20091` 后实现两套独立 scalar oracle 与一个 Blender projection probe prototype。`/tmp` smoke 中 Python/Node 对 3,900-row candidate table 和 selected masks byte exact，临时选择 TOP/BOTTOM 各 109 个纯 target witnesses、NEITHER 4,071 个纯 target witnesses；candidate table SHA-256 为 `97920657e2c1c4663dfe04866bcc93a1ba9f6a1eb91740561cb7cebba5908ff9`。这些是未冻结工具的 preformal observations，不能成为正式 calibration 结果或未来 holdout 输入。

三次真实 Blender 5.2 factory-empty、zero-render probes 均拒绝原 `1e-9 pixel` hard gate：TOP/BOTTOM/NEITHER 的 Blender maximum absolute projection errors 分别为 `5.7220458984375e-6`、`5.781650543212891e-6`、`5.0067901611328125e-6`；对应独立 scalar errors 仅约 `7.1e-15–1.4e-14`。Render Result 均不存在，EXR count、render/model/network calls 均为 0，临时目录随后清除。

另一个设计缺口也在 tool freeze 前被识别：NEITHER 的 `58.5366×` 投影尺度差尚未证明能由同一尺寸刚体平面的双帧 transforms 实现；当前 probe 只是分别反解两个矩形。因而原 spec 必须保留而不能事后放宽，formal root 不得创建。下一步应使用新 experiment ID 预登记 world-space rigid-realizability calibration，直接冻结 owner size、camera/owner transforms、Euler rotations、3D ray-plane oracle 与基于本次已披露量化观察的新容差。

Artifact: `research/2026-08-28-b52-d12-14-c1-directional-calibration-preregistered-gate-falsification.md`。

## J-236 · D12.14-C2 world-space rigid directional calibration 预登记

Date: 2026-08-28 · Type: PILOT-INFORMED RIGID FIXTURE CALIBRATION PREREGISTRATION · New Blender renders: 0

在 C2 spec、五个新 tool paths 与 formal root 全部不存在时，先用不落盘的 scalar pilot 检查 world-space 可行域，再冻结 `B52-D12.14-C2`。与已失效的 C1 不同，C2 每个候选只允许一个固定 local mesh：foreground 尺寸恒为 `[8,7]`、scale 恒为 `[1,1,1]`，两帧只能改变 location 与 XYZ Euler rotation。背景同样为固定刚体平面；foreground/background 继续共享 Object Index，owner domain 仅由 Material/analytic token 区分。

已披露 pilot 找到三个同一刚体平面可行例：TOP 187、BOTTOM 189、NEITHER 12,192 个 target witnesses，non-target one-sided 均为 0；TOP/BOTTOM 分别对相邻 Y displacement 保持 target，NEITHER 对 previous Z `-1/0/+1` 保持 12,192。真实 Blender 5.2 zero-render corner pilot 的最大 scalar-vs-Blender error 为 `1.2781884947798972e-5 pixel`，所以新 spec 在观察之后、正式工具之前把 hard tolerance 冻结为精确 `1/32768 = 3.0517578125e-5 pixel`。这不是 pixel identity，也不得在 formal run 后继续放宽。

正式搜索共 500 个 world-space candidates：TOP/BOTTOM 各 180，NEITHER 140。Python/Node 必须独立实现 binary64 Euler XYZ、ray-plane nearest visibility、current-local → previous-world reprojection、previous owner raster、radius-2、bilinear floor 与 directional outer taps，并对 candidate metrics/selected masks byte exact。三个选中 target 各由独立 Blender factory-empty process 复核同一 mesh datablock、恒定 scale、RNA transforms 与 corner projection；加上 independent audit，总计 6 个唯一子进程，render/EXR/model/network 必须全为 0。

这是 pilot-informed calibration，不是 blind holdout。即使 derived，也只授权另行预登记 fresh-render test；不能修复 D12.12-H1、改变 D12.13-D1 或进入 compiler。Spec SHA-256: `e123b80fdba40c7e7e396e1aad149573e1e123c57198a21fa8af944320d7e4c3`。

Artifact: `specs/blender-material-owner-rigid-directional-calibration.v0.1.json`。下一动作必须先提交并推送 exact spec，然后才实现五个 C2 tools；formal root 在 tool-freeze commit 前必须不存在。

## J-237 · D12.14-C2 五工具待冻结检查点

Date: 2026-08-28 · Type: FORMAL TOOL IMPLEMENTATION CHECKPOINT · New Blender renders: 0

预登记 commit `d1f4d9a` 之后才创建五个 C2 tool paths：Blender rigid probe、独立 scalar Python/Node 3D oracles、independent auditor 与 six-process runner。两套 oracle 都从 world-space camera rays 开始，独立执行前景/背景 bounded ray-plane nearest visibility、current local point 到 previous rigid transform、previous owner raster、radius-2、bilinear floor 与五类 directional masks；不 import 旧 C1 prototype 或彼此实现。

`/tmp` smoke 对冻结的 500 candidates 达到 candidate table 与 selected masks byte exact，table SHA-256 为 `d92fc7a9ec26ce0186f0879c209d715d2281d5d715e1171b7cefbb1d48a7ba5f`。两者机械选择相同三项：`TOP-000153`（target/neighborhood 187，non-target 0）、`BOTTOM-000069`（189/189，0）、`NEITHER-000113`（15,113/15,113，0）。三次真实 Blender 5.2 factory-empty probe 均保持同一 foreground mesh datablock、local-vertex hash 与 `[1,1,1]` scale；maximum projection errors 分别为 `1.0908596152603423e-5`、`1.2781884947798972e-5`、`5.573793135482674e-6 pixel`，均低于预登记 `3.0517578125e-5`。NEITHER RNA rotation error为 `3.003596038553269e-9`，world-corner error为 `5.4045198982777265e-8`；其余两项为 0。Render Result、EXR、render/model/network calls 均为 0，临时目录已清除。

五工具 SHA-256（按 spec 顺序）为 `b98150ec8dbd85acf3076af427e8656039651dd93ab62ab0ea9af429e75c9b39`、`43693be502e89ed35d9083798a086590643fde3ae354e7a352fb4b767b503e04`、`2344c46247f650c1ea3f4640c85dd98acd4dc5fe7199c49ffa680e7d5ab48dff`、`d745e5e00d81733bf55bdd1725a3f075cab65c0b766417953aa5b27a75421eda`、`35b7351bb0313fbcd80d496ea71b61842a87457dba9a91d64301ac03e0ef95c5`。固定 Python/Node syntax checks 通过；formal root 仍不存在。下一动作必须将这些 exact bytes 与本 journal entry 提交为 tool-freeze commit，随后 runner 才可创建正式输出。

## J-238 · D12.14-C2 刚体方向夹具候选正式导出

Date: 2026-08-28 · Type: PILOT-INFORMED CALIBRATION DERIVED / AUDIT ACCEPTED · New Blender renders: 0

Tool-freeze commit `afd94d51bf085e10290f846d05903e92281dc3c2` 后，formal runner 完成 6/6 unique child processes：Python/Node 3D oracles、三个 Blender probes 与 independent auditor 全部 exit 0。Runner evidence 8/8、audit baseline 18/18、concrete semantic attacks 64/64，receipt valid；H1 formal tree 前后保持 `de1ac6a394a3963a158d0e3432d5dfb89aaf9a87`。正式 root 仅 2.1 MiB，EXR/render/model/network 均为 0。

机械选择为 `TOP-000153`、`BOTTOM-000069`、`NEITHER-000113`。TOP/BOTTOM target 与 robustness minima 分别为 187/187、189/189，NEITHER 为 15,113/15,113；三者 non-target one-sided 均为 0。Blender 真实 RNA probe 证明每个候选在两帧复用同一 `[8,7]` mesh datablock，scale 恒为 `[1,1,1]`；projection error 全部低于预冻结 `1/32768 pixel`。Verdict 为 `MATERIAL_OWNER_RIGID_DIRECTIONAL_CALIBRATION_CANDIDATES_DERIVED`。

Result / audit / execution / receipt file SHA-256 为 `005d4338ccd0c7e791b3279517b3a3c1f7590eb20739f997d94f4358bcd79f96` / `0e4c0f514ed469ed09c6582d4f2369339dfaa4b653dfcd3d1fc18fd1be8f38f5` / `86870d88fe65422bfbcda6cd49c07afb2f78ef39f279626b1db3ca34fa8b76b3` / `373706abc369cb3a09017cb88a1d6de51de8ea314f0c0999ed9c1aed27f669d4`；对应 self-hash 为 `7f6270a24d4c57218034401a9821aac1e39e649324ad33ac2b1d9e0c4a1bde8f` / `6a1c20d463cc4148677101eeffb7350f6c0aeb6e13c6dfc9f5332a4577604fd8` / `04b82b594a68813e52fd10917486fd5a6af0c2e09aba502a17d65d4e9996f925` / `e2a6cc139972ee9120ed70edc3b79df7b8378ae26badcb145409aabcf474d4c7`。

该结果只解决 world-space rigid fixture realizability，不验证 factor 1 或 Blender passes。下一动作是提交 formal root 与 result note，然后为 fresh rendered holdout 另行预登记新 rasters/tokens/signals/output；不能直接复用 calibration cells 充当 confirmatory evidence。

Artifact: `research/2026-08-28-b52-d12-14-c2-rigid-directional-calibration-result.md`。

## J-239 · Codex 升级重启前的 D12.14-C2 网站发布检查点

Date: 2026-08-28 · Type: RESTART-SAFE PUBLICATION CHECKPOINT · New Blender renders: 0

D12.14-C2 的正式实验已经完整保存在 `main` 与远端 commit `2ab40ad`：500 个 world-space candidates、6 个唯一子进程、runner 8/8、audit baseline 18/18、semantic attacks 64/64、receipt valid。当前没有 Blender、Vinext/Next 或临时 HTTP 服务进程；重启不会中断实验或遗留渲染任务。

尚未发布的站点工作被隔离到 checkpoint 分支 `codex/d12-14-c2-site-publication`。已完成内容包括：从正式 result masks 机械导出的 2×3 source-bound domain matrix、带资产哈希的 manifest、可重放导出器，以及 `/blender-material-owner-rigid-directional-calibration-v0-1/` 页面主体。PNG SHA-256 为 `5a1d12e39178922344cc268c41ef352cab542d3afca2948c8fa3cf4100e6e9d7`；manifest internal hash 为 `2af904965f56cddebb04cd5044887bda24aa9929bc46955f29f829a8c217b669`。该图只作 `SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE`，不能替代 fresh rendered holdout。

重启后的精确续接顺序：先补 D12.14-C2 scoped CSS；再把新 route 接入首页与 D12.13 邻接导航；再将新页面直接 import 的 `results.json`、`audit.json`、`execution.json` 加入 GitHub Pages sparse checkout；随后执行 exporter replay、定向 ESLint、Vinext production build 与 GitHub static build。所有验证通过后才允许合入 `main`、等待公开 exact route HTTP 200，并将同一 source commit 发布到 owner-only Sites。最后另行预登记 fresh Blender render holdout；不得把 calibration masks 当作 confirmatory denominator。

用户原有未提交内容 `README.md` 与三份 2026-08-26 Physis/Remainder Room research drafts 均未纳入 checkpoint，也未被改写。

## J-240 · D12.14-C2 页面完成并通过双构建验证

Date: 2026-08-28 · Type: PUBLICATION VALIDATION · New Blender renders: 0

Checkpoint 恢复后完成 `/blender-material-owner-rigid-directional-calibration-v0-1/` 的 scoped CSS、首页入口、D12.13 邻接导航与 GitHub Pages 精确 sparse-checkout 输入。页面从已提交的 `results.json`、`audit.json` 与 `execution.json` 直接构建候选、probe 和 evidence-chain 数值；不复制一套独立 measurement source。内容明确区分 C1 preformal falsification、C2 pilot-informed calibration、真实 Blender 5.2 zero-render realizability 与尚未执行的 fresh rendered holdout。

站点 proxy 重放首先暴露一个可复现性缺口：PNG 已 byte exact，但 exporter 把临时输出目录写入 manifest 的 `outputs[].uri`，导致相同证据在不同目录产生不同 manifest hash。修复将该字段固定为公开逻辑 URI，不改变任何像素、source URI、source hash 或分类；随后从新临时目录重放得到 PNG SHA-256 `5a1d12e39178922344cc268c41ef352cab542d3afca2948c8fa3cf4100e6e9d7` 与 manifest SHA-256 `35906b4956eaf08ac7f7a15aa8f44a2436e856de4c168632b9af5181f8aef92a`，两者均与 checkpoint 资产逐字节一致，manifest internal hash 仍为 `2af904965f56cddebb04cd5044887bda24aa9929bc46955f29f829a8c217b669`。

新页、首页和 D12.13 页定向 ESLint 为 0 errors；导出器在 Blender 5.2 bundled Python 下 syntax check 通过；精确 local route 返回 HTTP 200。Vinext/Sites production build 成功并发现 82 个 CDN warmup paths；GitHub Pages static build 成功生成 84/84 pages，新 route 被确认 static。按发布规范未执行未请求的截图、DOM、点击或视觉 QA。下一动作是把 exact validated source 合入 `main`，等待公开 Pages exact route 成功，再将同一 source commit 发布到经复核仍为 owner-only 的 Sites。

## J-241 · D12.14-C2 刚体校准页双站点发布完成

Date: 2026-08-28 · Type: PUBLICATION COMPLETE · New Blender renders: 0

Validated source commit `9ed2e59733d4fd1a5f34c3cba45e98cf59300b5e` 已 fast-forward 合入并推送 `main`。GitHub Pages workflow `33164288341` 的 build 与 deploy jobs 均 completed/success，公开精确 route 返回 HTTP 200。

Sites 发布前再次复核 current user role 为 owner、access mode 为 custom、唯一 allowed account user 为当前 owner、external visitors 为 0、workspace/tenant groups 均为空。随后将同一 source commit 推送到受控 source repository，以成功的本地 Vinext build archive 保存 version 75，并完成 private deployment `appgdep_6a91666a1540819193f8b13c3f7271ca`。匿名访问精确 route 返回 HTTP 401；本地开发服务与临时 archive 均已关闭或清除。

公开 route: `https://lovejzzz.github.io/BlenderFilmStudio/blender-material-owner-rigid-directional-calibration-v0-1/`。Owner-only route: `https://blender-film-studio-research.skylab.chatgpt.site/blender-material-owner-rigid-directional-calibration-v0-1/`。

下一阶段不再修改 calibration 结论。必须使用新 experiment ID 预登记 fresh Blender render holdout：固定 C2 导出的三条 world transforms，但重新冻结 Material/Object tokens、Generated/Vector/Depth signals、EXR outputs、两次 clean repeats 与 quality/directional/fallback gates；calibration masks 只能用于 fixture construction，不能充当 confirmatory denominator。

## J-242 · D12.14-H1 fresh rigid directional render holdout 预登记

Date: 2026-08-28 · Type: PILOT-INFORMED RENDERED HOLDOUT PREREGISTRATION · New Blender renders: 0

在新 spec、八个 H1 tool paths、preflight root 与 formal root 均不存在时，冻结 `B52-D12.14-H1`。该实验只继承 C2 的三条刚体 world transforms；新 raster、Material/Object tokens、mesh tessellation、Generated emission coefficients、render seed、EXR paths 与全部真实 passes 均在 C2 之后冻结。正式矩阵为 3 fixtures × 2 frames × 2 clean repeats = 12 个 factory-empty Cycles CPU renders，加 adapter、Python/Node consumers、typed envelopes、analyzer 与 independent audit，总计 56 个唯一子进程。

预登记前的 zero-render raster-phase pilot 暴露了新的结构反例：把 C2 三个 raster 直接改为 `[199,133]`、`[201,135]`、`[203,137]` 后，TOP/BOTTOM/NEITHER 目标 witnesses 全部变为 0。随后在每个 C2 宽高的 ±8、step 2 网格上做未落盘探索，确认目标域对 width phase 敏感而对已选择 width 下的 height 更稳定。冻结的新 raster 为 TOP `[193,135]`（189 target，15,876 bilinear，15,687 full）、BOTTOM `[193,137]`（189 target，22,302 bilinear，22,113 full）与 NEITHER `[197,139]`（16,065 target/bilinear，0 full）；三者 non-target one-sided 均为 0。该 pilot 只观察解析结构域，没有构造新材质、调用 Blender、读取 passes 或计算 risk/acceptance/quality，明确不是 confirmatory measurement。

正式判定继续使用 D12.12-H1 的 factor 1、Q30/Q24、inclusive threshold 131,072、2⁻¹⁵ quality 与 exact fallback；TOP/BOTTOM 每个 repeat 至少 128 个 formal pass-derived eligible cells、至少 1 accepted 且 acceptance ≥ 50%，NEITHER 每个 repeat 至少 1,024 witnesses 且 accepted 必须为 0。任何 pilot mask 都禁止成为 source、adapter、consumer、analyzer 或 auditor 输入。即使全部通过，也只支持这三个 fresh opaque rigid-planar emission fixtures；D12.13-D1 的 global coverage rejection 仍阻止 compiler promotion。

预登记时 free bytes 为 109,606,830,080；冻结最大写入 134,217,728 bytes 后余量 109,472,612,352，仍高于 100 GiB reserve。Spec static audit 通过：3 fixtures、56-process sum、12-render matrix、唯一 Material tokens、shared Object Index negative controls、full-frame regions、parent tree identity 与 runtime executable hashes全部一致。Spec SHA-256: `7ff239d91dca6ea8708ce4cac955dd0b129ae067028a77ec1699a43a236195a8`。

Artifact: `specs/blender-material-owner-rigid-directional-render-holdout.v0.1.json`。下一动作必须先提交并推送 exact spec；随后才允许实现八个工具。Formal root 在 tool-freeze commit 之前必须不存在。

## J-243 · Codex 升级重启前的 D12.14-H1 工具实现检查点

Date: 2026-08-28 · Type: RESTART-SAFE IMPLEMENTATION CHECKPOINT · New Blender renders: 0

预登记 commit `33692d211a37f6db98ddb3def4e91a4e5cd07547` 已在远端 `main`；其后才创建八个全新 H1 tool paths。当前实现已完成从旧 holdout 工具的结构化分叉、D12.14-H1 schema/path 替换，以及 `effective_fixture` 归一化层：它把 spec 的全局 camera、background owner 与 foreground owner 几何配置机械展开为每个 fixture 的 frame-local 输入，供 Blender source、Python/Node consumers 与 analyzer 读取。7 个 Python 文件通过 `py_compile`，Node consumer 通过 `node --check`。

这是非冻结 WIP，不是 formal tool-freeze，也不是实验结果。已知尚未完成项包括：把四个 runner/analyzer/auditor/preflight 中的 parent tree 键改为 `rigidCalibrationFormalRoot` 与 `rejectedRenderedHoldoutFormalRoot`；把 runner 的 pre-audit child count 从旧矩阵改为 55（加 audit 后总计 56）；把 analyzer/auditor 从旧 coverage/static verdict 改为 TOP/BOTTOM directional + NEITHER zero-acceptance 语义；让零 accepted 样本的 quality gate 保持 vacuous safety，以便正确映射 `directionFailureVerdict`；增加固定 local mesh hash 与 `[1,1,1]` scale 的显式证明；最后才可做 `/tmp` source smoke、工具 hash 冻结、提交并推送 tool-freeze commit。

本检查点不得创建 preflight/formal roots，不得运行正式 Cycles render，也不得据此宣称 D12.14-H1 支持或拒绝。重启后的精确续接入口是先完成上述静态适配，再重复语法检查与临时 source probe；只有 exact tool bytes 提交后才能运行 preflight，preflight 通过后才允许创建 formal root。用户原有 `README.md` 与三份 2026-08-26 Physis/Remainder Room research drafts 继续保持未纳入、未改写。

## J-244 · D12.14-H1 八工具冻结前真实 Blender zero-render 验证

Date: 2026-08-28 · Type: FORMAL TOOL-FREEZE CANDIDATE · New Blender renders: 0

在预登记 commit `33692d211a37f6db98ddb3def4e91a4e5cd07547` 与非冻结恢复检查点 `be2a501c7f54c8050dec87fd76499e99a0de3b05` 之后，完成 H1 八工具的 spec-specific 适配。Parent tree 绑定改为 C2 rigid calibration 与被拒绝的 D12.12-H1 formal roots；runner 冻结为 55 个 pre-audit children、加 audit 后 56 个唯一进程；analyzer/auditor 删除旧 coverage/static verdict，改为 TOP、BOTTOM 与 NEITHER witness 的 direction-only mapping，同时把任何 NEITHER acceptance 保持为 hard rejection。零 accepted 样本的 RGB safety 使用空集上的 vacuous pass，因此不会把纯方向失败错误映射成 safety rejection。

静态审计还识别并修正一个更关键的旧实验复制残留：正式 consumer/analyzer 的 Vector 与 current Depth oracle 现在使用 spec 已冻结的绝对 `1/16384` 容差，而不是旧代码的相对 `/1024` 或更宽 Vector 容差；previous-depth bilinear structural gate 仍严格保留预登记的 `max(1,predictedDepth)/1024`。Analyzer 另增加一次真实 replay：只把 current RGB 三通道改为常数、保持 alpha/所有 pass 不变，并要求全部 control 与除 reconstructed fallback 外的 decision arrays byte identical。固定 mesh gate现在显式记录并核对 local-vertex hash、mesh data name、顶点/面数、scale `[1,1,1]`、两帧声明 transform 与三帧 LINEAR action。

在 `/tmp` 中运行三次独立 Blender 5.2.0 LTS factory-empty source probes；TOP/BOTTOM/NEITHER 全部 exit 0，Material/Object/Vector/Depth/Combined passes 注册正确，foreground scale 均为 `[1,1,1]`，三帧 action 与 effective fixture exact，Render Result 与正式 EXR 均未创建，`blenderRenderCalls=0`。Foreground local-vertex hashes 分别为 `a893e2a5bf6dfa0d1b55027301f2e38a5915132a34bd8e85b54c2586051270fc`、`adc8bc7af08b454cac384dae10d69928f61e71996fe630491f6ed0d60e1ef2cd`、`ae1737191a854ba2f246e42a09fd0f9d8d6d9ceffeb38a434ff54c7bdee81a3c`。7 个 Python tools 通过 `py_compile`，Node consumer 通过 `node --check`；preflight 与 formal roots 仍不存在。

按 spec 顺序，待冻结的八个 tool SHA-256 为：`9ba86e95e8d24c2592690c575cd87749433a1af00a7d2c18ace3e2153daf36ce`、`1ae9316c0448006bc7696f60778a23154f70791d9bf7059dac3592f4cdac856e`、`7bae8c665df9d904369fe7774204c42024a2b15c3a4b615bd7e8d28ab8238c40`、`ec43f68c9d893051e8ead149bf29c6c29f57e9963e7aa5f3174ae8d91fdd4378`、`144ac0360205cedf719cf570f1f022887e4b4e551bbc415a4a62809c406c3705`、`6b9d6dd864e1671cd4c49bb70e3369917259c1555d1b529aaeaa93d9798d0671`、`42ddde68468ec6b8652ecafdecf785a54bf52e2e21be4d24eaa98b44476789b0`、`9b5503143d132ac9f9deca807c33fd611434dee6c901f122a82a98e49855f0d1`。下一动作必须提交并推送这些 exact bytes 与本 entry，形成 tool-freeze commit；随后才可运行 official zero-render preflight。

## J-245 · D12.14-H1 official zero-render preflight 全门通过

Date: 2026-08-28 · Type: FORMAL PREFLIGHT ACCEPTED · New Blender renders: 0

Tool-freeze commit `7488f0a` 推送后、formal root 仍不存在时，使用冻结的 Blender bundled Python 启动 official preflight。5/5 child processes exit 0：两项 Python/Node syntax checks 与三项 Blender 5.2 factory-empty scene probes。Preflight 14/14 gates 全部通过，包括 spec/tool/runtime/environment identities、所有 parent bytes、C2 与 D12.12-H1 formal Git trees、三套场景构造、pass registration、固定 local mesh/scale/三帧 action、synthetic direction/Q arithmetic、current-RGB source isolation、disk reserve、formal-root absence，以及 render/model/network 零调用。

正式运行前观察 free bytes 为 109,609,832,448；冻结 required-before-formal 为 107,508,400,128，headroom 2,101,432,320 bytes。Preflight root 140 KiB；`preflight.json` file SHA-256 / self-hash 为 `38e1e2d1783994bf9d1b7ec4e53a1f81de639080f8f38e47d340b74a8a219e4d` / `b14c2bcd207caeb1d023e2c8431fe72b237dafcc92973cb8d0659fa67ca7ddd4`；`receipt.json` file SHA-256 / self-hash 为 `615a7cad4af09fc2180f1d6c96238cb984efaeb2e4f09d4542e7f1a951e6bdb7` / `bb4da865f29bca8b7933a818264e9e3fe8f36cd05dd9cd23630fc7fbcc29c398`。三个 probe report self-hash 均由独立 canonical replay 验证。

该 preflight 只证明正式运行已被准入，不能预测 H1 科学 verdict。下一动作是先提交并推送 exact preflight evidence，再让冻结 runner 一次性创建 fresh formal root；若任一真实 render、adapter、consumer、analyzer 或 auditor gate 失败，应保留失败输出并报告，不得修改工具后重跑同一 experiment ID。

## J-246 · D12.14-H1 正式运行被冻结 analyzer 缺口中止

Date: 2026-08-28 · Type: FORMAL RUN INVALIDATED / FROZEN TOOL FAILURE · New Blender renders: 12

Passing preflight commit `5c6bacad87c9db72078ef4b7497d2da5bd929081` 后，runner 一次性创建 fresh formal root。前 54 个 children 全部成功：12 个 Blender 5.2 Cycles CPU renders、6 adapters、Python/Node 各 6 consumers、Python/Node 各 12 typed envelopes。第 55 个 analyzer 以 `KeyError: 'subdivisions'` 中止；冻结 analyzer 的 `effective_fixture` 没有像 source/preflight/auditor 那样为 background owner 展开全局 subdivisions，却在新增 mesh gate 中直接读取该键。Audit 未启动，results/execution/receipt 均未产生。因此 H1 没有科学 verdict，合法状态只能是 `FORMAL_RUN_INVALIDATED_BY_FROZEN_ANALYZER_FAILURE`；修复后不得用相同 experiment ID 重跑。

失败后的只读取证确认 12 source reports/EXR bindings、6 adapter reports、12 consumer reports self-hash 有效；Python/Node every array、repeat adapter arrays、repeat consumer arrays与 24 envelope pairs均 byte exact。EXR containers 的 repeat bytes 不同，但 decoded pass arrays exact；OpenImageIO diff 把已观察的 Combined metadata 差异定位为 `Date`、`RenderTime` 与按 repeat 命名的 `Scene`，其余四个 subimages无 metadata 差异。冻结 analyzer 把 container SHA 当成 source-pass repeat identity，故该 gate 即使绕过当前异常也会失败。

非决定性取证得到：TOP 每次 189/189 accepted、quality max `2.4020671844482422e-5`；BOTTOM 每次 189/189、quality max `1.9103288650512695e-5`；两者 risk-underbound RGB samples 为 0。NEITHER 每次 accepted 0，但正式 witnesses 仅 270，低于冻结 minimum 1,024。它们只能指导新 ID 的 pilot-informed 设计，不能补造 H1 verdict。

Machine failure self-hash: `6629e437b37bb4c7b10be22967a57f978830d515d680cac173c7d912b8ddaef3`。Artifact: `research/2026-08-28-b52-d12-14-h1-rendered-holdout-frozen-tool-failure.md`。下一步是提交并推送完整 partial root 与 failure record，再预登记新 experiment ID；新 spec 必须包含 analyzer-on-probe schema smoke、canonical decoded-pass repeat identity、fresh signal/tokens/output，以及 runner failure receipt finally-path。

## J-247 · D12.14-H1 失败证据树已封存并推送

Date: 2026-08-28 · Type: FAILURE EVIDENCE PRESERVATION COMPLETE · New Blender renders: 0

完整 partial root、machine-readable failure record、研究说明与 J-246 已在 commit `6dec6a3ede714d56fcddc39dd9841ada0c8de827` 推送到远端 `main`。Formal partial-root Git tree 为 `7c29757a99d197a56641dde70338d1a73e6441aa`；`failure.json` file SHA-256 为 `8a5caef198ee65ac35a932f26d2a74604fff833ce978407c1a6526132fa6f953`，内部 self-hash 为 `6629e437b37bb4c7b10be22967a57f978830d515d680cac173c7d912b8ddaef3`；研究说明 file SHA-256 为 `11c67946936d26661a4c214d6bb5e3025c560011dc7933e624c4f4c09fc666ce`。

H1 至此封闭，不再修改或重跑。下一阶段必须使用新 ID，把 270-witness NEITHER 观察和 EXR metadata variation 当作已披露 pilot inputs，先寻找仍满足 1,024 witness minimum 的 fresh raster/transform；在新 spec 提交前不得创建修复工具或新 formal root。

## J-248 · D12.14-H1 工具失败研究页双站点发布与重启检查点

Date: 2026-08-28 · Type: PUBLICATION COMPLETE / RESTART-SAFE CHECKPOINT · New Blender renders: 0

H1 页面以 `NO SCIENTIFIC VERDICT` 为首要结论，公开呈现 12 次真实 Blender 5.2 Cycles renders、54 个成功 children、第 55 个冻结 analyzer 的 `KeyError: 'subdivisions'`、未启动 audit，以及 repeat EXR container bytes 与 decoded pass arrays 的不同身份语义。页面没有把 TOP/BOTTOM 的非决定性数值或 NEITHER 的 zero acceptance 冒充正式 verdict；它明确说明相同 experiment ID 不得修复后重跑。

站点 source commit `72f779fde27d3e22eddbbdd7378c24ec165fdd70` 已推送。新页、C2 邻接页与首页定向 ESLint 为 0 errors；Vinext/Sites production build 成功并发现 83 个 CDN warmup paths；GitHub Pages static build 成功生成 85/85 pages。GitHub Pages workflow `33166896578` 的 build 与 deploy 均 completed/success，公开首页与精确 H1 route 均返回 HTTP 200。

Sites 发布前复核 current user role 为 owner、access mode 为 custom、唯一 allowed account 为当前 owner、external visitors 为 0、workspace/tenant groups 均为空。同一 source commit 被保存为 Sites version 76；archive content hash 为 `sha256:4d6c944f9ad88d91d4536f34f37f28ba35eefc93aaeafe3fb628ffbd21c4a950`，deployment `appgdep_6a917012b9d881919e4cc6cde1e80fac` succeeded。匿名访问 owner-only 精确 route 返回 HTTP 401。按发布规范未执行未请求的截图、DOM、点击或视觉 QA。

公开 route: `https://lovejzzz.github.io/BlenderFilmStudio/blender-material-owner-rigid-directional-render-holdout-v0-1/`。Owner-only route: `https://blender-film-studio-research.skylab.chatgpt.site/blender-material-owner-rigid-directional-render-holdout-v0-1/`。

重启后的精确续接顺序已经冻结为：先对 H1 partial arrays 做只读取证，分解 NEITHER 270 witnesses 的 reason-code、owner、Vector、current Depth 与 previous-support 损失；再用全新实验 ID 预登记 H2。H2 至少增加 analyzer-on-probe-shaped-report schema smoke、canonical decoded-pass digest、容许且单独报告的 container metadata 差异、可在 child failure 时仍写 immutable failure execution/receipt 的 finally-path，并选择真实 pass pilot 支持至少 1,024 个 NEITHER witnesses 的 fresh raster/transform。新 spec 提交前不得创建 H2 tool bytes、output root 或 formal render。之后才返回主目标 SceneSpec → immutable BuildPlan → Blender 5.2 compiler 的 B01/B02 净构建复现。

用户原有未提交内容 `README.md` 与三份 2026-08-26 Physis/Remainder Room research drafts 均未纳入本检查点，也未被改写。

## J-249 · D12.14-H1 NEITHER 失效机理定位与 P1 Position oracle 预登记

Date: 2026-08-28 · Type: POSTFAILURE READ-ONLY DIAGNOSTIC / DEVELOPMENT PREREGISTRATION · New Blender renders: 0

从 J-248 精确恢复后，只读取证分解 H1 consumer arrays。NEITHER 的 reason chain 为：27,383 registered，16,819 same-owner bilinear support，16,541 `INVALID_DEPTH`，278 structural-valid，270 radius-2，270 `SUPPORT_UNAVAILABLE`，0 eligible/accepted。TOP 与 BOTTOM 没有 depth failure。因此 270-witness 缺口不是 risk candidate 或 raster-domain 本身造成，而是 edge-on previous plane 的 Z interpolation contract。

对 16,819 个 same-owner supports，直接 `bilinear(Z)` 相对 transform-predicted previous depth 的绝对误差 median/max 为 `0.3819589931877907` / `0.4652322060410441`；解析 tap depths 自身也重现同一数量级，rendered taps 与解析 taps 的最大差仅 `0.0035654820740553816`，排除了 Blender Depth pass 大幅失真。改为 `1 / bilinear(1 / Z)` 后 median/max 降至 `2.75397720024273e-5` / `1.884176535824622e-4`；全部 16,819 supports 通过原 relative-depth gate，随后精确恢复 16,065 radius-2 与 16,065 NEITHER witnesses，等于 H1 的 disclosed zero-render pilot。该结果是新算法设计输入，不是 H1 verdict。

另一个独立缺口是 pixel-center Vector oracle：TOP/BOTTOM/NEITHER observed max 分别为 `2.0807439631198577e-4`、`1.52587890625e-4` 与 `5.771591031589196e-4` pixel，均超过冻结 `1/16384`。本机 build hash 对应的官方 Blender commit `fbe6228777e7d9afefcd61a413844e790ae75db7` 源码显示 Position、Depth 与 Vector 同源于 first-hit `ShaderData.sd->P`，Vector 再经过 previous object 与 raster projection；因此 integer pixel center 不是同一物理样本。

在 P1 spec、三条新工具路径与 output root 全部确认不存在时，预登记 `B52-D12.14-P1`。它将用同一 H1 development-only fixture 做两次新的 Blender 5.2 current-frame render，只增加 Position pass，并以 Position world point 重建 current/previous raster endpoints。P1 只验证 H2 instrument design；该 fixture、结果与 H1 EXR 均禁止成为 H2 formal measurement input。P1 spec SHA-256 为 `2ccffbcfe861fd80406901b417cf4cd2b2b8977c6925d6fb73e3d0328092efe3`。下一动作必须先提交推送 exact P1 spec/protocol；随后才允许创建 P1 tools，工具冻结提交后才允许渲染。

## J-250 · D12.14-P1 三工具冻结候选与零渲染验证

Date: 2026-08-28 · Type: DEVELOPMENT TOOL-FREEZE CANDIDATE · New Blender renders: 0

P1 preregistration commit `15a4f19` 已推送后才创建三条新工具。Source 通过 import identity 复用冻结 H1 scene construction，只改 scene/view-layer development identity并启用 Position pass；它仍执行 factory-empty Cycles CPU、H1 88° rigid fixture、frame 1、sample 1 与原 seed。Analyzer 从 decoded Position world XYZ 反解 current local point、施加 previous rigid transform并分别投影 current/previous raster endpoints；integer pixel-center oracle仅作为失败对照，禁止成为新 gate。Analyzer 还检查六个 multipart subimages、float channel roster、Position→Depth、zero next Vector、两次 decoded-array identity 与仅 `Date`/`RenderTime`/`Scene` 可变化的 container metadata。

Runner 冻结为两个 source children 加一个 analyzer child；在任何 child failure 上也会写 `execution.json`、`failure.json` 与 `receipt.json`，避免 H1 runner 没有 finally-path 的证据缺口。运行前另有 100 GiB reserve safety gate 和 32 MiB maximum projected write；该 gate 只保护主机，不改变 P1 development outcome。

真实 Blender 5.2 factory-startup 加载 source 的 `--help` 路径成功，确认 `bpy`、frozen H1 import 与 argparse 可加载；两个 bundled-Python tools 的 `--help` 成功；三文件均通过 bundled Python 3.13 `py_compile`，P1 output root 保持不存在，render calls 为 0。按 source/analyzer/runner 顺序的 SHA-256 为 `9e1d338608306cfc89ed2111560ed88e46b860549505e084388e4150a7b3def2`、`6cf55af97af37dfe4e94e048246a3796b1a143760c0077fd6f343ea5fcb8b302`、`9e607fb8d8c33bedbf572e3a9d764eaffb08a48f40e7c161ce64e2bcbd58441f`。下一动作必须提交推送 exact tool bytes；只有该 tool-freeze commit 在远端后才能创建 P1 output root并运行两次新 render。

## J-251 · D12.14-P1 Position oracle development supported

Date: 2026-08-28 · Type: REAL BLENDER DEVELOPMENT RESULT · New Blender renders: 2

Tool-freeze commit `0a7ed9b` 推送后，runner 一次性创建 fresh P1 root。两个 Blender 5.2 Cycles CPU source children 与 analyzer child 全部 exit 0；14/14 development gates 成立。27,383 个 foreground Position pixels全部 finite且 token exact，Position-derived current Depth max error 为 0，next Vector max magnitude为 0。

旧 integer pixel-center oracle 的 Vector max error 为 `5.771591031589196e-4 px`；Position 投影显示真实 first-hit current raster 相对 integer center 在 X/Y 均有约 `5.07e-4`–`5.56e-4 px` 偏移。改用同一个 Position world point 计算 current/previous endpoints 后，Vector error median/p99/max 为 `7.949904869519742e-6` / `2.4902754290678786e-5` / `3.281015233369544e-5 px`，通过冻结 `1/16384` gate。该开发结果支持 Position 作为 H2 control oracle，不支持 Position 进入 reconstruction decisions。

两次 EXR container bytes不同，但 Combined、Depth、Position、Vector、Object Index 与 Material Index decoded arrays全部 byte exact；metadata differences精确限制在 Combined 的 `Date`、`RenderTime`、`Scene`。因此 H2 repeat identity 应冻结为 decoded-pass digest，container与 allowlisted metadata另行报告。

独立 posthoc evidence check 的 19/19 项通过，包括 results/execution/receipt 与两份 source report self-hash、EXR bindings、artifact/log hashes、3/3 children和实际 operation counts。与此同时保留一个工具覆盖缺口：P1 analyzer 的 `OPERATION_BOUNDARY` 是常量 true，而不是内部 replay；独立检查证明观察值，但不是 preregistered gate。H2 必须把 source/runner counts replay 写进 analyzer 与 audit。Result file/self hashes为 `69edb9ad3db3c67b5b21ad3b3a4c9e0ab59e05e29d38a60a34ce9ae04457b9fa` / `c3d8b7226872702d3947320ed19dbeed80b19704adf9432dbc2505e4abcd534e`；receipt self-hash为 `4b805e0f513100b836867c017cab1fa07cf8101a9c8b4fd75fef68b9871e40e8`。

P1 至此封闭，不修改或重跑。下一步先提交并推送 exact evidence root、posthoc audit 和 result note；然后把 P1 与 H1 inverse-depth 诊断发布到研究网站，再预登记 fresh H2。

## J-252 · D12.14 投影修复研究页完成本地验证

Date: 2026-08-28 · Type: WEBSITE SOURCE VALIDATED / RESTART CHECKPOINT · New Blender renders: 0

新增研究页 `blender-projective-depth-position-oracle-v0-1`，把 H1 失败后的两条独立算法缺口明确分开：previous-depth gate 不能对 perspective depth 直接做 `bilinear(Z)`，已观察的同 owner support 应改为 `1 / bilinear(1 / Z)`；Vector control oracle 不能假定 integer pixel center，必须使用 Position pass 记录的同一 first-hit world point。页面直接读取 P1 frozen `results.json` 与独立 `audit.posthoc.json`，公开 P1 的 27,383 foreground Position pixels、Position-derived current Depth exact、Position-based Vector max `3.281015233369544e-5 px`、六组 decoded pass arrays repeat exact，以及 EXR container metadata variation 的严格边界。

首页新增 `D12.14-P1 投影修复` tab；H1 页面新增到 P1 的证据链链接和 H2 约束；GitHub Pages sparse checkout 显式加入 P1 results/audit 两份机器证据。新页、H1 页与首页定向 ESLint 为 0 errors；Vinext/Sites production build 成功并发现 84 个 CDN warmup paths；GitHub Pages static build 成功生成 86/86 pages。localhost 上首页、H1 和 P1 route 均返回 HTTP 200。P1 页 metadata 的 title、description 与 canonical 已核对；详情页显式清除继承的 Open Graph/X 图片，同时保留全站既有 `public/og.png`，没有伪造与实验无关的图像。

按站点验证边界，本阶段没有执行用户未请求的截图、DOM、点击或视觉 QA。下一动作是只提交并推送站点源文件、本 journal 与 Pages workflow；必须继续排除用户原有 `README.md` 和三份 2026-08-26 research drafts。重启后先确认该 source commit 与 GitHub Pages workflow，再完成 owner-only Sites 发布；之后以全新 ID 预登记 H2，把 inverse-depth、Position oracle、decoded-pass identity、probe-shaped analyzer smoke、operation-count replay 和 failure receipt 写成可执行 gate。

## J-253 · D12.14-P1 投影修复研究页双站点发布完成

Date: 2026-08-28 · Type: PUBLICATION COMPLETE · New Blender renders: 0

重启后从 source commit `3546985d0d1996e317084b3cb2db105529cb9051` 精确恢复。GitHub Pages workflow `33168944260` 的 build 与 deploy 均 completed/success；公开 P1 route 返回 HTTP 200。相同 commit 被推送到 Sites source repository，重新执行 production build后保存为 version 77；archive content hash 为 `sha256:e233b0072f4e13d1ba6139e966889242684370ec6ee15f78581e1f96e82f1757`，deployment `appgdep_6a91778f8ea88191b130401a3c72319f` succeeded。

Sites 发布前再次验证 current user role 为 owner、access mode 为 custom、唯一 allowed account 为 owner、external visitors 为 0、workspace/tenant groups 为空。Owner-only P1 exact route 的匿名请求返回 HTTP 401；没有改变站点共享边界。公开 route 为 `https://lovejzzz.github.io/BlenderFilmStudio/blender-projective-depth-position-oracle-v0-1/`；owner-only route 为 `https://blender-film-studio-research.skylab.chatgpt.site/blender-projective-depth-position-oracle-v0-1/`。

P1 publication 至此封闭。下一动作转入 fresh H2 preregistration：先冻结 hypothesis、fresh fixture、inverse-depth algorithm、Position-only control oracle、decoded-pass repeat identity、probe-shaped analyzer smoke、actual operation-count replay、minimum witness 与 failure-receipt semantics；spec commit 推送之前不得创建 H2 tools 或 formal output root。

## J-254 · D12.14-H2 projective-depth formal holdout 预登记

Date: 2026-08-28 · Type: FORMAL PREREGISTRATION · New Blender renders: 0

在八条 H2 tool paths、preflight root 与 formal root 全部确认不存在时，预登记 `B52-D12.14-H2`。该实验使用 C2 candidate table 中此前未选中、从未渲染的 `NEITHER-000060` trajectory；新 raster 为 `201x137`，并冻结新的 foreground/background tessellation、Material/Object tokens、Generated emission、view layer 与 render seed。H1/P1 的 EXR、decoded arrays 与 masks 永久禁止成为 H2 measurement inputs。

预登记前唯一新增 construction evidence 是一次 unsaved Blender-bundled Python scalar pilot：它只调用 frozen C2 analytic raster functions，在 16 个新 raster sizes 上检查 structural masks；没有 Blender process、render、EXR、model 或 network call。冻结 raster 的 analytic current-radius2 / bilinear-support / NEITHER / full-stencil counts 为 `26,201 / 13,034 / 13,034 / 0`。这些值只建立目标 domain，不预测 Cycles Depth、Position、Vector、tokens、RGB、repeat identity 或 verdict。

H2 把两条修正严格分离。consumer decision只允许 Combined RGBA、Depth、Material Index 与 Vector XY；正式 depth gate使用 `1 / bilinear(1/Z)`，而 `bilinear(Z)` 只是 paired control。Position、Vector ZW、Object Index 与 analytic truth写入独立 control directory，只允许 analyzer/auditor验证 actual first-hit Depth/Vector，不得进入 Python/Node decisions。每个 repeat必须至少有 1,024 个 inverse-depth-valid cells、1,024 个 direct-Z-fail/inverse-pass rescued cells与1,024个 NEITHER witnesses；NEITHER accepted必须为0，fallback必须 exact。

预登记同时冻结 decoded-pass repeat identity、仅 `Date`/`RenderTime`/`Scene` 的 container metadata allowlist、Python/Node every-array identity、current-RGB decision metamorphism、64项独立 semantic attacks、4次正式 Cycles renders、analyzer probe-shaped schema smoke、analyzer/audit actual operation-count replay，以及 runner child failure finally-path 的 execution/failure/receipt。任何 tool/execution failure都只能产生 `scientificVerdict=null`，不得修复后用相同 ID重跑。

Spec SHA-256 为 `2961f621b38f934cffaa7abe36deaaa5e01e7505d6361985039d0380578d244b`；protocol SHA-256 为 `6b87d3c26d1fe7ec93664076a893fe6d50bd0de32df331dbf1fd5b97d10767fe`。下一动作必须只提交并推送 spec、protocol 与本 entry；该 preregistration commit在远端之前不得创建任何 H2 tool byte。

## J-255 · D12.14-H2-C1 consumer predicted-depth 语义更正

Date: 2026-08-28 · Type: PRE-TOOL SPECIFICATION CORRECTION · New Blender renders: 0

H2 preregistration commit `c4321835dcc4acb225d398e645efa46f99030fb1` 推送后、八条 H2 tool paths 与两个 output roots仍全部不存在时，审读识别出一个执行歧义：parent spec正确禁止 Position进入 consumer decisions，也把 Position-predicted depth指定为 analysis control，却没有命名 consumer执行 depth gate时允许使用的 predicted previous depth来源。若不先更正，Python/Node可能各自选择不同隐式 oracle，或错误读取 Position。

更正 `B52-D12.14-H2-C1` 冻结两条独立路径。consumer只用 integer cell、decoded current Depth、exact Material token和 frozen camera/owner transforms，重建 pixel-center current world point并预测 previous depth；Position仍不传给 consumer。analyzer独立从 decoded Position first-hit计算 control predicted depth与 Vector。正式 rescued witness必须同时属于 consumer rescued set并通过 Position-derived reciprocal-depth gate；冻结的1,024 minimum施加于该 intersection。consumer-only cells单独报告并排除，不能被用于提高 verdict。

C1不改变 trajectory、raster、signal、tokens、formula、relative tolerance、minimum witnesses、zero acceptance、Position tolerance、repeat identity、render/process counts、attack minimum或 verdict mapping。Correction SHA-256 为 `9b6fdcedd571ad1ec7fb8d02bc7c6a630014d204de02f4a8b74bf5509c625a92`。所有 H2 tools必须同时要求 parent spec与C1 correction并拒绝任一 identity mismatch。下一动作仍是先提交推送 exact correction与本 entry；远端 commit形成之前不得创建工具。

## J-256 · D12.14-H2 八工具冻结候选与零渲染验证

Date: 2026-08-28 · Type: FORMAL TOOL-FREEZE CANDIDATE · New Blender renders: 0

C1 correction commit `a5abc64` 推送后才创建八条 H2 tools。Source从 factory-empty scene构造新 mesh/material/action/camera并注册 Combined、Depth、Position、Vector、Object Index、Material Index；adapter把 Position/Vector ZW/Object Index写入 control directory，把 consumers允许的 RGBA/Depth/Material/Vector XY写入独立 decision directory。Python/Node consumers只接收 basename为 `decision` 的目录，独立执行 pixel-center current-Depth unprojection、direct-Z control、reciprocal-depth decision、radius-2、NEITHER/unavailable与exact fallback。Analyzer从 Position first-hit独立计算 previous depth/Vector，并把 consumer rescued set与Position gate取intersection；它还实现consumer replay与current-RGB metamorphism。Auditor直接重开四个raw multipart EXRs并执行64项一字段semantic attacks。Runner冻结20-child formal roster与任何child failure的finally evidence path。

7个Python tools通过Blender-bundled Python 3.13 `py_compile`，Node consumer通过Node 26 `--check`；Blender source、analyzer与runner的CLI加载成功。一个完全synthetic、非H1/P1的201x137 static background decision set被Python/Node consumers处理；两者所有output files byte exact，counts均为27,200 bilinear/direct/inverse、26,201 radius-2、0 rescued、0 accepted。Analyzer probe-shaped schema smoke与runner forced pre-render failure probe均通过独立self-hash replay。另一次真实Blender 5.2 factory-startup scene probe构造两个新meshes，foreground/background分别为5,025/5,859 vertices与4,884/5,704 polygons；Position pass注册、201x137 raster、scale `[1,1,1]`、0 render calls、0 EXR全部成立。

按source、adapter、Python consumer、Node consumer、analyzer、auditor、preflight、runner顺序的SHA-256为：`c12e637352f8c6b8fbf6aad6c56b9264884a95087c33d2229af61d0c908262b5`、`65ecb58e2bbf8b569f9e82b72d21995cd5892a888787e68d6129c3a1a6ebbae7`、`507253e5b3f7778736a4fc3c765267ea82ee7afd6efe350b6a9afaa417b6f009`、`73b3127d9cf08e8220520a6fd93481b2879ee0bdb86419833b18a03025b02ef3`、`c246b35d4c68af4d6556f3ac1b6298ef9e329637ea33b72248501898e623fc7a`、`6b180be8cc623c615ef667df70d3d40cb56741fd1c2c2de801fe245a06bc5e3c`、`03ec5b996332ee976ca96a783f12ce09f3f65ec83a85deebf31c9fc81fef522d`、`9ff190fb878e5ad3e2cae1e72f251c2143fdb67445894d6087794e9411156f2b`。两个H2 output roots仍不存在。下一动作必须提交推送 exact tools与本 entry形成tool-freeze；之后才允许运行 official zero-render preflight。

## J-257 · D12.14-H2 首次 preflight 被 full-shape probe 否决

Date: 2026-08-28 · Type: PREFORMAL INFRASTRUCTURE FAILURE / INVALIDATED PREFLIGHT · New Blender renders: 0

tool-freeze commit `0fbb9e2fa1350377de15fadcce9be1699761adc2` 推送后，首次official preflight自身报告13/13 accepted、0 render。随后在formal root仍不存在时追加一个更强的完整formal-shaped analyzer dry run：synthetic adapter树、Python/Node consumers、18-child execution draft与envelopes全部使用正式目录层级，期望analyzer正常产生NOT_SUPPORTED而非异常。

该probe在Node consumer阶段立即发现冻结工具缺口：`fs.mkdirSync(outputDir,{recursive:false})` 在runner将要使用的、parent尚不存在的 `consumers/node/R1/arrays` 路径抛出 `ENOENT`。Python consumer成功是因为其 `mkdir(parents=True)`；首次development byte test误用了已存在的直接parent，official preflight又只检查syntax与scalar arithmetic，因此均未覆盖真正目录边界。没有H2 Blender process、render、EXR或formal root产生，不能形成科学 verdict。

首次preflight root已完整保留并重命名为 `experiments/blender-material-owner-projective-depth-holdout-preflight-invalid-v0-1`；其accepted状态被machine record明确作废。`postflight-failure.json` file SHA-256 / self-hash为 `2a911349011137a815fffcedb4c2f7d2d32b03715c878cb48382f9783474f9fa` / `9b6a2343af33ed7dbfad082ab793a3819e39bc6b66db78d7fb870c745d27a78e`。

预登记 `B52-D12.14-H2-TOOL-C2` 只授权两项preformal change：Node mkdir改为recursive；preflight必须实际运行nested-parent Python/Node synthetic consumers并完成full-shaped analyzer dry run。source、adapter、Python consumer、analyzer、auditor、runner及全部科学语义禁止改动。C2 SHA-256为 `d3cab8e72764d1b12046be41068d3f6cafbd014110fc46748a03e29904bc2e38`。下一动作是先提交推送C2与invalid root；随后才编辑两条授权工具并形成第二tool-freeze。

## J-258 · Codex 升级重启前安全断点

Date: 2026-08-28 · Type: OPERATIONAL CHECKPOINT / NO EXPERIMENT EXECUTION · New Blender renders: 0

因用户准备升级并重启 Codex，本轮主动停止在 `B52-D12.14-H2-TOOL-C2` 已预登记、尚未实施的边界。检查时 Git `HEAD` 与 `origin/main` 均为 `6f1bc09433f23d2b542b2b5becb804e8eeb88451`；正式 H2 root `experiments/blender-material-owner-projective-depth-holdout-v0-1` 从未创建，corrected official preflight 也尚未运行。没有 Blender render、EXR、consumer measurement 或 scientific verdict 在此断点之后产生。

机器上没有实验 runner、Blender render、localhost server 或 H2 Python process在运行；仅存在 macOS 启动的 Blender thumbnailer application extension，不属于实验任务，保留不动。工作卷剩余约 `102 GiB`。用户原有 `README.md` 修改与三份未跟踪的 2026-08-26 research drafts仍明确排除于项目提交之外。

重启后的唯一恢复入口：先确认本断点 commit与远端一致；再严格按C2只修改Node consumer的一处recursive parent materialization，以及preflight的nested-parent Python/Node + full-shaped analyzer NOT_SUPPORTED probe。完成syntax与零渲染验证后提交第二tool-freeze；随后才允许运行新的official preflight。只有该preflight被提交并推送，才可启动exactly 4次正式 H2 renders。不得以首次13/13但已作废的preflight作为runner凭据，也不得跳过C2或提前创建formal root。

## J-259 · D12.14-H2-C2 第二次工具冻结候选

Date: 2026-08-28 · Type: PRE-FORMAL TOOL CORRECTION / ZERO-RENDER VALIDATION · New Blender renders: 0

从checkpoint commit `1c79aebea95eab452920a5be6cc40aca1e7219d8`恢复，确认corrected official preflight root与formal root均不存在后，严格实施 `B52-D12.14-H2-TOOL-C2` 的两项授权变更。Node consumer只把最终output directory materialization从 `recursive:false` 改为 `recursive:true`；preflight新增真实nested-parent Python/Node consumer执行、every-array byte identity、两repeat adapter/consumer formal-shaped tree、18-child synthetic execution draft、typed-envelope pair与完整analyzer NOT_SUPPORTED dry run。没有修改source、adapter、Python consumer、analyzer、auditor、runner、spec、correction或任何科学判据。

Blender-bundled Python 3.13 `py_compile` 与Node 26 `--check`均通过。独立 `/tmp` 零渲染开发probe从四个不存在的 `consumers/{python,node}/R{1,2}` parents启动，4/4 consumer children和analyzer child全部exit 0；Python/Node every output array byte exact；analyzer完整执行12项gates，唯一false为preregistered `PROJECTIVE_DEPTH_MEASUREMENT`，因此正确返回 `MATERIAL_OWNER_PROJECTIVE_DEPTH_EFFECT_NOT_SUPPORTED`，不是异常或REJECTED。probe result self-hash为 `b4ee503e28671e0e075c71b9544fbcce806dc384fc97daa424fa9a9c082fb5d2`，analysis receipt self-hash为 `02f06788b34d9a2929304daf6df956eb206fe789c120caffd53c4f021e3956ef`；临时root已移入用户Trash，不成为formal evidence。

Node consumer SHA-256从 `73b3127d9cf08e8220520a6fd93481b2879ee0bdb86419833b18a03025b02ef3` 变为 `d0a03b358962da9b564ae3b0b1fda526c640c8fd11aac11cd26f9e0435e631ef`；preflight从 `03ec5b996332ee976ca96a783f12ce09f3f65ec83a85deebf31c9fc81fef522d` 变为 `869a1e9cedebf03d2e256395e99d94c664429feaf40cb3868f9047fde024348e`。其余六工具SHA依次仍为 `c12e637352f8c6b8fbf6aad6c56b9264884a95087c33d2229af61d0c908262b5`、`65ecb58e2bbf8b569f9e82b72d21995cd5892a888787e68d6129c3a1a6ebbae7`、`507253e5b3f7778736a4fc3c765267ea82ee7afd6efe350b6a9afaa417b6f009`、`c246b35d4c68af4d6556f3ac1b6298ef9e329637ea33b72248501898e623fc7a`、`6b180be8cc623c615ef667df70d3d40cb56741fd1c2c2de801fe245a06bc5e3c`、`9ff190fb878e5ad3e2cae1e72f251c2143fdb67445894d6087794e9411156f2b`。下一动作只提交推送这两条corrected tool bytes与本entry形成第二tool-freeze；远端形成后才可创建fresh official preflight。

## J-260 · D12.14-H2 corrected official preflight 接纳

Date: 2026-08-28 · Type: OFFICIAL ZERO-RENDER PREFLIGHT ACCEPTED · New Blender renders: 0

第二tool-freeze commit `ffa30d5ca2a3f90ec1d1f3dead974e6b4733bfab` 与远端一致、formal root仍不存在后，创建fresh corrected official preflight。15/15 evidence gates全部通过：exact spec/correction、八工具tracked-clean、Python/Node syntax、factory scene construction、0 render/0 EXR、reciprocal-depth arithmetic、17-key schema smoke、runner finally failure path、四组此前不存在的nested consumer parents、Python/Node every-array byte identity、完整formal-shaped analyzer NOT_SUPPORTED path、formal-root absence、disk reserve、11个unique child PIDs、全部child exit 0及0 model/network calls。

preflight实际operation counts为1个preflight process、11个children、1个Blender factory probe、0 Blender render calls、0 Cycles ray renders、0 EXR、0 model calls、0 network calls。scene probe未启动渲染。full-shape analyzer的12项中11项通过，唯一false为故意构造不足样本的 `PROJECTIVE_DEPTH_MEASUREMENT`；它正确返回 `MATERIAL_OWNER_PROJECTIVE_DEPTH_EFFECT_NOT_SUPPORTED`。两个repeat的Position current-depth、Vector与Vector-next control maximum errors均为0；这只是工具路径验证，不是H2 measurement。

preflight file SHA-256 / self-hash为 `e7551d41df86c8a56a8f660c8c491c208cbbeb69372855217ec2bd26ffa7400c` / `019d1c85d4b157d0d46d43bf1ce1b9e0dd5b46f37fcc94b351703a2875fab3fd`；receipt file SHA-256 / self-hash为 `4fda09b4f4853eaa9f41b16ad7219d640194d0bbbb1998c75777788f139e7a07` / `c2d4dce8632f981980e3f365c56c134c75f332c419be917b9dc5d8f4c2ee952f`。full-shape result / analysis receipt self-hashes为 `e3868cb53d5671523f4f039476a7e6a2ef4c6fb51c1e6c93bd150d5ab7ca89cf` / `738b1358656ea6befa4c57efef0f6959f4dd3f81205684a488a7442641cd54e2`。独立9项复核重算四份canonical self-hash、preflight file binding、22份child stdout/stderr bindings、11个exit codes/PIDs，并确认root中0个EXR。observed free bytes为109,593,456,640；扣除67,108,864 projected bytes后仍高于107,374,182,400 minimum reserve。

下一动作只提交并推送exact preflight evidence root与本entry。该evidence commit形成且远端一致之前不得运行formal runner；之后runner才被允许创建fresh formal root并执行exactly 4次Blender 5.2 Cycles renders。

## J-261 · D12.14-H2 正式调用被冻结 runner admission 缺口作废

Date: 2026-08-28 · Type: FORMAL INVOCATION INVALIDATED / NO SCIENTIFIC VERDICT · New Blender renders: 0

corrected official preflight evidence commit `7986502763ccbeffa5c1f40ba2b0bfa218e836b0` 推送且本地/远端一致后，按protocol首次且唯一调用formal runner。调用使用仓库内相对 `--preflight-root` 与 `--output-root`，与此前所有命令风格一致。冻结runner在创建formal root与进入自身failure-finally范围之前，于line 127执行 `cli.preflight_root.relative_to(root)`；相对Path不能相对于绝对repo root求relative path，因此立即抛出 `ValueError`，exit 1。

这是preflight未覆盖的第二个admission缺口：preflight验证了runner forced-failure finally path和完整nested tree，却没有用runner正式CLI的相对路径形状执行只读admission。此次失败发生在任何child启动之前：1次runner invocation、0 child、0 Blender process、0 render calls、0 Cycles renders、0 EXR、0 adapter/consumer/analyzer/auditor、0 model/network calls；formal root在调用前后均不存在。H2因此没有scientific verdict，不能声称supported、not-supported或rejected。

按原始H2 preregistration的不可修复规则，冻结tool failure禁止用同一experiment ID修复重跑。即使改用absolute path可能绕过该bug，也不允许再次调用 `B52-D12.14-H2`。机器证据保存在 `experiments/blender-material-owner-projective-depth-holdout-formal-invocation-failure-v0-1`：stderr SHA-256为 `fbaa7799dcc00a584b688f206beee1289ee23203e90e5af285c46fbbcf5fe007`；failure file SHA-256 / self-hash为 `6a212c91d8eeff0319017ae51d00daf3505d14d9f494a0318d441924f2b6d492` / `8ca7ba69004dfd51fa0b08d00153f033d43961f608252e161617b0b3a511ae4c`；receipt file SHA-256 / self-hash为 `d5133f52b712e32b93b0997aff9837722a241ae9e781eb1919f7c3136f56e5ab` / `479bde998ad41d0f21e08cabea6c4405d91afa45558239538aeda87b14c93e38`。独立6项检查重算两份self-hash与两层file binding，并确认null verdict和0 render。

下一动作只提交推送失效证据与本entry，不修改H2 runner、不创建H2 formal root。随后遵守promotion boundary，返回主目标 `SceneSpec → immutable BuildPlan → Blender 5.2 compiler`，先审计B01/B02现有证据与尚未满足的两次净构建结构哈希复现门。

## J-262 · H2 后核心 SceneSpec 编译器门重新核验

Date: 2026-08-28 · Type: CORE GOAL EVIDENCE REVALIDATION · New Blender renders: 0 · New Blender compilations: 0

H2失效证据commit `e6b8fb857d6bdcf19294bd8714bb98de505b75b8` 推送后，按主目标逐项重开当前证据，而不是依赖旧journal结论。SceneSpec v0.1 fixture suite为22/22；current `compileBuildPlan()`在同一fresh Node process中对B01、B02各执行两次，两个wrapper分别canonical byte exact，plan hashes仍为 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` 与 `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`。

current receipt verifier重新验证native B01-A/B、B02-A/B，4/4均PASS OK且每份19项bindings成立。随后直接重算native receipt root与corrected Linux/amd64 B42-C1 root的八份 `scene.structure.canonical.json`：每份parsed content均与adjacent manifest structure深相等，byte SHA均同时等于manifest的两处binding。B01四份仍为 `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`；B02四份仍为 `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`。

因此核心 `SceneSpec → immutable BuildPlan → Blender 5.2` B01/B02双净构建结构复现门有当前直接证据支持，不需要用H2替代，也不因H2失效而回退。新result note为 `research/2026-08-28-post-h2-core-compiler-revalidation.md`。下一项有观察支持的缺口是formal-run admission reliability：future one-shot preflight必须执行relative/absolute path equivalence、containment、fresh-root、pushed-evidence lookup与failure-receipt reachability；必须作为新实验，禁止修复或重跑H2。

## J-263 · D12.14-H2 正式调用失效研究页完成本地验证

Date: 2026-08-28 · Type: WEBSITE SOURCE VALIDATED · New Blender renders: 0

新增研究页 `blender-projective-depth-formal-invalidation-v0-1`，直接读取corrected preflight、formal invocation failure与failure receipt机器证据。页面把三件事严格分开：15/15 preflight确实验证了nested consumers与full-shaped analyzer；正式runner在0 child/0 Blender/0 render时因relative/absolute path admission缺口作废；inverse-depth hypothesis因此没有scientific verdict。页面同时公开下一版formal admission contract与H2后B01/B02核心编译器复核结果。

首页新增 `D12.14-H2 正式调用失效` tab；P1页面从未来时entry contract更新为observed H2 outcome，并链接完整失效链。GitHub Pages sparse checkout只新增页面实际import的三份小型machine JSON，没有引入9.3 MiB preflight arrays。新页、P1与首页定向ESLint为0 errors；Vinext/Sites production build成功并发现85个CDN warmup paths；GitHub Pages static build成功生成87/87 pages，新route明确为static。本地新页、P1与首页exact routes均返回HTTP 200。

按Sites验证边界，没有执行用户未请求的截图、DOM、点击、resize或视觉QA。React best-practices复核确认新增页面是纯Server Component、无hooks/client data waterfall、无第三方bundle或hydration state，现有静态map规模无需额外memoization。下一动作只提交并推送新页、CSS、导航、Pages workflow与本entry；随后确认公开Pages exact commit，并在owner-only Sites access复核后发布同一source commit。

## J-264 · D12.14-H2 正式调用失效研究页双站点发布完成

Date: 2026-08-28 · Type: PUBLICATION COMPLETE · New Blender renders: 0

site source commit `9cf632d256dc495b7ac696da8292d0ec7be33123` 推送后，GitHub Pages workflow `33172634355` 的build与deploy均completed/success，head SHA exact；公开H2 route返回HTTP 200。公开URL为 `https://lovejzzz.github.io/BlenderFilmStudio/blender-projective-depth-formal-invalidation-v0-1/`。

同一source commit推送到Sites source repository并保存为version 78；archive content hash为 `sha256:b2a38e2707ce2c7f01a1135db090cded288c70dfac63e1a687eb7394e8c535f6`，deployment `appgdep_6a9183f78e4c819186e2ab05f9679b08` succeeded。发布前再次验证current user为owner、access mode为custom、exactly one allowed account且其role为owner、external visitors为0、workspace/tenant groups为空；owner-only exact route的匿名请求返回HTTP 401。Owner-only URL为 `https://blender-film-studio-research.skylab.chatgpt.site/blender-projective-depth-formal-invalidation-v0-1/`。

H2 publication至此封闭；没有改变H2 null verdict或same-ID禁止重跑边界。下一阶段按J-262观察启动新的formal-run admission reliability实验：先预登记relative/absolute equivalence、containment、fresh-root、pushed-evidence lookup与pre-try failure receipt reachability，再创建任何tool byte。

## J-265 · B53-E1 formal runner admission path totality 预登记

Date: 2026-08-28 · Type: FORMAL PREREGISTRATION · New Blender renders: 0

在spec、protocol、三条new tool paths与formal root全部确认不存在时，预登记 `B53-E1`。Parent evidence绑定B42 nested mountpoint/null-observation failure、D12.14-H1 producer-only schema smoke failure与D12.14-H2 relative/absolute path admission failure；本实验不修复或重跑任何parent。

冻结17-case matrix：relative、dot-segment与absolute三种等价positive spellings必须accept并产生exact canonical evidence identity；14个negatives分别要求outside repo、symlink、missing/not-directory、untracked、committed-not-pushed、preflight self-hash/status、tool hash、outside/symlink/existing output与missing origin branch的exact earliest reason。每个case都必须拥有receipt；每个rejection都必须在任何formal work之前写self-hashed failure，scientificVerdict始终为null。Admission不得创建声明的formal output。

正式实现限定为dependency-free Node admission library、single-use runner与不import前两者的independent auditor。Runner只可创建isolated local fixture Git repo和local bare origin；Blender、Docker/Colima、network、model、render与external repository全部禁止。Audit必须重开fixture、复算hash/path/Git ancestry/process boundary并执行至少32项one-field semantic attacks。Spec SHA-256为 `d85c450e4f927a684a630324da3ee5281b0cd57f3fcd23cdccf5d4cfe3f2b4f5`；protocol SHA-256为 `d3470821f5d4ae3d31fa2f3a2d218db0cfc2bb66e7c576eee9d7a80313d031a5`。

下一动作只能提交并推送exact spec、protocol与本entry；远端preregistration commit形成前不得创建任何B53-E1 tool byte或output root。Supported verdict只授权未来新实验采用admission module；production compiler orchestration变更仍必须重跑B01/B02 structure regression。

## J-266 · B53-E1 Codex 升级重启前实现断点

Date: 2026-08-28 · Type: OPERATIONAL CHECKPOINT / UNFROZEN IMPLEMENTATION · New Blender renders: 0

用户准备升级并重启 Codex，因此在B53-E1正式工具冻结前主动停止。preregistration commit `ae7e57ff86d8a5f735e5a32d3b80755edb6b8f4d` 已与 `origin/main` 一致；此后仅创建dependency-free Node admission library候选 `scripts/lib/formal-run-admission.mjs`，未创建runner、independent auditor或formal output root，也未执行任何B53-E1 case、Git fixture、Blender、Docker/Colima、network、model或render工作。

当前library候选为183行，SHA-256 `382a06e82c815b69539edf6211bd3d9db28a05c2aa49d1f7a6ddaed61f18f67a`；`node --check` 与 `git diff --check`通过。该文件只是可恢复的实现checkpoint，不是tool-freeze，不构成formal evidence或admission结论。其path、Git ancestry、self-hash、tool binding和output containment逻辑尚须由runner matrix与不import该library的auditor验证。

重启后的恢复入口：确认本checkpoint commit与远端一致；先实现 `scripts/run-b53-e1-formal-runner-admission-path-totality.mjs` 与 `scripts/audit-b53-e1-formal-runner-admission-path-totality.mjs`，再对三条工具做syntax和仅位于临时目录的development probes。只有审读与零formal-output验证通过后，才能记录exact tool hashes并形成独立tool-freeze commit；tool-freeze推送前不得创建 `experiments/formal-runner-admission-path-totality-v0-1`。用户原有 `README.md` 修改与三份未跟踪research drafts继续排除于提交之外。

## J-267 · B53-E1 三工具冻结候选与完整临时矩阵

Date: 2026-08-28 · Type: FORMAL TOOL-FREEZE CANDIDATE / TEMPORARY DEVELOPMENT PROBES · New Blender renders: 0

checkpoint commit `2db59b7e93088ca8e2562a5093960d43ea16baf0` 推送后，完成dependency-free admission library、single-use runner与不import前两者的independent auditor。Runner在语义admission前创建每case attempt ledger；三种positive只返回canonical target而不物化；14种negative各写self-hashed failure与receipt。Auditor重新实现path、Git ancestry、preflight/tool hashing，重开17个isolated clones，逐条绑定execution summary，并执行34项one-field attacks。

第一个临时positive probe揭示macOS `$TMPDIR` lexical `/var/...` 与realpath `/private/var/...` 的清理守卫差异；遗留的唯一自有临时目录已移入用户Trash。第二个probe确认repository root也必须在创建后立即canonicalize，而不能放宽symlink拒绝条件。这两项都在tool-freeze前修正；没有创建formal root或formal verdict。

最终完整development matrix只在runner自有临时目录执行并由runner删除：17 case evaluations全部符合冻结reason；34/34 semantic attacks被拒绝；`SPEC_AND_TOOL_IDENTITIES`因三工具尚未提交而按预期为false，其余13/13 gates全部为true。该probe记录135个runner-side与84个auditor-side Git children，仅用于开发覆盖，不冒充未来formal counts。三工具均通过Node 26 `--check`、`git diff --check`与定向ESLint 0 errors；formal root继续不存在，Blender、Docker/Colima、network、model、render均为0。

按library、runner、auditor顺序的SHA-256为 `382a06e82c815b69539edf6211bd3d9db28a05c2aa49d1f7a6ddaed61f18f67a`、`a479693b085774eee92f0eb2f0dfa18bc84221ac7578f9677e1635ec59bb44b8`、`ff25d1f768489f2e0f6304a0d0dddc31cacb94509c4557dd673e04f375404536`。下一动作必须只提交并推送这三条exact tool bytes与本entry形成tool-freeze；远端commit一致后才可创建single-use formal root并调用runner一次。

## J-268 · B53-E1 formal runner admission path totality 支持

Date: 2026-08-28 · Type: FORMAL EXECUTION-INFRASTRUCTURE RESULT · New Blender renders: 0

tool-freeze commit `4c028c455357e14d4248767e1d3c33354f0e3a7d` 与 `origin/main` exact一致、三条tool paths tracked-clean且formal root不存在后，只调用formal runner一次。独立auditor在临时fixture删除前重开local bare origin与17个isolated clones；正式结果为 `FORMAL_RUNNER_ADMISSION_PATH_TOTALITY_SUPPORTED`，14/14 frozen gates和34/34 one-field semantic attacks全部通过。

P01 relative、P02 dot-segment与P03 absolute均ACCEPT，三者canonical evidence identity exact，identity hash为 `8e69d1eeb68f314aa6697347fef5a43fb539fae8d84667d776278444c6f023b5`；三种output canonical parent均为 `fixture`，target basenames不同且均未物化。14个negative逐一返回冻结的earliest reason；每个case都有attempt、admission/failure、receipt三份记录，`scientificVerdict`在case层始终为null。所有17个output fingerprint before/after exact。

正式operation counts为1个runner process、1个independent auditor、17个case evaluations、140个runner-side Git children、84个auditor-side Git children，共224个Git children；Blender process/render、Cycles ray render、Docker/Colima、model与network均为0。临时fixture由runner在audit完成后删除，formal root中无invalidation record。

formal-start、execution、audit、results、receipt的file SHA-256依次为 `13d1e6912927f2789b340ad85b50451fc504c0d8399d16101dfb323c78569e22`、`f1c8ac9177b2cd27bd7ba7dd41791f4dcdb3c4175c2c3b6e0b6f5dafed48ac31`、`bd330841231065c1217f7eda3e02892788b737c5e5eb6fe3953e284c108f6968`、`a5e58a5d925a1e3222ba5ee51f4b4d4db973ffcdef0dac64e6d1c2c4bdfb0c48`、`e8655510dd49b3522af2ebc7b57b3c8a512bb3c55a48efc3950c9aa9c38da68e`；对应self-hashes为 `9c021b95836becdba9f471d740e0871a547b3f10d88d96c420bc7296a5f305c0`、`de07aa440861288ad40709e28b95e9e92d160b51897e513a4c71adc626493e63`、`fe270af055104a20e49194cff2d5833c600348a6fc52a573504c9cb28162241a`、`1b5d1dfd36de6689e2692c6fee3e3f853ca278523917c53aba61bbbd932ce33f`、`82169fc5a46681c4ba1b3a995e574eb372809eceb3f96047a284a2d54d5880b9`。

正式调用后另做一次不import formal tools的只读离线复核；首个inline命令有未闭合括号并在解析阶段退出，未读取或修改evidence。修正后的命令验证8/8顶层self-hash、51/51 case self-hash、17/17 case file bindings、17/17 frozen outcome/reason、17/17 output unchanged、tool/result/receipt bindings、fixture deletion和no-invalidation全部为true。B53-E1同一ID现已封闭，禁止修复或重跑。下一动作只提交推送exact formal root与本entry；随后发布研究页，并在任何production orchestration adoption前预登记integration且重跑B01/B02 structure regressions。

## J-269 · B53-E1 研究页完成本地验证

Date: 2026-08-28 · Type: WEBSITE SOURCE VALIDATED · New Blender renders: 0

formal evidence commit `ed65023` 推送后，新增 `formal-runner-admission-totality-v0-1` 研究页。页面直接读取frozen spec、audit、results与receipt，展示B42→H1→H2→B53失败链、relative/dot-segment/absolute三路径汇入同一canonical identity、14个exact negative reasons、attempt→failure→receipt ledger、14个gates、34个semantic attacks、224个Git children及全部forbidden operation为0。Claim boundary明确保留H2 null verdict，并要求未来production adoption重新预登记和复跑B01/B02 structure regressions。

首页新增 `B53-E1 准入总路径` tab；H2失效页把此前future admission contract更新为observed B53-E1 follow-up，但没有更改H2的null verdict。GitHub Pages sparse checkout只加入页面实际import的spec、audit、results与receipt。新页、H2页和首页定向ESLint为0 errors；React best-practices复核确认新增页保持纯Server Component，无hooks、client data waterfall、第三方bundle或hydration state。

本地dev server上新页、H2页与首页exact routes均返回HTTP 200。Vinext/Sites production build成功，发现86个CDN warmup paths；GitHub Pages Next static build成功生成88/88 pages，新route明确为static。按Sites验证边界，没有执行截图、DOM、点击、resize或视觉QA。下一动作只提交推送本页、CSS、导航、Pages workflow与本entry；随后确认GitHub Pages exact source commit，再以owner-only access发布同一source commit到Sites。

## J-270 · B53-E1 研究页双站点发布完成

Date: 2026-08-28 · Type: PUBLICATION COMPLETE · New Blender renders: 0

site source commit `c4eb406558b6c25fc87fe1e1ea537861e21dec0f` 推送后，GitHub Pages workflow `33174920237` 的build与deploy均completed/success，head SHA exact；公开B53 route与更新后的H2 route均返回HTTP 200。公开URL为 `https://lovejzzz.github.io/BlenderFilmStudio/formal-runner-admission-totality-v0-1/`。

同一source commit推送到Sites source repository并保存为version 79；archive content hash为 `sha256:cf74f1497a5abd78fc976d642df86a54ef4eb604219e29ce3a3de067e345f3d5`，共373 files、28,876,800 bytes。deployment `appgdep_6a918bd6e6288191a224ee9cded21e1f` succeeded。发布前再次验证current user为owner、access mode为custom、exactly one allowed account且其role为owner、external visitors为0、workspace/tenant groups为空；owner-only exact route匿名请求返回HTTP 401。Owner-only URL为 `https://blender-film-studio-research.skylab.chatgpt.site/formal-runner-admission-totality-v0-1/`。

本地dev server已停止；发布临时archive目录已移入用户Trash。没有创建或刷新Sites screenshot，也没有执行视觉QA。B53-E1 publication至此封闭。下一阶段必须遵守promotion boundary：若把admission module接入production compiler orchestration，先建立新的integration preregistration，冻结采用边界与失败receipt semantics，并以B01/B02双净构建structure hashes作为不可回退的回归门。

## J-271 · B54-E1 admission-gated native compiler integration 预登记

Date: 2026-08-28 · Type: FORMAL PREREGISTRATION · New Blender renders: 0

在spec、protocol、三条new tool paths、preflight/attempt/formal roots全部确认不存在时，预登记 `B54-E1`。B53-E1只证明isolated formal admission totality；本实验冻结下一步最小integration：不修改现有production compiler files，新建single-use wrapper，在任何Blender授权前消费repository-relative preflight/formal paths并持久化attempt→admission/failure→receipt。

正式runner必须从当前B01/B02 SceneSpecs各调用 `compileBuildPlan()` 两次，要求canonical wrapper byte exact及plan hashes `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` / `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`；随后通过unchanged restricted CLI执行B01-A/B、B02-A/B四次fresh native Blender 5.2 compiles。Acceptance仍是canonical structure bytes pair-exact及frozen hashes `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b` / `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`，不要求 `.blend` byte identity。

Preflight冻结为0 Blender process：22/22 SceneSpec suite、B01/B02 in-memory dual compile、tool/Git/runtime identities、relative-path component boundary、three-root absence和512 MiB projection后100 GiB reserve。正式audit不import新preflight/runner；它外部调用current verifier要求4份receipt各19 checks，重开四份structure/manifests，以Blender审计四个 `.blend` embedded bindings并执行至少24项one-field attacks。正式语义计数冻结4 restricted compiles、4 native compile invocations、4 receipt identity probes、4 current verifier invocations、4 verifier identity probes、4 blend audits、1 runner与1 auditor；existing APIs不暴露八个Blender `--version` probe PIDs，必须明确作为非OS-attestation边界。

Spec SHA-256为 `4453d24e7e2a36ca114435a979dc7501247b3da1f5ec0f394143356c058d30cd`；protocol SHA-256为 `8df4b9e239c5fa61aa12e6b7d539d2c3bf2e088be7ee2a52e8177badf227ac60`。18项gates全部通过才支持 `ADMISSION_GATED_NATIVE_COMPILER_INTEGRATION_SUPPORTED`；任何tool/process exception使scientificVerdict为null并禁止同ID修复重跑。下一动作只提交推送exact spec、protocol与本entry；远端preregistration commit形成前不得创建任何B54 tool byte或root。

## J-272 · B54-E1 Codex 升级重启前实现断点

Date: 2026-08-28 · Type: OPERATIONAL CHECKPOINT / UNFROZEN IMPLEMENTATION · New Blender renders: 0

用户准备升级并重启 Codex，因此在B54-E1正式工具冻结与任何native compile之前主动停止。preregistration commit `ad13c0bc7400a3e43b296449d8263f10e6a974af` 已与 `origin/main` 一致；此后只创建preflight候选 `scripts/preflight-b54-e1-admission-gated-native-compiler.mjs`。runner、independent auditor、preflight/attempt/formal roots均未创建，也未执行Blender、Docker/Colima、network、model或render工作。当前没有B54或Blender compile后台进程；macOS Blender thumbnailer app extension不属于本实验。

候选preflight为315行，SHA-256为 `e650cf69b969c36564ec0c372250a7d2bdbb9de051262d80cb81a34af56f0e42`，并通过Node 26 `--check`。一次显式 `--development-probe` 返回PASS：SceneSpec suite 22/22；B01与B02各两次in-memory BuildPlan canonical bytes exact且frozen plan hashes分别为 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` 与 `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`；repository-relative component admission ACCEPTED且probe output保持不存在；磁盘在512 MiB projection后预计剩余108,877,807,616 bytes，高于100 GiB reserve。该probe记录5个Git children、0 Blender processes与0 render calls，并明确没有创建formal roots。

本文件只是可恢复的implementation checkpoint，不是tool-freeze、official preflight、formal evidence或scientific verdict。重启后的恢复入口：先审读并完善preflight异常失败持久化与字段命名，再实现single-use runner与不import preflight/runner的auditor；三工具完成后只能在不创建B54 roots的development mode验证。随后记录exact tool hashes、提交推送独立tool-freeze，确认远端一致后才允许调用一次official zero-Blender preflight。用户原有 `README.md` 修改与三份未跟踪research drafts继续排除于提交之外。

## J-273 · B54-E1 三工具隔离彩排前 checkpoint

Date: 2026-08-28 · Type: IMPLEMENTATION CHECKPOINT / ZERO-BLENDER DEVELOPMENT PROBES · New Blender renders: 0

从commit `bed5603473c09cafa9a7b71ff75d9111ba4ccb2c`恢复后，完成preflight异常留证、single-use admission-gated runner与不import前两者的independent auditor候选。Preflight现在在确认three-root absence后先创建自身single-use root；后续任何tool/Git/runtime/component异常都会保留REJECTED preflight与receipt。Runner在admission之前持久化attempt，在accepted admission与receipt durable之后才创建formal root；四个restricted compiler children与auditor child均绑定PID、arguments、exit、elapsed及独立stdout/stderr files。Auditor外部调用四次current receipt verifier和四次Blender artifact audit，重开plans、receipts、budget reports、manifests、canonical structure与 `.blend` bindings，并定义33项one-field attacks。

三条development probes全部PASS且未创建任何B54 root：preflight观察SceneSpec 22/22、B01/B02 dual in-memory BuildPlan exact、relative component admission ACCEPTED、512 MiB projection后剩余108,816,105,472 bytes；runner再次观察两组BuildPlan exact；auditor只验证spec identity。Node 26 `--check`、`git diff --check`与三文件定向ESLint均为0 errors/0 warnings。按preflight、runner、auditor顺序的当前checkpoint SHA-256为 `2a79b5483290b8167de54243322ec9d48731507035008c3e84083b843e8fcde8`、`b1e71234130019a6d5f23b32445cb9bca32b6091081b960f06538026ea891905`、`e5cc331b973798150bd3d246195d07efee384ff41739f7348d39bdb8c0ff90d8`。

代码审读同时发现冻结protocol中的可证伪矛盾：current `budgeted-process.mjs` report绑定native Blender command/args/exit/resource metrics，但其 `child` object没有PID；因此不能满足“native compile PID由budget report绑定”的强表述。现有production files按预登记保持unchanged，auditor不得把semantic invocation binding冒充OS PID attestation；若正式证据仍如此，`DIRECT_PROCESS_AND_SEMANTIC_OPERATION_COUNTS_EXACT`必须为false，B54-E1应得到outcome-neutral REJECTED而不是伪支持。下一动作是在隔离临时Git origin/clone中用这些candidate bytes完成一次全流程彩排；彩排可调试且不创建real repository B54 roots。彩排修正完成后才形成正式tool-freeze。

## J-274 · B54-E1 隔离全流程彩排与工具冻结候选

Date: 2026-08-28 · Type: ISOLATED NATIVE REHEARSAL / TOOL-FREEZE CANDIDATE · New Blender compilations: 8 · New Blender renders: 0

为避免把real single-use roots当作调试环境，建立仅含必需tracked paths的 `/tmp` sparse clone、local shared bare origin与现有只读 `node_modules` link。第一次full-clone fixture因ignored AJV dependency缺失在module import阶段退出，未创建preflight或启动Blender；第二次full clone通过15/16 checks但因clone自身占用1.8 GiB使100 GiB disk reserve失败。两份明确owned的full-clone temporary roots合计约3.6 GiB已删除；预登记disk gate未降低。

第一次sparse official-style preflight为16/16 ACCEPTED。其formal rehearsal完成四次fresh native compiles后，在写operation draft时因candidate runner变量名错误保留self-hashed invalidation；该失败clone未修复或续跑。错误在real tools中修正后，第二个全新sparse rehearsal完整执行，发现production compiler按设计创建空 `frames/` directory；candidate auditor此前把它误判为unbound roster。Auditor改为要求该directory存在且为空，失败clone同样未续跑。

第三个全新sparse rehearsal从commit `bf88f1a2ea197d667530d034886a8b78373001f2`开始：zero-Blender preflight 16/16 ACCEPTED并commit/push到isolated local origin；relative-path admission accepted；B01-A/B与B02-A/B四次fresh native Blender 5.2 compile全部PASS；四份current CompileReceipt verifier各19 checks；四份 `.blend` embedded plan/structure/manifest/Blender bindings exact；B01/B02 plan hashes分别为 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` / `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`，pair canonical bytes exact；structure hashes分别为 `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b` / `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`，A/B bytes exact。33/33 semantic attacks全部rejected，direct runner/auditor child records与semantic counts exact。

Outcome-neutral rehearsal verdict为 `ADMISSION_GATED_NATIVE_COMPILER_INTEGRATION_REJECTED`，17/18 gates；唯一false gate为 `DIRECT_PROCESS_AND_SEMANTIC_OPERATION_COUNTS_EXACT`，因为四份budget report仍没有native child PID。该single failure是冻结contract对current production supervisor的真实反证，不是编译或结构复现失败。按preflight、runner、auditor顺序的最终candidate SHA-256为 `2a79b5483290b8167de54243322ec9d48731507035008c3e84083b843e8fcde8`、`db77a75968bf59b198c59ccdeb618868b61d6f1c08d93eb88dc6bdf37ce5d4d7`、`a1294f1255937af9cde92ff0295f1bec3b20dde72703505c9260396277f0c53f`；三文件Node 26 syntax、targeted ESLint与diff checks通过。下一动作只能删除owned sparse rehearsal root、提交推送本entry形成exact tool-freeze；随后在real repo运行一次official zero-Blender preflight。

## J-275 · B54-E1 official zero-Blender preflight accepted

Date: 2026-08-28 · Type: FORMAL PREFLIGHT ACCEPTANCE · New Blender processes: 0 · New Blender renders: 0

tool-freeze commit `ae15019a5e0e7d8078f625340dc41ffc79c7eeda` 与 `origin/main` exact，三条tool hashes与J-274一致，preflight/attempt/formal roots全部不存在后，正式preflight只调用一次。结果为ACCEPTED：16/16 checks；SceneSpec 22/22；B01/B02各两次in-memory BuildPlan canonical bytes exact且plan hashes frozen；relative component admission ACCEPTED且没有创建probe output；B53 parent evidence、all tool/config/runtime identities、tracked-clean/pushed ancestry与three-root absence全部exact。

本次preflight记录1个preflight process、1个SceneSpec validator child、10个Git children，Blender process/render、Cycles ray render、Docker/Colima、model与network均为0。观察到109,569,703,936 available bytes；512 MiB projection后为109,032,833,024 bytes，高于100 GiB reserve。`preflight.json` file SHA-256 / self-hash为 `004d81fefa4e18aa693ceb36d379613bda6dc68490087b7a5abdd8ad33009a64` / `457b45b050b66201487634b436196c7a6e754d74b7cb582ac103a0f3f659a668`；`receipt.json` file SHA-256 / self-hash为 `696f71f4be3a887e8252da675f42968b2f95368c4618975768d0109655b6878e` / `ecbc44e982bfe2933b819ee3b2c0a317bf4ed087b91098837db84483c465f825`。独立built-in-only readback复算两份self-hash均exact；attempt/formal roots仍不存在。

下一动作只能提交并推送exact accepted preflight root与本entry；确认其affecting commit已在 `origin/main` 后，才可用repository-relative spellings调用formal runner一次。预计scientific result可能因已观察到的native PID evidence gap而REJECTED，但formal mapping必须由independent audit observation产生，不能预写结果。

## J-276 · B54-E1 admission-gated native compiler formal result

Date: 2026-08-28 · Type: FORMAL NATIVE COMPILER INTEGRATION RESULT · New Blender compilations: 4 · New Blender renders: 0

accepted preflight affecting commit `53082290d0107736f1a4ea98bc491997b27f545f` 与 `origin/main` exact、attempt/formal roots不存在后，只用冻结的repository-relative spellings调用formal runner一次。Runner先持久化sequence 1 attempt、sequence 2 accepted admission与sequence 3 receipt；sequence 4 formal-start绑定attempt receipt后才创建formal root并授权compiler。Admission evidence commit、preflight file/self hash、tool hashes与relative output identity exact；没有admission rejection或formal invalidation。

Formal BuildPlan对B01/B02各调用current `compileBuildPlan()`两次，canonical wrapper bytes pair-exact；frozen plan hashes分别为 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` / `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`。随后B01-A/B与B02-A/B四个never-before-existing outputs通过unchanged restricted CLI完成native Blender 5.2 compiles；四份budget outcomes PASS、四份current verifier各PASS OK且19 checks、四份 `.blend` embedded plan/structure/manifest version `0.2.0` / Blender build `fbe6228777e7` exact。B01 canonical structure A/B byte-exact且SHA-256 `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`；B02 A/B byte-exact且SHA-256 `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`。四个 `.blend` file hashes各不相同，符合“不要求container byte identity”的预登记边界。

Independent auditor完成33/33 one-field semantic attacks、17/18 gates，outcome-neutral formal verdict为 `ADMISSION_GATED_NATIVE_COMPILER_INTEGRATION_REJECTED`。唯一false gate是 `DIRECT_PROCESS_AND_SEMANTIC_OPERATION_COUNTS_EXACT`：runner四个restricted child PIDs、auditor PID、四个verifier child PIDs、四个blend-audit child PIDs及所有semantic counts均exact，但current四份budget report的 `child` object只有exit/signal/spawnError，没有native Blender PID，因此 `nativeCompilePidBindingsAvailable=false`。这是强OS process-attestation要求失败，不是SceneSpec、BuildPlan、native compile、receipt、structure或 `.blend` binding失败。Blender render、Cycles ray render、Docker/Colima、model与network均为0。

不import B54 tools的formal readback复算10/10顶层self-hashes通过；attempt、admission、attempt receipt、formal-start、plan observations、operation draft、audit、operation、results、formal receipt的file SHA-256依次为 `466a8d3d5a122d3bf02c45b72de760aea36d2a982d54790984b5f4ca445c7ae3`、`04892d25b0bc3404e5ffc4c6e45819e162115f85887f8211298740d7e9777266`、`2961dc9a9d8ecce3a877fa6bc3fb36387796bb9a4ea0200c29dfa8c60d0fdc15`、`7161e6495b9dc17c868d80f01a4228fd4d6ea6c05242e6f5e7be0fd135cae1c1`、`1212f9ced08ecf661d2a963e1f978d466f4529e78de3c82a6bf0ccf3370f97ca`、`2a8a606fb63e78c074e2598e13d14c64b944ca100801929ab3814b7f560355dd`、`a8bc8556465dfc43f5986b801384565e8fdef07fc98d03a2ba89ef5ac256a747`、`10b9ab8eb961e59f95546edf68c28365eb69cfd229f3e3a6600b1abcfbf8b3be`、`b0859222afef40e450d22e2c731fd108e7c55fa88f3bbd156e44db42562064ac`、`03a32ba5134051ac0535ca0a52bfc8ff6b14c3e77b1d085cef83aa985612888c`；对应self-hashes为 `a71db2fae42973122f3931ef70d2c94c3d46dc8c455899168e5e7f8b562c9c8a`、`a6bd6bd5c350f1bcf11aa337513ff9f200873160316c8ca5746edd81abd08786`、`ed8465f943e2eb0064c366727b80ae90c10e15cb93ea7099ac267b4f2d956ec8`、`d40dec89fb365c742196d2bb84fe0c87235cebcdc2f7eb4a410694bee4e18596`、`51d5469fae69f256f82c7755436e0a3ae032606793f4b1b89a7cd6af1f301427`、`55a4e6f9328a5e9b0bec8f6ef93ea0df76b1ecc93b16f6fcc615cc604980293d`、`2cbed88860d3b143a29dc131cac53051a4cee36cdf37e43ea3500bfdc649cc93`、`015e0c90746664b9474b5074f512ce4b7378c33669365b63c6921fdfcd16c4f6`、`1a9a231d2d2b683ee17ca82b2c231ff8755b167a108a16493b2c6e908b6624fc`、`dbdeb57ea3388a642de885bd57bd20c666b37cd14e2944436171dcf5f8cc9565`。B54-E1同一ID现已封闭，禁止修复或重跑。下一动作只提交推送exact attempt/formal roots与本entry；随后发布REJECTED研究页，并预登记最小supervisor PID-receipt correction，而不是修改B54 evidence。

## J-277 · B54-E1 研究页完成本地验证

Date: 2026-08-28 · Type: WEBSITE SOURCE VALIDATED · New Blender renders: 0

formal evidence commit `7ed5727`推送后，新增 `admission-gated-native-compiler-v0-1` 研究页。页面不把REJECTED简化为“编译失败”：首屏明确区分4/4 native compiles、4×19 receipt checks、2/2 structure identities与17/18 formal gates；authorization sequence图展示attempt→admission→receipt先于formal root；四-run矩阵同时展示plan/structure/verifier/`.blend` bindings与四个NULL native PIDs；18-gate map只把 `DIRECT_PROCESS_AND_SEMANTIC_OPERATION_COUNTS_EXACT`标红；PID evidence flow解释in-memory `child.pid`未进入budget report，因此不得从command/exit/metrics反推OS PID。

Homepage新增 `B54-E1 原生编译器准入` tab；B53页把未来integration gate更新为observed B54 17/18结果并链接新页。GitHub Pages sparse checkout只加入新页实际import的spec、preflight、audit、results与receipt。B54、B53与homepage exact local routes均HTTP 200；三TSX定向ESLint为0 errors/0 warnings；Vinext/Sites build成功并发现87个CDN warmup paths；GitHub Pages production build通过TypeScript并生成89/89 static pages，新route明确为static。

React best-practices复核：新页是纯Server Component，JSON在module scope静态加载；没有client hooks、effect、hydration state、third-party bundle、data waterfall或重复network fetch。Existing social preview与metadata policy保持不变；B54 detail metadata单独设置title/description且清空继承image。按Sites验证边界，没有执行截图、DOM inspection、点击、resize或视觉QA。下一动作只提交推送page/CSS/navigation/Pages workflow与本entry；随后确认GitHub Pages exact source commit，并把同一validated source发布到owner-only Sites。

## J-278 · B54-E1 研究页双站点发布与重启断点

Date: 2026-08-28 · Type: PUBLICATION COMPLETE / OPERATIONAL CHECKPOINT · New Blender renders: 0

site source commit `ce092da0535f111f61cd87f3396f8489df9277b5` 已与 `origin/main` exact一致。GitHub Pages workflow `33178371484` completed/success且head SHA exact；公开B54 route返回HTTP 200：`https://lovejzzz.github.io/BlenderFilmStudio/admission-gated-native-compiler-v0-1/`。

同一source commit推送到Sites source repository，重新执行Vinext production build后用hosting helper打包成功；保存为version 80，archive content hash为 `sha256:822e8cf1c216f7f344ba44132b3fa23ded3624e4f56fc21c83c99cfb1f190bd5`，共374 files、28,999,680 bytes。deployment `appgdep_6a919669f5b481918869fbdbcf124e72` succeeded，owner-only exact route为 `https://blender-film-studio-research.skylab.chatgpt.site/admission-gated-native-compiler-v0-1/`。

发布前再次验证current user为owner、access mode为custom、exactly one allowed account且其role为owner、external visitors为0、workspace/tenant groups为空；owner-only route匿名请求返回HTTP 401。没有创建或刷新Sites screenshot，也没有执行截图、DOM、点击、resize或视觉QA。

用户准备升级并重启Codex，因此本次在publication checkpoint主动收口，不启动B55。B54-E1 scientific verdict保持封闭的 `ADMISSION_GATED_NATIVE_COMPILER_INTEGRATION_REJECTED`：编译器4/4、receipt 4×19、B01/B02 structure identity 2/2均通过，唯一失败是budget report未持久化native Blender PID。重启后的下一实验应先预登记最小supervisor PID-receipt correction，再修改 `scripts/lib/budgeted-process.mjs`；不得改写或重跑B54 evidence。用户原有 `README.md` 修改与三份未跟踪research drafts继续排除于本次提交之外。

## J-279 · B55-E1 budgeted native child PID receipt correction 预登记

Date: 2026-08-28 · Type: FORMAL PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

从J-278断点恢复后，重新确认repository HEAD与 `origin/main` exact为 `8acc451a9c2efc9ff49930d91d868c09d923d180`，B55 spec/protocol/三条tool paths和three roots全部不存在，production supervisor仍为SHA-256 `0c4cc332139d7e11bd33dccb0c340a3947851907fc02ab68b57be5275ec5ec40`。B54 results/audit/receipt file与self hashes exact；18 gates中exactly 17为true，唯一false gate仍是 `DIRECT_PROCESS_AND_SEMANTIC_OPERATION_COUNTS_EXACT`，`nativeCompilePidBindingsAvailable=false`。

B55冻结最小production intervention：只允许 `scripts/lib/budgeted-process.mjs` 把spawn返回的 `child.pid` 立即捕获为positive safe integer或null，并把 `BFS_BUDGETED_PROCESS_RESULT` 从0.1.0升级到0.2.0；budget validation、monitoring、termination、outcome mapping和所有旧字段必须保持。Restricted CLI、Blender compiler、CompileReceipt generator/verifier、BuildPlan compiler均以当前SHA冻结为unchanged controls。

Official zero-Blender preflight必须经corrected supervisor运行四种child-authored probe：PASS exit 0、CHILD_FAILED exit 7、WALL_TIME budget kill三种均要求child自写PID与report PID一致、child自写PPID与preflight PID一致；spawn error要求PID exact null。Accepted preflight commit/push后，formal runner才可relative-path admission并执行B01-A/B、B02-A/B四次fresh native compile。四份budget report必须为v0.2、positive native PIDs、exact Blender command与clean exit；每个native PID不得等于其同时存活的wrapper parent PID，但不要求非重叠运行的PID全局唯一，因为OS可在退出后复用。四份current verifier仍须各19 checks，B01/B02 plan/structure identities不可回退，independent audit至少拒绝32项attacks。

预登记前磁盘available为109,511,720,960 bytes；512 MiB projection后108,974,850,048 bytes，高于100 GiB reserve。未清理用户或历史证据。下一动作只能提交并推送exact spec、protocol与本entry；远端preregistration commit形成前不得修改supervisor、创建B55 tool byte、运行PID probe或创建B55 root。

## J-280 · B55-E1 PID receipt correction 隔离彩排与工具冻结候选

Date: 2026-08-28 · Type: ISOLATED NATIVE REHEARSAL / TOOL-FREEZE CANDIDATE · New Blender compilations: 4 · New Blender renders: 0

preregistration commit `bf62f9a02dbfb966f585a4c0e634da1e3507cd72` 与 `origin/main` exact后，production supervisor只发生三处冻结变化：spawn下一行立即规范化捕获 `child.pid`；result version从0.1.0升至0.2.0；既有child object前置新增pid。Independent minimality reconstruction从preregistration source逐项执行三次single replacement，before/current/expected hashes分别为 `0c4cc332139d7e11bd33dccb0c340a3947851907fc02ab68b57be5275ec5ec40` / `cda932ce86069524173066426365a5e8c60e0747c21187115d85defde5061c7d` / `cda932ce86069524173066426365a5e8c60e0747c21187115d85defde5061c7d`，3/3 replacement counts均exactly 1。

三工具development probes保持zero Blender：SceneSpec 22/22；B01/B02 dual in-memory BuildPlan canonical exact，plan hashes不变；relative component admission ACCEPTED且probe output未创建；512 MiB projection后仍高于100 GiB reserve。前三个稀疏fixture依次暴露测试装配缺少tracked `assets/`、research provenance与 `library/`：第一个因shell未fail-fast继续写出REJECTED zero-Blender preflight，后两个在development probe即退出；三者均未启动Blender、未创建formal root且分别完整删除，未在同一fixture修补续跑。

第四个fresh sparse fixture补齐全部冻结依赖后，official zero-Blender preflight 19/19 ACCEPTED。PASS、exit-7 CHILD_FAILED、WALL_TIME BUDGET_EXCEEDED三种Node child自写PID与supervisor receipt逐一exact，自写PPID均等于preflight PID；spawn-error case为v0.2 CHILD_FAILED、`child.pid=null`且spawnError非空。随后accepted preflight在isolated origin commit/push，relative-path formal admission通过，B01-A/B、B02-A/B四次fresh native Blender 5.2 compile全部PASS。

完整independent audit为22/22 gates、41/41 semantic attacks，formal rehearsal verdict `BUDGETED_NATIVE_CHILD_PID_RECEIPT_CORRECTION_SUPPORTED`。四份budget reports均为 `BFS_BUDGETED_PROCESS_RESULT@0.2.0`、positive safe-integer native PID、exact Blender command、exit 0、null signal/spawnError、termination unrequested，且各PID不等于同时存活的restricted wrapper parent PID；四份current CompileReceipt verifier各19 checks，并由receipt file SHA覆盖PID-bearing report。B01/B02 plan hashes与canonical structure pair identities保持 `316114...` / `a9022b...` 和 `c699fc...` / `025c6f...`；12/12顶层self-hashes、4/4 PID schemas、4/4 receipt budget bindings离线复算通过。Blender render、Cycles ray render、Docker/Colima、model与network均为0。

按supervisor、preflight、runner、auditor顺序的最终candidate SHA-256为 `cda932ce86069524173066426365a5e8c60e0747c21187115d85defde5061c7d`、`e1ffa80665c4174812a851f435b7360d92e538c39aa10c2c9bf8c8016180b557`、`b385f7867de97e50d4d135ce34b76a2ce91cda1d197fc1561c2e35b2b7538a5e`、`351b3ca54ecc5a2c90cd93c780518a1610af89c9f59522587c17659f06fcec60`；四文件Node syntax、targeted ESLint与diff checks通过。26 MiB最终fixture与此前owned rehearsal roots均已删除。下一动作只能提交推送这四条exact bytes与本entry形成tool-freeze；远端一致后才允许在real repository调用official preflight一次。

## J-281 · B55-E1 official zero-Blender PID preflight accepted

Date: 2026-08-28 · Type: FORMAL PREFLIGHT ACCEPTANCE · New Blender processes: 0 · New Blender renders: 0

tool-freeze commit `d36956299caa7067656d159533172809db1173a0` 与 `origin/main` exact、四条tool hashes与J-280一致且preflight/attempt/formal roots全部不存在后，只调用official preflight一次。结果为19/19 ACCEPTED：B54 parent的17/18与single PID gap exact；production supervisor before/current/expected hashes与3/3 single replacements exact；unchanged production controls exact；SceneSpec 22/22；B01/B02 dual BuildPlan canonical与frozen plan hashes exact；relative component admission accepted且未创建probe output。

四种正式PID probes全部通过。Preflight PID为81376；PASS child receipt/self-report为81399/81399、PPID 81376、exit 0；CHILD_FAILED为81403/81403、PPID 81376、exit 7；WALL_TIME为81407/81407、PPID 81376、`BUDGET_EXCEEDED`、breach `WALL_TIME`、termination requested/awaited；spawn-error为v0.2 `CHILD_FAILED`、PID exact null、exit -2且spawnError非空。四次budget calls中只有三次实际Node child spawn；Blender、render、Cycles ray render、Docker/Colima、model与network均为0。

观察到109,276,856,320 available bytes；512 MiB projection后108,739,985,408 bytes，高于100 GiB reserve。`preflight.json` file SHA-256 / self-hash为 `d74ee91ca4bc7db370cd5f5f4833435607d7b062a9e251e858e4406761514368` / `68bf69f562e4eebb950638713ffbfa224f4e4142bd5c328c348553d6b3e2b3f5`；`receipt.json` file SHA-256 / self-hash为 `59e657e428d4ba275976ab7caf78565546aa27d0d2ca69faeee488f5bf006c48` / `b740884ec4682b1743675666319f5d9748a2ea9d5fda05c4f05cc90e61b27840`。不import B55 tools的built-in-only readback复算两份self-hash均exact；attempt/formal roots仍不存在。

下一动作只能提交并推送exact accepted preflight root与本entry。确认其affecting commit在 `origin/main` 后，才可用冻结的repository-relative spellings调用formal runner一次；同一B55 ID禁止修复或重跑。

## J-282 · B55-E1 budgeted native child PID receipt formal result

Date: 2026-08-28 · Type: FORMAL NATIVE PROCESS-RECEIPT CORRECTION RESULT · New Blender compilations: 4 · New Blender renders: 0

accepted preflight affecting commit `37416bcf7540589ed9327e176868cb2aab1da65a` 与 `origin/main` exact、attempt/formal roots不存在后，只用冻结的repository-relative spellings调用formal runner一次。Runner先写sequence 1 attempt并独立重开accepted preflight语义；再由unchanged admission module写sequence 2 admission与sequence 3 receipt；sequence 4 formal-start绑定durable attempt receipt后才创建formal root并授权restricted compiler。无admission rejection或formal invalidation。

B01/B02各执行两次current `compileBuildPlan()`，canonical wrapper bytes pair-exact，plan hashes仍为 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` / `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`。B01-A/B、B02-A/B四个fresh outputs通过unchanged restricted CLI完成native Blender 5.2 compiles；wrapper/native PID分别为81627/81628、81641/81644、81653/81654、81662/81663。四份budget reports均为 `BFS_BUDGETED_PROCESS_RESULT@0.2.0`、PASS、exact Blender command、positive safe-integer child PID、exit 0、null signal/spawnError、termination unrequested，且PID不同于同时存活的wrapper parent。

四份current CompileReceipt verifier各PASS OK且19 checks，四份receipt file SHA逐一绑定包含PID的budget report；四份 `.blend` audit绑定exact planHash、structureHash、manifest version `0.2.0`与Blender build `fbe6228777e7`。B01 canonical structure A/B byte-exact且SHA-256 `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`；B02 A/B byte-exact且SHA-256 `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`。不要求 `.blend` container byte identity。

Independent auditor重新推导B54 exact single gap、三处minimal source transformation、官方四类PID probes、preflight Git push/admission、process records、receipts、structures与blend bindings；结果为22/22 gates、41/41 one-field semantic attacks，outcome-neutral formal verdict `BUDGETED_NATIVE_CHILD_PID_RECEIPT_CORRECTION_SUPPORTED`。Evidence boundary明确为 `SUPERVISOR_LOCAL_SPAWN_PID_CORROBORATED_BY_CHILD_AUTHORED_PREFLIGHT`：这是frozen supervisor对spawn event的本地receipt，不是cryptographic/remote attestation，PID退出后可被OS复用。Blender render、Cycles ray render、Docker/Colima、model与network均为0；无invalidation、`.blend1`、image或EXR outputs。

不import B55 tools的formal readback复算10/10顶层self-hashes通过。attempt、admission、attempt receipt、formal-start、plan observations、operation draft、audit、operation、results、formal receipt的file SHA-256依次为 `0c946195a15a8b7ca31ea83b03080d03b6289268c6fd05397c3e378a7a479e09`、`025d58e1806016cf323bbf915d49d8c4ad4b5b34e27a8ba2de664c319cb12cfe`、`bbb8748deb2bf02d76b8f819f228f99c3bdd873ee0139cd1868c59db9a39d724`、`37a94d2829c95a0511346d9da4fd190db76f666ab70431da76fac784a19be019`、`bc6acd71e88c8909b2b3ec6a27e483a0450a2a53fc672f975978cb8d52e1af20`、`d15e9898822f6876e9c8444282592ad53632191f202de8a5bba198d978521fc3`、`8f5ee5c33b3132494893d2294b3eee9ae4fd524c6a9f37c32fa13bd4763d9944`、`84f5c46ea4ca6ec5662fb4686936617e6ae20cfc0b3356dcccd61e3e059e9bb6`、`7e24d5a9ef6a948b73b98a3dbe9d2e970bdc553d7c217b30c43e7621efd93b7c`、`b8529364d0010fe218856f65fc0e5ec0e4fdf9dda7f61d35ca0bb8ee61476fe6`；对应self-hashes为 `a5b0773c09f782c7003e65d781cb272b5c738ce03de24095f79ecb74abd05b78`、`2c8654d24077e017a316f5d5ffba30eb210a6cc97afd5a379886f12e22ff238f`、`8f904bac15b50d2f8edb6f34ae2cb1332dbf84ed0270fee84538a7e3135b6e59`、`7dc88ac4a8599babe59e23ec12dea1c6f06f9705f24e1fcb7aa13ec71c24a0fe`、`41f04744e2cc3d4c28d3d7abcefd7310de054452ed3bfebfc9d7fd2eab34658a`、`9cc3806f4119e3aa102cb6356dff67c3b32cc63773156802feb2e1c2fd6f41bb`、`411fe96ab68b2c7916a44e6cf2b0a4c971a0298eee7090556a5f131adfa7a0d2`、`8d7b3147656972615f6a7137079838e91a76d59619651404c6855686e780cfa4`、`870043988767f80cad009a62c43f53b4935674c5e0ad71c122bc18277818f2dc`、`d70ea4ccadefd43f808787854960ab9034a352de9fa886ba811d9daa9c0dc8ae`。

首次离线blend readback误用不存在的 `status` 字段，正确读取所有文件但predicate返回false并以exit 1结束；未写或修改任何evidence。修正为document/version/scene/blender binding后，4/4 PID schemas、4/4 receipt-budget file bindings、4/4 verifier checks与4/4 blend bindings全部通过。B55-E1同一ID现已封闭，禁止修改或重跑。下一动作只提交推送exact attempt/formal roots与本entry；随后发布研究页，并以B55的claim boundary评估下一项production adoption缺口。

## J-283 · B55-E1 研究页升级重启前源码断点

Date: 2026-08-28 · Type: WEBSITE SOURCE CHECKPOINT / NOT YET PUBLISHED · New Blender renders: 0

用户准备升级并重启Codex，因此在完整production builds与双站点发布前主动收口。新增 `budgeted-native-child-pid-receipt-v0-1` 研究页源码，直接读取B55 frozen spec、official preflight、independent audit、results与formal receipt；页面展示三处最小supervisor correction、四类PID probe、四次formal native compile的wrapper/native PID、B01/B02 plan与structure identity、22/22 gates、41/41 attacks，以及“本地spawn receipt并非远程或密码学attestation”的claim boundary。首页加入B55 tab，B54页的next-step叙述更新为已观察到的B55 correction，GitHub Pages sparse checkout加入本页实际import的B55证据。

本地dev server曾成功热更新，收口时已明确停止。新B55页、B54页与首页的targeted ESLint为0 errors/0 warnings，`git diff --check`通过；没有执行production build、GitHub Pages deploy或Sites deploy，因此本entry不声称页面已发布，也没有做截图、DOM、点击、resize或视觉QA。重启后的exact恢复入口：先对该checkpoint commit运行Vinext/Sites build与GitHub Pages static build，再按source-commit exactness完成公开GitHub Pages和owner-only Sites双发布；发布完成后才预登记下一项production entry promotion实验。用户原有 `README.md` 修改与三份未跟踪research drafts继续排除于本次提交之外。

## J-284 · Codex内部浏览器重复崩溃与持久规避边界

Date: 2026-08-28 · Type: OPERATIONAL INCIDENT / CLIENT-STABILITY GUARD · New Blender renders: 0

在用户要求把大量内部浏览器标签清理到一个后，第一次实现错误地并发claim/close多个标签；Codex desktop随后于10:47:49崩溃。重启后再次尝试内部浏览器automation连接，应用于10:53:24第二次崩溃。两份macOS crash reports的SHA-256分别为 `ea125aa9336004a6c2119419f16307e953851d5481f29798266da80feafd1e6a` 与 `035649c3c49d8d95385f5221f968fd2824132d30184399ab204341542ef6d4b8`；二者均来自Codex `26.820.80927 (7271)`、均由thread 20 `Chrome_IOThread`触发、均为 `EXC_BREAKPOINT (SIGTRAP)` / signal 5，且crashed stack前七层symbol-relative offsets完全一致。该一致性支持“同一客户端browser-control failure mode复现”，但缺少未剥离符号和内部断言文本，因此不声称已经证明具体source-level root cause。

替代解释检查：`codesign --verify --deep --strict`通过，Gatekeeper判定为Notarized Developer ID；48 GiB机器无memory throttling，根卷仍有约89 GiB available；检查时没有Vinext/Vite listener或Blender进程。系统统一日志在第一次重启后的browser-control窗口记录CUA service bootstrap timeout与连续XPC connection interruptions。综合时间线与两次相同signature，当前最强可操作解释是内部浏览器automation并发关闭及其重连路径触发客户端不变量失败，而不是Blender、网站source、磁盘耗尽、内存压力或app bundle损坏。

新增repository-root `AGENTS.md` 作为跨会话持久guard：在Codex app版本变化或用户明确授权controlled retest之前，本repo禁止in-app browser automation和browser-target `open_in_codex`；保持最多一个用户可见BlenderFilmStudio标签；不得并发或批量close；验证改用build及non-browser HTTP。Guard启用后未再调用browser tools。随后在不启动dev/HMR listener的条件下，Vinext production build成功并发现88个CDN warmup paths；GitHub Pages production build通过TypeScript并生成90/90 static pages，B55 route在两种build中均存在。该build结果证明网站source可编译，不证明客户端缺陷已被上游修复；当前结论是已建立可持续规避，不是修复Codex二进制。

## J-285 · B55-E1 研究页双站点发布完成

Date: 2026-08-28 · Type: PUBLICATION COMPLETE / NON-BROWSER VERIFICATION · New Blender renders: 0

包含B55页面和client-stability guard的source commit `b175edb631f88020033526b56430b27980c5fae9` 与 `origin/main` exact一致。GitHub Pages workflow `33182974561` 的build与deploy均completed/success、head SHA exact；公开B55 route与B54 parent route均返回HTTP 200。公开B55 URL为 `https://lovejzzz.github.io/BlenderFilmStudio/budgeted-native-child-pid-receipt-v0-1/`。

同一source commit推送到Sites source repository，并在journal变更后重新执行Vinext production build，继续发现88个CDN warmup paths。hosting helper打包后保存为version 81；server archive content hash为 `sha256:e70dc64f39b3d1f0039894d0bbf1b98ef74155f4f4702e97b3c61f3848a960f5`，共375 files、29,143,040 bytes。Owner-only deployment `appgdep_6a91a37217f88191afa5142ff6e15401` succeeded。发布前access重新验证为current user owner、custom mode、exactly one allowed account且其role为owner、external visitors为0、workspace/tenant groups均为空；发布后exact B55 route匿名请求返回HTTP 401，携带站点自身owner bypass credential的non-browser请求返回HTTP 200。Owner-only URL为 `https://blender-film-studio-research.skylab.chatgpt.site/budgeted-native-child-pid-receipt-v0-1/`。

为遵守J-284 guard，没有执行browser handoff、截图、DOM、点击、resize或视觉QA，唯一用户可见标签保持不新增。临时24 MiB发布archive目录已移动到用户Trash，可恢复且可由exact source重新生成。Guard启用后当前Codex main process连续运行超过9分钟，已经越过第二次同signature crash的约5分15秒复现窗口，且没有新ChatGPT diagnostic report；这支持规避措施有效，但不扩大为上游binary defect已修复。B55-E1 publication至此封闭。下一项有证据支持的缺口是把B54/B55验证过的admission、budgeted process与receipt语义提升为production compiler首选入口；必须先做新ID预登记，不能把实验专用runner直接冒充production interface。
## J-286 · 主机磁盘容量门恢复与精确缓存清理

Date: 2026-08-28 · Type: OPERATIONAL CAPACITY INTERVENTION · New Blender processes: 0 · New Blender renders: 0

新goal生效后的首个生产入口预检观察available 98,323,091,456 bytes；100 GiB冻结reserve加512 MiB projected write共需107,911,053,312 bytes，shortfall为9,587,961,856 bytes，因此B56不得预登记后继续执行。只读审计确认12 GiB Hugging Face cache由Qwen等模型占用，LTX-Video本体已不存在，仅余0-byte lock；Colima 24 GiB包含当前BFS Blender worker与GPT Bot profiles；repo experiments约18 GiB属于不可删除科研证据。

沿用用户此前“授权清理缓存并扩容 Colima”及明确删除LTX的授权，只清空六个精确、可重建cache targets：Adobe 3,206,708 KiB、Video Village plugin downloads 2,637,572 KiB、Adobe Camera Raw 1,169,088 KiB、Telegram 926,880 KiB、Google 550,972 KiB与Codex workspace dependencies 1,619,196 KiB。没有删除Qwen、BFS Blender worker image、任何Colima profile、repo evidence或用户工作树文件。清理后available为108,449,669,120 bytes；扣除512 MiB后为107,912,798,208 bytes，高于100 GiB reserve 538,615,808 bytes，unchanged gate为PASS。既有`scripts/disk-space-guard.mjs`保持fail-closed且default projected write仍为20 GiB；没有降低reserve或新增automatic deletion。

## J-287 · B56-E1 production compiler entry promotion 预登记

Date: 2026-08-28 · Type: FORMAL PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

B55-E1 formal evidence commit `e3bf6c1d71cd5c931d0937c12e647331851c436f` 仍为22/22 gates、41/41 attacks和四次native compile通过；results/audit/receipt file SHA-256分别为 `7e24d5a9ef6a948b73b98a3dbe9d2e970bdc553d7c217b30c43e7621efd93b7c`、`8f5ee5c33b3132494893d2294b3eee9ae4fd524c6a9f37c32fa13bd4763d9944`、`b8529364d0010fe218856f65fc0e5ec0e4fdf9dda7f61d35ca0bb8ee61476fe6`。当前package只暴露`compile:plan`、低层`compile:restricted`与`verify:receipt`，三个production aliases与五条production paths均不存在；B54/B55 runner是single-use evidence tool，不能冒充可复用production API。

B56冻结一个additive release layer：新增release manifest、production preflight/runner/receipt library/verifier和exactly three package aliases，既有formal admission、budget supervisor v0.2、restricted compiler、BuildPlan compiler、CompileReceipt generator/verifier、Blender compiler/auditor保持exact hash。Production sequence必须是pushed zero-Blender preflight → fsynced attempt → admission → fsynced receipt → output materialization → immutable BuildPlan → exactly one restricted compile → production receipt → independent verifier；拒绝路径必须zero Blender且不创建requested output。

Formal matrix冻结B01-A/B、B02-A/B四次preferred alias invocation，四份current CompileReceipt各19 checks、四份positive native PID、B01/B02 plan/structure pair identity、四份blend binding、zero render/model/network/Docker与至少48项semantic attacks。512 MiB projection后仍须保留100 GiB；预登记观察available为108,446,367,744 bytes。下一动作只能提交并推送exact spec、protocol与本entry；远端preregistration commit形成前不得创建release manifest、package aliases、B56 tool byte或任何B56 output root。

## J-288 · B56-E1 production entry 全链隔离彩排与tool-freeze候选

Date: 2026-08-28 · Type: ISOLATED FULL REHEARSAL / TOOL-FREEZE CANDIDATE · New Blender compilations: 6 · New Blender renders: 0

preregistration commit `b9cf983abb3e741b5a7726200e9082bc50e1a89d` 与 `origin/main` exact后，才新增release manifest、四条production paths、三条B56 tools与exactly three package aliases。Production receipt library统一实现strict repo-relative paths、exclusive create、file/directory fsync、canonical self-hash及authorization/BuildPlan/budget/CompileReceipt/manifest/structure/blend bindings；production runner在sequence 1 attempt、2 admission、3 receipt全部fsync后才materialize output并写sequence 4 formal-start；production verifier不import runner，外部执行current receipt verifier与冻结Blender artifact auditor。

两个早期隔离装配失败均发生在Blender之前：full clone没有`node_modules`导致AJV import失败；补依赖后，full checkout占用空间使真实100 GiB reserve gate返回`DISK_ADMISSION`。该1.5 GiB临时clone随即精确删除，主机gate恢复。改用只含工具、B01依赖与父证据的sparse clone后，production preflight ACCEPTED；首个真实B01 compile完成但production receipt拒绝existing compiler生成的空`frames/`目录。Candidate correction没有放宽output roster：只在该目录被证明为空时删除它，任何frame entry仍fail-closed；失败开发路径不复用，改用C1 fresh roots。

C1单链彩排通过：authorization sequence为1/2/3/4，B01 plan/structure hashes保持 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` / `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`，wrapper/native PID为65282/65283，current CompileReceipt 19 checks和production verifier 10 checks均PASS。随后完整B56 sparse rehearsal通过15/15 zero-Blender preflight、9/9 fail-closed negative cases、四次preferred production compiles、四次verifiers、27/27 gates与64/64 attacks；四组wrapper/native PID为69477/69480、69589/69593、69703/69706、69817/69820。B01/B02 pair plan与structure identities exact，render/model/network/Docker为0。

最终candidate按release manifest、production preflight/runner/receipt library/verifier、B56 preflight/runner/auditor顺序的SHA-256为 `010cb8bbfc4acd56c1f766cf014b1bdbf9652b3d35f92ed89e8891a51a8e43cf`、`e2a542b318d0c29ad4f23fccfea7dc3b28d65a489e69e90f4b0418dc621de4d2`、`ab5f9b2d73e6f60235dd5b07c68540bd49f0649dac2078a203cdc39703352fc6`、`e695fb624faec50991af301f91e9dfb3fcd8dc04e6bdced642710377aa7f90cd`、`c2ce9bb630a1104c92aae216914743946ca20ca6acf1e6e089002d68c30f943c`、`6f5c596c15dc8734ace1d1d8264dee9ec179795d5e9af6e990128db5a798bf4f`、`bc0c5d4e5b65cf9aa6ba35a1a75d5f10618948ed0726fd8b3c68e07ce9ba9c1b`、`93f87f429e03c253e871f4f2b9aab0bcdba094539ff050946c8fdb939c5f1d0a`。全部Node syntax、targeted ESLint、release 29-file hash replay与diff checks通过；full rehearsal 17 MiB fixture已删除，主仓库preflight/attempt/formal roots仍全部不存在。下一动作只提交推送exact package、八candidate paths与本entry形成tool-freeze；远端一致后才允许创建official preflight root。

## J-289 · B56-E1 official zero-Blender production preflight accepted

Date: 2026-08-28 · Type: FORMAL PREFLIGHT ACCEPTANCE · New Blender processes: 0 · New Blender renders: 0

tool-freeze commit `dc33df91984254c6f44d2447eba788f1eac241b7` 与 `origin/main` exact、三类正式roots全部不存在后，只调用official B56 preflight一次。结果15/15 ACCEPTED：B55 parent evidence、preregistration absence、package exactly-three-alias delta、release 29-file freeze、七条new tool bytes、Node/Blender binary hashes、22/22 SceneSpec suite、B01/B02 dual in-memory BuildPlan pair、100 GiB reserve以及root freshness全部通过。

四次preferred `preflight:production` aliases均zero Blender并各自ACCEPTED：B01-A/B plan hash为 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`，B02-A/B为 `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`；四份output spelling分别绑定formal root下对应run。隔离sparse fixtures中的9/9 negative cases全部fail-closed且zero Blender：absolute/outside/symlink/existing output、deterministic low-disk ceiling、dirty tool、dirty SceneSpec、unpushed release与post-preflight output swap。所有fixture在观测后删除。

Preflight观察available 108,942,209,024 bytes；512 MiB projection后108,405,338,112 bytes，高于107,374,182,400-byte reserve。Meta `preflight.json` file SHA/self-hash为 `c1dd738761ba79fb501a7a250f4979128d9a01c086b305a77fcec30227f1a6fc` / `8d61d9b56bf216ce54e18fa33fa7ba1237ca64cdb4ed39a5600d1b170ad8e838`；`receipt.json` file SHA/self-hash为 `2c0fb14aaa479e2ecd9cea5ff12b0be1490fc8018277b50754f9f3f339f974df` / `6a9573a710b43ae74528bc120d409b5adf73cf86d71176e9759fcc429f7775db`。Built-in-only readback复算六份self-hash全部exact；attempt/formal roots仍不存在。下一动作只提交推送exact accepted preflight root与本entry；其affecting commit进入`origin/main`之前不得调用formal runner。

## J-290 · B56-E1 production compiler entry promotion formal result

Date: 2026-08-28 · Type: FORMAL PRODUCTION ENTRY PROMOTION RESULT · New Blender compilations: 4 · New Blender renders: 0

accepted preflight evidence commit `5c7aaa197f523ab3afc96c21a3e06f1669015ada` 与 `origin/main` exact、attempt/formal roots不存在后，只调用single-use B56 runner一次。Meta runner先fsync sequence-1 attempt，经unchanged admission module验证pushed preflight后fsync sequence-2 admission与sequence-3 receipt；只有随后才materialize formal root并fsync sequence-4 formal-start。四个production wrapper分别重复同样的attempt/admission/receipt/output顺序，没有admission rejection或formal invalidation。

B01-A/B、B02-A/B四次preferred `compile:production` aliases全部PASS；wrapper/native Blender PID分别为75379/75382、75496/75499、75613/75617、75739/75742。四份budget report均为`BFS_BUDGETED_PROCESS_RESULT@0.2.0`、positive native PID、exact Blender command、exit 0、null signal/spawnError，且native PID不同于同时存活的wrapper PID。每次existing compiler生成的empty zero-render `frames/` directory都只在empty proof后移除；正式输出root roster为build-plan/formal-start/production-receipt/restricted，restricted roster严格为budget report、current CompileReceipt、`.blend`、manifest与canonical structure。

四次preferred `verify:production-receipt` aliases均10/10 checks PASS；其内部current CompileReceipt verifier各19 checks，并由四个真实Blender artifact auditor重新读取`.blend` embedded plan/structure/manifest-version/build-hash bindings。B01 plan/structure A/B byte exact且保持 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` / `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`；B02保持 `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687` / `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`。四份production receipt file SHA依次为 `1c34aadd00cdfb6f23e5b4cd2cc454dbf4784352e60dad5ced0b9bd7f7049977`、`9baa0090cc1816daa8b1f708632a90f0d1ad7fce71c5ca482c6e1e84d8153935`、`0f088d823ad9d5fc4adbca57251c1081689c96bafa97e113c72c2bf970dc6493`、`6f8700cf846aa2c933a486ca5656c38e5d9e9610fe1898fccba48a89568992f2`，self-hash全部exact。

Independent auditor不import production/B56 execution modules，直接重开所有source/evidence bytes、package/release hashes、Git ancestry、authorization files、BuildPlans、budget reports、current receipts、manifests、canonical structures与verifier内保存的Blender audit records。正式结论为 `PRODUCTION_COMPILER_ENTRY_PROMOTION_SUPPORTED`，27/27 gates与64/64 one-field semantic attacks通过；operation counts为4 preferred compiles、4 production wrappers、4 native compiles、4 current receipt verifiers、4 preferred verifiers、4 blend audits、1 meta runner与1 independent auditor。Blender render、Cycles ray render、image/EXR/video、model、network、Docker/Colima均为0；只有四份`.blend`，没有`.blend1`。

Attempt/admission/attempt-receipt file SHA/self-hash为 `ece54da746c63fe33845054553e1ecd674c53d263005af01eafd0078b2494b7e` / `4f4ba9a26bbc81dc93b5f185764a1f37295affc214834548ebfd651e619d2f84`、`43d462638dc4ff16665241f2f92e5ded2a8ecb113a48e13f8922d814e022cb66` / `ba3cddd1d88e65fb08d768b5e971940b2e348f9713b9dd604f70e32cb972bbce`、`e9490f979404a548ebaf184dcfb71d08ccf7cbdc4022143b17f8d98ff2a6fd4f` / `743e0823666ceb689d5d94397fcfcd2e666423d91d56bbe3f5a767d0458da1c9`。Formal-start/audit/results/operation/receipt file SHA/self-hash分别为 `b41d67d1468ce8ce06b1964b1dd3ee2234108a86931e382b224257f6adfea06d` / `d6f65e90224cf00030047fbdbe004b182425ae0c5b6dbbe205543e931fa68af1`、`41281dd92f1833e4ca5f549713c81a7ce01aa157a30f898d3728f1dc3b193c79` / `07e829a8ecf4480e62784e5c161241d38d9cbb7e83efee1f15a116a64b282328`、`9a55513ac1e2aa049a392e122c1a9b09866f74808151b1918061750d6cbec228` / `cb9fe4260c97b8ba2cf12537a2bbfe10f90495c642cca89ce8154527ec49479d`、`ceb8c18fbc88b7d57d7ac819f9f8c654bab6ab2aa7dd4ad2a4dbf9dbb00e7c50` / `e029af57247edc7e8e2fe737adb0f4560935400f02377e5fd37f8b83feade148`、`4d9979160a70d06cde416f35526d8dab0e08d5680fd7205b87162210e554693d` / `c9508dfa04c08ea1c713176668f94574d87e62856e27008703957aa05ef38d04`。Built-in-only readback复算9/9顶层self-hashes、4/4 production receipts与全部rosters通过。B56-E1同一ID现已封闭，禁止修改或重跑；下一动作只提交推送exact evidence与本entry，然后发布研究页。

本次SUPPORTED只证明preferred production entry在冻结preflight到紧随其后的formal run边界内成立。Production runner本身尚未在native compile前重新观察disk；若accepted preflight长期搁置，host free space可能在两者之间变化。该TOCTOU不是B56已注册gate，不能事后改判B56，但必须作为发布后的下一项separately preregistered production-safety correction，且不得降低100 GiB reserve。

## J-291 · B56-E1 研究页双站点发布完成

Date: 2026-08-28 · Type: PUBLICATION COMPLETE / NON-BROWSER VERIFICATION · New Blender renders: 0

B56 evidence已在commit `208a898394b856409fc09685605b31014c2a41df`推送后保持封闭；研究页source commit `4e9598c20ef7984bb496bc0ef52fdff9cf5dcacb` 与 `origin/main` exact。页面直接读取frozen promotion spec、release manifest、official preflight、results、audit与formal receipt，展示three preferred aliases、seven-step authorization、4/4 native compiles、27/27 gates、64/64 attacks、B01/B02 plan/structure identities与zero-render claim boundary；B55页、homepage、web journal和Pages sparse checkout同步链接B56。

Targeted ESLint、TypeScript、GitHub Pages 91-route static build与Vinext/Sites production build全部通过。GitHub Pages workflow `33187954821` 的build/deploy completed/success，公开exact route `https://lovejzzz.github.io/BlenderFilmStudio/production-compiler-entry-promotion-v0-1/` 返回HTTP 200并包含`27 PASS + 0 FAIL`与`disk TOCTOU`边界。

同一source commit推送到Sites source repository，hosting helper archive保存为version 82；server archive content hash为 `sha256:2eb0f39218e871da0fa3ba9065adc7ef2dc00e6a5a34688cc35428fed235d753`，共376 files、29,245,440 bytes。Owner-only deployment `appgdep_6a91b167fe108191868ca306cdac536a` succeeded，exact route为 `https://blender-film-studio-research.skylab.chatgpt.site/production-compiler-entry-promotion-v0-1/`；发布前重新验证current user owner、custom access、exactly one allowed owner account、external visitors 0、workspace/tenant groups empty，匿名route返回HTTP 401。

遵守J-284 crash guard，没有browser handoff、截图、DOM、点击、resize或视觉QA，也没有新增用户可见tab。临时发布archive已精确删除；用户README修改和三份未跟踪research drafts未被stage。B56 publication至此封闭，下一实验只处理已公开的native-spawn前disk TOCTOU。

## J-292 · B57-E1 native-compile disk JIT readmission 预登记

Date: 2026-08-28 · Type: FORMAL PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

B57 machine-readable spec与human protocol SHA-256分别为 `fa91173f1e824b8b9f1689d401586100a04e2632817895f6e209ace007833ecf` / `6258f7fe6880842ab54dcc40a729b9fc377d24c92e587a8ffd322400754b0ff0`。

B56-E1 parent保持`PRODUCTION_COMPILER_ENTRY_PROMOTION_SUPPORTED`、27/27 gates、64/64 attacks、4 native compiles与0 renders；results/audit/receipt file SHA分别为 `9a55513ac1e2aa049a392e122c1a9b09866f74808151b1918061750d6cbec228`、`41281dd92f1833e4ca5f549713c81a7ce01aa157a30f898d3728f1dc3b193c79`、`4d9979160a70d06cde416f35526d8dab0e08d5680fd7205b87162210e554693d`。Current v0.1 release、preflight、runner、receipt library、verifier与package before hashes冻结为 `010cb8…`、`e2a542…`、`ab5f9b…`、`e695fb…`、`c2ce9b…`、`a2235a…`；v0.1 release必须保留为B56 evidence。

B57只修复一个因果缺口：accepted preflight的disk observation可能在formal invocation前过期。冻结intervention是在immutable BuildPlan持久化后、restricted wrapper spawn前重新`statfs(repositoryRoot)`，继续使用100 GiB reserve与0.5 GiB projected write、禁止override，并先fsync sequence-5 `native-compile-disk-admission.json`。Accepted decision必须由升级后的production receipt/verifier绑定；rejected decision必须保留self-hashed disk record与invalidation，restricted/native process count为0。

正式负例冻结为正常accepted preflight之后把effective available ceiling设为107,911,053,311 bytes，即required reserve+projection少1 byte；ceiling只能降低真实观察，不能制造acceptance。正式正例仍为B01-A/B、B02-A/B四个fresh preferred-alias compiles，并要求四份JIT disk admission、四份production verifier、四份19-check current receipt、native PID、plan/structure/blend bindings全部通过；render/model/network/Docker为0。Independent auditor不得import execution modules，至少拒绝56项semantic attacks；26-gate outcome mapping已在spec/protocol中冻结。

预登记时repository filesystem available为108,723,322,880 bytes，projection后108,186,451,968 bytes，高于107,374,182,400-byte reserve。下一动作只能提交并推送exact spec、protocol与本entry形成preregistration commit；远端一致前不得创建v0.2 release、修改production tool byte或创建任何B57 root。

## J-293 · B57 v0.2 release与JIT disk receipt实现候选

Date: 2026-08-28 · Type: DEVELOPMENT IMPLEMENTATION CANDIDATE · New Blender processes: 0 · New Blender renders: 0

Preregistration commit `c9e0b9e25c41b751fb456cf115e29e63996dbea4` 与 `origin/main` exact后才创建additive `production-compiler-entry.v0.2.json`并修改四条production implementation paths；v0.1 release SHA仍exact `010cb8bbfc4acd56c1f766cf014b1bdbf9652b3d35f92ed89e8891a51a8e43cf`。三个package aliases与全部unchanged controls保持原hash。

Runner候选在BuildPlan durable write之后把phase设为`NATIVE_COMPILE_DISK_ADMISSION`，真实`statfs(repositoryRoot)`后使用冻结100 GiB reserve与0.5 GiB projection，先exclusive-create/fsync sequence-5 disk admission，再允许restricted wrapper spawn。Test ceiling只接受non-negative且不高于real observation的整数；非法或raise ceiling都写REJECTED。Receipt升级为`bfs.productionCompileReceipt.v0.2`，root roster加入disk admission，并绑定file SHA、自哈希、real/effective bytes、ceiling flag与policy；independent production verifier增加`NATIVE_COMPILE_DISK_READMISSION`检查。

v0.2 release冻结31 files且全量SHA replay 31/31 exact；release/preflight/runner/receipt/verifier candidate SHA依次为 `c5dc72a3a30c67d3cfeee1cd9c0fc07fa438fa466e9bff587d3e7e7dd2c74311`、`48adeb62acbdb4f0dc250c93a9a3b69dda7a489743d0538ea14a53b6a0386b11`、`05ae75819a4b1517c3a68345ac1d64b0cea2fd6d3f3891a887bea917c2785466`、`039ff78c7c9129d0c34a2980ed9c28c1c49fe7320085d73a179ab7aa89ff0d46`、`17bf7e0a99faeba01f688e1df518b356fe54d66fa331052a1fed2323c4e15f1c`。四文件Node syntax、targeted ESLint与diff check通过；未创建B57 root、未运行preflight或Blender。下一动作先提交推送candidate，随后只在fresh development roots验证正常与one-byte-below路径；发现缺陷必须保留反例并换fresh root。

## J-294 · B57 one-byte-below development preflight accepted

Date: 2026-08-28 · Type: DEVELOPMENT PREFLIGHT EVIDENCE · New Blender processes: 0 · New Blender renders: 0

Implementation candidate commit `968cc709f02721a623a85e816b4a071d6d1824db` 与 `origin/main` exact后，为冻结的低磁盘development case创建fresh preflight，绑定B01 SceneSpec、fresh output `experiments/b57-jit-development-low-output-v0-1`与v0.2 release commit。Preferred `preflight:production` 返回ACCEPTED，BuildPlan hash保持 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`；真实available 108,625,825,792 bytes，projection后108,088,954,880 bytes，高于100 GiB reserve。Blender/render/model/network/Docker均为0。

Preflight file SHA/self-hash为 `a6a87093a237500de8aebb3b94767379e401c6022298795ef14eabf523db042f` / `68aef97d8f9a68a2c7a70adb077cc06bed1396af63a09292efc24a91fb650bf8`；requested output与attempt root仍不存在。下一动作只提交推送该accepted development evidence与本entry；随后以exact evidence commit调用production runner一次，并将JIT ceiling固定为107,911,053,311 bytes。Expected outcome是`NATIVE_COMPILE_DISK_ADMISSION` invalidation、restricted/native process 0，不是compile PASS。

## J-295 · 首个low-disk调用因手写commit身份失效

Date: 2026-08-28 · Type: DEVELOPMENT ASSEMBLY FAILURE · New Blender processes: 0 · New Blender renders: 0

Accepted preflight evidence推送后，首次runner调用错误地使用了手写full SHA `fb1899ec3965db8704d92fd45a6635e44b366184`，真实commit为 `fb1899ee01e3df2bd0690c93ba5a0df007235c6e`。Unchanged formal admission在output materialization前返回`EVIDENCE_COMMIT_MISMATCH`，因此没有创建requested output、BuildPlan或disk admission，Blender=0。该结果不能用于B57磁盘假设。

失败attempt root保留sequence-1 attempt、sequence-2 failure与sequence-3 rejected receipt，自哈希分别为 `409ff7b46a6bdd7a93739b35575dcae609b07e831e4e51e3b4811cd9af44bed2`、`38d350d63bb1299a6fb81ba1d23476fc81682b4202b371bcb03f7ce346fd5601`、`b517095b7d679a375e0bf9a667f09a3b472f39c6c89d5eb6d25d848e21c86830`。没有在原attempt root修补；下一调用只允许使用Git读取的exact SHA与fresh C1 attempt root，同时保持同一accepted preflight及尚未创建的bound output。

## J-296 · one-byte-below JIT disk gate在spawn前拒绝

Date: 2026-08-28 · Type: DEVELOPMENT CAUSAL PROBE · New restricted compiler processes: 0 · New Blender processes: 0 · New Blender renders: 0

C1使用exact pushed evidence commit与fresh attempt root后，通过sequence 1/2/3 admission并materialize authorized output；formal-start sequence 4和B01 immutable BuildPlan写盘后，runner真实观察available 108,622,110,720 bytes，再应用冻结ceiling 107,911,053,311 bytes。扣除536,870,912 projected bytes后为107,374,182,399，exactly低于100 GiB reserve 1 byte。

Sequence-5 disk admission因此durably写为REJECTED、reason `FREE_AFTER_PROJECTED_WRITE_BELOW_RESERVE`，disk self-hash `6873e1118f8417b9ccc4d42bc7321c2ad724735252cae81015a8f3288d6c66e2`；随后invalidation phase exact `NATIVE_COMPILE_DISK_ADMISSION`、self-hash `9716473700daf9142639b2a753ffb199400186d52c5ec8a112154793fd5844ef`。Output roster exact为BuildPlan、formal-start、disk admission与invalidation；`restricted/`不存在，restricted wrapper与native Blender processes均0。该development probe支持核心fail-closed因果路径，但尚未验证正常capacity compile、production receipt v0.2或independent B57 audit，因此不写formal verdict。

## J-297 · B57 normal-capacity development preflight accepted

Date: 2026-08-28 · Type: DEVELOPMENT PREFLIGHT EVIDENCE · New Blender processes: 0 · New Blender renders: 0

在low-disk development evidence commit `4af2456`推送后，为对称正常路径创建fresh B01 preflight/output binding，release仍指向未变的implementation candidate `968cc709f02721a623a85e816b4a071d6d1824db`。Preferred preflight ACCEPTED，plan hash `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`；available 108,587,016,192 bytes，projection后108,050,145,280 bytes，Blender/render/model/network/Docker为0。Preflight file SHA/self-hash为 `4a80b853af5aecca94c6a110627b700bf172f60e5f71c5ea542e8732af5924a5` / `51973f0b2b1fe68f4b2a766bf143a84f8187aaa0bb8bcdd264cbe405e9776acc`。下一动作先推送该evidence，再以fresh attempt执行一次正常capacity real Blender compile并调用preferred verifier。

## J-298 · B57 normal-capacity real Blender development chain通过

Date: 2026-08-28 · Type: DEVELOPMENT REAL-BLENDER INTEGRATION PROBE · New Blender compilations: 1 · New Blender renders: 0

Accepted pass-path preflight evidence commit `d9a6187323470a2e6bac5ece5da1239e55008cab` 与 `origin/main` exact后，preferred `compile:production`在fresh attempt/output完成真实Blender 5.2 B01 compile。JIT时真实available/effective均为108,584,042,496 bytes，sequence-5 disk admission ACCEPTED，自哈希 `09535de98cf25e708dd3c98e4e00213f8ae57c929e85b2a4fee4bc5a0129eb25`，file SHA `76228c291f5f1c50ea84dda186222f115dddfaf3c7bd5e3fae6f46fd5ef8a321`；wrapper/native PID为13695/13699。

Production receipt schema为v0.2，file SHA/self-hash `bf4e22aef036e7093b02eb1f8d583c46e9fc7e2b9b0a3fa8d99762db286b1b35` / `cd34662fc21c940b2620482978b2ae6e4bb916ea74e06fa3f9234025f1697ad6`。Preferred verifier 11/11 checks PASS，其中新增`NATIVE_COMPILE_DISK_READMISSION`；其内部unchanged current CompileReceipt仍19/19。B01 plan/structure保持 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` / `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`，`.blend` audit绑定Blender build `fbe6228777e7`。Output roster含exact disk record且无frames/、`.blend1`、image或render；model/network/Docker为0。

两条development causal paths现已同时成立：差1 byte在spawn前拒绝，真实capacity完成receipt-bound compile。但这仍不是B57 formal verdict；还缺B57 single-use preflight/runner/independent auditor、完整B01/B02四-run矩阵、至少56 attacks与26-gate mapping。下一动作只提交推送development evidence，再实现这些正式工具并重新冻结hashes。

## J-299 · B57 single-use formal tools实现候选

Date: 2026-08-28 · Type: FORMAL TOOLING CANDIDATE / NOT YET FROZEN · New Blender processes: 0 · New Blender renders: 0

在development pass/blocked evidence全部推送后，新增三条B57 single-use tools。Preflight冻结B56 parent、v0.1 preserved release、v0.2 31-file release、三条B57 tool bytes、22/22 SceneSpec、B01/B02 dual BuildPlan、真实disk与one-byte boundary，并创建五份zero-Blender production preflight，分别绑定LOW-DISK与B01-A/B、B02-A/B未来输出。Formal runner使用meta attempt/admission/receipt/formal-start后先运行LOW-DISK，再依次运行四个preferred compile/verifier aliases，写operation draft后spawn独立auditor。Auditor只import Node built-ins，不import production或B57 execution modules，直接重开evidence并执行26-gate mapping与四run×14 mutations共56 attacks。

Candidate preflight/runner/auditor SHA-256分别为 `0bb66d85f1c168c98c258cba29465a52b62eeda43df29fafa8a9aca1260a4cc9`、`a7c0df0ff83516079ff4155d08fe5ed42d08e599c2c9f480b480995b0a7baa22`、`eb8f3ebfe9fb018db3f89cb502672939a56f367307f0bebd2ad5fa928ca9f713`；Node syntax、targeted ESLint与diff check通过。正式三根仍不存在。本entry不把静态检查写成tool freeze：下一动作先提交推送candidate，再在三组非正式fresh roots完整彩排；任何failure保留摘要并以新root重跑，只有稳定后的最终bytes才允许标记tool-freeze。

## J-300 · B57 formal preflight rehearsal与SHA装配反例

Date: 2026-08-28 · Type: ISOLATED FORMAL-PREFLIGHT REHEARSAL · New Blender processes: 0 · New Blender renders: 0

Candidate commit实际SHA为 `2e5cb9cb975fa4751c9c786ecb3a691cd6cd50e6`。首轮命令却再次手写了错误full SHA，meta preflight因此9/12 REJECTED：tool-freeze、release/tool freeze与five production preflights三项失败；五份nested production preflight全部在release identity层拒绝，Blender=0。Rejected meta file SHA/self-hash为 `eaaae73c8f436f6cbf7dad58f009cc32a4ec35059b4b9bbfcf2d3058adebfed5` / `48ffbe4df96f7282acb26bf68fde97552161b7eba844e9e7aaf9bbe97add633c`。该root保留，不在原ID修补。

C1使用Git读取的exact SHA与三组fresh roots后，B57 meta preflight 12/12 ACCEPTED；B56 parent、v0.1/v0.2 releases、31 frozen files、三条B57 tools、aliases、SceneSpec 22/22、B01/B02 BuildPlan pair、real disk与one-byte boundary全部exact。LOW-DISK、B01-A/B、B02-A/B五份preferred production preflight均ACCEPTED且zero Blender。C1 meta file SHA/self-hash为 `2fd94d2f370d1d641b0ee73492b8b845632077315cafe5b58abcd8590f79af15` / `3a20692c0af81fba792aa96dc31704fe4c0fdfb24d579d910ddda3829df89077`。正式B57 roots继续不存在。下一动作先推送rehearsal preflight evidence，再用C1 bound attempt/formal roots运行完整single-use runner；该运行仍是rehearsal，不是official B57。

## J-301 · B57 formal rehearsal在meta tool-hash接口前拒绝

Date: 2026-08-28 · Type: REHEARSAL ADMISSION FAILURE / MECHANICAL CORRECTION · New Blender processes: 0 · New Blender renders: 0

C1 accepted rehearsal preflight evidence commit `eb72f8d835e5c5a6293573106c843cd0b26ff14f` 与 `origin/main` exact后，single-use runner创建sequence-1 meta attempt，但unchanged `admitFormalRun()`立即返回`TOOL_HASH`，formal root保持不存在、Blender=0。原因是B57 meta preflight只保存了`toolFreeze.hashes`，而既有admission contract要求同一映射同时投影到顶层`toolHashes`；因此不是JIT磁盘假设或production compile失败。

Rejected attempt/failure/receipt file SHA分别为 `b895eee2904879954f7b0c2e9ad6bf739d05f45fbbcb0dd101fb7fcc34fdad40`、`0138f9b00a130b8e2bd6c899db4ef72820921df4c4716ff15b95ef4e7e3c98db`、`d82065faa6a767ac60c0527d11d80480463359ed53af93b3fe02327bbadb8a5b`，失败root保留。唯一correction是在meta preflight body增加`toolHashes: toolFreeze.hashes`，不改变任何hash集合、实验门、生产release或runner/auditor语义。该修改使preflight tool byte变化，因此旧C1 preflight不得复用；下一步提交推送correction与failure evidence后，必须使用C2三组fresh roots重新运行全部五份zero-Blender preflights。

## J-302 · B57 C2 rehearsal preflight重新准入

Date: 2026-08-28 · Type: CORRECTED REHEARSAL PREFLIGHT · New Blender processes: 0 · New Blender renders: 0

Mechanical correction commit `454ed0efe135984401d5ce6dcbc713db9e36961a` 与 `origin/main` exact后，C2 fresh meta preflight 12/12 ACCEPTED；顶层`toolHashes`现与`toolFreeze.hashes` byte-identical，五份LOW-DISK/B01-A/B/B02-A/B production preflight全部ACCEPTED，Blender/render/model/network/Docker为0。Meta file SHA/self-hash为 `4d5e85557fdda7afe24a5b26755b109db58690789680b498c53b65aee078378b` / `345268e8526db0649e703a13628cec7bc81dd61b74b11326856b283bf374a852`。下一动作先推送C2 evidence，再用其bound C2 attempt/formal roots运行完整rehearsal。

## J-303 · B57 C2完整彩排定位production receipt disk cross-binding缺口

Date: 2026-08-28 · Type: BOUNDED REHEARSAL / VERIFIER CORRECTION · New Blender compilations: 4 · New Blender renders: 0

C2 accepted preflight evidence commit `4fe11eea55277705d42a2c70846cfbb8625fe061` 与 `origin/main` exact后，single-use rehearsal runner完成LOW-DISK反例与B01-A/B、B02-A/B四次真实Blender 5.2净编译。LOW-DISK继续在sequence-5以冻结的one-byte-below ceiling拒绝，restricted/native process均为0。四个正常路径wrapper/native PID分别为33354/33357、33463/33466、33578/33581、33699/33702；B01/B02 plan与structure pair全部byte-exact，preferred compile/verifier、current 19-check verifier、native PID、`.blend` binding及zero-render/model/network/Docker边界均通过。

Independent auditor给出有边界而非支持结论：`PRODUCTION_DISK_JIT_READMISSION_BOUNDED`，25/26 gates，52/56 semantic attacks。唯一失败gate为`INDEPENDENT_AUDIT_AND_SEMANTIC_ATTACKS_MINIMUM_56`；四个escaped attacks精确为`B01-A_DISK_HASH`、`B01-B_DISK_HASH`、`B02-A_DISK_HASH`、`B02-B_DISK_HASH`。Results/audit/formal-receipt file SHA-256为 `f9f855103b852f5a89beb6b42bc210f26656b25bd3ed65f0eb714aacc8dbc533`、`121b84c0bcaad48b09e55f43b6f11c1bf9e307b58d7406c0d3e1490421199d01`、`b23d10a2ffe17e356d470b1c98c083d3c34e0ae1552c3db9d7d06f9388b7bfba`；formal receipt self-hash为 `54f186e898d46663cc053bf466f438409c39f517bf587ba4c840f400f2f9f694`。C2 roots永久保留，不在原ID修复或重跑。

逃逸原因不是JIT disk observation缺失，而是production verifier只分别验证disk文件SHA/self-hash与receipt self-hash，没有把receipt投影的`diskAdmissionHash`及sequence/status/observed/effective/ceiling/policy重新与实际disk record逐字段比较。攻击因此可以修改receipt里的disk hash、重新计算receiptHash，并保持指向的真实disk文件未变。Correction只在production verifier加入该外部交叉绑定，并让B57 independent auditor的receipt语义函数接收从真实disk record读取的expected hash；v0.2 release只更新该verifier frozen hash。新verifier/auditor/release SHA-256分别为 `80a719e19f6c71eeb878b946d767f40b4142d80a91c0f28253c4f1b26f7860c9`、`c13e103494e23ae61bd791cefb0b07357fc47deb2e7ed80e10c7e255bda8ea4c`、`77cefbc95a20d641e140f7d2c3385af27ef7ce801063872d5bfa812a82f56252`；v0.2 frozen replay为31/31 exact，Node syntax与targeted ESLint通过。

该修复不追溯改判C2。下一动作先提交推送C2失败证据、correction bytes与本entry，再用Git读取的exact commit在全新C3 preflight/attempt/formal roots重跑完整彩排；只有C3达到26/26与56/56后，才允许冻结正式工具并创建official B57 preflight。

## J-304 · B57 C3交叉绑定修复后零Blender preflight接受

Date: 2026-08-28 · Type: CORRECTED REHEARSAL PREFLIGHT · New Blender processes: 0 · New Blender renders: 0

C2 bounded evidence与production verifier cross-binding correction commit `c621c5b01f647fb1c4fdf88ba2b17c14d8750f12` 已与 `origin/main` exact。C3使用Git实际读取的该full SHA作为tool-freeze commit，在三个fresh disjoint roots上执行meta preflight。12/12 checks全部通过：B56 parent、B57 spec/preregistration、v0.1 preserved release、v0.2 31-file release与三条B57 tool bytes、package aliases、SceneSpec 22/22、B01/B02 dual BuildPlan、real disk、one-byte boundary及五份production preflight均exact。

Meta preflight file SHA/self-hash为 `2aff716a18a4d54acf07f81e206b7da1f0e3dd1b4282feca2e4d80083bf2c7ed` / `3450f9a9f428064d2d585fcfdf4393a7c18e741de3f533401b5998d72f69c520`。真实available为108,594,233,344 bytes，扣除536,870,912 projected bytes后为108,057,362,432 bytes，高于107,374,182,400-byte reserve；forced negative 107,911,053,311 bytes仍比threshold精确少1 byte且只会降低真实观察。LOW-DISK、B01-A/B、B02-A/B五份nested preflight均ACCEPTED，operation count为五个production preflight processes、0 Blender/render/model/network/Docker。

Bound C3 attempt/formal roots仍不存在。下一动作只提交推送该preflight与本entry，再用Git读取的exact evidence commit调用single-use C3 runner一次。C3是完整彩排而非official B57；只有26/26 gates与56/56 attacks均通过，才允许后续冻结最终tool commit并创建三个预登记的official roots。

## J-305 · B57 C3完整彩排关闭disk receipt cross-binding缺口

Date: 2026-08-28 · Type: FULL REHEARSAL SUPPORTED / TOOL-FREEZE CANDIDATE · New Blender compilations: 4 · New Blender renders: 0

C3 accepted preflight evidence commit `5639cb8e83cad4ca3696827bb14f64e83f96a389` 与 `origin/main` exact后，single-use runner只调用一次并完成完整矩阵。LOW-DISK真实观察108,571,279,360 bytes后应用冻结ceiling 107,911,053,311 bytes，扣除projected write后为107,374,182,399，精确低于100 GiB reserve 1 byte；sequence-5 disk admission以`FREE_AFTER_PROJECTED_WRITE_BELOW_RESERVE`拒绝，disk/invalidation self-hash为 `909c4993b1b6f4efe02643013613e6e787b7a586ec860fb11e9f626ea8f14449` / `fc08e7ec1b905811d30223049e60e531b1c72713afdec2babb68185146292563`，restricted/native processes均0。

B01-A/B、B02-A/B四次preferred production compile与verifier全部PASS；wrapper/native PID分别为52998/53001、53105/53107、53231/53234、53337/53340。B01 plan/structure pair保持 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` / `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`；B02保持 `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687` / `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`。四份actual disk record与receipt投影的disk hash逐份exact，disk/receipt self-hash全部exact，root/restricted rosters无多余文件。

Independent auditor给出 `PRODUCTION_DISK_JIT_READMISSION_SUPPORTED`：26/26 gates、56/56 resealed semantic attacks、0 escaped。C2暴露的四个`DISK_HASH` attacks现全部被实际disk record外部交叉绑定拒绝。Formal-start/operation/audit/results/receipt file SHA-256分别为 `883b00864902215a2bcd7df20f1cb1900a2af4ed4bb46914049844bd1941e9e4`、`117bfb4e054d95edd132f0f89570194decea9328c385a60e1406b46768b899d5`、`ef2e3d2f83c147d284c0ac4d972a18cae732cb1d393cc7471cf46f2fbc55646b`、`7a886e9c8c4a26f957b272486b856f5519cf9ddb786a15f7c01f4a426f205bb2`、`77be6ff68e05842d1c7dd97da9a82c3eacc1ecb76711d291cb23f6c1d6e4db43`；formal receipt self-hash为 `2cfe230eb6f217023cec36a185e60183894f9e117b0e97b1c479e6f2d5d2a4f4`。45个formal files中只有四份`.blend`，无EXR/image/video/`.blend1`；render/model/network/Docker均0。

C3只证明最终tool bytes在隔离彩排中可达全部冻结门槛，不替代official B57。下一动作先提交推送C3 attempt/formal evidence与本entry；该exact evidence commit将作为final tool-freeze commit。随后只允许在预登记的三个official roots执行一次zero-Blender preflight，推送后再执行一次official runner。

## J-306 · B57-E1 official zero-Blender preflight接受

Date: 2026-08-28 · Type: OFFICIAL PREFLIGHT ACCEPTED · New Blender processes: 0 · New Blender renders: 0

C3完整彩排证据commit `3c4d3bc7533379f472b281a5bdd14443fe1beb44` 与 `origin/main` exact，且成为official final tool-freeze commit。在预登记的三个official roots全部fresh、absent且互不嵌套时，只调用official meta preflight一次。结果12/12 ACCEPTED：B56 parent、B57 spec/preregistration、v0.1 release preservation、v0.2 31-file release、三条B57 tools、package aliases、SceneSpec 22/22、B01/B02 BuildPlan pairs、real disk、one-byte boundary与五份nested production preflight全部exact。

Official preflight file SHA/self-hash为 `793c1d316ce6ad863e32ba1c9e0b353729b20c2c4f7f3918979a71b2e776a9d8` / `a78eb660438434fbd6931b8ebaf396d56c68db5b0017a645f793408c65b1a222`。真实available为108,501,454,848 bytes，扣除536,870,912 projected bytes后为107,964,583,936 bytes，高于107,374,182,400-byte reserve；forced negative仍为107,911,053,311 bytes并精确低于threshold 1 byte。LOW-DISK与B01-A/B、B02-A/B五份production preflight均ACCEPTED；Blender/render/model/network/Docker全部0，official attempt/formal roots仍不存在。

下一动作只提交推送official preflight与本entry，读取exact evidence commit并确认`origin/main`一致，然后对bound official attempt/formal roots调用single-use runner一次。任何失败都必须保留，official同一ID禁止修补或重跑。

## J-307 · B57-E1 production disk JIT readmission正式支持

Date: 2026-08-28 · Type: OFFICIAL FORMAL RESULT · New Blender compilations: 4 · New Blender renders: 0

Official accepted preflight evidence commit `ab43958de3b6387fdb148115edf034d72949e717` 与 `origin/main` exact后，single-use B57 runner只调用一次。Meta attempt/admission/receipt/formal-start按sequence 1–4 durable写入；LOW-DISK先执行，四个正常production compiles随后依固定顺序完成，最后由独立auditor直接重开全部证据。

LOW-DISK在native spawn前真实观察108,497,092,608 bytes，effective ceiling为107,911,053,311 bytes，projection后107,374,182,399，精确低于100 GiB reserve 1 byte。Sequence-5 disk admission以`FREE_AFTER_PROJECTED_WRITE_BELOW_RESERVE`拒绝，disk/invalidation self-hash为 `a02b4d89947f8c1dc9b365578c25009779e632506590f4ab8342d2be21652147` / `2fc2b3e6a32585e04e18bdfe270f02a40fd71082b29e7d627cf9640db739cfaf`；restricted wrapper与native Blender processes均0。

B01-A/B、B02-A/B四次preferred production compile与verifier全部PASS；wrapper/native PID分别为58237/58240、58343/58346、58448/58451、58553/58556。B01 plan/structure pair保持 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` / `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`；B02保持 `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687` / `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`。四份receipt均把sequence/status、observed/effective bytes、ceiling、policy与disk hash逐字段绑定回真实disk record；disk/receipt self-hash、root/restricted rosters与`.blend` embedded bindings全部exact。

Independent formal verdict为 `PRODUCTION_DISK_JIT_READMISSION_SUPPORTED`：26/26 gates、56/56 resealed semantic attacks、0 escaped。Formal-start/operation/audit/results/receipt file SHA-256依次为 `5401b79143c8b65b4710edb45788ad9aa52067856bf7349a3419d9ec75c1b6a7`、`9dc6841bee1302605850f0fbd1ce5ede94a060c492d6ca83c7d233d1fd25cfdf`、`9a9aa2275dfe03c26de514f31957b884647f1283620f86291449ad50cef15798`、`2d8bdc2260c964ae106d29b4832cd128abdf101ddae99e028b8e68572136f047`、`68d7252a26d5e49ba02680f5da5051ebe2598cf56172068358159c3512213b74`；formal receipt self-hash为 `5deeeda43de95376a96dfc6c688a3dce1a9e33d4ced304fa504d58cfb4645521`。45个formal files仅含四份`.blend`，无EXR/image/video/`.blend1`；render/model/network/Docker均0。

B57-E1 official ID至此封闭，禁止修改或重跑。该SUPPORTED只关闭“accepted preflight之后、native compile之前磁盘容量可能过期且receipt未强绑定”的生产安全缺口；它不证明Codex进程崩溃恢复、跨阶段幂等续跑或最终电影质量。下一动作先提交推送exact official evidence并发布B57研究页，随后按当前Goal进入restart-safe job manifest与受控中断恢复，不再扩张同类disk experiments。

## J-308 · B57-E1 研究页双站点发布完成并修复Pages取证缺口

Date: 2026-08-28 · Type: PUBLICATION COMPLETE / DEPLOYMENT INCIDENT CLOSED · New Blender renders: 0

B57 official evidence commit `64d93980bdccab13c1f6b306bfcc0ff0eb670ab9` 与研究页source commit `3192b61329b70757bbc88865c965d037f7b09f87` 均已推送。页面直接读取frozen spec、v0.2 release、official preflight/results/audit/receipt/low-disk record及C2 bounded results/audit，公开展示`PRODUCTION_DISK_JIT_READMISSION_SUPPORTED`、26/26 gates、56/56 attacks、one-byte-below spawn-block、C2反例与cross-binding correction、4次真实Blender 5.2 compile及zero-render claim boundary。Targeted ESLint、TypeScript、92-route GitHub Pages static build、Vinext production build与本地non-browser HTTP验证全部通过。

首次GitHub Pages workflow run `33191281987` 失败，原因不是页面实现或实验结论，而是`.github/workflows/deploy-pages.yml`的sparse checkout遗漏了页面静态导入的9份B57 JSON证据。修复只把这9个exact tracked paths加入checkout，不修改B57 evidence、页面语义或实验工具；fix commit为 `42c5ef8783267bf6b541ba18e8c96a51998c1c2d`。替代workflow run `33191448458` 在同一commit完成build与deploy并为success；公开route `https://lovejzzz.github.io/BlenderFilmStudio/production-disk-jit-readmission-v0-1/` 返回HTTP 200、58,913 bytes，并包含`26 PASS`、`56/56`、`C2 REHEARSAL`与`restart-safe`。邮件中的失败通知因此对应已被替代的旧run，incident至此关闭。

同一fix commit已推送到Sites source repository。现有成功Vinext archive重新保存为version 84，server archive content hash为 `sha256:ba1136a36ef0ccc46e480d33affda3bdbb65c7882d90abe2f34b2b74d3dc9ea0`，377 files、29,317,120 bytes；owner-only deployment `appgdep_6a91bc0dc7d8819187c529a057f37012` succeeded。Authenticated exact route返回HTTP 200、70,247 bytes并包含同一四项证据标记；anonymous route返回HTTP 401。发布时重新验证current user为owner、custom access、exactly one allowed owner account、external visitors 0、workspace/tenant groups empty。

遵守J-284 crash guard，全程没有browser handoff、截图、DOM、点击、resize或新增用户可见tab；所有发布验收均为构建、workflow状态与non-browser HTTP。临时archive与本次HTTP抓取随后精确清理，README及三份未跟踪research drafts未被stage。B57 publication现已封闭；下一阶段只进入restart-safe job manifest、受控中断恢复与exactly-once阶段语义。

## J-309 · B58-E1 restart-safe production orchestrator预登记

Date: 2026-08-28 · Type: FORMAL PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

B57 parent保持正式结论 `PRODUCTION_DISK_JIT_READMISSION_SUPPORTED`、26/26 gates、56/56 attacks；results/audit/receipt file SHA-256继续为 `2d8bdc2260c964ae106d29b4832cd128abdf101ddae99e028b8e68572136f047`、`9a9aa2275dfe03c26de514f31957b884647f1283620f86291449ad50cef15798`、`68d7252a26d5e49ba02680f5da5051ebe2598cf56172068358159c3512213b74`。B58 machine-readable spec与human protocol SHA-256分别为 `a1ea52598d66263989c56f9737917b7ff297122b6731ec31d6f535cacc32cf41` / `50c3d8f8e61ea894e4dadf0d1f2a2ff92e793de56bacfe1f2d01d48951d35f81`。

B58冻结单机append-only orchestration contract：immutable job manifest、hash-chained event ledger、PLAN_BIND → PRODUCTION_COMPILE → VERIFY_RECEIPT → FINALIZE四阶段DAG、exclusive-create/fsync receipts、只从已验证bytes重建状态、completed stage只写`SKIPPED_VERIFIED`而不得再次spawn、live/ambiguous process必须`WAIT/REFUSE`、failed/abandoned attempt永久保留且只能用新attempt ID与empty root重试。Candidate `job:production` entry与ledger/orchestrator/preflight/formal runner/independent auditor五条未来tool paths已在spec冻结；登记时全部不存在，三个formal roots也全部不存在。

正式矩阵冻结四个cells：B01 baseline；在compile completed receipt和ledger event落盘后、verify开始前exit 86，下一独立invocation必须0 additional Blender恢复；B02真实native Blender受控SIGTERM，失败attempt不得promote，恢复只重试compile而不重跑已完成plan；以及live exact child identity阻止duplicate spawn。上限为4 production compiler/native Blender starts、3 successful compiles、1 controlled interruption、3 preferred verifiers及0 render/model/network/Docker。Independent auditor不得import orchestrator execution modules，必须重开全部authoritative bytes；SUPPORTED要求34/34 gates与至少64/72 frozen one-field attacks，任何completed-stage duplicate spawn、dirty attempt promotion、unsafe live-process处理或B57 disk门降低都直接REJECTED。

预登记时filesystem available为108,261,376,000 bytes，扣除536,870,912 projected write后为107,724,505,088，仅比100 GiB reserve高350,322,688 bytes。该余量很薄：正式preflight或任何native-spawn readmission若跌破原门槛，必须先安全恢复容量，禁止降低reserve。下一动作只提交推送spec、protocol与本entry；远端exact前不得创建B58 tools或任何B58 root。

## J-310 · B58 durable ledger library实现checkpoint

Date: 2026-08-28 · Type: RESTART-SAFE IMPLEMENTATION CHECKPOINT / DEVELOPMENT ONLY · New Blender processes: 0 · New Blender renders: 0

B58 preregistration commit `9fe37d7c8b3d2e6b3ea522ba9c2e4515a100d99b` 已推送到`origin/main`后，才创建冻结path `scripts/lib/restart-safe-job-ledger.mjs`。Candidate SHA-256为 `05032a4532d96170476479a352842399d463d2ee16687f2e2a0a2ac50a4592fa`。实现包括canonical JSON限制、SHA-256/self-hash、exclusive-create + file/directory fsync、contained non-symlink path、immutable manifest、canonical six-digit hash-chained ledger、stage completion receipt cross-binding、DAG state reducer、macOS process start/executable/argv identity以及atomic writer lease/live-writer拒绝/dead-lease quarantine primitives。

第一轮仅位于系统temporary root的development integration test暴露两个实现错误：macOS `/tmp` → `/private/tmp`根别名被误判成root内部symlink traversal；随后writer identity局部变量遮蔽全局`process`导致`ReferenceError`。两者均在临时root保留终端反例后修正；没有创建B58 formal roots、没有改动B57 production surface，也没有启动Blender。修正后的positive probe创建manifest、3-event contiguous ledger、PLAN_BIND completed receipt，重新derive为COMPLETED，并成功获取/释放writer lease。Negative probe确认第二writer得到`LIVE_WRITER`，单字段ledger payload mutation得到`LEDGER_EVENT_HASH`。

`node --check`、targeted ESLint、`git diff --check`与两组temporary probes现全部通过，temporary roots已精确清理。本文件仍只是unfrozen implementation candidate，不是tool-freeze、official preflight或restart-safety verdict。下一动作先提交推送library checkpoint，再实现同一预登记path的`job:production` orchestrator；正式根继续禁止创建。

## J-311 · B58-E1-C1 preferred verifier进程记账修正预登记

Date: 2026-08-28 · Type: PREREGISTRATION CORRECTION / NO B58 EXECUTION · New Blender processes: 0 · New Blender renders: 0

在实现`job:production` orchestrator前重读冻结的 `scripts/verify-production-compile-receipt.mjs` bytes，发现B58 parent把“post-compile recovery不启动额外Blender”与“必须调用preferred verifier”同时写入，而该verifier每次成功调用必然spawn一个Blender 5.2 child重开`.blend`执行`blender/audit_compiled_artifact.py`。这个child不是native compile且不render，但仍是Blender process，因此原aggregate wording不可同时满足。该缺口发现时production orchestrator、official preflight、formal roots与任何B58 Blender process全部不存在。

原B58 spec/protocol保持byte exact `a1ea52598d66263989c56f9737917b7ff297122b6731ec31d6f535cacc32cf41` / `50c3d8f8e61ea894e4dadf0d1f2a2ff92e793de56bacfe1f2d01d48951d35f81`，不原地改写。C1 correction spec/protocol SHA-256为 `1a8f17bda34e7d1f7c683b742e93a2f32d1b9c3a1651388c68efddf566f9c3cd` / `e297c5b2396aac39409fc0eeb8185d2d19deace0ebf10bfb347aa6091aff7b34`。唯一授权修正是把process taxonomy拆为native-compile Blender与artifact-audit Blender，并将一个effective gate改为`RECOVERY_STARTS_ZERO_ADDITIONAL_NATIVE_COMPILE_BLENDER_AFTER_COMPILE_CHECKPOINT`；34-gate denominator、72 parent attacks和所有其他语义不变。

正式exact上限现为4 production compiler wrappers、4 native-compile Blender starts（3 success + 1 controlled interruption）、3 preferred verifier CLIs、3 current-receipt Node children、3 artifact-audit Blender starts，即7 total Blender processes但仍0 render/model/network/Docker。新增8项correction attacks拒绝把compile伪装成audit、遗漏audit child或总数off-by-one。下一动作只提交推送C1与本entry；远端一致前仍不得创建production orchestrator或B58 roots。

## J-312 · B58 `job:production` manifest与PLAN_BIND checkpoint

Date: 2026-08-28 · Type: PARTIAL ORCHESTRATOR IMPLEMENTATION / DEVELOPMENT ONLY · New Blender processes: 0 · New Blender renders: 0

B58-C1 correction commit `fc01f6fb74d3ad0517d27b2639e1bc057a3d44cb` 与`origin/main` exact后，创建冻结candidate path `scripts/run-restart-safe-production-job.mjs`，当前SHA-256为 `33ed4fda615f8c45cf44da7a591690cfe1608baf432160a3bc17a367c8dc70bc`；ledger library保持 `05032a4532d96170476479a352842399d463d2ee16687f2e2a0a2ac50a4592fa`。该checkpoint只实现start/resume/status参数、self-hashed job request验证、SceneSpec/release/expected BuildPlan bindings、immutable manifest、writer lease与`PLAN_BIND` stage；production compile/verify/finalize路径显式拒绝，尚未添加package alias，因此不能被误当成可用production entry。

Temporary B01 development job从fresh root创建manifest与`JOB_CREATED`，PLAN_BIND两次编译得到byte-identical plan hash `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`，落盘two plan artifacts、completed stage receipt和3-event ledger。随后独立resume重新验证receipt，只追加`STAGE_SKIPPED_VERIFIED`，ledger变为4 events；PLAN_BIND attempt count仍exactly 1，child/Blender/render/model/network/Docker均0。两次status只读且未改变ledger。

`node --check`、targeted ESLint与`git diff --check`通过，temporary request/job root已精确删除，三个formal roots继续不存在。本文件和library仍未冻结。下一动作先提交推送该checkpoint，再实现PRODUCTION_COMPILE stage的bounded child capture、native fault observation、failed-attempt quarantine与completed receipt；在development preflight存在前不得启动Blender。

## J-313 · B58 PRODUCTION_COMPILE状态机与orphan拒绝checkpoint

Date: 2026-08-28 · Type: COMPILE-STAGE IMPLEMENTATION CHECKPOINT / ZERO-BLENDER DEVELOPMENT · New Blender processes: 0 · New Blender renders: 0

PLAN_BIND checkpoint commit `9ad4804db0b7461b735dd793a26e91c0f7388870` 与`origin/main` exact后，扩展ledger library和`job:production` candidate。当前SHA-256分别为 `0946685b991c588fb1ecd6417445c1da42e544026d864d205f3ca69971e07d13` / `1b1d4c4dde6a7bd5690524cbedadd151bb8281cbcbd993a2599510ef42f46cb3`。新增failed/abandoned attempt receipt cross-binding、registered root disjointness、accepted production preflight/fresh attempt/output spawn gate、4 MiB bounded stdout/stderr hash capture、wrapper/native process identity、controlled SIGTERM hook、failure quarantine、fresh candidate retry、basic B57 receipt/disk/current-receipt/PID binding及post-compile exit-86 boundary。

审读中拒绝了“只记录npm wrapper PID”的初始实现方向：budget supervisor让native Blender使用独立process group；若wrapper先死，Blender可能成为orphan，单看wrapper会产生duplicate compile风险。Candidate现要求每次compile在等待terminal前先持久化native Blender PID、process start identity、executable与argv hash。恢复时wrapper或native任一exact process仍live都返回`WAIT_LIVE_PROCESS`；PID reuse/change或dead wrapper但缺少native identity均`REFUSE_RECOVERY`，不得把歧义当dead并spawn新attempt。Successful production receipt中的native PID必须回绑同一observed PID。

所有probe仍只使用temporary zero-Blender roots。Reducer probe证明FAILED COMPILE-1后可用new COMPILE-2进入STARTED，同时PLAN_BIND保持COMPLETED；missing preflight probe在任何compile/process event前拒绝spawn，ledger保持3 events且compile PENDING；synthetic dead-wrapper/no-native-identity probe精确返回`REFUSE_RECOVERY`。Node syntax、targeted ESLint和diff check通过，temporary roots已删除，三个B58 formal roots仍不存在。当前filesystem available为109,272,715,264 bytes，扣除projected write后高于100 GiB reserve约1.36 GiB。

本checkpoint尚未用真实production preflight或Blender验证process-tree observation与fault path，不是tool-freeze或B58 verdict。下一动作只提交推送代码与本entry；随后创建、提交并推送一组独立development B01 production preflight/job request，确认disk门后才允许一次真实compile-stage probe。

## J-314 · B58 B01 compile-stage development preflight接受

Date: 2026-08-28 · Type: DEVELOPMENT PREFLIGHT EVIDENCE · New Blender processes: 0 · New Blender renders: 0

Compile-stage candidate commit `4fedacbc78cd3f940ccabca87d606130b4c04a48` 与`origin/main` exact后，为独立development B01 cell调用现有preferred `preflight:production`一次。Preflight绑定SceneSpec、fresh output `experiments/restart-safe-production-orchestrator-development-b01-output-v0-1`与同一pushed release commit，返回ACCEPTED；plan hash为 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`，Blender/render/model/network/Docker全部0。

Preflight file SHA/self-hash为 `2c7012078f1a325612c0abc2f5e4e2a50d0f19a430ca9c9cb79ad17a777c6b8b` / `c82ba7adcb3d2cd2b888a02c1020b773b1765a291f8ebcd15b56300af20240fb`。真实available为109,405,233,152 bytes，扣除536,870,912 projected write后为108,868,362,240 bytes，高于107,374,182,400-byte reserve。Self-hashed job request file SHA/requestHash为 `fd7fe9d3c28d0f3ede47b87be00d86e2da3d85cbfd641ade24c2f425191e4314` / `2a07ae38d430a9dcc5e7515178ced80677984d59c89aefd4a65b57c885c017a4`，冻结one normal compile candidate、disjoint preflight/production-attempt/output/job roots及C1资源口径。

Production attempt、output与job roots继续全部不存在，三个official B58 roots也不存在。下一动作只提交推送development preflight、request与本entry；远端exact后，使用该evidence commit调用`job:production start --development-stop-after-compile`一次。该probe预计启动1 production wrapper与1 native compile Blender、0 verifier/audit Blender、0 render；任何native identity observation或receipt binding失败都保留为development counterexample，不在原root修补。

## J-315 · B58 B01真实compile-stage与零重复resume通过

Date: 2026-08-28 · Type: DEVELOPMENT REAL-BLENDER RESTART PROBE · New native Blender compilations: 1 · New Blender renders: 0

Accepted development preflight/request evidence commit `269d0590d9355a235cb62101a26c5c3e0edeae6a` 与`origin/main` exact后，只调用`job:production start --development-stop-after-compile`一次。PLAN_BIND完成后，orchestrator durably写入wrapper start与native observation，再等待现有preferred production compiler。Wrapper/native PID为76543/76662；native executable、process-start identity与argv hash先进入sequence-6 ledger event，随后budget report再次给出同一PID 76662、exit 0、null signal/spawn error。Compile stage COMPLETED且promotable，stage receipt file SHA/self-hash为 `31a49c2985f5f5b854536cfcf5ff1439186197a8a6e56e9840c2f2ddda923987` / `0e85e6816344eef22665884053c290b761e7d60ba95524ea13893f2e1c4fed86`。

Production receipt file SHA/self-hash为 `d2c30ca3522b858b2d655830bbcd26ee5a6ad257517450432b7148b7a8385f50` / `90091f7845c87e2cc91b4591f0466b865041ad90d4352c2493d030b4b2e92ec3`；plan/structure保持B57 B01 identities `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` / `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`。JIT disk observed/effective为109,351,952,384 bytes，扣除projected write后仍高于100 GiB reserve；disk admission self-hash为 `caff6e67aa4c643ed20bdf1ded351e0e9e06b1d08d6106bf3683543f4e409e54`。Job manifest file SHA/self-hash为 `c557966c941e1f12c519a14a457477c1530946a7160df6524f2be9b237065982` / `9254ce91aeb09363caf7023e0f32076541c41503952c90f35aaa9991ebfe0bf0`；`.blend` SHA为 `a1441d98605ef41b278b69742efe16d2a3fc1e350d46b794e6d0774a525eff27`。

随后使用新的orchestrator process调用`resume --development-stop-after-compile`。Reducer重新验证manifest、完整ledger、PLAN_BIND与PRODUCTION_COMPILE receipts，只追加两个`STAGE_SKIPPED_VERIFIED` events；production receipt SHA前后保持 `d2c30…`，PLAN与COMPILE attempt count均仍1，PROCESS_STARTED和NATIVE_PROCESS_OBSERVED总数均保持1。Sequence-9 compile skip event file SHA/eventHash为 `6e63c1f5692e4ba3c256bdf3c9542261cd42ca17fbb0dab60b2c1f8006912847` / `356882d60d5ae808171bd36c07260e7e1824edc164ac350357cb2468abe25a03`。只读status不改变ledger；检查时compile Blender running count为0。

Operation accounting为1 production wrapper、1 native compile Blender、1 successful compile、0 preferred verifier/current-verifier/artifact-audit Blender、0 render/model/network/Docker。Job/output分别14/9 files，无frames、image、EXR、video或`.blend1`。该probe支持“completed compile receipt在新process invocation中不会重跑”，但尚未测试exit-86边界、真实Blender interruption/retry、preferred verifier/final receipt或independent auditor，因此不是B58 formal verdict。下一动作先提交推送全部development evidence；随后实现VERIFY_RECEIPT与FINALIZE，再为controlled interruption创建新的预登记development candidates，不复用本root。

## J-316 · B58 VERIFY、FINALIZE与tool-freeze continuation候选

Date: 2026-08-28 · Type: IMPLEMENTATION CHECKPOINT / NO NEW BLENDER EXECUTION · New Blender processes: 0 · New Blender renders: 0

B01 compile development evidence commit `723921021d47b265310e1c7f64adf56accb27a15` 推送后，完成`VERIFY_RECEIPT`与`FINALIZE`候选实现；ledger library保持SHA `0946685b991c588fb1ecd6417445c1da42e544026d864d205f3ca69971e07d13`，orchestrator当前SHA为 `f85fe21c951beea0622c14cc4b1afbeea2de521aedd136ccdd03fa92033a96d7`。Preferred verifier stage现在先durably记录CLI identity，再观察并记录真实artifact-audit Blender identity；terminal verification必须11/11、verification self-hash、production receipt、plan、native PID与current/audit child PIDs全部交叉绑定。Started verifier恢复与compile相同：wrapper或audit Blender任一live则WAIT，dead但缺少audit identity或PID reuse则REFUSE，只有两者exact dead才允许新verify attempt。

FINALIZE从全部completed/failed/abandoned receipts机械重算production wrapper、native compile、preferred/current verifier、artifact-audit Blender及zero render/model/network/Docker totals；FINALIZE stage completed后才创建self-hashed final receipt，final receipt绑定manifest、stage receipts与completed ledger prefix，随后terminal `JOB_FINALIZED` event反向绑定receipt。实现同时覆盖两个crash window：FINALIZE stage completed但final receipt尚未创建时，resume只materialize receipt而不重跑stage；final receipt已fsync但terminal event未写时，resume只补terminal closure。Closed final receipt的再次resume返回byte-exact existing receipt且processStarts 0。

新增continuation safety：job request/manifest必须绑定ledger与orchestrator的exact SHA及pushed tool-freeze commit；每次start/resume都用Git blob与current bytes双重验证。工具升级后的旧job只允许status/read audit，不允许由新bytes继续执行。因本实现改变orchestrator bytes，J-315 B01 job至此保持封闭，不用它运行verify/finalize。Node syntax、targeted ESLint、diff check与旧job只读status通过；没有启动新Blender。下一动作只提交推送本checkpoint；随后以该commit生成fresh full-chain B01 preflight/request，执行compile + preferred verifier + finalize，并验证第二次resume为0 processes。

## J-317 · B58 full-chain B01 development preflight接受

Date: 2026-08-28 · Type: DEVELOPMENT FULL-CHAIN PREFLIGHT · New Blender processes: 0 · New Blender renders: 0

VERIFY/FINALIZE candidate commit `37fb87791b829f3b275c249f9e09ccec64636726` 与`origin/main` exact后，为fresh full-chain B01 cell调用preferred production preflight一次。结果ACCEPTED，plan hash保持 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`；preflight file SHA/self-hash为 `8478325d19db2c0d1ee43ace3198d434f9d408d503f539dd53a5aba5330a62ea` / `1373d9d7b94f00911697fb51364cb6a923399bb9f4b0cb2047296f6d07d0ca2b`。Observed available为109,317,533,696 bytes，projection后108,780,662,784，高于100 GiB reserve；Blender/render/model/network/Docker为0。

Fresh job request file SHA/requestHash为 `81a8a6d5360720ed62c51278d8348d2f69d9ca60bf5697990571b63738099c25` / `8ed1c1e9714f965a1ed2d9825069d6aa29b6a90d7417f3ccf30f72d87d7340cc`。它绑定tool-freeze commit与ledger/orchestrator SHA `0946685b991c588fb1ecd6417445c1da42e544026d864d205f3ca69971e07d13` / `f85fe21c951beea0622c14cc4b1afbeea2de521aedd136ccdd03fa92033a96d7`，并冻结one normal compile candidate、fresh disjoint production-attempt/output/job roots与C1 resource categories。

三个execution roots和official B58 roots均保持不存在。下一动作只提交推送preflight/request与本entry；随后对其pushed evidence commit调用完整`job:production start`一次，不使用development stop。Expected chain为PLAN、1 compile Blender、preferred verifier + 1 current Node child + 1 artifact-audit Blender、FINALIZE、terminal final receipt，render/model/network/Docker仍0。任何tool hash、audit observation、11-check verification或closure failure必须保留counterexample。

## J-318 · B58 B01完整compile→verify→finalize链与终态幂等通过

Date: 2026-08-28 · Type: DEVELOPMENT REAL-BLENDER FULL-CHAIN PROBE · New Blender processes: 2 · New Blender renders: 0

Accepted full-chain preflight/request evidence commit `912b4a20b5dc2a858a53e7697ffd420d2374b03f` 与`origin/main` exact后，仅在fresh disjoint roots调用一次`job:production start`。Job `B58-DEV-FULL-B01-1`完成PLAN_BIND、PRODUCTION_COMPILE、VERIFY_RECEIPT、FINALIZE与terminal `JOB_FINALIZED`，14条ledger events连续且hash-chain head为 `14066e5e0606bb06084931832421c7d3cd28b4dffe07814ceaa2094145c5b460`。Manifest self-hash为 `7f11c3472863b748dd3fac69b21be2ad08553f473420218aefac1c87be9f6655`；PLAN/COMPILE/VERIFY/FINALIZE stage receipt self-hash依次为 `d10ff7db2cf2583e04fd0475f18dba81454af82a9879a6a4c2b4caf48fb72e8e`、`7463ad84572adc78b5e2472d3d37920883b44eaa736509201ab3fd78115c878f`、`a51794156875021071c27f837f7a5cd491eb0a4a5b2c7b06d821dc1435901fcb`、`2a373ffb0c5edb3d018f751aa817726f841c117129d7807fa0e80525ac0c3e83`。

Production wrapper/native Blender PID为83976/84108，production receipt file SHA/self-hash为 `ba5bcbd73dd31b11440572519dcfa1f85ac7f813656e49627a700ca57ad9c7cb` / `a3efda585125e9b1a94fb12f026be78a7e3d2fe2bfbeee96892eae822b8d709b`，plan/structure保持B01 identities `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf` / `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`。Preferred verifier wrapper/current-receipt child/artifact-audit Blender PID为84131/84167/84322；verification 11/11 checks与内嵌current receipt 19/19 checks全部通过，verification self-hash为 `31b38c28351d53dc2ac2f5e372c531750ce5eee13ec456a2991df43d3ab4eeb9`，并回绑native PID 84108。

Final receipt file SHA/self-hash为 `f6cf9b9ff98886eaa485e339116c8f7bdf9d252d16b24184f09143c89e11e21f` / `104b258307313843ebe9a27e9670d5627da19cdb0d457994e558735939450620`；其completed-stage ledger prefix为13 events，terminal第14条event反向绑定该receipt。C1 resource totals精确为1 production compiler wrapper、1 native compile Blender、1 successful native compile、1 preferred verifier、1 current-receipt Node child、1 artifact-audit Blender，因此total Blender starts为2；render/model/network/Docker均为0。

随后用第二个独立orchestrator process调用`resume`。返回`ALREADY_FINALIZED`；final receipt file SHA前后仍为 `f6cf9b…`，ledger event count仍14，`PROCESS_STARTED` / `NATIVE_PROCESS_OBSERVED` / `ARTIFACT_AUDIT_PROCESS_OBSERVED`数量前后仍为2/1/1，没有追加skip event。只读status重建出四阶段全部COMPLETED且`complete: true`。Manifest、四份stage receipt、verification、production receipt、disk admission与final receipt共9个self-hash全部独立重算通过；Node syntax、targeted ESLint与diff check通过。

该development probe现在支持正常路径的完整终态closure与closed-job zero-process resume，但仍不是B58 formal verdict。尚缺exit-86 post-compile recovery、真native Blender interruption后的fresh-attempt retry、live-process WAIT/REFUSE实验以及official single-use preflight/runner/independent auditor的34/34 gate与至少64/72 attacks。下一动作先提交推送本完整证据，然后使用不变的tool-freeze bytes在fresh roots运行受控故障开发矩阵。

## J-319 · B58 exit-86 post-compile recovery development preflight接受

Date: 2026-08-28 · Type: DEVELOPMENT FAULT-INJECTION PREFLIGHT · New Blender processes: 0 · New Blender renders: 0

Full-chain baseline evidence commit `30f209b3a95d666b2943fb37d2b8f041114cb03c` 与`origin/main` exact后，为B01 post-compile crash window创建fresh disjoint preflight/output/production-attempt/job roots。Preferred production preflight返回ACCEPTED，BuildPlan hash保持 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`；preflight file SHA/self-hash为 `143b09199f94226ac34fa1b35f2a415c7b2262b30ccf715c2074424adb62dcc9` / `c8757cfeeb074c65d031e401a19b27ebbd9ae6fb7efcf5837ab0d360005cd64c`。真实available为109,330,673,664 bytes，projection后108,793,802,752 bytes，高于100 GiB reserve；Blender/render/model/network/Docker均为0。

Self-hashed job request file SHA/requestHash为 `5201175e61e761d7a7251a44660d744aeb8498f3086f0c977f4ee81ae30888dc` / `8af13ec108ab7114237ff096ed114d9baecd135ba406d300f4391b5edc00e823`。它绑定不变的tool-freeze commit `37fb87791b829f3b275c249f9e09ccec64636726`与ledger/orchestrator hashes，只注册一个normal compile candidate，并把`orchestratorFault`冻结为`EXIT_AFTER_PRODUCTION_COMPILE`。Expected first invocation必须在compile completed receipt与对应ledger event durable之后、VERIFY_RECEIPT start之前返回exit code 86；随后新进程resume必须对compile只写verified skip，不得新启native compile Blender，但应正常启动preferred verifier与audit Blender并完成FINALIZE。

Execution roots与三个official B58 roots继续不存在。下一动作只提交推送该preflight/request与本entry；远端exact后才允许first invocation。

## J-320 · exit-86首次调用因手写evidence commit失配在Blender前拒绝

Date: 2026-08-28 · Type: DEVELOPMENT ASSEMBLY FAILURE / FAIL-CLOSED RECOVERY PROBE · New Blender processes: 0 · New Blender renders: 0

Exit-86 preflight/request commit的真实full SHA为 `44d9efeb5b404a1998f8cc7171ca9c83b95e823a`，首次orchestrator调用却错误手写了`44d9efe035c9e2e1341689eb89267f07d1181968`。Restart-safe job已durably完成PLAN_BIND并记录production npm wrapper PID 84965，但内层unchanged production admission在output materialization前精确返回`EVIDENCE_COMMIT_MISMATCH`。Production attempt/failure/rejected receipt file SHA分别为 `3baa4b75b680dde5a510da9d26ffdf429b34f500ae7cee3eabaf02338591bab1`、`63551f62c7c34129f08ca07f9fffafe93b7df8c0b2d28970298a5d8dabe530bb`、`90481c27b80ba0bbe6fa06fc3749116e6dbfd20cf8a95b338e4d9978bf2fa936`；rejected receipt自哈希为 `d3245d15ae1d42e68f7e0b8d2510224aa6e32a5587881156c39e73ab9b9abbe8`。其声明compiler/Blender processes started为0，requested output root仍不存在，render/model/network/Docker均为0。该root不能用于exit-86假设。

对该started job使用独立resume时，reducer先验证并追加一条PLAN_BIND `STAGE_SKIPPED_VERIFIED`，随后因dead wrapper没有durable native Blender identity返回`REFUSE_RECOVERY: ... orphan state is ambiguous`，没有spawn任何新进程。Ledger因此从5 events增为6 events，compile仍STARTED，VERIFY仍PENDING。这是预登记fail-closed规则的真实负例，不在原job/attempt root修补或重试。

C1 request改用fresh job `B58-DEV-EXIT86-B01-C1`与fresh production-attempt root，保持原accepted preflight绑定的仍未创建output root。C1 request file SHA/requestHash为 `001b419ce6d28f70d46b7c50c114554439f40f440bbac14b4f1e9a1826501e8f` / `b2fe2457e1d25254eef1d250cada0e3422dc87e96c0aec7c7c75f04e03a4e250`，tool-freeze bytes与exit-86语义不变。下一动作先提交推送本失败证据与C1 request，然后必须用`git log -1 --format=%H -- <preflight-root>`读取的exact SHA，不再手写commit身份。

## J-321 · B58 exit-86 post-compile新进程恢复且零重复native compile通过

Date: 2026-08-28 · Type: DEVELOPMENT REAL-BLENDER CRASH-RECOVERY PROBE · New Blender processes: 2 · New Blender renders: 0

C1 assembly/evidence commit `07e469ee1c52340f53d067a52fa8625390d34dbb` 与`origin/main` exact后，命令不再接受手写SHA，而是直接读取preflight的last-affecting commit `44d9efeb5b404a1998f8cc7171ca9c83b95e823a`。C1 first invocation完成一次B01真native Blender compile，wrapper/native PID为85253/85383；PRODUCTION_COMPILE stage receipt self-hash为 `adeae65286f4216c321d889b7a182f14c60351a6f3ca2214ce233d271adf1f03`，production receipt file SHA/self-hash为 `3bcb865194d7a810437d243206b0ddd84f614e7db1a2cd754c36eae5e41c1975` / `f58f607e0a3822528a4c1e40c797651665ffddb71a851badb26b9047c98dd855`。

First invocation随后精确以exit code 86结束。此时ledger共8 events：sequence 7是compile `STAGE_COMPLETED`，sequence 8是`ORCHESTRATOR_FAULT_TRIGGERED`，boundary为`AFTER_COMPILE_RECEIPT_BEFORE_VERIFY_START`；VERIFY_RECEIPT仍PENDING且其receipt不存在，final receipt不存在。这证明fault不是在compile receipt durable前停机，也没有越过verify start边界。

第二个独立orchestrator invocation使用`resume`：先后写入PLAN_BIND与PRODUCTION_COMPILE的`STAGE_SKIPPED_VERIFIED`，再启动一次preferred verifier及一次artifact-audit Blender，完成VERIFY、FINALIZE与terminal closure。Ledger从8增为17 events，`NATIVE_PROCESS_OBSERVED`计数在resume前后保持1→1，因此recovery additional native compile Blender精确为0；`PROCESS_STARTED`从1→2只增加verifier wrapper，`ARTIFACT_AUDIT_PROCESS_OBSERVED`从0→1。Verifier wrapper/current child/audit Blender PID为85438/85474/85621，verification 11/11与current receipt 19/19 checks通过，verification self-hash为 `9b85ee75dcb68b3b77a6f6a9d5fe64892ac778707bc6df95fef97eb2c6165355`，仍绑定原native PID 85383。

Final receipt file SHA/self-hash为 `fd8364db1bd31f94d98ac8fde51a8285faa75643714f1af50b8792b58647bfc6` / `ca47deaa329da7f4a748bd554bb446e2d27ba4fd94358c5d501801a291cfb09b`，resource totals为1 production compiler、1 native compile Blender、1 successful compile、1 preferred verifier、1 current verifier child、1 artifact-audit Blender，total Blender starts 2，render/model/network/Docker为0。第三个closed-job resume返回`ALREADY_FINALIZED`，final file SHA与17-event ledger均byte-exact不变。Manifest、四份stage receipts、verification、production receipt、disk admission与final receipt共9个self-hash全部独立重算通过；Node syntax、targeted ESLint与diff check通过。

该development probe现在支持B58的post-compile crash recovery与zero-additional-native-compile命题，但仍不是formal verdict。下一个最高价值缺口是B02真native Blender受控SIGTERM：failed attempt必须不可promote，新invocation只能使用fresh attempt/output重试compile，PLAN不得重跑。

## J-322 · B58 B02 native-interruption/retry development preflights接受

Date: 2026-08-28 · Type: DEVELOPMENT FAULT-INJECTION PREFLIGHT · New Blender processes: 0 · New Blender renders: 0

Exit-86恢复证据commit `67da431` 推送后，为B02受控中断与fresh retry创建两组彻底disjoint的preflight/production-attempt/output roots，另用一个fresh job root串联两个candidate。两次preferred production preflight均ACCEPTED，BuildPlan hash均为B02 identity `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`，SceneSpec file SHA为 `774415a396bec91598ea8fac407443f04b6a630bdee046b15a14fae5fcad6c16`。

Interrupted candidate preflight file SHA/self-hash为 `8812927b70102951e401458c817f83ac7e721eeb13c60f3efc11eb071835e8fe` / `305070dda943ca37033df25c61ecda2a021fa880dec58307aca970cfdc4b8149`，observed/projection-after disk为109,326,573,568 / 108,789,702,656 bytes。Retry candidate preflight file SHA/self-hash为 `63a7f0dbed15d7ea718174df10c5b8fc0bc9adc52d4a266e9f833c7f823899fd` / `440f9e409cedbfa5138798613da694b96b3ac7df0243a4bbea730608644c49f9`，observed/projection-after为109,326,307,328 / 108,789,436,416 bytes。两者都高于107,374,182,400-byte reserve，且Blender/render/model/network/Docker为0。

Job request file SHA/requestHash为 `5a8be8e544648bd0b96b2d69658324314ba8b3d39bdd2c00e9dc66054e46a866` / `9737380294225ea8d65a8fbed20f7bc98e7b7bdef07ae8b1d8a92efe40da9acb`。它按序冻结两个compile candidates：`B02-INTERRUPTED-COMPILE-0001` 使用`INTERRUPT_NATIVE_AFTER_OBSERVED`，`B02-RETRY-COMPILE-0002` 无fault。Expected first invocation必须在durable native identity后向该Blender process group发SIGTERM，并以non-promotable FAILED attempt停止；second invocation必须verified-skip PLAN，不得使用第一output root，只能在第亊fresh root启动一次compile，随后verify/finalize。

两组execution roots、job root与official B58 roots均仍不存在。下一动作只提交推送两份preflight、request与本entry；实验调用仍必须从Git读取exact preflight evidence commit。

## J-323 · B58 B02真native Blender SIGTERM、failed quarantine与fresh retry通过

Date: 2026-08-28 · Type: DEVELOPMENT REAL-BLENDER INTERRUPTION/RETRY PROBE · New Blender processes: 3 · New Blender renders: 0

Dual-preflight/request evidence commit `d0257dab0d7d958bee32197edfaeb1535b210a54` 与`origin/main` exact后，first invocation完成PLAN_BIND，启动B02 first compile wrapper/native Blender PID 86091/86217，并在sequence 6持久化native process identity。Sequence 7 `FAULT_INJECTED`记录对native process group发送`SIGTERM`且`signalSent: true`；wrapper terminal为exit 1、null signal/spawn error、stderr 133 bytes。Sequence 8把attempt封存为FAILED，reason `CONTROLLED_NATIVE_INTERRUPTION`、`promotable: false`，attempt receipt file SHA/self-hash为 `5da2a621975a9412a18d6383515458e6ead589095e7ddd863a898636ef63ebf1` / `460585fabd1bdca0fdd40989bcaf4ae548521deeda80214b9ec47a371e1f6bd3`。

Failed output只包含BuildPlan、formal-start、JIT disk admission、restricted budget report与invalidation；production receipt、compile receipt与`.blend`均不存在。Invalidation self-hash为 `c646ef576ad0214d9ab518f64d05f5f9d9d83b32f420ea8bbe4445775f3264f9`。First invocation返回`COMPILE_FAILED_NEEDS_RESUME`，job状态为PLAN COMPLETED、COMPILE FAILED、VERIFY/FINALIZE PENDING；resource accounting为1 production compiler、1 native compile Blender、0 successful compile、0 verifier/audit Blender、0 render/model/network/Docker。

Second independent invocation使用`resume`，对PLAN_BIND只写一条`STAGE_SKIPPED_VERIFIED`，随后选择预登记的fresh `B02-RETRY-COMPILE-0002`，未重用failed attempt或dirty output。Retry wrapper/native PID为86275/86392，completed stage receipt self-hash为 `bbf826616423532934cbaaddec26c471f8cd3388eaff488cdc92107b59148c0b`；production receipt file SHA/self-hash为 `29e7708ec842e54659739249cae899b349d2cb59fe191503d66f6836b7e2fa83` / `e89901f86c5b021e0c640d2f5556d88a37214869caab9e7b16fa08fa9866fc10`，plan/structure为B02 identities `a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687` / `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856`。

Preferred verifier随后完成11/11，current receipt内嵌19/19，current child/audit Blender PID为86447/86602，verification self-hash为 `c8e644b75c03ae18025102326ded2a90bee94f7a475fe2bf1609d41a67a11596`并绑定native PID 86392。Final ledger共20 events：唯一FAULT、一个FAILED compile attempt、一个COMPLETED retry，四阶段最终全部COMPLETED。Final receipt file SHA/self-hash为 `2fd8677210a7fb481ab7e123549e02e4a9c9a0f0bc6fcccebed9ea0d794953d5` / `20faee8e2c3eddf6c911ee3c1ff47f356a61a06d98251db57d49c80c7d2cc7b7`；resource totals为2 production compilers、2 native compile Blender starts、1 successful compile、1 preferred verifier、1 current child、1 artifact-audit Blender，total Blender starts 3，render/model/network/Docker为0。

第三个closed-job resume返回`ALREADY_FINALIZED`，final file SHA和20-event ledger均不变。Manifest、PLAN receipt、failed attempt receipt、completed compile/verify/finalize receipts、verification、final receipt、invalidation、retry production receipt与disk admission共11个self-hash全部独立重算通过；Node syntax、targeted ESLint与diff check通过。该probe支持受控native中断不可promote、failed evidence不丢失及fresh retry语义，仍不是B58 formal verdict。下一缺口是真实live-process WAIT/REFUSE，然后才能实现official preflight/runner/auditor。

## J-324 · B58 live-process refusal development preflight接受

Date: 2026-08-28 · Type: DEVELOPMENT LIVE-PROCESS PREFLIGHT · New Blender processes: 0 · New Blender renders: 0

Native-interruption/retry evidence commit `bd78b14` 推送后，为B01 live-process cell创建fresh preflight/output/production-attempt/job roots。Preferred preflight返回ACCEPTED，BuildPlan hash为 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`；preflight file SHA/self-hash为 `dcfacda137f290a8f304b1fea02c6a71368fd4c63deb240ec94886e3bb321162` / `9a41901eb33c6627ba7cad797362e49846d3e9f9cb31b00c118ef61cc9c66284`。Observed available为109,335,576,576 bytes，projection后108,798,705,664 bytes，高于100 GiB reserve；Blender/render/model/network/Docker均为0。

Self-hashed request file SHA/requestHash为 `99518e996626d7d5bf44052ef308de1be23170c41f5561f691a74ff5c976036a` / `1c8ab0544a5257ecacb844d210d79fc9bce6be932ea5adac98bd824803ffa705`，只注册一个B01 normal compile candidate。Development intervention不改production/tool-freeze bytes：首个orchestrator在`NATIVE_PROCESS_OBSERVED`已fsync后，由外部harness对exact native PID发SIGSTOP，再终止orchestrator模拟主进程丢失，保持已记录wrapper/native child存活。第二个resume必须验证identity并返回`WAIT_LIVE_PROCESS`，compile `PROCESS_STARTED` / `NATIVE_PROCESS_OBSERVED`均不得增加，也不得创建stage terminal receipt或第亊output。证据采集后只允许向记录且再验证的exact PID/process group发送终止信号，禁止宽泛清理。

Execution roots与official B58 roots仍不存在。下一动作只提交推送本preflight/request与entry，随后由bounded harness一次性执行上述过程。

## J-325 · live-process首轮安全REFUSE并定位re-parented wrapper优先级缺口

Date: 2026-08-28 · Type: DEVELOPMENT LIVE-PROCESS COUNTEREXAMPLE / RECOVERY CORRECTION · New Blender processes: 1 · New Blender renders: 0

Live preflight/request evidence commit的exact SHA为 `6f2f7be39cd7f9577a7ae0c085bc716ed54a3ae2`。Bounded harness启动orchestrator PID 86984，ledger先后持久化production wrapper PID 87019和native Blender PID 87185及其exact identity hashes `72e5f444a1b481dfd449bf31db27ba2c1614aae355090af7466baa0dd00b4112` / `353f7d29fd571f3757ff8bf979cc7f4e15162fda185a53566913b72c0b015054`。Harness对重新验证的native PID发SIGSTOP，`ps` state为`TNs`，随后对exact orchestrator PID发SIGTERM，终端exit 143；wrapper与native在resume前均仍存活。

第二个resume没有spawn新进程：`PROCESS_STARTED` / `NATIVE_PROCESS_OBSERVED`计数均保持1→1，compile terminal receipt不存在。但它在PLAN `STAGE_SKIPPED_VERIFIED`使ledger 6→7后返回`REFUSE_RECOVERY: compiler wrapper PID identity is ambiguous or reused`，而非预期的`WAIT_LIVE_PROCESS`。原因是orchestrator死亡后npm wrapper被OS re-parent，其parentPid改变使wrapper full identity不再exact；但已记录native Blender仍在原budget-supervisor下，full identity保持exact live。当前代码先查wrapper，因而在检查exact live native之前就fail-closed。该root是安全bounded反例：没有duplicate spawn，但不满足预登记WAIT outcome，不在原root重试。

证据采集后，harness只向再验证的native process group发TERM+CONT，并等待wrapper收尾；86984/87019/87185三个PID均确认消失，无Blender核心进程遗留。Production output以`RESTRICTED_COMPILE` invalidation收尾，file SHA/self-hash为 `75c2c5a6a994441183fdb27625b47bf87644143cc31f4655e058756d737c0d37` / `3d8560a6c0612c96dced70a8315668906427612059b9964d72739ec5e7790e26`，production receipt不存在，render/model/network/Docker为0。

修正只改recovery检查顺序，不改identity判定强度：compile若已有durable native identity，先检查native；exact live立即WAIT，ambiguous/reused立即REFUSE，exact dead才继续查wrapper。Verifier recovery对durable artifact-audit Blender对称使用相同child-first规则。Wrapper仍exact live时仍WAIT，两者dead才ABANDON，任一identity ambiguous均REFUSE。修正后orchestrator candidate SHA为 `ab06eb891719f4ce65b1b48535cfcbb40007bf801f351572766fb1965dcee0ab`，ledger library保持 `0946685b991c588fb1ecd6417445c1da42e544026d864d205f3ca69971e07d13`；Node syntax、targeted ESLint与diff check通过。下一动作先提交推送反例与correction bytes，然后用fresh C1 preflight/request/job roots重跑同一live intervention。

## J-326 · B58 live-process child-first C1 preflight接受

Date: 2026-08-28 · Type: CORRECTED DEVELOPMENT LIVE-PROCESS PREFLIGHT · New Blender processes: 0 · New Blender renders: 0

Child-first correction commit `b629b9bc8b98ce1f9b2d1f6ad032b575c754fa0b` 与`origin/main` exact后，使用fresh C1 preflight/output/production-attempt/job roots重新准入B01 live-process cell。Preferred preflight返回ACCEPTED，BuildPlan hash保持 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`；preflight file SHA/self-hash为 `b5b0a0f9636a4d092b42fa63546314e95de8fe2746543455cc3d79357c211386` / `e9ed0fdbb2199a16127c92943e90d0e8ace1c7c1c9fb1686c684f87749fc05e7`。Observed available为109,273,387,008 bytes，projection后108,736,516,096 bytes，高于100 GiB reserve；Blender/render/model/network/Docker为0。

C1 request file SHA/requestHash为 `d9e1572a35e9faae989acc893e77e1c47b79c9cff04e9c7bed4cac928dd7c875` / `38be38faaa1acf467631d18010883283d2f990d7f7fe2960f5c7ffd87f6c3d7a`，绑定tool-freeze commit `b629b9bc8b98ce1f9b2d1f6ad032b575c754fa0b`、unchanged ledger SHA `0946685b…`与corrected orchestrator SHA `ab06eb891719f4ce65b1b48535cfcbb40007bf801f351572766fb1965dcee0ab`。介入、期望WAIT outcome、zero duplicate process与exact-PID cleanup边界与J-324完全相同；原root不复用。

C1 execution roots与official B58 roots仍不存在。下一动作只提交推送C1 preflight/request与本entry，随后使用相同bounded harness一次性复现。

## J-327 · live-process C1命中WAIT，但CLI未投影wait PID

Date: 2026-08-28 · Type: DEVELOPMENT LIVE-PROCESS BOUNDED SUCCESS / OBSERVABILITY CORRECTION · New Blender processes: 1 · New Blender renders: 0

C1 preflight/request evidence commit `968c528a33e8624187271908691c3d38ad005822` 与`origin/main` exact后，bounded harness启动orchestrator/wrapper/native Blender PID 87636/87670/87834。Wrapper/native durable identity hashes为 `c7b3e2bbc90b66447b1e804e896bf867a683a5637b9096a403b2376284686df5` / `7aa283f88aff17946712eb9c59fc22017b381b3b5d5e0e37a06086be976d9dab`。Native在SIGSTOP后state为`TNs`；orchestrator以143退出后，wrapper被re-parent为PPID 1，native仍以PPID 87800存活并保持stopped。

第二个resume正式返回`WAIT_LIVE_PROCESS`，证明child-first修正跨过了re-parented wrapper mismatch并看到已记录live native。`PROCESS_STARTED` / `NATIVE_PROCESS_OBSERVED`均保持1→1，无duplicate compiler/Blender/verifier；ledger只因PLAN verified skip从6→7，compile仍STARTED且terminal receipt不存在，production receipt不存在。证据采集后exact native group经TERM+CONT收尾，87636/87670/87834均确认消失，无Blender核心进程遗留。Output invalidation file SHA/self-hash为 `03888e75c6fa3f64993813ce14753a55996d6e0650d2f15cf3afeb11fdd4eda9` / `479f3981f233dda4f09554c0518b795de812bfece8c3cb33f576e10be6b71327`，render/model/network/Docker为0。

然而当前CLI有一个可审计性缺口：`runAvailableStages()`的返回值确实包含`process` identity，但command-line输出只序列化`result.state`，所以外部harness无法从stdout直接断言WAIT的PID是87834。该次结果因此只记为bounded success，不用于关闭live-process gate。原C1 root不复用。

C2 correction仅使CLI在result存在`process`时向原status JSON增加`waitProcess`，完整投影PID、parentPid、start、executable、argv SHA与identity hash；非WAIT outcome的现有输出不变，不改任何recovery判定。Correction后orchestrator candidate SHA为 `d8f3126f34c15d6adb1c6c2324b640fa9aa0756733d008d3087a5b5ab7b5b41a`，ledger SHA保持 `0946685b…`；Node syntax、targeted ESLint与diff check通过。下一动作先提交推送C1 evidence与CLI correction，然后用fresh C2 roots最后复验stdout `waitProcess.pid === recorded native PID`。

## J-328 · B58 live-process C2 auditable-WAIT preflight接受

Date: 2026-08-28 · Type: CORRECTED DEVELOPMENT LIVE-PROCESS PREFLIGHT · New Blender processes: 0 · New Blender renders: 0

WAIT CLI projection correction commit `742484c8295ec8afa55ff7990542071a67933e98` 与`origin/main` exact后，使用fresh C2 preflight/output/production-attempt/job roots第三次准入B01 live-process cell。Preferred preflight返回ACCEPTED，BuildPlan hash保持 `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`；preflight file SHA/self-hash为 `2de09f9dcc2de5e7ace11dbb90747ce790a4d632e3a3cdd6a4ab3f7310085adf` / `38e5f66ce6ac9df5f93f50e1d0a3da465e1ba224049f13800d0a55cf52ea3d1a`。Observed available为109,293,395,968 bytes，projection后108,756,525,056 bytes，高于100 GiB reserve；Blender/render/model/network/Docker为0。

C2 request file SHA/requestHash为 `46813afee135deaabbb3eee8c9bf0aad1ac4dc6000cc86777c432d87623b5b46` / `45b7d2b82dd50bf9c7d71bea8cb54bf52c3b2a9832a1bb6ffa109f0a60251ed9`，绑定tool-freeze commit `742484c8295ec8afa55ff7990542071a67933e98`、ledger SHA `0946685b…`与orchestrator SHA `d8f3126f34c15d6adb1c6c2324b640fa9aa0756733d008d3087a5b5ab7b5b41a`。Expected outcome除C1的WAIT、zero duplicate与exact cleanup外，新增可机械审计条件：stdout的`waitProcess.pid`、`identityHash`、executable与argv SHA必须与ledger中`NATIVE_PROCESS_OBSERVED` exact一致。

C2 execution roots与official B58 roots仍不存在。下一动作只提交推送C2 preflight/request与本entry，随后使用相同bounded harness最后执行一次。

## J-329 · B58 live-process C2 exact native WAIT与zero-duplicate通过

Date: 2026-08-28 · Type: DEVELOPMENT REAL-BLENDER LIVE-PROCESS PROBE · New Blender processes: 1 · New Blender renders: 0

C2 preflight/request evidence commit `11f3946d35fb7d8e416737aa84e9f048af74f07a` 与`origin/main` exact后，bounded harness启动orchestrator/wrapper/native Blender PID 88257/88291/88452。Wrapper/native durable identity hashes为 `bf337a58783ef97f7f98c82e2b730461acb4fcce7fe9469d1472fb668b82f8cc` / `990c2aea6d4f3be27b87348a2ad6c6104b7b12cc51931d4e7dc1882897d93bcc`，native argv SHA为 `bc1872c2c0569b0fd9580a7177f913fdf49d0048697ddab41bef5800552dd8ef`。Native在SIGSTOP后state为`TNs`；orchestrator以143退出后，wrapper PPID已变1，native仍以PPID 88426存活。

第二个resume以exit 0返回`WAIT_LIVE_PROCESS`，stdout新增的`waitProcess` exact投影PID 88452、executable `/Applications/Blender.app/Contents/MacOS/Blender`、identity hash `990c2a…`与argv SHA `bc1872…`，四项全部与sequence-6 `NATIVE_PROCESS_OBSERVED` byte-exact一致。`PROCESS_STARTED` / `NATIVE_PROCESS_OBSERVED`计数均保持1→1，ledger只因PLAN verified skip从6→7，compile仍STARTED，compile terminal receipt与production receipt均不存在，因此duplicate compiler/native/verifier spawn全部为0。

采集后harness只对重新验证的native group发TERM+CONT并等待wrapper收尾；88257/88291/88452均确认消失，无Blender核心进程遗留。Output以`RESTRICTED_COMPILE` invalidation收尾，file SHA/self-hash为 `3af264ecbde2b317b22bb14c4bea6da1afd63160aeee373b46165a99101c99d5` / `56891da63425f64a27c46d7ce244efe8a0fb6761ef22441689055196b74a0896`，render/model/network/Docker为0。Job manifest self-hash为 `83268c9c21c469bc74944b5272841882df775f368d1391952bc416a56b48c324`，7-event ledger head为 `3e21bda971ecd594bbb260ff4e5d638f56605cb71474b9a6e4fc82b96bbfef27`。

该development probe现在关闭真实live-process WAIT/zero-duplicate开发缺口，但仍不是B58 formal verdict。正常full chain、exit-86、native interruption/fresh retry和live WAIT四类真Blender development路径已齐。下一阶段是实现预登记的official single-use preflight、formal runner与不import execution modules的independent auditor，然后才能在三个冻结official roots上评定34/34 gates与至少64/72 attacks。

## J-330 · Goal 重定义：稳定性成为 B58 official run 的前置 Gate 0

Date: 2026-08-28 · Type: GOAL CORRECTION / CRASH CONTAINMENT · New Blender processes: 0 · New Blender renders: 0

用户提供的Codex桌面端崩溃报告记录 `com.openai.codex` 26.820.80927 (7271) 在 `Chrome_IOThread` 触发 `EXC_BREAKPOINT (SIGTRAP)`，同时主线程位于 `v8::ValueSerializer::WriteValue`。该证据提示内嵌Chromium I/O、跨进程消息或V8值序列化路径，但当前不足以唯一归因，因此不把Blender、磁盘或单个网页标签直接宣判为根因。

项目执行目标现改为“稳定、可恢复、可审计的Blender 5.2电影生产系统”，并按Gate 0宿主稳定性、Gate 1工作流正确性、Gate 2电影质量与成本顺序推进。Gate 0通过前，B58 official formal run暂停；只允许低风险静态检查、证据整理、轻量实现和稳定性诊断。默认防线包括最少浏览器标签、大输出落盘只回传摘要、低频状态更新、严格磁盘余量、精确PID回收、断点续作，以及每次实验的资源预算和停止条件。

完整执行宪章保存为 `research/2026-08-28-stability-first-goal-v0.1.zh-CN.md`。本次没有启动Blender、渲染、模型、网络或Docker工作负载。

## J-331 · B59-G0 Codex宿主稳定性有界基线预注册

Date: 2026-08-28 · Type: STABILITY BASELINE PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

在B58 official run暂停后，先预注册一个不主动复现崩溃的只读宿主基线。Spec冻结用户崩溃报告SHA-256 `035649c3c49d8d95385f5221f968fd2824132d30184399ab204341542ef6d4b8`、252,628 bytes、1,323 lines及`Chrome_IOThread` / `EXC_BREAKPOINT (SIGTRAP)` / `v8::ValueSerializer::WriteValue`签名，但明确不把它解释为唯一根因。

B59-G0冻结20个gates、24个mutation attacks、8 KiB stdout和64 KiB receipt上限。Formal runner只允许最多12个短时本地读取子进程，禁止Blender、render、浏览器自动化、网络、模型、Docker、清理、信号与重启。磁盘准入比B58更严：100 GiB核心reserve + 0.5 GiB B58 projection + 4 GiB稳定余量，共要求至少112,205,053,952 available bytes；不降低原production门槛。

当前formal root和两个tool paths在预注册时均不存在，parent commit与`origin/main`均为 `098276e590f73cfef90906a80d41886c79c56adc`。下一动作只提交推送spec/protocol/journal，再实现有界runner和仅用Node built-ins的独立auditor。

## J-332 · B59-G0有界runner与独立auditor实现冻结

Date: 2026-08-28 · Type: STABILITY TOOL IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

在预注册commit `e98b569` 推送后，实现只读runner与不import runner的独立auditor。Runner SHA-256为 `fbfea40c3d4184b0dadd6ebaa7fc63ad5e3434a80b4f7893a6262bd54600e5b3`，270 lines / 12,489 bytes；auditor SHA-256为 `269a745a88d85150b88aa6300fa6c62c4b016c0ca610b6dbad1e7d2a50f23fc6`，297 lines / 17,645 bytes。

Runner只使用bounded `git`、`memory_pressure`和`ps`读取子进程，直接从plist与`statfs`读取版本和磁盘；原始process table与252 KB crash report均不输出。Auditor独立重算receipt语义、自哈希、即时资源门并对24个resealed mutations逐项验证拒绝。两者均对stdout施加8 KiB上限，对receipt施加64 KiB上限，formal ceilings保持零Blender/render/browser automation/network/model/Docker/cleanup/signal/restart。

Node syntax、zero-warning targeted ESLint和diff check通过；formal root仍不存在。下一动作只提交推送工具字节，再在临时clone中排练，不消费正式single-use root。

## J-333 · B59-G0临时clone反例与C1 attack-control修正预注册

Date: 2026-08-28 · Type: REHEARSAL COUNTEREXAMPLE / CORRECTION PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

工具commit `6875e1f` 推送后，在共享Git objects的临时sparse clone中排练，未消费真实formal root。首命令因sparse clone缺少空`experiments/`父目录而在formal root创建前ENOENT停止；补建临时父目录后，runner生成3,755-byte bounded receipt，provisional verdict为`BLOCKED_HOST_STABILITY`，真实失败门是`DISK_STABILITY_MARGIN`与`CODEX_TREE_RSS`。结果SHA为 `fc02787390de94188d8bd3232d998206f02e7cb9aecbf52c5db32e15bb4bf514`。

Auditor的16个integrity checks全部通过，runner/auditor合计8/12 children，零Blender及其他禁用资源；但三项同族攻击被既有false gate吸收：A10 disk available、A11 disk projection、A16 Codex tree RSS。Audit只得21/24并正确返回`INVALID_EVIDENCE`，audit SHA为 `1bf2c1631ad33486ebf82c50cbea2a940f865495fdffb90b6d599696c09f7493`。

C1冻结唯一修正：不改runner、阈值、gate、attack ID或formal root；auditor先从冻结阈值构造并验证一个明确标记的synthetic admissible control，再把原24个mutations逐一施加到独立control clones。Synthetic control不替代真实宿主观察，真实disk/RSS blocker必须保留。实际formal root仍不存在。

## J-334 · B59-G0-C1 synthetic admissible attack control实现

Date: 2026-08-28 · Type: AUDITOR CORRECTION IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

C1 preregistration commit `6adece1` 推送后，只修改independent auditor。它现在从真实receipt克隆一个明确标记的synthetic control，把disk、memory、process与zero-resource字段设为冻结门槛内的边界值，投影19个true runner gates、pending audit gate、空failure list与`ADMITTED_PENDING_AUDIT`，reseal后必须先通过同一个semantic validator。24个原始攻击随后分别作用于该control的独立clone；A01–A23重封hash，A24只破坏hash。

Runner字节与SHA `fbfea40c…`保持不变，所有资源阈值、20 gates、24 attack IDs及formal root不变。Corrected auditor SHA为 `52474b5c07e9b598e8d8d3336b2222223e0edbcb1857c8d4ff8172c3cc347054`。Node syntax、zero-warning targeted ESLint与diff check通过，实际formal root仍不存在。下一动作提交推送修正后，在新的临时sparse clone重跑完整rehearsal。

## J-335 · B59-G0-C1排练发现总数字段算术反例并预注册C2

Date: 2026-08-28 · Type: REHEARSAL COUNTEREXAMPLE / ARITHMETIC CORRECTION PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

C1 commit `ae11980` 推送后，在fresh临时sparse clone完成第二次排练。真实runner receipt为3,732 bytes，保留`DISK_STABILITY_MARGIN` blocker；auditor的integrity replay通过且24/24 attacks全部拒绝，但synthetic admissible control未通过，final仍为`INVALID_EVIDENCE`。Results/audit SHA分别为 `dc8aa9f7c30b5ec5d34152132cdbe0bdaf80915830578a98ac0bfac9f4310256` / `9d3a805c9425742f2766d325c8098a007c720d2d76c0d92b8b7cbf7385de9be9`。

根因为预注册冗余总数字段的算术笔误：107,374,182,400 + 536,870,912 + 4,294,967,296精确等于112,206,020,608，而JSON/protocol写成112,205,053,952，少966,656 bytes。Runner始终从三个冻结加数实时求和，执行门没有被放松。

C2只允许把冗余`minimumAvailableBytes`和对应prose改为112,206,020,608；三个component thresholds、runner、auditor、20 gates、24 attacks、ceilings及formal root全部不变。实际formal root仍不存在。

## J-336 · B59-G0-C2精确总数修正实现

Date: 2026-08-28 · Type: PREREGISTERED ARITHMETIC CORRECTION · New Blender processes: 0 · New Blender renders: 0

C2 preregistration commit `ac833e8` 推送后，只把parent spec的`minimumAvailableBytes`与parent protocol对应prose从112,205,053,952修正为112,206,020,608。Node独立重算确认它精确等于107,374,182,400 + 536,870,912 + 4,294,967,296。

修正后parent spec/protocol SHA为 `ad8a49082dca1a9cf1df6e0626dc5c313c499a7232fbd2f01460d163f27cd11c` / `1b79ce07e376005336d913b90588478ea7de655cb83ac8a9a0e67f5c0b74d54d`。Runner/auditor SHA保持 `fbfea40c…` / `52474b5c…`，Node syntax、zero-warning targeted ESLint与diff check通过。实际formal root仍不存在；下一动作提交推送两字节修正与本entry，再用第三个fresh临时sparse clone重跑。

## J-337 · B59-G0-C2完整rehearsal收敛为可信host blocker

Date: 2026-08-28 · Type: BOUNDED STABILITY REHEARSAL · New Blender processes: 0 · New Blender renders: 0

C2 commit `365c07c` 推送后，第三个fresh临时sparse clone完成runner+auditor全链。Synthetic admissible control有效，16个integrity checks无失败，24/24 attacks拒绝，runner/auditor合计8/12 short read-only children，stdout与两份receipt均远低于冻结上限。Final verdict从前两次的`INVALID_EVIDENCE`收敛为可信的`BLOCKED_HOST_STABILITY`，19/20 gates通过。

唯一失败门为`DISK_STABILITY_MARGIN`：available 109,111,910,400 bytes，相对精确minimum 112,206,020,608少3,094,110,208 bytes。Codex main/renderer为1/4，最大renderer RSS 1,016,823,808 bytes，Codex tree RSS 4,287,758,336 bytes，低于4 GiB门但只余约7.2 MB；active Blender/B58/browser automation均为0。观察到8个PPID-1 crashpad handlers，仅作为诊断记录，不自动清理、不推定根因。

Rehearsal results/audit SHA为 `a671cc44ac31eff28532275580d908de76052f39ac3de954df727a93b9ada092` / `573672e8487ebf0e4a43e6bfeab2b55645010dc8503af59627ac3f86562e376b`。实际formal root仍不存在；下一动作提交推送本entry，再运行单次真实B59-G0 bounded baseline。

## J-338 · B59-G0真实有界宿主基线：证据有效，稳定性阻断

Date: 2026-08-28 · Type: FORMAL READ-ONLY HOST BASELINE · New Blender processes: 0 · New Blender renders: 0

Release commit `e3237177ecf95a889a03fbfc43939be0fb964c5b` 与`origin/main` exact后，single-use formal runner和独立auditor在真实root完成。Results/audit file SHA为 `5a0132be20d5cc9de439bec3e848b3f89416de282706c2b443c42bb442b48c33` / `06e54e79f7ec1fa7bb60a4cef69ef36830f8bab89bb6d213d6007962c45c4b43`，self-hash为 `709723234ef543a889e0766445fd9dbe3e0e72ef1c1cc889d8a9edf7f6dbdeae` / `d7f9d75ae09aaaa1886eff1a351a2ccae15794bd8c2b0140ce50bff317920f9a`。Receipts只有3,755 / 5,014 bytes；合计8/12 short read-only children，24/24 attacks，synthetic control有效，所有integrity checks通过。

Final verdict为可信`BLOCKED_HOST_STABILITY`，18/20 gates通过。磁盘available 109,110,300,672 bytes，比112,206,020,608-byte稳定门少3,095,719,936 bytes。Codex tree RSS 4,306,321,408 bytes，比4 GiB ceiling高11,354,112 bytes；system-wide memory free仍为89%。进程观察为1 main、4 renderers、最大renderer 1,032,830,976 bytes、0 active Blender、0 B58 worker、0 browser automation。8个PPID-1 crashpad handlers只记录未清理。

该结果不关闭Gate 0，也不授权B58 official run。下一动作是提交推送正式证据，然后只读定位至少约3.1 GB可重建缓存与Codex RSS来源；任何清理或进程处置必须精确到目标，且处置后使用新协议做readmission，绝不降低门槛。

## J-339 · 精确缓存处置与B59-G0-R1 readmission预注册

Date: 2026-08-28 · Type: AUTHORIZED CACHE REMEDIATION / READMISSION PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

在正式blocked evidence commit `d115e5d` 推送后，只读容量定位发现LTX权重本体已经不存在，仅剩空lock；Hugging Face大目录实际为Qwen，因此未把Qwen冒充LTX删除。Colima约25 GiB且属于worker基础设施，也未改动。

使用用户此前明确的缓存清理授权，精确删除六个可重建目标：pnpm store 1,784,520 KiB、Gradle caches 1,032,468 KiB、Bun install cache 715,804 KiB、npm `_npx` 210,528 KiB、npm logs 44 KiB及未运行DaVinci时的`~/Movies/CacheClip` 648,720 KiB。目标`du`合计4,497,494,016 bytes；没有相关包管理器/Resolve进程运行，没有模型、Colima、项目媒体或repo证据被删，也没有发送signal。第一次宽泛`rm -rf`命令被安全层拒绝且未产生变更，实际处置使用每个绝对目标限定的`find -depth -delete`并逐项验证消失。

Formal baseline available为109,110,300,672 bytes；immediate post-cleanup为112,308,187,136 bytes，实测增加3,197,886,464 bytes，比不变的112,206,020,608-byte稳定门高102,166,528 bytes。非正式RSS复测为1 main、4 renderers、Codex tree 4,294,721,536 bytes，仅比4 GiB ceiling低245,760 bytes，因此不能据此宣告稳定。

R1预注册全量复用20 gates、24 attacks及全部阈值，只允许同一runner/auditor新增显式repository-relative `--spec`选择，为fresh root `experiments/codex-host-stability-readmission-v0-1`执行。即使R1 admitted也只允许进入重复观察阶段，不关闭Gate 0、不授权B58。

## J-340 · B59-G0-R1显式spec选择与parent-evidence绑定实现

Date: 2026-08-28 · Type: READMISSION TOOL INTERFACE IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

R1 preregistration commit `27d496a` 推送后，为runner/auditor增加唯一可选接口`--spec specs/name.json`。路径必须匹配repository-relative `specs/*.json`且禁止`..`；无参数行为仍绑定原baseline spec。Selected spec现在决定experiment ID、formal root、release paths、parent commit、阈值与攻击表，results/audit绑定selected spec path与SHA。

R1还在`SPEC_AND_PARENT_IDENTITY`中加入parent results/audit文件SHA复核，确保readmission不能脱离原blocked evidence。Runner/auditor新SHA为 `da28e24ca7f87a8636ddbad5d2fd1d230e72e375458d220e86d4b0cb98cfbd4d` / `a0629f14a6cd2c23c04c580a65cd0932e0ff14ef80cb2537d4350494bd2e3f9d`；R1 spec SHA为 `89bee700c22585c45cfb6019b644091af2bf5df8c11bc33ba106d006b6befe9d`。Node syntax、zero-warning targeted ESLint与diff check通过，R1 formal root仍不存在。下一动作提交推送工具字节，再在fresh临时sparse clone以显式R1 spec排练。

## J-341 · B59-G0-R1 parameterized readmission rehearsal有效

Date: 2026-08-28 · Type: BOUNDED READMISSION REHEARSAL · New Blender processes: 0 · New Blender renders: 0

Parameterized tool commit `fe43248` 推送后，fresh临时sparse clone以显式R1 spec完成runner+auditor。Parent results/audit SHA绑定有效，selected spec path/SHA exact，synthetic control有效，所有integrity checks通过，24/24 attacks拒绝，合计8/12 children且所有禁用资源为0。Results/audit SHA为 `7e46ace77de901a7a5b391621c185f3d74c8eab4f32057a1d767c4c955d40eec` / `15ec063adbb2f7ff6b2292faa8e0dd7e07e6cfe12124edc41adf04cade265e2c`。

Rehearsal final为可信`BLOCKED_HOST_STABILITY`，19/20 gates；磁盘已通过，available 112,283,795,456 bytes、门上余量77,774,848 bytes。唯一失败为`CODEX_TREE_RSS`：4,321,673,216 bytes，超4 GiB ceiling 26,705,920 bytes。额外浏览器检查显示当前in-app browser为0 session tabs / 0 user tabs，因此没有可关闭标签，未执行close或打开新页面。

实际R1 formal root仍不存在。下一动作提交推送本entry后执行真实R1；若RSS仍失败，则保留正式阻断证据并在可恢复断点请求重启Codex，不发送宽泛process signals。

## J-342 · B59-G0-R1真实readmission：磁盘恢复，当前Codex会话RSS阻断

Date: 2026-08-28 · Type: FORMAL HOST READMISSION / RESTART CHECKPOINT · New Blender processes: 0 · New Blender renders: 0

Release commit `9ca67eba93e6937657b1d8b34519d8718961c5e2` 与`origin/main` exact后，真实R1 single-use root完成。Parent B59 results/audit SHA重新验证有效，selected R1 spec path/SHA exact，synthetic control有效，所有integrity checks通过，24/24 attacks拒绝，合计8/12 short read-only children，零Blender/render/browser automation/network/model/Docker/cleanup/signal/restart。Results/audit file SHA为 `86cad7343ac49c33abedb722bea2f63041a9f3ea76f30a93260704b3dfb5fe6f` / `3b3c8bdf1b3a74681339d820ab76b839f76e02c7ee3a1199713c34c738062bee`，self-hash为 `c68791970ea44a95c30ca7960e1d85fde66f08c6e0fff8077586a77098efc472` / `55a8bbbdde8d68f1f4360a43e22215738a8e78d44699556279ce5f7bd6c33ab2`。

Final verdict为可信`BLOCKED_HOST_STABILITY`，19/20 gates。磁盘已通过：available 112,269,066,240 bytes，比不变门槛高63,045,632 bytes。唯一失败为`CODEX_TREE_RSS`：5,069,733,888 bytes，超过4 GiB ceiling 774,766,592 bytes；system-wide memory free仍85%，1 main、4 renderers、最大renderer 1,191,804,928 bytes。In-app browser检查为0 tabs，没有可关闭对象。

当前安全断点完整：全部变化与证据已落盘，未运行B58/Blender。不得杀承载本任务的renderer或在同一失败root重试。下一动作需要用户重启Codex；重启后先预注册fresh R2 post-restart readmission，再运行同一20-gate/24-attack有界链。只有R2通过才进入重复稳定性观察阶段。

## J-343 · B59-G0-R2 post-restart readmission预注册

Date: 2026-08-28 · Type: POST-RESTART READMISSION PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

自动续作时只读确认Codex尚未重启：main PID仍为92848，local start `Fri Aug 28 10:55:25 2026`，已运行约3小时35分；Codex tree RSS 4,687,347,712 bytes，仍超4 GiB ceiling 392,380,416 bytes。磁盘available 112,269,209,600 bytes，仍比稳定门高63,188,992 bytes。没有据此复用R1 root或宣称post-restart。

R2冻结fresh root `experiments/codex-host-stability-post-restart-readmission-v0-1`及restart boundary：exactly one current main、current PID必须不同于92848、旧PID必须不存在。原20 gates及全部资源阈值不变；`CODEX_MAIN_PROCESS_COUNT`在R2中同时承载restart boundary。新增A25 `RESTART_BOUNDARY_MUTATION`，因此R2要求25/25 attacks；baseline/R1仍保持原24 attacks语义。

下一动作先提交推送R2 spec/protocol/journal，再实现main PID投影、独立replay及conditional A25。旧PID仍存在时不得运行R2 formal root。

## J-344 · B59-G0-R2 restart boundary与conditional A25实现

Date: 2026-08-28 · Type: POST-RESTART TOOL IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

R2 preregistration commit `bd32c15` 推送后，runner/auditor的process summary增加排序后的main Codex PID列表。只有selected spec包含`restartBoundary`时，runner才记录previous/current PID、old PID presence、PID difference与boundary verdict，并把它合入`CODEX_MAIN_PROCESS_COUNT`；baseline/R1无restart boundary时仍沿用原语义。

Auditor独立重采main PID列表并要求与receipt exact一致。Synthetic admissible control在R2中使用一个不同于旧PID的合成PID；A25把resealed candidate的current PID改回92848并标记old PID present，必须被semantic validator拒绝。R2为25 attacks，旧spec仍为24。

Runner/auditor新SHA为 `46127189b5491622923fef33d655b69fa699cad375113d241ac756e85b126b8a` / `14bd615626de8667e5a0f5dc091db70e630f901bf988ed6b771896e7750e49ff`。Node syntax、zero-warning targeted ESLint与diff check通过，真实R2 formal root仍不存在。下一动作提交推送工具字节，再在旧PID仍存活的fresh临时clone证明R2 fail-closed且25/25 attacks完整；不消费真实R2 root。

## J-345 · B59-G0-R2 pre-restart负控正确fail-closed

Date: 2026-08-28 · Type: PRE-RESTART NEGATIVE CONTROL · New Blender processes: 0 · New Blender renders: 0

R2 tool commit `ce62f76` 推送后，在旧Codex仍存活时用fresh临时sparse clone执行R2负控，未消费真实R2 root。Runner exact观察current main PID仍为92848，old PID present=true、current PID different=false、restart boundary valid=false；因此`CODEX_MAIN_PROCESS_COUNT`正确失败。Codex tree RSS 4,663,197,696 bytes也失败；磁盘available 112,264,663,040 bytes，仍高于稳定门58,642,432 bytes。

Auditor final为可信`BLOCKED_HOST_STABILITY`，18/20 gates，25/25 attacks，synthetic control有效、integrity failures与failed attacks均为0、合计8/12 children，禁用资源全部为0。Results/audit SHA为 `0789d8f551bcef0de9e8f5beea88f9dccbe28320b2eb76748d9de13b12537e08` / `766915b2572bbb639360b5bc924a0953912226723e2cc6045a58a03603b76e90`。

该负控证明新turn、RSS波动或renderer变化不能伪装成重启。真实R2 root仍不存在。下一动作只接受完整Codex重启后出现不同main PID，再从已推送release运行真实R2；当前旧进程不再增加实验负担。

## J-346 · R2通过、R3磁盘反例与D1/D2受控归因链

Date: 2026-08-29 · Type: HOST-STABILITY READMISSION / DISK ATTRIBUTION / CONTROLLED INTERVENTION · New Blender processes: 0 · New Blender renders: 0

Codex重启后main PID从92848变为26962。真实R2 post-restart readmission最终20/20 gates、25/25 attacks通过；results/audit SHA为 `2bb7ecc7be213dac754d2c81a19da24630659b0d34cba53d308ac424056c4519` / `02a28904b285348c20fe6e24c14c57e127c5cc59e736d40b01e430e5294f8810`。随后R3四样本360.135秒纵向观察保持PID、RSS、browser temp与crash稳定，但available减少3,327,586,304 bytes，唯一失败门为`DISK_RETENTION_BOUNDED`；15 gates中14通过且20/20 attacks，证据有效但host稳定性仍blocked。

D1用四个30秒间隔只读样本跟踪Colima两块稀疏盘及五个Codex/host文件。91.290秒内host loss仅8,941,568 bytes，低于64 MiB material threshold；Colima allocated growth仅16,384 bytes、占host loss约0.18%，不能解释R3的3.33 GB事件。D1为8/8 gates、10/10 attacks的`VALID_ATTRIBUTION_EVIDENCE`，结果只能标记`COLIMA_CONTRIBUTION_OBSERVED`，不得宣称primary attribution。

用户随后明确授权一次`default` Colima及四容器的受控停启。D2完成运行、停止、恢复三段各三个样本；stop/start分别13.590/12.891秒，原四个full container IDs由`unless-stopped`自动恢复，显式container starts为0。全窗口available增加171,732,672,512 bytes，而两块Colima sparse files allocated合计减少3,208,155,136 bytes，绝大部分回收不能归因给Colima。D2形式门因错误要求自动生成的`_lima/colima/lima.yaml`字节哈希不变而保守失败；权威`colima.yaml`、runtime、四容器、disk device/inode/logical size均恢复。Evidence保留failure/recovery而无results/audit，不把operational success伪装成formal causal pass。

## J-347 · R4 post-reclaim 12分钟保留性观察重新准入

Date: 2026-08-29 · Type: FORMAL POST-RECLAIM LONGITUDINAL STABILITY · New Blender processes: 0 · New Blender renders: 0

在D2恢复后的约320 GB available新基线上，R4预注册七个样本、120秒最小间隔、720秒总跨度；沿用R3的1 GiB first-to-last disk-loss ceiling，并把每样本disk floor提高到250 GiB以保护新回收容量。既有R3 runner/auditor只增加显式repository-relative `BFS_STABILITY_SPEC`选择，默认历史R3行为不变；路径越界负控与selected-spec identity自测通过。

正式R4完成7/7样本，跨度720,161 ms。Available从320,158,425,088降至320,027,803,648 bytes，loss为130,621,440 bytes，仅为1 GiB ceiling约12.2%；最低available仍为320,027,803,648。Codex tree RSS first-to-last减少27,344,896 bytes，最大3,842,129,920；最大renderer RSS 975,994,880；memory free最低87%；browser temp保持20,480 bytes且zero growth；main PID全程26962，new crash reports为0。

Producer 14/14 pre-audit gates，independent auditor 15/15 final gates、20/20 attacks，final verdict `ADMITTED_FOR_GATE0_CLOSEOUT`。Results/audit SHA为 `4f7b7dbe2881b20301bee3a7c0897bfad43f7808b5788a09e22b7d247195bfe7` / `f696592bfd8386d6b5696998072a987296655d252cd3b2384eeeefa2f67eb773`。这把Gate 0从`BLOCKED_DISK_RETENTION`提升为`SHORT_WINDOW_READMITTED`，但不把12分钟冒充长期稳定；B58仍等待更长无人值守保留性证明与主动容量防线。

## J-348 · R5容量哨兵首次安装在冗余kickstart处安全回滚

Date: 2026-08-29 · Type: CAPACITY SENTINEL INSTALLATION COUNTEREXAMPLE · New Blender processes: 0 · New Blender renders: 0

R5冻结15分钟user LaunchAgent、250/180/140 GiB warning/critical/emergency floors、10 GiB/10–30 minute与25 GiB/18–30 hour loss detectors、192-sample/48-hour bounded history、256 KiB state ceiling及zero automatic deletion/cleanup/restart。Existing per-job 100 GiB reserve guard不变。Core/auditor self-tests分别9 cases和15 registered attacks，plist lint、Node syntax、targeted ESLint与dry-run通过；preinstall确认formal/state/plist/service targets全部不存在。工具commit `2aa0273167c4faddb7f7083b6c7e9476e4ef1c97`与origin exact后执行一次正式安装。

`launchctl bootstrap`与`RunAtLoad`实际成功，05:48:36Z写出一个self-hashed `HEALTHY` sample：available 319,974,277,120 bytes、browser temp 20,480 bytes、所有prohibited action counters为0。安装器随后要求第二次`kickstart -k`，该命令超过10秒timeout且无stderr，因而formal attempt fail-closed。Rollback精确bootout该label并移除新plist；事后service print exit 113、plist不存在、无sentinel process。v0.1 state保留，formal root只含start/failure且无install/audit。

本机launchctl文档与实测共同说明RunAtLoad已经完成首次执行，额外kickstart不是安装成立所必需。下一动作不复用v0.1 root，不删除失败state；预注册fresh v0.2 formal/state roots，把bootstrap+RunAtLoad fresh sample作为唯一首次触发，并继续要求exact reversible uninstall与independent audit。

## J-349 · R5-C1主动容量哨兵安装与独立审计通过

Date: 2026-08-29 · Type: ACTIVE CAPACITY SENTINEL ADMISSION · New Blender processes: 0 · New Blender renders: 0

C1只把首次触发从`bootstrap + RunAtLoad + kickstart`修正为`bootstrap + RunAtLoad`，其余250/180/140 GiB capacity floors、10 GiB rapid/25 GiB long loss、browser 64 MiB/1 GiB、15-minute interval、192-sample bounded history、256 KiB state ceiling、zero automatic cleanup/restart及15 attacks不变。Fresh v0.2 formal/state roots在release commit `570b0079b4fbb56f5457137b839d37823ef1fdb4`与origin exact后安装。

正式动作只有1 plist create和1 bootstrap；RunAtLoad在05:51:48Z写出`HEALTHY` sample，available 320,036,970,496 bytes、browser temp 20,480 bytes/24 entries、Colima VM/data allocated 1,552,670,720 / 7,346,622,464 bytes。Kickstart/deletion/cleanup/service restart/Docker/Blender/network/model均为0。Installed plist与repo template byte-exact；launchd label保持loaded、runs=1、last exit=0、run interval=900 seconds。Periodic one-shot在样本间`not running`是预期状态，不要求常驻进程。

Independent audit通过10/10 gates、15/15 attacks，final `ACTIVE_CAPACITY_SENTINEL_ADMITTED`。Install/audit SHA为 `b1ec4be0c7a4097648ef1104a3156d146cb35552c28b53116d22d2f23d9b4e94` / `3e971023a840497d29647f29bf9eff3d3e885e2890665f6f07642c00890b3532`。容量预警机制现在已主动运行，但Gate 0仍等待它积累无人值守样本并审计cadence与趋势；B58继续暂停。

## J-350 · R6首次自然周期证明LaunchAgent无人干预续跑

Date: 2026-08-29 · Type: UNATTENDED RETENTION INTERIM OBSERVATION · New Blender processes: 0 · New Blender renders: 0

R6 runner与independent auditor已在commit `3abfc873feaf687ee2b0c94a0132dace7a587191`实现并推送；两者self-test分别通过5-sample/3,600-second aggregate与15 registered attacks。正式root `experiments/host-capacity-retention-v0-1`保持不存在，观察期间没有使用`kickstart`、restart或任何手动采样。

LaunchAgent在首样本后自然等待900秒，于06:06:48.444Z写出第二个self-hashed `HEALTHY` sample。相邻间隔为900,223 ms；launchd runs从1精确增为2，last exit仍为0、run interval仍为900秒。Available从320,036,970,496降至319,973,339,136 bytes，900秒正向loss为63,631,360 bytes，折算约0.237 GiB/hour，低于冻结的1 GiB/hour ceiling；browser temp保持20,480 bytes、zero growth；Colima combined allocated仅增加262,144 bytes；全部prohibited-action counters继续为0。

R6 preflight正确返回`WAIT_UNATTENDED_RETENTION`、sampleCount 2、span 900,223 ms、formalRootAbsent true，不因两个健康点提前创建证据或宣布长期稳定。下一动作保持LaunchAgent自然运行，至少积累5个样本与3,600秒first-to-last span后，冻结完整历史并运行12-gate/15-attack独立审计。

## J-351 · R6一小时宿主观察健康，但A09控制反例使审计无效

Date: 2026-08-29 · Type: FORMAL UNATTENDED RETENTION / AUDIT COUNTEREXAMPLE · New Blender processes: 0 · New Blender renders: 0

LaunchAgent无人干预地产生5个样本，四段间隔为900,223 / 900,151 / 900,195 / 900,252 ms，首尾跨度3,600,821 ms。Preflight在sampleCount 5、latest age 27,621 ms、service loaded、fresh formal root、release commit与origin均为`381d434cfad1c9ff640ee5cb539a0c29e40c8bf7`时返回`READY_UNATTENDED_RETENTION`，随后冻结完整历史；没有kickstart、restart、手动采样或历史切片。

Runner的11/11 pre-audit gates全部通过，provisional `ADMITTED_PENDING_AUDIT`。Minimum available为319,742,877,696 bytes；first-to-last loss 294,092,800 bytes，归一化294,025,745.795 bytes/hour；maximum interval loss 95,473,664 bytes。Browser保持20,480 bytes且zero growth；Colima combined allocated growth 602,112 bytes、归一化601,974.716 bytes/hour；五个样本全部`HEALTHY`且prohibited actions为0。Codex仍为同一PID 26962、同version/hash/bundle，首样本后没有新crash report。Results SHA为`1104d6edf251bfbfb041e6f96d482a7fd8968676f2249f8971bfc6b8070e7311`。

Independent audit的START/SNAPSHOTS/RESULTS/GATE_PROJECTION/RELEASE/PARENT/LIVE_LAUNCHD/LIVE_RUNTIME/NO_ALERT九项完整性检查全通过，但15个攻击只拒绝14个。唯一逃逸为`A09_DISK_RATE_BREACH`：它把last available固定成first available减`1 GiB + 1 byte`；真实span比一小时长821 ms，因此归一化rate反而略低于1 GiB/hour，同时相对第四个真实样本的single-interval loss也未超过1 GiB。Auditor据此正确给出11/12 gates的`INVALID_UNATTENDED_RETENTION`，audit SHA为`464eca68fafe518997bd08d80b931a5af422ee44159243dcad1ceef78cfe6f94`。

这不是宿主容量反例，而是mutation-control算法没有按实际span构造严格越界值；生产阈值和健康观测均不改变。失败root原样保留。下一动作先推送该证据，再预注册fresh C1 root，只把A09 loss改为`floor(maxRate * actualSpanHours) + 1`并证明独立重算必然越界；不得复用原root、重写audit或选择更有利的历史子集。

## J-352 · R6-C1跨度归一化A09修正预注册

Date: 2026-08-29 · Type: AUDIT CONTROL CORRECTION PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

R6 INVALID evidence commit `10842726f48d2a3a24c22a30b7ee44be45958638`推送后，C1冻结fresh root `experiments/host-capacity-retention-c1-v0-1`并绑定原results/audit SHA `1104d6ed…` / `464eca68…`。原root、原audit和原`INVALID_UNATTENDED_RETENTION` verdict不修改。

C1完整复用R6的source、runtime identity、250 GiB floor、1 GiB/hour host与Colima rate ceilings、1 GiB maximum interval loss、browser bounds、900-second launchd cadence、12 gates、15 attack IDs及所有byte/resource ceilings。唯一允许的语义修正是A09 mutation：`breachLossBytes = floor(maximumRate * actualSpanMs / 3,600,000) + 1`，并要求auditor在计数前独立证明重算rate严格大于门槛。

Runner/auditor只允许增加安全的repository-relative `--spec specs/name.json`选择；无参数仍绑定原R6 spec。下一动作先提交推送本预注册，再实现selector、A09 helper和over-one-hour drift self-test；在工具commit与origin exact、fresh C1 root及live history仍满足资格后才可执行。

## J-353 · R6-C1 spec选择与跨度归一化A09实现

Date: 2026-08-29 · Type: AUDIT CONTROL CORRECTION IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

C1 preregistration commit `1a5a534db7e345d3b2ed811e5bf26d406972867f`推送后，runner/auditor增加严格匹配`specs/[safe-name].json`的显式`--spec`接口；未提供时仍选择原R6 spec，`../`路径负控以exit 1拒绝。Runner输出中的spec path现在绑定实际selected spec。

Auditor新增唯一的`diskRateBreachLoss`修正：从候选首尾时间重算span，构造`floor(maxRate * spanMs / 3,600,000) + 1` bytes，并在施加mutation前断言重算rate严格大于maxRate。专门的3,600.821-second drift self-test通过；默认R6与C1 spec下的runner/auditor self-tests、Node syntax、zero-warning targeted ESLint及diff check均通过。

Runner/auditor SHA为`a7bf65bef9faf7a10c407fbb0d71d1d1b0213ed3aa4ad4f2122bad6dcad6a642` / `b7638d0c67186ba18a266a48e0a2784ab5215f64036a21af4190a72b27df6ecd`。C1 read-only preflight在5 samples、3,600,821 ms span、latest age 222,438 ms、service loaded、fresh root时返回READY。下一动作只提交推送工具与本entry；随后从HEAD/origin exact的release运行fresh C1 root和独立审计。

## J-354 · R6-C1一小时无人值守容量保留性正式准入

Date: 2026-08-29 · Type: FORMAL UNATTENDED RETENTION READMISSION · New Blender processes: 0 · New Blender renders: 0

Correction tool commit `ce54c4fc808644f11a8aa2501fdd52147b8bafc9`与origin exact后，C1 preflight在完整5-sample history、3,600,821 ms span、latest age 248,594 ms、service loaded、fresh root和父INVALID evidence SHA exact时READY。Fresh runner再次通过11/11 pre-audit gates，未改动原R6 root。

Independent auditor的九项file/live integrity checks全部通过，span-normalized A09及其余14个攻击全部被拒绝，最终12/12 gates、15/15 attacks，verdict `ONE_HOUR_UNATTENDED_RETENTION_ADMITTED`。Results/audit SHA为`f0c246f1b2f295cbf07b0a2dc1f3e948677f2a16c213142551582355b5a81045` / `0643f75e223f35be81dfa11f4255d54044b369dc85da3fcb3bc3dd46565598db`；receipt仅3,062 / 2,922 bytes。

冻结历史的minimum available为319,742,877,696 bytes；host loss 294,092,800 bytes、294,025,745.795 bytes/hour；maximum interval loss 95,473,664 bytes；browser zero growth；Colima growth 602,112 bytes、601,974.716 bytes/hour；5/5 severities HEALTHY、prohibited actions全0。同一Codex PID 26962持续存活且无新crash report，launchd runs 5、last exit 0、interval 900秒。

C1关闭了R6长期无人值守输入，但不单独关闭Gate 0。下一动作提交推送C1证据，然后预注册Gate 0 closeout：只聚合R2 restart readmission、R4 post-reclaim、R5 active sentinel、R6-C1 unattended retention及D2 operational recovery facts，逐项验证hash、verdict、live sentinel与可恢复性，禁止把D2形式失败改写成因果成功。

## J-355 · B59-G0宿主稳定性closeout预注册

Date: 2026-08-29 · Type: GATE 0 CLOSEOUT PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

R6-C1 admission commit `378765dee04313178936ad68ba593623691ab764`推送后，Gate 0 closeout冻结fresh root `experiments/gate0-closeout-v0-1`、15 gates和20个定向攻击。正证据为R2 20/20+25/25 post-restart、R4 15/15+20/20 post-reclaim、R5-C1 10/10+15/15 active sentinel及R6-C1 12/12+15/15 one-hour retention；所有results/audit paths与SHA逐个冻结。

反证据也成为硬门：R3的`DISK_RETENTION_BOUNDED`失败、R5-v0.1的kickstart failure与exact rollback、原R6的14/15 invalid audit均必须存在、hash exact且不得重标为成功。D2继续是formal failure；closeout只允许从start/stop/start/failure/recovery receipts验证一次stop/start、exact four IDs、authoritative config、profile/runtime与disk identity的操作恢复，同时必须保留generated `lima.yaml` hash mismatch，不得宣称Colima因果归因。

Live门要求哨兵plist byte-exact、launchd loaded/900 seconds/last exit 0、latest age不超过1,200秒、HEALTHY、available至少250 GiB、browser低于64 MiB、history bounded、无alert；Codex须维持PID 26962与同version/hash/bundle，且R6 cutoff后无新crash report。Closeout自身禁止Blender/Docker/network/model/cleanup/service mutation。

Auditor必须独立重读全部parent artifacts和live state；20个attack逐项指定必须翻转的目标gate，避免靠无关hash gate吸收攻击。只有15/15 gates、20/20 attacks才可输出`GATE0_HOST_STABILITY_CLOSED`，且只允许进入独立B58 minimal preflight。

## J-356 · B59-G0 closeout runner与定向攻击auditor实现

Date: 2026-08-29 · Type: GATE 0 CLOSEOUT TOOL IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

Closeout preregistration commit `14fe6ca519ab23e497b683cdc9547d4ed35ba921`推送后，实现只读runner和不import runner的独立auditor。Runner重算19份父证据的file/self hashes、全部positive/negative verdict、D2 operational boundary、live sentinel与Codex/crash边界；正式模式只允许在fresh root exclusive写start/results。Auditor独立重读同一19份证据与live state，并对20个attack逐项要求其指定target gate从true变false。

Runner/auditor SHA为`9464bcd0c49850eb3582e702d05a8f9ebd9db3482a9a053f8b7f1c54ebeabdbd` / `26758d87ff9742ba90deba6f4db07362cbbd255703ee8b425e7489c21efd5479`，209 / 196 lines、19,889 / 21,423 bytes。两者self-test、Node syntax、zero-warning targeted ESLint与diff check通过。Live preflight当前除`SPEC_RELEASE_AND_EVIDENCE_HASHES`外全部门为true；该唯一失败由两份新工具尚未提交导致，evidence hashes exact、sampleCount 5、latest age 776,695 ms、formal root absent。

下一动作只提交推送工具与本entry，再在fresh临时clone执行完整runner+auditor rehearsal；只有15/15与20/20同时通过且当前正式root仍不存在，才运行真实closeout。

## J-357 · B59-G0 closeout fresh-clone全链排练通过

Date: 2026-08-29 · Type: GATE 0 CLOSEOUT REHEARSAL · New Blender processes: 0 · New Blender renders: 0

Tool commit `04e00ef782ffb8846c1171e58bd4f9d0dfe25ec6`与origin exact后，在fresh shared clone `/tmp/bfs-g0-rehearsal.GFetIF/repo`执行完整preflight、runner与auditor，未消费真实formal root。Preflight在19份evidence hashes exact、sampleCount 5、latest age 837,730 ms和release clean时READY。

Runner通过14/14 pre-audit gates；independent auditor通过15/15 final gates、20/20 targeted attacks与START/RESULTS/SPEC/EVIDENCE_RECEIPTS/RELEASE/GATE_PROJECTION/LIVE_SENTINEL/LIVE_RUNTIME八项integrity checks。Final rehearsal verdict为`GATE0_HOST_STABILITY_CLOSED`，resource accounting对Blender/Docker/network/model/cleanup/service mutations全部为0。

Rehearsal start/results/audit SHA为`8285207745b43b393f566a2f6d25ceacd012473004b446dde3517df381c48191` / `9d93a7c9401eb22027251f3d208e9885918d0859e1d417070bcaf1847878c475` / `83f713c48ff4aec0d3565565633621d25c4b28127d3ffa52a1a5ae450ad2bb32`，bytes为6,858 / 10,385 / 6,241，均远低于64 KiB ceiling。临时目录随后用exact target逐项删除并验证不存在；第一次`rm -rf`请求被安全层拒绝且未执行。真实formal root仍不存在。

下一动作提交推送本entry，然后在HEAD/origin exact且live sentinel仍fresh时运行单次正式Gate 0 closeout。

## J-358 · B59-G0宿主稳定性Gate 0正式关闭

Date: 2026-08-29 · Type: FORMAL GATE 0 HOST-STABILITY CLOSEOUT · New Blender processes: 0 · New Blender renders: 0

Rehearsal journal commit `063ecef58b4ef289b3505a78295ea2517d90a0e9`与origin exact后，真实preflight在19份evidence hashes exact、sampleCount 5、latest age 875,237 ms、release clean及fresh formal root时READY。Single-use runner通过14/14 pre-audit gates，独立auditor通过15/15 final gates、20/20 targeted attacks和八项integrity/live checks。

Final verdict为`GATE0_HOST_STABILITY_CLOSED`。Results/audit SHA为`588da9723eb7cfd7c611e2eb8122da1e6d29a93bee19e55c36eae85fbf0db54a` / `6d3a372f5fc3f07a3a154d22b8e9d124b264a8d4532db2fd5a777f3ed6395af7`；start SHA为`977ff21d31efb5fb6a82f69d4a60ed6a459cf5a1d195a01e57483fa4a5e720f4`。

Audit时live sentinel为HEALTHY、latest age 882,411 ms、available 319,742,877,696 bytes、browser temp 20,480 bytes、无alert；launchd loaded、runs 5、last exit 0、interval 900 seconds。Codex仍为PID 26962、expected version/hash/bundle且无新crash report。Closeout自身Blender/Docker/network/model/cleanup/service mutation全0。

Gate 0现在从`SHORT_WINDOW_READMITTED`正式提升为`CLOSED_WITH_ACTIVE_SENTINEL_AND_TESTED_RECOVERY`。这只解除宿主安全阻断；下一动作提交推送证据后执行独立B58 minimal preflight，只有preflight通过才允许恢复B58生产编排验证。

## J-359 · B58-E1-C2 Gate 0绑定修正预注册

Date: 2026-08-29 · Type: B58 PREREGISTRATION CORRECTION · New Blender processes: 0 · New Blender renders: 0

Gate 0 evidence commit `5d7d307cbc389592b765b6ad021a9796f232f432`与origin exact后，静态审查确认B58三份formal candidate tools是在J-309–J-329 development matrix后、J-330暂停点留下的未跟踪候选；三个official roots仍全部不存在。Candidate绑定B57与C1，但尚未绑定后来成为硬前置的Gate 0，不能原样执行official preflight。

C2冻结唯一修正：把原34门中的`PREREGISTRATION_AND_TOOL_FREEZE_PUSHED`有效解释替换为`PREREGISTRATION_TOOL_FREEZE_AND_GATE0_CLOSED`，denominator仍34。Official preflight必须在创建任何五个production preflight children之前验证Gate 0 results/audit exact SHA、自哈希、`GATE0_HOST_STABILITY_CLOSED`、15/15 gates、20/20 attacks，以及fresh self-hashed HEALTHY sentinel、250 GiB floor、64 MiB browser ceiling与无alert；runner/auditor必须绑定同一receipt。

新增6项C2攻击覆盖results/audit SHA、verdict、gate/attack counts和stale sentinel；原72 attacks、C1 8 attacks、DAG、process ceilings、100 GiB+0.5 GiB disk门及zero render/model/network/Docker均不变。下一动作先提交推送C2 spec/protocol/journal，再修改未冻结candidate tools；正式根继续禁止创建。

## J-360 · B58-C2 Gate 0绑定与formal tool-freeze候选实现

Date: 2026-08-29 · Type: B58 FORMAL TOOL IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

C2 preregistration commit `6dba91af525351b64c2147a63bf1681569ed9e29`推送后，official preflight现在在创建任何production-preflight child之前重读Gate 0 results/audit及live sentinel，验证exact hashes/self-hashes、15/15、20/20、HEALTHY、freshness、250 GiB floor、browser ceiling与无alert；receipt进入preflight。Formal runner在创建attempt root前复核同一binding，independent auditor再次重开evidence/live state并要求6/6 C2 attacks。

Tool-freeze前静态审查还发现machine-readable B58 spec已冻结`job:production` alias，但package尚无该键；现补为exact命令`node scripts/run-restart-safe-production-job.mjs`并纳入preflight hash scope。Auditor里一个原candidate从未读取的`allCompletedExact`局部赋值被机械删除，不改变任何gate或结果。

当前package/preflight/runner/auditor SHA为`6d13fa59a730d1b418208bfb7d28bc319b20d120aef98433e60a531fd20960af` / `11bc9221a23cac6f32c01cc1173f399bf435e7edf392b1779a815b25da866d10` / `29cad215ace783490641b12fc52a628fc631754c7fe17238a3a5d3f34afee794` / `f8571196cd4c425a987545b3b52ce7a5cf97bc572ca9a94311312a8de0ad9d53`；ledger/orchestrator保持`0946685b…` / `d8f3126f…`。三份formal scripts的Node syntax、zero-warning targeted ESLint、diff check及alias assertion通过，Gate 0与sentinel hashes也由B58自身canonicalizer验证。

下一动作提交推送package、三份formal tools和本entry形成tool-freeze commit；之后在fresh临时clone先跑official preflight rehearsal，验证Gate 0 fail/pass binding、zero Blender和五份production preflight，再决定是否消费真实preflight root。

## J-361 · B58 zero-Blender rehearsal发现package alias与B57 freeze冲突，C3预注册

Date: 2026-08-29 · Type: B58 PREFLIGHT COUNTEREXAMPLE / CORRECTION PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

Tool-freeze candidate commit `52b91bda366d732640632cd0ac49e3a770d7ba7a`与origin exact后，fresh clone首次因无`node_modules/ajv`在module load前退出且未创建root；链接主仓库只读依赖后重跑，B58 preflight通过Gate 0读取，但第一个B01 preferred production preflight未生成accepted receipt。单独复现得到self-hashed `REJECTED / RELEASE_BLOB`，message `Release hash mismatch for package.json`，receipt SHA/self-hash为`618aece343a3c01c39e85c2f965201763bb567c5efda26546d72a009f8765aa5` / `ce633332f017f3c51fae469eb90811d7af3d7b2ccf497f69059307021348a8bb`，Blender/render/model/network/Docker全0。

根因是B57把package冻结为`a2235a7558…`，而新增`job:production` alias使其变成`6d13fa59…`。原B58 convenience alias要求与B57 byte-exact production surface不可同时成立，且parent安全门优先。三个official roots仍不存在。

C3唯一授权修正是恢复package到B57 exact bytes，并把effective entry冻结为alias原本会调用的同一direct command `node scripts/run-restart-safe-production-job.mjs`。新增2项攻击分别变异package hash与direct command；B58 orchestrator bytes/modes、34 gates、72+C1+C2 attacks、DAG、process ceilings和disk门不变。下一动作先提交推送C3，再执行package恢复和tool检查。

## J-362 · B58-C3恢复B57 package并冻结direct entry

Date: 2026-08-29 · Type: B58 TOOL-FREEZE CORRECTION IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

C3 preregistration commit `fd808bffd0a02109dff349d9d821d9ec0ad4df3d`推送后，移除新增alias，使`package.json`恢复B57 exact SHA `a2235a7558d420c86acb62eafda2c52fbfc1620c1de934fa88e02eea27381520`。Preflight把C3 spec/protocol与commit加入tool-freeze ancestry/hash scope，并要求B58 spec command exact等于`node scripts/run-restart-safe-production-job.mjs`且package无新增alias；runner在attempt root前复核；auditor新增2个定向攻击。

修正后preflight/runner/auditor SHA为`4f70246ad2b6d015fbe1592939ce99b4f576b3f0a377b95651c3420ded6178d6` / `689f9b4d1cd0402dde7b22a772b912514d38fcdc6ec200225405ef8d37466f39` / `3bba47733e7c58a84296b1616c29b0d67b84a973739db14f2507b5a36d9adbee`。Node syntax、zero-warning targeted ESLint、diff check、package hash与alias-absence assertions全部通过。

下一动作提交推送这一有效tool-freeze，然后用fresh clone重跑official preflight rehearsal；前一临时failure保留为C3反例，不复用其root。

## J-363 · B58 fresh-clone rehearsal发现nested preflight parent contract，C4预注册

Date: 2026-08-29 · Type: B58 PREFLIGHT COUNTEREXAMPLE / CORRECTION PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

C3有效tool-freeze commit `8f8a07d41c8237575011d1480baff0e45fa5289b`与origin exact后，fresh clone中的flat production preflight返回`ACCEPTED`且operations全0；B58 exact nested layout `<preflight-root>/production-preflights/BASELINE_B01`却在创建最终目录时返回`ENOENT`。根因不是release、Gate 0或磁盘门，而是B57 production preflight的持久化目录接口只创建最终一级，要求immediate parent预先存在。B58 caller没有准备`production-preflights` parent；它随后未检查child exit就读取不存在的receipt，又用第二个`ENOENT`遮住原始原因。

Direct child与outer stderr line hashes分别为`590727f67f0260937d4684669ac2925d8bab7d3b05eb958758deaf94c1c0dfb2` / `91ba680702818d9f56c03b317fbf4af1eb522e5e5898a6d4011fde2762c2dc58`。两次调用均为zero Blender/render/model/network/Docker；三个official roots仍不存在。

C4仅授权B58在所有既有admission checks之后、首个child之前durably创建exact parent `<b58-preflight-root>/production-preflights`，并在读取receipt前检查child exit/receipt presence，失败时停止后续children并传播bounded stdout/stderr。B57 bytes、case final-root exclusive creation、34 gates、72+C1-C3 attacks、DAG/process/disk/recovery/verdict均不变；新增2项攻击覆盖parent preparation removal和child-failure propagation bypass。下一动作先单独提交推送C4 spec/protocol/journal，再改candidate tools。

## J-364 · B58-C4 nested parent与child failure propagation实现候选

Date: 2026-08-29 · Type: B58 TOOL-FREEZE CORRECTION IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

C4 preregistration commit `cc808b45cacd50e415c957c6a40694e07f0151dc`推送后，B58 preflight现在在Gate 0、release、paths、disk及scene/plan检查完成后durably创建exact parent `<output-root>/production-preflights`，各B57 child仍exclusive-create自己的case final root。每个child返回后先检查exit code和receipt presence；失败时以case id、exit/signal及最多4096 bytes stdout/stderr停止序列，不再读取缺失receipt，也不启动后续children。

Runner在materialize attempt root之前复核C4 spec hash、parent spelling、policy、5份nested accepted receipts；independent auditor直接重开B58 preflight source和evidence，2项C4攻击分别变异parent preparation与failure-before-read ordering。原34 gates、72 attacks、C1 8、C2 6、C3 2和所有B57 bytes不变。

新的preflight/runner/auditor SHA-256为`e5a5f119bd036557a667be840bc52b2e6ed18ed6d4501dae31c0cf00fce47242` / `7b87b0fcf719ef2c8a9bd50e4f89cc42b515484f2ee152808c9aab26a0dfae22` / `dba355aaed6f12c64858e8d8c40cf194b2d12a3f60f6c79997a3722dcc74ca17`；ledger/orchestrator保持`0946685b991c588fb1ecd6417445c1da42e544026d864d205f3ca69971e07d13` / `d8f3126f34c15d6adb1c6c2324b640fa9aa0756733d008d3087a5b5ab7b5b41a`。三工具Node syntax、targeted ESLint zero-warning与diff check通过；official roots仍不存在。下一动作提交推送这组exact bytes，再在fresh clone运行zero-Blender rehearsal。

## J-365 · B58 official preflight拒绝错误commit输入，C5保留失败并预注册v0.2 retry roots

Date: 2026-08-29 · Type: B58 OFFICIAL PREFLIGHT INPUT FAILURE / RETRY PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

C4 tool-freeze commit `c86476405af442b419141e69609bfaed59c7f3cd`推送后，fresh clone rehearsal通过16/16、5/5 production preflights、4/4 job requests且operations全0。随后第一次official invocation误传了不存在的40位SHA `c8647647743e5e0ba55eb94b4b330ee693d8997a`。首个B57 child正确产生self-hashed `REJECTED / RELEASE_COMMIT`，message为`Release commit is missing: fatal: Needed a single revision`；C4在读取前检测exit 1并停止，未启动其余children。

失败receipt固定在`experiments/restart-safe-production-orchestrator-preflight-v0-1/production-preflights/BASELINE_B01/preflight.json`，SHA/self-hash为`5b49bd337055e088efa091dba3228b4296c66861108294e0d86d0cd28ec8cec5` / `151776edd83415305481eb9e19a7e5386fbb8d54e657309a2dcd98a045e427a9`，operations证明Blender/render/model/network/Docker均0。Outer receipt、v0.1 attempt root和v0.1 formal root不存在。

不得覆盖或清理v0.1失败。C5授权exactly one retry使用fresh/disjoint v0.2 preflight/attempt/formal roots，并要求preflight、runner、independent auditor都重开并验证v0.1失败证据与v0.2 root binding；新增2项攻击覆盖失败证据消失/变异及v0.1 root复用。原34 gates、72+C1-C4 attacks及所有生产语义不变。下一动作提交推送C5 spec/protocol、失败receipt与本entry，然后实现三工具binding；v0.2 roots在此之前不得创建。

## J-366 · B58-C5 retained failure与v0.2 root binding实现候选

Date: 2026-08-29 · Type: B58 TOOL-FREEZE CORRECTION IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

C5 preregistration/evidence commit `52e7e6e56169151bcf339bd8dbc794f5748170f1`推送后，preflight仅接受correction中三条exact v0.2 roots；在创建新root前重开v0.1失败receipt，验证SHA/self-hash、`REJECTED / RELEASE_COMMIT`、错误submitted commit、outer receipt absent及operations全0，并把C5 spec/protocol/failure receipt纳入tool-freeze blob scope。Runner在创建v0.2 attempt root前再次验证同一failure和三根binding；independent auditor第三次直接重开failed receipt并执行2项C5 mutations。

Formal gate denominator保持34；semantic gate现同时要求72 original attacks、C1 8、C2 6、C3 2、C4 2、C5 2。新的preflight/runner/auditor SHA-256为`cdf04560605bfad99113f6f9bd4d2dc01fb9f1fce579e4dbd34c4701fe539fb3` / `61a3030ea80ffd574853022799da00a14633542b27cf3fd4a2a03da1e309c6c1` / `b1139156ecfb526a10dfdf136b3250432b944b40fc3e87233e0772c9a45553b5`。Node syntax、targeted ESLint zero-warning及diff check通过；v0.2 roots仍不存在。下一动作提交推送这些exact bytes，fresh clone rehearsal必须使用git解析出的完整HEAD，而不是手写SHA。

## J-367 · B58-C5 fresh rehearsal与official v0.2 preflight接受

Date: 2026-08-29 · Type: B58 OFFICIAL PREFLIGHT ADMISSION · New Blender processes: 0 · New Blender renders: 0

C5 tool-freeze commit `9276afbfd61c078d199050e0cd1f82ed145d4de8`与origin exact后，在fresh clone用`git rev-parse HEAD`生成SHA并运行v0.2 exact roots：17/17 checks、5/5 B57 production preflights与4/4 self-hashed job requests全部接受，preflight self-hash `90244caf5cd8abe678955657a0b0e25734aa1ae325bf9394e6c30fd9815025d7`，operations全0。Retained v0.1 failure再次验证SHA/self-hash/status/reason exact。

主仓库随后同样用Git动态读取full HEAD，先验证三条v0.2 roots absent，再运行一次official preflight。结果`ACCEPTED 17/17`；preflight file SHA/self-hash为`b2eb355738425d448b8ab4442eaa80886ce0476efaedc2e292d62a7738de7aa1` / `d0ba9a6f717f83d8c5921b0c1d387688cd2248530f66440751d1da8fc77d87ef`。共10份文件：outer receipt、5份accepted child receipts与4份job requests。Gate 0 live sampleCount 7、age 439,997 ms、HEALTHY、available 316,820,500,480 bytes、browser 20,480 bytes、alert absent；Blender/render/model/network/Docker均0。

下一动作只提交推送v0.2 official preflight 10 files与本entry形成evidence commit。Formal runner必须以该exact evidence commit入场；在此之前v0.2 attempt/formal roots继续不存在。

## J-368 · B58 formal v0.2启动前失败，C6预注册runtime parents与v0.3 retry

Date: 2026-08-29 · Type: B58 FORMAL COUNTEREXAMPLE / CORRECTION PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

Official preflight evidence commit `ea2ccc26bad60de83e45d0052d046b70e2b83bb7`与origin exact后，formal admission成功并创建self-hashed attempt/admission/receipt及AUTHORIZED formal-start。Baseline job完成PLAN_BIND，随后记录npm production wrapper PID 9206，但没有`NATIVE_PROCESS_OBSERVED`、production attempt/output、audit或outer result receipt；runner fail-closed返回`Native Blender completed or failed before durable process identity observation`。进程检查无Blender存活。

Fresh clone隔离诊断直接运行同一B57命令，0.31秒、exit 1、明确返回`ENOENT`创建nested production-attempt final root失败。因此不是短Blender漏采，而是Blender从未启动：B58创建了v0.2 attempt/formal roots，却未创建它传给B57的immediate parents `production-attempts`与`outputs`；B57 final-root-only durable mkdir contract按设计拒绝。B58又在native observation为空时丢弃已完成wrapper terminal，导致误分类。

Retained v0.2 attempt/formal tree共13 files，canonical tree SHA `ac13387581ecdd0293fe8b16e7e579fe1f32ab02207657d90d284171797b5b72`；last PROCESS_STARTED file SHA/event hash为`118f91d384c59b5f8359ecbf9c85d0c1d6e450fe14cfda767a33b5ff638ffd12` / `456d11d33b36a1af17cb49a4f4c3ad6b44a4c8b05128d4b31dee348a474358b4`。C6授权B58在spawn前durably创建两个exact parent，保留B57 exclusive final roots；wrapper先结束时必须先写FAILED non-promotable terminal receipt。v0.2永久失败，只允许fresh/disjoint v0.3三根重试。新增5项攻击；34 gates、72+C1-C5 attacks、Blender ceiling及所有生产语义不变。下一动作先提交推送C6、13-file failure tree与本entry，v0.3 roots在此之前禁止创建。

## J-369 · B58-C6 runtime parent与terminal failure retention实现候选

Date: 2026-08-29 · Type: B58 TOOL-FREEZE CORRECTION IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

C6 preregistration/evidence commit `542aecaa882133eac8b3609def0d25403bd97e18`推送后，restart-safe job在candidate final-root freshness/overlap验证之后、npm spawn之前，用ledger durable recursive mkdir创建`dirname(productionAttemptRoot)`与`dirname(outputRoot)`；B57仍exclusive-create两个final roots。若wrapper先于native observation终止，job先写`FAILED`、`promotable:false` attempt receipt，保存wrapper identity及bounded terminal hashes/exit/signal，再fail-closed传播；成功路径仍必须有live native identity。

B58 preflight/runner/auditor现在把C6 spec/protocol与13-file v0.2 failure tree纳入hash/commit scope，重算tree SHA `ac133875…`，只接受v0.3 exact roots。C5 retained v0.1与v0.2 historical root authorization仍作为历史攻击独立复核；C6新增5/5 attacks覆盖tree、两个parent、terminal retention与v0.2 reuse。Formal denominator仍34。

Orchestrator/preflight/runner/auditor SHA-256分别为`ee321de2cc025f502b5a845ccda7f7042bb18dbf0181fb2515f95783bd1502ef` / `e0309ecee5022b97856a64c9dd41a054c130fdffe00a16dfbc0942ba15850725` / `69828fafab17cd679a35f4396dbc849e99c5e017ef286d2909d67d37471f0c2a` / `a1d186a8007005fe3d467b38b9adcc87f8e5b57338a1209d80a7dfb178a1521a`；ledger保持`0946685b…`。四工具Node syntax、targeted ESLint zero-warning及diff check通过；v0.3 roots仍不存在。下一动作提交推送tool-freeze，再在fresh clone生成并运行v0.3 zero-Blender preflight。

## J-370 · B58-C6 fresh rehearsal与official v0.3 preflight接受

Date: 2026-08-29 · Type: B58 OFFICIAL PREFLIGHT ADMISSION · New Blender processes: 0 · New Blender renders: 0

C6 tool-freeze commit `7eeafb9`与origin exact后，fresh clone以Git动态解析full HEAD运行v0.3：`ACCEPTED 18/18`，self-hash `9bcb1e0cfcc32e79c59ae0e9ce190d91b866869fbed0a45c7dad52ff63a4462e`。主仓库确认三条v0.3 roots absent后运行official preflight，同样`ACCEPTED 18/18`；file SHA/self-hash为`0c2fb6da88002ca862409f831ce0a5dc357b3bad8651c4c7970482b129646ed7` / `a4d85378d80b52fb429a1a77f73ac22623e99a18ccd973a087ecfe77d8d51301`。

Official root含10 files：5/5 production preflights accepted、4/4 job requests self-hashed及outer receipt。v0.1 failure exact，v0.2 13-file tree exact `ac133875…`；Gate 0 live sampleCount 8、age 36,232 ms、HEALTHY、available 312,724,525,056 bytes、browser 20,480 bytes、alert absent。Operations仍为zero Blender/render/model/network/Docker。下一动作提交推送这10 files与本entry形成v0.3 evidence commit，然后formal runner才可创建v0.3 attempt/formal roots。

## J-371 · B58 v0.3完整真实Blender矩阵为BOUNDED，C7预注册immutable re-audit

Date: 2026-08-29 · Type: B58 COMPLETE FORMAL / VERIFIER COUNTEREXAMPLE · Real Blender processes: 7 · New Blender renders: 0

v0.3 evidence commit `6d8532b`与origin exact后，formal runner完整结束并产出operation/audit/results/receipt。真实计数为4 native compile Blender starts（3 success + 1 controlled interruption）、3 artifact-audit Blender starts、合计7；三份completed jobs final receipt均为self-hashed `PASS/promotable:true`，exit-86恢复未重复compile，B02失败attempt retained/non-promotable且新attempt/output重试，live process拒绝duplicate spawn。Render/model/network/Docker全0，结束后无Blender存活。

Old verdict为`RESTART_SAFE_PRODUCTION_ORCHESTRATOR_BOUNDED`：31/34 gates、71/72 original attacks；C1 8/8、C2 6/6、C3 2/2、C4 2/2、C5 2/2、C6 5/5。三项gate失败同源：terminal event实际字段为`payload.receipt`，auditor错误读取`payload.finalReceipt`；A64失败是validator只检查64-hex形状，未要求log hash等于immutable observation。

v0.3 attempt/formal tree共141 files、约1.1 MiB，canonical tree SHA `c7f5ed6bddd030be24d86a8592e5dd80e24832de0ac72e0cd6fad1cf87bbae89`。Old audit file SHA/self-hash `ca162c4b…` / `f52076d5…`，results SHA/self-hash `0cf05356…` / `72cb12e6…`，receipt SHA/self-hash `de96e875…` / `45710ecf…`。C7只授权修独立auditor的两处binding并新增zero-Blender re-audit runner；不得改141-file evidence。下一动作提交推送C7 spec/protocol、完整v0.3 evidence与本entry，再实现新工具；reaudit root在此之前必须不存在。

## J-372 · B58-C7 corrected auditor与immutable re-audit runner候选

Date: 2026-08-29 · Type: B58 VERIFIER CORRECTION IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

C7 preregistration/evidence commit `9de260ff992301a106f81656e7e1faa879d3ea50`推送后，independent auditor只做两处授权修改：final exact读取actual frozen `JOB_FINALIZED.payload.receipt.receiptHash`；accounting validator新增`logSha256 === expectedLogSha256`。新增2项C7 attacks分别变异终结receipt binding与log equality。Scientific support现在要求exact 34/34、72/72及C7 2/2；C1-C6要求不变。

新`run-b58-e1-c7-reaudit.mjs`只用Node built-ins，要求tool-freeze commit等于HEAD/origin，重算141-file evidence tree与old audit/results/receipt hashes，创建独立fresh output，spawn一次Node auditor，前后比较evidence tree byte identity，再写self-hashed results/receipt；operations冻结为1 Node auditor、0 Blender/render/model/network/Docker。

未冻结隔离rehearsal输出到`/tmp`，返回34/34、72/72、C1 8/8、C2 6/6、C3 2/2、C4 2/2、C5 2/2、C6 5/5、C7 2/2，verdict `RESTART_SAFE_PRODUCTION_ORCHESTRATOR_SUPPORTED`，无failed gates/attacks。Auditor/runner SHA-256为`0e414af9a713796ce079735f8f39f2dc53aec68ea6a19edbb88d84e16672be1a` / `663e64d1044dd59058519d2438be00b1438eecb513ff99767563ddc5fb77dadf`；syntax、targeted ESLint zero-warning及diff check通过。正式reaudit root仍不存在。下一动作提交推送工具与本entry形成tool-freeze，再运行一次正式zero-Blender C7 re-audit。

## J-373 · B58-C7正式immutable re-audit支持restart-safe production orchestrator

Date: 2026-08-29 · Type: B58 CORRECTED FINAL AUDIT · New Blender processes: 0 · New Blender renders: 0

C7 tool-freeze commit `026bf1d04a73847427824c6b0d91c3328343cb8e`与origin exact、reaudit root fresh时，runner重算v0.3 141-file evidence tree为`c7f5ed6bddd030be24d86a8592e5dd80e24832de0ac72e0cd6fad1cf87bbae89`，old audit/results/receipt hashes exact，随后只spawn一次Node auditor。Re-audit前后tree fileCount/hash byte exact，未启动Blender。

Corrected independent audit通过34/34 gates、72/72 original attacks、C1 8/8、C2 6/6、C3 2/2、C4 2/2、C5 2/2、C6 5/5、C7 2/2；无failed gates或attacks，final verdict `RESTART_SAFE_PRODUCTION_ORCHESTRATOR_SUPPORTED`。Audit file SHA/self-hash为`6b1f1f8c0d59ecb38d69384dea9633f74f8e8d20fdb79b0efab78a9b10966242` / `bcac6697c735d1cc6572839efb9b870cdf348ac8f0ebe039b0950c1cb3d83c90`；results SHA/self-hash为`f1c5341de4a06f17fa9ae632a4f7b17e3b2a21dd2f5ce3558de86d97c81f96f6` / `3c69da6d5713dd881d6e321a7ba54503465c247a3d9825b15db5a369f46d0f80`；receipt SHA/self-hash为`f6112e89c068207379c0a30cf390822144110d41367a7849e179de6f2b0e9894` / `eef5dbff57191110ea9ca57d58c1c9bb68b5833682a2d16670d94b65a11767d9`。

结论边界：B58现在支持可重启生产编排、持久化stage ledger、exit-86恢复、native Blender受控中断保留/新root重试、live PID拒绝duplicate spawn、3份B01/B02 compile+artifact audit与zero-render操作计数。它不证明最终影院级像素质量、跨镜头角色一致性或成本目标；下一主阶段进入三道生产门，而不是把B58扩大解释为成片完成。

## J-374 · B60三镜头确定编译与共享状态门预注册

Date: 2026-08-29 · Type: B60 PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

B58关闭后，下一项正式实验冻结为B60-E1：同一B03人物资产、ActorSpec、144帧表演、targets、双灯与world组成wide/medium/close三镜头；每镜头独立production compile两次，共六次真实Blender编译。三份输入为`SHOT_6001 / 40 mm`、`SHOT_6002 / 72 mm`、`SHOT_6003 / 100 mm`。各自BuildPlan在预注册前仅做schema/canonical静态检查，expected plan hash为`518bfd62…`、`5213b1b3…`、`a0689507…`。

第一次静态输入尝试使用非数字shot ID，被SceneSpec v0.2 schema在BuildPlan前正确拒绝；Blender启动0。正式输入已改为合法数字ID，三份静态BuildPlan成功。人物资产、ActorSpec与动作文件哈希保持`10feb54a… / 4299388f… / 165ea0b9…`；Blender实机版本为`5.2.0 LTS / fbe6228777e7`，磁盘可用约297 GiB，高于100 GiB reserve。

正式协议预注册15项gate、10项单字段负控、六次production compiler/native Blender上限和zero-render/model/network/Docker边界。共享投影覆盖actor/asset/target/light/world、除目录外的render、output/security与真实scene structure；唯一允许变化为shot标识、camera和两个planned output-root字段。三项candidate tools及三条official roots当前均不存在。下一动作是提交推送本协议与三份SceneSpec，随后才实现preflight/runner/independent auditor。

## J-375 · B60 outer preflight、formal runner与独立auditor候选

Date: 2026-08-29 · Type: B60 TOOL-FREEZE CANDIDATE · New Blender processes: 0 · New Blender renders: 0

预注册commit `97e3afee8fc44695a4a3277265a051dd1a3cf272`推送后，新增三项candidate tools。Outer preflight要求tool-freeze commit等于pushed HEAD/origin，重开七份冻结输入，三份BuildPlan各生成两次，验证identity locks、共享投影与摄影机差异，然后调用六个production preflight children；正式根和attempt根保持fresh。

Formal runner绑定独立的tool-freeze commit与后续preflight-evidence commit，先写self-hashed attempt/admission/receipt，再为六个case各调用一次已准入production compiler，最后只调用一次独立auditor。Auditor不信任runner汇总：它重开七份输入、outer/child preflight、18份authorization records、六份production receipt、BuildPlan、canonical structure、manifest、budget/compile receipt和blend identity，直接验证A/B重复、跨镜头共享投影、camera contract、runtime、root roster与self/file hashes；10项负控均为内存单字段mutation，不改正式证据、不启Blender。

Preflight/runner/auditor SHA-256为`075ac274673b79b728f626a3bf65d8871e4cc992186fda068326a8d693a8a961` / `894f960bdc955a3f0317d04cc558d2a3dc6b14a43ee8245001ab190217006ab0` / `912e8df044543af94ee936348e50f18eef2d4a3f9c7c53d00268562ac5dd7a70`。三工具Node syntax、targeted ESLint zero-warning及diff check通过；三条official roots仍不存在。下一动作提交推送这些exact bytes形成tool freeze，再用fresh clone运行zero-Blender rehearsal；主仓库official preflight在rehearsal成功前不得创建。

## J-376 · B60 fresh-clone rehearsal与official preflight接受

Date: 2026-08-29 · Type: B60 OFFICIAL PREFLIGHT ADMISSION · New Blender processes: 0 · New Blender renders: 0

Tool-freeze commit `0b21584c0acc653f879c2711dc76d92028bf2d70`与origin exact后，全新临时clone先运行同构rehearsal：9/9 outer checks与6/6 production preflights均接受，outer self-hash `7618db3e…`，operations为zero Blender/render/model/network/Docker。第一次用absolute script path的rehearsal invocation因CLI entry identity条件未触发而没有执行，也没有创建主仓库或clone证据；改为clone工作目录内的repository-relative entry后才得到上述有效结果。临时clone随后以validated `/tmp/bfs-b60-preflight.*` target用depth-first delete完整清理。

主仓库确认preflight/attempt/formal三根均不存在后，用同一tool freeze运行official preflight。结果`ACCEPTED 9/9`，6份child preflight全部`ACCEPTED`且各自BuildPlan hash匹配预注册值；outer file SHA/self-hash为`076c6bf7916c5283bf1431943fcdc25f095e61e5cfcb7842af54e22f9ce5c80e` / `10162d643aa784c6bae6184be8c8c3740c7276acddfe3bf48f32e39c7674678c`。七份receipt全部通过独立self-hash重算；available bytes为318,863,503,360，高于107,374,182,400 reserve。Blender/render/model/network/Docker均0，结束后无Blender进程；attempt与formal roots继续不存在。

下一动作只提交推送official preflight七份文件与本entry形成preflight evidence commit。Formal runner必须绑定该exact commit；在此之前不得创建attempt或formal root。

## J-377 · B60六次真实Blender编译支持三镜头结构一致性

Date: 2026-08-29 · Type: B60 COMPLETE FORMAL / INDEPENDENT AUDIT · Real Blender processes: 6 · New Blender renders: 0

Preflight evidence commit `c6a8849`推送且attempt/formal roots fresh后，formal runner绑定tool freeze `0b21584c0acc653f879c2711dc76d92028bf2d70`入场。WIDE/MEDIUM/CLOSE各执行A/B两次production compile，六个wrapper exit 0/signal null，六个native Blender child PID为`72780/72799/72813/72827/72841/72855`且互异。独立auditor返回15/15 gates、10/10 single-field mutation attacks，verdict `CINEMATIC_SEQUENCE_DETERMINISTIC_COMPILE_AND_SHARED_STATE_SUPPORTED`。

外部只读复核重算49个self-hashed records与六份production receipt全部file identities。三组A/B BuildPlan SHA分别为`af06d37b… / 15d64a77… / 9efd903f…`且组内exact；三组structure SHA为`f08f9b78… / 23b5b24d… / 38cdd44a…`且组内exact。跨六次shared BuildPlan/structure/non-camera projection各只有一个hash：`58747e63… / b158aa70… / d808fef7…`。正式树无EXR/PNG/JPG/MP4，render/model/network/Docker均0，结束后无Blender存活。

六个production wrapper合计7.293574833秒；native budget elapsed合计3029 ms、均值504.83 ms，最大sampled RSS 235,077,632 bytes，artifact bytes合计870,206。Attempt/formal tree为28/58 files、57,147/1,117,680 bytes；磁盘仍约297 GiB available。

必须保留的边界发现：同镜头A/B的压缩`.blend` SHA不同，但canonical BuildPlan与structure相同。`nativeBlendBytesDeterministic:false`已在正式运行前冻结，因此没有放宽门槛；结果只支持确定的结构语义，不支持容器字节确定或像素结论。Audit file SHA/self-hash为`526625a3… / 32f65b51…`，results为`2ba5dc63… / 36f87f76…`，receipt为`12937d85… / 312060d8…`。

B60由此关闭输入确定编译门，并关闭跨镜头一致性的结构/契约层；视觉/像素层与影院级渲染成本门仍未关闭。下一阶段必须实际渲染预注册EXR帧，不能继续用compile-only证据外推电影质量。

## J-378 · B61前置真实Cycles资源校准预注册

Date: 2026-08-29 · Type: RENDER CALIBRATION PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

B60正式证据commit `f04919c`推送后，预注册一个非准入校准：绑定WIDE-A已审计scene.blend SHA `9019e6dc…`与production receipt file/self-hash `98d6ab29… / 9cd68189…`，固定frame 72、1920×1080、Cycles CPU、multilayer half-float EXR，分别用32与64 samples启动两个独立Blender进程。输出根`experiments/b61-render-calibration-v0-1`当前不存在。

校准只用于冻结B61正式矩阵的samples、timeout与容量预算；不产生像素复现、视觉一致或电影质量结论。上限为2 Blender starts、2 render calls、2 frames、单进程300秒，100 GiB reserve，zero model/network/Docker。失败文件与日志必须保留，不得覆盖重跑。下一动作先提交推送本协议，再执行两个case。

## J-379 · B61校准v0.1颜色管线反例与C1预注册

Date: 2026-08-29 · Type: RENDER CALIBRATION COUNTEREXAMPLE / CORRECTION PREREGISTRATION · Real Blender processes: 2 · Rendered frames: 2

校准协议commit `4f377ca`推送后，CAL32/CAL64分别exit 0并在3.53/4.99秒写出约1.3 MiB multilayer EXR；但两次stdout均出现4条color-management fallback warnings。冻结的`sRGB - Display / ACES 2.0 - SDR 100 nits (Rec.709) / Un-tone-mapped`被自动替换为系统可用的`sRGB / ACES 2.0 / Standard`。因此这两个EXR不可作为冻结ACES管线的像素或timing证据。

根因是production compiler通过`OCIO`环境变量加载verified config，而独立render invocation遗漏该环境；`.blend`不打包配置。v0.1保留7 files / 2,752,881 bytes，tree hash `2c0623c3…`；failure file SHA/self-hash为`e5ab5bfa… / 52322c6e…`，status `INVALIDATED / OCIO_RUNTIME_NOT_PINNED`。Blender/render/frame计数2/2/2，model/network/Docker为0，磁盘约297 GiB available。

C1只授权在fresh v0.2 root启动前设置exact `OCIO`绝对路径，并先验证config SHA `24ec8184…`；source/frame/resolution/32+64 samples/engine/device/format/timeout与上限均不变。新增四项in-process color assertions与zero color-warning门。下一动作提交推送v0.1完整失败证据、C1与本entry，随后才创建v0.2 root。

## J-380 · B61校准v0.2 startup warning反例与C2预注册

Date: 2026-08-29 · Type: RENDER CALIBRATION COUNTEREXAMPLE / AUDIT-PHASE CORRECTION · Real Blender processes: 1 · Rendered frames: 1

v0.1反例/C1 commit `fa705ff`推送后，v0.2 CAL32在exact OCIO environment下启动。四项target-scene assertions全部通过，3.50秒写出EXR；但stdout仍有5条color warning，触发预注册zero-warning gate，runner因此未启动CAL64。v0.2按协议判`INVALIDATED / PREREGISTERED_ZERO_COLOR_WARNING_GATE_FAILED`，不能把CAL32当作成功校准。

日志时序证明五条warning全部在目标`blend | Read blend`之前：它们把Blender默认startup scene的built-in sRGB/AgX/Standard迁移到自定义ACES config，而不是目标blend回退。v0.2固定为4 files / 1,382,142 bytes，tree hash `f3c2d8bc…`；failure file SHA/self-hash `b3cb19fd… / efe31eda…`。Operations为1 Blender、1 render、1 frame、zero model/network/Docker。

C2只授权把日志门改成phase-aware：必须验证exact OCIO与目标Read-blend事件；只容忍其之前的startup迁移warning，Read-blend之后任何color warning仍拒绝，并继续要求四项in-process assertions。Fresh v0.3 root当前不存在；所有渲染参数和资源上限不变。下一动作提交推送v0.2失败证据/C2，再运行v0.3两个case。

## J-381 · B61校准v0.3支持64-spp正式预算

Date: 2026-08-29 · Type: RENDER CALIBRATION RESULT · Real Blender processes: 2 · Rendered frames: 2

C2 commit `3258e43`推送后，fresh v0.3重跑CAL32/CAL64。两次均验证exact OCIO config SHA/name、display与view；每次有5条允许的startup-scene migration warning，全部在目标Read-blend之前，之后warning为0，保存事件发生在Read-blend之后。两个进程exit 0，生成1920×1080 OpenEXR v2 scanline ZIP文件。

CAL32/CAL64 wall time为3.54/5.02秒，EXR bytes为1,378,126/1,368,644，SHA为`cfc2aab2… / 8ab8313d…`；maximum resident set size观测约4.159/4.158 GB。Result file SHA/self-hash为`75ddbe2e083c7b571b3160cb1cfb1228bedb92b29388859fd714c15a00f25aab / afe8df5b5698ab2f20abc5971cc41ba08aff488d604f7c7f30e1671a396d09b0`。Operations为2 Blender、2 render、2 frames，zero model/network/Docker。

校准决策冻结为：B61正式矩阵使用64 spp、单次120秒timeout、100 GiB reserve。该结果只证明资源可承受，不证明像素复现、视觉一致或电影质量。下一动作提交推送v0.3证据，然后以64 spp预注册正式B61，而不是继续调整采样数。

## J-382 · B61三镜头EXR像素复现与成本门预注册

Date: 2026-08-29 · Type: B61 FORMAL PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

校准结果commit `0d4e966`推送后，正式B61-E1冻结为三镜头×frames 1/72/144×A/B独立重复：6 render Blender starts、18 render calls/EXR/PNG/pixel reports，另允许1次独立EXR reopen audit Blender。所有case固定1920×1080、Cycles CPU、64 spp、half-float ZIP multilayer EXR、denoise on、seed 24082960、animated seed false、frozen ACES config、单process 120秒与100 GiB reserve。

复现判据不是EXR container hash，而是每次保存后用Blender重开EXR，对decoded Combined RGBA float32 little-endian bytes求SHA；九组shot/frame A/B必须exact，独立audit重算也必须exact。PNG只用于后续review，不进入技术verdict。协议冻结16 gates、10 single-field attacks与1 GiB formal ceiling；任何pixel pair不同都fail，不设置事后容差。

WIDE/MEDIUM/CLOSE source blend SHA为`9019e6dc… / 61618765… / ce11abd1…`，分别绑定B60 production receipt self-hash与structure hash。五项candidate tools和三条official roots当前均不存在。即使B61通过也不支持全序列、跨硬件、时间连续、真人视觉身份或电影感。下一动作提交推送本预注册，再实现render/audit工具；正式root在tool freeze与zero-Blender preflight前不得创建。

## J-383 · B61 Blender-side render与EXR reopen算法候选

Date: 2026-08-29 · Type: B61 ALGORITHM IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

预注册commit `06dcbfb`推送后，实现两段Blender-side candidate。`render_b61_frames.py`对一个shot/repetition验证source blend、Blender build、frozen OCIO environment/custom props/display/view，固定64-spp render contract，依次渲染1/72/144；每帧写multilayer EXR，从磁盘重开后取得decoded Combined RGBA float32 LE digest与finite/channel/dynamic统计，再从同一Render Result保存PNG并写self-hashed pixel/run reports。它不以container hash冒充pixel digest。

`audit_b61_exr.py`在独立Blender进程中重开18个EXR，重算同一decoded projection并与18份self-hashed render report逐一匹配；不调用render。两文件SHA为`d13590ee27da8283c08d927efb86ded9fcf4ee12792ed50cbdb79e6176693bbd / f60fee8c357d951edcfdb7e1a0d82d8919c0d0a80314bcd10c86980ef8f86767`，静态Python syntax和diff check通过。尚未用正式B61 Blender验证multilayer EXR reopen API，不能据此宣称运行成功；三个official roots继续不存在。下一动作实现Node preflight/runner/auditor，再一起冻结并在fresh clone rehearsal。

## J-384 · B61完整tool-freeze候选

Date: 2026-08-29 · Type: B61 TOOL-FREEZE CANDIDATE · New Blender processes: 0 · New Blender renders: 0

完成三项Node candidate。Preflight要求pushed HEAD/origin exact，重开三份source blend/production receipts、OCIO、v0.3 calibration与v0.1/v0.2 retained failures，验证1 GiB projected output仍保留100 GiB reserve，全程zero Blender。Runner写attempt/admission/receipt后按WIDE/MEDIUM/CLOSE×A/B启动6个受120秒限制的Blender进程，每进程渲染3帧；之后只启动1个EXR reopen Blender和1个Node auditor，失败时写self-hashed invalidation并保留partial root。Node auditor直接重开18组EXR/PNG/pixel reports、6份run/process reports和Blender reopen audit，验证A/B decoded pixel exact、EXR/PNG headers、finite/dynamic pixels、成本、disk/bytes与10项mutations。

为避免空gate，render report新增实际half/ZIP/multilayer、denoise、OCIO字段；auditor新增对应exact检查、最终disk reserve与formal byte ceiling。最终render/audit-python/preflight/runner/auditor SHA为`e47198e9d5e0487d644128683dfdb29eedf2d462922e593878684f2ff9725dfc / f60fee8c357d951edcfdb7e1a0d82d8919c0d0a80314bcd10c86980ef8f86767 / 50eba33dbf48445055f7fa6290ae5328b769c57650932105bb9302a754dc6c0a / 84f0b60c140820dcdbced72964541c427f4d3ea4e0eb0acf42e3de88a8dcf317 / 8d66e353a54925bd4f83b3cc54c405b2c6ef162470bc5bf819adfd2985ee1a73`。Node syntax、targeted ESLint zero-warning、Python syntax与diff check通过；official roots仍不存在。下一动作提交推送tool freeze，fresh clone先跑zero-Blender preflight，再决定是否执行18帧rehearsal。

## J-385 · B61 fresh-clone rehearsal与official preflight接受

Date: 2026-08-29 · Type: B61 OFFICIAL PREFLIGHT ADMISSION · New Blender processes: 0 · New Blender renders: 0

Tool-freeze commit `0e68107`推送后，全新临时clone运行exact-root preflight，返回`ACCEPTED 9/9`、self-hash `c6efbeed…`；三份source/production bindings、v0.3 calibration、v0.1/v0.2 retained failures、五项工具、矩阵与资源上限全部通过，operations全零。临时clone随后以validated `/tmp/bfs-b61-preflight.*` target depth-first删除。

主仓库确认三根fresh后运行official preflight，同样`ACCEPTED 9/9`。File SHA/self-hash为`cb1f222d5a08eafb1253c52678bf64e7641ef6dafa7dd7824202e0ffee2519fe / 6b0bcf86af7a5ddc284186b015bc2bfb330a908566f84908760a3688b3ef5c52`；available 318,655,078,400 bytes，预留1 GiB formal后仍高于100 GiB reserve。Blender/render/frame/model/network/Docker均0，attempt/formal roots继续不存在。下一动作仅提交推送此receipt与本entry形成evidence commit；之后formal runner才可创建18帧矩阵。

## J-386 · B61 v0.1首帧后无终结receipt，C1 observability修正预注册

Date: 2026-08-29 · Type: B61 FORMAL COUNTEREXAMPLE / CORRECTION PREREGISTRATION · Real Blender processes: 1 · Rendered EXR frames: 1

Preflight evidence commit `476cd03`推送后，formal runner启动WIDE-A。进程在frozen OCIO phase gate下约5.07秒写出`frame-0001.exr`，SHA `679e199a…`，随后没有pixel/PNG/run report；其余5个render cases、EXR auditor和Node auditor均未启动。Runner写self-hashed invalidation，file SHA/self-hash `a46698b9… / 459cf821…`。

Invocation缺少`--python-exit-code 1`，且process receipt只保留stdout/stderr 1162/1388 bytes的SHA，没有正文。因而exit 0不能证明Python成功，日志缺口也使具体exception不可恢复；failure summary明确标记`rootCauseProven:false`，file SHA/self-hash `986e861d… / 905dc1ee…`。Attempt tree为4 files/3,102 bytes/`f6a21fb5…`，formal tree为4 files/1,348,155 bytes/`bf482918…`。

C1仅授权fresh v0.2加入Python exit-code、4 MiB bounded durable raw logs和8-stage fsync ledger；所有像素、质量、资源与claim门槛不变。v0.2三根当前不存在。下一动作提交推送C1与完整v0.1失败树，再修改工具；不得覆盖v0.1或直接猜测根因。

## J-387 · B61-C1 terminal observability工具候选

Date: 2026-08-29 · Type: B61 CORRECTION IMPLEMENTATION · New Blender processes: 0 · New Blender renders: 0

C1/evidence commit `67f5bcd`推送后，preflight/runner/auditor改绑fresh v0.2三根，并在创建新root前复核v0.1 attempt/formal tree与failure-summary exact。Runner现在把`--python-exit-code 1`加入render与EXR-audit Blender，先exclusive+fsync写stdout/stderr各最多4 MiB的raw logs，再写含full-stream/captured hashes与truncation状态的process JSON。Render script新增hash-chained、逐append fsync的`stage-events.jsonl`，每帧记录EXR write/reopen、pixel projection、PNG与report终结；Node auditor验证20-event exact chain、raw-log binding和`pythonExitCodeEnforced:true`。

C1 spec/protocol SHA为`57ed5959dd589b8086a5e7b994a0d2272e31eeed3ea4e103028267fecd3a4b11 / 00eb5670cbd306716ea61daf0bf92e4afd0d2706c57956423cb81a51cf01dfcf`。修正后render/audit-python/preflight/runner/auditor SHA为`ee5f149d18f1950b823b0479a137cd7f5523cddf0f687048d9b647282020bbe8 / f60fee8c357d951edcfdb7e1a0d82d8919c0d0a80314bcd10c86980ef8f86767 / 1fee6b79ef995f3a59f31dd230713bcd878f42ece59adeebd0710c956920a108 / d395d6aded438aab05045a332b87577a58a8532d00077e3c79b2cff75d6bcc4d / 1c1ee47e62f335aa7ad08175062b3fb8657e90d5af9df4ef1cc533873e0538b6`。Node/Python syntax、targeted ESLint zero-warning与diff check通过；v0.2 roots仍不存在。下一动作提交推送tool freeze并做fresh-clone zero-Blender preflight。

## J-388 · B61-C1 fresh-clone rehearsal与official v0.2 preflight接受

Date: 2026-08-29 · Type: B61 CORRECTED OFFICIAL PREFLIGHT ADMISSION · New Blender processes: 0 · New Blender renders: 0

Tool-freeze commit `d4ee68a48cb0d7382dfe8f5f9317619465d43406`与origin/main exact后，全新临时clone先运行C1 v0.2同构preflight rehearsal。结果`ACCEPTED 9/9`，self-hash `8e508f3613ca8a22f9d1e7a2028d3d671697f1b42d5b78fe3fac7889fe5afee5`；v0.1 attempt/formal tree、failure summary与C1 correction binding全部exact，operations为zero Blender/render/frame/model/network/Docker。临时clone随后仅对validated `/tmp/bfs-b61-c1-preflight.*` target执行depth-first delete，并删除其marker。

主仓库确认v0.2 preflight/attempt/formal三根均不存在后，以同一tool freeze签发official preflight，返回`ACCEPTED 9/9`。File SHA/self-hash为`8126d1ce93f8f8d2e772edd8ff9328b8dc1221a457b8f8afff072452212dd411 / d3f1d57ebe957754917e92ee6a474a1fa2eba33f16f783b177dfc2cf2e76f0b8`；available bytes为318,553,251,840，扣除1 GiB projected formal仍高于100 GiB reserve。记录再次确认C1只改变terminal observability，像素、质量、成本与资源阈值未改变；operations全零，attempt/formal roots继续不存在。

下一动作只提交推送official v0.2 preflight与本entry形成evidence commit。之后formal runner必须同时绑定tool-freeze `d4ee68a48cb0d7382dfe8f5f9317619465d43406`与该exact evidence commit，才允许创建v0.2 attempt/formal roots并启动真实Blender。

## J-389 · B61 v0.2证明multilayer EXR的bpy pixel路径失效，D1预注册

Date: 2026-08-29 · Type: B61 FORMAL COUNTEREXAMPLE / DIAGNOSTIC PREREGISTRATION · Real Blender processes: 1 · Rendered EXR frames: 1

Official preflight evidence commit `eb068607899af4b0bc197ba96dbe7d0d36b655fd`推送后，第一次runner invocation使用了不存在的手写full commit并在任何root创建或Blender启动前由Git拒绝；确认v0.2 attempt/formal仍fresh后，使用`git rev-parse`取得的exact commit才进入正式路径。

WIDE-A约5.02秒完成frame 1 EXR durable write，随后`pixel_projection()`在`bpy.data.images.load()`重开的multilayer image上观测到零个pixel values，抛出`ZeroDivisionError: float division by zero`。`--python-exit-code 1`把它正确转换为process exit 1；4 MiB bounded raw stdout/stderr完整保留且未截断，stage ledger终止于sequence 3 `EXR_WRITTEN`。其余5个render processes、EXR auditor与Node auditor均未启动。

Failure summary file SHA/self-hash为`2c32bef58fe631f63c64778c7f548bf66ad84aca3b61b10262de0ea1944eb27a / 54666b30f13b664ee4aa0e8efc9725da823c98d9de8938869366903f00e0af39`，明确`rootCauseProven:true`。Attempt tree为6 files/6,864 bytes/`46e5744c…`；加入failure summary后的formal tree为5 files/1,351,590 bytes/`440a8802…`；retained EXR SHA为`a094fcae…`。

由于修正decoder前仍需证明Blender 5.2内可用的磁盘EXR接口，D1只预注册一个30秒、1 Blender start、zero-render诊断：复现bpy空pixel路径，枚举Image RNA，并测试Blender随附OpenImageIO能否唯一解析Combined RGBA及两次float32-LE exact digest。D1不授权formal retry；只有PASS后才能另行预注册C2和fresh v0.3 roots。

## J-390 · B61-D1零渲染EXR decoder探针候选

Date: 2026-08-29 · Type: DIAGNOSTIC TOOL-FREEZE CANDIDATE · New Blender processes: 0 · New Blender renders: 0

D1预注册commit `9d5cc09`推送后，实现一个Blender-side probe和一个bounded Node supervisor。Probe首先使用bpy重开保留EXR并记录Image identity/RNA/pixel count，再导入Blender 5.2随附OpenImageIO与NumPy；它枚举所有subimages/channels，只接受唯一以`Combined`结尾的RGBA quartet，以float32读取并显式转换为little-endian contiguous RGBA bytes，独立重开解码两次。Supervisor在启动前重算v0.2两棵失败树、failure self-hash与EXR binding，限定一个带`--python-exit-code 1`的Blender process、30秒、zero render/model/network/Docker和1 MiB输出。

Probe/runner SHA-256为`25573038f7c163c689d7f198c187ca3e2752261e811ce90bb86448c12aba6fb8 / 0bf2c25e9d57035bae82df6007d1249c72599b10a587d963bd41fd4e80fbacc8`；spec/protocol SHA为`c7c3c71ea85512a77815d3bc85d9cd61b66818ba2bfb4cff8b90a1c1c09fe431 / e3f950f48c1a59e980b344caf297a3b3937ca6787b28ed00c975b65a7b835528`。Node syntax、targeted ESLint zero-warning、Python syntax与diff check通过，正式D1 output root仍不存在。下一动作提交推送形成tool freeze；在tool freeze与origin exact之前不得创建`experiments/b61-exr-reopen-diagnostic-v0-1`或启动诊断Blender。

## J-391 · B61-D1参数入口反例与D2最小修正预注册

Date: 2026-08-29 · Type: DIAGNOSTIC COUNTEREXAMPLE / CORRECTION PREREGISTRATION · Real Blender processes: 1 · New Blender renders: 0

D1 tool-freeze commit `e4300113eba493ac9c03f45dfa4fb2642b487ac9`推送后，一个Blender background process在0.4546秒以exit 2终止。Raw stderr证明argparse报告`--repository-root / --spec / --output`全部missing；probe在EXR binding与OpenImageIO import前终止。原因是脚本直接调用`parse_args()`解析Blender完整argv，没有显式截取最后一个`--`后的参数。这不反驳OpenImageIO候选，但D1已消耗其唯一Blender start，因此结果必须INVALIDATED且原root不得复用。

D1 failure file SHA/self-hash为`e9c555c213a7b252f515373ea82bddaea897da78631414230898085931779a5d / 13eaa2c5728de8b94d632236d210e28128e27203fdece1e8487b523ec3bb0dba`；完整root为4 files/2,844 bytes/`bcbd13ae…`，operations为1 Blender、zero render/model/network/Docker。D2只授权argv-after-double-dash切片、绑定该失败树并使用fresh v0.2 root；输入、decoder、接受条件和资源上限不变。下一动作先提交推送失败证据与D2，再修改工具。

## J-392 · B61-D2 argv correction工具候选

Date: 2026-08-29 · Type: DIAGNOSTIC CORRECTION TOOL-FREEZE CANDIDATE · New Blender processes: 0 · New Blender renders: 0

D2 preregistration commit `172735c`推送后，probe唯一算法变化是要求`sys.argv`中存在`--`并把其后的slice交给argparse。Supervisor改绑fresh v0.2 output root，把D2 correction/protocol加入tool freeze，并在启动前额外重算D1 retained tree与failure self-hash。EXR decoder、channel选择、projection、接受条件和资源上限均未修改。

Probe/runner SHA-256为`aa0cc85b95ffb9afa5ed731d19b7edc7628c5e95f5997758d67bd0bd27736749 / 21e968c799fcbd3473e67f7ac5aee94bf9f5cb9049ec398384245afc4fd691d2`；D2 spec/protocol SHA为`fc97b4da288f5bcf1dcd4d154ee7d8a934913faa356de81fa4bef6a743a08982 / 2f4a7da7694b93c96014ba0fc45bca2fe6b97a42bde508d1ff71354b810007be`。Node/Python syntax、targeted ESLint zero-warning与diff check通过，v0.2 output root仍不存在。下一动作提交推送形成tool freeze；只有tool-freeze与origin exact后才允许第二个诊断Blender start。

## J-393 · B61-D2真实decoder成功但跨运行时self-hash未准入，D3预注册

Date: 2026-08-29 · Type: DECODER RESULT / ENVELOPE COUNTEREXAMPLE / RECONCILIATION PREREGISTRATION · Real Blender processes: 1 · New Blender renders: 0

D2 tool-freeze commit `10f8dc0efc6a52fb19551ad392ca7180d2e8ffcf`推送后，Blender process exit 0。它复现bpy image size/channels/depth/pixel count均为0，并由Blender随附OpenImageIO 3.1.13.1枚举8个EXR subimages；唯一Combined quartet是`BFS_MASTER.Combined.R/G/B/A`。两次独立open均得到1920×1080×4、8,294,400个finite float32-LE values，digest exact为`192237bde2f628e9f554b7bbb480090d2139e3bcf04a198772ecf564c4c1409a`。

Probe result内部status PASS、Python canonical self-hash `5d502545…`；Node supervisor重算为`e0c9c275…`并拒绝写receipt。独立静态重算证明，Python原hash与stored exact；只把finite integral floats（如alpha统计中的`1.0`）规范为integer后，Python hash exact变为Node hash。因此D2整体标记INVALIDATED，不能直接当作accepted diagnostic，但decoder observations完整保留。D2 failure file SHA/self-hash为`7e1cf6761dfccb134d81bec4b3f1007d2daab3fe367e239137a01ea769ec024f / b0e4adf8c3acc90c0dd110f2f33080fa548ecc3e36f82a9e2db982c2ccc4751f`，root为5 files/10,386 bytes/`4e89e722…`。

D3预注册为zero-Blender reconciliation：绑定immutable D2 tree，用Blender bundled standalone Python重算原self-hash，Node重现mismatch并证明仅integral-float normalization即可收敛，同时独立验证process/log/result所有语义门。D3不重解码、不改threshold，也不授权formal retry。

## J-394 · B61-D3 zero-Blender reconciliation工具候选

Date: 2026-08-29 · Type: RECONCILIATION TOOL-FREEZE CANDIDATE · New Blender processes: 0 · New Blender renders: 0

D3 preregistration commit `9d7df10`推送后，实现单一Node supervisor。它在任何输出前验证tool freeze、D2 tree/failure/result/process/raw logs；重现Node canonical mismatch；只启动一次Blender-bundled standalone Python 3.13重算原Python hash与finite-integral-float normalized hash；最后直接检查bpy empty-pixel、唯一Combined quartet、projection shape/finite/repeat digest和zero-render operations。它不导入bpy、不启动Blender、不重解码EXR。

Runner SHA-256为`20fc21328d97f41bf25e6aae6d0dac4a148fd6e89ddf65f96f3cc2a82433c2a1`；D3 spec/protocol SHA为`a6d63ed6984ba1c07574a3daafc4e29e8c8066743d56075868d8df1766ab5c82 / e28ea39d6313e0edf231fd34cce1d778c8858961bf2692817e26f64876643f90`。Node syntax、targeted ESLint zero-warning与diff check通过，D3 output root仍不存在。下一动作提交推送freeze；随后才允许创建fresh D3 output root并执行zero-Blender reconciliation。

## J-395 · B61-D3关闭decoder诊断门并预注册C2 formal修正

Date: 2026-08-29 · Type: DIAGNOSTIC PASS / FORMAL CORRECTION PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

D3 tool-freeze commit `567e70c5a4fecbe100ed7ee2bc091f011433498c`推送后，zero-Blender reconciliation PASS。Bundled Python原canonical hash exact为`5d502545…`；finite-integral-float normalized hash exact等于Node的`e0c9c275…`。所有retained process/log/result语义门通过，支持verdict `BLENDER_BUNDLED_OPENIMAGEIO_COMBINED_RGBA_DECODER_SUPPORTED`。Result file SHA/self-hash为`ff7be927163fc1774888df3349c42d13a4e2c7b4eecbad4e2f1b6fbc3fb922b1 / 7d83021daf035c0daa854c874da3aee50f8f20ab8cf1a4683ecfb64d120e2bb7`；receipt file SHA/self-hash为`ebf220f832e22a45b6fda098ec84d71b805e55bf2fbc21ae7e119d73c37b0315 / 802a0553aa34e642131cd46ed265c653b703541a796776b829b078ea14988fc4`。Operations为0 Blender/render/model/network/Docker、1 bundled-Python，0.0188秒。

C2据此只授权：两段Blender Python改用exact bundled OIIO 3.1.13.1/NumPy 2.3.4 decoder；Python canonical hash规范finite integral float；三段Node supervision绑定C2/D2/D3与fresh v0.3 roots。multilayer half/ZIP、像素exact、18 render、16 gates/10 attacks及全部资源门不变。下一动作提交推送D3 evidence/C2，再实现工具。

## J-396 · B61-C2 formal工具候选

Date: 2026-08-29 · Type: FORMAL CORRECTION TOOL-FREEZE CANDIDATE · New Blender processes: 0 · New Blender renders: 0

C2 preregistration commit `a8ef00e`推送后，render与independent audit两段Python均实现D2已证明的exact decoder：要求OIIO 3.1.13.1/NumPy 2.3.4，枚举subimages，只接受唯一`.Combined` RGBA quartet，float32读取并转为C-contiguous little-endian RGBA bytes。两段canonical hash统一在序列化前仅规范finite integral float。Pixel report现在记录decoder module/version/subimage/prefix/channel names/indices，独立auditor逐帧回传并与render report exact绑定。

三段Node supervision改用fresh v0.3 roots，tool freeze加入C2 protocol与D3 evidence；preflight重算v0.2 retained trees/failure、D2真实decoder result和D3 result/receipt；Node auditor新增每帧decoder runtime/channel gate。所有渲染、像素、资源及16 gates/10 attacks不变。

Render/audit-python/preflight/runner/auditor SHA-256为`b3aa8d4d20a5efb2eaac454c20c6b36bcd50f1016af94ddf411bbaaeac34527b / f3e998f9418917bf198424984630f9ad666ab439270a5d363b4e98f6ead54339 / d01ec7721e968d348f4d65c013ff184283c8af6c1cc24a8dc4b3b4196682cc49 / a213d7714771e957e4ac64a9f2dd05f49f58d98f7cbb64dbc80e4b93f55b3787 / 38d0a901853d4af1380809207705c93ee6dfef91ae1f116c859386340951d8c2`。Node/Python syntax、targeted ESLint zero-warning与diff check通过；v0.3 roots仍不存在。下一动作提交推送tool freeze，再做fresh-clone zero-Blender preflight rehearsal。

## J-397 · B61-C2 fresh-clone rehearsal与official v0.3 preflight接受

Date: 2026-08-29 · Type: CORRECTED OFFICIAL PREFLIGHT ADMISSION · New Blender processes: 0 · New Blender renders: 0

Tool-freeze `5e1ad6c5203338daed07d08f54868a26a5df4d84`与origin exact后，全新临时clone第一次因未安装AJV在模块加载期退出，尚未执行preflight或创建证据；保留同一干净clone，仅把主仓库已安装`node_modules`以临时symlink提供给Node，随后同构preflight返回`ACCEPTED 9/9`、self-hash `a38f11bed091e180dade81f4bdac6f6fb5957e1dae52f1dc4b83efc651a55f31`。该symlink与整个validated `/tmp/bfs-b61-c2-preflight.*`临时树随后depth-first删除。

主仓库确认v0.3三根fresh后签发official preflight，同样`ACCEPTED 9/9`。File SHA/self-hash为`1d802cb1887a5f906847169436ae4100ab1ceb1f8e5a05ca3a196a5f58d75865 / c942b0d596a1eaa6923ce9cb9331fe4a8b87e76c43972561c7633a5f9475ecb8`；C2 failure trees、D2 projection `192237bd…`与D3 receipt `802a0553…`全部exact。Available bytes为318,452,441,088，扣除1 GiB projected后仍高于100 GiB reserve；operations全零，attempt/formal roots继续不存在。

下一动作只提交推送official v0.3 preflight与本entry形成evidence commit；之后runner必须绑定tool freeze与该exact evidence commit才可启动18帧正式矩阵。

## J-398 · B61 v0.3穿过C2 decoder后在PNG review context失效，D4预注册

Date: 2026-08-29 · Type: FORMAL COUNTEREXAMPLE / DIAGNOSTIC PREREGISTRATION · Real Blender processes: 1 · Rendered EXR frames: 1

Preflight evidence commit `2992f2f1c59d6d95343383e565e0ccdb54df2a1b`推送后，WIDE-A完成首帧EXR write、OpenImageIO reopen与pixel projection。Stage ledger终止于sequence 5 `PIXEL_PROJECTED`，decoded digest exact为D2已证明的`192237bde2f628e9f554b7bbb480090d2139e3bcf04a198772ecf564c4c1409a`、nonfinite 0；这直接证明C2正式decoder路径已经工作。EXR container SHA为新的`36908a04…`，再次说明container bytes不是pixel identity。

随后active production scene把`image_settings.file_format`从`OPEN_EXR_MULTILAYER`赋为`PNG`时，Blender 5.2只报告允许枚举`('OPEN_EXR_MULTILAYER')`并抛TypeError。Process exit 1，其他5个render processes与两级auditor未启动。Failure summary file SHA/self-hash为`51f5797d1049e041b9aa511e9f2180a110a22b9cfab00e2e7eb218843b5ac722 / 67c65a3f9137538b1f06f450082db94071f97b349457375bce807cd6e9bae346`；attempt/formal trees为6 files/7,141 bytes/`e6812631…`与5 files/1,352,271 bytes/`76f7d849…`。

D4只预注册一个zero-render Blender probe：复现active scene枚举锁，测试isolated review scene能否设置PNG并用generated 2×2 image写出有效PNG，同时要求production settings不变。PNG仍只用于review，技术像素门和所有render设置不变。

## J-399 · B61-D4 PNG context探针候选

Date: 2026-08-29 · Type: DIAGNOSTIC TOOL-FREEZE CANDIDATE · New Blender processes: 0 · New Blender renders: 0

D4 preregistration commit `85e74ee`推送后，实现一个Blender probe与bounded supervisor。Probe在production blend内snapshot active render/image/color settings，尝试并记录multilayer-to-PNG assignment；随后创建isolated review scene与2×2 generated float image，以`Image.save_render(..., scene=review)`写PNG，验证header/dimensions，删除临时数据并要求production snapshot exact。Supervisor在一个Blender start前重算v0.3两棵失败树与failure self-hash，限定zero render/model/network/Docker、30秒与1 MiB。

Probe/runner SHA-256为`07d8451ddacd604dd4a7f5daf620351538d19c03f6ecc6bbd7ab692aaf99ef47 / 4a47185132a6a59bab0e500ec73e5915df51a3aab8607d1421e28d4cf9854d4e`；spec/protocol SHA为`41a9e96c011bd234b02349db34e9e45ae21e4d8e51edae4a7dda274c886aad9f / 0dbe73d063e7bfdee1c214880fad1b11a415c7cdf00bea7ed1cfac594c131c33`。Node/Python syntax、targeted ESLint zero-warning与diff check通过，D4 root仍不存在。下一动作提交推送tool freeze；只有origin exact后才执行D4。

## J-400 · B61-D4关闭PNG context诊断并预注册C3

Date: 2026-08-29 · Type: DIAGNOSTIC PASS / FORMAL CORRECTION PREREGISTRATION · Real Blender processes: 1 · New Blender renders: 0

D4 tool-freeze commit `8a685b2`推送后，one Blender/zero-render probe PASS。Active production scene从multilayer改PNG的assignment failure exact复现；isolated review scene接受PNG/RGBA/8-bit并写出265-byte、2×2有效PNG，生产scene before/after snapshot exact。Result file SHA/self-hash为`ba05262f3b7937ea0e3d2fcab50534b5de4f767184310e2ad7e345c6e02e5271 / 7186f6f1b32dab34e0f52114fa2c6f3d7b9ff0815567e18a7b78f5f330c4f468`；receipt file SHA/self-hash为`bff263a9455b9c03947e4196fc5793e6880bd703326eab226dd12bf891a3e5a1 / 8d72ea94d7cc43d836fa2edf8217d8511ef3ba7b3a18d82671517e279280d505`。

C3只授权render process创建isolated review scene，复制color settings并传给`Render Result.save_render`，finally删除；生产image settings不再改动。Node supervision绑定D4/v0.3 failure并使用fresh v0.4 roots。下一动作提交D4 evidence/C3，再实现工具。

## J-401 · B61-C3 formal工具候选

Date: 2026-08-29 · Type: FORMAL CORRECTION TOOL-FREEZE CANDIDATE · New Blender processes: 0 · New Blender renders: 0

C3 preregistration commit `0b69ca8`推送后，render script在生产scene完成multilayer/half/ZIP配置后snapshot三项image settings，创建process-local isolated review scene，复制display/view/look/exposure/gamma并配置PNG/RGBA/8-bit。每帧PNG只通过`Render Result.save_render(..., scene=review_scene)`输出；pixel report要求production settings exact未变并记录`ISOLATED_REVIEW_SCENE`；成功run report后删除review scene。EXR render和OIIO decoder未改。

Preflight/runner/auditor切到fresh v0.4 roots，freeze同时覆盖C2/C3、D3与D4 evidence；preflight复核v0.3 failure trees及D4 result/receipt；auditor逐帧要求review context与production settings unchanged。Render/audit-python/preflight/runner/auditor SHA为`ddc94499cfe9c36db4eeb868679a0f7d9d0b4c7c0e4a2d16182b1aa8221ecfee / f3e998f9418917bf198424984630f9ad666ab439270a5d363b4e98f6ead54339 / 438b6e7ca7408d60e22221b59392343d03522f80d435053cd7bab40ae741b42a / d28dbee4d4fe56794b170ab1763d7bd6c6e1df0d708b3a47db6de380bd0293a0 / 2f8b6624e5b642d635b3853418518cbb4a68021db4de2abe693e7695633685df`。静态检查全过，v0.4 roots不存在。下一动作提交推送freeze并做fresh-clone preflight rehearsal。

## J-402 · B61-C3 fresh-clone与official v0.4 preflight接受

Date: 2026-08-29 · Type: CORRECTED OFFICIAL PREFLIGHT ADMISSION · New Blender processes: 0 · New Blender renders: 0

Tool-freeze `9a84cfdcdbca17ce88ef87e85ce00f0c5cd6e3d4`推送后，fresh clone通过临时只读node_modules symlink运行同构preflight，返回`ACCEPTED 9/9`、self-hash `cf8e1142f1c24aa798f2ad51a914df3dd563c287973fd95b66ccd4ff788dd6e9`；临时clone/symlink随后validated depth-first删除。

主仓库确认v0.4三根fresh后official preflight同样9/9。File SHA/self-hash为`f249524f87f350436e424b635c3d3ff9a2342e466b77fd2d605ef46ac80ae8c2 / c0b9b39fdd96c813ba3b675cf60171737f77f775844b1fef98e3e8877258cbaa`；v0.3 failure trees与D4 result/receipt exact。Available bytes 318,404,898,816，operations全零；attempt/formal继续不存在。下一动作提交推送preflight evidence，然后运行v0.4正式矩阵。

## J-403 · B61 v0.4证明headless Render Result无data，D5预注册

Date: 2026-08-29 · Type: FORMAL COUNTEREXAMPLE / DIAGNOSTIC PREREGISTRATION · Real Blender processes: 1 · Rendered EXR frames: 1

v0.4首帧再次完成EXR/OIIO projection，digest仍为`192237bd…`，stage停在sequence 5。Isolated review scene已创建并接受PNG，但`Render Result.save_render`抛出`Image Render Result does not have any image data`；这证明C3只解决了format context，headless buffer ownership仍未解决。其余5个render processes与auditors未启动。

Failure summary file SHA/self-hash为`8b83f86d357b9e42adefd05921cd680415e8f780d46c67c86319ac8ccfdd8f20 / 959d9dbda9393f1b90293a9cc011d793b8edfd113821ba278e03f3b1b92895ff`；attempt/formal trees为6 files/7,785 bytes/`55a11af4…`与5 files/1,351,670 bytes/`75d459d5…`。

D5预注册为one-Blender/zero-render 1080p probe：从保留EXR得到exact OIIO RGBA array，创建temporary Blender float image，再经isolated review scene输出PNG并清理。该路径复用已证明的两半，但必须在正式C4前验证完整1920×1080数据量。

## J-404 · B61-D5 1080p generated review探针候选

Date: 2026-08-29 · Type: DIAGNOSTIC TOOL-FREEZE CANDIDATE · New Blender processes: 0 · New Blender renders: 0

D5 preregistration commit `b2db213`推送后，实现one-Blender supervisor与probe。Probe绑定v0.4 retained EXR，复用唯一Combined/OIIO 3.1.13.1 decoder并要求`192237bd…`；基于OCIO `scene_linear: ACEScg`把array标记为ACEScg，做`OIIO Y0 top → Blender pixel0 bottom` row conversion，填充1920×1080 float image，再经isolated review scene的完整display/view/look/exposure/gamma输出PNG。生成image/scene在finally删除，production snapshot必须exact。

Supervisor在启动前复核v0.4两棵失败树/failure/EXR，设置frozen OCIO，限定one Blender、zero render/model/network/Docker、60秒与16 MiB。Probe/runner SHA-256为`01ed911880fb207fb2524dfca48d742208f543d37305791d693f796487a933c4 / 3adbb0a5b08c18243c147f63d788bf45d46ca85a5344ccaaa4cfa5e5499e66cd`；spec/protocol SHA为`753b0fe4f013c05f0f28063f97c61b0f8cc5b1b3ff0783ff1b62674ce8814c8b / 6d6dad0111217c50cc89558c59ccb7bbff9a9dd6af20d77097c55bfadd5cc4e4`。Node/Python syntax、targeted ESLint zero-warning与diff check通过；D5 root仍不存在。下一动作提交推送freeze后执行真实Blender D5。

## J-405 · B61-D5关闭1080p review-image门并预注册C4

Date: 2026-08-29 · Type: DIAGNOSTIC PASS / FORMAL CORRECTION PREREGISTRATION · Real Blender processes: 1 · New Blender renders: 0

D5 tool-freeze commit `e36969a`推送后，真实Blender probe PASS。OIIO Combined digest exact保持`192237bd…`；8,294,400 float values填入1920×1080 Blender image，source colorspace ACEScg、row order显式转换，经isolated ACES 2.0 review scene写出118,627-byte PNG。生产scene settings exact不变，operations为one Blender/zero render/model/network/Docker。人工原分辨率检查显示主体方向正确、色彩与照明可读。

Result file SHA/self-hash为`5445aaf64032b2162f84c8334134132393c0acce431034222bc3f122796d6cf4 / d26a8f21814572864ac847a2513832d5a195f893d1bed7399ccf00a19e510276`；receipt file SHA/self-hash为`7939f525d0869f445396770174c251dc00b224ac2ffc86ce3169e376426419d7 / 1954de1cd54c7021c07b94b19c93bfd346c3dda17fd0c896003fa44c72c757ed`；PNG SHA为`91585292…`。

C4只授权从同一次OIIO projection返回RGBA array并生成review float image；禁止Render Result与二次EXR decode。Node supervision绑定D5/v0.4 failure并使用fresh v0.5 roots。下一动作提交D5 evidence/C4，再实现正式工具。

## J-406 · B61-C4 formal工具候选

Date: 2026-08-29 · Type: FORMAL CORRECTION TOOL-FREEZE CANDIDATE · New Blender processes: 0 · New Blender renders: 0

C4 preregistration commit `e603864`推送后，render-side OIIO函数在计算原有projection receipt的同时返回同一RGBA ndarray。每帧review image只使用该array：flip Y rows、float32 contiguous、ACEScg、generated Blender float image、C3 isolated review scene；写PNG后在finally删除image。Report exact记录pixel source、colorspace、row order与source digest。不存在Render Result读取或EXR二次decode。

Node supervision切换fresh v0.5 roots，freeze覆盖C2/C3/C4与D3/D4/D5 evidence；preflight复核v0.4 failure trees和D5 result/receipt；auditor逐帧绑定generated review source与decoded digest。Render/audit-python/preflight/runner/auditor SHA为`917d8a5dc0a57e2ff7df318fde0288b80906c003ba186267d0bbc7bad1ee491a / f3e998f9418917bf198424984630f9ad666ab439270a5d363b4e98f6ead54339 / 028f287f82ccf1753eed9190c5afba96efcdb6e2c8d59c08addbf40d1a283c30 / ec50d5ff4a0e959dbba0bbca7618923b11c47c8f4ed188f8d01c7cf1668890b7 / 13224333127d420a4f888063507c094c8dfc27d472c67d27a7e7474904505e8d`。静态检查通过，v0.5 roots不存在。下一动作提交推送freeze并运行fresh-clone preflight。

## J-407 · B61-C4 fresh-clone与official v0.5 preflight接受

Date: 2026-08-29 · Type: CORRECTED OFFICIAL PREFLIGHT ADMISSION · New Blender processes: 0 · New Blender renders: 0

Tool-freeze `004b7a727c3b12de4228b7f4d175ce22d3484dfa`推送后，fresh clone通过临时只读node_modules symlink运行同构preflight，返回9/9、self-hash `82412dd14ca751efd842f2f1e0574ee045f5b798d7b8102b7656cd13f6cb0cb3`；临时树与symlink随后validated depth-first删除。

主仓库v0.5 official preflight返回`ACCEPTED 9/9`。File SHA/self-hash为`50caa1eeee24806f6e9e57a076bbe35810cc2cb529c71f00c0a2c47d074c0ff6 / 034e71f80c0d3ae52d62fe08985e9166f3b4a733f026ca6b80c1a7a9620fd584`；v0.4 trees/failure与D5 result/receipt exact，available bytes 318,406,385,664，operations全零，attempt/formal roots继续fresh。下一动作提交preflight evidence后启动v0.5 18-frame matrix。

## J-408 · B61 v0.5正式关闭同机像素复现与成本门

Date: 2026-08-29 · Type: FORMAL PASS / REAL BLENDER RENDER MATRIX · Real Blender processes: 7 · Render calls: 18

Preflight evidence commit `0b2cb76`推送后，formal runner绑定C4 tool-freeze `004b7a727c3b12de4228b7f4d175ce22d3484dfa`并完成WIDE/MEDIUM/CLOSE × frames 1/72/144 × A/B矩阵。6个独立render Blender processes全部exit 0并留下terminal `BFS_B61_RENDER_OK`，共18次1920×1080 Cycles CPU 64-spp render；第7个Blender独立重开18份multilayer EXR，不调用render。16/16 frozen gates、10/10 negative controls全部通过，zero model/network/Docker，formal verdict为`CINEMATIC_RENDER_TECHNICAL_REPRODUCIBILITY_AND_COST_SUPPORTED`。

九组A/B decoded Combined RGBA float32-LE digest全部exact；PNG container hash也逐对exact，但EXR container hash九组均不相等，因此正式identity surface明确是decoded pixel，而不是容器字节。18份pixel reports的self-hash均有效，独立EXR reopen与render report exact匹配；所有目标blend read后的颜色警告为0。Formal audit/results/receipt file SHA分别为`7bef5611… / 1477cc00… / 9ab3b2cf…`，self-hash分别为`ad8b6c10… / b3730720… / 18bc3a53…`；EXR auditor file/self-hash为`9af1fb4b… / 95535d55…`。Attempt tree为27 files/30,131 bytes/`4ee442ff…`；formal tree为71 files/96,621,748 bytes/`21ddfcfb…`。

18帧render operator总计109.506秒、均值6.084秒；6个process wall总计121.366秒，实测峰值RSS约4.50–4.54 GB。EXR合计91,620,900 bytes，PNG合计4,864,796 bytes。按当前still-frame样本机械外推为146.008 wall seconds/finished second，或约8,760.494秒（2.433小时）/finished minute at 24 fps；该值不包含全序列时间连续性、启动摊销变化或影院级资产成本。

人工检查九张A-run review PNG接触表：方向正确、颜色/照明可读、WIDE→MEDIUM→CLOSE景别明确、三帧运动状态不同，无空白或翻转。但资产刻意为低多边形测试几何，因此本PASS只关闭同机同build技术像素复现与成本门，不支持电影感、真人身份、跨硬件、全144帧连续性、完整成片成本或影院显示校准。v0.1–v0.4的四轮失败、raw logs、stage ledger和修正预注册全部保留。下一动作是提交推送formal evidence与结果说明、公开结果页，然后预注册真实英雄角色三镜头的电影质量与一致性门。

## J-409 · B61证据与图文结果双站发布完成

Date: 2026-08-29 · Type: EVIDENCE PUBLICATION / DEPLOYMENT RECOVERY · New Blender processes: 0 · New Blender renders: 0

B61 attempt/formal trees、J-408与结果说明以commit `a92c88c`推送；图文页与九张真实A-run review PNG以`04c4387`推送。页面主视觉明确写出“像素复现了，电影感还没有”，展示WIDE/MEDIUM/CLOSE × frames 1/72/144、9/9 decoded-pixel identity、0/9 EXR-container identity、六进程时间/RSS、成本外推、四轮失败与声明边界。vinext生产构建通过。

Sites owner-only production version 85发布成功。GitHub Pages第一次因sparse checkout没有包含新页面引用的B61 audit/receipt而在module resolution处失败；没有部署错误页面。只把两份小型JSON加入既有稀疏清单后，本机exact `GITHUB_PAGES=true next build`生成93/93 static pages，修正commit `ca120c7`推送，GitHub build/deploy均成功。公开B61 route非浏览器HTTP检查返回200、44,316 bytes，并找到`B61-E1 / 9/9 / 像素复现了`标记。遵守browser crash guard，未打开或自动操作新的内置浏览器tab。

## J-410 · B62终局样片goal freeze

Date: 2026-08-29 · Type: TERMINAL GOAL FREEZE · New Blender processes: 0 · New Blender renders: 0

下一目标冻结为12秒/24 fps/288帧原创短场景《守夜人点亮观测核心》：机械守夜人在废弃轨道观测站接近控制台、完成右手接触并点亮核心，最后在面罩上形成反射。三镜头固定为35 mm WIDE_APPROACH、65 mm MEDIUM_CONTACT、100 mm CLOSE_REFLECTION，各96帧。选择机械角色是显式边界：先完成可审计的stylized-realism角色/环境/接触/灯光/摄影/动画管线，不冒充已解决真人皮肤、毛发与微表演。

终局验收要求clean root单入口、SceneSpec→immutable BuildPlan→Blender、共享asset/look/state hashes、multilayer EXR与12秒交付视频；首镜完成后受控终止orchestrator与Codex工作回合，必须从verified receipts恢复且不重做已完成stage。所有输出、进程、资源和失败均可独立审计，0 generative-video pixel calls。自动门不能宣布电影感；必须留下匿名人类审片response。该goal freeze不授权288帧formal render；下一动作是有界Phase 0资产manifest、animatic、接触/灯光状态机和真实Cycles校准，再单独预注册正式B62。

## J-411 · B62 Phase 0资产、Animatic与Cycles校准预注册

Date: 2026-08-29 · Type: TERMINAL PROOF PHASE-0 PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

B58 C7、B60、B61 receipt file/self-hash重新核验exact为`f6112e89…/eef5dbff…`、`12937d85…/312060d8…`、`9ab3b2cf…/18bc3a53…`。宿主约296 GiB可用，capacity sentinel最近exit 0，无活动render/orchestrator Blender；六个B62工具和preflight/attempt/formal三棵root全部absent。

B62-P0-E1冻结12秒/288帧三镜头资产与look admission：one generator Blender生成原创机械守夜人、观测站、控制台核心、三段动作与master blend；one Eevee process输出288帧640×360 animatic；three fresh Cycles processes以固定64 spp/1080p渲染frames 48/144/240；one independent Blender zero-render reopen audit。上限6 Blender starts/291 renders/one ffmpeg/one Node auditor/2 GiB projected writes/100 GiB reserve，zero model/network/Docker。

机器判决要求18/18 gates、16/16 mutation controls，特别检查完整rig/material/asset identity、三镜头frame/lens、frame144右手接触≤2 cm、核心cold→warm因果顺序、close镜warm状态不重置、288帧/24fps/12秒视频、三份multilayer EXR、独立重开与资源收据。即使PASS也只得到`B62_PHASE0_ASSET_ANIMATIC_AND_CALIBRATION_ADMITTED`；不授权288帧正式Cycles，不宣布电影感或真人质量。下一动作提交推送预注册，随后才允许实现六个工具。

## J-412 · B62 Phase 0 C1 ffprobe进程记账更正

Date: 2026-08-29

实现独立auditor时发现父协议明确要求ffprobe验证animatic为24 fps/288 frames/12秒，但父process budget只列one ffmpeg encoder与one Node auditor，漏记只读metadata probe。此时六个工具尚未tool-freeze，preflight/attempt/formal roots仍absent，也没有启动B62 Blender或产生正式输出。

C1在执行前显式增加且只增加one ffprobe zero-output read-only process；six Blender starts、291 renders、one ffmpeg encoding、one Node auditor、2 GiB writes、100 GiB reserve、18 gates/16 attacks以及zero model/network/Docker均不变。preflight、runner与auditor必须同时绑定父合同和C1，不得把探针隐藏在Node进程统计中。

## J-413 · B62 Phase 0六工具实现与静态审查

Date: 2026-08-29 · Type: TOOL IMPLEMENTATION BEFORE FREEZE · New B62 Blender processes: 0 · New B62 renders: 0

完成六个预注册工具：procedural asset/master generator、Eevee animatic与Cycles calibration renderer、独立Blender re-open auditor、zero-Blender preflight、bounded runner、独立Node auditor。runner使用先attempt/admission/receipt、后formal-root的durable授权顺序；每个logical child都有独立stdout/stderr hash、wall/user/system/peak-RSS、timeout、combined-log ceiling与process-group TERM→KILL控制。输出预算同时覆盖attempt与formal，ffmpeg和C1新增的只读ffprobe分别记账。

静态审查发现并在tool freeze前修正三类会造成伪PASS的风险：Eevee final render必须写`taa_render_samples=16`而不是只写viewport samples；frame 143新增zero activation key，使frame 144 contact与transition同帧发生而非Bezier预亮；asset identity必须在master-only IK/socket constraint加入前冻结。生成报告现在含mesh topology、material node parameter、rig rest pose与motion action-key digests；独立Blender不导入生成/渲染工具，重新append三份asset library与motion action、重算digests、检查摄影机action ranges、contact/state、288 PNG及三份EXR decoded Combined pixels。

Node auditor将18个machine gates逐一映射到实际观测，并对冻结的16个negative controls逐个复制观测后注入mutation，只有全部被拒绝才允许写audit。最终receipt仍由runner在audit之后生成并立即重算self-hash，避免audit↔receipt循环依赖。三份Python通过`py_compile`，三份Node通过`node --check`与ESLint，`git diff --check` clean；正式preflight/attempt/formal roots仍不存在。下一动作是提交推送tool-freeze，再做fresh-clone zero-Blender rehearsal。

## J-414 · B62 Phase 0 fresh-clone rehearsal失败与C2预注册

Date: 2026-08-29 · Type: RETAINED REHEARSAL FAILURE / CORRECTION PREREGISTRATION · New B62 Blender processes: 0 · New B62 renders: 0

tool freeze `37d9524…`推送后，从本机仓库创建fresh clone `/tmp/b62-rehearsal-37d9524`。zero-Blender preflight在模块加载时因`ERR_MODULE_NOT_FOUND: ajv`退出；clone与official preflight roots均absent，attempt/formal absent，没有Blender、render、model、network或Docker操作。根因为三个B62 Node入口只为读取`repositoryRoot`却导入通用SceneSpec模块，后者顶层依赖Ajv；主工作树已有node_modules掩盖了缺陷。

C2在retry前只授权三个Node入口用Node built-ins从`import.meta.url`推导repository root，并把C2加入tool hashes/ancestry。明确禁止给clone安装或symlink node_modules，也禁止改变任何资产、镜头、render dose、timeout、预算、gate、attack或verdict。修正后必须新的tool freeze与新的fresh clone；失败clone不作为official evidence。

## J-415 · B62 Phase 0 C2 fresh-clone rehearsal PASS

Date: 2026-08-29 · Type: ZERO-BLENDER REHEARSAL · New B62 Blender processes: 0 · New B62 renders: 0

C2实现只修改三个Node入口：移除SceneSpec/Ajv传递依赖，以Node built-ins执行canonical hash、durable JSON与repository-contained path checks；tool freeze `21d49742…`推送且HEAD/origin exact。另建fresh local clone `/tmp/b62-rehearsal-21d4974`，没有安装或symlink node_modules。

clean clone preflight得到9/9 ACCEPTED，self-hash `ca53e2ce4d83391e49c8e18a6b6d56c3c139682b7b74a9a1d1bf89ae61b43960`；upstream receipts、prereg/C1/C2 ancestry、tool hashes、runtime executables、291 render budget、18/16 rosters与disk reserve均exact。观测available `313,538,138,112` bytes，projected 2 GiB，reserve 100 GiB；operations明确为0 child/Blender/render/model/network/Docker。该clone只作rehearsal，随后移出`/tmp`，其preflight不作为official evidence。下一动作是在主仓库相同tool freeze上生成official zero-Blender preflight并提交推送。

## J-416 · B62 Phase 0 v0.1 generator正式失败与C3预注册

Date: 2026-08-29 · Type: RETAINED FORMAL FAILURE / CORRECTION PREREGISTRATION · New B62 Blender processes: 1 · New B62 renders: 0

official preflight `ad7bc82…`以evidence commit `ea88148…`推送后，v0.1 runner完成durable admission并启动01-GENERATOR。Blender 5.2.0 LTS `fbe6228777e7`在0.752秒、peak RSS 260,882,432 bytes后exit 1；未timeout、未termination、logs未截断、render 0。错误为factory scene在`media_type=IMAGE`时，`file_format`枚举没有`OPEN_EXR_MULTILAYER`。

失败保持`B62_PHASE0_INVALIDATED`：attempt 7 files/7,519 bytes/tree `f27179c8…`，formal 5 files/493,005 bytes/tree `f71e288a…`，failure file/self `8cb9c5cd…/dc47c06a…`。没有进入animatic/calibration，不得覆盖v0.1。

B61同build成功的差异是其source blend已保存multilayer media状态；C3预注册D1 one-Blender/zero-render probe，测试factory默认、错误顺序reject、先`MULTI_LAYER_IMAGE`再`OPEN_EXR_MULTILAYER`accept及HALF/ZIP。只有D1 PASS才允许两份Blender工具增加显式media_type设置；其余参数完全不变，retry使用全新v0.2三棵roots。

## J-417 · B62 D1 retained FAIL与C4动态setter预注册

Date: 2026-08-29 · Type: RETAINED DIAGNOSTIC FAILURE / FOLLOW-UP PREREGISTRATION · New B62 Blender processes: 1 · New B62 renders: 0

D1 Blender probe本身exit 0、0.468秒、peak RSS 241,074,176 bytes、zero render/external calls。它观察到factory `media_type=IMAGE`时multilayer setter TypeError；切到`MULTI_LAYER_IMAGE`后setter、HALF、ZIP全部成功。但RNA `enum_items`在两状态都返回包含`OPEN_EXR_MULTILAYER`的static superset，导致预注册8 checks中`MULTILAYER_ENUM_ABSENT_BEFORE_MEDIA_TYPE`唯一false。result/receipt status均FAIL，root 4 files/6,238 bytes/tree `a0194426…`，不得改判。

C4把失败归因为static metadata不是dynamic assignability的有效proxy，预注册D2 one-Blender/zero-render、3 repetitions A→B→A setter实验：每轮IMAGE reject、MULTI accept、回IMAGE reject，共9/9 outcomes；判决明确忽略enum roster。只有D2 PASS才能实施C3限定的media_type production correction与v0.2 retry。

## J-418 · B62 D2 dynamic setter PASS与C5 v0.2 retry预注册

Date: 2026-08-29 · Type: DIAGNOSTIC PASS / RETRY PREREGISTRATION · New B62 Blender processes: 1 · New B62 renders: 0

D2 tool freeze `356f93c…` pushed；one Blender在0.46秒、peak RSS 239,124,480 bytes完成3 repetitions A→B→A。所有A1/A2 `IMAGE`赋值均TypeError reject，所有B `MULTI_LAYER_IMAGE`均accept，9/9 outcomes exact；final MLEXR/RGBA/HALF/ZIP exact，zero render/model/network/Docker。8/8 runner checks与独立audit PASS，result/receipt file/self hashes exact为`1537b178…/6d26de07…`与`1d529640…/c342ff04…`。

C5在production tools未改前冻结v0.2策略：两份Blender工具只加media_type顺序与report字段；三个Node工具只绑定C3/C4/C5、D2 PASS、v0.1 retained trees并换用v0.2 roots。six Blender/291 renders/2 GiB/100 GiB/18 gates/16 attacks与所有claims不变。下一动作先提交推送D2+C5，再实现五文件限定修改与新tool freeze。

## J-419 · B62 Phase 0 v0.2 fresh-clone rehearsal PASS

Date: 2026-08-29 · Type: ZERO-BLENDER RETRY REHEARSAL · New B62 Blender processes: 0 · New B62 renders: 0

五个C5授权文件修改后，v0.2 tool freeze `50f26d400ac56a43516a56429956d2b4b68dc0ea` pushed且HEAD/origin exact。fresh local clone `/tmp/b62-rehearsal-50f26d4`未安装node_modules，v0.2 roots初始absent。

preflight 9/9 ACCEPTED，self-hash `79bbde89542a5faa59dcd584eac2f93e536aac0d2c6884131199f2ab32f82de3`。除C1–C5 ancestry/tool hashes/upstream/runtime/disk外，它重新计算v0.1 attempt/formal与D1 retained trees，并exact绑定D2 result/receipt self-hashes `6d26de07…/c342ff04…`。available 311,752,810,496 bytes，2 GiB projected与100 GiB reserve通过；0 child/Blender/render/model/network/Docker。clone随后移出`/tmp`，不作为official evidence。下一动作主仓库official v0.2 preflight。

## J-420 · B62 Phase 0 v0.2 color-look正式失败与C6预注册

Date: 2026-08-29 · Type: RETAINED FORMAL FAILURE / CONFIG-SURFACE PREREGISTRATION · New B62 Blender processes: 1 · New B62 renders: 0

official v0.2 preflight `bdf4d0e…`以commit `4ae9076…`推送后，01-GENERATOR越过MLEXR设置，在0.709秒、peak RSS 262,062,080 bytes后因`Medium High Contrast`不属于当前look enum退出；zero render，未timeout/termination/log truncation。attempt 7 files/8,541 bytes/tree `affb94dc…`，formal 5 files/493,162 bytes/tree `ee02554c…`，failure file/self `e93877ef…/e5bdfba2…`，永久保留。

C6不再逐一猜API，预注册D3 one-Blender/zero-render配置表面探针，一次检查runtime display/view/look、Cycles、Eevee final samples、motion blur与MLEXR/HALF/ZIP。若全部PASS，只允许neutral runtime override `sRGB - Display / ACES 2.0 - SDR 100 nits (Rec.709) / None`；不允许看像素后补偿调色。后续候选root为v0.3，formal budgets/claims不变。

## J-421 · B62 D3 retained engine-enum失败与C7预注册

Date: 2026-08-29 · Type: RETAINED DIAGNOSTIC FAILURE / RUNTIME ENUM PREREGISTRATION · New B62 Blender processes: 1 · New B62 renders: 0

D3在structured marker前exit 1，只留下stdout/stderr 2 files/2,218 bytes/tree `408c555f…`；file hashes `92594064…/ba40ddf2…`。color neutral与Cycles赋值已执行未抛错，停止点为`BLENDER_EEVEE_NEXT`不在runtime enum；Blender 5.2列出的当前engine是`BLENDER_EEVEE`。zero render。

C7预注册D4 one-Blender/zero-render：catch并记录旧name reject，要求新`BLENDER_EEVEE`accept、taa_render_samples 16 accept，再完成全部C6 color/Cycles/motion/EXR surface checks。仅完整PASS才允许runtime engine与neutral color override；formal dose/budgets/claims不变。

## J-422 · B62 D4完整配置表面PASS与C8 generator smoke预注册

Date: 2026-08-29 · Type: DIAGNOSTIC PASS / PRODUCTION-SMOKE PREREGISTRATION · New B62 Blender processes: 1 · New B62 renders: 0

D4 tool freeze `2b81b26…`；one Blender 0.46秒/peak RSS 237,944,832 bytes，captured surface errors zero。9/9 checks与独立audit PASS：neutral display/view/look exact，Cycles CPU/64/denoise/fixed seed exact，旧Eevee name reject、`BLENDER_EEVEE`+16 viewport/final samples accept，motion blur与MLEXR/HALF/ZIP exact，zero render/external calls。result/receipt file/self hashes为`8c911957…/2e09fe11…`和`c7fd3bba…/67b951e0…`。

C8在production code未改前授权两项runtime-only更正，并预注册D5真实generator smoke：冻结production generator，one Blender/zero render，独立root，512 MiB write/100 GiB reserve；必须完整生成3 assets+motion+master+valid report。D5通过前不更新formal Node tools、不运行v0.3。

## J-423 · B62 D5生产generator smoke PASS与C9 v0.3预注册

Date: 2026-08-29 · Type: PRODUCTION GENERATOR SMOKE PASS / FORMAL RETRY PREREGISTRATION · New B62 Blender processes: 1 · New B62 renders: 0

D5 tool freeze `2288a2edd2aa15085da99bbc2bdb50ccc873619d`推送后，真实Blender 5.2 production generator在0.729秒、peak RSS 268,468,224 bytes内完成。它生成三份asset libraries、motion library与master blend；timeline为1–288/24 fps/三镜头，neutral ACES transform exact。8/8 checks与独立Node audit均PASS，zero render/model/network/Docker。

D5 root共10 files/895,636 bytes/tree `023e5c5c…`；result file/self `ce348efb…/a7157c11…`，receipt file/self `8ad9c755…/7f0fc9e6…`，verdict为`B62_PRODUCTION_GENERATOR_SMOKE_PROVEN`。磁盘仍约290 GiB available。

C9在formal Node工具修改前绑定C6–C9、retained v0.2/D3、D4/D5 PASS与D5-frozen production Blender tools。只允许三个Node工具切换v0.3 fresh roots、要求`BLENDER_EEVEE`与neutral color exact；18 gates/16 attacks、6 Blender/291 renders、2 GiB/100 GiB及claim boundary不变。下一动作提交推送D5+C9，再实现Node binding、fresh-clone rehearsal和official preflight。

## J-424 · B62 Phase 0 v0.3 fresh-clone与official preflight PASS

Date: 2026-08-29 · Type: ZERO-BLENDER RETRY REHEARSAL / OFFICIAL PREFLIGHT · New B62 Blender processes: 0 · New B62 renders: 0

三个C9授权Node工具以commit `ee6ffff37852fcb38fbf9de81146552a4d162ffc`冻结并推送。工具绑定C1–C9 ancestry、retained v0.1/v0.2/D1/D3 trees、D2/D4/D5 PASS evidence以及production Blender tools；formal expectations切到`BLENDER_EEVEE`和D4-proven neutral color，v0.3 roots fresh。

fresh local clone无`node_modules`。首次用`/tmp`绝对script path调用时，macOS将module URL规范化为`/private/tmp`，入口guard未触发，未创建root、未启动child；改为clone内相对入口后preflight 9/9 ACCEPTED，self-hash `31e2f53e…`，zero child/Blender/render/model/network/Docker，随后clone移入Trash。

主仓库official preflight同一freeze上9/9 ACCEPTED；file/self hashes为`126a31a159c92416413f2231b6820d712a5b4484fefbd19181ba0332b759ab4c / 37aece8774d5d88ce049ad7b60e36a4fea4843bdc7fdef9e7b890f7f840a82cd`。D2/D4/D5 self-hashes exact，available 310,012,510,208 bytes，projected 2 GiB/100 GiB reserve通过。下一动作提交推送official evidence后启动v0.3 formal attempt。

## J-425 · B62 Phase 0 v0.3完成291 renders但独立library gate失败

Date: 2026-08-29 · Type: RETAINED FORMAL FAILURE / LOCALITY DIAGNOSTIC PREREGISTRATION · New B62 Blender processes: 6 · New B62 renders: 291

v0.3完成generator、288-frame Eevee animatic、ffmpeg、ffprobe与frames 48/144/240三张1080p/64 spp Cycles calibration。阶段wall time约0.73/32.32/0.19/0.06/35.02/41.14/44.92秒；Cycles peak RSS约3.75–3.76 GiB。生成、timeline、neutral color、288-frame/24 fps/12 s video、三份MLEXR/HALF/ZIP及decoded finite/dynamic pixels均成功，zero model/network/Docker。

第六个Blender即独立auditor在1.91秒完成观察后exit 1。23 checks中21项PASS，只有`masterExternalLibrariesZero`与`assetLibrariesSafe`false；每份asset唯一finding均为`EXTERNAL_LIBRARY`，但其identity/topology/rig仍exact，motion action也exact。v0.3保持INVALIDATED：attempt 28 files/81,121 bytes/tree `c08a3422…`，formal 308 files/122,895,659 bytes/tree `a2ca78e3…`，failure file/self `5aaf7b9e…/f934bc8d…`，audit file/self `6a346c9f…/9aebbe68…`。

代码审查发现可能的temporal contamination：auditor在三次append之后才读取master library总数，并把append新增descriptor直接视为外链，未检查appended IDs的`.library`。C10预注册D6 one-Blender/zero-render locality probe；在D6证明前禁止放宽安全门或重用v0.3作为PASS。

人工原分辨率抽查：wide与medium能读出cold→warm机械守夜人场景；close frame 240大面积被前景遮挡，构图质量不足。该观察不是当前machine verdict的一部分，必须后续另立camera-quality实验，不能事后修改本轮门槛。

## J-426 · B62 D6证明append-locality并预注册C11 corrected-auditor smoke

Date: 2026-08-29 · Type: DIAGNOSTIC PASS / AUDITOR-ONLY CORRECTION PREREGISTRATION · New B62 Blender processes: 1 · New B62 renders: 0

D6 tool freeze `e843840c97084011601eeb4f4092745139adb78f`推送后，one Blender在0.494秒、peak RSS 255,377,408 bytes完成。master初始library与linked IDs均为0；三份asset分别append 54/84/16个tracked IDs，全部`.library=null`。每份只新增一个descriptor且路径exact指向对应source blend；descriptor删除成功且local IDs全部存活，逐项cleanup与最终roster exact。

8/8 runner checks与独立Node audit PASS，zero render/model/network/Docker。D6 root 5 files/48,753 bytes/tree `d507bf6b…`；probe file/self `84c11998…/49713805…`，result file/self `8bc69dce…/1952f4bd…`，receipt file/self `c7b11368…/150fb110…`，verdict为`LOCAL_APPEND_SOURCE_DESCRIPTOR_ONLY`。

C11在production auditor修改前只授权temporal/locality更正：master gate读取append前snapshot；asset gate要求ID local、descriptor exact-source、移除后存活、cleanup exact。既有23 checks不减，v0.3仍INVALIDATED。下一动作提交推送D6+C11，实现auditor并以D7 one-Blender/zero-render独立root验证。

## J-427 · B62 D7 corrected production auditor 23/23 PASS与C12 v0.4预注册

Date: 2026-08-29 · Type: CORRECTED AUDITOR SMOKE PASS / FRESH FORMAL RETRY PREREGISTRATION · New B62 Blender processes: 1 · New B62 renders: 0

D7 tool freeze `0402f2476c7259cef3c4c85ced7bf80553f458a7`推送后，corrected production auditor只读重开retained v0.3，在1.865秒、peak RSS 433,881,088 bytes完成。原有23 checks全部PASS；master locality初始空，三份asset无findings，54/84/16 appended IDs全local，descriptor exact-source、移除后存活、cleanup exact。zero render/model/network/Docker。

D7 runner与独立Node audit均8/8 PASS。root 5 files/134,507 bytes/tree `7b5e6194…`；audit file/self `6c223524…/8183f498…`，result file/self `f4ff4c68…/59078802…`，receipt file/self `b42b905c…/31903a70…`，verdict为`CORRECTED_PRODUCTION_AUDITOR_PROVEN`。

C12在formal Node工具修改前授权绑定C10–C12、retained v0.3、D6/D7 PASS与D7-frozen auditor，并使用fresh v0.4 roots。Node audit必须直接复核locality rows；其余生产工具、291 renders、18 gates/16 attacks、预算与claims不变。下一动作提交推送D7+C12，再做tool freeze、fresh-clone rehearsal、official preflight和完整v0.4重跑。

## J-428 · B62 Phase 0 v0.4 fresh-clone与official preflight PASS

Date: 2026-08-29 · Type: ZERO-BLENDER REHEARSAL / OFFICIAL PREFLIGHT · New B62 Blender processes: 0 · New B62 renders: 0

三个C12授权Node工具以commit `20c5c4bd07d842a0131e8b14896ae72ed09734fd`冻结推送，绑定C1–C12、retained failures、D2/D4/D5/D6/D7 evidence与D7-frozen production auditor，并切换fresh v0.4 roots。静态syntax、ESLint与diff checks通过。

无`node_modules` fresh clone preflight 9/9 ACCEPTED，self-hash `a6a01d14…`；zero child/Blender/render/model/network/Docker，随后clone移入Trash。主仓库official preflight同一freeze上9/9 ACCEPTED，file/self `ae3a619c7387d5deffdb2a8c7067eb061601efd8898e8e98c481db61a17e9f88 / 6145aa064d0023e2f110993c95561ed47a8d8fceaa13c8c83d27ede8f1423bef`。available 307,508,101,120 bytes，projected 2 GiB/100 GiB reserve通过。下一动作提交推送official evidence后启动v0.4完整formal。

## J-429 · B62 Phase 0 v0.4正式通过，镜头质量门仍开放

Date: 2026-08-29 · Type: FORMAL PHASE-0 PASS / QUALITATIVE COUNTEREVIDENCE · New B62 Blender processes: 6 · New B62 renders: 291

v0.4在tool freeze `20c5c4bd07d842a0131e8b14896ae72ed09734fd`上使用fresh roots完整重跑：generator、288-frame Eevee animatic、ffmpeg/ffprobe、frames 48/144/240三张1080p 64 spp Cycles calibration、独立Blender reopen audit与Node audit全部exit 0。18/18 gates、16/16 mutation attacks、23/23 Blender checks通过，verdict为`B62_PHASE0_ASSET_ANIMATIC_AND_CALIBRATION_ADMITTED`，receipt self-hash `462ae5409019fc1dc578dad74e9648ad1e6132641a49cffc9d73a90e770b6986`。

本轮6次Blender启动、291次render（288 Eevee + 3 Cycles）、1次ffmpeg、1次ffprobe、1次Node audit；model/network/Docker均0。process wall before Node audit 154.7549秒，animatic render 29.8739秒，三张Cycles合计118.0201秒、mean 39.3400秒/frame，peak RSS 3,766,190,080 bytes。机械外推288帧约3.15小时，但明确不是实测sequence成本。attempt tree为30 files/84,420 bytes/`35a57b81…`；formal tree为311 files/122,957,493 bytes/`3de8ee7e…`。

v0.3/v0.4描述性复现中，三张Cycles decoded Combined digests、三张calibration PNG、asset identity、motion action与final MP4均exact；individual animatic PNG container hashes为0/288 exact，未做新的decoded-pixel实验，因此不追加像素exact主张。

人工原分辨率观察与machine verdict分开记录：WIDE与MEDIUM可读，CLOSE frame 240被前景大面积遮挡，构图质量不足。Phase 0只关闭资产、animatic、calibration与审计链，不支持电影级构图、photoreal actor、人类审片或完整288帧Cycles。下一步先预注册camera-quality gate，在关键帧与廉价animatic上拒绝坏镜头，再决定是否支付full Cycles成本。

## J-430 · B62证据双站发布闭环与Sites运行时A/B

Date: 2026-08-29 · Type: EVIDENCE PUBLICATION / RETAINED DEPLOYMENT FAILURES · New Blender processes: 0 · New Blender renders: 0

B62 Phase 0研究页、三张Cycles校准PNG与12秒animatic先以commit `5a6b321…`提交。首轮GitHub Pages因sparse checkout缺少页面直接导入的6份JSON而失败；commit `4b94250…`把exact audit/receipt/pixel evidence加入checkout后，Pages恢复。随后各发布修正触发的Pages workflows全部成功；最终公开探针验证研究页、PNG与MP4均HTTP 200。

私有Sites保留全部失败版本，不把“deployment succeeded”等同于“page works”。直接推送约118 MiB全仓库与浅clone均遇到provider HTTP 500，因此改用与Pages证据选择一致的轻量source snapshot。v86因vinext default export不是`{fetch}`而deployment failed；v87增加adapter后部署成功、静态媒体200，但动态页因缺失`react/jsx-runtime`返回500；v88把全部runtime依赖绑定进单一entry，部署成功但Worker启动即Cloudflare 1101，页面与静态媒体全500；v89改为轻量worker entry与lazy bundled SSR，静态PNG/MP4恢复200，但页面SSR仍1101。

最终v90没有继续要求平台实时SSR这份完全可静态化的研究档案：先由Next输出94个确定性静态页面，再由vinext生成Sites worker/fallback，最后把static export合并到client asset tree。真实本地Wrangler检查首页、B62、Blender 5.2、Journal、PNG与MP4均200；owner-only production deployment `appgdep_6a92c3931e8c8191bc4964eb0be4ec96`成功后，使用Sites身份头重复同一六项探针，全部HTTP 200。v90 source commit为`74827cdab5eb04ea368ef533bbf8193f32866559`，archive content hash为`sha256:e4ccc822a3a5f45eaad5d825cc83a628c58029b8e65b5378ee793f72bbd3de9a`。

发布层结论：研究证据现在同时存在公开GitHub Pages与owner-only Sites；构建成功、部署成功、静态媒体可达和动态页面可达必须分别验证。该闭环不改变J-429的科学边界；下一技术目标仍是camera-quality gate，而不是完整288帧Cycles。

## J-431 · B62-Q1-D1相机近遮挡几何诊断预注册

Date: 2026-08-29 · Type: CAMERA QUALITY DIAGNOSTIC PREREGISTRATION · New Blender processes: 0 · New Blender renders: 0

重新以原分辨率查看B62三张校准帧：WIDE与MEDIUM可读，CLOSE frame 240几乎整帧为无语义的平滑近景表面。该观察只形成公开的derivation label，不能直接授权凭眼移动相机。

D1冻结two fresh Blender/zero-render只读诊断。primary与independent Python分别在frames 48/144/240投射64×36 camera rays，记录first-hit owner/distance、0.5 m near-field share、dominant owner、center ray、五个语义anchor exact visibility及角色evaluated-vertex投影。两实现不得互相import，整数roster exact、float tolerance 1e-9；随后独立Node auditor检查input/tool/runtime/process/resource/output与outcome-neutral verdict。

诊断只在CLOSE同时满足dominant share≥0.90、near-field share≥0.90、5 anchors最多1个可见，且两个readable controls均不满足完整signature时，支持`B62_CLOSE_FAILURE_GEOMETRIC_NEAR_OCCLUSION_LOCALIZED`。阈值只用于定位已知反例，不是电影感定义。预算2 Blender starts、0 render、64 MiB writes、100 GiB reserve、zero model/network/Docker。下一动作先提交推送本预注册，再允许创建四个工具。

## J-432 · B62-Q1-D1 v0.1版本字符串合同失效与C1预注册

Date: 2026-08-29 · Type: RETAINED FORMAL FAILURE / CONTRACT NORMALIZATION PREREGISTRATION · New Blender processes: 2 · New Blender renders: 0

D1 tool freeze `76fd3b3…`推送后，PRIMARY与INDEPENDENT Blender均在约0.72/0.55秒、peak sampled RSS约254/253 MiB内exit 0，各完成3 frames×2,304 rays与五anchor/角色投影观察，render/model/network/Docker均0。独立Node auditor在47 ms后exit 1，错误为`PRIMARY Blender identity mismatch`，因此没有comparison/audit/receipt，scientific verdict为null。

根因是spec冻结CLI字符串`Blender 5.2.0 LTS`，而两份bpy observation按API真实返回`5.2.0 LTS`；build hash均为正确的`fbe6228777e7`。v0.1永久保留7 files/1,527,639 bytes/tree `bbd77737…`，failure file/self `758e2187…/38e36cdd…`。

C1在Node工具修改前只允许auditor比较`Blender ${bpyVersion}`并继续exact检查build hash，同时允许runner绑定v0.1 retained tree后使用fresh v0.2 root。两份Blender工具bytes、ray grid、frames/cameras、anchors、0.5 m、0.90/0.90/1-of-5 signature、process/resource budgets与zero-render边界全部不变；v0.1几何字段不得复制到retry，也未用于改阈值。

## J-433 · B62-Q1-D1科学否定与D2材质感知构图诊断预注册

Date: 2026-08-29 · Type: DIAGNOSTIC TECHNICAL PASS / SCIENTIFIC REJECTION / NEXT DIAGNOSTIC PREREGISTRATION · New Blender processes: 2 · New Blender renders: 0

D1 C1 retry以tool freeze `9e17cd798732098c089aabe083b037c076f2c705`运行。PRIMARY与INDEPENDENT分别约0.584/0.558秒、peak sampled RSS 256,032,768/254,951,424 bytes，独立Node auditor约0.063秒；两实现exact同意，12/12 technical checks PASS，zero render/model/network/Docker。v0.2 immutable root为9 files/1,535,498 bytes/tree `d0c80437a478669d81d1f3afef6e0d7a60ff2bdcf9d13762218719622bd6db3b`，receipt file/self为`bec3a277…/2a5dc2aa…`。

科学结论按预注册原样REJECTED：`CLOSE_REFLECTION`的near-field share为0，不满足0.5 m阈值；`WIDE_APPROACH`反而满足complete signature。原因不是控制帧视觉失败，而是普通`scene.ray_cast`把只有Volume连接、没有Surface连接的`B62_ATMOSPHERE`闭合网格边界当成opaque first hit。因此不得改0.5 m或删除WIDE反例，verdict保留为`B62_CLOSE_FAILURE_GEOMETRIC_NEAR_OCCLUSION_NOT_LOCALIZED`。

D1同时暴露另一条待检信号：CLOSE 2,304/2,304 rays均first-hit `B62_HELMET`，角色on-screen vertex fraction仅0.07549，unclamped bounds大幅越界而clamped union area为1.0；WIDE/MEDIUM分别为1.0/0.65649 on-screen。D2在任何新工具创建前冻结material-aware traversal：仅跳过每个material slot都Volume-linked且Surface-unlinked的owner，10 μm推进、最多64 intersections；two independent Blender重新测三帧。CLOSE必须同时满足helmet dominant≥0.95、character blocker≥0.95、on-screen vertices≤0.10、clamped area≥0.95、anchors≤1/5，且两controls不满足全条件。阈值明确由D1导出，只能定位该失败，不能宣称通用电影构图或holdout通过。

## J-434 · B62-Q1-D2材质感知定位PASS与D3有界相机搜索预注册

Date: 2026-08-29 · Type: DIAGNOSTIC SCIENTIFIC PASS / CAMERA SEARCH PREREGISTRATION · New Blender processes: 2 · New Blender renders: 0

D2以tool freeze `8a898331c531e4115dd9f10ff1285473f739950b`运行，PRIMARY/INDEPENDENT分别0.665/0.644秒、peak sampled RSS 258,179,072/265,748,480 bytes，Node auditor 0.086秒。13/13 checks与完整observation在1e-9内同意；root为9 files/5,153,731 bytes/tree `d1f21b573b6f6bb5579106bfd6100afeadf7acf1b7b72e39dec6c44659775cf9`，receipt file/self为`b0faa652…/d9554b57…`，zero render/model/network/Docker。

`B62_ATMOSPHERE`被两实现exact证明为`MAT_B62_VOLUME`、one Material Output、Volume linked、Surface unlinked，并按冻结规则穿透。WIDE的visual blocker因此恢复为多对象场景，dominant为floor 0.17014、character share 0.03993；MEDIUM为torso 0.21918、character share 0.56033。CLOSE仍是2,304/2,304 helmet、character share 1.0、on-screen vertex fraction 0.07549、clamped area 1.0、anchors 1/5；只有CLOSE满足六项完整signature。scientific verdict为`B62_CLOSE_FAILURE_MATERIAL_AWARE_EXTREME_HELMET_FRAMING_LOCALIZED`。

D3在任何search工具创建前冻结96-cell相机族：8个绕target的world-Z azimuth × 3个radial scale × 4个lens，只读测frames 216/240/264；frames 193/204/228/252/276/288预先封存为后续holdout。two independent Blender必须搜索完整288 cells。候选需在三帧都露出visor+eye，helmet≤0.70、character blockers 0.20–0.90、on-screen vertices 0.10–0.60、clamped area 0.35–0.90、visible anchors≥2；原始baseline必须失败。通过只证明有界族内存在eligible correction，不等于渲染或电影感通过。

## J-435 · B62-Q1-D3 v0.1浮点原语失配与C1预注册

Date: 2026-08-29 · Type: RETAINED FORMAL FAILURE / NUMERIC PRIMITIVE CORRECTION PREREGISTRATION · New Blender processes: 2 · New Blender renders: 0

D3 tool freeze `d5c198ec9224d06925041311c203168f84e6ea40`运行后，两份Blender都完成96 candidates×3 derivation frames、zero render/model/network/Docker，并都报告baseline infeasible、feasible count 1、selected `AZ_M045_R200_L065`。但是Node audit只通过14/15 checks：91个`clampedUnionAreaFraction`差异超过冻结的1e-9，最大量级约1e-7；因此scientific verdict按合同为null，不能用相同candidate ID补救。

根因是PRIMARY使用Blender `Matrix.Rotation`，INDEPENDENT手写Python `sin/cos`构造同一world-Z rotation；微小coordinate差传播到projection bounds。v0.1永久保留9 files/1,262,543 bytes/tree `6f4d2928…`，failure file/self `56371264…/d1848261…`。

C1在工具修改前只授权INDEPENDENT改用同一Blender rotation primitive，并授权runner/auditor绑定retained failure后使用fresh v0.2 root。PRIMARY hash `146a45da…`固定；96 cells、frames 216/240/264、六个sealed holdouts、全部feasibility bounds、selection order、1e-9 tolerance与zero-render预算均不变。

## J-436 · B62-Q1-D3 v0.2唯一候选PASS与D4 holdout渲染预注册

Date: 2026-08-29 · Type: BOUNDED SEARCH PASS / SEALED HOLDOUT RENDER PREREGISTRATION · New Blender processes: 2 · New Blender renders: 0

C1 retry以tool freeze `029913a1b9fd8e43559387cc31a4e82c4677ab50`在fresh v0.2 root运行。PRIMARY/INDEPENDENT分别5.378/5.387秒、peak sampled RSS 255,180,800/255,082,496 bytes；Node audit 0.061秒。16/16 checks、96-cell roster、288 candidate-frame cells与1e-9 comparison全部PASS，zero render/model/network/Docker。root 9 files/1,250,026 bytes/tree `94e04a65…`，receipt file/self `3d00ed2d…/1111e6fa…`。

原始baseline在derivation frames不合格；96 cells仅`AZ_M045_R200_L065`一个候选三帧全合格：绕target −45°、radial distance ×2、65 mm。frames 216/240/264的helmet share为0.25/0.12847/0.16840，character share 0.43924/0.27778/0.34375，on-screen vertex fraction 0.29283/0.37744/0.32676，clamped area 0.80054/0.48127/0.60346；每帧均exact可见visor、eye slit、chest light与core。verdict为`B62_CLOSE_CAMERA_BOUNDED_FEASIBLE_CANDIDATE_FOUND`。

D4在任何新工具创建前冻结该唯一候选，并只在admission后解封frames 193/204/228/252/276/288。候选将按每个integer frame采样原camera后变换并bake到新camera，保存derived `.blend`；原camera保留作paired control。第二Blender以960×540、Cycles CPU 16 spp渲染6×2 EXR/PNG，第三Blender独立复开检查bake、几何与像素。corrected六帧必须全过D3 template、original六帧必须全拒绝，12 EXR必须finite/non-empty且每pair不同。即使technical PASS，六组原图仍需人眼审查；不得直接宣称电影感。

## J-437 · B62-Q1-D4 v0.1 Blender 5.2 layered Action API失败与C1预注册

Date: 2026-08-29 · Type: RETAINED BUILD FAILURE / API CORRECTION PREREGISTRATION · New Blender processes: 1 · New Blender renders: 0

D4 tool freeze `d074402bb2ad80b6f6885feaed9be83af08f75de`运行后，BUILD Blender在0.486秒、peak sampled RSS 225,935,360 bytes失败；未创建derived scene，render calls为0。错误是builder访问`Action.fcurves`，但Blender 5.2 layered Action必须通过assigned-slot channelbag访问。v0.1永久保留3 files/7,084 bytes/tree `8538b1bc…`，failure file/self `c6ff5399…/7f3c1849…`。

C1在工具修改前只授权builder使用`anim_utils.animdata_get_channelbag_for_assigned_slot(...).fcurves`，runner/auditor绑定failure并切换fresh v0.2。render tool hash `e20efbad…`与independent audit hash `c39a39bb…`固定；候选、96-frame bake、六个holdout、12 render、所有阈值和预算不变。

## J-438 · B62-Q1-D4 v0.2跨语言浮点canonical失败与C2预注册

Date: 2026-08-29 · Type: RETAINED REPORT-ADMISSION FAILURE / CANONICALIZATION PREREGISTRATION · New Blender processes: 1 · New Blender renders: 0

C1 BUILD在0.527秒、peak sampled RSS 262,012,928 bytes通过，新增camera/data/action各1，bake 96 frames并产生337,606-byte derived blend `3784fc48…`。runner随后拒绝build report：Python self hash为`f78897b1…`，Node按同一数值对象重算为`a98f3bf1…`。根因是极小非整数浮点的JSON exponent拼写`e-08` vs `e-8`；数值round-trip相同，canonical bytes不同。无render发生，v0.2保留5 files/469,558 bytes/tree `eb62dd16…`。

C2在工具变更前冻结跨语言representation：非整数finite float转为`{"$f64be":16-hex IEEE-754 binary64 bits}`参与hash，整数float转integer；持久化科学字段仍为number。三份Python与两份Node只改canonical helper和fresh v0.3 bindings；候选、bake、holdout、几何、Cycles、12 render与预算不变，v0.2 scene禁止复用。

## J-439 · B62-Q1-D4 v0.3 timeline marker路由失败与C3预注册

Date: 2026-08-29 · Type: RETAINED FULL-RENDER FAILURE / CAMERA ROUTING CORRECTION PREREGISTRATION · New Blender processes: 3 · New Blender renders: 12

C2 retry完成BUILD 0.529秒、RENDER 38.587秒、INDEPENDENT 2.414秒；RENDER peak sampled RSS 1,321,336,832 bytes。12次960×540 Cycles CPU 16 spp均生成finite EXR/PNG，独立解码通过。但六组original/corrected Combined digest逐组exact相同。根因是derived scene保留frame-193 `SHOT_CLOSE_REFLECTION` camera marker；render evaluation把脚本设置的corrected camera再次覆盖为original。Node audit仅`PAIR_PIXEL_DIGESTS_DIFFER`失败，v0.3 verdict为null；root保留35 files/53,694,719 bytes/tree `5e0ebd67…`。

独立几何同时给出不能隐藏的holdout信号：original 6/6失败；corrected frames 193/204/228/252/276通过，但frame 288 clamped area 0.933787超过冻结0.90，因此correctedAllPass=false。C3只授权render时同时设置active marker与scene.camera、结束后恢复marker，并切换fresh v0.4；builder/audit bytes固定，frame288不得删除或放宽。正确路由后允许technical PASS但scientific REJECTED。

## J-440 · B62-Q1-D4 v0.4已正确路由但Node相机名合同失败，C4预注册

Date: 2026-08-29 · Type: RETAINED FULL-RENDER FAILURE / AUDITOR NAME-CONTRACT CORRECTION PREREGISTRATION · New Blender processes: 3 · New Blender renders: 12

C3 retry以tool freeze `b6dd0c74953f25ec0a48d14833e06da17942a608`运行。BUILD 0.523秒；RENDER 34.072秒、peak sampled RSS 1,328,889,856 bytes；INDEPENDENT 2.423秒。12次960×540 Cycles CPU 16 spp全部生成finite EXR/PNG，六组ORIGINAL/CORRECTED Combined digest逐组不同，证明timeline marker与scene camera双路由已经生效。独立Blender报告original 6/6失败；corrected前五帧通过，frame 288仍只因clamped area 0.933787超过冻结0.90而失败。

Node audit 17项通过、仅`TIMELINE_MARKER_CAMERA_ROUTING_EXACT`失败，scientific verdict因此保持null。根因是C3新增审计表硬编码`CAM_CLOSE_REFLECTION_CORRECTED`，遗漏base spec和三份Blender工具早已冻结的`_D4`后缀；12条render记录的`camera`与`timelineMarkerCamera`都正确为`CAM_CLOSE_REFLECTION_CORRECTED_D4`。v0.4永久保留35 files/54,119,323 bytes/tree `365b4bc64267575bbdbcb92f7390c9690f18514e5c08c10bcc56f584003e885e`。

C4在任何工具修改前只授权Node auditor从`spec.selectedIntervention.sourceCamera/correctedCamera`读取期望名，并授权runner/auditor绑定v0.4后切换fresh v0.5。三份Blender Python bytes、候选、96-frame bake、六帧、全部阈值、12-render Cycles设置和scientific mapping不变；v0.5必须全量新建场、重渲染和独立复开，禁止复用v0.4。若技术链通过，当前冻结数据预计产生合法的scientific REJECTED，而不是PASS。

## J-441 · B62-Q1-D4 v0.5技术链PASS、科学拒绝与原分辨率人工复核

Date: 2026-08-29 · Type: FORMAL TECHNICAL PASS / SCIENTIFIC REJECTION / HUMAN ENGINEERING REVIEW · New Blender processes: 3 · New Blender renders: 12

C4 retry以tool freeze `6c78738`在fresh v0.5 root全量执行。BUILD 0.530秒、peak RSS 260,800,512 bytes；RENDER 34.089秒、peak RSS 1,332,363,264 bytes；INDEPENDENT 2.425秒、peak RSS 302,792,704 bytes；Node auditor 0.083秒。18/18 checks全部PASS，六组像素pair不同，三份Blender Python hash与Blender 5.2 build identity exact，96-frame bake、12份EXR/PNG、独立解码、zero model/network/Docker全部成立。

正式scientific verdict按预登记为`B62_CLOSE_CAMERA_CORRECTION_FAILS_FROZEN_HOLDOUT`：original 6/6失败，corrected frames 193/204/228/252/276通过，frame 288以clamped union area 0.933787超过冻结0.90，故correctedAllPass=false。receipt file/self为`8a7c6cd…/119c1028…`，audit file/self为`97fcca32…/e832532c…`；root 35 files/54,124,627 bytes/tree `f1f25fa4…`。

随后逐张打开全部12张960×540 PNG做有标签工程复核。六张ORIGINAL均为头盔表面近乎占满画面，角色动作与环境关系不可读。CORRECTED在193–228显著恢复visor/eye、上身、手臂和chamber lights，252开始变紧，276–288头盔/肩部持续扩张、环境和身体信息减少，288缺少呼吸空间。人工观察与机械拒绝方向一致，但不改变machine verdict，也不是blind preference evidence。

D4关闭了“静态有界修正能否覆盖全shot”的问题：能修复灾难性遮挡，但不能稳定覆盖运动中的整段构图。下一实验必须保留0.90门槛，预登记motion-aware camera path或scale compensation；不得推广v0.5 camera、删除frame288或把16 spp诊断图称为最终电影画质。
