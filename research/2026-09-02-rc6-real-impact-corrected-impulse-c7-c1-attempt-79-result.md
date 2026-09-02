# RC6 real-impact corrected-impulse C7-C1 attempt-79 result

Date: 2026-09-02

C7-C1 is a retained physical `FAIL` with an independent 23/23 audit. Against
the corrected attempt-77 baseline it changed only `driveEndFrame` from 9 to 8,
raising mean striker speed from 1.38 to 1.577 m/s.

- contact moved from frame 19 to frame 17;
- peak tilt changed only 2.67° to 3.19°;
- maximum origin translation rose 30.42 to 34.90 mm/frame;
- maximum surface motion rose 34.66 to 40.83 mm/frame;
- derived Preview-96 subframes rose from four to five;
- floor and domain containment remained PASS.

The additional impulse mainly translated the cup instead of producing a useful
moment. Close striker-speed tuning under the corrected 2 mm margin. Do not
increase speed again and do not start liquid.

Read-only source inspection supplies the next causal hypothesis. Bullet
multiplies the two body friction values. The exact cup/floor pair gives
`0.75 * 0.58 = 0.435`. A simple rigid tipping comparison for the 150 mm base
radius and 340 mm impact height gives `r/h = 0.4412`; the current combined
friction is just below that boundary. A future separately preregistered gate
should return to attempt-77's lower I09 impulse and test exactly one modest cup
friction value above the derived boundary. This is a hypothesis, not a result.

Counts were one Blender start, one Bullet bake and zero liquid, render, save,
build, network and engine-write operations. Result/receipt/audit self hashes
are `142c582e...` / `3f749fd6...` / `2af15f9d...`.
