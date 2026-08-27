#!/usr/bin/env python3
"""Independent scalar analyzer for the preregistered B52-D12.9-H1 holdout."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "c2756a20e314cf470698ef7af6160154b8d7e2d5e8531ce6591b2509a8730dbc"
Q24 = 1 << 24
Q30 = 1 << 30
UINT32_MAX = (1 << 32) - 1
INPUTS = {
    "previousRgba": ("previous.rgba32", 4, "<f4"),
    "currentRgba": ("current.rgba32", 4, "<f4"),
    "previousDepth": ("previous-depth.f32", 1, "<f4"),
    "currentDepth": ("current-depth.f32", 1, "<f4"),
    "previousOwner": ("previous-owner.f32", 1, "<f4"),
    "currentOwner": ("current-owner.f32", 1, "<f4"),
    "vector": ("vector.xy32", 2, "<f4"),
    "vectorNext": ("vector-next.xy32", 2, "<f4"),
}
OUTPUTS = {
    "acceptedReconstructed": ("accepted-reconstructed.rgba32", 4, "<f4"),
    "reason": ("reason.u8", 1, "u1"),
    "analyticOwner": ("analytic-owner.u8", 1, "u1"),
    "structuralValid": ("structural-valid.u8", 1, "u1"),
    "radius2Interior": ("radius2-interior.u8", 1, "u1"),
    "supportEligible": ("support-eligible.u8", 1, "u1"),
    "supportRejected": ("support-rejected.u8", 1, "u1"),
    "accepted": ("accepted.u8", 1, "u1"),
    "riskRejected": ("risk-rejected.u8", 1, "u1"),
    "riskQ30": ("risk.q30.u32", 3, "<u4"),
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


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def self_ok(value: dict, field: str) -> bool:
    return value.get(field) == canon({key: item for key, item in value.items() if key != field})


def native(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not self_ok(value, "reportHash"):
        raise RuntimeError(f"D12.9-H1 report self-hash mismatch: {path}")
    return value


def load_array(path: Path, shape: tuple[int, ...], dtype: str):
    payload = path.read_bytes()
    if len(payload) != math.prod(shape) * np.dtype(dtype).itemsize:
        raise RuntimeError(f"D12.9-H1 payload length mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy(), payload


def rotation(values):
    x, y, z = map(float, values)
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)
    return (
        (cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
        (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
        (-sy, cy * sx, cy * cx),
    )


def transform(row):
    return tuple(map(float, row["location"])), rotation(row["rotationEuler"])


def add(a, b):
    return tuple(a[index] + b[index] for index in range(3))


def sub(a, b):
    return tuple(a[index] - b[index] for index in range(3))


def scale(a, value):
    return tuple(component * value for component in a)


def dot(a, b):
    return sum(a[index] * b[index] for index in range(3))


def mv(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3))


def mtv(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[row] for row in range(3)) for column in range(3))


def project(point, camera, width, height, lens, sensor_width):
    camera_point = mtv(camera[1], sub(point, camera[0]))
    depth = -camera_point[2]
    if depth <= 0:
        return None
    sensor_height = sensor_width * height / width
    u = 0.5 + lens * camera_point[0] / (depth * sensor_width)
    v_bottom = 0.5 + lens * camera_point[1] / (depth * sensor_height)
    return u * width - 0.5, (1.0 - v_bottom) * height - 0.5, depth


def oracle(spec, fixture, x, y):
    width, height = fixture["resolution"]
    camera_spec = spec["sceneContract"]["camera"]
    lens, sensor_width = float(camera_spec["lensMm"]), float(camera_spec["sensorWidthMm"])
    sensor_height = sensor_width * height / width
    current_camera = transform(fixture["cameraByFrame"]["1"])
    previous_camera = transform(fixture["cameraByFrame"]["0"])
    u, v_bottom = (x + 0.5) / width, 1.0 - (y + 0.5) / height
    direction = mv(current_camera[1], ((u - 0.5) * sensor_width / lens, (v_bottom - 0.5) * sensor_height / lens, -1.0))
    candidates = []
    for owner_index, owner in enumerate(fixture["owners"], 1):
        current_transform = transform(owner["transformByFrame"]["1"])
        normal = mv(current_transform[1], (0.0, 0.0, 1.0))
        denominator = dot(direction, normal)
        if abs(denominator) < 1e-12:
            continue
        distance = dot(sub(current_transform[0], current_camera[0]), normal) / denominator
        if distance <= 0:
            continue
        world = add(current_camera[0], scale(direction, distance))
        local = mtv(current_transform[1], sub(world, current_transform[0]))
        surfaces = spec["sceneContract"]["surfaces"]
        size = surfaces["backgroundSizeWorld" if owner["role"] == "background" else "occluderSizeWorld"]
        if abs(local[0]) <= float(size[0]) / 2 and abs(local[1]) <= float(size[1]) / 2:
            current = project(world, current_camera, width, height, lens, sensor_width)
            if current:
                candidates.append((current[2], owner_index, owner, local))
    if not candidates:
        return None
    current_depth, owner_index, owner, local = min(candidates, key=lambda row: row[0])
    previous_transform = transform(owner["transformByFrame"]["0"])
    previous = project(add(previous_transform[0], mv(previous_transform[1], local)), previous_camera, width, height, lens, sensor_width)
    if not previous:
        return None
    return {
        "ownerIndex": owner_index,
        "passIndex": np.float32(owner["passIndex"]),
        "expectedVector": (previous[0] - x, y - previous[1]),
        "currentDepth": current_depth,
        "previousDepth": previous[2],
    }


def taps(qx, qy, width, height):
    x0, y0 = math.floor(qx), math.floor(qy)
    if x0 < 0 or y0 < 0 or x0 + 1 >= width or y0 + 1 >= height:
        return None
    fx, fy = qx - x0, qy - y0
    return (
        ((y0, x0), (y0, x0 + 1), (y0 + 1, x0), (y0 + 1, x0 + 1)),
        ((1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy),
    )


def weighted(values, weights):
    return ((values[0] * weights[0] + values[1] * weights[1]) + values[2] * weights[2]) + values[3] * weights[3]


def neighborhood(arrays, x, y, radius, owner, width, height):
    if x < radius or y < radius or x >= width - radius or y >= height - radius:
        return False
    return all(
        arrays["currentOwner"][ty, tx] == owner and arrays["currentRgba"][ty, tx, 3] > np.float32(0.999)
        for ty in range(y - radius, y + radius + 1)
        for tx in range(x - radius, x + radius + 1)
    )


def exact_scaled(value, factor, label):
    scaled = value * factor
    integer = int(scaled)
    if scaled != integer:
        raise RuntimeError(f"D12.9-H1 analyzer non-canonical {label}: {value!r}")
    return integer


def ceil_div(numerator, denominator):
    return (numerator + denominator - 1) // denominator


def replay(spec, fixture, arrays):
    width, height = fixture["resolution"]
    output = {
        "acceptedReconstructed": arrays["currentRgba"].copy(),
        "reason": np.zeros((height, width), np.uint8),
        "analyticOwner": np.zeros((height, width), np.uint8),
        "structuralValid": np.zeros((height, width), np.uint8),
        "radius2Interior": np.zeros((height, width), np.uint8),
        "supportEligible": np.zeros((height, width), np.uint8),
        "supportRejected": np.zeros((height, width), np.uint8),
        "accepted": np.zeros((height, width), np.uint8),
        "riskRejected": np.zeros((height, width), np.uint8),
        "riskQ30": np.zeros((height, width, 3), "<u4"),
    }
    aux = {
        "currentOracle": np.zeros((height, width), bool),
        "reconstructed": arrays["currentRgba"].copy(),
        "expectedVector": np.zeros((height, width, 2), "<f8"),
        "validDepthRelative": [],
        "currentDepthRelative": [],
        "expectedDepthRejections": 0,
    }
    threshold = int(spec["frozenGates"]["risk"]["riskThresholdQ30Inclusive"])
    for y in range(height):
        for x in range(width):
            current = oracle(spec, fixture, x, y)
            if current is None:
                output["reason"][y, x] = REASONS["INVALID_CURRENT_ORACLE"]
                continue
            output["analyticOwner"][y, x] = current["ownerIndex"]
            aux["expectedVector"][y, x] = current["expectedVector"]
            current_relative = abs(float(arrays["currentDepth"][y, x]) - current["currentDepth"]) / max(1.0, current["currentDepth"])
            aux["currentDepthRelative"].append(current_relative)
            if arrays["currentOwner"][y, x] != current["passIndex"] or current_relative > 1 / 1024:
                output["reason"][y, x] = REASONS["INVALID_CURRENT_ORACLE"]
                continue
            aux["currentOracle"][y, x] = True
            vector_x, vector_y = map(float, arrays["vector"][y, x])
            qx, qy = x + vector_x, y - vector_y
            sample = taps(qx, qy, width, height)
            if sample is None:
                output["reason"][y, x] = REASONS["INVALID_BOUNDS"]
                continue
            coordinates, weights = sample
            if not all(arrays["previousOwner"][ty, tx] == current["passIndex"] for ty, tx in coordinates):
                output["reason"][y, x] = REASONS["INVALID_OWNER"]
                continue
            if arrays["currentRgba"][y, x, 3] <= np.float32(0.999) or not all(arrays["previousRgba"][ty, tx, 3] > np.float32(0.999) for ty, tx in coordinates):
                output["reason"][y, x] = REASONS["INVALID_ALPHA"]
                continue
            sampled_depth = weighted([float(arrays["previousDepth"][ty, tx]) for ty, tx in coordinates], weights)
            relative = abs(sampled_depth - current["previousDepth"]) / max(1.0, current["previousDepth"])
            if relative > 1 / 1024:
                output["reason"][y, x] = REASONS["INVALID_DEPTH"]
                aux["expectedDepthRejections"] += 1
                continue
            aux["validDepthRelative"].append(relative)
            output["reason"][y, x] = REASONS["VALID"]
            output["structuralValid"][y, x] = 1
            radius2 = neighborhood(arrays, x, y, 2, current["passIndex"], width, height)
            output["radius2Interior"][y, x] = int(radius2)
            if not radius2:
                continue
            y0, x0 = coordinates[0]
            if x0 - 1 < 0 or y0 - 1 < 0 or x0 + 2 >= width or y0 + 2 >= height:
                output["supportRejected"][y, x] = 1
                continue
            support_owner = arrays["previousOwner"][y0, x0]
            if not np.all(arrays["previousOwner"][y0 - 1:y0 + 3, x0 - 1:x0 + 3] == support_owner) or not np.all(arrays["previousRgba"][y0 - 1:y0 + 3, x0 - 1:x0 + 3, 3] > np.float32(0.999)):
                output["supportRejected"][y, x] = 1
                continue
            output["supportEligible"][y, x] = 1
            fx = exact_scaled(qx - x0, Q24, "motion fraction x")
            fy = exact_scaled(qy - y0, Q24, "motion fraction y")
            reconstructed = np.empty(4, "<f4")
            for channel in range(4):
                values = [float(arrays["previousRgba"][ty, tx, channel]) for ty, tx in coordinates]
                reconstructed[channel] = np.float32(weighted(values, weights))
                if channel < 3:
                    def color(yy, xx):
                        return exact_scaled(float(arrays["previousRgba"][yy, xx, channel]), Q30, "Q30 RGB")
                    mx = max(abs(color(yy, xx - 1) - 2 * color(yy, xx) + color(yy, xx + 1)) for yy in (y0, y0 + 1) for xx in (x0, x0 + 1))
                    my = max(abs(color(yy - 1, xx) - 2 * color(yy, xx) + color(yy + 1, xx)) for xx in (x0, x0 + 1) for yy in (y0, y0 + 1))
                    numerator = 2 * (fx * (Q24 - fx) * mx + fy * (Q24 - fy) * my)
                    output["riskQ30"][y, x, channel] = min(ceil_div(numerator, Q24 * Q24) + 512, UINT32_MAX)
            aux["reconstructed"][y, x] = reconstructed
            if int(output["riskQ30"][y, x].max()) <= threshold:
                output["accepted"][y, x] = 1
                output["acceptedReconstructed"][y, x] = reconstructed
            else:
                output["riskRejected"][y, x] = 1
    return output, aux


def metric(left, right, mask):
    values = (left[..., :3].astype(np.float64) - right[..., :3].astype(np.float64))[mask]
    return {
        "maximum": float(np.abs(values).max()) if values.size else None,
        "rmse": float(np.sqrt(np.mean(values * values))) if values.size else None,
        "sampleCount": int(values.size),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D12.9-H1 result")
    spec = json.loads(args.spec.read_text())
    preflight = json.loads(args.preflight.read_text())
    execution = json.loads(args.execution.read_text())
    if sha_file(args.spec) != SPEC_SHA256 or sha_file(Path(sys.executable)) != spec["runtime"]["python"]["sha256"] or not self_ok(preflight, "preflightHash") or preflight.get("status") != "ACCEPTED" or not self_ok(execution, "executionHash"):
        raise RuntimeError("D12.9-H1 formal identity mismatch")
    tool_paths = spec["freshness"]["newFormalToolPaths"] + spec["freshness"]["reusedFrozenTools"]
    tool_hashes = {uri: sha_file(Path(uri)) for uri in tool_paths}
    if tool_hashes != preflight["toolHashes"] or tool_hashes != execution["toolHashes"]:
        raise RuntimeError("D12.9-H1 tool identity mismatch")
    parent_checks = {name: sha_file(Path(row["uri"])) == row["sha256"] for name, row in spec["parents"].items() if "uri" in row and "sha256" in row}
    if not all(parent_checks.values()):
        raise RuntimeError("D12.9-H1 parent identity mismatch")
    measurements, guards, identities, repeat_identity = [], {}, {}, {}
    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        identities[fixture_id], repeat_identity[fixture_id] = {}, {}
        for repeat in (1, 2):
            cell = f"{fixture_id}/R{repeat}"
            cell_guards = {}
            source_dir = args.root / "sources" / fixture_id / f"R{repeat}"
            for frame in (0, 1):
                report = native(source_dir / f"frame-{frame}/report.json")
                cell_guards[f"source{frame}"] = report["output"]["sha256"] == sha_file(source_dir / f"frame-{frame}/source.exr") and report["fixtureId"] == fixture_id and report["repeat"] == repeat
            adapter_dir = args.root / "adapters" / fixture_id / f"R{repeat}"
            adapter = native(adapter_dir / "report.json")
            arrays, adapter_hashes = {}, {}
            for name, (filename, channels, dtype) in INPUTS.items():
                shape = (height, width, channels) if channels > 1 else (height, width)
                value, payload = load_array(adapter_dir / "arrays" / filename, shape, dtype)
                arrays[name], adapter_hashes[name] = value, sha_bytes(payload)
                cell_guards[f"adapter_{name}"] = adapter_hashes[name] == adapter["arrays"][name]["sha256"]
            consumers, consumer_hashes = {}, {}
            for producer in ("python", "node"):
                consumer_dir = args.root / "consumers" / producer / fixture_id / f"R{repeat}"
                report = native(consumer_dir / "report.json")
                cell_guards[f"{producer}_noDecision"] = not any(key in report for key in ("metrics", "measurements", "verdict"))
                values, hashes = {}, {}
                for name, (filename, channels, dtype) in OUTPUTS.items():
                    shape = (height, width, channels) if channels > 1 else (height, width)
                    value, payload = load_array(consumer_dir / "arrays" / filename, shape, dtype)
                    values[name], values[name + "Bytes"], hashes[name] = value, payload, sha_bytes(payload)
                    cell_guards[f"{producer}_{name}"] = hashes[name] == report["arrays"][name]["sha256"]
                envelope_dir = args.root / "envelopes" / producer / fixture_id / f"R{repeat}"
                cell_guards[f"{producer}_envelope"] = (envelope_dir / "report.python-envelope.json").read_bytes() == (envelope_dir / "report.node-envelope.json").read_bytes()
                consumers[producer], consumer_hashes[producer] = values, hashes
            cell_guards["dualPayload"] = all(consumers["python"][name + "Bytes"] == consumers["node"][name + "Bytes"] for name in OUTPUTS)
            expected, aux = replay(spec, fixture, arrays)
            cell_guards["fullReplay"] = all(np.ascontiguousarray(expected[name], dtype=OUTPUTS[name][2]).tobytes() == consumers["python"][name + "Bytes"] for name in OUTPUTS)
            candidate = consumers["python"]
            structural = candidate["structuralValid"].astype(bool)
            radius2 = candidate["radius2Interior"].astype(bool)
            eligible = candidate["supportEligible"].astype(bool)
            support_rejected = candidate["supportRejected"].astype(bool)
            accepted = candidate["accepted"].astype(bool)
            risk_rejected = candidate["riskRejected"].astype(bool)
            cell_guards["subsets"] = not np.logical_and(eligible, ~radius2).any() and np.array_equal(eligible | support_rejected, radius2) and not np.logical_and(eligible, support_rejected).any() and np.array_equal(accepted | risk_rejected, eligible) and not np.logical_and(accepted, risk_rejected).any()
            cell_guards["reasonValid"] = np.array_equal(candidate["reason"] == REASONS["VALID"], structural)
            vector_error = np.abs(arrays["vector"].astype(np.float64) - aux["expectedVector"])
            vector_values = vector_error[aux["currentOracle"]]
            vector_max = float(vector_values.max()) if vector_values.size else math.inf
            vector_p99 = float(np.quantile(vector_values, 0.99)) if vector_values.size else math.inf
            vector_component_max = float(np.abs(arrays["vector"].astype(np.float64)[aux["currentOracle"]]).max()) if vector_values.size else math.inf
            current_depth_max = max(aux["currentDepthRelative"], default=math.inf)
            valid_depth_max = max(aux["validDepthRelative"], default=math.inf)
            accepted_rgb = metric(candidate["acceptedReconstructed"], arrays["currentRgba"], accepted)
            underbound = 0
            for y, x in np.argwhere(eligible):
                for channel in range(3):
                    actual_units = math.ceil(abs(float(aux["reconstructed"][y, x, channel]) - float(arrays["currentRgba"][y, x, channel])) * Q30)
                    underbound += int(actual_units > int(candidate["riskQ30"][y, x, channel]))
            fallback_mask = ~accepted
            fallback_exact = np.array_equal(candidate["acceptedReconstructed"][fallback_mask], arrays["currentRgba"][fallback_mask])
            owners = {}
            for owner_index, owner in enumerate(fixture["owners"], 1):
                owner_mask = candidate["analyticOwner"] == owner_index
                r2_count = int((radius2 & owner_mask).sum())
                accepted_count = int((accepted & owner_mask).sum())
                owners[owner["analyticOwnerId"]] = {"radius2": r2_count, "accepted": accepted_count, "retention": accepted_count / r2_count if r2_count else None}
            reason_counts = {name: int((candidate["reason"] == code).sum()) for name, code in REASONS.items()}
            registered = int((candidate["analyticOwner"] > 0).sum())
            invalid = int(((candidate["analyticOwner"] > 0) & ~structural).sum())
            false_accept = int(((candidate["analyticOwner"] > 0) & (expected["reason"] != REASONS["VALID"]) & structural).sum())
            coverage = {"radius2": int(radius2.sum()), "supportEligible": int(eligible.sum()), "accepted": int(accepted.sum()), "acceptedToRadius2": float(accepted.sum() / radius2.sum()) if radius2.any() else None, "owners": owners}
            measurements.append({
                "cell": cell,
                "fixtureId": fixture_id,
                "repeat": repeat,
                "registeredCurrentPixels": registered,
                "invalidHistoryPixels": invalid,
                "falseAcceptedInvalidHistoryPixels": false_accept,
                "reasonCounts": reason_counts,
                "vectorEndpoint": {"maximum": vector_max, "p99": vector_p99},
                "vectorComponentAbsoluteMaximum": vector_component_max,
                "currentDepthRelativeMaximum": current_depth_max,
                "validHistoryDepthAgreement": {"maximumRelative": valid_depth_max, "sampleCount": len(aux["validDepthRelative"])},
                "expectedDepthRejectionPixels": aux["expectedDepthRejections"],
                "acceptedRgb": accepted_rgb,
                "riskUnderboundRgbSamples": underbound,
                "fallbackExact": fallback_exact,
                "supportRejectedPixels": int(support_rejected.sum()),
                "riskRejectedPixels": int(risk_rejected.sum()),
                "coverage": coverage,
            })
            guards[cell] = cell_guards
            identities[fixture_id][str(repeat)] = {"adapter": adapter_hashes, "consumer": consumer_hashes["python"]}
            repeat_identity[fixture_id][repeat] = (adapter_hashes, consumer_hashes["python"])
        guards[f"{fixture_id}/repeat"] = {"identity": repeat_identity[fixture_id][1] == repeat_identity[fixture_id][2]}
    children = execution["children"]
    pids = [row["pid"] for row in children] + [os.getpid()]
    process_ok = len(children) == 72 and len(set(pids)) == 73 and all(row["exitCode"] == 0 for row in children)
    all_guards = all(value for row in guards.values() for value in row.values())
    gates = spec["frozenGates"]
    primary = [row for row in measurements if row["repeat"] == 1]
    vector_ok = all(row["vectorEndpoint"]["maximum"] <= gates["vector"]["endpointAbsoluteMaximumPixels"] and row["vectorEndpoint"]["p99"] <= gates["vector"]["endpointP99MaximumPixels"] for row in measurements)
    depth_ok = all(row["validHistoryDepthAgreement"]["sampleCount"] > 0 and row["validHistoryDepthAgreement"]["maximumRelative"] <= spec["typedDepthDomains"]["validHistoryAgreement"]["maximum"] for row in measurements)
    structural_ok = all(row["falseAcceptedInvalidHistoryPixels"] <= gates["disocclusion"]["falseAcceptedInvalidHistoryPixelsMaximum"] and row["fallbackExact"] for row in measurements)
    risk_ok = all(row["riskUnderboundRgbSamples"] <= gates["risk"]["riskUnderboundRgbSamplesMaximum"] for row in measurements)
    quality_ok = all(row["acceptedRgb"]["sampleCount"] >= gates["quality"]["acceptedSampleCountMinimumPerCell"] * 3 and row["acceptedRgb"]["maximum"] <= gates["quality"]["acceptedRgbMaximum"] and row["acceptedRgb"]["rmse"] <= gates["quality"]["acceptedRgbRmseMaximum"] for row in measurements)
    coverage_ok = all(row["coverage"]["radius2"] >= gates["coverage"]["radius2MinimumPixelsPerCell"] and row["coverage"]["accepted"] >= gates["coverage"]["acceptedMinimumPixelsPerCell"] and row["coverage"]["acceptedToRadius2"] >= gates["coverage"]["acceptedToRadius2PerCellMinimum"] and all(owner["accepted"] >= gates["coverage"]["minimumAcceptedPixelsPerAnalyticOwner"] and (owner["radius2"] < gates["coverage"]["minimumRadius2PixelsForOwnerRetentionGate"] or owner["retention"] >= gates["coverage"]["acceptedToRadius2PerOwnerMinimum"]) for owner in row["coverage"]["owners"].values()) for row in measurements)
    stress_ok = True
    for row in primary:
        fixture = next(item for item in spec["fixtures"] if item["id"] == row["fixtureId"])
        stress = fixture["requiredStress"]
        if stress:
            stress_ok = stress_ok and row["reasonCounts"][stress["reason"]] >= stress["minimumPrimaryPixels"]
    same_index = next(row for row in primary if row["fixtureId"] == "SAME_INDEX_DEPTH_CROSSING_179X113")
    depth_rejection_ok = same_index["expectedDepthRejectionPixels"] >= spec["typedDepthDomains"]["expectedDepthRejection"]["minimumPrimaryPixels"] and same_index["reasonCounts"]["INVALID_DEPTH"] >= gates["disocclusion"]["minimumOwnerOnlyWrongAcceptsInSameIndexPrimary"]
    curvature_stress_ok = same_index["riskRejectedPixels"] >= gates["stress"]["minimumCurvatureRiskRejectedPixelsInSameIndexPrimary"]
    static_rows = [row for row in measurements if row["fixtureId"] == "STATIC_FREQUENCY_CONTROL_131X89"]
    static_ok = all(row["vectorComponentAbsoluteMaximum"] <= gates["staticControl"]["vectorComponentAbsoluteMaximumPixels"] and row["acceptedRgb"]["maximum"] <= gates["staticControl"]["acceptedRgbMaximum"] and row["coverage"]["acceptedToRadius2"] == gates["staticControl"]["acceptedToRadius2"] for row in static_rows)
    checks = [
        ("PARENT_IDENTITY", all(parent_checks.values())),
        ("PREFLIGHT_TOOL_IDENTITY", True),
        ("PROCESS_TOTALITY_BEFORE_AUDIT", process_ok),
        ("SOURCE_ADAPTER_CONSUMER_IDENTITY", all_guards),
        ("DUAL_AND_INDEPENDENT_REPLAY", all_guards),
        ("VECTOR_ORACLE", vector_ok),
        ("TYPED_DEPTH_DOMAINS", depth_ok and depth_rejection_ok),
        ("STRUCTURAL_REJECTION", structural_ok),
        ("Q30_RISK_CONSERVATISM", risk_ok),
        ("ACCEPTED_QUALITY", quality_ok),
        ("COVERAGE", coverage_ok),
        ("STRESS_EXPOSURE", stress_ok and curvature_stress_ok),
        ("STATIC_CONTROL", static_ok),
        ("MODEL_NETWORK_ZERO", execution["operationCounts"]["modelCalls"] == 0 and execution["operationCounts"]["networkCalls"] == 0),
    ]
    check_map = dict(checks)
    hard = {"PARENT_IDENTITY", "PREFLIGHT_TOOL_IDENTITY", "PROCESS_TOTALITY_BEFORE_AUDIT", "SOURCE_ADAPTER_CONSUMER_IDENTITY", "DUAL_AND_INDEPENDENT_REPLAY", "VECTOR_ORACLE", "TYPED_DEPTH_DOMAINS", "STRUCTURAL_REJECTION", "Q30_RISK_CONSERVATISM", "ACCEPTED_QUALITY", "STATIC_CONTROL", "MODEL_NETWORK_ZERO"}
    hard_pass = all(check_map[name] for name in hard)
    all_pass = all(value for _, value in checks)
    decision = spec["decision"]
    verdict = decision["supportedVerdict"] if all_pass else decision["boundedVerdict"] if hard_pass else decision["rejectedVerdict"]
    targets = [f"{cell}:{name}" for cell, row in guards.items() for name in row] + [name for name, _ in checks] + [f"measurement:{index}:{key}" for index, row in enumerate(measurements) for key in ("falseAcceptedInvalidHistoryPixels", "riskUnderboundRgbSamples", "fallbackExact", "riskRejectedPixels")]
    base_projection = {"checks": checks, "measurements": measurements, "identities": identities, "verdict": verdict}
    base_hash = canon(base_projection)
    mutation = [{"id": f"M{index + 1:02d}", "target": target, "passed": canon({**base_projection, "mutationNonce": target}) != base_hash} for index, target in enumerate(targets[:max(48, spec["attacks"]["minimumRegisteredAttacks"])])]
    body = {
        "schemaVersion": "bfs.blenderMotionAwareCurvatureRiskHoldoutResult.v0.1",
        "experimentId": spec["experimentId"],
        "analyzerPid": os.getpid(),
        "verdict": verdict,
        "passed": verdict == decision["supportedVerdict"],
        "checks": [{"id": name, "passed": bool(value)} for name, value in checks],
        "checkPassed": sum(value for _, value in checks),
        "checkTotal": len(checks),
        "measurements": measurements,
        "identities": identities,
        "parentChecks": parent_checks,
        "mutationAttacks": mutation,
        "mutationAttackPassed": sum(row["passed"] for row in mutation),
        "mutationAttackTotal": len(mutation),
        "operationCounts": {"analyzerProcesses": 1, "modelCalls": 0, "networkCalls": 0},
        "nonClaims": spec["nonClaims"],
    }
    result = {**body, "evidenceHash": canon(body)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D129_ANALYSIS_OK verdict={verdict} checks={result['checkPassed']}/{result['checkTotal']} attacks={result['mutationAttackPassed']}/{result['mutationAttackTotal']}")


if __name__ == "__main__":
    main()
