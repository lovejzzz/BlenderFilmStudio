# B59-G0-R3-D2 · Controlled Colima disk A/B closeout

Date: 2026-08-29  
Verdict: `OPERATIONALLY_RESTORED / INVALID_FORMAL_EVIDENCE`  
Evidence root: `experiments/codex-host-disk-colima-ab-v0-1`

## Outcome first

The authorized temporary interruption is complete. The `default` profile is running again with the same `aarch64` architecture, Docker runtime and `virtiofs` mount type. All four original full container IDs, names, images, restart policies and `AutoRemove=false` values are present and running. Colima restored them automatically; the experiment issued zero explicit container starts.

No prune, delete, compact, recreate, image/volume mutation, signal, model call or network call was performed. One graceful stop and one normal start were issued.

The run is not valid formal causal evidence. It deliberately remains failed because one preregistered restoration predicate was technically wrong: Colima normally regenerates its internal Lima runtime YAML during start, so byte-for-byte identity of that derived file is not a valid definition of restored service state.

## Transition receipts

| Event | UTC time | Duration | Exit | Confirmation |
|---|---:|---:|---:|---|
| Formal start | 2026-08-29 05:14:14 | — | — | Initial manifest matched |
| `colima stop default` | 2026-08-29 05:15:14 | 13.590 s | 0 | Profile stopped; Docker socket unavailable |
| `colima start default` | 2026-08-29 05:16:28 | 12.891 s | 0 | Runtime matched; 4/4 exact IDs running |
| Final guard | 2026-08-29 05:17:43 | — | — | Operational state restored; derived YAML hash differed |

## Disk observations

Positive values below mean the host gained available space.

| Phase | Span | Host available-space change | VM disk allocated change | Data disk allocated change |
|---|---:|---:|---:|---:|
| `ACTIVE_BASELINE` | 60.001 s | +1,015,808 B | 0 B | 0 B |
| `STOPPED` | 60.003 s | +1,094,262,784 B | 0 B | 0 B |
| `RESTORED` | 60.002 s | +161,163,218,944 B | +3,960,832 B | +18,071,552 B |
| Whole sampled window | 207.646 s | +171,732,672,512 B | −2,600,960 B | −3,205,554,176 B |

The whole-window sparse-file reduction includes transition effects between phases, whereas each phase row compares only its first and last sample. The host recovered roughly 171.7 GB, but the two tracked Colima files explain only about 3.21 GB of reduced APFS allocation. APFS purgeable-space accounting, delayed reclamation or another untracked system mechanism must account for most of the difference. This is a strong operational recovery observation, not a quantitative attribution.

None of the three phases showed the preregistered 64 MiB material-loss condition. If the data were evaluated descriptively without the failed restoration predicate, the frozen label would be `NO_MATERIAL_LOSS_REPRODUCED`.

## Restoration comparison

Preserved:

- `default` running; `aarch64`; Docker; `virtiofs`
- Four exact full container IDs running, with the same names, image, restart policy and auto-remove setting
- `/Users/tianxing/.colima/default/colima.yaml` SHA-256 `861be8798…`
- VM disk device/inode/logical size `16777233 / 224554643 / 21474836480`
- Data disk device/inode/logical size `16777233 / 224554600 / 21474836480`

Expected derived-file rewrite:

- `/Users/tianxing/.colima/_lima/colima/lima.yaml`: `59daf66c…` before stop → `29ffdf82…` after normal start
- The file is part of the generated Lima instance state. Colima also regenerated sibling runtime artifacts during the same start.

Because the original generated YAML content was intentionally not copied into evidence, semantic equality of old versus new cannot be reconstructed after the fact. The conservative response is to reject the formal verdict, retain all evidence, and define any future restoration gate around authoritative user configuration plus observable service semantics.

## Evidence integrity

The fresh root contains `start.json`, nine self-hashed samples, two self-hashed transition receipts, `recovery.json`, and `failure.json`. It contains no `results.json` or `audit.json`, which correctly prevents this attempt from being mistaken for passing evidence.

Key SHA-256 values:

- `start.json`: `7c1325d5ecf35694e17b84605898b3922608ea4e6c759b52f0086150058d7866`
- `transition-stop.json`: `40cf5c498e86d4afff21bc5bc0435a80757f7922aac08fa8f89913e42006c1cc`
- `transition-start.json`: `652c478f2557df4e2277bbc9acc013ac8f40bb57951181f7b107b35a54ce7185`
- `recovery.json`: `15a2d4f3b9028ddf24012cc45de62eb93a15c64edcd1c86a1fc16aa456ce0f12`
- `failure.json`: `7a69715a21f40889f6310b0c853c12a2b1a1b100aec065c91398d3e27e995bb3`

## Next admission decision

Do not repeat the interruption merely to manufacture a passing formal result: the stop/start already changed the host's free-space regime materially. First run the ordinary post-intervention disk-retention observation against the now-restored workload. Only if material loss recurs should a v0.2 A/B be preregistered, with generated Lima files treated as observed transition artifacts rather than immutable source configuration.
