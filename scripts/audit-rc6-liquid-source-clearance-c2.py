#!/usr/bin/env python3
"""Independently audit the zero-recompute attempt-23 C2 closure."""

import hashlib
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
RETAINED_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-source-clearance-c1-attempt-23")
RETAINED_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-source-clearance-c1-attempt-23"
CLOSURE_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-source-clearance-c2-closure-attempt-24"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-source-clearance-c2-closure.v0.24.json"
RUNNER = RESEARCH / "scripts/close-rc6-liquid-source-clearance-c2.py"
AUDITOR = Path(__file__).resolve()
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-source-clearance-scene-c1.py"
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


def bytes_sha(value):
    return hashlib.sha256(value).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_exclusive(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def manifest(root, exclusions=()):
    excluded = set(exclusions)
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = str(path.relative_to(root))
        if relative in excluded:
            continue
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha(path)})
    value = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(root), "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def expected_argv(cell_id, requested):
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(SOURCE_BLEND), "--python", str(SCENE_TOOL), "--", "--cell-id", cell_id,
        "--work-root", str(RETAINED_WORK), "--evidence-root", str(RETAINED_EVIDENCE),
        "--resolution", "96", "--frame-end", "7", "--particle-radius", "1.6",
        "--particle-number", "2", "--mesh-particle-radius", "4.5",
        "--source-bottom-clearance", str(requested),
    ]


def expected_cache_files():
    return sorted(
        [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
        + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
        + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)]
    )


def signed_topology_passes(row, thresholds):
    for sample in row["samples"]:
        components = sample.get("components", [])
        positive = [item for item in components if item["signedVolumeCubicMeters"] > 1e-12]
        negative = [item for item in components if item["signedVolumeCubicMeters"] < -1e-12]
        if len(positive) != 1 or len(negative) > thresholds["maximumNegativeNestedShellCount"]:
            return False
        if any(item["nonManifoldEdgeCount"] for item in components):
            return False
        outer = positive[0]
        for inner in negative:
            contained = all(
                inner["boundsMinWorld"][axis] >= outer["boundsMinWorld"][axis] - 1e-7
                and inner["boundsMaxWorld"][axis] <= outer["boundsMaxWorld"][axis] + 1e-7
                for axis in range(3)
            )
            separation = sum(
                (inner["centroidWorld"][axis] - outer["centroidWorld"][axis]) ** 2 for axis in range(3)
            ) ** 0.5
            if not contained or separation > thresholds["maximumNestedCentroidSeparationMeters"]:
                return False
    return True


def cell_passes(row, thresholds):
    metrics = row["metrics"]
    return (
        metrics["maximumNonManifoldEdgeCount"] == 0
        and metrics["maximumAbsoluteVolumeDriftFraction"] <= thresholds["maximumAbsoluteTemporalDriftFraction"]
        and metrics["maximumAbsoluteSourceVolumeErrorFraction"] <= thresholds["maximumAbsoluteSourceVolumeErrorFraction"]
        and metrics["maximumOutsideCupInteriorPlusOneVoxelFraction"] <= thresholds["maximumOutsideCupInteriorPlusOneVoxelFraction"]
        and signed_topology_passes(row, thresholds)
    )


def check(label, condition, checks):
    checks[label] = bool(condition)


