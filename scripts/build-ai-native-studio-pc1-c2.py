#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build the frozen PC.1 modeling-detail derivative and A/B stills."""

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


SENTINELS = (1, 48, 96, 97, 144, 192, 193, 240, 288)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


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
    return [round(float(value), 9) for value in values]


def scene_state(scene):
    cameras = sorted((obj for obj in bpy.data.objects if obj.type == "CAMERA"), key=lambda item: item.name)
    lights = sorted((obj for obj in bpy.data.objects if obj.type == "LIGHT"), key=lambda item: item.name)
    result = []
    for frame in SENTINELS:
        scene.frame_set(frame)
        result.append({
            "frame": frame,
            "cameras": {obj.name: {"matrixWorld": [rounded(row) for row in obj.matrix_world], "lens": round(float(obj.data.lens), 9)} for obj in cameras},
            "lights": {obj.name: {"matrixWorld": [rounded(row) for row in obj.matrix_world], "energy": round(float(obj.data.energy), 9), "color": rounded(obj.data.color)} for obj in lights},
        })
    return result


def action_state():
    rows = []
    for action in sorted(bpy.data.actions, key=lambda item: item.name):
        fcurves = []
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    fcurves.extend(channelbag.fcurves)
        rows.append({"name": action.name, "fcurves": len(fcurves), "keyframes": sum(len(curve.keyframe_points) for curve in fcurves)})
    return rows


def principled(material):
    return material.node_tree.nodes.get("Principled BSDF")


def input_named(node, *names):
    for name in names:
        if name in node.inputs:
            return node.inputs[name]
    raise RuntimeError(f"missing input {names}")


def detail_material(name, base, metallic, roughness, emission=None):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = principled(material)
    input_named(shader, "Base Color").default_value = (*base, 1.0)
    input_named(shader, "Metallic").default_value = metallic
    input_named(shader, "Roughness").default_value = roughness
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 18.0
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.65
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.04
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    if emission:
        input_named(shader, "Emission Color", "Emission").default_value = (*emission, 1.0)
        input_named(shader, "Emission Strength").default_value = 5.0
    material["bfs_pc1_material_region"] = name
    return material


def finish(obj, collection, material, detail_id, category):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["bfs_pc1_detail_id"] = detail_id
    obj["bfs_pc1_category"] = category
    obj["bfs_pc1_material_region"] = material.name
    return obj


def inherit_parent(obj, anchor):
    world = obj.matrix_world.copy()
    if anchor.parent and anchor.parent_type == "BONE":
        obj.parent = anchor.parent
        obj.parent_type = "BONE"
        obj.parent_bone = anchor.parent_bone
    else:
        obj.parent = anchor
    obj.matrix_world = world


def box(collection, detail_id, anchor_name, offset, scale, material, category, rotation=(0.0, 0.0, 0.0)):
    anchor = bpy.data.objects[anchor_name]
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    obj.name = detail_id
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("PC1_BAKED_BEVEL", "BEVEL")
    bevel.width = min(scale) * 0.28
    bevel.segments = 3
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    obj.matrix_world = anchor.matrix_world @ Matrix.Translation(offset) @ Euler(rotation, "XYZ").to_matrix().to_4x4()
    finish(obj, collection, material, detail_id, category)
    inherit_parent(obj, anchor)
    return obj


def torus(collection, detail_id, anchor_name, major, minor, material, category, rotation):
    anchor = bpy.data.objects[anchor_name]
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=48, minor_segments=10)
    obj = bpy.context.object
    obj.name = detail_id
    obj.matrix_world = anchor.matrix_world @ Euler(rotation, "XYZ").to_matrix().to_4x4()
    finish(obj, collection, material, detail_id, category)
    inherit_parent(obj, anchor)
    return obj


