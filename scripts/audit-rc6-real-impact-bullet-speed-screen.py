#!/usr/bin/env python3
"""Independent audit for RC6 real-impact Bullet speed screen attempt-71."""

import hashlib
import json
import math
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-bullet-speed-screen-attempt-71")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-bullet-speed-screen-attempt-71"
CELLS = (("I08", 8), ("I10", 10), ("I12", 12))
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-real-impact-bullet-speed-screen-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-real-impact-bullet-speed-screen.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-bullet-speed-screen.v0.82.json"
EXPECTED_COMMIT_PATHS = {
    "research/2026-09-02-rc6-real-impact-bullet-speed-screen-preregistration.md",
    "research/lab-journal.md",
    "scripts/audit-rc6-real-impact-bullet-speed-screen.py",
    "scripts/run-rc6-real-impact-bullet-speed-screen-scene.py",
    "scripts/run-rc6-real-impact-bullet-speed-screen.py",
    "specs/ai-native-studio-rc6-real-impact-bullet-speed-screen.v0.82.json",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def manifest(root, excluded=()):
    excluded = {Path(value) for value in excluded}
    return [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root) not in excluded
    ]


receipt = json.loads((EVIDENCE / "receipt.json").read_text())
admission = json.loads((EVIDENCE / "admission.json").read_text())
spec = json.loads(SPEC.read_text())
results = [json.loads((EVIDENCE / "cells" / cell / "result.json").read_text()) for cell, _ in CELLS]
processes = [json.loads(path.read_text()) for path in sorted((EVIDENCE / "processes").glob("*.json"))]

result_hashes_exact = all(row["resultHash"] == self_hash(row, "resultHash") for row in results)
metrics_recompute = True
checks_recompute = True
configuration_exact = True
domain_center = [0.45, 0.0, 0.26]
domain_dimensions = [0.9, 0.5, 0.58]
base_voxel = 0.009375
domain_low = [domain_center[i] - domain_dimensions[i] * 0.5 for i in range(3)]
domain_high = [domain_center[i] + domain_dimensions[i] * 0.5 for i in range(3)]
for row, (cell_id, drive_end) in zip(results, CELLS):
    samples = row["samples"]
    maximum_surface = max(sample["cupSurfaceDisplacementFromPriorFrameMeters"] for sample in samples)
    maximum_origin = max(sample["cupOriginDisplacementFromPriorFrameMeters"] for sample in samples)
    maximum_rotation = max(sample["cupRotationDeltaFromPriorFrameDegrees"] for sample in samples)
    first_5 = next((sample["frame"] for sample in samples if sample["cupTiltDegrees"] >= 5.0), None)
    first_45 = next((sample["frame"] for sample in samples if sample["cupTiltDegrees"] >= 45.0), None)
    contact = next(
        (sample["frame"] for sample in samples if sample["ballCupCollisionSurfaceSeparationMeters"] <= 0.01),
        None,
    )
    peak = max(sample["cupTiltDegrees"] for sample in samples)
    swept_low = [min(sample["cupBoundsMin"][axis] for sample in samples) for axis in range(3)]
    swept_high = [max(sample["cupBoundsMax"][axis] for sample in samples) for axis in range(3)]
    required = max(1, math.ceil(maximum_surface / base_voxel - 1e-10))
    domain_contains = all(
        swept_low[axis] >= domain_low[axis] + base_voxel
        and swept_high[axis] <= domain_high[axis] - base_voxel
        for axis in range(3)
    )
    expected_checks = {
        "exactAcceptedSource": True,
        "exactRigidBodyIdentity": True,
        "bulletOnlyNoFluidModifiers": True,
        "noInitialBallCupPenetration": samples[0]["ballCupCollisionSurfaceSeparationMeters"] >= 0.01,
        "derivedContactLeavesTwelveFrameResponseWindow": contact is not None and contact <= 36,
        "solverOwnedCupTiltAtLeast45ByFrame48": first_45 is not None and peak >= 45.0,
        "responseFollowsDerivedContact": contact is not None
        and first_5 is not None
        and first_45 is not None
        and first_5 >= contact - 1
        and first_45 >= contact,
        "cupRemainsOnFloor": swept_low[2] >= -0.005,
        "cupContainedByAcceptedPreviewDomainWithOneVoxelMargin": domain_contains,
        "derivedEffectorSubframesWithinEight": required <= 8,
        "noOutcomeBodyAnimation": True,
        "pusherIsOnlyAuthoredRigidActuator": True,
    }
    configuration_exact &= (
        row["cellId"] == cell_id
        and row["configuration"]["driveEndFrame"] == drive_end
        and row["configuration"]["frameStart"] == 1
        and row["configuration"]["frameEnd"] == 48
        and row["configuration"]["fps"] == 24
        and row["configuration"]["bulletSubstepsPerFrame"] == 20
        and row["configuration"]["bulletSolverIterations"] == 80
        and row["configuration"]["previewResolution"] == 96
        and row["configuration"]["acceptedDomainCenterMeters"] == domain_center
        and row["configuration"]["acceptedDomainDimensionsMeters"] == domain_dimensions
        and abs(row["configuration"]["baseVoxelMeters"] - base_voxel) <= 1e-10
        and abs(row["configuration"]["cupCollisionRadiusMeters"] - 0.15) <= 1e-6
        and abs(row["configuration"]["cupCollisionHalfHeightMeters"] - 0.22) <= 1e-6
        and abs(row["configuration"]["ballCollisionRadiusMeters"] - 0.12) <= 1e-6
    )
    metrics_recompute &= (
        row["metrics"]["derivedContactFrame"] == contact
        and row["metrics"]["firstFiveDegreeFrame"] == first_5
        and row["metrics"]["firstFortyFiveDegreeFrame"] == first_45
        and abs(row["metrics"]["peakCupTiltDegrees"] - peak) <= 1e-8
        and abs(row["metrics"]["maximumCupSurfaceDisplacementPerFrameMeters"] - maximum_surface) <= 1e-8
        and abs(row["metrics"]["maximumCupOriginDisplacementPerFrameMeters"] - maximum_origin) <= 1e-8
        and abs(row["metrics"]["maximumCupRotationDeltaPerFrameDegrees"] - maximum_rotation) <= 1e-8
        and row["metrics"]["requiredEffectorSubframes"] == required
        and all(abs(row["metrics"]["sweptCupBoundsMin"][i] - swept_low[i]) <= 1e-8 for i in range(3))
        and all(abs(row["metrics"]["sweptCupBoundsMax"][i] - swept_high[i]) <= 1e-8 for i in range(3))
    )
    checks_recompute &= row["checks"] == expected_checks and row["status"] == (
        "PASS" if all(expected_checks.values()) else "FAIL"
    )

