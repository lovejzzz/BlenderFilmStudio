# B41-D1 · Guest derivation silently hashes an empty stream

Verdict: `DERIVATION_AGREEMENT`  
Accepted attacks: `5/8`  
Blender/image/container operations: `0`

The official archive matched `384441228` bytes and SHA-256 `96f6c181a30f4950607839dc84d42a354b250d8a0231b098b59b7bc69c351c48`. Host bsdtar found the exact member once and streamed `174666336` bytes with candidate SHA-256 `83e8261eace07a5337f71b52d156c1eece1a6ba913403cc6406182ae58bacf27`. Its first 64 bytes decoded as ELF64, little-endian, machine code 62 (`x86-64`).

The Colima guest path returned the SHA-256 of an empty stream and zero bytes. Post-run inspection showed GNU tar 1.35 supports `-J` but the minimal Colima guest has no `xz`/`unxz` program. The frozen POSIX `sh` pipeline had no `pipefail`; downstream `sha256sum` and `wc` exited successfully and masked tar's decompressor failure. Therefore the host candidate cannot be promoted from this run.

The analyzer rejected at `DERIVATION_AGREEMENT`. Five early attacks reached their intended primary reason; the remaining three were shadowed by the same base failure. Independent audit matched tool identities and reproduced `5/8`, therefore also failed.

B41-D1-C1 may replace only the guest archive-member implementation with Colima's installed Python 3 standard-library `lzma`/`tarfile` path and structured fail-closed output. Archive identity, host derivation, ELF gates, zero-execution boundary and attacks remain unchanged.

Result SHA-256: `ce7337fcf966434085856a959909baea729b0a529855789c69496c23e43b7a1a`  
Audit SHA-256: `6d49a9fddcde0129e8ccdad72deabee612ac58a4f21ff3231549a1ff41123f2d`

Artifacts: `experiments/linux-amd64-blender-binary-identity-derivation-v0-1/`.
