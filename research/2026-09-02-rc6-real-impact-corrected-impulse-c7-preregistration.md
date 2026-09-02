# RC6 real-impact corrected-impulse C7 preregistration

Date: 2026-09-02

## Question

After correcting the cup's hidden 40 mm Bullet envelope to an explicit 2 mm
margin, can the nearest previously bounded higher impulse produce a real,
solver-owned cup tip without reintroducing floor/domain failure or requiring
more than eight Preview-96 effector subframes?

## Exactly one physical degree of freedom

C7 keeps attempt-77's exact scene and corrected margin and changes only
`strikerDriveEndFrame` from `9` to `8`. The same 0.46 m actuator travel then
occurs in seven instead of eight frame intervals, increasing mean speed from
about 1.38 to 1.58 m/s. Cup/ball geometry, mass, friction, contact height,
Bullet quality, domain, frame range and all thresholds remain exact.

This value is the nearest already bounded neighbor, not a scan. The old I08
result under the 40 mm envelope does not predict the corrected-margin outcome.

## Frozen acceptance and stop

The run passes only if contact is derived by frame 36, response follows contact,
the free cup reaches at least 45 degrees by frame 48, the visible cup remains
above -5 mm and inside the accepted domain with one voxel margin, no ball/cup
outcome animation exists, and the measured surface displacement requires at
most eight Preview-96 effector subframes.

Run one fresh Bullet-only cell. Retain PASS or FAIL. Process ceilings are one
Blender start, one Bullet bake and zero liquid bakes, renders, saves, native
builds, network calls and engine writes. Do not tune another value after seeing
the result and do not start Mantaflow unless this trajectory passes.
