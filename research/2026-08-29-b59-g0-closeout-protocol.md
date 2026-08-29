# B59-G0 · Gate 0 host-stability closeout protocol

Date: 2026-08-29
Status: COMPLETE — GATE 0 CLOSED
Parent commit: `378765dee04313178936ad68ba593623691ab764`

## Decision question

Does the complete retained evidence establish that the recovered host can support the next bounded B58 preflight without recurring browser/Colima/evidence-write disk exhaustion, while an active capacity warning system and a tested operational recovery path remain available?

This is a closeout of the host-safety prerequisite only. It is not a Blender production-quality result and does not bypass any of the three production gates.

## Required positive evidence

- R2: a different post-restart Codex main PID passed 20/20 gates and 25/25 attacks.
- R4: seven post-reclaim samples over at least 12 minutes passed 15/15 gates and 20/20 attacks, including disk, RSS, browser and crash continuity.
- R5-C1: the active 15-minute capacity sentinel passed 10/10 gates and 15/15 attacks, remains installed byte-exact and performs no automatic cleanup or restart.
- R6-C1: the complete one-hour unattended history passed 12/12 gates and 15/15 attacks with the frozen 250 GiB floor and 1 GiB/hour host-loss ceiling.

## Required negative-evidence preservation

R3's disk-loss failure, R5-v0.1's redundant-kickstart failure and exact rollback, and R6's 14/15 invalid audit must remain present and hash-exact. Closeout fails if any is deleted, relabeled or treated as admission.

D2 remains a formal failure because Colima regenerated `_lima/colima/lima.yaml`. Closeout may recognize only the narrower operational recovery facts encoded in the retained receipts: one confirmed stop and one confirmed start, the profile running again, the exact four container IDs and metadata restored without explicit starts, the authoritative `colima.yaml` unchanged, and both sparse-disk identities preserved. The generated Lima hash must remain visibly different. This does not establish Colima as the cause of the earlier disk loss.

## Live boundary

At closeout, launchd must still report the exact label, 900-second interval and last exit 0; the latest self-hashed sample must be no more than 1,200 seconds old, `HEALTHY`, at least 250 GiB available, browser allocation below 64 MiB, no alert, and bounded history. The installed plist must equal the repository template.

Codex must remain version/hash/bundle exact with exactly one main process at PID 26962, started before the R6 cutoff, and no new `ChatGPT*.ips` report after that cutoff.

## Evidence discipline

The runner is read-only except for a fresh, exclusive formal receipt. It may call only bounded `git`, `launchctl` and `ps` reads; Blender, Docker, network, models, cleanup and service mutations remain zero. An independent auditor must re-read every parent artifact and live boundary, replay all 15 gates and reject 20 directed attacks. Every attack names the gate it must flip so rejection cannot be credited only to an unrelated hash failure.

Only 15/15 gates and 20/20 attacks establish `GATE0_HOST_STABILITY_CLOSED`. Passing permits a separate minimal B58 preflight. It does not authorize a Blender render until that preflight itself passes.

## Recorded outcome

The formal runner passed all 14 pre-audit gates. The independent auditor passed 15/15 final gates, all eight integrity/live checks and 20/20 directed attacks. Final verdict: `GATE0_HOST_STABILITY_CLOSED`.

At audit time the sentinel was `HEALTHY`, latest age 882,411 ms, available space 319,742,877,696 bytes, browser temporary allocation 20,480 bytes and no alert. Launchd remained loaded with five runs, 900-second interval and last exit 0. Codex remained PID 26962 with the expected version/hash/bundle and no new crash report. No Blender, Docker, network, model, cleanup or service mutation occurred.

Results and audit SHA-256 are `588da9723eb7cfd7c611e2eb8122da1e6d29a93bee19e55c36eae85fbf0db54a` and `6d3a372f5fc3f07a3a154d22b8e9d124b264a8d4532db2fd5a777f3ed6395af7`. Gate 0 closure permits only the separately gated B58 minimal preflight.
