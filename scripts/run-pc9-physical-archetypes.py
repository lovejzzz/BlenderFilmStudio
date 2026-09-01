#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed PC9 clean build and metric physical-archetype formal runner."""

import hashlib
import json
import math
import os
import plistlib
import struct
import subprocess
import time
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FREEZE = ROOT / "specs/ai-native-studio-pc9-physical-archetypes-tool-freeze.v0.1.json"
SPEC_URI = "specs/fixtures/causal-studio/PC9_F1.metric-basketball-three-filled-bottles.scene-spec.v0.6.json"
DEVELOPMENT_SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC9-development/source")
EXTERNAL = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC9-2026-09-01-attempt-01")
SOURCE, BUILD, RUNTIME = EXTERNAL / "source", EXTERNAL / "build", EXTERNAL / "runtime"
EVIDENCE = ROOT / "experiments/physical-archetypes/PC9-2026-09-01-attempt-01"
DEPENDENCY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.6-2026-08-31-mac-m2max-attempt-01/source/lib/macos_arm64")
BINARY = BUILD / "bin/Film Studio Engine F0.app/Contents/MacOS/Blender"
FFMPEG, FFPROBE = Path("/opt/homebrew/bin/ffmpeg"), Path("/opt/homebrew/bin/ffprobe")
SOURCE_BASE = "9d5a66869528b66216b977c01312cdc849f28fad"
SOURCE_HEAD = "b8f65c8a6935dcbe4f47a4d070e1a971dc21563b"
DEPENDENCY_HEAD = "a76ef917b4849ba2b1b1deb1a643e131a884a63b"
PRODUCT_HELPER = ROOT / "scripts/run-pc9-physical-archetypes-product.py"
VALIDATION_HELPER = ROOT / "scripts/check-pc9-physical-archetypes-development.py"


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
def self_hashed(value, field):
    body = dict(value); body.pop(field, None); body[field] = hashlib.sha256(canonical(body)).hexdigest(); return body
def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest()
def tree_bytes(path): return 0 if not path.exists() else sum(item.stat().st_size for item in path.rglob("*") if item.is_file() and not item.is_symlink())
def git(*args, cwd=SOURCE):
    result = subprocess.run(["/usr/bin/git", *args], cwd=cwd, text=True, capture_output=True)
    if result.returncode: raise RuntimeError(result.stderr)
    return result.stdout.strip()
def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try: os.write(descriptor, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()); os.fsync(descriptor)
    finally: os.close(descriptor)


def js_number(value):
    if not math.isfinite(value): raise ValueError("nonfinite")
    if value == 0: return "0"
    absolute, source = abs(value), repr(value).lower()
    if 1e-6 <= absolute < 1e21:
        if "e" in source:
            fixed = format(Decimal(source), "f"); return fixed.rstrip("0").rstrip(".") if "." in fixed else fixed
        return source[:-2] if source.endswith(".0") else source
    if "e" not in source:
        source = format(value, ".15e"); mantissa, exponent = source.split("e"); mantissa = mantissa.rstrip("0").rstrip(".")
    else: mantissa, exponent = source.split("e")
    exponent_value = int(exponent); return f"{mantissa}e{'+' if exponent_value >= 0 else '-'}{abs(exponent_value)}"


def js_canonical(value):
    if value is None: return "null"
    if value is True: return "true"
    if value is False: return "false"
    if isinstance(value, str): return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, int): return str(value)
    if isinstance(value, float): return js_number(value)
    if isinstance(value, list): return "[" + ",".join(js_canonical(child) for child in value) + "]"
    if isinstance(value, dict): return "{" + ",".join(f"{js_canonical(key)}:{js_canonical(value[key])}" for key in sorted(value)) + "}"
    raise TypeError(type(value))


def valid_js_self(value, field):
    body = dict(value); expected = body.pop(field, None)
    return expected == hashlib.sha256(js_canonical(body).encode()).hexdigest()


