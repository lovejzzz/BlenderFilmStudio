# B59-G0-R3-D1 · Disk-loss attribution protocol

Date: 2026-08-29
Status: COMPLETED — VALID EVIDENCE, PRIMARY CAUSE UNRESOLVED
Parent commit: `e48d9af17f648cab6cfbf2353f28e4d42d079d2c`

## Trigger

Formal R3 preserved Codex RSS, PID, browser temporary storage and crash stability but lost `3,327,586,304` available bytes over 360 seconds. Post-run read-only diagnosis found an active Colima `default` VM with four `gpt-bot-agent-*` containers. Its two sparse disks were modified throughout the R3 window. Container writable layers totalled only about 6.4 MB, so modification time alone does not prove which host allocation consumed the space.

## Question

During a new bounded read-only window, does host available-space loss quantitatively track growth in the allocated APFS blocks of the active Colima sparse disks, or is the loss better explained by the tracked Codex/hostagent files or left unattributed?

## Design

D1 captures four immutable samples at least 30 seconds apart over at least 90 seconds. Each records host available bytes, logical and allocated bytes plus identity metadata for seven frozen files, Colima profile status, active VM-disk opener identity, running container names/count, and self-hash. It performs only read-only status/inspection calls and writes only its bounded formal evidence.

### Preregistered correction C1: Colima status stream capture

The first disposable rehearsal showed that Colima emits its status lines on stderr. Before any formal D1 root existed, C1 changed the runner and auditor to capture and parse bounded stdout plus stderr from the fixed `colima status` command. Exit status, byte ceiling and command accounting remain enforced. No observation or interpretation threshold changes.

### Preregistered correction C2: quoted log-field boundary

The C1 rehearsal captured the stream but parsed `aarch64"` and `docker"` from Colima's `msg="..."` envelope. Before formal D1, C2 freezes the field token as non-whitespace characters excluding `"`. No expected value or gate changes.

### Preregistered correction C3: aggregate-claim attack sealing

The C2 rehearsal passed all observed gates but A06/A07 were neutralized because the generic resealer recomputed the forged aggregate. Before formal D1, C3 seals those forged result claims without recomputing them, so independent replay must reject the mismatch. No producer or attribution rule changes.

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

## Formal result

The 91.290-second formal window passed 8/8 gates and 10/10 attacks with `VALID_ATTRIBUTION_EVIDENCE`. Its frozen interpretation label was `COLIMA_CONTRIBUTION_OBSERVED`, because the active VM disk allocated 16,384 additional bytes. This is not a primary attribution:

- Host available-space loss: `8,941,568` bytes, below the 64 MiB material-loss threshold.
- Colima allocated-block growth: `16,384` bytes.
- Colima fraction of host loss: `0.00183234` (about 0.18%).
- Other tracked allocated-block growth: `0` bytes.
- `results.json` SHA-256: `37a6306e740ee0549fdfaedb8b2070049fc4af3131fbf1219cebb8a678b6d4d4`
- `audit.json` SHA-256: `d7d78555226c8e73c2c68e86484ee974914ed69c630a49b14fbc6708eab2fce4`

D1 therefore does not explain the 3.33 GB R3 event and does not support `COLIMA_PRIMARY_MATCH`. A controlled running/stopped Colima A/B would have higher discriminatory value, but stopping the four active GPT Bot containers and VM is outside this protocol and requires explicit authority.
