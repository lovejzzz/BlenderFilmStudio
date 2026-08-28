#!/usr/bin/env python3
"""Independent scalar Python oracle for B52-D12.14-C1."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
from pathlib import Path


SPEC_SHA256 = "fd3fe2808346c49a87183b3ed215b07abcbaf4058df13d055cc893b482ae30f5"
TARGETS = (
    "TOP_MISSING_BOTTOM_AVAILABLE",
    "BOTTOM_MISSING_TOP_AVAILABLE",
    "NEITHER_HORIZONTAL_AVAILABLE",
)
TARGET_CODE = {name: index for index, name in enumerate(TARGETS, start=1)}
MASK_NAMES = (
    "current-interior",
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


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def fixed(value: float) -> int:
    return int(math.floor(value * 1_000_000.0 + 0.5))


def inside(rect: tuple[float, float, float, float], x: int, y: int) -> bool:
    left, top, right, bottom = rect
    return left <= x <= right and top <= y <= bottom


def target_prefix(target: str) -> str:
    return {
        "TOP_MISSING_BOTTOM_AVAILABLE": "TOP",
        "BOTTOM_MISSING_TOP_AVAILABLE": "BOTTOM",
        "NEITHER_HORIZONTAL_AVAILABLE": "NEITHER",
    }[target]


def candidate_id(target: str, ordinal: int) -> str:
    return f"{target_prefix(target)}-{ordinal:06d}"


def directional_masks(candidate: dict, keep_masks: bool = False) -> tuple[dict, dict[str, bytearray] | None]:
    width, height = candidate["resolution"]
    current_rect = candidate["currentRect"]
    previous_rect = candidate["previousRect"]
    current_center = candidate["currentCenter"]
    previous_center = candidate["previousCenter"]
    scale_x, scale_y = candidate["scale"]
    masks = {name: bytearray(width * height) for name in MASK_NAMES} if keep_masks else None
    counts = {name: 0 for name in MASK_NAMES}

    def mark(name: str, index: int, value: bool) -> None:
        if value:
            counts[name] += 1
            if masks is not None:
                masks[name][index] = 1

    for y in range(2, height - 2):
        for x in range(2, width - 2):
            interior = inside(current_rect, x - 2, y - 2) and inside(current_rect, x + 2, y + 2)
            if not interior:
                continue
            index = y * width + x
            mark("current-interior", index, True)
            previous_x = previous_center[0] + (x - current_center[0]) / scale_x
            previous_y = previous_center[1] + (y - current_center[1]) / scale_y
            x0, y0 = math.floor(previous_x), math.floor(previous_y)
            taps = ((x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1))
            bilinear = all(0 <= px < width and 0 <= py < height and inside(previous_rect, px, py) for px, py in taps)
            mark("bilinear-support", index, bilinear)
            if not bilinear:
                continue
            left0 = x0 - 1 >= 0 and inside(previous_rect, x0 - 1, y0)
            right0 = x0 + 2 < width and inside(previous_rect, x0 + 2, y0)
            left1 = x0 - 1 >= 0 and inside(previous_rect, x0 - 1, y0 + 1)
            right1 = x0 + 2 < width and inside(previous_rect, x0 + 2, y0 + 1)
            left = left0 and left1
            right = right0 and right1
            top = y0 - 1 >= 0 and inside(previous_rect, x0, y0 - 1) and inside(previous_rect, x0 + 1, y0 - 1)
            bottom = y0 + 2 < height and inside(previous_rect, x0, y0 + 2) and inside(previous_rect, x0 + 1, y0 + 2)
            direction_left = (not left) and right and top and bottom
            direction_right = left and (not right) and top and bottom
            direction_top = (not top) and bottom and left and right
            direction_bottom = top and (not bottom) and left and right
            neither = ((not left0 and not right0) or (not left1 and not right1))
            full = left and right and top and bottom
            values = {
                "direction-left": direction_left,
                "direction-right": direction_right,
                "direction-top": direction_top,
                "direction-bottom": direction_bottom,
                "neither-horizontal": neither,
                "full-stencil": full,
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


def vertical_candidates(spec: dict, target: str) -> list[dict]:
    grid = spec["searchSpace"]["vertical"]
    width, height = grid["resolutionByTarget"][target]
    center_x, center_y = (width - 1) / 2.0, (height - 1) / 2.0
    rows = []
    ordinal = 0
    for current_width in grid["currentWidthPixels"]:
        for current_height in grid["currentHeightPixels"]:
            for scale_x in grid["scaleX"]:
                for scale_y_index, scale_y in enumerate(grid["scaleY"]):
                    for phase_index, phase in enumerate(grid["targetEdgePhase"]):
                        for orthogonal_offset in grid["orthogonalCenterOffsetPixels"]:
                            for current_axis_offset in grid["targetAxisCurrentCenterOffsetPixels"]:
                                current_center = (center_x, center_y + current_axis_offset)
                                current_rect = (
                                    current_center[0] - current_width / 2.0,
                                    current_center[1] - current_height / 2.0,
                                    current_center[0] + current_width / 2.0,
                                    current_center[1] + current_height / 2.0,
                                )
                                previous_width = current_width / scale_x
                                previous_height = current_height / scale_y
                                anchor = math.floor((height - previous_height) / 2.0) + phase
                                if target == "TOP_MISSING_BOTTOM_AVAILABLE":
                                    previous_top = anchor
                                    previous_bottom = previous_top + previous_height
                                else:
                                    previous_bottom = height - 1 - anchor
                                    previous_top = previous_bottom - previous_height
                                previous_center = (center_x + orthogonal_offset, (previous_top + previous_bottom) / 2.0)
                                previous_rect = (
                                    previous_center[0] - previous_width / 2.0,
                                    previous_top,
                                    previous_center[0] + previous_width / 2.0,
                                    previous_bottom,
                                )
                                rows.append({
                                    "id": candidate_id(target, ordinal),
                                    "ordinal": ordinal,
                                    "target": target,
                                    "resolution": [width, height],
                                    "currentRect": current_rect,
                                    "previousRect": previous_rect,
                                    "currentCenter": current_center,
                                    "previousCenter": previous_center,
                                    "scale": (scale_x, scale_y),
                                    "phaseIndex": phase_index,
                                    "scaleIndex": scale_y_index,
                                    "neighborhoodKey": [fixed(current_width), fixed(current_height), fixed(scale_x), fixed(scale_y), fixed(orthogonal_offset), fixed(current_axis_offset)],
                                })
                                ordinal += 1
    return rows


def neither_candidates(spec: dict) -> list[dict]:
    target = "NEITHER_HORIZONTAL_AVAILABLE"
    grid = spec["searchSpace"]["neitherHorizontal"]
    width, height = grid["resolution"]
    center_x, center_y = (width - 1) / 2.0, (height - 1) / 2.0
    rows = []
    ordinal = 0
    for current_width in grid["currentWidthPixels"]:
        for current_height in grid["currentHeightPixels"]:
            for previous_width in grid["previousWidthPixels"]:
                for previous_height in grid["previousHeightPixels"]:
                    for phase_index, phase in enumerate(grid["previousCenterPhaseX"]):
                        for previous_offset_y in grid["previousCenterOffsetY"]:
                            current_center = (center_x, center_y)
                            previous_center = (math.floor(center_x) + phase, center_y + previous_offset_y)
                            current_rect = (
                                current_center[0] - current_width / 2.0,
                                current_center[1] - current_height / 2.0,
                                current_center[0] + current_width / 2.0,
                                current_center[1] + current_height / 2.0,
                            )
                            previous_rect = (
                                previous_center[0] - previous_width / 2.0,
                                previous_center[1] - previous_height / 2.0,
                                previous_center[0] + previous_width / 2.0,
                                previous_center[1] + previous_height / 2.0,
                            )
                            rows.append({
                                "id": candidate_id(target, ordinal),
                                "ordinal": ordinal,
                                "target": target,
                                "resolution": [width, height],
                                "currentRect": current_rect,
                                "previousRect": previous_rect,
                                "currentCenter": current_center,
                                "previousCenter": previous_center,
                                "scale": (current_width / previous_width, current_height / previous_height),
                                "phaseIndex": phase_index,
                                "neighborhoodKey": [fixed(current_width), fixed(current_height), fixed(previous_width), fixed(previous_height), fixed(previous_offset_y)],
                            })
                            ordinal += 1
    return rows


def row_payload(candidate: dict, counts: dict, neighborhood_minimum: int, passed: bool) -> list[int]:
    cr, pr = candidate["currentRect"], candidate["previousRect"]
    cc, pc = candidate["currentCenter"], candidate["previousCenter"]
    sx, sy = candidate["scale"]
    return [
        TARGET_CODE[candidate["target"]], candidate["ordinal"], *candidate["resolution"],
        *(fixed(value) for value in cr), *(fixed(value) for value in pr),
        fixed(cc[0]), fixed(cc[1]), fixed(pc[0]), fixed(pc[1]), fixed(sx), fixed(sy),
        counts["current-interior"], counts["bilinear-support"],
        counts["direction-left"], counts["direction-right"], counts["direction-top"], counts["direction-bottom"],
        counts["neither-horizontal"], counts["full-stencil"], counts["target"], counts["non-target-one-sided"],
        neighborhood_minimum, int(passed),
    ]


def evaluate_target(spec: dict, candidates: list[dict]) -> tuple[list[list[int]], dict | None, dict[str, bytearray] | None]:
    measured = []
    lookup: dict[tuple, dict[int, int]] = {}
    for candidate in candidates:
        counts, _ = directional_masks(candidate)
        candidate["counts"] = counts
        lookup.setdefault(tuple(candidate["neighborhoodKey"]), {})[candidate["phaseIndex"]] = counts["target"]
    contract = spec["measurementContract"]
    target = candidates[0]["target"]
    target_floor = contract["neitherHorizontalMinimumWitnesses"] if target == "NEITHER_HORIZONTAL_AVAILABLE" else contract["perVerticalTargetMinimumWitnesses"]
    phase_count = max(candidate["phaseIndex"] for candidate in candidates) + 1
    passing = []
    for candidate in candidates:
        neighbors = lookup[tuple(candidate["neighborhoodKey"])]
        indices = [index for index in (candidate["phaseIndex"] - 1, candidate["phaseIndex"], candidate["phaseIndex"] + 1) if 0 <= index < phase_count]
        neighborhood_minimum = min(neighbors[index] for index in indices)
        counts = candidate["counts"]
        one_sided = counts["target"] + counts["non-target-one-sided"]
        purity_ok = one_sided > 0 and counts["non-target-one-sided"] * 100 <= 5 * one_sided
        passed = (
            counts["target"] >= target_floor
            and counts["current-interior"] >= contract["minimumCurrentInterior"]
            and counts["bilinear-support"] >= contract["minimumBilinearSupport"]
            and neighborhood_minimum >= contract["minimumNeighborhoodTargetWitnesses"]
            and purity_ok
        )
        candidate["neighborhoodMinimum"] = neighborhood_minimum
        candidate["passed"] = passed
        measured.append(row_payload(candidate, counts, neighborhood_minimum, passed))
        if passed:
            passing.append(candidate)
    if not passing:
        return measured, None, None
    scale_index = 1 if target != "NEITHER_HORIZONTAL_AVAILABLE" else 0
    selected = sorted(
        passing,
        key=lambda row: (
            -row["neighborhoodMinimum"],
            row["counts"]["non-target-one-sided"],
            fixed(row["scale"][scale_index]),
            row["id"],
        ),
    )[0]
    selected_counts, masks = directional_masks(selected, keep_masks=True)
    if selected_counts != selected["counts"] or masks is None:
        raise RuntimeError("D12.14-C1 selected mask replay mismatch")
    return measured, selected, masks


def report_candidate(candidate: dict) -> dict:
    return {
        "candidateId": candidate["id"],
        "target": candidate["target"],
        "ordinal": candidate["ordinal"],
        "resolution": candidate["resolution"],
        "currentRect": list(candidate["currentRect"]),
        "previousRect": list(candidate["previousRect"]),
        "currentCenter": list(candidate["currentCenter"]),
        "previousCenter": list(candidate["previousCenter"]),
        "scale": list(candidate["scale"]),
        "phaseIndex": candidate["phaseIndex"],
        "neighborhoodMinimumTargetWitnesses": candidate["neighborhoodMinimum"],
        "counts": candidate["counts"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if sha_file(args.spec) != SPEC_SHA256 or args.output.exists():
        raise RuntimeError("D12.14-C1 spec identity or output freshness failure")
    spec = json.loads(args.spec.read_text())
    args.output.mkdir(parents=True)
    all_rows: list[list[int]] = []
    selected_reports = []
    selected_hashes = {}
    for target in TARGETS:
        candidates = neither_candidates(spec) if target == "NEITHER_HORIZONTAL_AVAILABLE" else vertical_candidates(spec, target)
        rows, selected, masks = evaluate_target(spec, candidates)
        all_rows.extend(rows)
        target_hashes = {}
        if selected is not None and masks is not None:
            selected_dir = args.output / "selected" / target
            selected_dir.mkdir(parents=True)
            for name in MASK_NAMES:
                path = selected_dir / f"{name}.u8"
                path.write_bytes(masks[name])
                target_hashes[name] = {"sha256": sha_file(path), "bytes": path.stat().st_size}
        selected_hashes[target] = target_hashes
        selected_reports.append(report_candidate(selected) if selected is not None else {"target": target, "candidateId": None})
    candidate_bytes = json.dumps(all_rows, separators=(",", ":"), allow_nan=False).encode()
    candidate_path = args.output / "candidates.bin"
    candidate_path.write_bytes(candidate_bytes)
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerDirectionalFixtureCalibrationOracleReport.v0.1",
        "experimentId": spec["experimentId"],
        "specSha256": SPEC_SHA256,
        "language": "python",
        "pid": os.getpid(),
        "runtime": {"python": platform.python_version(), "executable": sys.executable, "executableSha256": sha_file(Path(sys.executable))},
        "candidateCount": len(all_rows),
        "candidateTable": {"uri": str(candidate_path), "sha256": sha_file(candidate_path), "bytes": candidate_path.stat().st_size},
        "selected": selected_reports,
        "selectedMasks": selected_hashes,
        "operationCounts": {"blenderProcesses": 0, "blenderRenderCalls": 0, "cyclesRayRenders": 0, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1214C1_PYTHON_OK candidates={len(all_rows)} selected={','.join(row['candidateId'] for row in selected_reports)}")


if __name__ == "__main__":
    main()
