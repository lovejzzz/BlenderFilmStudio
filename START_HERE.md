# BlenderFilmStudio — new machine cold start

> **Current decision:** F0.1 through F0.4 passed on the admitted M2 Max host.
> F0.4 attempts 01 and 02 remain retained `FAIL` results. Attempt-01 proved
> canonical-exact B01/B02 BuildPlans and all four negative controls, then found
> a missing OCIO launch binding. Attempt-02 fixed only that binding and built
> B01, but the frozen full structure hash differed because it includes the
> product build hash. Attempt-03 versioned semantic structure separately from
> exact product provenance and closed F0.4 as `PASS`. F0.5 is next; do not
> assume the fork is viable until F0.1-F0.7 all close.

This is the authoritative handoff for a fresh Codex session. The repository is
both a research notebook and an executable evidence base. Read this page,
`AGENTS.md`, and the machine-readable state before doing anything expensive.

## Where the project stands

- **Latest direction:** direct official Blender thin fork; Bforartists is a UI
  and fork-maintenance reference; an external shell remains the fallback.
- **Pinned engine baseline:** official `v5.2.0` at
  `fbe6228777e7d9afefcd61a413844e790ae75db7`.
- **Active experiment:** `F0-SOURCE-FEASIBILITY`, F0.5 render-and-receipt
  preregistration. No F0.5 render is authorized before its inputs, resource
  budgets, pixel gates, cost receipts and failure controls are frozen.
- **Closed gates:** `F0.1 PASS`, `F0.2 PASS`, `F0.3 PASS` and `F0.4 PASS`. Two clean official builds reported Blender
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
- **Inherited evidence:** B01-B62 cover structured scene compilation, Blender
  execution, safety/admission, pixels, production passes, cost, recovery and a
  three-shot cinematic attempt. These results are evidence, not a claim that
  autonomous filmmaking is solved.
- **Most important retained rejection:** B62's latest camera holdout passed all
  technical gates but failed the frozen composition threshold at frame 288.
  Source control does not replace direction or taste.
- **Unproven:** mouse-free EEVEE preview, Cycles EXR and render receipts inside
  the product, merge cost, packaging and `.blend` round-trip isolation.

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

5. F0.1-F0.4 are closed. Before any F0.5 product start, create a new immutable
   evidence root and preregister exact B01/B02 source `.blend` identities,
   EEVEE preview and Cycles EXR settings, mouse-free commands, render-count and
   disk ceilings, process/pixel/cost/failure receipts, negative controls and
   stop rules. Cross-bind the accepted F0.4 verdict and never overwrite its two
   retained failures.

## What not to do

- Do not restart B62 or create a new rendering side quest as the main task.
- Do not clone Blender inside this repository or commit build products.
- Do not begin a permanent engine repository before all F0 gates have verdicts.
- Do not copy Bforartists as a second upstream; inspect it as a reference.
- Do not give a model unrestricted `bpy`, shell or filesystem authority.
- Do not hide failed builds, relax thresholds after seeing results, or overwrite
  receipts.
- Do not use in-app browser automation while the crash guard in `AGENTS.md` is
  active.
- Do not stage unrelated worktree changes; this repository may contain the
  owner's unpublished files.

## Definition of a useful next checkpoint

The next machine should push one small, auditable F0.5 preregistration checkpoint containing:

- a unique F0.5 evidence root that cross-binds accepted F0.4 attempt-03;
- exact B01/B02 `.blend`, manifest, semantic structure, product and OCIO identities;
- one frozen EEVEE preview profile and one frozen Cycles EXR profile;
- mouse-free invocation, render-count, time, RSS, disk and output-byte ceilings;
- independently specified process, pixel, cost, restart/failure and artifact receipts;
- negative controls for identity mismatch, output escape, invalid render state
  and incomplete receipt;
- a journal entry and, if useful, a website update.

The scientific result may be `PASS`, `FAIL`, or `BLOCKED`. “Still working” is
not a gate verdict; “failed with preserved evidence and a bounded next test” is.

## Public routes

- Research home: <https://lovejzzz.github.io/BlenderFilmStudio/>
- Latest design: <https://lovejzzz.github.io/BlenderFilmStudio/ai-native-studio-design/>
- New-machine handoff: <https://lovejzzz.github.io/BlenderFilmStudio/ai-native-studio-handoff/>

If a public route has not deployed yet, validate with `npm run build` and a
plain HTTP request after deployment. Do not work around the browser stability
guard.
