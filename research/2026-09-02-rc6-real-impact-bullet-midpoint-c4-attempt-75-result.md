# RC6 real-impact Bullet midpoint C4 attempt-75 result

Date: 2026-09-02

I09 is a retained physical `FAIL`. It derived contact at frame 19 and reached
45° at frame 33 and 90.00° peak, but maximum cup-surface motion was
`0.09684143 m/frame`, requiring 11 Preview-96 effector subframes. Its visible
surface swept to x=`1.04133344 m` and z=`-0.01656712 m`, outside the accepted
domain and below the frozen floor threshold. Counts were one Blender start,
one Bullet bake and zero liquid/render/save/build/network/write operations.

Together with I08, this proves that once the unconstrained cup crosses the
tipping transition, speed interpolation does not reduce the maximum falling/
landing surface step. Do not scan another striker speed. The next physical
diagnostic is the cup's exact Bullet collision margin/congruence; a separate
simulation-tier/domain decision may follow only after that check.

The first independent audit is retained at 22/23. Its sole false check is still
configuration representation: Vector fields now use tolerance, but
`baseVoxelMeters=0.0093749998` was compared with `0.009375` at `1e-10`.
All physical metrics, hashes, logs, processes, manifests and side-effect checks
pass. Close this with a zero-Blender audit-only correction; never rerun or edit
attempt-75.
