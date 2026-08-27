#!/usr/bin/env python3
"""Independent replay and mutation audit for B52-D12.4 localization."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np


SPEC_SHA256 = "8df3c666e4409a243b1611131e5927b757fcd47453511b732fc26e579f526326"
REGISTERED = (
    "D12_3_SPEC_IDENTITY",
    "D12_3_RESULTS_FILE_IDENTITY",
    "D12_3_RESULTS_INTERNAL_IDENTITY",
    "D12_3_RECEIPT_FILE_IDENTITY",
    "D12_3_RECEIPT_INTERNAL_IDENTITY",
    "D12_3_EXECUTION_FILE_IDENTITY",
    "D12_3_EXECUTION_INTERNAL_IDENTITY",
    "ADAPTER_REPORT_IDENTITY",
    "CONSUMER_REPORT_IDENTITY",
    "PAYLOAD_IDENTITY",
    "REPEAT_PAYLOAD_IDENTITY",
    "RECONSTRUCTION_BYTE_IDENTITY",
    "GLOBAL_MAXIMUM_IDENTITY",
    "TIED_COORDINATE_TOTALITY",
    "OUTPUT_SELF_HASH",
)


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


def self_hash(document: dict, field: str) -> str:
    return canonical_hash({key: value for key, value in document.items() if key != field})


def read_f32(path: Path, shape: tuple[int, ...]) -> np.ndarray:
    payload = path.read_bytes()
    if len(payload) != math.prod(shape) * 4:
        raise RuntimeError(f"array length mismatch: {path}")
    return np.frombuffer(payload, dtype="<f4").reshape(shape).copy()


def actual_state(spec: dict, root: Path, result: dict) -> dict:
    d12_spec_path = Path(spec["frozenInputs"]["d12_3Spec"]["uri"])
    d12_spec = json.loads(d12_spec_path.read_text())
    top = {}
    for name, field in (("formalResults", "evidenceHash"), ("formalReceipt", "receiptHash"), ("formalExecution", "executionHash")):
        frozen = spec["frozenInputs"][name]
        path = Path(frozen["uri"])
        document = json.loads(path.read_text())
        top[name] = {"sha256": sha256_file(path), "internalHash": document.get(field), "selfHash": self_hash(document, field)}
    fixtures = {}
    all_errors = []
    for fixture in d12_spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        identities = {"adapterReports": {}, "consumerReports": {}, "arrays": {}}
        payloads = {}
        primary = {}
        for repeat in (1, 2):
            adapter_dir = root / "adapters" / fixture_id / f"R{repeat}"
            consumer_dir = root / "consumers" / "python" / fixture_id / f"R{repeat}"
            adapter_path = adapter_dir / "report.json"
            consumer_path = consumer_dir / "report.json"
            adapter = json.loads(adapter_path.read_text())
            identities["adapterReports"][str(repeat)] = {"sha256": sha256_file(adapter_path), "reportHash": adapter.get("reportHash"), "selfHash": self_hash(adapter, "reportHash")}
            identities["consumerReports"][str(repeat)] = {"sha256": sha256_file(consumer_path)}
            cell_payloads = {}
            for key, filename in (("adapter.previousRgba", "previous.rgba32"), ("adapter.currentRgba", "current.rgba32"), ("adapter.previousOwner", "previous-owner.f32"), ("adapter.currentOwner", "current-owner.f32"), ("adapter.vector", "vector.xy32"), ("adapter.vectorNext", "vector-next.xy32")):
                cell_payloads[key] = (adapter_dir / "arrays" / filename).read_bytes()
            for key, filename in (("consumer.reconstructed", "reconstructed.rgba32"), ("consumer.valid", "valid.u8"), ("consumer.boundary", "boundary.u8")):
                cell_payloads[key] = (consumer_dir / "arrays" / filename).read_bytes()
            identities["arrays"][str(repeat)] = {key: sha256_bytes(value) for key, value in cell_payloads.items()}
            payloads[repeat] = cell_payloads
            if repeat == 1:
                primary = {
                    "previous": read_f32(adapter_dir / "arrays" / "previous.rgba32", (height, width, 4)),
                    "current": read_f32(adapter_dir / "arrays" / "current.rgba32", (height, width, 4)),
                    "vector": read_f32(adapter_dir / "arrays" / "vector.xy32", (height, width, 2)),
                    "reconstructed": read_f32(consumer_dir / "arrays" / "reconstructed.rgba32", (height, width, 4)),
                    "valid": np.frombuffer(cell_payloads["consumer.valid"], dtype="u1").reshape(height, width).copy(),
                }
        replay = primary["current"].copy()
        errors = []
        for y in range(height):
            for x in range(width):
                if not primary["valid"][y, x]:
                    continue
                qx = x + float(primary["vector"][y, x, 0])
                qy = y - float(primary["vector"][y, x, 1])
                x0, y0 = math.floor(qx), math.floor(qy)
                fx, fy = qx - x0, qy - y0
                weights = ((1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy)
                for channel in range(4):
                    values = (float(primary["previous"][y0, x0, channel]), float(primary["previous"][y0, x0 + 1, channel]), float(primary["previous"][y0 + 1, x0, channel]), float(primary["previous"][y0 + 1, x0 + 1, channel]))
                    replay[y, x, channel] = np.float32((((values[0] * weights[0]) + (values[1] * weights[1])) + (values[2] * weights[2])) + (values[3] * weights[3]))
                for channel, label in enumerate(("R", "G", "B")):
                    absolute = abs(float(primary["reconstructed"][y, x, channel]) - float(primary["current"][y, x, channel]))
                    errors.append((absolute, y, x, label))
                    all_errors.append((absolute, fixture_id, y, x, label))
        errors.sort(key=lambda row: (-row[0], row[1], row[2], row[3]))
        maximum = errors[0][0]
        fixtures[fixture_id] = {
            "identities": identities,
            "repeatPayloadExact": payloads[1] == payloads[2],
            "reconstructionByteExact": np.ascontiguousarray(replay, dtype="<f4").tobytes() == payloads[1]["consumer.reconstructed"],
            "maximum": maximum,
            "ties": [{"fixtureId": fixture_id, "x": x, "y": y, "channel": label} for absolute, y, x, label in errors if absolute == maximum],
        }
    all_errors.sort(key=lambda row: (-row[0], row[1], row[2], row[3], row[4]))
    maximum = all_errors[0][0]
    return {
        "d12SpecSha256": sha256_file(d12_spec_path),
        "top": top,
        "fixtures": fixtures,
        "globalMaximum": maximum,
        "globalTies": [{"fixtureId": fixture_id, "x": x, "y": y, "channel": label} for absolute, fixture_id, y, x, label in all_errors if absolute == maximum],
    }


def verify(candidate: dict, spec: dict, actual: dict) -> dict[str, bool]:
    reported_fixtures = {row["fixtureId"]: row for row in candidate.get("fixtures", [])}
    adapter_ok = consumer_ok = payload_ok = repeat_ok = reconstruction_ok = True
    for fixture_id, state in actual["fixtures"].items():
        row = reported_fixtures.get(fixture_id, {})
        identity = row.get("identity", {})
        for repeat in ("1", "2"):
            adapter_actual = state["identities"]["adapterReports"][repeat]
            adapter_reported = identity.get("adapterReports", {}).get(repeat, {})
            adapter_ok &= adapter_actual["sha256"] == adapter_reported.get("sha256") and adapter_actual["reportHash"] == adapter_reported.get("reportHash") == adapter_actual["selfHash"]
            consumer_ok &= state["identities"]["consumerReports"][repeat]["sha256"] == identity.get("consumerReports", {}).get(repeat, {}).get("sha256")
            payload_ok &= state["identities"]["arrays"][repeat] == identity.get("arrays", {}).get(repeat)
        repeat_ok &= state["repeatPayloadExact"] and identity.get("arrays", {}).get("1") == identity.get("arrays", {}).get("2")
        reconstruction_ok &= state["reconstructionByteExact"] and row.get("reconstructionByteExact") is True and row.get("maskByteExact") is True
    global_report = candidate.get("global", {})
    checks = {
        "D12_3_SPEC_IDENTITY": candidate.get("inputIdentities", {}).get("d12_3Spec", {}).get("sha256") == actual["d12SpecSha256"] == spec["frozenInputs"]["d12_3Spec"]["sha256"],
        "D12_3_RESULTS_FILE_IDENTITY": candidate.get("inputIdentities", {}).get("formalResults", {}).get("sha256") == actual["top"]["formalResults"]["sha256"],
        "D12_3_RESULTS_INTERNAL_IDENTITY": candidate.get("inputIdentities", {}).get("formalResults", {}).get("internalHash") == actual["top"]["formalResults"]["internalHash"] == actual["top"]["formalResults"]["selfHash"],
        "D12_3_RECEIPT_FILE_IDENTITY": candidate.get("inputIdentities", {}).get("formalReceipt", {}).get("sha256") == actual["top"]["formalReceipt"]["sha256"],
        "D12_3_RECEIPT_INTERNAL_IDENTITY": candidate.get("inputIdentities", {}).get("formalReceipt", {}).get("internalHash") == actual["top"]["formalReceipt"]["internalHash"] == actual["top"]["formalReceipt"]["selfHash"],
        "D12_3_EXECUTION_FILE_IDENTITY": candidate.get("inputIdentities", {}).get("formalExecution", {}).get("sha256") == actual["top"]["formalExecution"]["sha256"],
        "D12_3_EXECUTION_INTERNAL_IDENTITY": candidate.get("inputIdentities", {}).get("formalExecution", {}).get("internalHash") == actual["top"]["formalExecution"]["internalHash"] == actual["top"]["formalExecution"]["selfHash"],
        "ADAPTER_REPORT_IDENTITY": adapter_ok,
        "CONSUMER_REPORT_IDENTITY": consumer_ok,
        "PAYLOAD_IDENTITY": payload_ok,
        "REPEAT_PAYLOAD_IDENTITY": repeat_ok,
        "RECONSTRUCTION_BYTE_IDENTITY": reconstruction_ok,
        "GLOBAL_MAXIMUM_IDENTITY": global_report.get("interiorRgbMaximum") == actual["globalMaximum"] == spec["frozenFormalBoundary"]["interiorRgbMaximumInclusive"],
        "TIED_COORDINATE_TOTALITY": global_report.get("tieCount") == len(actual["globalTies"]) and global_report.get("tiedCoordinates") == actual["globalTies"],
        "OUTPUT_SELF_HASH": candidate.get("analysisHash") == self_hash(candidate, "analysisHash"),
    }
    return checks


def mutate(candidate: dict, attack: str) -> None:
    zeros = "0" * 64
    if attack == "D12_3_SPEC_IDENTITY": candidate["inputIdentities"]["d12_3Spec"]["sha256"] = zeros
    elif attack == "D12_3_RESULTS_FILE_IDENTITY": candidate["inputIdentities"]["formalResults"]["sha256"] = zeros
    elif attack == "D12_3_RESULTS_INTERNAL_IDENTITY": candidate["inputIdentities"]["formalResults"]["internalHash"] = zeros
    elif attack == "D12_3_RECEIPT_FILE_IDENTITY": candidate["inputIdentities"]["formalReceipt"]["sha256"] = zeros
    elif attack == "D12_3_RECEIPT_INTERNAL_IDENTITY": candidate["inputIdentities"]["formalReceipt"]["internalHash"] = zeros
    elif attack == "D12_3_EXECUTION_FILE_IDENTITY": candidate["inputIdentities"]["formalExecution"]["sha256"] = zeros
    elif attack == "D12_3_EXECUTION_INTERNAL_IDENTITY": candidate["inputIdentities"]["formalExecution"]["internalHash"] = zeros
    elif attack == "ADAPTER_REPORT_IDENTITY": candidate["fixtures"][0]["identity"]["adapterReports"]["1"]["sha256"] = zeros
    elif attack == "CONSUMER_REPORT_IDENTITY": candidate["fixtures"][0]["identity"]["consumerReports"]["1"]["sha256"] = zeros
    elif attack == "PAYLOAD_IDENTITY": candidate["fixtures"][0]["identity"]["arrays"]["1"]["adapter.previousRgba"] = zeros
    elif attack == "REPEAT_PAYLOAD_IDENTITY": candidate["fixtures"][0]["identity"]["arrays"]["2"]["adapter.previousRgba"] = zeros
    elif attack == "RECONSTRUCTION_BYTE_IDENTITY": candidate["fixtures"][0]["reconstructionByteExact"] = False
    elif attack == "GLOBAL_MAXIMUM_IDENTITY": candidate["global"]["interiorRgbMaximum"] = 0.0
    elif attack == "TIED_COORDINATE_TOTALITY": candidate["global"]["tiedCoordinates"] = []
    elif attack == "OUTPUT_SELF_HASH": candidate["analysisHash"] = zeros
    else: raise RuntimeError(attack)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise RuntimeError("refusing to overwrite D12.4 audit")
    if sha256_file(args.spec) != SPEC_SHA256: raise RuntimeError("D12.4 spec identity mismatch")
    spec = json.loads(args.spec.read_text())
    if tuple(spec["registeredNegativeCases"]) != REGISTERED: raise RuntimeError("registered attack roster mismatch")
    result = json.loads(args.result.read_text())
    actual = actual_state(spec, args.experiment_root, result)
    base = verify(result, spec, actual)
    attacks = []
    for attack in REGISTERED:
        altered = copy.deepcopy(result)
        mutate(altered, attack)
        observed = verify(altered, spec, actual)
        attacks.append({"id": attack, "passed": observed.get(attack) is False})
    passed = all(base.values()) and all(row["passed"] for row in attacks)
    body = {
        "schemaVersion": "bfs.blenderStaticZeroHeadroomLocalizationAudit.v0.1",
        "experimentId": spec["experimentId"],
        "verdict": "AUDIT_MATCH" if passed else "AUDIT_MISMATCH",
        "passed": passed,
        "baseChecks": [{"id": name, "passed": bool(value)} for name, value in base.items()],
        "basePassed": sum(base.values()),
        "baseTotal": len(base),
        "attacks": attacks,
        "attackPassed": sum(row["passed"] for row in attacks),
        "attackTotal": len(attacks),
        "independentReplay": {"globalMaximum": actual["globalMaximum"], "tiedCoordinates": actual["globalTies"], "fixtureMaximums": {fixture_id: value["maximum"] for fixture_id, value in actual["fixtures"].items()}},
        "input": {"uri": str(args.result), "sha256": sha256_file(args.result), "analysisHash": result.get("analysisHash")},
        "operationCounts": {"newBlenderRenders": 0, "modelCalls": 0, "networkCalls": 0},
    }
    audit = {**body, "auditHash": canonical_hash(body)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D124_AUDIT_OK verdict={audit['verdict']} base={audit['basePassed']}/{audit['baseTotal']} attacks={audit['attackPassed']}/{audit['attackTotal']}")


if __name__ == "__main__": main()
