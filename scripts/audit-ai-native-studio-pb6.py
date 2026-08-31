#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent PB.6 audit; imports neither product render module nor helper."""

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


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def valid_self(value, field):
    expected = value.get(field)
    body = dict(value)
    body.pop(field, None)
    return isinstance(expected, str) and hashlib.sha256(canonical(body)).hexdigest() == expected


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def decode(path):
    image_input = oiio.ImageInput.open(str(path))
    if image_input is None:
        raise RuntimeError(f"Cannot decode {path}")
    try:
        spec = image_input.spec()
        pixels = np.asarray(image_input.read_image(format=oiio.FLOAT), dtype=np.float32).reshape(spec.height, spec.width, spec.nchannels)
    finally:
        image_input.close()
    rgb = pixels[:, :, :3]
    return {
        "width": spec.width,
        "height": spec.height,
        "channels": spec.nchannels,
        "finite": bool(np.isfinite(pixels).all()),
        "dynamicRange": float(np.max(rgb) - np.min(rgb)),
        "nonzeroRgbPixels": int(np.count_nonzero(np.any(rgb != 0.0, axis=2))),
        "decodedSha256": hashlib.sha256(pixels.tobytes(order="C")).hexdigest(),
    }


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--action")
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--manifest-uri", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    return parser.parse_args(argv)


args = parse_args()
root = args.repository_root.resolve()
evidence = args.evidence_root.resolve()
manifest = read_json(root / args.manifest_uri)
source = Path(manifest["source"]["absolutePath"])

shots = [
    {"id": "WIDE", "framesInclusive": [1, 96], "camera": "CAM_WIDE_APPROACH"},
    {"id": "MEDIUM", "framesInclusive": [97, 192], "camera": "CAM_MEDIUM_CONTACT"},
    {"id": "CLOSE", "framesInclusive": [193, 288], "camera": "CAM_CLOSE_MOTION_TERMINAL"},
]
shot_receipts = {shot["id"]: read_json(evidence / "shots" / shot["id"].lower() / "receipt.json") for shot in shots}
slice_receipt = read_json(evidence / "slice" / "receipt.json")
processes = [read_json(evidence / "processes" / f"0{index}-{name}.json") for index, name in ((1, "inspect"), (2, "render"), (3, "reopen"))]
failures = {name: read_json(evidence / "attacks" / name / "failures" / f"{name}.json") for name in ("tampered-source", "shot-overlap", "shared-identity", "boundary-removed", "threshold-relaxed")}

frame_rows = []
decoded = {}
for shot in shots:
    receipt = shot_receipts[shot["id"]]
    if not valid_self(receipt, "receiptHash"):
        raise RuntimeError(f"Invalid {shot['id']} receipt")
    for row in receipt["frames"]:
        path = evidence / row["uri"]
        if not path.is_file() or path.is_symlink() or sha256_file(path) != row["sha256"] or path.stat().st_size != row["bytes"]:
            raise RuntimeError(f"Frame binding differs: {row['frame']}")
        metrics = decode(path)
        if metrics["width"] != 640 or metrics["height"] != 360 or metrics["channels"] != 4 or not metrics["finite"] or metrics["dynamicRange"] <= 0.01 or metrics["nonzeroRgbPixels"] == 0:
            raise RuntimeError(f"Frame pixels rejected: {row['frame']}")
        decoded[row["frame"]] = metrics
        frame_rows.append(row)

expected_frames = list(range(1, 289))
roster_exact = [row["frame"] for row in frame_rows] == expected_frames
camera_exact = all(row["camera"] == next(shot["camera"] for shot in shots if shot["framesInclusive"][0] <= row["frame"] <= shot["framesInclusive"][1]) for row in frame_rows)
per_shot_distinct = {shot["id"]: len({decoded[frame]["decodedSha256"] for frame in range(shot["framesInclusive"][0], shot["framesInclusive"][1] + 1)}) for shot in shots}
not_frozen = all(count >= 24 for count in per_shot_distinct.values()) and decoded[96]["decodedSha256"] != decoded[97]["decodedSha256"] and decoded[192]["decodedSha256"] != decoded[193]["decodedSha256"]

