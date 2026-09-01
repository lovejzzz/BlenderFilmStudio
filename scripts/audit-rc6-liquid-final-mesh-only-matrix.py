#!/usr/bin/env python3
"""Independently audit the copied-data resolution-192 mesh-only matrix."""

import hashlib
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
RETAINED_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-source-clearance-final-c2-attempt-27")
RETAINED_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-source-clearance-final-c2-attempt-27"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-final-mesh-only-attempt-28")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-final-mesh-only-attempt-28"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-final-mesh-only-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-liquid-final-mesh-only-matrix.py"
AUDITOR = Path(__file__).resolve()
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-final-mesh-only.v0.28.json"
RETAINED_CELL = RETAINED_WORK / "clearance-35mm-res192"
RETAINED_BLEND = RETAINED_CELL / "baked-state.blend"
RETAINED_CACHE = RETAINED_CELL / "mantaflow-cache"
CELLS = (("mesh-radius-8p0", 8.0), ("mesh-radius-9p0", 9.0), ("mesh-radius-9p5", 9.5), ("mesh-radius-10p0", 10.0))
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


def expected_data_files():
    return sorted(
        [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
        + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
    )


def expected_all_files():
    return sorted(expected_data_files() + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)])


def data_manifest(cache_root):
    files = []
    for relative in expected_data_files():
        path = cache_root / relative
        if not path.is_file() or path.is_symlink():
            return None
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha(path)})
    value = {"schemaVersion": "bfs.rc6LiquidDataManifest.v0.1", "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def cache_roster(cache_root):
    return sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())


def expected_argv(cell_id, radius, retained_data_hash):
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(WORK / cell_id / "copied-baked-state.blend"), "--python", str(SCENE_TOOL), "--",
        "--cell-id", cell_id, "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--mesh-particle-radius", str(radius), "--retained-data-manifest-hash", retained_data_hash,
    ]


def signed_topology_passes(result, thresholds):
    for sample in result["samples"]:
        components = sample.get("components", [])
        positive = [item for item in components if item["signedVolumeCubicMeters"] > 1e-12]
        negative = [item for item in components if item["signedVolumeCubicMeters"] < -1e-12]
        if len(positive) != 1 or len(negative) > thresholds["maximumNegativeNestedShellCount"] or any(item["nonManifoldEdgeCount"] for item in components):
            return False
        outer = positive[0]
        for inner in negative:
            contained = all(inner["boundsMinWorld"][axis] >= outer["boundsMinWorld"][axis] - 1e-7 and inner["boundsMaxWorld"][axis] <= outer["boundsMaxWorld"][axis] + 1e-7 for axis in range(3))
            separation = sum((inner["centroidWorld"][axis] - outer["centroidWorld"][axis]) ** 2 for axis in range(3)) ** 0.5
            if not contained or separation > thresholds["maximumNestedCentroidSeparationMeters"]:
                return False
    return True


def cell_passes(result, thresholds):
    metrics = result["metrics"]
    return (
        metrics["maximumAbsoluteSourceVolumeErrorFraction"] <= thresholds["maximumAbsoluteSourceVolumeErrorFraction"]
        and metrics["maximumAbsoluteVolumeDriftFraction"] <= thresholds["maximumAbsoluteTemporalDriftFraction"]
        and metrics["maximumOutsideCupInteriorPlusOneVoxelFraction"] <= thresholds["maximumOutsideCupInteriorPlusOneVoxelFraction"]
        and metrics["maximumNonManifoldEdgeCount"] == thresholds["maximumNonManifoldEdgeCount"]
        and signed_topology_passes(result, thresholds)
    )


def check(label, condition, checks):
    checks[label] = bool(condition)


