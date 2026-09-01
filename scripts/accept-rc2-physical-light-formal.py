#!/usr/bin/env python3
"""Close RC2 after machine, independent and direct visual review all pass."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/physical-light-transfer/RC2-2026-09-01-attempt-01"


def load(name): return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def self_hash(value, field):
    body = dict(value); body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest()


receipt, audit, visual, build, reopen = (load(name) for name in ("receipt.json", "audit.json", "direct-visual-review.json", "build.json", "reopen.json"))
if receipt["status"] != "PASS_PENDING_DIRECT_VISUAL_AND_INDEPENDENT_AUDIT" or audit["status"] != "PASS" or visual["status"] != "PASS" or reopen["status"] != "PASS":
    raise SystemExit("RC2 prerequisite did not pass")
physics = build["result"]["physics"]
acceptance = {
    "schemaVersion": "bfs.rc2PhysicalLightAcceptance.v0.1",
    "status": "PASS",
    "experimentId": "RC2-PHYSICAL-FILM-DIRECTION-TRANSFER",
    "projectTitle": "The Signal Gate",
    "productCommit": receipt["productCommit"],
    "binarySha256": receipt["binary"]["sha256"],
    "machineReceiptHash": receipt["receiptHash"],
    "independentAudit": {"checks": f"{audit['passCount']}/{audit['checkCount']} PASS", "auditHash": audit["auditHash"]},
    "directVisualReview": {"questions": f"{visual['yesCount']}/{visual['questionCount']} YES", "reviewHash": visual["reviewHash"]},
    "measurements": {
        "contactFrame": physics["contactFrame"], "responseFrame": physics["firstShutterResponseFrame"], "responseDelayFrames": physics["firstResponseDelayFrames"],
        "actorTravelMeters": physics["actorTravelMeters"], "medianRollingSlipRatio": physics["medianRollingSlipRatio"], "peakShutterOpenDegrees": physics["peakShutterOpenDegrees"], "settledWindowStartFrame": physics["settledWindowStartFrame"],
        "actualToClosedLuminanceRatio": build["illuminationCausality"]["actualToClosedLuminanceRatio"], "reopenMaximumActorLocationDeltaMeters": reopen["maximumActorLocationDeltaMeters"], "reopenMaximumShutterAngleDeltaDegrees": reopen["maximumShutterAngleDeltaDegrees"],
        "actorPoseKeyframes": build["result"]["authority"]["actorPoseKeyframesAfterRelease"], "shutterPoseKeyframes": build["result"]["authority"]["shutterPoseKeyframesAfterContact"], "lightAnimationChannels": build["result"]["authority"]["lightAnimationChannels"],
    },
    "regressions": {"pc8Pc9": load("backward-compatibility.json")["status"], "pc9NegativeControls": load("negative-controls.json")["status"], "rc1Source": load("rc1-source-regression.json")["status"]},
    "counts": receipt["counts"],
    "claimCeiling": visual["claimCeiling"],
}
acceptance["acceptanceHash"] = self_hash(acceptance, "acceptanceHash")
(EVIDENCE / "acceptance.json").write_text(json.dumps(acceptance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

files = []
for path in sorted(item for item in EVIDENCE.rglob("*") if item.is_file() and item.name != "root-manifest.json"):
    files.append({"path": path.relative_to(EVIDENCE).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
manifest = {"schemaVersion": "bfs.rc2PhysicalLightRootManifest.v0.1", "files": files}
manifest["manifestHash"] = self_hash(manifest, "manifestHash")
(EVIDENCE / "root-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": "PASS", "acceptanceHash": acceptance["acceptanceHash"], "manifestHash": manifest["manifestHash"], "fileCount": len(files)}, sort_keys=True))
