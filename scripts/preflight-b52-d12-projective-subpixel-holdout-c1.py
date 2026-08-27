#!/usr/bin/env python3
"""Zero-output identity, correction-delta, API and disk admission for B52-D12-C1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2"
CORRECTION_SHA256 = "f540b6a2ee0bb7b2e149c795b89adbc5ab24355750f73392f21ca65c40020a79"
ORIGINAL_TOOL_FREEZE = "37fb06e68c7761dc432fa48b9287e78f7a427f24"
ORIGINAL_MKDIR = "fs.mkdirSync(args['output-dir'], { recursive: false });"
CORRECTED_MKDIR = "fs.mkdirSync(args['output-dir'], { recursive: true });"
C1_TOOL_PATHS = (
    "scripts/reconstruct-b52-d12-subpixel-c1.mjs",
    "scripts/run-b52-d12-projective-subpixel-holdout-c1.py",
    "scripts/preflight-b52-d12-projective-subpixel-holdout-c1.py",
    "tests/test_b52_d12_c1_parent_directory_contract.py",
)


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def run(argv: list[str], root: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=root, env=env, text=True, capture_output=True, check=False)


def git_identity(root: Path, commit: str, relative: str) -> dict[str, object]:
    path = root / relative
    result = run(["git", "show", f"{commit}:{relative}"], root)
    git_bytes = result.stdout.encode() if result.returncode == 0 else b""
    working_bytes = path.read_bytes() if path.is_file() else b""
    return {
        "uri": relative,
        "freezeCommit": commit,
        "workingSha256": sha_bytes(working_bytes) if working_bytes else None,
        "gitBlobSha256": sha_bytes(git_bytes) if git_bytes else None,
        "match": bool(working_bytes) and result.returncode == 0 and working_bytes == git_bytes,
    }


def write_probe_exr(path: Path, width: int, height: int) -> None:
    pixels = np.zeros((height, width, 4), dtype=np.float32)
    pixels[..., 0] = np.linspace(0.0, 1.0, width, dtype=np.float32)
    pixels[..., 1] = 0.25
    pixels[..., 2] = 0.75
    pixels[..., 3] = 1.0
    output = oiio.ImageOutput.create(str(path))
    spec = oiio.ImageSpec(width, height, 4, oiio.FLOAT)
    spec.channelnames = ("R", "G", "B", "A")
    spec.attribute("oiio:ColorSpace", "Raw")
    spec.attribute("compression", "zip")
    if output is None or not output.open(str(path), spec) or not output.write_image(pixels):
        raise RuntimeError(oiio.geterror() or "D12-C1 preflight EXR write failed")
    output.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--correction-spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()

    root = Path.cwd().resolve()
    spec_path = args.spec.resolve()
    correction_path = args.correction_spec.resolve()
    spec = json.loads(spec_path.read_text())
    correction = json.loads(correction_path.read_text())
    if sha(spec_path) != SPEC_SHA256 or sha(correction_path) != CORRECTION_SHA256:
        raise RuntimeError("B52-D12-C1 specification identity mismatch")
    if args.output.exists() or args.output.parent.exists():
        raise RuntimeError("B52-D12-C1 preflight output must be fresh")

    formal_root = root / correction["execution"]["formalOutputRoot"]
    formal_absent_before = not formal_root.exists()
    invalid_root = root / correction["invalidExecution"]["root"]
    failure_path = root / correction["invalidExecution"]["failureUri"]
    invalid_evidence = {
        "rootExists": invalid_root.is_dir(),
        "failureUri": correction["invalidExecution"]["failureUri"],
        "expectedFailureSha256": correction["invalidExecution"]["failureSha256"],
        "actualFailureSha256": sha(failure_path) if failure_path.is_file() else None,
    }
    invalid_evidence["match"] = (
        invalid_evidence["rootExists"]
        and invalid_evidence["actualFailureSha256"] == invalid_evidence["expectedFailureSha256"]
    )

    parent_rows = []
    for name, row in spec["parents"].items():
        if not isinstance(row, dict) or "uri" not in row or "sha256" not in row:
            continue
        path = root / row["uri"]
        actual = sha(path) if path.is_file() else None
        parent_rows.append({"name": name, "uri": row["uri"], "expectedSha256": row["sha256"], "actualSha256": actual, "match": actual == row["sha256"]})
    parents_match = all(row["match"] for row in parent_rows)

    runtime_rows = []
    for name in ("blender", "python", "node"):
        row = spec["runtime"][name]
        path = Path(row["executable"])
        actual = sha(path) if path.is_file() else None
        runtime_rows.append({"name": name, "uri": str(path), "expectedSha256": row["sha256"], "actualSha256": actual, "match": actual == row["sha256"]})
    ocio = root / spec["runtime"]["ocio"]["uri"]
    ocio_actual = sha(ocio) if ocio.is_file() else None
    runtime_rows.append({"name": "ocio", "uri": str(ocio), "expectedSha256": spec["runtime"]["ocio"]["sha256"], "actualSha256": ocio_actual, "match": ocio_actual == spec["runtime"]["ocio"]["sha256"]})
    runtime_match = all(row["match"] for row in runtime_rows)

    unchanged_rows = [git_identity(root, ORIGINAL_TOOL_FREEZE, relative) for relative in correction["unchangedScientificToolPaths"]]
    c1_rows = [git_identity(root, args.freeze_commit, relative) for relative in C1_TOOL_PATHS]
    tool_rows = unchanged_rows + c1_rows
    all_tools_match = all(row["match"] for row in tool_rows)

    original_node = root / correction["cause"]["originalTool"]
    corrected_node = root / C1_TOOL_PATHS[0]
    original_text = original_node.read_text() if original_node.is_file() else ""
    corrected_text = corrected_node.read_text() if corrected_node.is_file() else ""
    expected_corrected = original_text.replace(ORIGINAL_MKDIR, CORRECTED_MKDIR)
    correction_delta = {
        "originalUri": correction["cause"]["originalTool"],
        "originalExpectedSha256": correction["cause"]["originalToolSha256"],
        "originalActualSha256": sha(original_node) if original_node.is_file() else None,
        "correctedUri": C1_TOOL_PATHS[0],
        "correctedSha256": sha(corrected_node) if corrected_node.is_file() else None,
        "originalOccurrenceCount": original_text.count(ORIGINAL_MKDIR),
        "correctedOccurrenceCount": corrected_text.count(CORRECTED_MKDIR),
        "exactRegisteredReplacement": (
            sha(original_node) == correction["cause"]["originalToolSha256"]
            and original_text.count(ORIGINAL_MKDIR) == 1
            and corrected_text.count(CORRECTED_MKDIR) == 1
            and corrected_text == expected_corrected
        ) if original_node.is_file() and corrected_node.is_file() else False,
    }

    inherited_paths = (
        "specs/blender-projective-subpixel-reconstruction-holdout.v0.1.json",
        "scripts/reconstruct-b52-d12-subpixel.py",
        "scripts/reconstruct-b52-d12-subpixel.mjs",
        "tests/test_b52_d12_projective_subpixel_contract.py",
    )
    with tempfile.TemporaryDirectory(prefix="bfs-d12-c1-inherited-contract-") as inherited_text:
        inherited_root = Path(inherited_text)
        for relative in inherited_paths:
            target = inherited_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            frozen = subprocess.run(
                ["git", "show", f"{ORIGINAL_TOOL_FREEZE}:{relative}"],
                cwd=root, capture_output=True, check=True,
            ).stdout
            target.write_bytes(frozen)
        inherited_tests = run([spec["runtime"]["python"]["executable"], "-m", "unittest", "-v", "tests/test_b52_d12_projective_subpixel_contract.py"], inherited_root)
    correction_tests = run([spec["runtime"]["python"]["executable"], "-m", "unittest", "-v", "tests/test_b52_d12_c1_parent_directory_contract.py"], root)
    contract_tests = {
        "passed": inherited_tests.returncode == 0 and correction_tests.returncode == 0,
        "inherited": {"exitCode": inherited_tests.returncode, "testCount": 11, "stdout": inherited_tests.stdout, "stderr": inherited_tests.stderr},
        "missingParent": {"exitCode": correction_tests.returncode, "testCount": 1, "stdout": correction_tests.stdout, "stderr": correction_tests.stderr},
        "totalTestCount": 12,
    }

    probe_environment = {key: os.environ[key] for key in spec["runtime"]["environmentAllowlist"] if key in os.environ}
    probe_environment["OCIO"] = str(ocio.resolve())
    with tempfile.TemporaryDirectory(prefix="bfs-d12-c1-preflight-") as temp_text:
        temp = Path(temp_text)
        source_report = temp / "source-probe.json"
        source_argv = [
            spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"],
            "--python", str(root / "blender/render_b52_d12_projective_source.py"), "--",
            "--spec", str(spec_path), "--fixture", spec["fixtures"][3]["id"], "--frame", "1", "--repeat", "1",
            "--report", str(source_report), "--probe-only",
        ]
        with tempfile.TemporaryDirectory(prefix="bfs-d12-config-") as config, tempfile.TemporaryDirectory(prefix="bfs-d12-scripts-") as scripts:
            env = {**probe_environment, "BLENDER_USER_CONFIG": config, "BLENDER_USER_SCRIPTS": scripts}
            source_completed = run(source_argv, root, env)
        source_payload = json.loads(source_report.read_text()) if source_report.is_file() else {}
        source_probe = {
            "passed": source_completed.returncode == 0 and source_payload.get("probeOnly") is True and source_payload.get("operationCounts", {}).get("cyclesRayRenders") == 0 and source_payload.get("passState", {}).get("Vector") is True,
            "exitCode": source_completed.returncode, "stdout": source_completed.stdout, "stderr": source_completed.stderr, "report": source_payload,
        }

        probe_exr = temp / "probe.exr"
        write_probe_exr(probe_exr, *spec["scene"]["resolution"])
        bridge_report = temp / "bridge-probe.json"
        bridge_argv = [
            spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"],
            "--python", str(root / "blender/render_b52_d12_reconstruction_passthrough.py"), "--",
            "--spec", str(spec_path), "--fixture", spec["fixtures"][3]["id"], "--source-repeat", "1", "--bridge-repeat", "1",
            "--input", str(probe_exr), "--report", str(bridge_report), "--probe-only",
        ]
        with tempfile.TemporaryDirectory(prefix="bfs-d12-config-") as config, tempfile.TemporaryDirectory(prefix="bfs-d12-scripts-") as scripts:
            env = {**probe_environment, "BLENDER_USER_CONFIG": config, "BLENDER_USER_SCRIPTS": scripts}
            bridge_completed = run(bridge_argv, root, env)
        bridge_payload = json.loads(bridge_report.read_text()) if bridge_report.is_file() else {}
        bridge_probe = {
            "passed": bridge_completed.returncode == 0 and bridge_payload.get("graph", {}).get("match") is True and bridge_payload.get("rna", {}).get("match") is True and bridge_payload.get("operationCounts", {}).get("bridgeCompositorRenders") == 0,
            "exitCode": bridge_completed.returncode, "stdout": bridge_completed.stdout, "stderr": bridge_completed.stderr, "report": bridge_payload,
        }

    analyzer_text = (root / "scripts/analyze-b52-d12-projective-subpixel-holdout.py").read_text()
    analyzer_independent = all(token not in analyzer_text for token in ("import bpy", "import bpy_extras", "import mathutils", "import reconstruct_b52_d12", "importlib"))
    runner_text = (root / C1_TOOL_PATHS[1]).read_text()
    no_failed_root_measurement_reference = correction["invalidExecution"]["root"] not in runner_text
    available = shutil.disk_usage(root).free
    projected_write = correction["execution"]["projectedWriteBytes"]
    reserve = correction["execution"]["diskReserveBytes"]
    projected_after = available - projected_write
    disk = {"availableBytes": available, "projectedWriteBytes": projected_write, "projectedAvailableAfterBytes": projected_after, "reserveBytes": reserve, "accepted": projected_after >= reserve}
    freshness = {
        "formalRootAbsent": formal_absent_before and not formal_root.exists(),
        "failedRootRetained": invalid_evidence["match"],
        "failedRootNotRoutedAsMeasurementInput": no_failed_root_measurement_reference,
        "formalOperationCounts": {"formalRenders": 0, "formalMeasurements": 0},
    }
    freshness_matched = all((freshness["formalRootAbsent"], freshness["failedRootRetained"], freshness["failedRootNotRoutedAsMeasurementInput"]))

    accepted = all((
        parents_match, runtime_match, all_tools_match, correction_delta["exactRegisteredReplacement"],
        contract_tests["passed"], source_probe["passed"], bridge_probe["passed"], analyzer_independent,
        freshness_matched, disk["accepted"],
    ))
    body = {
        "schemaVersion": "bfs.blenderProjectiveSubpixelC1FrozenToolPreflight.v0.1",
        "experimentId": spec["experimentId"],
        "correctionId": correction["correctionId"],
        "status": "ACCEPTED" if accepted else "REJECTED",
        "freezeCommit": args.freeze_commit,
        "spec": {"uri": str(args.spec), "sha256": SPEC_SHA256},
        "correctionSpec": {"uri": str(args.correction_spec), "sha256": CORRECTION_SHA256},
        "invalidEvidence": invalid_evidence,
        "parents": parent_rows,
        "parentsMatch": parents_match,
        "runtimes": runtime_rows,
        "runtimeMatch": runtime_match,
        "tools": tool_rows,
        "allFrozenToolsMatchGit": all_tools_match,
        "correctionDelta": correction_delta,
        "contractTests": contract_tests,
        "sourceApiProbe": source_probe,
        "bridgeApiProbe": bridge_probe,
        "analyzerIndependent": analyzer_independent,
        "freshness": freshness,
        "freshnessMatched": freshness_matched,
        "formalRootAbsent": freshness["formalRootAbsent"],
        "diskAdmission": disk,
        "operationCounts": {"formalChildProcesses": 0, "formalRenders": 0, "formalMeasurements": 0, "preflightBlenderProcesses": 2, "preflightBlenderRenders": 0, "modelCalls": 0, "networkCalls": 0},
    }
    result = {**body, "preflightHash": canonical_hash(body)}
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D12_C1_PREFLIGHT status={result['status']} tools={sum(row['match'] for row in tool_rows)}/{len(tool_rows)} tests={contract_tests['passed']} delta={correction_delta['exactRegisteredReplacement']} disk={disk['accepted']}")
    if not accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
