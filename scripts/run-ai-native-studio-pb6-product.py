#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Product-side PB.6 actions executed by the built Film Studio Engine."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
import numpy as np
import OpenImageIO as oiio
import film_studio_render


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def self_hashed(value, field):
    body = dict(value)
    body.pop(field, None)
    body[field] = hashlib.sha256(canonical(body)).hexdigest()
    return body


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def configure_state(args):
    state = bpy.context.scene.film_studio
    state.slice_repository_root = str(args.repository_root)
    state.slice_manifest_uri = args.manifest_uri
    state.slice_evidence_root = str(args.evidence_root)
    return state


def operator_result(name, result):
    if "FINISHED" not in result:
        raise RuntimeError(f"{name} failed: {sorted(result)}")


def contact_sheet(evidence):
    sources = [evidence / "frames" / f"frame-{frame:04d}.png" for frame in (48, 144, 288)]
    images = []
    for source in sources:
        image_input = oiio.ImageInput.open(str(source))
        if image_input is None:
            raise RuntimeError(f"Cannot open {source}")
        try:
            spec = image_input.spec()
            pixels = np.asarray(image_input.read_image(format=oiio.FLOAT), dtype=np.float32).reshape(spec.height, spec.width, spec.nchannels)
        finally:
            image_input.close()
        images.append(np.clip(pixels[:, :, :4], 0.0, 1.0))
    combined = np.concatenate(images, axis=1)
    output = evidence / "review" / "contact-sheet.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = oiio.ImageOutput.create(str(output))
    if writer is None:
        raise RuntimeError("Cannot create contact sheet")
    spec = oiio.ImageSpec(combined.shape[1], combined.shape[0], 4, oiio.UINT8)
    if not writer.open(str(output), spec):
        raise RuntimeError("Cannot open contact-sheet output")
    try:
        writer.write_image((combined * 255.0 + 0.5).astype(np.uint8))
    finally:
        writer.close()
    return output


def inspect_action(args):
    state = configure_state(args)
    operator_result("inspect", bpy.ops.film_studio.inspect_vertical_slice())
    expected = "PASS_REVIEW_READY" if args.expect_complete else "APPROVED_READY"
    if state.slice_status != expected:
        raise RuntimeError(f"Unexpected slice status: {state.slice_status}")
    return {
        "status": state.slice_status,
        "sliceId": state.slice_id,
        "manifestHash": state.slice_manifest_hash,
        "sharedIdentity": state.slice_shared_identity,
        "historicalBoundary": state.slice_historical_boundary,
        "currentShot": state.slice_current_shot,
        "completedFrames": state.slice_completed_frames,
        "lastReceiptHash": state.slice_last_receipt_hash,
        "pid": os.getpid(),
        "renderCalls": 0,
    }


def render_action(args):
    state = configure_state(args)
    operator_result("inspect", bpy.ops.film_studio.inspect_vertical_slice())
    if state.slice_status != "APPROVED_READY" or not state.slice_inspection_token:
        raise RuntimeError("Slice is not approved for first execution")
    operator_result("render", bpy.ops.film_studio.build_vertical_slice_review())
    sheet = contact_sheet(args.evidence_root)
    return {
        "status": state.slice_status,
        "sliceId": state.slice_id,
        "completedFrames": state.slice_completed_frames,
        "currentShot": state.slice_current_shot,
        "receiptHash": state.slice_last_receipt_hash,
        "contactSheet": str(sheet.relative_to(args.evidence_root)),
        "pid": os.getpid(),
        "renderCalls": 288,
    }


def attack_manifest(base, name, evidence):
    value = json.loads(json.dumps(base))
    value["authorizedEvidenceRoot"] = str(evidence)
    if name == "tampered-source":
        value["source"]["sha256"] = "0" * 64
    elif name == "shot-overlap":
        value["shots"][1]["framesInclusive"][0] = 96
    elif name == "shared-identity":
        value["sharedNonCameraIdentity"]["assetIdentityHashes"]["CHAR_B62_GUARDIAN"] = "f" * 64
    elif name == "boundary-removed":
        del value["historicalFrame288Boundary"]
    elif name == "threshold-relaxed":
        value["historicalFrame288Boundary"]["maximum"] = 0.91
    else:
        raise RuntimeError(name)
    return self_hashed(value, "manifestHash")


def negative_action(args):
    base = json.loads((args.repository_root / args.manifest_uri).read_text(encoding="utf-8"))
    expected = {
        "tampered-source": "SOURCE_HASH_MISMATCH",
        "shot-overlap": "SHOT_ROSTER_INVALID",
        "shared-identity": "SHARED_IDENTITY_MISMATCH",
        "boundary-removed": "HISTORICAL_BOUNDARY_MISSING",
        "threshold-relaxed": "HUMAN_BOUNDARY_MUTATED",
    }
    results = []
    for name, reason in expected.items():
        evidence = args.evidence_root / "attacks" / name
        evidence.mkdir(parents=True)
        manifest_path = evidence / "manifest.json"
        write_exclusive(manifest_path, attack_manifest(base, name, evidence))
        manifest_uri = manifest_path.relative_to(args.repository_root).as_posix()
        try:
            film_studio_render.inspect_vertical_slice_with_failure_receipt(
                args.repository_root, manifest_uri, evidence, name,
            )
        except film_studio_render.RenderContractError as error:
            if error.reason != reason:
                raise RuntimeError(f"{name}: {error.reason} != {reason}") from error
            results.append({"id": name, "reason": reason, "renderCalls": 0})
        else:
            raise RuntimeError(f"Attack unexpectedly passed: {name}")
    return {"status": "PASS", "attacks": results, "pid": os.getpid(), "renderCalls": 0}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=("INSPECT", "RENDER", "REOPEN", "NEGATIVE"), required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--manifest-uri", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--expect-complete", action="store_true")
    return parser.parse_args(argv)


args = parse_args()
if args.action == "INSPECT":
    payload = inspect_action(args)
elif args.action == "RENDER":
    payload = render_action(args)
elif args.action == "REOPEN":
    args.expect_complete = True
    payload = inspect_action(args)
else:
    payload = negative_action(args)
print("PB6_PRODUCT=" + json.dumps(payload, sort_keys=True), flush=True)
