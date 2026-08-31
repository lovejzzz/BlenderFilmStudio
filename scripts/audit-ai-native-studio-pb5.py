# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent PB.5 source/process/resume/pixel/pass audit; no product-module import."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
import numpy as np
import OpenImageIO as oiio


def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest()
def read_json(path): return json.loads(path.read_text(encoding="utf-8"))
def valid_self(value, field):
    expected = value.get(field); body = dict(value); body.pop(field, None)
    return isinstance(expected, str) and hashlib.sha256(canonical(body)).hexdigest() == expected
def write_exclusive(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try: os.write(descriptor, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()); os.fsync(descriptor)
    finally: os.close(descriptor)


def single_image(path):
    image = oiio.ImageInput.open(str(path)); assert image is not None
    try:
        spec = image.spec(); array = np.asarray(image.read_image(0, 0, 0, spec.nchannels, oiio.FLOAT), dtype=np.float32).reshape(spec.height, spec.width, spec.nchannels); rgb = array[..., :3]
        return {"width": spec.width, "height": spec.height, "channels": list(spec.channelnames), "nonFiniteValues": int(array.size - np.isfinite(array).sum()), "rgbDynamicRange": float(rgb.max() - rgb.min()), "nonzeroRgbPixels": int(np.count_nonzero(np.any(rgb != 0, axis=2))), "decodedSha256": hashlib.sha256(np.ascontiguousarray(array, dtype=np.dtype("<f4")).tobytes()).hexdigest()}
    finally: image.close()


def multilayer(path):
    image = oiio.ImageInput.open(str(path)); assert image is not None
    rows, combined, index = [], None, 0
    try:
        while image.seek_subimage(index, 0):
            spec = image.spec(); names = list(spec.channelnames); passes = sorted({name.split(".")[-2] for name in names if "." in name}); rows.append({"index": index, "width": spec.width, "height": spec.height, "channels": names, "passes": passes, "format": str(spec.format)})
            indices = []
            for suffix in ("Combined.R", "Combined.G", "Combined.B", "Combined.A"):
                matches = [position for position, name in enumerate(names) if name == suffix or name.endswith("." + suffix)]
                if len(matches) != 1: indices = []; break
                indices.append(matches[0])
            if indices:
                array = np.asarray(image.read_image(index, 0, 0, spec.nchannels, oiio.FLOAT), dtype=np.float32).reshape(spec.height, spec.width, spec.nchannels); rgba = np.ascontiguousarray(array[..., indices], dtype=np.dtype("<f4"))
                combined = {"width": spec.width, "height": spec.height, "nonFiniteValues": int(rgba.size - np.isfinite(rgba).sum()), "rgbDynamicRange": float(rgba[..., :3].max() - rgba[..., :3].min()), "nonzeroRgbPixels": int(np.count_nonzero(np.any(rgba[..., :3] != 0, axis=2))), "decodedSha256": hashlib.sha256(rgba.tobytes()).hexdigest()}
            index += 1
    finally: image.close()
    assert combined is not None
    return {"subimages": rows, "passes": sorted({item for row in rows for item in row["passes"]}), "combined": combined}


parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--action")
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--manifest-uri", required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
parser.add_argument("--work-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
root = args.repository_root.resolve(strict=True); evidence = args.evidence_root.resolve(strict=True)
manifest = read_json(root / args.manifest_uri); source = Path(manifest["source"]["absolutePath"]); preview = evidence / "preview/preview.png"; final = evidence / "final/final.exr"
preview_receipt = read_json(evidence / "preview/receipt.json"); final_receipt = read_json(evidence / "final/receipt.json")
decisions = [read_json(path) for path in sorted((evidence / "job-control").glob("*.json"))]
processes = [read_json(path) for path in sorted((evidence / "processes").glob("0[1-3]-*.json"))]
failures = {name: read_json(evidence / "attacks" / name / "failures" / f"{name}.json") for name in ("stale", "forged", "budget")}
preview_pixels = single_image(preview); final_pixels = multilayer(final)
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False); scene = bpy.context.scene
source_checks = {"sha256": sha256_file(source) == manifest["source"]["sha256"], "planHash": scene.get("bfs_plan_hash") == manifest["source"]["planHash"], "semantic": scene.get("bfs_structure_hash") == manifest["source"]["semanticStructureSha256"]}
receipt_checks = {"manifest": valid_self(manifest, "manifestHash"), "preview": valid_self(preview_receipt, "receiptHash") and preview_receipt["output"]["sha256"] == sha256_file(preview), "final": valid_self(final_receipt, "receiptHash") and final_receipt["output"]["sha256"] == sha256_file(final), "decisions": len(decisions) == 3 and all(valid_self(row, "decisionHash") for row in decisions), "processes": len(processes) == 3 and all(valid_self(row, "processHash") for row in processes), "failures": all(valid_self(row, "failureHash") for row in failures.values())}
resume_checks = {"decisionStages": [row["executedStage"] for row in decisions] == ["PREVIEW", "FINAL", "COMPLETE"], "decisionRenderCalls": [row["renderCallsThisDecision"] for row in decisions] == [1, 1, 0], "firstInterrupted": processes[0]["status"] == "INTERRUPTED_ACCEPTED" and processes[0]["exitCode"] == 75, "laterPass": all(row["status"] == "PASS" and row["exitCode"] == 0 for row in processes[1:]), "renderCallsExact": sum(row["payload"]["renderCalls"] for row in processes) == 2, "previewSkippedExact": processes[1]["payload"]["previewSha256Before"] == sha256_file(preview) and processes[2]["payload"]["previewSha256Before"] == sha256_file(preview), "completeNoOp": processes[2]["payload"]["renderCalls"] == 0 and processes[2]["payload"]["finalSha256Before"] == sha256_file(final)}
failure_checks = {"reasons": {name: row["reason"] for name, row in failures.items()} == {"stale": "JOB_EXPIRED", "forged": "PREVIEW_RECEIPT_INVALID", "budget": "RENDER_BUDGET_EXHAUSTED"}, "zeroRenders": all(row["process"]["renderCalls"] == 0 and row["newRenderArtifactsWritten"] == 0 for row in failures.values()), "sourceUnchanged": all(row["source"]["unchanged"] for row in failures.values())}
pixel_checks = {"previewShape": (preview_pixels["width"], preview_pixels["height"]) == (640, 360) and preview.stat().st_size >= 1024, "previewFiniteDynamic": preview_pixels["nonFiniteValues"] == 0 and preview_pixels["rgbDynamicRange"] >= 0.01 and preview_pixels["nonzeroRgbPixels"] >= 1000, "finalShape": (final_pixels["combined"]["width"], final_pixels["combined"]["height"]) == (640, 360) and final.stat().st_size >= 4096, "finalFiniteDynamic": final_pixels["combined"]["nonFiniteValues"] == 0 and final_pixels["combined"]["rgbDynamicRange"] >= 0.01 and final_pixels["combined"]["nonzeroRgbPixels"] >= 1000, "requiredPasses": all(name in final_pixels["passes"] for name in ("Combined", "Depth", "Normal"))}
groups = (source_checks, receipt_checks, resume_checks, failure_checks, pixel_checks); status = "PASS" if all(all(group.values()) for group in groups) else "FAIL"
body = {"schemaVersion": "bfs.pb5IndependentAudit.v0.1", "status": status, "pid": os.getpid(), "independence": "Imports neither film_studio_render nor the product helper and performs zero render calls.", "decoder": {"openImageIO": oiio.VERSION_STRING, "numpy": np.__version__}, "sourceChecks": source_checks, "receiptChecks": receipt_checks, "resumeChecks": resume_checks, "failureChecks": failure_checks, "pixelChecks": pixel_checks, "previewPixels": preview_pixels, "finalPixels": final_pixels, "renderCalls": 0}
record = dict(body); record["auditHash"] = hashlib.sha256(canonical(body)).hexdigest(); write_exclusive(evidence / "independent-audit.json", record)
if status != "PASS": raise RuntimeError("PB.5 independent audit failed")
print("PB5_AUDIT=" + json.dumps({"pid": os.getpid(), "renderCalls": 0, "auditHash": record["auditHash"]}, sort_keys=True), flush=True)
