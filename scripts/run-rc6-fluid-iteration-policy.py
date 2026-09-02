#!/usr/bin/env python3
"""Validate the one-path RC6 product fluid-iteration policy candidate."""

import copy
import hashlib
import importlib
import json
import math
import subprocess
import sys
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-fluid-pipeline-development/source")
MODULE_DIR = SOURCE / "scripts/modules"
MODULE = MODULE_DIR / "film_studio_fluid_pipeline.py"
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-fluid-policy-attempt-35"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-fluid-iteration-policy-tool-freeze.v0.37.json"
RUNNER = Path(__file__).resolve()
AUDITOR = RESEARCH / "scripts/audit-rc6-fluid-iteration-policy.py"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = copy.deepcopy(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def load_policy():
    sys.path.insert(0, str(MODULE_DIR))
    try:
        return importlib.import_module("film_studio_fluid_pipeline")
    finally:
        sys.path.remove(str(MODULE_DIR))


def snapshot(policy, *, frame_end=7, physics=None, surface=None, visual=None):
    return {
        "schemaVersion": policy.SNAPSHOT_VERSION,
        "physics": {
            "frameStart": 1,
            "frameEnd": frame_end,
            "fps": 24,
            "parameters": physics or {
                "domainBoundsMeters": [0.36, 0.36, 0.5],
                "method": "APIC",
                "particleRadius": 1.6,
                "particleNumber": 2,
                "cfl": 2.0,
                "viscosity": [1.0, 6],
                "flowBindings": ["wide-mouth source"],
                "effectorBindings": ["open tumbler proxy"],
            },
        },
        "surface": {"parameters": surface or {
            "meshScale": 2,
            "meshParticleRadius": 9.0,
            "smoothPositive": 1,
            "smoothNegative": 1,
            "concavityLower": 0.4,
            "concavityUpper": 3.5,
        }},
        "visual": {"parameters": visual or {
            "material": "clear-water",
            "camera": "physical-contact",
            "lighting": "layered-studio",
        }},
    }


def request(policy, tier, current, previous=None, review=None):
    return {
        "schemaVersion": policy.REQUEST_VERSION,
        "requestedTier": tier,
        "currentSnapshot": current,
        "previousState": previous,
        "reviewReceipt": review,
    }


def expect_rejection(policy, label, expected_reason, function):
    try:
        function()
    except policy.FluidPipelineError as error:
        return {"id": label, "expectedReason": expected_reason, "observedReason": error.reason, "pass": error.reason == expected_reason}
    return {"id": label, "expectedReason": expected_reason, "observedReason": None, "pass": False}


def run_cases(policy):
    base = snapshot(policy)
    dummy_data = "a" * 64
    dummy_mesh = "b" * 64
    positive = []

    draft = policy.compile_iteration_plan(request(policy, "DRAFT", base))
    positive.append({"id": "P01_DRAFT_INITIAL", "pass": draft["decision"] == "BAKE_DATA_THEN_MESH" and draft["resolutionMax"] == 64 and draft["stages"] == ["DATA", "MESH"], "planHash": draft["planHash"], "decision": draft["decision"]})
    preview = policy.compile_iteration_plan(request(policy, "PREVIEW", base))
    positive.append({"id": "P02_PREVIEW_INITIAL", "pass": preview["decision"] == "BAKE_DATA_THEN_MESH" and preview["resolutionMax"] == 96, "planHash": preview["planHash"], "decision": preview["decision"]})
    preview_state = policy.seal_iteration_state(preview, dummy_data, dummy_mesh)
    positive.append({"id": "P03_STATE_SEAL", "pass": preview_state["stateHash"] == policy._self_hash(preview_state, "stateHash") and preview_state["tier"] == "PREVIEW", "stateHash": preview_state["stateHash"], "decision": "SEALED"})

    physics_changed = copy.deepcopy(base)
    physics_changed["physics"]["parameters"]["particleRadius"] = 1.55
    physics_plan = policy.compile_iteration_plan(request(policy, "PREVIEW", physics_changed, preview_state))
    positive.append({"id": "P04_PHYSICS_INVALIDATES_DATA", "pass": physics_plan["decision"] == "BAKE_DATA_THEN_MESH" and physics_plan["reuse"] == [], "planHash": physics_plan["planHash"], "decision": physics_plan["decision"]})

    surface_changed = copy.deepcopy(base)
    surface_changed["surface"]["parameters"]["meshParticleRadius"] = 8.0
    surface_plan = policy.compile_iteration_plan(request(policy, "PREVIEW", surface_changed, preview_state))
    positive.append({"id": "P05_SURFACE_REUSES_DATA", "pass": surface_plan["decision"] == "REUSE_DATA_BAKE_MESH" and surface_plan["boundCaches"] == {"dataCacheHash": dummy_data, "meshCacheHash": None}, "planHash": surface_plan["planHash"], "decision": surface_plan["decision"]})

    visual_changed = copy.deepcopy(base)
    visual_changed["visual"]["parameters"]["camera"] = "wide-review"
    visual_plan = policy.compile_iteration_plan(request(policy, "PREVIEW", visual_changed, preview_state))
    positive.append({"id": "P06_VISUAL_REUSES_BOTH", "pass": visual_plan["decision"] == "REUSE_DATA_AND_MESH_VISUAL_ONLY" and visual_plan["boundCaches"] == {"dataCacheHash": dummy_data, "meshCacheHash": dummy_mesh}, "planHash": visual_plan["planHash"], "decision": visual_plan["decision"]})

    exact_plan = policy.compile_iteration_plan(request(policy, "PREVIEW", base, preview_state))
    positive.append({"id": "P07_EXACT_REUSE", "pass": exact_plan["decision"] == "REUSE_ALL" and exact_plan["stages"] == [], "planHash": exact_plan["planHash"], "decision": exact_plan["decision"]})

    review_plan = policy.compile_iteration_plan(request(policy, "REVIEW", base))
    positive.append({"id": "P08_REVIEW_INITIAL", "pass": review_plan["decision"] == "BAKE_DATA_THEN_MESH" and review_plan["resolutionMax"] == 128, "planHash": review_plan["planHash"], "decision": review_plan["decision"]})
    review_receipt = policy.seal_review_receipt(review_plan, "c" * 64, "d" * 64)
    final_plan = policy.compile_iteration_plan(request(policy, "FINAL", base, None, review_receipt))
    positive.append({"id": "P09_FINAL_FROM_EXACT_REVIEW", "pass": final_plan["decision"] == "BAKE_DATA_THEN_MESH" and final_plan["resolutionMax"] == 192 and final_plan["reviewReceiptHash"] == review_receipt["receiptHash"], "planHash": final_plan["planHash"], "decision": final_plan["decision"]})

    negative = []
    negative.append(expect_rejection(policy, "N01_UNKNOWN_TIER", "UNKNOWN_TIER", lambda: policy.compile_iteration_plan(request(policy, "ULTRA", base))))
    with_resolution = copy.deepcopy(base)
    with_resolution["physics"]["parameters"]["resolutionMax"] = 192
    negative.append(expect_rejection(policy, "N02_RESOLUTION_OVERRIDE", "CALLER_AUTHORITY", lambda: policy.compile_iteration_plan(request(policy, "PREVIEW", with_resolution))))
    negative.append(expect_rejection(policy, "N03_FRAME_CEILING", "TIER_FRAME_CEILING", lambda: policy.compile_iteration_plan(request(policy, "DRAFT", snapshot(policy, frame_end=13)))))
    nonfinite = copy.deepcopy(base)
    nonfinite["physics"]["parameters"]["cfl"] = math.inf
    negative.append(expect_rejection(policy, "N04_NONFINITE", "NONFINITE_NUMBER", lambda: policy.compile_iteration_plan(request(policy, "PREVIEW", nonfinite))))
    missing_data = copy.deepcopy(preview_state)
    missing_data["dataCacheHash"] = None
    missing_data["stateHash"] = policy._self_hash(missing_data, "stateHash")
    negative.append(expect_rejection(policy, "N05_MISSING_DATA_CACHE", "SPEC_SCHEMA", lambda: policy.compile_iteration_plan(request(policy, "PREVIEW", surface_changed, missing_data))))
    missing_mesh = copy.deepcopy(preview_state)
    missing_mesh["meshCacheHash"] = None
    missing_mesh["stateHash"] = policy._self_hash(missing_mesh, "stateHash")
    negative.append(expect_rejection(policy, "N06_MISSING_MESH_CACHE", "SPEC_SCHEMA", lambda: policy.compile_iteration_plan(request(policy, "PREVIEW", visual_changed, missing_mesh))))
    negative.append(expect_rejection(policy, "N07_FINAL_WITHOUT_REVIEW", "FINAL_WITHOUT_REVIEW", lambda: policy.compile_iteration_plan(request(policy, "FINAL", base))))
    forged = copy.deepcopy(review_receipt)
    forged["receiptHash"] = "0" * 64
    negative.append(expect_rejection(policy, "N08_FORGED_REVIEW_HASH", "STALE_REVIEW_RECEIPT", lambda: policy.compile_iteration_plan(request(policy, "FINAL", base, None, forged))))
    changed_after_review = copy.deepcopy(base)
    changed_after_review["physics"]["parameters"]["particleNumber"] = 3
    negative.append(expect_rejection(policy, "N09_PHYSICS_AFTER_REVIEW", "PHYSICS_CHANGED_AFTER_REVIEW", lambda: policy.compile_iteration_plan(request(policy, "FINAL", changed_after_review, None, review_receipt))))
    surface_after_review = copy.deepcopy(base)
    surface_after_review["surface"]["parameters"]["meshParticleRadius"] = 8.5
    negative.append(expect_rejection(policy, "N10_SURFACE_AFTER_REVIEW", "SURFACE_CHANGED_AFTER_REVIEW", lambda: policy.compile_iteration_plan(request(policy, "FINAL", surface_after_review, None, review_receipt))))
    negative.append(expect_rejection(policy, "N11_FRAME_AFTER_REVIEW", "FRAME_WINDOW_CHANGED_AFTER_REVIEW", lambda: policy.compile_iteration_plan(request(policy, "FINAL", snapshot(policy, frame_end=8), None, review_receipt))))
    caller_decision = copy.deepcopy(base)
    caller_decision["physics"]["parameters"]["cacheDecision"] = "REUSE_ALL"
    negative.append(expect_rejection(policy, "N12_CALLER_CACHE_DECISION", "CALLER_AUTHORITY", lambda: policy.compile_iteration_plan(request(policy, "PREVIEW", caller_decision))))
    negative.append(expect_rejection(policy, "N13_UNEXPECTED_REVIEW", "UNEXPECTED_REVIEW_RECEIPT", lambda: policy.compile_iteration_plan(request(policy, "PREVIEW", base, None, review_receipt))))
    negative.append(expect_rejection(policy, "N14_SEAL_NON_REVIEW", "REVIEW_TIER", lambda: policy.seal_review_receipt(preview, "c" * 64, "d" * 64)))
    corrupt_plan = copy.deepcopy(preview)
    corrupt_plan["decision"] = "REUSE_ALL"
    negative.append(expect_rejection(policy, "N15_CORRUPT_PLAN", "PLAN_HASH", lambda: policy.seal_iteration_state(corrupt_plan, dummy_data, dummy_mesh)))
    return positive, negative


def main():
    if EVIDENCE.exists():
        raise RuntimeError("RC6 fluid-policy evidence root is not fresh")
    if git("status", "--porcelain", cwd=RESEARCH):
        raise RuntimeError("research worktree must be clean")
    if git("status", "--porcelain", cwd=SOURCE):
        raise RuntimeError("product source worktree must be clean")
    spec = read_json(SPEC)
    if spec.get("status") != "FROZEN" or spec.get("specHash") != self_hash(spec, "specHash"):
        raise RuntimeError("fluid-policy tool-freeze identity mismatch")
    if git("rev-parse", "HEAD", cwd=SOURCE) != spec["productCandidate"]["commit"]:
        raise RuntimeError("fluid-policy product commit mismatch")
    changed_paths = git("diff", "--name-only", spec["productCandidate"]["parentCommit"] + "..HEAD", cwd=SOURCE).splitlines()
    if changed_paths != [spec["productCandidate"]["path"]] or sha(MODULE) != spec["productCandidate"]["moduleSha256"]:
        raise RuntimeError("fluid-policy one-path source identity mismatch")
    expected_tools = {
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR),
    }
    if spec.get("tools") != expected_tools:
        raise RuntimeError("fluid-policy tool roster mismatch")
    EVIDENCE.mkdir(parents=True, exist_ok=False)
    policy = load_policy()
    positive, negative = run_cases(policy)
    pass_all = len(positive) >= 8 and len(negative) >= 11 and all(row["pass"] for row in positive + negative)
    receipt = {
        "schemaVersion": "bfs.rc6FluidIterationPolicyReceipt.v0.1",
        "status": "PASS" if pass_all else "FAIL",
        "researchCommit": git("rev-parse", "HEAD", cwd=RESEARCH),
        "specHash": spec["specHash"],
        "productParent": spec["productCandidate"]["parentCommit"],
        "productCommit": spec["productCandidate"]["commit"],
        "productChangedPaths": changed_paths,
        "moduleSha256": sha(MODULE),
        "qualityTiers": policy.QUALITY_TIERS,
        "positiveCases": positive,
        "negativeCases": negative,
        "counts": {
            "positiveCases": len(positive), "negativeCases": len(negative),
            "blenderStarts": 0, "builds": 0, "bakes": 0, "renders": 0,
            "networkCalls": 0, "engineRemoteWrites": 0,
        },
        "claimCeiling": spec["claimCeiling"],
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write_exclusive(EVIDENCE / "receipt.json", receipt)
    print(canonical({"status": receipt["status"], "positive": len(positive), "negative": len(negative), "receiptHash": receipt["receiptHash"]}))
    if not pass_all:
        raise RuntimeError("fluid-policy validation failed")


if __name__ == "__main__":
    main()
