# RC6 C32 result — Native fields available; passivity not yet proved

Date: 2026-09-02
Verdict: `PASS_SOURCE_BINDING_ONLY`, 26/26 mechanical checks.

C32 closes the read-only investigation requested after C31. The RC5 source
contains an existing resumable-Data export path for `phi`, `phi_particles`
and `phi_previous`; no engine modification or new build is needed to test
that path. However, the setting also changes import and hence the native phi
input available to Mesh generation. It is not an established passive switch.

The next bounded experiment must therefore be Data-only, first proving reader
readiness and then testing unchanged physical settings/common particle and
velocity outputs. Do not bake a new Mesh to assess this measurement change.
Native negative-levelset occupied volume remains a numerical descriptor, not
exact mass. VDB active counts, zero background, tiles, finite dimensions,
cell-versus-world units, half precision and frame-terminal sampling must all
be handled explicitly.

## Evidence

- Freeze/execution commit: `05f0d61f2a4cb1f1bf331c22109f5ebaa99bd46f`.
- Evidence root: `experiments/physical-richness/RC6-2026-09-02-native-conservation-observability-c32-attempt-111`.
- Source observation self hash: `28eb5274c4251e9c4a7c70876c2af2464b3b49241100b26e1100dc3cecfbddc1`.
- Audit self hash: `a3b9cd3508ac5082eef0a5c2c18b10f53ad5e789fd8cb471f3e18e78a2f0eeb1`.
- Eleven source files match exact RC5 commit bytes; eighteen line-ranged
  source anchors and eight additional checks pass. Retained bound input
  bytes and source worktree are unchanged.
- Evidence: 34,368 bytes, below the frozen 1 MiB ceiling.
- One formal system-Python audit; zero Blender starts, bakes, renders, saves,
  builds, cache copies/mounts, engine edits/writes or audit network calls.
  Research Git publication is a separate standing-authority operation.

This audit independently re-extracts and binds source anchors; it does not
automatically establish every human interpretation or any runtime result.
The full analysis and future stop conditions are in
`research/2026-09-02-rc6-native-conservation-observability-c32-source-inspection.md`.

## Next action and unchanged project status

Next: **C33 Data-only native-field diagnostic**, beginning with a separately
frozen reader-readiness gate. Establish actual retained cache policy/precision,
validate a finite-grid phi reader and sufficiently strong common-field
comparison before spending another bake. If the reader cannot compare particle
positions/attributes and velocity values, stop rather than substituting weak
occupancy equality. Then freeze the one-run diagnostic, resources and exact
fresh roots. C33 was neither frozen nor started by C32.

R40 impact liquid remains physical FAIL; no new liquid demo was rendered.
The existing RC5 48-frame, 720p, two-second rigid-body contact clip is viewable
at `experiments/physical-richness/RC5-2026-09-01-attempt-01/contact-clip.mp4`.
It is an earlier basketball/bottle collision demonstration, not C32 output or
proof of solved impact liquid. A fresh inspection of its retained contact sheet
shows readable motion and shadows, but a simple fixed shot and elementary
asset detail; it remains a prototype demonstration, not finished film quality.

The 154 GiB host reading remains below 160 GiB for a clean native build.
Continue using the existing binary only under a separately admitted protocol;
do not clean up retained evidence or substitute the unexecuted C31 holdout for
the user's primary impact project.
