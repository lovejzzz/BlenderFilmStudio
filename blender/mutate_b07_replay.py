"""Create B07 replay runtime-negative fixtures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mutation", choices=["RIGID_BODY", "KEY_MUTATION"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def main() -> None:
    args = parse_args()
    prop = bpy.data.objects["B06_PROP"]
    if args.mutation == "RIGID_BODY":
        bpy.context.view_layer.objects.active = prop
        prop.select_set(True)
        bpy.ops.rigidbody.object_add()
        prop.select_set(False)
    else:
        bpy.context.scene.frame_set(60)
        prop.location.x += 0.1
        prop.keyframe_insert(data_path="location", frame=60, group="B07_NEGATIVE")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), check_existing=False, compress=True)
    print(f"BFS_B07_MUTATION_OK {args.mutation} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B07_MUTATION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
