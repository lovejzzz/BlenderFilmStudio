# RC6 C5-C2 attempt-54 retained marker-binding failure

Date: 2026-09-02

Aggregate verdict: `FAIL_RUNNER_MARKER_BINDING`

Attempt-54 completed one exact C5F48 Blender/Bullet process. The physical cell
passed all 13 frozen checks: it reached 60.00286288 degrees, took 31 frames from
5 to 45 degrees, moved the cup surface at most 0.0118653 m per frame, required
two derived effector subframes, held the hinge pivot within 0.00001238 m, stayed
on the floor and remained inside the candidate domain margin.

The aggregate runner then stopped because its versioned wrapper expected
`RC6_SLOW_TIP_BULLET_SCREEN_C5_C2=`, while the deliberately byte-identical C5
scene tool emitted its frozen `RC6_SLOW_TIP_BULLET_SCREEN_C5=` marker. The
remaining three cells did not start and no aggregate receipt exists. This is a
harness failure with one valid passing physical cell, not a completed four-cell
screen.

The append-only independent failure audit passes 16/16. Failure self hash is
`ed8e1157ecbcf9ade127ed3b6d3f443be9709859666bc533f280a2f02743417e`;
audit self hash is
`011c51f59ecba8249ad9d54aa3d94bc0f0229f2eba443a7cdf4a5809a9a45f2e`.
Counts are one Blender start, one Bullet bake and zero fluid, render, save,
build, network or engine-write work.

A versioned correction may change only the runner's expected cell marker back
to the unchanged scene tool's actual C5 marker and route to fresh roots. It may
not change the scene tool, motor cells, physics, thresholds or resources.
