#!/usr/bin/env python3
"""Independent raw-payload/result audit for B52-D12.11-I1."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "89dd3637ffe5af3544e8cd8aca8869eedd8b1a1867d41e08a354e5cd0c3b2a0e"
H1_SPEC_SHA256 = "c2756a20e314cf470698ef7af6160154b8d7e2d5e8531ce6591b2509a8730dbc"
ARRAYS = {
    "previousRgba": ("previous.rgba32", 4, "<f4", "adapter"),
    "currentRgba": ("current.rgba32", 4, "<f4", "adapter"),
    "previousDepth": ("previous-depth.f32", 1, "<f4", "adapter"),
    "currentDepth": ("current-depth.f32", 1, "<f4", "adapter"),
    "previousOwner": ("previous-owner.f32", 1, "<f4", "adapter"),
    "currentOwner": ("current-owner.f32", 1, "<f4", "adapter"),
    "previousObjectIndex": ("previous-object-index.f32", 1, "<f4", "adapter"),
    "currentObjectIndex": ("current-object-index.f32", 1, "<f4", "adapter"),
    "vector": ("vector.xy32", 2, "<f4", "adapter"),
    "vectorNext": ("vector-next.xy32", 2, "<f4", "adapter"),
    "acceptedReconstructed": ("accepted-reconstructed.rgba32", 4, "<f4", "consumer"),
    "reason": ("reason.u8", 1, "u1", "consumer"),
    "analyticOwner": ("analytic-owner.u8", 1, "u1", "consumer"),
    "structuralValid": ("structural-valid.u8", 1, "u1", "consumer"),
    "radius2Interior": ("radius2-interior.u8", 1, "u1", "consumer"),
    "supportEligible": ("support-eligible.u8", 1, "u1", "consumer"),
    "supportRejected": ("support-rejected.u8", 1, "u1", "consumer"),
    "accepted": ("accepted.u8", 1, "u1", "consumer"),
    "riskRejected": ("risk-rejected.u8", 1, "u1", "consumer"),
    "riskQ30": ("risk.q30.u32", 3, "<u4", "consumer"),
}
REASONS = {"UNREGISTERED": 0, "INVALID_CURRENT_ORACLE": 1, "INVALID_BOUNDS": 2, "INVALID_OWNER": 3, "INVALID_ALPHA": 4, "INVALID_DEPTH": 5, "VALID": 6}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def self_ok(value: dict, field: str) -> bool:
    return value.get(field) == canon({key: item for key, item in value.items() if key != field})


def load(path: Path, shape, dtype):
    payload = path.read_bytes()
    if len(payload) != math.prod(shape) * np.dtype(dtype).itemsize:
        raise RuntimeError(f"D12.11-I1 audit payload length mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy(), payload


def metric(left, right, mask):
    values = (left[..., :3].astype(np.float64) - right[..., :3].astype(np.float64))[mask]
    return {"maximum": float(np.abs(values).max()) if values.size else None, "rmse": float(np.sqrt(np.mean(values * values))) if values.size else None, "sampleCount": int(values.size)}


def close(left, right, tolerance=1e-15):
    return left is right if left is None or right is None else abs(float(left) - float(right)) <= tolerance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D12.11-I1 audit")
    intervention = json.loads(args.spec.read_text())
    h1_path = Path(intervention["parents"]["h1Spec"]["uri"])
    if sha_file(args.spec) != SPEC_SHA256 or sha_file(h1_path) != H1_SPEC_SHA256:
        raise RuntimeError("D12.11-I1 spec identity mismatch")
    spec = json.loads(h1_path.read_text())
    result = json.loads(args.result.read_text())
    execution = json.loads(args.execution.read_text())
    if sha_file(Path(sys.executable)) != spec["runtime"]["python"]["sha256"]:
        raise RuntimeError("D12.11-I1 audit runtime identity mismatch")
    h1_root = Path(intervention["parents"]["h1Result"]["uri"]).parent
    localization_root = Path(intervention["parents"]["ownerLocalizationResult"]["uri"]).parent
    result_hash_ok = self_ok(result, "evidenceHash")
    execution_ok = self_ok(execution, "executionHash")
    raw_checks, dual_checks, measurement_checks = [], [], []
    measurement_by_cell = {row["cell"]: row for row in result["measurements"]}
    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        for repeat in (1, 2):
            cell = f"{fixture_id}/R{repeat}"
            adapter_dir = args.root / "adapters" / fixture_id / f"R{repeat}" / "arrays"
            python_dir = args.root / "consumers/python" / fixture_id / f"R{repeat}" / "arrays"
            node_dir = args.root / "consumers/node" / fixture_id / f"R{repeat}" / "arrays"
            arrays = {}
            for name, (filename, channels, dtype, origin) in ARRAYS.items():
                shape = (height, width, channels) if channels > 1 else (height, width)
                directory = adapter_dir if origin == "adapter" else python_dir
                arrays[name], payload = load(directory / filename, shape, dtype)
                if origin == "consumer":
                    dual_checks.append((node_dir / filename).read_bytes() == payload)
            h1_accepted = np.frombuffer((h1_root / "consumers/python" / fixture_id / f"R{repeat}" / "arrays/accepted.u8").read_bytes(), dtype="u1").reshape(height, width).astype(bool)
            true_owner = np.frombuffer((localization_root / "payloads" / fixture_id / f"R{repeat}" / "true-owner-bilinear.u8").read_bytes(), dtype="u1").reshape(height, width).astype(bool)
            paired_map = {
                "previousRgba": "previous.rgba32", "currentRgba": "current.rgba32",
                "previousDepth": "previous-depth.f32", "currentDepth": "current-depth.f32",
                "vector": "vector.xy32", "vectorNext": "vector-next.xy32",
                "previousObjectIndex": "previous-owner.f32", "currentObjectIndex": "current-owner.f32",
            }
            h1_adapter = h1_root / "adapters" / fixture_id / f"R{repeat}" / "arrays"
            raw_checks.append(all((adapter_dir / ARRAYS[name][0]).read_bytes() == (h1_adapter / h1_name).read_bytes() for name, h1_name in paired_map.items()))
            allowed_tokens = {0.0, *(float(value) for value in intervention["materialOwnerTokens"]["assignments"].values())}
            raw_checks.append(set(np.unique(arrays["previousOwner"]).astype(float)).issubset(allowed_tokens) and set(np.unique(arrays["currentOwner"]).astype(float)).issubset(allowed_tokens))
            structural = arrays["structuralValid"].astype(bool)
            radius2 = arrays["radius2Interior"].astype(bool)
            eligible = arrays["supportEligible"].astype(bool)
            support_rejected = arrays["supportRejected"].astype(bool)
            accepted = arrays["accepted"].astype(bool)
            risk_rejected = arrays["riskRejected"].astype(bool)
            raw_checks.extend([
                np.array_equal(arrays["reason"] == REASONS["VALID"], structural),
                not np.logical_and(eligible, ~radius2).any(),
                np.array_equal(eligible | support_rejected, radius2),
                not np.logical_and(eligible, support_rejected).any(),
                np.array_equal(accepted | risk_rejected, eligible),
                not np.logical_and(accepted, risk_rejected).any(),
                not np.any(arrays["riskQ30"][~eligible]),
                np.array_equal(arrays["acceptedReconstructed"][~accepted], arrays["currentRgba"][~accepted]),
            ])
            row = measurement_by_cell[cell]
            reason_counts = {name: int((arrays["reason"] == code).sum()) for name, code in REASONS.items()}
            owners = {}
            for owner_index, owner in enumerate(fixture["owners"], 1):
                owner_mask = arrays["analyticOwner"] == owner_index
                radius_count = int((radius2 & owner_mask).sum())
                accepted_count = int((accepted & owner_mask).sum())
                owners[owner["analyticOwnerId"]] = {"radius2": radius_count, "accepted": accepted_count, "retention": accepted_count / radius_count if radius_count else None}
            coverage = {"radius2": int(radius2.sum()), "supportEligible": int(eligible.sum()), "accepted": int(accepted.sum()), "acceptedToRadius2": float(accepted.sum() / radius2.sum()) if radius2.any() else None, "owners": owners}
            rgb = metric(arrays["acceptedReconstructed"], arrays["currentRgba"], accepted)
            measurement_checks.extend([
                row["reasonCounts"] == reason_counts,
                row["fallbackExact"] == np.array_equal(arrays["acceptedReconstructed"][~accepted], arrays["currentRgba"][~accepted]),
                row["supportRejectedPixels"] == int(support_rejected.sum()),
                row["riskRejectedPixels"] == int(risk_rejected.sum()),
                row["coverage"] == coverage,
                row["acceptedRgb"]["sampleCount"] == rgb["sampleCount"],
                close(row["acceptedRgb"]["maximum"], rgb["maximum"]),
                close(row["acceptedRgb"]["rmse"], rgb["rmse"]),
                row["pairedIntervention"] == {
                    "registeredH1AcceptedAliasPixels": int((h1_accepted & ~true_owner).sum()),
                    "acceptedOutsideTrueOwnerBilinearPixels": int((accepted & ~true_owner).sum()),
                    "acceptedOnRegisteredAliasPixels": int((accepted & h1_accepted & ~true_owner).sum()),
                    "newAcceptedPixelsRelativeToH1": int((accepted & ~h1_accepted).sum()),
                    "h1AcceptedPixels": int(h1_accepted.sum()),
                    "materialAcceptedPixels": int(accepted.sum()),
                },
            ])
    checks_map = {row["id"]: bool(row["passed"]) for row in result["checks"]}
    decision = intervention["decision"]
    hard = {"PARENT_IDENTITY", "PREFLIGHT_TOOL_IDENTITY", "PROCESS_TOTALITY_BEFORE_AUDIT", "PAIRED_H1_PAYLOAD_IDENTITY", "MATERIAL_TOKEN_DOMAIN", "SOURCE_ADAPTER_CONSUMER_IDENTITY", "DUAL_AND_INDEPENDENT_REPLAY", "VECTOR_ORACLE", "TYPED_DEPTH_DOMAINS", "STRUCTURAL_REJECTION", "Q30_RISK_CONSERVATISM", "ACCEPTED_QUALITY", "PRIMARY_ALIAS_ROSTER", "PRIMARY_ALIAS_ELIMINATION", "NO_NEW_ACCEPTED_COORDINATES", "STATIC_CONTROL", "MODEL_NETWORK_ZERO"}
    hard_without_alias = hard - {"PRIMARY_ALIAS_ELIMINATION"}
    hard_pass = all(checks_map.get(name, False) for name in hard)
    hard_without_alias_pass = all(checks_map.get(name, False) for name in hard_without_alias)
    all_pass = all(checks_map.values())
    expected_verdict = decision["supportedVerdict"] if all_pass else decision["boundedVerdict"] if hard_pass else decision["aliasFailureVerdict"] if hard_without_alias_pass else decision["rejectedVerdict"]
    verdict_ok = result["verdict"] == expected_verdict and result["passed"] == (expected_verdict == decision["supportedVerdict"])
    attacks = result.get("mutationAttacks", [])
    attack_ok = len(attacks) >= intervention["attacks"]["minimumRegisteredAttacks"] and len({row["id"] for row in attacks}) == len(attacks) and all(row.get("passed") is True for row in attacks) and result.get("mutationAttackPassed") == len(attacks) == result.get("mutationAttackTotal")
    children = execution.get("children", [])
    pids = [row["pid"] for row in children] + [result.get("analyzerPid"), os.getpid()]
    process_ok = execution_ok and len(children) == 72 and len(set(pids)) == 74 and all(row.get("exitCode") == 0 for row in children) and execution["operationCounts"]["modelCalls"] == 0 and execution["operationCounts"]["networkCalls"] == 0
    checks = [
        ("SPEC_RUNTIME_RESULT_HASH", result_hash_ok),
        ("EXECUTION_AND_74_PID_TOTALITY", process_ok),
        ("RAW_PAYLOAD_INVARIANTS", all(raw_checks)),
        ("DUAL_PAYLOAD_IDENTITY", all(dual_checks)),
        ("MEASUREMENT_RAW_REPLAY", all(measurement_checks)),
        ("VERDICT_MAPPING", verdict_ok),
        ("MUTATION_ROSTER_TOTALITY", attack_ok),
        ("RESULT_COUNTS", result.get("checkPassed") == sum(checks_map.values()) and result.get("checkTotal") == len(checks_map)),
        ("MODEL_NETWORK_ZERO", result["operationCounts"]["modelCalls"] == 0 and result["operationCounts"]["networkCalls"] == 0),
    ]
    body = {
        "schemaVersion": "bfs.blenderMaterialIndexOwnerIntegrationAudit.v0.1",
        "experimentId": intervention["experimentId"],
        "auditPid": os.getpid(),
        "passed": all(value for _, value in checks),
        "checks": [{"id": name, "passed": bool(value)} for name, value in checks],
        "checkPassed": sum(value for _, value in checks),
        "checkTotal": len(checks),
        "expectedVerdict": expected_verdict,
        "resultEvidenceHash": result.get("evidenceHash"),
        "resultSha256": sha_file(args.result),
        "rawCellCount": len(measurement_by_cell),
        "dualPayloadChecks": len(dual_checks),
        "measurementReplayChecks": len(measurement_checks),
        "operationCounts": {"auditProcesses": 1, "modelCalls": 0, "networkCalls": 0},
    }
    audit = {**body, "auditHash": canon(body)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1211_AUDIT_OK passed={audit['passed']} checks={audit['checkPassed']}/{audit['checkTotal']}")
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
