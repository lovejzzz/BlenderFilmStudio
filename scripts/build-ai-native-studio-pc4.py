#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build the screenshot-led PC.4 hero shell and performance derivative."""

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
import OpenImageIO as oiio
from mathutils import Euler, Matrix


SENTINELS = (48, 144, 240)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_self(value, field):
    body = dict(value)
    expected = body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()


def write_self(path, value, field):
    body = dict(value)
    body[field] = hashlib.sha256(canonical(body)).hexdigest()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, (json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return body


def rounded(values):
    return [round(float(value), 8) for value in values]


def camera_light_state(scene):
    rows = []
    cameras = sorted((obj for obj in bpy.data.objects if obj.type == "CAMERA"), key=lambda obj: obj.name)
    lights = sorted((obj for obj in bpy.data.objects if obj.type == "LIGHT"), key=lambda obj: obj.name)
    for frame in SENTINELS:
        scene.frame_set(frame)
        rows.append({
            "frame": frame,
            "cameras": {obj.name: {"matrixWorld": [rounded(row) for row in obj.matrix_world], "lens": round(float(obj.data.lens), 8)} for obj in cameras},
            "lights": {obj.name: {"matrixWorld": [rounded(row) for row in obj.matrix_world], "energy": round(float(obj.data.energy), 8), "color": rounded(obj.data.color)} for obj in lights},
        })
    return rows


def input_named(node, *names):
    for name in names:
        if name in node.inputs:
            return node.inputs[name]
    raise RuntimeError(f"MISSING_INPUT_{names}")


def material(name, color, metallic, roughness, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    input_named(shader, "Base Color").default_value = (*color, 1.0)
    input_named(shader, "Metallic").default_value = metallic
    input_named(shader, "Roughness").default_value = roughness
    if "Coat Weight" in shader.inputs:
        shader.inputs["Coat Weight"].default_value = 0.22
        shader.inputs["Coat Roughness"].default_value = 0.18
    if emission is not None:
        input_named(shader, "Emission Color", "Emission").default_value = (*emission, 1.0)
        input_named(shader, "Emission Strength").default_value = emission_strength
    mat["bfs_pc4_material_region"] = name
    return mat


def move_to_collection(obj, collection):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def parent_like(obj, anchor):
    world = obj.matrix_world.copy()
    if anchor.parent and anchor.parent_type == "BONE":
        obj.parent = anchor.parent
        obj.parent_type = "BONE"
        obj.parent_bone = anchor.parent_bone
    else:
        obj.parent = anchor
    obj.matrix_world = world


def finish(obj, collection, anchor, mat, system):
    move_to_collection(obj, collection)
    obj.data.materials.append(mat)
    obj["bfs_pc4_part"] = obj.name
    obj["bfs_pc4_system"] = system
    obj["bfs_pc4_material_region"] = mat.name
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    parent_like(obj, anchor)
    return obj


def apply_bevel(obj, width, segments=4):
    modifier = obj.modifiers.new("PC4_BAKED_BEVEL", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def part_matrix(anchor, offset, rotation):
    return anchor.matrix_world @ Matrix.Translation(offset) @ Euler(rotation, "XYZ").to_matrix().to_4x4()


def box(collection, name, anchor_name, offset, scale, mat, system, rotation=(0.0, 0.0, 0.0), bevel=None):
    anchor = bpy.data.objects[anchor_name]
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_bevel(obj, bevel if bevel is not None else min(scale) * 0.32)
    obj.matrix_world = part_matrix(anchor, offset, rotation)
    return finish(obj, collection, anchor, mat, system)


def sphere(collection, name, anchor_name, offset, scale, mat, system):
    anchor = bpy.data.objects[anchor_name]
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=24)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.matrix_world = part_matrix(anchor, offset, (0.0, 0.0, 0.0))
    return finish(obj, collection, anchor, mat, system)


def cone(collection, name, anchor_name, offset, radius1, radius2, depth, mat, system, rotation=(0.0, 0.0, 0.0)):
    anchor = bpy.data.objects[anchor_name]
    bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=radius1, radius2=radius2, depth=depth)
    obj = bpy.context.object
    obj.name = name
    apply_bevel(obj, min(radius1, radius2) * 0.18, 3)
    obj.matrix_world = part_matrix(anchor, offset, rotation)
    return finish(obj, collection, anchor, mat, system)


def torus(collection, name, anchor_name, offset, major, minor, mat, system, rotation=(0.0, 0.0, 0.0)):
    anchor = bpy.data.objects[anchor_name]
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=48, minor_segments=12)
    obj = bpy.context.object
    obj.name = name
    obj.matrix_world = part_matrix(anchor, offset, rotation)
    return finish(obj, collection, anchor, mat, system)


