#!/usr/bin/env python3
"""Formal read-only arithmetic localizer for B52-D12.6."""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "9ae043172e3d126d590b6be7942de759a503eee3c76cf4b96062e92285691fe5"
CHANNELS = ("R", "G", "B")
SOURCE_FILES = {
    "previousRgba": ("previous.rgba32", 4),
    "currentRgba": ("current.rgba32", 4),
    "previousOwner": ("previous-owner.f32", 1),
    "currentOwner": ("current-owner.f32", 1),
    "vector": ("vector.xy32", 2),
    "vectorNext": ("vector-next.xy32", 2),
}
CONSUMER_FILES = {
    2: {
        "reconstructed": ("radius2-reconstructed.rgba32", 4, "<f4"),
        "interior": ("radius2-interior.u8", 1, "u1"),
        "boundary": ("radius2-boundary.u8", 1, "u1"),
    },
    3: {
        "reconstructed": ("radius3-reconstructed.rgba32", 4, "<f4"),
        "interior": ("radius3-interior.u8", 1, "u1"),
        "boundary": ("radius3-boundary.u8", 1, "u1"),
    },
}
PRODUCTION_GATE = 1.0 / 524288.0
HALF_GATE = 1.0 / 1048576.0


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return sha256_bytes(payload)


def self_hash_ok(document: dict, field: str) -> bool:
    return document.get(field) == canonical_hash({key: value for key, value in document.items() if key != field})


def normalized_envelope(value: object) -> object:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, float)):
        return {"$f64be": struct.pack(">d", float(value)).hex()}
    if isinstance(value, list):
        return [normalized_envelope(item) for item in value]
    if isinstance(value, dict):
        return {key: normalized_envelope(value[key]) for key in sorted(value)}
    raise TypeError(type(value))


def f32_bits(value: np.float32) -> str:
    return f"{struct.unpack('<I', struct.pack('<f', float(value)))[0]:08x}"


