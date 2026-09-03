# C33 C1 attempt-113 — explicit missing-codec rejection

Freeze commit: `536504cf44efc113af2cda96bd67ee9299384229`.
Result self hash: `16c736570609f6451454cb4d2018e00b46a4c3eb521042e6bd1fbf16bffb58b8`.

Canonical header ordering passed. One helper build took 9.372 seconds; all
eleven synthetic processes returned their expected success/rejection codes.
The complete 108-file C29 cache copy was verified. Reading copied frame1 then
rejected with `Cannot create attribute of unregistered type int32_trnc`.
No later real frame was read. Total runner time was 10.356 seconds, peak child
RSS 898,088,960 bytes. There were zero Blender/bake/render/engine operations.

The failure is a reader codec-registration gap, not corrupt fluid data. Bound
RC5 `extern/mantaflow/preprocessed/fileio/iovdb.cpp:397–400` explicitly
registers Mantaflow's truncated int, float and Vec3s attribute types. OpenVDB
initialization alone in the observer did not reproduce those registrations.
The original fixtures covered half scalar storage but used uncompressed
particle attributes, so they did not exercise this real-cache requirement.

Preserve attempt-113 work/evidence bytes. C2 adds those three existing codec
registrations and one truncated-particle fixture to the versioned helper,
with a corresponding independent known-value/hash check. Fresh attempt-114
uses the unchanged finite-volume/field oracle, copy strategy and resource
ceilings. This adds format coverage; it does not relax a threshold, change a
physical setting or permit any Blender start.
