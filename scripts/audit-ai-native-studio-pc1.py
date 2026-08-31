#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent semantic and pixel auditor for the frozen PC.1 derivative."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
import numpy as np


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


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


def load_pixels(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        width, height = image.size
        pixels = np.asarray(image.pixels[:], dtype=np.float32).reshape(height, width, 4)
        return pixels
    finally:
        bpy.data.images.remove(image)


def action_state():
    rows = []
    for action in sorted(bpy.data.actions, key=lambda item: item.name):
        curves = []
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    curves.extend(channelbag.fcurves)
        rows.append({"name": action.name, "fcurves": len(curves), "keyframes": sum(len(curve.keyframe_points) for curve in curves)})
    return rows


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
    raise RuntimeError("BINDING")
expected = sorted(spec["semanticDetailComponents"])
observed = sorted(obj.name for obj in bpy.data.objects if obj.get("bfs_pc1_detail_id"))
detail_rows = []
for name in observed:
    obj = bpy.data.objects[name]
    detail_rows.append({
        "id": name,
        "semanticIdExact": obj.get("bfs_pc1_detail_id") == name,
        "category": obj.get("bfs_pc1_category"),
        "materialRegion": obj.get("bfs_pc1_material_region"),
        "polygons": len(obj.data.polygons) if obj.type == "MESH" else 0,
    })
materials = []
for name in spec["materialRegions"]:
    material = bpy.data.materials.get(name)
    materials.append({"name": name, "exists": material is not None, "nodeCount": len(material.node_tree.nodes) if material and material.use_nodes else 0})
pixel_rows = []
for view in spec["protectedViews"]:
    baseline = load_pixels(args.evidence_root / "baseline" / f"frame-{view['frame']:04d}.png")
    derived = load_pixels(args.evidence_root / "derived" / f"frame-{view['frame']:04d}.png")
    if baseline.shape != derived.shape:
        raise RuntimeError("IMAGE_SHAPE")
    difference = np.abs(derived[:, :, :3] - baseline[:, :, :3])
    changed = float(np.any(difference > (2.0 / 255.0), axis=2).mean())
    mean = float(difference.mean())
    pixel_rows.append({
        "id": view["id"],
        "frame": view["frame"],
        "changedPixelFractionRgbThreshold2Of255": changed,
        "meanAbsoluteRgbDifference": mean,
        "passesVisibleChange": changed >= spec["acceptance"]["visibleChangePerView"]["minimumChangedPixelFractionRgbThreshold2Of255"] and mean >= spec["acceptance"]["visibleChangePerView"]["minimumMeanAbsoluteRgbDifference"],
    })
checks = {
    "exactDetailRoster": observed == expected,
    "semanticMetadata": all(row["semanticIdExact"] and row["category"] and row["materialRegion"] and row["polygons"] > 0 for row in detail_rows),
    "minimumDetails": len(observed) >= spec["acceptance"]["minimumNewSemanticDetailComponents"],
    "materialRegions": len(materials) >= spec["acceptance"]["minimumNewHeroMaterialRegions"] and all(row["exists"] and row["nodeCount"] >= 4 for row in materials),
    "countsIncrease": len(bpy.data.objects) > spec["baseline"]["counts"]["objects"] and sum(len(obj.data.polygons) for obj in bpy.data.objects if obj.type == "MESH") > spec["baseline"]["counts"]["polygons"],
    "protectedStateExact": build["protectedStateBefore"] == build["protectedStateAfter"],
    "actionsExact": build["actionsBefore"] == build["actionsAfter"] == action_state(),
    "visibleViews": sum(row["passesVisibleChange"] for row in pixel_rows) >= spec["acceptance"]["minimumProtectedViewsWithVisibleChange"],
}
record = write_self(args.evidence_root / "semantic-audit.json", {
    "schemaVersion": "bfs.pc1SemanticPixelAudit.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "detailRows": detail_rows,
    "materials": materials,
    "pixelMetrics": pixel_rows,
    "derivedCounts": {"objects": len(bpy.data.objects), "meshes": len([obj for obj in bpy.data.objects if obj.type == "MESH"]), "polygons": sum(len(obj.data.polygons) for obj in bpy.data.objects if obj.type == "MESH")},
    "operations": {"BlenderStarts": 1, "renderCalls": 0, "sceneSaves": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0},
}, "auditHash")
if record["status"] != "PASS":
    raise RuntimeError("SEMANTIC_AUDIT_FAIL_" + "_".join(key for key, value in checks.items() if not value))
print("PC1_SEMANTIC_AUDIT=" + json.dumps({"status": record["status"], "auditHash": record["auditHash"]}, sort_keys=True), flush=True)
