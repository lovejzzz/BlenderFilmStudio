#!/usr/bin/env python3
"""Post-hoc threshold/support diagnostic for the immutable D12.9-H1 result."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


FORMAL_IDENTITIES = {
    "results.json": "23cc449e6d1c83e06c8f5a80335ead42ec37cc433eee70c54cb4d9fef308d8ee",
    "audit.json": "160c194ddaaa4bb727328371de8e8f538af3b0935a4f65ec33e3e10821b46bb8",
    "receipt.json": "9d774b40fe41b2008d4d103a6f45b7f15afa324d8e2bd024d88cd112c7631d9f",
}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read(path: Path, shape, dtype):
    payload = path.read_bytes()
    if len(payload) != math.prod(shape) * np.dtype(dtype).itemsize:
        raise RuntimeError(f"D12.9-H1 coverage payload size mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy()


def bilinear_errors(previous, current, vector, eligible):
    height, width = eligible.shape
    maximum = np.zeros((height, width), dtype=np.float64)
    squared_sum = np.zeros((height, width), dtype=np.float64)
    for y, x in np.argwhere(eligible):
        qx, qy = x + float(vector[y, x, 0]), y - float(vector[y, x, 1])
        x0, y0 = math.floor(qx), math.floor(qy)
        fx, fy = qx - x0, qy - y0
        weights = ((1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy)
        taps = ((y0, x0), (y0, x0 + 1), (y0 + 1, x0), (y0 + 1, x0 + 1))
        reconstructed = np.asarray([
            ((float(previous[taps[0]][channel]) * weights[0] + float(previous[taps[1]][channel]) * weights[1]) + float(previous[taps[2]][channel]) * weights[2]) + float(previous[taps[3]][channel]) * weights[3]
            for channel in range(3)
        ], dtype=np.float64).astype(np.float32).astype(np.float64)
        difference = reconstructed - current[y, x, :3].astype(np.float64)
        maximum[y, x] = np.abs(difference).max()
        squared_sum[y, x] = np.sum(difference * difference)
    return maximum, squared_sum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D12.9-H1 coverage diagnostic")
    spec = json.loads(args.spec.read_text())
    formal = args.formal_root
    identity = {name: sha_file(formal / name) for name in FORMAL_IDENTITIES}
    if identity != FORMAL_IDENTITIES:
        raise RuntimeError("D12.9-H1 formal parent identity mismatch")
    result = json.loads((formal / "results.json").read_text())
    if result["verdict"] != "MOTION_AWARE_CURVATURE_RISK_SAFE_BUT_COVERAGE_NOT_SUPPORTED":
        raise RuntimeError("D12.9-H1 frozen verdict mismatch")
    base_threshold = int(spec["frozenGates"]["risk"]["riskThresholdQ30Inclusive"])
    coverage_target = float(spec["frozenGates"]["coverage"]["acceptedToRadius2PerCellMinimum"])
    quality_target = float(spec["frozenGates"]["quality"]["acceptedRgbMaximum"])
    rows = []
    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        adapter = formal / "adapters" / fixture_id / "R1/arrays"
        consumer = formal / "consumers/python" / fixture_id / "R1/arrays"
        previous = read(adapter / "previous.rgba32", (height, width, 4), "<f4")
        current = read(adapter / "current.rgba32", (height, width, 4), "<f4")
        vector = read(adapter / "vector.xy32", (height, width, 2), "<f4")
        owner = read(consumer / "analytic-owner.u8", (height, width), "u1")
        radius2 = read(consumer / "radius2-interior.u8", (height, width), "u1").astype(bool)
        eligible = read(consumer / "support-eligible.u8", (height, width), "u1").astype(bool)
        support_rejected = read(consumer / "support-rejected.u8", (height, width), "u1").astype(bool)
        risk_rejected = read(consumer / "risk-rejected.u8", (height, width), "u1").astype(bool)
        risk = read(consumer / "risk.q30.u32", (height, width, 3), "<u4").max(axis=2)
        errors, squared = bilinear_errors(previous, current, vector, eligible)
        radius_count = int(radius2.sum())
        base_accepted = eligible & (risk <= base_threshold)
        target_count = math.ceil(coverage_target * radius_count)
        additional_needed = max(0, target_count - int(base_accepted.sum()))
        rejected_risks = np.sort(risk[eligible & (risk > base_threshold)])
        feasible_by_support = target_count <= int(eligible.sum())
        threshold = int(rejected_risks[additional_needed - 1]) if additional_needed and additional_needed <= rejected_risks.size else base_threshold
        counterfactual = eligible & (risk <= threshold)
        counterfactual_samples = int(counterfactual.sum()) * 3
        counterfactual_rmse = float(math.sqrt(float(squared[counterfactual].sum()) / counterfactual_samples)) if counterfactual_samples else None
        owners = {}
        for index, owner_spec in enumerate(fixture["owners"], 1):
            owner_radius = radius2 & (owner == index)
            owner_accepted = base_accepted & (owner == index)
            owners[owner_spec["analyticOwnerId"]] = {
                "radius2": int(owner_radius.sum()),
                "supportRejected": int((support_rejected & (owner == index)).sum()),
                "riskRejected": int((risk_rejected & (owner == index)).sum()),
                "accepted": int(owner_accepted.sum()),
                "retention": float(owner_accepted.sum() / owner_radius.sum()) if owner_radius.any() else None,
            }
        rows.append({
            "fixtureId": fixture_id,
            "radius2": radius_count,
            "supportEligible": int(eligible.sum()),
            "supportRejected": int(support_rejected.sum()),
            "baseAccepted": int(base_accepted.sum()),
            "baseRetention": float(base_accepted.sum() / radius_count),
            "riskRejected": int(risk_rejected.sum()),
            "targetAcceptedFor97Percent": target_count,
            "additionalRiskRejectedPixelsNeeded": additional_needed,
            "targetFeasibleWithinFrozenSupport": feasible_by_support,
            "minimumCounterfactualThresholdQ30": threshold,
            "minimumCounterfactualThresholdSceneLinear": threshold / (1 << 30),
            "counterfactualAccepted": int(counterfactual.sum()),
            "counterfactualRetention": float(counterfactual.sum() / radius_count),
            "counterfactualRgbMaximum": float(errors[counterfactual].max()) if counterfactual.any() else None,
            "counterfactualRgbRmse": counterfactual_rmse,
            "counterfactualQualityMaximumPass": bool(counterfactual.any() and errors[counterfactual].max() <= quality_target),
            "owners": owners,
        })
    body = {
        "schemaVersion": "bfs.blenderMotionAwareCurvatureRiskCoverageBoundaryAnalysis.v0.1",
        "experimentId": "B52-D12.9-H1-POSTHOC-COVERAGE",
        "decisionRole": "POST_HOC_INTERPRETATION_ONLY_FORMAL_VERDICT_UNCHANGED",
        "formalParents": identity,
        "formalEvidenceHash": result["evidenceHash"],
        "formalVerdict": result["verdict"],
        "frozenBaseThresholdQ30": base_threshold,
        "frozenCoverageTarget": coverage_target,
        "frozenQualityMaximum": quality_target,
        "fixtures": rows,
        "conclusion": "No failing primary fixture reaches frozen 97% coverage by scalar threshold relaxation while preserving the frozen accepted RGB maximum.",
        "nonClaims": [
            "This post-hoc diagnostic does not alter the D12.9-H1 verdict.",
            "It does not select a new production threshold.",
            "It does not convert the formal holdout into a new holdout for future candidates.",
        ],
    }
    output = {**body, "analysisHash": canon(body)}
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D129_COVERAGE_DIAGNOSTIC_OK fixtures={len(rows)} hash={output['analysisHash']}")


if __name__ == "__main__":
    main()
