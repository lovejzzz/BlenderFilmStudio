#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build the preregistered PC.2 action-complexity derivative."""

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


def normalize_numbers(value):
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_numbers(item) for key, item in value.items()}
    return value


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_value(value):
    return hashlib.sha256(canonical(normalize_numbers(value))).hexdigest()


def valid_self(value, field):
    body = dict(value)
    expected = body.pop(field, None)
    return expected == hash_value(body)


def write_self(path, value, field):
    body = normalize_numbers(dict(value))
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
    result = []
    for frame in SENTINELS:
        scene.frame_set(frame)
        result.append({
            "frame": frame,
            "cameras": {obj.name: {"matrixWorld": [rounded(row) for row in obj.matrix_world], "lens": round(float(obj.data.lens), 9)} for obj in cameras},
            "lights": {obj.name: {"matrixWorld": [rounded(row) for row in obj.matrix_world], "energy": round(float(obj.data.energy), 9), "color": rounded(obj.data.color)} for obj in lights},
        })
    return result


def action_fcurves(action):
    curves = []
    if action is None:
        return curves
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                curves.extend(channelbag.fcurves)
    return curves


def action_summary():
    rows = []
    for action in sorted(bpy.data.actions, key=lambda item: item.name):
        curves = action_fcurves(action)
        rows.append({"name": action.name, "fcurves": len(curves), "keyframes": sum(len(curve.keyframe_points) for curve in curves)})
    return rows


def animated_object_targets():
    return sorted(obj.name for obj in bpy.data.objects if obj.animation_data and obj.animation_data.action)


def mesh_geometry_state():
    rows = []
    for obj in sorted((item for item in bpy.data.objects if item.type == "MESH"), key=lambda item: item.name):
        mesh = obj.data
        rows.append({
            "object": obj.name,
            "data": mesh.name,
            "parent": obj.parent.name if obj.parent else None,
            "parentType": obj.parent_type,
            "parentBone": obj.parent_bone,
            "vertices": [rounded(vertex.co) for vertex in mesh.vertices],
            "edges": [list(edge.vertices) for edge in mesh.edges],
            "polygons": [list(polygon.vertices) for polygon in mesh.polygons],
            "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
            "modifiers": [(modifier.name, modifier.type) for modifier in obj.modifiers],
        })
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


def set_object_curve(scene, obj, data_path, index, frames, values):
    for frame, value in zip(frames, values, strict=True):
        scene.frame_set(frame)
        target = getattr(obj, data_path)
        target[index] = value
        obj.keyframe_insert(data_path=data_path, index=index, frame=frame, group="PC2_ACTION_COMPLEXITY")


def set_bone_curve(scene, bone, data_path, index, frames, values):
    for frame, value in zip(frames, values, strict=True):
        scene.frame_set(frame)
        target = getattr(bone, data_path)
        target[index] = value
        bone.keyframe_insert(data_path=data_path, index=index, frame=frame, group="PC2_ACTION_COMPLEXITY")


def set_constraint_curve(scene, constraint, frames, values):
    for frame, value in zip(frames, values, strict=True):
        scene.frame_set(frame)
        constraint.influence = value
        constraint.keyframe_insert(data_path="influence", frame=frame, group="PC2_ACTION_COMPLEXITY")


def sampled(scene, frames, getter):
    values = []
    for frame in frames:
        scene.frame_set(frame)
        values.append(float(getter()))
    return values


def signal(phase, target, data_path, index, frames, values, minimum):
    return {"phase": phase, "target": target, "dataPath": data_path, "arrayIndex": index, "frames": frames, "values": rounded(values), "peakToPeak": round(max(values) - min(values), 9), "minimumPeakToPeak": minimum}


