# BlenderFilmStudio agent operating rules

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
