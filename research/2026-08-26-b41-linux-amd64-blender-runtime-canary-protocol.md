# B41 · Linux/amd64 Blender 5.2 runtime canary protocol

Status: preregistered before tooling, image build, Blender archive download or runtime.

## Question

Can the official Blender 5.2.0 Linux x64 artifact run under experimental QEMU-backed `linux/amd64` emulation on this admitted ARM64 Colima host while preserving the frozen B38 worker boundary? The positive canary must produce a real 32×32 Eevee PNG. A separate negative canary must ignore SIGTERM, reach the 30-second wall limit, receive SIGKILL after five seconds and remain non-promotable.

## Identity and transport

All Docker calls bind directly to `unix:///Users/tianxing/.colima/default/docker.sock`; the mutable global Docker context is not evidence. The official archive must match exact URL, filename, byte count and SHA-256 before build. The runtime image must be resolved to and launched by its `sha256:` image ID with `--pull never` and `--platform linux/amd64`.

## Frozen runtime boundary

The container has a read-only root, no network, UID/GID 65532, no capabilities, no-new-privileges, a 256 PID ceiling, 8 GiB memory ceiling, four-CPU quota, 1 GiB shared memory, one read-only input mount, one writable output mount, and tmpfs-only `/tmp` and `/work`. Blender receives background, factory-startup, disable-autoexec, offline-mode and Python exit-code flags without a shell.

The success script must test identity, environment, filesystem, network and cgroup controls before saving a `.blend` and rendering one Eevee frame. The timeout script is a separate attempt and its outputs are never promotable.

## Interpretation

The strongest accepted verdict is `LINUX_AMD64_BLENDER_5_2_CANARY_AND_TIMEOUT_SUPPORTED`. It remains an experimental compatibility/containment canary—not a production backend, performance claim, stress test, cinematic-quality result or determinism claim.