def main():
    audit_path = CLOSURE_EVIDENCE / "independent-audit.json"
    if audit_path.exists():
        raise RuntimeError("C2 independent audit path is not fresh")
    spec = read_json(SPEC)
    admission = read_json(CLOSURE_EVIDENCE / "admission.json")
    closure = read_json(CLOSURE_EVIDENCE / "closure.json")
    failure = read_json(RETAINED_EVIDENCE / "failure.json")
    checks = {}
    check("specSelfHash", spec.get("specHash") == self_hash(spec, "specHash") and spec.get("status") == "FROZEN", checks)
    check("toolRosterExact", spec.get("tools") == {
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR),
    }, checks)
    check("rootsExact", spec["roots"] == {
        "retainedWork": str(RETAINED_WORK), "retainedEvidence": str(RETAINED_EVIDENCE),
        "closureEvidence": str(CLOSURE_EVIDENCE),
    }, checks)
    check("inputIdentities", sha(BINARY) == spec["inputs"]["binarySha256"] and sha(SOURCE_BLEND) == spec["inputs"]["sourceBlendSha256"], checks)
    check("retainedFailureFile", sha(RETAINED_EVIDENCE / "failure.json") == spec["retainedAttempt"]["failureFileSha256"], checks)
    check("retainedFailureSelfHash", failure.get("failureHash") == self_hash(failure, "failureHash") == spec["retainedAttempt"]["failureHash"], checks)
    check("retainedFailureExpected", failure.get("status") == "FAIL_EXECUTION" and failure.get("message") == "clearance-20mm: configuration mismatch" and failure.get("counts", {}).get("blenderStarts") == 4, checks)
    check("admissionSelfHash", admission.get("admissionHash") == self_hash(admission, "admissionHash") and admission.get("status") == "PASS", checks)
    check("zeroRecomputeAdmission", all(admission.get(key) == 0 for key in ("newBlenderStarts", "newPhysicsBakes", "newRenderCalls", "networkCalls", "engineRemoteWrites")), checks)
    check("closureSelfHash", closure.get("closureHash") == self_hash(closure, "closureHash") and closure.get("status") == "PASS_CLOSURE", checks)
    check("noSymlinks", not any(path.is_symlink() for root in (RETAINED_WORK, RETAINED_EVIDENCE, CLOSURE_EVIDENCE) for path in root.rglob("*")), checks)
    check("zeroRenderMedia", not any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (RETAINED_WORK, RETAINED_EVIDENCE, CLOSURE_EVIDENCE) for path in root.rglob("*")), checks)

    fixed = spec["matrix"]["fixed"]
    thresholds = spec["acceptanceThresholds"]
    binding = spec["measurementBinding"]
    recomputed_cells = []
    results = []
    cell_checks = []
    for index, cell in enumerate(spec["matrix"]["cells"], start=1):
        cell_id = cell["cellId"]
        requested = cell["requestedClearanceMeters"]
        process_path = RETAINED_EVIDENCE / "processes" / f"{index:02d}-{cell_id}.json"
        stdout_path = RETAINED_EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stdout.log"
        stderr_path = RETAINED_EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stderr.log"
        result_path = RETAINED_EVIDENCE / "cells" / cell_id / "result.json"
        process = read_json(process_path)
        result = read_json(result_path)
        configuration = dict(result["configuration"])
        measured = configuration.pop("sourceBottomClearanceMeters")
        measured_voxels = configuration.pop("sourceBottomClearanceVoxels")
        baked = result["bakedState"]
        baked_path = Path(baked["uri"])
        cache_root = baked_path.parent / "mantaflow-cache"
        expected_cache = expected_cache_files()
        actual_cache = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
        clearance_error = abs(measured - requested)
        voxel_error = abs(measured_voxels - cell["requestedClearanceVoxels"])
        row_checks = {
            "cellId": cell_id,
            "processSelfHash": process.get("processHash") == self_hash(process, "processHash"),
            "argvExact": process.get("argv") == expected_argv(cell_id, requested),
            "cwdExact": process.get("cwd") == str(RESEARCH),
            "exitZero": process.get("exitCode") == 0,
            "logsExact": sha(stdout_path) == process.get("stdoutSha256") and sha(stderr_path) == process.get("stderrSha256") and stderr_path.stat().st_size == 0,
            "resultSelfHash": result.get("resultHash") == self_hash(result, "resultHash") and result.get("status") == "MEASURED" and result.get("cellId") == cell_id,
            "fixedConfigurationExact": configuration == fixed,
            "placementRoundoffBound": clearance_error <= binding["maximumAbsoluteClearanceErrorMeters"] and voxel_error <= binding["maximumAbsoluteClearanceErrorVoxels"],
            "samplesExact": [item.get("frame") for item in result.get("samples", [])] == list(range(1, 8)),
            "sourceVolumeExact": abs(result["metrics"]["sourceMeshVolumeCubicMeters"] - spec["inputs"]["sourceMeshVolumeCubicMeters"]) <= 1e-15,
            "bakedStateExact": baked_path.is_file() and baked_path.stat().st_size == baked["bytes"] and sha(baked_path) == baked["sha256"],
            "cacheRosterExact": result.get("cacheFiles") == expected_cache and actual_cache == expected_cache,
        }
        row_checks["pass"] = all(value for key, value in row_checks.items() if key != "cellId")
        cell_checks.append(row_checks)
        recomputed_cells.append({
            "cellId": cell_id,
            "requestedClearanceMeters": requested,
            "measuredClearanceMeters": measured,
            "absoluteClearanceErrorMeters": round(clearance_error, 12),
            "requestedClearanceVoxels": cell["requestedClearanceVoxels"],
            "measuredClearanceVoxels": measured_voxels,
            "absoluteClearanceErrorVoxels": round(voxel_error, 10),
            "passesStaticControl": cell_passes(result, thresholds),
            "resultHash": result["resultHash"],
            "processHash": process["processHash"],
            "metrics": result["metrics"],
        })
        results.append(result)
    check("fourRetainedCellsExact", len(cell_checks) == 4 and all(row["pass"] for row in cell_checks), checks)
    check("closureCellsRecomputed", closure.get("cells") == recomputed_cells, checks)
    passing = [row for row in results if cell_passes(row, thresholds)]
    ranked = sorted(results, key=lambda row: (
        not signed_topology_passes(row, thresholds),
        row["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"],
        row["metrics"]["maximumAbsoluteVolumeDriftFraction"],
        row["configuration"]["sourceBottomClearanceMeters"],
    ))
    expected_selected = (passing or ranked)[0]["cellId"]
    check("scientificVerdictRecomputed", closure.get("scientificVerdict") == ("PASS_STATIC_CONTROL" if passing else "FAIL_STATIC_CONTROL"), checks)
    check("selectionRecomputed", closure.get("selectedCellId") == expected_selected and closure.get("selectedCandidateKind") == ("accepted" if passing else "relative-only"), checks)
    check("slowTipGateRecomputed", closure.get("slowTipUnlocked") is bool(passing), checks)
    check("zeroRecomputeCounts", closure.get("counts") == {
        "retainedBlenderStarts": 4, "retainedFluidDataBakes": 4, "retainedFluidMeshBakes": 4,
        "newBlenderStarts": 0, "newPhysicsBakes": 0, "newRenderCalls": 0,
        "networkCalls": 0, "engineRemoteWrites": 0,
    }, checks)
    check("retainedWorkManifestExact", read_json(CLOSURE_EVIDENCE / "retained-work-manifest.json") == manifest(RETAINED_WORK), checks)
    check("retainedEvidenceManifestExact", read_json(CLOSURE_EVIDENCE / "retained-evidence-manifest.json") == manifest(RETAINED_EVIDENCE), checks)
    check("closureManifestExact", read_json(CLOSURE_EVIDENCE / "closure-manifest.json") == manifest(CLOSURE_EVIDENCE, exclusions=("closure-manifest.json", "independent-audit.json")), checks)
    check("resourceCeilings", closure["resources"]["retainedWorkBytes"] <= spec["resourceCeilings"]["retainedWorkBytes"] and closure["resources"]["retainedEvidenceBytes"] <= spec["resourceCeilings"]["retainedEvidenceBytes"] and closure["resources"]["freeBytesAfter"] >= spec["resourceCeilings"]["minimumFreeBytesAfter"], checks)

    committed_exact = True
    commit = admission["researchCommit"]
    for relative in list(spec["tools"]) + [str(SPEC.relative_to(RESEARCH))]:
        shown = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=RESEARCH, capture_output=True, check=False)
        committed_exact = committed_exact and shown.returncode == 0 and bytes_sha(shown.stdout) == sha(RESEARCH / relative)
    check("committedToolAndSpecBytesExact", committed_exact, checks)
    audit = {
        "schemaVersion": "bfs.rc6LiquidSourceClearanceC2IndependentAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "scientificVerdict": closure["scientificVerdict"],
        "slowTipUnlocked": closure["slowTipUnlocked"],
        "selectedCellId": closure["selectedCellId"],
        "checks": checks,
        "cellChecks": cell_checks,
        "checksPassed": sum(checks.values()),
        "checksTotal": len(checks),
        "closureHash": closure["closureHash"],
        "claimCeiling": spec["claimCeiling"],
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    write_exclusive(audit_path, audit)
    print(canonical({
        "status": audit["status"], "scientificVerdict": audit["scientificVerdict"],
        "slowTipUnlocked": audit["slowTipUnlocked"], "selectedCellId": audit["selectedCellId"],
        "checks": f"{audit['checksPassed']}/{audit['checksTotal']}", "auditHash": audit["auditHash"],
    }))
    if audit["status"] != "PASS":
        raise RuntimeError("RC6 C2 closure independent audit failed")


if __name__ == "__main__":
    main()
