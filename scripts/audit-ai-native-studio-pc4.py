#!/usr/bin/env python3
"""Reopen and independently audit the PC.4 hero redesign derivative."""

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


def inspect_image(path):
    image = oiio.ImageInput.open(str(path))
    if image is None:
        raise RuntimeError("IMAGE_OPEN")
    try:
        spec = image.spec()
        pixels = np.asarray(image.read_image(format=oiio.FLOAT), dtype=np.float32)
        return {"width": spec.width, "height": spec.height, "channels": spec.nchannels, "finite": bool(np.isfinite(pixels).all()), "sha256": sha256_file(path), "bytes": path.stat().st_size}
    finally:
        image.close()


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--spec", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
parser.add_argument("--work-root", type=Path, required=True)
args = parser.parse_args(argv)
spec = json.loads(args.spec.read_text(encoding="utf-8"))
build_path = args.evidence_root / "build.json"
build = json.loads(build_path.read_text(encoding="utf-8"))
checks = []


def gate(identifier, passed, detail):
    checks.append({"id": identifier, "pass": bool(passed), "detail": detail})


gate("SPEC_SELF_HASH", valid_self(spec, "specHash"), spec.get("specHash"))
gate("BUILD_SELF_HASH", valid_self(build, "buildHash"), build.get("buildHash"))
current_path = Path(bpy.data.filepath)
gate("DERIVED_PATH", current_path.resolve() == Path(build["derived"]["path"]).resolve(), str(current_path))
gate("DERIVED_HASH", sha256_file(current_path) == build["derived"]["sha256"], sha256_file(current_path))
gate("SOURCE_HASH", sha256_file(Path(spec["source"]["path"])) == spec["source"]["sha256"], sha256_file(Path(spec["source"]["path"])))
collection = bpy.data.collections.get("PC4_HERO_REDESIGN")
roster = sorted(obj.name for obj in collection.objects) if collection else []
gate("CREATED_PART_ROSTER", roster == sorted(spec["createdParts"]), {"count": len(roster)})
gate("CREATED_PART_FLOOR", len(roster) >= spec["acceptance"]["minimumCreatedParts"], len(roster))
hidden_legacy = [name for name in spec["legacyHeroObjectsToHide"] if name in bpy.data.objects and bpy.data.objects[name].hide_render]
hidden_occluders = [name for name in spec["foregroundOccludersToHide"] if name in bpy.data.objects and bpy.data.objects[name].hide_render]
gate("LEGACY_HIDDEN", hidden_legacy == spec["legacyHeroObjectsToHide"], len(hidden_legacy))
gate("OCCLUDERS_HIDDEN", hidden_occluders == spec["foregroundOccludersToHide"], len(hidden_occluders))
gate("MATERIAL_ROSTER", sorted(name for name in spec["materialRegions"] if name in bpy.data.materials) == sorted(spec["materialRegions"]), spec["materialRegions"])
gate("SCENE_SPEC_BINDING", bpy.context.scene.get("bfs_pc4_spec_hash") == spec["specHash"], bpy.context.scene.get("bfs_pc4_spec_hash"))
protected = camera_light_state(bpy.context.scene)
gate("CAMERA_LIGHT_STATE", protected == build["protectedStateAfter"] == build["protectedStateBefore"], len(protected))
gate("PERFORMANCE_PHASES", sorted(build["performancePhases"]) == sorted(spec["performancePhases"]), build["performancePhases"])
gate("ANIMATED_TARGET_FLOOR", len(build["animatedTargets"]) >= spec["acceptance"]["minimumAnimatedTargets"], len(build["animatedTargets"]))
images = []
for view in spec["protectedViews"]:
    path = args.evidence_root / "derived" / f"frame-{view['frame']:04d}.png"
    result = inspect_image(path)
    images.append({"frame": view["frame"], **result})
    gate(f"FRAME_{view['frame']}_FINITE_640X360", result["width"] == 640 and result["height"] == 360 and result["channels"] in (3, 4) and result["finite"], result)
    expected = next(row["derived"] for row in build["screenshots"] if row["frame"] == view["frame"])
    gate(f"FRAME_{view['frame']}_HASH", result["sha256"] == expected["sha256"], result["sha256"])
retained_exr = sorted(path.as_posix() for root in (args.evidence_root, args.work_root) for path in root.rglob("*.exr"))
gate("ZERO_RETAINED_EXR", retained_exr == [], retained_exr)
passed = sum(1 for row in checks if row["pass"])
if passed != len(checks):
    raise RuntimeError(f"AUDIT_{passed}_OF_{len(checks)}")
record = write_self(args.evidence_root / "audit.json", {
    "schemaVersion": "bfs.pc4HeroRedesignAudit.v0.1",
    "status": "MACHINE_PASS_VISUAL_REVIEW_REQUIRED",
    "gate": "PC.4",
    "checkPassed": passed,
    "checkTotal": len(checks),
    "checks": checks,
    "screenshots": images,
    "createdParts": len(roster),
    "sceneCounts": {"objects": len(bpy.data.objects), "meshes": len([obj for obj in bpy.data.objects if obj.type == "MESH"]), "polygons": sum(len(obj.data.polygons) for obj in bpy.data.objects if obj.type == "MESH")},
    "operations": {"BlenderStarts": 1, "renderCalls": 0, "sceneSaves": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0},
}, "auditHash")
print("PC4_AUDIT=" + json.dumps({"status": record["status"], "auditHash": record["auditHash"], "checks": f"{passed}/{len(checks)}"}, sort_keys=True), flush=True)
