# B59-G0-R2-C1 · Runtime transition correction and browser temporary-filesystem remediation

Date: 2026-08-29
Status: PREREGISTERED — remediation not yet executed
Formal R2 root at registration: absent

## Trigger

After the user-performed Codex restart, the restart boundary and 4 GiB Codex-tree RSS gate passed, but two newly observed preconditions prevented a valid formal R2 run:

1. Codex had upgraded from crash version `26.820.80927 (7271)` to current version `26.825.32147 (7303)`.
2. Available disk was `107,022,958,592` bytes, below the frozen R2 minimum of `112,206,020,608` bytes by `5,183,062,016` bytes.

No formal R2 directory was created before this correction.

## Version correction

Crash provenance and current-runtime identity are separate claims. The R2 spec therefore freezes `currentRuntimeExpectation.codexVersion` to `26.825.32147 (7303)` while leaving `crashEvidence.version` unchanged. The runner and auditor use the current-runtime field when present and retain the crash-version fallback for the already completed baseline and R1 experiments.

## Read-only storage diagnosis

The previously removed pnpm, Gradle, Bun, npm `_npx`, and `Movies/CacheClip` caches remained absent. Hugging Face occupied about 12.4 million KiB, primarily explicitly preserved Qwen models, and is excluded from remediation. GPT Bot pilots, Colima data, project media, and repository evidence are also excluded.

The dominant removable anomaly was:

`~/Library/Application Support/Codex/Default/Partitions/codex-browser-app/File System`

It occupied `45,837,380` KiB. Fourteen historical numbered buckets (`005`–`008`, `011`–`020`) each occupied approximately `3,271,068`–`3,271,076` KiB, with two small buckets (`009`, `010`). Their payloads are under Chromium temporary-filesystem directories named `t`; the largest payloads repeat identical file-size patterns across buckets. The latest large-bucket payload predates this session. This is consistent with leaked/repeated in-app-browser temporary assets rather than durable browser identity or project data.

## Exact remediation boundary

Delete only the contents and directories matching:

`~/Library/Application Support/Codex/Default/Partitions/codex-browser-app/File System/{005,006,007,008,009,010,011,012,013,014,015,016,017,018,019,020}/t`

Preserve:

- `File System/Origins` and its LevelDB metadata;
- browser cookies, history, login data, Local Storage, IndexedDB, Service Worker state, and session state;
- all Hugging Face/Qwen data;
- GPT Bot, Colima, BlenderFilmStudio, and user media;
- every path outside the exact `t` directories above.

The operation is an out-of-band remediation under the user's prior cache-cleanup authorization. It is not part of the formal R2 resource accounting. Afterward, record the exact post-cleanup available bytes and verify all targeted `t` paths are absent before deciding whether R2 may run.

## Fail-closed rule

Do not create the formal R2 root unless all of the following hold simultaneously: exact target deletion verified; available disk meets the frozen threshold; the old PID is absent; one new Codex main PID exists; current runtime matches the corrected expectation; scoped release files are committed and equal to `origin/main`; and all remaining preflight gates are satisfiable.
