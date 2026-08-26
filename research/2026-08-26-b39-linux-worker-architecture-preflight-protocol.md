# B39 · Linux worker architecture preflight protocol

Status: `PREREGISTERED_BEFORE_TOOLING_OR_OUTPUT`  
Date: 2026-08-26  
Scope: read-only architecture and artifact admission; no Blender/container/image runtime.

## Why this experiment exists

B38 froze a backend-agnostic `WorkerLaunchPlan`, but left the backend unbound. The next proposed backend was a disposable Linux worker on the local Colima VM. A read-only inventory now exposes a prior architectural question that must be answered before any container can be treated as a Blender candidate:

- the macOS host is `arm64`;
- Colima uses `macOS Virtualization.Framework` with an `aarch64` Linux VM;
- Docker reports `aarch64` and the existing Debian/Alpine images are `arm64`;
- the official Blender 5.2.0 release index lists `blender-5.2.0-linux-x64.tar.xz`, but no Linux ARM64 archive;
- the official checksum manifest binds that x64 archive to SHA-256 `96f6c181…351c48`.

Therefore B39 is not yet a containment test. It is an architecture preflight that prevents an x64-emulated route from being silently described as a native or production route.

## Frozen question

On this Apple-Silicon host, is there a native official Blender 5.2 Linux worker route? If not, is the official x64 artifact sufficiently and immutably identified to justify a later, separately preregistered best-effort emulation canary?

## Primary sources

- Blender 5.2.0 official release index: <https://download.blender.org/release/Blender5.2/>
- Blender 5.2.0 official SHA-256 manifest: <https://download.blender.org/release/Blender5.2/blender-5.2.0.sha256>
- Blender 5.2 LTS release page: <https://www.blender.org/releases/5-2/>
- Docker Apple-Silicon known issues: <https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/known-issues/>
- Docker rootless mode boundary: <https://docs.docker.com/engine/security/rootless/>

The Docker documentation describes `linux/amd64` on Apple Silicon as emulation and recommends native ARM64 images where possible; it also characterizes Intel-image execution as best effort. B39 freezes that limitation rather than treating emulation support as compatibility evidence.

## Frozen observations to re-measure

The post-preregistration runner may perform only the exact read-only probes listed in `specs/linux-worker-architecture-preflight.v0.1.json`. It must re-fetch the two small official text/index resources, inspect host/Colima/Docker identity, inspect only already-present base-image metadata, and read filesystem availability. It may not invoke `docker run`, `create`, `build`, `pull`, `exec` or any Blender process.

The runner must not download the 384,441,228-byte Blender archive. Filename, size and checksum-manifest identity are sufficient for this preflight; archive-byte verification belongs to a later admitted build stage.

## Frozen routes

### Route A · official native Linux ARM64

Accept only if the exact filename `blender-5.2.0-linux-arm64.tar.xz` appears in the official release index and the official manifest binds it to a SHA-256. The preregistered expected result is `REJECTED_NO_OFFICIAL_ARTIFACT`.

This rejection is narrow: it means Blender Foundation did not publish that artifact in the frozen 5.2.0 index. It does not mean an ARM64 source build is impossible.

### Route B · official Linux x64 under emulation

Identify the route only when the filename, byte count and SHA-256 all match the frozen official values. It remains `EXPERIMENT_ONLY_BEST_EFFORT_EMULATION`, never “native”, “compatible” or “production”. A real runtime canary additionally requires recovered disk admission and a separately built, digest-pinned worker image.

The preregistered current decision is `IDENTIFIED_BUT_RUNTIME_BLOCKED`.

## Disk and runtime gate

The same fail-closed rule from B38 remains authoritative:

`availableBytes - 20 GiB >= 100 GiB`

At preregistration time the host has only about 18 GiB available. B39 must record the real observation; it may not lower the reserve. Runtime-operation count must remain exactly zero.

## Analyzer and attacks

After this protocol commit, a pure classifier will reproduce both route decisions and reject 15 frozen evidence mutations, including fabricated ARM64 artifacts, altered official hashes, architecture relabeling, missing security options, disk overrides, hidden runtime execution and premature B40 completion.

An independent audit must reload the frozen spec and result, recompute the self-hash and replay all attacks. Analyzer code, runner and audit must be frozen in a later clean commit before accepted output exists.

## Decision and non-claims

Support requires every frozen gate plus all 15 attacks. The strongest possible B39 result is:

`ARCHITECTURE_PREFLIGHT_SUPPORT_RUNTIME_BLOCKED`

That result would support only the architecture decision. It would not support Linux runtime compatibility, Eevee/EGL operation, render equivalence, containment, production selection or performance. B40 remains a separate real-backend experiment after disk admission recovers.
