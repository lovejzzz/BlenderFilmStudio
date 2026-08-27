#!/usr/bin/env python3
"""Independent analyzer for exploratory B52-D12.9-D1 outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np


Q24 = 1 << 24
Q30 = 1 << 30
UINT32_MAX = (1 << 32) - 1


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_report(path: Path) -> dict:
    report = json.loads(path.read_text())
    body = {key: value for key, value in report.items() if key != "reportHash"}
    if report.get("reportHash") != canonical_hash(body):
        raise RuntimeError(f"report self-hash mismatch: {path}")
    return report


def exact_scaled(value: float, scale: int) -> int:
    scaled = value * scale
    if scaled != int(scaled):
        raise RuntimeError(f"non-canonical fixed-point value: {value!r}")
    return int(scaled)


def ceil_div(numerator: int, denominator: int) -> int:
    return (numerator + denominator - 1) // denominator


def load(path: Path, dtype: str, shape: tuple[int, ...]) -> np.ndarray:
    return np.frombuffer(path.read_bytes(), dtype=dtype).reshape(shape).copy()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--python-root", type=Path, required=True)
    parser.add_argument("--node-root", type=Path, required=True)
    parser.add_argument("--python-report", type=Path, required=True)
    parser.add_argument("--node-report", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D12.9-D1 result")
    spec = json.loads(args.spec.read_text())
    source_spec_path = Path.cwd() / spec["sourceEvidence"]["spec"]["uri"]
    source_result_path = Path.cwd() / spec["sourceEvidence"]["result"]["uri"]
    source_audit_path = Path.cwd() / spec["sourceEvidence"]["correctedAudit"]["uri"]
    source_spec = json.loads(source_spec_path.read_text())
    source_result = json.loads(source_result_path.read_text())
    source_audit = json.loads(source_audit_path.read_text())
    execution = json.loads(args.execution.read_text())
    python_report = validate_report(args.python_report)
    node_report = validate_report(args.node_report)
    parent_identity = (
        sha_file(source_spec_path) == spec["sourceEvidence"]["spec"]["sha256"]
        and sha_file(source_result_path) == spec["sourceEvidence"]["result"]["sha256"]
        and source_result.get("verdict") == spec["sourceEvidence"]["result"]["verdict"]
        and sha_file(source_audit_path) == spec["sourceEvidence"]["correctedAudit"]["sha256"]
        and source_audit.get("checkPassed") == spec["sourceEvidence"]["correctedAudit"]["checkPassed"]
        and source_audit.get("checkTotal") == spec["sourceEvidence"]["correctedAudit"]["checkTotal"]
    )
    fixture_by_id = {row["id"]: row for row in source_spec["fixtures"]}
    measurements = []
    identities = {}
    all_payload_identity = True
    all_replay = True
    risk_underbound_samples = 0
    quality_ok = True
    coverage_ok = True
    static_ok = True
    same_index_rejected = 0
    for fixture_id in spec["sourceEvidence"]["fixtures"]:
        fixture = fixture_by_id[fixture_id]
        width, height = fixture["resolution"]
        adapter_dir = args.source_root / "adapters" / fixture_id / "R1"
        consumer_dir = args.source_root / "consumers" / "python" / fixture_id / "R1"
        adapter = validate_report(adapter_dir / "report.json")
        consumer = validate_report(consumer_dir / "report.json")
        previous = load(adapter_dir / "arrays" / "previous.rgba32", "<f4", (height, width, 4))
        current = load(adapter_dir / "arrays" / "current.rgba32", "<f4", (height, width, 4))
        previous_owner = load(adapter_dir / "arrays" / "previous-owner.f32", "<f4", (height, width))
        vector = load(adapter_dir / "arrays" / "vector.xy32", "<f4", (height, width, 2))
        radius2 = load(consumer_dir / "arrays" / "radius2-interior.u8", "u1", (height, width))
        old_adaptive = load(consumer_dir / "arrays" / "adaptive-interior.u8", "u1", (height, width))
        analytic_owner = load(consumer_dir / "arrays" / "analytic-owner.u8", "u1", (height, width))
        producer_arrays = {}
        for producer, root in (("python", args.python_root), ("node", args.node_root)):
            directory = root / fixture_id
            producer_arrays[producer] = {
                "eligible": load(directory / "eligible.u8", "u1", (height, width)),
                "accepted": load(directory / "accepted.u8", "u1", (height, width)),
                "risk": load(directory / "risk.q30.u32", "<u4", (height, width, 3)),
            }
        fixture_identity = {}
        for name, filename in (("eligible", "eligible.u8"), ("accepted", "accepted.u8"), ("risk", "risk.q30.u32")):
            python_path = args.python_root / fixture_id / filename
            node_path = args.node_root / fixture_id / filename
            same = python_path.read_bytes() == node_path.read_bytes()
            all_payload_identity = all_payload_identity and same
            fixture_identity[name] = {"pythonSha256": sha_file(python_path), "nodeSha256": sha_file(node_path), "byteIdentical": same}
        expected_eligible = np.zeros((height, width), dtype=np.uint8)
        expected_accepted = np.zeros((height, width), dtype=np.uint8)
        expected_risk = np.zeros((height, width, 3), dtype="<u4")
        squared_error = 0.0
        error_samples = 0
        error_maximum = 0.0
        for y, x in zip(*np.nonzero(radius2)):
            qx = x + float(vector[y, x, 0])
            qy = y - float(vector[y, x, 1])
            x0, y0 = math.floor(qx), math.floor(qy)
            if x0 - 1 < 0 or x0 + 2 >= width or y0 - 1 < 0 or y0 + 2 >= height:
                continue
            owner = previous_owner[y0, x0]
            if not np.all(previous_owner[y0 - 1:y0 + 3, x0 - 1:x0 + 3] == owner) or not np.all(previous[y0 - 1:y0 + 3, x0 - 1:x0 + 3, 3] > np.float32(0.999)):
                continue
            fx_int = exact_scaled(qx - x0, Q24)
            fy_int = exact_scaled(qy - y0, Q24)
            expected_eligible[y, x] = 1
            for channel in range(3):
                def color(yy: int, xx: int) -> int:
                    return exact_scaled(float(previous[yy, xx, channel]), Q30)
                mx = max(abs(color(yy, xx - 1) - 2 * color(yy, xx) + color(yy, xx + 1)) for yy in (y0, y0 + 1) for xx in (x0, x0 + 1))
                my = max(abs(color(yy - 1, xx) - 2 * color(yy, xx) + color(yy + 1, xx)) for xx in (x0, x0 + 1) for yy in (y0, y0 + 1))
                numerator = 2 * (fx_int * (Q24 - fx_int) * mx + fy_int * (Q24 - fy_int) * my)
                units = ceil_div(numerator, Q24 * Q24) + spec["candidate"]["roundingAllowanceQ30"]
                expected_risk[y, x, channel] = min(units, UINT32_MAX)
            expected_accepted[y, x] = int(int(expected_risk[y, x].max()) <= spec["candidate"]["riskThresholdQ30Inclusive"])
            fx = qx - x0
            fy = qy - y0
            weights = ((1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy)
            taps = ((y0, x0), (y0, x0 + 1), (y0 + 1, x0), (y0 + 1, x0 + 1))
            for channel in range(3):
                values = [float(previous[ty, tx, channel]) for ty, tx in taps]
                reconstructed = ((values[0] * weights[0] + values[1] * weights[1]) + values[2] * weights[2]) + values[3] * weights[3]
                error = abs(reconstructed - float(current[y, x, channel]))
                risk_value = int(expected_risk[y, x, channel]) / Q30
                risk_underbound_samples += int(error > risk_value)
                if expected_accepted[y, x]:
                    squared_error += error * error
                    error_samples += 1
                    error_maximum = max(error_maximum, error)
        replay_ok = all(
            np.array_equal(producer_arrays[producer][name], expected)
            for producer in ("python", "node")
            for name, expected in (("eligible", expected_eligible), ("accepted", expected_accepted), ("risk", expected_risk))
        )
        all_replay = all_replay and replay_ok
        radius2_count = int(radius2.sum())
        eligible_count = int(expected_eligible.sum())
        accepted_count = int(expected_accepted.sum())
        retention = accepted_count / radius2_count
        owner_rows = {}
        for owner_index, owner_spec in enumerate(fixture["owners"], start=1):
            owner_radius = int(np.logical_and(radius2 == 1, analytic_owner == owner_index).sum())
            owner_accepted = int(np.logical_and(expected_accepted == 1, analytic_owner == owner_index).sum())
            owner_retention = owner_accepted / owner_radius if owner_radius else None
            owner_rows[owner_spec["analyticOwnerId"]] = {"radius2": owner_radius, "accepted": owner_accepted, "retention": owner_retention}
            if owner_radius >= spec["derivationGates"]["minimumRadius2PixelsForOwnerGate"]:
                coverage_ok = coverage_ok and owner_retention >= spec["derivationGates"]["minimumAcceptedToRadius2PerOwner"]
        rmse = math.sqrt(squared_error / error_samples) if error_samples else None
        quality_ok = quality_ok and error_samples > 0 and error_maximum <= spec["derivationGates"]["acceptedRgbMaximum"] and rmse <= spec["derivationGates"]["acceptedRgbRmseMaximum"]
        coverage_ok = coverage_ok and retention >= spec["derivationGates"]["minimumAcceptedToRadius2PerCell"]
        risk_rejected = int(np.logical_and(expected_eligible == 1, expected_accepted == 0).sum())
        if fixture_id == "SAME_INDEX_DEPTH_REVEAL_173X107":
            same_index_rejected = risk_rejected
        if fixture_id == "MULTI_OWNER_STATIC_CONTROL_127X83":
            static_ok = retention == spec["derivationGates"]["staticControlRetention"]
        measurements.append({
            "fixtureId": fixture_id,
            "radius2Pixels": radius2_count,
            "oldAdaptivePixels": int(old_adaptive.sum()),
            "eligiblePixels": eligible_count,
            "acceptedPixels": accepted_count,
            "supportRejectedPixels": radius2_count - eligible_count,
            "riskRejectedPixels": risk_rejected,
            "acceptedToRadius2": retention,
            "acceptedRgb": {"maximum": error_maximum, "rmse": rmse, "sampleCount": error_samples},
            "owners": owner_rows,
            "independentReplay": replay_ok,
        })
        identities[fixture_id] = fixture_identity
    process_ok = (
        execution.get("experimentId") == spec["experimentId"]
        and execution.get("operationCounts") == {"pythonProducers": 1, "nodeProducers": 1, "analyzers": 1, "modelCalls": 0, "networkCalls": 0}
        and len(execution.get("children", [])) == 2
        and len({row["pid"] for row in execution.get("children", [])} | {os.getpid()}) == 3
        and all(row.get("exitCode") == 0 for row in execution.get("children", []))
    )
    checks = [
        {"id": "PARENT_IDENTITY", "passed": parent_identity},
        {"id": "PROCESS_TOTALITY", "passed": process_ok},
        {"id": "DUAL_PAYLOAD_BYTE_IDENTITY", "passed": all_payload_identity},
        {"id": "INDEPENDENT_INTEGER_REPLAY", "passed": all_replay},
        {"id": "RISK_CONSERVATISM_ON_DERIVATION", "passed": risk_underbound_samples <= spec["derivationGates"]["riskUnderboundRgbSamplesMaximum"]},
        {"id": "DERIVATION_QUALITY", "passed": quality_ok},
        {"id": "DERIVATION_COVERAGE", "passed": coverage_ok},
        {"id": "SAME_INDEX_RISK_STRESS", "passed": same_index_rejected >= spec["derivationGates"]["minimumSameIndexRiskRejectedPixels"]},
        {"id": "STATIC_CONTROL", "passed": static_ok},
        {"id": "MODEL_NETWORK_ZERO", "passed": execution.get("operationCounts", {}).get("modelCalls") == 0 and execution.get("operationCounts", {}).get("networkCalls") == 0},
    ]
    passed = sum(row["passed"] for row in checks)
    verdict = "MOTION_AWARE_CURVATURE_RISK_CANDIDATE_DERIVED" if passed == len(checks) else "MOTION_AWARE_CURVATURE_RISK_CANDIDATE_NOT_DERIVED"
    evidence_core = {"checks": checks, "measurements": measurements, "identities": identities, "riskUnderboundRgbSamples": risk_underbound_samples}
    body = {
        "schemaVersion": "bfs.blenderMotionAwareCurvatureRiskDerivationResult.v0.1",
        "experimentId": spec["experimentId"],
        "analyzerPid": os.getpid(),
        "verdict": verdict,
        "interpretation": "post-hoc candidate derivation only; fresh preregistered Blender 5.2 evidence is required",
        "checkPassed": passed,
        "checkTotal": len(checks),
        **evidence_core,
        "evidenceHash": canonical_hash(evidence_core),
    }
    result = {**body, "resultHash": canonical_hash(body)}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D129_D1_ANALYSIS verdict={verdict} checks={passed}/{len(checks)} underbound={risk_underbound_samples}")


if __name__ == "__main__":
    main()