def main():
    audit_path = EVIDENCE / "independent-audit.json"
    if audit_path.exists():
        raise RuntimeError("mesh-only independent audit path is not fresh")
    spec = read_json(SPEC)
    admission = read_json(EVIDENCE / "admission.json")
    matrix = read_json(EVIDENCE / "matrix.json")
    retained_data = data_manifest(RETAINED_CACHE)
    checks = {}
    check("specSelfHash", spec.get("specHash") == self_hash(spec, "specHash") and spec.get("status") == "FROZEN", checks)
    check("toolRosterExact", spec.get("tools") == {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR),
    }, checks)
    check("rootsExact", spec["roots"] == {"retainedWork": str(RETAINED_WORK), "retainedEvidence": str(RETAINED_EVIDENCE), "work": str(WORK), "evidence": str(EVIDENCE)}, checks)
    check("inputIdentities", sha(BINARY) == spec["inputs"]["binarySha256"] == admission["binarySha256"] and sha(RETAINED_BLEND) == spec["inputs"]["retainedBakedStateSha256"] == admission["retainedBakedStateSha256"], checks)
    retained_work_manifest = read_json(RETAINED_EVIDENCE / "work-manifest.json")
    check("retainedWorkManifestExact", retained_work_manifest == manifest(RETAINED_WORK) and sha(RETAINED_EVIDENCE / "work-manifest.json") == spec["inputs"]["retainedWorkManifestFileSha256"], checks)
    check("retainedDataManifestExact", retained_data is not None and retained_data["manifestHash"] == spec["inputs"]["retainedDataManifestHash"] and read_json(EVIDENCE / "retained-data-manifest.json") == retained_data, checks)
    check("admissionSelfHash", admission.get("admissionHash") == self_hash(admission, "admissionHash") and admission.get("status") == "PASS", checks)
    check("matrixSelfHash", matrix.get("matrixHash") == self_hash(matrix, "matrixHash"), checks)
    check("executionPass", matrix.get("status") == "PASS_EXECUTION", checks)
    check("countCeilingsExact", matrix.get("counts") == {"blenderStarts": 4, "fluidDataBakes": 0, "fluidMeshBakes": 4, "blendSaves": 4, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}, checks)
    check("noSymlinks", not any(path.is_symlink() for root in (RETAINED_WORK, WORK, EVIDENCE) for path in root.rglob("*")), checks)
    check("zeroRenderMedia", not any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (WORK, EVIDENCE) for path in root.rglob("*")), checks)

    results = []
    process_checks = []
    for index, (cell_id, radius) in enumerate(CELLS, start=1):
        process_path = EVIDENCE / "processes" / f"{index:02d}-{cell_id}.json"
        stdout_path = EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stdout.log"
        stderr_path = EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stderr.log"
        result_path = EVIDENCE / "cells" / cell_id / "result.json"
        process = read_json(process_path)
        result = read_json(result_path)
        candidate_root = WORK / cell_id
        copied_blend = candidate_root / "copied-baked-state.blend"
        cache_root = candidate_root / "mantaflow-cache"
        baked = result["bakedState"]
        baked_path = Path(baked["uri"])
        row = {
            "cellId": cell_id,
            "processSelfHash": process.get("processHash") == self_hash(process, "processHash"),
            "argvExact": process.get("argv") == expected_argv(cell_id, radius, retained_data["manifestHash"]),
            "cwdExact": process.get("cwd") == str(RESEARCH),
            "exitZero": process.get("exitCode") == 0,
            "logsExact": sha(stdout_path) == process.get("stdoutSha256") and sha(stderr_path) == process.get("stderrSha256") and stderr_path.stat().st_size == 0 and "RC6_FINAL_MESH_ONLY=" in stdout_path.read_text(encoding="utf-8", errors="replace"),
            "resultSelfHash": result.get("resultHash") == self_hash(result, "resultHash") and result.get("status") == "MEASURED" and result.get("cellId") == cell_id,
            "configurationExact": result.get("configuration") == {
                "frameStart": 1, "frameEnd": 7, "resolutionMax": 192, "baseVoxelMeters": 0.0026041667,
                "particleNumber": 2, "particleRadius": 1.6, "meshScale": 2, "meshParticleRadius": radius,
                "sourceBottomClearanceMeters": 0.0350000039, "sourceBottomClearanceVoxels": 13.44000149,
                "sourceDimensionsMeters": [0.1099999994, 0.1099999994, 0.1400000006],
                "retainedDataManifestHash": retained_data["manifestHash"],
            },
            "authorityExact": result.get("authority") == {"retainedDataCopied": True, "fluidDataBakes": 0, "fluidMeshBakes": 1, "blendSaves": 1, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0},
            "sevenSamplesExact": [item.get("frame") for item in result.get("samples", [])] == list(range(1, 8)),
            "copiedBlendExact": copied_blend.is_file() and sha(copied_blend) == sha(RETAINED_BLEND),
            "dataUnchanged": data_manifest(cache_root) == retained_data,
            "cacheRosterExact": result.get("cacheFiles") == expected_all_files() and cache_roster(cache_root) == expected_all_files(),
            "bakedStateExact": baked_path.is_file() and baked_path.stat().st_size == baked["bytes"] and sha(baked_path) == baked["sha256"],
        }
        row["pass"] = all(value for key, value in row.items() if key != "cellId")
        process_checks.append(row)
        results.append(result)
    check("fourCellProcessAudits", len(process_checks) == 4 and all(row["pass"] for row in process_checks), checks)
    thresholds = spec["acceptanceThresholds"]
    passing = [row for row in results if cell_passes(row, thresholds)]
    ranked = sorted(results, key=lambda row: (
        not signed_topology_passes(row, thresholds),
        row["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"],
        row["metrics"]["maximumAbsoluteVolumeDriftFraction"],
        row["configuration"]["meshParticleRadius"],
    ))
    selected = (passing or ranked)[0]
    check("scientificVerdictRecomputed", matrix.get("scientificVerdict") == ("PASS_FINAL_STATIC" if passing else "FAIL_FINAL_STATIC"), checks)
    check("slowTipGateRecomputed", matrix.get("slowTipUnlocked") is bool(passing), checks)
    check("selectionRecomputed", matrix.get("selectedCellId") == selected["cellId"] and matrix.get("selectedCandidateKind") == ("accepted" if passing else "relative-only"), checks)
    check("matrixCellsExact", matrix.get("cells") == [{
        "cellId": row["cellId"], "meshParticleRadius": row["configuration"]["meshParticleRadius"],
        "passesFinalStatic": cell_passes(row, thresholds), "resultHash": row["resultHash"], "metrics": row["metrics"],
    } for row in results], checks)
    ceilings = spec["resourceCeilings"]
    check("resourceCeilings", tree_bytes(WORK) <= ceilings["workBytes"] and tree_bytes(EVIDENCE) <= ceilings["evidenceBytes"] and matrix["resources"]["freeBytesAfter"] >= ceilings["minimumFreeBytesAfter"], checks)
    check("workManifestExact", read_json(EVIDENCE / "work-manifest.json") == manifest(WORK), checks)
    check("evidenceManifestExact", read_json(EVIDENCE / "evidence-manifest.json") == manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")), checks)
    commit = admission["researchCommit"]
    committed_exact = True
    for relative in list(spec["tools"]) + [str(SPEC.relative_to(RESEARCH))]:
        shown = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=RESEARCH, capture_output=True, check=False)
        committed_exact = committed_exact and shown.returncode == 0 and bytes_sha(shown.stdout) == sha(RESEARCH / relative)
    check("committedToolAndSpecBytesExact", committed_exact, checks)

    audit = {
        "schemaVersion": "bfs.rc6LiquidFinalMeshOnlyIndependentAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "scientificVerdict": matrix["scientificVerdict"], "slowTipUnlocked": matrix["slowTipUnlocked"],
        "selectedCellId": matrix["selectedCellId"], "checks": checks, "processChecks": process_checks,
        "checksPassed": sum(checks.values()), "checksTotal": len(checks), "matrixHash": matrix["matrixHash"],
        "claimCeiling": spec["claimCeiling"],
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    write_exclusive(audit_path, audit)
    print(canonical({"status": audit["status"], "scientificVerdict": audit["scientificVerdict"], "slowTipUnlocked": audit["slowTipUnlocked"], "selectedCellId": audit["selectedCellId"], "checks": f"{audit['checksPassed']}/{audit['checksTotal']}", "auditHash": audit["auditHash"]}))
    if audit["status"] != "PASS":
        raise RuntimeError("mesh-only independent audit failed")


if __name__ == "__main__":
    main()
