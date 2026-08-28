#!/usr/bin/env python3
"""Independent scalar Python implementation of B52-D12.12-D1."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "f179b4cea6c8d3bc19b4cf2534055ef98b3fa8dac9954bfeae28bc2a237dd640"
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
    "vector": ("vector.xy32", 2),
}
CONTROL_OUTPUTS = {
    "structuralValid": "structural-valid.u8",
    "radius2Interior": "radius2-interior.u8",
    "bilinearSupport": "bilinear-support.u8",
    "fullStencil": "full-stencil.u8",
    "localizedOpportunity": "localized-opportunity.u8",
}
FACTOR_OUTPUTS = {
    "oneSidedEligible": ("one-sided-eligible.u8", "u1"),
    "oneSidedUnavailable": ("one-sided-unavailable.u8", "u1"),
    "accepted": ("accepted.u8", "u1"),
    "riskQ30": ("risk.q30.u32", "<u4"),
    "acceptedReconstructed": ("accepted-reconstructed.rgba32", "<f4"),
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


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--adapter-report", type=Path, required=True)
    parser.add_argument("--localization-classification", type=Path, required=True)
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


def scale(vector, value):
    return tuple(vector[i] * value for i in range(3))


def dot(left, right):
    return sum(left[i] * right[i] for i in range(3))


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


def dimensions(h1_spec, owner):
    surfaces = h1_spec["sceneContract"]["surfaces"]
    values = surfaces["backgroundSizeWorld"] if owner["role"] == "background" else surfaces["occluderSizeWorld"]
    return float(values[0]), float(values[1])


def oracle_pixel(h1_spec, fixture, x, y):
    width, height = fixture["resolution"]
    camera_spec = h1_spec["sceneContract"]["camera"]
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
        size_x, size_y = dimensions(h1_spec, owner)
        if abs(local_point[0]) <= size_x / 2.0 and abs(local_point[1]) <= size_y / 2.0:
            projected = project(world_point, current_camera, width, height, lens, sensor_width)
            if projected is not None:
                candidates.append((projected[2], owner_index, owner, local_point))
    if not candidates:
        return None
    current_depth, owner_index, owner, local_point = min(candidates, key=lambda row: row[0])
    previous_owner = transform(owner["transformByFrame"]["0"])
    previous_world = add(previous_owner[0], mat_vec(previous_owner[1], local_point))
    previous_projected = project(previous_world, previous_camera, width, height, lens, sensor_width)
    if previous_projected is None:
        return None
    previous_x, previous_y, previous_depth = previous_projected
    return {
        "ownerIndex": owner_index,
        "ownerToken": np.float32(owner["passIndex"]),
        "currentDepth": current_depth,
        "previousDepth": previous_depth,
        "expectedVector": (previous_x - x, y - previous_y),
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


def write_array(path, value, dtype):
    payload = np.ascontiguousarray(value, dtype=dtype).tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"uri": str(path), "sha256": sha_bytes(payload), "bytes": len(payload), "shape": list(value.shape), "dtype": dtype}


def main() -> None:
    cli = args()
    if sha_file(cli.spec) != SPEC_SHA256 or cli.output_dir.exists() or cli.report.exists():
        raise RuntimeError("D12.12-D1 spec identity or fresh output violation")
    spec = json.loads(cli.spec.read_text())
    i1_spec_path = Path(spec["parents"]["materialOwnerSpec"]["uri"])
    if sha_file(i1_spec_path) != spec["parents"]["materialOwnerSpec"]["sha256"]:
        raise RuntimeError("D12.12-D1 I1 spec identity mismatch")
    i1_spec = json.loads(i1_spec_path.read_text())
    h1_spec_path = Path(i1_spec["parents"]["h1Spec"]["uri"])
    h1_spec = json.loads(h1_spec_path.read_text())
    if sha_file(Path(sys.executable)) != spec["execution"]["python"]["sha256"] or np.__version__ != spec["execution"]["python"]["numpy"]:
        raise RuntimeError("D12.12-D1 Python runtime identity mismatch")
    fixture_source = next((row for row in h1_spec["fixtures"] if row["id"] == cli.fixture), None)
    if fixture_source is None:
        raise RuntimeError("unknown D12.12 fixture")
    fixture = json.loads(json.dumps(fixture_source))
    for owner in fixture["owners"]:
        owner["passIndex"] = i1_spec["materialOwnerTokens"]["assignments"][owner["analyticOwnerId"]]
    width, height = fixture["resolution"]
    adapter = json.loads(cli.adapter_report.read_text())
    adapter_body = {key: value for key, value in adapter.items() if key != "reportHash"}
    if adapter.get("reportHash") != canonical_hash(adapter_body) or adapter.get("fixtureId") != cli.fixture or adapter.get("repeat") != cli.repeat:
        raise RuntimeError("D12.12-D1 adapter report mismatch")
    arrays = {}
    for name, (filename, channels) in INPUTS.items():
        payload = (cli.input_dir / filename).read_bytes()
        if sha_bytes(payload) != adapter["arrays"][name]["sha256"]:
            raise RuntimeError(f"D12.12-D1 input hash mismatch: {name}")
        shape = (height, width, channels) if channels > 1 else (height, width)
        arrays[name] = np.frombuffer(payload, dtype="<f4").reshape(shape).copy()
    localization_result = json.loads(Path(spec["parents"]["ownerSupportLocalizationResult"]["uri"]).read_text())
    declared_classification_sha = localization_result["payloadHashes"][cli.fixture][str(cli.repeat)]["classification"]
    localization_payload = cli.localization_classification.read_bytes()
    if sha_bytes(localization_payload) != declared_classification_sha:
        raise RuntimeError("D12.12-D1 localization classification identity mismatch")
    localization = np.frombuffer(localization_payload, dtype="u1").reshape((height, width)).copy()
    localized_opportunity = (localization == 2).astype("u1")
    structural = np.zeros((height, width), dtype="u1")
    radius2 = np.zeros((height, width), dtype="u1")
    bilinear_support = np.zeros((height, width), dtype="u1")
    full_stencil = np.zeros((height, width), dtype="u1")
    eligible = np.zeros((height, width), dtype="u1")
    unavailable = np.zeros((height, width), dtype="u1")
    reconstructed = np.zeros((height, width, 4), dtype="<f4")
    fx_q24 = np.zeros((height, width), dtype="<u4")
    fy_q24 = np.zeros((height, width), dtype="<u4")
    curvature = {}
    for factor in spec["candidateFamily"]["inflationFactors"]:
        curvature[factor] = np.zeros((height, width, 3, 2), dtype=object)
    for y in range(height):
        for x in range(width):
            oracle = oracle_pixel(h1_spec, fixture, x, y)
            if oracle is None:
                continue
            tolerance = max(1.0, oracle["currentDepth"]) / 1024.0
            owner = oracle["ownerToken"]
            if arrays["currentOwner"][y, x] != owner or abs(float(arrays["currentDepth"][y, x]) - oracle["currentDepth"]) > tolerance:
                continue
            vector_x, vector_y = (float(value) for value in arrays["vector"][y, x])
            qx, qy = x + vector_x, y - vector_y
            sample = taps_and_weights(qx, qy, width, height)
            if sample is None:
                continue
            taps, weights, x0, y0, fx, fy = sample
            if not all(arrays["previousOwner"][ty, tx] == owner for ty, tx in taps):
                continue
            if arrays["currentRgba"][y, x, 3] <= np.float32(0.999) or not all(arrays["previousRgba"][ty, tx, 3] > np.float32(0.999) for ty, tx in taps):
                continue
            sampled_depth = weighted([float(arrays["previousDepth"][ty, tx]) for ty, tx in taps], weights)
            if abs(sampled_depth - oracle["previousDepth"]) > max(1.0, oracle["previousDepth"]) / 1024.0:
                continue
            structural[y, x] = 1
            bilinear_support[y, x] = 1
            if not current_radius2(arrays, x, y, owner, width, height):
                continue
            radius2[y, x] = 1
            full = all(valid_tap(arrays, ty, tx, owner, width, height) for ty in range(y0 - 1, y0 + 3) for tx in range(x0 - 1, x0 + 3))
            full_stencil[y, x] = int(full)
            horizontal = []
            vertical = []
            supported = True
            for yy in (y0, y0 + 1):
                left = valid_tap(arrays, yy, x0 - 1, owner, width, height)
                right = valid_tap(arrays, yy, x0 + 2, owner, width, height)
                if not left and not right:
                    supported = False
                horizontal.append((left, right))
            for xx in (x0, x0 + 1):
                top = valid_tap(arrays, y0 - 1, xx, owner, width, height)
                bottom = valid_tap(arrays, y0 + 2, xx, owner, width, height)
                if not top and not bottom:
                    supported = False
                vertical.append((top, bottom))
            if not supported:
                unavailable[y, x] = 1
                continue
            eligible[y, x] = 1
            fx_q24[y, x] = exact_scaled(fx, Q24, "motion fraction x")
            fy_q24[y, x] = exact_scaled(fy, Q24, "motion fraction y")
            for channel in range(4):
                values = [float(arrays["previousRgba"][ty, tx, channel]) for ty, tx in taps]
                reconstructed[y, x, channel] = np.float32(weighted(values, weights))
            def color(yy, xx, channel):
                return exact_scaled(float(arrays["previousRgba"][yy, xx, channel]), Q30, "Q30 RGB")
            for channel in range(3):
                row_differences = []
                for row_index, yy in enumerate((y0, y0 + 1)):
                    left, right = horizontal[row_index]
                    values = []
                    if left:
                        values.append(abs(color(yy, x0 - 1, channel) - 2 * color(yy, x0, channel) + color(yy, x0 + 1, channel)))
                    if right:
                        values.append(abs(color(yy, x0, channel) - 2 * color(yy, x0 + 1, channel) + color(yy, x0 + 2, channel)))
                    row_differences.append((values, len(values) == 1))
                column_differences = []
                for column_index, xx in enumerate((x0, x0 + 1)):
                    top, bottom = vertical[column_index]
                    values = []
                    if top:
                        values.append(abs(color(y0 - 1, xx, channel) - 2 * color(y0, xx, channel) + color(y0 + 1, xx, channel)))
                    if bottom:
                        values.append(abs(color(y0, xx, channel) - 2 * color(y0 + 1, xx, channel) + color(y0 + 2, xx, channel)))
                    column_differences.append((values, len(values) == 1))
                for factor in spec["candidateFamily"]["inflationFactors"]:
                    mx = max(max(values) * (factor if one_sided else 1) for values, one_sided in row_differences)
                    my = max(max(values) * (factor if one_sided else 1) for values, one_sided in column_differences)
                    curvature[factor][y, x, channel, 0] = mx
                    curvature[factor][y, x, channel, 1] = my
    unavailable |= np.logical_and(radius2.astype(bool), ~eligible.astype(bool)).astype("u1")
    cli.output_dir.mkdir(parents=True, exist_ok=False)
    control_records = {}
    for name, filename in CONTROL_OUTPUTS.items():
        value = {"structuralValid": structural, "radius2Interior": radius2, "bilinearSupport": bilinear_support, "fullStencil": full_stencil, "localizedOpportunity": localized_opportunity}[name]
        control_records[name] = write_array(cli.output_dir / "control" / filename, value, "u1")
    factor_records = {}
    threshold = int(spec["frozenBaseline"]["riskThresholdQ30Inclusive"])
    allowance = int(spec["frozenBaseline"]["roundingAllowanceQ30"])
    for factor in spec["candidateFamily"]["inflationFactors"]:
        risk = np.zeros((height, width, 3), dtype="<u4")
        accepted = np.zeros((height, width), dtype="u1")
        accepted_reconstructed = arrays["currentRgba"].copy()
        for y, x in np.argwhere(eligible.astype(bool)):
            fx = int(fx_q24[y, x])
            fy = int(fy_q24[y, x])
            for channel in range(3):
                mx = int(curvature[factor][y, x, channel, 0])
                my = int(curvature[factor][y, x, channel, 1])
                numerator = 2 * (fx * (Q24 - fx) * mx + fy * (Q24 - fy) * my)
                risk[y, x, channel] = min(ceil_div(numerator, Q24 * Q24) + allowance, UINT32_MAX)
            if int(risk[y, x].max()) <= threshold:
                accepted[y, x] = 1
                accepted_reconstructed[y, x] = reconstructed[y, x]
        factor_dir = cli.output_dir / f"factor-{factor:02d}"
        outputs = {
            "oneSidedEligible": eligible,
            "oneSidedUnavailable": unavailable,
            "accepted": accepted,
            "riskQ30": risk,
            "acceptedReconstructed": accepted_reconstructed,
        }
        factor_records[str(factor)] = {
            name: write_array(factor_dir / filename, outputs[name], dtype)
            for name, (filename, dtype) in FACTOR_OUTPUTS.items()
        }
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerOneSidedCurvatureConsumerReport.v0.1",
        "experimentId": spec["experimentId"],
        "producer": "python",
        "fixtureId": cli.fixture,
        "repeat": cli.repeat,
        "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha_file(Path(sys.executable)), "numpy": np.__version__},
        "adapter": {"uri": str(cli.adapter_report), "sha256": sha_file(cli.adapter_report), "reportHash": adapter["reportHash"]},
        "localizationClassification": {"uri": str(cli.localization_classification), "sha256": sha_bytes(localization_payload)},
        "inflationFactors": spec["candidateFamily"]["inflationFactors"],
        "controlArrays": control_records,
        "factorArrays": factor_records,
        "operationCounts": {"consumerProcesses": 1, "pixelsVisited": width * height, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    cli.report.parent.mkdir(parents=True, exist_ok=True)
    cli.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"BFS_B52_D1212_PYTHON fixture={cli.fixture} repeat={cli.repeat} factors={len(spec['candidateFamily']['inflationFactors'])}")


if __name__ == "__main__":
    main()
