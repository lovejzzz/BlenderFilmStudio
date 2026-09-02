# RC6 obstacle-voxel screen attempt-39 retained failure

Status: **FAIL_PREBAKE**

The first Preview baseline process opened the exact source scene and stopped before any fluid Data bake. The harness enabled FLIP particle export, updated the view layer, and incorrectly required Blender to create the display particle-system roster immediately. On this fresh unbaked source Blender retained zero systems at that boundary; the display system is created only after Data exists or during later evaluation.

No cell produced a physical result. Counts were one Blender start, zero Data bakes, zero Mesh bakes, zero saves, zero renders, zero network calls and zero engine writes. The remaining two cells did not start. Attempt-39 is retained and must not be reused.

The C1 correction is narrow: observe the coherent pre-bake roster, enable FLIP particle export and 100% display, run the already-frozen Data bake, and only then require one evaluated particle system. The three cells, physics settings, cache roster, interpretation table, resource ceilings and claim ceiling remain unchanged.
