#!/usr/bin/env python3
"""Independently audit the single Final-tier +1-cell effector Data comparison."""

import hashlib
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-data-attempt-42")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-final-effector-data-attempt-42"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
BASELINE_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-flip-particle-detail-attempt-37/cells/axis-control/result.json"
BASELINE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-flip-particle-detail-audit-c1-attempt-38/independent-audit-c1.json"
LOWER_TIER_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-obstacle-voxel-screen-c2-attempt-41/receipt.json"
LOWER_TIER_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-obstacle-voxel-screen-c2-attempt-41/independent-audit.json"
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-final-effector-data-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-liquid-final-effector-data.py"
AUDITOR = Path(__file__).resolve()
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-final-effector-data.v0.44.json"
CELL_ID = "final-effector-plus1"
BANNED_MEDIA = {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_exclusive(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def file_entries(root):
    return [{"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink()]


def manifest(root, exclusions=()):
    excluded = set(exclusions)
    files = [entry for entry in file_entries(root) if entry["path"] not in excluded]
    value = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(root), "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def expected_argv():
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(SOURCE_BLEND), "--python", str(SCENE_TOOL), "--",
        "--cell-id", CELL_ID, "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--resolution", "192", "--effector-surface-distance", "2.5",
    ]


def check(label, condition, checks):
    checks[label] = bool(condition)


def main():
    audit_path = EVIDENCE / "independent-audit.json"
    if audit_path.exists():
        raise RuntimeError("final-effector Data audit path is not fresh")
    spec = read_json(SPEC)
    admission = read_json(EVIDENCE / "admission.json")
    process = read_json(EVIDENCE / "processes/01-final-effector-plus1.json")
    result = read_json(EVIDENCE / f"cells/{CELL_ID}/result.json")
    receipt = read_json(EVIDENCE / "receipt.json")
    baseline = read_json(BASELINE_RESULT)
    baseline_audit = read_json(BASELINE_AUDIT)
    lower_tier_receipt = read_json(LOWER_TIER_RECEIPT)
    lower_tier_audit = read_json(LOWER_TIER_AUDIT)
    stdout_path = EVIDENCE / "logs/01-final-effector-plus1.stdout.log"
    stderr_path = EVIDENCE / "logs/01-final-effector-plus1.stderr.log"
    checks = {}

    check("specSelfHash", spec.get("status") == "FROZEN" and spec.get("specHash") == self_hash(spec, "specHash"), checks)
    check("toolRosterExact", spec.get("tools") == {str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL), str(RUNNER.relative_to(RESEARCH)): sha(RUNNER), str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR)}, checks)
    check("rootsExact", spec.get("roots") == {"work": str(WORK), "evidence": str(EVIDENCE)}, checks)
    check("inputsExact", sha(BINARY) == spec["inputs"]["binarySha256"] == admission["binarySha256"] and sha(SOURCE_BLEND) == spec["inputs"]["sourceBlendSha256"] == admission["sourceBlendSha256"], checks)
    check("baselineExact", sha(BASELINE_RESULT) == spec["retainedBaseline"]["resultFileSha256"] and baseline.get("resultHash") == spec["retainedBaseline"]["resultHash"] and sha(BASELINE_AUDIT) == spec["retainedBaseline"]["auditFileSha256"] and baseline_audit.get("auditHash") == spec["retainedBaseline"]["auditHash"], checks)
    check("lowerTierScreenExact", sha(LOWER_TIER_RECEIPT) == spec["lowerTierScreen"]["receiptFileSha256"] and lower_tier_receipt.get("receiptHash") == spec["lowerTierScreen"]["receiptHash"] and sha(LOWER_TIER_AUDIT) == spec["lowerTierScreen"]["auditFileSha256"] and lower_tier_audit.get("auditHash") == spec["lowerTierScreen"]["auditHash"] and lower_tier_receipt.get("status") == spec["lowerTierScreen"]["status"] and lower_tier_audit.get("status") == "PASS" and lower_tier_audit.get("screenVerdict") == spec["lowerTierScreen"]["status"], checks)
    check("admissionSelfHash", admission.get("status") == "PASS" and admission.get("admissionHash") == self_hash(admission, "admissionHash"), checks)
    check("admissionEvidenceBinding", admission.get("retainedBaselineResultHash") == baseline.get("resultHash") and admission.get("retainedBaselineAuditHash") == baseline_audit.get("auditHash") and admission.get("lowerTierReceiptHash") == lower_tier_receipt.get("receiptHash") and admission.get("lowerTierAuditHash") == lower_tier_audit.get("auditHash"), checks)
    check("processAndLogsExact", process.get("processHash") == self_hash(process, "processHash") and process.get("argv") == expected_argv() and process.get("cwd") == str(RESEARCH) and process.get("exitCode") == 0 and sha(stdout_path) == process.get("stdoutSha256") and sha(stderr_path) == process.get("stderrSha256") and stderr_path.stat().st_size == 0 and "RC6_FINAL_EFFECTOR_DATA=" in stdout_path.read_text(encoding="utf-8", errors="replace"), checks)
    expected_config = {
        "frameStart": 1, "frameEnd": 7, "resolutionMax": 192, "baseVoxelMeters": 0.0026041667,
        "domainCenterMeters": [0.32, 0.0, 0.25], "domainDimensionsMeters": [0.36, 0.36, 0.5],
        "sourceDimensionsMeters": [0.1099999994, 0.1099999994, 0.1400000006],
        "sourceMeshVolumeCubicMeters": 0.0013283283766941, "sourceBottomClearanceMeters": 0.0350000039,
        "simulationMethod": "APIC", "useAdaptiveTimesteps": True, "timestepsMin": 1, "timestepsMax": 4,
        "cflCondition": 2.0, "particleNumber": 2, "particleRadius": 1.6, "useMesh": False,
        "useFlipParticles": True, "initialUseFlipParticles": True, "initialParticleSystemCount": 1,
        "finalParticleSystemCount": 1, "displayPercentage": 100, "useFractions": True,
        "deleteInObstacle": False, "waterViscosityBase": 1.0, "waterViscosityExponent": 6,
        "flowSurfaceDistanceCells": 0.0, "cupEffectorSurfaceDistanceCells": 2.5,
        "cupEffectorIsPlanar": False, "cupEffectorEnabled": True, "cupEffectorSubframes": 0,
    }
    check("resultAndConfigurationExact", result.get("status") == "MEASURED_DATA_ONLY" and result.get("cellId") == CELL_ID and result.get("resultHash") == self_hash(result, "resultHash") and result.get("configuration") == expected_config and result.get("authority") == {"fluidDataBakes": 1, "fluidMeshBakes": 0, "blendSaves": 0, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}, checks)
    expected_cache = sorted([f"config/config_{frame:04d}.uni" for frame in range(1, 8)] + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)])
    cache_root = WORK / CELL_ID / "mantaflow-cache"
    actual_cache = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
    check("cacheRosterExact", result.get("cacheFiles") == expected_cache and actual_cache == expected_cache, checks)

    arithmetic = True
    details = True
    for sample in result.get("samples", []):
        for row in (sample.get("strictInterior", {}), sample.get("oneVoxelEnvelope", {})):
            combos = row.get("exclusiveCombinations", {})
            count = row.get("particleCount", 0)
            union = row.get("outsideUnionCount", -1)
            arithmetic = arithmetic and sum(combos.values()) == count and union == count - combos.get("inside", 0)
        details = details and len(sample.get("outliersOneVoxel", [])) == sample.get("oneVoxelEnvelope", {}).get("outsideUnionCount")
        details = details and all(detail.get("detailHash") == self_hash(detail, "detailHash") for detail in sample.get("outliersOneVoxel", []))
    check("particleArithmeticAndDetails", arithmetic and details and [sample.get("frame") for sample in result.get("samples", [])] == list(range(1, 8)), checks)

    baseline_max = max(sample["aggregate"]["outsideUnionCount"] for sample in baseline["samples"])
    candidate_max = result["metrics"]["maximumOneVoxelOutlierCount"]
    expected_status = "PASS_FINAL_SURFACE_DISTANCE_DATA_SIGNAL" if baseline_max == 9 and candidate_max == 0 else "FAIL_FINAL_SURFACE_DISTANCE_NO_CORRECTION"
    check("receiptSelfHash", receipt.get("receiptHash") == self_hash(receipt, "receiptHash"), checks)
    check("comparisonRecomputed", receipt.get("status") == expected_status and receipt.get("retainedBaseline", {}).get("maximumOneVoxelOutlierCount") == baseline_max and receipt.get("candidate", {}).get("maximumOneVoxelOutlierCount") == candidate_max and receipt.get("candidate", {}).get("resultHash") == result.get("resultHash"), checks)
    check("countCeilingsExact", receipt.get("counts") == {"blenderStarts": 1, "fluidDataBakes": 1, "fluidMeshBakes": 0, "blendSaves": 0, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0} and receipt.get("processHash") == process.get("processHash"), checks)
    ceilings = spec["resourceCeilings"]
    check("resourceCeilings", tree_bytes(WORK) <= ceilings["workBytes"] and tree_bytes(EVIDENCE) <= ceilings["evidenceBytes"] and receipt["resources"]["freeBytesAfter"] >= ceilings["minimumFreeBytesAfter"], checks)
    check("noSymlinksOrMedia", not any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*")) and not any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (WORK, EVIDENCE) for path in root.rglob("*")), checks)
    check("manifestsExact", read_json(EVIDENCE / "work-manifest.json") == manifest(WORK) and read_json(EVIDENCE / "evidence-manifest.json") == manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")), checks)
    commit = admission["researchCommit"]
    committed_exact = True
    for relative in list(spec["tools"]) + [str(SPEC.relative_to(RESEARCH))]:
        shown = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=RESEARCH, capture_output=True, check=False)
        committed_exact = committed_exact and shown.returncode == 0 and hashlib.sha256(shown.stdout).hexdigest() == sha(RESEARCH / relative)
    check("committedToolAndSpecBytesExact", committed_exact, checks)

    audit = {
        "schemaVersion": "bfs.rc6LiquidFinalEffectorDataIndependentAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "comparisonVerdict": receipt["status"],
        "checks": checks,
        "checksPassed": sum(checks.values()),
        "checksTotal": len(checks),
        "receiptHash": receipt["receiptHash"],
        "baselineResultHash": baseline["resultHash"],
        "candidateResultHash": result["resultHash"],
        "claimCeiling": spec["claimCeiling"],
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    write_exclusive(audit_path, audit)
    print(canonical({"status": audit["status"], "checks": f"{audit['checksPassed']}/{audit['checksTotal']}", "comparisonVerdict": audit["comparisonVerdict"], "auditHash": audit["auditHash"]}))
    if audit["status"] != "PASS":
        raise RuntimeError("final-effector Data independent audit failed")


if __name__ == "__main__":
    main()
