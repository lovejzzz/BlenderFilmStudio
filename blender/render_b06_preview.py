"""Render technical evidence frames from a B06 rigid-body run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    scene.frame_set(args.frame)
    camera_data = bpy.data.cameras.new("B06_PREVIEW_CAMERA_DATA")
    camera = bpy.data.objects.new("B06_PREVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.65, -1.35, 0.55)
    camera.data.lens = 64
    look_at(camera, Vector((0, 0, 0.15)))
    scene.camera = camera
    for name, location, energy, size in (
        ("B06_KEY", (-0.4, -0.6, 0.9), 420, 0.8),
        ("B06_FILL", (0.7, -0.3, 0.5), 240, 0.7),
    ):
        data = bpy.data.lights.new(name, type="AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        light = bpy.data.objects.new(name, data)
        light.location = location
        look_at(light, Vector((0, 0, 0.15)))
        scene.collection.objects.link(light)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("B06_PREVIEW_WORLD")
    scene.world.color = (0.004, 0.008, 0.015)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 960, 540, 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(args.output.resolve())
    result = bpy.ops.render.render(write_still=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"Preview failed: {sorted(result)}")
    print(f"BFS_B06_PREVIEW_OK {args.frame} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B06_PREVIEW_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
