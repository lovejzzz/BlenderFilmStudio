#!/usr/bin/env python3
"""C1 host runner with exact stage-artifact and success-sentinel enforcement."""

import importlib.util
import json
import shutil
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE_PATH = RESEARCH / "scripts/run-rc6-fluid-consequence-feasibility.py"
spec = importlib.util.spec_from_file_location("rc6_feasibility_base", BASE_PATH)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-02")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-feasibility-attempt-02"
SCENE_TOOL = RESEARCH / "scripts/run-rc6-fluid-consequence-scene-c1.py"
base.WORK = WORK
base.EVIDENCE = EVIDENCE
base.SCENE_TOOL = SCENE_TOOL


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("RC6 C1 feasibility roots are not fresh")
    if not base.BINARY.is_file() or base.sha(base.BINARY) != base.EXPECTED_BINARY_SHA256:
        raise RuntimeError("accepted RC5 binary identity mismatch")
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < base.MINIMUM_FREE or free_before < base.MINIMUM_RESERVE + base.PROJECTED_WRITES:
        raise RuntimeError("RC6 C1 feasibility resource admission failed")
    for root in (WORK, EVIDENCE):
        root.mkdir(parents=True, exist_ok=False)
    for root in (EVIDENCE / "logs", EVIDENCE / "processes", WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions"):
        root.mkdir(parents=True, exist_ok=False)
    admission = {
        "schemaVersion": "bfs.rc6FluidConsequenceFeasibilityC1Admission.v0.1",
        "status": "PASS",
        "freeBytesBefore": free_before,
        "minimumFreeBytes": base.MINIMUM_FREE,
        "minimumReserveBytes": base.MINIMUM_RESERVE,
        "projectedWriteBytes": base.PROJECTED_WRITES,
        "workLimitBytes": base.WORK_LIMIT,
        "evidenceLimitBytes": base.EVIDENCE_LIMIT,
        "binarySha256": base.sha(base.BINARY),
        "retainedAttempt01FailureAuditHash": "864aa40aad30c38f54c71a26898ed84e8d209ef88b8068a08556f1b195ecb7df",
    }
    admission["admissionHash"] = base.self_hash(admission, "admissionHash")
    base.write(EVIDENCE / "admission.json", admission)

    processes = []

    def stage(index, name, argv, expected, sentinel):
        row = base.command(index, name, argv)
        processes.append(row)
        stdout = (EVIDENCE / "logs" / f"{index:02d}-{name}.stdout.log").read_text(encoding="utf-8", errors="replace")
        stderr = (EVIDENCE / "logs" / f"{index:02d}-{name}.stderr.log").read_text(encoding="utf-8", errors="replace")
        if sentinel not in stdout or "Traceback (most recent call last)" in stderr or not all(path.exists() for path in expected):
            raise RuntimeError(f"{name} failed exact stage-artifact enforcement")
        return row

    try:
        common = [str(base.BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode", "--python", str(SCENE_TOOL), "--"]
        tail = ["--work-root", str(WORK), "--evidence-root", str(EVIDENCE)]
        blend = WORK / "RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend"
        stage(1, "build-bake-render", common + ["--action", "build", *tail], [blend, EVIDENCE / "build.json", EVIDENCE / "clip/frame-0048.png"], "RC6_BUILD=")
        opened = [str(base.BINARY), "--background", "--disable-autoexec", "--offline-mode", str(blend), "--python", str(SCENE_TOOL), "--"]
        stage(2, "reopen", opened + ["--action", "reopen", *tail], [EVIDENCE / "reopen.json"], "RC6_REOPEN=")
        video = EVIDENCE / "contact-clip.mp4"
        row = base.command(3, "contact-video", ["/opt/homebrew/bin/ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "24", "-pattern_type", "glob", "-i", str(EVIDENCE / "clip/frame-*.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)])
        processes.append(row)
        if not video.is_file():
            raise RuntimeError("contact-video missing exact stage artifact")

        build = json.loads((EVIDENCE / "build.json").read_text(encoding="utf-8"))
        reopen = json.loads((EVIDENCE / "reopen.json").read_text(encoding="utf-8"))
        work_bytes, evidence_bytes = base.tree_bytes(WORK), base.tree_bytes(EVIDENCE)
        checks = {
            "worldCorrectionBound": admission["retainedAttempt01FailureAuditHash"] == "864aa40aad30c38f54c71a26898ed84e8d209ef88b8068a08556f1b195ecb7df",
            "stageArtifactEnforcement": len(processes) == 3,
            "buildPass": build["status"] == "PASS" and all(build["result"]["checks"].values()),
            "reopenPass": reopen["status"] == "PASS" and all(reopen["checks"].values()),
            "renderRoster": len(build["renders"]["stills"]) == 3 and len(build["renders"]["clipFrames"]) == 48,
            "resourceCeilings": work_bytes <= base.WORK_LIMIT and evidence_bytes <= base.EVIDENCE_LIMIT and shutil.disk_usage(WORK.parent).free >= base.MINIMUM_RESERVE,
            "noNetwork": build["counts"]["networkCalls"] == 0 and reopen["counts"]["networkCalls"] == 0,
        }
        receipt = {
            "schemaVersion": "bfs.rc6FluidConsequenceFeasibilityC1Receipt.v0.1",
            "status": "PASS_PENDING_DIRECT_VISUAL_REVIEW" if all(checks.values()) else "FAIL",
            "baseline": {"productCommit": "8e18c82548f8716c415e6e1b69fdbbdeef1f1900", "binarySha256": base.EXPECTED_BINARY_SHA256},
            "checks": checks,
            "resultHash": build["result"]["resultHash"],
            "blendSha256": build["blend"]["sha256"],
            "videoSha256": base.sha(video),
            "tools": {Path(__file__).name: base.sha(Path(__file__)), SCENE_TOOL.name: base.sha(SCENE_TOOL), BASE_PATH.name: base.sha(BASE_PATH)},
            "processes": [{"index": row["index"], "name": row["name"], "processHash": row["processHash"]} for row in processes],
            "counts": {"nativeBuilds": 0, "blenderStarts": 2, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "blendSaves": 1, "reopens": 1, "renderCalls": 51, "ffmpegProcesses": 1, "networkCalls": 0, "engineRemoteWrites": 0},
            "resources": {"freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(WORK.parent).free, "workBytes": work_bytes, "evidenceBytes": evidence_bytes},
            "claimCeiling": build["result"]["claimCeiling"],
        }
        receipt["receiptHash"] = base.self_hash(receipt, "receiptHash")
        base.write(EVIDENCE / "receipt.json", receipt)
        print("RC6_C1_FEASIBILITY=" + base.canonical(receipt))
        if receipt["status"] == "FAIL":
            raise RuntimeError("RC6 C1 feasibility receipt failed")
    except Exception as error:
        failure = {
            "schemaVersion": "bfs.rc6FluidConsequenceFeasibilityC1Failure.v0.1",
            "status": "FAIL",
            "errorType": type(error).__name__,
            "message": str(error),
            "completedProcesses": [{"index": row["index"], "name": row["name"], "processHash": row["processHash"]} for row in processes],
            "counts": {"nativeBuilds": 0, "blenderStartsCompleted": sum(1 for row in processes if row["name"] in {"build-bake-render", "reopen"}), "networkCalls": 0, "engineRemoteWrites": 0},
            "resources": {"freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(WORK.parent).free, "workBytes": base.tree_bytes(WORK), "evidenceBytes": base.tree_bytes(EVIDENCE)},
        }
        failure["failureHash"] = base.self_hash(failure, "failureHash")
        base.write(EVIDENCE / "failure.json", failure)
        raise


if __name__ == "__main__":
    main()
