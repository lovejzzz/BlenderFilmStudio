# BlenderFilmStudio — new machine cold start

> **Current decision:** F0.1 through F0.7 passed on the admitted M2 Max host.
> F0.4 attempts 01 and 02 remain retained `FAIL` results. Attempt-01 proved
> canonical-exact B01/B02 BuildPlans and all four negative controls, then found
> a missing OCIO launch binding. Attempt-02 fixed only that binding and built
> B01, but the frozen full structure hash differed because it includes the
> product build hash. Attempt-03 versioned semantic structure separately from
> exact product provenance and closed F0.4 as `PASS`. F0.5 attempt-01 remains
> a retained preview setup `FAIL`; attempt-02 preserved the same thresholds and
> closed F0.5 as `PASS`. F0.6 attempts 01 and 02 remain retained harness
> `FAIL` results; attempt-03 preserved them, passed the fixed merge ceilings and
> the complete F0.1–F0.5 regression corpus, and closed F0.6 as `PASS`. F0.7
> attempts 01–04 remain retained `FAIL` results; attempt-05 produced the
> unsigned research DMG, passed isolated install/uninstall and two frozen
> same-host `.blend` round trips, and closed F0.7 as `PASS`. The direct thin
> fork is now supported for a product prototype, within the recorded claim
> ceiling.

This is the authoritative handoff for a fresh Codex session. The repository is
both a research notebook and an executable evidence base. Read this page,
`AGENTS.md`, and the machine-readable state before doing anything expensive.

Owner standing autonomy is now active through
`specs/ai-native-studio-standing-autonomy-charter.v1.0.json`. Safe, in-scope,
reversible project edits, builds, Blender runs/renders, evidence creation,
ordinary commits and non-force fast-forward pushes no longer require repeated
per-attempt authorization. Purchases/new charges, destructive or force actions,
public binary releases/DMG distribution, signing/notarization, credential or
account changes, third-party/legal commitments and material scope/resource
expansion still require specific confirmation. Historical frozen evidence is
not rewritten; new adapters must bind the standing charter explicitly.

## Where the project stands

- **Latest direction:** direct official Blender thin fork; Bforartists is a UI
  and fork-maintenance reference; an external shell remains the fallback.
- **Pinned engine baseline:** official `v5.2.0` at
  `fbe6228777e7d9afefcd61a413844e790ae75db7`; the admitted F0.6 merge target is
  official `v5.2.1` commit `9e2066aef7ef7e20c142ad7bd3303138a4304c93`.
- **Completed experiment:** `F0-SOURCE-FEASIBILITY`. All seven gates are
  `PASS`. The post-F0 repository/Phase B charter is frozen at commit
  `6a38ca3b…`; repository creation was later authorized, and Phase B is now
  governed by the active standing-autonomy charter plus versioned protocols.
- **Repository readiness:** the current F0 checkout is shallow (1,165 reachable
  commits), so direct push from it was rejected as a full-history strategy.
  A read-only GitHub Blender mirror plus local-only graft/push rehearsal closed
  as `PASS` in C2 attempt-03. Its destination contains 162,917 reachable commits,
  exact HEAD `fa1b578b…`, exact tree `4d761fb7…`, merge base `9e2066ae…` and a
  clean full `git fsck`. Runner/auditor self hashes are `dc1cc768…` and
  `b841e519…` (93/93). External repository creates/pushes and LFS uploads were 0.
- **Repository publication failure retained:** owner authorization v0.2 changed
  the name to `film-engine`. The runner created public fork
  `lovejzzz/film-engine`, verified parent `blender/blender`, one generated
  `main`, zero PRs/releases, then GitHub rejected both new brand LFS objects at
  0/2 and 0 bytes: `can not upload new objects to public fork`. Stop rules held:
  external create/LFS upload/ref update/release/Phase B counts are
  `1/0/0/0/0`; independent failure audit is 33/33 PASS.
- **Repository publication C1 accepted:** owner authorized the exact three-path
  ordinary-blob correction. One commit, `4061e12b…` / tree `5f0cb3eb…`, has
  sole parent `fa1b578b…` and changes only `.gitattributes`, icon and splash.
  Fresh local and GitHub no-smudge clones materialized both unchanged binaries.
  One exact `08bed5b5…`-bound lease push updated only `main`; LFS uploads,
  other refs/tags, releases and Phase B were 0. Independent audit is 59/59
  PASS with self hash `71d6e9d5…`. Later Phase B work is governed by standing
  autonomy and versioned protocols.
- **PB.1 attempt-01 retained failure:** the authorized public no-smudge clone,
  complete graph, local-only LFS materialization and 9/9 negative controls passed.
  The runner stopped before dependency/build/start because the retained F0
  `841/68` line statistic was evaluated under C1 attributes, where the two old LFS
  pointer paths are binary (`837/64 + 2 binary`). A first failure audit retained a
  storage-scope error at 41/42; C1 independently passed 29/29, proving all immutable
  LFS objects unchanged and recording 3,918 zero-byte tmp files. Another correction
  checkout/materialization is not authorized.
- **PB.1 C1 attempt-02 retained failure:** exact v0.5 authorization, formal preflight
  and 9/9 negative controls passed. One local-only clone was consumed, then the runner
  stopped before LFS checkout because skip-smudge publication checkout had created an
  empty 6,424-directory `.git/lfs/objects` skeleton before symlink installation. LFS
  materialization, dependency clone, build, product starts and all forbidden mutations
  remained 0. The first audit is retained at 29/30; its C1 audit passed 24/24.
- **PB.1 C2 attempt-03 retained failure:** exact v0.7 authorization and preflight
  passed. The checkout-before-symlink correction worked: all 6,669 engine LFS paths,
  full history, corrected metric, license inventory and dependency identity passed.
  The single clean build stopped after 47.20 seconds because the fresh dependency
  clone left all 622 dependency LFS paths as pointers; the linker rejected the
  131-byte `libzstd.a` pointer. No product start/render or forbidden mutation occurred.
  Independent failure audit passed 36/36. Attempt-03 is immutable; the next fresh
  correction is limited to zero-network dependency-LFS materialization.
- **PB.1 C3 attempt-04 retained failure:** the dependency correction and clean
  arm64 build passed, including a 602.91-second build and exact product identity.
  The two zero-render starts failed only configuration isolation because macOS
  ignored the process `HOME` override and used the real FilmStudioEngineF0 root.
  Independent failure audit passed 39/39. C4 may reuse this build with explicit
  Blender user paths; it must not rebuild or modify attempt-04.
- **PB.1 validation-only accepted:** C4 reused the exact attempt-04 binary and
  performed two fresh zero-render starts with all four `BLENDER_USER_*` paths
  explicitly isolated. Product identity, saved preferences, official config and
  the real FilmStudioEngineF0 config were exact/unchanged. Verdict is `PASS`;
  the accepted C1 audit is 15/15. PB.2–PB.7 remain unauthorized.
- **PB.2 readiness-only accepted:** the inherited F0.4 B01/B02 typed proposals,
  exact approvals, four pre-mutation controls and current clean `film-engine`
  contract source were cross-bound without executing a proposal or starting
  Blender. Attempt-01 is retained at `FAIL 16/19` for three audit-contract
  errors. C1 corrected those errors in a new version and passed 14/14, producing
  combined readiness 19/19. Blender starts, BuildPlan writes, engine/remote
  mutations and network calls were all 0. This readiness result is not the
  formal PB.2 verdict.
- **PB.2 base formal tools retained:** v0.3 froze a system-Python runner,
  an auditor that does not import the product contract module, exact B01/B02
  inputs, eight negative cases, fresh roots and zero Blender/write ceilings.
  Static attempt-01 is retained at `FAIL 27/28` for a filename/import false
  positive; C1 passed 10/10 and makes combined tool readiness 28/28. At this
  base-freeze checkpoint no runner, proposal or Blender process was started.
- **PB.2 execution template ready, non-executable:** the v0.4 template binds the
  frozen commit, tools, paths, cases and future argv, while authorization fields
  and `researchCommit` remain null. Static preflight passed 23/23 without
  invoking the runner. The template cannot be used as the execution contract;
  explicit PB.2 authority must be copied into a new committed file.
- **PB.2 execution authorized; C1 identity correction ready:** the user approved
  the linked validation-only scope. The template's self-referential commit field
  was impossible to construct, so v0.5 preserves all scope and instead verifies
  execution parent, current HEAD and exact committed contract bytes. Static C1
  tool audit passes 16/16 after retaining one 15/16 audit-harness failure. The
  formal roots remain absent pending the committed execution contract.
- **PB.2 C2 tool correction accepted:** C1 still placed current HEAD inside the
  contract body. C2 removes that last self-reference; current HEAD is derived
  and written only to the receipt, then independently re-audited through Git.
  Static C2 tool audit passed 17/17. The v0.4/v0.5 execution shapes are retained
  as non-executable protocol failures.
- **PB.2 validation-only PASS:** the exact user
  approval is bound in
  `specs/ai-native-studio-pb2-validation-only-execution-c2.v0.6.json` together
  with the C2 tools, parent commit, unique attempt-01 roots, two positive
  inspections, eight negative controls and zero Blender/render/write/network
  ceilings. Its file SHA-256 is `25aa2519c...`; execution commit is
  `7237f8b9...`. Attempt-01 passed both positive inspections and all eight
  negative controls; receipt self hash is `ffb845af...`, and the independent
  audit passed 19/19 with self hash `0a57ccf7...`. Blender, render, proposal
  execution, BuildPlan write, scene mutation, network and engine-write counts
  were all zero. The one-run authorization is consumed; PB.3–PB.7 remain
  unauthorized.
