# B59-G0-R3-D1 · Disk-loss attribution protocol

Date: 2026-08-29
Status: PREREGISTERED
Parent commit: `e48d9af17f648cab6cfbf2353f28e4d42d079d2c`

## Trigger

Formal R3 preserved Codex RSS, PID, browser temporary storage and crash stability but lost `3,327,586,304` available bytes over 360 seconds. Post-run read-only diagnosis found an active Colima `default` VM with four `gpt-bot-agent-*` containers. Its two sparse disks were modified throughout the R3 window. Container writable layers totalled only about 6.4 MB, so modification time alone does not prove which host allocation consumed the space.

## Question

During a new bounded read-only window, does host available-space loss quantitatively track growth in the allocated APFS blocks of the active Colima sparse disks, or is the loss better explained by the tracked Codex/hostagent files or left unattributed?

## Design

D1 captures four immutable samples at least 30 seconds apart over at least 90 seconds. Each records host available bytes, logical and allocated bytes plus identity metadata for seven frozen files, Colima profile status, active VM-disk opener identity, running container names/count, and self-hash. It performs only read-only status/inspection calls and writes only its bounded formal evidence.

The next due time is anchored to the preceding actual capture, using the R3 C1 correction. Samples cannot be overwritten. Final results bind ordered sample hashes and the blocked R3 evidence; the auditor replays current identities and tests ten mutations.

## Frozen interpretation

Let host loss be first available bytes minus last available bytes. Let Colima growth be the sum of positive allocated-block growth in the active VM disk and data disk. Let other tracked growth be the sum of positive allocated-block growth in the remaining five frozen files.

- `COLIMA_PRIMARY_MATCH`: host loss is at least 64 MiB; Colima growth is positive and at least 80% of host loss; absolute residual between host loss and Colima growth is at most 512 MiB; other tracked growth is less than 20% of host loss.
- `COLIMA_CONTRIBUTION_OBSERVED`: Colima allocated blocks grow, but the primary-match criteria are not all satisfied.
- `OTHER_TRACKED_GROWTH_DOMINANT`: another tracked file group grows more than Colima.
- `NO_MATERIAL_LOSS_IN_WINDOW`: host loss is below 64 MiB and no attribution claim is made.
- `UNATTRIBUTED_HOST_LOSS`: material host loss occurs without matching tracked growth.

These labels describe association within one bounded window, not an internal filesystem mechanism or proof that a particular container payload caused allocation.

## Stop and authority boundary

D1 does not stop Colima, containers or orphaned Lima processes; prune images/volumes; compact sparse disks; delete files; or start Blender. Any such remediation requires a separate exact target and authority decision. Regardless of outcome, the formal evidence is retained and no R3 threshold is relaxed.