def load_array(path: Path, shape: tuple[int, ...], dtype: str = "<f4") -> tuple[np.ndarray, bytes]:
    payload = path.read_bytes()
    expected = math.prod(shape) * np.dtype(dtype).itemsize
    if len(payload) != expected:
        raise RuntimeError(f"array length mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy(), payload


def load_native_report(path: Path) -> dict:
    report = json.loads(path.read_text())
    if not self_hash_ok(report, "reportHash"):
        raise RuntimeError(f"native report hash mismatch: {path}")
    return report


def owner_distance(owner: np.ndarray, alpha: np.ndarray, registered: set[float]) -> np.ndarray:
    height, width = owner.shape
    distance = np.zeros((height, width), dtype=np.int16)
    valid = np.isin(owner, list(registered)) & (alpha > np.float32(0.999))
    queue: deque[tuple[int, int]] = deque()
    for y, x in np.argwhere(valid):
        value = owner[y, x]
        edge = x == 0 or y == 0 or x == width - 1 or y == height - 1
        if not edge:
            edge = any(
                not valid[ty, tx] or owner[ty, tx] != value
                for ty in range(y - 1, y + 2)
                for tx in range(x - 1, x + 2)
            )
        if edge:
            distance[y, x] = 1
            queue.append((int(y), int(x)))
    while queue:
        y, x = queue.popleft()
        next_distance = distance[y, x] + 1
        value = owner[y, x]
        for ty in range(max(0, y - 1), min(height, y + 2)):
            for tx in range(max(0, x - 1), min(width, x + 2)):
                if valid[ty, tx] and owner[ty, tx] == value and distance[ty, tx] == 0:
                    distance[ty, tx] = next_distance
                    queue.append((ty, tx))
    return distance


def bilinear_terms(previous: np.ndarray, current: np.ndarray, vector: np.ndarray, x: int, y: int, channel: int) -> dict:
    vx = float(vector[y, x, 0])
    vy = float(vector[y, x, 1])
    qx, qy = x + vx, y - vy
    x0, y0 = math.floor(qx), math.floor(qy)
    x1, y1 = x0 + 1, y0 + 1
    fx, fy = qx - x0, qy - y0
    weights = ((1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy)
    coordinates = ((x0, y0), (x1, y0), (x0, y1), (x1, y1))
    taps = tuple(float(previous[ty, tx, channel]) for tx, ty in coordinates)
    center = float(current[y, x, channel])
    contributions = tuple(weight * (tap - center) for weight, tap in zip(weights, taps))
    pre_cast = (((taps[0] * weights[0]) + (taps[1] * weights[1])) + (taps[2] * weights[2])) + (taps[3] * weights[3])
    final = np.float32(pre_cast)
    ulp = abs(float(np.spacing(final)))
    bound = sum(abs(weight) * abs(tap - center) for weight, tap in zip(weights, taps)) + ulp
    return {
        "qx": qx,
        "qy": qy,
        "fractional": (fx, fy),
        "coordinates": coordinates,
        "weights": weights,
        "taps": taps,
        "center": center,
        "contributions": contributions,
        "preCast": pre_cast,
        "final": final,
        "ulp": ulp,
        "bound": bound,
    }


def reconstruct(arrays: dict[str, np.ndarray], registered: set[float], radius: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    previous = arrays["previousRgba"]
    current = arrays["currentRgba"]
    previous_owner = arrays["previousOwner"]
    current_owner = arrays["currentOwner"]
    vector = arrays["vector"]
    height, width = current_owner.shape
    reconstructed = current.copy()
    interior = np.zeros((height, width), dtype=np.uint8)
    boundary = np.zeros((height, width), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            owner = current_owner[y, x]
            if float(owner) not in registered or current[y, x, 3] <= np.float32(0.999):
                continue
            qx = x + float(vector[y, x, 0])
            qy = y - float(vector[y, x, 1])
            x0, y0 = math.floor(qx), math.floor(qy)
            coords = ((x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1))
            neighborhood_ok = x >= radius and y >= radius and x < width - radius and y < height - radius
            if neighborhood_ok:
                neighborhood_ok = all(
                    current_owner[ty, tx] == owner and current[ty, tx, 3] > np.float32(0.999)
                    for ty in range(y - radius, y + radius + 1)
                    for tx in range(x - radius, x + radius + 1)
                )
            taps_ok = all(0 <= tx < width and 0 <= ty < height for tx, ty in coords)
            if taps_ok:
                taps_ok = all(
                    previous_owner[ty, tx] == owner and previous[ty, tx, 3] > np.float32(0.999)
                    for tx, ty in coords
                )
            if not neighborhood_ok or not taps_ok:
                boundary[y, x] = 1
                continue
            for channel in range(4):
                reconstructed[y, x, channel] = bilinear_terms(previous, current, vector, x, y, channel)["final"]
            interior[y, x] = 1
    return reconstructed, interior, boundary


def tied_maximum_records(
    fixture: str,
    radius: int,
    arrays: dict[str, np.ndarray],
    reconstructed: np.ndarray,
    interior: np.ndarray,
    distance: np.ndarray,
    top_count: int,
) -> tuple[list[dict], list[dict], dict]:
    rows: list[tuple[float, float, int, int, int, dict]] = []
    underbounds = 0
    maximum_slack = 0.0
    ratios: list[float] = []
    pixel_actual: list[float] = []
    pixel_risk: list[float] = []
    threshold_rows = {
        "production": {"threshold": PRODUCTION_GATE, "actualPositive": 0, "selected": 0, "truePositive": 0},
        "halfGate": {"threshold": HALF_GATE, "actualPositive": 0, "selected": 0, "truePositive": 0},
    }
    for y, x in np.argwhere(interior.astype(bool)):
        channel_actual = []
        channel_risk = []
        for channel in range(3):
            terms = bilinear_terms(arrays["previousRgba"], arrays["currentRgba"], arrays["vector"], int(x), int(y), channel)
            actual = abs(float(reconstructed[y, x, channel]) - float(arrays["currentRgba"][y, x, channel]))
            risk = float(terms["bound"])
            if actual > risk:
                underbounds += 1
            maximum_slack = max(maximum_slack, risk - actual)
            if actual > 0.0:
                ratios.append(risk / actual)
            channel_actual.append(actual)
            channel_risk.append(risk)
            rows.append((actual, risk, int(y), int(x), channel, terms))
        actual_pixel = max(channel_actual)
        risk_pixel = max(channel_risk)
        pixel_actual.append(actual_pixel)
        pixel_risk.append(risk_pixel)
        for threshold in threshold_rows.values():
            actual_positive = actual_pixel > threshold["threshold"]
            selected = risk_pixel > threshold["threshold"]
            threshold["actualPositive"] += int(actual_positive)
            threshold["selected"] += int(selected)
            threshold["truePositive"] += int(actual_positive and selected)
    if not rows:
        raise RuntimeError(f"empty interior: {fixture}/radius{radius}")
    maximum = max(row[0] for row in rows)
    tied = [row for row in rows if row[0] == maximum]
    top = sorted(rows, key=lambda row: (-row[0], row[2], row[3], row[4]))[:top_count]

    def record(row: tuple[float, float, int, int, int, dict]) -> dict:
        actual, risk, y, x, channel, terms = row
        owner = int(arrays["currentOwner"][y, x])
        final = np.float32(terms["final"])
        formal = np.float32(reconstructed[y, x, channel])
        vector_values = [np.float32(arrays["vector"][y, x, index]) for index in range(2)]
        return {
            "fixtureId": fixture,
            "radius": radius,
            "ownerPassIndex": owner,
            "x": x,
            "y": y,
            "channel": CHANNELS[channel],
            "silhouetteDistanceChebyshevPx": int(distance[y, x]),
            "vector": {"xy": [float(value) for value in vector_values], "uint32Hex": [f32_bits(value) for value in vector_values]},
            "previousSampleCoordinate": {"qx": terms["qx"], "qy": terms["qy"], "fractional": list(terms["fractional"])},
            "tapCoordinates": [list(value) for value in terms["coordinates"]],
            "weights": list(terms["weights"]),
            "tapValues": list(terms["taps"]),
            "currentCenter": terms["center"],
            "signedTapContributions": list(terms["contributions"]),
            "preCastReconstructed": terms["preCast"],
            "finalFloat32Reconstructed": float(final),
            "finalFloat32Bits": f32_bits(final),
            "formalFloat32Reconstructed": float(formal),
            "formalFloat32Bits": f32_bits(formal),
            "signedFormalError": float(formal) - terms["center"],
            "absoluteFormalError": actual,
            "float32Ulp": terms["ulp"],
            "registeredChannelRiskBound": risk,
            "boundMinusActual": risk - actual,
        }

    for threshold in threshold_rows.values():
        threshold["recall"] = threshold["truePositive"] / threshold["actualPositive"] if threshold["actualPositive"] else 1.0
        threshold["selectedPixelFraction"] = threshold["selected"] / len(pixel_actual)
    correlation = spearman(pixel_risk, pixel_actual)
    summary = {
        "interiorPixels": int(interior.sum()),
        "rgbSamples": len(rows),
        "maximumActualError": maximum,
        "tiedMaximumCount": len(tied),
        "underboundRgbSamples": underbounds,
        "maximumBoundSlack": maximum_slack,
        "positiveActualRatio": distribution(ratios),
        "pixelRiskActualSpearman": correlation,
        "thresholdDiagnostics": threshold_rows,
    }
    return [record(row) for row in tied], [record(row) for row in top], summary


def distribution(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "minimum": None, "p50": None, "p95": None, "maximum": None}
    ordered = sorted(values)
    pick = lambda fraction: ordered[min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction)))]
    return {"count": len(values), "minimum": ordered[0], "p50": pick(0.5), "p95": pick(0.95), "maximum": ordered[-1]}


def average_ranks(values: list[float]) -> np.ndarray:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = np.empty(len(values), dtype=np.float64)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        rank = (cursor + end - 1) / 2.0 + 1.0
        for index in order[cursor:end]:
            ranks[index] = rank
        cursor = end
    return ranks


def spearman(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2:
        return None
    a, b = average_ranks(left), average_ranks(right)
    a -= a.mean()
    b -= b.mean()
    denominator = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
    return float(np.dot(a, b) / denominator) if denominator else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D12.6 result")
    spec = json.loads(args.spec.read_text())
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("D12.6 spec identity mismatch")
    if sha256_file(Path(sys.executable)) != spec["runtime"]["python"]["sha256"]:
        raise RuntimeError("D12.6 Python identity mismatch")
    preflight = json.loads(args.preflight.read_text())
    if not self_hash_ok(preflight, "preflightHash") or preflight.get("status") != "ACCEPTED":
        raise RuntimeError("D12.6 preflight identity or status mismatch")
    current_tool_hashes = {path: sha256_file(Path(path)) for path in spec["formalToolPaths"]}
    if preflight.get("toolHashes") != current_tool_hashes:
        raise RuntimeError("D12.6 frozen tool identity mismatch")

    parent_checks: dict[str, bool] = {}
    parent_documents: dict[str, dict] = {}
    for name, record in spec["parents"].items():
        path = Path(record["uri"])
        parent_checks[f"{name}FileHash"] = sha256_file(path) == record["sha256"]
        if path.suffix == ".json":
            parent_documents[name] = json.loads(path.read_text())
    parent_checks["d12_5ResultInternalHash"] = self_hash_ok(parent_documents["d12_5Result"], "evidenceHash") and parent_documents["d12_5Result"]["evidenceHash"] == spec["parents"]["d12_5Result"]["evidenceHash"]
    parent_checks["d12_5ReceiptInternalHash"] = self_hash_ok(parent_documents["d12_5Receipt"], "receiptHash") and parent_documents["d12_5Receipt"]["receiptHash"] == spec["parents"]["d12_5Receipt"]["receiptHash"]
    parent_checks["d12_5ExecutionInternalHash"] = self_hash_ok(parent_documents["d12_5Execution"], "executionHash") and parent_documents["d12_5Execution"]["executionHash"] == spec["parents"]["d12_5Execution"]["executionHash"]
    parent_checks["d12_5Verdict"] = parent_documents["d12_5Result"]["verdict"] == spec["parents"]["d12_5Result"]["verdict"]
    parent_checks["invalidD12_6Status"] = parent_documents["invalidD12_6Run"]["status"] == spec["parents"]["invalidD12_6Run"]["status"] and parent_documents["invalidD12_6Run"]["resultFileWritten"] is False and parent_documents["invalidD12_6Run"]["measurementInspected"] is False
    if not all(parent_checks.values()):
        raise RuntimeError(f"parent identity failure: {parent_checks}")

    parent_spec = json.loads(Path(spec["parents"]["d12_5Spec"]["uri"]).read_text())
    parent_results = parent_documents["d12_5Result"]
    fixture_contracts = {row["id"]: row for row in parent_spec["fixtures"]}
    top_count = spec["frozenInputs"]["topSamplesPerFixtureRadius"]
    primary_cells = []
    repeat_identity: dict[str, dict] = {}
    byte_replay_checks: dict[str, bool] = {}
    report_binding_checks: dict[str, bool] = {}

    for fixture_id in spec["frozenInputs"]["fixtures"]:
        fixture = fixture_contracts[fixture_id]
        width, height = fixture["resolution"]
        registered = {float(row["passIndex"]) for row in fixture["owners"]}
        repeat_payloads: dict[int, dict[str, bytes]] = {}
        repeat_sources: dict[int, dict[str, bytes]] = {}
        primary_material: tuple[dict[str, np.ndarray], dict[int, dict[str, np.ndarray]]] | None = None
        for repeat in (1, 2):
            source_dir = args.root / "sources" / fixture_id / f"R{repeat}"
            for frame in (0, 1):
                source_report_path = source_dir / f"frame-{frame}" / "report.json"
                source_report = load_native_report(source_report_path)
                source_exr = source_dir / f"frame-{frame}" / "source.exr"
                report_binding_checks[f"{fixture_id}/R{repeat}/source/frame{frame}"] = source_report["output"]["sha256"] == sha256_file(source_exr)
            adapter_dir = args.root / "adapters" / fixture_id / f"R{repeat}"
            adapter_report_path = adapter_dir / "report.json"
            adapter_report = load_native_report(adapter_report_path)
            arrays: dict[str, np.ndarray] = {}
            source_payloads: dict[str, bytes] = {}
            for name, (filename, channels) in SOURCE_FILES.items():
                shape = (height, width, channels) if channels > 1 else (height, width)
                path = adapter_dir / "arrays" / filename
                array, payload = load_array(path, shape)
                arrays[name] = array
                source_payloads[name] = payload
                report_binding_checks[f"{fixture_id}/R{repeat}/adapter/{name}"] = sha256_bytes(payload) == adapter_report["arrays"][name]["sha256"]
                report_binding_checks[f"{fixture_id}/R{repeat}/parentSource/{name}"] = sha256_bytes(payload) == parent_results["identities"]["source"][fixture_id][str(repeat)][name]
            repeat_sources[repeat] = source_payloads

            producer_outputs: dict[str, dict[int, dict[str, np.ndarray | bytes]]] = {}
            for producer in ("python", "node"):
                consumer_dir = args.root / "consumers" / producer / fixture_id / f"R{repeat}"
                consumer_report_path = consumer_dir / "report.json"
                consumer_report = json.loads(consumer_report_path.read_text())
                report_binding_checks[f"{fixture_id}/R{repeat}/{producer}/adapter"] = consumer_report["adapter"]["sha256"] == sha256_file(adapter_report_path) and consumer_report["adapter"]["reportHash"] == adapter_report["reportHash"]
                envelope_dir = args.root / "envelopes" / producer / fixture_id / f"R{repeat}"
                encoded = json.dumps(normalized_envelope(consumer_report), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
                report_binding_checks[f"{fixture_id}/R{repeat}/{producer}/pythonEnvelope"] = encoded == (envelope_dir / "report.python-envelope.json").read_bytes()
                report_binding_checks[f"{fixture_id}/R{repeat}/{producer}/nodeEnvelope"] = encoded == (envelope_dir / "report.node-envelope.json").read_bytes()
                radius_outputs: dict[int, dict[str, np.ndarray | bytes]] = {}
                for radius in (2, 3):
                    outputs: dict[str, np.ndarray | bytes] = {}
                    for name, (filename, channels, dtype) in CONSUMER_FILES[radius].items():
                        shape = (height, width, channels) if channels > 1 else (height, width)
                        path = consumer_dir / "arrays" / filename
                        array, payload = load_array(path, shape, dtype)
                        outputs[name] = array
                        outputs[f"{name}Bytes"] = payload
                        report_key = f"radius{radius}{name.title()}"
                        report_binding_checks[f"{fixture_id}/R{repeat}/{producer}/r{radius}/{name}"] = sha256_bytes(payload) == consumer_report["arrays"][report_key]["sha256"]
                        report_binding_checks[f"{fixture_id}/R{repeat}/parentConsumer/r{radius}/{name}"] = sha256_bytes(payload) == parent_results["identities"]["consumer"][fixture_id][str(repeat)][str(radius)][name]
                    radius_outputs[radius] = outputs
                producer_outputs[producer] = radius_outputs
            repeat_payloads[repeat] = {
                f"r{radius}/{name}": producer_outputs["python"][radius][f"{name}Bytes"]
                for radius in (2, 3) for name in CONSUMER_FILES[radius]
            }
            for radius in (2, 3):
                for name in CONSUMER_FILES[radius]:
                    report_binding_checks[f"{fixture_id}/R{repeat}/dual/r{radius}/{name}"] = producer_outputs["python"][radius][f"{name}Bytes"] == producer_outputs["node"][radius][f"{name}Bytes"]
                replay_reconstructed, replay_interior, replay_boundary = reconstruct(arrays, registered, radius)
                formal = producer_outputs["python"][radius]
                byte_replay_checks[f"{fixture_id}/R{repeat}/r{radius}/reconstructed"] = replay_reconstructed.tobytes() == formal["reconstructedBytes"]
                byte_replay_checks[f"{fixture_id}/R{repeat}/r{radius}/interior"] = replay_interior.tobytes() == formal["interiorBytes"]
                byte_replay_checks[f"{fixture_id}/R{repeat}/r{radius}/boundary"] = replay_boundary.tobytes() == formal["boundaryBytes"]
            if repeat == spec["frozenInputs"]["repeatForPrimaryAnalysis"]:
                primary_material = (arrays, {radius: {name: producer_outputs["python"][radius][name] for name in ("reconstructed", "interior", "boundary")} for radius in (2, 3)})
        repeat_identity[fixture_id] = {
            "sourceArrays": all(repeat_sources[1][name] == repeat_sources[2][name] for name in SOURCE_FILES),
            "consumerPayloads": all(repeat_payloads[1][name] == repeat_payloads[2][name] for name in repeat_payloads[1]),
        }
        if primary_material is None:
            raise RuntimeError("primary material absent")
        arrays, radius_outputs = primary_material
        distance = owner_distance(arrays["currentOwner"], arrays["currentRgba"][..., 3], registered)
        for radius in (2, 3):
            output = radius_outputs[radius]
            tied, top, summary = tied_maximum_records(fixture_id, radius, arrays, output["reconstructed"], output["interior"], distance, top_count)
            primary_cells.append({
                "fixtureId": fixture_id,
                "radius": radius,
                "summary": summary,
                "tiedMaximumRecords": tied,
                "topActualErrorRecords": top,
                "recordsHash": canonical_hash({"tiedMaximumRecords": tied, "topActualErrorRecords": top}),
            })

    checks = [
        {"id": "PREFLIGHT_AND_TOOL_IDENTITY", "passed": True},
        {"id": "PARENT_IDENTITIES", "passed": all(parent_checks.values())},
        {"id": "REPORT_PAYLOAD_BINDINGS", "passed": all(report_binding_checks.values())},
        {"id": "REPEAT_IDENTITY", "passed": all(all(row.values()) for row in repeat_identity.values())},
        {"id": "FLOAT32_BYTE_REPLAY", "passed": all(byte_replay_checks.values())},
        {"id": "MAXIMUM_TOTALITY", "passed": all(cell["summary"]["tiedMaximumCount"] == len(cell["tiedMaximumRecords"]) and len(cell["tiedMaximumRecords"]) >= 1 for cell in primary_cells)},
        {"id": "LOCAL_RISK_BOUND_CONSERVATIVE", "passed": sum(cell["summary"]["underboundRgbSamples"] for cell in primary_cells) == 0},
        {"id": "MODEL_NETWORK_ZERO", "passed": True},
    ]
    passed = all(row["passed"] for row in checks)
    body = {
        "schemaVersion": "bfs.blenderStaticInteriorRiskLocalizationResult.v0.1",
        "experimentId": spec["experimentId"],
        "analyzerPid": os.getpid(),
        "verdict": spec["success"]["verdict"] if passed else spec["success"]["failureVerdict"],
        "passed": passed,
        "checks": checks,
        "parentChecks": parent_checks,
        "preflight": {"sha256": sha256_file(args.preflight), "preflightHash": preflight["preflightHash"], "toolHashes": current_tool_hashes},
        "reportBindingCheckCount": len(report_binding_checks),
        "reportBindingChecksHash": canonical_hash(report_binding_checks),
        "byteReplayCheckCount": len(byte_replay_checks),
        "byteReplayChecksHash": canonical_hash(byte_replay_checks),
        "repeatIdentity": repeat_identity,
        "primaryCells": primary_cells,
        "aggregate": {
            "cellCount": len(primary_cells),
            "rgbSamples": sum(cell["summary"]["rgbSamples"] for cell in primary_cells),
            "underboundRgbSamples": sum(cell["summary"]["underboundRgbSamples"] for cell in primary_cells),
            "maximumActualError": max(cell["summary"]["maximumActualError"] for cell in primary_cells),
            "maximumBoundSlack": max(cell["summary"]["maximumBoundSlack"] for cell in primary_cells),
        },
        "operationCounts": {"localizerProcesses": 1, "blenderProcesses": 0, "blenderRenders": 0, "modelCalls": 0, "networkCalls": 0},
        "nonClaims": spec["nonClaims"],
    }
    result = {**body, "evidenceHash": canonical_hash(body)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D126_LOCALIZER_OK verdict={result['verdict']} cells={len(primary_cells)} underbounds={result['aggregate']['underboundRgbSamples']}")


if __name__ == "__main__":
    main()