- **PB.3 readiness preregistered, formal execution unauthorized:** the read-only
  v0.1 inventory binds the PB.1 accepted binary/source, PB.2 PASS, F0.3
  workspace persistence/Expert Mode and F0.4 exact B01/B02 plan/semantic
  evidence. Current source contains both the contract bridge and typed
  workspace, but there is no accepted same-run combined proof. Formal roots and
  every Blender/compile/write/render/network/engine-mutation count remain zero.
- **PB.3 formal tools frozen, still inert:** v0.2 fixes the combined B01/B02
  compile → semantic scene → typed workspace save → reopen/Expert-state oracle.
  A future exact run is capped at four zero-render Blender starts and two
  proposal/BuildPlan writes. Static audit passed 28/28; the non-authorized v0.3
  template was rejected before root creation. C1 v0.3 then closes a completion-
  audit finding by enforcing exclusive logs, rejecting symlinks and independently
  recomputing the unchanged 2 GiB / 64 MiB root ceilings. C1 static audit passed
  25/25; its v0.4 template is also inert. The superseding exact authorization
  request was then replaced by C2 after a second completion audit. C2 binds the
  exact authorization text/hash, a single-path execution commit, authorized
  roots, four exact argv, eight process logs and two root manifests. Its static
  audit passed 29/29; the active request is
  `specs/ai-native-studio-pb3-validation-only-authorization-request-c2.v0.4.json`.
  That request was approved and consumed by attempt-01, which stopped before
  any Blender start because v0.2 contains one SceneSpec SHA transcription
  error. The 13-input audit found 12 exact and one mismatch; independent
  retained-failure audit passed 24/24. Attempt-01 roots are immutable. Active
  C3 permits only a versioned correction of `commonInputs[0].sha256`. The
  corrected v0.8 tool differs from v0.2 at exactly that one JSON leaf; the
  consolidated C3 runner/auditor, inert attempt-02 template and exact request
  were frozen. Static audit passed 32/32 before execution. The exact request was
  approved and consumed by attempt-02. Its four zero-render Blender starts and
  B01/B02 semantic/workspace operations completed, but the run is retained
  `FAIL`: base audit 17/18 found two automatic isolated-HOME thumbnail PNGs;
  C3 audit 21/23 also found relative-versus-absolute `--tool-contract` argv
  spelling. C4 corrected those two harness defects and passed static 32/32, but
  its approved attempt-03 stopped before root creation because the execution
  contract added one token to the frozen `stillUnauthorized` array. One
  disclosed read-only remote admission query also exceeded the zero-network
  ceiling. Attempt-03 failure audit passed 22/22. C5 then froze exact-array,
  retained-attempt and real receipt-field binding. Its first static attempt is
  retained at 29/30 for callback arity; the versioned C2 runner changes one
  signature line and now passes static/negative audit 30/30. The former request
  is `specs/ai-native-studio-pb3-validation-only-authorization-request-c5-c2.v1.10.json`.
  It remains historical. The versioned C6 standing-authority adapter now passes
  static/negative audit 32/32 without claiming the historical exact sentence.
  Its single-path attempt-04 contract passed outer standing-authority checks but
  the nested base runner retained a second historical status check and stopped
  before root creation or Blender start. Attempt-04 is now an immutable 19/19-
  audited harness failure. C6-C1 adapts only that nested authority function; its
  first static run is retained 31/32 for an obsolete C5 freshness self-test.
  C6-C2 directly verifies the retained attempt and passes 32/32. Attempt-05
  completed all semantic processes but retained two HOME thumbnails and failed
  the unchanged work-root artifact gate. C6-C3 moves only HOME into bounded,
  resource-accounted evidence storage and passes static 32/32. Attempt-06 is the
  accepted PB.3 `PASS`: base audit 18/18 and C6 audit 29/29, with all four
  semantic processes exact and zero work-root render-like artifacts.
- **PB.4 product render/receipts PASS:** the three-path / 382-line product
  increment built cleanly as arm64 commit `df5c2967…`. Attempt-01 passed the
  visible Render Job inspection and persisted typed status, rejected all three
  negative controls before rendering, then produced one 640×360 EEVEE PNG
  (`bcdaf54d…`) and one CPU Cycles multilayer EXR (`93955cfb…`) with exactly two
  render calls. The independent OpenImageIO audit passed every source, process,
  pixel, pass and failure check. Its final Node wrapper remains a retained
  `FAIL` only because Python `0.0` and Node `0` canonical number spellings
  produced different audit hashes. C1 attempt-02 performed no build, Blender
  start or render and independently closed that verifier defect at 25/25 PASS;
  composite receipt hash is `687f2759…`. Both roots are immutable.
- **PB.5 restart-safe job control PASS:** the three-path / 274-addition product
  increment built cleanly as native arm64 commit `373881e1…`. Four starts proved
  PREVIEW + exit-75 interruption, FINAL-only resume, COMPLETE no-op, and three
  zero-render stale/forged/out-of-budget rejections. Exactly two render calls
  produced immutable PNG `90d2cf9e…` and EXR `947d2217…`; the 13/13 validation
  receipt self hash is `1baa24ee…` and the independent audit self hash is
  `a18a32c3…`. The unexecuted v0.2 stale-self-hash manifest is retained; v0.3
  is the accepted corrected binding. The validated commit was then published
  to `lovejzzz/film-engine/main` by one ordinary non-force fast-forward.
- **PB.6 B62 three-shot vertical slice PASS:** the three-path / 345-addition
  product increment built as native arm64 commit `aa4fff39…`. The visible
  product workflow produced a fresh WIDE/MEDIUM/CLOSE 96/96/96-frame EEVEE
  review slice, a 640×360/24 fps/288-frame MP4 and contact sheet. Validation is
  9/9 and independent audit 15/15 with receipt/audit hashes `f8e1cc9d…` /
  `2f7b08ee…`. Five attacks rejected with zero render calls. The historical
  frame-288 `0.93378717684983 > 0.90` rejection remains exact; human review is
  intentionally pending until PB.7. PB.7's four questions, allowed answers,
  delayed-disclosure ordering and verdict mapping are now preregistered before
  any human response. Its strict recorder and independent auditor are also
  frozen, with 20/20 static checks and a final 27/27 isolated synthetic audit.
  C1 corrects only the v0.1 independent-audit self-hash field semantics; no
  question, value or verdict mapping changed. PB.7 is now accepted `PASS` from
  exact owner answers `YES YES YES YES` and a 27/27 independent audit. Owner
  feedback preserves the strengths (lighting/camera) and identifies the next
  improvement priorities (modeling detail/action complexity). The validated two-commit increment was
  published to `lovejzzz/film-engine/main` by one ordinary non-force fast-forward.
- **RC4 solver-owned realism PASS and published:** the current public product
  head is `db662438…`. A clean native build proved a metric basketball/three-
  filled-bottle Bullet collision, exact derived contact and settled-response
  cinematography, zero post-release pose authority, exact save/reopen, 12/12
  machine checks, 10/10 direct visual review and a 20/20 independent audit.
  This closes the earlier RC3 visual/formal gap and productizes a reusable
  procedural physical look; it does not prove fluid, fracture, deformation,
  sound or arbitrary photoreal filmmaking.
- **Closed gates:** `F0.1 PASS`, `F0.2 PASS`, `F0.3 PASS`, `F0.4 PASS`, `F0.5 PASS`,
  `F0.6 PASS` and `F0.7 PASS`. Two clean official builds reported Blender
  5.2.0 and the pinned source hash. The bundles are semantically identical but
  not byte-for-byte reproducible; the bounded differences are recorded in
  `F0.1-2026-08-29-mac-m2max-attempt-07/comparison.json`.
- **Independent identity:** the 13-path / 110-line identity patch builds as
  `Film Studio Engine F0`, uses `studio.ainativefilm.f0`, and resolves user
  state under `FilmStudioEngineF0`. Save, reset and GUI launch left the
  official Blender configuration root absent; the accepted receipt is in
  `F0.2-2026-08-29-mac-m2max-attempt-02/verdict.json`.
- **Minimum film workspace:** the 3-path / 190-line F0.3 patch adds versioned
  typed Project / Scene / Shot / Character RNA state, a one-click SH010 Camera
  task, persistent `.blend` state and a lossless Expert Mode round-trip. The
  frozen UI task required 1 interaction versus 24 in official Blender; the
  accepted receipt is in
  `F0.3-2026-08-30-mac-m2max-attempt-01/verdict.json`.
- **Retained F0.4 attempt-01:** attempt-01 proved canonical-exact embedded B01/B02
  BuildPlans, approval ordering and four pre-mutation rejections, then failed
  formal product start 3 because `ocio.GetCurrentConfig().getName()` returned
  an empty string instead of the frozen ACES 2 config name. B02 and the fifth
  product audit were not run. The self-hashed verdict is in
  `F0.4-2026-08-30-mac-m2max-attempt-01/verdict.json`; same-ID repair is forbidden.
- **Retained F0.4 attempt-02:** the preregistered ACES 2 `OCIO` launch binding
  was exact and B01 built successfully with the frozen planHash. Its full
  structure SHA was `6084df51…`, not frozen `c699fc27…`; the sole JSON
  difference was `$.blender.buildHash` (`b47eae224b6d` versus official
  `fbe6228777e7`). Removing that provenance field made both semantic structures
  byte-exact at `0bb1caf9…`. The stop rule skipped B02 and the product audit;
  verdict self hash is `279028206e81c40ffede744313f6b40f4d97fe03d6b5d4a5d40bd0e6867651cb`.
