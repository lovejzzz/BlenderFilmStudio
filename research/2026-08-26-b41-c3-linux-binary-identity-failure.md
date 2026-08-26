# B41-C3 · Guest buildx reaches amd64, then rejects the macOS binary identity

Verdict: `LINUX_AMD64_BLENDER_5_2_CANARY_FAILED`  
Docker build exit: `1`  
Container/Blender runs: `0`

## What B41-C3 established

- The frozen disk admission passed.
- Colima guest buildx `v0.34.1` used BuildKit `v0.30.0` with explicit `linux/amd64`, `--pull` and `--load` on the same Docker Engine.
- The build trace installed Debian packages labelled `:amd64`, correcting the C2 legacy-builder platform failure.
- The official Blender archive again matched exact byte count `384441228` and SHA-256 `96f6c181a30f4950607839dc84d42a354b250d8a0231b098b59b7bc69c351c48` inside the image build.
- No final image, container or Blender process was created, no experiment container remained running, and the temporary build root was removed.

## Falsified identity assumption

The Dockerfile then compared `/opt/bfs/blender/blender`, extracted from the authenticated official Linux x64 archive, to `60ba7a9b6743f7acf101274361fa76409e382ae07cd2007ce07dea30f6b129f2`. That frozen value is the separately measured local macOS executable `/Applications/Blender.app/Contents/MacOS/Blender`, not a Linux executable identity. `sha256sum --check --strict` therefore rejected the extracted file before `blender --version` or either canary could run.

This is a protocol error, not evidence that the Linux archive is corrupt or that Blender cannot execute under emulation. The historical B38 macOS launch contract remains unchanged. A platform-specific Linux identity must be derived from the already frozen official archive under a separate preregistered protocol and then bound by a narrow correction.

## Audit boundary

The frozen C3 independent audit reported `tools=MATCH` but `artifacts=MISMATCH` because its artifact comparator requires runtime PNG and `.blend` objects even when the image build fails before runtime. The audit result remains `FAIL`; it is not rewritten into a pass. A later correction may recognize a valid pre-runtime rejection while continuing to require real artifacts for any successful canary claim.

Result SHA-256: `52030d29021274d5f2ca3444d0d52273ce6faff02661d51483b02cd69119aae6`  
Audit SHA-256: `9a7f8bab1b4ae74a7672494db57baa1994a48807b3bfec615dae35ad954d06b1`  
Build stderr SHA-256: `b09cbb2fa51bb762b21c40edc389509e297c8f6ae629e1ca2e69aecedb3de200`

Artifacts: `experiments/linux-amd64-blender-runtime-canary-v0-4/`.
