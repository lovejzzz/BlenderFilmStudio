# B39 · Linux worker architecture preflight result

Verdict: `X64_INDEX_IDENTITY`  
Status: `REJECTED_PROTOCOL_ASSUMPTION`  
Runtime operations: `0`

## What was preregistered

B39 froze a read-only preflight before tool implementation. The positive gate required the official x64 filename to occur exactly once in the Blender 5.2.0 release-index response, while separately requiring its byte count and checksum-manifest identity. It also froze the expected absence of an official Linux ARM64 artifact, exact host/Colima/Docker architectures, required Docker security-option metadata, disk admission and 15 analyzer attacks.

Protocol commit: `59b7344b020ae98a7cdf2a6868b0a6c0365bf141`  
Tool freeze commit: `10bcf1348093809929d6fb891ac310a083143f23`  
Spec SHA-256: `06645fda0af4778f487893a9a1881fa749d06e4774559bf975034ec49140e30f`

## Measured result

The runner executed the eight allowed read-only probes and no runtime operation. It observed:

- x64 filename raw-text occurrences: `2`, not the frozen `1`;
- x64 byte count: `384441228`, matching the frozen official value;
- x64 checksum occurrences: `1`;
- x64 SHA-256: `96f6c181a30f4950607839dc84d42a354b250d8a0231b098b59b7bc69c351c48`, matching;
- Linux ARM64 filename/index/checksum occurrences: `0 / 0`;
- host / Colima / Docker architectures: `arm64 / aarch64 / aarch64`;
- required Docker metadata: AppArmor, builtin seccomp and cgroup namespace present;
- available bytes: `19703353344`;
- free after the frozen 20 GiB projection: `-1771483136`;
- disk admission: `BLOCKED · DISK_RESERVE`;
- runtime operations executed: `0`.

The directory index contains the filename once as the hyperlink target and once as visible link text. The raw substring cardinality gate was therefore false even though filename, byte count and checksum identity agreed. Because route classification intentionally depended on that gate, the x64 route remained `REJECTED_ARTIFACT_OR_HOST_IDENTITY` rather than the expected `IDENTIFIED_BUT_RUNTIME_BLOCKED`.

## Independent audit

The audit independently reproduced both analysis failures:

- `X64_INDEX_IDENTITY`
- `EMULATED_ROUTE_DECISION`

It also showed that all 15 mutated candidates would be rejected, but the accepted result recorded no attacks because the base positive gate failed. Therefore `recordedAttacksMatch=false` and the audit verdict is correctly `FAIL`, not a promoted attack result.

Result SHA-256: `b4e709f565427fe96478c29bf9ca21c2ea93d7d1e5fb45828f498d6e71728e73`  
Audit SHA-256: `16b081cf56731bbc2f99e817ec9d64440244718caf6cf6ec99846472e674c2b5`

## Interpretation

This run falsifies the preregistered raw-occurrence assumption. It does not falsify the official x64 artifact identity, because byte count and checksum matched independently. It also does not promote the ARM64-absence or x64-emulation route to an accepted B39 conclusion, because the combined gate failed.

The correction must be preregistered after this failure. It will distinguish raw text occurrences (`2`) from exact hyperlink-target occurrences (`1`) and retain all other gates unchanged. The original result and audit remain immutable evidence.

## Non-claims

No Blender archive was downloaded. No Blender process, container, image build, pull, create or run occurred. No native ARM64 impossibility, x64 compatibility, Eevee/EGL, containment, performance or production-backend claim is made.