def hull(collection, name, anchor_name, offset, rings, mat, system, rotation=(0.0, 0.0, 0.0), segments=32):
    anchor = bpy.data.objects[anchor_name]
    vertices = []
    for z, radius_x, radius_y, center_y in rings:
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            vertices.append((radius_x * math.cos(angle), center_y + radius_y * math.sin(angle), z))
    faces = []
    for ring_index in range(len(rings) - 1):
        start = ring_index * segments
        nxt = (ring_index + 1) * segments
        for index in range(segments):
            following = (index + 1) % segments
            faces.append((start + index, start + following, nxt + following, nxt + index))
    bottom_center = len(vertices)
    vertices.append((0.0, rings[0][3], rings[0][0]))
    top_center = len(vertices)
    vertices.append((0.0, rings[-1][3], rings[-1][0]))
    for index in range(segments):
        following = (index + 1) % segments
        faces.append((bottom_center, following, index))
        top_start = (len(rings) - 1) * segments
        faces.append((top_center, top_start + index, top_start + following))
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    apply_bevel(obj, 0.014, 3)
    obj.matrix_world = part_matrix(anchor, offset, rotation)
    return finish(obj, collection, anchor, mat, system)


def hide_exact(names):
    missing = [name for name in names if name not in bpy.data.objects]
    if missing:
        raise RuntimeError("MISSING_HIDE_OBJECTS_" + ",".join(missing))
    for name in names:
        obj = bpy.data.objects[name]
        obj.hide_render = True
        obj.hide_set(True)


