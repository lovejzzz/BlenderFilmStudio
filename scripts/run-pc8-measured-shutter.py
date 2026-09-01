#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed PC8 clean build and measured-shutter formal runner."""

import hashlib
import json
import os
import plistlib
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "specs/ai-native-studio-pc8-measured-shutter-c1-preregistration.v0.2.json"
FREEZE = ROOT / "specs/ai-native-studio-pc8-measured-shutter-tool-freeze.v0.1.json"
HELPER = ROOT / "scripts/run-pc8-measured-shutter-product.py"
SPEC_URI = "specs/fixtures/causal-studio/PC8_F1.measured-shutter-filmic-physics.scene-spec.v0.4.json"
PC7_BUILD = ROOT / "experiments/filmic-physics/PC7-2026-09-01-attempt-01/build.json"
DEVELOPMENT_SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC8-development/source")
EXTERNAL = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC8-2026-09-01-attempt-01")
SOURCE = EXTERNAL / "source"
BUILD = EXTERNAL / "build"
RUNTIME = EXTERNAL / "runtime"
EVIDENCE = ROOT / "experiments/measured-shutter/PC8-2026-09-01-attempt-01"
DEPENDENCY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.6-2026-08-31-mac-m2max-attempt-01/source/lib/macos_arm64")
BINARY = BUILD / "bin/Film Studio Engine F0.app/Contents/MacOS/Blender"
FFMPEG = Path("/opt/homebrew/bin/ffmpeg")
FFPROBE = Path("/opt/homebrew/bin/ffprobe")
SOURCE_BASE = "c7eece67bff64cbff2de4c6e1aee3248afbca600"
SOURCE_HEAD = "9d5a66869528b66216b977c01312cdc849f28fad"
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
    body = dict(value); body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()


def self_hashed(value, field):
    body = dict(value); body.pop(field, None)
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
    return 0 if not path.exists() else sum(item.stat().st_size for item in path.rglob("*") if item.is_file() and not item.is_symlink())


def run_product(index, name, action, blend=None, timeout=600):
    home = RUNTIME / "homes" / f"{index:02d}-{name}"
    home.mkdir(parents=True)
    environment = {**os.environ, "HOME": str(home), "BLENDER_USER_CONFIG": str(home / "config"), "BLENDER_USER_SCRIPTS": str(home / "scripts"), "BLENDER_USER_DATAFILES": str(home / "datafiles"), "BLENDER_USER_AUTOSAVE": str(home / "autosave"), "PYTHONNOUSERSITE": "1", "LC_ALL": "C", "LANG": "C"}
    argv = [str(BINARY), "--background", "--factory-startup"]
    if blend is not None:
        argv.append(str(blend))
    argv += ["--disable-autoexec", "--offline-mode", "--python", str(HELPER), "--", "--action", action, "--repository-root", str(ROOT), "--scene-spec-uri", SPEC_URI, "--evidence-root", str(EVIDENCE), "--work-root", str(RUNTIME)]
    started = time.time()
    result = subprocess.run(["/usr/bin/caffeinate", "-dimsu", *argv], cwd=BUILD, env=environment, text=True, capture_output=True, timeout=timeout)
    stdout_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stdout.log"
    stderr_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stderr.log"
    stdout_path.write_text(result.stdout, encoding="utf-8"); stderr_path.write_text(result.stderr, encoding="utf-8")
    marker = {"negative": "PC8_NEGATIVE=", "build": "PC8_BUILD=", "reopen": "PC8_REOPEN="}[action]
    line = next((row for row in result.stdout.splitlines() if row.startswith(marker)), None)
    payload = json.loads(line[len(marker):]) if line else None
    receipt = self_hashed({"schemaVersion": "bfs.pc8ProcessReceipt.v0.1", "status": "PASS" if result.returncode == 0 and payload and payload.get("status") == "PASS" else "FAIL", "index": index, "name": name, "action": action, "argv": argv, "exitCode": result.returncode, "wallSeconds": time.time() - started, "stdoutSha256": sha256_file(stdout_path), "stderrSha256": sha256_file(stderr_path), "payload": payload}, "processHash")
    write_json(EVIDENCE / "processes" / f"{index:02d}-{name}.json", receipt)
    if receipt["status"] != "PASS":
        raise RuntimeError(f"PC8 product process failed: {name}")
    return receipt


