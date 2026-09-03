# C33 reader readiness — no new fluid bake

Preregistered 2026-09-03, after accepted C32, before attempt-112 roots.
This gate implements a trusted read-only cache observer, not a new physics
setting. The formal spec and tool hashes must be committed before execution.

The bundled OpenVDB Python API exposes scalar/vector grid access but not
point-attribute handles. One read-only, no-file-output API inspection confirmed
that limitation. A small arm64 C++ observer will link the existing exact RC5
OpenVDB/TBB libraries. This is one bounded diagnostic-helper compilation,
not an engine build; the 160 GiB clean-engine admission remains closed.

Scope: one helper compile, eleven synthetic VDB fixtures, reads of those
fixtures and one complete verified copy of retained C29's 108 cache files.
Read all 36 copied Data frames, recording finite-grid velocity hashes, decoded
particle positions/velocity/flags, attribute codecs and actual cache field
roster/precision. No Blender, bake, render, save, engine mutation or network
inside the formal gate. Never mount a retained cache in Blender.

The helper hashes sorted particle rows (index-space position XYZ, stored
particle velocity XYZ, flag U), preserving duplicates but ignoring storage
ordering; the voxel transform is separately validated and bound. Scalar and
vector values are hashed over the finite metadata dimensions in Z/Y/X order.
Each numeric value is canonical little-endian binary64 with positive zero;
nonfinite numbers reject. Hashes are exact decoded-data descriptors, not a
tolerance-based physical equivalence assertion. No exact mass claim follows.

Synthetic acceptance must independently check all three particle rows and
their hash; changing position, particle velocity or flag while keeping the
same number of occupied cells must change the decoded hash. Changed velocity
grid values must change their hash. Finite negative phi volume must count both
active and inactive negative tiles, exclude zero background, and respond to a
single sign change. Half-storage roundtrip must preserve this exactly
representable synthetic field. Missing point attributes, NaN, zero dimensions
and inconsistent transforms must reject with no partial JSON result.

The copied real cache must remain exact before and after reading. Python's
existing OpenVDB accessor independently recomputes every velocity value hash
in all 36 frames; it may not stand in for point-attribute tests. The retained
two-grid roster establishes absence of native phi in these files. Report
observed codecs/storage precision, distinguishing effective non-resumable
export from an unrecorded RNA boolean. Do not infer native volume from old
files lacking phi, and do not pretend C33 readiness proves cache passivity.

Resources: 100 GiB reserve plus 512 MiB workspace and 16 MiB evidence;
helper compile timeout 180 seconds, each reader timeout 60 seconds, overall
runner budget 900 seconds. Stop on a failed build/test/read; retain evidence
and never repair a frozen root. Any correction receives a new version/root.
Successful readiness permits preparing, not silently starting, the separately
frozen Data-only native-field experiment on the same R40 project.
