#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed PC7 native build and filmic physics validation runner."""

import hashlib
import json
import os
import plistlib
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "specs/ai-native-studio-pc7-filmic-physics-preregistration.v0.1.json"
FREEZE = ROOT / "specs/ai-native-studio-pc7-filmic-physics-tool-freeze.v0.1.json"
HELPER = ROOT / "scripts/run-pc7-filmic-physics-product.py"
SPEC_URI = "specs/fixtures/causal-studio/PC7_F1.five-domino-filmic-physics.scene-spec.v0.2.json"
DEVELOPMENT_SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC7-development/source")
EXTERNAL = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC7-2026-09-01-attempt-01")
SOURCE = EXTERNAL / "source"
BUILD = EXTERNAL / "build"
RUNTIME = EXTERNAL / "runtime"
EVIDENCE = ROOT / "experiments/filmic-physics/PC7-2026-09-01-attempt-01"
DEPENDENCY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.6-2026-08-31-mac-m2max-attempt-01/source/lib/macos_arm64")
BINARY = BUILD / "bin/Film Studio Engine F0.app/Contents/MacOS/Blender"
FFMPEG = Path("/opt/homebrew/bin/ffmpeg")
FFPROBE = Path("/opt/homebrew/bin/ffprobe")
SOURCE_BASE = "5f3b981a6d84fd49d2eaafe35645456bf4d669e5"
SOURCE_HEAD = "c7eece67bff64cbff2de4c6e1aee3248afbca600"
DEPENDENCY_HEAD = "a76ef917b4849ba2b1b1deb1a643e131a884a63b"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def valid_self(value, field):
    expected = value.get(field)
    body = dict(value)
    body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()


def self_hashed(value, field):
    body = dict(value)
    body.pop(field, None)
    body[field] = hashlib.sha256(canonical(body)).hexdigest()
    return body


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def git(*args, cwd=SOURCE):
    result = subprocess.run(["/usr/bin/git", *args], cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def tree_bytes(path):
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file() and not item.is_symlink())


def run_process(index, name, action, blend=None, timeout=480):
    home = RUNTIME / "homes" / f"{index:02d}-{name}"
    home.mkdir(parents=True)
    environment = {
        **os.environ, "HOME": str(home), "BLENDER_USER_CONFIG": str(home / "config"),
        "BLENDER_USER_SCRIPTS": str(home / "scripts"), "BLENDER_USER_DATAFILES": str(home / "datafiles"),
        "BLENDER_USER_AUTOSAVE": str(home / "autosave"), "PYTHONNOUSERSITE": "1", "LC_ALL": "C", "LANG": "C",
    }
    argv = [str(BINARY), "--background", "--factory-startup"]
    if blend is not None:
        argv.append(str(blend))
    argv += ["--python", str(HELPER), "--", "--action", action, "--repository-root", str(ROOT), "--scene-spec-uri", SPEC_URI, "--evidence-root", str(EVIDENCE), "--work-root", str(RUNTIME)]
    started = time.time()
    result = subprocess.run(["/usr/bin/caffeinate", "-dimsu", *argv], cwd=BUILD, env=environment, text=True, capture_output=True, timeout=timeout)
    wall = time.time() - started
    stdout_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stdout.log"
    stderr_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stderr.log"
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    marker = {"negative": "PC7_NEGATIVE=", "build": "PC7_BUILD=", "reopen": "PC7_REOPEN="}[action]
    line = next((row for row in result.stdout.splitlines() if row.startswith(marker)), None)
    payload = json.loads(line[len(marker):]) if line else None
    receipt = self_hashed({
        "schemaVersion": "bfs.pc7ProcessReceipt.v0.1", "status": "PASS" if result.returncode == 0 and payload and payload.get("status") == "PASS" else "FAIL",
        "index": index, "name": name, "action": action, "argv": argv, "exitCode": result.returncode, "wallSeconds": wall,
        "stdoutSha256": sha256_file(stdout_path), "stderrSha256": sha256_file(stderr_path), "payload": payload,
    }, "processHash")
    write_json(EVIDENCE / "processes" / f"{index:02d}-{name}.json", receipt)
    if receipt["status"] != "PASS":
        raise RuntimeError(f"PC7 product process failed: {name}")
    return receipt


