# RC6 liquid mesh reconstruction attempt-21 result

## Verdict

`PASS_EXECUTION / FAIL_STATIC_CONTROL`. The independent auditor passed 22/22 checks, but no cell met the frozen source-volume, temporal-drift, signed-topology and containment thresholds. Slow-tip remains locked.

## Bound result

- Tool-freeze commit: `1ee470551e1f93fe99a7e72e932101d1ffab733b`
- Spec hash: `effc048e2f1a9613bd5ac09bdcfda8d98854ea55675b2831326cf983b59ca528`
- Matrix hash: `699d64be425baa175d668b9f4d00641146868e7e0688509016b414312e57856b`
- Independent audit hash: `5cc92659a85f71f9ea72958ea9ef4365cb3965f3ccf1a2f1ed5eebb7834b8c22`
- Four Blender starts, four seven-frame data bakes, four mesh bakes, four saves, zero renders, zero network calls and zero engine writes.
- Every cell retained exactly 21 Mantaflow cache files: one config, data and mesh file for each frame 1 through 7. No extra frame was evaluated or retained.

| mesh particle radius | wall seconds | max source error | max temporal drift | max outside | max components | verdict |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 4.0 | 104.673 | 12.7645% | 6.2336% | 4.9231% | 7 | fail |
| 4.5 | 102.377 | 6.3362% | 7.3995% | 5.5647% | 7 | fail / relative-only |
| 4.75 | 104.861 | 7.8183% | 7.2275% | 6.5553% | 8 | fail |
| 5.0 | 96.186 | 13.6711% | 7.5120% | 6.9735% | 6 | fail |

Radius 4.5 moved reconstructed volume closest to the frozen source, but it did not establish a valid liquid body. Starting at frame 2, several small positive-volume components remained at exactly the same locations and volumes through frame 7. They were not a natural evolving splash.

## Geometry diagnosis

The retained cup origin is at world `z=0.220 m`; its inner floor is local `z=-0.160 m`, hence world `z=0.060 m`. The frozen source bottom is world `z=0.075 m`, leaving only `0.015 m`, or 2.88 base voxels at `0.0052083333 m` per voxel. The cup effector surface distance is 1.5 cells and `delete_in_obstacle` is intentionally false so collision failure remains visible.

The persistent positive fragments had lower/upper world-Z bounds of approximately `0.0068–0.0404 m`, entirely below the cup's inner floor. Their volume increased with mesh reconstruction radius. This supports an insufficient source-to-effector clearance diagnosis; it does not support accepting the fragments as water, filtering them from the measurement, or enabling deletion in obstacles to hide them.

## Decision

Retain attempt-21 unchanged. The next static control must preserve the source mesh volume, simulation particle radius 1.6 and mesh particle radius 4.5 while varying only the source-bottom clearance above the cup inner floor. It must keep exact 1–7 cache-file enforcement and the unchanged 5% source/temporal, 1% containment and signed-topology gates. No slow-tip or impact bake is unlocked.
