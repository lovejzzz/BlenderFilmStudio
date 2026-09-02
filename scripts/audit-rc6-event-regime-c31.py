#!/usr/bin/env python3
"""Independent raw-byte and direct-evidence audit; never import the producer."""
import ast
import hashlib
import json
import math
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
spec_path = root / "specs/ai-native-studio-rc6-event-regime-inventory-c31.v1.21.json"
spec = json.loads(spec_path.read_text())
evidence = root / spec["evidenceRoot"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value, key):
    return hashlib.sha256(json.dumps({k: v for k, v in value.items() if k != key}, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


inventory = json.loads((evidence / "inventory.json").read_text())
receipt = json.loads((evidence / "receipt.json").read_text())
paths = {row["role"]: root / row["path"] for row in spec["inputs"]}
data = {role: json.loads(path.read_text()) for role, path in paths.items() if role != "productModule"}
cases = inventory["cases"]
tree = ast.parse(paths["productModule"].read_text())
tiers = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "QUALITY_TIERS" for t in n.targets))
slow_start = data["slowResult"]["configuration"]["frameStart"]
slow_end = data["slowResult"]["configuration"]["frameEnd"]
slow_rows = [x for x in data["slowTrajectory"]["samples"] if slow_start <= x["frame"] <= slow_end]
travels = [max(x["surfaceDisplacementFromPriorFrameMeters"] for x in slow_rows)] + [data[role]["metrics"]["maximumCupSurfaceDisplacementPerFrameMeters"] for role in ("impactBaseline", "impactResult")]
sc = data["slowSpec"]["frozenConfiguration"]
ic = data["impactSpec"]["frozenConfiguration"]
diff = {k: {"slow": sc[k], "impact": ic[k]} for k in sorted(sc.keys() & ic.keys()) if sc[k] != ic[k]}
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
expected_roles = ["slowResult", "impactBaseline", "impactResult"]
checks = {
    "inputRosterExact": inventory["inputs"] == spec["inputs"] and all(not paths[r["role"]].is_symlink() and sha(paths[r["role"]]) == r["sha256"] for r in spec["inputs"]),
    "frozenToolsExact": all(sha(root / r["path"]) == r["sha256"] for r in spec["tools"]),
    "specExactCommittedBytes": subprocess.check_output(["git", "show", f"HEAD:{spec_path.relative_to(root)}"], cwd=root) == spec_path.read_bytes(),
    "executionCommitExact": inventory["researchExecutionCommit"] == receipt["researchExecutionCommit"] == commit,
    "specHashExact": inventory["specFileSha256"] == receipt["specFileSha256"] == sha(spec_path),
    "inventoryHashExact": inventory["inventoryHash"] == digest(inventory, "inventoryHash") == receipt["inventoryHash"],
    "receiptHashExact": receipt["receiptHash"] == digest(receipt, "receiptHash") and receipt["inventoryFileSha256"] == sha(evidence / "inventory.json"),
    "caseRosterExact": [r["role"] for r in cases] == expected_roles,
    "slowWindowExact": [r["frame"] for r in slow_rows] == list(range(slow_start, slow_end + 1)) and cases[0]["window"] == [slow_start, slow_end],
    "travelAndVoxelRecomputed": all(row["maximumSurfaceTravelMeters"] == travel and row["baseVoxelMeters"] == data[row["role"]]["configuration"]["baseVoxelMeters"] and abs(row["surfaceTravelVoxelsPerFrame"] - travel / row["baseVoxelMeters"]) <= 1e-12 for row, travel in zip(cases, travels)),
    "samplingAndSubframesRecomputed": all(row["samplingBand"] == ("SUBVOXEL_PER_FRAME" if row["surfaceTravelVoxelsPerFrame"] <= 1 else "MULTIVOXEL_PER_FRAME") and row["derivedEffectorSubframes"] == max(1, math.ceil(row["surfaceTravelVoxelsPerFrame"])) for row in cases),
    "physicalChecksRecomputed": all(row["observedPhysicalStatus"] == data[row["role"]]["status"] and row["failedChecks"] == sorted(k for k, v in data[row["role"]]["checks"].items() if not v) for row in cases),
    "physicalMetricsRecomputed": all(row["sourceVolumeError"] == data[row["role"]]["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"] and row["temporalVolumeDrift"] == data[row["role"]]["metrics"]["maximumAbsoluteTemporalVolumeDriftFraction"] and row["maximumPositiveBodies"] == data[row["role"]]["metrics"]["maximumPositiveBodyCount"] for row in cases),
    "tierMismatchRecomputed": tiers == inventory["productQualityTiers"] and [r["productPreviewWindowAdmitted"] for r in cases] == [r["window"][1] - r["window"][0] + 1 <= tiers["PREVIEW"]["maximumFrameCount"] for r in cases] == [True, False, False],
    "crossRegimeConfoundersExact": diff == inventory["crossRegimeConfigurationDifferences"] and all(k in diff for k in ("timestepsMax", "fractionsThreshold", "cupEffectorSubframes", "frameEnd")),
    "noAcceptedImpactRecipe": [r["observedPhysicalStatus"] for r in cases] == ["PASS", "FAIL", "FAIL"] and spec["decisionContract"]["automaticRecipeSelection"] is False and all(data[role]["status"] == expected for role, expected in {"slowAudit": "PASS", "impactBaselineAudit": "PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED", "impactAudit": "PASS", "comparisonAudit": "PASS"}.items()),
    "holdoutNotClaimedExecuted": spec["physicalHoldout"]["status"] == "FROZEN_DESIGN_NOT_EXECUTED" and spec["physicalHoldout"]["requiresIndependentPhysicalValidation"] is True,
    "zeroBlenderAndMutationCounts": receipt["counts"] == spec["operationCounts"] and all(value == 0 for key, value in receipt["counts"].items() if key != "systemPythonStartsIncludingAudit") and receipt["counts"]["systemPythonStartsIncludingAudit"] == 2,
    "producerChecksPass": inventory["checkCount"] == 10 and inventory["passCount"] == 10 and all(inventory["checks"].values()),
    "boundedExactPreAuditRoot": sorted(p.name for p in evidence.iterdir()) == ["inventory.json", "receipt.json"] and sum(p.stat().st_size for p in evidence.iterdir()) < spec["maximumEvidenceBytes"],
}
audit = {"schemaVersion": "bfs.rc6C31Audit.v1.0", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "passCount": sum(checks.values()), "checkCount": len(checks), "inventoryHash": inventory["inventoryHash"], "receiptHash": receipt["receiptHash"], "claimCeiling": spec["claimCeiling"]}
audit["auditHash"] = digest(audit, "auditHash")
with (evidence / "independent-audit.json").open("x") as handle:
    json.dump(audit, handle, indent=2, sort_keys=True, allow_nan=False)
    handle.write("\n")
assert sum(p.stat().st_size for p in evidence.iterdir()) < spec["maximumEvidenceBytes"]
print(json.dumps({"status": audit["status"], "checks": f"{audit['passCount']}/{audit['checkCount']}", "auditHash": audit["auditHash"]}))
raise SystemExit(0 if all(checks.values()) else 1)
