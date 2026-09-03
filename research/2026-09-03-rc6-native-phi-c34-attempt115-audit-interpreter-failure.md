# RC6 C34 attempt-115 retained audit-interpreter failure

Date: 2026-09-03

Attempt-115 completed the one authorized uninterrupted exact-C29 Data bake:
36/36 Data frames, 72 exact cache files, one Blender start, one Bullet bake,
one Data bake, zero Mesh, render, save, build, engine write or network call.
The scene checks passed 14/14 and the accepted C33 reader reported decoded
particle and velocity equality on all 36 frames.

The attempt remains `FAIL_RETAINED`, because its independent audit was started
with the runner's Homebrew `sys.executable`, which does not provide the
`openvdb` module. It stopped at import before reading a cache file or writing an
audit result. This is a harness defect, not an accepted scientific verdict.
Both attempt-115 roots are immutable.

C1 may correct only the audit interpreter to the exact RC5 bundled Python
3.13, whose `openvdb` reports library 13.0.0 and NumPy 2.3.4. It may copy five
small evidence records into one fresh evidence-only root and run the unchanged
C34 auditor against the retained work root. It may not start Blender, copy or
modify a cache, rebake, render, change a threshold or write either retained
root.
