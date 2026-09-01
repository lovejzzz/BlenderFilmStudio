#!/usr/bin/env python3
"""Trusted typed executor for BFS VisualImprovementPlan semantic operations."""

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


EXECUTOR_VERSION = "BFS_TYPED_VISUAL_EXECUTOR_0_1"
ALLOWED = {
    ("SET_SHOT_VISIBILITY", "HIDE_CONFIRMED_FOREGROUND_OCCLUDER"),
    ("APPLY_FRAMING_PRESET", "READABLE_SUBJECT_FRAMING"),
    ("REPLACE_FORM_WITH_ASSEMBLY", "LAYERED_MECHANICAL_JOINT"),
    ("ADD_DETAIL_SYSTEM", "FACIAL_SEGMENTATION"),
    ("ADD_DETAIL_SYSTEM", "MID_SCALE_PANEL_HIERARCHY"),
}


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


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    return parser.parse_args(argv)


def rounded(values):
    return [f"{float(value):.8f}" for value in values]


def number_string(value):
    return f"{float(value):.8f}"


def matrix_rows(matrix):
    return [rounded(row) for row in matrix]


def protected_state(scene, frames):
    cameras = sorted((obj for obj in bpy.data.objects if obj.type == "CAMERA"), key=lambda obj: obj.name)
    lights = sorted((obj for obj in bpy.data.objects if obj.type == "LIGHT"), key=lambda obj: obj.name)
    rows = []
    for frame in frames:
        scene.frame_set(frame)
        rows.append({
            "frame": frame,
            "cameras": {obj.name: {"matrixWorld": matrix_rows(obj.matrix_world), "lens": number_string(obj.data.lens)} for obj in cameras},
            "lights": {obj.name: {"matrixWorld": matrix_rows(obj.matrix_world), "energy": number_string(obj.data.energy), "color": rounded(obj.data.color)} for obj in lights},
        })
    return rows


def transform_projection(state, key):
    if key == "cameras":
        return [{"frame": row["frame"], "cameras": {name: value["matrixWorld"] for name, value in row["cameras"].items()}} for row in state]
    return [{"frame": row["frame"], "lights": row["lights"]} for row in state]


def input_named(node, *names):
    for name in names:
        if name in node.inputs:
            return node.inputs[name]
    raise RuntimeError("MISSING_SHADER_INPUT")


def make_material(name, color, metallic, roughness, emission=None):
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    input_named(shader, "Base Color").default_value = (*color, 1.0)
    input_named(shader, "Metallic").default_value = metallic
    input_named(shader, "Roughness").default_value = roughness
    if emission:
        input_named(shader, "Emission Color", "Emission").default_value = (*emission, 1.0)
        input_named(shader, "Emission Strength").default_value = 4.0
    material["bfs_typed_executor_material"] = EXECUTOR_VERSION
    return material


def move_to_collection(obj, collection):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def parent_preserve_world(obj, anchor):
    world = obj.matrix_world.copy()
    obj.parent = anchor
    obj.matrix_parent_inverse = anchor.matrix_world.inverted_safe()
    obj.matrix_world = world


def apply_bevel(obj, width):
    modifier = obj.modifiers.new("BFS_TYPED_BAKED_BEVEL", "BEVEL")
    modifier.width = max(0.002, float(width))
    modifier.segments = 3
    modifier.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def basis_matrix(right, toward, up, center):
    return Matrix((
        (right.x, toward.x, up.x, center.x),
        (right.y, toward.y, up.y, center.y),
        (right.z, toward.z, up.z, center.z),
        (0.0, 0.0, 0.0, 1.0),
    ))


def camera_basis(camera, center):
    toward = (camera.matrix_world.translation - center).normalized()
    up = camera.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))
    up = (up - toward * up.dot(toward)).normalized()
    right = toward.cross(up).normalized()
    return right, toward, up


def bbox_geometry(obj, camera):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    center = sum(corners, Vector()) / len(corners)
    right, toward, up = camera_basis(camera, center)
    extents = {
        "right": max(abs((corner - center).dot(right)) for corner in corners),
        "toward": max(abs((corner - center).dot(toward)) for corner in corners),
        "up": max(abs((corner - center).dot(up)) for corner in corners),
    }
    return center, right, toward, up, extents


def rotate_face_basis(right, toward, up, angle_degrees):
    angle = math.radians(angle_degrees)
    rotated_right = (right * math.cos(angle) + up * math.sin(angle)).normalized()
    rotated_up = (-right * math.sin(angle) + up * math.cos(angle)).normalized()
    return rotated_right, toward, rotated_up


