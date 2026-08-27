# B41-D1-C1 · Fail-closed guest member reader correction

Status: preregistered before correction tooling or output.

B41-D1 authenticated the archive and produced a host ELF identity candidate, but its Colima GNU-tar path needed an external `xz` executable that is absent. A shell pipeline without `pipefail` then converted the decompressor failure into a successful empty-stream hash.

B41-D1-C1 changes only that guest implementation. The already installed Colima Python `3.12.3` standard library must open the same archive in `r:xz` mode, locate the same member, stream its bytes into SHA-256 and a byte counter, emit exactly one JSON object, and exit nonzero on every failure. No package installation, shell pipeline, Blender execution, Docker build or container run is allowed.

All archive, host derivation, ELF, cleanup, operation-boundary and eight attack conditions remain frozen. The parent failure remains immutable.
