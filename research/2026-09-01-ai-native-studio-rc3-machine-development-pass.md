# RC3 physics-native action graph machine development pass

Date: 2026-09-01

RC3 C3 attempt-03 passes the accepted-binary zero-render development stage.
One unchanged generic module executed two different graphs: D1 used two active
rigid bodies and one hinge; H1 used four active rigid bodies and no constraint.
Both were saved and reopened exactly, and sixteen negative controls rejected.

D1 contact and first response both occur at frame 52. The sphere travels
4.19088622 m with median rolling slip `1.79e-6`; the gate peaks at
98.80388412 degrees and settles from frame 77. H1 contact and first response
both occur at frame 16. All three bottles respond; two finish near 90 degrees
while the third returns upright. The result is intentionally not normalized
into three matching final poses.

Post-release transform keys, authored outcome fields, authored event frames,
light animation channels, arbitrary executable authority, network calls and
renders are all zero. D1/H1 maximum reopen actor-location deltas are
`3.26e-9` / `7.68e-9` m; H1 target tilt delta is `4.99e-9` degrees.
Independent audit is 21/21 PASS with hash
`7dd91b372d9e9c3bffa5d2cc20d6ffb5b6b01e81b0a489578c6282513c4b4382`.

The product candidate is `5f595fe3aca7118847aec5b572f6d90a377a4352`,
sole parent `636f42f28f781f3e858fd5b6bf641910a549c91b`. It changes exactly
`film_studio_physics_action.py` and the Film Studio workspace operator by
881 additions / 5 deletions. Publication remains blocked on direct visual
review and a later clean native formal build.

The next bounded action renders the two already solved/saved scenes without
resimulation or source mutation, then judges their cause/contact/effect stills
and complete contact clips. Machine PASS alone is not a cinematic PASS.
