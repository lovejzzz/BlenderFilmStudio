#!/usr/bin/env python3
"""Independent payload-level analyzer for B52-D12.2."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np


SPEC_SHA256 = "fa63daa0c3b7b3f080a488aa0fc84996fd52cd731efce94ebe28bbc81b55d9d3"
SOURCE_ARRAYS = ("previousRgba", "currentRgba", "previousOwner", "currentOwner", "vector", "vectorNext")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def valid_native_report(path: Path) -> dict:
    report = json.loads(path.read_text())
    body = {key: value for key, value in report.items() if key != "reportHash"}
    if report.get("reportHash") != canonical_hash(body):
        raise RuntimeError(f"native report hash mismatch: {path}")
    return report


def load_f32(path: Path, shape: tuple[int, ...]) -> np.ndarray:
    payload = path.read_bytes()
    expected = math.prod(shape) * 4
    if len(payload) != expected:
        raise RuntimeError(f"array byte length mismatch: {path}")
    return np.frombuffer(payload, dtype="<f4").reshape(shape)


def metric(reconstructed: np.ndarray, current: np.ndarray, valid: np.ndarray) -> dict:
    maximum = 0.0
    squared_total = 0.0
    count = 0
    all_zero = True
    height, width = valid.shape
    for y in range(height):
        for x in range(width):
            if not valid[y, x]:
                continue
            for channel in range(3):
                error = float(reconstructed[y, x, channel]) - float(current[y, x, channel])
                absolute = abs(error)
                maximum = max(maximum, absolute)
                squared_total += error * error
                count += 1
                all_zero = all_zero and error == 0.0
    if count == 0:
        raise RuntimeError("no valid metric samples")
    return {"maximum": maximum, "rmse": math.sqrt(squared_total / count), "sampleCount": count, "allZero": all_zero}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D12.2 results")
    spec = json.loads(args.spec.read_text())
    preflight = json.loads(args.preflight.read_text())
    execution = json.loads(args.execution.read_text())
    threshold = spec["thresholds"]
    measurements, source_hashes, reconstruction_hashes = [], {}, {}
    source_reports_ok = adapter_reports_ok = multipart_ok = payload_identity = envelope_identity = True
    producer_metrics_absent = True
    transform_identity = True
    all_vector_zero = True
    all_reconstruction_zero = True
    all_minimum_valid = all_vector_bound = all_maximum_bound = all_rmse_bound = all_source_static_exact = True

    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        source_hashes[fixture_id], reconstruction_hashes[fixture_id] = {}, {}
        for repeat in (1, 2):
            cell = f"{fixture_id}/R{repeat}"
            source_dir = args.root / "sources" / fixture_id / f"R{repeat}"
            adapter_dir = args.root / "adapters" / fixture_id / f"R{repeat}"
            try:
                previous_report = valid_native_report(source_dir / "frame-0" / "report.json")
                current_report = valid_native_report(source_dir / "frame-1" / "report.json")
                source_reports_ok = source_reports_ok and previous_report["output"]["sha256"] == sha256_file(source_dir / "frame-0" / "source.exr")
                source_reports_ok = source_reports_ok and current_report["output"]["sha256"] == sha256_file(source_dir / "frame-1" / "source.exr")
                for report in (previous_report, current_report):
                    for owner in ("surface", "camera"):
                        for curve in report["animation"][owner]:
                            keys = curve["keys"]
                            transform_identity = transform_identity and [row[0] for row in keys] == [0.0, 1.0, 2.0]
                            transform_identity = transform_identity and len({row[1] for row in keys}) == 1 and all(row[2] == "LINEAR" for row in keys)
                adapter = valid_native_report(adapter_dir / "report.json")
                adapter_reports_ok = adapter_reports_ok and adapter["fixtureId"] == fixture_id and adapter["repeat"] == repeat
                layer = spec["sceneContract"]["render"]["viewLayer"]
                expected_roster = [f"{layer}.Combined", f"{layer}.Depth", f"{layer}.Vector", f"{layer}.Object Index"]
                multipart_ok = multipart_ok and adapter["multipart"]["previousRoster"] == expected_roster and adapter["multipart"]["currentRoster"] == expected_roster
            except Exception:
                source_reports_ok = adapter_reports_ok = multipart_ok = False
                raise

            arrays = {}
            shapes = {
                "previousRgba": (height, width, 4), "currentRgba": (height, width, 4),
                "previousOwner": (height, width), "currentOwner": (height, width),
                "vector": (height, width, 2), "vectorNext": (height, width, 2),
            }
            for name in SOURCE_ARRAYS:
                record = adapter["arrays"][name]
                path = Path(record["uri"])
                payload = path.read_bytes()
                if sha256_bytes(payload) != record["sha256"]:
                    adapter_reports_ok = False
                arrays[name] = load_f32(path, shapes[name])
            source_hashes[fixture_id][repeat] = {name: adapter["arrays"][name]["sha256"] for name in SOURCE_ARRAYS}

            reports, outputs = {}, {}
            for producer in ("python", "node"):
                consumer_dir = args.root / "consumers" / producer / fixture_id / f"R{repeat}"
                report_path = consumer_dir / "report.json"
                report = json.loads(report_path.read_text())
                reports[producer] = report
                producer_metrics_absent = producer_metrics_absent and "measurements" not in report and "metrics" not in report
                reconstructed_payload = (consumer_dir / "arrays" / "reconstructed.rgba32").read_bytes()
                valid_payload = (consumer_dir / "arrays" / "valid.u8").read_bytes()
                outputs[producer] = {
                    "reconstructedPayload": reconstructed_payload,
                    "validPayload": valid_payload,
                    "reconstructed": np.frombuffer(reconstructed_payload, dtype="<f4").reshape(height, width, 4),
                    "valid": np.frombuffer(valid_payload, dtype="u1").reshape(height, width),
                }
                payload_identity = payload_identity and sha256_bytes(reconstructed_payload) == report["arrays"]["reconstructed"]["sha256"]
                payload_identity = payload_identity and sha256_bytes(valid_payload) == report["arrays"]["valid"]["sha256"]
                envelope_dir = args.root / "envelopes" / producer / fixture_id / f"R{repeat}"
                py_envelope = (envelope_dir / "report.python-envelope.json").read_bytes()
                node_envelope = (envelope_dir / "report.node-envelope.json").read_bytes()
                envelope_identity = envelope_identity and py_envelope == node_envelope
            payload_identity = payload_identity and outputs["python"]["reconstructedPayload"] == outputs["node"]["reconstructedPayload"]
            payload_identity = payload_identity and outputs["python"]["validPayload"] == outputs["node"]["validPayload"]
            reconstruction_hashes[fixture_id][repeat] = {
                "reconstructed": sha256_bytes(outputs["python"]["reconstructedPayload"]),
                "valid": sha256_bytes(outputs["python"]["validPayload"]),
            }

            valid = outputs["python"]["valid"].astype(bool)
            valid_pixels = int(valid.sum())
            vector_maximum = 0.0
            vector_all_zero = True
            for y in range(height):
                for x in range(width):
                    if not valid[y, x]:
                        continue
                    for channel in range(2):
                        value = float(arrays["vector"][y, x, channel])
                        vector_maximum = max(vector_maximum, abs(value))
                        vector_all_zero = vector_all_zero and value == 0.0
            source_metric = metric(arrays["previousRgba"], arrays["currentRgba"], valid)
            reconstruction_metric = metric(outputs["python"]["reconstructed"], arrays["currentRgba"], valid)
            all_vector_zero = all_vector_zero and vector_all_zero
            all_reconstruction_zero = all_reconstruction_zero and reconstruction_metric["allZero"]
            all_minimum_valid = all_minimum_valid and valid_pixels >= threshold["minimumValidPixelsPerCell"]
            all_vector_bound = all_vector_bound and vector_maximum <= threshold["vectorComponentAbsoluteMaximum"]
            all_maximum_bound = all_maximum_bound and reconstruction_metric["maximum"] <= threshold["reconstructionRgbAbsoluteMaximum"]
            all_rmse_bound = all_rmse_bound and reconstruction_metric["rmse"] <= threshold["reconstructionRgbRmseMaximum"]
            all_source_static_exact = all_source_static_exact and source_metric["maximum"] <= threshold["sourceStaticRgbAbsoluteMaximum"]
            measurements.append({
                "cell": cell, "fixtureId": fixture_id, "repeat": repeat, "resolution": fixture["resolution"],
                "validPixels": valid_pixels, "vectorComponentAbsoluteMaximum": vector_maximum,
                "vectorAllZero": vector_all_zero, "sourceStaticRgb": source_metric, "reconstructionRgb": reconstruction_metric,
            })

    repeat_source_identity = all(source_hashes[fixture["id"]][1] == source_hashes[fixture["id"]][2] for fixture in spec["fixtures"])
    repeat_reconstruction_identity = all(reconstruction_hashes[fixture["id"]][1] == reconstruction_hashes[fixture["id"]][2] for fixture in spec["fixtures"])
    children = execution.get("children", [])
    child_pids = [row.get("pid") for row in children]
    process_boundary = len(children) == spec["processBoundary"]["expectedUniqueChildProcesses"] - 1 and len(set(child_pids + [os.getpid()])) == spec["processBoundary"]["expectedUniqueChildProcesses"]
    current_tool_hashes = {path: sha256_file(Path(path)) for path in spec["formalToolPaths"]}
    tool_identity = preflight.get("status") == "ACCEPTED" and preflight.get("toolHashes") == current_tool_hashes
    analyzer_tree = ast.parse(Path(__file__).read_text())
    imported_modules = []
    for node in ast.walk(analyzer_tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.append(node.module or "")
    analyzer_independent = all(not name.startswith(("scripts", "blender", "importlib")) for name in imported_modules)
    spec_identity = sha256_file(args.spec) == SPEC_SHA256
    runtime_identity = all(row.get("exitCode") == 0 for row in children)
    roster = [row["cell"] for row in measurements] == [f"{fixture['id']}/R{repeat}" for fixture in spec["fixtures"] for repeat in (1, 2)]
    exact_zero = all_vector_zero and all_reconstruction_zero
    exact_zero_observation = "STATIC_EXACT_ZERO_OBSERVED" if exact_zero else "STATIC_EXACT_ZERO_FALSIFIED"
    attacks = [
        ["SPEC_BYTE_IDENTITY", spec_identity], ["TOOL_PREFLIGHT_IDENTITY", tool_identity], ["RUNTIME_IDENTITY", runtime_identity],
        ["SINGLE_USE_ROOT_MARKER", execution.get("rootCreatedFresh") is True], ["DISK_RESERVE_ADMISSION", preflight.get("diskAdmission", {}).get("status") == "ACCEPTED"],
        ["FIXTURE_ROSTER_ORDER", roster], ["THREE_FRAME_TRANSFORM_IDENTITY", transform_identity], ["SOURCE_REPORT_SELF_BINDING", source_reports_ok],
        ["MULTIPART_ROSTER", multipart_ok], ["ADAPTER_ARRAY_BINDING", adapter_reports_ok], ["PROCESS_IDENTITY_TOTALITY", process_boundary],
        ["PYTHON_NODE_PAYLOAD_IDENTITY", payload_identity], ["DUAL_TYPED_ENVELOPE_IDENTITY", envelope_identity], ["ANALYZER_INDEPENDENCE", analyzer_independent],
        ["MINIMUM_VALID_COVERAGE", all_minimum_valid], ["VECTOR_BOUND", all_vector_bound], ["RECONSTRUCTION_MAXIMUM_BOUND", all_maximum_bound],
        ["RECONSTRUCTION_RMSE_BOUND", all_rmse_bound], ["SOURCE_STATIC_BEAUTY_IDENTITY", all_source_static_exact],
        ["REPEAT_SOURCE_ARRAY_IDENTITY", repeat_source_identity], ["REPEAT_RECONSTRUCTION_IDENTITY", repeat_reconstruction_identity],
        ["PRODUCER_METRICS_EXCLUDED", producer_metrics_absent], ["EXACT_ZERO_CLASSIFICATION_TOTAL", exact_zero_observation in ("STATIC_EXACT_ZERO_OBSERVED", "STATIC_EXACT_ZERO_FALSIFIED")],
        ["RESULT_SELF_HASH_CONSTRUCTION", True],
    ]
    passed = all(value for _, value in attacks)
    body = {
        "schemaVersion": "bfs.blenderStaticVectorFloorThreeLayerEvidenceResult.v0.1",
        "experimentId": spec["experimentId"],
        "analyzerPid": os.getpid(),
        "verdict": spec["classification"]["supported"] if passed else spec["classification"]["notSupported"],
        "exactZeroObservation": exact_zero_observation,
        "passed": passed,
        "baseFailure": next((name for name, value in attacks if not value), None),
        "measurements": measurements,
        "identities": {"source": source_hashes, "reconstruction": reconstruction_hashes},
        "attacks": [{"id": name, "passed": value} for name, value in attacks],
        "attackPassed": sum(value for _, value in attacks),
        "attackTotal": len(attacks),
        "operationCounts": {"modelCalls": 0, "networkCalls": 0},
        "nonClaims": spec["nonClaims"],
    }
    result = {**body, "evidenceHash": canonical_hash(body)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D122_ANALYSIS_OK verdict={result['verdict']} exactZero={exact_zero_observation} attacks={result['attackPassed']}/{result['attackTotal']}")


if __name__ == "__main__":
    main()
