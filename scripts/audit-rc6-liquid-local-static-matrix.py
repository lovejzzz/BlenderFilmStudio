#!/usr/bin/env python3
"""Independently audit RC6 attempt-19 local-domain static Mantaflow evidence."""

import hashlib
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-local-static-attempt-19")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-local-static-attempt-19"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-local-static-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-liquid-local-static-matrix.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-local-static.v0.19.json"
CELLS = (("radius-1p0", 1.0), ("radius-1p1", 1.1), ("radius-1p2", 1.2), ("radius-1p3", 1.3))
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


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def manifest(root, exclusions=()):
    excluded = {str(value) for value in exclusions}
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


def expected_argv(cell_id, radius):
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(SOURCE_BLEND), "--python", str(SCENE_TOOL), "--",
        "--cell-id", cell_id, "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--resolution", "96", "--frame-end", "7", "--particle-radius", str(radius), "--particle-number", "2",
    ]


def cell_passes(row, thresholds):
    metrics = row["metrics"]
    return (
        metrics["maximumNonManifoldEdgeCount"] == 0
        and metrics["maximumConnectedComponentCount"] <= thresholds["maximumConnectedComponentCount"]
        and metrics["minimumLargestComponentFraction"] >= thresholds["minimumLargestComponentFraction"]
        and metrics["maximumAbsoluteVolumeDriftFraction"] <= thresholds["maximumAbsoluteTemporalDriftFraction"]
        and metrics["maximumAbsoluteSourceVolumeErrorFraction"] <= thresholds["maximumAbsoluteSourceVolumeErrorFraction"]
        and metrics["maximumOutsideCupInteriorPlusOneVoxelFraction"] <= thresholds["maximumOutsideCupInteriorPlusOneVoxelFraction"]
    )


def check(label, condition, checks):
    checks[label] = bool(condition)


