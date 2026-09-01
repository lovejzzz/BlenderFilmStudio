#!/usr/bin/env python3
"""Trusted relation-constrained executor for BFS VisualImprovementPlan v0.2."""

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
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector


VERSION = "BFS_FILM_LANGUAGE_EXECUTOR_0_2"
ALLOWED = {
    ("RESOLVE_SCREENSPACE_OCCLUSION", "HIDE_NEAREST_NONSTORY_OCCLUDER"),
    ("APPLY_FRAMING_CONSTRAINT", "FIT_BOUND_SUBJECT_WITH_MARGIN"),
    ("REPLACE_FORM_WITH_CONTOUR_ASSEMBLY", "CONCENTRIC_CORE_SHELL_GAP"),
    ("ADD_CONTOUR_DETAIL_SYSTEM", "LANDMARK_DRIVEN_FACEPLATE"),
    ("ADD_CONTOUR_DETAIL_SYSTEM", "SPARSE_HIERARCHICAL_PANELING"),
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


def args_value():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    return parser.parse_args(argv)


def rounded(values):
    return [f"{float(value):.8f}" for value in values]


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
            "cameras": {obj.name: {"matrixWorld": matrix_rows(obj.matrix_world), "lens": f"{float(obj.data.lens):.8f}", "shift": rounded((obj.data.shift_x, obj.data.shift_y))} for obj in cameras},
            "lights": {obj.name: {"matrixWorld": matrix_rows(obj.matrix_world), "energy": f"{float(obj.data.energy):.8f}", "color": rounded(obj.data.color)} for obj in lights},
        })
    return rows


def input_named(node, *names):
    for name in names:
        if name in node.inputs:
            return node.inputs[name]
    raise RuntimeError("MISSING_SHADER_INPUT")


def make_material(name, color, metallic, roughness, emission=None):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    input_named(shader, "Base Color").default_value = (*color, 1.0)
    input_named(shader, "Metallic").default_value = metallic
    input_named(shader, "Roughness").default_value = roughness
    if emission:
        input_named(shader, "Emission Color", "Emission").default_value = (*emission, 1.0)
        input_named(shader, "Emission Strength").default_value = 3.0
    material["bfs_film_language_version"] = VERSION
    return material


def move_to_collection(obj, collection):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def parent_world(obj, anchor):
    world = obj.matrix_world.copy()
    obj.parent = anchor
    obj.matrix_parent_inverse = anchor.matrix_world.inverted_safe()
    obj.matrix_world = world


def bevel(obj, width):
    modifier = obj.modifiers.new("BFS_FILM_LANGUAGE_BEVEL", "BEVEL")
    modifier.width = max(0.001, float(width))
    modifier.segments = 3
    modifier.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def face_basis(right, toward, up, center):
    return Matrix(((right.x, toward.x, up.x, center.x), (right.y, toward.y, up.y, center.y), (right.z, toward.z, up.z, center.z), (0.0, 0.0, 0.0, 1.0)))


def axial_basis(right, up, toward, center):
    return Matrix(((right.x, up.x, toward.x, center.x), (right.y, up.y, toward.y, center.y), (right.z, up.z, toward.z, center.z), (0.0, 0.0, 0.0, 1.0)))


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
    ext = {axis: max(abs((corner - center).dot(vector)) for corner in corners) for axis, vector in (("right", right), ("toward", toward), ("up", up))}
    return center, right, toward, up, ext


def tag(obj, operation, semantic, zone=None, scale_band=None, relief_ratio=None, coverage_ratio=None):
    obj["bfs_film_language_operation"] = operation["operationId"]
    obj["bfs_film_language_semantic"] = semantic
    obj["bfs_film_language_version"] = VERSION
    if zone is not None:
        obj["bfs_film_language_face_zone"] = zone
    if scale_band is not None:
        obj["bfs_film_language_scale_band"] = int(scale_band)
    if relief_ratio is not None:
        obj["bfs_film_language_relief_ratio"] = float(relief_ratio)
    if coverage_ratio is not None:
        obj["bfs_film_language_coverage_ratio"] = float(coverage_ratio)


