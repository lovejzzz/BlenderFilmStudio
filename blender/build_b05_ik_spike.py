"""Build the preregistered B05 two-finger IK feasibility scene."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras import anim_utils
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def reset() -> None:
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.armatures, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            datablocks.remove(datablock)


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.diffuse_color = color
    value.use_nodes = True
    shader = value.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = 0.42
    return value


def cube(name: str, location: tuple[float, float, float], dimensions: tuple[float, float, float], mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def sphere(name: str, radius: float, mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def bone_parent(obj: bpy.types.Object, armature: bpy.types.Object, bone_name: str, distance: float) -> None:
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.location = (0, distance, 0)


def key_location(obj: bpy.types.Object, frame: int, value: tuple[float, float, float]) -> None:
    obj.location = value
    obj.keyframe_insert(data_path="location", frame=frame)


def configure_linear_keys(obj: bpy.types.Object) -> None:
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(obj.animation_data)
    if channelbag:
        for fcurve in channelbag.fcurves:
            for point in fcurve.keyframe_points:
                point.interpolation = "LINEAR"


def build_armature(carrier: bpy.types.Object, finger_mat: bpy.types.Material, tip_mat: bpy.types.Material) -> bpy.types.Object:
    armature_data = bpy.data.armatures.new("B05_GRIPPER_ARMATURE")
    armature = bpy.data.objects.new("B05_GRIPPER", armature_data)
    bpy.context.collection.objects.link(armature)
    armature.parent = carrier
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    definitions = {
        "thumb": [((-0.16, -0.05, 0), (-0.10, -0.05, 0)), ((-0.10, -0.05, 0), (-0.04, -0.05, 0))],
        "index": [((0.16, 0.05, 0), (0.10, 0.05, 0)), ((0.10, 0.05, 0), (0.04, 0.05, 0))],
    }
    for finger, segments in definitions.items():
        parent = None
        for index, (head, tail) in enumerate(segments, 1):
            bone = armature_data.edit_bones.new(f"{finger}.{index}")
            bone.head, bone.tail = head, tail
            bone.parent = parent
            bone.use_connect = parent is not None
            parent = bone
    bpy.ops.object.mode_set(mode="POSE")
    limits = {
        "thumb.1": (-10, 65, 0.35), "thumb.2": (0, 75, 0.25),
        "index.1": (0, 90, 0.35), "index.2": (0, 95, 0.25),
    }
    for name, (minimum, maximum, stiffness) in limits.items():
        pose_bone = armature.pose.bones[name]
        pose_bone.rotation_mode = "XYZ"
        pose_bone.lock_ik_x = True
        pose_bone.lock_ik_y = True
        pose_bone.use_ik_limit_z = True
        pose_bone.ik_min_z = math.radians(minimum)
        pose_bone.ik_max_z = math.radians(maximum)
        pose_bone.ik_stiffness_z = stiffness
        pose_bone.ik_stretch = 0
    bpy.ops.object.mode_set(mode="OBJECT")

    for finger in ("thumb", "index"):
        target = bpy.data.objects.new(f"TARGET_{finger.upper()}", None)
        bpy.context.collection.objects.link(target)
        target.parent = carrier
        start = (-0.04, -0.05, 0) if finger == "thumb" else (0.04, 0.05, 0)
        hold = (-0.061, 0, 0) if finger == "thumb" else (0.061, 0, 0)
        for frame, value in ((1, start), (36, start), (48, hold), (108, hold), (120, start)):
            key_location(target, frame, value)
        configure_linear_keys(target)
        constraint = armature.pose.bones[f"{finger}.2"].constraints.new("IK")
        constraint.name = f"IK_{finger.upper()}"
        constraint.target = target
        constraint.chain_count = 2
        constraint.use_stretch = False

        for index in (1, 2):
            segment = cube(f"SEGMENT_{finger.upper()}_{index}", (0, 0, 0), (0.025, 0.06, 0.03), finger_mat)
            bone_parent(segment, armature, f"{finger}.{index}", 0.03)
        tip = sphere(f"TIP_{finger.upper()}", 0.01, tip_mat)
        bone_parent(tip, armature, f"{finger}.2", 0.06)
    return armature


def normalized_manifest(scene: bpy.types.Scene, armature: bpy.types.Object) -> dict:
    objects = []
    for obj in sorted(scene.objects, key=lambda value: value.name):
        objects.append({"name": obj.name, "type": obj.type, "parent": obj.parent.name if obj.parent else None, "parentType": obj.parent_type, "parentBone": obj.parent_bone})
    bones = []
    for bone in sorted(armature.pose.bones, key=lambda value: value.name):
        bones.append({
            "name": bone.name,
            "ikMinZ": round(bone.ik_min_z, 12), "ikMaxZ": round(bone.ik_max_z, 12), "ikStretch": bone.ik_stretch,
            "constraints": [{"name": item.name, "type": item.type, "target": item.target.name if item.target else None, "chainCount": getattr(item, "chain_count", None), "useStretch": getattr(item, "use_stretch", None)} for item in bone.constraints],
        })
    actions = []
    for action in sorted(bpy.data.actions, key=lambda value: value.name):
        curves = []
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    curves.extend({"slotHandle": channelbag.slot_handle, "path": curve.data_path, "index": curve.array_index, "keys": [[round(point.co.x, 6), round(point.co.y, 9)] for point in curve.keyframe_points]} for curve in channelbag.fcurves)
        actions.append({"name": action.name, "slots": [slot.identifier for slot in action.slots], "curves": sorted(curves, key=lambda value: (value["slotHandle"], value["path"], value["index"]))})
    return {"documentType": "BFS_B05_IK_STRUCTURE", "blender": bpy.app.version_string, "objects": objects, "bones": bones, "actions": actions}


def main() -> None:
    args = parse_args()
    reset()
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end, scene.render.fps = 1, 120, 24
    carrier = bpy.data.objects.new("B05_CARRIER", None)
    bpy.context.collection.objects.link(carrier)
    for frame, z in ((1, 0), (49, 0), (108, 0.30), (120, 0.30)):
        key_location(carrier, frame, (0, 0, z))
    configure_linear_keys(carrier)
    prop = cube("PROP_BODY", (0, 0, 0), (0.10, 0.12, 0.14), material("MAT_PROP", (0.15, 0.45, 0.8, 1)))
    prop.parent = carrier
    armature = build_armature(carrier, material("MAT_FINGER", (0.85, 0.25, 0.18, 1)), material("MAT_TIP", (1.0, 0.65, 0.2, 1)))
    scene.frame_set(1)
    manifest = normalized_manifest(scene, armature)
    serialized = f"{json.dumps(manifest, indent=2)}\n"
    manifest["structureSha256"] = hashlib.sha256(serialized.encode()).hexdigest()
    serialized = f"{json.dumps(manifest, indent=2)}\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(serialized, encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), check_existing=False)
    print(f"BFS_B05_IK_BUILD_OK {manifest['structureSha256']} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B05_IK_BUILD_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
