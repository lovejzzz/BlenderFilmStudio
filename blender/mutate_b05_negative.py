"""Create pre-registered B05 runtime-negative .blend fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--mutation", choices=["STRETCH", "CONTACT_DISABLED", "TARGET_DRIFT"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def main() -> None:
    args = parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))["plan"]
    binding = plan["grasps"][0]
    spec = binding["graspSpec"]
    rig = bpy.data.objects[binding["armatureObject"]]
    finger = spec["fingerChains"][1]
    terminal = rig.pose.bones[finger["bones"][-1]["boneSemantic"]]
    constraint = terminal.constraints[f"BFS_GRASP_IK_{finger['id']}"]

    if args.mutation == "STRETCH":
        constraint.use_stretch = True
        for bone in finger["bones"]:
            rig.pose.bones[bone["boneSemantic"]].ik_stretch = 1.0
    elif args.mutation == "CONTACT_DISABLED":
        frame = 60
        bpy.context.scene.frame_set(frame)
        constraint.influence = 0.0
        constraint.keyframe_insert(data_path="influence", frame=frame, group="BFS_NEGATIVE")
    elif args.mutation == "TARGET_DRIFT":
        target = bpy.data.objects[f"{binding['id']}__{spec['contactPatches'][1]['id']}"]
        base = target.location.copy()
        for frame, location in ((49, base), (60, base + Vector((0, 0.02, 0))), (108, base)):
            target.location = location
            target.keyframe_insert(data_path="location", frame=frame, group="BFS_NEGATIVE")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), check_existing=False, compress=True)
    print(f"BFS_B05_NEGATIVE_OK {args.mutation} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B05_NEGATIVE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