def new_box(collection, name, anchor, center, right, toward, up, dimensions, material, operation, semantic, bevel_scale=0.12):
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(max(0.004, float(value) / 2.0) for value in dimensions)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_bevel(obj, min(dimensions) * bevel_scale)
    obj.matrix_world = basis_matrix(right, toward, up, center)
    move_to_collection(obj, collection)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj["bfs_typed_operation_id"] = operation["operationId"]
    obj["bfs_typed_semantic"] = semantic
    obj["bfs_typed_executor_version"] = EXECUTOR_VERSION
    parent_preserve_world(obj, anchor)
    return obj


def shot_map(context):
    return {shot["shotId"]: shot for shot in context["shots"]}


def frame_map(packet):
    return {frame["frameId"]: frame for frame in packet["frames"]}


def operation_camera(operation, shots):
    if len(operation["shotIds"]) != 1:
        raise RuntimeError("OPERATION_REQUIRES_ONE_SHOT")
    shot = shots.get(operation["shotIds"][0])
    if not shot or shot["cameraId"] not in bpy.data.objects or bpy.data.objects[shot["cameraId"]].type != "CAMERA":
        raise RuntimeError("MISSING_SHOT_CAMERA")
    return shot, bpy.data.objects[shot["cameraId"]]


def ensure_targets(operation):
    missing = [name for name in operation["targetEntityIds"] if name not in bpy.data.objects]
    if missing:
        raise RuntimeError("MISSING_PLAN_TARGET_" + ",".join(missing))
    return [bpy.data.objects[name] for name in operation["targetEntityIds"]]


def apply_visibility(scene, operation, shots):
    if operation["parameters"]["visible"] is not False:
        raise RuntimeError("VISIBILITY_PARAMETER")
    shot, _camera = operation_camera(operation, shots)
    effects = []
    for obj in ensure_targets(operation):
        scene.frame_set(max(scene.frame_start, shot["frameStart"] - 1))
        prior = bool(obj.hide_render)
        if shot["frameStart"] > scene.frame_start:
            obj.hide_render = prior
            obj.keyframe_insert(data_path="hide_render", frame=shot["frameStart"] - 1)
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_render", frame=shot["frameStart"])
        obj.keyframe_insert(data_path="hide_render", frame=shot["frameEnd"])
        if shot["frameEnd"] < scene.frame_end:
            obj.hide_render = prior
            obj.keyframe_insert(data_path="hide_render", frame=shot["frameEnd"] + 1)
        action = obj.animation_data.action if obj.animation_data else None
        if action:
            for layer in action.layers:
                for strip in layer.strips:
                    for channelbag in strip.channelbags:
                        for curve in channelbag.fcurves:
                            if curve.data_path == "hide_render":
                                for point in curve.keyframe_points:
                                    point.interpolation = "CONSTANT"
        scene.frame_set(shot["reviewFrame"])
        if not obj.hide_render:
            raise RuntimeError("VISIBILITY_REVIEW_FRAME")
        effects.append({"target": obj.name, "prior": prior, "shot": shot["shotId"], "frameStart": shot["frameStart"], "frameEnd": shot["frameEnd"]})
    return effects


def apply_framing(operation, shots):
    shot, camera = operation_camera(operation, shots)
    ensure_targets(operation)
    maximum = float(operation["parameters"]["maximumLensChangePercent"])
    requested = 12.0
    if requested > maximum:
        raise RuntimeError("FRAMING_LIMIT")
    old_lens = float(camera.data.lens)
    new_lens = old_lens * (1.0 - requested / 100.0)
    camera.data.lens = new_lens
    return [{"camera": camera.name, "shot": shot["shotId"], "oldLens": number_string(old_lens), "newLens": number_string(new_lens), "absoluteChangePercent": int(requested)}]


