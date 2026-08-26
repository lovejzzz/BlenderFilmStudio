"""Render a technical evidence frame for the B05 IK feasibility spike."""

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


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.use_nodes = True
    shader = value.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = 0.38
    return value


def add_pose_proxy(armature: bpy.types.Object, bone_name: str, mat: bpy.types.Material) -> None:
    pose_bone = armature.pose.bones[bone_name]
    head = armature.matrix_world @ pose_bone.head
    tail = armature.matrix_world @ pose_bone.tail
    direction = tail - head
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.012, depth=direction.length, location=(head + tail) / 2)
    segment = bpy.context.object
    segment.name = f"EVIDENCE_{bone_name}"
    segment.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    segment.data.materials.append(mat)


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("B05_PREVIEW_CAMERA")
    camera = bpy.data.objects.new("B05_PREVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (0.45, -1.20, 0.85)
    camera.data.lens = 58
    look_at(camera, Vector((0, 0, 0.15)))
    for name, location, energy, size in (
        ("B05_KEY", (-0.35, -0.55, 0.55), 220, 0.55),
        ("B05_FILL", (0.50, -0.35, 0.30), 110, 0.45),
    ):
        light_data = bpy.data.lights.new(name, type="AREA")
        light_data.energy, light_data.shape, light_data.size = energy, "DISK", size
        light = bpy.data.objects.new(name, light_data)
        light.location = location
        look_at(light, Vector((0, 0, 0.15)))
        scene.collection.objects.link(light)
    scene.world.color = (0.005, 0.008, 0.015)
    scene.frame_set(args.frame)
    for obj in scene.objects:
        if obj.name.startswith("SEGMENT_") or obj.name.startswith("TIP_"):
            obj.hide_render = True
    armature = bpy.data.objects["B05_GRIPPER"]
    thumb_mat = material("MAT_EVIDENCE_THUMB", (0.95, 0.28, 0.12, 1))
    index_mat = material("MAT_EVIDENCE_INDEX", (1.0, 0.68, 0.12, 1))
    for finger, mat in (("thumb", thumb_mat), ("index", index_mat)):
        for index in (1, 2):
            add_pose_proxy(armature, f"{finger}.{index}", mat)
        tip = armature.matrix_world @ armature.pose.bones[f"{finger}.2"].tail
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.01, location=tip)
        bpy.context.object.name = f"EVIDENCE_TIP_{finger.upper()}"
        bpy.context.object.data.materials.append(mat)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.render.use_motion_blur = False
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
    print(f"BFS_B05_IK_PREVIEW_OK {args.frame} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B05_IK_PREVIEW_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
