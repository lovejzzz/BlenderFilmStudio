# RC6 slow-tip Bullet screen attempt-47 result

Date: 2026-09-02  
Verdict: `FAIL_BULLET_SCREEN`; execution and independent audit valid

Attempt-47 completed the exact four frozen Bullet-only cells in 3.41 wall
seconds. The receipt self hash is
`ef2987187a59b25bcff494e78445a911c962d6a871020fd5fb6b0a3b88de5a64`.
The independent audit passed 18/18 with audit hash
`d195987858e1ec0c41edbe02d1b0464d9c06e4fac72a7974dc9e04a0e363f8e3`.
There were four Blender starts and four narrow Bullet bakes, with zero fluid
bakes, renders, blend saves, network calls or engine writes.

All four causes reached or nearly reached the cup and stayed inside the
candidate liquid-domain sweep. Their measured moving-effector requirements
were modest: D12/D16 required five subframes and D20/D24 required four. The
failure was not a Mantaflow sampling or domain-size problem.

The indirect ball cause became too weak when slowed:

- D12 contacted at frame 26 and peaked at `10.14016409°`.
- D16 contacted at frame 35 and peaked at `14.66776048°`.
- D20 contacted at frame 44 and peaked at `9.28755558°`.
- D24 contacted at frame 52 and peaked at `7.24868238°`.

None reached the frozen 45-degree slow-tip response, so no cell was selected.
D12–D20 also crossed the strict `-5 mm` minimum world-bound check by only
`1.0–4.3 mm`; that secondary observation does not repair the missing tilt and
the threshold remains unchanged.

The corrective hypothesis is not to lower the response gate or pose the cup.
Slow-container validation needs a dedicated low-speed physical contact fixture
that applies torque above the cup center of mass while Bullet continues to own
all cup transforms. The final basketball impact remains a later, separate gate.
Any C1 must use new roots, retain attempt-47 unchanged, and preregister the
direct-contact geometry before another solve.
