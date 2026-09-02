# RC6 obstacle-voxel screen C1 attempt-40 retained failure

Status: **FAIL_POSTBAKE**

The first Preview baseline completed its exact seven-frame Data bake in 87.65 seconds and produced the complete 14-file config/Data cache. It then stopped before measurement because no FLIP display particle system remained.

A separate zero-write source inspection established that the source `.blend` opens with `use_flip_particles=true` and exactly one particle system. Blender 5.2's `rna_Fluid_flip_parts_update` callback is toggle-style: when the property is assigned and a FLIP system already exists, the callback deletes the system and clears the particle-type bit. The scene harness's unconditional `settings.use_flip_particles = True` therefore removed the valid existing system even though the assigned Boolean value looked unchanged.

No physical particle result was produced. Counts were one Blender start, one complete Data bake, zero Mesh bakes, zero saves, zero renders, zero network calls and zero engine writes. The remaining two cells did not start. Attempt-40 and its complete first-cell cache are retained and will not be reused.

C2 changes only roster handling: require the measured coherent `true/one` initial state, preserve it without reassigning the property, run the unchanged Data bake, and then require one evaluated particle system. The cells, physics, exact cache roster, thresholds, interpretation table and resource ceilings remain unchanged.
