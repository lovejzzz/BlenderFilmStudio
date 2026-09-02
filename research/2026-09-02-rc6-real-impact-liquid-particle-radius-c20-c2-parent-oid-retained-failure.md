# RC6 C20 C2 — retained parent-OID admission failure

Date: 2026-09-02
Status: retained harness failure before evidence-root creation

The frozen C2 audit-only tool was invoked once at commit
`ff601314136a6cbd8378b49b7f968191bf4650ac`. It stopped during the outer freeze
check because the spec transcribed its parent as
`ec81581799a18e44e86afc9ba8cc1fad0f6193d9`; the actual parent is
`ec81581796ff708b146b8de8919cdd39b9d2ca3b`.

The failure occurred before attempt-95 evidence-root creation and before the
retained attempt-94 audit was executed. Blender, Bullet, Data, Mesh, render,
save, build, network, engine write and retained-root write counts are all zero.
Attempt-95 remains absent. C20's physical FAIL23/27 and retained20/21 audit are
unchanged.

A versioned C3 correction may change only the parent OID and versioned tool,
spec, preregistration and fresh evidence-root names. Its expanded audit logic,
`2e-8` centroid tolerance, `1e-8` volume tolerances, physical checks, retained
hashes, claim and zero-Blender ceilings must remain exact C2.
