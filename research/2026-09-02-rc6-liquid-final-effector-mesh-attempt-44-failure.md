# RC6 Final effector Mesh attempt-44 retained failure

Attempt-44 is retained as `FAIL_PREMESH_CACHE_STATE`. Its single Blender
process exited without a Mesh bake, Data bake, save or render after 1.194838
seconds. The exact copied 14-file Data cache passed admission, but the source
blend had never been saved after the accepted Data bake. Reconstructing the
same transforms and settings and rebinding the copied cache therefore left
`has_cache_baked_data=false`; Blender then removed the copied cache during
process teardown. The retained accepted attempt-42 cache remained byte-exact.

The process self hash is
`cd45f418c7f783534e84da1a6e953a7a65f8af8984d79b062a7f94f4e4c7d797`.
The stderr file SHA-256 is
`9ee8397a4d2cc13070096289882394e85d1c8af5742a503cfc7edfb4f29821bc`.
The immutable failure evidence-root manifest hash is
`ee25a750b8f047d7344a5c0c6548acd23b496e7c45e0490fd84c37b040473a35`;
the post-failure work-root manifest hash is
`92a11306b195baaea647551868949459e07bd083462fa7532c3abae8f09c35ca`.

Local source inspection shows `has_cache_baked_data` is the RNA view of the
`FLUID_DOMAIN_BAKED_DATA` cache flag. The smallest correction is not another
Data solve: after independently verifying an exact copied Data manifest and
reconstructing the exact scene state, set that flag through RNA, verify its
readback, save the adopted Data state, and only then invoke one Mesh bake.
The correction must use fresh roots and fail if any Data byte changes.
