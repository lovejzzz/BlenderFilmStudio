# RC6 slow-tip Bullet screen C1 attempt-48 result

Date: 2026-09-02  
Verdict: `FAIL_BULLET_SCREEN`; execution and independent audit valid

The exact C1 direct-contact screen completed in 3.47 seconds. Its receipt hash
is `1dcc09d1e995f1a369b1e803379172e4dde08f1ebbf8c1998149c4b48b55b234`.
The independent audit passed 18/18 with audit hash
`1d7b4187e501111dc29a8e4b5164eb8dd6750d1a7d6412c86917fc8511832e45`.
All four runs were Bullet-only; fluid, render, save, network and engine-write
counts remained zero.

The exact mesh-vertex correction worked. Across the four cells the minimum
actual cup-surface z was only about `-0.69` to `-1.22 mm`, safely above the
unchanged `-5 mm` floor gate. The prior transformed-bound-box values were not a
valid cylinder-surface measurement.

The direct upper-half actuator contacted at frames 10/12/14/16 and required
only 3/2/2/2 derived effector subframes. It nevertheless translated the free
cup horizontally instead of tipping it: peak tilt was
`0.99327509° / 1.53046242° / 1.68875943° / 1.77343381°`. No cell reached the
unchanged 45-degree response gate.

C2 must add a small passive rigid-body toe stop at the cup base, with a
measured positive initial gap and solver-observed stop contact before the
45-degree response. This creates a real pivot for the existing slow upper-cup
force. It may not constrain or animate the cup, lower the tilt gate, add a final
pose, or begin fluid work. Attempt-48 remains immutable.