- **Accepted F0.4 attempt-03:** manifest v0.3 keeps exact product provenance in
  `execution.blender` and hashes semantic scene structure independently. B01
  and B02 built in isolated roots at semantic hashes `e8c55fb7…` and
  `d197b024…`; both retained exact product build `b47eae224b6d`. An independent
  product process reopened both `.blend` files, cross-bound attempts 01/02 and
  passed four identity-separation attacks. Verdict self hash is
  `f2888a3b4c89df3370c13fbf28097ecb4d83a3f11f325588a12321d27f7666a3`.
- **Retained F0.5 attempt-01:** the insufficient-disk control rejected with zero
  product starts, then the first admitted preview exited before any render call
  because the harness selected PNG while the source still had
  `media_type=MULTI_LAYER_IMAGE`. No render artifact was written and the stop
  rule skipped every later stage. Verdict self hash is
  `e36afca30fc3567368ae72466c682a32ab54723300b2aa063667382b5b06c617`.
- **Accepted F0.5 attempt-02:** the preregistered correction set the preview and
  final media types explicitly without changing profiles or thresholds. Four
  admitted product starts produced one EEVEE PNG, one controlled pre-render
  SIGTERM, one recovered Cycles multilayer EXR and one zero-render independent
  audit. Expected/observed render calls were exact at 2, the preview was not
  rerendered, Combined/Depth/Normal decoded successfully, and both unsafe
  admission controls rejected before an additional product start. Verdict self
  hash is `a85a2d64bb080b89051986ad83b6489317909a6f0b7ad75b5c194a252a375e71`.
- **Retained F0.6 attempts 01/02:** the merge and native build passed in both
  cases, but attempt-01 bound the F0.4 approval to the wrong evidence root and
  attempt-02 used insertion-order-sensitive JSON comparison for exact
  provenance. Their failures remain immutable as `F04_EVIDENCE_ROOT_BINDING`
  and `F04_PROVENANCE_OBJECT_KEY_ORDER`; neither was repaired in place.
- **Accepted F0.6 attempt-03:** the frozen `v5.2.1` merge completed with 0 manual
  conflict paths, 0 person-hours and 909 non-generated fork-owned changed lines,
  below ceilings of 10, 8 hours and 5000 lines. The native arm64 product reports
  build `fa1b578bb421`; an order-insensitive exact provenance audit cross-bound
  all ten prior F0.1–F0.4 processes, and the unchanged product then passed the
  full four-start F0.5 corpus. Verdict self hash is
  `e67b9b942f772b9aef096c4b5cd988dfac7be2e1a3bfec7ad5a28a51111693d3`.
- **Retained F0.7 attempts 01–04:** attempt-01 timed out while creating the DMG;
  attempt-02 exposed a pre-save depsgraph snapshot defect and official-config
  empty-directory drift; attempts 03/04 completed both round trips but failed
  closed while assembling the final install receipt because of two distinct
  undefined variable names. Every root and self-hashed verdict remains public.
- **Accepted F0.7 attempt-05:** the retained 341,069,106-byte unsigned DMG has
  SHA-256 `20a8aefd…`; `hdiutil verify` and its read-only mounted payload passed.
  Six product starts preserved core scene semantics at `139852cf…`; typed F0
  metadata was preserved exactly and absent optional metadata degraded
  gracefully. The exact generated install target was removed, official Blender
  and both configuration namespaces remained unchanged, and an independent
  103-check audit passed. Verdict self hash is
  `626ea953fefd6fb1b8c3044248c653c7ce0cbc18a69a2e8eff5bb37e78a2d94a`.
- **Inherited evidence:** B01-B62 cover structured scene compilation, Blender
  execution, safety/admission, pixels, production passes, cost, recovery and a
  three-shot cinematic attempt. These results are evidence, not a claim that
  autonomous filmmaking is solved.
- **Most important retained rejection:** B62's latest camera holdout passed all
  technical gates but failed the frozen composition threshold at frame 288.
  Source control does not replace direction or taste.
- **Still unproven:** Developer ID signing, notarization, Gatekeeper acceptance,
  public distribution, production support, cross-version/platform
  generalization and legal sufficiency. F0.7 made no such claim.

## Read in this order

1. [`AGENTS.md`](./AGENTS.md) — binding operating and safety rules.
2. [`handoff/ai-native-studio-current-state.v0.1.json`](./handoff/ai-native-studio-current-state.v0.1.json)
   — compact state for an agent or script.
3. [`research/2026-08-29-ai-native-film-studio-design-v0.1.zh-CN.md`](./research/2026-08-29-ai-native-film-studio-design-v0.1.zh-CN.md)
   — full product and architecture decision.
4. [`research/2026-08-29-ai-native-film-studio-f0-source-feasibility-protocol-v0.1.zh-CN.md`](./research/2026-08-29-ai-native-film-studio-f0-source-feasibility-protocol-v0.1.zh-CN.md)
   — preregistered F0 method and stop rules.
5. [`specs/ai-native-studio-f0.v0.1.json`](./specs/ai-native-studio-f0.v0.1.json)
   — machine-readable gates and acceptance criteria.
6. [`app/ai-native-studio-design/page.tsx`](./app/ai-native-studio-design/page.tsx)
   and [`app/ai-native-studio-handoff/page.tsx`](./app/ai-native-studio-handoff/page.tsx)
   — public explanation and live handoff dashboard.
7. [`research/2026-08-30-ai-native-film-studio-post-f0-repository-phase-b-charter-v0.1.zh-CN.md`](./research/2026-08-30-ai-native-film-studio-post-f0-repository-phase-b-charter-v0.1.zh-CN.md)
   and [`specs/ai-native-studio-post-f0-phase-b.v0.1.json`](./specs/ai-native-studio-post-f0-phase-b.v0.1.json)
   — frozen permanent-repository boundary and PB.1–PB.7 contract.
8. [`research/2026-08-30-post-f0-repository-readiness-protocol-v0.1.zh-CN.md`](./research/2026-08-30-post-f0-repository-readiness-protocol-v0.1.zh-CN.md),
   [`research/2026-08-30-post-f0-repository-readiness-c2-bundle-argv.md`](./research/2026-08-30-post-f0-repository-readiness-c2-bundle-argv.md)
   and [`specs/ai-native-studio-repository-readiness.v0.3.json`](./specs/ai-native-studio-repository-readiness.v0.3.json)
   — public-fork/private-mirror topology, retained corrections, no-write gates
   and the exact authorization sentence.
9. [`experiments/ai-native-studio-post-f0/repository-readiness-2026-08-30-mac-m2max-attempt-03/verdict.json`](./experiments/ai-native-studio-post-f0/repository-readiness-2026-08-30-mac-m2max-attempt-03/verdict.json)
   and [`audit.json`](./experiments/ai-native-studio-post-f0/repository-readiness-2026-08-30-mac-m2max-attempt-03/audit.json)
   — accepted local full-history rehearsal and independent 93-check audit.
10. [`research/2026-08-30-film-studio-engine-public-fork-authorization-request-v0.1.zh-CN.md`](./research/2026-08-30-film-studio-engine-public-fork-authorization-request-v0.1.zh-CN.md)
    and [`specs/ai-native-studio-repository-authorization-request.v0.1.json`](./specs/ai-native-studio-repository-authorization-request.v0.1.json)
    — exact public-fork, two-object LFS, billing and fresh-main lease request.
11. [`research/2026-08-30-film-engine-public-fork-c1-github-lfs-policy.md`](./research/2026-08-30-film-engine-public-fork-c1-github-lfs-policy.md),
    [`specs/ai-native-studio-repository-publication-c1.v0.3.json`](./specs/ai-native-studio-repository-publication-c1.v0.3.json)
    and [`audit-failure.json`](./experiments/ai-native-studio-post-f0/repository-publication-2026-08-30-mac-m2max-attempt-01/audit-failure.json)
    — retained GitHub public-fork LFS policy failure, 33/33 audit and the
    original minimal ordinary-blob correction.
12. [`research/2026-08-30-film-engine-publication-c1-pass.md`](./research/2026-08-30-film-engine-publication-c1-pass.md),
    [`specs/ai-native-studio-repository-publication-c1-execution.v0.4.json`](./specs/ai-native-studio-repository-publication-c1-execution.v0.4.json),
    [`verdict.json`](./experiments/ai-native-studio-post-f0/repository-publication-c1-2026-08-30-mac-m2max-attempt-01/verdict.json)
    and [`audit.json`](./experiments/ai-native-studio-post-f0/repository-publication-c1-2026-08-30-mac-m2max-attempt-01/audit.json)
    — accepted C1 publication, exact one-ref update and independent 59/59 audit.
13. [`research/2026-08-30-ai-native-studio-pb1-validation-only-authorization-request-v0.2.zh-CN.md`](./research/2026-08-30-ai-native-studio-pb1-validation-only-authorization-request-v0.2.zh-CN.md)
    and [`specs/ai-native-studio-pb1-validation-only-authorization-request.v0.2.json`](./specs/ai-native-studio-pb1-validation-only-authorization-request.v0.2.json)
    — exact authorization boundary for a no-source-edit/no-engine-write PB.1
    history, identity, license and clean-build validation.
