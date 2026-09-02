#!/usr/bin/env python3
"""Independently audit the Preview/Review obstacle level-set screen."""

import hashlib
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-obstacle-voxel-screen-attempt-39")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-obstacle-voxel-screen-attempt-39"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-obstacle-voxel-screen-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-liquid-obstacle-voxel-screen.py"
AUDITOR = Path(__file__).resolve()
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-obstacle-voxel-screen.v0.41.json"
CELLS = (
    ("preview-baseline", 96, 1.5),
    ("preview-effector-plus1", 96, 2.5),
    ("review-baseline", 128, 1.5),
)
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
    return [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    ]


def manifest(root, exclusions=()):
    excluded = set(exclusions)
    files = [entry for entry in file_entries(root) if entry["path"] not in excluded]
    value = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(root), "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def expected_argv(cell_id, resolution, distance):
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(SOURCE_BLEND), "--python", str(SCENE_TOOL), "--",
        "--cell-id", cell_id, "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--resolution", str(resolution), "--effector-surface-distance", str(distance),
    ]


def check(label, condition, checks):
    checks[label] = bool(condition)


def main():
    audit_path = EVIDENCE / "independent-audit.json"
    if audit_path.exists():
        raise RuntimeError("obstacle-voxel independent audit path is not fresh")
    spec = read_json(SPEC)
    admission = read_json(EVIDENCE / "admission.json")
    receipt = read_json(EVIDENCE / "receipt.json")
    checks = {}

    check("specSelfHash", spec.get("status") == "FROZEN" and spec.get("specHash") == self_hash(spec, "specHash"), checks)
    check("toolRosterExact", spec.get("tools") == {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR),
    }, checks)
    check("rootsExact", spec.get("roots") == {"work": str(WORK), "evidence": str(EVIDENCE)}, checks)
    check("inputsExact", sha(BINARY) == spec["inputs"]["binarySha256"] == admission["binarySha256"] and sha(SOURCE_BLEND) == spec["inputs"]["sourceBlendSha256"] == admission["sourceBlendSha256"], checks)
    check("admissionSelfHash", admission.get("status") == "PASS" and admission.get("admissionHash") == self_hash(admission, "admissionHash") and admission.get("specHash") == spec.get("specHash"), checks)

    all_processes = True
    all_results = True
    arithmetic_exact = True
    detail_exact = True
    cache_exact = True
    results = []
    process_hashes = []
    for index, (cell_id, resolution, distance) in enumerate(CELLS, start=1):
        process = read_json(EVIDENCE / f"processes/{index:02d}-{cell_id}.json")
        result = read_json(EVIDENCE / f"cells/{cell_id}/result.json")
        stdout_path = EVIDENCE / f"logs/{index:02d}-{cell_id}.stdout.log"
        stderr_path = EVIDENCE / f"logs/{index:02d}-{cell_id}.stderr.log"
        all_processes = all_processes and process.get("processHash") == self_hash(process, "processHash")
        all_processes = all_processes and process.get("argv") == expected_argv(cell_id, resolution, distance) and process.get("cwd") == str(RESEARCH)
        all_processes = all_processes and process.get("exitCode") == 0 and sha(stdout_path) == process.get("stdoutSha256") and sha(stderr_path) == process.get("stderrSha256") and stderr_path.stat().st_size == 0
        all_processes = all_processes and "RC6_OBSTACLE_VOXEL_SCREEN=" in stdout_path.read_text(encoding="utf-8", errors="replace")
        process_hashes.append(process["processHash"])

        config = dict(result.get("configuration", {}))
        initial_roster = (
            config.pop("initialUseFlipParticles", None),
            config.pop("initialParticleSystemCount", None),
        )
        base_voxel = round(0.5 / resolution, 10)
        expected_config = {
            "frameStart": 1, "frameEnd": 7, "resolutionMax": resolution, "baseVoxelMeters": base_voxel,
            "domainCenterMeters": [0.32, 0.0, 0.25], "domainDimensionsMeters": [0.36, 0.36, 0.5],
            "sourceDimensionsMeters": [0.1099999994, 0.1099999994, 0.1400000006],
            "sourceMeshVolumeCubicMeters": 0.0013283283766941, "sourceBottomClearanceMeters": 0.0350000039,
            "simulationMethod": "APIC", "useAdaptiveTimesteps": True, "timestepsMin": 1, "timestepsMax": 4,
            "cflCondition": 2.0, "particleNumber": 2, "particleRadius": 1.6, "useMesh": False,
            "useFlipParticles": True, "finalParticleSystemCount": 1, "displayPercentage": 100, "useFractions": True,
            "deleteInObstacle": False, "waterViscosityBase": 1.0, "waterViscosityExponent": 6,
            "flowSurfaceDistanceCells": 0.0, "cupEffectorSurfaceDistanceCells": distance,
            "cupEffectorIsPlanar": False, "cupEffectorEnabled": True, "cupEffectorSubframes": 0,
        }
        all_results = all_results and result.get("status") == "MEASURED_DATA_ONLY" and result.get("cellId") == cell_id and result.get("resultHash") == self_hash(result, "resultHash")
        all_results = all_results and initial_roster in {(False, 0), (False, 1), (True, 1)}
        all_results = all_results and config == expected_config and result.get("authority") == {
            "fluidDataBakes": 1, "fluidMeshBakes": 0, "blendSaves": 0,
            "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0,
        }
        all_results = all_results and [sample.get("frame") for sample in result.get("samples", [])] == list(range(1, 8))

        expected_cache = sorted(
            [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
            + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
        )
        cache_root = WORK / cell_id / "mantaflow-cache"
        actual_cache = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
        cache_exact = cache_exact and result.get("cacheFiles") == expected_cache and actual_cache == expected_cache

        for sample in result.get("samples", []):
            for row in (sample.get("strictInterior", {}), sample.get("oneVoxelEnvelope", {})):
                combos = row.get("exclusiveCombinations", {})
                count = row.get("particleCount", 0)
                union = row.get("outsideUnionCount", -1)
                arithmetic_exact = arithmetic_exact and sum(combos.values()) == count and union == count - combos.get("inside", 0)
                arithmetic_exact = arithmetic_exact and row.get("radialCount") == combos.get("radialOnly", 0) + combos.get("radialAndBelow", 0) + combos.get("radialAndAbove", 0) + combos.get("allThree", 0)
                arithmetic_exact = arithmetic_exact and row.get("belowFloorCount") == combos.get("belowOnly", 0) + combos.get("radialAndBelow", 0) + combos.get("belowAndAbove", 0) + combos.get("allThree", 0)
                arithmetic_exact = arithmetic_exact and row.get("aboveRimCount") == combos.get("aboveOnly", 0) + combos.get("radialAndAbove", 0) + combos.get("belowAndAbove", 0) + combos.get("allThree", 0)
            details = sample.get("outliersOneVoxel", [])
            detail_exact = detail_exact and len(details) == sample.get("oneVoxelEnvelope", {}).get("outsideUnionCount")
            for detail in details:
                local = detail.get("locationCupLocal", [])
                if len(local) != 3:
                    detail_exact = False
                    continue
                radial = (local[0] * local[0] + local[1] * local[1]) ** 0.5
                radial_out = radial > 0.09 + 0.5 / resolution
                below_out = local[2] < -0.16 - 0.5 / resolution
                above_out = local[2] > 0.22 + 0.5 / resolution
                region = "INSIDE_CUP_SOLID_FLOOR" if radial <= 0.15 and -0.22 <= local[2] < -0.16 else ("BELOW_CUP_OUTER_BOTTOM" if local[2] < -0.22 else ("INSIDE_CUP_SOLID_WALL" if 0.09 < radial <= 0.15 and -0.22 <= local[2] <= 0.22 else "OUTSIDE_MODELED_CUP_SOLID"))
                detail_exact = detail_exact and detail.get("detailHash") == self_hash(detail, "detailHash") and detail.get("aliveState") == "ALIVE"
                detail_exact = detail_exact and detail.get("physicalRegion") == region and detail.get("radialOutsideOneVoxel") == radial_out and detail.get("belowFloorOneVoxel") == below_out and detail.get("aboveRimOneVoxel") == above_out and (radial_out or below_out or above_out)
                expected_penetration = round(max(0.0, -0.16 - local[2]), 8)
                detail_exact = detail_exact and abs(detail.get("interiorFloorPenetrationMeters") - expected_penetration) <= 0.00000001
        results.append(result)

    check("processesAndLogsExact", all_processes, checks)
    check("resultsAndConfigurationExact", all_results, checks)
    check("cacheRostersExact", cache_exact, checks)
    check("axisArithmeticExact", arithmetic_exact, checks)
    check("outlierDetailsExact", detail_exact, checks)

    by_id = {result["cellId"]: result for result in results}
    preview_base = by_id["preview-baseline"]["metrics"]["maximumOneVoxelOutlierCount"]
    preview_plus = by_id["preview-effector-plus1"]["metrics"]["maximumOneVoxelOutlierCount"]
    review_base = by_id["review-baseline"]["metrics"]["maximumOneVoxelOutlierCount"]
    surface_signal = preview_base > 0 and preview_plus == 0
    resolution_signal = preview_base != review_base
    if surface_signal:
        expected_status, expected_next = "PASS_SURFACE_DISTANCE_SIGNAL", "review-effector-plus1"
    elif resolution_signal:
        expected_status = "PASS_RESOLUTION_SIGNAL"
        expected_next = "review-effector-plus1" if review_base > 0 else "final-resolution-baseline-reproduction"
    elif preview_base == 0 and preview_plus == 0 and review_base == 0:
        expected_status, expected_next = "INCONCLUSIVE_LOWER_TIERS_CONTAINED", "final-resolution-effector-paired-screen"
    else:
        expected_status, expected_next = "FAIL_OBSTACLE_VOXEL_SCREEN_NO_CORRECTION", "cup-topology-and-transform-audit"
    expected_cells = [{
        "cellId": result["cellId"], "resolutionMax": result["configuration"]["resolutionMax"],
        "cupEffectorSurfaceDistanceCells": result["configuration"]["cupEffectorSurfaceDistanceCells"],
        "maximumOneVoxelOutlierCount": result["metrics"]["maximumOneVoxelOutlierCount"],
        "maximumOneVoxelOutlierFraction": result["metrics"]["maximumOneVoxelOutlierFraction"],
        "framesWithOneVoxelOutliers": result["metrics"]["framesWithOneVoxelOutliers"],
        "maximumInteriorFloorPenetrationMeters": result["metrics"]["maximumInteriorFloorPenetrationMeters"],
        "outlierPhysicalRegions": result["metrics"]["outlierPhysicalRegions"],
        "wallSeconds": result["metrics"]["wallSeconds"], "resultHash": result["resultHash"],
    } for result in results]
    check("receiptSelfHash", receipt.get("receiptHash") == self_hash(receipt, "receiptHash"), checks)
    check("interpretationRecomputed", receipt.get("status") == expected_status and receipt.get("nextCell") == expected_next and receipt.get("surfaceDistanceSignal") == surface_signal and receipt.get("resolutionSignal") == resolution_signal and receipt.get("cells") == expected_cells, checks)
    check("countCeilingsExact", receipt.get("counts") == {"blenderStarts": 3, "fluidDataBakes": 3, "fluidMeshBakes": 0, "blendSaves": 0, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0} and receipt.get("processHashes") == process_hashes, checks)
    ceilings = spec["resourceCeilings"]
    check("resourceCeilings", tree_bytes(WORK) <= ceilings["workBytes"] and tree_bytes(EVIDENCE) <= ceilings["evidenceBytes"] and receipt["resources"]["freeBytesAfter"] >= ceilings["minimumFreeBytesAfter"], checks)
    check("noSymlinksOrMedia", not any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*")) and not any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (WORK, EVIDENCE) for path in root.rglob("*")), checks)
    check("workManifestExact", read_json(EVIDENCE / "work-manifest.json") == manifest(WORK), checks)
    check("evidenceManifestExact", read_json(EVIDENCE / "evidence-manifest.json") == manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")), checks)

    commit = admission["researchCommit"]
    committed_exact = True
    for relative in list(spec["tools"]) + [str(SPEC.relative_to(RESEARCH))]:
        shown = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=RESEARCH, capture_output=True, check=False)
        committed_exact = committed_exact and shown.returncode == 0 and hashlib.sha256(shown.stdout).hexdigest() == sha(RESEARCH / relative)
    check("committedToolAndSpecBytesExact", committed_exact, checks)

    audit = {
        "schemaVersion": "bfs.rc6LiquidObstacleVoxelScreenIndependentAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "screenVerdict": receipt["status"],
        "nextCell": receipt["nextCell"],
        "checks": checks,
        "checksPassed": sum(checks.values()),
        "checksTotal": len(checks),
        "receiptHash": receipt["receiptHash"],
        "resultHashes": [result["resultHash"] for result in results],
        "claimCeiling": spec["claimCeiling"],
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    write_exclusive(audit_path, audit)
    print(canonical({"status": audit["status"], "checks": f"{audit['checksPassed']}/{audit['checksTotal']}", "screenVerdict": audit["screenVerdict"], "auditHash": audit["auditHash"]}))
    if audit["status"] != "PASS":
        raise RuntimeError("obstacle-voxel independent audit failed")


if __name__ == "__main__":
    main()