def apply_joint(scene, operation, shots, collection, materials, created):
    shot, camera = operation_camera(operation, shots)
    scene.frame_set(shot["reviewFrame"])
    minimum_layers = int(operation["parameters"]["minimumLayers"])
    targets = ensure_targets(operation)
    primaries = [obj for obj in targets if obj.type == "MESH" and len(obj.data.polygons) >= 400]
    if len(primaries) < 4:
        raise RuntimeError("JOINT_PRIMARY_FLOOR")
    effects = []
    for primary_index, obj in enumerate(sorted(primaries, key=lambda item: item.name)):
        center, right, toward, up, ext = bbox_geometry(obj, camera)
        old_scale = tuple(float(value) for value in obj.scale)
        obj.scale = tuple(value * 0.62 for value in obj.scale)
        if obj.data.materials:
            obj.data.materials[0] = materials["core"]
        layers = [
            ("ARMOR", center + toward * (ext["toward"] * 0.84) + up * (ext["up"] * 0.10), (ext["right"] * 1.62, ext["toward"] * 0.34, ext["up"] * 1.08), materials["armor"]),
            ("UPPER", center + toward * (ext["toward"] * 0.76) + up * (ext["up"] * 0.62), (ext["right"] * 1.18, ext["toward"] * 0.28, ext["up"] * 0.34), materials["edge"]),
            ("COUPLER", center + toward * (ext["toward"] * 0.80) - up * (ext["up"] * 0.58), (ext["right"] * 0.86, ext["toward"] * 0.30, ext["up"] * 0.28), materials["accent"]),
        ]
        if len(layers) < minimum_layers:
            raise RuntimeError("JOINT_LAYER_FLOOR")
        names = []
        for layer_index, (label, layer_center, dimensions, material) in enumerate(layers):
            part = new_box(collection, f"VX_{operation['operationId']}_{primary_index:02d}_{layer_index:02d}_{label}", obj, layer_center, right, toward, up, dimensions, material, operation, "LAYERED_MECHANICAL_JOINT")
            created.append(part)
            names.append(part.name)
        effects.append({"primary": obj.name, "polygons": len(obj.data.polygons), "oldScale": rounded(old_scale), "newScale": rounded(obj.scale), "layers": names})
    return effects


def apply_face(scene, operation, shots, collection, materials, created):
    shot, camera = operation_camera(operation, shots)
    scene.frame_set(shot["reviewFrame"])
    targets = [obj for obj in ensure_targets(operation) if obj.type == "MESH"]
    candidates = []
    for obj in targets:
        center, right, toward, up, ext = bbox_geometry(obj, camera)
        candidates.append((ext["right"] * ext["toward"] * ext["up"], obj, center, right, toward, up, ext))
    if not candidates:
        raise RuntimeError("FACE_ANCHOR")
    _volume, anchor, center, right, toward, up, ext = max(candidates, key=lambda item: item[0])
    front = center + toward * (ext["toward"] * 1.03)
    thickness = max(0.014, ext["toward"] * 0.12)
    pieces = [
        ("BROW_L", -0.30, 0.30, 0.34, 0.11, -8.0, materials["edge"]),
        ("BROW_R", 0.30, 0.30, 0.34, 0.11, 8.0, materials["edge"]),
        ("CHEEK_L", -0.34, -0.04, 0.25, 0.28, 12.0, materials["armor"]),
        ("CHEEK_R", 0.34, -0.04, 0.25, 0.28, -12.0, materials["armor"]),
        ("JAW", 0.0, -0.42, 0.56, 0.14, 0.0, materials["edge"]),
        ("CREST", 0.0, 0.58, 0.15, 0.25, 0.0, materials["accent"]),
        ("VISOR_BRIDGE", 0.0, 0.08, 0.72, 0.075, 0.0, materials["accent"]),
    ]
    minimum = int(operation["parameters"]["minimumLayers"])
    if len(pieces) < max(7, minimum):
        raise RuntimeError("FACE_LAYER_FLOOR")
    names = []
    for index, (label, x_factor, z_factor, width_factor, height_factor, angle, material) in enumerate(pieces):
        local_right, local_toward, local_up = rotate_face_basis(right, toward, up, angle)
        part_center = front + right * (ext["right"] * x_factor) + up * (ext["up"] * z_factor)
        dimensions = (ext["right"] * width_factor * 2.0, thickness, ext["up"] * height_factor * 2.0)
        part = new_box(collection, f"VX_{operation['operationId']}_{index:02d}_{label}", anchor, part_center, local_right, local_toward, local_up, dimensions, material, operation, "FACIAL_SEGMENTATION", 0.16)
        created.append(part)
        names.append(part.name)
    return [{"anchor": anchor.name, "camera": camera.name, "parts": names}]