def build_shell(spec):
    collection = bpy.data.collections.new("PC4_HERO_REDESIGN")
    bpy.context.scene.collection.children.link(collection)
    armor = material("MAT_PC4_ARMOR", (0.025, 0.055, 0.085), 0.76, 0.23)
    graphite = material("MAT_PC4_GRAPHITE", (0.008, 0.014, 0.022), 0.48, 0.32)
    edge = material("MAT_PC4_EDGE", (0.12, 0.20, 0.24), 0.88, 0.16)
    cyan = material("MAT_PC4_CYAN_EMISSIVE", (0.0, 0.22, 0.34), 0.34, 0.16, (0.02, 0.80, 1.0), 7.0)
    coral = material("MAT_PC4_CORAL_EMISSIVE", (0.32, 0.018, 0.008), 0.28, 0.20, (1.0, 0.035, 0.012), 7.0)

    hull(collection, "PC4_TORSO_HULL", "B62_TORSO", (0.0, 0.0, 0.0), [(-0.34, 0.27, 0.19, 0.02), (-0.20, 0.34, 0.22, 0.0), (0.12, 0.43, 0.235, -0.01), (0.31, 0.35, 0.19, 0.0)], armor, "torso")
    box(collection, "PC4_CHEST_CARAPACE", "B62_CHEST_PLATE", (0.0, -0.055, 0.01), (0.31, 0.055, 0.205), edge, "torso", rotation=(math.radians(-4), 0.0, 0.0), bevel=0.035)
    torus(collection, "PC4_CHEST_REACTOR_FRAME", "B62_CHEST_LIGHT", (0.0, -0.035, 0.0), 0.105, 0.018, graphite, "torso", rotation=(math.radians(90), 0.0, 0.0))
    cone(collection, "PC4_CHEST_REACTOR_LENS", "B62_CHEST_LIGHT", (0.0, -0.052, 0.0), 0.075, 0.068, 0.035, coral, "torso", rotation=(math.radians(90), 0.0, 0.0))
    hull(collection, "PC4_WAIST_HULL", "B62_PELVIS", (0.0, 0.0, 0.02), [(-0.17, 0.25, 0.18, 0.0), (-0.06, 0.31, 0.20, 0.0), (0.11, 0.28, 0.19, 0.0), (0.18, 0.22, 0.16, 0.0)], graphite, "waist", segments=28)

    hull(collection, "PC4_HELMET_SHELL", "B62_HELMET", (0.0, 0.0, 0.0), [(-0.27, 0.19, 0.18, 0.015), (-0.17, 0.28, 0.235, 0.0), (0.10, 0.30, 0.25, 0.015), (0.26, 0.22, 0.17, 0.045)], armor, "head")
    box(collection, "PC4_FACEPLATE", "B62_VISOR", (0.0, -0.055, -0.005), (0.235, 0.045, 0.125), graphite, "head", bevel=0.028)
    box(collection, "PC4_VISOR_FRAME", "B62_VISOR", (0.0, -0.108, 0.035), (0.205, 0.018, 0.045), edge, "head", bevel=0.014)
    box(collection, "PC4_VISOR_LENS", "B62_VISOR", (0.0, -0.129, 0.035), (0.165, 0.009, 0.020), cyan, "head", bevel=0.008)
    box(collection, "PC4_CHIN_GUARD", "B62_HELMET", (0.0, -0.225, -0.175), (0.17, 0.055, 0.060), edge, "head", rotation=(math.radians(-10), 0.0, 0.0), bevel=0.022)
    for side, sign in (("L", 1.0), ("R", -1.0)):
        cone(collection, f"PC4_SIDE_POD_{side}", "B62_HELMET", (0.285 * sign, 0.015, 0.01), 0.085, 0.070, 0.055, coral if side == "L" else cyan, "head", rotation=(0.0, math.radians(90), 0.0))
    torus(collection, "PC4_NECK_RING_LOWER", "B62_NECK", (0.0, 0.0, -0.035), 0.115, 0.018, edge, "neck")
    torus(collection, "PC4_NECK_RING_UPPER", "B62_NECK", (0.0, 0.0, 0.035), 0.105, 0.014, cyan, "neck")

    for side, sign in (("L", 1.0), ("R", -1.0)):
        shoulder = f"B62_SHOULDER_{side}"
        upper = f"B62_UPPER_ARM_{side}"
        forearm = f"B62_FOREARM_{side}"
        hand = f"B62_HAND_{side}"
        thigh = f"B62_THIGH_{side}"
        shin = f"B62_SHIN_{side}"
        foot = f"B62_FOOT_{side}"
        sphere(collection, f"PC4_SHOULDER_SHELL_{side}", shoulder, (0.0, 0.0, 0.03), (0.19, 0.255, 0.15), armor, "arm")
        box(collection, f"PC4_SHOULDER_CAP_{side}", shoulder, (0.05 * sign, -0.06, 0.085), (0.16, 0.17, 0.055), edge, "arm", rotation=(0.0, math.radians(12 * sign), math.radians(-8 * sign)), bevel=0.025)
        cone(collection, f"PC4_UPPER_ARM_{side}", upper, (0.0, 0.0, 0.0), 0.115, 0.085, 0.38, armor, "arm")
        sphere(collection, f"PC4_ELBOW_{side}", forearm, (0.0, 0.0, 0.18), (0.12, 0.12, 0.11), edge, "arm")
        cone(collection, f"PC4_FOREARM_{side}", forearm, (0.0, 0.0, -0.025), 0.13, 0.085, 0.34, graphite, "arm")
        box(collection, f"PC4_PALM_{side}", hand, (0.0, -0.035, 0.0), (0.105, 0.095, 0.065), armor, "hand", bevel=0.026)
        for index, x_offset in enumerate((-0.065, 0.0, 0.065)):
            box(collection, f"PC4_FINGER_{side}_{index}", hand, (x_offset, -0.145, -0.012), (0.022, 0.075, 0.024), edge if index != 1 else coral, "hand", rotation=(math.radians(-8), 0.0, 0.0), bevel=0.012)
        cone(collection, f"PC4_THIGH_{side}", thigh, (0.0, 0.0, 0.0), 0.155, 0.115, 0.44, armor, "leg")
        sphere(collection, f"PC4_KNEE_{side}", shin, (0.0, -0.025, 0.205), (0.13, 0.11, 0.10), edge, "leg")
        cone(collection, f"PC4_SHIN_{side}", shin, (0.0, 0.0, -0.015), 0.125, 0.085, 0.40, graphite, "leg")
        torus(collection, f"PC4_ANKLE_{side}", foot, (0.0, 0.0, 0.105), 0.092, 0.016, cyan, "leg")
        box(collection, f"PC4_FOOT_{side}", foot, (0.0, -0.075, -0.015), (0.145, 0.265, 0.105), armor, "leg", rotation=(math.radians(2), 0.0, 0.0), bevel=0.035)

    box(collection, "PC4_BACK_SPINE", "B62_TORSO", (0.0, 0.225, 0.0), (0.075, 0.045, 0.26), edge, "back", bevel=0.02)
    box(collection, "PC4_BACK_VENT_L", "B62_TORSO", (0.18, 0.22, 0.08), (0.075, 0.035, 0.12), cyan, "back", rotation=(0.0, 0.0, math.radians(-8)), bevel=0.014)
    box(collection, "PC4_BACK_VENT_R", "B62_TORSO", (-0.18, 0.22, 0.08), (0.075, 0.035, 0.12), coral, "back", rotation=(0.0, 0.0, math.radians(8)), bevel=0.014)

    box(collection, "PC4_CONSOLE_HOLO_FRAME", "B62_CONSOLE_SURFACE", (0.0, 0.08, 0.24), (0.34, 0.025, 0.17), edge, "console", rotation=(math.radians(-18), 0.0, 0.0), bevel=0.022)
    box(collection, "PC4_CONSOLE_HOLO_LENS", "B62_CONSOLE_SURFACE", (0.0, 0.045, 0.24), (0.30, 0.012, 0.135), cyan, "console", rotation=(math.radians(-18), 0.0, 0.0), bevel=0.012)
    for index in range(6):
        box(collection, f"PC4_CONSOLE_CONTROL_{index}", "B62_CONSOLE_SURFACE", (-0.375 + 0.15 * index, -0.08, 0.095), (0.045, 0.035, 0.018), coral if index in (1, 4) else edge, "console", bevel=0.010)

    roster = sorted(obj.name for obj in collection.objects)
    if roster != sorted(spec["createdParts"]):
        raise RuntimeError("CREATED_PART_ROSTER")
    return collection, {"armor": armor, "graphite": graphite, "edge": edge, "cyan": cyan, "coral": coral}