def add_details(spec):
    collection = bpy.data.collections.new("PC1_MODELING_DETAILS")
    bpy.context.scene.collection.children.link(collection)
    edge = detail_material("MAT_PC1_ARMOR_EDGE", (0.12, 0.16, 0.20), 0.82, 0.22)
    warning = detail_material("MAT_PC1_WARNING_INLAY", (0.30, 0.035, 0.008), 0.38, 0.28, (1.0, 0.055, 0.006))
    core = detail_material("MAT_PC1_CORE_INLAY", (0.015, 0.20, 0.28), 0.42, 0.18, (0.02, 0.75, 1.0))
    box(collection, "PC1_GUARDIAN_TORSO_SPINE", "B62_TORSO", (0, -0.235, 0.01), (0.055, 0.025, 0.245), edge, "guardian-surface")
    for side, sign in (("L", 1), ("R", -1)):
        box(collection, f"PC1_GUARDIAN_CLAVICLE_{side}", "B62_TORSO", (0.20 * sign, -0.235, 0.17), (0.13, 0.022, 0.035), edge, "guardian-silhouette", rotation=(0, 0, math.radians(-12 * sign)))
        box(collection, f"PC1_GUARDIAN_SHOULDER_FIN_{side}", f"B62_SHOULDER_{side}", (0.13 * sign, 0.0, 0.08), (0.055, 0.17, 0.055), edge, "guardian-silhouette", rotation=(0, math.radians(18 * sign), 0))
        box(collection, f"PC1_GUARDIAN_FOREARM_RAIL_{side}", f"B62_FOREARM_{side}", (0, -0.09, 0), (0.035, 0.025, 0.12), warning, "guardian-surface")
        box(collection, f"PC1_GUARDIAN_SHIN_PLATE_{side}", f"B62_SHIN_{side}", (0, -0.10, 0), (0.075, 0.022, 0.145), edge, "guardian-surface")
        box(collection, f"PC1_GUARDIAN_HEEL_SPUR_{side}", f"B62_FOOT_{side}", (0, 0.21, -0.005), (0.07, 0.105, 0.045), edge, "guardian-silhouette")
        box(collection, f"PC1_GUARDIAN_HELMET_TEMPLE_{side}", "B62_HELMET", (0.245 * sign, -0.035, 0.0), (0.035, 0.11, 0.12), edge, "guardian-silhouette")
        box(collection, f"PC1_GUARDIAN_CHEEK_VENT_{side}", "B62_HELMET", (0.145 * sign, -0.225, -0.075), (0.055, 0.018, 0.045), warning, "guardian-surface")
    box(collection, "PC1_GUARDIAN_VISOR_BROW", "B62_VISOR", (0, -0.04, 0.075), (0.225, 0.022, 0.025), edge, "guardian-silhouette")
    box(collection, "PC1_GUARDIAN_CHEST_INLAY", "B62_CHEST_PLATE", (0, -0.06, 0), (0.15, 0.018, 0.105), warning, "guardian-surface")
    for side, sign in (("L", 1), ("R", -1)):
        box(collection, f"PC1_CONSOLE_RAIL_{side}", "B62_CONSOLE_SURFACE", (0.53 * sign, 0, 0.075), (0.035, 0.16, 0.035), edge, "console-silhouette")
        box(collection, f"PC1_CONSOLE_KEYBANK_{side}", "B62_CONSOLE_SURFACE", (0.25 * sign, -0.03, 0.08), (0.15, 0.07, 0.025), warning, "console-surface")
    box(collection, "PC1_CONSOLE_GLYPH_STRIP", "B62_CONSOLE_SURFACE", (0, -0.10, 0.085), (0.18, 0.035, 0.018), core, "console-surface")
    for index, angle in enumerate((0, 45, 90, 135)):
        torus(collection, f"PC1_CORE_GIMBAL_{index:02d}", "B62_CORE", 0.57 + index * 0.035, 0.018, core if index % 2 == 0 else edge, "core-silhouette", (math.radians(90), math.radians(angle), 0))
    roster = sorted(obj.name for obj in collection.objects)
    if roster != sorted(spec["semanticDetailComponents"]):
        raise RuntimeError("DETAIL_ROSTER")
    return collection


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
        pixels = np.asarray(image.read_image(subimage, 0, 0, channels, oiio.FLOAT), dtype=np.float32)
        pixels = pixels.reshape(height, width, channels)
        return np.ascontiguousarray(pixels[..., indices], dtype=np.float32)
    finally:
        image.close()


def render_frame(scene, frame, camera_name, path, scratch):
    scene.frame_set(frame)
    scene.camera = bpy.data.objects[camera_name]
    if scratch.exists() or path.exists():
        raise RuntimeError("OUTPUT_EXISTS")
    scene.render.filepath = str(scratch)
    result = bpy.ops.render.render(write_still=True)
    if "FINISHED" not in result or not scratch.is_file():
        raise RuntimeError("RENDER")
    rgba = decode_combined(scratch)
    if rgba.shape != (360, 640, 4) or not np.isfinite(rgba).all():
        raise RuntimeError("COMBINED_SHAPE")
    output_scene = bpy.data.scenes.new("PC1_ISOLATED_PNG_OUTPUT")
    output_scene.display_settings.display_device = "sRGB - Display"
    output_scene.view_settings.view_transform = "ACES 2.0 - SDR 100 nits (Rec.709)"
    output_scene.view_settings.look = "None"
    output_scene.render.image_settings.file_format = "PNG"
    output_scene.render.image_settings.color_mode = "RGBA"
    output_scene.render.image_settings.color_depth = "8"
    image = bpy.data.images.new("PC1_GENERATED_REVIEW", width=640, height=360, alpha=True, float_buffer=True)
    try:
        image.colorspace_settings.name = "ACEScg"
        image.pixels.foreach_set(np.ascontiguousarray(np.flipud(rgba), dtype=np.float32).reshape(-1))
        image.update()
        image.save_render(filepath=str(path), scene=output_scene)
    finally:
        bpy.data.images.remove(image)
        bpy.data.scenes.remove(output_scene)
        scratch.unlink()
    if not path.is_file() or scratch.exists():
        raise RuntimeError("PNG_ADAPTER")


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    return parser.parse_args(argv)