def run_process(index, name, action, helper, blend=None, timeout=900):
    home = RUNTIME / "homes" / f"{index:02d}-{name}"; home.mkdir(parents=True)
    env = {**os.environ, "HOME": str(home), "BLENDER_USER_CONFIG": str(home / "config"), "BLENDER_USER_SCRIPTS": str(home / "scripts"), "BLENDER_USER_DATAFILES": str(home / "datafiles"), "BLENDER_USER_AUTOSAVE": str(home / "autosave"), "PYTHONNOUSERSITE": "1", "LC_ALL": "C", "LANG": "C"}
    argv = [str(BINARY), "--background", "--factory-startup"]
    if blend: argv.append(str(blend))
    argv += ["--disable-autoexec", "--offline-mode", "--python", str(helper), "--", "--action", action, "--repository-root", str(ROOT), "--scene-spec-uri", SPEC_URI, "--evidence-root", str(EVIDENCE)]
    if helper == VALIDATION_HELPER: argv += ["--module-root", str(BINARY.parents[1] / "Resources/5.2/scripts/modules")]
    else: argv += ["--work-root", str(RUNTIME)]
    started = time.time(); result = subprocess.run(["/usr/bin/caffeinate", "-dimsu", *argv], cwd=BUILD, env=env, text=True, capture_output=True, timeout=timeout)
    stdout, stderr = EVIDENCE / "logs" / f"{index:02d}-{name}.stdout.log", EVIDENCE / "logs" / f"{index:02d}-{name}.stderr.log"
    stdout.write_text(result.stdout, encoding="utf-8"); stderr.write_text(result.stderr, encoding="utf-8")
    receipt = self_hashed({"schemaVersion": "bfs.pc9ProcessReceipt.v0.1", "status": "PASS" if result.returncode == 0 else "FAIL", "index": index, "name": name, "action": action, "argv": argv, "exitCode": result.returncode, "wallSeconds": time.time() - started, "stdoutSha256": sha256_file(stdout), "stderrSha256": sha256_file(stderr)}, "processHash")
    write_json(EVIDENCE / "processes" / f"{index:02d}-{name}.json", receipt)
    if result.returncode: raise RuntimeError(f"PC9 product process failed: {name}")
    return receipt


