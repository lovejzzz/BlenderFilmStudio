# PC.2 attempt-01 retained pre-mutation canonicalization failure

Attempt-01 stopped in its first Blender process before any action keyframe insertion, save or render. The accepted PC.1 camera/light sentinel object was structurally unchanged, but its canonical SHA differed solely because Node and Python spell scientific-notation exponents differently. Source SHA remained exact and the work root contains no files.

C1 may only bind and read the accepted PC.1 `build.json` by exact file SHA, then compare `protectedStateAfter` structurally. It may not change any camera/light value, action phase, amplitude floor, authorized target, geometry/material rule, operation count or resource ceiling. A fresh attempt-02 is required.