def encode_clip(build):
    clip = build["clip"]
    output = EVIDENCE / "review/impact-motion.mp4"
    argv = [str(FFMPEG), "-hide_banner", "-loglevel", "error", "-framerate", "24", "-start_number", str(clip["startFrame"]), "-i", str(EVIDENCE / "clip/frame-%04d.png"), "-frames:v", str(clip["frameCount"]), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
    result = subprocess.run(argv, text=True, capture_output=True, timeout=120)
    (EVIDENCE / "logs/04-ffmpeg.stdout.log").write_text(result.stdout, encoding="utf-8")
    (EVIDENCE / "logs/04-ffmpeg.stderr.log").write_text(result.stderr, encoding="utf-8")
    if result.returncode or not output.is_file():
        raise RuntimeError("PC7 clip encoding failed")
    probe_argv = [str(FFPROBE), "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames", "-of", "json", str(output)]
    probe = subprocess.run(probe_argv, text=True, capture_output=True, timeout=30)
    (EVIDENCE / "logs/05-ffprobe.stdout.log").write_text(probe.stdout, encoding="utf-8")
    (EVIDENCE / "logs/05-ffprobe.stderr.log").write_text(probe.stderr, encoding="utf-8")
    if probe.returncode:
        raise RuntimeError("PC7 clip probe failed")
    stream = json.loads(probe.stdout)["streams"][0]
    body = {
        "schemaVersion": "bfs.pc7ImpactClipReceipt.v0.1", "status": "PASS", "uri": output.relative_to(EVIDENCE).as_posix(),
        "sha256": sha256_file(output), "bytes": output.stat().st_size, "startFrame": clip["startFrame"], "endFrame": clip["endFrame"],
        "frames": int(stream["nb_read_frames"]), "width": int(stream["width"]), "height": int(stream["height"]), "fps": stream["avg_frame_rate"],
        "argv": argv, "ffmpegExitCode": result.returncode, "ffprobeExitCode": probe.returncode,
    }
    receipt = self_hashed(body, "clipHash")
    write_json(EVIDENCE / "clip-video.json", receipt)
    return receipt


def execute():
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    if not valid_self(prereg, "specHash") or not valid_self(freeze, "freezeHash"):
        raise RuntimeError("PC7 frozen contract differs")
    if freeze["preregistration"]["sha256"] != sha256_file(PREREG) or freeze["fixture"]["sha256"] != sha256_file(ROOT / SPEC_URI):
        raise RuntimeError("PC7 frozen input binding differs")
    if any(sha256_file(ROOT / row["uri"]) != row["sha256"] for row in freeze["tools"]):
        raise RuntimeError("PC7 validation tool binding differs")
    if git("rev-parse", "HEAD", cwd=DEVELOPMENT_SOURCE) != SOURCE_HEAD or git("status", "--porcelain=v1", cwd=DEVELOPMENT_SOURCE):
        raise RuntimeError("PC7 development source differs")
    if sha256_file(DEVELOPMENT_SOURCE / freeze["productSource"]["uri"]) != freeze["productSource"]["sha256"]:
        raise RuntimeError("PC7 product source binding differs")
    if EXTERNAL.exists() or EVIDENCE.exists():
        raise RuntimeError("PC7 formal roots are not fresh")
    free = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    if free < prereg["resourceCeilings"]["minimumFreeDiskGiBBeforeBuild"] * 1024 ** 3:
        raise RuntimeError("PC7 disk admission rejected")
    if git("rev-parse", "HEAD", cwd=DEPENDENCY) != DEPENDENCY_HEAD or git("status", "--porcelain=v1", cwd=DEPENDENCY):
        raise RuntimeError("PC7 accepted dependency differs")
    EXTERNAL.mkdir(parents=True)
    clone = subprocess.run(["/usr/bin/git", "clone", "--local", str(DEVELOPMENT_SOURCE), str(SOURCE)], text=True, capture_output=True)
    if clone.returncode:
        raise RuntimeError(clone.stderr)
    if git("rev-parse", "HEAD") != SOURCE_HEAD or git("status", "--porcelain=v1"):
        raise RuntimeError("PC7 formal source identity differs")
    changed = git("diff", "--name-only", f"{SOURCE_BASE}..{SOURCE_HEAD}").splitlines()
    numstat = git("diff", "--numstat", f"{SOURCE_BASE}..{SOURCE_HEAD}").splitlines()
    additions = sum(int(row.split("\t")[0]) for row in numstat)
    deletions = sum(int(row.split("\t")[1]) for row in numstat)
    if changed != prereg["authorizedProductIncrement"]["paths"] or additions > prereg["authorizedProductIncrement"]["maximumAdditions"] or deletions > prereg["authorizedProductIncrement"]["maximumDeletions"]:
        raise RuntimeError("PC7 source scope differs")
    EVIDENCE.mkdir(parents=True); (EVIDENCE / "logs").mkdir(); (EVIDENCE / "processes").mkdir()
    build_argv = ["/usr/bin/make", "-s", f"BUILD_DIR={BUILD}", f"BUILD_CMAKE_ARGS=-DLIBDIR={DEPENDENCY}", "-j", "12", "release"]
    started = time.time()
    build_result = subprocess.run(["/usr/bin/caffeinate", "-dimsu", *build_argv], cwd=SOURCE, text=True, capture_output=True, timeout=prereg["resourceCeilings"]["maximumBuildSeconds"])
    build_seconds = time.time() - started
    (EVIDENCE / "logs/build.stdout.log").write_text(build_result.stdout, encoding="utf-8")
    (EVIDENCE / "logs/build.stderr.log").write_text(build_result.stderr, encoding="utf-8")
    built_bundle = BUILD / "bin/Blender.app"
    product_bundle = BUILD / "bin/Film Studio Engine F0.app"
    if build_result.returncode == 0 and built_bundle.is_dir() and not product_bundle.exists():
        built_bundle.rename(product_bundle)
    if build_result.returncode or not BINARY.is_file():
        raise RuntimeError(f"PC7 clean build failed: {build_result.returncode}")
    with (product_bundle / "Contents/Info.plist").open("rb") as handle:
        plist = plistlib.load(handle)
    installed_module = product_bundle / "Contents/Resources/5.2/scripts/modules/film_studio_causal.py"
    RUNTIME.mkdir(); (RUNTIME / "homes").mkdir()
    processes = [
        run_process(1, "negative", "negative"),
        run_process(2, "build", "build"),
        run_process(3, "reopen", "reopen", blend=RUNTIME / "PC7_FILMIC_PHYSICS.blend"),
    ]
    negative = json.loads((EVIDENCE / "negative-controls.json").read_text(encoding="utf-8"))
    build = json.loads((EVIDENCE / "build.json").read_text(encoding="utf-8"))
    reopen = json.loads((EVIDENCE / "reopen.json").read_text(encoding="utf-8"))
    clip = encode_clip(build)
    document = json.loads((ROOT / SPEC_URI).read_text(encoding="utf-8"))
    motion = build["physics"]["motionSelection"]
    variation = document["targetGroup"]["deterministicVariation"]
    initial = build["initialConditions"]["targets"]
    bounds_ok = len(initial) == 5 and all(
        abs(row["positionX"] - document["targetGroup"]["initialPositions"][index][0]) <= variation["positionJitterMetersMaximum"] + 1e-8
        and abs(row["positionY"] - document["targetGroup"]["initialPositions"][index][1]) <= variation["positionJitterMetersMaximum"] + 1e-8
        and abs(row["yawDegrees"]) <= variation["yawJitterDegreesMaximum"] + 1e-8
        for index, row in enumerate(initial)
    )
    responses = build["physics"]["targetResponseFrames"]
    tilts = build["physics"]["finalTiltDegrees"]
    checks = {
        "sourceIdentity": git("rev-parse", "HEAD") == SOURCE_HEAD and not git("status", "--porcelain=v1"),
        "sourceScope": changed == prereg["authorizedProductIncrement"]["paths"] and additions == 116 and deletions == 15,
        "cleanNativeBuild": BINARY.is_file() and build_result.returncode == 0,
        "bundleIdentity": plist.get("CFBundleName") == plist.get("CFBundleDisplayName") == "Film Studio Engine F0" and plist.get("CFBundleIdentifier") == "studio.ainativefilm.f0",
        "installedProductModule": installed_module.is_file() and sha256_file(installed_module) == freeze["productSource"]["sha256"],
        "negativeControls": negative["status"] == "PASS" and len(negative["cases"]) == 12 and negative["v1Compatibility"]["status"] == "APPROVED_READY",
        "productProcesses": len(processes) == 3 and all(row["status"] == "PASS" for row in processes),
        "realBulletProvenance": build["provenance"]["finalPoseSource"] == "BLENDER_BULLET_RIGID_BODY",
        "noFinalPoseAuthoring": build["animation"]["actorPoseFramesAfterRelease"] == [] and all(not frames for frames in build["animation"]["targetFrames"].values()),
        "allFiveRespond": len(responses) == 5 and all(isinstance(frame, int) for frame in responses.values()),
        "allFiveTilt": len(tilts) == 5 and all(value >= document["acceptance"]["targetTiltDegreesAtFinalMinimumEach"] for value in tilts.values()),
        "impactMotionSelection": motion["impactActiveTargetCount"] >= document["acceptance"]["impactActiveTargetCountMinimum"] and motion["impactFrame"] - build["physics"]["firstTargetResponseFrame"] >= document["acceptance"]["impactFrameAfterFirstResponseMinimum"],
        "evaluatedFraming": all(row["source"] == "EVALUATED_FRAME_SEMANTIC_WORLD_BOUNDS" for row in build["framing"].values()),
        "boundedVariation": build["initialConditions"]["source"] == "SHA256_SCENE_HASH_SEED_TARGET_INDEX_CHANNEL" and bounds_ok,
        "reviewStills": len(build["review"]) == 3 and all((EVIDENCE / row["uri"]).is_file() and sha256_file(EVIDENCE / row["uri"]) == row["sha256"] for row in build["review"]),
        "impactClip": build["clip"]["frameCount"] == 24 and len({row["sha256"] for row in build["clip"]["frames"]}) >= 12 and clip["status"] == "PASS" and clip["frames"] == 24 and clip["width"] == 960 and clip["height"] == 540 and clip["fps"] == "24/1",
        "reopenExact": reopen["status"] == "PASS" and reopen["responseFramesExact"] and reopen["motionSelectionExact"],
        "dependencyRetained": git("rev-parse", "HEAD", cwd=DEPENDENCY) == DEPENDENCY_HEAD and not git("status", "--porcelain=v1", cwd=DEPENDENCY),
        "resourceCeilings": tree_bytes(EXTERNAL) <= prereg["resourceCeilings"]["workspaceBytes"] and tree_bytes(EVIDENCE) <= prereg["resourceCeilings"]["evidenceBytes"],
    }
    body = {
        "schemaVersion": "bfs.pc7FilmicPhysicsReceipt.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "verdict": "PASS" if all(checks.values()) else "FAIL",
        "claim": "The product selected impact and aftermath from evaluated Blender/Bullet motion, applied only bounded hash-derived initial variation, retained zero final-pose authority, rendered a 24-frame impact clip and reopened exactly.",
        "preregistration": {"uri": PREREG.relative_to(ROOT).as_posix(), "sha256": sha256_file(PREREG), "specHash": prereg["specHash"]},
        "source": {"baseline": SOURCE_BASE, "head": SOURCE_HEAD, "paths": changed, "additions": additions, "deletions": deletions},
        "build": {"argv": build_argv, "exitCode": build_result.returncode, "wallSeconds": build_seconds, "binary": str(BINARY), "binarySha256": sha256_file(BINARY)},
        "checks": checks, "processHashes": [row["processHash"] for row in processes], "clipHash": clip["clipHash"],
        "counters": {"cleanBuilds": 1, "productStarts": 3, "sceneMutatingExecutions": 1, "blendSaves": 1, "reopens": 1, "reviewStillRenders": 3, "impactClipFrameRenders": 24, "networkCalls": 0, "engineRemoteWrites": 0, "forcePushes": 0, "tags": 0, "releases": 0, "binaryDistribution": 0, "signing": 0, "notarization": 0},
        "resources": {"freeBytesAtAdmission": free, "workspaceBytes": tree_bytes(EXTERNAL), "evidenceBytesBeforeReceipt": tree_bytes(EVIDENCE)},
    }
    receipt = self_hashed(body, "receiptHash")
    write_json(EVIDENCE / "receipt.json", receipt)
    if receipt["status"] != "PASS":
        raise RuntimeError("PC7 receipt failed")
    print(f"PC7_EXECUTION_PASS {receipt['receiptHash']} {receipt['build']['binarySha256']} {motion['impactFrame']} {motion['aftermathFrame']}")


try:
    execute()
except Exception as error:
    if EVIDENCE.exists() and not (EVIDENCE / "failure.json").exists():
        write_json(EVIDENCE / "failure.json", self_hashed({"schemaVersion": "bfs.pc7Failure.v0.1", "status": "FAIL", "error": repr(error), "networkCalls": 0, "engineRemoteWrites": 0}, "failureHash"))
    raise
