#!/usr/bin/env python3
"""Scalar Python decision consumer for B52-D12.14-H2."""
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
INPUTS = {
    "previousRgba": ("previous.rgba32", 4), "currentRgba": ("current.rgba32", 4),
    "previousDepth": ("previous-depth.f32", 1), "currentDepth": ("current-depth.f32", 1),
    "previousOwner": ("previous-owner.f32", 1), "currentOwner": ("current-owner.f32", 1),
    "vector": ("vector.xy32", 2),
}
CONTROL_OUTPUTS = {
    "registered": ("registered.u8", "u1"), "bilinearSupport": ("bilinear-support.u8", "u1"),
    "directZValid": ("direct-z-valid.u8", "u1"), "inverseDepthValid": ("inverse-depth-valid.u8", "u1"),
    "projectiveDepthRescued": ("projective-depth-rescued.u8", "u1"), "radius2Interior": ("radius2-interior.u8", "u1"),
    "neitherHorizontal": ("neither-horizontal.u8", "u1"), "oneSidedUnavailable": ("one-sided-unavailable.u8", "u1"),
    "consumerPredictedDepth": ("consumer-predicted-depth.f32", "<f4"), "directZSample": ("direct-z-sample.f32", "<f4"),
    "inverseDepthSample": ("inverse-depth-sample.f32", "<f4"),
}
DECISION_OUTPUTS = {
    "accepted": ("accepted.u8", "u1"), "reason": ("reason.u8", "u1"), "reconstructed": ("reconstructed.rgba32", "<f4"),
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
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def rotation_xyz(values):
    x, y, z = (float(value) for value in values)
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)
    return (
        (cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
        (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
        (-sy, cy * sx, cy * cx),
    )


def transform(row):
    return tuple(float(value) for value in row["location"]), rotation_xyz(row["rotationEuler"])


def add(left, right):
    return tuple(left[i] + right[i] for i in range(3))


def subtract(left, right):
    return tuple(left[i] - right[i] for i in range(3))


def mat_vec(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3))


def mat_t_vec(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[row] for row in range(3)) for column in range(3))


def owner_for_token(spec: dict, token: np.float32):
    for owner in spec["fixture"]["owners"]:
        if token == np.float32(owner["materialPassIndex"]):
            return owner
    return None


def owner_transform(spec: dict, owner: dict, frame: int):
    return transform(spec["sceneContract"][owner["role"]]["transformByFrame"][str(frame)])


def camera_transform(spec: dict, frame: int):
    camera = spec["sceneContract"]["camera"]
    return transform({"location": camera["locationByFrame"][str(frame)], "rotationEuler": camera["rotationEulerByFrame"][str(frame)]})


def consumer_predicted_depth(spec: dict, owner: dict, x: int, y: int, current_depth: float, width: int, height: int):
    if not math.isfinite(current_depth) or current_depth <= 0.0:
        return None
    camera = spec["sceneContract"]["camera"]
    lens, sensor_width = float(camera["lensMm"]), float(camera["sensorWidthMm"])
    sensor_height = sensor_width * height / width
    u = (x + 0.5) / width
    v_bottom = 1.0 - (y + 0.5) / height
    current_camera_point = ((u - 0.5) * sensor_width / lens * current_depth, (v_bottom - 0.5) * sensor_height / lens * current_depth, -current_depth)
    current_camera = camera_transform(spec, 1)
    current_world = add(current_camera[0], mat_vec(current_camera[1], current_camera_point))
    current_owner = owner_transform(spec, owner, 1)
    local = mat_t_vec(current_owner[1], subtract(current_world, current_owner[0]))
    previous_owner = owner_transform(spec, owner, 0)
    previous_world = add(previous_owner[0], mat_vec(previous_owner[1], local))
    previous_camera = camera_transform(spec, 0)
    previous_camera_point = mat_t_vec(previous_camera[1], subtract(previous_world, previous_camera[0]))
    depth = -previous_camera_point[2]
    return depth if math.isfinite(depth) and depth > 0.0 else None


