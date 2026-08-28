#!/usr/bin/env python3
"""Independent formal analyzer for the B52-D12.14-H1 Blender holdout."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "7ff239d91dca6ea8708ce4cac955dd0b129ae067028a77ec1699a43a236195a8"
Q24 = 1 << 24
Q30 = 1 << 30
UINT32_MAX = (1 << 32) - 1
INPUTS = {
    "previousRgba": ("previous.rgba32", "<f4", 4),
    "currentRgba": ("current.rgba32", "<f4", 4),
    "previousDepth": ("previous-depth.f32", "<f4", 1),
    "currentDepth": ("current-depth.f32", "<f4", 1),
    "previousOwner": ("previous-owner.f32", "<f4", 1),
    "currentOwner": ("current-owner.f32", "<f4", 1),
    "previousObjectIndex": ("previous-object-index.f32", "<f4", 1),
    "currentObjectIndex": ("current-object-index.f32", "<f4", 1),
    "vector": ("vector.xy32", "<f4", 2),
    "vectorNext": ("vector-next.xy32", "<f4", 2),
}
CONTROLS = {
    "registered": ("control/registered.u8", "u1", 1),
    "structuralValid": ("control/structural-valid.u8", "u1", 1),
    "radius2Interior": ("control/radius2-interior.u8", "u1", 1),
    "bilinearSupport": ("control/bilinear-support.u8", "u1", 1),
    "fullStencil": ("control/full-stencil.u8", "u1", 1),
    "directionLeft": ("control/direction-left.u8", "u1", 1),
    "directionRight": ("control/direction-right.u8", "u1", 1),
    "directionTop": ("control/direction-top.u8", "u1", 1),
    "directionBottom": ("control/direction-bottom.u8", "u1", 1),
    "neitherHorizontal": ("control/neither-horizontal.u8", "u1", 1),
    "analyticValidHistory": ("control/analytic-valid-history.u8", "u1", 1),
    "symmetricAccepted": ("control/symmetric-accepted.u8", "u1", 1),
    "symmetricRiskQ30": ("control/symmetric-risk.q30.u32", "<u4", 3),
}
DECISIONS = {
    "oneSidedEligible": ("decision/one-sided-eligible.u8", "u1", 1),
    "oneSidedUnavailable": ("decision/one-sided-unavailable.u8", "u1", 1),
    "accepted": ("decision/accepted.u8", "u1", 1),
    "reason": ("decision/reason.u8", "u1", 1),
    "riskQ30": ("decision/risk.q30.u32", "<u4", 3),
    "reconstructed": ("decision/reconstructed.rgba32", "<f4", 4),
}
DIRECTION_MASK = {
    "LEFT_MISSING_RIGHT_AVAILABLE": "directionLeft",
    "RIGHT_MISSING_LEFT_AVAILABLE": "directionRight",
    "TOP_MISSING_BOTTOM_AVAILABLE": "directionTop",
    "BOTTOM_MISSING_TOP_AVAILABLE": "directionBottom",
    "NEITHER_HORIZONTAL_AVAILABLE": "neitherHorizontal",
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


def self_ok(value: dict, field: str) -> bool:
    return value.get(field) == canonical_hash({key: row for key, row in value.items() if key != field})


def normalized_array_records(records: dict) -> dict:
    return {name: {key: value for key, value in row.items() if key != "uri"} for name, row in records.items()}


def normalized_consumer_report(report: dict, *, for_repeat: bool) -> dict:
    ignored = {"reportHash", "pid", "producer", "runtime"}
    if for_repeat:
        ignored.add("repeat")
    value = {key: row for key, row in report.items() if key not in ignored}
    value["controlArrays"] = normalized_array_records(report["controlArrays"])
    value["decisionArrays"] = normalized_array_records(report["decisionArrays"])
    if for_repeat:
        value["adapter"] = {"arraysBoundByConsumer": True}
    return value


def normalized_adapter_report(report: dict) -> dict:
    value = {key: row for key, row in report.items() if key not in {"reportHash", "pid", "repeat", "inputs"}}
    value["arrays"] = normalized_array_records(report["arrays"])
    return value


def expected_multipart_channels(layer: str) -> dict[str, list[str]]:
    return {
        f"{layer}.Combined": [f"{layer}.Combined.{channel}" for channel in ("R", "G", "B", "A")],
        f"{layer}.Depth": [f"{layer}.Depth.Z"],
        f"{layer}.Vector": [f"{layer}.Vector.{channel}" for channel in ("X", "Y", "Z", "W")],
        f"{layer}.Object Index": [f"{layer}.Object Index.X"],
        f"{layer}.Material Index": [f"{layer}.Material Index.X"],
    }


def git_tree(uri: str) -> str:
    return subprocess.run(["git", "rev-parse", f"HEAD:{uri}"], check=True, text=True, capture_output=True).stdout.strip()


def load_array(path: Path, dtype: str, height: int, width: int, channels: int):
    payload = path.read_bytes()
    shape = (height, width, channels) if channels > 1 else (height, width)
    expected = int(np.prod(shape)) * np.dtype(dtype).itemsize
    if len(payload) != expected:
        raise RuntimeError(f"D12.14-H1 array length mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy(), payload


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
    camera_point = mat_t_vec(camera_transform[1], subtract(point, camera_transform[0]))
    depth = -camera_point[2]
    if depth <= 0.0:
        return None
    sensor_height = sensor_width * height / width
    u = 0.5 + lens * camera_point[0] / (depth * sensor_width)
    v_bottom = 0.5 + lens * camera_point[1] / (depth * sensor_height)
    return u * width - 0.5, (1.0 - v_bottom) * height - 0.5, depth


def effective_fixture(spec: dict, fixture: dict) -> dict:
    camera = spec["sceneContract"]["camera"]
    result = {
        **fixture,
        "cameraByFrame": {
            frame: {"location": camera["locationByFrame"][frame], "rotationEuler": camera["rotationEulerByFrame"][frame]}
            for frame in ("0", "1", "2")
        },
    }
    owners = []
    for row in fixture["owners"]:
        owner = dict(row)
        if owner["role"] == "background":
            background = spec["sceneContract"]["background"]
            owner.update({"sizeWorld": background["sizeWorld"], "transformByFrame": background["transformByFrame"]})
        else:
            owner["sizeWorld"] = spec["sceneContract"]["foreground"]["sizeWorld"]
        owners.append(owner)
    result["owners"] = owners
    return result


def animation_matches(rows: list[dict], transforms: dict, tolerance: float = 1e-6) -> bool:
    expected_paths = {"location": "location", "rotation_euler": "rotationEuler"}
    indexed = {(row.get("dataPath"), row.get("arrayIndex")): row for row in rows}
    if set(indexed) != {(path, index) for path in expected_paths for index in range(3)}:
        return False
    for data_path, source_key in expected_paths.items():
        for index in range(3):
            keyframes = indexed[(data_path, index)].get("keyframes", [])
            if len(keyframes) != 3:
                return False
            for frame, keyframe in zip((0, 1, 2), keyframes):
                if int(keyframe[0]) != frame or keyframe[2] != "LINEAR":
                    return False
                if abs(float(keyframe[1]) - float(transforms[str(frame)][source_key][index])) > tolerance:
                    return False
    return True


def surface_at(spec, fixture, frame, pixel_x, pixel_y):
    width, height = fixture["resolution"]
    camera_spec = spec["sceneContract"]["camera"]
    lens, sensor_width = float(camera_spec["lensMm"]), float(camera_spec["sensorWidthMm"])
    sensor_height = sensor_width * height / width
    camera = transform(fixture["cameraByFrame"][str(frame)])
    u = (pixel_x + 0.5) / width
    v_bottom = 1.0 - (pixel_y + 0.5) / height
    direction = ((u - 0.5) * sensor_width / lens, (v_bottom - 0.5) * sensor_height / lens, -1.0)
    world_direction = mat_vec(camera[1], direction)
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
            if projected:
                candidates.append((projected[2], owner, local_point))
    return min(candidates, key=lambda row: row[0]) if candidates else None


def oracle_pixel(spec, fixture, x, y):
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
        and abs(float(visible[0]) - previous_depth) <= float(spec["projectionOracle"]["tolerances"]["depthMaximumAbsoluteError"])
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
        x0, y0, fx, fy,
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


def replay(spec, fixture, arrays):
    width, height = fixture["resolution"]
    names = (
        "registered", "structuralValid", "radius2Interior", "bilinearSupport", "fullStencil",
        "directionLeft", "directionRight", "directionTop", "directionBottom", "neitherHorizontal",
        "analyticValidHistory", "symmetricAccepted", "oneSidedEligible", "oneSidedUnavailable", "accepted",
    )
    masks = {name: np.zeros((height, width), dtype="u1") for name in names}
    reason = np.zeros((height, width), dtype="u1")
    risk = np.zeros((height, width, 3), dtype="<u4")
    symmetric_risk = np.zeros((height, width, 3), dtype="<u4")
    reconstructed = arrays["currentRgba"].copy()
    owner_truth = np.zeros((height, width), dtype="<u4")
    vector_mismatch = 0
    threshold = int(spec["frozenCandidate"]["riskThresholdQ30Inclusive"])
    allowance = int(spec["frozenCandidate"]["roundingAllowanceQ30"])
    vector_oracle_tolerance = float(spec["projectionOracle"]["tolerances"]["vectorMaximumAbsoluteErrorPixels"])
    depth_oracle_tolerance = float(spec["projectionOracle"]["tolerances"]["depthMaximumAbsoluteError"])

    def valid_tap(yy, xx, owner):
        return 0 <= xx < width and 0 <= yy < height and arrays["previousOwner"][yy, xx] == owner and arrays["previousRgba"][yy, xx, 3] > np.float32(0.999)

    def radius2(xx, yy, owner):
        if xx < 2 or yy < 2 or xx >= width - 2 or yy >= height - 2:
            return False
        return all(
            arrays["currentOwner"][ty, tx] == owner and arrays["currentRgba"][ty, tx, 3] > np.float32(0.999)
            for ty in range(yy - 2, yy + 3) for tx in range(xx - 2, xx + 3)
        )

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
            owner_truth[y, x] = int(oracle["ownerToken"])
            masks["analyticValidHistory"][y, x] = int(oracle["validHistory"])
            if max(abs(float(arrays["vector"][y, x, index]) - oracle["expectedVector"][index]) for index in range(2)) > vector_oracle_tolerance:
                vector_mismatch += 1
            if owner_value != oracle["ownerToken"] or arrays["currentObjectIndex"][y, x] != oracle["objectIndex"] or abs(float(arrays["currentDepth"][y, x]) - oracle["currentDepth"]) > depth_oracle_tolerance:
                reason[y, x] = 1
                continue
            vector_x, vector_y = (float(value) for value in arrays["vector"][y, x])
            sample = taps_and_weights(x + vector_x, y - vector_y, width, height)
            if sample is None:
                reason[y, x] = 2
                continue
            taps, weights, x0, y0, fx, fy = sample
            if not all(arrays["previousOwner"][ty, tx] == owner_value for ty, tx in taps) or not all(arrays["previousRgba"][ty, tx, 3] > np.float32(0.999) for ty, tx in taps):
                reason[y, x] = 3
                continue
            masks["bilinearSupport"][y, x] = 1
            sampled_depth = weighted([float(arrays["previousDepth"][ty, tx]) for ty, tx in taps], weights)
            if abs(sampled_depth - oracle["previousDepth"]) > max(1.0, oracle["previousDepth"]) / 1024.0:
                reason[y, x] = 4
                continue
            masks["structuralValid"][y, x] = 1
            if not radius2(x, y, owner_value):
                reason[y, x] = 5
                continue
            masks["radius2Interior"][y, x] = 1
            horizontal = [(valid_tap(yy, x0 - 1, owner_value), valid_tap(yy, x0 + 2, owner_value)) for yy in (y0, y0 + 1)]
            vertical = [(valid_tap(y0 - 1, xx, owner_value), valid_tap(y0 + 2, xx, owner_value)) for xx in (x0, x0 + 1)]
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
            fx_q24, fy_q24 = exact_scaled(fx, Q24, "motion fraction x"), exact_scaled(fy, Q24, "motion fraction y")
            bilinear = np.zeros(4, dtype="<f4")
            for channel in range(4):
                bilinear[channel] = np.float32(weighted([float(arrays["previousRgba"][ty, tx, channel]) for ty, tx in taps], weights))

            def color(yy, xx, channel):
                return exact_scaled(float(arrays["previousRgba"][yy, xx, channel]), Q30, "Q30 RGB")

            for channel in range(3):
                rows = []
                for row_index, yy in enumerate((y0, y0 + 1)):
                    left, right = horizontal[row_index]
                    values = []
                    if left:
                        values.append(abs(color(yy, x0 - 1, channel) - 2 * color(yy, x0, channel) + color(yy, x0 + 1, channel)))
                    if right:
                        values.append(abs(color(yy, x0, channel) - 2 * color(yy, x0 + 1, channel) + color(yy, x0 + 2, channel)))
                    rows.append(values)
                columns = []
                for column_index, xx in enumerate((x0, x0 + 1)):
                    top, bottom = vertical[column_index]
                    values = []
                    if top:
                        values.append(abs(color(y0 - 1, xx, channel) - 2 * color(y0, xx, channel) + color(y0 + 1, xx, channel)))
                    if bottom:
                        values.append(abs(color(y0, xx, channel) - 2 * color(y0 + 1, xx, channel) + color(y0 + 2, xx, channel)))
                    columns.append(values)
                mx, my = max(max(values) for values in rows), max(max(values) for values in columns)
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
    return {**masks, "reason": reason, "riskQ30": risk, "symmetricRiskQ30": symmetric_risk, "reconstructed": reconstructed, "ownerTruth": owner_truth, "vectorMismatch": vector_mismatch}


def measurement_region(fixture):
    width, height = fixture["resolution"]
    x0, y0, x1, y1 = fixture["measurementRegionNormalized"]
    xs = (np.arange(width, dtype=np.float64) + 0.5) / width
    ys = (np.arange(height, dtype=np.float64) + 0.5) / height
    return np.logical_and.outer((ys >= y0) & (ys <= y1), (xs >= x0) & (xs <= x1))


def metric(reconstructed, current, mask):
    values = (reconstructed[..., :3].astype(np.float64) - current[..., :3].astype(np.float64))[mask]
    return {
        "maximum": float(np.abs(values).max()) if values.size else None,
        "rmse": float(np.sqrt(np.mean(values * values))) if values.size else None,
        "sampleCount": int(values.size),
    }


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--analysis-receipt", type=Path, required=True)
    return parser.parse_args()


def main():
    cli = arguments()
    if sha_file(cli.spec) != SPEC_SHA256 or cli.output.exists() or cli.analysis_receipt.exists():
        raise RuntimeError("D12.14-H1 analyzer identity or fresh output violation")
    spec = json.loads(cli.spec.read_text())
    runtime = spec["runtime"]["python"]
    if sha_file(Path(sys.executable)) != runtime["sha256"] or np.__version__ != runtime["numpy"]:
        raise RuntimeError("D12.14-H1 analyzer runtime identity mismatch")
    parent_checks = {}
    for name, row in spec["parents"].items():
        if "uri" in row and "sha256" in row:
            parent_checks[name] = sha_file(Path(row["uri"])) == row["sha256"]
    parent_trees = {
        "rigidCalibrationFormalRoot": git_tree(spec["parents"]["rigidCalibrationFormalRoot"]["uri"]),
        "rejectedRenderedHoldoutFormalRoot": git_tree(spec["parents"]["rejectedRenderedHoldoutFormalRoot"]["uri"]),
    }
    parent_tree_exact = (
        parent_trees["rigidCalibrationFormalRoot"] == spec["parents"]["rigidCalibrationFormalRoot"]["gitTree"]
        and parent_trees["rejectedRenderedHoldoutFormalRoot"] == spec["parents"]["rejectedRenderedHoldoutFormalRoot"]["gitTree"]
    )
    tool_hashes = {uri: sha_file(Path(uri)) for uri in spec["freshness"]["newFormalToolPaths"]}
    report_hashes = True
    source_bindings = True
    mesh_transform_exact = True
    source_repeat_identity = True
    adapter_repeat_identity = True
    cross_language = True
    consumer_repeat_identity = True
    typed_envelopes = True
    report_semantic_identity = True
    replay_exact = True
    current_rgb_metamorphism = True
    material_domain_exact = True
    object_negative_control = True
    fallback_exact = True
    full_identity = True
    risk_underbound = 0
    false_invalid = 0
    material_aliases = 0
    error_values = []
    cells = []
    repeat_fingerprints = {}
    repeat_report_fingerprints = {}
    source_fingerprints = {}
    adapter_fingerprints = {}
    adapter_report_fingerprints = {}
    source_mesh_fingerprints = {}

    for raw_fixture in spec["fixtures"]:
        fixture = effective_fixture(spec, raw_fixture)
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        repeat_fingerprints[fixture_id] = {}
        repeat_report_fingerprints[fixture_id] = {}
        source_fingerprints[fixture_id] = {}
        adapter_fingerprints[fixture_id] = {}
        adapter_report_fingerprints[fixture_id] = {}
        source_mesh_fingerprints[fixture_id] = {}
        for repeat in (1, 2):
            source_hashes = {}
            source_semantics = {}
            for frame in (0, 1):
                base = cli.root / "sources" / fixture_id / f"R{repeat}"
                exr, report_path = base / f"frame-{frame}.exr", base / f"frame-{frame}-report.json"
                report = json.loads(report_path.read_text())
                report_hashes &= self_ok(report, "reportHash")
                source_bindings &= (
                    report.get("fixtureId") == fixture_id and report.get("repeat") == repeat and report.get("frame") == frame
                    and report.get("probeOnly") is False and report.get("output", {}).get("sha256") == sha_file(exr)
                    and report.get("fixture") == fixture
                )
                observed_owners = {
                    owner.get("analyticOwnerId"): owner
                    for owner in report.get("sceneStructure", {}).get("owners", [])
                }
                mesh_transform_exact &= set(observed_owners) == {owner["analyticOwnerId"] for owner in fixture["owners"]}
                animation_owners = report.get("animation", {}).get("owners", {})
                for owner in fixture["owners"]:
                    observed = observed_owners.get(owner["analyticOwnerId"], {})
                    columns, rows = (int(value) for value in owner["subdivisions"])
                    expected_transform = owner["transformByFrame"][str(frame)]
                    mesh_transform_exact &= (
                        observed.get("role") == owner["role"]
                        and observed.get("vertices") == (columns + 1) * (rows + 1)
                        and observed.get("polygons") == columns * rows
                        and observed.get("scale") == [1.0, 1.0, 1.0]
                        and isinstance(observed.get("meshDataName"), str)
                        and isinstance(observed.get("localVertexSha256"), str)
                        and len(observed.get("localVertexSha256", "")) == 64
                        and np.allclose(observed.get("location", []), expected_transform["location"], rtol=0.0, atol=1e-6)
                        and np.allclose(observed.get("rotationEuler", []), expected_transform["rotationEuler"], rtol=0.0, atol=1e-6)
                        and animation_matches(animation_owners.get(observed.get("name"), []), owner["transformByFrame"])
                    )
                    fingerprint = {
                        key: observed.get(key)
                        for key in ("meshDataName", "localVertexSha256", "vertices", "polygons", "scale")
                    }
                    prior = source_mesh_fingerprints[fixture_id].setdefault(owner["analyticOwnerId"], fingerprint)
                    mesh_transform_exact &= prior == fingerprint
                source_hashes[frame] = sha_file(exr)
                source_semantics[frame] = {
                    "fixture": report.get("fixture"), "runtime": report.get("runtime"),
                    "sceneStructure": report.get("sceneStructure"), "animation": report.get("animation"),
                    "passState": report.get("passState"), "operationCounts": report.get("operationCounts"),
                }
            source_fingerprints[fixture_id][repeat] = {"exr": source_hashes, "semantics": source_semantics}

            adapter_base = cli.root / "adapters" / fixture_id / f"R{repeat}"
            adapter_report = json.loads((adapter_base / "report.json").read_text())
            report_hashes &= self_ok(adapter_report, "reportHash")
            render = spec["sceneContract"]["render"]
            expected_roster = render["expectedSubimages"]
            expected_channels = expected_multipart_channels(render["viewLayer"])
            source_bindings &= (
                adapter_report.get("multipart", {}).get("previousRoster") == expected_roster
                and adapter_report.get("multipart", {}).get("currentRoster") == expected_roster
                and adapter_report.get("multipart", {}).get("previousChannels") == expected_channels
                and adapter_report.get("multipart", {}).get("currentChannels") == expected_channels
            )
            adapter_report_fingerprints[fixture_id][repeat] = normalized_adapter_report(adapter_report)
            arrays = {}
            adapter_hashes = {}
            for name, (filename, dtype, channels) in INPUTS.items():
                value, payload = load_array(adapter_base / "arrays" / filename, dtype, height, width, channels)
                arrays[name] = value
                adapter_hashes[name] = sha_bytes(payload)
                source_bindings &= adapter_report["arrays"][name]["sha256"] == adapter_hashes[name]
            adapter_fingerprints[fixture_id][repeat] = adapter_hashes
            declared_material = {0.0, *(float(owner["materialPassIndex"]) for owner in fixture["owners"])}
            declared_nonzero = {float(owner["materialPassIndex"]) for owner in fixture["owners"]}
            shared_object = float(fixture["owners"][0]["objectPassIndex"])
            material_domain_exact &= len(declared_nonzero) == len(fixture["owners"])
            material_domain_exact &= all(1.0 <= token <= 32767.0 for token in declared_nonzero)
            for name in ("previousOwner", "currentOwner"):
                observed_material = set(float(value) for value in np.unique(arrays[name]))
                material_domain_exact &= observed_material.issubset(declared_material) and declared_nonzero.issubset(observed_material)
            object_negative_control &= fixture["owners"][0]["objectPassIndex"] == fixture["owners"][1]["objectPassIndex"]
            for name in ("previousObjectIndex", "currentObjectIndex"):
                observed_object = set(float(value) for value in np.unique(arrays[name]))
                object_negative_control &= observed_object.issubset({0.0, shared_object}) and shared_object in observed_object

            replayed = replay(spec, fixture, arrays)
            metamorphic_arrays = {name: value for name, value in arrays.items()}
            metamorphic_arrays["currentRgba"] = arrays["currentRgba"].copy()
            metamorphic_arrays["currentRgba"][..., :3] = np.float32(0.3125)
            metamorphic = replay(spec, fixture, metamorphic_arrays)
            current_rgb_metamorphism &= all(
                np.array_equal(replayed[name], metamorphic[name])
                for name in (*CONTROLS, *(name for name in DECISIONS if name != "reconstructed"))
            )
            producer_values, producer_hashes = {}, {}
            producer_reports = {}
            for producer in ("python", "node"):
                consumer_base = cli.root / "consumers" / producer / fixture_id / f"R{repeat}"
                consumer_report = json.loads((consumer_base / "report.json").read_text())
                report_hashes &= self_ok(consumer_report, "reportHash")
                producer_reports[producer] = consumer_report
                values, hashes = {}, {}
                for name, (relative, dtype, channels) in {**CONTROLS, **DECISIONS}.items():
                    value, payload = load_array(consumer_base / "arrays" / relative, dtype, height, width, channels)
                    values[name], hashes[name] = value, sha_bytes(payload)
                    section = "controlArrays" if name in CONTROLS else "decisionArrays"
                    source_bindings &= consumer_report[section][name]["sha256"] == hashes[name]
                producer_values[producer], producer_hashes[producer] = values, hashes
            cross_language &= producer_hashes["python"] == producer_hashes["node"]
            report_semantic_identity &= normalized_consumer_report(producer_reports["python"], for_repeat=False) == normalized_consumer_report(producer_reports["node"], for_repeat=False)
            repeat_fingerprints[fixture_id][repeat] = producer_hashes["python"]
            repeat_report_fingerprints[fixture_id][repeat] = normalized_consumer_report(producer_reports["python"], for_repeat=True)
            values = producer_values["python"]
            expected = {name: replayed[name] for name in CONTROLS}
            expected.update({name: replayed[name] for name in DECISIONS})
            replay_exact &= all(np.array_equal(values[name], expected[name]) for name in expected)
            accepted = values["accepted"].astype(bool)
            eligible = values["oneSidedEligible"].astype(bool)
            radius2 = values["radius2Interior"].astype(bool)
            full = values["fullStencil"].astype(bool)
            fallback_exact &= np.array_equal(values["reconstructed"][~accepted], arrays["currentRgba"][~accepted])
            full_identity &= (
                np.array_equal(values["riskQ30"][full], values["symmetricRiskQ30"][full])
                and np.array_equal(values["accepted"][full], values["symmetricAccepted"][full])
            )
            for y, x in np.argwhere(eligible):
                for channel in range(3):
                    actual = math.ceil(abs(float(values["reconstructed"][y, x, channel]) - float(arrays["currentRgba"][y, x, channel])) * Q30)
                    risk_underbound += int(actual > int(values["riskQ30"][y, x, channel]))
            if accepted.any():
                error_values.append((values["reconstructed"][..., :3].astype(np.float64) - arrays["currentRgba"][..., :3].astype(np.float64))[accepted])
            false_invalid += int(np.logical_and(accepted, ~values["analyticValidHistory"].astype(bool)).sum())
            material_aliases += int(np.logical_and(accepted, arrays["currentOwner"] != replayed["ownerTruth"].astype("<f4")).sum())

            region = measurement_region(fixture)
            direction_name = DIRECTION_MASK.get(fixture["primaryDirectionalClass"])
            direction = values[direction_name].astype(bool) if direction_name else full
            measured = np.logical_and(region, direction)
            directional_eligible = int(np.logical_and(measured, eligible).sum())
            directional_accepted = int(np.logical_and(measured, accepted).sum())
            owner_rows = {}
            for owner in fixture["owners"]:
                token = np.float32(owner["materialPassIndex"])
                owner_mask = arrays["currentOwner"] == token
                denominator = int(np.logical_and(radius2, owner_mask).sum())
                numerator = int(np.logical_and(accepted, np.logical_and(radius2, owner_mask)).sum())
                owner_rows[owner["analyticOwnerId"]] = {"radius2": denominator, "accepted": numerator, "retention": numerator / denominator if denominator else None}
            quality = metric(values["reconstructed"], arrays["currentRgba"], accepted)
            cells.append({
                "cell": f"{fixture_id}/R{repeat}", "fixtureId": fixture_id, "repeat": repeat,
                "primaryDirectionalClass": fixture["primaryDirectionalClass"],
                "registered": int(values["registered"].sum()), "structuralValid": int(values["structuralValid"].sum()),
                "radius2": int(radius2.sum()), "fullStencil": int(full.sum()),
                "oneSidedEligible": int(eligible.sum()), "oneSidedUnavailable": int(values["oneSidedUnavailable"].sum()),
                "accepted": int(accepted.sum()), "fullStencilAccepted": int(np.logical_and(full, accepted).sum()),
                "oneSidedAccepted": int(np.logical_and(~full, accepted).sum()),
                "oneSidedRiskRejected": int(np.logical_and(np.logical_and(eligible, ~full), ~accepted).sum()),
                "otherRiskRejected": int(np.logical_and(np.logical_and(eligible, full), ~accepted).sum()),
                "directionalWitnesses": int(measured.sum()), "directionalEligible": directional_eligible,
                "directionalAccepted": directional_accepted,
                "directionalAcceptance": directional_accepted / directional_eligible if directional_eligible else None,
                "acceptedToRadius2": int(accepted.sum()) / int(radius2.sum()) if radius2.any() else None,
                "perOwner": owner_rows, "quality": quality, "vectorMismatch": replayed["vectorMismatch"],
            })
            for subtree in ("controlArrays", "decisionArrays"):
                envelope_base = cli.root / "envelopes" / fixture_id / f"R{repeat}" / subtree
                py_payload = (envelope_base / "python.bin").read_bytes()
                node_payload = (envelope_base / "node.bin").read_bytes()
                typed_envelopes &= py_payload == node_payload

        source_repeat_identity &= source_fingerprints[fixture_id][1] == source_fingerprints[fixture_id][2]
        adapter_repeat_identity &= adapter_fingerprints[fixture_id][1] == adapter_fingerprints[fixture_id][2]
        adapter_repeat_identity &= adapter_report_fingerprints[fixture_id][1] == adapter_report_fingerprints[fixture_id][2]
        consumer_repeat_identity &= repeat_fingerprints[fixture_id][1] == repeat_fingerprints[fixture_id][2]
        report_semantic_identity &= repeat_report_fingerprints[fixture_id][1] == repeat_report_fingerprints[fixture_id][2]

    if error_values:
        all_errors = np.concatenate(error_values, axis=0)
        global_quality = {"maximum": float(np.abs(all_errors).max()), "rmse": float(np.sqrt(np.mean(all_errors * all_errors))), "sampleCount": int(all_errors.size)}
    else:
        global_quality = {"maximum": None, "rmse": None, "sampleCount": 0}
    direction_threshold = spec["directionalMeasurementContract"]
    top_contract = True
    bottom_contract = True
    neither_witness_contract = True
    neither_zero_accept_contract = True
    for row in cells:
        klass = row["primaryDirectionalClass"]
        if klass == "TOP_MISSING_BOTTOM_AVAILABLE":
            top_contract &= (
                row["directionalEligible"] >= direction_threshold["topMinimumDirectionalEligiblePerRepeat"]
                and row["directionalAccepted"] >= direction_threshold["topMinimumDirectionalAcceptedPerRepeat"]
                and row["directionalAcceptance"] is not None
                and row["directionalAcceptance"] >= direction_threshold["topMinimumDirectionalAcceptancePerRepeat"]
            )
        if klass == "BOTTOM_MISSING_TOP_AVAILABLE":
            bottom_contract &= (
                row["directionalEligible"] >= direction_threshold["bottomMinimumDirectionalEligiblePerRepeat"]
                and row["directionalAccepted"] >= direction_threshold["bottomMinimumDirectionalAcceptedPerRepeat"]
                and row["directionalAcceptance"] is not None
                and row["directionalAcceptance"] >= direction_threshold["bottomMinimumDirectionalAcceptancePerRepeat"]
            )
        if klass == "NEITHER_HORIZONTAL_AVAILABLE":
            neither_witness_contract &= row["directionalWitnesses"] >= direction_threshold["neitherMinimumWitnessesPerRepeat"]
            neither_zero_accept_contract &= row["directionalAccepted"] <= direction_threshold["neitherAcceptedMaximumPerRepeat"]
    direction_checks = {
        "TOP_DIRECTIONAL_ACCEPTANCE": top_contract,
        "BOTTOM_DIRECTIONAL_ACCEPTANCE": bottom_contract,
        "NEITHER_MINIMUM_WITNESSES": neither_witness_contract,
    }
    direction_contract = all(direction_checks.values())

    source_isolation = True
    python_source = Path("scripts/reconstruct-b52-d12-14-h1-rigid-directional.py").read_text()
    node_source = Path("scripts/reconstruct-b52-d12-14-h1-rigid-directional.mjs").read_text()
    for fragment in ("currentRgba\"][y, x, 0", "currentRgba\"][y, x, 1", "currentRgba\"][y, x, 2"):
        source_isolation &= fragment not in python_source
    for fragment in ("currentRgba[rgba(pixel, 0)]", "currentRgba[rgba(pixel, 1)]", "currentRgba[rgba(pixel, 2)]"):
        source_isolation &= fragment not in node_source
    quality_limit = float(spec["hardGates"]["acceptedRgbMaximum"])
    rmse_limit = float(spec["hardGates"]["acceptedRgbRmseMaximum"])
    hard_checks = {
        "PARENT_BYTES": all(parent_checks.values()), "PARENT_FORMAL_TREES": parent_tree_exact,
        "SOURCE_REPORT_EXR_BINDINGS": report_hashes and source_bindings,
        "FIXED_MESH_SCALE_DECLARED_TRANSFORMS": mesh_transform_exact,
        "SOURCE_REPEAT_IDENTITY": source_repeat_identity, "ADAPTER_REPEAT_IDENTITY": adapter_repeat_identity,
        "CONSUMER_REPEAT_IDENTITY": consumer_repeat_identity, "CROSS_LANGUAGE_EVERY_ARRAY": cross_language,
        "NORMALIZED_CONSUMER_REPORT_IDENTITY": report_semantic_identity,
        "TYPED_ENVELOPE_EXACT": typed_envelopes, "INDEPENDENT_PROJECTION_STRUCTURAL_RISK_REPLAY": replay_exact,
        "VECTOR_PROJECTION_ORACLE": all(row["vectorMismatch"] == 0 for row in cells),
        "MATERIAL_TOKEN_DOMAIN": material_domain_exact, "OBJECT_INDEX_SHARED_NEGATIVE_CONTROL": object_negative_control,
        "FULL_STENCIL_BASELINE_IDENTITY": full_identity, "RISK_UNDERBOUND_ZERO": risk_underbound == 0,
        "ACCEPTED_RGB_MAXIMUM": global_quality["maximum"] is None or global_quality["maximum"] <= quality_limit,
        "ACCEPTED_RGB_RMSE": global_quality["rmse"] is None or global_quality["rmse"] <= rmse_limit,
        "FALSE_INVALID_HISTORY_ZERO": false_invalid == 0, "MATERIAL_ALIAS_ZERO": material_aliases == 0,
        "FALLBACK_EXACT": fallback_exact,
        "CURRENT_RGB_DECISION_METAMORPHISM": source_isolation and current_rgb_metamorphism,
        "NEITHER_ACCEPTED_ZERO": neither_zero_accept_contract,
    }
    hard_passed = all(hard_checks.values())
    if not hard_passed:
        verdict = spec["decision"]["rejectedVerdict"]
    elif not direction_contract:
        verdict = spec["decision"]["directionFailureVerdict"]
    else:
        verdict = spec["decision"]["supportedVerdict"]
    supported = verdict == spec["decision"]["supportedVerdict"]
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalRenderHoldoutResult.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256,
        "passed": supported, "verdict": verdict, "factor": 1,
        "hardChecksPassed": sum(bool(value) for value in hard_checks.values()), "hardChecksTotal": len(hard_checks),
        "hardChecks": [{"id": name, "passed": bool(value)} for name, value in hard_checks.items()],
        "directionChecksPassed": sum(bool(value) for value in direction_checks.values()),
        "directionChecksTotal": len(direction_checks),
        "directionChecks": [{"id": name, "passed": bool(value)} for name, value in direction_checks.items()],
        "directionalStressContract": bool(direction_contract),
        "neitherWitnessContract": bool(neither_witness_contract),
        "neitherAcceptedZero": bool(neither_zero_accept_contract),
        "globalQuality": global_quality, "riskUnderboundRgbSamples": risk_underbound,
        "falseInvalidHistoryAccepts": false_invalid, "acceptedMaterialAliases": material_aliases,
        "currentRgbDecisionMetamorphism": bool(current_rgb_metamorphism),
        "cells": cells, "parentChecks": parent_checks, "parentTrees": parent_trees,
        "toolHashes": tool_hashes,
        "operationCounts": {"analyzerProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
        "promotionBoundary": spec["decision"]["promotionBoundary"], "nonClaims": spec["nonClaims"],
    }
    result = {**body, "resultHash": canonical_hash(body)}
    cli.output.parent.mkdir(parents=True, exist_ok=True)
    cli.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    receipt_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalRenderHoldoutAnalysisReceipt.v0.1",
        "experimentId": spec["experimentId"], "pid": os.getpid(),
        "result": {"uri": str(cli.output), "sha256": sha_file(cli.output), "resultHash": result["resultHash"]},
        "toolHashes": tool_hashes,
        "operationCounts": {"analyzerProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}
    cli.analysis_receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1214H1_ANALYZER verdict={verdict} hard={sum(hard_checks.values())}/{len(hard_checks)} direction={sum(direction_checks.values())}/{len(direction_checks)}")


if __name__ == "__main__":
    main()
