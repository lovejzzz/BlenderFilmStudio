# B39-C1 · Release-index parser correction protocol

Status: `PREREGISTERED_CORRECTION_BEFORE_V02_TOOLING_OR_OUTPUT`  
Date: 2026-08-26  
Parent failure: B39 `X64_INDEX_IDENTITY`

## Correction boundary

Rejected B39 assumed that the official x64 filename would occur once in the raw HTML response. The accepted evidence instead recorded two occurrences: one inside the exact link target and one as visible link text. Byte count and official checksum agreed, so this is a parser-cardinality defect rather than evidence that the x64 artifact identity changed.

B39-C1 changes exactly one assumption:

- old: raw filename occurrences must equal `1`;
- corrected: raw filename occurrences must equal `2`, and exact `href="blender-5.2.0-linux-x64.tar.xz"` target occurrences must equal `1`.

The rejected result and audit are bound into the correction spec by SHA-256. They remain unchanged.

## Gates held fixed

All other gate families remain unchanged: official URL identity, filename, byte count, checksum-manifest occurrence and SHA-256; absence of the Linux ARM64 filename/link/checksum; host, Colima and Docker architectures; Docker security options; eight-probe trace; zero runtime operations; disk reserve; native-route rejection; best-effort x64 classification; pending digest-pinned image; and separate B40 preregistration.

The corrected parser extracts hyperlink targets structurally with an exact quoted `href` pattern. It does not infer identity from visible text alone.

## Execution and attacks

After this commit, a new v0.2 library, runner and independent audit will be created without modifying the v0.1 toolchain or evidence. The runner may repeat only the same eight read-only probes. It may not download the Blender archive or execute a runtime operation.

Fifteen attacks are frozen, beginning with restoration of the rejected `raw=1` assumption and removal/fabrication of href targets. Every mutated candidate must receive a fresh evidence self-hash so an attack cannot pass merely because the original hash was stale.

## Accepted verdict

The strongest accepted result is:

`ARCHITECTURE_PREFLIGHT_CORRECTION_SUPPORT_RUNTIME_BLOCKED`

It supports a corrected architecture/artifact preflight only. It does not establish Blender x64 execution, Eevee/EGL, render compatibility, containment, performance or production readiness. B40 stays pending until the 100 GiB reserve plus 20 GiB projection gate is satisfied.
