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
