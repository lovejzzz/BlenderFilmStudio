#!/usr/bin/env python3
"""Independent replay audit and mutation testing for B52-D12.6."""

from __future__ import annotations

import argparse
from collections import deque
import copy
import hashlib
import json
import math
import os
import struct
from pathlib import Path

import numpy as np


SPEC_SHA256 = "9ae043172e3d126d590b6be7942de759a503eee3c76cf4b96062e92285691fe5"
CHANNELS = ("R", "G", "B")


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def self_ok(document: dict, field: str) -> bool:
    return document.get(field) == canon({key: value for key, value in document.items() if key != field})


def bits(value: np.float32) -> str:
    return f"{struct.unpack('<I', struct.pack('<f', float(value)))[0]:08x}"


def array(path: Path, shape: tuple[int, ...], dtype: str = "<f4") -> np.ndarray:
    payload = path.read_bytes()
    if len(payload) != math.prod(shape) * np.dtype(dtype).itemsize:
        raise RuntimeError(f"length mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy()


def distance_map(owner: np.ndarray, alpha: np.ndarray, registered: set[float]) -> np.ndarray:
    height, width = owner.shape
    valid = np.isin(owner, list(registered)) & (alpha > np.float32(0.999))
    distance = np.zeros((height, width), dtype=np.int16)
    queue: deque[tuple[int, int]] = deque()
    for y, x in np.argwhere(valid):
        value = owner[y, x]
        boundary = x == 0 or y == 0 or x == width - 1 or y == height - 1
        if not boundary:
            boundary = any(not valid[ny, nx] or owner[ny, nx] != value for ny in range(y - 1, y + 2) for nx in range(x - 1, x + 2))
        if boundary:
            distance[y, x] = 1
            queue.append((int(y), int(x)))
    while queue:
        y, x = queue.popleft()
        value = owner[y, x]
        for ny in range(max(0, y - 1), min(height, y + 2)):
            for nx in range(max(0, x - 1), min(width, x + 2)):
                if valid[ny, nx] and owner[ny, nx] == value and distance[ny, nx] == 0:
                    distance[ny, nx] = distance[y, x] + 1
                    queue.append((ny, nx))
    return distance


def terms(previous: np.ndarray, current: np.ndarray, vector: np.ndarray, x: int, y: int, channel: int) -> dict:
    qx, qy = x + float(vector[y, x, 0]), y - float(vector[y, x, 1])
    x0, y0 = math.floor(qx), math.floor(qy)
    fx, fy = qx - x0, qy - y0
    coordinates = ((x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1))
    weights = ((1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy)
    taps = tuple(float(previous[ty, tx, channel]) for tx, ty in coordinates)
    center = float(current[y, x, channel])
    contributions = tuple(weight * (tap - center) for weight, tap in zip(weights, taps))
    pre_cast = (((taps[0] * weights[0]) + (taps[1] * weights[1])) + (taps[2] * weights[2])) + (taps[3] * weights[3])
    final = np.float32(pre_cast)
    ulp = abs(float(np.spacing(final)))
    risk = sum(abs(weight) * abs(tap - center) for weight, tap in zip(weights, taps)) + ulp
    return {"qx": qx, "qy": qy, "fractional": (fx, fy), "coordinates": coordinates, "weights": weights, "taps": taps, "center": center, "contributions": contributions, "preCast": pre_cast, "final": final, "ulp": ulp, "risk": risk}


def distribution(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "minimum": None, "p50": None, "p95": None, "maximum": None}
    ordered = sorted(values)
    def pick(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction)))]
    return {"count": len(values), "minimum": ordered[0], "p50": pick(0.5), "p95": pick(0.95), "maximum": ordered[-1]}


def rank(values: list[float]) -> np.ndarray:
    ordering = sorted(range(len(values)), key=lambda index: (values[index], index))
    result = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(ordering):
        end = start + 1
        while end < len(ordering) and values[ordering[end]] == values[ordering[start]]:
            end += 1
        value = (start + end - 1) / 2.0 + 1.0
        for index in ordering[start:end]:
            result[index] = value
        start = end
    return result


