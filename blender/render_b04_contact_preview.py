"""Render non-master evidence frames from the compiled B04 scene."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--camera-location", nargs=3, type=float, default=(2.45, -4.3, 1.85))
    parser.add_argument("--look-at", nargs=3, type=float, default=(-0.05, 0.02, 1.30))
    parser.add_argument("--lens", type=float, default=62.0)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_floor(scene: bpy.types.Scene) -> None:
    if "B04_PREVIEW_FLOOR" in bpy.data.objects:
        return
    mesh = bpy.data.meshes.new("B04_PREVIEW_FLOOR_MESH")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=3.0)
    bm.to_mesh(mesh)
    bm.free()
    floor = bpy.data.objects.new("B04_PREVIEW_FLOOR", mesh)
    material = bpy.data.materials.new("MAT_B04_PREVIEW_FLOOR")
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.018, 0.028, 0.045, 1.0)
    shader.inputs["Roughness"].default_value = 0.38
    mesh.materials.append(material)
    scene.collection.objects.link(floor)


def add_camera_light(scene: bpy.types.Scene, camera: bpy.types.Object) -> None:
    light_data = bpy.data.lights.new("B04_REVIEW_CAMERA_LIGHT", type="AREA")
    light_data.energy = 850
    light_data.shape = "DISK"
    light_data.size = 4.0
    light = bpy.data.objects.new("B04_REVIEW_CAMERA_LIGHT", light_data)
    light.location = camera.location
    light.rotation_euler = camera.rotation_euler
    scene.collection.objects.link(light)


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    add_floor(scene)
    camera = scene.camera
    camera.location = args.camera_location
    camera.data.lens = args.lens
    look_at(camera, Vector(args.look_at))
    add_camera_light(scene, camera)
    for obj in bpy.data.objects:
        if obj.type == "LIGHT":
            look_at(obj, Vector((-0.05, 0.02, 1.28)))
    scene.frame_set(args.frame)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.use_motion_blur = False
    scene.eevee.taa_render_samples = 64
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str(args.output.resolve())
    scene.render.film_transparent = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = bpy.ops.render.render(write_still=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"Preview failed: {sorted(result)}")
    print(f"BFS_B04_PREVIEW_OK {args.frame} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B04_PREVIEW_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
