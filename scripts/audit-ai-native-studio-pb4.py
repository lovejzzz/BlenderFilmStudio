# SPDX-FileCopyrightText: 2026 BlenderFilmStudio Authors
# SPDX-License-Identifier: GPL-2.0-or-later

"""Independent PB.4 pixel/pass/source audit; imports no product render module."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
import numpy
import OpenImageIO as oiio


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root differs: {path}")
    return value


def valid_self(value, field):
    expected = value.get(field)
    body = dict(value)
    body.pop(field, None)
    return isinstance(expected, str) and hashlib.sha256(canonical(body)).hexdigest() == expected


def read_single_image(path):
    image = oiio.ImageInput.open(str(path))
    if image is None:
        raise RuntimeError(f"Cannot open image: {path}")
    try:
        spec = image.spec()
        pixels = image.read_image(0, 0, 0, spec.nchannels, oiio.FLOAT)
        array = numpy.asarray(pixels, dtype=numpy.float32).reshape(spec.height, spec.width, spec.nchannels)
        rgb = array[..., :3]
        return {
            "width": spec.width,
            "height": spec.height,
            "channels": list(spec.channelnames),
            "format": str(spec.format),
            "nonFiniteValues": int(array.size - numpy.isfinite(array).sum()),
            "rgbDynamicRange": float(rgb.max() - rgb.min()),
            "nonzeroRgbPixels": int(numpy.count_nonzero(numpy.any(rgb != 0, axis=2))),
            "decodedSha256": hashlib.sha256(
                numpy.ascontiguousarray(array, dtype=numpy.dtype("<f4")).tobytes()
            ).hexdigest(),
        }
    finally:
        image.close()


def read_multilayer_exr(path):
    image = oiio.ImageInput.open(str(path))
    if image is None:
        raise RuntimeError(f"Cannot open EXR: {path}")
    subimages = []
    combined = None
    try:
        index = 0
        while image.seek_subimage(index, 0):
            spec = image.spec()
            names = list(spec.channelnames)
            passes = sorted({name.split(".")[-2] for name in names if "." in name})
            subimages.append({
                "index": index,
                "width": spec.width,
                "height": spec.height,
                "channels": names,
                "passes": passes,
                "format": str(spec.format),
            })
            suffixes = ["Combined.R", "Combined.G", "Combined.B", "Combined.A"]
            indices = []
            for suffix in suffixes:
                matches = [position for position, name in enumerate(names) if name == suffix or name.endswith(f".{suffix}")]
                if len(matches) != 1:
                    indices = []
                    break
                indices.append(matches[0])
            if indices:
                pixels = image.read_image(index, 0, 0, spec.nchannels, oiio.FLOAT)
                array = numpy.asarray(pixels, dtype=numpy.float32).reshape(spec.height, spec.width, spec.nchannels)
                rgba = numpy.ascontiguousarray(array[..., indices], dtype=numpy.dtype("<f4"))
                combined = {
                    "subimage": index,
                    "width": spec.width,
                    "height": spec.height,
                    "nonFiniteValues": int(rgba.size - numpy.isfinite(rgba).sum()),
                    "rgbDynamicRange": float(rgba[..., :3].max() - rgba[..., :3].min()),
                    "nonzeroRgbPixels": int(numpy.count_nonzero(numpy.any(rgba[..., :3] != 0, axis=2))),
                    "decodedSha256": hashlib.sha256(rgba.tobytes()).hexdigest(),
                }
            index += 1
    finally:
        image.close()
    if combined is None:
        raise RuntimeError("EXR Combined pass missing")
    return {
        "subimages": subimages,
        "passes": sorted({name for row in subimages for name in row["passes"]}),
        "combined": combined,
    }


parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--manifest-uri", required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
parser.add_argument("--source-blend", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

repository = args.repository_root.resolve(strict=True)
evidence = args.evidence_root.resolve(strict=True)
source = args.source_blend.resolve(strict=True)
manifest = read_json(repository / args.manifest_uri)
preview_receipt = read_json(evidence / "preview/receipt.json")
final_receipt = read_json(evidence / "final/receipt.json")
failure_names = ("tampered-manifest", "escaped-output", "final-without-preview")
failures = {name: read_json(evidence / "failures" / f"{name}.json") for name in failure_names}
processes = [read_json(evidence / "processes" / f"0{index}-{name}.json") for index, name in (
    (1, "inspect-negative"),
    (2, "preview"),
    (3, "final"),
)]

preview_path = evidence / preview_receipt["output"]["uri"]
final_path = evidence / final_receipt["output"]["uri"]
preview_pixels = read_single_image(preview_path)
final_pixels = read_multilayer_exr(final_path)

bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
scene = bpy.context.scene
source_sha = sha256_file(source)
source_checks = {
    "blendSha256": source_sha == manifest["source"]["sha256"],
    "planHash": scene.get("bfs_plan_hash") == manifest["source"]["planHash"],
    "semanticStructureSha256": scene.get("bfs_structure_hash") == manifest["source"]["semanticStructureSha256"],
}
receipt_checks = {
    "manifest": valid_self(manifest, "manifestHash") and manifest["status"] == "APPROVED",
    "preview": valid_self(preview_receipt, "receiptHash") and preview_receipt["status"] == "PASS",
    "final": valid_self(final_receipt, "receiptHash") and final_receipt["status"] == "PASS",
    "failures": all(valid_self(value, "failureHash") and value["status"] == "REJECTED" for value in failures.values()),
    "processes": all(valid_self(value, "processHash") and value["status"] == "PASS" for value in processes),
    "outputBindings": preview_receipt["output"]["sha256"] == sha256_file(preview_path)
        and final_receipt["output"]["sha256"] == sha256_file(final_path),
}
process_checks = {
    "exitZero": all(value["exitCode"] == 0 for value in processes),
    "renderCallsExact": sum(value["payload"]["renderCalls"] for value in processes) == 2,
    "negativeBeforeRender": processes[0]["payload"]["renderCalls"] == 0,
    "typedStatePersisted": processes[0]["payload"]["typedStatePersisted"] is True,
    "sourceUnchanged": source_sha == manifest["source"]["sha256"],
}
pixel_checks = {
    "previewDimensionsAndBytes": preview_pixels["width"] == 640 and preview_pixels["height"] == 360 and preview_path.stat().st_size >= 1024,
    "previewFiniteDynamic": preview_pixels["nonFiniteValues"] == 0 and preview_pixels["rgbDynamicRange"] >= 0.01 and preview_pixels["nonzeroRgbPixels"] >= 1000,
    "finalDimensionsAndBytes": final_pixels["combined"]["width"] == 640 and final_pixels["combined"]["height"] == 360 and final_path.stat().st_size >= 4096,
    "finalFiniteDynamic": final_pixels["combined"]["nonFiniteValues"] == 0 and final_pixels["combined"]["rgbDynamicRange"] >= 0.01 and final_pixels["combined"]["nonzeroRgbPixels"] >= 1000,
    "requiredPasses": all(name in final_pixels["passes"] for name in ("Combined", "Depth", "Normal")),
}
failure_checks = {
    "renderCallsZero": all(value["process"]["renderCalls"] == 0 for value in failures.values()),
    "sourceUnchanged": all(value["source"]["unchanged"] is True and value["source"]["sha256BeforeAndAfter"] == source_sha for value in failures.values()),
    "artifactsAbsent": not (evidence.parent / "escaped.png").exists(),
}
all_checks = [source_checks, receipt_checks, process_checks, pixel_checks, failure_checks]
status = "PASS" if all(all(group.values()) for group in all_checks) else "FAIL"
body = {
    "schemaVersion": "bfs.pb4PixelPassAudit.v0.1",
    "status": status,
    "pid": os.getpid(),
    "independence": "This script imports neither film_studio_render nor the product helper and performs zero render calls.",
    "decoder": {"openImageIO": oiio.VERSION_STRING, "numpy": numpy.__version__},
    "sourceChecks": source_checks,
    "receiptChecks": receipt_checks,
    "processChecks": process_checks,
    "pixelChecks": pixel_checks,
    "failureChecks": failure_checks,
    "previewPixels": preview_pixels,
    "finalPixels": final_pixels,
    "renderCalls": 0,
}
record = dict(body)
record["auditHash"] = hashlib.sha256(canonical(body)).hexdigest()
path = evidence / "pixel-pass-audit.json"
descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
try:
    os.write(descriptor, (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode())
    os.fsync(descriptor)
finally:
    os.close(descriptor)
if status != "PASS":
    raise RuntimeError("PB.4 independent pixel/pass audit failed")
print("PB4_AUDIT=" + json.dumps({"pid": os.getpid(), "renderCalls": 0, "auditHash": record["auditHash"]}, sort_keys=True), flush=True)
