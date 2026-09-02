# RC6 C5-C3 attempt-55 retained base-audit failure

Date: 2026-09-02

Runner receipt: `PASS_BULLET_SCREEN`

Base independent audit: `FAIL` 17/18

All four frozen HINGE/MOTOR cells completed and passed every physical check.
The receipt selected the slowest, C5F96: peak tilt 60.00240151 degrees,
5-to-45-degree span 63 frames, maximum cup-surface displacement 0.00587031 m
per frame, one derived effector subframe and maximum hinge-pivot drift
0.00000581 m. The receipt self hash is
`903b1d0aaf4a5bdd72c59ec9ece3e7199f50e1382c677df8d71b2120bae11e68`.

The only base-audit failure is `metricsIndependentlyRecomputed`. Its exact
cause is an audit-only representation comparison: Blender serialized the
authored domain dimensions as float32
`[0.8999999761581421, 0.5, 0.5799999833106995]`, while the auditor required
literal JSON equality with `[0.9, 0.5, 0.58]`. Every other independent metric,
identity, process, resource and zero-authority check passed. Base audit self
hash is `3f3c310887b7b39805923199f0c14c26b5aa652064fbca85ed40e27645280f80`.

Retain the base audit unchanged. A C5-C4 audit-only correction may replace only
that literal domain-dimension equality with a per-axis `1e-6` float32
representation tolerance, write a new audit path and perform zero Blender,
Bullet, fluid, render, save, build or network work.