def taps_and_weights(qx: float, qy: float, width: int, height: int):
    x0, y0 = math.floor(qx), math.floor(qy)
    if x0 < 0 or y0 < 0 or x0 + 1 >= width or y0 + 1 >= height:
        return None
    fx, fy = qx - x0, qy - y0
    return (
        ((y0, x0), (y0, x0 + 1), (y0 + 1, x0), (y0 + 1, x0 + 1)),
        ((1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy),
        x0, y0,
    )


def weighted(values, weights):
    return ((values[0] * weights[0] + values[1] * weights[1]) + values[2] * weights[2]) + values[3] * weights[3]


def same_owner(arrays, y: int, x: int, owner: np.float32, width: int, height: int) -> bool:
    return 0 <= x < width and 0 <= y < height and arrays["previousOwner"][y, x] == owner and arrays["previousRgba"][y, x, 3] > np.float32(0.999)


def current_radius2(arrays, x: int, y: int, owner: np.float32, width: int, height: int) -> bool:
    if x < 2 or y < 2 or x >= width - 2 or y >= height - 2:
        return False
    return all(arrays["currentOwner"][yy, xx] == owner and arrays["currentRgba"][yy, xx, 3] > np.float32(0.999) for yy in range(y - 2, y + 3) for xx in range(x - 2, x + 3))


def write_array(path: Path, value: np.ndarray, dtype: str) -> dict:
    array = np.ascontiguousarray(value, dtype=dtype)
    payload = array.tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"uri": str(path), "sha256": sha_bytes(payload), "bytes": len(payload), "shape": list(array.shape), "dtype": dtype}


