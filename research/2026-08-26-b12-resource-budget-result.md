# B12 Blender compile resource-budget result

Date: 2026-08-26

Classification: **FORMAL B12 TRUE / SOFT WATCHDOG / NOT AN OS SANDBOX**

## Result

The restricted Codex/CLI-to-Blender compile entry point now applies one pinned budget profile before launching Blender and records the exact command, profile hash, elapsed time, sampled root-process RSS, combined log bytes, output file count/bytes, exit status and termination reason.

Budget profile SHA-256:

`9203aba815c5a1b9063c288219219df1d4801eec598aa6cb1dc01729ff32eebe`

The production profile is scoped to scene compilation, not final frame rendering:

| Budget | Limit |
|---|---:|
| Wall time | 30,000 ms |
| Sampled root-process RSS | 2,147,483,648 B |
| Combined stdout/stderr | 2,097,152 B |
| Output files | 32 |
| Output bytes | 134,217,728 B |
| Sampling interval | 100 ms |

## B01 positive control

The pre-watchdog unbudgeted B01 baseline used approximately `0.54 s`, reached `255,361,024 B` maximum RSS under macOS `/usr/bin/time`, and wrote two files totalling `124,972 B`.

The final restricted CLI run passed with:

- elapsed time: `568 ms`;
- peak sampled root-process RSS: `253,837,312 B`;
- combined log: `1,109 B`;
- output: three files, `129,032 B`;
- CLI exit code: `0`;
- structure SHA-256: `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`.

The few-byte `.blend` size variation is not a determinism gate. The published semantic structure hash is unchanged.

This final regression was executed after B13 introduced `scene.structure.canonical.json`; the third output file is the exact Blender/Python canonical structure byte stream used for cross-language receipt verification.

## Negative matrix

All six pre-registered cases produced the expected stable outcome:

| Case | Test limit | Observed | Outcome |
|---|---:|---:|---|
| `N_TIMEOUT` | 250 ms | 261 ms at breach | `WALL_TIME`, SIGTERM, awaited |
| `N_LOG_BYTES` | 8,192 B | 65,536 B at breach | `LOG_BYTES`, SIGTERM, awaited |
| `N_OUTPUT_FILES` | 4 | 12 | `OUTPUT_FILES`, SIGTERM, awaited |
| `N_OUTPUT_BYTES` | 65,536 B | 262,144 B | `OUTPUT_BYTES`, SIGTERM, awaited |
| `N_RSS` | 50,331,648 B | 183,189,504 B | `RSS_BYTES`, SIGTERM, awaited |
| `N_NONZERO_EXIT` | exit 0 required | exit 7 | `CHILD_FAILED`, awaited |

The log guard retains only a 4 KiB preview and records the SHA-256 of the complete observed stream. It therefore bounds report growth without discarding evidence that the captured stream changed.

## Path-security regression

The new CLI validates its BuildPlan, output directory and report destination with the same lexical-path plus nearest-real-ancestor policy established by B10. Three supplementary regressions passed: repository-external report, repository-external output and a BuildPlan symlink were rejected before Blender launch; neither external target was created.

## Boundary

B12 is a fail-closed application watchdog. It is not a kernel-enforced resource sandbox.

- wall, log and output checks can overshoot by one sampling interval or one stream chunk;
- RSS is sampled from the root child only, not summed across descendants;
- a process can allocate and release memory between samples;
- GPU VRAM, network access and system calls are not isolated;
- the trusted Node supervisor itself is outside the quota;
- final Cycles rendering needs a separate shot-derived profile;
- parser exploitation remains outside the protection proven here.

The next security claim must therefore target an OS/container execution boundary or a signed remote worker, not enlarge the wording of this watchdog result.

## Artifacts

- `research/2026-08-26-b12-resource-budget-protocol.md`
- `specs/restricted-compile-budget.v0.1.json`
- `experiments/resource-budget-v0-1/first-run-baseline.json`
- `experiments/resource-budget-v0-1/results.json`
- `scripts/lib/budgeted-process.mjs`
- `scripts/run-restricted-blender-compile.mjs`
- `scripts/run-b12-resource-budget-experiment.mjs`