def spearman(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2:
        return None
    a, b = rank(left), rank(right)
    a -= a.mean(); b -= b.mean()
    denominator = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
    return float(np.dot(a, b) / denominator) if denominator else None


def expected_record(fixture: str, radius: int, arrays: dict[str, np.ndarray], reconstructed: np.ndarray, distance: np.ndarray, x: int, y: int, channel: int) -> dict:
    row = terms(arrays["previous"], arrays["current"], arrays["vector"], x, y, channel)
    formal = np.float32(reconstructed[y, x, channel])
    vector_values = [np.float32(arrays["vector"][y, x, index]) for index in range(2)]
    actual = abs(float(formal) - row["center"])
    return {
        "fixtureId": fixture, "radius": radius, "ownerPassIndex": int(arrays["owner"][y, x]), "x": x, "y": y, "channel": CHANNELS[channel],
        "silhouetteDistanceChebyshevPx": int(distance[y, x]),
        "vector": {"xy": [float(value) for value in vector_values], "uint32Hex": [bits(value) for value in vector_values]},
        "previousSampleCoordinate": {"qx": row["qx"], "qy": row["qy"], "fractional": list(row["fractional"])},
        "tapCoordinates": [list(value) for value in row["coordinates"]], "weights": list(row["weights"]), "tapValues": list(row["taps"]), "currentCenter": row["center"],
        "signedTapContributions": list(row["contributions"]), "preCastReconstructed": row["preCast"], "finalFloat32Reconstructed": float(row["final"]), "finalFloat32Bits": bits(row["final"]),
        "formalFloat32Reconstructed": float(formal), "formalFloat32Bits": bits(formal), "signedFormalError": float(formal) - row["center"], "absoluteFormalError": actual,
        "float32Ulp": row["ulp"], "registeredChannelRiskBound": row["risk"], "boundMinusActual": row["risk"] - actual,
    }


def validate_result(document: dict, expected: dict) -> bool:
    if not self_ok(document, "evidenceHash"):
        return False
    for key in ("experimentId", "verdict", "passed", "checks", "aggregate"):
        if document.get(key) != expected.get(key):
            return False
    if len(document.get("primaryCells", [])) != len(expected["primaryCells"]):
        return False
    for actual_cell, expected_cell in zip(document["primaryCells"], expected["primaryCells"]):
        for key in ("fixtureId", "radius", "summary", "tiedMaximumRecords", "topActualErrorRecords", "recordsHash"):
            if actual_cell.get(key) != expected_cell.get(key):
                return False
    return True


def mutate(document: dict, index: int) -> dict:
    altered = copy.deepcopy(document)
    cell = altered["primaryCells"][index % len(altered["primaryCells"])]
    mode = index % 9
    if mode == 0: altered["verdict"] = "MUTATED"
    elif mode == 1: altered["aggregate"]["underboundRgbSamples"] += 1
    elif mode == 2: cell["summary"]["maximumActualError"] += 1e-9
    elif mode == 3: cell["summary"]["tiedMaximumCount"] += 1
    elif mode == 4: cell["tiedMaximumRecords"][0]["x"] += 1
    elif mode == 5: cell["tiedMaximumRecords"][0]["weights"][0] += 1e-12
    elif mode == 6: cell["topActualErrorRecords"][0]["registeredChannelRiskBound"] += 1e-12
    elif mode == 7: cell["recordsHash"] = "0" * 64
    else: altered["checks"][0]["passed"] = not altered["checks"][0]["passed"]
    altered["evidenceHash"] = canon({key: value for key, value in altered.items() if key != "evidenceHash"})
    return altered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D12.6 audit")
    if sha_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("spec identity mismatch")
    spec = json.loads(args.spec.read_text())
    result = json.loads(args.result.read_text())
    preflight = json.loads(args.preflight.read_text())
    tool_hashes = {path: sha_file(Path(path)) for path in spec["formalToolPaths"]}
    if not self_ok(preflight, "preflightHash") or preflight.get("status") != "ACCEPTED" or preflight.get("toolHashes") != tool_hashes:
        raise RuntimeError("preflight or frozen tool identity mismatch")
    parent_spec = json.loads(Path(spec["parents"]["d12_5Spec"]["uri"]).read_text())
    contracts = {row["id"]: row for row in parent_spec["fixtures"]}
    expected_cells = []
    total_underbounds = 0
    maximum_actual = 0.0
    maximum_slack = 0.0
    for actual_cell in result["primaryCells"]:
        fixture = actual_cell["fixtureId"]
        radius = int(actual_cell["radius"])
        width, height = contracts[fixture]["resolution"]
        registered = {float(row["passIndex"]) for row in contracts[fixture]["owners"]}
        adapter = args.root / "adapters" / fixture / "R1" / "arrays"
        consumer = args.root / "consumers" / "python" / fixture / "R1" / "arrays"
        arrays = {
            "previous": array(adapter / "previous.rgba32", (height, width, 4)),
            "current": array(adapter / "current.rgba32", (height, width, 4)),
            "owner": array(adapter / "current-owner.f32", (height, width)),
            "vector": array(adapter / "vector.xy32", (height, width, 2)),
        }
        reconstructed = array(consumer / f"radius{radius}-reconstructed.rgba32", (height, width, 4))
        interior = array(consumer / f"radius{radius}-interior.u8", (height, width), "u1").astype(bool)
        distance = distance_map(arrays["owner"], arrays["current"][..., 3], registered)
        rows = []
        underbounds = 0
        slack = 0.0
        ratios = []
        pixel_actual, pixel_risk = [], []
        thresholds = {"production": {"threshold": 1 / 524288, "actualPositive": 0, "selected": 0, "truePositive": 0}, "halfGate": {"threshold": 1 / 1048576, "actualPositive": 0, "selected": 0, "truePositive": 0}}
        for y, x in np.argwhere(interior):
            actual_channels, risk_channels = [], []
            for channel in range(3):
                record = expected_record(fixture, radius, arrays, reconstructed, distance, int(x), int(y), channel)
                actual, risk = record["absoluteFormalError"], record["registeredChannelRiskBound"]
                rows.append((actual, int(y), int(x), channel, record)); actual_channels.append(actual); risk_channels.append(risk)
                underbounds += int(actual > risk); slack = max(slack, risk - actual)
                if actual > 0: ratios.append(risk / actual)
            ap, rp = max(actual_channels), max(risk_channels); pixel_actual.append(ap); pixel_risk.append(rp)
            for row in thresholds.values():
                positive, selected = ap > row["threshold"], rp > row["threshold"]
                row["actualPositive"] += int(positive); row["selected"] += int(selected); row["truePositive"] += int(positive and selected)
        maximum = max(row[0] for row in rows)
        tied = [row[4] for row in rows if row[0] == maximum]
        top = [row[4] for row in sorted(rows, key=lambda row: (-row[0], row[1], row[2], row[3]))[:spec["frozenInputs"]["topSamplesPerFixtureRadius"]]]
        for row in thresholds.values():
            row["recall"] = row["truePositive"] / row["actualPositive"] if row["actualPositive"] else 1.0
            row["selectedPixelFraction"] = row["selected"] / len(pixel_actual)
        # Report-only statistics are checked directly against the formal result below;
        # the audit's independent duty is exact record and aggregate reproduction.
        expected_cell = copy.deepcopy(actual_cell)
        expected_cell["tiedMaximumRecords"] = tied
        expected_cell["topActualErrorRecords"] = top
        expected_cell["recordsHash"] = canon({"tiedMaximumRecords": tied, "topActualErrorRecords": top})
        expected_cell["summary"]["interiorPixels"] = int(interior.sum())
        expected_cell["summary"]["rgbSamples"] = len(rows)
        expected_cell["summary"]["maximumActualError"] = maximum
        expected_cell["summary"]["tiedMaximumCount"] = len(tied)
        expected_cell["summary"]["underboundRgbSamples"] = underbounds
        expected_cell["summary"]["maximumBoundSlack"] = slack
        expected_cell["summary"]["positiveActualRatio"] = distribution(ratios)
        expected_cell["summary"]["pixelRiskActualSpearman"] = spearman(pixel_risk, pixel_actual)
        expected_cell["summary"]["thresholdDiagnostics"] = thresholds
        expected_cells.append(expected_cell)
        total_underbounds += underbounds; maximum_actual = max(maximum_actual, maximum); maximum_slack = max(maximum_slack, slack)
    expected = copy.deepcopy(result)
    expected["primaryCells"] = expected_cells
    expected["aggregate"] = {"cellCount": len(expected_cells), "rgbSamples": sum(cell["summary"]["rgbSamples"] for cell in expected_cells), "underboundRgbSamples": total_underbounds, "maximumActualError": maximum_actual, "maximumBoundSlack": maximum_slack}
    base_pass = validate_result(result, expected) and result["analyzerPid"] != os.getpid() and result["preflight"]["sha256"] == sha_file(args.preflight)
    attacks = []
    for index in range(18):
        rejected = not validate_result(mutate(result, index), expected)
        attacks.append({"id": f"M{index + 1:02d}", "passed": rejected})
    passed = base_pass and all(row["passed"] for row in attacks)
    body = {
        "schemaVersion": "bfs.blenderStaticInteriorRiskLocalizationAudit.v0.1", "experimentId": spec["experimentId"], "auditPid": os.getpid(),
        "analyzerPid": result["analyzerPid"], "passed": passed, "baseReplayPassed": base_pass,
        "cellRecordsHash": canon(expected_cells), "aggregate": expected["aggregate"], "mutationAttacks": attacks,
        "mutationAttackPassed": sum(row["passed"] for row in attacks), "mutationAttackTotal": len(attacks),
        "operationCounts": {"auditProcesses": 1, "blenderProcesses": 0, "blenderRenders": 0, "modelCalls": 0, "networkCalls": 0},
    }
    document = {**body, "auditHash": canon(body)}
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D126_AUDIT_{'OK' if passed else 'FAILED'} attacks={document['mutationAttackPassed']}/{document['mutationAttackTotal']}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
