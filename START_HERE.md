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

## Where the project stands

- **Latest direction:** direct official Blender thin fork; Bforartists is a UI
  and fork-maintenance reference; an external shell remains the fallback.
- **Pinned engine baseline:** official `v5.2.0` at
  `fbe6228777e7d9afefcd61a413844e790ae75db7`; the admitted F0.6 merge target is
  official `v5.2.1` commit `9e2066aef7ef7e20c142ad7bd3303138a4304c93`.
- **Completed experiment:** `F0-SOURCE-FEASIBILITY`. All seven gates are
  `PASS`. The post-F0 repository/Phase B charter is frozen at commit
  `6a38ca3b…`; repository creation was later authorized, while Phase B remains
  unauthorized.
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
  PASS with self hash `71d6e9d5…`. Phase B remains unauthorized.
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
  spelling. Attempt-01 and attempt-02 are immutable; PB.4–PB.7 remain
  unauthorized.
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

PB.2 validation-only is closed `PASS`; PB.3 attempt-01 and attempt-02 are
retained harness failures. Attempt-02 completed all four zero-render semantic
processes but failed frozen postconditions at 17/18 base and 21/23 C3 audit.
The C4-C1 inert correction now passes 32/32 static checks: exact argv
normalization and thumbnail prevention are frozen without relaxing the
no-render-artifact threshold. The next checkpoint is exact C4 attempt-03
authorization. Attempt-03 roots remain absent and no fresh execution is
authorized. Do not retry either formal root, mutate `film-engine`, or begin
PB.4–PB.7.

No Developer ID, notarization, unsigned-DMG distribution or Phase B mutation is
implied by repository authorization. Any change to the frozen charter requires
a new version, not an in-place edit.

## Public routes

- Research home: <https://lovejzzz.github.io/BlenderFilmStudio/>
- Latest design: <https://lovejzzz.github.io/BlenderFilmStudio/ai-native-studio-design/>
- New-machine handoff: <https://lovejzzz.github.io/BlenderFilmStudio/ai-native-studio-handoff/>

If a public route has not deployed yet, validate with `npm run build` and a
plain HTTP request after deployment. Do not work around the browser stability
guard.
