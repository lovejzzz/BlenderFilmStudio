#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Reopen and independently audit the PC.2 action derivative."""

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy


SENTINELS = (1, 48, 96, 97, 144, 192, 193, 240, 288)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def normalize(value):
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def hash_value(value):
    return hashlib.sha256(canonical(normalize(value))).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_self(value, field):
    body = dict(value)
    expected = body.pop(field, None)
    return expected == hash_value(body)


def write_self(path, value, field):
    body = normalize(dict(value))
    body[field] = hash_value(body)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, (json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return body


def rounded(values):
    return [round(float(value), 9) for value in values]


def camera_light_state(scene):
    cameras = sorted((obj for obj in bpy.data.objects if obj.type == "CAMERA"), key=lambda item: item.name)
    lights = sorted((obj for obj in bpy.data.objects if obj.type == "LIGHT"), key=lambda item: item.name)
    rows = []
    for frame in SENTINELS:
        scene.frame_set(frame)
        rows.append({
            "frame": frame,
            "cameras": {obj.name: {"matrixWorld": [rounded(row) for row in obj.matrix_world], "lens": round(float(obj.data.lens), 9)} for obj in cameras},
            "lights": {obj.name: {"matrixWorld": [rounded(row) for row in obj.matrix_world], "energy": round(float(obj.data.energy), 9), "color": rounded(obj.data.color)} for obj in lights},
        })
    return rows


def mesh_geometry_state():
    rows = []
    for obj in sorted((item for item in bpy.data.objects if item.type == "MESH"), key=lambda item: item.name):
        mesh = obj.data
        rows.append({"object": obj.name, "data": mesh.name, "parent": obj.parent.name if obj.parent else None, "parentType": obj.parent_type, "parentBone": obj.parent_bone, "vertices": [rounded(vertex.co) for vertex in mesh.vertices], "edges": [list(edge.vertices) for edge in mesh.edges], "polygons": [list(polygon.vertices) for polygon in mesh.polygons], "materials": [slot.material.name if slot.material else None for slot in obj.material_slots], "modifiers": [(modifier.name, modifier.type) for modifier in obj.modifiers]})
    return {"objects": len(bpy.data.objects), "meshes": len(rows), "polygons": sum(len(obj.data.polygons) for obj in bpy.data.objects if obj.type == "MESH"), "canonicalSha256": hash_value(rows)}


def material_state():
    rows = []
    for material in sorted(bpy.data.materials, key=lambda item: item.name):
        nodes = []
        if material.use_nodes and material.node_tree:
            for node in sorted(material.node_tree.nodes, key=lambda item: item.name):
                inputs = []
                for index, socket in enumerate(node.inputs):
                    value = getattr(socket, "default_value", None)
                    if isinstance(value, (float, int)):
                        inputs.append([index, socket.name, round(float(value), 9)])
                    elif value is not None and hasattr(value, "__len__"):
                        try:
                            inputs.append([index, socket.name, rounded(value)])
                        except (TypeError, ValueError):
                            pass
                nodes.append({"name": node.name, "type": node.bl_idname, "inputs": inputs})
        rows.append({"name": material.name, "useNodes": bool(material.use_nodes), "nodes": nodes})
    return {"materials": len(rows), "canonicalSha256": hash_value(rows)}


def shot_state(scene):
    return [{"name": marker.name, "frame": marker.frame, "camera": marker.camera.name if marker.camera else None} for marker in sorted(scene.timeline_markers, key=lambda item: (item.frame, item.name))]


def action_fcurves(action):
    curves = []
    if action is None:
        return curves
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                curves.extend(channelbag.fcurves)
    return curves


def curve_for(target, data_path, index):
    action = target.animation_data.action if target.animation_data else None
    matches = [curve for curve in action_fcurves(action) if curve.data_path == data_path and curve.array_index == index]
    if len(matches) != 1:
        raise RuntimeError(f"CURVE_{target.name}_{data_path}_{index}_{len(matches)}")
    return matches[0]


def verify_signal(row):
    target = bpy.data.objects[row["target"]]
    curve = curve_for(target, row["dataPath"], row["arrayIndex"])
    points = {round(float(point.co[0]), 6): float(point.co[1]) for point in curve.keyframe_points}
    actual = []
    for frame, expected in zip(row["frames"], row["values"], strict=True):
        if float(frame) not in points or abs(points[float(frame)] - float(expected)) > 1e-6:
            raise RuntimeError(f"SIGNAL_POINT_{row['target']}_{row['dataPath']}_{frame}")
        actual.append(points[float(frame)])
    peak = max(actual) - min(actual)
    return {"phase": row["phase"], "target": row["target"], "dataPath": row["dataPath"], "arrayIndex": row["arrayIndex"], "frames": row["frames"], "peakToPeak": round(peak, 9), "minimumPeakToPeak": row["minimumPeakToPeak"], "passed": peak + 1e-6 >= row["minimumPeakToPeak"]}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    return parser.parse_args(argv)


args = parse_args()
spec = json.loads(args.spec.read_text(encoding="utf-8"))
build = json.loads((args.evidence_root / "build.json").read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or not valid_self(build, "buildHash"):
    raise RuntimeError("SELF_HASH")
scene = bpy.context.scene
opened_path = Path(bpy.data.filepath)
if sha256_file(opened_path) != build["derived"]["sha256"]:
    raise RuntimeError("DERIVED_SHA")
if scene.get("bfs_pc2_spec_hash") != spec["specHash"] or scene.get("bfs_pc2_source_sha256") != spec["acceptedPc1Baseline"]["sha256"] or scene.get("bfs_pc2_signal_hash") != hash_value(build["signals"]):
    raise RuntimeError("SCENE_BINDING")

geometry = mesh_geometry_state()
materials = material_state()
protected = camera_light_state(scene)
shots = shot_state(scene)
if geometry != build["geometryAfter"] or geometry != build["geometryBefore"]:
    raise RuntimeError("GEOMETRY")
if materials != build["materialsAfter"] or materials != build["materialsBefore"]:
    raise RuntimeError("MATERIALS")
if protected != build["protectedStateAfter"] or protected != build["protectedStateBefore"]:
    raise RuntimeError("PROTECTED")
if hash_value(protected) != spec["acceptedPc1Baseline"]["cameraLightSentinelsCanonicalSha256"]:
    raise RuntimeError("PROTECTED_BASELINE")
if shots != build["shotsAfter"] or shots != build["shotsBefore"]:
    raise RuntimeError("SHOTS")

signal_checks = [verify_signal(row) for row in build["signals"]]
phase_ids = sorted({row["phase"] for row in signal_checks})
signal_targets = sorted({row["target"] for row in signal_checks})
if not all(row["passed"] for row in signal_checks):
    raise RuntimeError("AMPLITUDE")
if len(phase_ids) != spec["acceptance"]["minimumSemanticTemporalPhases"] or len(signal_targets) < spec["acceptance"]["minimumAnimatedNonCameraTargets"]:
    raise RuntimeError("FLOORS")
if not set(signal_targets).issubset(set(spec["authorizedAnimatedNonCameraTargets"])):
    raise RuntimeError("TARGET_SCOPE")
render_artifacts = sorted(str(path) for root in (args.evidence_root, args.work_root) for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"})
if render_artifacts:
    raise RuntimeError("RENDER_ARTIFACTS")

audit = write_self(args.evidence_root / "semantic-audit.json", {
    "schemaVersion": "bfs.pc2SemanticAudit.v0.1",
    "status": "PASS",
    "gate": "PC.2",
    "openedBlend": {"path": str(opened_path), "sha256": sha256_file(opened_path)},
    "geometry": geometry,
    "materials": materials,
    "protectedStateCanonicalSha256": hash_value(protected),
    "shotStateCanonicalSha256": hash_value(shots),
    "phaseIds": phase_ids,
    "signalTargets": signal_targets,
    "signalChecks": signal_checks,
    "independentActionChannels": build["independentActionChannels"],
    "renderArtifacts": render_artifacts,
    "operations": {"BlenderStarts": 1, "renderCalls": 0, "sceneSaves": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0},
}, "auditHash")
print("PC2_AUDIT=" + json.dumps({"status": audit["status"], "auditHash": audit["auditHash"]}, sort_keys=True), flush=True)
