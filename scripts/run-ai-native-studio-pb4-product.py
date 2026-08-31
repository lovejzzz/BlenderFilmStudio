# SPDX-FileCopyrightText: 2026 BlenderFilmStudio Authors
# SPDX-License-Identifier: GPL-2.0-or-later

"""PB.4 product-process helper: one bounded action per Blender start."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
import film_studio_render


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def self_hashed(value, field):
    body = dict(value)
    body.pop(field, None)
    body[field] = hashlib.sha256(canonical(body)).hexdigest()
    return body


def expect_rejection(function, reasons):
    try:
        function()
    except film_studio_render.RenderContractError as error:
        if error.reason not in reasons:
            raise RuntimeError(f"Unexpected rejection reason: {error.reason}") from error
        return error.reason
    raise RuntimeError("Negative control unexpectedly succeeded")


def inspect_and_negative(args, render_events):
    source = Path(bpy.data.filepath).resolve(strict=True)
    source_before = sha256_file(source)
    repository = args.repository_root.resolve(strict=True)
    evidence = args.evidence_root.resolve(strict=True)
    work = args.work_root.resolve(strict=True)

    state = bpy.context.scene.film_studio
    state.render_repository_root = str(repository)
    state.render_manifest_uri = args.manifest_uri
    state.render_evidence_root = str(evidence)
    operator_result = sorted(bpy.ops.film_studio.inspect_render_job())
    if operator_result != ["FINISHED"]:
        raise RuntimeError(f"Product inspection failed: {operator_result}")
    if state.render_status != "APPROVED_READY":
        raise RuntimeError(f"Typed render status differs: {state.render_status}")
    if state.render_preview_status != "READY" or state.render_final_status != "BLOCKED: PREVIEW_REQUIRED":
        raise RuntimeError("Initial stage status differs")

    main_manifest = json.loads((repository / args.manifest_uri).read_text(encoding="utf-8"))
    negative_root = work / "negative-manifests"
    negative_root.mkdir(parents=True, exist_ok=False)

    tampered = dict(main_manifest)
    tampered["status"] = "REJECTED"
    tampered_path = negative_root / "tampered-approval.json"
    write_json_exclusive(tampered_path, tampered)
    tampered_reason = expect_rejection(
        lambda: film_studio_render.execute_stage_with_failure_receipt(
            negative_root,
            tampered_path.name,
            evidence,
            "PREVIEW",
            "tampered-manifest",
        ),
        {"JOB_NOT_APPROVED", "MANIFEST_HASH_INVALID"},
    )

    escaped = json.loads(json.dumps(main_manifest))
    escaped["profiles"]["PREVIEW"]["output"] = "../escaped.png"
    escaped = self_hashed(escaped, "manifestHash")
    escaped_path = negative_root / "escaped-output.json"
    write_json_exclusive(escaped_path, escaped)
    escaped_reason = expect_rejection(
        lambda: film_studio_render.execute_stage_with_failure_receipt(
            negative_root,
            escaped_path.name,
            evidence,
            "PREVIEW",
            "escaped-output",
        ),
        {"OUTPUT_PATH_OUT_OF_SCOPE", "PROFILE_MISMATCH"},
    )

    missing_preview_reason = expect_rejection(
        lambda: film_studio_render.execute_stage_with_failure_receipt(
            repository,
            args.manifest_uri,
            evidence,
            "FINAL",
            "final-without-preview",
        ),
        {"PREVIEW_RECEIPT_MISSING"},
    )

    persisted = {
        "status": state.render_status,
        "jobId": state.render_job_id,
        "approvalId": state.render_approval_id,
        "manifestHash": state.render_manifest_hash,
        "previewStatus": state.render_preview_status,
        "finalStatus": state.render_final_status,
        "inspectionToken": state.render_inspection_token,
    }
    copy_path = work / "inspection" / "inspected-render-job.blend"
    copy_path.parent.mkdir(parents=True, exist_ok=True)
    save_result = sorted(bpy.ops.wm.save_as_mainfile(filepath=str(copy_path), copy=True))
    if save_result != ["FINISHED"]:
        raise RuntimeError(f"Inspection-copy save failed: {save_result}")
    bpy.ops.wm.open_mainfile(filepath=str(copy_path), load_ui=False)
    reopened = bpy.context.scene.film_studio
    reopened_values = {
        "status": reopened.render_status,
        "jobId": reopened.render_job_id,
        "approvalId": reopened.render_approval_id,
        "manifestHash": reopened.render_manifest_hash,
        "previewStatus": reopened.render_preview_status,
        "finalStatus": reopened.render_final_status,
        "inspectionToken": reopened.render_inspection_token,
    }
    if reopened_values != persisted:
        raise RuntimeError("Typed render-job state did not persist through workspace copy reopen")
    if sha256_file(source) != source_before:
        raise RuntimeError("Accepted PB.3 source changed")
    escaped_artifact = evidence.parent / "escaped.png"
    if escaped_artifact.exists():
        raise RuntimeError("Escaped artifact exists")
    if render_events:
        raise RuntimeError("Negative controls invoked render")
    return {
        "action": args.action,
        "pid": os.getpid(),
        "renderCalls": 0,
        "operatorResult": operator_result,
        "typedStatePersisted": True,
        "inspectionCopy": str(copy_path),
        "sourceSha256BeforeAndAfter": source_before,
        "negativeControls": {
            "tamperedManifest": tampered_reason,
            "escapedOutput": escaped_reason,
            "finalWithoutPreview": missing_preview_reason,
        },
    }


def render_stage(args, render_events):
    source = Path(bpy.data.filepath).resolve(strict=True)
    source_before = sha256_file(source)
    receipt = film_studio_render.execute_stage(
        args.repository_root.resolve(strict=True),
        args.manifest_uri,
        args.evidence_root.resolve(strict=True),
        args.action,
    )
    if len(render_events) != 1:
        raise RuntimeError(f"Expected one render call, observed {len(render_events)}")
    if sha256_file(source) != source_before:
        raise RuntimeError("Accepted PB.3 source changed")
    return {
        "action": args.action,
        "pid": os.getpid(),
        "renderCalls": 1,
        "receiptHash": receipt["receiptHash"],
        "output": receipt["output"],
        "sourceSha256BeforeAndAfter": source_before,
    }


parser = argparse.ArgumentParser()
parser.add_argument("--action", choices=("INSPECT_NEGATIVE", "PREVIEW", "FINAL"), required=True)
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--manifest-uri", required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
parser.add_argument("--work-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

events = []
bpy.app.handlers.render_pre.append(lambda scene: events.append(scene.name))
payload = inspect_and_negative(args, events) if args.action == "INSPECT_NEGATIVE" else render_stage(args, events)
print("PB4_PRODUCT=" + json.dumps(payload, sort_keys=True), flush=True)