def sample_then_offset(scene, target, data_path, index, frames, offsets, label, phase):
    bases = []
    for frame in frames:
        scene.frame_set(frame)
        bases.append(float(getattr(target, data_path)[index]))
    values = [base + offset for base, offset in zip(bases, offsets, strict=True)]
    for frame, value in zip(frames, values, strict=True):
        scene.frame_set(frame)
        getattr(target, data_path)[index] = value
        target.keyframe_insert(data_path=data_path, index=index, frame=frame, group="PC4_READABLE_PERFORMANCE")
    return {"phase": phase, "target": label, "dataPath": data_path, "arrayIndex": index, "frames": frames, "values": rounded(values), "peakToPeak": round(max(values) - min(values), 8)}


def animate_performance(scene, materials):
    rig = bpy.data.objects["RIG_B62_GUARDIAN"]
    rig.rotation_mode = "XYZ"
    chest = rig.pose.bones["chest"]
    head = rig.pose.bones["head"]
    upper_left = rig.pose.bones["upper_arm.L"]
    for bone in (chest, head, upper_left):
        bone.rotation_mode = "XYZ"
    target = bpy.data.objects["B62_PHASE0_IK_HAND_R_TARGET"]
    pole = bpy.data.objects["B62_PHASE0_IK_HAND_R_POLE"]
    signals = []

    approach = [1, 20, 40, 60, 80, 96]
    signals.append(sample_then_offset(scene, rig, "location", 0, approach, [-0.05, 0.04, -0.035, 0.055, -0.02, 0.0], rig.name, "APPROACH_ANTICIPATION"))
    signals.append(sample_then_offset(scene, rig, "location", 2, approach, [0.0, 0.055, 0.015, 0.075, 0.025, 0.0], rig.name, "WEIGHT_TRANSFER"))
    signals.append(sample_then_offset(scene, rig, "rotation_euler", 2, approach, [-0.04, 0.055, -0.035, 0.07, -0.02, 0.0], rig.name, "WEIGHT_TRANSFER"))
    signals.append(sample_then_offset(scene, chest, "rotation_euler", 2, approach, [-0.03, 0.07, -0.055, 0.09, -0.03, 0.0], 'RIG_B62_GUARDIAN.pose.bones["chest"]', "WEIGHT_TRANSFER"))

    contact = [97, 112, 128, 144, 160, 176, 192]
    signals.append(sample_then_offset(scene, target, "location", 0, contact, [0.0, -0.04, -0.10, -0.16, -0.12, -0.05, 0.0], target.name, "CONTACT_REACH_AND_BRACE"))
    signals.append(sample_then_offset(scene, target, "location", 1, contact, [0.0, -0.05, -0.15, -0.24, -0.20, -0.08, 0.0], target.name, "CONTACT_REACH_AND_BRACE"))
    signals.append(sample_then_offset(scene, target, "location", 2, contact, [0.0, 0.06, 0.14, 0.20, 0.13, 0.05, 0.0], target.name, "CONTACT_REACH_AND_BRACE"))
    signals.append(sample_then_offset(scene, pole, "location", 0, contact, [0.0, -0.04, -0.10, -0.13, -0.09, -0.03, 0.0], pole.name, "CONTACT_REACH_AND_BRACE"))
    signals.append(sample_then_offset(scene, chest, "rotation_euler", 0, contact, [0.0, -0.05, -0.12, -0.19, -0.12, -0.04, 0.0], 'RIG_B62_GUARDIAN.pose.bones["chest"]', "CONTACT_REACH_AND_BRACE"))
    signals.append(sample_then_offset(scene, head, "rotation_euler", 0, contact, [0.0, 0.04, 0.11, 0.18, 0.12, 0.04, 0.0], 'RIG_B62_GUARDIAN.pose.bones["head"]', "CONTACT_REACH_AND_BRACE"))
    signals.append(sample_then_offset(scene, upper_left, "rotation_euler", 0, contact, [0.0, 0.04, 0.10, 0.16, 0.10, 0.03, 0.0], 'RIG_B62_GUARDIAN.pose.bones["upper_arm.L"]', "CONTACT_REACH_AND_BRACE"))

    reaction = [136, 144, 152, 160, 176, 192]
    signals.append(sample_then_offset(scene, chest, "rotation_euler", 1, reaction, [0.0, -0.035, -0.10, -0.17, -0.055, 0.0], 'RIG_B62_GUARDIAN.pose.bones["chest"]', "ACTIVATION_REACTION"))
    signals.append(sample_then_offset(scene, head, "rotation_euler", 1, reaction, [0.0, 0.035, -0.07, -0.13, -0.035, 0.0], 'RIG_B62_GUARDIAN.pose.bones["head"]', "ACTIVATION_REACTION"))
    signals.append(sample_then_offset(scene, rig, "location", 1, reaction, [0.0, 0.02, 0.055, 0.09, 0.025, 0.0], rig.name, "ACTIVATION_REACTION"))

    reflection = [193, 208, 224, 240, 256, 272, 288]
    signals.append(sample_then_offset(scene, head, "rotation_euler", 2, reflection, [0.0, -0.08, -0.17, -0.06, 0.15, 0.07, 0.0], 'RIG_B62_GUARDIAN.pose.bones["head"]', "REFLECTION_AND_SETTLE"))
    signals.append(sample_then_offset(scene, head, "rotation_euler", 0, reflection, [0.0, 0.035, 0.09, 0.15, 0.075, 0.025, 0.0], 'RIG_B62_GUARDIAN.pose.bones["head"]', "REFLECTION_AND_SETTLE"))
    signals.append(sample_then_offset(scene, chest, "rotation_euler", 0, reflection, [0.0, 0.025, 0.065, 0.04, 0.02, 0.008, 0.0], 'RIG_B62_GUARDIAN.pose.bones["chest"]', "REFLECTION_AND_SETTLE"))

    emission = input_named(materials["cyan"].node_tree.nodes.get("Principled BSDF"), "Emission Strength")
    pulse = [3.0, 5.0, 8.0, 12.0, 7.0, 4.0, 3.0]
    for frame, value in zip(reflection, pulse, strict=True):
        scene.frame_set(frame)
        emission.default_value = value
        emission.keyframe_insert(data_path="default_value", frame=frame)
    signals.append({"phase": "REFLECTION_AND_SETTLE", "target": "MAT_PC4_CYAN_EMISSIVE", "dataPath": "nodes[Principled BSDF].Emission Strength", "arrayIndex": 0, "frames": reflection, "values": pulse, "peakToPeak": 9.0})
    return signals


