# RC6 real-impact passive-ramp C9 preregistration

Date: 2026-09-02

Impulse and floor-friction tests mainly translated the corrected cup. C9 moves
to the missing physical variable: contact moment arm.

The exact lane top is z=0.22 m, the ball radius is 0.12 m and the cup rim is
z=0.44 m. A fixed passive convex wedge begins on the lane at x=-0.26 and ends
at x=0.04, rises 0.06 m over 0.30 m (11.31°), and is 0.40 m wide. Its end
surface is z=0.28, so Bullet—not animation—can lift the ball center from 0.34
toward 0.40 m, about 40 mm below the rim.

This categorical passive ramp is the one selected physical degree of freedom.
The ball receives no animation. I09 speed, cup friction 0.75, explicit 2 mm
margin, all masses, domain, Bullet quality and acceptance thresholds remain
exact.

Run R60 once and retain PASS or FAIL. Require the ball center at derived contact
to reach at least 0.38 m, the cup to reach 45° by frame 48, floor/domain gates
to pass, and the measured surface motion to require no more than eight
Preview-96 subframes. One Blender/Bullet run is allowed; liquid, render, save,
build, network and engine writes remain zero.
