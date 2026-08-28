#!/usr/bin/env python3
"""Independent formal analyzer for B52-D12.14-H2."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np


SPEC_SHA256 = "2961f621b38f934cffaa7abe36deaaa5e01e7505d6361985039d0380578d244b"
CORRECTION_SHA256 = "9b6fdcedd571ad1ec7fb8d02bc7c6a630014d204de02f4a8b74bf5509c625a92"
CONTROL_FILES = {
    "registered": ("registered.u8", "u1"), "bilinearSupport": ("bilinear-support.u8", "u1"),
    "directZValid": ("direct-z-valid.u8", "u1"), "inverseDepthValid": ("inverse-depth-valid.u8", "u1"),
    "projectiveDepthRescued": ("projective-depth-rescued.u8", "u1"), "radius2Interior": ("radius2-interior.u8", "u1"),
    "neitherHorizontal": ("neither-horizontal.u8", "u1"), "oneSidedUnavailable": ("one-sided-unavailable.u8", "u1"),
    "consumerPredictedDepth": ("consumer-predicted-depth.f32", "<f4"), "directZSample": ("direct-z-sample.f32", "<f4"),
    "inverseDepthSample": ("inverse-depth-sample.f32", "<f4"),
}
DECISION_FILES = {"accepted": ("accepted.u8", "u1"), "reason": ("reason.u8", "u1"), "reconstructed": ("reconstructed.rgba32", "<f4")}
ADAPTER_DECISION = {
    "previousRgba": ("previous.rgba32", 4), "currentRgba": ("current.rgba32", 4),
    "previousDepth": ("previous-depth.f32", 1), "currentDepth": ("current-depth.f32", 1),
    "previousOwner": ("previous-owner.f32", 1), "currentOwner": ("current-owner.f32", 1), "vector": ("vector.xy32", 2),
}
ADAPTER_CONTROL = {
    "previousPosition": ("previous-position.xyz32", 3), "currentPosition": ("current-position.xyz32", 3),
    "vectorNext": ("vector-next.xy32", 2), "previousObjectIndex": ("previous-object-index.f32", 1), "currentObjectIndex": ("current-object-index.f32", 1),
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--correction", type=Path, required=True)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--execution-draft", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--analysis-receipt", type=Path)
    parser.add_argument("--schema-smoke", type=Path)
    return parser.parse_args()


def require(record: dict, path_text: str):
    value = record
    for key in path_text.split("."):
        if not isinstance(value, dict) or key not in value:
            raise RuntimeError(f"H2 analyzer missing schema key: {path_text}")
        value = value[key]
    return value


def schema_smoke(cli, spec: dict) -> None:
    bundle = json.loads(cli.schema_smoke.read_text())
    if require(bundle, "experimentId") != spec["experimentId"] or require(bundle, "specSha256") != SPEC_SHA256 or require(bundle, "correctionSha256") != CORRECTION_SHA256:
        raise RuntimeError("H2 analyzer smoke identity mismatch")
    for path_text in (
        "source.reportHash", "source.output.sha256", "source.operationCounts.blenderRenderCalls", "source.passState.Position",
        "adapter.reportHash", "adapter.multipart.previousMetadata", "adapter.decodedPasses.current", "adapter.decisionArrays.currentDepth.sha256", "adapter.controlArrays.currentPosition.sha256",
        "consumer.reportHash", "consumer.inputBoundary.positionAvailable", "consumer.controlArrays.projectiveDepthRescued.sha256", "consumer.decisionArrays.reconstructed.sha256", "consumer.counts.neitherHorizontal",
        "execution.executionHash", "execution.children", "execution.operationCounts.blenderRenderCalls",
    ):
        require(bundle, path_text)
    body = {"schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthAnalyzerSmoke.v0.1", "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256, "passed": True, "keysExercised": 17, "operationCounts": {"analyzerProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0}}
    result = {**body, "resultHash": canonical_hash(body)}
    cli.output.parent.mkdir(parents=True, exist_ok=True)
    cli.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("BFS_D1214H2_ANALYZER_SCHEMA_SMOKE_OK")


def self_hashed(path: Path, field: str) -> dict:
    row = json.loads(path.read_text())
    body = {key: value for key, value in row.items() if key != field}
    if row.get(field) != canonical_hash(body):
        raise RuntimeError(f"H2 self-hash mismatch: {path}")
    return row


def load_record(path: Path, record: dict, dtype: str, shape: tuple[int, ...]) -> np.ndarray:
    payload = path.read_bytes()
    if sha_bytes(payload) != record.get("sha256") or len(payload) != record.get("bytes"):
        raise RuntimeError(f"H2 array binding mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy()


def rotation_xyz(values):
    x, y, z = (float(value) for value in values)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    return ((cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx), (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx), (-sy, cy * sx, cy * cx))


def transform(row):
    return tuple(float(value) for value in row["location"]), rotation_xyz(row["rotationEuler"])


def add(a, b): return tuple(a[i] + b[i] for i in range(3))
def subtract(a, b): return tuple(a[i] - b[i] for i in range(3))
def mat_vec(m, v): return tuple(sum(m[row][column] * v[column] for column in range(3)) for row in range(3))
def mat_t_vec(m, v): return tuple(sum(m[row][column] * v[row] for row in range(3)) for column in range(3))


def owner_for_token(spec: dict, token):
    return next((row for row in spec["fixture"]["owners"] if token == np.float32(row["materialPassIndex"])), None)


def owner_transform(spec: dict, owner: dict, frame: int):
    return transform(spec["sceneContract"][owner["role"]]["transformByFrame"][str(frame)])


def camera_transform(spec: dict, frame: int):
    camera = spec["sceneContract"]["camera"]
    return transform({"location": camera["locationByFrame"][str(frame)], "rotationEuler": camera["rotationEulerByFrame"][str(frame)]})


def project(spec: dict, point, frame: int, width: int, height: int):
    camera = spec["sceneContract"]["camera"]
    camera_row = camera_transform(spec, frame)
    camera_point = mat_t_vec(camera_row[1], subtract(point, camera_row[0]))
    depth = -camera_point[2]
    if depth <= 0.0 or not math.isfinite(depth):
        return None
    sensor_width, lens = float(camera["sensorWidthMm"]), float(camera["lensMm"])
    sensor_height = sensor_width * height / width
    x = (0.5 + lens * camera_point[0] / (depth * sensor_width)) * width - 0.5
    y = (0.5 - lens * camera_point[1] / (depth * sensor_height)) * height - 0.5
    return x, y, depth


def consumer_predicted_depth(spec: dict, owner: dict, x: int, y: int, current_depth: float, width: int, height: int):
    if not math.isfinite(current_depth) or current_depth <= 0.0:
        return None
    camera = spec["sceneContract"]["camera"]
    sensor_width, lens = float(camera["sensorWidthMm"]), float(camera["lensMm"])
    sensor_height = sensor_width * height / width
    u, v_bottom = (x + 0.5) / width, 1.0 - (y + 0.5) / height
    camera_point = ((u - 0.5) * sensor_width / lens * current_depth, (v_bottom - 0.5) * sensor_height / lens * current_depth, -current_depth)
    current_camera = camera_transform(spec, 1)
    current_world = add(current_camera[0], mat_vec(current_camera[1], camera_point))
    current_owner = owner_transform(spec, owner, 1)
    local = mat_t_vec(current_owner[1], subtract(current_world, current_owner[0]))
    previous_owner = owner_transform(spec, owner, 0)
    previous_world = add(previous_owner[0], mat_vec(previous_owner[1], local))
    previous = project(spec, previous_world, 0, width, height)
    return previous[2] if previous is not None else None


def taps_and_weights(qx, qy, width, height):
    x0, y0 = math.floor(qx), math.floor(qy)
    if x0 < 0 or y0 < 0 or x0 + 1 >= width or y0 + 1 >= height:
        return None
    fx, fy = qx - x0, qy - y0
    return (((y0, x0), (y0, x0 + 1), (y0 + 1, x0), (y0 + 1, x0 + 1)), ((1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy), x0, y0)


def weighted(values, weights):
    return ((values[0] * weights[0] + values[1] * weights[1]) + values[2] * weights[2]) + values[3] * weights[3]


def same_owner(arrays, y, x, owner, width, height):
    return 0 <= x < width and 0 <= y < height and arrays["previousOwner"][y, x] == owner and arrays["previousRgba"][y, x, 3] > np.float32(0.999)


def current_radius2(arrays, x, y, owner, width, height):
    return 2 <= x < width - 2 and 2 <= y < height - 2 and all(arrays["currentOwner"][yy, xx] == owner and arrays["currentRgba"][yy, xx, 3] > np.float32(0.999) for yy in range(y - 2, y + 3) for xx in range(x - 2, x + 3))


def replay_consumer(spec: dict, arrays: dict, current_rgba: np.ndarray) -> dict:
    width, height = spec["sceneContract"]["render"]["resolution"]
    masks = {name: np.zeros((height, width), dtype="u1") for name in ("registered", "bilinearSupport", "directZValid", "inverseDepthValid", "projectiveDepthRescued", "radius2Interior", "neitherHorizontal", "oneSidedUnavailable", "accepted")}
    reason = np.zeros((height, width), dtype="u1")
    predicted = np.zeros((height, width), dtype="<f4")
    direct_sample = np.zeros((height, width), dtype="<f4")
    inverse_sample = np.zeros((height, width), dtype="<f4")
    replay_arrays = {**arrays, "currentRgba": current_rgba}
    for y in range(height):
        for x in range(width):
            owner_token = replay_arrays["currentOwner"][y, x]
            owner = owner_for_token(spec, owner_token)
            if owner is None or owner_token == np.float32(0.0) or current_rgba[y, x, 3] <= np.float32(0.999):
                continue
            values = [*current_rgba[y, x], replay_arrays["currentDepth"][y, x], *replay_arrays["vector"][y, x]]
            if not all(math.isfinite(float(value)) for value in values):
                continue
            masks["registered"][y, x] = 1
            sample = taps_and_weights(x + float(replay_arrays["vector"][y, x, 0]), y - float(replay_arrays["vector"][y, x, 1]), width, height)
            if sample is None:
                reason[y, x] = 2; continue
            taps, weights, x0, y0 = sample
            if not all(same_owner(replay_arrays, yy, xx, owner_token, width, height) for yy, xx in taps):
                reason[y, x] = 3; continue
            depths = [float(replay_arrays["previousDepth"][yy, xx]) for yy, xx in taps]
            if not all(math.isfinite(value) and value > 0.0 for value in depths):
                reason[y, x] = 4; continue
            masks["bilinearSupport"][y, x] = 1
            predicted_depth = consumer_predicted_depth(spec, owner, x, y, float(replay_arrays["currentDepth"][y, x]), width, height)
            if predicted_depth is None:
                reason[y, x] = 4; continue
            direct = weighted(depths, weights)
            reciprocal = weighted([1.0 / value for value in depths], weights)
            inverse = 1.0 / reciprocal if reciprocal > 0.0 and math.isfinite(reciprocal) else math.nan
            predicted[y, x], direct_sample[y, x], inverse_sample[y, x] = np.float32(predicted_depth), np.float32(direct), np.float32(inverse if math.isfinite(inverse) else 0.0)
            tolerance = max(1.0, predicted_depth) / 1024.0
            direct_valid, inverse_valid = abs(direct - predicted_depth) <= tolerance, math.isfinite(inverse) and abs(inverse - predicted_depth) <= tolerance
            masks["directZValid"][y, x], masks["inverseDepthValid"][y, x] = int(direct_valid), int(inverse_valid)
            masks["projectiveDepthRescued"][y, x] = int(inverse_valid and not direct_valid)
            if not inverse_valid:
                reason[y, x] = 4; continue
            if not current_radius2(replay_arrays, x, y, owner_token, width, height):
                reason[y, x] = 5; continue
            masks["radius2Interior"][y, x] = 1
            horizontal = [(same_owner(replay_arrays, yy, x0 - 1, owner_token, width, height), same_owner(replay_arrays, yy, x0 + 2, owner_token, width, height)) for yy in (y0, y0 + 1)]
            vertical = [(same_owner(replay_arrays, y0 - 1, xx, owner_token, width, height), same_owner(replay_arrays, y0 + 2, xx, owner_token, width, height)) for xx in (x0, x0 + 1)]
            neither_h = any((not left) and (not right) for left, right in horizontal)
            neither_v = any((not top) and (not bottom) for top, bottom in vertical)
            masks["neitherHorizontal"][y, x] = int(neither_h)
            if neither_h or neither_v:
                masks["oneSidedUnavailable"][y, x] = 1; reason[y, x] = 6
            else:
                reason[y, x] = 7
    return {**masks, "consumerPredictedDepth": predicted, "directZSample": direct_sample, "inverseDepthSample": inverse_sample, "reason": reason, "reconstructed": current_rgba.copy()}


def metadata_differences(left: dict, right: dict) -> list[dict]:
    rows = []
    for part in sorted(set(left) | set(right)):
        lrow, rrow = left.get(part, {}), right.get(part, {})
        for name in sorted(set(lrow) | set(rrow)):
            if lrow.get(name) != rrow.get(name):
                rows.append({"subimage": part, "name": name, "repeat1": lrow.get(name), "repeat2": rrow.get(name)})
    return rows


def maximum(values) -> float:
    return float(max(values)) if values else math.inf


def main() -> None:
    cli = arguments()
    if sha_file(cli.spec) != SPEC_SHA256 or sha_file(cli.correction) != CORRECTION_SHA256 or cli.output.exists():
        raise RuntimeError("H2 analyzer identity/output freshness failure")
    spec = json.loads(cli.spec.read_text())
    if cli.schema_smoke is not None:
        schema_smoke(cli, spec); return
    if cli.root is None or cli.execution_draft is None or cli.analysis_receipt is None or cli.analysis_receipt.exists():
        raise RuntimeError("H2 analyzer formal arguments missing")
    runtime = spec["runtime"]["python"]
    if sha_file(Path(sys.executable)) != runtime["sha256"] or np.__version__ != runtime["numpy"]:
        raise RuntimeError("H2 analyzer runtime mismatch")
    width, height = spec["sceneContract"]["render"]["resolution"]
    adapters, consumers, adapter_arrays, consumer_arrays = {}, {}, {}, {}
    identity_ok = True
    for repeat in (1, 2):
        adapter_path = cli.root / "adapters" / f"R{repeat}" / "report.json"
        adapter = self_hashed(adapter_path, "reportHash")
        adapters[repeat] = adapter
        identity_ok &= adapter.get("experimentId") == spec["experimentId"] and adapter.get("specSha256") == SPEC_SHA256 and adapter.get("correctionSha256") == CORRECTION_SHA256 and adapter.get("repeat") == repeat
        decision_dir = cli.root / "adapters" / f"R{repeat}" / "arrays" / "decision"
        control_dir = cli.root / "adapters" / f"R{repeat}" / "arrays" / "control"
        arrays = {}
        for name, (filename, channels) in ADAPTER_DECISION.items():
            shape = (height, width, channels) if channels > 1 else (height, width)
            arrays[name] = load_record(decision_dir / filename, adapter["decisionArrays"][name], "<f4", shape)
        for name, (filename, channels) in ADAPTER_CONTROL.items():
            shape = (height, width, channels) if channels > 1 else (height, width)
            arrays[name] = load_record(control_dir / filename, adapter["controlArrays"][name], "<f4", shape)
        adapter_arrays[repeat] = arrays
        consumers[repeat], consumer_arrays[repeat] = {}, {}
        for producer in ("python", "node"):
            report_path = cli.root / "consumers" / producer / f"R{repeat}" / "report.json"
            report = self_hashed(report_path, "reportHash")
            consumers[repeat][producer] = report
            identity_ok &= report.get("experimentId") == spec["experimentId"] and report.get("specSha256") == SPEC_SHA256 and report.get("correctionSha256") == CORRECTION_SHA256 and report.get("repeat") == repeat and report.get("producer") == producer
            identity_ok &= report.get("inputBoundary", {}).get("positionAvailable") is False and report.get("inputBoundary", {}).get("objectIndexAvailable") is False and report.get("inputBoundary", {}).get("directoryName") == "decision"
            output_dir = cli.root / "consumers" / producer / f"R{repeat}" / "arrays"
            loaded = {}
            for name, (filename, dtype) in CONTROL_FILES.items():
                loaded[name] = load_record(output_dir / "control" / filename, report["controlArrays"][name], dtype, (height, width))
            for name, (filename, dtype) in DECISION_FILES.items():
                shape = (height, width, 4) if name == "reconstructed" else (height, width)
                loaded[name] = load_record(output_dir / "decision" / filename, report["decisionArrays"][name], dtype, shape)
            consumer_arrays[repeat][producer] = loaded
    decoded_exact = all(adapters[1]["decodedPasses"][frame][part]["sha256"] == adapters[2]["decodedPasses"][frame][part]["sha256"] for frame in ("previous", "current") for part in adapters[1]["decodedPasses"][frame])
    metadata_rows = metadata_differences(adapters[1]["multipart"]["previousMetadata"], adapters[2]["multipart"]["previousMetadata"]) + metadata_differences(adapters[1]["multipart"]["currentMetadata"], adapters[2]["multipart"]["currentMetadata"])
    allowed_metadata = set(spec["repeatIdentity"]["containerMetadataDifferenceAllowlist"])
    metadata_ok = all(row["name"] in allowed_metadata and row["subimage"].endswith(".Combined") for row in metadata_rows)
    cross_language_exact = all(np.array_equal(consumer_arrays[repeat]["python"][name], consumer_arrays[repeat]["node"][name]) for repeat in (1, 2) for name in consumer_arrays[repeat]["python"])
    repeat_consumer_exact = all(np.array_equal(consumer_arrays[1][producer][name], consumer_arrays[2][producer][name]) for producer in ("python", "node") for name in consumer_arrays[1][producer])
    replay_exact, metamorphic_ok, fallback_ok = True, True, True
    metrics = []
    position_gate = True
    measurement_gate = True
    foreground = next(owner for owner in spec["fixture"]["owners"] if owner["role"] == "foreground")
    foreground_token = np.float32(foreground["materialPassIndex"])
    object_token = np.float32(foreground["objectPassIndex"])
    tolerance = spec["positionControlOracle"]["tolerances"]
    for repeat in (1, 2):
        arrays, formal = adapter_arrays[repeat], consumer_arrays[repeat]["python"]
        replay = replay_consumer(spec, arrays, arrays["currentRgba"])
        for name in (*CONTROL_FILES, *DECISION_FILES):
            replay_exact &= np.array_equal(replay[name], formal[name])
        mutated_rgba = arrays["currentRgba"].copy()
        mutated_rgba[..., 0] = np.float32(0.125); mutated_rgba[..., 1] = np.float32(0.625); mutated_rgba[..., 2] = np.float32(0.375)
        mutated = replay_consumer(spec, arrays, mutated_rgba)
        metamorphic_ok &= all(np.array_equal(replay[name], mutated[name]) for name in (*CONTROL_FILES, "accepted", "reason") if name != "reconstructed")
        fallback_ok &= np.array_equal(formal["reconstructed"][formal["accepted"] == 0], arrays["currentRgba"][formal["accepted"] == 0])
        target = (arrays["currentOwner"] == foreground_token) & (arrays["currentObjectIndex"] == object_token) & (arrays["currentRgba"][..., 3] > np.float32(0.999))
        depth_errors, vector_errors, next_errors = [], [], []
        position_inverse = np.zeros((height, width), dtype=bool)
        position_direct = np.zeros((height, width), dtype=bool)
        current_owner = owner_transform(spec, foreground, 1)
        previous_owner = owner_transform(spec, foreground, 0)
        for y, x in zip(*np.nonzero(target)):
            point = tuple(float(value) for value in arrays["currentPosition"][y, x])
            current_projected = project(spec, point, 1, width, height)
            if current_projected is None:
                position_gate = False; continue
            local = mat_t_vec(current_owner[1], subtract(point, current_owner[0]))
            previous_point = add(previous_owner[0], mat_vec(previous_owner[1], local))
            previous_projected = project(spec, previous_point, 0, width, height)
            if previous_projected is None:
                position_gate = False; continue
            depth_errors.append(abs(float(arrays["currentDepth"][y, x]) - current_projected[2]))
            expected_vector = (previous_projected[0] - current_projected[0], current_projected[1] - previous_projected[1])
            vector_errors.extend(abs(float(arrays["vector"][y, x, channel]) - expected_vector[channel]) for channel in (0, 1))
            next_errors.extend(abs(float(value)) for value in arrays["vectorNext"][y, x])
            sample = taps_and_weights(x + float(arrays["vector"][y, x, 0]), y - float(arrays["vector"][y, x, 1]), width, height)
            if sample is None:
                continue
            taps, weights, _, _ = sample
            if not all(same_owner(arrays, yy, xx, foreground_token, width, height) for yy, xx in taps):
                continue
            depths = [float(arrays["previousDepth"][yy, xx]) for yy, xx in taps]
            if not all(math.isfinite(value) and value > 0.0 for value in depths):
                continue
            direct = weighted(depths, weights); reciprocal = weighted([1.0 / value for value in depths], weights); inverse = 1.0 / reciprocal
            depth_tolerance = max(1.0, previous_projected[2]) / 1024.0
            position_direct[y, x] = abs(direct - previous_projected[2]) <= depth_tolerance
            position_inverse[y, x] = abs(inverse - previous_projected[2]) <= depth_tolerance
        position_gate &= maximum(depth_errors) <= tolerance["currentDepthMaximumAbsoluteError"] and maximum(vector_errors) <= tolerance["vectorMaximumAbsoluteErrorPixels"] and maximum(next_errors) <= tolerance["vectorNextMaximumAbsoluteMagnitudePixels"]
        consumer_rescued = formal["projectiveDepthRescued"].astype(bool)
        consumer_neither = formal["neitherHorizontal"].astype(bool)
        intersection_rescued = consumer_rescued & position_inverse & ~position_direct & target
        intersection_neither = intersection_rescued & consumer_neither
        counts = {
            "registered": int((formal["registered"].astype(bool) & target).sum()),
            "sameOwnerBilinear": int((formal["bilinearSupport"].astype(bool) & target).sum()),
            "consumerDirectZValid": int((formal["directZValid"].astype(bool) & target).sum()),
            "consumerInverseDepthValid": int((formal["inverseDepthValid"].astype(bool) & target).sum()),
            "consumerRescued": int((consumer_rescued & target).sum()),
            "positionInverseDepthValid": int((position_inverse & target).sum()),
            "intersectionRescued": int(intersection_rescued.sum()),
            "intersectionNeither": int(intersection_neither.sum()),
            "intersectionUnavailable": int((intersection_neither & formal["oneSidedUnavailable"].astype(bool)).sum()),
            "intersectionAccepted": int((intersection_neither & formal["accepted"].astype(bool)).sum()),
            "consumerOnlyInverse": int((formal["inverseDepthValid"].astype(bool) & ~position_inverse & target).sum()),
        }
        contract = spec["measurementContract"]
        repeat_measurement = counts["sameOwnerBilinear"] >= contract["sameOwnerBilinearSupportMinimumPerRepeat"] and counts["consumerInverseDepthValid"] >= contract["inverseDepthValidMinimumPerRepeat"] and counts["intersectionRescued"] >= contract["projectiveDepthRescuedMinimumPerRepeat"] and counts["intersectionNeither"] >= contract["inverseDepthNeitherWitnessMinimumPerRepeat"] and counts["intersectionAccepted"] <= contract["inverseDepthNeitherAcceptedMaximumPerRepeat"] and counts["intersectionUnavailable"] == counts["intersectionNeither"]
        measurement_gate &= repeat_measurement
        metrics.append({"repeat": repeat, "counts": counts, "positionControl": {"foregroundPixels": int(target.sum()), "currentDepthMaximumAbsoluteError": maximum(depth_errors), "vectorMaximumAbsoluteErrorPixels": maximum(vector_errors), "vectorNextMaximumAbsoluteMagnitudePixels": maximum(next_errors)}, "measurementPassed": repeat_measurement})
    envelope_exact = True
    for repeat in (1, 2):
        for subtree in ("controlArrays", "decisionArrays"):
            left = cli.root / "envelopes" / f"R{repeat}" / subtree / "python.bin"
            right = cli.root / "envelopes" / f"R{repeat}" / subtree / "node.bin"
            envelope_exact &= left.is_file() and right.is_file() and left.read_bytes() == right.read_bytes()
    execution = self_hashed(cli.execution_draft, "executionHash")
    expected_labels = {*(f"source-R{repeat}-F{frame}" for repeat in (1, 2) for frame in (0, 1)), *(f"adapter-R{repeat}" for repeat in (1, 2)), *(f"consumer-{producer}-R{repeat}" for producer in ("python", "node") for repeat in (1, 2)), *(f"envelope-{producer}-R{repeat}-{subtree}" for producer in ("python", "node") for repeat in (1, 2) for subtree in ("controlArrays", "decisionArrays"))}
    children = execution.get("children", [])
    operation_ok = len(children) == 18 and {row.get("label") for row in children} == expected_labels and len({row.get("pid") for row in children}) == 18 and all(row.get("exitCode") == 0 for row in children) and execution.get("operationCounts") == {"childProcessesCompleted": 18, "blenderProcesses": 4, "blenderRenderCalls": 4, "cyclesRayRenders": 4, "adapterProcesses": 2, "consumerProcesses": 4, "typedEnvelopeProcesses": 8, "analyzerProcesses": 0, "auditProcesses": 0, "modelCalls": 0, "networkCalls": 0}
    checks = {
        "IDENTITY_AND_INPUT_BOUNDARY": bool(identity_ok), "DECODED_PASS_REPEAT_IDENTITY": bool(decoded_exact), "CONTAINER_METADATA_ALLOWLIST": bool(metadata_ok),
        "PYTHON_NODE_EVERY_ARRAY_IDENTITY": bool(cross_language_exact), "CONSUMER_REPEAT_IDENTITY": bool(repeat_consumer_exact), "INDEPENDENT_CONSUMER_REPLAY": bool(replay_exact),
        "CURRENT_RGB_DECISION_METAMORPHISM": bool(metamorphic_ok), "FALLBACK_EXACT": bool(fallback_ok), "POSITION_DEPTH_VECTOR_CONTROL": bool(position_gate),
        "TYPED_ENVELOPE_IDENTITY": bool(envelope_exact), "ACTUAL_OPERATION_BOUNDARY": bool(operation_ok), "PROJECTIVE_DEPTH_MEASUREMENT": bool(measurement_gate),
    }
    integrity_names = [name for name in checks if name != "PROJECTIVE_DEPTH_MEASUREMENT"]
    integrity_passed = all(checks[name] for name in integrity_names)
    if integrity_passed and measurement_gate:
        verdict = spec["decision"]["supportedVerdict"]
    elif integrity_passed:
        verdict = spec["decision"]["notSupportedVerdict"]
    else:
        verdict = spec["decision"]["rejectedVerdict"]
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthResult.v0.1", "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256,
        "pid": os.getpid(), "verdict": verdict, "scientificVerdict": verdict, "passed": bool(integrity_passed and measurement_gate),
        "evidenceChecks": [{"name": name, "passed": bool(value)} for name, value in checks.items()], "evidenceChecksPassed": sum(bool(value) for value in checks.values()), "evidenceChecksTotal": len(checks),
        "metrics": metrics, "metadataDifferences": metadata_rows, "operationCounts": {"analyzerProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
        "executionDraft": {"uri": str(cli.execution_draft), "sha256": sha_file(cli.execution_draft), "executionHash": execution["executionHash"]},
        "nonClaims": spec["nonClaims"], "promotionBoundary": spec["promotionBoundary"],
    }
    results = {**body, "resultHash": canonical_hash(body)}
    cli.output.parent.mkdir(parents=True, exist_ok=True)
    cli.output.write_text(json.dumps(results, indent=2, sort_keys=True, allow_nan=False) + "\n")
    receipt_body = {"schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthAnalysisReceipt.v0.1", "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256, "results": {"uri": str(cli.output), "sha256": sha_file(cli.output), "resultHash": results["resultHash"]}, "executionDraft": body["executionDraft"], "operationCounts": {"analysisReceiptWrites": 1, "modelCalls": 0, "networkCalls": 0}}
    receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}
    cli.analysis_receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(f"BFS_D1214H2_ANALYZER_OK verdict={verdict} rescued={metrics[0]['counts']['intersectionRescued']}")


if __name__ == "__main__":
    main()
