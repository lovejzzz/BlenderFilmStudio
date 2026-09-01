#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""PC6 C2: remove one verified empty clone-created directory before C1 link."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
C1_RUNNER = ROOT / "scripts/run-pc6-causal-productization-c1.py"
C2_SPEC = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c2-preregistration.v0.3.json"
C2_FREEZE = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c2-tool-freeze.v0.3.json"
ATTEMPT02 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-02")
ATTEMPT03 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-03")
EVIDENCE02 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-02"
EVIDENCE03 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-03"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_self(value, field):
    expected = value.get(field)
    body = dict(value)
    body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()


def write_json(path, body, field):
    value = dict(body)
    value[field] = hashlib.sha256(canonical(body)).hexdigest()
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


spec = json.loads(C2_SPEC.read_text(encoding="utf-8"))
freeze = json.loads(C2_FREEZE.read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or not valid_self(freeze, "freezeHash"):
    raise RuntimeError("PC6 C2 spec/tool freeze invalid")
if freeze["c2PreregistrationSha256"] != sha256_file(C2_SPEC) or any(sha256_file(ROOT / row["uri"]) != row["sha256"] for row in freeze["tools"]):
    raise RuntimeError("PC6 C2 bindings differ")
retained = spec["retainedAttempt02"]
if sha256_file(EVIDENCE02 / "failure.json") != retained["failureFileSha256"]:
    raise RuntimeError("PC6 attempt-02 retained failure differs")
target02 = ATTEMPT02 / "source/lib/macos_arm64"
if not target02.is_dir() or target02.is_symlink() or any(target02.iterdir()):
    raise RuntimeError("PC6 attempt-02 empty-directory observation differs")
if ATTEMPT03.exists() or EVIDENCE03.exists():
    raise RuntimeError("PC6 attempt-03 roots are not fresh")
c1_source = C1_RUNNER.read_text(encoding="utf-8")
old = '''    if dependency_target.exists() or dependency_target.is_symlink():
        raise RuntimeError("PC6 attempt-02 dependency target is not fresh")
    os.symlink(DEPENDENCY_SOURCE, dependency_target, target_is_directory=True)'''
new = '''    if not dependency_target.is_dir() or dependency_target.is_symlink() or any(dependency_target.iterdir()):
        raise RuntimeError("PC6 attempt-03 clone-created dependency directory is not exactly empty")
    dependency_target.rmdir()
    os.symlink(DEPENDENCY_SOURCE, dependency_target, target_is_directory=True)'''
if c1_source.count(old) != 1:
    raise RuntimeError("PC6 C1 correction site differs")
c2_source = c1_source.replace(old, new).rsplit("\nexecute()", 1)[0]
namespace = {"__file__": str(C1_RUNNER), "__name__": "pc6_c1_runner_c2"}
exec(compile(c2_source, str(C1_RUNNER), "exec"), namespace)
namespace["ATTEMPT02"] = ATTEMPT03
namespace["EVIDENCE02"] = EVIDENCE03
namespace["execute"]()
c1_receipt = json.loads((EVIDENCE03 / "c1-receipt.json").read_text(encoding="utf-8"))
body = {
    "schemaVersion": "bfs.pc6C2Receipt.v0.3",
    "status": c1_receipt["status"],
    "correction": "REMOVE_ONE_VERIFIED_EMPTY_DIRECTORY_THEN_CREATE_C1_DEPENDENCY_SYMLINK",
    "removedEmptyDirectories": 1,
    "dependencySymlinks": 1,
    "baseReceiptHash": c1_receipt["baseReceiptHash"],
    "c1ReceiptHash": c1_receipt["c1ReceiptHash"],
    "retainedAttempt02FailureHash": retained["failureHash"],
    "networkCalls": 0,
    "dependencyWrites": 0,
    "engineRemoteWrites": 0,
}
receipt = write_json(EVIDENCE03 / "c2-receipt.json", body, "c2ReceiptHash")
print(f"PC6_C2_PASS {receipt['c2ReceiptHash']} {receipt['baseReceiptHash']}")