14. [`research/2026-08-31-ai-native-studio-pb1-attempt-01-retained-failure.md`](./research/2026-08-31-ai-native-studio-pb1-attempt-01-retained-failure.md),
    [`verdict.json`](./experiments/ai-native-studio-phase-b/PB.1-2026-08-30-mac-m2max-attempt-01/verdict.json)
    and [`audit-failure-c1.json`](./experiments/ai-native-studio-phase-b/PB.1-2026-08-30-mac-m2max-attempt-01/audit-failure-c1.json)
    — retained pre-build metric failure, retained first auditor failure and accepted
    29/29 failure audit.
15. [`research/2026-08-31-ai-native-studio-pb1-attempt-02-retained-failure.md`](./research/2026-08-31-ai-native-studio-pb1-attempt-02-retained-failure.md),
    [`verdict.json`](./experiments/ai-native-studio-phase-b/PB.1-2026-08-31-mac-m2max-attempt-02/verdict.json)
    and [`audit-failure-c1.json`](./experiments/ai-native-studio-phase-b/PB.1-2026-08-31-mac-m2max-attempt-02/audit-failure-c1.json)
    — retained pre-materialization ordering failure and accepted 24/24 failure audit.
16. [`research/2026-08-31-ai-native-studio-pb1-attempt-03-retained-failure.md`](./research/2026-08-31-ai-native-studio-pb1-attempt-03-retained-failure.md),
    [`verdict.json`](./experiments/ai-native-studio-phase-b/PB.1-2026-08-31-mac-m2max-attempt-03/verdict.json)
    and [`audit-failure.json`](./experiments/ai-native-studio-phase-b/PB.1-2026-08-31-mac-m2max-attempt-03/audit-failure.json)
    — retained dependency-LFS materialization failure and accepted 36/36 failure audit.
17. [`research/2026-08-31-ai-native-studio-pb1-validation-only-c3-tool-freeze-v0.9.md`](./research/2026-08-31-ai-native-studio-pb1-validation-only-c3-tool-freeze-v0.9.md)
    and [`specs/ai-native-studio-pb1-validation-only-c3-execution.v0.9.json`](./specs/ai-native-studio-pb1-validation-only-c3-execution.v0.9.json)
    — standing-authorized fresh attempt-04 contract and dependency-LFS-only correction.

Use `research/`, `specs/`, `scripts/`, `experiments/` and `app/` as the map.
Historical experiments are intentionally numerous; search by the B-number or
contract name instead of reading everything.

## First 30 minutes on a new Mac

1. Confirm the checkout and preserve any existing changes:

   ```sh
   git status --short
   git remote -v
   git log -1 --oneline
   ```

2. Run the read-only host admission check:

   ```sh
   node scripts/preflight-f0-source-host.mjs
   ```

   It writes nothing. `F0_HOST_PREFLIGHT_ACCEPTED` means the host has the basic
   toolchain and at least 100 GiB reserve plus a 60 GiB projected source/build
   budget. A rejection is evidence; fix or document it before cloning Blender.

3. Choose an absolute workspace outside this repository. Preview the source
   acquisition plan, then explicitly execute it:

   ```sh
   scripts/bootstrap-f0-blender-source.sh --workspace /absolute/path/to/f0-workspace
   scripts/bootstrap-f0-blender-source.sh --workspace /absolute/path/to/f0-workspace --execute
   ```

   Add `--with-dependencies` only after reviewing the plan and disk budget. The
   script refuses non-empty targets, checks out the exact commit detached, and
   verifies that dependency acquisition did not move the source revision.

4. Create a new immutable evidence root under
   `experiments/ai-native-studio-f0/`. Copy the protocol identifiers and record
   the preflight output before the first build mutation. Never reuse or replace
   another machine's root.

5. F0.1-F0.7 and the no-external-write repository rehearsal are closed. Verify
   F0.7 attempt-05, repository-readiness attempt-03, and repository-publication
   attempt-01 failure/audit. Do not mutate retained DMG, evidence, failures or
   frozen contracts. Do not push the shallow F0 checkout as full history. The
   public fork C1 publication is closed as PASS. Do not infer Phase B authority
   from that result.

## What not to do

- Do not restart B62 or create a new rendering side quest as the main task.
- Do not clone Blender inside this repository or commit build products.
- Do not retry LFS, update another remote ref, delete/recreate/rename the
  existing `lovejzzz/film-engine` fork, or create a replacement repository.
- Do not create a release, sign/notarize/distribute a DMG or begin Phase B
  without a new explicit authorization and versioned protocol.
- Do not copy Bforartists as a second upstream; inspect it as a reference.
- Do not give a model unrestricted `bpy`, shell or filesystem authority.
- Do not hide failed builds, relax thresholds after seeing results, or overwrite
  receipts.
- Do not use in-app browser automation while the crash guard in `AGENTS.md` is
  active.
- Do not stage unrelated worktree changes; this repository may contain the
  owner's unpublished files.

## Definition of a useful next checkpoint

PB.2 validation-only is closed `PASS`; PB.3 attempt-01, attempt-02 and
attempt-03 are retained harness failures. Attempt-02 completed all four zero-
render semantic processes; attempt-03 stopped before creating a work root or
starting Blender. C5-C2 passes 30/30 static checks and the C6 standing-authority
adapter passes 32/32 while keeping the C4 semantic/helper corrections, exact
no-render-artifact threshold, retained attempts and zero-network ceiling
frozen. Attempt-04 then stopped pre-root at a nested historical authority check.
PB.3, PB.4, PB.5 and PB.6 are closed `PASS`; PB.6 is the accepted B62
three-shot product slice with human review still pending. Do not repair or rerun
any retained root. PB.7 is closed `PASS`: exact owner answers are
`YES YES YES YES`, human receipt self hash is `0d806411…`, and the independent
audit is 27/27 with self hash `e02c1dc4…`. PB.1–PB.7 now close this bounded
product-prototype phase. The next checkpoint is a versioned improvement program
for the two weaknesses named by the owner—modeling detail and action
complexity—without expanding the result into a production-readiness or
autonomous-filmmaking claim. That program is now preregistered; the immediate
gate PC.0 is closed `PASS`. Attempt-01 remains a retained zero-start harness
failure with failure/manifest self hashes `7ccd6388…` / `1f77c2ff…`. C1
attempt-02 used one zero-render, zero-save start and passed an independent 27/27
audit (`ece09ea4…`); receipt and manifest self hashes are `c2a979f5…` and
`b33e720f…`. It measured 78 objects, 66 meshes, 15,734 polygons, 12 materials,
0 modifiers, 12 actions and 9 animated object targets while preserving the
source SHA exactly. PC.1 is now preregistered with 26 semantic details, three
new material regions and frames 48/144/240 A/B checks. Its exact builder,
reopen semantic/pixel auditor, runner and final auditor are frozen against the
one-leaf EEVEE C1 correction with self hash `e7e86dc2…`. Attempt-01 then
stopped before its first render because the product output contract permits
only internal multilayer EXR, not direct PNG; it used 1 start, 0 render and 0
save, and remains sealed (`dcd59081…` / `ffec4a49…`). The immediate checkpoint
C2 attempt-02 completed the product increment and all three visible-view floors,
but final audit rejected a Python `1.0` versus Node `1` canonicalization mismatch;
it remains sealed (`7722b9de…` / `f1d44dc4…`). C3 normalized integer-valued
floats and reproduced the same accepted product metrics, but attempt-03 remained
FAIL because Python `8e-08` and Node `8e-8` spell the same finite number
differently; it is sealed (`f65073be…` / `562ffd0c…`). C4 changed only final
Node self-hash verification. Fresh attempt-04 is now accepted `PASS`: 26 exact
details, three material regions and all three visible-view floors passed while
camera/light sentinels, actions and source SHA remained exact. Receipt/audit/
manifest self hashes are `2a60c050…` / `69cca7c8…` / `ce2279e1…`. PC.1 is
closed; PC.2 action complexity is the active gate. Its v0.1 preregistration is
frozen at `48bdfa56…`: four causal phases, four independent channels and ten
authorized non-camera targets, with at least six required to animate. PC.1
geometry/materials and all protected camera/light states remain exact; tools
are frozen at `83e0ba88…` before the first zero-render PC.2 start. Fresh
attempt-01 stopped before action mutation on another Node/Python number-spelling
hash mismatch and is sealed (`01b43e04…` / `4bb70807…`). C1 binds accepted
PC.1 `build.json` and compares the same camera/light state structurally; it is
frozen at `26d100c4…`. Fresh C1 attempt-02 is accepted `PASS`: four phases,
four channels and ten non-camera signal targets passed 19/19 after reopen;
exactly six PC.1 detail objects gained animation. Receipt/audit/manifest self
hashes are `f99fc297…` / `b68b6600…` / `15aeacec…`. Geometry/materials,
camera/lights and shot markers remained exact. PC.2 is closed; PC.3 integrated
video and delayed visual comparison is the active gate. PC.3 preregistration
and exact render/video/audit tools are frozen at `4a7a1f84…` / `d9cce851…`;
fresh attempt-01 is now `MACHINE_PASS_HUMAN_PENDING`. All 288 frame hashes are
unique, 287/287 consecutive pairs are dynamic, all 288 frames visibly differ
from A, and median RGB MAD is 0.019747. Receipt/audit/manifest self hashes are
`0eff3b11…` / `be0e1366…` / `94f6280d…`; integrated video SHA is `8c6afc36…`.
The four owner A/B questions are now open; the model must not answer them. The
strict response recorder and independent auditor are frozen before any answer
at self hash `1846f9a2…`; their 23/23 static tests pass and the unique formal
human-review root remains absent. The owner then explicitly expanded the active
goal to require screenshot-led model visual judgment. Direct inspection rejected
PC.3 B as an insufficient visual upgrade: it preserves the strong lighting and
shot language but still reads as a sphere/box/cylinder hero with attached detail
and weak performance. PC.4 is now preregistered at `09ba0c5b…` and its exact
53-part hero-shell, five-phase performance, three-frame builder/auditor/runner
are frozen at `61ff2d8c…` before mutation. PC.3 human evidence remains pending
and must not be fabricated; PC.4 is a separate model-guided corrective iteration.
PC.4 attempt-01 retained the complete derivative plus first EXR but failed before
any review PNG because the binary exposes display device `sRGB`, not the frozen
`sRGB - Display`. C1 changes that one literal only and is frozen at `f5b013f8…`
against fresh attempt-02 roots. C2 then bound the admitted `ACES 2.0` name and
attempt-03 produced all three screenshots. Its Python build self hash is valid,
but the runner stopped on Node/Python number spelling before reopen. More
importantly, direct screenshot review rejects the product result: actual chamber
ring/column occlusion remains, spherical shoulder/elbow volumes dominate medium,
and the close helmet still lacks sufficient layered structure. Attempt-03 is a
retained visual `FAIL` at failure self hash `e3de738f…`; the next iteration must
change those visible design causes, not merely repair the auditor. The workflow
has therefore been promoted from one-off scene patches to the reusable PC4-VU1
visual-understanding loop. Its strict VisualReviewPacket, VisualAssessment and
VisualImprovementPlan contracts compile screenshot evidence into six bounded
semantic operations while preserving accepted lighting/camera strengths and
carrying no Python, shell, network or arbitrary-filesystem authority. Formal
attempt-03 passes 19/19 contract tests and an independent 20/20 audit; plan hash
is `674bc082…`, receipt/audit self hashes are `b72a6354…` / `eb853d06…`.
PC4-VU1 proves the understanding-to-plan boundary, not a new visual result. The
first typed executor has now been run and directly rejected: it consumed all six
operations and passed its machine audit, but part-count and layer floors produced
floating rectangular clutter. Visual Film Language v0.2 replaces those floors
with screen-space occlusion, negative-space, occupancy, contour-relief, detail-
density, scale-band and facial-landmark constraints. Its 5-operation plan passes
8/8 tests and a 12/12 audit. PC4-VX2 attempt-01 shows real local improvement in
wide/medium readability, but is retained `FAIL`: direct review found environment
over-removal, medium occupancy `0.35712820 < 0.48`, and an unreadable close face.
It also exposed a machine false positive because audit A14 omitted the occupancy
lower bound. The active next step is a versioned correction that first closes
that false-positive and then teaches pixel-visible occlusion and target-view
landmark visibility; do not hand-place another project-specific patch.