def decode_combined(path):
    image = oiio.ImageInput.open(str(path))
    if image is None:
        raise RuntimeError("EXR_OPEN")
    try:
        candidates = []
        subimage = 0
        while image.seek_subimage(subimage, 0):
            spec = image.spec()
            names = list(spec.channelnames)
            positions = {name: index for index, name in enumerate(names)}
            for name in names:
                if not name.endswith(".R"):
                    continue
                prefix = name[:-2]
                wanted = [f"{prefix}.{channel}" for channel in "RGBA"]
                if prefix.split(".")[-1] == "Combined" and all(channel in positions for channel in wanted):
                    candidates.append((subimage, spec.width, spec.height, spec.nchannels, [positions[channel] for channel in wanted]))
            subimage += 1
        if len(candidates) != 1:
            raise RuntimeError(f"COMBINED_COUNT_{len(candidates)}")
        subimage, width, height, channels, indices = candidates[0]
        pixels = np.asarray(image.read_image(subimage, 0, 0, channels, oiio.FLOAT), dtype=np.float32).reshape(height, width, channels)
        return np.ascontiguousarray(pixels[..., indices], dtype=np.float32)
    finally:
        image.close()


def save_png(path, rgba):
    output_scene = bpy.data.scenes.new("PC4_ISOLATED_PNG_OUTPUT")
    output_scene.display_settings.display_device = "sRGB - Display"
    output_scene.view_settings.view_transform = "ACES 2.0 - SDR 100 nits (Rec.709)"
    output_scene.view_settings.look = "None"
    output_scene.render.image_settings.file_format = "PNG"
    output_scene.render.image_settings.color_mode = "RGBA"
    output_scene.render.image_settings.color_depth = "8"
    image = bpy.data.images.new("PC4_REVIEW_FRAME", width=640, height=360, alpha=True, float_buffer=True)
    try:
        image.colorspace_settings.name = "ACEScg"
        image.pixels.foreach_set(np.ascontiguousarray(np.flipud(rgba), dtype=np.float32).reshape(-1))
        image.update()
        image.save_render(filepath=str(path), scene=output_scene)
    finally:
        bpy.data.images.remove(image)
        bpy.data.scenes.remove(output_scene)


