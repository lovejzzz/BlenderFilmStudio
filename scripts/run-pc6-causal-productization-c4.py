#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""PC6 C4: retain the successful build and apply the accepted bundle rename."""

import hashlib
import json
import plistlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE_RUNNER = ROOT / "scripts/run-pc6-causal-productization.py"
C4_SPEC = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c4-preregistration.v0.5.json"
C4_FREEZE = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c4-tool-freeze.v0.5.json"
ATTEMPT01 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-01")
ATTEMPT04 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-04")
ATTEMPT05 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-05")
EVIDENCE04 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-04"
EVIDENCE05 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-05"
DEPENDENCY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.6-2026-08-31-mac-m2max-attempt-01/source/lib/macos_arm64")


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


def run(*argv, cwd=None):
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def write_json(path, body, field):
    value = dict(body)
    value[field] = hashlib.sha256(canonical(body)).hexdigest()
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


spec = json.loads(C4_SPEC.read_text(encoding="utf-8"))
freeze = json.loads(C4_FREEZE.read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or not valid_self(freeze, "freezeHash") or any(sha256_file(ROOT / row["uri"]) != row["sha256"] for row in freeze["tools"]):
    raise RuntimeError("PC6 C4 bindings differ")
retained = spec["retainedAttempt04"]
if sha256_file(EVIDENCE04 / "failure.json") != retained["failureFileSha256"]:
    raise RuntimeError("PC6 attempt-04 retained failure differs")
retained_binary = ATTEMPT04 / "build/bin/Blender.app/Contents/MacOS/Blender"
if not retained_binary.is_file() or sha256_file(retained_binary) != retained["builtBinarySha256"]:
    raise RuntimeError("PC6 attempt-04 retained binary differs")
if ATTEMPT05.exists() or EVIDENCE05.exists():
    raise RuntimeError("PC6 attempt-05 roots are not fresh")
ATTEMPT05.mkdir(parents=True)
run("/usr/bin/git", "clone", "--local", str(ATTEMPT01 / "source"), str(ATTEMPT05 / "source"))
source05 = ATTEMPT05 / "source"
gitlink = source05 / "lib/macos_arm64"
index_row = run("/usr/bin/git", "ls-files", "-s", "lib/macos_arm64", cwd=source05)
if index_row != f"160000 {spec['buildInput']['gitlinkCommit']} 0\tlib/macos_arm64" or not gitlink.is_dir() or gitlink.is_symlink() or any(gitlink.iterdir()):
    raise RuntimeError("PC6 attempt-05 gitlink checkout differs")
base_source = BASE_RUNNER.read_text(encoding="utf-8")
old_build = '    build_argv = ["/usr/bin/make", "-s", f"BUILD_DIR={BUILD}", "-j", "12", "release"]'
new_build = '    build_argv = ["/usr/bin/make", "-s", f"BUILD_DIR={BUILD}", f"BUILD_CMAKE_ARGS=-DLIBDIR={DEPENDENCY}", "-j", "12", "release"]'
old_gate = '    if build_result.returncode or not BINARY.is_file():\n        raise RuntimeError(f"PC6 clean build failed: {build_result.returncode}")'
new_gate = '''    built_bundle = BUILD / "bin/Blender.app"
    product_bundle = BUILD / "bin/Film Studio Engine F0.app"
    if build_result.returncode == 0 and built_bundle.is_dir() and not product_bundle.exists():
        built_bundle.rename(product_bundle)
    if build_result.returncode or not BINARY.is_file():
        raise RuntimeError(f"PC6 clean build failed: {build_result.returncode}")'''
if base_source.count(old_build) != 1 or base_source.count(old_gate) != 1:
    raise RuntimeError("PC6 base correction sites differ")
c4_source = base_source.replace(old_build, new_build).replace(old_gate, new_gate).rsplit("\ntry:\n    execute()", 1)[0]
namespace = {"__file__": str(BASE_RUNNER), "__name__": "pc6_base_runner_c4", "DEPENDENCY": DEPENDENCY}
exec(compile(c4_source, str(BASE_RUNNER), "exec"), namespace)
namespace["EXTERNAL"] = ATTEMPT05
namespace["SOURCE"] = source05
namespace["BUILD"] = ATTEMPT05 / "build"
namespace["RUNTIME"] = ATTEMPT05 / "runtime"
namespace["EVIDENCE"] = EVIDENCE05
namespace["BINARY"] = ATTEMPT05 / "build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender"
namespace["DEPENDENCY"] = DEPENDENCY
namespace["execute"]()
base_receipt = json.loads((EVIDENCE05 / "receipt.json").read_text(encoding="utf-8"))
product_bundle = ATTEMPT05 / spec["onlyCorrection"]["productBundle"]
built_bundle = ATTEMPT05 / spec["onlyCorrection"]["sourceBundle"]
with (product_bundle / "Contents/Info.plist").open("rb") as handle:
    plist = plistlib.load(handle)
dependency_head = run("/usr/bin/git", "rev-parse", "HEAD", cwd=DEPENDENCY)
dependency_status = run("/usr/bin/git", "status", "--porcelain=v1", cwd=DEPENDENCY)
body = {
    "schemaVersion": "bfs.pc6C4Receipt.v0.5",
    "status": base_receipt["status"],
    "correction": spec["onlyCorrection"]["operation"],
    "buildCmakeArgument": spec["buildInput"]["argument"],
    "gitlinkIndex": index_row,
    "bundle": {
        "sourceAbsentAfterRename": not built_bundle.exists(),
        "productPresentAfterRename": product_bundle.is_dir(),
        "operationCount": 1,
        "cfBundleName": plist.get("CFBundleName"),
        "cfBundleDisplayName": plist.get("CFBundleDisplayName"),
        "cfBundleIdentifier": plist.get("CFBundleIdentifier"),
    },
    "gitlinkMutations": 0,
    "dependencySymlinks": 0,
    "dependencyHeadAfterBuild": dependency_head,
    "dependencyCleanAfterBuild": dependency_status == "",
    "dependencyNetworkCalls": 0,
    "dependencyWrites": 0,
    "engineRemoteWrites": 0,
    "baseReceiptHash": base_receipt["receiptHash"],
    "retainedAttempt04FailureHash": retained["failureHash"],
}
receipt = write_json(EVIDENCE05 / "c4-receipt.json", body, "c4ReceiptHash")
print(f"PC6_C4_PASS {receipt['c4ReceiptHash']} {receipt['baseReceiptHash']}")