def add_action_complexity(scene):
    rig = bpy.data.objects["RIG_B62_GUARDIAN"]
    chest = rig.pose.bones["chest"]
    head = rig.pose.bones["head"]
    target = bpy.data.objects["B62_PHASE0_IK_HAND_R_TARGET"]
    pole = bpy.data.objects["B62_PHASE0_IK_HAND_R_POLE"]
    socket = bpy.data.objects["HAND_R_SOCKET"]
    socket_lock = socket.constraints["B62_PHASE0_CONTACT_SOCKET_LOCK"]

    approach = [1, 17, 33, 49, 65, 81, 96]
    root_z = [0.0, 0.03, 0.0, 0.035, 0.0, 0.025, 0.0]
    chest_roll = [0.0, -0.025, 0.025, -0.03, 0.03, -0.02, 0.0]
    set_object_curve(scene, rig, "location", 2, approach, root_z)
    set_bone_curve(scene, chest, "rotation_euler", 2, approach, chest_roll)

    contact = [97, 108, 118, 126, 132, 150, 176, 192]
    target_base = sampled(scene, contact, lambda: target.location[2])
    pole_base = sampled(scene, contact, lambda: pole.location[0])
    target_values = [base + offset for base, offset in zip(target_base, [0.0, 0.035, 0.075, 0.11, 0.095, 0.06, 0.025, 0.0], strict=True)]
    pole_values = [base + offset for base, offset in zip(pole_base, [0.0, -0.02, -0.055, -0.075, -0.06, -0.035, -0.015, 0.0], strict=True)]
    socket_values = [0.0, 0.12, 0.55, 0.92, 1.0, 0.88, 0.32, 0.0]
    set_object_curve(scene, target, "location", 2, contact, target_values)
    set_object_curve(scene, pole, "location", 0, contact, pole_values)
    set_constraint_curve(scene, socket_lock, contact, socket_values)

    activation = [138, 144, 150, 160, 176, 192]
    gimbal_signals = []
    for index in range(4):
        obj = bpy.data.objects[f"PC1_CORE_GIMBAL_{index:02d}"]
        obj.rotation_mode = "XYZ"
        base = float(obj.rotation_euler[2])
        sign = 1.0 if index % 2 == 0 else -1.0
        offsets = [0.0, 0.10 + index * 0.03, 0.28 + index * 0.04, 0.58 + index * 0.05, 0.92 + index * 0.06, 1.18 + index * 0.07]
        values = [base + sign * offset for offset in offsets]
        set_object_curve(scene, obj, "rotation_euler", 2, activation, values)
        gimbal_signals.append(signal("ACTIVATION_MECHANICAL_RECOIL", obj.name, "rotation_euler", 2, activation, values, 0.45))
    chest_activation_base = sampled(scene, activation, lambda: chest.rotation_euler[0])
    chest_activation = [base + offset for base, offset in zip(chest_activation_base, [0.0, -0.02, -0.055, -0.08, -0.035, 0.0], strict=True)]
    set_bone_curve(scene, chest, "rotation_euler", 0, activation, chest_activation)

    reflection = [193, 208, 224, 240, 264, 288]
    chest_reflection_base = sampled(scene, reflection, lambda: chest.rotation_euler[0])
    head_reflection_base = sampled(scene, reflection, lambda: head.rotation_euler[2])
    chest_reflection = [base + offset for base, offset in zip(chest_reflection_base, [0.0, 0.022, 0.046, 0.018, 0.034, 0.0], strict=True)]
    head_reflection = [base + offset for base, offset in zip(head_reflection_base, [0.0, -0.035, 0.055, 0.085, 0.025, 0.0], strict=True)]
    set_bone_curve(scene, chest, "rotation_euler", 0, reflection, chest_reflection)
    set_bone_curve(scene, head, "rotation_euler", 2, reflection, head_reflection)
    fin_signals = []
    for name, sign in (("PC1_GUARDIAN_SHOULDER_FIN_L", 1.0), ("PC1_GUARDIAN_SHOULDER_FIN_R", -1.0)):
        obj = bpy.data.objects[name]
        obj.rotation_mode = "XYZ"
        base = float(obj.rotation_euler[1])
        offsets = [0.0, 0.025, 0.07, 0.10, 0.045, 0.0]
        values = [base + sign * offset for offset in offsets]
        set_object_curve(scene, obj, "rotation_euler", 1, reflection, values)
        fin_signals.append(signal("REFLECTION_BREATH_SETTLE", name, "rotation_euler", 1, reflection, values, 0.06))

    signals = [
        signal("APPROACH_WEIGHT_TRANSFER", rig.name, "location", 2, approach, root_z, 0.025),
        signal("APPROACH_WEIGHT_TRANSFER", rig.name, 'pose.bones["chest"].rotation_euler', 2, approach, chest_roll, 0.04),
        signal("CONTACT_REACH_ARC", target.name, "location", 2, contact, target_values, 0.08),
        signal("CONTACT_REACH_ARC", pole.name, "location", 0, contact, pole_values, 0.05),
        signal("CONTACT_REACH_ARC", socket.name, 'constraints["B62_PHASE0_CONTACT_SOCKET_LOCK"].influence', 0, contact, socket_values, 0.9),
        *gimbal_signals,
        signal("ACTIVATION_MECHANICAL_RECOIL", rig.name, 'pose.bones["chest"].rotation_euler', 0, activation, chest_activation, 0.05),
        signal("REFLECTION_BREATH_SETTLE", rig.name, 'pose.bones["chest"].rotation_euler', 0, reflection, chest_reflection, 0.035),
        signal("REFLECTION_BREATH_SETTLE", rig.name, 'pose.bones["head"].rotation_euler', 2, reflection, head_reflection, 0.06),
        *fin_signals,
    ]
    return signals


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    return parser.parse_args(argv)


