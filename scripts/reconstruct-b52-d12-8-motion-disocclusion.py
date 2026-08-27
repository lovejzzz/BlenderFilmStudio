#!/usr/bin/env python3
"""Scalar Python structural-validity and adaptive-risk consumer for B52-D12.8."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "67722b1c8fafa0b83518e6e467de1adb9ca88bd32b7145f15be2d5627767b4d4"
INPUTS = {
    "previousRgba": ("previous.rgba32", 4),
    "currentRgba": ("current.rgba32", 4),
    "previousDepth": ("previous-depth.f32", 1),
    "currentDepth": ("current-depth.f32", 1),
    "previousOwner": ("previous-owner.f32", 1),
    "currentOwner": ("current-owner.f32", 1),
    "vector": ("vector.xy32", 2),
    "vectorNext": ("vector-next.xy32", 2),
}
OUTPUTS = {
    "adaptiveReconstructed": ("adaptive-reconstructed.rgba32", "<f4"),
    "reason": ("reason.u8", "u1"),
    "analyticOwner": ("analytic-owner.u8", "u1"),
    "structuralValid": ("structural-valid.u8", "u1"),
    "radius2Interior": ("radius2-interior.u8", "u1"),
    "radius3Interior": ("radius3-interior.u8", "u1"),
    "adaptiveInterior": ("adaptive-interior.u8", "u1"),
    "adaptiveRejected": ("adaptive-rejected.u8", "u1"),
    "riskRgb": ("risk.rgb64", "<f8"),
}
REASONS = {
    "UNREGISTERED": 0,
    "INVALID_CURRENT_ORACLE": 1,
    "INVALID_BOUNDS": 2,
    "INVALID_OWNER": 3,
    "INVALID_ALPHA": 4,
    "INVALID_DEPTH": 5,
    "VALID": 6,
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--adapter-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def rotation_xyz(values: list[float]) -> tuple[tuple[float, float, float], ...]:
    x, y, z = (float(value) for value in values)
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)
    return (
        (cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
        (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
        (-sy, cy * sx, cy * cx),
    )


def transform(row: dict) -> tuple[tuple[float, float, float], tuple[tuple[float, float, float], ...]]:
    return tuple(float(value) for value in row["location"]), rotation_xyz(row["rotationEuler"])


def add(left, right):
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def subtract(left, right):
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def scale(vector, value: float):
    return (vector[0] * value, vector[1] * value, vector[2] * value)


def dot(left, right) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def mat_vec(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3))


def mat_t_vec(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[row] for row in range(3)) for column in range(3))


def project(point, camera_transform, width: int, height: int, lens: float, sensor_width: float):
    camera_location, camera_rotation = camera_transform
    camera_point = mat_t_vec(camera_rotation, subtract(point, camera_location))
    depth = -camera_point[2]
    if depth <= 0.0:
        return None
    sensor_height = sensor_width * height / width
    u = 0.5 + lens * camera_point[0] / (depth * sensor_width)
    v_bottom = 0.5 + lens * camera_point[1] / (depth * sensor_height)
    return u * width - 0.5, (1.0 - v_bottom) * height - 0.5, depth


def dimensions(spec: dict, owner: dict) -> tuple[float, float]:
    surfaces = spec["sceneContract"]["surfaces"]
    values = surfaces["backgroundSizeWorld"] if owner["role"] == "background" else surfaces["occluderSizeWorld"]
    return float(values[0]), float(values[1])


def oracle_pixel(spec: dict, fixture: dict, x: int, y: int):
    width, height = fixture["resolution"]
    camera_spec = spec["sceneContract"]["camera"]
    lens, sensor_width = float(camera_spec["lensMm"]), float(camera_spec["sensorWidthMm"])
    sensor_height = sensor_width * height / width
    current_camera = transform(fixture["cameraByFrame"]["1"])
    previous_camera = transform(fixture["cameraByFrame"]["0"])
    u = (x + 0.5) / width
    v_bottom = 1.0 - (y + 0.5) / height
    camera_direction = ((u - 0.5) * sensor_width / lens, (v_bottom - 0.5) * sensor_height / lens, -1.0)
    world_direction = mat_vec(current_camera[1], camera_direction)
    candidates = []
    for owner_index, owner in enumerate(fixture["owners"], start=1):
        current_owner = transform(owner["transformByFrame"]["1"])
        normal = mat_vec(current_owner[1], (0.0, 0.0, 1.0))
        denominator = dot(world_direction, normal)
        if abs(denominator) < 1e-12:
            continue
        distance = dot(subtract(current_owner[0], current_camera[0]), normal) / denominator
        if distance <= 0.0:
            continue
        world_point = add(current_camera[0], scale(world_direction, distance))
        local_point = mat_t_vec(current_owner[1], subtract(world_point, current_owner[0]))
        size_x, size_y = dimensions(spec, owner)
        if abs(local_point[0]) <= size_x / 2.0 and abs(local_point[1]) <= size_y / 2.0:
            projected = project(world_point, current_camera, width, height, lens, sensor_width)
            if projected is not None:
                candidates.append((projected[2], owner_index, owner, local_point, world_point))
    if not candidates:
        return None
    current_depth, owner_index, owner, local_point, _world_point = min(candidates, key=lambda row: row[0])
    previous_owner = transform(owner["transformByFrame"]["0"])
    previous_world = add(previous_owner[0], mat_vec(previous_owner[1], local_point))
    previous_projected = project(previous_world, previous_camera, width, height, lens, sensor_width)
    if previous_projected is None:
        return None
    previous_x, previous_y, previous_depth = previous_projected
    return {
        "ownerIndex": owner_index,
        "passIndex": np.float32(owner["passIndex"]),
        "expectedVector": (previous_x - x, y - previous_y),
        "currentDepth": current_depth,
        "previousDepth": previous_depth,
    }


def taps_and_weights(qx: float, qy: float, width: int, height: int):
    x0, y0 = math.floor(qx), math.floor(qy)
    if x0 < 0 or y0 < 0 or x0 + 1 >= width or y0 + 1 >= height:
        return None
    fx, fy = qx - x0, qy - y0
    return (
        ((y0, x0), (y0, x0 + 1), (y0 + 1, x0), (y0 + 1, x0 + 1)),
        ((1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy),
    )


def weighted(values: list[float], weights: tuple[float, ...]) -> float:
    return ((values[0] * weights[0] + values[1] * weights[1]) + values[2] * weights[2]) + values[3] * weights[3]


def neighborhood(arrays: dict, x: int, y: int, radius: int, owner: np.float32, width: int, height: int) -> bool:
    if x < radius or y < radius or x >= width - radius or y >= height - radius:
        return False
    return all(
        arrays["currentOwner"][ty, tx] == owner and arrays["currentRgba"][ty, tx, 3] > np.float32(0.999)
        for ty in range(y - radius, y + radius + 1)
        for tx in range(x - radius, x + radius + 1)
    )


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    if sha_file(args.spec) != SPEC_SHA256 or sha_file(Path(sys.executable)) != spec["runtime"]["python"]["sha256"] or np.__version__ != spec["runtime"]["python"]["numpy"]:
        raise RuntimeError("D12.8 Python/spec identity mismatch")
    fixture = next((row for row in spec["fixtures"] if row["id"] == args.fixture), None)
    if fixture is None or args.output_dir.exists() or args.report.exists():
        raise RuntimeError("D12.8 consumer fixture or output invalid")
    adapter = json.loads(args.adapter_report.read_text())
    body_without_hash = {key: value for key, value in adapter.items() if key != "reportHash"}
    if adapter.get("reportHash") != canonical_hash(body_without_hash) or adapter.get("fixtureId") != args.fixture or adapter.get("repeat") != args.repeat:
        raise RuntimeError("D12.8 adapter identity mismatch")
    width, height = fixture["resolution"]
    arrays = {}
    for name, (filename, channels) in INPUTS.items():
        payload = (args.input_dir / filename).read_bytes()
        if sha_bytes(payload) != adapter["arrays"][name]["sha256"]:
            raise RuntimeError(f"D12.8 input hash mismatch: {name}")
        shape = (height, width, channels) if channels > 1 else (height, width)
        arrays[name] = np.frombuffer(payload, dtype="<f4").reshape(shape).copy()
    outputs = {
        "adaptiveReconstructed": arrays["currentRgba"].copy(),
        "reason": np.zeros((height, width), dtype=np.uint8),
        "analyticOwner": np.zeros((height, width), dtype=np.uint8),
        "structuralValid": np.zeros((height, width), dtype=np.uint8),
        "radius2Interior": np.zeros((height, width), dtype=np.uint8),
        "radius3Interior": np.zeros((height, width), dtype=np.uint8),
        "adaptiveInterior": np.zeros((height, width), dtype=np.uint8),
        "adaptiveRejected": np.zeros((height, width), dtype=np.uint8),
        "riskRgb": np.zeros((height, width, 3), dtype="<f8"),
    }
    threshold = float(spec["frozenGates"]["adaptiveQuality"]["rgbMaximum"])
    for y in range(height):
        for x in range(width):
            oracle = oracle_pixel(spec, fixture, x, y)
            if oracle is None:
                outputs["reason"][y, x] = REASONS["INVALID_CURRENT_ORACLE"]
                continue
            outputs["analyticOwner"][y, x] = oracle["ownerIndex"]
            current_depth_tolerance = max(1.0, oracle["currentDepth"]) / 1024.0
            current_ok = arrays["currentOwner"][y, x] == oracle["passIndex"] and abs(float(arrays["currentDepth"][y, x]) - oracle["currentDepth"]) <= current_depth_tolerance
            if not current_ok:
                outputs["reason"][y, x] = REASONS["INVALID_CURRENT_ORACLE"]
                continue
            vector_x, vector_y = (float(value) for value in arrays["vector"][y, x])
            sample = taps_and_weights(x + vector_x, y - vector_y, width, height)
            if sample is None:
                outputs["reason"][y, x] = REASONS["INVALID_BOUNDS"]
                continue
            taps, weights = sample
            if not all(arrays["previousOwner"][ty, tx] == oracle["passIndex"] for ty, tx in taps):
                outputs["reason"][y, x] = REASONS["INVALID_OWNER"]
                continue
            if arrays["currentRgba"][y, x, 3] <= np.float32(0.999) or not all(arrays["previousRgba"][ty, tx, 3] > np.float32(0.999) for ty, tx in taps):
                outputs["reason"][y, x] = REASONS["INVALID_ALPHA"]
                continue
            sampled_depth = weighted([float(arrays["previousDepth"][ty, tx]) for ty, tx in taps], weights)
            depth_tolerance = max(1.0, oracle["previousDepth"]) / 1024.0
            if abs(sampled_depth - oracle["previousDepth"]) > depth_tolerance:
                outputs["reason"][y, x] = REASONS["INVALID_DEPTH"]
                continue
            outputs["reason"][y, x] = REASONS["VALID"]
            outputs["structuralValid"][y, x] = 1
            r2 = neighborhood(arrays, x, y, 2, oracle["passIndex"], width, height)
            r3 = neighborhood(arrays, x, y, 3, oracle["passIndex"], width, height)
            outputs["radius2Interior"][y, x] = int(r2)
            outputs["radius3Interior"][y, x] = int(r3)
            if not r2:
                continue
            reconstructed = np.empty((4,), dtype="<f4")
            for channel in range(4):
                values = [float(arrays["previousRgba"][ty, tx, channel]) for ty, tx in taps]
                reconstructed[channel] = np.float32(weighted(values, weights))
                if channel < 3:
                    center = float(arrays["currentRgba"][y, x, channel])
                    outputs["riskRgb"][y, x, channel] = sum(abs(weight) * abs(value - center) for weight, value in zip(weights, values)) + abs(float(np.spacing(reconstructed[channel])))
            if float(outputs["riskRgb"][y, x].max()) <= threshold:
                outputs["adaptiveInterior"][y, x] = 1
                outputs["adaptiveReconstructed"][y, x] = reconstructed
            else:
                outputs["adaptiveRejected"][y, x] = 1
    args.output_dir.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, (filename, dtype) in OUTPUTS.items():
        payload = np.ascontiguousarray(outputs[name], dtype=dtype).tobytes()
        target = args.output_dir / filename
        target.write_bytes(payload)
        records[name] = {"uri": str(target), "sha256": sha_bytes(payload), "bytes": len(payload), "shape": list(outputs[name].shape), "dtype": "uint8" if dtype == "u1" else ("little-endian-float64" if dtype == "<f8" else "little-endian-float32")}
    body = {
        "schemaVersion": "bfs.blenderProjectiveMotionDisocclusionConsumerReport.v0.1",
        "experimentId": spec["experimentId"],
        "producer": "python",
        "fixtureId": args.fixture,
        "repeat": args.repeat,
        "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha_file(Path(sys.executable)), "numpy": np.__version__},
        "adapter": {"uri": str(args.adapter_report), "sha256": sha_file(args.adapter_report), "reportHash": adapter["reportHash"]},
        "reasonCodes": REASONS,
        "projectionContract": spec["projectionOracle"],
        "structuralContract": spec["structuralValidity"],
        "candidateContract": spec["candidateContract"],
        "arrays": records,
        "operationCounts": {"consumerProcesses": 1, "pixelsVisited": width * height, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D128_CONSUMER_PY_OK fixture={args.fixture} repeat={args.repeat}")


if __name__ == "__main__":
    main()
