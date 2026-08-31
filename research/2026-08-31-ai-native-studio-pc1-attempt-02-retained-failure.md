# PC.1 attempt-02 retained final-audit failure

C2 completed the actual modeling increment: 26 semantic details, three procedural material regions, 104 objects / 92 meshes / 19,810 polygons, six successful renders, zero retained EXR, exact camera/light/action state, and visible change in all three protected views. The runner and Blender semantic audit passed.

The final Node auditor rejected 17/18 because `build.json` was hashed using Python's `1.0` numeric spelling while JavaScript reserialized the same value as `1`. Python independently verifies the stored hash; this is a cross-language canonicalization failure, not a product or image failure. Attempt-02 remains FAIL and is sealed. C3 may only normalize integer-valued floats before writing the build record and use fresh attempt-03 roots; all product and quality thresholds remain unchanged.