The owner then identified a more fundamental curriculum problem: the robot
mixes modeling, performance, occlusion, lighting and cinematography so tightly
that failures are difficult to attribute. PC4 is retained as the future
capstone/holdout, not discarded. The active curriculum moved to
`PC5-CAUSAL-STUDIO`: one procedural sports ball, three procedural bottles and
an actual Blender/Bullet rigid-body collision told as SETUP / IMPACT /
AFTERMATH. Attempts 01–03 are retained pre-scene harness/API failures. Attempt-04
proved exact reopen-reproducible physics (responses 28/29/29; all final tilts
about 89.6°) but remained machine 19/20 and direct visual `FAIL`: fixed-space
AFTERMATH missed every bottle. C4 taught evaluated-frame semantic bounds,
measured occupancy/margin and cross-language numeric evidence. Fresh attempt-05
is the accepted controlled lesson: independent machine audit `21/21 PASS`, six
of six direct screenshot questions `YES`, receipt/audit/review self hashes
`9b72e2df…` / `33a9567c…` / `542874f0…`. The holdout was frozen before the
generic executor existed, then changed the target factory/count/collision shape
to four beveled wooden domino blocks with BOX collisions. Fresh PC5-G1
attempt-01 passed independent machine audit `23/23` and direct screenshot review
`6/6`; its receipt/audit/review hashes are `82374709…` / `e0ab4244…` /
`d7c3bd83…`. All four targets responded at frames 28/31/31/30 and settled at
56.97°/90.00°/90.00°/90.00° with zero target or final-pose keyframes; reopen was
exact. This proves one controlled unseen transfer, not broad general filmmaking.
PC6 has now productized that lesson in source commit `5f3b981a…`: the actual
Film Studio top bar exposes inspect/build actions backed by a strict
CausalSceneSpec allowlist. A clean native build then rejected all nine authority
attacks, built the frozen four-domino scene through Blender/Bullet, rendered
three evaluated-result views and reopened with exact response frames and 0.0°
tilt deltas. The corrected independent audits passed `21/21` and `11/11`;
acceptance self hash is `cd334acd…`. Direct inspection deliberately separates
capability from quality: the physical result is solver-owned, never posed, but
the first-response impact still is not the strongest propagation frame and the
manufactured-toy result lacks motion blur, contact deformation and secondary
motion. PC6 therefore passes product capability, not filmic realism. The active
PC7 checkpoint must improve evaluated motion timing and physical richness while
keeping final target/post-release transforms exclusively solver-owned; the PC4
robot remains a later capstone holdout.
PC7 is now accepted. Its frozen five-domino v0.2 fixture selects impact from
evaluated propagated angular motion, selects aftermath with an eight-frame
settle rule, and permits only bounded SHA-256-derived initial-condition
variation. The one-path product commit `c7eece67…` (116 additions / 15
deletions) passed a clean native build, 12 authority attacks, three product
starts, three still renders, a bound 24-frame impact clip and exact save/reopen.
Independent audit passed `27/27`; receipt/audit/direct-review/acceptance self
hashes are `403e2c91…` / `91789976…` / `c1654213…` / `39ebb081…`. All five
targets respond at frames 28/29/29/30/31. Frame 38 is the measured motion peak
with all five targets active and `30.55164633°` aggregate angular step; frame 86
is the first accepted settled window. Final target and post-release actor pose
keys remain zero, while solver-owned final tilts vary from 62.32° to 90.00°.
Direct inspection accepts visible continuous propagation and an unstaged
aftermath, but not photoreal film quality. PC8 must preserve this exact primary
Bullet solve while adding shutter-visible motion, contact and bounded secondary
physical realism; effects may not conceal weak motion or author final poses.
The validated source commit was subsequently published to
`lovejzzz/film-engine/main` by one ordinary non-force fast-forward from
`aa4fff39…` to `5f3b981a…`; a public raw-file check matched the local causal
module exactly. No tag, release, binary, LFS, signing or notarization operation
occurred.
The accepted PC7 increment was then published by a second ordinary non-force
fast-forward from `5f3b981a…` to `c7eece67…`. Public `main` and the raw causal
module match the validated source exactly; publication receipt self hash is
`a53f2016…`. Again, no tag, release, binary, LFS, signing or notarization
operation occurred.
PC8 measured shutter is preregistered at `834ff258…` with v0.3 fixture
`690c35c3…`. It must preserve every accepted PC7 initial condition, response,
motion-selection and final-tilt value. The only new product authority is to
measure actor/target projected displacement through the fitted IMPACT camera,
reduce it to median pixels per frame, and compute a bounded native Blender
shutter for a declared 6 px target. A sharp/blurred A/B, three product stills
and the 24-frame clip require direct inspection. Manual shutter lookup,
compositor/postprocess blur, weaker primary physics and final-pose authoring are
forbidden.
Development then invalidated that first design before any formal root existed:
adding cinematography changed the document self hash and therefore silently
resampled the hash-derived physical initial conditions. C1 `8110fdbb…` retains
v0.1/v0.3 unchanged and freezes corrected v0.4 fixture `3d97a1b8…`.
`basisSceneSpecHash=b1bcabc7…` now separates physical variation identity from
later presentation fields. It can influence only the already bounded initial
variation and cannot author final conditions. PC8 may proceed only after a
development replay reproduces every accepted PC7 initial/physics value exactly.
That replay is now exact. The one-path product candidate is frozen at
`9d5a6686…` (120 additions / 16 deletions) with module SHA `009544bd…`.
It reproduces all PC7 initial and physics records, leaves v0.2 motion blur off,
and derives `19.61656045 px/frame` median motion → `0.30586402 frame` native
shutter with `4e-8 px` target error. The first frozen runner stopped before
root creation because Python serialized the C1 boundary value `0.000001` as
`1e-06`; C2 corrected only that host self-hash verifier and retained the v0.1
tools unchanged. Its correction/freeze hashes are `b2ef2f4a…` / `ec5d9ce8…`.
Fresh formal attempt-01 then passed one clean native build, 16 authority
attacks, three product starts, one sharp control, three product stills, a
24-frame clip and exact reopen. Receipt/audit/direct-review/acceptance hashes
are `801b2c83…` / `8faff835…` / `e4fb5586…` / `48ab5ec2…`; independent audit
is `27/27 PASS`. The complete PC7 Bullet record remains exact, target/final
pose authority remains zero, and the measured native blur adds readable speed
without hiding the causal chain. Direct review still rejects photoreal quality:
the abstract wooden targets, clean environment and orderly contact expose asset
and physical-archetype limits. PC9 must teach recognizable basketball/bottle
construction, scale-aware mass/collision geometry and richer contact response
without authoring any final pose. The PC4 robot remains the later capstone.
The accepted PC8 source was then published by one ordinary non-force
fast-forward from `c7eece67…` to `9d5a6686…`; public `main` and the raw causal
module match the validated source exactly. No tag, release, binary, LFS,
signing or notarization operation occurred.
PC9 is now preregistered before product mutation. Its v0.5 fixture hash is
`51018f80…`; the preregistration hash is `d95c9c4a…`. It returns to one
basketball and three bottles, but replaces the old oversized PC5 scene with
metric dimensions: 0.12 m ball radius, 0.624 kg ball mass, 0.28 m bottle height
and three visible fill fractions. The same fill inputs must derive exact target
masses `0.10685/0.30645/0.48110 kg` and COM heights
`0.05469894/0.06743313/0.09645380 m`; manual per-target mass/COM and final-pose
authority are forbidden. `CONVEX_HULL` must use the visible lathed bottle body,
measured shutter remains active, and direct review must answer seven frozen
recognizability/scale/fill/contact questions YES. This does not claim liquid
sloshing or photorealism. The next action is a one-path product implementation
and zero-network development replay; thresholds may not be weakened after the
result is seen.
PC9 development run-01 is retained as a pre-formal counterexample. All three
bottles responded and the two lighter bottles settled near 90°, but the 0.4811
kg high-fill bottle on a rear split path recovered to 0°; alpha-dithered shell
transparency also made the fill appearance noisy. C1 `5f514928…` preserves all
thresholds, dimensions, masses, COM values, launch momentum and final-pose
denials. Corrected v0.6 fixture `2bf661e0…` places the highest derived mass on
the direct line of action and lighter targets on propagation branches; the
generic shell rule uses native transmission with alpha 1.0. Run-01 receipt hash
is `ecaebabb…`. No product commit or formal root existed at correction time.
Development run-02 closes the C1 physics failure: all three response frames are
28/29 and all three final tilts are approximately 90 degrees, with zero target
or post-release actor pose keys. It is retained because direct visual question
3 is still NO—the opaque shell hides the exact 15/55/90% internal liquid
columns and colored labels can be mistaken for fill. Its receipt hash is
`47fe6f69…`. C2 `60de8cad…` changes no fixture, physical input, threshold,
camera or pose. It preregisters a generic native-glass shell plus readable
fill-derived internal column, while forbidding alpha dither, external fill
gauges and label-based fill encoding. The next action is the C2 development
replay; formal roots and product commit still do not exist.
Development run-03 then falsified the assumption that a Glass BSDF alone is
sufficient in the accepted EEVEE path: the bottles became nearly opaque dark
glass and still hid the fill. Physics remained exact. The retained receipt hash
is `d667254a…`. C3 `fda477ff…` preregisters the engine capability that was
actually observed on the accepted binary—native EEVEE ray tracing plus
per-material screen/raytrace refraction—for the generic filled-bottle factory.
It does not authorize alpha tricks, cutaways, gauges, label encoding, camera
changes or final poses. The next action is the C3 development replay.
C3 E1 `f5341a5f…` corrects one evidence sentence before that replay: the
bound run-03 module already enabled scene-level EEVEE ray tracing; only the two
per-material screen/raytrace refraction flags were absent. Historical files
remain unchanged. The allowed product delta is narrowed to those material
flags only.
The first backward-compatibility replay then found a small but nonzero PC8
measured-shutter drift while PC8 Bullet physics, initial conditions and pose
provenance remained exact. The same harness reproduces the accepted module
exactly, isolating the cause to a 0.0002 m old-schema actor-seam radius change
that perturbed camera fitting. C4 `dbe75ef1…` preregisters one restoration:
v0.1/v0.2/v0.4 retain historical `radius + 0.002`, while v0.5 alone uses the
metric radius-scaled seam. The 29 authority attacks already pass. Exact PC8
cinematography must pass after the fix.
C4 replay now reproduces accepted PC8 physics, initial conditions,
cinematography and pose provenance exactly. The first PC9 reopen verifier then
exposed Blender's float32 `rigid_body.mass` storage (`0.30645` appears as
`0.30645001`) while the canonical product value, COM, physics and shutter were
exact. C5 `e8b37483…` freezes dual exact checks: canonical decimal values in
the result/custom property and independently computed IEEE-754 float32 values
in Blender's solver field, with no tolerance. Development run-08 passes all ten
reopen checks plus exact PC8 compatibility.
C6 `6cba0cc3…` records the actual C1 file SHA after a C2 parent-binding typo
was found; no historical file was edited. Formal tools are now frozen before
root mutation at freeze hash `e9cd86dd…` and file SHA `e4caf317…`, binding the
complete v0.1–v0.8 contract chain, corrected v0.6 fixture, product commit
`b8f65c8a…`, four formal tools and exact module SHA `b45c86d3…`. The single
clean native formal attempt is the next action.
PC9 formal attempt-01 is now accepted. One clean arm64 build completed in
603.09 s; all 29 authority attacks, exact PC8 compatibility, metric
mass/COM/fill/hull checks, three product processes, 24-frame native-blur clip
and exact save/reopen passed. Receipt/audit/direct-review/acceptance hashes are
`96e64534…` / `a20cc945…` / `5c7158b1…` / `85d6789b…`; independent audit is
`27/27 PASS` and direct visual review is `7/7 YES`. All bottles respond at
frames 28/29 and settle near 90 degrees with zero target or post-release actor
pose keys. The accepted claim is a metric rigid-body archetype lesson, not
liquid slosh, deformation or advertising-grade photorealism. The validated
source commit is `b8f65c8a…`; ordinary fast-forward publication is next.
Publication is now complete: `lovejzzz/film-engine/main` advanced by ordinary
fast-forward from `9d5a668a…` to validated `b8f65c8a…`. Git remote, GitHub API
and public raw module checks all agree; raw module SHA is `b45c86d3…` and the
publication receipt hash is `b2b8e254…`. No force, tag, release, binary, LFS,
signing or notarization operation occurred. PC9 is closed; the next curriculum
step may apply these generalized physical rules to the retained robot capstone
as a holdout, without hand-placing outcomes.
RC1 is now preregistered before robot product or scene mutation at spec hash
`ecc70545…`; its declarative performance fixture hash is `19deab68…`. Read-only
inventory found 183 objects, one 18-bone rig, 32 guardian action curves and a
working right-hand IK constraint, but zero rigid bodies and zero rigid-body
constraints. RC1 therefore separates authored intention from physical result:
the existing armature may drive a kinematic hand collider, while a generic
spring control derived from the evaluated hand trajectory must compress,
reverse, settle and choose its final pose through Blender Bullet. The contract
also closes the prior visual false pass with bidirectional medium occupancy,
environment-layer preservation and close facial-landmark visibility. Product
code may consume declarative object bindings but may not branch on robot names,
performance ID or fixture hash. Read-only inventory then showed that v0.1 named
the visual thresholds but not the retained environment and face objects that
must satisfy them. RC1-C1 freezes v0.2 fixture hash `d658ff86…`: four environment
roles and five face-landmark roles are now declarative fixture data only. No
physical parameter, threshold, direct-review question, source scene, product
path, final-pose rule or resource ceiling changed. No RC1 product/source/scene
mutation existed at C1 freeze. The first unsaved development execution then
exposed a measurement-definition failure, not a missing Bullet response: the
finite collider begins response before the closest support-anchor sample, and
the Generic Spring establishes a stable precontact equilibrium 12.33727 mm from
the authored object origin. C2 hash `b102863f…` therefore separates anchor
frame, solver-derived contact onset and precontact equilibrium. It preserves the
exact 25–50 mm peak, reversal, two-frame response, 2 mm/eight-frame settle,
visual and zero-final-pose thresholds. No formal root, saved RC1 scene or
product commit exists yet.