def new_box(collection, name, anchor, center, right, toward, up, dimensions, material, operation, semantic, **metadata):
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(max(0.002, value / 2.0) for value in dimensions)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(obj, min(dimensions) * 0.18)
    obj.matrix_world = face_basis(right, toward, up, center)
    move_to_collection(obj, collection)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    tag(obj, operation, semantic, **metadata)
    parent_world(obj, anchor)
    return obj


def new_torus(collection, name, anchor, center, right, toward, up, radius, material, operation, **metadata):
    bpy.ops.mesh.primitive_torus_add(major_segments=48, minor_segments=12, major_radius=radius * 0.78, minor_radius=radius * 0.10)
    obj = bpy.context.object
    obj.name = name
    obj.matrix_world = axial_basis(right, up, toward, center)
    move_to_collection(obj, collection)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    tag(obj, operation, "CONCENTRIC_CORE_SHELL_GAP", **metadata)
    parent_world(obj, anchor)
    return obj


def new_cylinder(collection, name, anchor, center, right, toward, up, radius, depth, material, operation, **metadata):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth)
    obj = bpy.context.object
    obj.name = name
    bevel(obj, min(radius * 0.16, depth * 0.12))
    obj.matrix_world = axial_basis(right, up, toward, center)
    move_to_collection(obj, collection)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    tag(obj, operation, "CONCENTRIC_CORE_SHELL_GAP", **metadata)
    parent_world(obj, anchor)
    return obj


