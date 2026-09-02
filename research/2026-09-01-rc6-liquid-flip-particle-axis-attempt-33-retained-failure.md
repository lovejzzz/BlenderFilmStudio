# RC6 cached FLIP particle axis attempt-33 retained failure

Attempt-33 stopped before measurement because its scene tool required both
`use_flip_particles == false` and an empty domain particle-system roster. The
copied baked scene did not satisfy that combined assumption. Blender reported
the error before changing the setting or reading a particle position.

This is a harness failure, not evidence that particles do or do not cross the
cup floor. The one Blender start performed zero data bakes, mesh bakes, saves,
renders, network calls and engine writes. After the process, all 23 copied
candidate files and 32,362,945 bytes remained byte-exact with the immutable
source candidate; the copied root contained no symlinks or render media.

Attempt-33 is immutable. A fresh C1 attempt may correct only the initial
particle-roster observation and handling. It must preserve the same candidate,
frames 1–7, resolution 192, particle and mesh settings, cup measurements,
strict and one-voxel classifications, resource ceilings, and zero
bake/save/render/network authority.
