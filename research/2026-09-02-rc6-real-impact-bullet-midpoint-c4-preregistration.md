# RC6 real-impact Bullet midpoint C4 preregistration

Date: 2026-09-02

Attempt-73 establishes opposite failures around one integer midpoint: I08 tips
the free cup but requires 11 Preview subframes and leaves the accepted domain;
I10 remains inside the cost envelope but peaks below 10°. C4 therefore tests
only `I09`, or `driveEndFrame=9`.

Every other physical value and acceptance threshold remains unchanged from the
audited attempt-73 protocol. One isolated Blender start and one 48-frame Bullet
bake are allowed. There are zero fluid bakes, renders, saves, builds, network
calls and engine writes. A PASS requires derived contact by frame 36, at least
45° solver-owned tilt by frame 48, response after contact, cup-floor and
accepted-domain validity, no ball/cup animation and no more than eight derived
effector subframes.

There is no fallback candidate. PASS or FAIL is retained, and no liquid bake
may begin unless I09 passes an independent audit.