No Developer ID, notarization or unsigned-DMG distribution is implied by PB.6.
Any change to the frozen charter requires a new version, not an in-place edit.

RC1 formal C3 attempt-02 is now accepted and published. One clean native arm64
build and three product starts produced a solver-owned spring-contact robot
performance, a saved/reopened workspace, three formal stills and a 48-frame
contact clip. The mechanism has zero final-pose keys; contact is frame 175,
peak response is 45.65408 mm at frame 178, reversal is frame 179, and the
settled residual is at most 1.73156 mm from frame 189. Reopened actual physics
transforms differ by at most `4.9419513342696675e-9` m. Direct visual review is
`9/9 YES`; independent audit is `37/37 PASS`. The accepted evidence root is
`experiments/robot-capstone/RC1-2026-09-01-attempt-02`; attempt-01 remains an
immutable bundle-name harness failure.

Validated product commit `0e84ef3b…` was published to
`lovejzzz/film-engine/main` by ordinary fast-forward. The reusable method is
also captured in the validated local `physical-film-direction` Codex skill.
This proves one hybrid authored-intention/solver-response holdout, not
photoreal modeling, nuanced full-body acting or finished-film quality.

RC2 is now preregistered and has an accepted-binary development pass. “The
Signal Gate” uses a grooved ceramic sphere rolling under gravity to strike a
Bullet hinge shutter; a passive collision stop holds the gate at 98.80388412°
with zero actor/shutter pose keys, while a constant 1050 W area light reveals
the receiver only through the simulated opening. Contact and response both
occur at frame 51, actor travel is 4.1908872 m, median rolling slip is
`1.48e-6`, the actual/closed receiver luminance ratio is 2.66373562, and all
19 frozen machine checks plus 9/9 direct visual questions pass. Reopened
physics differs by at most `3.725290298461914e-9` m and
`4.300723333017231e-9`°. The software's real inspect/execute route passes,
negative controls fail closed, and the exact RC1 result hash remains unchanged.
Accepted development evidence is
`experiments/physical-light-transfer/RC2-2026-09-01-development-attempt-02`;
attempt-01 is a retained sealing-harness failure.

