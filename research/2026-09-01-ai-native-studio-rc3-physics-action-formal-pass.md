# RC3 physics-native action formal pass

Date: 2026-09-01

RC3 passes the clean-build formal stage. Candidate
`5f595fe3aca7118847aec5b572f6d90a377a4352` was cloned locally without
network materialization, built once as a native arm64 application, and used for
both D1 and H1 by the same restricted physics-action compiler.

The formal receipt is
`c50e703b3469b3bda8324fe7e96f981dbb084da12f7eaea869f0d0fa0719eebe`.
The C2 independent audit passes 32/32 with hash
`3393593ef723aa6ee22689f063d8257c47713b1a92c33edb7eed311d1f2f4585`.
The fresh formal direct review passes all ten frozen questions with hash
`49926ce8219196866f6ee16f4445916ede5a24ea8e280f1d70b71b47326b2e91`.

The build produced binary SHA-256
`c071ce0dd63b7c0a1a422c0ade55329e54339b318933564baae1cd4137eb2ca4`.
D1 contact and first response remain frame 52; its shutter peaks at
98.80388412 degrees. H1 contact and first response remain frame 16; all three
bottles respond and settle at approximately 90, 90 and 0 degrees. The
asymmetric two-down/one-upright result is preserved as solver output, not
normalized into a more dramatic pose.

One frozen audit-tool failure is retained: the v0.1 auditor read inherited
resource limits from the v0.2 fixture correction and raised a `KeyError` before
writing an audit. C2 corrected only that lookup in a new audit root and did not
rerun the build, Blender, physics or renders. Because formal still files were
not byte-identical to the development visual packet, the formal images were
inspected afresh; both complete formal videos were byte-identical to their
previously reviewed counterparts.

This pass establishes a reusable, product-integrated Bullet action grammar
across two different mechanisms. It does not establish photoreal asset quality,
liquid slosh, deformation, debris, sound or finished-film realism. Those remain
the next project lesson and must preserve zero authored outcome/event fields and
zero post-release pose keys.
