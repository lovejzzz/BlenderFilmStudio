# RC6 moving-liquid Preview attempt-56 failure C1 preregistration

Date: 2026-09-02

Status: preregistered before append-only failure closure

Attempt-56 consumed exactly one Blender start, one Bullet bake, one 24-frame
Preview-96 Data bake and one Mesh bake. Blender wrote a self-hashed physical
`FAIL` result: 15/17 checks passed, while source-relative mesh volume reached
36.82% loss and temporal mesh-volume drift reached 34.23%. The liquid otherwise
remained one positive, manifold, fully contained body and moved 35.84 mm in cup
coordinates on the exact C5F96 trajectory.

The scene tool raised its frozen threshold exception after writing the result,
but Blender background mode returned exit code zero. The base runner therefore
stopped on result/process status mismatch before receipt/audit creation. C1 is
strictly audit-only: zero Blender, bake, render, save or network processes. It
may append only a failure receipt, independent audit and two manifests to the
existing evidence root. It must preserve all existing attempt-56 files and the
workspace/cache bytes exactly.

This closure will not change the physical verdict or authorize another bake.
The next physical hypothesis must be versioned after the retained failure is
independently closed.
