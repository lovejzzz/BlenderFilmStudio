# RC6 C14 restart checkpoint

Recorded before the owner restarts Codex on 2026-09-02.

## Durable state

- Research repository HEAD and `origin/main` were both
  `9b7a64507149c96c50ee2d26eb5a215d28a54f31` before this checkpoint commit.
- The worktree was clean.
- No Blender, RC6 runner, bake or render process was active.
- Both read-only research subagents had completed; neither changed local files.
- The active long-running goal remains open. This checkpoint is a pause, not a
  completion or blocked verdict.

## Accepted evidence boundary

C14 attempt-86 is immutable and must not be rerun, repaired or rendered:

- evidence:
  `experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86`
- workspace:
  `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86`
- result SHA-256:
  `5dbc4e416466567365e101d64f8c68b4d28323364f385a19cc9e451d115cabbf`
- receipt SHA-256:
  `c8d56e2b3ea85cc6a3c1bfdff304ef37d95546e5d056dd06f8b25a305409e5fc`
- independent audit SHA-256:
  `3c3dd1d592833811b4e5d24130492011ed9852d4c3480113d9acf0eb27047bbb`
- verdict: physical `FAIL`, independent audit `PASS` 20/20.

The one isolated change, `timesteps_max` 4 to 8, was a large improvement but
not a repair: peak source-volume multiple fell from about 16.385 to 3.357,
positive liquid bodies from 239 to 50, and connected components from 243 to 52.
Source conservation, temporal drift, bounded topology and maximum cup-solid
intrusion of 2.453988% still fail.

## Exact resume action

Resume at `RC6-REAL-IMPACT-C14-TRANSITION-ANALYSIS`:

1. Read `AGENTS.md`, `START_HERE.md`, and
   `handoff/ai-native-studio-current-state.v0.1.json`.
2. Run the read-only host preflight.
3. Perform only read-only per-frame comparison of retained C12 and C14 over the
   first instability interval, locating the first Data/Mesh expansion,
   fragmentation and cup-intrusion threshold crossings.
4. Preregister exactly one further Data/collision degree of freedom before any
   fresh cache root or Blender run.

Preserve the R40 Bullet trajectory, geometry, domain, source, resolution, Mesh
settings and all 27 physical thresholds. Do not render until the physical gate
passes. Do not mount a retained cache in Blender.

## Host admission at pause

The read-only preflight observed 155 GiB free on the M2 Max host at
`2026-09-02T11:32:51.247Z`. This is below the conservative 160 GiB threshold for
a fresh native build. Read-only analysis and bounded runs with the accepted
binary remain admissible; another clean native build is not.