args = parse_args()
spec = json.loads(args.spec.read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or spec["status"] != "PREREGISTERED_CORRECTION_BEFORE_PC1_SCENE_MUTATION":
    raise RuntimeError("SPEC")
scene = bpy.context.scene
source_path = Path(bpy.data.filepath)
source_before = sha256_file(source_path)
if source_before != spec["baseline"]["source"]["sha256"]:
    raise RuntimeError("SOURCE")
before_state = scene_state(scene)
before_actions = action_state()
scene.render.engine = spec["renderProfile"]["engine"]
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = spec["renderProfile"]["resolution"]
if scene.render.image_settings.file_format != "OPEN_EXR_MULTILAYER" or scene.render.image_settings.media_type != "MULTI_LAYER_IMAGE":
    raise RuntimeError("PRODUCTION_OUTPUT_CONTRACT")
scene.render.film_transparent = False
scene.render.resolution_percentage = 100
scene.eevee.taa_samples = spec["renderProfile"]["samples"]
scene.eevee.taa_render_samples = spec["renderProfile"]["samples"]
scratch = args.work_root / "tmp" / "pc1-current-frame.exr"
for view in spec["protectedViews"]:
    render_frame(scene, view["frame"], view["camera"], args.evidence_root / "baseline" / f"frame-{view['frame']:04d}.png", scratch)
scene.frame_set(1)
details = add_details(spec)
derived_path = args.work_root / "PC1_MODELING_DETAIL.blend"
bpy.context.preferences.filepaths.file_preview_type = "NONE"
bpy.ops.wm.save_as_mainfile(filepath=str(derived_path), check_existing=False)
for view in spec["protectedViews"]:
    render_frame(scene, view["frame"], view["camera"], args.evidence_root / "derived" / f"frame-{view['frame']:04d}.png", scratch)
after_state = scene_state(scene)
after_actions = action_state()
if before_state != after_state or before_actions != after_actions:
    raise RuntimeError("PROTECTED_STATE_DRIFT")
source_after = sha256_file(source_path)
if source_after != source_before:
    raise RuntimeError("SOURCE_DRIFT")
detail_objects = sorted(details.objects, key=lambda item: item.name)
record = write_self(args.evidence_root / "build.json", {
    "schemaVersion": "bfs.pc1ModelingBuild.v0.1",
    "status": "PASS",
    "source": {"path": str(source_path), "beforeSha256": source_before, "afterSha256": source_after},
    "derived": {"path": str(derived_path), "sha256": sha256_file(derived_path), "bytes": derived_path.stat().st_size},
    "details": [{"id": obj.name, "category": obj["bfs_pc1_category"], "materialRegion": obj["bfs_pc1_material_region"], "polygons": len(obj.data.polygons)} for obj in detail_objects],
    "materialRegions": [{"name": name, "nodeCount": len(bpy.data.materials[name].node_tree.nodes)} for name in spec["materialRegions"]],
    "baselineCounts": spec["baseline"]["counts"],
    "derivedCounts": {"objects": len(bpy.data.objects), "meshes": len([obj for obj in bpy.data.objects if obj.type == "MESH"]), "polygons": sum(len(obj.data.polygons) for obj in bpy.data.objects if obj.type == "MESH")},
    "protectedStateBefore": before_state,
    "protectedStateAfter": after_state,
    "actionsBefore": before_actions,
    "actionsAfter": after_actions,
    "outputAdapter": {"productionFormat": "OPEN_EXR_MULTILAYER", "finalFormat": "PNG", "temporaryExrWrites": 6, "temporaryExrFilesRetained": 0, "oiioVersion": oiio.VERSION_STRING, "numpyVersion": np.__version__},
    "operations": {"BlenderStarts": 1, "renderCalls": 6, "derivedSceneSaves": 1, "sourceSceneSaves": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0},
}, "buildHash")
print("PC1_BUILD=" + json.dumps({"status": record["status"], "buildHash": record["buildHash"]}, sort_keys=True), flush=True)
