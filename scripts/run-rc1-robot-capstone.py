#!/usr/bin/env python3
"""Run the frozen RC1 robot-capstone machine stage in fresh roots."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORKSPACE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC1-2026-09-01-attempt-02")
EVIDENCE = RESEARCH / "experiments/robot-capstone/RC1-2026-09-01-attempt-02"
PRODUCT_SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC1-development/source")
PRODUCT_COMMIT = "0e84ef3b6f79521b4f21a9d12a180dfd9713aab4"
PRODUCT_PARENT = "b8f65c8a6935dcbe4f47a4d070e1a971dc21563b"
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC4-VX2-2026-08-31-attempt-01/FILM_LANGUAGE_IMPROVEMENT.blend")
SOURCE_BLEND_SHA256 = "e4dec4948f24f843effe29806fed7f8000f9e06ff5f8a7bc2d7a4b998fce1875"
DEPENDENCIES = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.6-2026-08-31-mac-m2max-attempt-01/source/lib/macos_arm64")
LFS_OBJECTS = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC9-2026-09-01-attempt-01/source/.git/lfs/objects")
SPEC_URI = "specs/fixtures/robot-holdout/RC1.guardian-spring-control.performance-spec.v0.2.json"
PC9_SPEC_URI = "specs/fixtures/causal-studio/PC9_F1.metric-basketball-three-filled-bottles.scene-spec.v0.6.json"
MINIMUM_RESERVE = 100 * 1024**3
PROJECTED_WRITES = 8 * 1024**3
WORKSPACE_LIMIT = 50 * 1024**3
EVIDENCE_LIMIT = 512 * 1024**2


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def directory_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def command(index, name, argv, cwd=None, env=None):
    logs = EVIDENCE / "logs"
    stdout_path = logs / f"{index:02d}-{name}.stdout.log"
    stderr_path = logs / f"{index:02d}-{name}.stderr.log"
    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        completed = subprocess.run(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr, check=False)
    receipt = {
        "index": index,
        "name": name,
        "argv": [str(value) for value in argv],
        "cwd": None if cwd is None else str(cwd),
        "exitCode": completed.returncode,
        "wallSeconds": round(time.monotonic() - started, 6),
        "stdoutSha256": sha256_file(stdout_path),
        "stderrSha256": sha256_file(stderr_path),
    }
    receipt["processHash"] = self_hash(receipt, "processHash")
    write(EVIDENCE / "processes" / f"{index:02d}-{name}.json", receipt)
    if completed.returncode != 0:
        raise RuntimeError(f"{name} failed; see {stderr_path}")
    return receipt


def output(argv, cwd=None):
    return subprocess.check_output(argv, cwd=cwd, text=True).strip()


def main():
    if WORKSPACE.exists() or EVIDENCE.exists():
        raise RuntimeError("formal RC1 root is not fresh")
    if output(["git", "-C", str(PRODUCT_SOURCE), "rev-parse", "HEAD"]) != PRODUCT_COMMIT:
        raise RuntimeError("product source commit mismatch")
    if output(["git", "-C", str(PRODUCT_SOURCE), "status", "--porcelain"]):
        raise RuntimeError("product source is not clean")
    if sha256_file(SOURCE_BLEND) != SOURCE_BLEND_SHA256:
        raise RuntimeError("source blend hash mismatch")
    usage = shutil.disk_usage(WORKSPACE.parent)
    if usage.free < MINIMUM_RESERVE + PROJECTED_WRITES:
        raise RuntimeError("resource admission failed")

    for path in (WORKSPACE, EVIDENCE, EVIDENCE / "logs", EVIDENCE / "processes", WORKSPACE / "runtime"):
        path.mkdir(parents=True, exist_ok=False)
    admission = {
        "schemaVersion": "bfs.rc1ResourceAdmission.v0.1",
        "status": "PASS",
        "freeBytesBefore": usage.free,
        "minimumReserveBytes": MINIMUM_RESERVE,
        "projectedWriteBytes": PROJECTED_WRITES,
        "workspaceLimitBytes": WORKSPACE_LIMIT,
        "evidenceLimitBytes": EVIDENCE_LIMIT,
    }
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write(EVIDENCE / "admission.json", admission)

    source = WORKSPACE / "source"
    build = WORKSPACE / "build"
    runtime = WORKSPACE / "runtime"
    env = dict(os.environ)
    env.update({"GIT_LFS_SKIP_SMUDGE": "1", "GIT_TERMINAL_PROMPT": "0"})
    processes = []
    processes.append(command(1, "local-clone", ["git", "clone", "--local", "--no-hardlinks", "--no-checkout", str(PRODUCT_SOURCE), str(source)], env=env))
    lfs_dir = source / ".git/lfs"
    lfs_dir.mkdir(parents=True, exist_ok=True)
    objects = lfs_dir / "objects"
    if objects.exists() and not objects.is_symlink():
        objects.rmdir()
    objects.symlink_to(LFS_OBJECTS, target_is_directory=True)
    processes.append(command(2, "checkout", ["git", "checkout", "--detach", PRODUCT_COMMIT], cwd=source, env=env))
    processes.append(command(3, "lfs-checkout", ["git", "lfs", "checkout"], cwd=source, env=env))
    if output(["git", "rev-parse", "HEAD"], source) != PRODUCT_COMMIT or output(["git", "status", "--porcelain"], source):
        raise RuntimeError("formal source identity or cleanliness mismatch")

    build_argv = ["/usr/bin/make", "-s", f"BUILD_DIR={build}", f"BUILD_CMAKE_ARGS=-DLIBDIR={DEPENDENCIES}", "-j", "12", "release"]
    processes.append(command(4, "clean-native-build", build_argv, cwd=source, env=env))
    built_bundle = build / "bin/Blender.app"
    product_bundle = build / "bin/Film Studio Engine F0.app"
    if not built_bundle.is_dir() or product_bundle.exists():
        raise RuntimeError("C3 bundle rename precondition failed")
    built_bundle.rename(product_bundle)
    rename_receipt = {"schemaVersion": "bfs.rc1BundleRename.v0.1", "status": "PASS", "source": str(built_bundle), "destination": str(product_bundle), "sourceAbsentAfter": not built_bundle.exists(), "destinationPresentAfter": product_bundle.is_dir(), "retainedAttempt01FailureHash": "8adebb9bfdcfbe81d1991ac42cff1401a5d85a3a3f5c7ed6809870288b3d0e01"}
    rename_receipt["renameHash"] = self_hash(rename_receipt, "renameHash")
    write(EVIDENCE / "bundle-rename.json", rename_receipt)
    binary = build / "bin/Film Studio Engine F0.app/Contents/MacOS/Blender"
    module_root = build / "bin/Film Studio Engine F0.app/Contents/Resources/5.2/scripts/modules"
    if not binary.is_file() or not (module_root / "film_studio_physical_performance.py").is_file():
        raise RuntimeError("built product or installed module missing")

    common = [str(binary), "--background", "--disable-autoexec", "--offline-mode"]
    processes.append(command(5, "pc8-pc9-regression", common + ["--factory-startup", "--python", str(RESEARCH / "scripts/check-pc9-physical-archetypes-development.py"), "--", "--action", "validate", "--repository-root", str(RESEARCH), "--scene-spec-uri", PC9_SPEC_URI, "--evidence-root", str(EVIDENCE), "--module-root", str(module_root)], cwd=RESEARCH))
    product_tool = RESEARCH / "scripts/run-rc1-robot-capstone-product.py"
    processes.append(command(6, "robot-build", common + [str(SOURCE_BLEND), "--python", str(product_tool), "--", "--action", "build", "--repository-root", str(RESEARCH), "--scene-spec-uri", SPEC_URI, "--evidence-root", str(EVIDENCE), "--work-root", str(runtime)], cwd=RESEARCH))
    saved_blend = runtime / "RC1_PHYSICAL_PERFORMANCE.blend"
    processes.append(command(7, "robot-reopen", common + [str(saved_blend), "--python", str(product_tool), "--", "--action", "reopen", "--repository-root", str(RESEARCH), "--scene-spec-uri", SPEC_URI, "--evidence-root", str(EVIDENCE), "--work-root", str(runtime)], cwd=RESEARCH))
    review = EVIDENCE / "review"
    video = review / "contact-clip-frame-0159-0206.mp4"
    processes.append(command(8, "ffmpeg", ["/opt/homebrew/bin/ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "24", "-start_number", "159", "-i", str(EVIDENCE / "clip/frame-%04d.png"), "-frames:v", "48", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)]))
    probe_path = EVIDENCE / "clip-video.json"
    probe = json.loads(output(["/opt/homebrew/bin/ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames", "-of", "json", str(video)]))
    clip_video = {"schemaVersion": "bfs.rc1ClipVideo.v0.1", "status": "PASS", "path": str(video), "sha256": sha256_file(video), "bytes": video.stat().st_size, "probe": probe}
    clip_video["clipVideoHash"] = self_hash(clip_video, "clipVideoHash")
    write(probe_path, clip_video)

    workspace_bytes = directory_bytes(WORKSPACE)
    evidence_bytes = directory_bytes(EVIDENCE)
    if workspace_bytes > WORKSPACE_LIMIT or evidence_bytes > EVIDENCE_LIMIT or shutil.disk_usage(WORKSPACE.parent).free < MINIMUM_RESERVE:
        raise RuntimeError("post-run resource ceiling failed")
    changed = output(["git", "diff", "--numstat", PRODUCT_PARENT, PRODUCT_COMMIT, "--", "scripts/modules/film_studio_physical_performance.py", "scripts/startup/bl_operators/film_studio_workspace.py"], source)
    receipt = {
        "schemaVersion": "bfs.rc1RobotCapstoneMachineReceipt.v0.1",
        "status": "PASS_PENDING_DIRECT_VISUAL_AND_INDEPENDENT_AUDIT",
        "productCommit": PRODUCT_COMMIT,
        "productParent": PRODUCT_PARENT,
        "correctionHash": "44408a780b686f847ea2d46486a4fcd2256ff70a066e3697d22bac1d820487e2",
        "retainedAttempt01FailureHash": "8adebb9bfdcfbe81d1991ac42cff1401a5d85a3a3f5c7ed6809870288b3d0e01",
        "sourceBlendSha256": SOURCE_BLEND_SHA256,
        "performanceSpecHash": json.loads((RESEARCH / SPEC_URI).read_text(encoding="utf-8"))["performanceSpecHash"],
        "binary": {"path": str(binary), "sha256": sha256_file(binary), "bytes": binary.stat().st_size},
        "installedModule": {"path": str(module_root / "film_studio_physical_performance.py"), "sha256": sha256_file(module_root / "film_studio_physical_performance.py")},
        "tools": {path.name: sha256_file(path) for path in (Path(__file__).resolve(), product_tool, RESEARCH / "scripts/check-pc9-physical-archetypes-development.py")},
        "sourceDiffNumstat": changed.splitlines(),
        "processes": [{"index": row["index"], "name": row["name"], "processHash": row["processHash"]} for row in processes],
        "counts": {"cleanNativeBuilds": 1, "productStarts": 3, "sceneMutatingExecutions": 1, "blendSaves": 1, "reopens": 1, "reviewStillRenders": 3, "contactClipFrameRenders": 48, "networkCalls": 0, "engineRemoteWrites": 0, "forcePushes": 0, "tags": 0, "releases": 0, "binaryDistribution": 0, "signing": 0, "notarization": 0},
        "resources": {"workspaceBytes": workspace_bytes, "evidenceBytes": evidence_bytes, "freeBytesAfter": shutil.disk_usage(WORKSPACE.parent).free},
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write(EVIDENCE / "receipt.json", receipt)
    print("RC1_MACHINE_STAGE=" + canonical(receipt))


if __name__ == "__main__":
    main()
