# B41-C2 · Build and receipt tooling correction protocol

Status: preregistered before correction tooling or output.

B41-C1 verified the official Blender archive but stopped because the legacy Docker builder rejected `--progress`. Its receipt also demonstrated self-hash, OCIO collation and correction-tool URI defects. B41-C2 changes only those four operations: remove the unsupported progress arguments, exclude `evidenceHash` from self-hashing, sort OCIO paths by raw UTF-8 bytes, and bind correction hashes to correction URIs.

The archive, Dockerfile, base digest, disk gate, launch contract, Eevee result, forced timeout, audit and non-claims remain frozen. A new failure beyond these corrections is retained rather than repaired inside the run.
