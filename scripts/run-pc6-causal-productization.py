#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed PC6 product build and causal contract validation runner."""

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-preregistration.v0.1.json"
FREEZE = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-tool-freeze.v0.1.json"
EXTERNAL = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-01")
SOURCE = EXTERNAL / "source"
BUILD = EXTERNAL / "build"
RUNTIME = EXTERNAL / "runtime"
EVIDENCE = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-01"
BINARY = BUILD / "bin/Film Studio Engine F0.app/Contents/MacOS/Blender"
HELPER = ROOT / "scripts/run-pc6-causal-product.py"
SPEC_URI = "specs/fixtures/causal-studio/PC5_G1.domino-four.scene-spec.v0.1.json"
SOURCE_BASE = "aa4fff39ca5d5c4030dec2b8d0d4f576138787ad"
SOURCE_HEAD = "5f3b981a6d84fd49d2eaafe35645456bf4d669e5"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def self_hashed(value, field):
    body = dict(value)
    body.pop(field, None)
    body[field] = hashlib.sha256(canonical(body)).hexdigest()
    return body


def valid_self(value, field):
    expected = value.get(field)
    body = dict(value)
    body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def git(*args):
    result = subprocess.run(["/usr/bin/git", *args], cwd=SOURCE, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def tree_bytes(path):
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file() and not item.is_symlink())


