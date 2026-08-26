# B12 Blender compile resource-budget protocol

Date frozen: 2026-08-26, before implementing the budget runner or measuring the B01 process baseline.

Status: **PRE-REGISTERED / NOT YET EXECUTED**

## Question

Can the Codex/CLI-to-Blender boundary stop a compile process that exceeds declared wall-time, resident-memory, log-volume or output-directory budgets, while leaving a valid B01 compile and its published structure hash unchanged?

B12 tests resource containment, not asset semantics. B10 covers paths and B11 covers appended Blender evaluation structures.

## Frozen production budget v0.1

The initial restricted compile profile is intentionally generous relative to a single benchmark scene:

- wall time: `30,000 ms`;
- sampled root-process RSS: `2,147,483,648 bytes`;
- combined stdout/stderr: `2,097,152 bytes`;
- output files: `32`;
- output bytes: `134,217,728 bytes`;
- sampling interval: at most `250 ms`.

Budgets apply to one Blender scene-compilation process, not final Cycles frame rendering. A production render profile will require separate limits derived from shot resolution, samples and frame count.

## Frozen experiment

1. Record a valid B01 compile through the unbudgeted command path as the first-run baseline.
2. Implement one reusable budget runner and a restricted Blender compile entry point.
3. Run the same B01 BuildPlan through the restricted entry point.
4. Require the published B01 structure SHA-256 `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`.
5. Execute harmless, local fixtures for each independent breach class.
6. Publish measured elapsed time, peak sampled RSS, log bytes, output file count/bytes, termination reason and exit status.

## Negative cases

- `N_TIMEOUT`: a Blender process sleeps beyond a deliberately low test wall budget;
- `N_LOG_BYTES`: a Blender process emits more than a deliberately low log budget;
- `N_OUTPUT_FILES`: a local fixture creates more than the allowed file count inside its assigned work directory;
- `N_OUTPUT_BYTES`: a local fixture writes more than the allowed byte count inside its assigned work directory;
- `N_RSS`: a local fixture exceeds a deliberately low sampled RSS budget;
- `N_NONZERO_EXIT`: a child failure is returned as failure rather than mistaken for a budget pass.

The attack fixtures contain no network access, persistence, secret reads or executable payloads. All writes are confined to the ignored `experiments/resource-budget-v0-1/work/` directory.

## Acceptance gate

Formal B12 is true only if:

- all six negative cases are detected with the correct stable reason;
- over-budget processes are terminated and awaited;
- B01 succeeds within the production profile;
- B01 structure hash is unchanged;
- results distinguish measured soft watchdogs from kernel-enforced hard limits;
- the command, exact budget profile and observations are stored as JSON.

## Explicit non-claims

B12 v0.1 does **not** establish:

- network isolation;
- a hardened `.blend` parser;
- kernel-level hard memory or CPU quotas;
- complete descendant-process memory accounting;
- GPU VRAM containment;
- protection from a process that consumes resources between samples;
- a render-farm quota policy;
- container, VM or macOS sandbox isolation.

Those require an OS/container execution layer. B12 v0.1 is a deterministic fail-closed watchdog and measurement layer for the current local Codex/CLI workflow.
