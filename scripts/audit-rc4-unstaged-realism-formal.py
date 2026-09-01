#!/usr/bin/env python3
"""Independent RC4 formal evidence audit after fresh pixel review."""

import hashlib
import json
import struct
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
EVIDENCE = RESEARCH / "experiments/unstaged-physical-realism/RC4-2026-09-01-attempt-01"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC4-2026-09-01-attempt-01")
COMMIT = "db662438edfef0a1979d8227c8b58cf8620e2b74"
PARENT = "5f595fe3aca7118847aec5b572f6d90a377a4352"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def png_dimensions(path):
    with path.open("rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n" or handle.read(4) != b"\x00\x00\x00\r" or handle.read(4) != b"IHDR":
            return None
        return list(struct.unpack(">II", handle.read(8)))


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def manifest(root, excluded=()):
    return [{"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(root.rglob("*")) if path.is_file() and path.name not in excluded]


def main():
    if (EVIDENCE / "formal-audit.json").exists():
        raise RuntimeError("formal audit already exists")
    receipt = load(EVIDENCE / "receipt.json")
    admission = load(EVIDENCE / "admission.json")
    build = load(EVIDENCE / "R1-build.json")
    reopen = load(EVIDENCE / "R1-reopen.json")
    regressions = load(EVIDENCE / "regressions.json")
    negative = load(EVIDENCE / "negative-controls.json")
    render = load(EVIDENCE / "render.json")
    visual = load(EVIDENCE / "formal-visual-review.json")
    process_names = ((1, "local-clone"), (2, "checkout"), (3, "lfs-checkout"), (4, "clean-native-build"), (5, "r1-build"), (6, "r1-reopen"), (7, "d1-h1-regressions"), (8, "negative-controls"), (9, "r1-render"), (10, "contact-video"))
    processes = [load(EVIDENCE / "processes" / f"{index:02d}-{name}.json") for index, name in process_names]
    process_integrity = all(row["processHash"] == self_hash(row, "processHash") and row["exitCode"] == 0 and sha(EVIDENCE / "logs" / f"{row['index']:02d}-{row['name']}.stdout.log") == row["stdoutSha256"] and sha(EVIDENCE / "logs" / f"{row['index']:02d}-{row['name']}.stderr.log") == row["stderrSha256"] for row in processes)
    result, physics = build["result"], build["result"]["physics"]
    images = sorted((EVIDENCE / "stills").glob("*.png")) + sorted((EVIDENCE / "clip").glob("*.png"))
    source = WORK / "source"
    installed_root = WORK / "build/bin/Film Studio Engine F0.app/Contents/Resources/5.2/scripts/modules"
    installed_expected = receipt["installed"]["moduleSha256"]
    installed_paths = {"physicsAction": installed_root / "film_studio_physics_action.py", "physicalLook": installed_root / "film_studio_physical_look.py", "causal": installed_root / "film_studio_causal.py", "physicalLight": installed_root / "film_studio_physical_light.py", "physicalPerformance": installed_root / "film_studio_physical_performance.py"}
    checks = {
        "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash"),
        "receiptMachinePass": receipt["status"] == "PASS_PENDING_FRESH_DIRECT_VISUAL_REVIEW_AND_INDEPENDENT_AUDIT" and all(receipt["checks"].values()),
        "admission": admission["status"] == "PASS" and admission["admissionHash"] == self_hash(admission, "admissionHash") and admission["freeBytesBefore"] >= 160 * 1024**3,
        "processIntegrity": process_integrity,
        "offlineProductStarts": all("--offline-mode" in row["argv"] and "--disable-autoexec" in row["argv"] for row in processes[4:9]),
        "sourceIdentity": receipt["product"]["commit"] == COMMIT and receipt["product"]["parent"] == PARENT and (source / ".git").exists(),
        "sourceScope": receipt["product"]["sourceDiffNumstat"] == ["270\t0\tscripts/modules/film_studio_physical_look.py", "101\t19\tscripts/modules/film_studio_physics_action.py"],
        "installedExact": all(path.is_file() and sha(path) == installed_expected[name] for name, path in installed_paths.items()),
        "r1Physics": result["topology"] == "GROUP_RESPONSE" and result["mechanism"]["activeRigidBodyCount"] == 4 and result["mechanism"]["rigidBodyConstraintCount"] == 0 and physics["respondingTargetCount"] == 3 and physics["firstResponseDelayFrames"] <= 2 and physics["continuousActorMotionThroughContact"],
        "settleWindow": physics["settledWindowFrameCount"] >= 10 and physics["settledMaximumAggregateAngularStepDegrees"] <= .25 and physics["settledMaximumTargetTranslationStepMeters"] <= .0015 and result["cinematography"]["effect"]["frame"] == physics["settledGroupFrame"],
        "solverAuthority": result["authority"]["postReleaseTransformKeyframes"] == result["authority"]["authoredOutcomeFields"] == result["authority"]["authoredContactResponsePeakOrFinalFrames"] == result["authority"]["lightAnimationChannels"] == 0,
        "saveReopen": reopen["status"] == "PASS" and reopen["maximumActorLocationDeltaMeters"] <= 1e-6 and reopen["maximumTargetTiltDeltaDegrees"] <= .001,
        "regressions": regressions["status"] == "PASS" and all(row["status"] == "PASS" for row in regressions["cases"]),
        "negativeControls": negative["status"] == "PASS" and negative["passCount"] == negative["caseCount"] and all(row["passed"] for row in negative["cases"]),
        "fixedContactCamera": render["clip"]["cameraPolicy"] == "FIXED_CONTACT_CAMERA_WITH_TIMELINE_MARKERS_REMOVED_AFTER_STILLS" and len(render["clip"]["removedTimelineMarkers"]) == 3,
        "renderRoster": len(images) == 51 and len(render["stills"]) == 3 and render["clip"]["frameCount"] == 48 and all(png_dimensions(path) == [1280, 720] for path in images),
        "freshVisualReview": visual["status"] == "PASS" and visual["yesCount"] == 10 and visual["noCount"] == 0 and visual["allFramesInspected"] is True and visual["formalReceiptHash"] == receipt["receiptHash"] and visual["reviewHash"] == self_hash(visual, "reviewHash"),
        "visualBindings": all(sha(RESEARCH / row["uri"]) == row["sha256"] for row in visual["artifacts"]),
        "operationCounts": receipt["counts"] == {"binaryDistribution": 0, "blendSaves": 1, "cleanNativeBuilds": 1, "contactClipFrames": 48, "engineRemoteWrites": 0, "ffmpegProcesses": 1, "forcePushes": 0, "networkCalls": 0, "notarization": 0, "productStarts": 5, "releases": 0, "reopens": 1, "reviewStills": 3, "sceneMutations": 3, "signing": 0, "tags": 0},
        "resourceCeilings": tree_bytes(WORK) <= 64 * 1024**3 and tree_bytes(EVIDENCE) <= 1024 * 1024**2 and receipt["resources"]["freeBytesAfter"] >= 100 * 1024**3,
    }
    evidence_manifest = manifest(EVIDENCE, excluded=("formal-audit.json", "formal-evidence-manifest.json", "formal-work-manifest.json"))
    work_manifest = manifest(WORK)
    (EVIDENCE / "formal-evidence-manifest.json").write_text(json.dumps(evidence_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (EVIDENCE / "formal-work-manifest.json").write_text(json.dumps(work_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    audit = {"schemaVersion": "bfs.rc4UnstagedRealismFormalAudit.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "checkCount": len(checks), "passCount": sum(checks.values()), "formalReceiptHash": receipt["receiptHash"], "binarySha256": receipt["binary"]["sha256"], "evidenceManifestSha256": sha(EVIDENCE / "formal-evidence-manifest.json"), "workManifestSha256": sha(EVIDENCE / "formal-work-manifest.json")}
    audit["auditHash"] = self_hash(audit, "auditHash")
    (EVIDENCE / "formal-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canonical(audit))
    if audit["status"] != "PASS":
        raise RuntimeError("RC4 formal audit failed")


if __name__ == "__main__":
    main()
