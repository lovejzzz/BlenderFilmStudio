# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent F0.5 process, pixel, pass, cost, failure and recovery audit."""

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


SOURCE_SHA = "648ba4e5c0be2620f0da85dd8fdc0a23d878c39054e61e69029221b5457da942"
PLAN_HASH = "316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf"
STRUCTURE_SHA = "e8c55fb73737f1871ac0008faa705dc204ebfe5bac471323cbb0a2d31435b4f8"
PRODUCT_BUILD = "b47eae224b6d"
OCIO_SHA = "24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def valid_self(path, field):
    value = json.loads(path.read_text())
    expected = value.pop(field)
    actual = hashlib.sha256((json.dumps(value, indent=2) + "\n").encode()).hexdigest()
    return expected == actual


def read_single_image(path):
    image = oiio.ImageInput.open(str(path))
    if image is None:
        raise RuntimeError(f"Cannot open image: {path}")
    try:
        spec = image.spec()
        pixels = image.read_image(0, 0, 0, spec.nchannels, oiio.FLOAT)
        array = numpy.asarray(pixels, dtype=numpy.float32).reshape(spec.height, spec.width, spec.nchannels)
        finite = numpy.isfinite(array)
        rgb = array[..., :3]
        return {
            "width": spec.width,
            "height": spec.height,
            "channels": list(spec.channelnames),
            "nonFiniteValues": int(array.size - finite.sum()),
            "rgbDynamicRange": float(rgb.max() - rgb.min()),
            "nonzeroRgbPixels": int(numpy.count_nonzero(numpy.any(rgb != 0, axis=2))),
            "decodedSha256": hashlib.sha256(numpy.ascontiguousarray(array, dtype=numpy.dtype("<f4")).tobytes()).hexdigest(),
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
            subimages.append({"index": index, "width": spec.width, "height": spec.height, "channels": names, "passes": passes, "format": str(spec.format)})
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
    all_passes = sorted({name for row in subimages for name in row["passes"]})
    return {"subimages": subimages, "passes": all_passes, "combined": combined}


parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
root = args.repository_root.resolve(strict=True)
evidence = (root / args.evidence_root).resolve(strict=True)
source = root / "experiments/ai-native-studio-f0/F0.4-2026-08-30-mac-m2max-attempt-03/b01/artifacts/scene.blend"
preview = evidence / "preview/preview.png"
final = evidence / "final/final.exr"

preview_pixels = read_single_image(preview)
final_pixels = read_multilayer_exr(final)
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
scene = bpy.context.scene
source_checks = {
    "blendSha256": digest(source) == SOURCE_SHA,
    "planHash": scene.get("bfs_plan_hash") == PLAN_HASH,
    "semanticStructureSha256": scene.get("bfs_structure_hash") == STRUCTURE_SHA,
    "productBuildHash": scene.get("bfs_product_build_hash") == PRODUCT_BUILD,
    "ocioConfigSha256": scene.get("bfs_ocio_sha256") == OCIO_SHA,
}

job = json.loads((evidence / "job-manifest.json").read_text())
preview_receipt = json.loads((evidence / "preview/receipt.json").read_text())
final_receipt = json.loads((evidence / "final/receipt.json").read_text())
recovery = json.loads((evidence / "recovery.json").read_text())
cost = json.loads((evidence / "cost-receipt.json").read_text())
insufficient = json.loads((evidence / "admissions/00-insufficient-disk.json").read_text())
tampered = json.loads((evidence / "tampered-receipt.json").read_text())
preview_process = json.loads((evidence / "processes/01-preview.json").read_text())
interrupt_process = json.loads((evidence / "processes/02-final-interrupted.json").read_text())
final_process = json.loads((evidence / "processes/03-final-recovery.json").read_text())

receipt_checks = {
    "jobManifest": valid_self(evidence / "job-manifest.json", "manifestHash") and job["status"] == "APPROVED",
    "approval": valid_self(evidence / "approval.json", "approvalHash"),
    "previewReceipt": valid_self(evidence / "preview/receipt.json", "receiptHash") and preview_receipt["status"] == "PASS",
    "finalReceipt": valid_self(evidence / "final/receipt.json", "receiptHash") and final_receipt["status"] == "PASS",
    "recovery": valid_self(evidence / "recovery.json", "recoveryHash") and recovery["status"] == "PASS",
    "cost": valid_self(evidence / "cost-receipt.json", "costHash") and cost["status"] == "PASS",
    "insufficientDisk": valid_self(evidence / "admissions/00-insufficient-disk.json", "admissionHash") and insufficient["status"] == "REJECTED" and insufficient["productStarts"] == 0,
    "tamperedReceipt": valid_self(evidence / "tampered-receipt.json", "negativeHash") and tampered["status"] == "REJECTED" and tampered["additionalProductStarts"] == 0,
    "previewProcess": valid_self(evidence / "processes/01-preview.json", "processHash") and preview_process["status"] == "PASS",
    "interruptedProcess": valid_self(evidence / "processes/02-final-interrupted.json", "processHash") and interrupt_process["status"] == "INTERRUPTED" and interrupt_process["renderCalls"] == 0,
    "finalProcess": valid_self(evidence / "processes/03-final-recovery.json", "processHash") and final_process["status"] == "PASS",
}
process_checks = {
    "previewExitZero": preview_process["exitCode"] == 0,
    "interruptNonzero": interrupt_process["exitCode"] != 0,
    "finalExitZero": final_process["exitCode"] == 0,
    "wallCeilings": all(row["timing"]["realSeconds"] <= 120 for row in (preview_process, interrupt_process, final_process)),
    "rssCeilings": all(row["timing"]["maximumResidentSetSizeBytes"] <= 8589934592 for row in (preview_process, interrupt_process, final_process)),
    "renderCallsExact": preview_process["renderCalls"] + interrupt_process["renderCalls"] + final_process["renderCalls"] == 2,
    "sourceNeverSaved": digest(source) == SOURCE_SHA,
}
pixel_checks = {
    "previewSize": preview_pixels["width"] == 640 and preview_pixels["height"] == 360 and preview.stat().st_size >= 1024,
    "previewFiniteDynamic": preview_pixels["nonFiniteValues"] == 0 and preview_pixels["rgbDynamicRange"] >= 0.01 and preview_pixels["nonzeroRgbPixels"] >= 1000,
    "finalSize": final_pixels["combined"]["width"] == 640 and final_pixels["combined"]["height"] == 360 and final.stat().st_size >= 4096,
    "finalFiniteDynamic": final_pixels["combined"]["nonFiniteValues"] == 0 and final_pixels["combined"]["rgbDynamicRange"] >= 0.01 and final_pixels["combined"]["nonzeroRgbPixels"] >= 1000,
    "requiredPasses": all(name in final_pixels["passes"] for name in ("Combined", "Depth", "Normal")),
    "receiptOutputBindings": preview_receipt["output"]["sha256"] == digest(preview) and final_receipt["output"]["sha256"] == digest(final),
}
recovery_checks = {
    "previewVerifiedAndSkipped": recovery["previewReceiptVerified"] and recovery["previewRerenderCount"] == 0,
    "interruptionBeforeRender": recovery["interruptionVerified"] and recovery["interruptedRenderCalls"] == 0 and recovery["interruptedFinalArtifactAbsent"],
    "tamperingRejectedBeforeStart": recovery["tamperedReceiptRejected"] and tampered["additionalProductStarts"] == 0,
    "onlyFinalRecovered": recovery["recoveredStages"] == ["FINAL"] and recovery["finalRenderCalls"] == 1,
}
resource_checks = {
    "formalOutputCeiling": cost["formalOutputBytes"] <= 268435456,
    "positiveAdmissions": all(json.loads(path.read_text())["status"] == "ACCEPTED" for path in sorted((evidence / "admissions").glob("0[1-4]-*.json"))),
    "maximumConcurrent": cost["maximumConcurrentNativeProcesses"] == 1,
    "productStarts": cost["formalProductStarts"] == 4,
    "rendererStarts": cost["rendererStarts"] == 3,
}

body = {
    "schemaVersion": "bfs.f0.5.independentAudit.v0.1",
    "status": "PASS" if all(source_checks.values()) and all(receipt_checks.values()) and all(process_checks.values()) and all(pixel_checks.values()) and all(recovery_checks.values()) and all(resource_checks.values()) else "FAIL",
    "formalProductStart": 4,
    "independence": "Imports neither render-stage.py nor run-f05.mjs and performs zero render calls.",
    "decoder": {"openImageIO": oiio.VERSION_STRING, "numpy": numpy.__version__},
    "sourceChecks": source_checks,
    "receiptChecks": receipt_checks,
    "processChecks": process_checks,
    "pixelChecks": pixel_checks,
    "recoveryChecks": recovery_checks,
    "resourceChecks": resource_checks,
    "previewPixels": preview_pixels,
    "finalPixels": final_pixels,
    "renderCalls": 0,
}
record = {**body, "auditHash": hashlib.sha256(canonical(body).encode()).hexdigest()}
path = evidence / "audit.json"
descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
try:
    os.write(descriptor, (json.dumps(record, indent=2) + "\n").encode())
    os.fsync(descriptor)
finally:
    os.close(descriptor)
if body["status"] != "PASS":
    raise RuntimeError("F0.5 independent audit failed")
print("F05_AUDIT_PASS preview=1 final=1 interruption=1 attacks=2 renderCalls=0", flush=True)