def encode_clip(build):
    clip, output = build["clip"], EVIDENCE / "review/impact-motion-measured.mp4"
    argv = [str(FFMPEG), "-hide_banner", "-loglevel", "error", "-framerate", "24", "-start_number", str(clip["startFrame"]), "-i", str(EVIDENCE / "clip/frame-%04d.png"), "-frames:v", str(clip["frameCount"]), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
    result = subprocess.run(argv, text=True, capture_output=True, timeout=120)
    (EVIDENCE / "logs/04-ffmpeg.stdout.log").write_text(result.stdout); (EVIDENCE / "logs/04-ffmpeg.stderr.log").write_text(result.stderr)
    if result.returncode or not output.is_file(): raise RuntimeError("PC9 clip encoding failed")
    probe = subprocess.run([str(FFPROBE), "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames", "-of", "json", str(output)], text=True, capture_output=True, timeout=30)
    if probe.returncode: raise RuntimeError("PC9 clip probe failed")
    stream = json.loads(probe.stdout)["streams"][0]
    receipt = self_hashed({"schemaVersion": "bfs.pc9ImpactClipReceipt.v0.1", "status": "PASS", "uri": output.relative_to(EVIDENCE).as_posix(), "sha256": sha256_file(output), "bytes": output.stat().st_size, "frames": int(stream["nb_read_frames"]), "width": int(stream["width"]), "height": int(stream["height"]), "fps": stream["avg_frame_rate"], "argv": argv}, "clipHash")
    write_json(EVIDENCE / "clip-video.json", receipt); return receipt


def execute():
    freeze = json.loads(FREEZE.read_text()); prereg = json.loads((ROOT / freeze["preregistration"]["uri"]).read_text())
    if not valid_js_self(prereg, "specHash") or not valid_js_self(freeze, "freezeHash"): raise RuntimeError("PC9 frozen contract differs")
    for row in freeze["bindings"]:
        if sha256_file(ROOT / row["uri"]) != row["sha256"]: raise RuntimeError(f"PC9 frozen binding differs: {row['uri']}")
    if git("rev-parse", "HEAD", cwd=DEVELOPMENT_SOURCE) != SOURCE_HEAD or git("status", "--porcelain=v1", cwd=DEVELOPMENT_SOURCE): raise RuntimeError("PC9 development source differs")
    if sha256_file(DEVELOPMENT_SOURCE / freeze["productSource"]["uri"]) != freeze["productSource"]["sha256"]: raise RuntimeError("PC9 product module differs")
    if EXTERNAL.exists() or EVIDENCE.exists(): raise RuntimeError("PC9 formal roots are not fresh")
    free = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize; projected = 8 * 1024 ** 3
    if free < 100 * 1024 ** 3 + projected: raise RuntimeError("PC9 disk admission rejected")
    if git("rev-parse", "HEAD", cwd=DEPENDENCY) != DEPENDENCY_HEAD or git("status", "--porcelain=v1", cwd=DEPENDENCY): raise RuntimeError("PC9 dependency differs")
    EXTERNAL.mkdir(parents=True)
    clone = subprocess.run(["/usr/bin/git", "clone", "--local", str(DEVELOPMENT_SOURCE), str(SOURCE)], text=True, capture_output=True)
    if clone.returncode: raise RuntimeError(clone.stderr)
    changed = git("diff", "--name-only", f"{SOURCE_BASE}..{SOURCE_HEAD}").splitlines(); numstat = git("diff", "--numstat", f"{SOURCE_BASE}..{SOURCE_HEAD}").splitlines()
    additions = sum(int(row.split("\t")[0]) for row in numstat); deletions = sum(int(row.split("\t")[1]) for row in numstat)
    if changed != ["scripts/modules/film_studio_causal.py"] or additions > 600 or deletions > 240: raise RuntimeError("PC9 source scope differs")
    EVIDENCE.mkdir(parents=True); (EVIDENCE / "logs").mkdir(); (EVIDENCE / "processes").mkdir()
    build_argv = ["/usr/bin/make", "-s", f"BUILD_DIR={BUILD}", f"BUILD_CMAKE_ARGS=-DLIBDIR={DEPENDENCY}", "-j", "12", "release"]
    started = time.time(); built = subprocess.run(["/usr/bin/caffeinate", "-dimsu", *build_argv], cwd=SOURCE, text=True, capture_output=True, timeout=2400); build_seconds = time.time() - started
    (EVIDENCE / "logs/build.stdout.log").write_text(built.stdout); (EVIDENCE / "logs/build.stderr.log").write_text(built.stderr)
    built_bundle, product_bundle = BUILD / "bin/Blender.app", BUILD / "bin/Film Studio Engine F0.app"
    if built.returncode == 0 and built_bundle.is_dir() and not product_bundle.exists(): built_bundle.rename(product_bundle)
    if built.returncode or not BINARY.is_file(): raise RuntimeError("PC9 clean native build failed")
    with (product_bundle / "Contents/Info.plist").open("rb") as handle: plist = plistlib.load(handle)
    installed = product_bundle / "Contents/Resources/5.2/scripts/modules/film_studio_causal.py"
    RUNTIME.mkdir(); (RUNTIME / "homes").mkdir()
    processes = [run_process(1, "validation", "validate", VALIDATION_HELPER), run_process(2, "build", "build", PRODUCT_HELPER), run_process(3, "reopen", "reopen", PRODUCT_HELPER, RUNTIME / "PC9_PHYSICAL_ARCHETYPES.blend")]
    negative = json.loads((EVIDENCE / "negative-controls.json").read_text()); compat = json.loads((EVIDENCE / "backward-compatibility.json").read_text()); build = json.loads((EVIDENCE / "build.json").read_text()); reopen = json.loads((EVIDENCE / "reopen.json").read_text()); clip = encode_clip(build); document = json.loads((ROOT / SPEC_URI).read_text())
    tilts = list(build["physics"]["finalTiltDegrees"].values()); blur = build["cinematography"]["motionBlur"]; expected_mass = document["acceptance"]["derivedMassesKgExact"]; expected_solver = [struct.unpack("f", struct.pack("f", value))[0] for value in expected_mass]
    checks = {
        "sourceIdentity": git("rev-parse", "HEAD") == SOURCE_HEAD and not git("status", "--porcelain=v1"), "sourceScope": changed == ["scripts/modules/film_studio_causal.py"] and additions == 319 and deletions == 38,
        "cleanNativeBuild": BINARY.is_file(), "bundleIdentity": plist.get("CFBundleName") == plist.get("CFBundleDisplayName") == "Film Studio Engine F0" and plist.get("CFBundleIdentifier") == "studio.ainativefilm.f0",
        "installedModule": sha256_file(installed) == freeze["productSource"]["sha256"], "threeProcesses": len(processes) == 3 and all(row["status"] == "PASS" for row in processes),
        "negativeControls": negative["status"] == "PASS" and negative["caseCount"] == 29, "backwardCompatibility": compat["status"] == "PASS" and all(compat["checks"].values()),
        "allTargetsRespond": all(value is not None for value in build["physics"]["targetResponseFrames"].values()), "impactActiveTargets": build["physics"]["motionSelection"]["impactActiveTargetCount"] >= 3,
        "finalTilts": min(tilts) >= 25 and sum(value >= 60 for value in tilts) >= 2, "canonicalMasses": build["canonicalMassesKg"] == expected_mass, "solverMasses": build["solverFloat32MassesKg"] == expected_solver,
        "centersOfMass": build["centerOfMassHeightsMeters"] == document["acceptance"]["derivedCenterOfMassHeightsMetersExact"], "visibleFill": [row["fillFraction"] for row in build["physicalArchetypes"]["targets"]] == document["targetGroup"]["physicalArchetype"]["fillFractions"],
        "visibleCollisionHull": build["physicalArchetypes"]["visibleBodyIsCollisionHullSource"] and all(row["collisionShape"] == "CONVEX_HULL" and row["detailObjectCount"] >= 4 for row in build["physicalArchetypes"]["targets"]),
        "solverOwnedPoses": build["animation"]["actorPoseFramesAfterRelease"] == [] and all(not frames for frames in build["animation"]["targetFrames"].values()),
        "measuredNativeBlur": blur["nativeTransformMotionBlur"] and not blur["compositorOrPostprocessBlur"] and document["acceptance"]["measuredMedianMotionPixelsPerFrameRange"][0] <= blur["medianPixelsPerFrame"] <= document["acceptance"]["measuredMedianMotionPixelsPerFrameRange"][1],
        "refraction": all(build["refraction"]["screen"]) and all(build["refraction"]["raytrace"]), "sharpBlurredDiffer": build["sharpImpactControl"]["sha256"] != next(row["sha256"] for row in build["review"] if row["shotId"] == "IMPACT"),
        "reviewStills": len(build["review"]) == 3, "impactClip": clip["frames"] == 24 and clip["width"] == 960 and clip["height"] == 540 and len({row["sha256"] for row in build["clip"]["frames"]}) >= 12,
        "reopen": reopen["status"] == "PASS" and all(reopen["checks"].values()), "resourceCeilings": tree_bytes(EXTERNAL) <= 53687091200 and tree_bytes(EVIDENCE) <= 335544320,
    }
    receipt = self_hashed({"schemaVersion": "bfs.pc9PhysicalArchetypesReceipt.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "verdict": "PASS" if all(checks.values()) else "FAIL", "claim": "The product generated metric basketball and filled-bottle archetypes whose visible fill controls canonical mass and center of mass while Blender Bullet exclusively determines post-release poses.", "source": {"baseline": SOURCE_BASE, "head": SOURCE_HEAD, "paths": changed, "additions": additions, "deletions": deletions}, "build": {"argv": build_argv, "exitCode": built.returncode, "wallSeconds": build_seconds, "binary": str(BINARY), "binarySha256": sha256_file(BINARY)}, "checks": checks, "processHashes": [row["processHash"] for row in processes], "physics": {"targetResponseFrames": build["physics"]["targetResponseFrames"], "finalTiltDegrees": build["physics"]["finalTiltDegrees"], "motionSelection": build["physics"]["motionSelection"]}, "physicalArchetypes": build["physicalArchetypes"], "motionBlur": blur, "clipHash": clip["clipHash"], "counters": {"cleanBuilds": 1, "productStarts": 3, "sceneMutatingExecutions": 1, "sharpImpactControlRenders": 1, "productReviewStillRenders": 3, "impactClipFrameRenders": 24, "blendSaves": 1, "reopens": 1, "networkCalls": 0, "engineRemoteWrites": 0, "forcePushes": 0, "tags": 0, "releases": 0, "binaryDistribution": 0, "signing": 0, "notarization": 0}, "resources": {"freeBytesAtAdmission": free, "projectedWritesBytes": projected, "workspaceBytes": tree_bytes(EXTERNAL), "evidenceBytesBeforeReceipt": tree_bytes(EVIDENCE)}}, "receiptHash")
    write_json(EVIDENCE / "receipt.json", receipt)
    if receipt["status"] != "PASS": raise RuntimeError("PC9 receipt failed")
    print(f"PC9_EXECUTION_PASS {receipt['receiptHash']} {receipt['build']['binarySha256']}")


try: execute()
except Exception as error:
    if EVIDENCE.exists() and not (EVIDENCE / "failure.json").exists(): write_json(EVIDENCE / "failure.json", self_hashed({"schemaVersion": "bfs.pc9Failure.v0.1", "status": "FAIL", "error": repr(error), "networkCalls": 0, "engineRemoteWrites": 0}, "failureHash"))
    raise
