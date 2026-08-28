# BlenderFilmStudio agent operating rules

## Current operating goal

Build BlenderFilmStudio into a low-cost, restart-safe and independently
auditable Blender 5.2 film-production pipeline, then use it to deliver one
finished cinematic proof rather than indefinitely expanding the research
catalog.

The terminal acceptance artifact is a 10–20 second sequence containing at
least three continuous shots with a consistent character and environment. A
single command from a clean output root must be able to compile the frozen
shot brief through `SceneSpec -> immutable BuildPlan -> Blender`, survive one
controlled Blender interruption and a Codex restart, resume only from verified
receipts, and finish the EXR and delivery-video outputs. The asset, structure,
cost, process and output receipts must be independently replayable. The code,
failures, journal, evidence and research page must all be pushed and published.
No generative video model participates in the image pipeline.

The work is ordered by four gates:

1. **Control-plane stability.** Terminal-first operation, bounded tool output,
   the in-app-browser guard below, at least 100 GiB free-space reserve plus
   projected writes, native-spawn just-in-time admission, unique immutable
   output roots, and an immediate journal/commit/push checkpoint after every
   atomic result.
2. **B57 closure.** Prove the disk readmission and receipt cross-binding with
   26/26 formal gates, at least 56/56 semantic attacks, four real clean Blender
   compilations, and a one-byte-below negative case that launches no restricted
   or native process.
3. **Restart-safe orchestration.** Add a durable job manifest, stage
   checkpoints, idempotent recovery, resource accounting and fault injection so
   a crash or restart loses no accepted evidence and never reruns a completed
   immutable stage.
4. **Cinematic proof.** Compile the real character, environment, animation,
   camera, lighting, materials and render, verify cross-shot consistency, then
   publish the finished proof and its exact limitations.

Reaching gate 4 is the stopping condition. At that point, stop creating new
research IDs for adjacent questions and issue a final boundary report. Until
then, prioritize the next unmet gate over new website tabs, broad surveys or
unrelated experiments.

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
