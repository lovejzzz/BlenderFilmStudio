#!/usr/bin/env python3
"""Independent scalar Python projective subpixel reconstructor for B52-D12."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2"
INPUTS = {
    "previousRgba": ("previous.rgba32", 4),
    "currentRgba": ("current.rgba32", 4),
    "previousDepth": ("previous-depth.f32", 1),
    "currentDepth": ("current-depth.f32", 1),
    "previousOwner": ("previous-owner.f32", 1),
    "currentOwner": ("current-owner.f32", 1),
    "vector": ("vector.xy32", 2),
}
OUTPUTS = {
    "reconstructed": ("reconstructed.rgba32", 4, "<f4"),
    "valid": ("valid.u8", 1, "u1"),
    "expectedVector": ("expected-vector.xy32", 2, "<f4"),
    "predictedCurrentDepth": ("predicted-current-depth.f32", 1, "<f4"),
    "predictedPreviousDepth": ("predicted-previous-depth.f32", 1, "<f4"),
    "nearest": ("nearest.rgba32", 4, "<f4"),
    "wrongSign": ("wrong-sign.rgba32", 4, "<f4"),
    "directDepthValid": ("direct-depth-valid.u8", 1, "u1"),
}


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


def transform(fixture: dict, kind: str, frame: int) -> tuple[tuple[float, float, float], tuple[tuple[float, float, float], ...]]:
    row = fixture[f"{kind}ByFrame"][str(frame)]
    return tuple(float(value) for value in row["location"]), rotation_xyz(row["rotationEuler"])


def add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def subtract(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a: tuple[float, float, float], value: float) -> tuple[float, float, float]:
    return (a[0] * value, a[1] * value, a[2] * value)


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def mat_vec(matrix: tuple[tuple[float, float, float], ...], vector: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        matrix[0][0] * vector[0] + matrix[0][1] * vector[1] + matrix[0][2] * vector[2],
        matrix[1][0] * vector[0] + matrix[1][1] * vector[1] + matrix[1][2] * vector[2],
        matrix[2][0] * vector[0] + matrix[2][1] * vector[1] + matrix[2][2] * vector[2],
    )


def mat_t_vec(matrix: tuple[tuple[float, float, float], ...], vector: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        matrix[0][0] * vector[0] + matrix[1][0] * vector[1] + matrix[2][0] * vector[2],
        matrix[0][1] * vector[0] + matrix[1][1] * vector[1] + matrix[2][1] * vector[2],
        matrix[0][2] * vector[0] + matrix[1][2] * vector[1] + matrix[2][2] * vector[2],
    )


def project(point, camera_location, camera_rotation, width: int, height: int, lens: float, sensor_width: float) -> tuple[float, float, float]:
    camera_point = mat_t_vec(camera_rotation, subtract(point, camera_location))
    depth = -float(camera_point[2])
    if depth <= 0.0:
        raise RuntimeError("surface point behind D12 camera")
    sensor_height = sensor_width * height / width
    u = 0.5 + lens * float(camera_point[0]) / (depth * sensor_width)
    v_bottom = 0.5 + lens * float(camera_point[1]) / (depth * sensor_height)
    return u * width - 0.5, (1.0 - v_bottom) * height - 0.5, depth


def oracle_pixel(fixture: dict, scene: dict, x: int, y: int) -> tuple[float, float, float, float]:
    width, height = scene["resolution"]
    camera_spec = scene["camera"]
    lens, sensor_width = float(camera_spec["lensMm"]), float(camera_spec["sensorWidthMm"])
    sensor_height = sensor_width * height / width
    current_frame, previous_frame = 1, 0
    camera_current_location, camera_current_rotation = transform(fixture, "camera", current_frame)
    surface_current_location, surface_current_rotation = transform(fixture, "surface", current_frame)
    u = (x + 0.5) / width
    v_bottom = 1.0 - (y + 0.5) / height
    camera_direction = ((u - 0.5) * sensor_width / lens, (v_bottom - 0.5) * sensor_height / lens, -1.0)
    world_direction = mat_vec(camera_current_rotation, camera_direction)
    plane_normal = mat_vec(surface_current_rotation, (0.0, 0.0, 1.0))
    denominator = dot(world_direction, plane_normal)
    if abs(denominator) < 1e-12:
        raise RuntimeError("D12 ray parallel to plane")
    distance = dot(subtract(surface_current_location, camera_current_location), plane_normal) / denominator
    current_world = add(camera_current_location, scale(world_direction, distance))
    local = mat_t_vec(surface_current_rotation, subtract(current_world, surface_current_location))
    surface_previous_location, surface_previous_rotation = transform(fixture, "surface", previous_frame)
    previous_world = add(surface_previous_location, mat_vec(surface_previous_rotation, local))
    camera_previous_location, camera_previous_rotation = transform(fixture, "camera", previous_frame)
    previous_x, previous_y, previous_depth = project(previous_world, camera_previous_location, camera_previous_rotation, width, height, lens, sensor_width)
    _, _, current_depth = project(current_world, camera_current_location, camera_current_rotation, width, height, lens, sensor_width)
    return previous_x - x, y - previous_y, current_depth, previous_depth


def bilinear(image: np.ndarray, qx: float, qy: float) -> tuple[np.ndarray, tuple[int, int, int, int], bool]:
    height, width = image.shape[:2]
    x0, y0 = math.floor(qx), math.floor(qy)
    if x0 < 0 or y0 < 0 or x0 + 1 >= width or y0 + 1 >= height:
        return np.zeros(image.shape[2:] or (), dtype=np.float32), (x0, y0, x0 + 1, y0 + 1), False
    fx, fy = qx - x0, qy - y0
    weights = ((1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy)
    taps = (image[y0, x0], image[y0, x0 + 1], image[y0 + 1, x0], image[y0 + 1, x0 + 1])
    count = image.shape[2] if image.ndim == 3 else 1
    result = np.empty((count,), dtype=np.float32)
    for channel in range(count):
        values = [float(tap[channel] if count > 1 else tap.item()) for tap in taps]
        result[channel] = values[0] * weights[0] + values[1] * weights[1] + values[2] * weights[2] + values[3] * weights[3]
    return result, (x0, y0, x0 + 1, y0 + 1), True


def round_even(value: float) -> int:
    lower = math.floor(value)
    fraction = value - lower
    if fraction < 0.5:
        return lower
    if fraction > 0.5:
        return lower + 1
    return lower if lower % 2 == 0 else lower + 1


def metric(reconstructed: np.ndarray, current: np.ndarray, mask: np.ndarray) -> dict:
    error = reconstructed[..., :3].astype(np.float64) - current[..., :3].astype(np.float64)
    signed = error[mask]
    absolute = np.abs(signed)
    mse = float(np.mean(np.square(signed)))
    return {
        "maximum": float(np.max(absolute)),
        "p99": float(np.quantile(absolute, 0.99)),
        "rmse": math.sqrt(mse),
        "absoluteSignedMeanPerChannel": [abs(float(np.mean(signed[:, channel]))) for channel in range(3)],
        "psnrUnitRangeDb": 999.0 if mse == 0.0 else -10.0 * math.log10(mse),
    }


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D12 spec identity mismatch")
    if sha256_file(Path(sys.executable)) != spec["runtime"]["python"]["sha256"] or np.__version__ != spec["runtime"]["python"]["numpy"]:
        raise RuntimeError("Python runtime identity mismatch")
    fixture = next((item for item in spec["fixtures"] if item["id"] == args.fixture), None)
    if fixture is None:
        raise RuntimeError("fixture outside frozen D12 roster")
    if args.output_dir.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite D12 reconstruction")
    adapter = json.loads(args.adapter_report.read_text())
    adapter_body = {key: value for key, value in adapter.items() if key != "reportHash"}
    if adapter.get("reportHash") != canonical_hash(adapter_body) or adapter.get("fixtureId") != args.fixture or adapter.get("repeat") != args.repeat:
        raise RuntimeError("D12 adapter report mismatch")
    width, height = spec["scene"]["resolution"]
    arrays = {}
    for name, (filename, channels) in INPUTS.items():
        path = args.input_dir / filename
        payload = path.read_bytes()
        if sha256_bytes(payload) != adapter["arrays"][name]["sha256"]:
            raise RuntimeError(f"D12 adapter array hash mismatch: {name}")
        shape = (height, width, channels) if channels > 1 else (height, width)
        arrays[name] = np.frombuffer(payload, dtype="<f4").reshape(shape).copy()

    current, previous = arrays["currentRgba"], arrays["previousRgba"]
    outputs = {
        "reconstructed": current.copy(),
        "valid": np.zeros((height, width), dtype=np.uint8),
        "expectedVector": np.zeros((height, width, 2), dtype="<f4"),
        "predictedCurrentDepth": np.zeros((height, width), dtype="<f4"),
        "predictedPreviousDepth": np.zeros((height, width), dtype="<f4"),
        "nearest": current.copy(),
        "wrongSign": current.copy(),
        "directDepthValid": np.zeros((height, width), dtype=np.uint8),
    }
    owner_id = np.float32(fixture["passIndex"])
    margin = 4
    for y in range(height):
        for x in range(width):
            expected_x, expected_y, predicted_current_depth, predicted_previous_depth = oracle_pixel(fixture, spec["scene"], x, y)
            outputs["expectedVector"][y, x] = (expected_x, expected_y)
            outputs["predictedCurrentDepth"][y, x] = predicted_current_depth
            outputs["predictedPreviousDepth"][y, x] = predicted_previous_depth
            vector_x, vector_y = (float(value) for value in arrays["vector"][y, x])
            qx, qy = x + vector_x, y - vector_y
            sampled, taps, in_bounds = bilinear(previous, qx, qy)
            sampled_depth, _, depth_bounds = bilinear(arrays["previousDepth"][..., None], qx, qy)
            wrong, _, wrong_bounds = bilinear(previous, x - vector_x, y + vector_y)
            if wrong_bounds:
                outputs["wrongSign"][y, x] = wrong
            nearest_x, nearest_y = round_even(qx), round_even(qy)
            nearest_bounds = 0 <= nearest_x < width and 0 <= nearest_y < height
            if nearest_bounds:
                outputs["nearest"][y, x] = previous[nearest_y, nearest_x]
            x0, y0, x1, y1 = taps
            interior = margin <= x < width - margin and margin <= y < height - margin
            current_meta = arrays["currentOwner"][y, x] == owner_id and current[y, x, 3] > np.float32(0.999)
            previous_meta = False
            if in_bounds:
                previous_meta = all(
                    arrays["previousOwner"][ty, tx] == owner_id and previous[ty, tx, 3] > np.float32(0.999)
                    for ty, tx in ((y0, x0), (y0, x1), (y1, x0), (y1, x1))
                )
            current_tolerance = max(1.0, predicted_current_depth) / 1024.0
            previous_tolerance = max(1.0, predicted_previous_depth) / 1024.0
            current_depth_ok = abs(float(arrays["currentDepth"][y, x]) - predicted_current_depth) <= current_tolerance
            previous_depth_ok = depth_bounds and abs(float(sampled_depth[0]) - predicted_previous_depth) <= previous_tolerance
            valid = interior and in_bounds and nearest_bounds and current_meta and previous_meta and current_depth_ok and previous_depth_ok
            if valid:
                outputs["valid"][y, x] = 1
                outputs["reconstructed"][y, x] = sampled
                direct_tolerance = max(1.0, float(arrays["currentDepth"][y, x])) / 1024.0
                outputs["directDepthValid"][y, x] = int(abs(float(sampled_depth[0]) - float(arrays["currentDepth"][y, x])) <= direct_tolerance)

    mask = outputs["valid"].astype(bool)
    if not np.any(mask):
        raise RuntimeError("D12 reconstruction produced no valid pixels")
    vector_error = arrays["vector"].astype(np.float64) - outputs["expectedVector"].astype(np.float64)
    moving = mask & (np.linalg.norm(outputs["expectedVector"].astype(np.float64), axis=2) > 1e-8)
    measured = moving if np.any(moving) else mask
    endpoint_absolute = np.abs(vector_error[measured])
    fractional = np.abs(arrays["vector"].astype(np.float64) - np.rint(arrays["vector"].astype(np.float64)))[measured]
    args.output_dir.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, (filename, _channels, dtype) in OUTPUTS.items():
        payload = np.ascontiguousarray(outputs[name], dtype=dtype).tobytes(order="C")
        target = args.output_dir / filename
        target.write_bytes(payload)
        records[name] = {"uri": str(target), "sha256": sha256_bytes(payload), "bytes": len(payload), "shape": list(outputs[name].shape), "dtype": "uint8" if dtype == "u1" else "little-endian-float32"}
    body = {
        "schemaVersion": "bfs.blenderProjectiveSubpixelReconstructorReport.v0.1",
        "experimentId": spec["experimentId"],
        "producer": "python",
        "fixtureId": args.fixture,
        "repeat": args.repeat,
        "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha256_file(Path(sys.executable)), "numpy": np.__version__},
        "adapter": {"uri": str(args.adapter_report), "sha256": sha256_file(args.adapter_report), "reportHash": adapter["reportHash"]},
        "formula": spec["projectionOracle"],
        "kernel": spec["reconstruction"]["kernel"],
        "measurements": {
            "validPixels": int(np.count_nonzero(mask)),
            "movingPixels": int(np.count_nonzero(moving)),
            "fractionalComponentFractionBeyond1Over1024": float(np.mean(fractional > 1.0 / 1024.0)),
            "fractionalDistanceP50": float(np.quantile(fractional, 0.5)),
            "vectorEndpointMaximum": float(np.max(endpoint_absolute)),
            "vectorEndpointP99": float(np.quantile(endpoint_absolute, 0.99)),
            "directDepthIdentityRejectedPixels": int(np.count_nonzero(mask & ~outputs["directDepthValid"].astype(bool))),
            "directDepthIdentityRejectedFraction": float(np.mean(~outputs["directDepthValid"][mask].astype(bool))),
            "correct": metric(outputs["reconstructed"], current, mask),
            "nearest": metric(outputs["nearest"], current, mask),
            "wrongSign": metric(outputs["wrongSign"], current, mask),
        },
        "arrays": records,
        "operationCounts": {"reconstructorProcesses": 1, "pixelsVisited": width * height, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D12_RECONSTRUCT_PY_OK fixture={args.fixture} repeat={args.repeat} valid={body['measurements']['validPixels']}")


if __name__ == "__main__":
    main()
