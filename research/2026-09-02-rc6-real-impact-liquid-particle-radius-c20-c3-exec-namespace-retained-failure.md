# RC6 C20 C3 — retained audit execution-namespace failure

Date: 2026-09-02
Status: retained harness failure after admission; no scientific verdict

C3 bound the corrected parent OID, verified the retained attempt-94 manifest and
created fresh attempt-96 with one admission file. Its generated audit then ran
with separate globals/locals mappings. A generator expression resolved function
globals and could not see the top-level `source_volume` local, raising
`NameError` before writing an audit.

No Blender, bake, render, save, build, network, engine write or retained-root
write occurred. Attempt-96 is immutable. C4 may change only the execution call
to construct one shared environment dictionary and pass it as both globals and
locals. Expanded audit bytes, `2e-8` centroid replay, `1e-8` volume replays,
physical checks, retained hashes, claims and ceilings remain unchanged.