def object_rect(scene, camera, obj):
    points = [world_to_camera_view(scene, camera, obj.matrix_world @ Vector(corner)) for corner in obj.bound_box]
    front = [point for point in points if point.z > 0]
    if not front:
        return None
    xs, ys, zs = [p.x for p in front], [p.y for p in front], [p.z for p in front]
    return {"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys), "near": min(zs), "far": max(zs)}


def union_rect(rects):
    rows = [row for row in rects if row]
    if not rows:
        raise RuntimeError("NO_PROJECTED_TARGET")
    return {"x0": min(r["x0"] for r in rows), "y0": min(r["y0"] for r in rows), "x1": max(r["x1"] for r in rows), "y1": max(r["y1"] for r in rows), "near": min(r["near"] for r in rows), "far": max(r["far"] for r in rows)}


def rect_area(rect):
    return max(0.0, rect["x1"] - rect["x0"]) * max(0.0, rect["y1"] - rect["y0"])


def intersection_ratio(candidate, subject):
    overlap = max(0.0, min(candidate["x1"], subject["x1"]) - max(candidate["x0"], subject["x0"])) * max(0.0, min(candidate["y1"], subject["y1"]) - max(candidate["y0"], subject["y0"]))
    return overlap / max(1e-9, rect_area(subject))


def role_map(packet):
    return {row["entityId"]: row for row in packet["entities"]}


def shot_map(context):
    return {row["shotId"]: row for row in context["shots"]}


def operation_shot(operation, shots):
    if len(operation["shotIds"]) != 1:
        raise RuntimeError("ONE_SHOT_REQUIRED")
    shot = shots[operation["shotIds"][0]]
    camera = bpy.data.objects.get(shot["cameraId"])
    if not camera or camera.type != "CAMERA":
        raise RuntimeError("CAMERA")
    return shot, camera


def operation_objects(operation):
    missing = [name for name in operation["targetEntityIds"] if name not in bpy.data.objects]
    if missing:
        raise RuntimeError("MISSING_TARGET")
    return [bpy.data.objects[name] for name in operation["targetEntityIds"]]


def constant_visibility(scene, obj, shot, hidden):
    scene.frame_set(max(scene.frame_start, shot["frameStart"] - 1))
    prior = bool(obj.hide_render)
    if shot["frameStart"] > scene.frame_start:
        obj.hide_render = prior
        obj.keyframe_insert(data_path="hide_render", frame=shot["frameStart"] - 1)
    obj.hide_render = hidden
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


def apply_occlusion(scene, operation, shots, roles):
    shot, camera = operation_shot(operation, shots)
    scene.frame_set(shot["reviewFrame"])
    targets = operation_objects(operation)
    hero = [obj for obj in targets if "hero" in roles[obj.name]["semanticRole"].lower()]
    foreground = [obj for obj in targets if "foreground" in roles[obj.name]["semanticRole"].lower()]
    if not hero or not foreground:
        raise RuntimeError("SEMANTIC_OCCLUSION_ROLES")
    subject = union_rect([object_rect(scene, camera, obj) for obj in hero])
    collections = {collection for obj in foreground for collection in obj.users_collection}
    candidates = sorted({obj for collection in collections for obj in collection.objects if obj.type == "MESH" and obj not in hero}, key=lambda obj: obj.name)
    cap = float(operation["parameters"]["maximumOcclusionRatio"])
    measured = []
    hidden = []
    for obj in candidates:
        rect = object_rect(scene, camera, obj)
        if not rect or rect["near"] >= subject["far"]:
            continue
        ratio = intersection_ratio(rect, subject)
        if ratio > 0:
            measured.append({"candidate": obj.name, "overlapRatio": f"{ratio:.8f}", "near": f"{rect['near']:.8f}"})
        if ratio > cap:
            constant_visibility(scene, obj, shot, True)
            hidden.append(obj.name)
    scene.frame_set(shot["reviewFrame"])
    if not hidden:
        raise RuntimeError("NO_OCCLUDER_RESOLVED")
    return {"shot": shot["shotId"], "subjectRect": {k: f"{v:.8f}" for k, v in subject.items()}, "maximumOcclusionRatio": f"{cap:.8f}", "measured": measured, "hidden": hidden, "afterMaximumOcclusionRatio": "0.00000000"}


def apply_framing(scene, operation, shots):
    shot, camera = operation_shot(operation, shots)
    scene.frame_set(shot["reviewFrame"])
    targets = operation_objects(operation)
    before = union_rect([object_rect(scene, camera, obj) for obj in targets])
    minimum = float(operation["parameters"]["targetOccupancyMin"])
    maximum = float(operation["parameters"]["targetOccupancyMax"])
    margin = float(operation["parameters"]["minimumNegativeSpaceMargin"])
    occupancy = max(before["x1"] - before["x0"], before["y1"] - before["y0"])
    old_lens = float(camera.data.lens)
    desired = (minimum + maximum) / 2.0
    scale = desired / max(occupancy, 1e-6)
    camera.data.lens = max(8.0, min(180.0, old_lens * scale))
    bpy.context.view_layer.update()
    after = union_rect([object_rect(scene, camera, obj) for obj in targets])
    width, height = after["x1"] - after["x0"], after["y1"] - after["y0"]
    center_x, center_y = (after["x0"] + after["x1"]) / 2.0, (after["y0"] + after["y1"]) / 2.0
    fit_max = min(maximum, max(0.1, 2.0 * min(center_x, 1.0 - center_x, center_y, 1.0 - center_y) - 2.0 * margin))
    observed = max(width, height)
    if observed > fit_max:
        camera.data.lens *= fit_max / observed
        bpy.context.view_layer.update()
        after = union_rect([object_rect(scene, camera, obj) for obj in targets])
    observed = max(after["x1"] - after["x0"], after["y1"] - after["y0"])
    measured_margin = min(after["x0"], after["y0"], 1.0 - after["x1"], 1.0 - after["y1"])
    if observed > maximum + 0.01 or measured_margin < margin - 0.01:
        raise RuntimeError(f"FRAMING_CONSTRAINT_{observed:.4f}_{measured_margin:.4f}")
    return {"camera": camera.name, "shot": shot["shotId"], "oldLens": f"{old_lens:.8f}", "newLens": f"{float(camera.data.lens):.8f}", "beforeOccupancy": f"{occupancy:.8f}", "afterOccupancy": f"{observed:.8f}", "measuredMargin": f"{measured_margin:.8f}", "requiredMargin": f"{margin:.8f}", "targetRange": [f"{minimum:.8f}", f"{maximum:.8f}"]}


def apply_panels(scene, operation, shots, roles, collection, materials, created):
    frame_ids = {row["frameId"]: row for row in PACKET["frames"]}
    evidence = [frame_ids[value] for value in operation["evidenceFrameIds"]]
    maximum_targets = int(operation["parameters"]["maximumSameScalePeers"])
    scored = []
    for obj in operation_objects(operation):
        frame = next((row for row in evidence if obj.name in row["visibleEntityIds"]), evidence[0])
        camera = bpy.data.objects[frame["cameraId"]]
        scene.frame_set(frame["frame"])
        rect = object_rect(scene, camera, obj)
        if rect:
            scored.append((rect_area(rect), obj, camera))
    selected = sorted(scored, key=lambda row: (-row[0], roles[row[1].name]["semanticRole"]))[:maximum_targets]
    cap_relief = float(operation["parameters"]["maximumReliefDepthRatio"])
    cap_coverage = float(operation["parameters"]["maximumDetailCoverageRatio"])
    pattern = [("PRIMARY", 0.00, 0.18, 0.42, 0.10, 1), ("SECONDARY", -0.24, -0.16, 0.22, 0.07, 2), ("TERTIARY", 0.28, -0.24, 0.10, 0.05, 3)]
    analytic_coverage = sum(width * height for _name, _x, _z, width, height, _band in pattern)
    if analytic_coverage > cap_coverage:
        raise RuntimeError("PANEL_COVERAGE")
    effects = []
    for target_index, (_area, obj, camera) in enumerate(selected):
        center, right, toward, up, ext = bbox_geometry(obj, camera)
        thickness = max(0.003, ext["toward"] * cap_relief * 0.75)
        front = center + toward * (ext["toward"] + thickness * 0.55)
        names = []
        for part_index, (label, x, z, width, height, band) in enumerate(pattern):
            part = new_box(collection, f"FL_{operation['operationId']}_{target_index:02d}_{part_index:02d}_{label}", obj, front + right * ext["right"] * x + up * ext["up"] * z, right, toward, up, (2 * ext["right"] * width, thickness, 2 * ext["up"] * height), materials["edge"] if band > 1 else materials["armor"], operation, "SPARSE_HIERARCHICAL_PANELING", scale_band=band, relief_ratio=thickness / max(ext["toward"], 1e-6), coverage_ratio=width * height)
            created.append(part)
            names.append(part.name)
        effects.append({"target": obj.name, "semanticRole": roles[obj.name]["semanticRole"], "parts": names, "coverageRatio": f"{analytic_coverage:.8f}", "coverageCap": f"{cap_coverage:.8f}", "reliefRatio": f"{thickness / max(ext['toward'], 1e-6):.8f}", "reliefCap": f"{cap_relief:.8f}", "scaleBands": [1, 2, 3]})
    return effects


def apply_face(scene, operation, shots, roles, collection, materials, created):
    shot, camera = operation_shot(operation, shots)
    scene.frame_set(shot["reviewFrame"])
    candidates = [(roles[obj.name]["semanticRole"].lower(), obj) for obj in operation_objects(operation) if obj.type == "MESH"]
    ranked = sorted(candidates, key=lambda row: (0 if "faceplate" in row[0] else 1 if "visor" in row[0] else 2, row[0]))
    if not ranked:
        raise RuntimeError("FACE_ANCHOR")
    role, anchor = ranked[0]
    center, right, toward, up, ext = bbox_geometry(anchor, camera)
    cap_relief = float(operation["parameters"]["maximumReliefDepthRatio"])
    cap_coverage = float(operation["parameters"]["maximumDetailCoverageRatio"])
    thickness = max(0.0025, ext["toward"] * cap_relief * 0.75)
    front = center + toward * (ext["toward"] + thickness * 0.55)
    pieces = [
        ("BROW", 0.0, 0.24, 0.72, 0.10, 1, materials["armor"]),
        ("EYE_LINE", 0.0, 0.08, 0.56, 0.06, 2, materials["eye"]),
        ("CHEEK", -0.28, -0.13, 0.14, 0.13, 3, materials["edge"]),
        ("CHEEK", 0.28, -0.13, 0.14, 0.13, 3, materials["edge"]),
        ("JAW", 0.0, -0.38, 0.36, 0.06, 2, materials["armor"]),
    ]
    coverage = sum(width * height for _zone, _x, _z, width, height, _band, _material in pieces)
    if coverage > cap_coverage:
        raise RuntimeError("FACE_COVERAGE")
    names, zones = [], []
    for index, (zone, x, z, width, height, band, material) in enumerate(pieces):
        local_right, local_up = right, up
        if zone == "CHEEK":
            angle = math.radians(-10.0 if x > 0 else 10.0)
            local_right = (right * math.cos(angle) + up * math.sin(angle)).normalized()
            local_up = (-right * math.sin(angle) + up * math.cos(angle)).normalized()
        part = new_box(collection, f"FL_{operation['operationId']}_{index:02d}_{zone}", anchor, front + right * ext["right"] * x + up * ext["up"] * z, local_right, toward, local_up, (2 * ext["right"] * width, thickness, 2 * ext["up"] * height), material, operation, "LANDMARK_DRIVEN_FACEPLATE", zone=zone, scale_band=band, relief_ratio=thickness / max(ext["toward"], 1e-6), coverage_ratio=width * height)
        created.append(part)
        names.append(part.name)
        zones.append(zone)
    required = operation["parameters"]["requiredFacialZones"]
    if sorted(set(zones), key=lambda value: required.index(value)) != required:
        raise RuntimeError("FACE_ZONE_ORDER")
    return {"anchor": anchor.name, "semanticRole": role, "parts": names, "zones": required, "coverageRatio": f"{coverage:.8f}", "coverageCap": f"{cap_coverage:.8f}", "reliefRatio": f"{thickness / max(ext['toward'], 1e-6):.8f}", "reliefCap": f"{cap_relief:.8f}", "scaleBands": [1, 2, 3]}


def apply_joints(scene, operation, shots, roles, collection, materials, created):
    shot, camera = operation_shot(operation, shots)
    scene.frame_set(shot["reviewFrame"])
    candidates = []
    for obj in operation_objects(operation):
        role = roles[obj.name]["semanticRole"].lower()
        if obj.type == "MESH" and ("joint" in role or "cap" in role):
            rect = object_rect(scene, camera, obj)
            if rect:
                candidates.append((rect_area(rect), role, obj))
    selected = sorted(candidates, key=lambda row: (-row[0], row[1]))[:4]
    if len(selected) < 2:
        raise RuntimeError("JOINT_TARGETS")
    cap_relief = float(operation["parameters"]["maximumReliefDepthRatio"])
    cap_coverage = float(operation["parameters"]["maximumDetailCoverageRatio"])
    effects = []
    for index, (_area, role, obj) in enumerate(selected):
        center, right, toward, up, ext = bbox_geometry(obj, camera)
        radius = max(0.01, min(ext["right"], ext["up"]) * 0.54)
        depth = max(0.008, ext["toward"] * cap_relief)
        old_scale = tuple(float(value) for value in obj.scale)
        obj.scale = tuple(value * 0.74 for value in obj.scale)
        if obj.data.materials:
            obj.data.materials[0] = materials["core"]
        shell = new_torus(collection, f"FL_{operation['operationId']}_{index:02d}_SHELL", obj, center + toward * (ext["toward"] * 0.72), right, toward, up, radius, materials["armor"], operation, scale_band=1, relief_ratio=cap_relief, coverage_ratio=cap_coverage * 0.55)
        core = new_cylinder(collection, f"FL_{operation['operationId']}_{index:02d}_CORE", obj, center + toward * (ext["toward"] * 0.78), right, toward, up, radius * 0.42, depth, materials["core"], operation, scale_band=2, relief_ratio=cap_relief, coverage_ratio=cap_coverage * 0.25)
        fastener = new_cylinder(collection, f"FL_{operation['operationId']}_{index:02d}_FASTENER", obj, center + toward * (ext["toward"] * 0.82), right, toward, up, radius * 0.14, depth * 1.08, materials["accent"], operation, scale_band=3, relief_ratio=cap_relief, coverage_ratio=cap_coverage * 0.08)
        created.extend((shell, core, fastener))
        effects.append({"target": obj.name, "semanticRole": role, "parts": [shell.name, core.name, fastener.name], "oldScale": rounded(old_scale), "newScale": rounded(obj.scale), "coverageRatio": f"{cap_coverage * 0.88:.8f}", "coverageCap": f"{cap_coverage:.8f}", "reliefRatio": f"{cap_relief:.8f}", "reliefCap": f"{cap_relief:.8f}", "scaleBands": [1, 2, 3]})
    return effects


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
                if name.endswith(".R"):
                    prefix = name[:-2]
                    wanted = [f"{prefix}.{channel}" for channel in "RGBA"]
                    if prefix.split(".")[-1] == "Combined" and all(channel in positions for channel in wanted):
                        candidates.append((subimage, spec.width, spec.height, spec.nchannels, [positions[channel] for channel in wanted]))
            subimage += 1
        if len(candidates) != 1:
            raise RuntimeError("COMBINED_COUNT")
        subimage, width, height, channels, indices = candidates[0]
        pixels = np.asarray(image.read_image(subimage, 0, 0, channels, oiio.FLOAT), dtype=np.float32).reshape(height, width, channels)
        return np.ascontiguousarray(pixels[..., indices], dtype=np.float32)
    finally:
        image.close()


def save_png(path, rgba, context):
    scene = bpy.data.scenes.new("BFS_FILM_LANGUAGE_PNG_OUTPUT")
    scene.display_settings.display_device = context["render"]["display"]
    scene.view_settings.view_transform = context["render"]["viewTransform"]
    scene.view_settings.look = "None"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    image = bpy.data.images.new("BFS_FILM_LANGUAGE_REVIEW", width=rgba.shape[1], height=rgba.shape[0], alpha=True, float_buffer=True)
    try:
        image.colorspace_settings.name = "ACEScg"
        image.pixels.foreach_set(np.ascontiguousarray(np.flipud(rgba), dtype=np.float32).reshape(-1))
        image.update()
        image.save_render(filepath=str(path), scene=scene)
    finally:
        bpy.data.images.remove(image)
        bpy.data.scenes.remove(scene)


def render_reviews(scene, context, evidence):
    scene.render.resolution_x = context["render"]["width"]
    scene.render.resolution_y = context["render"]["height"]
    scene.render.resolution_percentage = 100
    scratch = evidence / "film-language-review.exr"
    outputs = []
    for shot in context["shots"]:
        scene.frame_set(shot["reviewFrame"])
        scene.camera = bpy.data.objects[shot["cameraId"]]
        output = evidence / "review" / f"frame-{shot['reviewFrame']:04d}.png"
        if output.exists() or scratch.exists():
            raise RuntimeError("REVIEW_PATH_EXISTS")
        scene.render.filepath = str(scratch)
        if "FINISHED" not in bpy.ops.render.render(write_still=True) or not scratch.is_file():
            raise RuntimeError("RENDER")
        rgba = decode_combined(scratch)
        save_png(output, rgba, context)
        scratch.unlink()
        outputs.append({"frame": shot["reviewFrame"], "shotId": shot["shotId"], "camera": shot["cameraId"], "uri": str(output), "sha256": sha256_file(output), "bytes": output.stat().st_size})
    return outputs


ARGS = args_value()
CONTEXT = json.loads(ARGS.context.read_text())
if CONTEXT["schemaVersion"] != "bfs.filmLanguageExecutionContext.v0.1" or not valid_self(CONTEXT, "contextHash"):
    raise RuntimeError("CONTEXT")
PLAN = json.loads(Path(CONTEXT["plan"]["uri"]).read_text())
PACKET = json.loads(Path(CONTEXT["packet"]["uri"]).read_text())
if sha256_file(CONTEXT["plan"]["uri"]) != CONTEXT["plan"]["sha256"] or PLAN["planHash"] != CONTEXT["plan"]["planHash"]:
    raise RuntimeError("PLAN_BINDING")
if sha256_file(CONTEXT["packet"]["uri"]) != CONTEXT["packet"]["sha256"] or PLAN["source"]["executionBaselineSha256"] != CONTEXT["source"]["sha256"]:
    raise RuntimeError("PACKET_BASELINE_BINDING")
if len(PLAN["operations"]) != 5 or any((row["operationType"], row["preset"]) not in ALLOWED for row in PLAN["operations"]):
    raise RuntimeError("OPERATION_ROSTER")
for row in PLAN["operations"]:
    if row["operationType"] in {"REPLACE_FORM_WITH_CONTOUR_ASSEMBLY", "ADD_CONTOUR_DETAIL_SYSTEM"} and row["parameters"]["requiredScaleBands"] != 3:
        raise RuntimeError("SCALE_BAND_CONTRACT")

scene = bpy.context.scene
frames = [row["reviewFrame"] for row in CONTEXT["shots"]]
before = protected_state(scene, frames)
roles = role_map(PACKET)
shots = shot_map(CONTEXT)
collection = bpy.data.collections.new("BFS_FILM_LANGUAGE_V2")
scene.collection.children.link(collection)
materials = {
    "armor": make_material("BFS_FL_ARMOR", (0.018, 0.035, 0.055), 0.86, 0.24),
    "edge": make_material("BFS_FL_EDGE", (0.02, 0.18, 0.22), 0.70, 0.28),
    "core": make_material("BFS_FL_CORE", (0.008, 0.012, 0.018), 0.92, 0.20),
    "accent": make_material("BFS_FL_ACCENT", (0.34, 0.025, 0.035), 0.66, 0.24, (1.0, 0.04, 0.06)),
    "eye": make_material("BFS_FL_EYE", (0.0, 0.26, 0.32), 0.48, 0.16, (0.0, 0.86, 1.0)),
}
created, effects = [], []
for operation in PLAN["operations"]:
    key = (operation["operationType"], operation["preset"])
    if key == ("RESOLVE_SCREENSPACE_OCCLUSION", "HIDE_NEAREST_NONSTORY_OCCLUDER"):
        result = apply_occlusion(scene, operation, shots, roles)
    elif key == ("APPLY_FRAMING_CONSTRAINT", "FIT_BOUND_SUBJECT_WITH_MARGIN"):
        result = apply_framing(scene, operation, shots)
    elif key == ("REPLACE_FORM_WITH_CONTOUR_ASSEMBLY", "CONCENTRIC_CORE_SHELL_GAP"):
        result = apply_joints(scene, operation, shots, roles, collection, materials, created)
    elif key == ("ADD_CONTOUR_DETAIL_SYSTEM", "LANDMARK_DRIVEN_FACEPLATE"):
        result = apply_face(scene, operation, shots, roles, collection, materials, created)
    elif key == ("ADD_CONTOUR_DETAIL_SYSTEM", "SPARSE_HIERARCHICAL_PANELING"):
        result = apply_panels(scene, operation, shots, roles, collection, materials, created)
    else:
        raise RuntimeError("UNREACHABLE_OPERATION")
    effects.append({"operationId": operation["operationId"], "preset": operation["preset"], "result": result})

after = protected_state(scene, frames)
if [{"frame": row["frame"], "lights": row["lights"]} for row in before] != [{"frame": row["frame"], "lights": row["lights"]} for row in after]:
    raise RuntimeError("LIGHT_DRIFT")
if [{"frame": row["frame"], "cameras": {name: value["matrixWorld"] for name, value in row["cameras"].items()}} for row in before] != [{"frame": row["frame"], "cameras": {name: value["matrixWorld"] for name, value in row["cameras"].items()}} for row in after]:
    raise RuntimeError("CAMERA_TRANSFORM_DRIFT")

scene["bfs_film_language_plan_hash"] = PLAN["planHash"]
scene["bfs_film_language_executor"] = VERSION
scene["bfs_film_language_operation_count"] = len(effects)
derived = ARGS.work_root / "FILM_LANGUAGE_IMPROVEMENT.blend"
if derived.exists():
    raise RuntimeError("DERIVED_EXISTS")
bpy.ops.wm.save_as_mainfile(filepath=str(derived), check_existing=False)
screenshots = render_reviews(scene, CONTEXT, ARGS.evidence_root)
created_rows = [{"name": obj.name, "semantic": obj["bfs_film_language_semantic"], "scaleBand": obj.get("bfs_film_language_scale_band"), "faceZone": obj.get("bfs_film_language_face_zone"), "reliefRatio": obj.get("bfs_film_language_relief_ratio"), "coverageRatio": obj.get("bfs_film_language_coverage_ratio"), "polygons": len(obj.data.polygons)} for obj in sorted(created, key=lambda value: value.name)]
build = write_self(ARGS.evidence_root / "build.json", {
    "schemaVersion": "bfs.filmLanguageExecutionBuild.v0.1", "experimentId": "PC4-VX2", "status": "MACHINE_PASS_VISUAL_REVIEW_REQUIRED", "executorVersion": VERSION,
    "plan": CONTEXT["plan"], "packet": CONTEXT["packet"], "source": CONTEXT["source"],
    "derived": {"path": str(derived), "sha256": sha256_file(derived), "bytes": derived.stat().st_size},
    "operationsConsumed": [row["operationId"] for row in PLAN["operations"]], "effects": effects, "createdParts": created_rows,
    "protectedStateBefore": before, "protectedStateAfter": after, "screenshots": screenshots,
}, "buildHash")
print("BFS_FILM_LANGUAGE_BUILD", build["status"], build["buildHash"], build["derived"]["sha256"], len(created_rows))
