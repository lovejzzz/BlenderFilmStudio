#!/usr/bin/env python3
"""Host-side bounded runner for RC6 Bullet-to-Mantaflow feasibility."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-01")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-feasibility-attempt-01"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-fluid-consequence-scene.py"
EXPECTED_BINARY_SHA256 = "ad08b54132b75325a12580f705fdefc205dd4444a36f2491e4d8a200e1091ef2"
MINIMUM_FREE = 120 * 1024**3
MINIMUM_RESERVE = 100 * 1024**3
PROJECTED_WRITES = 6 * 1024**3
WORK_LIMIT = 8 * 1024**3
EVIDENCE_LIMIT = 1024 * 1024**2


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


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def command(index, name, argv):
    stdout_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stdout.log"
    stderr_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stderr.log"
    environment = dict(os.environ)
    environment.update({
        "BLENDER_USER_CONFIG": str(WORK / "user/config"),
        "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"),
        "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"),
        "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions"),
    })
    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        done = subprocess.run(argv, cwd=RESEARCH, env=environment, stdout=stdout, stderr=stderr, check=False)
    row = {
        "index": index,
        "name": name,
        "argv": [str(value) for value in argv],
        "cwd": str(RESEARCH),
        "exitCode": done.returncode,
        "wallSeconds": round(time.monotonic() - started, 6),
        "stdoutSha256": sha(stdout_path),
        "stderrSha256": sha(stderr_path),
    }
    row["processHash"] = self_hash(row, "processHash")
    write(EVIDENCE / "processes" / f"{index:02d}-{name}.json", row)
    if done.returncode:
        raise RuntimeError(f"{name} failed")
    return row


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("RC6 feasibility roots are not fresh")
    if not BINARY.is_file() or sha(BINARY) != EXPECTED_BINARY_SHA256:
        raise RuntimeError("accepted RC5 binary identity mismatch")
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < MINIMUM_FREE or free_before < MINIMUM_RESERVE + PROJECTED_WRITES:
        raise RuntimeError("RC6 feasibility resource admission failed")
    for root in (WORK, EVIDENCE):
        root.mkdir(parents=True, exist_ok=False)
    for root in (EVIDENCE / "logs", EVIDENCE / "processes", WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions"):
        root.mkdir(parents=True, exist_ok=False)
    admission = {
        "schemaVersion": "bfs.rc6FluidConsequenceFeasibilityAdmission.v0.1",
        "status": "PASS",
        "freeBytesBefore": free_before,
        "minimumFreeBytes": MINIMUM_FREE,
        "minimumReserveBytes": MINIMUM_RESERVE,
        "projectedWriteBytes": PROJECTED_WRITES,
        "workLimitBytes": WORK_LIMIT,
        "evidenceLimitBytes": EVIDENCE_LIMIT,
        "binarySha256": sha(BINARY),
    }
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write(EVIDENCE / "admission.json", admission)

    processes = []
    try:
        common = [str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode", "--python", str(SCENE_TOOL), "--"]
        tail = ["--work-root", str(WORK), "--evidence-root", str(EVIDENCE)]
        processes.append(command(1, "build-bake-render", common + ["--action", "build", *tail]))
        blend = WORK / "RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend"
        opened = [str(BINARY), "--background", "--disable-autoexec", "--offline-mode", str(blend), "--python", str(SCENE_TOOL), "--"]
        processes.append(command(2, "reopen", opened + ["--action", "reopen", *tail]))
        video = EVIDENCE / "contact-clip.mp4"
        processes.append(command(3, "contact-video", ["/opt/homebrew/bin/ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "24", "-pattern_type", "glob", "-i", str(EVIDENCE / "clip/frame-*.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)]))

        build = json.loads((EVIDENCE / "build.json").read_text(encoding="utf-8"))
        reopen = json.loads((EVIDENCE / "reopen.json").read_text(encoding="utf-8"))
        work_bytes, evidence_bytes = tree_bytes(WORK), tree_bytes(EVIDENCE)
        checks = {
            "buildPass": build["status"] == "PASS" and all(build["result"]["checks"].values()),
            "reopenPass": reopen["status"] == "PASS" and all(reopen["checks"].values()),
            "renderRoster": len(build["renders"]["stills"]) == 3 and len(build["renders"]["clipFrames"]) == 48,
            "processCounts": len(processes) == 3 and all(row["exitCode"] == 0 for row in processes),
            "resourceCeilings": work_bytes <= WORK_LIMIT and evidence_bytes <= EVIDENCE_LIMIT and shutil.disk_usage(WORK.parent).free >= MINIMUM_RESERVE,
            "noNetwork": build["counts"]["networkCalls"] == 0 and reopen["counts"]["networkCalls"] == 0,
        }
        receipt = {
            "schemaVersion": "bfs.rc6FluidConsequenceFeasibilityReceipt.v0.1",
            "status": "PASS_PENDING_DIRECT_VISUAL_REVIEW" if all(checks.values()) else "FAIL",
            "baseline": {"productCommit": "8e18c82548f8716c415e6e1b69fdbbdeef1f1900", "binarySha256": EXPECTED_BINARY_SHA256},
            "checks": checks,
            "resultHash": build["result"]["resultHash"],
            "blendSha256": build["blend"]["sha256"],
            "videoSha256": sha(video),
            "tools": {Path(__file__).name: sha(Path(__file__)), SCENE_TOOL.name: sha(SCENE_TOOL)},
            "processes": [{"index": row["index"], "name": row["name"], "processHash": row["processHash"]} for row in processes],
            "counts": {"nativeBuilds": 0, "blenderStarts": 2, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "blendSaves": 1, "reopens": 1, "renderCalls": 51, "ffmpegProcesses": 1, "networkCalls": 0, "engineRemoteWrites": 0},
            "resources": {"freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(WORK.parent).free, "workBytes": work_bytes, "evidenceBytes": evidence_bytes},
            "claimCeiling": build["result"]["claimCeiling"],
        }
        receipt["receiptHash"] = self_hash(receipt, "receiptHash")
        write(EVIDENCE / "receipt.json", receipt)
        print("RC6_FEASIBILITY=" + canonical(receipt))
        if receipt["status"] == "FAIL":
            raise RuntimeError("RC6 feasibility receipt failed")
    except Exception as error:
        failure = {
            "schemaVersion": "bfs.rc6FluidConsequenceFeasibilityFailure.v0.1",
            "status": "FAIL",
            "errorType": type(error).__name__,
            "message": str(error),
            "completedProcesses": [{"index": row["index"], "name": row["name"], "processHash": row["processHash"]} for row in processes],
            "counts": {"nativeBuilds": 0, "blenderStartsCompleted": sum(1 for row in processes if row["name"] in {"build-bake-render", "reopen"}), "networkCalls": 0, "engineRemoteWrites": 0},
            "resources": {"freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(WORK.parent).free, "workBytes": tree_bytes(WORK), "evidenceBytes": tree_bytes(EVIDENCE)},
        }
        failure["failureHash"] = self_hash(failure, "failureHash")
        write(EVIDENCE / "failure.json", failure)
        raise


if __name__ == "__main__":
    main()