The first exact cleanup attempt released
31.77 GB but left the host at a rounded 159 GiB and is retained as
`FAIL_CLEANUP_INSUFFICIENT`. A second exact cleanup removed one regenerable
6.0 GiB Claude VM bundle; its wrapper misclassified the valid status spelling
and is also retained as a harness failure. Read-only C2 attempt-03 binds both
receipts and passes with 165 GiB free against the conservative 160 GiB
threshold, zero failures and zero additional mutations. No retained experiment
root, source tree, personal document or recording was deleted.

RC2 formal attempt-01 is now accepted. One local-only clone, one clean native
arm64 build and three offline product starts reproduced the development result:
contact/response at frame 51, 4.1908872 m actor travel, `1.48e-6` median rolling
slip, 98.80388412° peak gate opening, settled window from frame 76, 2.663735624×
actual/closed receiver luminance, zero actor/shutter pose keys and zero light
animation channels. Save/reopen deltas remain below `3.73e-9` m and `4.31e-9`°.
Independent audit is 40/40 `PASS`; direct review is 9/9 `YES`; the 117-file root
manifest is `feb6b6ea18550ec5b9f8737ed77097d932f57133c96469c07930db2f3910505a`.
Accepted evidence is
`experiments/physical-light-transfer/RC2-2026-09-01-attempt-01`. Validated
product commit `636f42f2…` is now public on `lovejzzz/film-engine/main` after
one ordinary fast-forward from `0e84ef3b…`; Git, the GitHub API and both raw
source routes verified the exact OID and bytes. The next program step is to
generalize this learned method into a physics-native action grammar: software
must derive motion from initial conditions, Bullet bodies, collisions and
constraints, and reject authored target/final poses.

RC3 is now preregistered before product or scene mutation. It replaces
project-shaped executors with one restricted graph whose nodes are approved
asset factories plus physical initial conditions, and whose relations are
rolling, support, collision, hinge, occlusion and response propagation. The
same compiler bytes must run a Signal Gate topology and a structurally distinct
basketball/three-filled-bottle topology. Contact, response, camera beats and all
post-release poses remain derived; input outcome fields are rejected.

The first RC3 D1 fixture is retained as a preregistration failure: it confused
a hinge-relative path offset with world Y and placed the ball center outside
the aperture. C1 was frozen with zero product mutations and zero Blender starts;
it changes only the actor, ramp and gate initial locations to the accepted RC2
metric derivation. H1 and every authority, acceptance and resource rule remain
unchanged. The active contract is RC3 preregistration v0.2.

RC3 C3 attempt-03 passed the zero-render machine development stage. D1
contact/response is frame 52 with a 98.80388412° gate peak; H1 contact/response
is frame 16 and all three bottles respond, but only two finish near 90° while
one finishes upright. That asymmetry is retained as a solver result, not
corrected into choreography. Both saves reopen below `8e-9` m, sixteen negative
controls pass, and independent audit is 21/21. Candidate product commit
`5f595fe3…` became the sole parent of the RC4 accepted increment.

RC4 unstaged physical realism is now accepted and published. The two-path
product commit `db662438…` adds one reusable procedural physical-look module
and teaches the restricted action grammar to derive exact contact and settled
response shots from Bullet evaluation. One clean native arm64 build, five
offline product starts, D1/H1 regressions, negative controls, exact save/reopen,
three stills and a 48-frame contact clip passed machine checks `12/12`, fresh
direct review `10/10`, and independent audit `20/20`. The basketball and three
differently filled glass bottles use metric rigid bodies; all post-release
transforms, response frames and final poses remain solver-owned. The settled
shot fits the response group, not the distant initiator, and the unsaved review
render neutralizes timeline camera markers so they cannot silently replace the
declared shot camera. Formal receipt/audit hashes are `18116093…` / `addf528f…`.
Public `lovejzzz/film-engine/main` is exactly `db662438…` after one ordinary
fast-forward from `5f595fe3…`; public Git, GitHub API and raw source bytes agree.
The publication receipt is
`experiments/unstaged-physical-realism/RC4-publication-2026-09-01-attempt-01/receipt.json`
with self hash `bce3c1d5…`. One retained local mirror named `origin` was also
advanced by ordinary fast-forward before the separately named `public` remote;
that sequencing is disclosed in the receipt and involved no force or history
rewrite. The reusable `physical-film-direction` skill now records the observed
camera-marker, response-framing and stable-Eevee-glass lessons. The claim
ceiling remains one M2 Max procedural Eevee/Bullet lesson—not optical glass,
liquid slosh, deformation, breakage, sound, cross-platform behavior,
distribution or arbitrary photoreal filmmaking. The next curriculum gate must
add a new physical degree of freedom such as deformation, fracture or audible
contact while preserving RC4 as an exact no-pose baseline.
RC5 breakable-attachment is formally accepted and published. The one-path
product commit `8e18c825…` is on top of
public RC4 `db662438…`. It adds one native Bullet breakable fixed constraint,
derives the attached bottle from the basketball release ray, and rejects typed
break frames, detached poses and detachment velocities. The accepted B1 run
measured contact at frame 16, cap detachment at frame 24, three responding
bottles and a solver-owned settled group at frames 132–141. Save/reopen passed
7/7 below `1e-8`; RC4/D1/H1 remained exact; twelve authority negatives passed;
the 3-still plus 48-frame review passed direct visual judgment 10/10 and an
independent development audit 27/27. Attempts 01–12 remain retained failures,
including the attempt-11 machine pass / visual fail and attempt-12 camera-cache
failure. The lesson is not fracture mechanics: it is transferable physical
secondary-event direction, molded-glass contact ovality and a cache-safe
derived camera. Accepted development evidence is
`experiments/physical-richness/RC5-2026-09-01-development-attempt-13` with
receipt/audit self hashes `396fc68a…` / `b7020a9b…`. Formal attempt-01 then used
one local-only clone, one clean native arm64 build and four offline product
starts. Its result hash is development-exact `6bc858c6…`; machine receipt is
12/12, fresh direct review is 10/10, and the new binary SHA-256 is
`ad08b541…`. The base independent audit is retained at 26/27 `FAIL` because it
mistook 3,829 immutable Blender source media fixtures for runtime render
leakage. Frozen C1 changed only that audit scope, found zero media in the scene
runtime and passed 10/10 with self hash `bca91646…`. Formal evidence is
`experiments/physical-richness/RC5-2026-09-01-attempt-01`. One ordinary
fast-forward advanced public `lovejzzz/film-engine/main` from `db662438…` to
exact `8e18c825…`; Git ref, GitHub API, tree OID and raw module bytes agree.
There were zero tags, releases, LFS uploads or binary distribution. Publication
receipt self hash is `815c4cc5…`. The next curriculum gate is RC6 design and
must choose one measurable physical degree of freedom before mutation. The
post-build host check is 156 GiB against the conservative 160 GiB clean-build
threshold, so no further native build may begin until a fresh admission passes.

RC6 is now past static-liquid calibration and paused at a safe restart
boundary. The accepted final static mesh is
`experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-c3-attempt-46`:
the cross-process cache adoption and mesh-only reconstruction passed with
receipt `0363fcda…` and independent audit `a332e8a5…`. Mesh bake time was
82.72 seconds; source-volume error was 4.15%, drift was 2.31%, and the final
mesh had zero outside-domain vertices and zero non-manifold edges. This closes
only the frozen static-liquid control, not moving liquid or film quality.

The moving-effector path is intentionally still Bullet-only. Attempts 47–50
are immutable, independently audited `FAIL_BULLET_SCREEN` results: slowing the
indirect ball chain removed torque; direct contact slid the cup; a passive toe
stop tipped but launched or rebounded the cup; and the explicit hinge finally
proved the correct planar geometry but exposed a stale-frame pivot derivation
and an unlimited free fall to 90 degrees. Attempt-50 is retained at
`experiments/physical-richness/RC6-2026-09-02-slow-tip-bullet-screen-c3-attempt-50`;
receipt/audit self hashes are `8b422857…` / `5bf296d3…` and its independent
audit is 18/18 PASS.

C4 attempt-51 is also a retained `FAIL_BULLET_SCREEN`, independently audited
18/18. Its bounded hinge stopped all four cells near 60 degrees with only
2.54–3.47 mm pivot drift, but the kinematic pusher penetrated the visible cup
surface by as much as 57.85 mm and produced a 126.96–142.80 mm per-frame
surface displacement, requiring 14–16 subframes. The domain margin also missed
by only 1–2 mm. Receipt/audit self hashes are `729a1a65…` / `5dc0e42a…`.

C5 replaced that penetrating pusher with a separate impulse-bounded Bullet
MOTOR paired with the existing HINGE. Attempt-52 is retained as a harness-only
`FAIL_EXECUTION`: the first 120-frame Bullet bake completed, but an obsolete
post-bake conditional referenced the removed `separation` variable before any
physical result was written. It used one Blender start and one Bullet bake,
with zero fluid, render, save or network work. Failure self hash is
`df357639…`. Do not infer anything about motor physics from this harness error.

The slow-tip Bullet gate is now accepted by composition. C5-C1 attempt-53 is a
retained pre-root wrapper-count failure. C5-C2 attempt-54 completed one passing
C5F48 cell but retained an aggregate marker-binding failure, independently
audited 16/16. C5-C3 attempt-55 then completed all four unchanged cells and
produced a `PASS_BULLET_SCREEN` receipt selecting the slowest cell, C5F96. Its
15.15789474°/s motor reached 60.0024°, took 63 frames from 5→45°, moved the cup
surface at most 5.87031 mm per frame, required one derived effector subframe
and held hinge-pivot drift to 0.00581 mm. Receipt self hash is `903b1d0a…`.

