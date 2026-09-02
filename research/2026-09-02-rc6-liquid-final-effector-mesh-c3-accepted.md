# RC6 Final effector Mesh C3 accepted

The C3 correction proved cross-process reuse of the accepted resolution-192
Data cache without a Data bake. Retained attempts 44 and 45 remain immutable:
the first showed that an ordinary source blend does not infer baked state from
cache files, and the second showed that reset-triggering scene reconstruction
deletes a pre-populated copied cache.

Attempt-46 reconstructed all physical scene state against an empty final cache,
then materialized the separately verified 14-file Data manifest, wrote
`has_cache_baked_data=true`, saved, reopened that state in a second Blender
process, and performed exactly one Mesh bake. Adoption and first save took
1.727862 seconds; reopen, Mesh and second save took 82.720041 seconds. No Data
bake, render, network call or engine remote write occurred, and every copied
Data byte remained exact.

The fixed resolution-192 surface candidate used simulation particle radius
1.6, mesh particle radius 9.0, upper concavity 3.5 and cup effector distance
2.5 cells. Across frames 1–7 it measured maximum absolute source-volume error
0.04150869, maximum temporal drift 0.02311318, maximum one-voxel cup-exterior
fraction 0.0, maximum connected components 2 and zero non-manifold edges. The
scientific receipt is `PASS_FINAL_EFFECTOR_MESH_C3_STATIC`, self hash
`0363fcda866ba76c6c28e2e8d810d9f405982775ddba72d08740f584808413be`.
The independent audit passed 14/14 with self hash
`a332e8a5d11de4c12ab05052e02353cb687d0b81a05005d8e826ed8f8e3f10bd`.

This closes the static liquid gate and unlocks a slow solver-owned tip. It does
not prove moving-effector behavior, impact, lighting, camera or finished-film
quality. The production pipeline should normally save the baked scene state
inside the original Data process; staged cache adoption is a verified recovery
protocol for a complete immutable cache, not a substitute for normal state
persistence.
