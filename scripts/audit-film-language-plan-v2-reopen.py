#!/usr/bin/env python3
"""Reopen audit for the relation-constrained film-language executor."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy


VERSION = "BFS_FILM_LANGUAGE_EXECUTOR_0_2"


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


args = args_value()
context = json.loads(args.context.read_text())
if context["schemaVersion"] != "bfs.filmLanguageExecutionContext.v0.1" or not valid_self(context, "contextHash"):
    raise RuntimeError("CONTEXT")
build_path = args.evidence_root / "build.json"
build = json.loads(build_path.read_text())
if not valid_self(build, "buildHash") or build["plan"]["planHash"] != context["plan"]["planHash"]:
    raise RuntimeError("BUILD")
current_path = Path(bpy.data.filepath)
if sha256_file(current_path) != build["derived"]["sha256"]:
    raise RuntimeError("DERIVED")
scene = bpy.context.scene
if scene.get("bfs_film_language_plan_hash") != context["plan"]["planHash"] or scene.get("bfs_film_language_executor") != VERSION:
    raise RuntimeError("SCENE_BINDING")
parts = sorted((obj for obj in bpy.data.objects if obj.get("bfs_film_language_version") == VERSION), key=lambda obj: obj.name)
expected = build["createdParts"]
if [obj.name for obj in parts] != [row["name"] for row in expected]:
    raise RuntimeError("PART_ROSTER")
zones = sorted({obj.get("bfs_film_language_face_zone") for obj in parts if obj.get("bfs_film_language_face_zone")})
bands = sorted({int(obj.get("bfs_film_language_scale_band")) for obj in parts if obj.get("bfs_film_language_scale_band")})
if zones != ["BROW", "CHEEK", "EYE_LINE", "JAW"] or bands != [1, 2, 3]:
    raise RuntimeError("FILM_LANGUAGE_METADATA")
for obj in parts:
    relief = obj.get("bfs_film_language_relief_ratio")
    coverage = obj.get("bfs_film_language_coverage_ratio")
    if relief is not None and (float(relief) <= 0 or float(relief) > 0.12 + 1e-9):
        raise RuntimeError("RELIEF_CAP")
    if coverage is not None and (float(coverage) <= 0 or float(coverage) > 0.18 + 1e-9):
        raise RuntimeError("COVERAGE_CAP")
observed = protected_state(scene, [row["reviewFrame"] for row in context["shots"]])
if observed != build["protectedStateAfter"]:
    raise RuntimeError("REOPEN_STATE")
audit = write_self(args.evidence_root / "reopen-audit.json", {
    "schemaVersion": "bfs.filmLanguageReopenAudit.v0.1", "experimentId": context["experimentId"], "status": "PASS",
    "build": {"sha256": sha256_file(build_path), "buildHash": build["buildHash"]},
    "derived": {"path": str(current_path), "sha256": build["derived"]["sha256"]},
    "parts": len(parts), "faceZones": zones, "scaleBands": bands, "protectedStateExact": True,
}, "auditHash")
print("BFS_FILM_LANGUAGE_REOPEN", audit["status"], audit["auditHash"], len(parts))
