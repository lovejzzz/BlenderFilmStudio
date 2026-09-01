#!/usr/bin/env python3
"""Zero-render reopen auditor for the trusted typed visual plan executor."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy


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


def protected_state(scene, frames):
    cameras = sorted((obj for obj in bpy.data.objects if obj.type == "CAMERA"), key=lambda obj: obj.name)
    lights = sorted((obj for obj in bpy.data.objects if obj.type == "LIGHT"), key=lambda obj: obj.name)
    rows = []
    for frame in frames:
        scene.frame_set(frame)
        rows.append({
            "frame": frame,
            "cameras": {obj.name: {"matrixWorld": [rounded(row) for row in obj.matrix_world], "lens": number_string(obj.data.lens)} for obj in cameras},
            "lights": {obj.name: {"matrixWorld": [rounded(row) for row in obj.matrix_world], "energy": number_string(obj.data.energy), "color": rounded(obj.data.color)} for obj in lights},
        })
    return rows


args = parse_args()
context = json.loads(args.context.read_text(encoding="utf-8"))
if not valid_self(context, "contextHash") or context["experimentId"] != "PC4-VX1":
    raise RuntimeError("CONTEXT")
build_path = args.evidence_root / "build.json"
build = json.loads(build_path.read_text(encoding="utf-8"))
if not valid_self(build, "buildHash") or build["status"] != "MACHINE_PASS_VISUAL_REVIEW_REQUIRED":
    raise RuntimeError("BUILD")
derived_path = args.work_root / "PC4_TYPED_VISUAL_IMPROVEMENT.blend"
if Path(bpy.data.filepath) != derived_path or sha256_file(derived_path) != build["derived"]["sha256"]:
    raise RuntimeError("DERIVED")
if sha256_file(context["source"]["path"]) != context["source"]["sha256"]:
    raise RuntimeError("SOURCE_DRIFT")
scene = bpy.context.scene
if scene.get("bfs_visual_plan_hash") != context["plan"]["planHash"] or scene.get("bfs_typed_operation_count") != 6:
    raise RuntimeError("SCENE_BINDING")
collection = bpy.data.collections.get("BFS_TYPED_VISUAL_IMPROVEMENT")
if not collection:
    raise RuntimeError("COLLECTION")
created = sorted((obj for obj in collection.objects if obj.get("bfs_typed_executor_version") == "BFS_TYPED_VISUAL_EXECUTOR_0_1"), key=lambda obj: obj.name)
if len(created) != len(build["createdParts"]) or len(created) < 28:
    raise RuntimeError("CREATED_PARTS")
if [obj.name for obj in created] != sorted(row["name"] for row in build["createdParts"]):
    raise RuntimeError("CREATED_ROSTER")

plan = json.loads(Path(context["plan"]["uri"]).read_text(encoding="utf-8"))
visibility = next(operation for operation in plan["operations"] if operation["operationType"] == "SET_SHOT_VISIBILITY")
for target in visibility["targetEntityIds"]:
    obj = bpy.data.objects[target]
    scene.frame_set(48)
    if not obj.hide_render:
        raise RuntimeError("VISIBILITY_AT_REVIEW")
    scene.frame_set(97)
    if obj.hide_render:
        raise RuntimeError("VISIBILITY_OUTSIDE_SHOT")

current_state = protected_state(scene, context["render"]["reviewFrames"])
if current_state != build["protectedStateAfter"]:
    raise RuntimeError("PROTECTED_STATE_REOPEN")
for row in build["screenshots"]:
    path = Path(row["uri"])
    if not path.is_file() or sha256_file(path) != row["sha256"]:
        raise RuntimeError("SCREENSHOT_DRIFT")

semantic_counts = {}
for obj in created:
    semantic = obj["bfs_typed_semantic"]
    semantic_counts[semantic] = semantic_counts.get(semantic, 0) + 1
if semantic_counts.get("LAYERED_MECHANICAL_JOINT", 0) < 12 or semantic_counts.get("FACIAL_SEGMENTATION", 0) < 7 or semantic_counts.get("MID_SCALE_PANEL_HIERARCHY", 0) < 9:
    raise RuntimeError("SEMANTIC_FLOORS")

record = write_self(args.evidence_root / "reopen-audit.json", {
    "schemaVersion": "bfs.visualPlanTypedExecutionReopenAudit.v0.1",
    "experimentId": "PC4-VX1",
    "status": "PASS",
    "build": {"uri": str(build_path), "sha256": sha256_file(build_path), "buildHash": build["buildHash"]},
    "derived": {"path": str(derived_path), "sha256": sha256_file(derived_path)},
    "planHash": context["plan"]["planHash"],
    "operationsConsumed": build["operationsConsumed"],
    "createdParts": len(created),
    "semanticCounts": semantic_counts,
    "visibilityRoundTrip": True,
    "protectedStateRoundTrip": True,
    "screenshotsExact": len(build["screenshots"]),
    "operations": {"BlenderStarts": 1, "renderCalls": 0, "sceneSaves": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0},
}, "auditHash")
print("BFS_TYPED_VISUAL_REOPEN=" + json.dumps({"status": record["status"], "auditHash": record["auditHash"], "createdParts": len(created)}, sort_keys=True), flush=True)
