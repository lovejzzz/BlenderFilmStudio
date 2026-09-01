#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""PC6 C1: fresh local clone plus one retained dependency-directory symlink."""

import hashlib
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE_RUNNER = ROOT / "scripts/run-pc6-causal-productization.py"
C1_SPEC = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c1-preregistration.v0.2.json"
C1_FREEZE = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c1-tool-freeze.v0.2.json"
ATTEMPT01 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-01")
ATTEMPT02 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-02")
EVIDENCE01 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-01"
EVIDENCE02 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-02"
DEPENDENCY_SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.6-2026-08-31-mac-m2max-attempt-01/source/lib/macos_arm64")


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


def write_json(path, body, field):
    value = dict(body)
    value[field] = hashlib.sha256(canonical(body)).hexdigest()
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


def run(*argv, cwd=None):
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def execute():
    spec = json.loads(C1_SPEC.read_text(encoding="utf-8"))
    freeze = json.loads(C1_FREEZE.read_text(encoding="utf-8"))
    if not valid_self(spec, "specHash") or not valid_self(freeze, "freezeHash"):
        raise RuntimeError("PC6 C1 spec/tool freeze invalid")
    if freeze["c1PreregistrationSha256"] != sha256_file(C1_SPEC):
        raise RuntimeError("PC6 C1 preregistration binding differs")
    if any(sha256_file(ROOT / row["uri"]) != row["sha256"] for row in freeze["tools"]):
        raise RuntimeError("PC6 C1 tool binding differs")
    retained = spec["retainedAttempt01"]
    if sha256_file(EVIDENCE01 / "failure.json") != retained["failureFileSha256"] or sha256_file(EVIDENCE01 / "logs/build.stdout.log") != retained["buildStdoutSha256"] or sha256_file(EVIDENCE01 / "logs/build.stderr.log") != retained["buildStderrSha256"]:
        raise RuntimeError("PC6 attempt-01 retained evidence differs")
    if run("/usr/bin/git", "rev-parse", "HEAD", cwd=ATTEMPT01 / "source") != retained["sourceHead"] or run("/usr/bin/git", "status", "--porcelain=v1", cwd=ATTEMPT01 / "source"):
        raise RuntimeError("PC6 attempt-01 retained source differs")
    correction = spec["onlyCorrection"]
    representative = DEPENDENCY_SOURCE / correction["representativeObject"]
    if representative.stat().st_size != correction["representativeObjectBytes"] or sha256_file(representative) != correction["representativeObjectSha256"]:
        raise RuntimeError("PC6 retained dependency object differs")
    if ATTEMPT02.exists() or EVIDENCE02.exists():
        raise RuntimeError("PC6 attempt-02 roots are not fresh")
    ATTEMPT02.mkdir(parents=True)
    run("/usr/bin/git", "clone", "--local", str(ATTEMPT01 / "source"), str(ATTEMPT02 / "source"))
    dependency_target = ATTEMPT02 / "source/lib/macos_arm64"
    if dependency_target.exists() or dependency_target.is_symlink():
        raise RuntimeError("PC6 attempt-02 dependency target is not fresh")
    os.symlink(DEPENDENCY_SOURCE, dependency_target, target_is_directory=True)
    base_source = BASE_RUNNER.read_text(encoding="utf-8")
    base_prefix = base_source.rsplit("\ntry:\n    execute()", 1)[0]
    namespace = {"__file__": str(BASE_RUNNER), "__name__": "pc6_base_runner_c1"}
    exec(compile(base_prefix, str(BASE_RUNNER), "exec"), namespace)
    namespace["EXTERNAL"] = ATTEMPT02
    namespace["SOURCE"] = ATTEMPT02 / "source"
    namespace["BUILD"] = ATTEMPT02 / "build"
    namespace["RUNTIME"] = ATTEMPT02 / "runtime"
    namespace["EVIDENCE"] = EVIDENCE02
    namespace["BINARY"] = ATTEMPT02 / "build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender"
    namespace["execute"]()
    base_receipt = json.loads((EVIDENCE02 / "receipt.json").read_text(encoding="utf-8"))
    body = {
        "schemaVersion": "bfs.pc6C1Receipt.v0.2",
        "status": base_receipt["status"],
        "correction": "ONE_LOCAL_PRECOMPILED_DEPENDENCY_DIRECTORY_SYMLINK",
        "dependencySource": str(DEPENDENCY_SOURCE),
        "dependencyTarget": str(dependency_target),
        "dependencyTargetIsSymlink": dependency_target.is_symlink(),
        "representativeObjectSha256": sha256_file(dependency_target / correction["representativeObject"]),
        "baseReceiptHash": base_receipt["receiptHash"],
        "retainedAttempt01FailureHash": retained["failureHash"],
        "networkDependencyAcquisition": 0,
        "dependencyWrites": 0,
        "engineRemoteWrites": 0,
    }
    receipt = write_json(EVIDENCE02 / "c1-receipt.json", body, "c1ReceiptHash")
    print(f"PC6_C1_PASS {receipt['c1ReceiptHash']} {base_receipt['receiptHash']}")


execute()
