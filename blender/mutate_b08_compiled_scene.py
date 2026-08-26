"""Inject one frozen runtime mutation into a positive B08 compiled scene."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from bpy_extras import anim_utils


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mutation", choices=["KEY_MUTATION", "RIGID_BODY"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def main() -> None:
    args = parse_args()
    prop = bpy.data.objects["B06_PROP"]
    if args.mutation == "RIGID_BODY":
        bpy.context.view_layer.objects.active = prop
        prop.select_set(True)
        bpy.ops.rigidbody.object_add()
    else:
        bag = anim_utils.animdata_get_channelbag_for_assigned_slot(prop.animation_data)
        curve = next(item for item in bag.fcurves if item.data_path == "location" and item.array_index == 0)
        point = next(item for item in curve.keyframe_points if round(item.co.x) == 60)
        point.co.y += 0.01
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), check_existing=False, compress=True)
    print(f"BFS_B08_MUTATION_OK {args.mutation} {args.output}")


if __name__ == "__main__":
    main()
