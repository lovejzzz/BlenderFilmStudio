# B39-C1 · Release-index parser correction result

Verdict: `ARCHITECTURE_PREFLIGHT_CORRECTION_SUPPORT_RUNTIME_BLOCKED`  
Audit: `PASS · 15/15`  
Runtime operations: `0`

## Provenance

Correction preregistration commit: `9c4260d527736f9ac5301d12d226b9be6bb080ce`  
Tool freeze commit: `57daa34a510fb83167c5c9cda98cee65f4538091`  
Spec SHA-256: `775ba7436c385cf5175fc3d1e792f25d164dd50d91ff2166f4a3cc30aef4595e`

The correction spec binds the rejected B39 result (`b4e709f5…28e73`) and audit (`16b081cf…c2b5`) and changes only the directory-index cardinality model.

## Corrected artifact observation

Official x64 artifact:

- filename: `blender-5.2.0-linux-x64.tar.xz`;
- raw filename occurrences: `2`;
- exact hyperlink-target occurrences: `1`;
- byte count: `384441228`;
- checksum-manifest occurrences: `1`;
- SHA-256: `96f6c181a30f4950607839dc84d42a354b250d8a0231b098b59b7bc69c351c48`.

Expected official Linux ARM64 filename:

- raw occurrences: `0`;
- exact hyperlink-target occurrences: `0`;
- checksum occurrences: `0`;
- SHA-256: `null`.

The corrected parser requires the exact quoted hyperlink target. Visible text alone cannot establish artifact identity.

## Host and route decisions

Measured host identity remained:

- macOS host: `arm64`;
- Colima VM: `aarch64`, `macOS Virtualization.Framework`;
- Docker engine: `29.5.2`, `aarch64`;
- existing Alpine and Debian images: Linux ARM64;
- security metadata: AppArmor, builtin seccomp and cgroup namespace present.

Route A, official native Linux ARM64: `REJECTED_NO_OFFICIAL_ARTIFACT`. This means only that the exact official 5.2.0 release index and manifest do not list that artifact; source-build feasibility remains open.

Route B, official Linux x64 under ARM emulation: `IDENTIFIED_BUT_RUNTIME_BLOCKED`, class `EXPERIMENT_ONLY_BEST_EFFORT_EMULATION`. It is not relabeled as native, compatible or production.

## Disk admission

Available bytes were `19705393152`. Subtracting the frozen 20 GiB projected runtime write leaves `-1769443328`, far below the 100 GiB reserve. The runner recorded `BLOCKED · DISK_RESERVE`; it did not override or soften the gate.

## Attacks and audit

All 15 freshly self-hashed mutations were rejected, including restoring `raw=1`, removing the exact href, fabricating ARM64, changing size/hash, architecture relabeling, removing security metadata, accepting below-reserve disk, claiming runtime execution, using an unpinned image and marking B40 complete.

The independent audit reloaded the frozen v0.2 spec and evidence, recomputed the analysis, replayed all 15 attacks and matched the recorded attack vector exactly.

Evidence self-hash: `f5cdd05127eb295f0b980d333e6f2422f1e082e4aeccacf47ace91dd8c238f78`  
Result file SHA-256: `1898cca99da9215e4fd394df099417a5324d9405e5d6713711486d21875a1edf`  
Audit file SHA-256: `12b292973eb166aea0eccf2fc071fdc730cec7dc102c2ad3d1297f4a7539edc7`

## Strongest supported claim

A structure-aware, preregistered correction reproduces the official artifact and host-architecture decision without erasing the rejected first run. On this ARM64 testbed, there is no official Blender 5.2.0 Linux ARM64 binary in the frozen release listing; the official x64 artifact is immutably identified but only as a later best-effort emulation candidate, and the real runtime remains blocked by disk admission.

## Next boundary

B40 may be preregistered only after disk admission recovers. It must build and hash a Linux/amd64 worker image, then test actual Blender 5.2.0 identity, x64 emulation, background GPU/EGL availability, B38 mount/env/argv contracts, resource breaches, timeout recovery and a minimal compiler/render receipt.

No Blender archive download, image build/pull, container, Blender process or runtime compatibility test occurred in B39-C1.
