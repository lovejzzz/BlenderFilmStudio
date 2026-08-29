# B62-Q1-D5-C4 · Quaternion record-primitive alignment

Date: 2026-08-29  
Status: PREREGISTERED — v0.3 retained; no C4 tool change exists yet

Fresh v0.3 passed every gate except D4 pose reproduction. All nine evaluated camera locations matched the D4 bake, all six geometry rows matched, and both D5 implementations agreed. The 36 remaining mismatches were the four quaternion components on nine frames.

This is a same-orientation, different-record-primitive problem. D4 serialized the assigned Blender object property `corrected.rotation_quaternion`. C2 serialized a quaternion reconstructed from `camera.matrix_world`. Blender's reconstruction normalizes through float32 matrix arithmetic, shifting components by roughly `6e-8–1.8e-7`. Raising the frozen `1e-9` tolerance would conceal this representational mismatch and is forbidden.

C4 authorizes only a like-for-like record change: keep evaluated world-matrix location, but record the post-synchronization object property as `assignedCameraQuaternion` and compare it with D4's `correctedQuaternion`. The camera transform used by projection and ray casting is unchanged. Both Blender tools must make the independently written equivalent change, and the full 14×9 search must run again in fresh v0.4.
