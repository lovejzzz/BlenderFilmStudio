#!/usr/bin/env python3
"""Reopen the accepted PC.2 scene and audit PC.3 frames against PB.6 baseline A."""

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


SENTINELS = (1, 48, 96, 97, 144, 192, 193, 240, 288)
def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
def normalize(value):
    if isinstance(value, float) and math.isfinite(value) and value.is_integer(): return int(value)
    if isinstance(value, list): return [normalize(item) for item in value]
    if isinstance(value, dict): return {key: normalize(item) for key, item in value.items()}
    return value
def hash_value(value): return hashlib.sha256(canonical(normalize(value))).hexdigest()
def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
def valid_self(value, field):
    body = dict(value); expected = body.pop(field, None)
    return expected == hash_value(body)
def write_self(path, value, field):
    body = normalize(dict(value)); body[field] = hash_value(body)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try: os.write(descriptor, (json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode()); os.fsync(descriptor)
    finally: os.close(descriptor)
    return body
def rounded(values): return [round(float(value), 9) for value in values]


def camera_light_state(scene):
    cameras = sorted((obj for obj in bpy.data.objects if obj.type == "CAMERA"), key=lambda item: item.name); lights = sorted((obj for obj in bpy.data.objects if obj.type == "LIGHT"), key=lambda item: item.name); rows = []
    for frame in SENTINELS:
        scene.frame_set(frame); rows.append({"frame": frame, "cameras": {obj.name: {"matrixWorld": [rounded(row) for row in obj.matrix_world], "lens": round(float(obj.data.lens), 9)} for obj in cameras}, "lights": {obj.name: {"matrixWorld": [rounded(row) for row in obj.matrix_world], "energy": round(float(obj.data.energy), 9), "color": rounded(obj.data.color)} for obj in lights}})
    return rows


def read_rgba(path):
    image = oiio.ImageInput.open(str(path))
    if image is None: raise RuntimeError(f"IMAGE_OPEN_{path}")
    try:
        spec = image.spec(); pixels = np.asarray(image.read_image(format=oiio.FLOAT), dtype=np.float32).reshape(spec.height, spec.width, spec.nchannels)
        if (spec.width, spec.height) != (640, 360) or spec.nchannels not in (3, 4) or not np.isfinite(pixels).all(): raise RuntimeError("IMAGE_CONTRACT")
        return pixels[:, :, :3]
    finally: image.close()


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser(); parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--evidence-root", type=Path, required=True); parser.add_argument("--work-root", type=Path, required=True); args = parser.parse_args(argv)
spec = json.loads(args.spec.read_text(encoding="utf-8")); render = json.loads((args.evidence_root / "render.json").read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or not valid_self(render, "renderHash"): raise RuntimeError("SELF_HASH")
source = Path(bpy.data.filepath)
if sha256_file(source) != spec["source"]["sha256"] or bpy.context.scene.get("bfs_pc2_spec_hash") != "48bdfa56a480f25b2a894d66edb3fdea3d3037ae2e2ff2e03e2d66a5b74e830e": raise RuntimeError("SOURCE")
pc2_build_path = Path("experiments/ai-native-studio-post-pb7/PC.2-2026-08-31-mac-m2max-attempt-02/build.json")
if sha256_file(pc2_build_path) != "4608a64efb2c6201e7e5e0f6467789796bd7e30738f62ea471f171ff589dd4c9": raise RuntimeError("PC2_BUILD")
pc2_build = json.loads(pc2_build_path.read_text(encoding="utf-8"))
if camera_light_state(bpy.context.scene) != pc2_build["protectedStateAfter"]: raise RuntimeError("PROTECTED_STATE")

if len(render["frames"]) != 288: raise RuntimeError("FRAME_ROSTER")
hashes = []; metrics = []; dynamic_pairs = 0; previous = None
threshold = spec["machineAcceptance"]["visibleDifferenceRgbThreshold"]
for index, row in enumerate(render["frames"], start=1):
    expected_camera = "CAM_WIDE_APPROACH" if index <= 96 else "CAM_MEDIUM_CONTACT" if index <= 192 else "CAM_CLOSE_MOTION_TERMINAL"
    current_path = args.evidence_root / "frames" / f"frame-{index:04d}.png"; baseline_path = Path(spec["baselineA"]["framesRoot"]) / f"frame-{index:04d}.png"
    if row["frame"] != index or row["camera"] != expected_camera or row["sha256"] != sha256_file(current_path) or row["bytes"] != current_path.stat().st_size: raise RuntimeError("FRAME_BINDING")
    current = read_rgba(current_path); baseline = read_rgba(baseline_path); delta = np.abs(current - baseline)
    fraction = float(np.mean(np.any(delta > threshold, axis=2))); mad = float(np.mean(delta))
    metrics.append({"frame": index, "changedPixelFractionRgbThreshold2Of255": fraction, "meanAbsoluteRgbDifference": mad, "passesVisibleDifference": fraction >= spec["machineAcceptance"]["minimumChangedPixelFractionPerPassingFrame"]})
    if previous is not None and float(np.mean(np.abs(current - previous))) > 1e-5: dynamic_pairs += 1
    previous = current; hashes.append(row["sha256"])
passing = sum(row["passesVisibleDifference"] for row in metrics); median_mad = float(np.median([row["meanAbsoluteRgbDifference"] for row in metrics]))
if len(set(hashes)) < spec["machineAcceptance"]["minimumUniqueFrameHashes"] or dynamic_pairs < spec["machineAcceptance"]["minimumDynamicConsecutivePairs"] or passing < spec["machineAcceptance"]["minimumFramesVisiblyDifferentFromBaselineA"] or median_mad < spec["machineAcceptance"]["minimumMedianMeanAbsoluteRgbDifference"]: raise RuntimeError("PIXEL_FLOORS")
media = [path for root in (args.evidence_root, args.work_root) for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".exr"]
if media: raise RuntimeError("EXR_RESIDUE")
audit = write_self(args.evidence_root / "semantic-audit.json", {"schemaVersion": "bfs.pc3SemanticPixelAudit.v0.1", "status": "PASS", "gate": "PC.3", "source": {"path": str(source), "sha256": sha256_file(source)}, "frameCount": len(metrics), "uniqueFrameHashes": len(set(hashes)), "dynamicConsecutivePairs": dynamic_pairs, "visiblyDifferentFrames": passing, "medianMeanAbsoluteRgbDifference": median_mad, "pixelMetrics": metrics, "protectedStateMatchesPc2": True, "temporaryExrRetained": 0, "operations": {"BlenderStarts": 1, "renderCalls": 0, "sceneSaves": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0}}, "auditHash")
print("PC3_AUDIT=" + json.dumps({"status": audit["status"], "auditHash": audit["auditHash"], "visiblyDifferentFrames": passing}, sort_keys=True), flush=True)
