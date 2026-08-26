"""Render a small, explicitly non-master PNG from a compiled scene."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--samples", type=int, default=32)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    if args.frame < scene.frame_start or args.frame > scene.frame_end:
        raise RuntimeError(f"Preview frame {args.frame} is outside {scene.frame_start}–{scene.frame_end}")
    scene.frame_set(args.frame)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = args.samples
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str(args.output.resolve())
    scene.render.film_transparent = False
    result = bpy.ops.render.render(write_still=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"Preview render failed: {sorted(result)}")
    print(f"BFS_PREVIEW_OK {scene.name} {args.frame} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_PREVIEW_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
