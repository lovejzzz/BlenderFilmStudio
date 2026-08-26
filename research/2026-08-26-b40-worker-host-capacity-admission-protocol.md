# B40 · Worker host capacity admission protocol

Status: `PREREGISTERED_BEFORE_TOOLING_OR_OUTPUT`  
Date: 2026-08-26  
Scope: read-only host/VM/daemon capacity admission; no Blender or container runtime.

## Why B40 exists

B39-C1 identified the official Linux x64 artifact as a later best-effort emulation candidate, but architecture availability alone is insufficient. B38 froze an 8 GiB memory ceiling, four CPUs, 1 GiB shared memory and a 20 GiB projected host write. The current Colima VM is configured for only 6 GiB memory and four CPUs. Its Docker data filesystem reports about 4.64 GB available.

A cgroup memory/CPU ceiling is a maximum, not a reservation. Configuring a container ceiling greater than its VM capacity cannot demonstrate that the ceiling is safely available, and giving a worker all VM CPUs leaves no explicit infrastructure headroom. B40 therefore freezes a host-admission policy before any runtime image is built.

## Evidence ancestry

The protocol binds by SHA-256:

- B38 launch-contract spec, result and audit;
- B39-C1 corrected architecture-preflight result and audit.

If any ancestor file changes, B40 is invalid rather than silently adopting the new bytes.

## Frozen capacity policy

The later B41 candidate requires:

- host: `available - 20 GiB >= 100 GiB`;
- VM memory: frozen 8 GiB worker ceiling + 2 GiB infrastructure reserve = 10 GiB total;
- VM CPUs: frozen four-worker-CPU ceiling + one infrastructure CPU = five CPUs;
- Docker storage: at least 8 GiB free before the trusted image build;
- VM swap: zero;
- active competing containers: zero;
- `qemu-x86_64`: enabled with `/usr/bin/qemu-x86_64` and required `POCF` flags.

The 2 GiB, one CPU and 8 GiB figures are explicit BFS operational safety policies. They are not presented as Blender system requirements or exact consumption forecasts. The Docker storage floor covers archive, extraction, package layers, final image and rollback uncertainty; B41 must later record actual peak and final sizes.

## Frozen probes

After this protocol commit, B40 may read only:

- host filesystem availability;
- `colima status --json` and the existing Colima YAML;
- VM `/proc/meminfo`, online CPU count, Docker filesystem `df` and registered binfmt entry through read-only `colima ssh` commands;
- Docker running-container IDs;
- ancestor file hashes.

It may not mutate Colima, invoke a container lifecycle operation, download Blender, build/pull/prune/delete an image, launch Blender, clean disk or override a reserve.

## Expected current result

Four gates are preregistered as blocked:

1. `HOST_DISK_RESERVE`;
2. `VM_MEMORY_CAPACITY`;
3. `VM_CPU_CAPACITY`;
4. `DOCKER_STORAGE_CAPACITY`.

Zero swap, enabled x64 emulator and zero running containers are expected to pass. Overall admission remains `BLOCKED`; runtime-operation count remains zero.

## Attacks and promotion

Fourteen analyzer attacks are frozen, covering lowered reserves, false acceptances, hidden containers, fabricated emulation, changed ancestry, runtime-execution claims and overall promotion. Each attack receives a fresh evidence self-hash.

The strongest accepted verdict is `WORKER_HOST_CAPACITY_BLOCKED`. B40 cannot become an accepted runtime experiment later. After the external capacity state changes, a new clean admission plus separately preregistered B41 is required.

## Non-claims

B40 does not establish Blender x64 compatibility, Eevee/EGL availability, performance, determinism, containment or production fitness. It does not authorize reconfiguring Colima or deleting any Docker/user data.
