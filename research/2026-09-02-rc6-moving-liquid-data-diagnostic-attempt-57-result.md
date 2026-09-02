# RC6 moving-liquid Data diagnostic attempt-57 result

Date: 2026-09-02

Status: `PASS_DIAGNOSTIC`, classification `DATA_PARTICLE_COUNT_DRIFT_SIGNAL`

Attempt-57 repeated exact attempt-56 physics over frames 1–24 at Preview-96,
disabled only Mesh bake, and exposed 100% of the evaluated FLIP particle roster.
One Blender start, one 0.033-second Bullet bake and one 297.41-second Data bake
completed. The exact 48-file config/Data cache, exact C5F96 trajectory and all
11 harness checks passed. The independent audit passed 18/18 with self hash
`c0cb6268…`; receipt self hash is `9db62ed9…`.

All ALIVE particles remained inside the cup's one-voxel envelope on every frame:
zero radial, below-floor or above-rim outliers. The cup-local particle centroid
moved 41.58 mm. However, the ALIVE roster grew from 8,105 particles at frame 1
to 10,557 at frame 24, a maximum absolute count drift of 30.25%. The frozen
classification is therefore `DATA_PARTICLE_COUNT_DRIFT_SIGNAL`.

This does not prove Data gained 30.25% mass. Mantaflow particle reseeding makes
raw count an invalid exact mass proxy; the opposite directions are decisive:
attempt-57 particle count grew 30.25% while attempt-56 reconstructed Mesh volume
fell 34.23% on the same physics. Particle count alone cannot attribute the loss
to simulation or reconstruction.

The next step is zero-bake capability discovery and then one read-only analysis
of a fresh copy of the immutable attempt-57 Data cache. Prefer a solver-native
liquid level-set/occupancy grid volume across all 24 frames. Do not change
`particle_radius`, `mesh_particle_radius`, thresholds, impact or render state
until the Data-volume measurement exists.
