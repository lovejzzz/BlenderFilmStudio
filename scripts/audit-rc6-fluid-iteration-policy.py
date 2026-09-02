#!/usr/bin/env python3
"""Independent source and behavior audit for RC6 fluid iteration policy."""

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
RUNNER = RESEARCH / "scripts/run-rc6-fluid-iteration-policy.py"
AUDITOR = Path(__file__).resolve()


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
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def git(*args, cwd, binary=False):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=not binary, check=True).stdout


def load_policy():
    sys.path.insert(0, str(MODULE_DIR))
    try:
        return importlib.import_module("film_studio_fluid_pipeline")
    finally:
        sys.path.remove(str(MODULE_DIR))


def snapshot(policy, *, frame_end=7):
    return {
        "schemaVersion": policy.SNAPSHOT_VERSION,
        "physics": {"frameStart": 1, "frameEnd": frame_end, "fps": 24, "parameters": {
            "domainBoundsMeters": [0.36, 0.36, 0.5], "method": "APIC",
            "particleRadius": 1.6, "particleNumber": 2, "cfl": 2.0,
            "viscosity": [1.0, 6], "flowBindings": ["wide-mouth source"],
            "effectorBindings": ["open tumbler proxy"],
        }},
        "surface": {"parameters": {
            "meshScale": 2, "meshParticleRadius": 9.0,
            "smoothPositive": 1, "smoothNegative": 1,
            "concavityLower": 0.4, "concavityUpper": 3.5,
        }},
        "visual": {"parameters": {
            "material": "clear-water", "camera": "physical-contact",
            "lighting": "layered-studio",
        }},
    }


def request(policy, tier, current, previous=None, review=None):
    return {"schemaVersion": policy.REQUEST_VERSION, "requestedTier": tier, "currentSnapshot": current, "previousState": previous, "reviewReceipt": review}


def reason(policy, function):
    try:
        function()
    except policy.FluidPipelineError as error:
        return error.reason
    return None


def check(label, condition, checks):
    checks[label] = bool(condition)


