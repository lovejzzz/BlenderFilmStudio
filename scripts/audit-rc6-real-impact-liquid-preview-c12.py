#!/usr/bin/env python3
"""Independently audit the bounded R40 Bullet plus APIC Preview experiment."""

import hashlib
import json
import math
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend")
STATIC_CACHE = SOURCE.parent / "mantaflow-cache"
TRAJECTORY = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-passive-ramp-c10-attempt-82/cells/R40/result.json"
ATTEMPT70_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-particle-band-width-attempt-70/result.json"
ATTEMPT70_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-particle-band-width-attempt-70/independent-audit.json"
C11_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-event-window-c11-attempt-83/event-window-audit.json"
SCENE_TOOL = RESEARCH / "scripts/run-rc6-real-impact-liquid-preview-c12-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-real-impact-liquid-preview-c12.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-liquid-preview-c12.v0.95.json"
EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-preview-c12-preregistration.md",
    "research/lab-journal.md",
    "scripts/audit-rc6-real-impact-liquid-preview-c12.py",
    "scripts/run-rc6-real-impact-liquid-preview-c12-scene.py",
    "scripts/run-rc6-real-impact-liquid-preview-c12.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-preview-c12.v0.95.json",
}


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


def manifest(root, exclude=()):
    excluded = {Path(item) for item in exclude}
    rows = [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root) not in excluded
    ]
    value = {"root": str(root), "files": rows}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def quaternion_angle_degrees(first, second):
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    dot = abs(sum(a * b for a, b in zip(first, second)) / (first_norm * second_norm))
    return math.degrees(2.0 * math.acos(min(1.0, max(-1.0, dot))))


spec = json.loads(SPEC.read_text())
result = json.loads((EVIDENCE / "result.json").read_text())
receipt = json.loads((EVIDENCE / "receipt.json").read_text())
process = json.loads((EVIDENCE / "processes/01-real-impact-liquid.json").read_text())
admission = json.loads((EVIDENCE / "admission.json").read_text())
trajectory = json.loads(TRAJECTORY.read_text())
attempt70_result = json.loads(ATTEMPT70_RESULT.read_text())
attempt70_audit = json.loads(ATTEMPT70_AUDIT.read_text())
c11_audit = json.loads(C11_AUDIT.read_text())
work_manifest = json.loads((EVIDENCE / "work-manifest.json").read_text())
preaudit_manifest = json.loads((EVIDENCE / "evidence-manifest.pre-audit.json").read_text())

fluid = result["fluidSamples"]
bullet = result["bulletSamples"]
post_bullet = result["postFluidBulletSamples"]
expected_trajectory = {row["frame"]: row for row in trajectory["samples"] if 1 <= row["frame"] <= 36}
source_volume = result["configuration"]["sourceMeshVolumeCubicMeters"]
initial_volume = fluid[0]["meshVolumeCubicMeters"]
source_error = max(abs(row["meshVolumeCubicMeters"] / source_volume - 1.0) for row in fluid)
temporal_drift = max(abs(row["meshVolumeCubicMeters"] / initial_volume - 1.0) for row in fluid)
centroid_shift = max(math.dist(row["centroidCupLocalMeters"], fluid[0]["centroidCupLocalMeters"]) for row in fluid)
contact = next((row["frame"] for row in bullet if row["ballCupCollisionSurfaceSeparationMeters"] <= 0.01), None)
first_seventy = next((row["frame"] for row in bullet if row["cupTiltDegrees"] >= 70.0), None)
maximum_surface = max(row["cupSurfaceDisplacementFromPriorFrameMeters"] for row in bullet)
required_subframes = max(1, math.ceil(maximum_surface / 0.009375))
precontact = [row for row in fluid if contact is not None and row["frame"] < contact]
postcontact = [row for row in fluid if contact is not None and row["frame"] > contact]
precontact_exterior = max((row["outsideCupInteriorPlusOneVoxelFraction"] for row in precontact), default=1.0)
first_spill = next((row["frame"] for row in postcontact if row["outsideCupInteriorPlusOneVoxelFraction"] >= 0.05), None)
postcontact_exterior = max((row["outsideCupInteriorPlusOneVoxelFraction"] for row in postcontact), default=0.0)

