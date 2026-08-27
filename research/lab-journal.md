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

## Active goal experimental contract

This contract is part of the active BlenderFilmStudio goal and applies to every subsequent stage:

1. preregister the falsifiable question, variables, controls, thresholds and rejection conditions before creating the tested tool or output;
2. test with real Blender when the claim concerns Blender, and record the exact runtime, hardware-relevant environment, input identity, process identity and randomness controls;
3. retain failed runs, counterexamples, negative observations and boundary conditions instead of rewriting the history around the successful path;
4. label statements as measured fact, inference, subjective judgment or unknown, and never promote one category into another;
5. require a clean reproduction plus adversarial/attack tests before promoting an engineering result;
6. require independent human observers for subjective visual claims; developer pilots and synthetic fixtures remain interface/attack evidence only;
7. publish machine-readable artifacts, hashes, non-claims and the next unresolved boundary, except when delayed disclosure is itself required to preserve a preregistered blind experiment.