def encode_clip(build):
    clip = build["clip"]
    output = EVIDENCE / "review/impact-motion-measured.mp4"
    argv = [str(FFMPEG), "-hide_banner", "-loglevel", "error", "-framerate", "24", "-start_number", str(clip["startFrame"]), "-i", str(EVIDENCE / "clip/frame-%04d.png"), "-frames:v", str(clip["frameCount"]), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
    result = subprocess.run(argv, text=True, capture_output=True, timeout=120)
    (EVIDENCE / "logs/04-ffmpeg.stdout.log").write_text(result.stdout, encoding="utf-8"); (EVIDENCE / "logs/04-ffmpeg.stderr.log").write_text(result.stderr, encoding="utf-8")
    if result.returncode or not output.is_file():
        raise RuntimeError("PC8 clip encoding failed")
    probe_argv = [str(FFPROBE), "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames", "-of", "json", str(output)]
    probe = subprocess.run(probe_argv, text=True, capture_output=True, timeout=30)
    (EVIDENCE / "logs/05-ffprobe.stdout.log").write_text(probe.stdout, encoding="utf-8"); (EVIDENCE / "logs/05-ffprobe.stderr.log").write_text(probe.stderr, encoding="utf-8")
    if probe.returncode:
        raise RuntimeError("PC8 clip probe failed")
    stream = json.loads(probe.stdout)["streams"][0]
    receipt = self_hashed({"schemaVersion": "bfs.pc8ImpactClipReceipt.v0.1", "status": "PASS", "uri": output.relative_to(EVIDENCE).as_posix(), "sha256": sha256_file(output), "bytes": output.stat().st_size, "startFrame": clip["startFrame"], "endFrame": clip["endFrame"], "frames": int(stream["nb_read_frames"]), "width": int(stream["width"]), "height": int(stream["height"]), "fps": stream["avg_frame_rate"], "argv": argv}, "clipHash")
    write_json(EVIDENCE / "clip-video.json", receipt)
    return receipt


def execute():
    prereg = json.loads(PREREG.read_text(encoding="utf-8")); freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    if not valid_self(prereg, "specHash") or not valid_self(freeze, "freezeHash"):
        raise RuntimeError("PC8 frozen contract differs")
    if freeze["preregistration"]["sha256"] != sha256_file(PREREG) or freeze["fixture"]["sha256"] != sha256_file(ROOT / SPEC_URI) or any(sha256_file(ROOT / row["uri"]) != row["sha256"] for row in freeze["tools"]):
        raise RuntimeError("PC8 frozen bindings differ")
    if git("rev-parse", "HEAD", cwd=DEVELOPMENT_SOURCE) != SOURCE_HEAD or git("status", "--porcelain=v1", cwd=DEVELOPMENT_SOURCE) or sha256_file(DEVELOPMENT_SOURCE / freeze["productSource"]["uri"]) != freeze["productSource"]["sha256"]:
        raise RuntimeError("PC8 development source differs")
    if EXTERNAL.exists() or EVIDENCE.exists():
        raise RuntimeError("PC8 formal roots are not fresh")
    free = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    if free < 100 * 1024 ** 3:
        raise RuntimeError("PC8 disk admission rejected")
    if git("rev-parse", "HEAD", cwd=DEPENDENCY) != DEPENDENCY_HEAD or git("status", "--porcelain=v1", cwd=DEPENDENCY):
        raise RuntimeError("PC8 accepted dependency differs")
    EXTERNAL.mkdir(parents=True)
    clone = subprocess.run(["/usr/bin/git", "clone", "--local", str(DEVELOPMENT_SOURCE), str(SOURCE)], text=True, capture_output=True)
    if clone.returncode:
        raise RuntimeError(clone.stderr)
    changed = git("diff", "--name-only", f"{SOURCE_BASE}..{SOURCE_HEAD}").splitlines(); numstat = git("diff", "--numstat", f"{SOURCE_BASE}..{SOURCE_HEAD}").splitlines()
    additions = sum(int(row.split("\t")[0]) for row in numstat); deletions = sum(int(row.split("\t")[1]) for row in numstat)
    if changed != prereg["unchangedBindings"]["authorizedProductPaths"] or additions > prereg["unchangedBindings"]["maximumAdditions"] or deletions > prereg["unchangedBindings"]["maximumDeletions"]:
        raise RuntimeError("PC8 source scope differs")
    EVIDENCE.mkdir(parents=True); (EVIDENCE / "logs").mkdir(); (EVIDENCE / "processes").mkdir()
    build_argv = ["/usr/bin/make", "-s", f"BUILD_DIR={BUILD}", f"BUILD_CMAKE_ARGS=-DLIBDIR={DEPENDENCY}", "-j", "12", "release"]
    started = time.time(); build_result = subprocess.run(["/usr/bin/caffeinate", "-dimsu", *build_argv], cwd=SOURCE, text=True, capture_output=True, timeout=2400); build_seconds = time.time() - started
    (EVIDENCE / "logs/build.stdout.log").write_text(build_result.stdout, encoding="utf-8"); (EVIDENCE / "logs/build.stderr.log").write_text(build_result.stderr, encoding="utf-8")
    built_bundle = BUILD / "bin/Blender.app"; product_bundle = BUILD / "bin/Film Studio Engine F0.app"
    if build_result.returncode == 0 and built_bundle.is_dir() and not product_bundle.exists():
        built_bundle.rename(product_bundle)
    if build_result.returncode or not BINARY.is_file():
        raise RuntimeError("PC8 clean native build failed")
    with (product_bundle / "Contents/Info.plist").open("rb") as handle:
        plist = plistlib.load(handle)
    installed_module = product_bundle / "Contents/Resources/5.2/scripts/modules/film_studio_causal.py"
    RUNTIME.mkdir(); (RUNTIME / "homes").mkdir()
    processes = [run_product(1, "negative", "negative"), run_product(2, "build", "build"), run_product(3, "reopen", "reopen", blend=RUNTIME / "PC8_MEASURED_SHUTTER.blend")]
    negative = json.loads((EVIDENCE / "negative-controls.json").read_text()); build = json.loads((EVIDENCE / "build.json").read_text()); reopen = json.loads((EVIDENCE / "reopen.json").read_text()); clip = encode_clip(build)
    document = json.loads((ROOT / SPEC_URI).read_text()); pc7 = json.loads(PC7_BUILD.read_text())
    blur = build["cinematography"]["motionBlur"]; median_range = document["acceptance"]["measuredMedianMotionPixelsPerFrameRange"]; shutter_range = document["acceptance"]["computedShutterFramesRange"]
    checks = {
        "sourceIdentity": git("rev-parse", "HEAD") == SOURCE_HEAD and not git("status", "--porcelain=v1"),
        "sourceScope": changed == ["scripts/modules/film_studio_causal.py"] and additions == 120 and deletions == 16,
        "cleanNativeBuild": BINARY.is_file() and build_result.returncode == 0,
        "bundleIdentity": plist.get("CFBundleName") == plist.get("CFBundleDisplayName") == "Film Studio Engine F0" and plist.get("CFBundleIdentifier") == "studio.ainativefilm.f0",
        "installedProductModule": installed_module.is_file() and sha256_file(installed_module) == freeze["productSource"]["sha256"],
        "negativeControls": negative["status"] == "PASS" and len(negative["cases"]) == 16 and negative["v2Compatibility"]["status"] == "APPROVED_READY",
        "threeProductProcesses": len(processes) == 3 and all(row["status"] == "PASS" for row in processes),
        "primaryInitialConditionsExact": build["initialConditions"]["targets"] == pc7["initialConditions"]["targets"] and build["initialConditions"]["basisSceneSpecHash"] == prereg["variationIdentityRule"]["basisSceneSpecHash"],
        "primaryPhysicsExact": build["physics"] == pc7["physics"],
        "solverOwnedFinalPoses": build["provenance"]["finalPoseSource"] == "BLENDER_BULLET_RIGID_BODY" and build["animation"]["actorPoseFramesAfterRelease"] == [] and all(not frames for frames in build["animation"]["targetFrames"].values()),
        "measuredMotionRange": median_range[0] <= blur["medianPixelsPerFrame"] <= median_range[1],
        "computedShutterRange": shutter_range[0] <= blur["computedShutterFrames"] <= shutter_range[1],
        "computedTargetExact": blur["targetErrorPixels"] <= document["acceptance"]["computedBlurTargetErrorPixelsMaximum"],
        "nativeTransformBlurOnly": blur["nativeTransformMotionBlur"] and not blur["compositorOrPostprocessBlur"] and blur["position"] == "CENTER",
        "sharpBlurredDiffer": build["sharpImpactControl"]["sha256"] != next(row["sha256"] for row in build["review"] if row["shotId"] == "IMPACT"),
        "reviewStills": len(build["review"]) == 3 and all((EVIDENCE / row["uri"]).is_file() and sha256_file(EVIDENCE / row["uri"]) == row["sha256"] for row in build["review"]),
        "impactClip": build["clip"]["frameCount"] == 24 and len({row["sha256"] for row in build["clip"]["frames"]}) >= 12 and clip["frames"] == 24 and clip["width"] == 960 and clip["height"] == 540 and clip["fps"] == "24/1",
        "reopenExact": reopen["status"] == "PASS" and reopen["physicsExact"] and reopen["motionBlurExact"] and max(reopen["finalTiltDeltaDegrees"].values()) == 0.0,
        "resourceCeilings": tree_bytes(EXTERNAL) <= 53687091200 and tree_bytes(EVIDENCE) <= 335544320,
    }
    receipt = self_hashed({"schemaVersion": "bfs.pc8MeasuredShutterReceipt.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "verdict": "PASS" if all(checks.values()) else "FAIL", "claim": "The product preserved the accepted PC7 Bullet solve exactly and derived native transform motion blur from evaluated projected semantic motion.", "preregistration": {"uri": PREREG.relative_to(ROOT).as_posix(), "sha256": sha256_file(PREREG), "specHash": prereg["specHash"]}, "source": {"baseline": SOURCE_BASE, "head": SOURCE_HEAD, "paths": changed, "additions": additions, "deletions": deletions}, "build": {"argv": build_argv, "exitCode": build_result.returncode, "wallSeconds": build_seconds, "binary": str(BINARY), "binarySha256": sha256_file(BINARY)}, "checks": checks, "processHashes": [row["processHash"] for row in processes], "motionBlur": blur, "clipHash": clip["clipHash"], "counters": {"cleanBuilds": 1, "productStarts": 3, "sceneMutatingExecutions": 1, "sharpImpactControlRenders": 1, "productReviewStillRenders": 3, "impactClipFrameRenders": 24, "blendSaves": 1, "reopens": 1, "networkCalls": 0, "engineRemoteWrites": 0, "forcePushes": 0, "tags": 0, "releases": 0, "binaryDistribution": 0, "signing": 0, "notarization": 0}, "resources": {"freeBytesAtAdmission": free, "workspaceBytes": tree_bytes(EXTERNAL), "evidenceBytesBeforeReceipt": tree_bytes(EVIDENCE)}}, "receiptHash")
    write_json(EVIDENCE / "receipt.json", receipt)
    if receipt["status"] != "PASS":
        raise RuntimeError("PC8 receipt failed")
    print(f"PC8_EXECUTION_PASS {receipt['receiptHash']} {receipt['build']['binarySha256']} {blur['medianPixelsPerFrame']} {blur['computedShutterFrames']}")


try:
    execute()
except Exception as error:
    if EVIDENCE.exists() and not (EVIDENCE / "failure.json").exists():
        write_json(EVIDENCE / "failure.json", self_hashed({"schemaVersion": "bfs.pc8Failure.v0.1", "status": "FAIL", "error": repr(error), "networkCalls": 0, "engineRemoteWrites": 0}, "failureHash"))
    raise
