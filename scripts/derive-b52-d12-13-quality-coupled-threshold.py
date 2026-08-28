#!/usr/bin/env python3
"""Independent Python threshold consumer for B52-D12.13-D1."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

import numpy as np


SPEC_SHA256 = "e9d79a2ec54acaf36a0df1168ea71102b0b94ab66f4e10f1cda56dbd1ea70c00"
PARENT_SPEC_SHA256 = "b0defadbd120f77dfe81bfa16d9dfd4e3a4d4a15ad1c8ddd1176d21f2e13b648"
PARENT_SUBTREE = "de1ac6a394a3963a158d0e3432d5dfb89aaf9a87"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--parent-root", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def verify_record(record: dict, label: str) -> bytes:
    path = Path(record["uri"])
    payload = path.read_bytes()
    if sha_bytes(payload) != record["sha256"] or len(payload) != record["bytes"]:
        raise RuntimeError(f"D12.13-D1 input binding failed: {label}")
    return payload


def array_record(path: Path, payload: bytes, dtype: str, shape: list[int]) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "uri": path.as_posix(),
        "sha256": sha_bytes(payload),
        "bytes": len(payload),
        "dtype": dtype,
        "shape": shape,
    }


def normalized_parent_report(report: dict) -> dict:
    return {key: value for key, value in report.items() if key not in {"pid", "reportHash", "runtime"}}


def main():
    cli = arguments()
    if cli.output.exists():
        raise RuntimeError("D12.13-D1 Python output must not pre-exist")
    if sha_file(cli.spec) != SPEC_SHA256:
        raise RuntimeError("D12.13-D1 spec identity failed")
    spec = json.loads(cli.spec.read_text())
    if cli.fixture not in spec["inputContract"]["fixtures"]:
        raise RuntimeError("D12.13-D1 fixture outside frozen roster")

    parent_spec = Path(spec["parents"]["h1Spec"]["uri"])
    if sha_file(parent_spec) != PARENT_SPEC_SHA256:
        raise RuntimeError("D12.13-D1 H1 spec identity failed")
    for row in (spec["parents"]["h1Result"], spec["parents"]["h1Audit"], spec["parents"]["h1Receipt"]):
        if sha_file(Path(row["uri"])) != row["sha256"]:
            raise RuntimeError("D12.13-D1 H1 evidence identity failed")
    subtree = subprocess.run(
        ["git", "rev-parse", f"HEAD:{spec['parents']['h1FormalRoot']['uri']}"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    if subtree != PARENT_SUBTREE:
        raise RuntimeError("D12.13-D1 H1 formal subtree changed")

    h1_spec = json.loads(parent_spec.read_text())
    fixture = next(row for row in h1_spec["fixtures"] if row["id"] == cli.fixture)
    width, height = fixture["resolution"]
    pixels = width * height
    repeat_label = f"R{cli.repeat}"
    adapter_path = cli.parent_root / "adapters" / cli.fixture / repeat_label / "report.json"
    h1_path = cli.parent_root / "consumers" / "python" / cli.fixture / repeat_label / "report.json"
    adapter = json.loads(adapter_path.read_text())
    h1 = json.loads(h1_path.read_text())
    if canonical_hash({key: value for key, value in adapter.items() if key != "reportHash"}) != adapter["reportHash"]:
        raise RuntimeError("D12.13-D1 adapter report self-hash failed")
    if canonical_hash({key: value for key, value in h1.items() if key != "reportHash"}) != h1["reportHash"]:
        raise RuntimeError("D12.13-D1 H1 report self-hash failed")

    adapter_keys = {"currentRgba": "current.rgba32", "currentOwner": "current-owner.f32"}
    control_keys = {
        "radius2Interior": "radius2-interior.u8", "fullStencil": "full-stencil.u8",
        "directionLeft": "direction-left.u8", "directionRight": "direction-right.u8",
        "directionTop": "direction-top.u8", "directionBottom": "direction-bottom.u8",
        "neitherHorizontal": "neither-horizontal.u8", "analyticValidHistory": "analytic-valid-history.u8",
    }
    decision_keys = {
        "oneSidedEligible": "one-sided-eligible.u8", "riskQ30": "risk.q30.u32",
        "reconstructed": "reconstructed.rgba32",
    }
    payloads: dict[str, bytes] = {}
    input_bindings: dict[str, dict] = {}
    for key, label in adapter_keys.items():
        record = adapter["arrays"][key]
        payloads[label] = verify_record(record, label)
        input_bindings[label] = {"uri": record["uri"], "sha256": record["sha256"]}
    for section, mapping in (("controlArrays", control_keys), ("decisionArrays", decision_keys)):
        for key, label in mapping.items():
            record = h1[section][key]
            payloads[label] = verify_record(record, label)
            input_bindings[label] = {"uri": record["uri"], "sha256": record["sha256"]}

    expected_lengths = {
        "current.rgba32": pixels * 16, "current-owner.f32": pixels * 4,
        "risk.q30.u32": pixels * 12, "reconstructed.rgba32": pixels * 16,
    }
    expected_lengths.update({label: pixels for label in control_keys.values()})
    expected_lengths["one-sided-eligible.u8"] = pixels
    for label, expected in expected_lengths.items():
        if len(payloads[label]) != expected:
            raise RuntimeError(f"D12.13-D1 array length failed: {label}")

    eligible = np.frombuffer(payloads["one-sided-eligible.u8"], dtype="u1").astype(bool)
    risk = np.frombuffer(payloads["risk.q30.u32"], dtype="<u4").reshape(pixels, 3)
    current_bytes = payloads["current.rgba32"]
    h1_reconstructed = payloads["reconstructed.rgba32"]
    root = cli.output
    root.mkdir(parents=True)
    shared = {
        "eligible": array_record(root / "shared" / "eligible.u8", payloads["one-sided-eligible.u8"], "u1", [height, width]),
        "riskQ30": array_record(root / "shared" / "risk.q30.u32", payloads["risk.q30.u32"], "<u4", [height, width, 3]),
    }
    thresholds: dict[str, dict] = {}
    for threshold in spec["thresholdFamily"]["candidateThresholdsQ30Descending"]:
        accepted = np.logical_and(eligible, np.all(risk <= np.uint32(threshold), axis=1))
        accepted_payload = accepted.astype("u1").tobytes()
        reconstructed_payload = bytearray(current_bytes)
        for index in np.flatnonzero(accepted):
            start = int(index) * 16
            reconstructed_payload[start:start + 16] = h1_reconstructed[start:start + 16]
        base = root / f"threshold-{threshold}"
        thresholds[str(threshold)] = {
            "accepted": array_record(base / "accepted.u8", accepted_payload, "u1", [height, width]),
            "reconstructed": array_record(base / "reconstructed.rgba32", bytes(reconstructed_payload), "<f4", [height, width, 4]),
            "acceptedCount": int(accepted.sum()),
        }

    report = {
        "schemaVersion": "bfs.blenderMaterialOwnerQualityCouplingConsumerReport.v0.1",
        "experimentId": spec["experimentId"],
        "specSha256": SPEC_SHA256,
        "producer": "python",
        "fixtureId": cli.fixture,
        "repeat": cli.repeat,
        "resolution": [width, height],
        "thresholdsQ30Descending": spec["thresholdFamily"]["candidateThresholdsQ30Descending"],
        "parentReports": {
            "adapter": {"uri": adapter_path.as_posix(), "sha256": sha_file(adapter_path), "normalizedHash": canonical_hash(normalized_parent_report(adapter))},
            "h1Consumer": {"uri": h1_path.as_posix(), "sha256": sha_file(h1_path), "normalizedHash": canonical_hash(normalized_parent_report(h1))},
        },
        "inputBindings": input_bindings,
        "sharedArrays": shared,
        "thresholdArrays": thresholds,
        "operationCounts": {
            "consumerProcesses": 1, "pixelsVisited": pixels, "thresholdsEvaluated": len(thresholds),
            "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0,
        },
        "runtime": {
            "python": platform.python_version(), "numpy": np.__version__,
            "pythonExecutableSha256": sha_file(Path(os.path.realpath(os.sys.executable))),
        },
        "pid": os.getpid(),
    }
    report["reportHash"] = canonical_hash(report)
    (root / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