def apply_surface(scene, operation, shots, collection, materials, created):
    frames = frame_map(PACKET)
    evidence = [frames[frame_id] for frame_id in operation["evidenceFrameIds"]]
    targets = [obj for obj in ensure_targets(operation) if obj.type == "MESH"]
    minimum = int(operation["parameters"]["minimumLayers"])
    effects = []
    for target_index, obj in enumerate(sorted(targets, key=lambda item: item.name)):
        matching = next((frame for frame in evidence if obj.name in frame["visibleEntityIds"]), evidence[0])
        camera = bpy.data.objects[matching["cameraId"]]
        scene.frame_set(matching["frame"])
        center, right, toward, up, ext = bbox_geometry(obj, camera)
        front = center + toward * (ext["toward"] * 1.04)
        thickness = max(0.008, ext["toward"] * 0.08)
        panels = [
            ("CENTER", 0.0, 0.18, 0.48, 0.13, materials["armor"]),
            ("LOW_L", -0.30, -0.26, 0.25, 0.18, materials["edge"]),
            ("LOW_R", 0.30, -0.26, 0.25, 0.18, materials["accent"]),
        ]
        if len(panels) < minimum:
            raise RuntimeError("SURFACE_LAYER_FLOOR")
        names = []
        for panel_index, (label, x_factor, z_factor, width_factor, height_factor, material) in enumerate(panels):
            panel_center = front + right * (ext["right"] * x_factor) + up * (ext["up"] * z_factor)
            dimensions = (ext["right"] * width_factor * 2.0, thickness, ext["up"] * height_factor * 2.0)
            part = new_box(collection, f"VX_{operation['operationId']}_{target_index:02d}_{panel_index:02d}_{label}", obj, panel_center, right, toward, up, dimensions, material, operation, "MID_SCALE_PANEL_HIERARCHY", 0.14)
            created.append(part)
            names.append(part.name)
        effects.append({"target": obj.name, "camera": camera.name, "parts": names})
    return effects


def render_reviews(scene, context, evidence_root):
    outputs = []
    scene.render.resolution_x = int(context["render"]["width"])
    scene.render.resolution_y = int(context["render"]["height"])
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.use_file_extension = True
    for shot in context["shots"]:
        scene.frame_set(shot["reviewFrame"])
        scene.camera = bpy.data.objects[shot["cameraId"]]
        output = evidence_root / "review" / f"frame-{shot['reviewFrame']:04d}.png"
        if output.exists():
            raise RuntimeError("REVIEW_OUTPUT_EXISTS")
        scene.render.filepath = str(output)
        result = bpy.ops.render.render(write_still=True)
        if "FINISHED" not in result or not output.is_file():
            raise RuntimeError("REVIEW_RENDER")
        outputs.append({"frame": shot["reviewFrame"], "shotId": shot["shotId"], "camera": shot["cameraId"], "uri": str(output), "sha256": sha256_file(output), "bytes": output.stat().st_size})
    return outputs


args = parse_args()
context = json.loads(args.context.read_text(encoding="utf-8"))
if not valid_self(context, "contextHash") or context["schemaVersion"] != "bfs.visualImprovementExecutionContextC1.v0.2" or context["experimentId"] != "PC4-VX1":
    raise RuntimeError("CONTEXT")
plan_path = Path(context["plan"]["uri"])
packet_path = Path(context["packet"]["uri"])
if sha256_file(plan_path) != context["plan"]["sha256"] or sha256_file(packet_path) != context["packet"]["sha256"]:
    raise RuntimeError("PLAN_PACKET_IDENTITY")
plan = json.loads(plan_path.read_text(encoding="utf-8"))
PACKET = json.loads(packet_path.read_text(encoding="utf-8"))
if plan["planHash"] != context["plan"]["planHash"] or plan["decision"] != "COMPILED" or len(plan["operations"]) != 6:
    raise RuntimeError("PLAN")
if any((operation["operationType"], operation["preset"]) not in ALLOWED for operation in plan["operations"]):
    raise RuntimeError("UNKNOWN_TYPED_ADAPTER")

scene = bpy.context.scene
source_path = Path(bpy.data.filepath)
source_before = sha256_file(source_path)
if str(source_path) != context["source"]["path"] or source_before != context["source"]["sha256"]:
    raise RuntimeError("SOURCE")
if args.evidence_root.exists() or args.work_root.exists():
    raise RuntimeError("ROOT_ALREADY_EXISTS")
args.evidence_root.mkdir(parents=True)
(args.evidence_root / "review").mkdir()
args.work_root.mkdir(parents=True)