video = evidence / manifest["reviewProfile"]["reviewVideo"]
video_receipt = read_json(evidence / "review" / "video.json")
ffprobe = read_json(evidence / "review" / "ffprobe.json")
sheet = evidence / "review" / "contact-sheet.png"
sheet_metrics = decode(sheet)
video_exact = valid_self(video_receipt, "videoHash") and video.is_file() and video.stat().st_size == video_receipt["bytes"] and sha256_file(video) == video_receipt["sha256"]
metadata_exact = ffprobe.get("width") == 640 and ffprobe.get("height") == 360 and ffprobe.get("frames") == 288 and ffprobe.get("fps") == "24/1"

expected_reasons = {
    "tampered-source": "SOURCE_HASH_MISMATCH",
    "shot-overlap": "SHOT_ROSTER_INVALID",
    "shared-identity": "SHARED_IDENTITY_MISMATCH",
    "boundary-removed": "HISTORICAL_BOUNDARY_MISSING",
    "threshold-relaxed": "HUMAN_BOUNDARY_MUTATED",
}
failure_exact = all(valid_self(failures[name], "failureHash") and failures[name]["reason"] == reason and failures[name]["process"]["renderCalls"] == 0 and failures[name]["source"]["unchanged"] and failures[name]["newRenderArtifactsWritten"] == 0 for name, reason in expected_reasons.items())

scene = bpy.context.scene
source_runtime = all(scene.timeline_markers.get(marker) is not None for marker in ("SHOT_WIDE_APPROACH", "SHOT_MEDIUM_CONTACT", "SHOT_CLOSE_REFLECTION"))
checks = {
    "manifestSelfHash": valid_self(manifest, "manifestHash"),
    "sourceExactUnchanged": sha256_file(source) == manifest["source"]["sha256"],
    "sourceRuntime": source_runtime,
    "sliceReceipt": valid_self(slice_receipt, "receiptHash") and slice_receipt["frames"]["count"] == 288 and slice_receipt["process"]["renderCalls"] == 288,
    "shotReceipts": len(shot_receipts) == 3 and all(valid_self(value, "receiptHash") for value in shot_receipts.values()),
    "frameRoster": roster_exact and len(frame_rows) == 288,
    "cameraRouting": camera_exact,
    "pixelsFiniteDynamic": len(decoded) == 288,
    "sequenceNotFrozen": not_frozen,
    "historicalRejectionRetained": manifest["historicalFrame288Boundary"] == {"verdict": "B62_CLOSE_CAMERA_CORRECTION_FAILS_FROZEN_HOLDOUT", "frame": 288, "metric": "clampedUnionAreaFraction", "observed": 0.93378717684983, "maximum": 0.9, "mustRemainRejected": True},
    "processes": all(valid_self(value, "processHash") and value["status"] == "PASS" for value in processes) and [value["payload"]["renderCalls"] for value in processes] == [0, 288, 0],
    "attacks": failure_exact,
    "video": video_exact and metadata_exact,
    "contactSheet": sheet.is_file() and sheet_metrics["width"] == 1920 and sheet_metrics["height"] == 360 and sheet_metrics["finite"],
    "humanPending": slice_receipt["humanReviewStatus"] == "PENDING_UNTIL_PB7",
}
body = {
    "schemaVersion": "bfs.pb6IndependentAudit.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "pid": os.getpid(),
    "independence": "Imports neither film_studio_render nor the PB.6 product helper; performs zero render calls.",
    "decoder": {"openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
    "checks": checks,
    "frames": {"count": len(decoded), "perShotDistinctDecoded": per_shot_distinct, "cut96To97Differs": decoded[96]["decodedSha256"] != decoded[97]["decodedSha256"], "cut192To193Differs": decoded[192]["decodedSha256"] != decoded[193]["decodedSha256"]},
    "review": {"videoSha256": sha256_file(video), "videoBytes": video.stat().st_size, "contactSheetSha256": sha256_file(sheet)},
    "operations": {"renderCalls": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0},
}
body["auditHash"] = hashlib.sha256(canonical(body)).hexdigest()
path = evidence / "independent-audit.json"
with path.open("x", encoding="utf-8") as handle:
    json.dump(body, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())
print("PB6_AUDIT=" + json.dumps({"status": body["status"], "auditHash": body["auditHash"], "pid": os.getpid(), "renderCalls": 0}, sort_keys=True), flush=True)
if body["status"] != "PASS":
    raise RuntimeError("PB.6 independent audit failed")
