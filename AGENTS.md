# BlenderFilmStudio agent operating rules

## Read this first

The authoritative cold-start entry is [`START_HERE.md`](./START_HERE.md). Read
it before changing code, running Blender, or extending the research catalog.
Then read the machine-readable snapshot at
[`handoff/ai-native-studio-current-state.v0.1.json`](./handoff/ai-native-studio-current-state.v0.1.json).

## Current operating goal

`F0-SOURCE-FEASIBILITY` is complete: F0.1 through F0.7 all closed as `PASS`
on the admitted M2 Max host. The measured result supports advancing the direct
official-Blender thin fork into a product prototype; it does not prove public
distribution, production readiness, cross-platform support, or autonomous
filmmaking.

Preserve the completed F0 evidence and prepare the next explicit decision
checkpoint: repository charter, licensing/release boundary, Phase B vertical
slice and its preregistered acceptance criteria. Do not create or publish a new
permanent repository until that scope is explicitly authorized.

The post-F0 contract is frozen at commit
`6a38ca3bdd93219ec6dcd001fa72143df7d80a10`:
`research/2026-08-30-ai-native-film-studio-post-f0-repository-phase-b-charter-v0.1.zh-CN.md`
and `specs/ai-native-studio-post-f0-phase-b.v0.1.json`. Do not edit v0.1 in
place. The next action requires explicit repository owner, visibility,
create-repository and first-push authorization; until then, no permanent
repository or Phase B source mutation is allowed.

The selected hypothesis is an independently branded, GPL-compliant, AI-native
film application built on the official Blender source. Bforartists is a design
and maintenance reference, not the source baseline. The fallback is an external
Film Studio process controlling an unmodified Blender build.

Do not resume B62 as the primary goal. B01-B62 are inherited evidence and the
future conformance suite. They may be rerun only when an F0 gate names them as a
fixture or regression.

The work is ordered by seven gates defined in
[`specs/ai-native-studio-f0.v0.1.json`](./specs/ai-native-studio-f0.v0.1.json):

1. **F0.1 Reproducible source build.** Build the pinned official Blender 5.2.0
   source commit on the new host and produce a binary plus source, dependency,
   toolchain, timing and resource receipts.
2. **F0.2 Independent identity.** Prove a separate name, bundle identifier,
   icon, splash and configuration root without using Blender as the product
   brand.
3. **F0.3 Film workspace.** Implement the smallest Project / Scene / Shot /
   Character workspace while preserving an explicit Expert Mode.
4. **F0.4 Embedded contract.** Accept the frozen SceneSpec and produce a
   BuildPlan canonical-exact with the existing external compiler before
   building the B01/B02 fixtures.
5. **F0.5 Render and receipts.** Without mouse interaction, produce an EEVEE
   preview, Cycles EXR and independently auditable process, pixel, cost and
   failure receipts.
6. **F0.6 Upstream merge drill.** Merge a preregistered later Blender commit
   interval and measure conflicts, patch surface, human time and regressions.
7. **F0.7 Package and round trip.** Install and uninstall the macOS app, define
   signing/notarization, isolate configuration and pass `.blend` round trips.

F0 is complete only when every gate has an evidence root and an explicit
`PASS`, `FAIL`, or `BLOCKED` verdict. A failed gate is a valid scientific
result. If source ownership is not justified by measured UX/control benefits,
or merge/package cost crosses the preregistered ceiling, recommend the external
shell rather than expanding the fork.

The accepted F0.7 root is
`experiments/ai-native-studio-f0/F0.7-2026-08-30-mac-m2max-attempt-05`.
It proves one unsigned local research DMG, isolated install/uninstall and two
same-host `.blend` round trips. Attempts 01–04 remain retained failures. No
Developer ID signing, notarization or Gatekeeper bypass was performed.

## Cold-start execution rules

- First run the read-only host check:
  `node scripts/preflight-f0-source-host.mjs`.
- Keep Blender source, dependencies and builds outside this research repository.
  Never vendor a Blender checkout or generated build tree here.
- Use official Blender source tag `v5.2.0`, commit
  `fbe6228777e7d9afefcd61a413844e790ae75db7`, until a versioned protocol
  amendment changes it.
- Preregister each gate before the first mutation. Freeze inputs, expected
  outputs, thresholds, negative controls, resource ceiling and stop rule.
- Use unique immutable evidence roots. Never overwrite a failed or accepted
  run; corrections must cross-bind the prior receipt.
- Preserve at least 100 GiB free disk plus all projected writes before native
  builds or renders. No source build begins if the admission check fails.
- Record the exact Git commit, Blender source commit, host/toolchain identity,
  commands, timings, peak resources, artifacts, hashes and negative results.
- After each atomic result: update the journal/protocol, commit only related
  files, push, and verify the public route with a non-browser HTTP request.
- Do not weaken frozen thresholds to convert a rejection into a pass.
- Do not modify historical specs, receipts or experiment outputs in place. Add
  a versioned correction or a new experiment root.
- Do not make broad cleanup changes. The worktree may contain user-owned files;
  inspect and preserve them.

## In-app browser stability guard

Two Codex desktop crashes were observed on 2026-08-28 with app version
`26.820.80927 (7271)`. Both reports had the same `Chrome_IOThread`,
`EXC_BREAKPOINT (SIGTRAP)` signature. The first occurred while many in-app
browser tabs were being claimed and closed; the second occurred after browser
automation was attempted again following relaunch.

Until the installed Codex app version changes or the user explicitly requests a
controlled retest:

- Do not use in-app browser automation for this repository, including tab
  discovery, claiming, navigation, DOM inspection, screenshots, or cleanup.
- Do not call `open_in_codex` with a browser target. Provide the exact URL to the
  user instead.
- Keep at most one user-visible BlenderFilmStudio browser tab. Reuse it manually;
  never create a second tab for local or deployed previews.
- Never close browser tabs concurrently or in a batch. If the user later asks
  for cleanup after the guard is lifted, close exactly one tab per operation and
  verify stability before continuing.
- Validate local routes with static/production builds and non-browser HTTP
  requests. If the execution environment cannot reach a local listener, record
  that limitation and rely on the production build plus deployed-route HTTP
  checks; do not fall back to browser automation.

These rules protect client stability. They do not change the scientific
acceptance criteria for Blender experiments or website publication.