def main():
    audit_path = EVIDENCE / "independent-audit.json"
    if audit_path.exists():
        raise RuntimeError("independent audit path is not fresh")
    spec = read_json(SPEC)
    admission = read_json(EVIDENCE / "admission.json")
    matrix = read_json(EVIDENCE / "matrix.json")
    checks = {}
    check("specSelfHash", spec.get("specHash") == self_hash(spec, "specHash") and spec.get("status") == "FROZEN", checks)
    expected_tools = {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve()),
    }
    check("toolRosterExact", spec.get("tools") == expected_tools, checks)
    check("inputBinaryExact", sha(BINARY) == spec["inputs"]["binarySha256"] == admission["binarySha256"], checks)
    check("inputSourceBlendExact", sha(SOURCE_BLEND) == spec["inputs"]["sourceBlendSha256"] == admission["sourceBlendSha256"], checks)
    check("admissionSelfHash", admission.get("admissionHash") == self_hash(admission, "admissionHash") and admission.get("status") == "PASS", checks)
    check("matrixSelfHash", matrix.get("matrixHash") == self_hash(matrix, "matrixHash"), checks)
    check("executionPass", matrix.get("status") == "PASS_EXECUTION", checks)
    check("countCeilingsExact", matrix.get("counts") == {"blenderStarts": 4, "fluidDataBakes": 4, "fluidMeshBakes": 4, "blendSaves": 4, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}, checks)
    check("rootsExact", str(WORK) == spec["roots"]["work"] and str(EVIDENCE) == spec["roots"]["evidence"], checks)
    check("noSymlinks", not any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*")), checks)
    check("zeroRenderMedia", not any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (WORK, EVIDENCE) for path in root.rglob("*")), checks)

    results = []
    process_checks = []
    fixed = spec["matrix"]["fixed"]
    for index, (cell_id, radius) in enumerate(CELLS, start=1):
        process_path = EVIDENCE / "processes" / f"{index:02d}-{cell_id}.json"
        stdout_path = EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stdout.log"
        stderr_path = EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stderr.log"
        result_path = EVIDENCE / "cells" / cell_id / "result.json"
        process = read_json(process_path)
        result = read_json(result_path)
        expected_configuration = dict(fixed)
        expected_configuration["particleRadius"] = radius
        baked = result["bakedState"]
        baked_path = Path(baked["uri"])
        row = {
            "cellId": cell_id,
            "processSelfHash": process.get("processHash") == self_hash(process, "processHash"),
            "argvExact": process.get("argv") == expected_argv(cell_id, radius),
            "cwdExact": process.get("cwd") == str(RESEARCH),
            "exitZero": process.get("exitCode") == 0,
            "stdoutExact": sha(stdout_path) == process.get("stdoutSha256") and "RC6_STATIC_CALIBRATION=" in stdout_path.read_text(encoding="utf-8", errors="replace"),
            "stderrExact": sha(stderr_path) == process.get("stderrSha256") and not stderr_path.read_text(encoding="utf-8", errors="replace"),
            "resultSelfHash": result.get("resultHash") == self_hash(result, "resultHash") and result.get("status") == "MEASURED",
            "configurationExact": result.get("configuration") == expected_configuration,
            "sevenSamplesExact": [item.get("frame") for item in result.get("samples", [])] == list(range(1, 8)),
            "sourceMeshVolumeExact": abs(result["metrics"]["sourceMeshVolumeCubicMeters"] - spec["inputs"]["sourceMeshVolumeCubicMeters"]) <= 1e-15,
            "bakedStateExact": baked_path.is_file() and baked_path.stat().st_size == baked["bytes"] and sha(baked_path) == baked["sha256"],
        }
        row["pass"] = all(value for key, value in row.items() if key != "cellId")
        process_checks.append(row)
        results.append(result)
    check("fourCellProcessAudits", len(process_checks) == 4 and all(row["pass"] for row in process_checks), checks)

    thresholds = spec["acceptanceThresholds"]
    passing = [row for row in results if cell_passes(row, thresholds)]
    ranked = sorted(results, key=lambda row: (
        row["metrics"]["maximumNonManifoldEdgeCount"] > 0,
        row["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"],
        row["metrics"]["maximumAbsoluteVolumeDriftFraction"],
        row["metrics"]["maximumConnectedComponentCount"],
        -row["metrics"]["minimumLargestComponentFraction"],
        row["configuration"]["particleRadius"],
    ))
    expected_verdict = "PASS_STATIC_CONTROL" if passing else "FAIL_STATIC_CONTROL"
    expected_selected = (passing or ranked)[0]["cellId"]
    check("scientificVerdictRecomputed", matrix.get("scientificVerdict") == expected_verdict, checks)
    check("slowTipGateRecomputed", matrix.get("slowTipUnlocked") is bool(passing), checks)
    check("selectionRecomputed", matrix.get("selectedCellId") == expected_selected and matrix.get("selectedCandidateKind") == ("accepted" if passing else "relative-only"), checks)
    check("matrixCellsExact", matrix.get("cells") == [{
        "cellId": row["cellId"], "particleRadius": row["configuration"]["particleRadius"],
        "passesStaticControl": cell_passes(row, thresholds), "resultHash": row["resultHash"], "metrics": row["metrics"],
    } for row in results], checks)
    ceilings = spec["resourceCeilings"]
    check("resourceCeilings", tree_bytes(WORK) <= ceilings["workBytes"] and tree_bytes(EVIDENCE) <= ceilings["evidenceBytes"] and matrix["resources"]["freeBytesAfter"] >= ceilings["minimumFreeBytesAfter"], checks)
    check("workManifestExact", read_json(EVIDENCE / "work-manifest.json") == manifest(WORK), checks)
    check("evidenceManifestExact", read_json(EVIDENCE / "evidence-manifest.json") == manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")), checks)

    for label, item in spec["retainedEvidence"].items():
        path = RESEARCH / item["path"]
        check(f"retained_{label}", path.is_file() and sha(path) == item["sha256"], checks)
    commit = admission["researchCommit"]
    committed_exact = True
    for relative in list(spec["tools"]) + [str(SPEC.relative_to(RESEARCH))]:
        shown = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=RESEARCH, capture_output=True, check=False)
        committed_exact = committed_exact and shown.returncode == 0 and bytes_sha(shown.stdout) == sha(RESEARCH / relative)
    check("committedToolAndSpecBytesExact", committed_exact, checks)

    audit = {
        "schemaVersion": "bfs.rc6LiquidLocalStaticIndependentAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "executionStatus": matrix["status"],
        "scientificVerdict": matrix["scientificVerdict"],
        "slowTipUnlocked": matrix["slowTipUnlocked"],
        "selectedCellId": matrix["selectedCellId"],
        "checks": checks,
        "processChecks": process_checks,
        "checksPassed": sum(checks.values()),
        "checksTotal": len(checks),
        "matrixHash": matrix["matrixHash"],
        "claimCeiling": spec["claimCeiling"],
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    write_exclusive(audit_path, audit)
    print(canonical({"status": audit["status"], "scientificVerdict": audit["scientificVerdict"], "slowTipUnlocked": audit["slowTipUnlocked"], "checks": f'{audit["checksPassed"]}/{audit["checksTotal"]}', "auditHash": audit["auditHash"]}))
    if audit["status"] != "PASS":
        raise RuntimeError("RC6 local static independent audit failed")


if __name__ == "__main__":
    main()
