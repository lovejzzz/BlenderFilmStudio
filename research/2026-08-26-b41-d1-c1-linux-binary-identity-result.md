# B41-D1-C1 · Accepted Linux Blender executable identity

Verdict: `LINUX_AMD64_BLENDER_EXECUTABLE_IDENTITY_DERIVED`  
Independent audit: `PASS`  
Attacks: `8/8`

## Measured result

The official Blender 5.2.0 Linux x64 archive matched:

- bytes: `384441228`;
- SHA-256: `96f6c181a30f4950607839dc84d42a354b250d8a0231b098b59b7bc69c351c48`;
- executable member: `blender-5.2.0-linux-x64/blender`, exactly once.

Host bsdtar streamed the member into Node. Colima Python 3.12.3 independently opened the same xz-compressed tar member through its standard library. Both paths measured:

- executable bytes: `174666336`;
- executable SHA-256: `83e8261eace07a5337f71b52d156c1eece1a6ba913403cc6406182ae58bacf27`.

The first 64 bytes identified ELF64, little-endian, machine code 62 (`x86-64`). The temporary archive was removed. The exact operation list contained only archive download and the two member streams; Blender, Docker image and container operations were absent.

All eight mutations failed at their preregistered reason. Independent audit matched current tool hashes, replayed the exact attack vector and passed.

## Boundary

This Linux hash is now eligible to be frozen in a separately preregistered B41 runtime correction. It does not itself prove that Blender launches under qemu, renders Eevee, honors the container restrictions, or obeys the timeout contract. It does not replace any historical macOS Blender hash.

Result SHA-256: `407a327462ecc50e62df28b138e6073095f9816594974883209917b016e44d3c`  
Audit SHA-256: `37c9adaf857840774db5ed8584b049b0f4958d5119286b2f995676a912c1ea54`

Artifacts: `experiments/linux-amd64-blender-binary-identity-derivation-v0-2/`.
