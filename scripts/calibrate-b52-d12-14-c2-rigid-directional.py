#!/usr/bin/env python3
"""Independent scalar Python 3D oracle for B52-D12.14-C2."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
from pathlib import Path


SPEC_SHA256 = "e123b80fdba40c7e7e396e1aad149573e1e123c57198a21fa8af944320d7e4c3"
TARGETS = (
    "TOP_MISSING_BOTTOM_AVAILABLE",
    "BOTTOM_MISSING_TOP_AVAILABLE",
    "NEITHER_HORIZONTAL_AVAILABLE",
)
TARGET_CODE = {target: index for index, target in enumerate(TARGETS, 1)}
MASK_NAMES = (
    "current-foreground",
    "current-radius2",
    "previous-foreground",
    "bilinear-support",
    "direction-left",
    "direction-right",
    "direction-top",
    "direction-bottom",
    "neither-horizontal",
    "full-stencil",
    "target",
    "non-target-one-sided",
)


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def fixed(value: float) -> int:
    return int(math.floor(value * 1_000_000.0 + 0.5)) if value >= 0 else -int(math.floor(-value * 1_000_000.0 + 0.5))


def rotation_xyz(values: tuple[float, float, float]) -> tuple[tuple[float, float, float], ...]:
    x, y, z = values
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)
    return (
        (cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
        (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx + cz * sx),
        (-sy, cy * sx, cy * cx),
    )


def add(left, right):
    return tuple(left[index] + right[index] for index in range(3))


def subtract(left, right):
    return tuple(left[index] - right[index] for index in range(3))


def scale(vector, amount):
    return tuple(vector[index] * amount for index in range(3))


def dot(left, right):
    return sum(left[index] * right[index] for index in range(3))


def mat_vec(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3))


def mat_t_vec(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[row] for row in range(3)) for column in range(3))


def transform(location, rotation):
    return tuple(float(value) for value in location), rotation_xyz(tuple(float(value) for value in rotation))


def camera_ray(spec: dict, width: int, height: int, pixel_x: float, pixel_y: float):
    camera = spec["sceneContract"]["camera"]
    sensor_width = float(camera["sensorWidthMm"])
    sensor_height = sensor_width * height / width
    lens = float(camera["lensMm"])
    u = (pixel_x + 0.5) / width
    v_bottom = 1.0 - (pixel_y + 0.5) / height
    return (
        (u - 0.5) * sensor_width / lens,
        (v_bottom - 0.5) * sensor_height / lens,
        -1.0,
    )


def intersect_plane(camera_location, direction, owner: dict):
    owner_location, owner_rotation = transform(owner["location"], owner["rotationEuler"])
    normal = mat_vec(owner_rotation, (0.0, 0.0, 1.0))
    denominator = dot(direction, normal)
    if denominator == 0.0:
        return None
    distance = dot(subtract(owner_location, camera_location), normal) / denominator
    if distance <= 0.0:
        return None
    world_point = add(camera_location, scale(direction, distance))
    local_point = mat_t_vec(owner_rotation, subtract(world_point, owner_location))
    size_x, size_y = owner["size"]
    if abs(local_point[0]) > size_x / 2.0 or abs(local_point[1]) > size_y / 2.0:
        return None
    depth = camera_location[2] - world_point[2]
    if depth <= 0.0:
        return None
    return depth, local_point


def prepared_owner(owner_id: str, size, location, rotation):
    owner_location, owner_rotation = transform(location, rotation)
    return {
        "id": owner_id,
        "size": tuple(float(value) for value in size),
        "location": owner_location,
        "rotation": owner_rotation,
        "normal": mat_vec(owner_rotation, (0.0, 0.0, 1.0)),
    }


def intersect_prepared(camera_location, direction, owner: dict):
    denominator = dot(direction, owner["normal"])
    if denominator == 0.0:
        return None
    distance = dot(subtract(owner["location"], camera_location), owner["normal"]) / denominator
    if distance <= 0.0:
        return None
    world_point = add(camera_location, scale(direction, distance))
    local_point = mat_t_vec(owner["rotation"], subtract(world_point, owner["location"]))
    if abs(local_point[0]) > owner["size"][0] / 2.0 or abs(local_point[1]) > owner["size"][1] / 2.0:
        return None
    depth = camera_location[2] - world_point[2]
    return (depth, local_point) if depth > 0.0 else None


def surface_at(spec: dict, candidate: dict, frame: int, x: float, y: float):
    width, height = candidate["resolution"]
    camera_location = tuple(float(value) for value in spec["sceneContract"]["camera"]["location"])
    direction = camera_ray(spec, width, height, x, y)
    foreground = {
        "id": "foreground",
        "size": tuple(float(value) for value in spec["sceneContract"]["foreground"]["sizeWorld"]),
        "location": candidate["previousLocation"] if frame == 0 else candidate["currentLocation"],
        "rotationEuler": candidate["previousRotation"] if frame == 0 else candidate["currentRotation"],
    }
    background_spec = spec["sceneContract"]["background"]
    background = {
        "id": "background",
        "size": tuple(float(value) for value in background_spec["sizeWorld"]),
        "location": tuple(float(value) for value in background_spec["locationByFrame"][str(frame)]),
        "rotationEuler": tuple(float(value) for value in background_spec["rotationEulerByFrame"][str(frame)]),
    }
    hits = []
    for owner in (foreground, background):
        hit = intersect_plane(camera_location, direction, owner)
        if hit is not None:
            hits.append((hit[0], owner["id"], hit[1]))
    return min(hits, key=lambda row: row[0]) if hits else None


def project(spec: dict, candidate: dict, world_point):
    width, height = candidate["resolution"]
    camera = spec["sceneContract"]["camera"]
    camera_location = tuple(float(value) for value in camera["location"])
    relative = subtract(world_point, camera_location)
    depth = -relative[2]
    if depth <= 0.0:
        return None
    sensor_width = float(camera["sensorWidthMm"])
    sensor_height = sensor_width * height / width
    lens = float(camera["lensMm"])
    return (
        (0.5 + lens * relative[0] / (depth * sensor_width)) * width - 0.5,
        (0.5 - lens * relative[1] / (depth * sensor_height)) * height - 0.5,
    )


def raster_frame(spec: dict, candidate: dict, frame: int, keep_local: bool):
    width, height = candidate["resolution"]
    camera_location = tuple(float(value) for value in spec["sceneContract"]["camera"]["location"])
    foreground_spec = spec["sceneContract"]["foreground"]
    foreground = prepared_owner(
        "foreground", foreground_spec["sizeWorld"],
        candidate["previousLocation"] if frame == 0 else candidate["currentLocation"],
        candidate["previousRotation"] if frame == 0 else candidate["currentRotation"],
    )
    background_spec = spec["sceneContract"]["background"]
    background = prepared_owner(
        "background", background_spec["sizeWorld"], background_spec["locationByFrame"][str(frame)], background_spec["rotationEulerByFrame"][str(frame)]
    )
    mask = bytearray(width * height)
    local_points: list[tuple[float, float, float] | None] | None = [None] * (width * height) if keep_local else None
    for y in range(height):
        for x in range(width):
            index = y * width + x
            direction = camera_ray(spec, width, height, x, y)
            hits = []
            for owner in (foreground, background):
                hit = intersect_prepared(camera_location, direction, owner)
                if hit is not None:
                    hits.append((hit[0], owner["id"], hit[1]))
            surface = min(hits, key=lambda row: row[0]) if hits else None
            if surface is not None and surface[1] == "foreground":
                mask[index] = 1
                if local_points is not None:
                    local_points[index] = surface[2]
    return mask, local_points


def foreground_rasters(spec: dict, candidate: dict, caches: dict):
    resolution_key = tuple(candidate["resolution"])
    current_key = (resolution_key, tuple(candidate["currentLocation"]), tuple(candidate["currentRotation"]))
    previous_key = (resolution_key, tuple(candidate["previousLocation"]), tuple(candidate["previousRotation"]))
    if current_key not in caches["current"]:
        caches["current"][current_key] = raster_frame(spec, candidate, 1, True)
    if previous_key not in caches["previous"]:
        caches["previous"][previous_key] = raster_frame(spec, candidate, 0, False)[0]
    current, current_local = caches["current"][current_key]
    previous = caches["previous"][previous_key]
    return current, previous, current_local


def directional_masks(spec: dict, candidate: dict, caches: dict, keep_masks: bool = False):
    width, height = candidate["resolution"]
    current, previous, current_local = foreground_rasters(spec, candidate, caches)
    masks = {name: bytearray(width * height) for name in MASK_NAMES} if keep_masks else None
    counts = {name: 0 for name in MASK_NAMES}
    counts["current-foreground"] = sum(current)
    counts["previous-foreground"] = sum(previous)
    if masks is not None:
        masks["current-foreground"][:] = current
        masks["previous-foreground"][:] = previous

    def mark(name: str, index: int, value: bool) -> None:
        if value:
            counts[name] += 1
            if masks is not None:
                masks[name][index] = 1

    previous_transform = transform(candidate["previousLocation"], candidate["previousRotation"])
    for y in range(2, height - 2):
        for x in range(2, width - 2):
            index = y * width + x
            interior = all(current[(y + dy) * width + x + dx] for dy in range(-2, 3) for dx in range(-2, 3))
            if not interior:
                continue
            mark("current-radius2", index, True)
            local_point = current_local[index] if current_local is not None else None
            if local_point is None:
                raise RuntimeError("D12.14-C2 missing current local point")
            previous_world = add(previous_transform[0], mat_vec(previous_transform[1], local_point))
            coordinate = project(spec, candidate, previous_world)
            if coordinate is None:
                continue
            x0, y0 = math.floor(coordinate[0]), math.floor(coordinate[1])

            def valid(px: int, py: int) -> bool:
                return 0 <= px < width and 0 <= py < height and bool(previous[py * width + px])

            bilinear = valid(x0, y0) and valid(x0 + 1, y0) and valid(x0, y0 + 1) and valid(x0 + 1, y0 + 1)
            mark("bilinear-support", index, bilinear)
            if not bilinear:
                continue
            left0, right0 = valid(x0 - 1, y0), valid(x0 + 2, y0)
            left1, right1 = valid(x0 - 1, y0 + 1), valid(x0 + 2, y0 + 1)
            left, right = left0 and left1, right0 and right1
            top = valid(x0, y0 - 1) and valid(x0 + 1, y0 - 1)
            bottom = valid(x0, y0 + 2) and valid(x0 + 1, y0 + 2)
            values = {
                "direction-left": (not left) and right and top and bottom,
                "direction-right": left and (not right) and top and bottom,
                "direction-top": left and right and (not top) and bottom,
                "direction-bottom": left and right and top and (not bottom),
                "neither-horizontal": (not left0 and not right0) or (not left1 and not right1),
                "full-stencil": left and right and top and bottom,
            }
            for name, value in values.items():
                mark(name, index, value)
            target_name = {
                "TOP_MISSING_BOTTOM_AVAILABLE": "direction-top",
                "BOTTOM_MISSING_TOP_AVAILABLE": "direction-bottom",
                "NEITHER_HORIZONTAL_AVAILABLE": "neither-horizontal",
            }[candidate["target"]]
            target = values[target_name]
            non_target = any(value for name, value in values.items() if name not in (target_name, "full-stencil"))
            mark("target", index, target)
            mark("non-target-one-sided", index, non_target)
    return counts, masks


def candidate_id(target: str, ordinal: int) -> str:
    prefix = {"TOP_MISSING_BOTTOM_AVAILABLE": "TOP", "BOTTOM_MISSING_TOP_AVAILABLE": "BOTTOM", "NEITHER_HORIZONTAL_AVAILABLE": "NEITHER"}[target]
    return f"{prefix}-{ordinal:06d}"


def vertical_candidates(spec: dict, target: str):
    grid = spec["searchSpace"]["vertical"]
    resolution = grid["resolutionByTarget"][target]
    ordinal = 0
    rows = []
    for current_x in grid["currentX"]:
        for current_y in grid["currentYByTarget"][target]:
            for current_z in grid["currentZ"]:
                for previous_x in grid["previousX"]:
                    for delta_index, delta_y in enumerate(grid["previousYDeltaFromCurrent"]):
                        for previous_z in grid["previousZ"]:
                            rows.append({
                                "id": candidate_id(target, ordinal), "ordinal": ordinal, "target": target, "resolution": resolution,
                                "currentLocation": (current_x, current_y, current_z), "currentRotation": (0.0, 0.0, 0.0),
                                "previousLocation": (previous_x, current_y + delta_y, previous_z), "previousRotation": (0.0, 0.0, 0.0),
                                "deltaY": delta_y, "robustnessIndex": delta_index,
                                "robustnessKey": (fixed(current_x), fixed(current_y), fixed(current_z), fixed(previous_x), fixed(previous_z)),
                            })
                            ordinal += 1
    return rows


def neither_candidates(spec: dict):
    target = "NEITHER_HORIZONTAL_AVAILABLE"
    grid = spec["searchSpace"]["neither"]
    ordinal = 0
    rows = []
    current_location = tuple(float(value) for value in grid["currentLocation"])
    current_rotation = tuple(math.radians(float(value)) for value in grid["currentRotationEulerDegrees"])
    for previous_x in grid["previousX"]:
        for previous_y in grid["previousY"]:
            for z_index, previous_z in enumerate(grid["previousZ"]):
                for angle in grid["previousRotationYDegrees"]:
                    for rotation_x in grid["previousRotationXDegrees"]:
                        for rotation_z in grid["previousRotationZDegrees"]:
                            rows.append({
                                "id": candidate_id(target, ordinal), "ordinal": ordinal, "target": target, "resolution": grid["resolution"],
                                "currentLocation": current_location, "currentRotation": current_rotation,
                                "previousLocation": (previous_x, previous_y, previous_z),
                                "previousRotation": (math.radians(rotation_x), math.radians(angle), math.radians(rotation_z)),
                                "previousRotationDegrees": (rotation_x, angle, rotation_z), "angleDegrees": angle,
                                "robustnessIndex": z_index,
                                "robustnessKey": (fixed(previous_x), fixed(previous_y), fixed(angle), fixed(rotation_x), fixed(rotation_z)),
                            })
                            ordinal += 1
    return rows


def row_payload(candidate: dict, counts: dict, neighborhood_minimum: int, passed: bool):
    rotation_degrees = candidate.get("previousRotationDegrees", tuple(math.degrees(value) for value in candidate["previousRotation"]))
    return [
        TARGET_CODE[candidate["target"]], candidate["ordinal"], *candidate["resolution"],
        *(fixed(value) for value in candidate["currentLocation"]), *(fixed(math.degrees(value)) for value in candidate["currentRotation"]),
        *(fixed(value) for value in candidate["previousLocation"]), *(fixed(value) for value in rotation_degrees),
        counts["current-foreground"], counts["current-radius2"], counts["previous-foreground"], counts["bilinear-support"],
        counts["direction-left"], counts["direction-right"], counts["direction-top"], counts["direction-bottom"],
        counts["neither-horizontal"], counts["full-stencil"], counts["target"], counts["non-target-one-sided"],
        neighborhood_minimum, int(passed),
    ]


def evaluate_target(spec: dict, candidates: list[dict], caches: dict):
    lookup: dict[tuple, dict[int, int]] = {}
    for candidate in candidates:
        counts, _ = directional_masks(spec, candidate, caches)
        candidate["counts"] = counts
        lookup.setdefault(candidate["robustnessKey"], {})[candidate["robustnessIndex"]] = counts["target"]
    target = candidates[0]["target"]
    contract = spec["measurementContract"]
    target_floor = contract["neitherTargetMinimumWitnesses"] if target == "NEITHER_HORIZONTAL_AVAILABLE" else contract["verticalTargetMinimumWitnesses"]
    neighborhood_floor = contract["neitherNeighborhoodMinimumWitnesses"] if target == "NEITHER_HORIZONTAL_AVAILABLE" else contract["verticalNeighborhoodMinimumWitnesses"]
    axis_count = max(row["robustnessIndex"] for row in candidates) + 1
    rows, passing = [], []
    for candidate in candidates:
        neighbors = lookup[candidate["robustnessKey"]]
        indices = [index for index in (candidate["robustnessIndex"] - 1, candidate["robustnessIndex"], candidate["robustnessIndex"] + 1) if 0 <= index < axis_count]
        neighborhood_minimum = min(neighbors[index] for index in indices)
        counts = candidate["counts"]
        passed = (
            counts["target"] >= target_floor
            and neighborhood_minimum >= neighborhood_floor
            and counts["current-radius2"] >= contract["minimumCurrentForegroundRadius2"]
            and counts["bilinear-support"] >= contract["minimumBilinearSupport"]
            and counts["non-target-one-sided"] <= contract["maximumNonTargetOneSidedWitnesses"]
        )
        candidate["neighborhoodMinimum"] = neighborhood_minimum
        candidate["passed"] = passed
        rows.append(row_payload(candidate, counts, neighborhood_minimum, passed))
        if passed:
            passing.append(candidate)
    if not passing:
        return rows, None, None
    if target == "NEITHER_HORIZONTAL_AVAILABLE":
        sort_key = lambda row: (-row["neighborhoodMinimum"], -row["counts"]["target"], fixed(abs(90.0 - row["angleDegrees"])), fixed(abs(row["previousLocation"][0])), row["id"])
    else:
        sort_key = lambda row: (-row["neighborhoodMinimum"], -row["counts"]["target"], fixed(abs(row["deltaY"])), row["id"])
    selected = sorted(passing, key=sort_key)[0]
    replay_counts, masks = directional_masks(spec, selected, caches, keep_masks=True)
    if replay_counts != selected["counts"] or masks is None:
        raise RuntimeError("D12.14-C2 selected replay mismatch")
    return rows, selected, masks


def report_candidate(candidate: dict):
    return {
        "candidateId": candidate["id"], "target": candidate["target"], "ordinal": candidate["ordinal"], "resolution": candidate["resolution"],
        "currentLocation": list(candidate["currentLocation"]), "currentRotationEuler": list(candidate["currentRotation"]),
        "previousLocation": list(candidate["previousLocation"]), "previousRotationEuler": list(candidate["previousRotation"]),
        "neighborhoodMinimumTargetWitnesses": candidate["neighborhoodMinimum"], "counts": candidate["counts"],
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    if sha_file(args.spec) != SPEC_SHA256 or args.output.exists():
        raise RuntimeError("D12.14-C2 spec identity or output freshness failure")
    spec = json.loads(args.spec.read_text())
    args.output.mkdir(parents=True)
    all_rows, selected_reports, selected_hashes = [], [], {}
    caches = {"current": {}, "previous": {}}
    for target in TARGETS:
        candidates = neither_candidates(spec) if target == "NEITHER_HORIZONTAL_AVAILABLE" else vertical_candidates(spec, target)
        rows, selected, masks = evaluate_target(spec, candidates, caches)
        all_rows.extend(rows)
        hashes = {}
        if selected is not None and masks is not None:
            selected_dir = args.output / "selected" / target
            selected_dir.mkdir(parents=True)
            for name in MASK_NAMES:
                mask_path = selected_dir / f"{name}.u8"
                mask_path.write_bytes(masks[name])
                hashes[name] = {"sha256": sha_file(mask_path), "bytes": mask_path.stat().st_size}
            selected_reports.append(report_candidate(selected))
        else:
            selected_reports.append({"target": target, "candidateId": None})
        selected_hashes[target] = hashes
    candidate_path = args.output / "candidates.bin"
    candidate_path.write_bytes(json.dumps(all_rows, separators=(",", ":"), allow_nan=False).encode())
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalCalibrationOracleReport.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "language": "python", "pid": os.getpid(),
        "runtime": {"python": platform.python_version(), "executable": sys.executable, "executableSha256": sha_file(Path(sys.executable))},
        "candidateCount": len(all_rows),
        "candidateTable": {"uri": str(candidate_path), "sha256": sha_file(candidate_path), "bytes": candidate_path.stat().st_size},
        "selected": selected_reports, "selectedMasks": selected_hashes,
        "operationCounts": {"blenderProcesses": 0, "blenderRenderCalls": 0, "cyclesRayRenders": 0, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1214C2_PYTHON_OK candidates={len(all_rows)} selected={','.join(row['candidateId'] or 'NONE' for row in selected_reports)}")


if __name__ == "__main__":
    main()