def main() -> None:
    cli = arguments()
    if sha_file(cli.spec) != SPEC_SHA256 or sha_file(cli.correction) != CORRECTION_SHA256 or cli.output_dir.exists() or cli.report.exists():
        raise RuntimeError("H2 Python consumer identity/output freshness failure")
    spec = json.loads(cli.spec.read_text())
    if cli.fixture != spec["fixture"]["id"] or cli.input_dir.name != "decision" or not cli.input_dir.is_dir():
        raise RuntimeError("H2 Python consumer fixture/input boundary mismatch")
    runtime = spec["runtime"]["python"]
    if sha_file(Path(sys.executable)) != runtime["sha256"] or np.__version__ != runtime["numpy"]:
        raise RuntimeError("H2 Python runtime mismatch")
    width, height = spec["sceneContract"]["render"]["resolution"]
    arrays, input_records = {}, {}
    for name, (filename, channels) in INPUTS.items():
        path = cli.input_dir / filename
        payload = path.read_bytes()
        shape = (height, width, channels) if channels > 1 else (height, width)
        arrays[name] = np.frombuffer(payload, dtype="<f4").reshape(shape).copy()
        input_records[name] = {"filename": filename, "sha256": sha_bytes(payload), "bytes": len(payload), "shape": list(shape)}
    masks = {name: np.zeros((height, width), dtype="u1") for name in (
        "registered", "bilinearSupport", "directZValid", "inverseDepthValid", "projectiveDepthRescued", "radius2Interior", "neitherHorizontal", "oneSidedUnavailable", "accepted",
    )}
    reason = np.zeros((height, width), dtype="u1")
    predicted = np.zeros((height, width), dtype="<f4")
    direct_sample = np.zeros((height, width), dtype="<f4")
    inverse_sample = np.zeros((height, width), dtype="<f4")
    reconstructed = arrays["currentRgba"].copy()
    tolerance_divisor = 1024.0
    for y in range(height):
        for x in range(width):
            owner_token = arrays["currentOwner"][y, x]
            owner = owner_for_token(spec, owner_token)
            if owner is None or owner_token == np.float32(0.0) or arrays["currentRgba"][y, x, 3] <= np.float32(0.999):
                continue
            if not all(math.isfinite(float(value)) for value in (*arrays["currentRgba"][y, x], arrays["currentDepth"][y, x], *arrays["vector"][y, x])):
                continue
            masks["registered"][y, x] = 1
            qx = x + float(arrays["vector"][y, x, 0])
            qy = y - float(arrays["vector"][y, x, 1])
            sample = taps_and_weights(qx, qy, width, height)
            if sample is None:
                reason[y, x] = 2
                continue
            taps, weights, x0, y0 = sample
            if not all(same_owner(arrays, yy, xx, owner_token, width, height) for yy, xx in taps):
                reason[y, x] = 3
                continue
            depths = [float(arrays["previousDepth"][yy, xx]) for yy, xx in taps]
            if not all(math.isfinite(value) and value > 0.0 for value in depths):
                reason[y, x] = 4
                continue
            masks["bilinearSupport"][y, x] = 1
            predicted_depth = consumer_predicted_depth(spec, owner, x, y, float(arrays["currentDepth"][y, x]), width, height)
            if predicted_depth is None:
                reason[y, x] = 4
                continue
            direct = weighted(depths, weights)
            reciprocal = weighted([1.0 / value for value in depths], weights)
            inverse = 1.0 / reciprocal if reciprocal > 0.0 and math.isfinite(reciprocal) else math.nan
            predicted[y, x] = np.float32(predicted_depth)
            direct_sample[y, x] = np.float32(direct)
            inverse_sample[y, x] = np.float32(inverse if math.isfinite(inverse) else 0.0)
            tolerance = max(1.0, predicted_depth) / tolerance_divisor
            direct_valid = abs(direct - predicted_depth) <= tolerance
            inverse_valid = math.isfinite(inverse) and abs(inverse - predicted_depth) <= tolerance
            masks["directZValid"][y, x] = int(direct_valid)
            masks["inverseDepthValid"][y, x] = int(inverse_valid)
            masks["projectiveDepthRescued"][y, x] = int(inverse_valid and not direct_valid)
            if not inverse_valid:
                reason[y, x] = 4
                continue
            if not current_radius2(arrays, x, y, owner_token, width, height):
                reason[y, x] = 5
                continue
            masks["radius2Interior"][y, x] = 1
            horizontal = [(same_owner(arrays, yy, x0 - 1, owner_token, width, height), same_owner(arrays, yy, x0 + 2, owner_token, width, height)) for yy in (y0, y0 + 1)]
            vertical = [(same_owner(arrays, y0 - 1, xx, owner_token, width, height), same_owner(arrays, y0 + 2, xx, owner_token, width, height)) for xx in (x0, x0 + 1)]
            neither_horizontal = any((not left) and (not right) for left, right in horizontal)
            neither_vertical = any((not top) and (not bottom) for top, bottom in vertical)
            masks["neitherHorizontal"][y, x] = int(neither_horizontal)
            if neither_horizontal or neither_vertical:
                masks["oneSidedUnavailable"][y, x] = 1
                reason[y, x] = 6
                continue
            reason[y, x] = 7
    control_values = {**masks, "consumerPredictedDepth": predicted, "directZSample": direct_sample, "inverseDepthSample": inverse_sample}
    cli.output_dir.mkdir(parents=True, exist_ok=False)
    control_records = {name: write_array(cli.output_dir / "control" / filename, control_values[name], dtype) for name, (filename, dtype) in CONTROL_OUTPUTS.items()}
    decision_values = {**masks, "reason": reason, "reconstructed": reconstructed}
    decision_records = {name: write_array(cli.output_dir / "decision" / filename, decision_values[name], dtype) for name, (filename, dtype) in DECISION_OUTPUTS.items()}
    counts = {name: int(value.sum()) for name, value in masks.items()}
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthConsumer.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256,
        "producer": "python", "fixtureId": cli.fixture, "repeat": cli.repeat, "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha_file(Path(sys.executable)), "numpy": np.__version__},
        "inputBoundary": {"directoryName": cli.input_dir.name, "positionAvailable": False, "objectIndexAvailable": False, "arrays": input_records},
        "controlArrays": control_records, "decisionArrays": decision_records, "counts": counts,
        "reasonCodes": {"NOT_REGISTERED": 0, "INVALID_BOUNDS": 2, "INVALID_OWNER": 3, "INVALID_PROJECTIVE_DEPTH": 4, "OUTSIDE_RADIUS2": 5, "SUPPORT_UNAVAILABLE": 6, "RISK_REJECTED": 7, "ACCEPTED": 8},
        "operationCounts": {"consumerProcesses": 1, "pixelsVisited": width * height, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    cli.report.parent.mkdir(parents=True, exist_ok=True)
    cli.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_D1214H2_PYTHON repeat={cli.repeat} rescued={counts['projectiveDepthRescued']} neither={counts['neitherHorizontal']}")


if __name__ == "__main__":
    main()
