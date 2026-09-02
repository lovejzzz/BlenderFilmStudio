# RC6 slow-tip Bullet screen accepted by C5-C4 composition

Date: 2026-09-02

Verdict: `PASS_BULLET_SCREEN`

The accepted result is the complete C5-C3 attempt-55 physical receipt composed
with the append-only C5-C4 audit-only correction. All four frozen cells passed;
the preregistered slowest-passing rule selected C5F96 at 15.15789474 degrees
per second.

C5F96 reached 60.00240151 degrees, took 63 frames from 5 to 45 degrees, moved
the measured cup surface at most 0.00587031 m per frame, required one derived
effector subframe and held maximum hinge-pivot drift to 0.00000581 m. It passed
floor, one-voxel domain-margin, mechanical-stop, constraint-identity and zero-
pose-key checks. The complete run used four Blender starts and four Bullet
bakes with zero fluid, render, save, build, network or engine-write work.

The retained base audit is 17/18 only because it required literal equality
between Blender float32 domain dimensions and decimal JSON. C5-C4 changed only
that representation comparison to `1e-6` per axis; its independent audit passes
18/18 with self hash
`791f7a135436029ff0a09dead17661287eea4035b49b3f554cd4e806924a649b`.
Receipt self hash is
`903b1d0aaf4a5bdd72c59ec9ece3e7199f50e1382c677df8d71b2120bae11e68`.

This accepts one solver-owned slow rigid trajectory for the next separately
preregistered moving-liquid gate. It does not prove moving liquid, real impact,
saved-cache persistence, rendered pixels or finished-film quality.
