# B41-C2 · Legacy builder platform failure

Verdict: `LINUX_AMD64_BLENDER_5_2_CANARY_FAILED`  
Docker build exit: `1`  
Container/Blender runs: `0`

## What B41-C2 established

- Disk admission passed.
- The official Blender archive again matched exact byte count and SHA-256.
- The OCIO tree matched the preregistered bytewise manifest hash `57f58f25ff919ab2acb214ed42e1a904f32b6c97836aea74c1ec87e13e8e0c16`.
- Correction tool URIs and hashes matched under independent audit.
- The corrected evidence self-hash passed.
- No experiment container remained running and the temporary archive/build root was removed.

## Real build failure

The Docker legacy builder accepted the `--platform linux/amd64` argument syntactically but executed the Dockerfile on an ARM64 base. Its apt trace installed packages labeled `:arm64`. When it attempted to commit intermediate image `sha256:cd3320596f2c...`, Docker rejected it because the produced image did not provide `linux/amd64`.

The local macOS Docker CLI has no buildx plugin. A read-only post-failure probe found Docker buildx `v0.34.1` inside the running Colima VM, connected to the same Docker Engine. The repository path is mounted into that VM through virtiofs.

B41-C3 must change only the build transport: execute `docker buildx build --platform linux/amd64 --load` inside Colima against the same frozen build context, Dockerfile, base digest, tag and Engine. Runtime Docker operations remain bound to the explicit host socket. Every Blender, isolation, render, timeout and audit condition remains unchanged.

Artifacts: `experiments/linux-amd64-blender-runtime-canary-v0-3/`.