passing = [row for row in results if row["status"] == "PASS"]
selected = max(passing, key=lambda row: row["configuration"]["driveEndFrame"]) if passing else None
expected_selected = selected["cellId"] if selected else None
expected_argv = []
for cell_id, drive_end in CELLS:
    expected_argv.append(
        [
            str(BINARY),
            "--background",
            str(SOURCE),
            "--python",
            str(SCENE_TOOL),
            "--",
            "--cell-id",
            cell_id,
            "--drive-end-frame",
            str(drive_end),
            "--source-blend",
            str(SOURCE),
            "--work-root",
            str(WORK),
            "--evidence-root",
            str(EVIDENCE),
        ]
    )
expected_user_paths = []
for cell_id, _ in CELLS:
    user_root = WORK / "user" / cell_id
    expected_user_paths.append(
        {
            "HOME": str(user_root / "home"),
            "BLENDER_USER_CONFIG": str(user_root / "config"),
            "BLENDER_USER_SCRIPTS": str(user_root / "scripts"),
            "BLENDER_USER_DATAFILES": str(user_root / "datafiles"),
            "BLENDER_USER_AUTOSAVE": str(user_root / "autosave"),
        }
    )
tool_hashes = {row["uri"]: row["sha256"] for row in spec["tools"]}
baseline_hashes = {row["uri"]: row["sha256"] for row in spec["baselineEvidenceFiles"]}
process_logs_bound = all(
    row["stdoutSha256"] == sha256(EVIDENCE / "logs" / f"{row['index']:02d}-{row['cellId']}.stdout.log")
    and row["stderrSha256"] == sha256(EVIDENCE / "logs" / f"{row['index']:02d}-{row['cellId']}.stderr.log")
    for row in processes
)
semantic_logs = all(
    f'RC6_REAL_IMPACT_BULLET_SPEED_SCREEN={{"cellId":"{row["cellId"]}"'
    in (EVIDENCE / "logs" / f"{row['index']:02d}-{row['cellId']}.stdout.log").read_text()
    and "Traceback (most recent call last)" not in (
        EVIDENCE / "logs" / f"{row['index']:02d}-{row['cellId']}.stderr.log"
    ).read_text()
    for row in processes
)
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
parent = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
commit_paths = set(
    subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        cwd=RESEARCH,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
)
work_manifest = json.loads((WORK / "work-manifest.json").read_text())
evidence_manifest = json.loads((EVIDENCE / "evidence-manifest.pre-audit.json").read_text())
banned = {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4", ".blend"}
no_symlinks = not any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*"))
expected_counts = {
    "blenderStarts": 3,
    "bulletBakes": 3,
    "fluidDataBakes": 0,
    "fluidMeshBakes": 0,
    "renders": 0,
    "blendSaves": 0,
    "nativeBuilds": 0,
    "networkCalls": 0,
    "engineRemoteWrites": 0,
}
checks = {
    "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "frozenToolIdentities": tool_hashes
    == {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha256(SCENE_TOOL),
        str(RUNNER.relative_to(RESEARCH)): sha256(RUNNER),
        str(Path(__file__).resolve().relative_to(RESEARCH)): sha256(Path(__file__).resolve()),
    },
    "baselineEvidenceExact": all(sha256(RESEARCH / uri) == digest for uri, digest in baseline_hashes.items()),
    "binaryAndSourceExact": sha256(BINARY) == spec["baseline"]["binarySha256"]
    and sha256(SOURCE) == spec["baseline"]["sourceBlendSha256"],
    "researchExecutionCommitBound": admission["researchHead"] == head
    and parent == spec["researchParentBeforePreregistration"]
    and commit_paths == EXPECTED_COMMIT_PATHS,
    "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash"),
    "admissionExact": admission["status"] == "PASS"
    and admission["workRootAbsentBeforeRun"]
    and admission["evidenceRootAbsentBeforeRun"]
    and admission["projectedWriteBytes"] == spec["resourceCeilings"]["projectedWriteBytes"]
    and admission["reserveBytes"] == spec["resourceCeilings"]["minimumReserveBytes"],
    "cellRosterAndConfigurationExact": configuration_exact
    and [(row["cellId"], row["configuration"]["driveEndFrame"]) for row in results] == list(CELLS),
    "cellResultSelfHashes": result_hashes_exact,
    "metricsIndependentlyRecomputed": metrics_recompute,
    "cellChecksAndVerdictsRecomputed": checks_recompute,
    "selectionIsSlowestPassing": receipt["selectedCellId"] == expected_selected
    and receipt["status"] == ("PASS" if selected else "FAIL")
    and receipt["verdict"]
    == ("PASS_REAL_IMPACT_BULLET_TRAJECTORY" if selected else "FAIL_REAL_IMPACT_BULLET_TRAJECTORY"),
    "receiptBindsCellsAndProcesses": receipt["cellResultHashes"] == [row["resultHash"] for row in results]
    and receipt["processHashes"] == [row["processHash"] for row in processes],
    "processRosterExact": len(processes) == 3
    and [row["cellId"] for row in processes] == [cell for cell, _ in CELLS],
    "processArgvExact": [row["argv"] for row in processes] == expected_argv,
    "isolatedUserPathsExact": [row["isolatedUserPaths"] for row in processes] == expected_user_paths
    and all(Path(value).is_dir() for paths in expected_user_paths for value in paths.values()),
    "processesSuccessfulAndSelfHashed": all(
        row["exitCode"] == 0 and row["processHash"] == self_hash(row, "processHash") for row in processes
    ),
    "logsPresentBoundAndSemantic": process_logs_bound and semantic_logs,
    "zeroFluidRenderSaveBuildNetworkWrites": receipt["counts"] == expected_counts,
    "preAuditRootManifestsExact": work_manifest
    == {"root": str(WORK), "files": manifest(WORK, excluded=(Path("work-manifest.json"),))}
    and evidence_manifest
    == {
        "root": str(EVIDENCE),
        "files": manifest(EVIDENCE, excluded=(Path("evidence-manifest.pre-audit.json"),)),
    },
    "noBannedArtifacts": not any(
        path.suffix.lower() in banned for root in (WORK, EVIDENCE) for path in root.rglob("*")
    ),
    "noSymlinks": no_symlinks,
    "rootsBelowCeiling": sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file())
    < spec["resourceCeilings"]["maximumWorkspaceBytes"]
    and sum(path.stat().st_size for path in EVIDENCE.rglob("*") if path.is_file())
    < spec["resourceCeilings"]["maximumEvidenceBytes"],
}
audit = {
    "schemaVersion": "bfs.rc6RealImpactBulletSpeedScreenIndependentAudit.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "physicalVerdict": receipt["verdict"],
    "selectedCellId": expected_selected,
}
audit["auditHash"] = self_hash(audit, "auditHash")
with (EVIDENCE / "independent-audit.json").open("x", encoding="utf-8") as handle:
    json.dump(audit, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_REAL_IMPACT_BULLET_SPEED_SCREEN_AUDIT=" + canonical(audit))
if audit["status"] != "PASS":
    raise RuntimeError("RC6 real-impact Bullet speed screen independent audit failed")