def main():
    audit_path = EVIDENCE / "independent-audit.json"
    if audit_path.exists():
        raise RuntimeError("fluid-policy audit path is not fresh")
    spec = read_json(SPEC)
    receipt = read_json(EVIDENCE / "receipt.json")
    checks = {}
    check("specSelfHash", spec.get("status") == "FROZEN" and spec.get("specHash") == self_hash(spec, "specHash"), checks)
    check("receiptSelfHash", receipt.get("status") == "PASS" and receipt.get("receiptHash") == self_hash(receipt, "receiptHash"), checks)
    check("sourceTreesClean", not git("status", "--porcelain", cwd=RESEARCH).strip() and not git("status", "--porcelain", cwd=SOURCE).strip(), checks)
    product_commit = git("rev-parse", "HEAD", cwd=SOURCE).strip()
    changed = git("diff", "--name-only", spec["productCandidate"]["parentCommit"] + "..HEAD", cwd=SOURCE).splitlines()
    check("productCommitAndOnePath", product_commit == spec["productCandidate"]["commit"] and changed == [spec["productCandidate"]["path"]], checks)
    committed_module = git("show", f"{product_commit}:{spec['productCandidate']['path']}", cwd=SOURCE, binary=True)
    check("moduleBytesExact", hashlib.sha256(committed_module).hexdigest() == sha(MODULE) == spec["productCandidate"]["moduleSha256"], checks)
    check("noBpyImport", b"import bpy" not in committed_module and b"from bpy" not in committed_module, checks)
    tools = {str(RUNNER.relative_to(RESEARCH)): sha(RUNNER), str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR)}
    check("toolRosterExact", spec.get("tools") == tools, checks)
    research_commit = receipt.get("researchCommit")
    committed_exact = True
    for relative in list(tools) + [str(SPEC.relative_to(RESEARCH))]:
        shown = git("show", f"{research_commit}:{relative}", cwd=RESEARCH, binary=True)
        committed_exact = committed_exact and hashlib.sha256(shown).hexdigest() == sha(RESEARCH / relative)
    check("committedResearchBytesExact", committed_exact, checks)
    expected_positive_ids = [
        "P01_DRAFT_INITIAL", "P02_PREVIEW_INITIAL", "P03_STATE_SEAL",
        "P04_PHYSICS_INVALIDATES_DATA", "P05_SURFACE_REUSES_DATA",
        "P06_VISUAL_REUSES_BOTH", "P07_EXACT_REUSE", "P08_REVIEW_INITIAL",
        "P09_FINAL_FROM_EXACT_REVIEW",
    ]
    expected_negative = {
        "N01_UNKNOWN_TIER": "UNKNOWN_TIER", "N02_RESOLUTION_OVERRIDE": "CALLER_AUTHORITY",
        "N03_FRAME_CEILING": "TIER_FRAME_CEILING", "N04_NONFINITE": "NONFINITE_NUMBER",
        "N05_MISSING_DATA_CACHE": "SPEC_SCHEMA", "N06_MISSING_MESH_CACHE": "SPEC_SCHEMA",
        "N07_FINAL_WITHOUT_REVIEW": "FINAL_WITHOUT_REVIEW", "N08_FORGED_REVIEW_HASH": "STALE_REVIEW_RECEIPT",
        "N09_PHYSICS_AFTER_REVIEW": "PHYSICS_CHANGED_AFTER_REVIEW", "N10_SURFACE_AFTER_REVIEW": "SURFACE_CHANGED_AFTER_REVIEW",
        "N11_FRAME_AFTER_REVIEW": "FRAME_WINDOW_CHANGED_AFTER_REVIEW", "N12_CALLER_CACHE_DECISION": "CALLER_AUTHORITY",
        "N13_UNEXPECTED_REVIEW": "UNEXPECTED_REVIEW_RECEIPT", "N14_SEAL_NON_REVIEW": "REVIEW_TIER",
        "N15_CORRUPT_PLAN": "PLAN_HASH",
    }
    positives = receipt.get("positiveCases", [])
    negatives = receipt.get("negativeCases", [])
    check("recordedPositiveCasesExact", [row.get("id") for row in positives] == expected_positive_ids and all(row.get("pass") is True for row in positives), checks)
    check("recordedNegativeCasesExact", {row.get("id"): row.get("observedReason") for row in negatives} == expected_negative and all(row.get("pass") is True for row in negatives), checks)
    check("zeroExecutionAuthority", receipt.get("counts") == {
        "positiveCases": 9, "negativeCases": 15, "blenderStarts": 0,
        "builds": 0, "bakes": 0, "renders": 0, "networkCalls": 0,
        "engineRemoteWrites": 0,
    }, checks)

    policy = load_policy()
    base = snapshot(policy)
    plans = {tier: policy.compile_iteration_plan(request(policy, tier, base)) for tier in ("DRAFT", "PREVIEW", "REVIEW")}
    check("tierResolutionAndCeilingsExact", policy.QUALITY_TIERS == {
        "DRAFT": {"resolutionMax": 64, "maximumFrameCount": 12},
        "PREVIEW": {"resolutionMax": 96, "maximumFrameCount": 24},
        "REVIEW": {"resolutionMax": 128, "maximumFrameCount": 48},
        "FINAL": {"resolutionMax": 192, "maximumFrameCount": 240},
    } and [plans[tier]["resolutionMax"] for tier in ("DRAFT", "PREVIEW", "REVIEW")] == [64, 96, 128], checks)
    state = policy.seal_iteration_state(plans["PREVIEW"], "a" * 64, "b" * 64)
    physics = copy.deepcopy(base); physics["physics"]["parameters"]["cfl"] = 1.8
    surface = copy.deepcopy(base); surface["surface"]["parameters"]["meshParticleRadius"] = 8.0
    visual = copy.deepcopy(base); visual["visual"]["parameters"]["camera"] = "wide-review"
    decisions = [
        policy.compile_iteration_plan(request(policy, "PREVIEW", physics, state))["decision"],
        policy.compile_iteration_plan(request(policy, "PREVIEW", surface, state))["decision"],
        policy.compile_iteration_plan(request(policy, "PREVIEW", visual, state))["decision"],
        policy.compile_iteration_plan(request(policy, "PREVIEW", base, state))["decision"],
    ]
    check("cacheDecisionTableRecomputed", decisions == ["BAKE_DATA_THEN_MESH", "REUSE_DATA_BAKE_MESH", "REUSE_DATA_AND_MESH_VISUAL_ONLY", "REUSE_ALL"], checks)
    review = policy.seal_review_receipt(plans["REVIEW"], "c" * 64, "d" * 64)
    final = policy.compile_iteration_plan(request(policy, "FINAL", base, None, review))
    check("finalAdmissionRecomputed", final["resolutionMax"] == 192 and final["decision"] == "BAKE_DATA_THEN_MESH" and final["reviewReceiptHash"] == review["receiptHash"], checks)
    independent_negative = {
        "UNKNOWN_TIER": reason(policy, lambda: policy.compile_iteration_plan(request(policy, "ULTRA", base))),
        "FINAL_WITHOUT_REVIEW": reason(policy, lambda: policy.compile_iteration_plan(request(policy, "FINAL", base))),
    }
    bad_resolution = copy.deepcopy(base); bad_resolution["physics"]["parameters"]["resolutionMax"] = 192
    independent_negative["RESOLUTION_OVERRIDE"] = reason(policy, lambda: policy.compile_iteration_plan(request(policy, "PREVIEW", bad_resolution)))
    bad_physics = copy.deepcopy(base); bad_physics["physics"]["parameters"]["particleRadius"] = 1.55
    independent_negative["PHYSICS_AFTER_REVIEW"] = reason(policy, lambda: policy.compile_iteration_plan(request(policy, "FINAL", bad_physics, None, review)))
    bad_surface = copy.deepcopy(base); bad_surface["surface"]["parameters"]["meshParticleRadius"] = 8.5
    independent_negative["SURFACE_AFTER_REVIEW"] = reason(policy, lambda: policy.compile_iteration_plan(request(policy, "FINAL", bad_surface, None, review)))
    independent_negative["FRAME_AFTER_REVIEW"] = reason(policy, lambda: policy.compile_iteration_plan(request(policy, "FINAL", snapshot(policy, frame_end=8), None, review)))
    check("keyNegativeControlsRecomputed", independent_negative == {
        "UNKNOWN_TIER": "UNKNOWN_TIER", "FINAL_WITHOUT_REVIEW": "FINAL_WITHOUT_REVIEW",
        "RESOLUTION_OVERRIDE": "CALLER_AUTHORITY", "PHYSICS_AFTER_REVIEW": "PHYSICS_CHANGED_AFTER_REVIEW",
        "SURFACE_AFTER_REVIEW": "SURFACE_CHANGED_AFTER_REVIEW", "FRAME_AFTER_REVIEW": "FRAME_WINDOW_CHANGED_AFTER_REVIEW",
    }, checks)

    audit = {
        "schemaVersion": "bfs.rc6FluidIterationPolicyIndependentAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "checksPassed": sum(checks.values()),
        "checksTotal": len(checks),
        "receiptHash": receipt["receiptHash"],
        "productCommit": product_commit,
        "moduleSha256": sha(MODULE),
        "claimCeiling": spec["claimCeiling"],
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    write_exclusive(audit_path, audit)
    print(canonical({"status": audit["status"], "checks": f"{audit['checksPassed']}/{audit['checksTotal']}", "auditHash": audit["auditHash"]}))
    if audit["status"] != "PASS":
        raise RuntimeError("fluid-policy independent audit failed")


if __name__ == "__main__":
    main()
