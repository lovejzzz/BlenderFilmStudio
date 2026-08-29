# BlenderFilmStudio — new machine cold start

> **Current decision:** validate an AI-native film application built as a thin,
> independently branded fork of the official Blender engine. Do not assume the
> fork is viable until F0.1-F0.7 close.

This is the authoritative handoff for a fresh Codex session. The repository is
both a research notebook and an executable evidence base. Read this page,
`AGENTS.md`, and the machine-readable state before doing anything expensive.

## Where the project stands

- **Latest direction:** direct official Blender thin fork; Bforartists is a UI
  and fork-maintenance reference; an external shell remains the fallback.
- **Pinned engine baseline:** official `v5.2.0` at
  `fbe6228777e7d9afefcd61a413844e790ae75db7`.
- **Active experiment:** `F0-SOURCE-FEASIBILITY`.
- **Inherited evidence:** B01-B62 cover structured scene compilation, Blender
  execution, safety/admission, pixels, production passes, cost, recovery and a
  three-shot cinematic attempt. These results are evidence, not a claim that
  autonomous filmmaking is solved.
- **Most important retained rejection:** B62's latest camera holdout passed all
  technical gates but failed the frozen composition threshold at frame 288.
  Source control does not replace direction or taste.
- **Unproven:** repeatable source build on the new host, independent application
  identity, native film workspace, embedded contract equivalence, merge cost,
  packaging and `.blend` round-trip isolation.

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

5. Close F0.1 before beginning branding or UI work. The first result should be a
   reproducible native Blender binary and receipt, not a mockup.

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

The next machine should push one small, auditable checkpoint containing:

- a unique F0.1 experiment root;
- host preflight receipt;
- pinned source and dependency identities;
- exact build command and toolchain;
- success or complete failure evidence with time, disk and peak-memory data;
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
