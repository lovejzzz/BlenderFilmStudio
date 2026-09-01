#!/usr/bin/env python3
"""Independent no-Blender audit of the frozen RC4 development evidence."""

import hashlib
import json
import struct
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC4-development-attempt-02")
EVIDENCE = RESEARCH / "experiments/unstaged-physical-realism/RC4-2026-09-01-development-attempt-02"
RETAINED_FAILURE = RESEARCH / "experiments/unstaged-physical-realism/RC4-2026-09-01-development-attempt-01/failure-receipt.json"
EXPECTED_WORK = "/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC4-development-attempt-02"
EXPECTED_EVIDENCE = "/Users/mengyingli/Documents/ChatGPT/MyBlenderFilmStudio/experiments/unstaged-physical-realism/RC4-2026-09-01-development-attempt-02"


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


def manifest(root, excluded=()):
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in excluded:
            rows.append({"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)})
    return rows


def png_dimensions(path):
    with path.open("rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n":
            return None
        length = struct.unpack(">I", handle.read(4))[0]
        if handle.read(4) != b"IHDR" or length < 8:
            return None
        return list(struct.unpack(">II", handle.read(8)))


def main():
    receipt = json.loads((EVIDENCE / "receipt.json").read_text(encoding="utf-8"))
    build = json.loads((EVIDENCE / "R1-build.json").read_text(encoding="utf-8"))
    reopen = json.loads((EVIDENCE / "R1-reopen.json").read_text(encoding="utf-8"))
    regressions = json.loads((EVIDENCE / "regressions.json").read_text(encoding="utf-8"))
    negative = json.loads((EVIDENCE / "negative-controls.json").read_text(encoding="utf-8"))
    render = json.loads((EVIDENCE / "render.json").read_text(encoding="utf-8"))
    processes = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((EVIDENCE / "processes").glob("*.json"))]
    image_paths = sorted((EVIDENCE / "stills").glob("*.png")) + sorted((EVIDENCE / "clip").glob("*.png"))
    unexpected_media = [str(path.relative_to(WORK)) for path in WORK.rglob("*") if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"}]
    checks = {
        "exactRoots": str(WORK.resolve()) == EXPECTED_WORK and str(EVIDENCE.resolve()) == EXPECTED_EVIDENCE,
        "retainedAttempt01Failure": RETAINED_FAILURE.is_file() and json.loads(RETAINED_FAILURE.read_text(encoding="utf-8"))["status"] == "FAIL_CANDIDATE_MODULE_NOT_LOADED",
        "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash"),
        "receiptPass": receipt["status"].startswith("PASS") and all(receipt["checks"].values()),
        "fiveBoundedProcesses": len(processes) == 5 and [row["index"] for row in processes] == [1, 2, 3, 4, 5] and all(row["exitCode"] == 0 for row in processes),
        "argvOfflineAndNoAutoexec": all("--offline-mode" in row["argv"] and "--disable-autoexec" in row["argv"] and "--background" in row["argv"] for row in processes),
        "processSelfHashes": all(row["processHash"] == self_hash(row, "processHash") for row in processes),
        "productResults": build["status"] == "PASS" and reopen["status"] == "PASS" and regressions["status"] == "PASS" and negative["status"] == "PASS",
        "solverOwnership": build["result"]["authority"]["postReleaseTransformKeyframes"] == build["result"]["authority"]["authoredOutcomeFields"] == build["result"]["authority"]["authoredContactResponsePeakOrFinalFrames"] == 0,
        "settledFrameBinding": build["result"]["cinematography"]["effect"]["frame"] == build["result"]["physics"]["settledGroupFrame"],
        "renderRoster": len(render["stills"]) == 3 and render["clip"]["frameCount"] == 48 and len(image_paths) == 51,
        "imageDimensions": all(png_dimensions(path) == [1280, 720] for path in image_paths),
        "singleBlendOnly": len(list(WORK.rglob("*.blend"))) == 1,
        "noRenderMediaInWorkRoot": not unexpected_media,
        "resourceCeilings": sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file()) <= 4 * 1024**3 and sum(path.stat().st_size for path in EVIDENCE.rglob("*") if path.is_file()) <= 256 * 1024**2,
    }
    evidence_manifest = manifest(EVIDENCE, excluded=("audit.json", "evidence-manifest.json", "work-manifest.json", "visual-review.json"))
    work_manifest = manifest(WORK)
    (EVIDENCE / "evidence-manifest.json").write_text(json.dumps(evidence_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (EVIDENCE / "work-manifest.json").write_text(json.dumps(work_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output = {
        "schemaVersion": "bfs.rc4UnstagedRealismDevelopmentAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "checkCount": len(checks),
        "passCount": sum(checks.values()),
        "receiptHash": receipt["receiptHash"],
        "evidenceManifestSha256": sha(EVIDENCE / "evidence-manifest.json"),
        "workManifestSha256": sha(EVIDENCE / "work-manifest.json"),
    }
    output["auditHash"] = self_hash(output, "auditHash")
    (EVIDENCE / "audit.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canonical(output))
    if output["status"] != "PASS":
        raise RuntimeError("RC4 development audit failed")


if __name__ == "__main__":
    main()