review_frames = context["render"]["reviewFrames"]
protected_before = protected_state(scene, review_frames)
collection = bpy.data.collections.new("BFS_TYPED_VISUAL_IMPROVEMENT")
scene.collection.children.link(collection)
materials = {
    "armor": make_material("MAT_BFS_VX_ARMOR", (0.035, 0.075, 0.11), 0.82, 0.20),
    "core": make_material("MAT_BFS_VX_CORE", (0.006, 0.010, 0.016), 0.58, 0.30),
    "edge": make_material("MAT_BFS_VX_EDGE", (0.13, 0.22, 0.27), 0.90, 0.15),
    "accent": make_material("MAT_BFS_VX_ACCENT", (0.0, 0.18, 0.28), 0.46, 0.18, (0.02, 0.75, 1.0)),
}
shots = shot_map(context)
created = []
effects = []
for operation in plan["operations"]:
    pair = (operation["operationType"], operation["preset"])
    if pair == ("SET_SHOT_VISIBILITY", "HIDE_CONFIRMED_FOREGROUND_OCCLUDER"):
        rows = apply_visibility(scene, operation, shots)
    elif pair == ("APPLY_FRAMING_PRESET", "READABLE_SUBJECT_FRAMING"):
        rows = apply_framing(operation, shots)
    elif pair == ("REPLACE_FORM_WITH_ASSEMBLY", "LAYERED_MECHANICAL_JOINT"):
        rows = apply_joint(scene, operation, shots, collection, materials, created)
    elif pair == ("ADD_DETAIL_SYSTEM", "FACIAL_SEGMENTATION"):
        rows = apply_face(scene, operation, shots, collection, materials, created)
    elif pair == ("ADD_DETAIL_SYSTEM", "MID_SCALE_PANEL_HIERARCHY"):
        rows = apply_surface(scene, operation, shots, collection, materials, created)
    else:
        raise RuntimeError("UNREACHABLE_TYPED_ADAPTER")
    effects.append({"operationId": operation["operationId"], "operationType": operation["operationType"], "preset": operation["preset"], "effects": rows})

if len(created) < 28:
    raise RuntimeError("CREATED_PART_FLOOR")
protected_after = protected_state(scene, review_frames)
if transform_projection(protected_before, "cameras") != transform_projection(protected_after, "cameras"):
    raise RuntimeError("CAMERA_TRANSFORM_DRIFT")
if transform_projection(protected_before, "lights") != transform_projection(protected_after, "lights"):
    raise RuntimeError("LIGHT_DRIFT")

scene["bfs_visual_plan_hash"] = plan["planHash"]
scene["bfs_typed_executor_version"] = EXECUTOR_VERSION
scene["bfs_typed_operation_count"] = len(plan["operations"])
scene["bfs_typed_created_part_count"] = len(created)
derived_path = args.work_root / "PC4_TYPED_VISUAL_IMPROVEMENT.blend"
bpy.context.preferences.filepaths.file_preview_type = "NONE"
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(derived_path), check_existing=False)
if sha256_file(source_path) != source_before:
    raise RuntimeError("SOURCE_DRIFT")
screenshots = render_reviews(scene, context, args.evidence_root)

record = write_self(args.evidence_root / "build.json", {
    "schemaVersion": "bfs.visualPlanTypedExecutionBuild.v0.1",
    "experimentId": "PC4-VX1",
    "status": "MACHINE_PASS_VISUAL_REVIEW_REQUIRED",
    "executorVersion": EXECUTOR_VERSION,
    "context": {"path": str(args.context), "sha256": sha256_file(args.context), "contextHash": context["contextHash"]},
    "plan": context["plan"],
    "source": {"path": str(source_path), "beforeSha256": source_before, "afterSha256": sha256_file(source_path)},
    "derived": {"path": str(derived_path), "sha256": sha256_file(derived_path), "bytes": derived_path.stat().st_size},
    "operationsConsumed": len(effects),
    "effects": effects,
    "createdParts": [{"name": obj.name, "semantic": obj["bfs_typed_semantic"], "operationId": obj["bfs_typed_operation_id"], "polygons": len(obj.data.polygons)} for obj in sorted(created, key=lambda item: item.name)],
    "protectedStateBefore": protected_before,
    "protectedStateAfter": protected_after,
    "screenshots": screenshots,
    "sceneCounts": {"objects": len(bpy.data.objects), "meshes": len([obj for obj in bpy.data.objects if obj.type == "MESH"]), "polygons": sum(len(obj.data.polygons) for obj in bpy.data.objects if obj.type == "MESH")},
    "operations": {"BlenderStarts": 1, "renderCalls": 3, "derivedSceneSaves": 1, "sourceSceneSaves": 0, "reviewPngWrites": 3, "retainedExr": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0},
}, "buildHash")
print("BFS_TYPED_VISUAL_EXECUTION=" + json.dumps({"status": record["status"], "buildHash": record["buildHash"], "createdParts": len(created)}, sort_keys=True), flush=True)
