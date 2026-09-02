#!/usr/bin/env python3
"""Validate the pure product cross-tier liquid-observation policy."""

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
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-fluid-observation-escalation-attempt-43"
MODULE_DIR = SOURCE / "scripts/modules"
MODULE = MODULE_DIR / "film_studio_fluid_pipeline.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-fluid-observation-escalation-tool-freeze.v0.46.json"
RUNNER = Path(__file__).resolve()
AUDITOR = RESEARCH / "scripts/audit-rc6-fluid-observation-escalation.py"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = copy.deepcopy(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def import_policy():
    sys.path.insert(0, str(MODULE_DIR))
    try:
        return importlib.import_module("film_studio_fluid_pipeline")
    finally:
        sys.path.pop(0)


def exercise(policy):
    physics = "a" * 64
    evidence = "b" * 64
    metric = "maximumOneVoxelOutlierCount"
    parameter = ["cupEffectorSurfaceDistanceCells"]

    def seal(status="CONTAINED", tier="FINAL", identity=physics, metric_id=metric, threshold=0, value=0, changed=parameter):
        return policy.seal_tier_observation(status, tier, identity, metric_id, threshold, value, changed, evidence)

    def request(candidate=None, defect=None):
        return {
            "schemaVersion": policy.OBSERVATION_ESCALATION_REQUEST_VERSION,
            "acceptedDefect": defect or seal("DEFECT_ACCEPTED", "FINAL", value=9, changed=[]),
            "candidateObservation": candidate or seal(),
        }

    positives = []
    for case_id, candidate, expected_status, expected_action in [
        ("P01_LOWER_CONTAINED", seal("CONTAINED", "REVIEW"), "INCONCLUSIVE_LOWER_TIER_CONTAINED", "RUN_SAME_TIER_SINGLE_VARIABLE_PROBE"),
        ("P02_SAME_TIER_CONTAINED", seal(), "CANDIDATE_SAME_TIER_SIGNAL", "VERIFY_NEXT_DEPENDENT_STAGE"),
        ("P03_SAME_TIER_DEFECT", seal("DEFECT_OBSERVED", value=9), "DEFECT_REPRODUCED", "AUDIT_CAUSAL_INPUTS"),
    ]:
        decision = policy.evaluate_observation_escalation(request(candidate))
        passed = decision["status"] == expected_status and decision["nextAction"] == expected_action and decision["nextTier"] == "FINAL" and decision["clearsAcceptedDefect"] is False and decision["decisionHash"] == policy._self_hash(decision, "decisionHash")
        positives.append({"caseId": case_id, "status": decision["status"], "nextAction": decision["nextAction"], "decisionHash": decision["decisionHash"], "pass": passed})

    def reason(call):
        try:
            call()
        except policy.FluidPipelineError as error:
            return error.reason
        return None

    cases = []
    def record(case_id, expected, call):
        actual = reason(call)
        cases.append({"caseId": case_id, "expectedReason": expected, "actualReason": actual, "pass": actual == expected})

    record("N01_UNKNOWN_TIER", "UNKNOWN_TIER", lambda: seal(tier="ULTRA"))
    bad = seal(); bad["resolutionMax"] = 96; bad["observationHash"] = policy._self_hash(bad, "observationHash")
    record("N02_TIER_RESOLUTION", "TIER_RESOLUTION_MISMATCH", lambda: policy.evaluate_observation_escalation(request(bad)))
    bad = request(); bad["verdict"] = "PASS"
    record("N03_UNKNOWN_FIELD", "SPEC_SCHEMA", lambda: policy.evaluate_observation_escalation(bad))
    bad = seal(); bad["observationHash"] = "0" * 64
    record("N04_FORGED_HASH", "STALE_OBSERVATION", lambda: policy.evaluate_observation_escalation(request(bad)))
    record("N05_PHYSICS_MISMATCH", "PHYSICS_IDENTITY_MISMATCH", lambda: policy.evaluate_observation_escalation(request(seal(identity="c" * 64))))
    record("N06_METRIC_MISMATCH", "METRIC_MISMATCH", lambda: policy.evaluate_observation_escalation(request(seal(metric_id="otherMetric"))))
    record("N07_THRESHOLD_MISMATCH", "THRESHOLD_MISMATCH", lambda: policy.evaluate_observation_escalation(request(seal(threshold=1))))
    review_defect = seal("DEFECT_ACCEPTED", "REVIEW", value=9, changed=[])
    record("N08_TIER_ABOVE_DEFECT", "CANDIDATE_TIER_ABOVE_DEFECT", lambda: policy.evaluate_observation_escalation(request(seal(), review_defect)))
    record("N09_ZERO_CHANGED", "CHANGED_PARAMETER_ROSTER", lambda: seal(changed=[]))
    record("N10_MULTI_CHANGED", "CHANGED_PARAMETER_ROSTER", lambda: seal(changed=["a", "b"]))
    bad = request(); bad["nextAction"] = "CLEAR_DEFECT"
    record("N11_CALLER_DECISION", "SPEC_SCHEMA", lambda: policy.evaluate_observation_escalation(bad))
    record("N12_NONFINITE", "NONFINITE_NUMBER", lambda: seal(value=math.nan))
    return positives, cases


def main():
    if EVIDENCE.exists():
        raise RuntimeError("observation escalation evidence root is not fresh")
    if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
        raise RuntimeError("research worktree must be clean")
    if subprocess.run(["git", "status", "--porcelain"], cwd=SOURCE, capture_output=True, text=True, check=True).stdout:
        raise RuntimeError("product worktree must be clean")
    spec = json.loads(SPEC.read_text())
    if spec.get("status") != "FROZEN" or spec.get("specHash") != self_hash(spec, "specHash"):
        raise RuntimeError("observation escalation spec mismatch")
    if spec.get("tools") != {str(RUNNER.relative_to(RESEARCH)): sha(RUNNER), str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR)}:
        raise RuntimeError("observation escalation tool roster mismatch")
    if subprocess.run(["git", "rev-parse", "HEAD"], cwd=SOURCE, capture_output=True, text=True, check=True).stdout.strip() != spec["productCandidate"]["commit"] or sha(MODULE) != spec["productCandidate"]["moduleSha256"]:
        raise RuntimeError("observation escalation product identity mismatch")
    changed = subprocess.run(["git", "diff", "--name-only", f"{spec['productCandidate']['parentCommit']}..HEAD"], cwd=SOURCE, capture_output=True, text=True, check=True).stdout.splitlines()
    if changed != [spec["productCandidate"]["path"]]:
        raise RuntimeError("observation escalation product path mismatch")
    EVIDENCE.mkdir(parents=True, exist_ok=False)
    policy = import_policy()
    positives, negatives = exercise(policy)
    status = "PASS" if all(case["pass"] for case in positives + negatives) and "bpy" not in sys.modules else "FAIL"
    receipt = {
        "schemaVersion": "bfs.rc6FluidObservationEscalationReceipt.v0.1",
        "status": status,
        "researchCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),
        "productCommit": spec["productCandidate"]["commit"],
        "moduleSha256": sha(MODULE),
        "positiveCases": positives,
        "negativeCases": negatives,
        "counts": {"positiveCases": len(positives), "negativeCases": len(negatives), "productPathsChanged": len(changed), "blenderStarts": 0, "builds": 0, "bakes": 0, "renders": 0, "networkCalls": 0, "engineRemoteWrites": 0},
        "claimCeiling": spec["claimCeiling"],
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write_exclusive(EVIDENCE / "receipt.json", receipt)
    files = [{"path": "receipt.json", "bytes": (EVIDENCE / "receipt.json").stat().st_size, "sha256": sha(EVIDENCE / "receipt.json")}]
    manifest = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(EVIDENCE), "files": files}
    manifest["manifestHash"] = self_hash(manifest, "manifestHash")
    write_exclusive(EVIDENCE / "evidence-manifest.json", manifest)
    print(canonical({"status": status, "positive": f"{sum(x['pass'] for x in positives)}/{len(positives)}", "negative": f"{sum(x['pass'] for x in negatives)}/{len(negatives)}", "receiptHash": receipt["receiptHash"]}))
    if status != "PASS":
        raise RuntimeError("observation escalation validation failed")


if __name__ == "__main__":
    main()