def trajectory_deltas(rows):
    return (
        max(math.dist(row["cupLocation"], expected_trajectory[row["frame"]]["cupLocation"]) for row in rows),
        max(quaternion_angle_degrees(row["cupRotationQuaternion"], expected_trajectory[row["frame"]]["cupRotationQuaternion"]) for row in rows),
        max(math.dist(row["ballLocation"], expected_trajectory[row["frame"]]["ballLocation"]) for row in rows),
    )


before_deltas = trajectory_deltas(bullet)
after_deltas = trajectory_deltas(post_bullet)
cache_root = WORK / "mantaflow-cache"
cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
expected_cache = sorted(
    [f"config/config_{frame:04d}.uni" for frame in range(1, 37)]
    + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 37)]
    + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 37)]
)
configuration = result["configuration"]
provenance = result["provenance"]
ramp = provenance["ramp"]
support_effectors = provenance["staticSupportEffectors"]

recomputed_checks = {
    "exactRetainedR40SameSolveBeforeFluid": before_deltas[0] <= 1e-5 and before_deltas[1] <= 1e-4 and before_deltas[2] <= 1e-5,
    "exactRetainedR40SameSolveAfterFluid": after_deltas[0] <= 1e-5 and after_deltas[1] <= 1e-4 and after_deltas[2] <= 1e-5,
    "derivedCausalEventWindowExact": contact == 19 and first_seventy == 36,
    "derivedEffectorSubframesExact": required_subframes == 8 and configuration["cupEffectorSubframes"] == 8,
    "cupCollisionMarginExplicitTwoMillimeters": configuration["cupUseMargin"] and abs(configuration["cupCollisionMarginMeters"] - 0.002) <= 1e-6 and not provenance["sourceCupUseMargin"] and abs(provenance["sourceCupCollisionMarginMeters"] - 0.04) <= 1e-6 and abs(configuration["cupFriction"] - 0.75) <= 1e-6,
    "passiveRampExact": ramp == {
        "animationCurveCount": 0, "rigidBodyType": "PASSIVE", "collisionShape": "CONVEX_HULL",
        "friction": ramp["friction"], "restitution": ramp["restitution"], "useMargin": True,
        "collisionMarginMeters": ramp["collisionMarginMeters"], "vertexCount": 8, "polygonCount": 6,
    } and abs(ramp["friction"] - 0.55) <= 1e-6 and abs(ramp["restitution"] - 0.08) <= 1e-6 and abs(ramp["collisionMarginMeters"] - 0.002) <= 1e-6 and configuration["rampRunMeters"] == 0.3 and configuration["rampRiseMeters"] == 0.04 and configuration["rampWidthMeters"] == 0.4 and configuration["rampSurfaceStartZ"] == 0.22 and configuration["rampSurfaceEndZ"] == 0.26,
    "floorAndRampStaticFluidEffectorsExact": len(support_effectors) == 2 and {row["role"] for row in support_effectors} == {"floor", "ramp"} and all(row["fluidType"] == "EFFECTOR" and row["rigidBodyType"] == "PASSIVE" and abs(row["surfaceDistanceCells"] - 2.0) <= 1e-6 and row["useEffector"] and not row["usePlaneInit"] and row["subframes"] == 0 for row in support_effectors),
    "pusherOnlyAuthoredRigidActuator": provenance["animatedRigidBodies"] == ["PHYS_VISIBLE_STRIKER"] and provenance["pusherKeyframes"] == [1, 9, 10, 12],
    "zeroBallCupOutcomePoseAuthority": provenance["cupActionCurveCount"] == 0 and provenance["ballActionCurveCount"] == 0,
    "exactCacheFrameRoster": cache_files == expected_cache,
    "liquidMeshEveryFrame": len(fluid) == 36 and all(row["vertexCount"] > 0 for row in fluid),
    "sourceRelativeVolumeWithin25Percent": source_error <= 0.25,
    "temporalVolumeDriftWithin15Percent": temporal_drift <= 0.15,
    "positiveLiquidBodiesBounded": min(row["positiveBodyCount"] for row in fluid) >= 1 and max(row["positiveBodyCount"] for row in fluid) <= 16,
    "manifoldEveryFrame": max(row["nonManifoldEdgeCount"] for row in fluid) == 0,
    "largestComponentAtLeastHalf": min(row["largestComponentFraction"] for row in fluid) >= 0.5,
    "connectedComponentsBounded": max(row["connectedComponentCount"] for row in fluid) <= 32,
    "precontactLiquidContained": precontact_exterior < 0.05,
    "significantSpillDerivedAfterContact": first_spill is not None and first_spill > contact and postcontact_exterior >= 0.05,
    "spillPersistsAtEventBoundary": fluid[-1]["outsideCupInteriorPlusOneVoxelFraction"] >= 0.05,
    "impactMovesLiquidRelativeToCup": centroid_shift >= 0.025,
    "worldFloorIntrusionWithinOnePercent": max(row["worldBelowFloorFraction"] for row in fluid) <= 0.01,
    "cupSolidIntrusionWithinOnePercent": max(row["cupSolidIntrusionFraction"] for row in fluid) <= 0.01,
    "rampSolidIntrusionWithinOnePercent": max(row["rampSolidIntrusionFraction"] for row in fluid) <= 0.01,
    "liquidInsideDomainOneVoxelInset": max(row["domainOutsideOneVoxelInsetFraction"] for row in fluid) == 0.0,
    "singleInitialGeometryFlow": provenance["sourceFlowBehavior"] == "GEOMETRY" and provenance["sourceAnimationCurveCount"] == 0,
    "previewTierExact": (
        configuration["frameStart"] == 1 and configuration["frameEnd"] == 36 and configuration["resolutionMax"] == 96
        and all(abs(actual - expected) <= 1e-6 for actual, expected in zip(configuration["domainCenterMeters"], (0.57, 0.0, 0.26)))
        and all(abs(actual - expected) <= 1e-6 for actual, expected in zip(configuration["domainDimensionsMeters"], (0.9, 0.5, 0.58)))
        and configuration["trajectoryCellId"] == "R40" and configuration["driveEndFrame"] == 9
        and configuration["bulletSubstepsPerFrame"] == 20 and configuration["bulletSolverIterations"] == 80
        and configuration["simulationMethod"] == "APIC" and configuration["particleNumber"] == 2
        and configuration["particleMinimum"] == 8 and configuration["particleMaximum"] == 16
        and abs(configuration["particleRadius"] - 1.8) <= 1e-6 and abs(configuration["particleBandWidth"] - 4.0) <= 1e-6
        and abs(configuration["meshParticleRadius"] - 2.5) <= 1e-6 and configuration["meshScale"] == 2
        and abs(configuration["meshConcaveLower"] - 0.4) <= 1e-6 and abs(configuration["meshConcaveUpper"] - 3.5) <= 1e-6
        and configuration["meshSmoothenPos"] == 1 and configuration["meshSmoothenNeg"] == 1
        and configuration["useFractions"] and abs(configuration["fractionsThreshold"] - 0.05) <= 1e-6
        and abs(configuration["fractionsDistance"] - 0.25) <= 1e-6 and not configuration["deleteInObstacle"]
        and abs(configuration["cupEffectorSurfaceDistanceCells"] - 2.0) <= 1e-6 and configuration["cupEffectorSubframes"] == 8
        and configuration["timestepsMin"] == 2 and configuration["timestepsMax"] == 4 and abs(configuration["cflCondition"] - 2.0) <= 1e-6
    ),
}

tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
stdout = EVIDENCE / "logs/01-real-impact-liquid.stdout.log"
stderr = EVIDENCE / "logs/01-real-impact-liquid.stderr.log"
source_copy = WORK / "source-state-copy.blend"
expected_argv = [str(BINARY), "--background", str(source_copy), "--python", str(SCENE_TOOL), "--", "--work-root", str(WORK), "--evidence-root", str(EVIDENCE), "--trajectory-json", str(TRAJECTORY), "--source-copy", str(source_copy)]
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
parent = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
freeze_paths = set(subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.splitlines())

checks = {
    "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "frozenToolIdentities": tools == {str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL), str(RUNNER.relative_to(RESEARCH)): sha(RUNNER), str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve())},
    "freezeCommitBound": parent == spec["researchParentBeforePreregistration"] and freeze_paths == EXPECTED_FREEZE_PATHS and head == receipt["researchExecutionCommit"],
    "baselineFilesExact": sha(BINARY) == spec["baseline"]["binarySha256"] and sha(SOURCE) == spec["baseline"]["sourceBlendSha256"] and sha(TRAJECTORY) == spec["baseline"]["trajectoryFileSha256"] and sha(ATTEMPT70_RESULT) == spec["baseline"]["attempt70ResultFileSha256"] and sha(ATTEMPT70_AUDIT) == spec["baseline"]["attempt70AuditFileSha256"] and sha(C11_AUDIT) == spec["baseline"]["c11AuditFileSha256"],
    "acceptedLineageExact": trajectory["cellId"] == "R40" and trajectory["status"] == "FAIL" and trajectory["resultHash"] == spec["baseline"]["trajectoryResultHash"] and attempt70_result["status"] == "PASS" and attempt70_result["resultHash"] == spec["baseline"]["attempt70ResultHash"] and attempt70_audit["status"] == "PASS" and c11_audit["status"] == "PASS" and c11_audit["auditHash"] == spec["baseline"]["c11AuditHash"],
    "admissionExact": admission["status"] == "PASS" and admission["workRootAbsentBeforeRun"] and admission["evidenceRootAbsentBeforeRun"] and admission["freeBytes"] >= spec["resourceCeilings"]["minimumReserveBytes"] + spec["resourceCeilings"]["projectedWriteBytes"],
    "resultSelfHash": result["resultHash"] == self_hash(result, "resultHash"),
    "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash") and receipt["resultHash"] == result["resultHash"],
    "processSelfHashArgvAndLogs": process["processHash"] == self_hash(process, "processHash") and process["exitCode"] == 0 and process["argv"] == expected_argv and process["cwd"] == str(RESEARCH) and process["stdoutSha256"] == sha(stdout) and process["stderrSha256"] == sha(stderr),
    "allPhysicalChecksRecomputed": recomputed_checks == result["checks"],
    "metricsRecomputed": abs(result["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"] - source_error) <= 1e-8 and abs(result["metrics"]["maximumAbsoluteTemporalVolumeDriftFraction"] - temporal_drift) <= 1e-8 and abs(result["metrics"]["maximumLiquidCentroidShiftCupLocalMeters"] - centroid_shift) <= 1e-8 and result["metrics"]["derivedContactFrame"] == contact and result["metrics"]["derivedFirstSeventyDegreeFrame"] == first_seventy and result["metrics"]["requiredEffectorSubframes"] == required_subframes,
    "verdictRecomputed": result["status"] == ("PASS" if all(recomputed_checks.values()) else "FAIL") and receipt["status"] == result["status"],
    "exact108FileCache": cache_files == expected_cache and len(cache_files) == 108 and result["cache"]["files"] == cache_files,
    "retainedStaticCacheExact": manifest(STATIC_CACHE)["manifestHash"] == receipt["retainedStaticCacheManifestBefore"] == receipt["retainedStaticCacheManifestAfter"] == spec["baseline"]["retainedStaticCacheManifestHash"],
    "sourceCopyOnlyBlend": sha(source_copy) == spec["baseline"]["sourceBlendSha256"] and [path for path in WORK.rglob("*.blend")] == [source_copy],
    "rootManifestsExact": work_manifest == manifest(WORK) and preaudit_manifest == manifest(EVIDENCE, exclude=("evidence-manifest.pre-audit.json",)),
    "zeroRenderSaveBuildNetwork": result["counts"] == spec["processCeilings"],
    "noMediaOrSymlinks": not any(path.is_symlink() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"} for root in (WORK, EVIDENCE) for path in root.rglob("*")),
    "rootsBelowCeilings": tree_bytes(WORK) < spec["resourceCeilings"]["maximumWorkspaceBytes"] and tree_bytes(EVIDENCE) < spec["resourceCeilings"]["maximumEvidenceBytes"],
    "claimCeilingExact": result["claimCeiling"] == spec["claimCeiling"] and receipt["claimCeiling"] == spec["claimCeiling"],
}
audit = {
    "schemaVersion": "bfs.rc6RealImpactLiquidPreviewC12IndependentAudit.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "physicalStatus": result["status"],
    "physicalPassCount": sum(recomputed_checks.values()),
    "physicalCheckCount": len(recomputed_checks),
    "recomputedPhysicalChecks": recomputed_checks,
    "resultHash": result["resultHash"],
    "receiptHash": receipt["receiptHash"],
}
audit["auditHash"] = self_hash(audit, "auditHash")
with (EVIDENCE / "independent-audit.json").open("x", encoding="utf-8") as handle:
    json.dump(audit, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_REAL_IMPACT_LIQUID_PREVIEW_C12_AUDIT=" + canonical(audit))
if audit["status"] != "PASS":
    raise RuntimeError("real-impact liquid C12 independent audit failed")
