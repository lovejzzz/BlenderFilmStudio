#!/usr/bin/env python3
"""Independently audit the pure product cross-tier observation policy."""

import copy
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-fluid-pipeline-development/source")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-fluid-observation-escalation-attempt-43"
MODULE_DIR = SOURCE / "scripts/modules"
MODULE = MODULE_DIR / "film_studio_fluid_pipeline.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-fluid-observation-escalation-tool-freeze.v0.46.json"
RUNNER = RESEARCH / "scripts/run-rc6-fluid-observation-escalation.py"
AUDITOR = Path(__file__).resolve()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = copy.deepcopy(value); body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(label, condition, checks):
    checks[label] = bool(condition)


def main():
    audit_path = EVIDENCE / "independent-audit.json"
    if audit_path.exists():
        raise RuntimeError("observation escalation audit path is not fresh")
    spec = json.loads(SPEC.read_text())
    receipt = json.loads((EVIDENCE / "receipt.json").read_text())
    manifest = json.loads((EVIDENCE / "evidence-manifest.json").read_text())
    checks = {}
    check("specSelfHash", spec.get("status") == "FROZEN" and spec.get("specHash") == self_hash(spec, "specHash"), checks)
    check("toolRosterExact", spec.get("tools") == {str(RUNNER.relative_to(RESEARCH)): sha(RUNNER), str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR)}, checks)
    check("productIdentityExact", subprocess.run(["git", "rev-parse", "HEAD"], cwd=SOURCE, capture_output=True, text=True, check=True).stdout.strip() == spec["productCandidate"]["commit"] and sha(MODULE) == spec["productCandidate"]["moduleSha256"], checks)
    changed = subprocess.run(["git", "diff", "--name-only", f"{spec['productCandidate']['parentCommit']}..HEAD"], cwd=SOURCE, capture_output=True, text=True, check=True).stdout.splitlines()
    check("oneProductPathExact", changed == [spec["productCandidate"]["path"]], checks)
    check("receiptSelfHash", receipt.get("status") == "PASS" and receipt.get("receiptHash") == self_hash(receipt, "receiptHash"), checks)
    check("positiveCasesExact", len(receipt.get("positiveCases", [])) == 3 and all(case.get("pass") for case in receipt["positiveCases"]) and [case["status"] for case in receipt["positiveCases"]] == ["INCONCLUSIVE_LOWER_TIER_CONTAINED", "CANDIDATE_SAME_TIER_SIGNAL", "DEFECT_REPRODUCED"], checks)
    expected_negative = ["UNKNOWN_TIER", "TIER_RESOLUTION_MISMATCH", "SPEC_SCHEMA", "STALE_OBSERVATION", "PHYSICS_IDENTITY_MISMATCH", "METRIC_MISMATCH", "THRESHOLD_MISMATCH", "CANDIDATE_TIER_ABOVE_DEFECT", "CHANGED_PARAMETER_ROSTER", "CHANGED_PARAMETER_ROSTER", "SPEC_SCHEMA", "NONFINITE_NUMBER"]
    check("negativeCasesExact", len(receipt.get("negativeCases", [])) == 12 and all(case.get("pass") for case in receipt["negativeCases"]) and [case["actualReason"] for case in receipt["negativeCases"]] == expected_negative, checks)
    counts = receipt.get("counts", {})
    check("zeroExecutionAuthority", counts == {"positiveCases": 3, "negativeCases": 12, "productPathsChanged": 1, "blenderStarts": 0, "builds": 0, "bakes": 0, "renders": 0, "networkCalls": 0, "engineRemoteWrites": 0}, checks)
    expected_manifest = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(EVIDENCE), "files": [{"path": "receipt.json", "bytes": (EVIDENCE / "receipt.json").stat().st_size, "sha256": sha(EVIDENCE / "receipt.json")}]}
    expected_manifest["manifestHash"] = self_hash(expected_manifest, "manifestHash")
    check("evidenceManifestExact", manifest == expected_manifest, checks)
    committed = True
    for relative in list(spec["tools"]) + [str(SPEC.relative_to(RESEARCH))]:
        shown = subprocess.run(["git", "show", f"{receipt['researchCommit']}:{relative}"], cwd=RESEARCH, capture_output=True, check=False)
        committed = committed and shown.returncode == 0 and hashlib.sha256(shown.stdout).hexdigest() == sha(RESEARCH / relative)
    check("committedToolAndSpecBytesExact", committed, checks)
    sys.path.insert(0, str(MODULE_DIR))
    try:
        policy = importlib.import_module("film_studio_fluid_pipeline")
    finally:
        sys.path.pop(0)
    defect = policy.seal_tier_observation("DEFECT_ACCEPTED", "FINAL", "a" * 64, "maximumOneVoxelOutlierCount", 0, 9, [], "b" * 64)
    candidate = policy.seal_tier_observation("CONTAINED", "REVIEW", "a" * 64, "maximumOneVoxelOutlierCount", 0, 0, ["cupEffectorSurfaceDistanceCells"], "b" * 64)
    decision = policy.evaluate_observation_escalation({"schemaVersion": policy.OBSERVATION_ESCALATION_REQUEST_VERSION, "acceptedDefect": defect, "candidateObservation": candidate})
    check("independentCoreDecision", decision["status"] == "INCONCLUSIVE_LOWER_TIER_CONTAINED" and decision["nextTier"] == "FINAL" and decision["nextAction"] == "RUN_SAME_TIER_SINGLE_VARIABLE_PROBE" and decision["clearsAcceptedDefect"] is False and decision["decisionHash"] == policy._self_hash(decision, "decisionHash"), checks)
    check("noBpyImport", "bpy" not in sys.modules and "import bpy" not in MODULE.read_text(), checks)
    audit = {"schemaVersion": "bfs.rc6FluidObservationEscalationIndependentAudit.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "checksPassed": sum(checks.values()), "checksTotal": len(checks), "receiptHash": receipt["receiptHash"], "claimCeiling": spec["claimCeiling"]}
    audit["auditHash"] = self_hash(audit, "auditHash")
    with audit_path.open("x", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2, sort_keys=True); handle.write("\n")
    print(canonical({"status": audit["status"], "checks": f"{audit['checksPassed']}/{audit['checksTotal']}", "auditHash": audit["auditHash"]}))
    if audit["status"] != "PASS":
        raise RuntimeError("observation escalation audit failed")


if __name__ == "__main__":
    main()
