# B59-G0-R3-D2 · Controlled Colima disk A/B protocol

Date: 2026-08-29  
Status: PREREGISTERED — MUTATION NOT YET RUN  
Parent commit: `d1150093beeaf4c74b4d27312622ffe7267ebc49`

## Authority and question

The user authorized temporarily stopping the `default` Colima profile and its four currently running containers, completing a controlled disk A/B, and restoring the original state. D1 observed only 16 KiB of Colima sparse-disk allocation growth during a 91-second window and could not explain R3's 3.33 GB host-space loss. D2 asks whether available-space loss is suppressed while this exact Colima workload is stopped and returns after restoration.

This is a bounded causal intervention, not cleanup. It does not prune, delete, compact, recreate, upgrade, reconfigure, or signal any workload.

## Frozen restore manifest

Immediately before preregistration, `default` was running on `aarch64`, Docker and `virtiofs`. The exact four running container IDs are:

1. `656ace940483450d32802eb98523a50176f741b52df0b2a5b2caa7540edf0be4` — `gpt-bot-agent-f87a4fc4fbb14afd8ea37ba604ce`
2. `baaef476f835b4e68ac8bc183cace91de0675a543dce76f52b84b8d33e617365` — `gpt-bot-agent-98c9350bc46542d3b83780997a00`
3. `2675985ebcd9a4ad4961d72df5c0d146f77eb597fbe38b5ece68c8f8233b1837` — `gpt-bot-agent-aa20bfe304854dfab53bbb5087cc`
4. `0a581b1a626ac0502c3e01d55176ac7f4261c693db12681547bb64e0c06c6470` — `gpt-bot-agent-94812fa95c82484fae4aee414aaf`

All four use image `gpt-bot-agent-computer:2.8`, restart policy `unless-stopped`, and `AutoRemove=false`. The spec freezes both configuration SHA-256 values and both sparse-disk device/inode/logical-size identities. Restoration means the same profile is running with the same runtime and all four exact IDs running again; names alone are insufficient.

## Three-phase design

Each phase captures three immutable samples, each at least 30 seconds apart and spanning at least 60 seconds:

1. `ACTIVE_BASELINE`: the original profile and all four containers are running.
2. `STOPPED`: after one graceful `/opt/homebrew/bin/colima stop default`, the profile is confirmed stopped and its Docker socket cannot enumerate running containers.
3. `RESTORED`: after `/opt/homebrew/bin/colima start default` with no configuration flags, the original runtime and all four exact container IDs are confirmed running.

Every sample records host available bytes; both sparse disks' logical and allocated bytes, modification time and identity; configuration hashes; profile state; and exact container state where the socket is available. The runner writes only bounded evidence inside the fresh formal root.

## Mandatory restoration invariant

The runner encloses every action after initial validation in a restoration guard. Success, failed observation, timeout, or exception all lead to a bounded attempt to start `default`. If Colima's restart policy does not automatically return every frozen container, the runner may issue one `docker start` for each missing frozen ID. It may attempt `colima start default` no more than twice in total and must preserve transition receipts.

No final scientific verdict is valid unless profile runtime, exact container set, configuration hashes, and disk identities are all restored. If restoration remains incomplete, the runner must report it prominently and retain diagnostic evidence; it must never reinterpret a failed restore as a successful experiment.

## Frozen interpretation

For each phase, host loss is first available bytes minus last available bytes. A material loss is at least 64 MiB. A stopped phase is suppressed only when its loss is at most 16 MiB and at most 25% of the active loss being compared.

- `ACTIVE_STOPPED_RESTORED_MATCH`: active and restored phases both show material loss, and stopped loss is suppressed relative to both.
- `ACTIVE_ONLY_STOPPED_SUPPRESSION`: active shows material loss and stopped loss is suppressed, but restored does not reproduce material loss. This is suggestive, not a repeat-confirmed causal result.
- `STOPPED_NOT_SUPPRESSED`: stopped itself shows material loss or is not suppressed relative to an active material-loss phase.
- `NO_MATERIAL_LOSS_REPRODUCED`: none of the three phases shows material loss.
- `MIXED_OR_INCONCLUSIVE`: all other combinations.

Allocated sparse-disk deltas are reported alongside host-space deltas but do not override these preregistered labels. APFS free-space noise, delayed writes and a non-reproduced intermittent event remain valid reasons for an inconclusive result.

## Admission and safety gates

The formal root must not exist before execution. The release-scoped files must be clean, HEAD must equal `origin/main`, and the parent evidence hashes must match. Initial state must match the frozen manifest. The independent auditor replays aggregates, identities, evidence hashes and 13 registered mutations.

A passing evidence audit does not itself prove Colima caused R3. It proves only that the authorized intervention, observations and restoration are intact enough to support the frozen interpretation label. Regardless of label, D2 does not authorize cleanup or relaxation of the R3 disk-retention gate.
