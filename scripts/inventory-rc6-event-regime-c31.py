#!/usr/bin/env python3
"""Read bound evidence and source without importing or executing the product."""
import ast
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/ai-native-studio-rc6-event-regime-inventory-c31.v1.21.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal(value, field):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {**value, field: hashlib.sha256(payload.encode()).hexdigest()}


def write(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def git(*args, cwd=ROOT):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def main():
    spec = json.loads(SPEC.read_text())
    assert spec["status"] == "PREREGISTERED_READ_ONLY_DESIGN"
    assert not git("status", "--porcelain"), "research tree must be clean"
    commit = git("rev-parse", "HEAD")
    assert git("rev-parse", "HEAD^") == spec["researchParent"]
    assert subprocess.check_output(["git", "show", f"HEAD:{SPEC.relative_to(ROOT)}"], cwd=ROOT) == SPEC.read_bytes()
    for row in spec["tools"]:
        assert sha(ROOT / row["path"]) == row["sha256"]
    paths = {row["role"]: ROOT / row["path"] for row in spec["inputs"]}
    for row in spec["inputs"]:
        assert not paths[row["role"]].is_symlink()
        assert sha(paths[row["role"]]) == row["sha256"]
    assert git("rev-parse", "HEAD", cwd=paths["productModule"].parents[2]) == spec["sourceCommit"]
    assert not git("status", "--porcelain", cwd=paths["productModule"].parents[2])
    evidence = ROOT / spec["evidenceRoot"]
    assert not evidence.exists(), "one fresh inventory root only"
    assert shutil.disk_usage(ROOT).free >= spec["minimumReserveBytes"] + spec["maximumEvidenceBytes"]
    values = {role: json.loads(path.read_text()) for role, path in paths.items() if role != "productModule"}
    tree = ast.parse(paths["productModule"].read_text())
    tiers = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "QUALITY_TIERS" for t in node.targets))
    slow = values["slowResult"]
    first, last = slow["configuration"]["frameStart"], slow["configuration"]["frameEnd"]
    slow_rows = [row for row in values["slowTrajectory"]["samples"] if first <= row["frame"] <= last]
    assert [row["frame"] for row in slow_rows] == list(range(first, last + 1))
    slow_travel = max(row["surfaceDisplacementFromPriorFrameMeters"] for row in slow_rows)
    cases = []
    for role, travel, window, mechanism in (
        ("slowResult", slow_travel, [first, last], "HINGE_AND_MOTOR"),
        ("impactBaseline", values["impactBaseline"]["metrics"]["maximumCupSurfaceDisplacementPerFrameMeters"], [1, 36], "FREE_BODY_EXTERNAL_COLLISION"),
        ("impactResult", values["impactResult"]["metrics"]["maximumCupSurfaceDisplacementPerFrameMeters"], [1, 36], "FREE_BODY_EXTERNAL_COLLISION"),
    ):
        result = values[role]
        voxel = result["configuration"]["baseVoxelMeters"]
        ratio = travel / voxel
        cases.append({
            "role": role, "mechanism": mechanism, "window": window,
            "maximumSurfaceTravelMeters": travel, "baseVoxelMeters": voxel,
            "surfaceTravelVoxelsPerFrame": ratio,
            "samplingBand": "SUBVOXEL_PER_FRAME" if ratio <= 1 else "MULTIVOXEL_PER_FRAME",
            "derivedEffectorSubframes": max(1, math.ceil(ratio)),
            "productPreviewWindowAdmitted": window[1] - window[0] + 1 <= tiers["PREVIEW"]["maximumFrameCount"],
            "observedPhysicalStatus": result["status"],
            "failedChecks": sorted(key for key, passed in result["checks"].items() if not passed),
            "sourceVolumeError": result["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"],
            "temporalVolumeDrift": result["metrics"]["maximumAbsoluteTemporalVolumeDriftFraction"],
            "maximumPositiveBodies": result["metrics"]["maximumPositiveBodyCount"],
        })
    slow_config = values["slowSpec"]["frozenConfiguration"]
    impact_config = values["impactSpec"]["frozenConfiguration"]
    differences = {key: {"slow": slow_config[key], "impact": impact_config[key]} for key in sorted(set(slow_config) & set(impact_config)) if slow_config[key] != impact_config[key]}
    checks = {
        "slowHasAcceptedPhysicalEvidence": slow["status"] == "PASS" and all(slow["checks"].values()),
        "neitherImpactCandidatePasses": all(values[role]["status"] == "FAIL" and not all(values[role]["checks"].values()) for role in ("impactBaseline", "impactResult")),
        "retainedAuditsPass": all(values[role]["status"] == expected for role, expected in {"slowAudit": "PASS", "impactBaselineAudit": "PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED", "impactAudit": "PASS", "comparisonAudit": "PASS"}.items()),
        "samplingBandsSeparateObservedCases": [row["samplingBand"] for row in cases] == ["SUBVOXEL_PER_FRAME", "MULTIVOXEL_PER_FRAME", "MULTIVOXEL_PER_FRAME"],
        "samplingFormulaMatchesActualSettings": [row["derivedEffectorSubframes"] for row in cases] == [1, 8, 8],
        "researchWindowIsNotProductTierAdmission": [row["productPreviewWindowAdmitted"] for row in cases] == [True, False, False],
        "crossRegimeComparisonIsConfounded": all(key in differences for key in ("timestepsMax", "fractionsThreshold", "cupEffectorSubframes", "frameEnd")),
        "c30SupportsParticleAndMeshLoss": values["comparison"]["classification"] == "PARTICLE_AND_MESH_SUPPORT_LOSS",
        "noRecipeAutoSelection": spec["decisionContract"]["automaticRecipeSelection"] is False,
        "holdoutUnexecutedAndFrozen": spec["physicalHoldout"]["status"] == "FROZEN_DESIGN_NOT_EXECUTED",
    }
    for row in spec["inputs"]:
        assert sha(paths[row["role"]]) == row["sha256"], "retained input changed"
    inventory = seal({"schemaVersion": "bfs.rc6C31Inventory.v1.0", "status": "PASS_DESIGN_INVENTORY" if all(checks.values()) else "FAIL", "researchExecutionCommit": commit, "specFileSha256": sha(SPEC), "inputs": spec["inputs"], "cases": cases, "productQualityTiers": tiers, "crossRegimeConfigurationDifferences": differences, "checks": checks, "passCount": sum(checks.values()), "checkCount": len(checks), "claimCeiling": spec["claimCeiling"]}, "inventoryHash")
    evidence.mkdir()
    write(evidence / "inventory.json", inventory)
    receipt = seal({"schemaVersion": "bfs.rc6C31Receipt.v1.0", "status": inventory["status"], "researchExecutionCommit": commit, "specFileSha256": sha(SPEC), "inventoryFileSha256": sha(evidence / "inventory.json"), "inventoryHash": inventory["inventoryHash"], "counts": spec["operationCounts"], "retainedInputsUnchanged": True}, "receiptHash")
    write(evidence / "receipt.json", receipt)
    assert sum(path.stat().st_size for path in evidence.iterdir()) <= spec["maximumEvidenceBytes"]
    print(json.dumps({"status": inventory["status"], "checks": f"{inventory['passCount']}/{inventory['checkCount']}", "receiptHash": receipt["receiptHash"]}))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
