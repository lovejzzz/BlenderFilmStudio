# B40-R2 · Worker host capacity re-admission result

Verdict: `WORKER_HOST_CAPACITY_ACCEPTED_REPLAY_STABLE`  
Independent audit: `PASS`  
Attacks: `16/16`  
Replay diagnostics: `111` (`evidence`, `analysis`, `attack vector`)  
Runtime operations: `0`

## Measured result

| Gate | Observed | Frozen requirement | Result |
|---|---:|---:|---|
| Host available | `139029028864` B | 20 GiB projected write, then ≥100 GiB reserve | ACCEPTED |
| Host free after projection | `117554192384` B | ≥`107374182400` B | ACCEPTED |
| VM memory | `12513595392` B | ≥10 GiB | ACCEPTED |
| VM online CPUs | `6` | ≥5 | ACCEPTED |
| Docker filesystem available | `14767869952` B | ≥8 GiB | ACCEPTED |
| VM swap | `0` B | exactly zero | ACCEPTED |
| x64 emulator | `/usr/bin/qemu-x86_64`, `POCF` | enabled, exact interpreter, required flags | ACCEPTED |
| Running containers | `0` | exactly zero | ACCEPTED |

The decision had no blocked reasons. All 16 frozen mutation attacks were rejected with their expected primary failure code. JSON-canonical evidence, analysis and attack-vector comparisons were all equal, and the independent audit reproduced the exact recorded attack vector.

## Intervention context

Before preregistering B40-R1/R2, the user explicitly authorized deletion of re-downloadable caches and LTX model data plus expansion of the existing Colima profile. Host disk utilization fell from 98% to 86%, and Colima changed from 4 CPU / 6 GiB / 10 GiB to 6 CPU / 12 GiB / 20 GiB. This result is therefore a non-blinded, confirmatory post-intervention admission.

## Non-claims

- No container or Blender process ran in B40-R2.
- The accepted capacity decision does not prove linux/amd64 Blender compatibility under aarch64 emulation.
- It does not prove Eevee/EGL operation, performance, image validity, containment or reproducibility.
- B41 requires a separately frozen runtime protocol and may still fail.

Machine evidence: `experiments/worker-host-capacity-readmission-v0-2/results.json`  
Independent audit: `experiments/worker-host-capacity-readmission-v0-2/audit.json`
