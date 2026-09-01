#!/usr/bin/env python3
"""Independent RC5 formal audit after fresh pixel review."""

import hashlib
import json
import struct
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
EVIDENCE = RESEARCH / "experiments/physical-richness/RC5-2026-09-01-attempt-01"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01")
DEVELOPMENT = RESEARCH / "experiments/physical-richness/RC5-2026-09-01-development-attempt-13"
COMMIT = "8e18c82548f8716c415e6e1b69fdbbdeef1f1900"
PARENT = "db662438edfef0a1979d8227c8b58cf8620e2b74"


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
    build = load(EVIDENCE / "B1-build.json")
    reopen = load(EVIDENCE / "B1-reopen.json")
    regression = load(EVIDENCE / "regression-negative.json")
    render = load(EVIDENCE / "render.json")
    visual = load(EVIDENCE / "formal-visual-review.json")
    development_receipt = load(DEVELOPMENT / "receipt.json")
    development_audit = load(DEVELOPMENT / "audit.json")
    process_names = ((1, "local-clone"), (2, "checkout"), (3, "lfs-checkout"), (4, "clean-native-build"), (5, "b1-build"), (6, "b1-reopen"), (7, "rc4-d1-h1-regression-negative"), (8, "b1-render"), (9, "contact-video"))
    processes = [load(EVIDENCE / "processes" / f"{index:02d}-{name}.json") for index, name in process_names]
    process_integrity = all(row["processHash"] == self_hash(row, "processHash") and row["exitCode"] == 0 and sha(EVIDENCE / "logs" / f"{row['index']:02d}-{row['name']}.stdout.log") == row["stdoutSha256"] and sha(EVIDENCE / "logs" / f"{row['index']:02d}-{row['name']}.stderr.log") == row["stderrSha256"] for row in processes)
    result, physics = build["result"], build["result"]["physics"]
    attachment = physics["breakableAttachment"]
    images = sorted((EVIDENCE / "stills").glob("*.png")) + sorted((EVIDENCE / "clip").glob("*.png"))
    source = WORK / "source"
    installed_root = WORK / "build/bin/Film Studio Engine F0.app/Contents/Resources/5.2/scripts/modules"
    installed_expected = receipt["installed"]["moduleSha256"]
    installed_paths = {"physicsAction": installed_root / "film_studio_physics_action.py", "physicalLook": installed_root / "film_studio_physical_look.py", "causal": installed_root / "film_studio_causal.py", "physicalLight": installed_root / "film_studio_physical_light.py", "physicalPerformance": installed_root / "film_studio_physical_performance.py"}
    binary = Path(receipt["binary"]["path"])
    work_media = [path for path in WORK.rglob("*") if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"}]
    checks = {
        "exactRoots": EVIDENCE.resolve() == EVIDENCE and WORK.resolve() == WORK,
        "developmentAccepted": development_receipt["receiptHash"] == "396fc68af41870908e51d82f01ce6741228efad97d1179faabf60fe1fa07cf2d" and development_audit["auditHash"] == "b7020a9b00b53565d18bb4e8a222881470defbb7f022912e994aeaa20ca37adf" and development_audit["status"] == "PASS",
        "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash"),
        "receiptMachinePass": receipt["status"] == "PASS_PENDING_FRESH_DIRECT_VISUAL_REVIEW_AND_INDEPENDENT_AUDIT" and all(receipt["checks"].values()),
        "admission": admission["status"] == "PASS" and admission["admissionHash"] == self_hash(admission, "admissionHash") and admission["freeBytesBefore"] >= 160 * 1024**3,
        "processIntegrity": process_integrity,
        "offlineProductStarts": all("--offline-mode" in row["argv"] and "--disable-autoexec" in row["argv"] for row in processes[4:8]),
        "sourceIdentity": receipt["product"]["commit"] == COMMIT and receipt["product"]["parent"] == PARENT and subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip() == COMMIT and not subprocess.check_output(["git", "status", "--porcelain"], cwd=source, text=True).strip(),
        "sourceScope": receipt["product"]["sourceDiffNumstat"] == ["322\t19\tscripts/modules/film_studio_physics_action.py"],
        "installedExact": all(path.is_file() and sha(path) == installed_expected[name] for name, path in installed_paths.items()),
        "nativeArm64Binary": binary.is_file() and sha(binary) == receipt["binary"]["sha256"] and "arm64" in subprocess.check_output(["file", str(binary)], text=True),
        "buildTwentyOfTwenty": build["status"] == "PASS" and build["checkCount"] == build["passCount"] == 20 and all(build["checks"].values()),
        "resultExact": result["resultHash"] == "6bc858c6a853f1b306575762728e8c1afc404b40db85dbbe8ae0e119440ac74c" and render["resultHash"] == result["resultHash"],
        "bulletAttachment": attachment["source"] == "BLENDER_BULLET_BREAKABLE_FIXED_CONSTRAINT" and attachment["constraintType"] == "FIXED" and attachment["detachmentFrame"] == 24 and attachment["attachmentTarget"] == "CAUSAL_TARGET_002" and attachment["maximumAttachmentSeparationMeters"] == 0.12205441,
        "derivedTargetAndCamera": attachment["attachmentTargetDerivation"]["source"] == "METRIC_INITIAL_CONDITIONS_BEFORE_SCENE_MUTATION" and attachment["attachmentTargetDerivation"]["uniquenessMarginMeters"] > .14 and result["cinematography"]["contact"]["secondaryReadability"]["candidateCameraObjectCount"] == 1 and result["cinematography"]["contact"]["secondaryReadability"]["candidateCameraObjectDeletions"] == 0,
        "physicalResponse": physics["contactFrame"] == 16 and physics["respondingTargetCount"] == 3 and physics["settledWindowStartFrame"] == 132 and physics["settledGroupFrame"] == 141 and attachment["maximumFloorPenetrationMeters"] < .005,
        "solverAuthority": result["authority"]["postReleaseTransformKeyframes"] == result["authority"]["authoredOutcomeFields"] == result["authority"]["authoredBreakFrames"] == result["authority"]["authoredDetachedPoses"] == result["authority"]["authoredDetachmentVelocities"] == 0,
        "saveReopen": reopen["status"] == "PASS" and all(reopen["checks"].values()) and max(reopen["maximumActorLocationDeltaMeters"], reopen["maximumCapLocationDeltaMeters"], reopen["maximumCapAngularDeltaDegrees"], reopen["maximumTargetTiltDeltaDegrees"]) < 1e-8,
        "regressions": regression["status"] == "PASS" and [row["resultHash"] for row in regression["regressions"]] == ["016ccd803ef9aecc0bce6e0dd91d98472b7a6b6304e1c083e236058e39dc5925", "05c72eeff8279ac812d9e2b2ea4565bd2cc2d8f7cd2844e6ffdade06556c8409", "064150af89de723f09802750b3b9282465d5acca4539ef9fd6221c91603f8c98"],
        "negativeControls": len(regression["negativeControls"]) == 12 and all(row["passed"] for row in regression["negativeControls"]),
        "fixedContactCamera": render["clip"]["cameraPolicy"] == "FIXED_CONTACT_CAMERA_WITH_TIMELINE_MARKERS_REMOVED_AFTER_STILLS" and len(render["clip"]["removedTimelineMarkers"]) == 3,
        "renderRoster": len(images) == 51 and len(render["stills"]) == 3 and render["clip"]["frameCount"] == 48 and all(png_dimensions(path) == [1280, 720] for path in images),
        "renderBindings": all(sha(Path(row["path"])) == row["sha256"] for row in render["stills"] + render["clip"]["frames"]) and sha(EVIDENCE / "contact-clip.mp4") == receipt["render"]["videoSha256"],
        "freshVisualReview": visual["status"] == "PASS" and visual["yesCount"] == 10 and visual["noCount"] == 0 and visual["allFramesInspected"] is True and visual["formalReceiptHash"] == receipt["receiptHash"] and visual["reviewHash"] == self_hash(visual, "reviewHash"),
        "visualBindings": all(sha(RESEARCH / row["uri"]) == row["sha256"] for row in visual["artifacts"]),
        "operationCounts": receipt["counts"] == {"binaryDistribution": 0, "blendSaves": 1, "cleanNativeBuilds": 1, "contactClipFrames": 48, "engineRemoteWrites": 0, "ffmpegProcesses": 1, "forcePushes": 0, "networkCalls": 0, "notarization": 0, "productStarts": 4, "releases": 0, "reopens": 1, "reviewStills": 3, "sceneMutations": 4, "signing": 0, "tags": 0},
        "workMediaAndResources": not work_media and tree_bytes(WORK) <= 64 * 1024**3 and tree_bytes(EVIDENCE) <= 1024 * 1024**2 and receipt["resources"]["freeBytesAfter"] >= 100 * 1024**3,
    }
    evidence_manifest = manifest(EVIDENCE, excluded=("formal-audit.json", "formal-evidence-manifest.json", "formal-work-manifest.json"))
    work_manifest = manifest(WORK)
    (EVIDENCE / "formal-evidence-manifest.json").write_text(json.dumps(evidence_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (EVIDENCE / "formal-work-manifest.json").write_text(json.dumps(work_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    audit = {
        "schemaVersion": "bfs.rc5BreakableAttachmentFormalAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "checkCount": len(checks),
        "passCount": sum(checks.values()),
        "formalReceiptHash": receipt["receiptHash"],
        "binarySha256": receipt["binary"]["sha256"],
        "resultHash": result["resultHash"],
        "evidenceManifestSha256": sha(EVIDENCE / "formal-evidence-manifest.json"),
        "workManifestSha256": sha(EVIDENCE / "formal-work-manifest.json"),
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    (EVIDENCE / "formal-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canonical(audit))
    if audit["status"] != "PASS":
        raise RuntimeError("RC5 formal audit failed")


if __name__ == "__main__":
    main()
