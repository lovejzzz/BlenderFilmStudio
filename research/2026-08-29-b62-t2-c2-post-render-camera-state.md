# B62-T2-E1-C2 · Post-render camera state is not an application receipt

Date: 2026-08-29
Status: PREREGISTERED — v0.2 retained; no C2 tool changed; v0.3 absent

## Retained result

C1 v0.2 is invalidated at the same first-cut boundary as v0.1: 97 PNGs, one Blender process, no budget breach, no complete render report or scientific verdict. The immutable root is 100 files, 25,861,042 bytes, tree SHA-256 `0428f1e9c1eb5be89f453e8bccdc5d7f25824955bbee4bb54d0f90676e393489`.

The intervention did have an observable effect. v0.2 frame 97 SHA-256 is `610094ea…`, while v0.1 frame 97 is `ce1dbf3c…`; direct labeled inspection also shows different rendered state. Therefore C1's explicit pre-render camera assignment was not a no-op.

## Invalid assumption

C1 captured `scene.camera` only after `bpy.ops.render` returned and required that mutable property to remain the applied medium camera. Blender's render/context evaluation may restore or reevaluate scene state. That post-operation property is not a receipt for which camera was explicitly selected immediately before rendering.

C2 keeps the strong precondition: derive the latest marker, verify exact marker and bound camera, assign `scene.camera`, and assert it immediately before the render call. The frame report records those captured pre-render identities. After the call, the immutable PNG header/hash/size are the valid output receipt. Independent Blender still derives routing directly from the source marker roster, and both cut pairs must still produce different decoded pixels.

Only the invalid post-render assertion is removed. All 288 frames must be regenerated in fresh v0.3; no prior PNG is reused. No scientific threshold or budget changes.
