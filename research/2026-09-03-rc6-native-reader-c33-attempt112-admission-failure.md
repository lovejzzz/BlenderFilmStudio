# C33 attempt-112 — retained pre-root admission failure

Execution freeze: `590f529efa772e31845c9a153438bdf22ceee2a8`.
The runner exited at line 54 while hashing dependency header trees. Neither
formal work nor evidence root was created. Helper compiles, fixtures, copied
cache files, helper reads, Blender starts, bakes and renders were all zero.
The terminal traceback is the observed execution record, not a fabricated
saved process log.

Independent read-only recomputation found identical file contents and counts:
OpenVDB219, TBB144, Imath35. Only ordering differs for TBB. Python Path sorting
compares path components; the preregistration's JavaScript sorts complete
relative-path strings. The runner produced
`4d1f174b9d6750dc9806cb47c9233f6d159aed5ba347b113a5fb238135beeb2d`,
whereas sorting those exact same TBB rows by their relative-path string yields
the frozen expected
`2cf6d9facc50fd7f555c2fbdef0a02b06ae5b9c0645b00b54b401f3c736aca9b`.
The other two header-tree hashes already match under both conventions.

Retain the v1.23 spec and all three frozen tools unchanged. Do not reuse
attempt-112. C1 may only normalize manifest rows by complete relative-path
string and route the same reader, fixtures, tests and limits through a new
v1.24 spec and fresh attempt-113 roots. The C++ reader and independent numeric
oracle are unchanged; no physical setting is involved.
