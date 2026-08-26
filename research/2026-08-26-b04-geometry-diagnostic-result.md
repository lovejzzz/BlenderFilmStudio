# B04 evaluated-geometry diagnostic v0.2 — result

Date: 2026-08-26  
Status: executed negative result  
Classification: `V01_AUTOMATIC_PASS_INSUFFICIENT_FOR_CONTACT_QUALITY`

## Result

The stronger diagnostic falsified the idea that B04's v0.1 automatic pass was sufficient evidence of acceptable contact.

| Phase | Frames with tessellated surface overlap | Maximum triangle pairs | Maximum inside-vertex depth proxy |
| --- | ---: | ---: | ---: |
| APPROACH | 0 / 36 | 0 | `0 m` |
| ACQUIRE | 9 / 12 | 25 | `0.068334341 m` |
| HOLD | 60 / 60 | 25 | `0.018445877 m` |
| RELEASE | 3 / 12 | 25 | `0.066128865 m` |
| RETREAT | 0 / 24 | 0 | `0 m` |

The minimum exact unsigned surface separation was `0.094780169 m` during APPROACH and `0.605083734 m` during RETREAT. During every HOLD frame the surfaces intersected, so unsigned separation was zero. Three evaluated hand vertices were classified inside the prop at representative HOLD frames 48, 78, and 108.

The maximum HOLD depth proxy, `18.445877 mm`, is 3.69 times the v0.1 contact position tolerance of `5 mm`. The v0.1 contact metric measured socket alignment, not surface quality; both values can be correct simultaneously.

## Terminology correction

The v0.1 evaluator constructed a BVH from source polygons with `all_triangles=False`; its overlap indices referred to source polygon faces. The v0.2 diagnostic explicitly called `Mesh.calc_loop_triangles()` and built a triangle BVH with `all_triangles=True`. Counts between versions must not be compared as if they used the same primitives.

## What remains unknown

The inside-vertex method is still only a proxy. It can miss edge/face crossings with no contained vertices, and ray parity assumes closed well-formed meshes. It is not:

- exact minimum translation distance;
- penetration volume;
- signed distance field;
- contact force, pressure, friction, or weight;
- visual acceptance.

## Consequence

B04 remains incomplete for two independent reasons:

1. human review has no collected responses;
2. the stronger automatic diagnostic detects material HOLD interpenetration.

The next implementation must change the grasp representation or geometry, not merely loosen thresholds. Candidate directions are a hand/prop contact shell, finger-level rig and authored grasp pose, or a robust signed-distance/collision proxy validated against labeled intersections.

## Primary references

- [Blender 5.2 geometry utilities](https://docs.blender.org/api/5.2/mathutils.geometry.html)
- [Blender 5.2 BVHTree utilities](https://docs.blender.org/api/5.2/mathutils.bvhtree.html)
- [Blender 5.2 Mesh API](https://docs.blender.org/api/5.2/bpy.types.Mesh.html)
