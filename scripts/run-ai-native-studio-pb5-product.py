# SPDX-License-Identifier: GPL-2.0-or-later
"""PB.5 product helper: one restart-safe action per Blender process."""

import argparse
import hashlib
import json
import os
import shutil
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


def self_hashed(value, field):
    body = dict(value)
    body.pop(field, None)
    body[field] = hashlib.sha256(canonical(body)).hexdigest()
    return body


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def configure_state(args):
    state = bpy.context.scene.film_studio
    state.render_repository_root = str(args.repository_root.resolve(strict=True))
    state.render_manifest_uri = args.manifest_uri
    state.render_evidence_root = str(args.evidence_root.resolve(strict=True))
    return state


def resume_action(args, events):
    source = Path(bpy.data.filepath).resolve(strict=True)
    source_before = sha256_file(source)
    state = configure_state(args)
    inspected = sorted(bpy.ops.film_studio.inspect_render_job())
    if inspected != ["FINISHED"]:
        raise RuntimeError(f"Render-job inspection failed: {inspected}")
    preview_before = None
    if (args.evidence_root / "preview/preview.png").exists():
        preview_before = sha256_file(args.evidence_root / "preview/preview.png")
    final_before = None
    if (args.evidence_root / "final/final.exr").exists():
        final_before = sha256_file(args.evidence_root / "final/final.exr")
    result = sorted(bpy.ops.film_studio.resume_render_job())
    if result != ["FINISHED"]:
        raise RuntimeError(f"Resume operator failed: {result}")
    expected = {
        "INTERRUPT_AFTER_PREVIEW": ("FINAL", 1, "PREVIEW"),
        "RESUME_FINAL": ("COMPLETE", 1, "PREVIEW, FINAL"),
        "RESUME_COMPLETE": ("COMPLETE", 0, "PREVIEW, FINAL"),
    }[args.action]
    if state.render_next_stage != expected[0] or len(events) != expected[1] or state.render_completed_stages != expected[2]:
        raise RuntimeError("Resume state or render count differs")
    if preview_before and sha256_file(args.evidence_root / "preview/preview.png") != preview_before:
        raise RuntimeError("Immutable Preview artifact changed")
    if final_before and sha256_file(args.evidence_root / "final/final.exr") != final_before:
        raise RuntimeError("Immutable Final artifact changed")
    if sha256_file(source) != source_before:
        raise RuntimeError("Accepted source .blend changed")
    payload = {
        "action": args.action,
        "pid": os.getpid(),
        "renderCalls": len(events),
        "nextStage": state.render_next_stage,
        "completedStages": state.render_completed_stages,
        "decisionHash": state.render_last_decision_hash,
        "sourceSha256BeforeAndAfter": source_before,
        "previewSha256Before": preview_before,
        "finalSha256Before": final_before,
    }
    print("PB5_PRODUCT=" + json.dumps(payload, sort_keys=True), flush=True)
    if args.action == "INTERRUPT_AFTER_PREVIEW":
        raise SystemExit(75)


def expect_rejection(function, expected):
    try:
        function()
    except film_studio_render.RenderContractError as error:
        if error.reason != expected:
            raise RuntimeError(f"Expected {expected}, got {error.reason}") from error
        return error.reason
    raise RuntimeError(f"Negative control unexpectedly passed: {expected}")


def negative_action(args, events):
    source = Path(bpy.data.filepath).resolve(strict=True)
    source_before = sha256_file(source)
    main = json.loads((args.repository_root / args.manifest_uri).read_text(encoding="utf-8"))
    attack_root = args.evidence_root / "attacks"
    manifest_root = args.work_root / "attack-manifests"
    manifest_root.mkdir(parents=True, exist_ok=False)
    results = {}

    stale_evidence = attack_root / "stale"
    stale_evidence.mkdir(parents=True)
    stale = json.loads(json.dumps(main))
    stale["authorizedEvidenceRoot"] = str(stale_evidence.resolve())
    stale["jobControl"]["notBefore"] = "2020-01-01T00:00:00Z"
    stale["jobControl"]["validUntil"] = "2021-01-01T00:00:00Z"
    stale = self_hashed(stale, "manifestHash")
    write_exclusive(manifest_root / "stale.json", stale)
    results["stale"] = expect_rejection(
        lambda: film_studio_render.plan_resume_with_failure_receipt(manifest_root, "stale.json", stale_evidence, "stale"),
        "JOB_EXPIRED",
    )

    budget_evidence = attack_root / "budget"
    budget_evidence.mkdir(parents=True)
    budget = json.loads(json.dumps(main))
    budget["authorizedEvidenceRoot"] = str(budget_evidence.resolve())
    budget["jobControl"]["maximumRenderCalls"] = 0
    budget = self_hashed(budget, "manifestHash")
    write_exclusive(manifest_root / "budget.json", budget)
    results["budget"] = expect_rejection(
        lambda: film_studio_render.plan_resume_with_failure_receipt(manifest_root, "budget.json", budget_evidence, "budget"),
        "RENDER_BUDGET_EXHAUSTED",
    )

    forged_evidence = attack_root / "forged"
    (forged_evidence / "preview").mkdir(parents=True)
    forged = json.loads(json.dumps(main))
    forged["authorizedEvidenceRoot"] = str(forged_evidence.resolve())
    forged = self_hashed(forged, "manifestHash")
    write_exclusive(manifest_root / "forged.json", forged)
    shutil.copyfile(args.evidence_root / "preview/preview.png", forged_evidence / "preview/preview.png")
    receipt = json.loads((args.evidence_root / "preview/receipt.json").read_text(encoding="utf-8"))
    receipt["status"] = "FORGED"
    write_exclusive(forged_evidence / "preview/receipt.json", receipt)
    results["forged"] = expect_rejection(
        lambda: film_studio_render.plan_resume_with_failure_receipt(manifest_root, "forged.json", forged_evidence, "forged"),
        "PREVIEW_RECEIPT_INVALID",
    )
    if events or sha256_file(source) != source_before:
        raise RuntimeError("Negative controls rendered or changed source")
    print("PB5_NEGATIVE=" + json.dumps({"pid": os.getpid(), "renderCalls": 0, "results": results}, sort_keys=True), flush=True)


parser = argparse.ArgumentParser()
parser.add_argument("--action", choices=("INTERRUPT_AFTER_PREVIEW", "RESUME_FINAL", "RESUME_COMPLETE", "NEGATIVE"), required=True)
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--manifest-uri", required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
parser.add_argument("--work-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
events = []
bpy.app.handlers.render_pre.append(lambda scene: events.append(scene.name))
negative_action(args, events) if args.action == "NEGATIVE" else resume_action(args, events)
