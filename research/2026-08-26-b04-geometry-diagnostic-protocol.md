# B04 geometry diagnostic v0.2 — preregistered method

Date: 2026-08-26  
Status: frozen before execution  
Input: compiled B04 run-A scene, evaluated `HAND_R` and `PROP_BODY` meshes

## Question

Does the B04 v0.1 combination of BVH triangle-overlap counts and vertex-to-surface endpoint samples hide a materially deep hand/prop intersection during HOLD?

## Method

For every frame 1–144:

1. obtain deformed meshes from the Blender dependency graph;
2. transform tessellated triangles into world space;
3. retain Blender BVH overlap-pair count;
4. when surfaces do not overlap, compute exact unsigned triangle-surface distance as the minimum of vertex-to-triangle and edge-to-edge distances across every triangle pair;
5. classify evaluated vertices as inside/outside the opposite closed mesh using repeated BVH ray casts in a fixed non-axis-aligned direction;
6. for inside vertices, measure nearest-surface distance and report the maximum as an inside-vertex penetration proxy.

The direction and epsilon are fixed before execution. All results are diagnostics; no new pass threshold is chosen after observing the result.

## Interpretation

- `exactUnsignedSurfaceDistanceM > 0`: surfaces are separated by that distance for these tessellated meshes.
- `overlapPairs > 0`: triangle surfaces intersect, but pair count has no length unit.
- `maxInsideVertexDepthM > 0`: at least one sampled evaluated vertex is inside the other closed mesh by the reported nearest-surface distance.
- overlap with zero inside-vertex depth remains possible for edge/face crossings and is a known sampling blind spot.

The penetration proxy is not an exact minimum translation distance, penetration volume, contact force, pressure, or signed distance field. It assumes closed meshes and can be unstable for open, non-manifold, self-intersecting, or degenerately tessellated assets.

## Decision use

This diagnostic cannot retroactively change the preregistered B04 v0.1 result. It determines whether the next contact validator needs a stronger representation before any claim of visually acceptable grasp.

If HOLD contains inside-vertex depth larger than the v0.1 position tolerance (`0.005 m`), the current automatic pass is classified as insufficient for contact quality, even though its original checks remain correctly reported as passed.

## Primary references

- [Blender 5.2 geometry utilities](https://docs.blender.org/api/5.2/mathutils.geometry.html)
- [Blender 5.2 BVHTree utilities](https://docs.blender.org/api/5.2/mathutils.bvhtree.html)
- [Blender 5.2 Mesh API and loop-triangle tessellation](https://docs.blender.org/api/5.2/bpy.types.Mesh.html)
