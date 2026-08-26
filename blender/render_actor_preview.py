"""Render a non-master preview of the B03 ActorSpec technical mannequin."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from bpy_extras import anim_utils
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def resolve_below(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve() if candidate.is_absolute() else (resolved_root / candidate).resolve()
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise RuntimeError(f"Path escapes repository: {candidate}")
    return resolved


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_floor(scene: bpy.types.Scene) -> None:
    mesh = bpy.data.meshes.new("B03_PREVIEW_FLOOR_MESH")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=3.0)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("B03_PREVIEW_FLOOR", mesh)
    material = bpy.data.materials.new("MAT_B03_PREVIEW_FLOOR")
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.025, 0.035, 0.05, 1.0)
    shader.inputs["Roughness"].default_value = 0.32
    mesh.materials.append(material)
    scene.collection.objects.link(obj)


def add_camera_and_lights(scene: bpy.types.Scene) -> None:
    camera_data = bpy.data.cameras.new("B03_PREVIEW_CAMERA_DATA")
    camera_data.lens = 72
    camera = bpy.data.objects.new("B03_PREVIEW_CAMERA", camera_data)
    camera.location = (2.45, -4.25, 1.75)
    look_at(camera, Vector((0.0, 0.0, 1.35)))
    scene.collection.objects.link(camera)
    scene.camera = camera
    for name, location, energy, size, color in (
        ("B03_KEY", (2.2, -2.1, 3.2), 1150, 2.0, (1.0, 0.72, 0.52)),
        ("B03_FILL", (-2.4, -1.4, 2.0), 720, 1.8, (0.36, 0.58, 1.0)),
        ("B03_RIM", (0.0, 1.7, 2.7), 980, 1.2, (0.55, 0.75, 1.0)),
    ):
        light_data = bpy.data.lights.new(f"{name}_DATA", "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light_data.color = color
        light = bpy.data.objects.new(name, light_data)
        light.location = location
        look_at(light, Vector((0.0, 0.0, 1.35)))
        scene.collection.objects.link(light)


def set_interpolation(animation_data, interpolation_by_frame: dict[int, str]) -> None:
    if not animation_data or not animation_data.action:
        return
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(animation_data)
    if not channelbag:
        return
    for curve in channelbag.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = interpolation_by_frame.get(round(point.co.x), "BEZIER")


def apply_performance(spec: dict, objects: dict[str, bpy.types.Object], root: Path) -> None:
    rig = objects[spec["rig"]["armatureObject"]]
    action_spec = spec["performance"]["bodyActions"][0]
    action_path = resolve_below(root, Path(action_spec["uri"]))
    with bpy.data.libraries.load(str(action_path), link=False) as (source, target):
        target.actions = [action_spec["actionName"]]
    action = target.actions[0]
    animation_data = rig.animation_data_create()
    animation_data.action = action
    animation_data.action_slot = action.slots[0]

    shape_mesh = objects[spec["deformation"]["shapeKeyMesh"]]
    shape_keys = shape_mesh.data.shape_keys
    channel_map = {item["id"]: item for item in spec["deformation"]["shapeChannels"]}
    interpolation = {}
    for curve in spec["performance"]["facialCurves"]:
        key_block = shape_keys.key_blocks[channel_map[curve["channel"]]["targetKey"]]
        for key in curve["keys"]:
            key_block.value = key["value"]
            key_block.keyframe_insert(data_path="value", frame=key["frame"], group="BFS_FACE")
            interpolation[key["frame"]] = key["interpolation"]
    set_interpolation(shape_keys.animation_data, interpolation)

    gaze_target = objects["GAZE_TARGET"]
    gaze_positions = ((0.0, -3.0, 1.68), (1.15, -2.5, 1.42))
    for index, key in enumerate(spec["performance"]["gazeKeys"]):
        gaze_target.location = gaze_positions[min(index, len(gaze_positions) - 1)]
        gaze_target.keyframe_insert(data_path="location", frame=key["frame"], group="BFS_GAZE_TARGET")


def main() -> None:
    args = parse_args()
    root = args.repository_root.resolve()
    spec = json.loads(resolve_below(root, args.spec).read_text(encoding="utf-8"))
    asset_path = resolve_below(root, Path(spec["actor"]["assetUri"]))
    with bpy.data.libraries.load(str(asset_path), link=False, recursive=True) as (source, target):
        target.collections = [spec["actor"]["assetRef"]]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    objects = {obj.name: obj for obj in collection.all_objects}

    scene = bpy.context.scene
    scene.name = "B03_ACTOR_PREVIEW"
    scene.frame_start = spec["performance"]["frameStart"]
    scene.frame_end = spec["performance"]["frameEnd"]
    scene.render.fps = spec["performance"]["frameRate"]["numerator"]
    scene.render.fps_base = spec["performance"]["frameRate"]["denominator"]
    apply_performance(spec, objects, root)
    add_floor(scene)
    add_camera_and_lights(scene)
    world = bpy.data.worlds.new("B03_PREVIEW_WORLD")
    world.color = (0.005, 0.008, 0.015)
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.008, 0.018, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.15
    scene.world = world

    scene.frame_set(args.frame)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str(args.output.resolve())
    scene.display_settings.display_device = "sRGB - Display"
    scene.view_settings.view_transform = "ACES 2.0 - SDR 100 nits (Rec.709)"
    scene.render.film_transparent = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = bpy.ops.render.render(write_still=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"Preview failed: {sorted(result)}")
    print(f"BFS_ACTOR_PREVIEW_OK {args.frame} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_ACTOR_PREVIEW_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