def render_review(scene, frame, camera_name, output, scratch):
    scene.frame_set(frame)
    scene.camera = bpy.data.objects[camera_name]
    scene.render.filepath = str(scratch)
    if output.exists() or scratch.exists():
        raise RuntimeError("OUTPUT_EXISTS")
    if "FINISHED" not in bpy.ops.render.render(write_still=True) or not scratch.is_file():
        raise RuntimeError("RENDER")
    rgba = decode_combined(scratch)
    if rgba.shape != (360, 640, 4) or not np.isfinite(rgba).all():
        raise RuntimeError("PIXELS")
    save_png(output, rgba)
    scratch.unlink()
    if not output.is_file() or scratch.exists():
        raise RuntimeError("OUTPUT_ADAPTER")


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    return parser.parse_args(argv)


args = parse_args()
spec = json.loads(args.spec.read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or spec["status"] != "PREREGISTERED_BEFORE_PC4_MUTATION":
    raise RuntimeError("SPEC")
scene = bpy.context.scene
source_path = Path(bpy.data.filepath)
source_before = sha256_file(source_path)
if source_before != spec["source"]["sha256"]:
    raise RuntimeError("SOURCE")
if scene.render.image_settings.file_format != "OPEN_EXR_MULTILAYER" or scene.render.image_settings.media_type != "MULTI_LAYER_IMAGE":
    raise RuntimeError("PRODUCTION_OUTPUT_CONTRACT")
scene.frame_set(1)
protected_before = camera_light_state(scene)
hide_exact(spec["legacyHeroObjectsToHide"])
hide_exact(spec["foregroundOccludersToHide"])
collection, materials = build_shell(spec)
signals = animate_performance(scene, materials)
phases = sorted({signal["phase"] for signal in signals})
targets = sorted({signal["target"] for signal in signals})
if sorted(phases) != sorted(spec["performancePhases"]):
    raise RuntimeError("PERFORMANCE_PHASES")
if len(targets) < spec["acceptance"]["minimumAnimatedTargets"]:
    raise RuntimeError("ANIMATED_TARGETS")
scene["bfs_pc4_spec_hash"] = spec["specHash"]
scene["bfs_pc4_visual_diagnosis"] = "PRIMARY_SILHOUETTE_AND_PERFORMANCE_REDESIGN"
scene["bfs_pc4_created_parts"] = len(collection.objects)
scene.frame_set(1)
protected_after = camera_light_state(scene)
if protected_before != protected_after:
    raise RuntimeError("CAMERA_LIGHT_DRIFT")
derived_path = args.work_root / "PC4_HERO_REDESIGN.blend"
bpy.context.preferences.filepaths.file_preview_type = "NONE"
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(derived_path), check_existing=False)
if sha256_file(source_path) != source_before:
    raise RuntimeError("SOURCE_DRIFT")

