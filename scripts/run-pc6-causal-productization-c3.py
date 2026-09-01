#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""PC6 C3: preserve the gitlink and pass the accepted dependency as LIBDIR."""

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE_RUNNER = ROOT / "scripts/run-pc6-causal-productization.py"
C3_SPEC = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c3-preregistration.v0.4.json"
C3_FREEZE = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c3-tool-freeze.v0.4.json"
ATTEMPT01 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-01")
ATTEMPT03 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-03")
ATTEMPT04 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-04")
EVIDENCE03 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-03"
EVIDENCE04 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-04"
DEPENDENCY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.6-2026-08-31-mac-m2max-attempt-01/source/lib/macos_arm64")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


spec = json.loads(C3_SPEC.read_text(encoding="utf-8"))
freeze = json.loads(C3_FREEZE.read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or not valid_self(freeze, "freezeHash") or any(sha256_file(ROOT / row["uri"]) != row["sha256"] for row in freeze["tools"]):
    raise RuntimeError("PC6 C3 bindings differ")
retained = spec["retainedAttempt03"]
if sha256_file(EVIDENCE03 / "failure.json") != retained["failureFileSha256"]:
    raise RuntimeError("PC6 attempt-03 retained failure differs")
if not (ATTEMPT03 / "source/lib/macos_arm64").is_symlink():
    raise RuntimeError("PC6 attempt-03 retained symlink observation differs")
if ATTEMPT04.exists() or EVIDENCE04.exists():
    raise RuntimeError("PC6 attempt-04 roots are not fresh")
ATTEMPT04.mkdir(parents=True)
run("/usr/bin/git", "clone", "--local", str(ATTEMPT01 / "source"), str(ATTEMPT04 / "source"))
source04 = ATTEMPT04 / "source"
gitlink = source04 / "lib/macos_arm64"
index_row = run("/usr/bin/git", "ls-files", "-s", "lib/macos_arm64", cwd=source04)
if index_row != f"160000 {retained['gitlinkCommit']} 0\tlib/macos_arm64" or not gitlink.is_dir() or gitlink.is_symlink() or any(gitlink.iterdir()):
    raise RuntimeError("PC6 attempt-04 gitlink checkout differs")
base_source = BASE_RUNNER.read_text(encoding="utf-8")
old = '    build_argv = ["/usr/bin/make", "-s", f"BUILD_DIR={BUILD}", "-j", "12", "release"]'
new = '    build_argv = ["/usr/bin/make", "-s", f"BUILD_DIR={BUILD}", f"BUILD_CMAKE_ARGS=-DLIBDIR={DEPENDENCY}", "-j", "12", "release"]'
if base_source.count(old) != 1:
    raise RuntimeError("PC6 base build argv site differs")
c3_source = base_source.replace(old, new).rsplit("\ntry:\n    execute()", 1)[0]
namespace = {"__file__": str(BASE_RUNNER), "__name__": "pc6_base_runner_c3", "DEPENDENCY": DEPENDENCY}
exec(compile(c3_source, str(BASE_RUNNER), "exec"), namespace)
namespace["EXTERNAL"] = ATTEMPT04
namespace["SOURCE"] = source04
namespace["BUILD"] = ATTEMPT04 / "build"
namespace["RUNTIME"] = ATTEMPT04 / "runtime"
namespace["EVIDENCE"] = EVIDENCE04
namespace["BINARY"] = ATTEMPT04 / "build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender"
namespace["DEPENDENCY"] = DEPENDENCY
namespace["execute"]()
base_receipt = json.loads((EVIDENCE04 / "receipt.json").read_text(encoding="utf-8"))
body = {
    "schemaVersion": "bfs.pc6C3Receipt.v0.4",
    "status": base_receipt["status"],
    "correction": "EXPLICIT_ACCEPTED_LIBDIR_WITH_GITLINK_UNCHANGED",
    "buildCmakeArgument": spec["onlyCorrection"]["buildCmakeArgument"],
    "gitlinkIndex": index_row,
    "gitlinkMutations": 0,
    "dependencySymlinks": 0,
    "dependencyNetworkCalls": 0,
    "dependencyWrites": 0,
    "engineRemoteWrites": 0,
    "baseReceiptHash": base_receipt["receiptHash"],
    "retainedAttempt03FailureHash": retained["failureHash"],
}
receipt = write_json(EVIDENCE04 / "c3-receipt.json", body, "c3ReceiptHash")
print(f"PC6_C3_PASS {receipt['c3ReceiptHash']} {receipt['baseReceiptHash']}")
