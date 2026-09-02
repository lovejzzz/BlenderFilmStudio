# RC6 real-impact cup collision-margin C6 attempt-77 result

Date: 2026-09-02

C6 is a retained physical `FAIL` with a clean independent audit of 23/23.
Changing only the cup's collision margin from implicit 40 mm to explicit 2 mm
kept derived ball contact at frame 19 but changed the physical outcome:

- visible floor penetration improved from 16.57 mm to 0.15 mm;
- cup-surface step improved from 96.84 mm to 34.66 mm;
- derived Preview-96 subframes improved from 11 to 4;
- the cup stayed inside the accepted domain;
- peak tilt fell from 90.00° to 2.67°.

The previous dramatic tip therefore depended on a scale-incongruent Bullet
envelope. It is not an acceptable real-impact trajectory. Preserve the 2 mm
margin as the corrected physical baseline and redesign the cause—contact point,
moment arm or impulse—without restoring 40 mm or authoring a cup outcome.

Counts were one Blender start, one Bullet bake and zero liquid, render, save,
build, network and engine-write operations. Receipt/audit self hashes are
`e04832b1…` / `5ae53476…`.