args = parse_args()
spec = json.loads(args.spec.read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or spec["status"] != "PREREGISTERED_BEFORE_PC2_ACTION_MUTATION":
    raise RuntimeError("SPEC")
scene = bpy.context.scene
source_path = Path(bpy.data.filepath)
source_before = sha256_file(source_path)
if source_before != spec["acceptedPc1Baseline"]["sha256"]:
    raise RuntimeError("SOURCE")

geometry_before = mesh_geometry_state()
materials_before = material_state()
protected_before = camera_light_state(scene)
shots_before = shot_state(scene)
actions_before = action_summary()
targets_before = animated_object_targets()
if geometry_before != {"objects": 104, "meshes": 92, "polygons": 19810, "canonicalSha256": geometry_before["canonicalSha256"]}:
    raise RuntimeError("BASELINE_COUNTS")
if hash_value(actions_before) != spec["acceptedPc1Baseline"]["actionSummaryCanonicalSha256"]:
    raise RuntimeError("BASELINE_ACTIONS")
if hash_value(protected_before) != spec["acceptedPc1Baseline"]["cameraLightSentinelsCanonicalSha256"]:
    raise RuntimeError("BASELINE_PROTECTED_STATE")

signals = add_action_complexity(scene)
scene.frame_set(1)
geometry_after = mesh_geometry_state()
materials_after = material_state()
protected_after = camera_light_state(scene)
shots_after = shot_state(scene)
actions_after = action_summary()
targets_after = animated_object_targets()
added_targets = sorted(set(targets_after) - set(targets_before))
authorized = set(spec["authorizedAnimatedNonCameraTargets"])
signal_targets = sorted({row["target"] for row in signals})
if geometry_before != geometry_after or materials_before != materials_after:
    raise RuntimeError("GEOMETRY_OR_MATERIAL_DRIFT")
if protected_before != protected_after or shots_before != shots_after:
    raise RuntimeError("PROTECTED_STATE_DRIFT")
if not set(added_targets).issubset(authorized) or not set(signal_targets).issubset(authorized):
    raise RuntimeError("UNAUTHORIZED_TARGET")
if len(signal_targets) < spec["acceptance"]["minimumAnimatedNonCameraTargets"]:
    raise RuntimeError("TARGET_FLOOR")
if any(row["peakToPeak"] + 1e-9 < row["minimumPeakToPeak"] for row in signals):
    raise RuntimeError("AMPLITUDE_FLOOR")
if len({row["phase"] for row in signals}) != spec["acceptance"]["minimumSemanticTemporalPhases"]:
    raise RuntimeError("PHASE_FLOOR")

scene["bfs_pc2_spec_hash"] = spec["specHash"]
scene["bfs_pc2_source_sha256"] = source_before
scene["bfs_pc2_signal_hash"] = hash_value(signals)
derived_path = args.work_root / "PC2_ACTION_COMPLEXITY.blend"
bpy.context.preferences.filepaths.file_preview_type = "NONE"
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(derived_path), check_existing=False)
source_after = sha256_file(source_path)
if source_after != source_before:
    raise RuntimeError("SOURCE_DRIFT")

record = write_self(args.evidence_root / "build.json", {
    "schemaVersion": "bfs.pc2ActionBuild.v0.1",
    "status": "PASS",
    "source": {"path": str(source_path), "beforeSha256": source_before, "afterSha256": source_after},
    "derived": {"path": str(derived_path), "sha256": sha256_file(derived_path), "bytes": derived_path.stat().st_size},
    "geometryBefore": geometry_before,
    "geometryAfter": geometry_after,
    "materialsBefore": materials_before,
    "materialsAfter": materials_after,
    "protectedStateBefore": protected_before,
    "protectedStateAfter": protected_after,
    "shotsBefore": shots_before,
    "shotsAfter": shots_after,
    "actionsBefore": actions_before,
    "actionsAfter": actions_after,
    "animatedTargetsBefore": targets_before,
    "animatedTargetsAfter": targets_after,
    "addedAnimatedTargets": added_targets,
    "signalTargets": signal_targets,
    "signals": signals,
    "phaseIds": sorted({row["phase"] for row in signals}),
    "independentActionChannels": spec["independentActionChannels"],
    "operations": {"BlenderStarts": 1, "renderCalls": 0, "derivedSceneSaves": 1, "sourceSceneSaves": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0},
}, "buildHash")
print("PC2_BUILD=" + json.dumps({"status": record["status"], "buildHash": record["buildHash"]}, sort_keys=True), flush=True)
