#!/usr/bin/env python3
"""Read-only per-pixel localization of the B52-D12.3 zero-headroom result."""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "8df3c666e4409a243b1611131e5927b757fcd47453511b732fc26e579f526326"
ADAPTER_FILES = {
    "previousRgba": ("previous.rgba32", 4),
    "currentRgba": ("current.rgba32", 4),
    "previousOwner": ("previous-owner.f32", 1),
    "currentOwner": ("current-owner.f32", 1),
    "vector": ("vector.xy32", 2),
    "vectorNext": ("vector-next.xy32", 2),
}
CONSUMER_FILES = {
    "reconstructed": ("reconstructed.rgba32", 4, "<f4"),
    "valid": ("valid.u8", 1, "u1"),
    "boundary": ("boundary.u8", 1, "u1"),
}
CHANNELS = ("R", "G", "B")


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
    return hashlib.sha256(payload).hexdigest()


def self_hash_ok(document: dict, field: str) -> bool:
    body = {key: value for key, value in document.items() if key != field}
    return document.get(field) == canonical_hash(body)


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


def load_array(path: Path, shape: tuple[int, ...], dtype: str) -> tuple[np.ndarray, bytes]:
    payload = path.read_bytes()
    expected = math.prod(shape) * np.dtype(dtype).itemsize
    if len(payload) != expected:
        raise RuntimeError(f"array length mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy(), payload


def depth_part(path: Path, width: int, height: int) -> np.ndarray:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        name = str(image.spec().getattribute("oiio:subimagename") or "")
        if name.endswith(".Depth"):
            pixels = np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4")
            if list(pixels.shape) != [height, width, 1]:
                raise RuntimeError(f"Depth shape mismatch: {path}")
            return np.ascontiguousarray(pixels[..., 0])
    raise RuntimeError(f"Depth absent: {path}")


def owner_distance_map(owner: np.ndarray, alpha: np.ndarray, owner_id: int) -> np.ndarray:
    height, width = owner.shape
    inside = np.zeros((height + 2, width + 2), dtype=bool)
    inside[1:-1, 1:-1] = (owner == np.float32(owner_id)) & (alpha > np.float32(0.999))
    distance = np.full(inside.shape, -1, dtype=np.int32)
    queue: deque[tuple[int, int]] = deque()
    for y, x in np.argwhere(~inside):
        distance[y, x] = 0
        queue.append((int(y), int(x)))
    while queue:
        y, x = queue.popleft()
        next_distance = distance[y, x] + 1
        for ty in range(max(0, y - 1), min(height + 2, y + 2)):
            for tx in range(max(0, x - 1), min(width + 2, x + 2)):
                if inside[ty, tx] and distance[ty, tx] < 0:
                    distance[ty, tx] = next_distance
                    queue.append((ty, tx))
    return distance[1:-1, 1:-1]


def depth_laplacian(depth: np.ndarray, owner: np.ndarray, x: int, y: int) -> float | None:
    height, width = owner.shape
    if x <= 0 or y <= 0 or x >= width - 1 or y >= height - 1:
        return None
    center_owner = owner[y, x]
    neighbors = ((y, x - 1), (y, x + 1), (y - 1, x), (y + 1, x))
    if any(owner[ty, tx] != center_owner for ty, tx in neighbors):
        return None
    values = [float(depth[ty, tx]) for ty, tx in neighbors]
    center = float(depth[y, x])
    if not all(math.isfinite(value) for value in values + [center]):
        return None
    return abs(sum(values) - 4.0 * center)


def vector_record(vector: np.ndarray, x: int, y: int) -> dict:
    values = [np.float32(vector[y, x, index]) for index in range(2)]
    return {
        "xy": [float(value) for value in values],
        "uint32Hex": [f"{int(value.view(np.uint32)):08x}" for value in values],
        "ratioTo2PowMinus17": [float(value) / (2.0 ** -17) for value in values],
    }


def sample_record(arrays: dict[str, np.ndarray], depth: np.ndarray, distance_maps: dict[int, np.ndarray], x: int, y: int, channel: int, threshold: float) -> dict:
    previous = arrays["previousRgba"]
    current = arrays["currentRgba"]
    reconstructed = arrays["reconstructed"]
    vector = arrays["vector"]
    owner = arrays["currentOwner"]
    vx, vy = float(vector[y, x, 0]), float(vector[y, x, 1])
    qx, qy = x + vx, y - vy
    x0, y0 = math.floor(qx), math.floor(qy)
    x1, y1 = x0 + 1, y0 + 1
    fx, fy = qx - x0, qy - y0
    weights = ((1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy)
    coords = ((x0, y0), (x1, y0), (x0, y1), (x1, y1))
    taps = [float(previous[ty, tx, channel]) for tx, ty in coords]
    center = float(current[y, x, channel])
    contributions = [weight * (tap - center) for weight, tap in zip(weights, taps)]
    pre_cast = (((taps[0] * weights[0]) + (taps[1] * weights[1])) + (taps[2] * weights[2])) + (taps[3] * weights[3])
    final = float(np.float32(pre_cast))
    signed_error = float(reconstructed[y, x, channel]) - center
    return {
        "x": x,
        "y": y,
        "channel": CHANNELS[channel],
        "ownerPassIndex": int(owner[y, x]),
        "silhouetteDistanceChebyshevPx": int(distance_maps[int(owner[y, x])][y, x]),
        "vector": vector_record(vector, x, y),
        "sampleCoordinate": {"qx": qx, "qy": qy, "fractional": [fx, fy]},
        "tapCoordinates": [[tx, ty] for tx, ty in coords],
        "weights": list(weights),
        "tapValues": taps,
        "currentCenter": center,
        "preCastReconstructed": pre_cast,
        "finalFloat32Reconstructed": final,
        "formalFloat32Reconstructed": float(reconstructed[y, x, channel]),
        "signedTapContributions": contributions,
        "contributionSum": sum(contributions),
        "localTapRange": max(taps) - min(taps),
        "signedError": signed_error,
        "absoluteError": abs(signed_error),
        "absoluteErrorGateFraction": abs(signed_error) / threshold,
        "depthPlanarityLaplacian": depth_laplacian(depth, owner, x, y),
    }


def recompute_consumer(arrays: dict[str, np.ndarray], owners: set[np.float32]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    previous, current = arrays["previousRgba"], arrays["currentRgba"]
    current_owner, previous_owner, vector = arrays["currentOwner"], arrays["previousOwner"], arrays["vector"]
    height, width = current_owner.shape
    reconstructed = current.copy()
    valid = np.zeros((height, width), dtype=np.uint8)
    boundary = np.zeros((height, width), dtype=np.uint8)
    radius = 2
    for y in range(height):
        for x in range(width):
            owner = current_owner[y, x]
            if owner not in owners or current[y, x, 3] <= np.float32(0.999):
                continue
            vx, vy = float(vector[y, x, 0]), float(vector[y, x, 1])
            qx, qy = x + vx, y - vy
            x0, y0 = math.floor(qx), math.floor(qy)
            x1, y1 = x0 + 1, y0 + 1
            neighborhood_ok = x >= radius and y >= radius and x < width - radius and y < height - radius
            if neighborhood_ok:
                neighborhood_ok = all(
                    current_owner[ty, tx] == owner and current[ty, tx, 3] > np.float32(0.999)
                    for ty in range(y - radius, y + radius + 1)
                    for tx in range(x - radius, x + radius + 1)
                )
            taps_ok = x0 >= 0 and y0 >= 0 and x1 < width and y1 < height
            if taps_ok:
                taps_ok = all(
                    previous_owner[ty, tx] == owner and previous[ty, tx, 3] > np.float32(0.999)
                    for ty, tx in ((y0, x0), (y0, x1), (y1, x0), (y1, x1))
                )
            if not neighborhood_ok or not taps_ok:
                boundary[y, x] = 1
                continue
            fx, fy = qx - x0, qy - y0
            weights = ((1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy)
            for channel in range(4):
                values = (
                    float(previous[y0, x0, channel]), float(previous[y0, x1, channel]),
                    float(previous[y1, x0, channel]), float(previous[y1, x1, channel]),
                )
                reconstructed[y, x, channel] = np.float32(
                    (((values[0] * weights[0]) + (values[1] * weights[1])) + (values[2] * weights[2])) + (values[3] * weights[3])
                )
            valid[y, x] = 1
    return reconstructed, valid, boundary


def binned_tail(errors: list[tuple[float, int, int, int]], arrays: dict[str, np.ndarray], distance_maps: dict[int, np.ndarray], distances: list[int]) -> list[dict]:
    buckets = []
    for lower, upper in zip(distances, distances[1:] + [None]):
        selected = []
        for absolute, y, x, channel in errors:
            owner_id = int(arrays["currentOwner"][y, x])
            distance = int(distance_maps[owner_id][y, x])
            if distance >= lower and (upper is None or distance < upper):
                selected.append(absolute)
        buckets.append({
            "distanceInclusive": lower,
            "distanceExclusive": upper,
            "sampleCount": len(selected),
            "maximum": max(selected) if selected else None,
            "rmse": math.sqrt(sum(value * value for value in selected) / len(selected)) if selected else None,
        })
    return buckets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D12.4 output")
    spec = json.loads(args.spec.read_text())
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("D12.4 spec identity mismatch")
    if sha256_file(Path(sys.executable)) != spec["runtime"]["python"]["sha256"]:
        raise RuntimeError("D12.4 Python identity mismatch")

    root = args.experiment_root
    input_documents = {}
    input_checks = []
    for name, field in (("formalResults", "evidenceHash"), ("formalReceipt", "receiptHash"), ("formalExecution", "executionHash")):
        frozen = spec["frozenInputs"][name]
        path = Path(frozen["uri"])
        document = json.loads(path.read_text())
        file_ok = sha256_file(path) == frozen["sha256"]
        internal_ok = document.get(field) == frozen["internalHash"] and self_hash_ok(document, field)
        input_checks.extend([(f"{name}.file", file_ok), (f"{name}.internal", internal_ok)])
        input_documents[name] = document
    d12_spec_path = Path(spec["frozenInputs"]["d12_3Spec"]["uri"])
    input_checks.append(("d12_3Spec.file", sha256_file(d12_spec_path) == spec["frozenInputs"]["d12_3Spec"]["sha256"]))
    d12_spec = json.loads(d12_spec_path.read_text())
    formal_results = input_documents["formalResults"]
    input_checks.append(("d12_3Verdict.unchanged", formal_results.get("verdict") == spec["frozenFormalBoundary"]["d12_3Verdict"] and formal_results.get("exactZeroObservation") == spec["frozenFormalBoundary"]["d12_3ExactZeroObservation"]))
    if not all(value for _, value in input_checks):
        raise RuntimeError(f"frozen D12.3 identity failure: {[name for name, value in input_checks if not value]}")

    formal_by_cell = {row["cell"]: row for row in formal_results["measurements"]}
    fixture_reports = []
    global_errors: list[tuple[float, str, int, int, int]] = []
    lower_checks = {name: True for name in ("adapterReport", "consumerReport", "payload", "repeatPayload", "reconstructionBytes", "formalMaximum")}
    for fixture in d12_spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        repeat_payloads: dict[int, dict[str, bytes]] = {}
        primary_arrays: dict[str, np.ndarray] = {}
        primary_depth = None
        identities = {"adapterReports": {}, "consumerReports": {}, "arrays": {}}
        for repeat in (spec["analysisCells"]["primaryRepeat"], spec["analysisCells"]["identityControlRepeat"]):
            adapter_dir = root / "adapters" / fixture_id / f"R{repeat}"
            adapter_path = adapter_dir / "report.json"
            adapter = json.loads(adapter_path.read_text())
            adapter_body = {key: value for key, value in adapter.items() if key != "reportHash"}
            lower_checks["adapterReport"] &= adapter.get("reportHash") == canonical_hash(adapter_body)
            arrays: dict[str, np.ndarray] = {}
            payloads: dict[str, bytes] = {}
            for name, (filename, channels) in ADAPTER_FILES.items():
                shape = (height, width, channels) if channels > 1 else (height, width)
                path = adapter_dir / "arrays" / filename
                array, payload = load_array(path, shape, "<f4")
                lower_checks["payload"] &= sha256_bytes(payload) == adapter["arrays"][name]["sha256"]
                arrays[name], payloads[f"adapter.{name}"] = array, payload

            consumer_dir = root / "consumers" / "python" / fixture_id / f"R{repeat}"
            consumer_path = consumer_dir / "report.json"
            consumer = json.loads(consumer_path.read_text())
            lower_checks["consumerReport"] &= consumer.get("fixtureId") == fixture_id and consumer.get("repeat") == repeat
            lower_checks["consumerReport"] &= consumer.get("adapter", {}).get("sha256") == sha256_file(adapter_path)
            envelope_dir = root / "envelopes" / "python" / fixture_id / f"R{repeat}"
            py_envelope = json.loads((envelope_dir / "report.python-envelope.json").read_text())
            node_envelope = json.loads((envelope_dir / "report.node-envelope.json").read_text())
            lower_checks["consumerReport"] &= py_envelope == node_envelope == normalized_envelope(consumer)
            for name, (filename, channels, dtype) in CONSUMER_FILES.items():
                shape = (height, width, channels) if channels > 1 else (height, width)
                path = consumer_dir / "arrays" / filename
                array, payload = load_array(path, shape, dtype)
                lower_checks["payload"] &= sha256_bytes(payload) == consumer["arrays"][name]["sha256"]
                arrays[name], payloads[f"consumer.{name}"] = array, payload

            node_dir = root / "consumers" / "node" / fixture_id / f"R{repeat}" / "arrays"
            for name, (filename, _channels, _dtype) in CONSUMER_FILES.items():
                lower_checks["payload"] &= (node_dir / filename).read_bytes() == payloads[f"consumer.{name}"]
            repeat_payloads[repeat] = payloads
            identities["adapterReports"][str(repeat)] = {"sha256": sha256_file(adapter_path), "reportHash": adapter["reportHash"]}
            identities["consumerReports"][str(repeat)] = {"sha256": sha256_file(consumer_path), "envelopeSha256": sha256_bytes(json.dumps(py_envelope, sort_keys=True, separators=(",", ":")).encode())}
            identities["arrays"][str(repeat)] = {key: sha256_bytes(value) for key, value in payloads.items()}
            if repeat == spec["analysisCells"]["primaryRepeat"]:
                primary_arrays = arrays
                source_path = root / "sources" / fixture_id / f"R{repeat}" / "frame-1" / "source.exr"
                source_report_path = source_path.with_name("report.json")
                source_report = json.loads(source_report_path.read_text())
                source_body = {key: value for key, value in source_report.items() if key != "reportHash"}
                lower_checks["adapterReport"] &= source_report.get("reportHash") == canonical_hash(source_body)
                lower_checks["payload"] &= source_report.get("output", {}).get("sha256") == sha256_file(source_path)
                primary_depth = depth_part(source_path, width, height)

        lower_checks["repeatPayload"] &= repeat_payloads[1] == repeat_payloads[2]
        owners = {np.float32(owner["passIndex"]) for owner in fixture["owners"]}
        recomputed, valid, boundary = recompute_consumer(primary_arrays, owners)
        reconstruction_exact = np.ascontiguousarray(recomputed, dtype="<f4").tobytes() == repeat_payloads[1]["consumer.reconstructed"]
        masks_exact = np.ascontiguousarray(valid, dtype="u1").tobytes() == repeat_payloads[1]["consumer.valid"] and np.ascontiguousarray(boundary, dtype="u1").tobytes() == repeat_payloads[1]["consumer.boundary"]
        lower_checks["reconstructionBytes"] &= reconstruction_exact and masks_exact

        valid_mask = primary_arrays["valid"].astype(bool)
        distance_maps = {int(owner["passIndex"]): owner_distance_map(primary_arrays["currentOwner"], primary_arrays["currentRgba"][..., 3], int(owner["passIndex"])) for owner in fixture["owners"]}
        errors: list[tuple[float, int, int, int]] = []
        for y in range(height):
            for x in range(width):
                if not valid_mask[y, x]:
                    continue
                for channel in range(3):
                    absolute = abs(float(primary_arrays["reconstructed"][y, x, channel]) - float(primary_arrays["currentRgba"][y, x, channel]))
                    errors.append((absolute, y, x, channel))
                    global_errors.append((absolute, fixture_id, y, x, channel))
        errors.sort(key=lambda row: (-row[0], row[1], row[2], row[3]))
        maximum = errors[0][0]
        ties = [row for row in errors if row[0] == maximum]
        formal = formal_by_cell[f"{fixture_id}/R1"]["interiorReconstructionRgb"]["maximum"]
        lower_checks["formalMaximum"] &= maximum == formal
        owner_summary = []
        for owner in fixture["owners"]:
            owner_id = int(owner["passIndex"])
            selected = [row[0] for row in errors if int(primary_arrays["currentOwner"][row[1], row[2]]) == owner_id]
            owner_summary.append({"ownerId": owner["id"], "passIndex": owner_id, "sampleCount": len(selected), "maximum": max(selected) if selected else None})
        fixture_reports.append({
            "fixtureId": fixture_id,
            "resolution": fixture["resolution"],
            "formalMaximum": formal,
            "recomputedMaximum": maximum,
            "gateFraction": maximum / spec["frozenFormalBoundary"]["interiorRgbMaximumInclusive"],
            "maximumTieCount": len(ties),
            "maximumSamples": [sample_record(primary_arrays, primary_depth, distance_maps, x, y, channel, spec["frozenFormalBoundary"]["interiorRgbMaximumInclusive"]) for _, y, x, channel in ties],
            "topSamples": [sample_record(primary_arrays, primary_depth, distance_maps, x, y, channel, spec["frozenFormalBoundary"]["interiorRgbMaximumInclusive"]) for _, y, x, channel in errors[:spec["analysisCells"]["topKInteriorSamplesPerFixture"]]],
            "ownerSummary": owner_summary,
            "silhouetteDistanceBins": binned_tail(errors, primary_arrays, distance_maps, spec["measurements"]["tailBins"]["silhouetteDistance"]),
            "identity": identities,
            "reconstructionByteExact": reconstruction_exact,
            "maskByteExact": masks_exact,
        })

    global_errors.sort(key=lambda row: (-row[0], row[1], row[2], row[3], row[4]))
    global_maximum = global_errors[0][0]
    global_ties = [row for row in global_errors if row[0] == global_maximum]
    tied_coordinates = [{"fixtureId": fixture_id, "x": x, "y": y, "channel": CHANNELS[channel]} for _, fixture_id, y, x, channel in global_ties]
    threshold = spec["frozenFormalBoundary"]["interiorRgbMaximumInclusive"]
    all_checks = input_checks + [(name, value) for name, value in lower_checks.items()]
    all_checks.extend([
        ("globalMaximum", global_maximum == threshold),
        ("tiedCoordinateTotality", len(tied_coordinates) > 0),
    ])
    passed = all(value for _, value in all_checks)
    body = {
        "schemaVersion": "bfs.blenderStaticZeroHeadroomLocalizationResult.v0.1",
        "experimentId": spec["experimentId"],
        "decisionRole": spec["decisionRole"],
        "verdict": spec["localizationGate"]["successVerdict"] if passed else spec["localizationGate"]["failureVerdict"],
        "passed": passed,
        "baseFailure": next((name for name, value in all_checks if not value), None),
        "d12_3FormalBoundaryUnchanged": True,
        "global": {
            "interiorRgbMaximum": global_maximum,
            "frozenInclusiveThreshold": threshold,
            "gateFraction": global_maximum / threshold,
            "tieCount": len(tied_coordinates),
            "tiedCoordinates": tied_coordinates,
        },
        "fixtures": fixture_reports,
        "checks": [{"id": name, "passed": bool(value)} for name, value in all_checks],
        "inputIdentities": {name: {"uri": value["uri"], "sha256": value["sha256"], "internalHash": value.get("internalHash")} for name, value in spec["frozenInputs"].items()},
        "runtime": {"pythonExecutableSha256": sha256_file(Path(sys.executable)), "python": sys.version.split()[0], "numpy": np.__version__, "openImageIO": oiio.VERSION_STRING},
        "operationCounts": {"newBlenderRenders": 0, "modelCalls": 0, "networkCalls": 0},
        "nonClaims": spec["nonClaims"],
    }
    result = {**body, "analysisHash": canonical_hash(body)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D124_LOCALIZATION_OK verdict={result['verdict']} global={global_maximum:.17g} ties={len(global_ties)} checks={sum(value for _, value in all_checks)}/{len(all_checks)}")


if __name__ == "__main__":
    main()
