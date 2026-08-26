# B41-C3 · Colima guest buildx correction protocol

Status: preregistered before correction tooling or output.

B41-C2 proved that the host legacy builder silently executed ARM64 layers despite the requested amd64 platform. The existing Colima VM exposes buildx `v0.34.1`, Docker-driver builder `default`, BuildKit `v0.30.0`, and `linux/amd64` support on the same Docker Engine. The repository and temporary build context are visible at the same absolute path through virtiofs.

B41-C3 changes only the build transport to `colima ssh -- docker buildx build --platform linux/amd64 --pull --load --progress plain`. Dockerfile, archive, base digest, tag and context are unchanged. Runtime launch remains bound to the explicit host Colima socket and the frozen B41 contract.

No builder installation or creation is allowed. A build, load, platform, Blender, render, isolation, timeout or audit failure remains a valid rejection.
