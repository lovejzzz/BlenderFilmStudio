#!/usr/bin/env python3
"""Close and independently audit retained C5-C2 attempt-54 partial evidence."""

import hashlib
import json
import math
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-slow-tip-bullet-screen-c5-c2-attempt-54"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-slow-tip-bullet-screen-c5-c2-attempt-54")
SPEC = RESEARCH / "specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5-c2.v0.62.json"
RUNNER = RESEARCH / "scripts/run-rc6-slow-tip-bullet-screen-c5-c2.py"
RESULT = EVIDENCE / "cells/C5F48/result.json"
PROCESS = EVIDENCE / "processes/01-C5F48.json"
STDOUT = EVIDENCE / "logs/01-C5F48.stdout.log"
STDERR = EVIDENCE / "logs/01-C5F48.stderr.log"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def manifest(root):
    rows = [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    value = {"root": str(root), "files": rows}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


for output in (EVIDENCE / "failure.json", EVIDENCE / "independent-failure-audit.json", EVIDENCE / "evidence-manifest.json", WORK / "work-manifest.json"):
    if output.exists():
        raise RuntimeError(f"C5-C2 failure closure output already exists: {output}")

spec = json.loads(SPEC.read_text())
result = json.loads(RESULT.read_text())
process = json.loads(PROCESS.read_text())
stdout = STDOUT.read_text()
samples = result["samples"]
maximum_displacement = max(row["surfaceDisplacementFromPriorFrameMeters"] for row in samples)
maximum_hinge_drift = max(row["hingePivotDriftMeters"] for row in samples)
first_5 = next(row["frame"] for row in samples if row["cupTiltDegrees"] >= 5.0)
first_45 = next(row["frame"] for row in samples if row["cupTiltDegrees"] >= 45.0)
peak = max(row["cupTiltDegrees"] for row in samples)
required = max(1, math.ceil(maximum_displacement / result["configuration"]["baseVoxelMeters"] - 1e-10))
banned = {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4", ".blend"}

checks = {
    "c5C2SpecSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "c5C2RunnerExact": sha(RUNNER) == "a3407a481531d077ae9cd5d702560d23f4728d19dfc5a51972b1a745aae567bf",
    "singleCellAndProcessExact": [path.name for path in (EVIDENCE / "cells").iterdir()] == ["C5F48"] and len(list((EVIDENCE / "processes").glob("*.json"))) == 1,
    "processSuccessfulAndSelfHashed": process["exitCode"] == 0 and process["processHash"] == self_hash(process, "processHash"),
    "processLogsBound": process["stdoutSha256"] == sha(STDOUT) and process["stderrSha256"] == sha(STDERR),
    "resultSelfHash": result["resultHash"] == self_hash(result, "resultHash") == "0e6255174d65bedf2b5d4edfef2480ed308bb7d135bf5b915f4e8d517151d075",
    "cellPhysicalChecksPass": result["status"] == "PASS" and all(result["checks"].values()),
    "metricsIndependentlyRecomputed": result["metrics"]["firstFiveDegreeFrame"] == first_5 and result["metrics"]["firstFortyFiveDegreeFrame"] == first_45 and result["metrics"]["slowTiltSpanFrames"] == first_45 - first_5 and abs(result["metrics"]["peakCupTiltDegrees"] - peak) <= 1e-8 and abs(result["metrics"]["maximumCupSurfaceDisplacementPerFrameMeters"] - maximum_displacement) <= 1e-8 and abs(result["metrics"]["maximumHingePivotDriftMeters"] - maximum_hinge_drift) <= 1e-8 and result["metrics"]["requiredEffectorSubframes"] == required,
    "actualSceneMarkerPresent": 'RC6_SLOW_TIP_BULLET_SCREEN_C5={"cellId":"C5F48"' in stdout,
    "mismatchedRunnerMarkerAbsent": 'RC6_SLOW_TIP_BULLET_SCREEN_C5_C2={"cellId":"C5F48"' not in stdout,
    "aggregateReceiptAbsent": not (EVIDENCE / "receipt.json").exists(),
    "laterCellsAbsent": all(not (EVIDENCE / "cells" / cell).exists() for cell in ("C5F60", "C5F72", "C5F96")),
    "zeroForbiddenCounts": result["counts"] == {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0},
    "noBannedArtifacts": not any(path.suffix.lower() in banned for root in (WORK, EVIDENCE) for path in root.rglob("*")),
    "noSymlinks": not any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*")),
    "rootsBelowCeilings": sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file()) < 268435456 and sum(path.stat().st_size for path in EVIDENCE.rglob("*") if path.is_file()) < 67108864,
}
failure = {
    "schemaVersion": "bfs.rc6SlowTipBulletScreenC5C2Failure.v0.1",
    "status": "FAIL_RUNNER_MARKER_BINDING",
    "message": "C5F48 physical result passed, but the runner expected a versioned C5-C2 marker from an unchanged C5 scene tool",
    "physicalResultStatus": result["status"],
    "physicalResultHash": result["resultHash"],
    "counts": {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0},
    "remainingCellsStarted": 0,
    "claimCeiling": "One independently checked passing C5F48 Bullet trajectory inside a retained aggregate-run harness failure; no four-cell selection or liquid claim.",
}
failure["failureHash"] = self_hash(failure, "failureHash")
audit = {
    "schemaVersion": "bfs.rc6SlowTipBulletScreenC5C2FailureAudit.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "failureHash": failure["failureHash"],
    "physicalResultHash": result["resultHash"],
}
audit["auditHash"] = self_hash(audit, "auditHash")
write_exclusive(EVIDENCE / "failure.json", failure)
write_exclusive(EVIDENCE / "independent-failure-audit.json", audit)
write_exclusive(WORK / "work-manifest.json", manifest(WORK))
write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE))
print("RC6_SLOW_TIP_C5_C2_FAILURE_AUDIT=" + canonical(audit))
if audit["status"] != "PASS":
    raise RuntimeError("C5-C2 failure closure audit failed")
