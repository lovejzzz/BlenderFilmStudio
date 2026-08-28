#!/usr/bin/env python3
"""Independent scalar Python consumer for B52-D12.12-H1."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "b0defadbd120f77dfe81bfa16d9dfd4e3a4d4a15ad1c8ddd1176d21f2e13b648"
Q24 = 1 << 24
Q30 = 1 << 30
UINT32_MAX = (1 << 32) - 1
INPUTS = {
    "previousRgba": ("previous.rgba32", 4),
    "currentRgba": ("current.rgba32", 4),
    "previousDepth": ("previous-depth.f32", 1),
    "currentDepth": ("current-depth.f32", 1),
    "previousOwner": ("previous-owner.f32", 1),
    "currentOwner": ("current-owner.f32", 1),
    "previousObjectIndex": ("previous-object-index.f32", 1),
    "currentObjectIndex": ("current-object-index.f32", 1),
    "vector": ("vector.xy32", 2),
}
CONTROL_OUTPUTS = {
    "registered": ("registered.u8", "u1"),
    "structuralValid": ("structural-valid.u8", "u1"),
    "radius2Interior": ("radius2-interior.u8", "u1"),
    "bilinearSupport": ("bilinear-support.u8", "u1"),
    "fullStencil": ("full-stencil.u8", "u1"),
    "directionLeft": ("direction-left.u8", "u1"),
    "directionRight": ("direction-right.u8", "u1"),
    "directionTop": ("direction-top.u8", "u1"),
    "directionBottom": ("direction-bottom.u8", "u1"),
    "neitherHorizontal": ("neither-horizontal.u8", "u1"),
    "analyticValidHistory": ("analytic-valid-history.u8", "u1"),
    "symmetricAccepted": ("symmetric-accepted.u8", "u1"),
    "symmetricRiskQ30": ("symmetric-risk.q30.u32", "<u4"),
}
DECISION_OUTPUTS = {
    "oneSidedEligible": ("one-sided-eligible.u8", "u1"),
    "oneSidedUnavailable": ("one-sided-unavailable.u8", "u1"),
    "accepted": ("accepted.u8", "u1"),
    "reason": ("reason.u8", "u1"),
    "riskQ30": ("risk.q30.u32", "<u4"),
    "reconstructed": ("reconstructed.rgba32", "<f4"),
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
    return tuple(left[index] + right[index] for index in range(3))


def subtract(left, right):
    return tuple(left[index] - right[index] for index in range(3))


def scale(vector, value):
    return tuple(vector[index] * value for index in range(3))


def dot(left, right):
    return sum(left[index] * right[index] for index in range(3))


def mat_vec(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3))


def mat_t_vec(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[row] for row in range(3)) for column in range(3))


def project(point, camera_transform, width, height, lens, sensor_width):
    camera_location, camera_rotation = camera_transform
    camera_point = mat_t_vec(camera_rotation, subtract(point, camera_location))
    depth = -camera_point[2]
    if depth <= 0.0:
        return None
    sensor_height = sensor_width * height / width
    u = 0.5 + lens * camera_point[0] / (depth * sensor_width)
    v_bottom = 0.5 + lens * camera_point[1] / (depth * sensor_height)
    return u * width - 0.5, (1.0 - v_bottom) * height - 0.5, depth


def surface_at(spec: dict, fixture: dict, frame: int, pixel_x: float, pixel_y: float):
    width, height = fixture["resolution"]
    camera_spec = spec["sceneContract"]["camera"]
    lens, sensor_width = float(camera_spec["lensMm"]), float(camera_spec["sensorWidthMm"])
    sensor_height = sensor_width * height / width
    camera = transform(fixture["cameraByFrame"][str(frame)])
    u = (pixel_x + 0.5) / width
    v_bottom = 1.0 - (pixel_y + 0.5) / height
    camera_direction = ((u - 0.5) * sensor_width / lens, (v_bottom - 0.5) * sensor_height / lens, -1.0)
    world_direction = mat_vec(camera[1], camera_direction)
    candidates = []
    for owner in fixture["owners"]:
        owner_transform = transform(owner["transformByFrame"][str(frame)])
        normal = mat_vec(owner_transform[1], (0.0, 0.0, 1.0))
        denominator = dot(world_direction, normal)
        if abs(denominator) < 1e-12:
            continue
        distance = dot(subtract(owner_transform[0], camera[0]), normal) / denominator
        if distance <= 0.0:
            continue
        world_point = add(camera[0], scale(world_direction, distance))
        local_point = mat_t_vec(owner_transform[1], subtract(world_point, owner_transform[0]))
        size_x, size_y = (float(value) for value in owner["sizeWorld"])
        if abs(local_point[0]) <= size_x / 2.0 and abs(local_point[1]) <= size_y / 2.0:
            projected = project(world_point, camera, width, height, lens, sensor_width)
            if projected is not None:
                candidates.append((projected[2], owner, local_point))
    return min(candidates, key=lambda row: row[0]) if candidates else None


def oracle_pixel(spec: dict, fixture: dict, x: int, y: int):
    width, height = fixture["resolution"]
    camera_spec = spec["sceneContract"]["camera"]
    lens, sensor_width = float(camera_spec["lensMm"]), float(camera_spec["sensorWidthMm"])
    current = surface_at(spec, fixture, 1, x, y)
    if current is None:
        return None
    current_depth, owner, local_point = current
    previous_owner = transform(owner["transformByFrame"]["0"])
    previous_world = add(previous_owner[0], mat_vec(previous_owner[1], local_point))
    previous_camera = transform(fixture["cameraByFrame"]["0"])
    previous = project(previous_world, previous_camera, width, height, lens, sensor_width)
    if previous is None:
        return None
    previous_x, previous_y, previous_depth = previous
    visible = None
    if -0.5 <= previous_x < width - 0.5 and -0.5 <= previous_y < height - 0.5:
        visible = surface_at(spec, fixture, 0, previous_x, previous_y)
    valid_history = bool(
        visible is not None
        and visible[1]["analyticOwnerId"] == owner["analyticOwnerId"]
        and abs(float(visible[0]) - previous_depth) <= max(1.0, previous_depth) / 4096.0
    )
    return {
        "ownerId": owner["analyticOwnerId"],
        "ownerToken": np.float32(owner["materialPassIndex"]),
        "objectIndex": np.float32(owner["objectPassIndex"]),
        "currentDepth": current_depth,
        "previousDepth": previous_depth,
        "previousX": previous_x,
        "previousY": previous_y,
        "expectedVector": (previous_x - x, y - previous_y),
        "validHistory": valid_history,
    }


def taps_and_weights(qx, qy, width, height):
    x0, y0 = math.floor(qx), math.floor(qy)
    if x0 < 0 or y0 < 0 or x0 + 1 >= width or y0 + 1 >= height:
        return None
    fx, fy = qx - x0, qy - y0
    return (
        ((y0, x0), (y0, x0 + 1), (y0 + 1, x0), (y0 + 1, x0 + 1)),
        ((1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy),
        x0,
        y0,
        fx,
        fy,
    )


def weighted(values, weights):
    return ((values[0] * weights[0] + values[1] * weights[1]) + values[2] * weights[2]) + values[3] * weights[3]


def exact_scaled(value, scale_value, label):
    scaled = value * scale_value
    integer = int(scaled)
    if scaled != integer:
        raise RuntimeError(f"non-canonical {label}: {value!r}")
    return integer


def ceil_div(numerator, denominator):
    return (numerator + denominator - 1) // denominator


def valid_tap(arrays, y, x, owner, width, height):
    return 0 <= x < width and 0 <= y < height and arrays["previousOwner"][y, x] == owner and arrays["previousRgba"][y, x, 3] > np.float32(0.999)


def current_radius2(arrays, x, y, owner, width, height):
    if x < 2 or y < 2 or x >= width - 2 or y >= height - 2:
        return False
    return all(
        arrays["currentOwner"][ty, tx] == owner and arrays["currentRgba"][ty, tx, 3] > np.float32(0.999)
        for ty in range(y - 2, y + 3)
        for tx in range(x - 2, x + 3)
    )


def write_array(path: Path, value: np.ndarray, dtype: str) -> dict:
    payload = np.ascontiguousarray(value, dtype=dtype).tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"uri": str(path), "sha256": sha_bytes(payload), "bytes": len(payload), "shape": list(value.shape), "dtype": dtype}


def main() -> None:
    cli = arguments()
    if sha_file(cli.spec) != SPEC_SHA256 or cli.output_dir.exists() or cli.report.exists():
        raise RuntimeError("D12.12-H1 spec identity or fresh consumer output violation")
    spec = json.loads(cli.spec.read_text())
    runtime = spec["runtime"]["python"]
    if sha_file(Path(sys.executable)) != runtime["sha256"] or np.__version__ != runtime["numpy"]:
        raise RuntimeError("D12.12-H1 Python runtime identity mismatch")
    fixture = next((row for row in spec["fixtures"] if row["id"] == cli.fixture), None)
    if fixture is None:
        raise RuntimeError("unknown D12.12-H1 fixture")
    width, height = fixture["resolution"]
    adapter = json.loads(cli.adapter_report.read_text())
    adapter_body = {key: value for key, value in adapter.items() if key != "reportHash"}
    if adapter.get("reportHash") != canonical_hash(adapter_body) or adapter.get("fixtureId") != cli.fixture or adapter.get("repeat") != cli.repeat:
        raise RuntimeError("D12.12-H1 adapter report mismatch")
    arrays = {}
    for name, (filename, channels) in INPUTS.items():
        payload = (cli.input_dir / filename).read_bytes()
        if sha_bytes(payload) != adapter["arrays"][name]["sha256"]:
            raise RuntimeError(f"D12.12-H1 input hash mismatch: {name}")
        shape = (height, width, channels) if channels > 1 else (height, width)
        arrays[name] = np.frombuffer(payload, dtype="<f4").reshape(shape).copy()

    masks = {name: np.zeros((height, width), dtype="u1") for name in (
        "registered", "structuralValid", "radius2Interior", "bilinearSupport", "fullStencil",
        "directionLeft", "directionRight", "directionTop", "directionBottom", "neitherHorizontal",
        "analyticValidHistory", "symmetricAccepted", "oneSidedEligible", "oneSidedUnavailable", "accepted",
    )}
    reason = np.zeros((height, width), dtype="u1")
    risk = np.zeros((height, width, 3), dtype="<u4")
    symmetric_risk = np.zeros((height, width, 3), dtype="<u4")
    reconstructed = arrays["currentRgba"].copy()
    threshold = int(spec["frozenCandidate"]["riskThresholdQ30Inclusive"])
    allowance = int(spec["frozenCandidate"]["roundingAllowanceQ30"])

    for y in range(height):
        for x in range(width):
            owner_value = arrays["currentOwner"][y, x]
            if owner_value == np.float32(0.0) or arrays["currentRgba"][y, x, 3] <= np.float32(0.999):
                continue
            masks["registered"][y, x] = 1
            oracle = oracle_pixel(spec, fixture, x, y)
            if oracle is None:
                reason[y, x] = 1
                continue
            masks["analyticValidHistory"][y, x] = int(oracle["validHistory"])
            tolerance = max(1.0, oracle["currentDepth"]) / 1024.0
            if owner_value != oracle["ownerToken"] or arrays["currentObjectIndex"][y, x] != oracle["objectIndex"] or abs(float(arrays["currentDepth"][y, x]) - oracle["currentDepth"]) > tolerance:
                reason[y, x] = 1
                continue
            vector_x, vector_y = (float(value) for value in arrays["vector"][y, x])
            sample = taps_and_weights(x + vector_x, y - vector_y, width, height)
            if sample is None:
                reason[y, x] = 2
                continue
            taps, weights, x0, y0, fx, fy = sample
            if not all(arrays["previousOwner"][ty, tx] == owner_value for ty, tx in taps):
                reason[y, x] = 3
                continue
            if not all(arrays["previousRgba"][ty, tx, 3] > np.float32(0.999) for ty, tx in taps):
                reason[y, x] = 3
                continue
            masks["bilinearSupport"][y, x] = 1
            sampled_depth = weighted([float(arrays["previousDepth"][ty, tx]) for ty, tx in taps], weights)
            if abs(sampled_depth - oracle["previousDepth"]) > max(1.0, oracle["previousDepth"]) / 1024.0:
                reason[y, x] = 4
                continue
            masks["structuralValid"][y, x] = 1
            if not current_radius2(arrays, x, y, owner_value, width, height):
                reason[y, x] = 5
                continue
            masks["radius2Interior"][y, x] = 1
            horizontal = []
            vertical = []
            for yy in (y0, y0 + 1):
                horizontal.append((valid_tap(arrays, yy, x0 - 1, owner_value, width, height), valid_tap(arrays, yy, x0 + 2, owner_value, width, height)))
            for xx in (x0, x0 + 1):
                vertical.append((valid_tap(arrays, y0 - 1, xx, owner_value, width, height), valid_tap(arrays, y0 + 2, xx, owner_value, width, height)))
            full = all(left and right for left, right in horizontal) and all(top and bottom for top, bottom in vertical)
            masks["fullStencil"][y, x] = int(full)
            vertical_full = all(top and bottom for top, bottom in vertical)
            horizontal_full = all(left and right for left, right in horizontal)
            masks["directionLeft"][y, x] = int(all((not left) and right for left, right in horizontal) and vertical_full)
            masks["directionRight"][y, x] = int(all(left and (not right) for left, right in horizontal) and vertical_full)
            masks["directionTop"][y, x] = int(all((not top) and bottom for top, bottom in vertical) and horizontal_full)
            masks["directionBottom"][y, x] = int(all(top and (not bottom) for top, bottom in vertical) and horizontal_full)
            masks["neitherHorizontal"][y, x] = int(any((not left) and (not right) for left, right in horizontal))
            if any((not left) and (not right) for left, right in horizontal) or any((not top) and (not bottom) for top, bottom in vertical):
                masks["oneSidedUnavailable"][y, x] = 1
                reason[y, x] = 6
                continue
            masks["oneSidedEligible"][y, x] = 1
            fx_q24 = exact_scaled(fx, Q24, "motion fraction x")
            fy_q24 = exact_scaled(fy, Q24, "motion fraction y")
            bilinear = np.zeros(4, dtype="<f4")
            for channel in range(4):
                bilinear[channel] = np.float32(weighted([float(arrays["previousRgba"][ty, tx, channel]) for ty, tx in taps], weights))

            def color(yy, xx, channel):
                return exact_scaled(float(arrays["previousRgba"][yy, xx, channel]), Q30, "Q30 RGB")

            for channel in range(3):
                row_values = []
                for row_index, yy in enumerate((y0, y0 + 1)):
                    left, right = horizontal[row_index]
                    values = []
                    if left:
                        values.append(abs(color(yy, x0 - 1, channel) - 2 * color(yy, x0, channel) + color(yy, x0 + 1, channel)))
                    if right:
                        values.append(abs(color(yy, x0, channel) - 2 * color(yy, x0 + 1, channel) + color(yy, x0 + 2, channel)))
                    row_values.append(values)
                column_values = []
                for column_index, xx in enumerate((x0, x0 + 1)):
                    top, bottom = vertical[column_index]
                    values = []
                    if top:
                        values.append(abs(color(y0 - 1, xx, channel) - 2 * color(y0, xx, channel) + color(y0 + 1, xx, channel)))
                    if bottom:
                        values.append(abs(color(y0, xx, channel) - 2 * color(y0 + 1, xx, channel) + color(y0 + 2, xx, channel)))
                    column_values.append(values)
                mx = max(max(values) for values in row_values)
                my = max(max(values) for values in column_values)
                numerator = 2 * (fx_q24 * (Q24 - fx_q24) * mx + fy_q24 * (Q24 - fy_q24) * my)
                risk[y, x, channel] = min(ceil_div(numerator, Q24 * Q24) + allowance, UINT32_MAX)
                if full:
                    symmetric_risk[y, x, channel] = risk[y, x, channel]
            if full and int(symmetric_risk[y, x].max()) <= threshold:
                masks["symmetricAccepted"][y, x] = 1
            if int(risk[y, x].max()) <= threshold:
                masks["accepted"][y, x] = 1
                reason[y, x] = 8
                reconstructed[y, x] = bilinear
            else:
                reason[y, x] = 7

    masks["oneSidedUnavailable"] |= np.logical_and(masks["radius2Interior"].astype(bool), ~masks["oneSidedEligible"].astype(bool)).astype("u1")
    cli.output_dir.mkdir(parents=True, exist_ok=False)
    control_values = {**masks, "symmetricRiskQ30": symmetric_risk}
    control_records = {name: write_array(cli.output_dir / "control" / filename, control_values[name], dtype) for name, (filename, dtype) in CONTROL_OUTPUTS.items()}
    decision_values = {**masks, "reason": reason, "riskQ30": risk, "reconstructed": reconstructed}
    decision_records = {name: write_array(cli.output_dir / "decision" / filename, decision_values[name], dtype) for name, (filename, dtype) in DECISION_OUTPUTS.items()}
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerOneSidedCurvatureHoldoutConsumerReport.v0.1",
        "experimentId": spec["experimentId"],
        "specSha256": SPEC_SHA256,
        "producer": "python",
        "fixtureId": cli.fixture,
        "repeat": cli.repeat,
        "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha_file(Path(sys.executable)), "numpy": np.__version__},
        "adapter": {"uri": str(cli.adapter_report), "sha256": sha_file(cli.adapter_report), "reportHash": adapter["reportHash"]},
        "factor": 1,
        "controlArrays": control_records,
        "decisionArrays": decision_records,
        "reasonCodes": {"NOT_REGISTERED": 0, "INVALID_CURRENT_ORACLE": 1, "INVALID_BOUNDS": 2, "INVALID_OWNER": 3, "INVALID_DEPTH": 4, "OUTSIDE_RADIUS2": 5, "SUPPORT_UNAVAILABLE": 6, "RISK_REJECTED": 7, "ACCEPTED": 8},
        "operationCounts": {"consumerProcesses": 1, "pixelsVisited": width * height, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    cli.report.parent.mkdir(parents=True, exist_ok=True)
    cli.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1212H1_PYTHON fixture={cli.fixture} repeat={cli.repeat} accepted={int(masks['accepted'].sum())}")


if __name__ == "__main__":
    main()
