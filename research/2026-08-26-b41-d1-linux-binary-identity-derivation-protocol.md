# B41-D1 · Linux Blender executable identity derivation protocol

Status: preregistered before derivation tooling or output.

B41-C3 proved that the guest buildx path creates amd64 layers and authenticates the official Blender archive, then falsified a cross-platform identity assumption: the Dockerfile expected the local macOS Blender executable hash for a member extracted from the Linux x64 archive.

B41-D1 asks only for the Linux member identity. It downloads the exact frozen official archive, checks its exact byte count and SHA-256, requires the member path `blender-5.2.0-linux-x64/blender` exactly once, and derives the member byte count and SHA-256 through two paths: host bsdtar streamed into Node, and GNU tar streamed inside the existing Colima guest. Both results must agree. The first 64 bytes must identify an ELF64, little-endian, x86-64 executable.

The executable must not run. Docker image build and container run are prohibited in this derivation. The temporary archive must be removed. Eight preregistered mutations must fail with their intended reason before the identity can be used by a later correction.

This derivation cannot establish Blender runtime compatibility, render success, timeout enforcement or containment. It also does not rewrite the historical macOS identity.