The C5-C3 base audit is retained at 17/18 solely because it compared Blender's
float32 domain dimensions literally with decimal JSON. C5-C4 changed only that
representation comparison to `1e-6` per axis and passed 18/18 without starting
Blender; audit self hash is `791f7a13…`. The accepted evidence root is
`experiments/physical-richness/RC6-2026-09-02-slow-tip-bullet-screen-c5-c3-attempt-55`.
This closes only the solver-owned slow rigid trajectory.

The bounded moving-liquid Preview attempt-56 is now a retained scientific
`FAIL`, independently closed 23/23. The exact 24-frame C5F96 trajectory,
one-positive-body topology, manifold state, full cup containment and 35.84 mm
cup-local liquid motion all passed. Data/Mesh took 277.86/2.88 seconds. Volume
did not pass: frame 24 was 36.82% below the frozen source and 34.23% below frame
1, yielding 15/17 physical checks. Blender also returned exit zero despite the
scene's threshold exception; C1 records this as a harness mismatch without
changing the physical verdict. Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-preview-attempt-56`;
failure/audit self hashes are `2c2f547a…` / `556d44f8…`. Next preregister one
fresh Data-only diagnostic on unchanged physics to expose all FLIP particles.

That attempt-57 diagnostic is now `PASS_DIAGNOSTIC`, independently audited
18/18. Data took 297.41 seconds and produced the exact 48-file roster. Every
particle stayed inside the cup envelope, but the ALIVE roster grew from 8,105 to
10,557 (`+30.25%`) while attempt-56 Mesh volume had fallen `34.23%`. This
invalidates raw FLIP count as an exact mass proxy; it does not locate the defect
in Data or Mesh. Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-diagnostic-attempt-57`;
receipt/audit self hashes are `9db62ed9…` / `c0cb6268…`. Next perform zero-bake
capability discovery, then read a fresh immutable Data-cache copy.

Attempt-58 completed that copied-cache analysis with zero Blender/bake work and
a 19/19 independent audit. The Data VDBs have particle/velocity grids but no
persisted liquid level set. Particle occupied-voxel support fell 1,227→874
(`−28.77%`) and tracked Mesh volume across all 24 frames at Pearson `0.98427`,
while ALIVE count correlated `−0.95368`. Occupancy is not exact mass, but a pure
Mesh reconstruction explanation is inadequate. Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-occupancy-attempt-58`;
receipt/audit self hashes are `33ec1fcf…` / `f2d76906…`. Attempt-59 then changed
only cup-effector `surface_distance` from 2.5 to 2.0 cells. It remains a physical
`FAIL`, independently audited 16/16: maximum source error improved from 36.82%
to 24.00% and passed, but temporal loss improved only from 34.23% to 23.03% and
still missed the frozen 15% ceiling. Exact motion, one positive manifold body,
containment and all other 16 checks passed; Data/Mesh took 251.55/2.89 seconds.
Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-attempt-59`;
receipt/audit self hashes are `62316a54…` / `95b7f021…`. Do not try a second
effector-distance value. Attempt-60 then passed its zero-bake copied-cache
diagnosis with an independent 19/19 audit. At 2.0 cells, particle occupied-
voxel support fell 1,335→979 (`-26.67%`), only 2.10 percentage points better
than the 2.5-cell baseline, and still correlated with Mesh at `r=0.95525`.
Data crossed the 15% loss line by frame 12 at only 6.84° tilt, before Mesh did.
Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60`;
receipt/audit self hashes are `fcae7479…` / `b4b55584…`. Attempt-61 then changed
only moving-effector subframes 1→2 and remains a physical `FAIL`, independently
audited 16/16. Temporal loss slightly worsened from 23.03% to 23.84%, source
error worsened from 24.00% to 24.80%, and Data cost rose 14.63%; every other
physical check still passed. Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61`;
receipt/audit self hashes are `57e3ade8…` / `ebf39452…`. Do not try subframes 3.
Attempt-62 then passed its reusable copied-cache comparison with an independent
19/19 audit. Subframes-2 Data support fell 1,335→970 (`-27.34%`), 0.67
percentage points worse than subframes-1; Mesh was 0.81 points worse and the
current curves correlated at `r=0.96060`. Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-subframes-data-comparison-attempt-62`;
receipt/audit self hashes are `97663618…` / `a847bffe…`. Effector-subframe
tuning is closed. Attempt-63 then changed only solver minimum timesteps 1→2
and remains a physical `FAIL`, independently audited 16/16. Temporal loss
improved from 23.03% to 21.70%, source error from 24.00% to 22.97%, and Data
cost rose 7.63%; every other check passed. Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-solver-timesteps-attempt-63`;
receipt/audit self hashes are `d2ae5e4e…` / `26d9a50f…`. Do not try timesteps 3
or change CFL/max steps. Attempt-64 then copied the exact Data cache and passed
its independent 19/19 audit with zero Blender or bake work. Two steps reduced
final occupied-voxel support loss only from 26.67% to 26.09% and worst loss only
from 27.42% to 26.99%; the current Data/Mesh curves correlate at `r=0.97958`,
but per-frame improvements do not. Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-timesteps-data-comparison-attempt-64`;
receipt/audit self hashes are `72e83b26…` / `4fa13dbb…`. Timestep tuning is
closed. Attempt-65 is now preregistered with one change on the modestly better
two-step baseline: simulation `particle_radius` 1.6→1.8, the single midpoint of
the previously measured static 1.6–2.0 interval. Its spec is
`specs/ai-native-studio-rc6-moving-liquid-particle-radius.v0.76.json`, self hash
`f1dacdd8…`. The exact run is now a retained physical `FAIL` with a 16/16
independent audit: temporal Mesh loss improved strongly from 21.70% to 17.05%,
source error improved from 22.97% to 22.10%, Data time was 265.50 seconds and
all topology/containment/motion checks passed. Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-particle-radius-attempt-65`;
receipt/audit self hashes are `f3a741cc…` / `a5b23c9f…`. Do not scan another
radius. Next perform one zero-bake copied-Data comparison against attempt-63/64
before selecting a different simulation property. That attempt-66 comparison
is now preregistered at
`specs/ai-native-studio-rc6-moving-liquid-particle-radius-data-comparison.v0.77.json`,
self hash `f719e46b…`. Attempt-66 is now `PASS_DIAGNOSTIC` with a 19/19
independent audit: radius-1.8 occupied support fell 28.91%, 2.82 points worse
than radius 1.6, even though Mesh improved 4.65 points. Current Data/Mesh curves
correlate at `r=0.95531`, but baseline-relative changes only at `r=0.47650`.
Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-particle-radius-data-comparison-attempt-66`;
receipt/audit self hashes are `04b70991…` / `aed82a88…`. Occupied support is
not mass, particle-radius tuning is closed, and the next design must examine a
distinct simulation-density variable rather than Mesh inflation. Bound source
inspection found that `particle_number` controls only initial sampling, while
per-step `adjustNumber` uses default minimum/maximum 8/16. Attempt-67 is now
preregistered to change only the continuing minimum 8→12, keeping maximum 16
and all attempt-65 physics exact. Its spec is
`specs/ai-native-studio-rc6-moving-liquid-particle-minimum.v0.78.json`, self
hash `1a803825…`. Attempt-67 is now a retained physical `FAIL` with a 16/16
independent audit. Raising the ongoing minimum 8→12 changed all 24 Data VDBs
but left all 24 Mesh files and every non-time physical metric exact with
attempt-65; temporal loss stayed 17.050045% while Data cost rose 4.81%.
Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-particle-minimum-attempt-67`;
receipt/audit self hashes are `22e0ad0c…` / `6a35f1ac…`. Particle-density
tuning is closed. Inspect fractional-obstacle separation next; do not render or
begin real impact. Bound source confirms default `fractions_distance=0.5` is
the per-step `pushOutofObs` separation threshold. Attempt-68 is now
preregistered to return to attempt-65 and change only 0.5→0.25; every
containment and topology gate stays exact. Its spec is
`specs/ai-native-studio-rc6-moving-liquid-fractions-distance.v0.79.json`, self
hash `1f9e6125…`. Attempt-68 is now a retained physical `FAIL` with a 16/16
independent audit: temporal loss improved 17.05%→15.44% and source error
22.10%→18.81%, with zero radial/floor/rim intrusion and valid one-body
manifold topology. It misses the frozen temporal gate by only 0.44 points;
Data cost rose 8.13%. Evidence is
`experiments/physical-richness/RC6-2026-09-02-moving-liquid-fractions-distance-attempt-68`;
receipt/audit self hashes are `6037c9cc…` / `8716e960…`. Do not try a second
distance. Compare the immutable Data cache before another distinct variable;
do not render or begin real impact. Attempt-69 is now preregistered as that
zero-bake comparison at
`specs/ai-native-studio-rc6-moving-liquid-fractions-distance-data-comparison.v0.80.json`,
self hash `8e5da68c…`; both roots remain absent.

## Public routes

- Research home: <https://lovejzzz.github.io/BlenderFilmStudio/>
- Latest design: <https://lovejzzz.github.io/BlenderFilmStudio/ai-native-studio-design/>
- New-machine handoff: <https://lovejzzz.github.io/BlenderFilmStudio/ai-native-studio-handoff/>

If a public route has not deployed yet, validate with `npm run build` and a
plain HTTP request after deployment. Do not work around the browser stability
guard.
