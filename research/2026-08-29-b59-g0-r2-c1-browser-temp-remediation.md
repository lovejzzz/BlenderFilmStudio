# B59-G0-R2-C1 · Runtime transition correction and browser temporary-filesystem remediation

Date: 2026-08-29
Status: EXECUTED AND VERIFIED
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

## Execution record

Executed at approximately `2026-08-29T04:08Z` using depth-first deletion on each exact preregistered `t` path; no recursive wildcard or parent-directory deletion was used.

- Target directories found and removed: `16/16`
- Target directories remaining: `0/16`
- Available bytes immediately before: `107,018,625,024`
- Available bytes immediately after: `153,958,375,424`
- Reclaimed bytes: `46,939,750,400` (about 43.72 GiB)
- `File System` size after: `20` KiB
- R2 disk threshold: `112,206,020,608` bytes
- Immediate post-remediation headroom: `41,752,354,816` bytes (about 38.89 GiB)

Preservation checks passed for `File System/Origins`, `models--Qwen--Qwen3-4B`, GPT Bot `Pilots`, and `.colima`. The formal R2 root remained absent during remediation.

## Disposable shadow rehearsal

After the remediation and code correction, a disposable spec variant redirected output to a non-formal rehearsal root. It returned `ADMITTED_FOR_LIGHTWEIGHT_WORK`, `20/20` gates and `25/25` attacks with no failed gate. Observed values included one new main PID (`26962`), old PID absent, Codex-tree RSS `3,917,840,384` bytes, available disk `153,939,959,808` bytes, and current version `26.825.32147 (7303)`.

Before deletion, the rehearsal result hashes were:

- `results.json`: `05f21b6783f7513b3c426b1fb0dcf53833ba1054644fabb5f2435c0d125013ba`
- `audit.json`: `e89347afbd4b3da5584e21deba061c3f2c6286bec2a9aafb17b7b51b9660bf71`

The disposable root was then removed and the formal spec restored byte-for-byte to its committed form. The formal R2 root remained absent. The rehearsal proves tool-path coherence only; it is not admission evidence.
