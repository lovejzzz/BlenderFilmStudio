# RC6 Final effector Mesh C2 attempt-45 retained failure

Attempt-45 is retained as `FAIL_PREADOPTION_DATA_RESET`. The canonical-path
correction passed and the first Blender process started, but it stopped in
1.08292 seconds before cache-state adoption, save or Mesh bake. Reconstructing
the exact Data-bake scene settings and binding the copied cache triggered
Blender's normal Data reset callbacks, which removed the copied 14-file cache.
The accepted retained attempt-42 cache remained byte-exact and the second
process never started.

The process self hash is
`260305d15c7a260fc49c6c924ca9d624b3e21758233e8d0fc053c35487b74be5`.
The stderr file SHA-256 is
`cb3ca1d639a74c1eadd270c7ebc2cddf1da6fb04eaf187005668d710130a741d`.
The immutable failure evidence-root manifest hash is
`939499efed78782ea3facdf7486ef3b87a461a5faaca551696969fc2e956c656`;
the post-failure work-root manifest hash is
`a6770491e6a29d9738a1d33c6cb5561a525da02da895b53cd7f8aa0b46202aeb`.

The smallest next correction changes only materialization order: keep the
verified copied Data in a staging directory, reconstruct every reset-triggering
scene property against an empty final cache directory, materialize the exact
14 files only after configuration and cache binding, then set the baked-Data
state bit and save. No Data bake is required or permitted.
