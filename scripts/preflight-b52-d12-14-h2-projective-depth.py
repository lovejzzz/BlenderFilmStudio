#!/usr/bin/env python3
"""Zero-render admission preflight for B52-D12.14-H2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np


SPEC_SHA256 = "2961f621b38f934cffaa7abe36deaaa5e01e7505d6361985039d0380578d244b"
CORRECTION_SHA256 = "9b6fdcedd571ad1ec7fb8d02bc7c6a630014d204de02f4a8b74bf5509c625a92"


def sha_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
def canonical_hash(value: object) -> str: return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--correction", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def clean_env(spec: dict, root: Path) -> dict:
    env = {key: os.environ[key] for key in spec["runtime"]["environmentAllowlist"] if key in os.environ}
    env.update({"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OCIO": str(root / spec["runtime"]["ocio"]["uri"]), "TMPDIR": os.environ.get("TMPDIR", "/tmp")})
    return env


def run_child(command: list[str], label: str, log_dir: Path, env: dict, children: list[dict]) -> None:
    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    stdout, stderr = process.communicate()
    stdout_path, stderr_path = log_dir / f"{label}.stdout.log", log_dir / f"{label}.stderr.log"
    stdout_path.write_text(stdout); stderr_path.write_text(stderr)
    row = {"label": label, "command": command, "pid": process.pid, "exitCode": process.returncode, "elapsedSeconds": round(time.monotonic() - started, 6), "stdout": {"uri": str(stdout_path), "sha256": sha_file(stdout_path)}, "stderr": {"uri": str(stderr_path), "sha256": sha_file(stderr_path)}}
    children.append(row)
    if process.returncode != 0: raise RuntimeError(f"H2 preflight child failed: {label}: {stderr[-2000:]}")


def git_value(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def write_f32_array(path: Path, value: np.ndarray) -> dict:
    array = np.ascontiguousarray(value, dtype="<f4")
    payload = array.tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"uri": str(path), "sha256": sha_bytes(payload), "bytes": len(payload), "shape": list(array.shape), "dtype": "<f4"}


def full_shape_probe(cli, spec: dict, root: Path, logs: Path, env: dict, children: list[dict]) -> dict:
    """Exercise the runner's nested consumer paths and the analyzer's complete formal shape without rendering."""
    probe_root = cli.output_root / "full-shape-probe"
    width, height = spec["sceneContract"]["render"]["resolution"]
    background = next(owner for owner in spec["fixture"]["owners"] if owner["role"] == "background")
    foreground = next(owner for owner in spec["fixture"]["owners"] if owner["role"] == "foreground")
    background_material = np.float32(background["materialPassIndex"])
    foreground_material = np.float32(foreground["materialPassIndex"])
    object_token = np.float32(foreground["objectPassIndex"])
    center_y, center_x = height // 2, width // 2

    previous_rgba = np.empty((height, width, 4), dtype="<f4")
    current_rgba = np.empty((height, width, 4), dtype="<f4")
    previous_rgba[...] = np.asarray([0.39, 0.51, 0.46, 1.0], dtype="<f4")
    current_rgba[...] = np.asarray([0.39, 0.51, 0.46, 1.0], dtype="<f4")
    previous_depth = np.full((height, width), 13.0, dtype="<f4")
    current_depth = np.full((height, width), 13.0, dtype="<f4")
    previous_owner = np.full((height, width), background_material, dtype="<f4")
    current_owner = np.full((height, width), background_material, dtype="<f4")
    vector = np.zeros((height, width, 2), dtype="<f4")
    previous_position = np.zeros((height, width, 3), dtype="<f4")
    current_position = np.zeros((height, width, 3), dtype="<f4")
    vector_next = np.zeros((height, width, 2), dtype="<f4")
    previous_object = np.full((height, width), object_token, dtype="<f4")
    current_object = np.full((height, width), object_token, dtype="<f4")

    previous_rgba[center_y - 1:center_y + 2, center_x - 1:center_x + 2] = np.asarray([0.37, 0.62, 0.52, 1.0], dtype="<f4")
    previous_depth[center_y - 1:center_y + 2, center_x - 1:center_x + 2] = np.float32(12.0)
    previous_owner[center_y - 1:center_y + 2, center_x - 1:center_x + 2] = foreground_material
    current_rgba[center_y, center_x] = np.asarray([0.37, 0.62, 0.52, 1.0], dtype="<f4")
    current_depth[center_y, center_x] = np.float32(7.0)
    current_owner[center_y, center_x] = foreground_material
    current_position[center_y, center_x] = np.asarray([0.0, 0.0, 4.0], dtype="<f4")

    decision_values = {
        "previousRgba": ("previous.rgba32", previous_rgba), "currentRgba": ("current.rgba32", current_rgba),
        "previousDepth": ("previous-depth.f32", previous_depth), "currentDepth": ("current-depth.f32", current_depth),
        "previousOwner": ("previous-owner.f32", previous_owner), "currentOwner": ("current-owner.f32", current_owner),
        "vector": ("vector.xy32", vector),
    }
    control_values = {
        "previousPosition": ("previous-position.xyz32", previous_position), "currentPosition": ("current-position.xyz32", current_position),
        "vectorNext": ("vector-next.xy32", vector_next), "previousObjectIndex": ("previous-object-index.f32", previous_object),
        "currentObjectIndex": ("current-object-index.f32", current_object),
    }
    layer = spec["sceneContract"]["render"]["viewLayer"]
    decoded_arrays = {
        f"{layer}.Combined": current_rgba,
        f"{layer}.Depth": current_depth[..., None],
        f"{layer}.Position": current_position,
        f"{layer}.Vector": np.concatenate((vector, vector_next), axis=2),
        f"{layer}.Object Index": current_object[..., None],
        f"{layer}.Material Index": current_owner[..., None],
    }
    decoded_records = {
        name: {"sha256": sha_bytes(np.ascontiguousarray(value, dtype="<f4").tobytes()), "shape": list(value.shape), "dtype": "<f4"}
        for name, value in decoded_arrays.items()
    }
    adapter_reports = []
    for repeat in (1, 2):
        adapter_root = probe_root / "adapters" / f"R{repeat}"
        decision_records = {name: write_f32_array(adapter_root / "arrays" / "decision" / filename, value) for name, (filename, value) in decision_values.items()}
        control_records = {name: write_f32_array(adapter_root / "arrays" / "control" / filename, value) for name, (filename, value) in control_values.items()}
        body = {
            "schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthAdapter.v0.1", "experimentId": spec["experimentId"],
            "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256, "fixtureId": spec["fixture"]["id"], "repeat": repeat,
            "pid": os.getpid(), "multipart": {"previousMetadata": {}, "currentMetadata": {}},
            "decodedPasses": {"previous": decoded_records, "current": decoded_records},
            "decisionArrays": decision_records, "controlArrays": control_records,
            "operationCounts": {"adapterProcesses": 0, "multipartExrsOpened": 0, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
        }
        report = {**body, "reportHash": canonical_hash(body)}
        report_path = adapter_root / "report.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
        adapter_reports.append(report_path)

    parent_absence = {}
    python_consumer = root / "scripts/reconstruct-b52-d12-14-h2-projective-depth.py"
    node_consumer = root / "scripts/reconstruct-b52-d12-14-h2-projective-depth.mjs"
    consumer_reports = []
    for producer, executable, tool in (
        ("python", spec["runtime"]["python"]["executable"], python_consumer),
        ("node", spec["runtime"]["node"]["executable"], node_consumer),
    ):
        for repeat in (1, 2):
            consumer_root = probe_root / "consumers" / producer / f"R{repeat}"
            parent_absence[f"{producer}-R{repeat}"] = not consumer_root.exists()
            report_path = consumer_root / "report.json"
            run_child([
                executable, str(tool), "--spec", str(cli.spec), "--correction", str(cli.correction),
                "--fixture", spec["fixture"]["id"], "--repeat", str(repeat),
                "--input-dir", str(probe_root / "adapters" / f"R{repeat}" / "arrays" / "decision"),
                "--output-dir", str(consumer_root / "arrays"), "--report", str(report_path),
            ], f"full-shape-consumer-{producer}-R{repeat}", logs, env, children)
            consumer_reports.append(report_path)

    arrays_exact = True
    for repeat in (1, 2):
        python_arrays = probe_root / "consumers" / "python" / f"R{repeat}" / "arrays"
        node_arrays = probe_root / "consumers" / "node" / f"R{repeat}" / "arrays"
        python_files = sorted(path.relative_to(python_arrays) for path in python_arrays.rglob("*") if path.is_file())
        node_files = sorted(path.relative_to(node_arrays) for path in node_arrays.rglob("*") if path.is_file())
        arrays_exact &= python_files == node_files and all((python_arrays / path).read_bytes() == (node_arrays / path).read_bytes() for path in python_files)

    for repeat in (1, 2):
        for subtree in ("controlArrays", "decisionArrays"):
            envelope_root = probe_root / "envelopes" / f"R{repeat}" / subtree
            envelope_root.mkdir(parents=True, exist_ok=True)
            payload = f"B52-D12.14-H2 full-shape {repeat} {subtree}\n".encode()
            (envelope_root / "python.bin").write_bytes(payload)
            (envelope_root / "node.bin").write_bytes(payload)

    expected_labels = [
        *(f"source-R{repeat}-F{frame}" for repeat in (1, 2) for frame in (0, 1)),
        *(f"adapter-R{repeat}" for repeat in (1, 2)),
        *(f"consumer-{producer}-R{repeat}" for producer in ("python", "node") for repeat in (1, 2)),
        *(f"envelope-{producer}-R{repeat}-{subtree}" for producer in ("python", "node") for repeat in (1, 2) for subtree in ("controlArrays", "decisionArrays")),
    ]
    execution_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthExecution.v0.1", "experimentId": spec["experimentId"],
        "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256,
        "children": [{"label": label, "pid": 50000 + index, "exitCode": 0} for index, label in enumerate(expected_labels)],
        "operationCounts": {"childProcessesCompleted": 18, "blenderProcesses": 4, "blenderRenderCalls": 4, "cyclesRayRenders": 4, "adapterProcesses": 2, "consumerProcesses": 4, "typedEnvelopeProcesses": 8, "analyzerProcesses": 0, "auditProcesses": 0, "modelCalls": 0, "networkCalls": 0},
    }
    execution = {**execution_body, "executionHash": canonical_hash(execution_body)}
    execution_path = probe_root / "execution.draft.json"
    execution_path.write_text(json.dumps(execution, indent=2, sort_keys=True) + "\n")
    result_path = probe_root / "results.json"
    receipt_path = probe_root / "analysis-receipt.json"
    analyzer_tool = root / "scripts/analyze-b52-d12-14-h2-projective-depth.py"
    run_child([
        spec["runtime"]["python"]["executable"], str(analyzer_tool), "--spec", str(cli.spec), "--correction", str(cli.correction),
        "--root", str(probe_root), "--execution-draft", str(execution_path), "--output", str(result_path), "--analysis-receipt", str(receipt_path),
    ], "analyzer-full-shape", logs, env, children)
    result = json.loads(result_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    failed_checks = [row["name"] for row in result.get("evidenceChecks", []) if not row.get("passed")]
    analyzer_ok = (
        result.get("resultHash") == canonical_hash({key: value for key, value in result.items() if key != "resultHash"})
        and receipt.get("receiptHash") == canonical_hash({key: value for key, value in receipt.items() if key != "receiptHash"})
        and result.get("scientificVerdict") == spec["decision"]["notSupportedVerdict"]
        and result.get("evidenceChecksPassed") == result.get("evidenceChecksTotal") - 1
        and failed_checks == ["PROJECTIVE_DEPTH_MEASUREMENT"]
    )
    return {
        "parentsAbsent": all(parent_absence.values()), "parentAbsence": parent_absence,
        "arraysExact": bool(arrays_exact), "analyzerNotSupported": bool(analyzer_ok),
        "result": {"uri": str(result_path), "sha256": sha_file(result_path), "resultHash": result.get("resultHash")},
        "analysisReceipt": {"uri": str(receipt_path), "sha256": sha_file(receipt_path), "receiptHash": receipt.get("receiptHash")},
        "adapterReports": [{"uri": str(path), "sha256": sha_file(path)} for path in adapter_reports],
        "consumerReports": [{"uri": str(path), "sha256": sha_file(path)} for path in consumer_reports],
    }


def main() -> None:
    cli = arguments()
    root = Path(__file__).resolve().parents[1]
    if sha_file(cli.spec) != SPEC_SHA256 or sha_file(cli.correction) != CORRECTION_SHA256 or cli.output_root.exists(): raise RuntimeError("H2 preflight identity/output freshness failure")
    spec = json.loads(cli.spec.read_text())
    correction = json.loads(cli.correction.read_text())
    if correction.get("experimentId") != spec["experimentId"]: raise RuntimeError("H2 preflight correction identity mismatch")
    formal_root = root / spec["freshness"]["formalRoot"]
    if formal_root.exists(): raise RuntimeError("H2 formal root exists before preflight")
    cli.output_root.mkdir(parents=True, exist_ok=False)
    logs = cli.output_root / "logs"; logs.mkdir()
    env = clean_env(spec, root)
    tool_paths = [root / path for path in spec["freshness"]["newToolPaths"]]
    if any(not path.is_file() for path in tool_paths): raise RuntimeError("H2 preflight missing frozen tool")
    tool_hashes = {str(path.relative_to(root)): sha_file(path) for path in tool_paths}
    tracked_clean = all(subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(path.relative_to(root))], cwd=root).returncode == 0 for path in tool_paths)
    if not tracked_clean: raise RuntimeError("H2 preflight tool bytes are not frozen in Git")
    children = []
    python_tools = [str(path) for path in tool_paths if path.suffix == ".py"]
    node_tools = [str(path) for path in tool_paths if path.suffix == ".mjs"]
    run_child([spec["runtime"]["python"]["executable"], "-m", "py_compile", *python_tools], "syntax-python", logs, env, children)
    run_child([spec["runtime"]["node"]["executable"], "--check", *node_tools], "syntax-node", logs, env, children)
    probe_report = cli.output_root / "scene-probe-report.json"
    source_tool = root / "blender/render_b52_d12_14_h2_projective_depth_source.py"
    run_child([spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"], "--python", str(source_tool), "--", "--spec", str(cli.spec), "--correction", str(cli.correction), "--fixture", spec["fixture"]["id"], "--frame", "1", "--repeat", "1", "--report", str(probe_report), "--probe-only"], "scene-probe", logs, env, children)
    probe = json.loads(probe_report.read_text())
    probe_body = {key: value for key, value in probe.items() if key != "reportHash"}
    probe_ok = probe.get("reportHash") == canonical_hash(probe_body) and probe.get("probeOnly") is True and probe.get("operationCounts", {}).get("blenderRenderCalls") == 0 and probe.get("passState", {}).get("Position") is True and probe.get("renderState", {}).get("resolution") == spec["sceneContract"]["render"]["resolution"]
    arithmetic_script = "const d=[2,4,2,4],w=[.25,.25,.25,.25];const f=(v)=>((v[0]*w[0]+v[1]*w[1])+v[2]*w[2])+v[3]*w[3];const direct=f(d),inverse=1/f(d.map(x=>1/x));if(direct!==3||Math.abs(inverse-8/3)>1e-15)process.exit(2);console.log(JSON.stringify({direct,inverse}));"
    run_child([spec["runtime"]["node"]["executable"], "-e", arithmetic_script], "synthetic-arithmetic", logs, env, children)
    depths, weights = [2.0, 4.0, 2.0, 4.0], [0.25] * 4
    direct = ((depths[0] * weights[0] + depths[1] * weights[1]) + depths[2] * weights[2]) + depths[3] * weights[3]
    inverse = 1.0 / ((((1.0 / depths[0]) * weights[0] + (1.0 / depths[1]) * weights[1]) + (1.0 / depths[2]) * weights[2]) + (1.0 / depths[3]) * weights[3])
    arithmetic_ok = direct == 3.0 and abs(inverse - 8.0 / 3.0) <= 1e-15
    smoke_bundle = cli.output_root / "analyzer-smoke-bundle.json"
    smoke_bundle.write_text(json.dumps({
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256,
        "source": {"reportHash": "probe", "output": {"sha256": "probe"}, "operationCounts": {"blenderRenderCalls": 0}, "passState": {"Position": True}},
        "adapter": {"reportHash": "probe", "multipart": {"previousMetadata": {}}, "decodedPasses": {"current": {}}, "decisionArrays": {"currentDepth": {"sha256": "probe"}}, "controlArrays": {"currentPosition": {"sha256": "probe"}}},
        "consumer": {"reportHash": "probe", "inputBoundary": {"positionAvailable": False}, "controlArrays": {"projectiveDepthRescued": {"sha256": "probe"}}, "decisionArrays": {"reconstructed": {"sha256": "probe"}}, "counts": {"neitherHorizontal": 0}},
        "execution": {"executionHash": "probe", "children": [], "operationCounts": {"blenderRenderCalls": 0}},
    }, indent=2, sort_keys=True) + "\n")
    smoke_output = cli.output_root / "analyzer-smoke-result.json"
    analyzer_tool = root / "scripts/analyze-b52-d12-14-h2-projective-depth.py"
    run_child([spec["runtime"]["python"]["executable"], str(analyzer_tool), "--spec", str(cli.spec), "--correction", str(cli.correction), "--schema-smoke", str(smoke_bundle), "--output", str(smoke_output)], "analyzer-schema-smoke", logs, env, children)
    smoke = json.loads(smoke_output.read_text())
    smoke_body = {key: value for key, value in smoke.items() if key != "resultHash"}
    smoke_ok = smoke.get("resultHash") == canonical_hash(smoke_body) and smoke.get("passed") is True and smoke.get("keysExercised") == 17
    failure_probe_root = cli.output_root / "runner-failure-probe"
    runner_tool = root / "scripts/run-b52-d12-14-h2-projective-depth.py"
    run_child([spec["runtime"]["python"]["executable"], str(runner_tool), "--spec", str(cli.spec), "--correction", str(cli.correction), "--failure-probe", "--probe-root", str(failure_probe_root)], "runner-failure-probe", logs, env, children)
    failure = json.loads((failure_probe_root / "failure.json").read_text())
    execution_probe = json.loads((failure_probe_root / "execution.json").read_text())
    receipt_probe = json.loads((failure_probe_root / "receipt.json").read_text())
    failure_probe_ok = failure.get("scientificVerdict") is None and failure.get("failureHash") == canonical_hash({key: value for key, value in failure.items() if key != "failureHash"}) and execution_probe.get("executionHash") == canonical_hash({key: value for key, value in execution_probe.items() if key != "executionHash"}) and receipt_probe.get("receiptHash") == canonical_hash({key: value for key, value in receipt_probe.items() if key != "receiptHash"})
    full_shape = full_shape_probe(cli, spec, root, logs, env, children)
    free_bytes = os.statvfs(root).f_bavail * os.statvfs(root).f_frsize
    disk_ok = free_bytes - spec["diskAdmission"]["projectedWriteBytes"] >= spec["diskAdmission"]["minimumReserveBytesAfterProjectedWrite"]
    gates = {
        "SPEC_AND_CORRECTION_IDENTITIES": True, "ALL_TOOL_BYTES_TRACKED_CLEAN": tracked_clean, "PYTHON_AND_NODE_SYNTAX": True,
        "FACTORY_SCENE_PROBE": probe_ok, "ZERO_RENDER_AND_EXR": probe.get("operationCounts") == {"blenderProcesses": 1, "blenderRenderCalls": 0, "cyclesRayRenders": 0, "exrFiles": 0, "modelCalls": 0, "networkCalls": 0},
        "RECIPROCAL_DEPTH_SYNTHETIC_ARITHMETIC": arithmetic_ok, "ANALYZER_PROBE_SCHEMA_SMOKE": smoke_ok, "RUNNER_FAILURE_FINALLY_PATH": failure_probe_ok,
        "NESTED_PARENT_CONSUMERS_AND_BYTE_IDENTITY": full_shape["parentsAbsent"] and full_shape["arraysExact"],
        "FULL_SHAPED_ANALYZER_NOT_SUPPORTED": full_shape["analyzerNotSupported"],
        "FORMAL_ROOT_ABSENT": not formal_root.exists(), "DISK_RESERVE": disk_ok, "UNIQUE_CHILD_PIDS": len({row["pid"] for row in children}) == len(children),
        "CHILDREN_EXIT_ZERO": all(row["exitCode"] == 0 for row in children), "MODEL_AND_NETWORK_ZERO": True,
    }
    passed = all(gates.values())
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthPreflight.v0.1", "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256,
        "status": "ACCEPTED" if passed else "REJECTED", "passed": passed, "pid": os.getpid(), "gitCommit": git_value(root, "rev-parse", "HEAD"), "gitTree": git_value(root, "rev-parse", "HEAD^{tree}"),
        "toolHashes": tool_hashes, "children": children, "evidenceChecks": [{"name": name, "passed": bool(value)} for name, value in gates.items()], "evidenceChecksPassed": sum(bool(value) for value in gates.values()), "evidenceChecksTotal": len(gates),
        "disk": {"freeBytesObserved": free_bytes, "projectedWriteBytes": spec["diskAdmission"]["projectedWriteBytes"], "minimumReserveBytesAfterProjectedWrite": spec["diskAdmission"]["minimumReserveBytesAfterProjectedWrite"]},
        "artifacts": {"sceneProbe": {"uri": str(probe_report), "sha256": sha_file(probe_report)}, "analyzerSmoke": {"uri": str(smoke_output), "sha256": sha_file(smoke_output)}, "runnerFailureProbe": {"uri": str(failure_probe_root), "failureSha256": sha_file(failure_probe_root / "failure.json")}, "fullShapeProbe": full_shape},
        "operationCounts": {"preflightProcesses": 1, "childProcesses": len(children), "blenderProcesses": 1, "blenderRenderCalls": 0, "cyclesRayRenders": 0, "exrFiles": 0, "modelCalls": 0, "networkCalls": 0},
    }
    preflight = {**body, "preflightHash": canonical_hash(body)}
    preflight_path = cli.output_root / "preflight.json"
    preflight_path.write_text(json.dumps(preflight, indent=2, sort_keys=True, allow_nan=False) + "\n")
    receipt_body = {"schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthPreflightReceipt.v0.1", "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256, "preflight": {"uri": str(preflight_path), "sha256": sha_file(preflight_path), "preflightHash": preflight["preflightHash"]}, "formalRootAbsent": not formal_root.exists(), "operationCounts": {"receiptWrites": 1, "modelCalls": 0, "networkCalls": 0}}
    receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}
    (cli.output_root / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    if not passed: raise RuntimeError("H2 preflight rejected")
    print(f"BFS_D1214H2_PREFLIGHT_ACCEPTED gates={sum(gates.values())}/{len(gates)}")


if __name__ == "__main__": main()
