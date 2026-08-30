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

The next useful checkpoint is an explicit owner decision on the prepared PB.1
validation-only request. It permits only one read-only public-engine clone,
local-only dependency/LFS materialization, one clean native build, at most two
zero-render identity/configuration starts and research evidence publication.
It permits no engine source edit or remote write and does not start PB.2–PB.7.
The exact authorization sentence is stored in
`specs/ai-native-studio-pb1-validation-only-authorization-request.v0.2.json`.

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