def run_process(index, name, action, blend=None, timeout=180):
    home = RUNTIME / "homes" / f"{index:02d}-{name}"
    home.mkdir(parents=True)
    environment = {
        **os.environ,
        "HOME": str(home),
        "BLENDER_USER_CONFIG": str(home / "config"),
        "BLENDER_USER_SCRIPTS": str(home / "scripts"),
        "BLENDER_USER_DATAFILES": str(home / "datafiles"),
        "BLENDER_USER_AUTOSAVE": str(home / "autosave"),
        "PYTHONNOUSERSITE": "1",
        "LC_ALL": "C",
        "LANG": "C",
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
    marker = {"negative": "PC6_NEGATIVE=", "build": "PC6_BUILD=", "reopen": "PC6_REOPEN="}[action]
    line = next((line for line in result.stdout.splitlines() if line.startswith(marker)), None)
    payload = json.loads(line[len(marker):]) if line else None
    receipt = self_hashed({
        "schemaVersion": "bfs.pc6ProcessReceipt.v0.1",
        "status": "PASS" if result.returncode == 0 and payload and payload.get("status") == "PASS" else "FAIL",
        "index": index,
        "name": name,
        "action": action,
        "argv": argv,
        "exitCode": result.returncode,
        "wallSeconds": wall,
        "stdoutSha256": sha256_file(stdout_path),
        "stderrSha256": sha256_file(stderr_path),
        "payload": payload,
    }, "processHash")
    write_json(EVIDENCE / "processes" / f"{index:02d}-{name}.json", receipt)
    if receipt["status"] != "PASS":
        raise RuntimeError(f"PC6 process failed: {name}")
    return receipt


def execute():
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    if prereg.get("specHash") != freeze["preregistration"]["specHash"] or prereg["status"] != "PREREGISTERED_BEFORE_PRODUCT_SOURCE_OR_ATTEMPT01_MUTATION":
        raise RuntimeError("PC6 preregistration invalid")
    if not valid_self(freeze, "freezeHash") or freeze["status"] != "FROZEN_BEFORE_ATTEMPT01_BUILD_OR_PRODUCT_SCENE_MUTATION":
        raise RuntimeError("PC6 tool freeze invalid")
    if freeze["preregistration"]["sha256"] != sha256_file(PREREG):
        raise RuntimeError("PC6 preregistration binding differs")
    if any(sha256_file(ROOT / row["uri"]) != row["sha256"] for row in freeze["tools"]):
        raise RuntimeError("PC6 validation tool binding differs")
    if any(sha256_file(SOURCE / row["uri"]) != row["sha256"] for row in freeze["productSource"]["paths"]):
        raise RuntimeError("PC6 product source binding differs")
    if EVIDENCE.exists() or BUILD.exists() or RUNTIME.exists():
        raise RuntimeError("PC6 formal output roots are not fresh")
    free = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    if free < prereg["resourceCeilings"]["minimumFreeDiskGiBBeforeBuild"] * 1024 ** 3:
        raise RuntimeError("PC6 disk admission rejected")
    if git("rev-parse", "HEAD") != SOURCE_HEAD or git("status", "--porcelain=v1"):
        raise RuntimeError("PC6 source identity is not exact and clean")
    changed = git("diff", "--name-only", f"{SOURCE_BASE}..{SOURCE_HEAD}").splitlines()
    if changed != prereg["authorizedProductIncrement"]["paths"]:
        raise RuntimeError(f"PC6 changed paths differ: {changed}")
    numstat = git("diff", "--numstat", f"{SOURCE_BASE}..{SOURCE_HEAD}").splitlines()
    additions = sum(int(row.split("\t")[0]) for row in numstat)
    deletions = sum(int(row.split("\t")[1]) for row in numstat)
    if additions > prereg["authorizedProductIncrement"]["maximumAdditions"] or deletions > prereg["authorizedProductIncrement"]["maximumDeletions"]:
        raise RuntimeError("PC6 source ceiling exceeded")
    EVIDENCE.mkdir(parents=True)
    (EVIDENCE / "logs").mkdir()
    (EVIDENCE / "processes").mkdir()
    build_argv = ["/usr/bin/make", "-s", f"BUILD_DIR={BUILD}", "-j", "12", "release"]
    started = time.time()
    build_result = subprocess.run(["/usr/bin/caffeinate", "-dimsu", *build_argv], cwd=SOURCE, text=True, capture_output=True, timeout=2400)
    build_seconds = time.time() - started
    (EVIDENCE / "logs/build.stdout.log").write_text(build_result.stdout, encoding="utf-8")
    (EVIDENCE / "logs/build.stderr.log").write_text(build_result.stderr, encoding="utf-8")
    if build_result.returncode or not BINARY.is_file():
        raise RuntimeError(f"PC6 clean build failed: {build_result.returncode}")
    RUNTIME.mkdir()
    binary_hash = sha256_file(BINARY)
    processes = [
        run_process(1, "negative", "negative", timeout=120),
        run_process(2, "build", "build", timeout=240),
        run_process(3, "reopen", "reopen", blend=RUNTIME / "PC6_CAUSAL_PRODUCT.blend", timeout=120),
    ]
    build = json.loads((EVIDENCE / "build.json").read_text(encoding="utf-8"))
    reopen = json.loads((EVIDENCE / "reopen.json").read_text(encoding="utf-8"))
    negative = json.loads((EVIDENCE / "negative-controls.json").read_text(encoding="utf-8"))
    response = build["physics"]["targetResponseFrames"]
    tilts = build["physics"]["finalTiltDegrees"]
    source_stat = {"paths": changed, "additions": additions, "deletions": deletions}
    checks = {
        "sourceIdentity": git("rev-parse", "HEAD") == SOURCE_HEAD and not git("status", "--porcelain=v1"),
        "sourceScope": changed == prereg["authorizedProductIncrement"]["paths"],
        "cleanNativeBuild": build_result.returncode == 0 and BINARY.is_file(),
        "negativeControls": negative["status"] == "PASS" and len(negative["cases"]) == 9,
        "productProcesses": len(processes) == 3 and all(row["status"] == "PASS" for row in processes),
        "realBulletProvenance": build["provenance"]["finalPoseSource"] == "BLENDER_BULLET_RIGID_BODY",
        "noFinalPoseAuthoring": build["animation"]["actorPoseFramesAfterRelease"] == [] and all(not frames for frames in build["animation"]["targetFrames"].values()),
        "allTargetsRespond": len(response) == 4 and all(frame is not None for frame in response.values()),
        "allTargetsTilt": len(tilts) == 4 and all(value >= prereg["positiveValidation"]["requiredFinalTiltDegreesMinimumEach"] for value in tilts.values()),
        "evaluatedFraming": all(row["source"] == "EVALUATED_FRAME_SEMANTIC_WORLD_BOUNDS" for row in build["framing"].values()),
        "threeReviewImages": len(build["review"]) == 3 and all((EVIDENCE / row["uri"]).is_file() and sha256_file(EVIDENCE / row["uri"]) == row["sha256"] for row in build["review"]),
        "reopenExact": reopen["status"] == "PASS" and reopen["responseFramesExact"],
        "resourceCeilings": tree_bytes(EXTERNAL) <= prereg["resourceCeilings"]["workspaceBytes"] and tree_bytes(EVIDENCE) <= prereg["resourceCeilings"]["evidenceBytes"],
    }
    body = {
        "schemaVersion": "bfs.pc6CausalProductizationReceipt.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "claim": "The Film Studio product inspected and built one allowlisted declarative scene whose post-release and target poses came from Blender/Bullet, then fit three cameras to evaluated results and reopened exactly.",
        "preregistration": {"uri": PREREG.relative_to(ROOT).as_posix(), "sha256": sha256_file(PREREG), "specHash": prereg["specHash"]},
        "source": {"baseline": SOURCE_BASE, "head": SOURCE_HEAD, "stat": source_stat},
        "build": {"argv": build_argv, "exitCode": build_result.returncode, "wallSeconds": build_seconds, "binary": str(BINARY), "binarySha256": binary_hash},
        "processHashes": [row["processHash"] for row in processes],
        "checks": checks,
        "counters": {"cleanBuilds": 1, "productStarts": 3, "sceneMutatingExecutions": 1, "blendSaves": 1, "reopens": 1, "reviewRenders": 3, "networkCalls": 0, "engineRemoteWrites": 0, "releases": 0, "signing": 0, "notarization": 0},
        "resources": {"freeBytesAtAdmission": free, "workspaceBytes": tree_bytes(EXTERNAL), "evidenceBytesBeforeReceipt": tree_bytes(EVIDENCE)},
    }
    receipt = self_hashed(body, "receiptHash")
    write_json(EVIDENCE / "receipt.json", receipt)
    if receipt["status"] != "PASS":
        raise RuntimeError("PC6 receipt failed")
    print(f"PC6_EXECUTION_PASS {receipt['receiptHash']} {binary_hash}")


try:
    execute()
except Exception as error:
    if EVIDENCE.exists() and not (EVIDENCE / "failure.json").exists():
        write_json(EVIDENCE / "failure.json", self_hashed({"schemaVersion": "bfs.pc6Failure.v0.1", "status": "FAIL", "error": repr(error), "networkCalls": 0, "engineRemoteWrites": 0}, "failureHash"))
    raise
