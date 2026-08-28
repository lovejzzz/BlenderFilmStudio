# B59-G0-R1 · Codex host stability readmission protocol

Date: 2026-08-28
Status: PREREGISTERED
Parent commit: `d115e5da8cacddb9f03a427c554acf5cde50dde0`

## Parent blocker

The B59-G0 formal baseline was valid but blocked on disk stability margin and Codex-tree RSS. Its immutable results/audit SHA-256 values are `5a0132be20d5cc9de439bec3e848b3f89416de282706c2b443c42bb442b48c33` and `06e54e79f7ec1fa7bb60a4cef69ef36830f8bab89bb6d213d6007962c45c4b43`.

## Exact remediation

Under the user's existing cache-cleanup authorization, six exact reconstructible cache targets were removed: pnpm store, Gradle caches, Bun install cache, npm `_npx`, npm logs and `~/Movies/CacheClip`. Their pre-removal `du` sum was 4,497,494,016 bytes. No Qwen model, Colima state, repository evidence or project media was removed, and no process received a signal.

The baseline observed 109,110,300,672 available bytes. The immediate post-cleanup observation was 112,308,187,136 bytes, an observed gain of 3,197,886,464 bytes and 102,166,528 bytes above the unchanged stability threshold. APFS accounting explains why the observed gain need not equal the `du` sum; neither number is substituted for the fresh readmission measurement.

## Readmission

R1 reuses the exact B59-G0 20 gates, 24 attacks, 100 GiB core reserve, 0.5 GiB B58 projection, 4 GiB stability margin, memory/process/RSS ceilings and bounded-output rules. The only tool interface change is an explicit repository-relative `--spec specs/codex-host-stability-readmission.v0.1.json` option so the same collector/auditor logic can target a new single-use root. Default no-argument behavior remains bound to the original baseline spec.

The runner and auditor must bind the selected spec SHA, parent ancestry, `HEAD == origin/main`, exact clean release paths and fresh `experiments/codex-host-stability-readmission-v0-1`. They remain limited to 12 combined short read-only children and zero Blender, render, browser automation, network, model, Docker, cleanup, signal or restart operations.

## Decision

- `ADMITTED_FOR_LIGHTWEIGHT_WORK` requires 20/20 gates, 24/24 attacks, a valid synthetic attack control and no integrity failure.
- `BLOCKED_HOST_STABILITY` retains any real resource/process failure without lowering a threshold.
- `INVALID_EVIDENCE` retains any identity, projection, hash, attack or independent-replay failure.

Even an admitted R1 does not close Gate 0 or authorize B58. It only permits the next preregistered repeated-observation phase.