scratch = args.work_root / "tmp" / "pc4-review.exr"
screenshots = []
for view in spec["protectedViews"]:
    output = args.evidence_root / "derived" / f"frame-{view['frame']:04d}.png"
    render_review(scene, view["frame"], view["camera"], output, scratch)
    baseline = next(row for row in spec["visualDiagnosis"]["baselineScreenshots"] if row["frame"] == view["frame"])
    screenshots.append({"frame": view["frame"], "camera": view["camera"], "baseline": baseline, "derived": {"uri": output.as_posix(), "sha256": sha256_file(output), "bytes": output.stat().st_size}})

created = sorted(collection.objects, key=lambda obj: obj.name)
record = write_self(args.evidence_root / "build.json", {
    "schemaVersion": "bfs.pc4HeroRedesignBuild.v0.1",
    "status": "MACHINE_PASS_VISUAL_REVIEW_REQUIRED",
    "source": {"path": str(source_path), "beforeSha256": source_before, "afterSha256": sha256_file(source_path)},
    "derived": {"path": str(derived_path), "sha256": sha256_file(derived_path), "bytes": derived_path.stat().st_size},
    "createdParts": [{"name": obj.name, "system": obj["bfs_pc4_system"], "materialRegion": obj["bfs_pc4_material_region"], "polygons": len(obj.data.polygons)} for obj in created],
    "hiddenLegacyHeroObjects": spec["legacyHeroObjectsToHide"],
    "hiddenForegroundOccluders": spec["foregroundOccludersToHide"],
    "materialRegions": spec["materialRegions"],
    "performancePhases": phases,
    "animatedTargets": targets,
    "signals": signals,
    "protectedStateBefore": protected_before,
    "protectedStateAfter": protected_after,
    "screenshots": screenshots,
    "sceneCounts": {"objects": len(bpy.data.objects), "meshes": len([obj for obj in bpy.data.objects if obj.type == "MESH"]), "polygons": sum(len(obj.data.polygons) for obj in bpy.data.objects if obj.type == "MESH")},
    "operations": {"BlenderStarts": 1, "renderCalls": 3, "derivedSceneSaves": 1, "sourceSceneSaves": 0, "temporaryExrWrites": 3, "temporaryExrRetained": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0},
}, "buildHash")
print("PC4_BUILD=" + json.dumps({"status": record["status"], "buildHash": record["buildHash"], "createdParts": len(created)}, sort_keys=True), flush=True)
