"""Render the anonymized 144-frame B04 human-review clip."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--clip-id", default="CLIP_A17F")
    parser.add_argument("--camera-location", nargs=3, type=float, default=(2.45, -4.3, 1.85))
    parser.add_argument("--look-at", nargs=3, type=float, default=(-0.05, 0.02, 1.30))
    parser.add_argument("--lens", type=float, default=62.0)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_floor(scene: bpy.types.Scene, clip_id: str) -> None:
    mesh = bpy.data.meshes.new(f"{clip_id}_FLOOR_MESH")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=3.0)
    bm.to_mesh(mesh)
    bm.free()
    floor = bpy.data.objects.new(f"{clip_id}_FLOOR", mesh)
    material = bpy.data.materials.new(f"{clip_id}_FLOOR_MATERIAL")
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.018, 0.028, 0.045, 1.0)
    shader.inputs["Roughness"].default_value = 0.38
    mesh.materials.append(material)
    scene.collection.objects.link(floor)


def add_camera_light(scene: bpy.types.Scene, camera: bpy.types.Object, clip_id: str) -> None:
    light_data = bpy.data.lights.new(f"{clip_id}_CAMERA_LIGHT", type="AREA")
    light_data.energy = 850
    light_data.shape = "DISK"
    light_data.size = 4.0
    light = bpy.data.objects.new(f"{clip_id}_CAMERA_LIGHT", light_data)
    light.location = camera.location
    light.rotation_euler = camera.rotation_euler
    scene.collection.objects.link(light)


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    add_floor(scene, args.clip_id)
    camera = scene.camera
    camera.location = args.camera_location
    camera.data.lens = args.lens
    look_at(camera, Vector(args.look_at))
    add_camera_light(scene, camera, args.clip_id)
    for obj in bpy.data.objects:
        if obj.type == "LIGHT":
            look_at(obj, Vector((-0.05, 0.02, 1.28)))
    scene.frame_start = 1
    scene.frame_end = 144
    scene.render.fps = 24
    scene.render.fps_base = 1
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.use_motion_blur = False
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "VIDEO"
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.audio_codec = "NONE"
    scene.render.filepath = str(args.output.resolve())
    result = bpy.ops.render.render(animation=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"Review render failed: {sorted(result)}")
    print(f"BFS_B04_REVIEW_CLIP_OK {args.clip_id} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B04_REVIEW_CLIP_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
