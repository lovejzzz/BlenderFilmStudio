#!/usr/bin/env python3
"""Independent audit for RC6 slow-tip Bullet screen attempt-47."""

import hashlib
import json
import math
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-slow-tip-bullet-screen-attempt-47")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-slow-tip-bullet-screen-attempt-47"
CELLS = (("D12", 12), ("D16", 16), ("D20", 20), ("D24", 24))
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-slow-tip-bullet-screen-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-slow-tip-bullet-screen.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-slow-tip-bullet-screen.v0.55.json"


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


receipt = json.loads((EVIDENCE / "receipt.json").read_text())
admission = json.loads((EVIDENCE / "admission.json").read_text())
spec = json.loads(SPEC.read_text())
results = [json.loads((EVIDENCE / "cells" / cell / "result.json").read_text()) for cell, _ in CELLS]
processes = [json.loads(path.read_text()) for path in sorted((EVIDENCE / "processes").glob("*.json"))]

result_hashes_exact = all(row["resultHash"] == self_hash(row, "resultHash") for row in results)
metrics_recompute = True
checks_recompute = True
for row, (cell_id, drive_end) in zip(results, CELLS):
    samples = row["samples"]
    maximum_displacement = max(sample["surfaceDisplacementFromPriorFrameMeters"] for sample in samples)
    first_5 = next((sample["frame"] for sample in samples if sample["cupTiltDegrees"] >= 5.0), None)
    first_45 = next((sample["frame"] for sample in samples if sample["cupTiltDegrees"] >= 45.0), None)
    contact = next((sample["frame"] for sample in samples if sample["ballCupSurfaceSeparationMeters"] <= 0.01), None)
    peak = max(sample["cupTiltDegrees"] for sample in samples)
    base_voxel = row["configuration"]["baseVoxelMeters"]
    required = max(1, math.ceil(maximum_displacement / base_voxel - 1e-10))
    metrics_recompute &= (
        row["cellId"] == cell_id
        and row["configuration"]["driveEndFrame"] == drive_end
        and row["metrics"]["contactFrame"] == contact
        and row["metrics"]["firstFiveDegreeFrame"] == first_5
        and row["metrics"]["firstFortyFiveDegreeFrame"] == first_45
        and row["metrics"]["slowTiltSpanFrames"] == (None if first_5 is None or first_45 is None else first_45 - first_5)
        and abs(row["metrics"]["peakCupTiltDegrees"] - peak) <= 1e-8
        and abs(row["metrics"]["maximumCupSurfaceDisplacementPerFrameMeters"] - maximum_displacement) <= 1e-8
        and row["metrics"]["requiredEffectorSubframes"] == required
    )
    checks_recompute &= row["status"] == ("PASS" if all(row["checks"].values()) else "FAIL")

passing = [row for row in results if row["status"] == "PASS"]
selected = max(passing, key=lambda row: row["configuration"]["driveEndFrame"]) if passing else None
expected_selected = selected["cellId"] if selected else None
logs = list((EVIDENCE / "logs").glob("*.log"))
banned = {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4", ".blend"}
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
tool_hashes = {row["uri"]: row["sha256"] for row in spec["tools"]}
process_logs_bound = all(
    row["stdoutSha256"] == sha256(EVIDENCE / "logs" / f"{row['index']:02d}-{row['cellId']}.stdout.log")
    and row["stderrSha256"] == sha256(EVIDENCE / "logs" / f"{row['index']:02d}-{row['cellId']}.stderr.log")
    for row in processes
)
no_symlinks = not any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*"))
checks = {
    "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "frozenToolIdentities": tool_hashes == {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha256(SCENE_TOOL),
        str(RUNNER.relative_to(RESEARCH)): sha256(RUNNER),
        str(Path(__file__).resolve().relative_to(RESEARCH)): sha256(Path(__file__).resolve()),
    },
    "binaryAndSourceExact": sha256(BINARY) == spec["baseline"]["binarySha256"]
    and sha256(SOURCE) == spec["baseline"]["sourceBlendSha256"],
    "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash"),
    "admissionExact": admission["status"] == "PASS" and admission["workRootAbsentBeforeRun"] and admission["evidenceRootAbsentBeforeRun"],
    "cellRosterExact": [(row["cellId"], row["configuration"]["driveEndFrame"]) for row in results] == list(CELLS),
    "cellResultSelfHashes": result_hashes_exact,
    "metricsIndependentlyRecomputed": metrics_recompute,
    "cellVerdictsRecomputed": checks_recompute,
    "selectionIsSlowestPassing": receipt["selectedCellId"] == expected_selected,
    "processRosterExact": len(processes) == 4 and [row["cellId"] for row in processes] == [cell for cell, _ in CELLS],
    "processArgvExact": [row["argv"] for row in processes] == expected_argv,
    "processesSuccessfulAndSelfHashed": all(row["exitCode"] == 0 and row["processHash"] == self_hash(row, "processHash") for row in processes),
    "logsPresentAndBound": len(logs) >= 8 and all(path.is_file() for path in logs) and process_logs_bound,
    "zeroFluidRenderSaveNetwork": receipt["counts"] == {"blenderStarts": 4, "bulletBakes": 4, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0},
    "noBannedArtifacts": not any(path.suffix.lower() in banned for root in (WORK, EVIDENCE) for path in root.rglob("*")),
    "noSymlinks": no_symlinks,
    "rootsBelowCeiling": sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file()) < 268435456 and sum(path.stat().st_size for path in EVIDENCE.rglob("*") if path.is_file()) < 67108864,
}
audit = {
    "schemaVersion": "bfs.rc6SlowTipBulletScreenIndependentAudit.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "selectedCellId": expected_selected,
}
audit["auditHash"] = self_hash(audit, "auditHash")
with (EVIDENCE / "independent-audit.json").open("x", encoding="utf-8") as handle:
    json.dump(audit, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_SLOW_TIP_BULLET_SCREEN_AUDIT=" + canonical(audit))
if audit["status"] != "PASS":
    raise RuntimeError("RC6 slow-tip Bullet screen independent audit failed")
