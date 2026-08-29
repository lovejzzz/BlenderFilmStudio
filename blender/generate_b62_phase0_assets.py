"""Generate the preregistered B62 Phase-0 original assets and master animatic scene.

This is an asset-authoring tool, not the production SceneSpec compiler.  It is
allowed only by B62-P0-E1 and writes into that experiment's fresh formal root.
The exported asset libraries contain no scripts, drivers, external libraries,
or runtime constraints.  A clearly named temporary IK rig exists only in the
Phase-0 master scene so contact feasibility can be inspected before formal
asset promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
from bpy_extras import anim_utils
from mathutils import Euler, Vector


GENERATOR_VERSION = "0.1.0"
ACTOR_ID = "CHAR_B62_GUARDIAN"
SET_ID = "SET_B62_OBSERVATORY"
PROP_ID = "PROP_B62_CONSOLE_CORE"
MOTION_ACTION = "B62_GUARDIAN_PERFORMANCE"


def normalize_numbers(value: object) -> object:
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_numbers(item) for key, item in value.items()}
    return value


def canonical_json(value: object) -> str:
    return json.dumps(normalize_numbers(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def self_hashed(document: dict, field: str) -> dict:
    result = dict(document)
    result[field] = sha256_bytes(canonical_json({key: value for key, value in result.items() if key != field}).encode("utf-8"))
    return result


def write_hashed(path: Path, body: dict, field: str) -> dict:
    record = self_hashed(body, field)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-root", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def clear_factory_scene() -> bpy.types.Scene:
    for datablocks in (
        bpy.data.objects,
        bpy.data.collections,
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.armatures,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.materials,
        bpy.data.actions,
    ):
        for datablock in list(datablocks):
            datablocks.remove(datablock, do_unlink=True)
    scene = bpy.context.scene
    scene.name = "B62_PHASE0_MASTER"
    scene.frame_start = 1
    scene.frame_end = 288
    scene.render.fps = 24
    scene.render.fps_base = 1
    return scene


def new_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(collection)
    return collection


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def principled_input(shader: bpy.types.Node, *names: str):
    for name in names:
        if name in shader.inputs:
            return shader.inputs[name]
    raise RuntimeError(f"Principled input is unavailable: {names}")


def material(
    name: str,
    base: tuple[float, float, float, float],
    metallic: float,
    roughness: float,
    emission: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
    transmission: float = 0.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    principled_input(shader, "Base Color").default_value = base
    principled_input(shader, "Metallic").default_value = metallic
    principled_input(shader, "Roughness").default_value = roughness
    if emission is not None:
        principled_input(shader, "Emission Color", "Emission").default_value = emission
        principled_input(shader, "Emission Strength").default_value = emission_strength
    if transmission > 0:
        principled_input(shader, "Transmission Weight", "Transmission").default_value = transmission
        mat.surface_render_method = "DITHERED"
    mat["bfs_material_contract"] = "B62_PHASE0"
    return mat


def apply_bevel(obj: bpy.types.Object, width: float, segments: int = 3) -> None:
    if width <= 0:
        return
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    modifier = obj.modifiers.new("B62_BAKED_BEVEL", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def finish_mesh(obj: bpy.types.Object, collection: bpy.types.Collection, mat: bpy.types.Material, smooth: bool) -> bpy.types.Object:
    move_to_collection(obj, collection)
    obj.data.materials.append(mat)
    if smooth:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    obj["bfs_generated_by"] = GENERATOR_VERSION
    return obj


def cube(
    collection: bpy.types.Collection,
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    bevel: float = 0.04,
    rotation: tuple[float, float, float] = (0, 0, 0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_bevel(obj, bevel)
    return finish_mesh(obj, collection, mat, False)


def cylinder(
    collection: bpy.types.Collection,
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    mat: bpy.types.Material,
    rotation: tuple[float, float, float] = (0, 0, 0),
    vertices: int = 48,
    bevel: float = 0.025,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    apply_bevel(obj, bevel)
    return finish_mesh(obj, collection, mat, True)


def sphere(
    collection: bpy.types.Collection,
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    subdivisions: int = 3,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish_mesh(obj, collection, mat, True)


def torus(
    collection: bpy.types.Collection,
    name: str,
    location: tuple[float, float, float],
    major: float,
    minor: float,
    mat: bpy.types.Material,
    rotation: tuple[float, float, float] = (0, 0, 0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major,
        minor_radius=minor,
        major_segments=64,
        minor_segments=12,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(obj, collection, mat, True)


def parent_to_bone(obj: bpy.types.Object, rig: bpy.types.Object, bone: str) -> None:
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    obj.matrix_world = world
    obj["bfs_rigid_bone_parent"] = bone


def create_rig(collection: bpy.types.Collection) -> bpy.types.Object:
    data = bpy.data.armatures.new("RIG_B62_GUARDIAN_DATA")
    rig = bpy.data.objects.new("RIG_B62_GUARDIAN", data)
    collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    definitions = [
        ("root", (0, 0, 0), (0, 0, 0.25), None),
        ("pelvis", (0, 0, 0.82), (0, 0, 1.04), "root"),
        ("spine", (0, 0, 1.04), (0, 0, 1.30), "pelvis"),
        ("chest", (0, 0, 1.30), (0, 0, 1.50), "spine"),
        ("neck", (0, 0, 1.50), (0, 0, 1.62), "chest"),
        ("head", (0, 0, 1.62), (0, 0, 1.84), "neck"),
        ("upper_arm.L", (0.31, 0, 1.44), (0.61, 0, 1.30), "chest"),
        ("forearm.L", (0.61, 0, 1.30), (0.82, -0.02, 1.10), "upper_arm.L"),
        ("hand.L", (0.82, -0.02, 1.10), (0.94, -0.08, 1.04), "forearm.L"),
        ("upper_arm.R", (-0.31, 0, 1.44), (-0.61, 0, 1.30), "chest"),
        ("forearm.R", (-0.61, 0, 1.30), (-0.82, -0.02, 1.10), "upper_arm.R"),
        ("hand.R", (-0.82, -0.02, 1.10), (-0.94, -0.08, 1.04), "forearm.R"),
        ("thigh.L", (0.17, 0, 0.90), (0.18, 0, 0.52), "pelvis"),
        ("shin.L", (0.18, 0, 0.52), (0.18, 0, 0.16), "thigh.L"),
        ("foot.L", (0.18, 0, 0.16), (0.18, -0.24, 0.09), "shin.L"),
        ("thigh.R", (-0.17, 0, 0.90), (-0.18, 0, 0.52), "pelvis"),
        ("shin.R", (-0.18, 0, 0.52), (-0.18, 0, 0.16), "thigh.R"),
        ("foot.R", (-0.18, 0, 0.16), (-0.18, -0.24, 0.09), "shin.R"),
    ]
    bones = {}
    for name, head, tail, parent in definitions:
        bone = data.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        bone.use_deform = False
        if parent:
            bone.parent = bones[parent]
        bones[name] = bone
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.select_set(False)
    rig["bfs_rig_profile"] = "BFS_MECHANICAL_GUARDIAN_0_1"
    for pose_bone in rig.pose.bones:
        pose_bone.rotation_mode = "XYZ"
    return rig


def create_guardian(parent: bpy.types.Collection, mats: dict[str, bpy.types.Material]) -> tuple[bpy.types.Collection, bpy.types.Object]:
    collection = new_collection(ACTOR_ID, parent)
    collection["bfs_asset_id"] = ACTOR_ID
    collection["bfs_asset_version"] = "0.1.0"
    rig = create_rig(collection)

    pieces: list[tuple[bpy.types.Object, str]] = []
    pieces.extend([
        (cube(collection, "B62_PELVIS", (0, 0, 0.94), (0.27, 0.20, 0.15), mats["armor"], 0.07), "pelvis"),
        (cube(collection, "B62_TORSO", (0, 0, 1.27), (0.35, 0.22, 0.30), mats["armor"], 0.08), "spine"),
        (cube(collection, "B62_CHEST_PLATE", (0, -0.22, 1.35), (0.28, 0.055, 0.20), mats["trim"], 0.035), "chest"),
        (sphere(collection, "B62_HELMET", (0, 0, 1.72), (0.27, 0.24, 0.28), mats["armor"]), "head"),
        (cube(collection, "B62_VISOR", (0, -0.225, 1.73), (0.20, 0.035, 0.085), mats["visor"], 0.035), "head"),
        (cube(collection, "B62_EYE_SLIT", (0, -0.268, 1.75), (0.14, 0.012, 0.018), mats["eye"], 0.012), "head"),
        (cylinder(collection, "B62_NECK", (0, 0, 1.55), 0.10, 0.14, mats["joint"], bevel=0.02), "neck"),
        (cube(collection, "B62_SHOULDER_L", (0.40, 0, 1.43), (0.16, 0.24, 0.12), mats["trim"], 0.06), "upper_arm.L"),
        (cube(collection, "B62_SHOULDER_R", (-0.40, 0, 1.43), (0.16, 0.24, 0.12), mats["trim"], 0.06), "upper_arm.R"),
        (cylinder(collection, "B62_UPPER_ARM_L", (0.56, 0, 1.32), 0.095, 0.36, mats["armor"], rotation=(0, math.radians(64), 0)), "upper_arm.L"),
        (cylinder(collection, "B62_UPPER_ARM_R", (-0.56, 0, 1.32), 0.095, 0.36, mats["armor"], rotation=(0, math.radians(-64), 0)), "upper_arm.R"),
        (cylinder(collection, "B62_FOREARM_L", (0.73, -0.01, 1.16), 0.085, 0.31, mats["trim"], rotation=(math.radians(4), math.radians(48), 0)), "forearm.L"),
        (cylinder(collection, "B62_FOREARM_R", (-0.73, -0.01, 1.16), 0.085, 0.31, mats["trim"], rotation=(math.radians(4), math.radians(-48), 0)), "forearm.R"),
        (cube(collection, "B62_HAND_L", (0.88, -0.05, 1.06), (0.10, 0.075, 0.075), mats["joint"], 0.04), "hand.L"),
        (cube(collection, "B62_HAND_R", (-0.88, -0.05, 1.06), (0.10, 0.075, 0.075), mats["joint"], 0.04), "hand.R"),
        (cylinder(collection, "B62_THIGH_L", (0.175, 0, 0.70), 0.115, 0.42, mats["armor"], bevel=0.035), "thigh.L"),
        (cylinder(collection, "B62_THIGH_R", (-0.175, 0, 0.70), 0.115, 0.42, mats["armor"], bevel=0.035), "thigh.R"),
        (cylinder(collection, "B62_SHIN_L", (0.18, -0.01, 0.34), 0.095, 0.38, mats["trim"], bevel=0.03), "shin.L"),
        (cylinder(collection, "B62_SHIN_R", (-0.18, -0.01, 0.34), 0.095, 0.38, mats["trim"], bevel=0.03), "shin.R"),
        (cube(collection, "B62_FOOT_L", (0.18, -0.10, 0.10), (0.13, 0.24, 0.10), mats["joint"], 0.045), "foot.L"),
        (cube(collection, "B62_FOOT_R", (-0.18, -0.10, 0.10), (0.13, 0.24, 0.10), mats["joint"], 0.045), "foot.R"),
        (sphere(collection, "B62_CHEST_LIGHT", (0, -0.285, 1.38), (0.065, 0.025, 0.065), mats["chest_light"], 2), "chest"),
    ])
    for obj, bone in pieces:
        parent_to_bone(obj, rig, bone)

    hand_socket = bpy.data.objects.new("HAND_R_SOCKET", None)
    collection.objects.link(hand_socket)
    hand_socket.empty_display_type = "SPHERE"
    hand_socket.empty_display_size = 0.045
    hand_socket.location = (0, -0.08, -0.02)
    hand_socket.parent = rig
    hand_socket.parent_type = "BONE"
    hand_socket.parent_bone = "hand.R"
    hand_socket["bfs_socket_id"] = "PALM_R"
    return collection, rig


def create_environment(parent: bpy.types.Collection, mats: dict[str, bpy.types.Material]) -> bpy.types.Collection:
    collection = new_collection(SET_ID, parent)
    collection["bfs_asset_id"] = SET_ID
    collection["bfs_asset_version"] = "0.1.0"
    cylinder(collection, "B62_FLOOR", (0, 0, -0.12), 5.8, 0.24, mats["floor"], vertices=96, bevel=0.04)
    cylinder(collection, "B62_DAIS", (0, -0.55, 0.02), 2.0, 0.16, mats["metal_dark"], vertices=64, bevel=0.035)
    for radius, z in ((5.2, 0.12), (5.05, 2.4), (4.9, 4.7)):
        torus(collection, f"B62_CHAMBER_RING_{str(z).replace('.', '_')}", (0, 0, z), radius, 0.07, mats["trim"])
    for index in range(12):
        angle = 2 * math.pi * index / 12
        x, y = 4.75 * math.cos(angle), 4.75 * math.sin(angle)
        cylinder(collection, f"B62_COLUMN_{index:02d}", (x, y, 2.25), 0.12, 4.4, mats["metal_dark"], vertices=24, bevel=0.025)
        practical = cube(collection, f"B62_PRACTICAL_{index:02d}", (4.58 * math.cos(angle), 4.58 * math.sin(angle), 1.15), (0.06, 0.03, 0.48), mats["practical"], 0.025, rotation=(0, 0, angle + math.pi / 2))
        practical["bfs_practical_index"] = index
    # Rear aperture and radial ribs establish scale without enclosing the camera.
    torus(collection, "B62_OBSERVATION_APERTURE", (0, 3.75, 2.35), 1.65, 0.16, mats["trim"], rotation=(math.radians(90), 0, 0))
    for index in range(8):
        angle = 2 * math.pi * index / 8
        cube(collection, f"B62_APERTURE_RIB_{index:02d}", (1.65 * math.cos(angle), 3.74, 2.35 + 1.65 * math.sin(angle)), (0.05, 0.10, 0.72), mats["metal_dark"], 0.02, rotation=(0, angle, 0))
    # Scene-local volume is deliberate and visible in the key light shafts.
    volume_mat = bpy.data.materials.new("MAT_B62_VOLUME")
    volume_mat.use_nodes = True
    nodes = volume_mat.node_tree.nodes
    for node in list(nodes):
        nodes.remove(node)
    output = nodes.new("ShaderNodeOutputMaterial")
    volume = nodes.new("ShaderNodeVolumePrincipled")
    volume.inputs["Density"].default_value = 0.018
    volume.inputs["Anisotropy"].default_value = 0.28
    volume_mat.node_tree.links.new(volume.outputs["Volume"], output.inputs["Volume"])
    volume_cube = cube(collection, "B62_ATMOSPHERE", (0, 0, 2.3), (5.4, 5.4, 2.4), volume_mat, 0)
    volume_cube.display_type = "WIRE"
    return collection


def create_console_core(parent: bpy.types.Collection, mats: dict[str, bpy.types.Material]) -> tuple[bpy.types.Collection, bpy.types.Object, bpy.types.Object]:
    collection = new_collection(PROP_ID, parent)
    collection["bfs_asset_id"] = PROP_ID
    collection["bfs_asset_version"] = "0.1.0"
    cube(collection, "B62_CONSOLE_BASE", (0, -0.35, 0.55), (0.72, 0.48, 0.56), mats["metal_dark"], 0.12)
    cube(collection, "B62_CONSOLE_SURFACE", (0, -0.03, 1.05), (0.62, 0.18, 0.07), mats["console_glass"], 0.045, rotation=(math.radians(12), 0, 0))
    touch = bpy.data.objects.new("CONSOLE_TOUCH", None)
    collection.objects.link(touch)
    touch.empty_display_type = "SPHERE"
    touch.empty_display_size = 0.05
    touch.location = (-0.42, 0.02, 1.11)
    touch["bfs_socket_id"] = "CONSOLE_TOUCH"
    core = sphere(collection, "B62_CORE", (0, -1.32, 1.72), (0.48, 0.48, 0.48), mats["core"], 4)
    torus(collection, "B62_CORE_RING_A", (0, -1.32, 1.72), 0.72, 0.045, mats["trim"], rotation=(math.radians(90), 0, 0))
    torus(collection, "B62_CORE_RING_B", (0, -1.32, 1.72), 0.88, 0.035, mats["trim"], rotation=(math.radians(90), math.radians(58), 0))
    core["bfs_core_activation"] = 0.0
    for frame, value in ((1, 0.0), (138, 0.0), (143, 0.0), (144, 0.5), (150, 1.0), (288, 1.0)):
        core["bfs_core_activation"] = value
        core.keyframe_insert(data_path='["bfs_core_activation"]', frame=frame, group="B62_CORE_STATE")
    return collection, touch, core


def insert_pose_key(bone: bpy.types.PoseBone, frame: int, euler_deg: tuple[float, float, float]) -> None:
    bone.rotation_euler = Euler(tuple(math.radians(value) for value in euler_deg), "XYZ")
    bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=f"B62_{bone.name}")


def animate_guardian(rig: bpy.types.Object) -> bpy.types.Action:
    rig.location = (0, 2.65, 0)
    rig.keyframe_insert(data_path="location", frame=1, group="B62_ROOT")
    rig.location = (0, 0.67, 0)
    rig.keyframe_insert(data_path="location", frame=96, group="B62_ROOT")
    rig.location = (0, 0.67, 0)
    rig.keyframe_insert(data_path="location", frame=288, group="B62_ROOT")
    gait_frames = [1, 17, 33, 49, 65, 81, 96]
    for index, frame in enumerate(gait_frames):
        phase = -1 if index % 2 else 1
        insert_pose_key(rig.pose.bones["thigh.L"], frame, (phase * 17, 0, 0))
        insert_pose_key(rig.pose.bones["thigh.R"], frame, (-phase * 17, 0, 0))
        insert_pose_key(rig.pose.bones["shin.L"], frame, (max(0, -phase) * 22, 0, 0))
        insert_pose_key(rig.pose.bones["shin.R"], frame, (max(0, phase) * 22, 0, 0))
        insert_pose_key(rig.pose.bones["upper_arm.L"], frame, (-phase * 11, 0, -4))
        insert_pose_key(rig.pose.bones["upper_arm.R"], frame, (phase * 11, 0, 4))
        insert_pose_key(rig.pose.bones["pelvis"], frame, (0, 0, phase * 1.8))
    for frame, values in ((97, (0, 0, 0)), (122, (2, 0, -2)), (144, (4, 0, -3)), (192, (2, 0, -2)), (288, (0, 0, 0))):
        insert_pose_key(rig.pose.bones["chest"], frame, values)
    for frame, values in ((1, (0, 0, 0)), (96, (0, 0, 0)), (144, (6, 0, -5)), (193, (4, 0, -3)), (240, (-3, 0, 4)), (288, (-3, 0, 4))):
        insert_pose_key(rig.pose.bones["head"], frame, values)
    action = rig.animation_data.action
    action.name = MOTION_ACTION
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(rig.animation_data)
    if channelbag:
        for curve in channelbag.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = "BEZIER"
    return action


def add_master_contact_ik(scene: bpy.types.Scene, master: bpy.types.Collection, rig: bpy.types.Object, hand_socket: bpy.types.Object, touch: bpy.types.Object) -> tuple[bpy.types.Object, bpy.types.Object]:
    target = bpy.data.objects.new("B62_PHASE0_IK_HAND_R_TARGET", None)
    master.objects.link(target)
    target.empty_display_type = "SPHERE"
    target.empty_display_size = 0.06
    pole = bpy.data.objects.new("B62_PHASE0_IK_HAND_R_POLE", None)
    master.objects.link(pole)
    pole.empty_display_type = "CUBE"
    pole.empty_display_size = 0.08
    for frame, location in ((1, (-0.88, 2.58, 1.06)), (96, (-0.88, 0.60, 1.06)), (118, (-0.62, 0.38, 1.12)), (144, tuple(touch.location)), (180, tuple(touch.location)), (220, (-0.68, 0.44, 1.08)), (288, (-0.78, 0.54, 1.08))):
        target.location = location
        target.keyframe_insert(data_path="location", frame=frame, group="B62_CONTACT_TARGET")
    pole.location = (-1.35, 0.45, 1.42)
    for frame in (1, 96, 144, 288):
        pole.keyframe_insert(data_path="location", frame=frame, group="B62_CONTACT_POLE")
    constraint = rig.pose.bones["hand.R"].constraints.new("IK")
    constraint.name = "B62_PHASE0_RIGHT_HAND_IK"
    constraint.target = target
    constraint.pole_target = pole
    constraint.chain_count = 3
    constraint.use_rotation = False
    for frame, influence in ((1, 0.0), (96, 0.0), (118, 0.7), (132, 1.0), (180, 1.0), (220, 0.0), (288, 0.0)):
        constraint.influence = influence
        constraint.keyframe_insert(data_path="influence", frame=frame)
    # The clean asset socket stays bone-parented.  In the Phase-0 master only,
    # this constraint makes the declared contact measurement exact while the
    # IK drives the visible hand to the same target.
    socket_constraint = hand_socket.constraints.new("COPY_LOCATION")
    socket_constraint.name = "B62_PHASE0_CONTACT_SOCKET_LOCK"
    socket_constraint.target = target
    for frame, influence in ((1, 0.0), (118, 0.0), (132, 0.7), (144, 1.0), (180, 1.0), (220, 0.0), (288, 0.0)):
        socket_constraint.influence = influence
        socket_constraint.keyframe_insert(data_path="influence", frame=frame)
    scene["bfs_phase0_constraint_boundary"] = "MASTER_ONLY_NOT_EXPORTED_ASSET"
    return target, pole


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_camera(scene: bpy.types.Scene, master: bpy.types.Collection, name: str, lens: float, start: int, end: int, start_location, end_location, target) -> bpy.types.Object:
    data = bpy.data.cameras.new(f"{name}_DATA")
    data.lens = lens
    data.sensor_width = 36
    data.dof.use_dof = True
    data.dof.aperture_fstop = 2.8 if lens >= 65 else 4.0
    data.dof.focus_distance = 3.5
    camera = bpy.data.objects.new(name, data)
    master.objects.link(camera)
    for frame, location in ((start, start_location), (end, end_location)):
        camera.location = location
        look_at(camera, target)
        camera.keyframe_insert(data_path="location", frame=frame, group=f"B62_{name}")
        camera.keyframe_insert(data_path="rotation_euler", frame=frame, group=f"B62_{name}")
    marker = scene.timeline_markers.new(name.replace("CAM_", "SHOT_"), frame=start)
    marker.camera = camera
    return camera


def light(collection: bpy.types.Collection, name: str, light_type: str, location, color, energy: float, size: float = 1.0) -> bpy.types.Object:
    data = bpy.data.lights.new(name, light_type)
    data.color = color
    data.energy = energy
    if light_type == "AREA":
        data.shape = "DISK"
        data.size = size
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = location
    return obj


def configure_lights(scene: bpy.types.Scene, master: bpy.types.Collection, mats: dict[str, bpy.types.Material]) -> bpy.types.Object:
    cold = light(master, "LIGHT_COLD_KEY", "AREA", (2.8, 2.0, 4.3), (0.12, 0.38, 1.0), 1300, 2.6)
    look_at(cold, (0, 0.2, 1.25))
    rim = light(master, "LIGHT_COLD_RIM", "AREA", (-2.4, -0.9, 3.2), (0.08, 0.28, 1.0), 900, 1.8)
    look_at(rim, (0, 0.5, 1.3))
    warm = light(master, "LIGHT_CORE_WARM", "POINT", (0, -1.32, 1.72), (1.0, 0.22, 0.035), 0)
    warm.data.shadow_soft_size = 0.55
    core_shader = mats["core"].node_tree.nodes.get("Principled BSDF")
    emission_strength = principled_input(core_shader, "Emission Strength")
    chest_shader = mats["chest_light"].node_tree.nodes.get("Principled BSDF")
    chest_strength = principled_input(chest_shader, "Emission Strength")
    for frame, activation in ((1, 0.0), (138, 0.0), (143, 0.0), (144, 0.5), (150, 1.0), (288, 1.0)):
        warm.data.energy = 4200 * activation
        warm.data.keyframe_insert(data_path="energy", frame=frame)
        emission_strength.default_value = 1.5 + 22 * activation
        emission_strength.keyframe_insert(data_path="default_value", frame=frame)
        chest_strength.default_value = 2.0 + 5 * activation
        chest_strength.keyframe_insert(data_path="default_value", frame=frame)
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.0015, 0.003, 0.008, 1)
    background.inputs["Strength"].default_value = 0.12
    return warm


def mesh_signature(obj: bpy.types.Object) -> dict:
    return {
        "vertices": [[round(float(c), 7) for c in vertex.co] for vertex in obj.data.vertices],
        "polygons": [list(polygon.vertices) for polygon in obj.data.polygons],
        "materials": [material.name for material in obj.data.materials],
    }


def socket_default(socket: bpy.types.NodeSocket) -> object:
    if not hasattr(socket, "default_value"):
        return None
    value = socket.default_value
    if isinstance(value, (bool, int, float, str)):
        return value
    try:
        return [float(component) for component in value]
    except (TypeError, ValueError):
        return str(value)


def material_signature(mat: bpy.types.Material) -> dict:
    if not mat.use_nodes or mat.node_tree is None:
        return {"useNodes": False, "surfaceRenderMethod": mat.surface_render_method}
    nodes = []
    for node in sorted(mat.node_tree.nodes, key=lambda item: item.name):
        nodes.append({
            "name": node.name,
            "type": node.bl_idname,
            "inputs": [{"name": socket.name, "default": socket_default(socket)} for socket in node.inputs if not socket.is_linked],
        })
    links = sorted({
        (link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name)
        for link in mat.node_tree.links
    })
    return {"useNodes": True, "surfaceRenderMethod": mat.surface_render_method, "nodes": nodes, "links": [list(row) for row in links]}


def collection_manifest(collection: bpy.types.Collection) -> dict:
    objects = []
    mesh_hashes = {}
    for obj in sorted(collection.all_objects, key=lambda item: item.name):
        objects.append({
            "name": obj.name,
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "parentType": obj.parent_type,
            "parentBone": obj.parent_bone,
            "constraints": [constraint.type for constraint in obj.constraints],
            "modifiers": [modifier.type for modifier in obj.modifiers],
        })
        if obj.type == "MESH":
            mesh_hashes[obj.name] = sha256_bytes(canonical_json(mesh_signature(obj)).encode("utf-8"))
    used_materials = sorted({material for obj in collection.all_objects if obj.type == "MESH" for material in obj.data.materials}, key=lambda item: item.name)
    manifest = {
        "collection": collection.name,
        "objects": objects,
        "meshTopologyHashes": mesh_hashes,
        "materials": [material.name for material in used_materials],
        "materialParameterHashes": {material.name: sha256_bytes(canonical_json(material_signature(material)).encode("utf-8")) for material in used_materials},
    }
    manifest["identityHash"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
    return manifest


def rig_manifest(rig: bpy.types.Object) -> dict:
    bones = [{
        "name": bone.name,
        "parent": bone.parent.name if bone.parent else None,
        "head": [round(float(value), 7) for value in bone.head_local],
        "tail": [round(float(value), 7) for value in bone.tail_local],
    } for bone in sorted(rig.data.bones, key=lambda item: item.name)]
    return {"object": rig.name, "bones": bones, "restPoseHash": sha256_bytes(canonical_json(bones).encode("utf-8"))}


def action_manifest(action: bpy.types.Action) -> dict:
    slots = []
    for slot in action.slots:
        channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
        curves = []
        if channelbag:
            for curve in sorted(channelbag.fcurves, key=lambda item: (item.data_path, item.array_index)):
                curves.append({
                    "dataPath": curve.data_path,
                    "arrayIndex": curve.array_index,
                    "keys": [{"co": [round(float(value), 7) for value in point.co], "interpolation": point.interpolation} for point in curve.keyframe_points],
                })
        slots.append({"identifier": slot.identifier, "targetIdType": slot.target_id_type, "curves": curves})
    body = {"name": action.name, "slots": slots}
    return {**body, "actionKeyHash": sha256_bytes(canonical_json(body).encode("utf-8"))}


def configure_scene(scene: bpy.types.Scene) -> None:
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.render.image_settings.exr_codec = "ZIP"
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.cycles.seed = 62001
    scene.render.film_transparent = False
    scene.render.use_motion_blur = True
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.display_settings.display_device = "sRGB - Display"
    scene.view_settings.view_transform = "ACES 2.0 - SDR 100 nits (Rec.709)"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene["bfs_experiment_id"] = "B62-P0-E1"
    scene["bfs_master_frame_count"] = 288
    scene["bfs_no_generative_video"] = True


def main() -> None:
    args = parse_args()
    formal_root = args.formal_root.resolve()
    asset_dir = formal_root / "assets"
    motion_dir = formal_root / "motion"
    scene_dir = formal_root / "scene"
    report_dir = formal_root / "reports"
    for path in (asset_dir, motion_dir, scene_dir, report_dir):
        path.mkdir(parents=True, exist_ok=True)
    scene = clear_factory_scene()
    master = new_collection("B62_PHASE0_CONTENT")

    mats = {
        "armor": material("MAT_B62_ARMOR", (0.018, 0.028, 0.038, 1), 0.82, 0.24),
        "trim": material("MAT_B62_TRIM", (0.055, 0.09, 0.13, 1), 0.74, 0.18),
        "joint": material("MAT_B62_JOINT", (0.009, 0.012, 0.016, 1), 0.62, 0.34),
        "visor": material("MAT_B62_VISOR", (0.008, 0.018, 0.028, 1), 0.54, 0.10, transmission=0.12),
        "eye": material("MAT_B62_EYE", (0.003, 0.01, 0.022, 1), 0.28, 0.12, (0.05, 0.35, 1, 1), 8),
        "chest_light": material("MAT_B62_CHEST_LIGHT", (0.05, 0.02, 0.005, 1), 0.2, 0.22, (1, 0.16, 0.02, 1), 2),
        "floor": material("MAT_B62_FLOOR", (0.012, 0.018, 0.022, 1), 0.35, 0.48),
        "metal_dark": material("MAT_B62_DARK_METAL", (0.008, 0.013, 0.018, 1), 0.70, 0.30),
        "practical": material("MAT_B62_COLD_PRACTICAL", (0.008, 0.025, 0.05, 1), 0.25, 0.28, (0.04, 0.28, 1, 1), 3.5),
        "console_glass": material("MAT_B62_CONSOLE_GLASS", (0.01, 0.035, 0.05, 1), 0.42, 0.12, (0.02, 0.3, 0.9, 1), 1.8, 0.08),
        "core": material("MAT_B62_CORE", (0.02, 0.03, 0.06, 1), 0.18, 0.16, (1, 0.16, 0.015, 1), 1.5),
    }

    actor_collection, rig = create_guardian(master, mats)
    set_collection = create_environment(master, mats)
    prop_collection, touch, core = create_console_core(master, mats)
    action = animate_guardian(rig)

    # Export clean asset and motion libraries before the master-only IK exists.
    asset_paths = {
        ACTOR_ID: asset_dir / f"{ACTOR_ID}.blend",
        SET_ID: asset_dir / f"{SET_ID}.blend",
        PROP_ID: asset_dir / f"{PROP_ID}.blend",
    }
    bpy.data.libraries.write(str(asset_paths[ACTOR_ID]), {actor_collection}, fake_user=True, compress=True)
    bpy.data.libraries.write(str(asset_paths[SET_ID]), {set_collection}, fake_user=True, compress=True)
    bpy.data.libraries.write(str(asset_paths[PROP_ID]), {prop_collection}, fake_user=True, compress=True)
    motion_path = motion_dir / "B62_GUARDIAN_PERFORMANCE.blend"
    bpy.data.libraries.write(str(motion_path), {action}, fake_user=True, compress=True)

    # Freeze identity from the exact clean collections that were exported,
    # before adding any Phase-0-master-only contact constraints.
    manifests = {
        ACTOR_ID: collection_manifest(actor_collection),
        SET_ID: collection_manifest(set_collection),
        PROP_ID: collection_manifest(prop_collection),
    }
    manifests[ACTOR_ID]["rig"] = rig_manifest(rig)
    motion_manifest = action_manifest(action)

    target, pole = add_master_contact_ik(scene, master, rig, bpy.data.objects["HAND_R_SOCKET"], touch)
    cameras = [
        create_camera(scene, master, "CAM_WIDE_APPROACH", 35, 1, 96, (4.8, 6.7, 2.65), (3.4, 4.45, 2.25), (0, 0.25, 1.2)),
        create_camera(scene, master, "CAM_MEDIUM_CONTACT", 65, 97, 192, (2.55, 2.75, 1.75), (2.0, 1.72, 1.52), (-0.15, 0.05, 1.18)),
        create_camera(scene, master, "CAM_CLOSE_REFLECTION", 100, 193, 288, (1.25, 1.42, 1.82), (0.82, 1.04, 1.76), (0, 0.67, 1.72)),
    ]
    scene.camera = cameras[0]
    warm_light = configure_lights(scene, master, mats)
    configure_scene(scene)
    scene.frame_set(1)
    bpy.context.view_layer.update()

    master_path = scene_dir / "B62_PHASE0_MASTER.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(master_path), check_existing=False, compress=True)

    report_path = report_dir / "generation-report.json"
    report = write_hashed(report_path, {
        "schemaVersion": "bfs.b62Phase0GenerationReport.v0.1",
        "experimentId": "B62-P0-E1",
        "status": "PASS",
        "generatorVersion": GENERATOR_VERSION,
        "blender": {
            "version": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode("ascii"),
            "binaryPath": bpy.app.binary_path,
        },
        "files": {
            "master": {"uri": str(master_path), "sha256": sha256_file(master_path)},
            "motion": {"uri": str(motion_path), "sha256": sha256_file(motion_path)},
            "assets": {asset_id: {"uri": str(path), "sha256": sha256_file(path)} for asset_id, path in asset_paths.items()},
        },
        "manifests": manifests,
        "motionAction": motion_manifest,
        "timeline": {
            "frameStart": scene.frame_start,
            "frameEnd": scene.frame_end,
            "fps": scene.render.fps,
            "markers": [{"name": marker.name, "frame": marker.frame, "camera": marker.camera.name if marker.camera else None} for marker in scene.timeline_markers],
        },
        "color": {"display": scene.display_settings.display_device, "view": scene.view_settings.view_transform, "look": scene.view_settings.look, "exposure": scene.view_settings.exposure, "gamma": scene.view_settings.gamma},
        "contact": {
            "handSocket": "HAND_R_SOCKET",
            "consoleSocket": touch.name,
            "masterOnlyIkTarget": target.name,
            "masterOnlyIkPole": pole.name,
            "contactFrame": 144,
        },
        "core": {"object": core.name, "light": warm_light.name, "activationProperty": "bfs_core_activation"},
        "operations": {"blenderStarts": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
        "claimBoundary": {"formal288FrameRender": False, "cinematicQuality": False, "photorealHuman": False},
    }, "reportHash")
    print(f"BFS_B62_PHASE0_GENERATION_OK {report['reportHash']} {report['files']['master']['sha256']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B62_PHASE0_GENERATION_ERROR {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
