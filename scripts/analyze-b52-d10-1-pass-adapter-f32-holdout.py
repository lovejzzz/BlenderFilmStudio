#!/usr/bin/env python3
"""Independently analyze the frozen B52-D10.1 real-Blender adapter holdout."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "11686c5e796c7bc1b4e45cf137c3d98347bc65bfec428f9d19545b55430f584b"
FILES = {
    "previousRgba": "previous.rgba32",
    "currentRgba": "current.rgba32",
    "previousDepth": "previous-depth.f32",
    "currentDepth": "current-depth.f32",
    "previousLayer": "previous-layer.f32",
    "currentLayer": "current-layer.f32",
    "motion": "motion.xy32",
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
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def float32_roundtrip(value: float) -> float:
    """Return the exact Python-float representation of one IEEE-754 binary32 value."""
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def next_float32_toward_positive_infinity(value: float) -> float:
    """Return the adjacent finite binary32 value toward positive infinity."""
    canonical = float32_roundtrip(value)
    if not math.isfinite(canonical):
        raise ValueError("finite binary32 required")
    bits = struct.unpack("<I", struct.pack("<f", canonical))[0]
    bits = bits + 1 if canonical >= 0.0 else bits - 1
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def array_bytes(value: np.ndarray) -> bytes:
    return np.ascontiguousarray(value, dtype="<f4").tobytes(order="C")


def array_hash(value: np.ndarray) -> str:
    return sha256_bytes(array_bytes(value))


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_multipart(path: Path) -> dict:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    roster, channels, parts = [], {}, {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        image_spec = image.spec()
        name = str(image_spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        roster.append(name)
        channels[name] = list(image_spec.channelnames)
        parts[name] = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
    return {"roster": roster, "channels": channels, "parts": parts}


def finite_stats(values: np.ndarray, prefix: str = "") -> dict:
    flat = np.asarray(values, dtype=np.float64).reshape(-1)
    title = lambda name: f"{prefix}{name[0].upper()}{name[1:]}" if prefix else name
    return {
        title("finite"): bool(flat.size and np.isfinite(flat).all()),
        title("minimum"): float(np.min(flat)),
        title("p50"): float(np.quantile(flat, 0.5)),
        title("p99"): float(np.quantile(flat, 0.99)),
        title("maximum"): float(np.max(flat)),
    }


def report_self_valid(report: dict) -> bool:
    body = {key: value for key, value in report.items() if key != "reportHash"}
    return report.get("reportHash") == canonical_hash(body)


def object_location(spec: dict, fixture: dict, name: str, frame: int) -> list[float]:
    base = next(item["location"] for item in spec["scene"]["objects"] if item["name"] == name)
    if name == "BFS_F32_MOVER" and fixture["moverByFrame"] is not None:
        return fixture["moverByFrame"][str(frame)]
    return base


def camera_location(spec: dict, fixture: dict, frame: int) -> list[float]:
    if fixture["cameraByFrame"] is not None:
        return fixture["cameraByFrame"][str(frame)]
    return spec["scene"]["camera"]["location"]


def screen_up(spec: dict, fixture: dict, name: str, frame: int, offset: list[float] | None = None) -> np.ndarray:
    width, height = spec["sourceRender"]["resolution"]
    scale = spec["scene"]["camera"]["orthoScale"]
    point = np.asarray(object_location(spec, fixture, name, frame), dtype=np.float64)
    if offset is not None:
        point[:2] += np.asarray(offset, dtype=np.float64)
    camera = np.asarray(camera_location(spec, fixture, frame), dtype=np.float64)
    return np.asarray([width / 2.0 + (point[0] - camera[0]) * width / scale, height / 2.0 + (point[1] - camera[1]) * width / scale], dtype=np.float64)


def top_left_probe(spec: dict, fixture: dict, item: dict, frame: int) -> tuple[int, int]:
    width, height = spec["sourceRender"]["resolution"]
    value = screen_up(spec, fixture, item["name"], frame, item["probeOffsetXY"])
    x = int(math.floor(value[0]))
    y = int(math.floor(height - value[1]))
    if not (0 <= x < width and 0 <= y < height):
        raise RuntimeError("analytic ownership probe out of bounds")
    return x, y


def expected_vectors(spec: dict, fixture: dict, name: str) -> tuple[np.ndarray, np.ndarray]:
    previous = screen_up(spec, fixture, name, spec["scene"]["previousFrame"])
    current = screen_up(spec, fixture, name, spec["scene"]["currentFrame"])
    following = screen_up(spec, fixture, name, spec["scene"]["nextFrame"])
    return previous - current, current - following


def expected_action(values: dict[str, list[float]] | None, *, canonicalize: bool = True) -> list[dict]:
    if values is None:
        return []
    convert = float32_roundtrip if canonicalize else float
    return [
        {
            "layerIndex": 0,
            "stripIndex": 0,
            "channelBagIndex": 0,
            "dataPath": "location",
            "arrayIndex": axis,
            "keyframes": [{"frame": convert(frame), "value": convert(location[axis]), "interpolation": "LINEAR"} for frame, location in values.items()],
        }
        for axis in range(3)
    ]


def expected_scene_structure(spec: dict, fixture: dict, frame: int, repeat: int, *, canonicalize: bool = True) -> dict:
    camera_spec = spec["scene"]["camera"]
    convert = float32_roundtrip if canonicalize else float
    return {
        "sceneName": f"BFS_D10_1_{fixture['id']}_F{frame}_R{repeat}",
        "frame": frame,
        "camera": {"name": camera_spec["name"], "location": [convert(v) for v in camera_location(spec, fixture, frame)], "rotationEuler": [convert(v) for v in camera_spec["rotationEuler"]], "type": camera_spec["type"], "orthoScale": convert(camera_spec["orthoScale"])},
        "objects": sorted([
            {"name": item["name"], "type": "MESH", "location": [convert(v) for v in object_location(spec, fixture, item["name"], frame)], "scale": [convert(v) for v in item["scale"]], "passIndex": int(item["passIndex"])}
            for item in spec["scene"]["objects"]
        ], key=lambda item: item["name"]),
    }


def write_png(path: Path, pixels: np.ndarray) -> dict:
    array = np.ascontiguousarray(pixels, dtype=np.uint8)
    output = oiio.ImageOutput.create(str(path))
    if output is None:
        raise RuntimeError(f"cannot create diagnostic: {path}")
    image_spec = oiio.ImageSpec(array.shape[1], array.shape[0], 3, oiio.UINT8)
    image_spec.channelnames = ["R", "G", "B"]
    if not output.open(str(path), image_spec) or not output.write_image(array):
        raise RuntimeError(output.geterror())
    output.close()
    reopened = oiio.ImageBuf(str(path))
    decoded = np.ascontiguousarray(np.asarray(reopened.get_pixels(oiio.UINT8), dtype=np.uint8))
    return {"pngSha256": sha256_file(path), "pixelSha256": sha256_bytes(array.tobytes()), "decodedPixelSha256": sha256_bytes(decoded.tobytes()), "reopenExact": bool(np.array_equal(array, decoded)), "shape": list(array.shape)}


def diagnostic_pixels(kind: str, current: dict) -> np.ndarray:
    if kind == "current-combined":
        rgb = np.clip(current["parts"]["BFS_F32_MASTER.Combined"][..., :3], 0.0, 1.0)
    elif kind == "current-depth":
        depth = current["parts"]["BFS_F32_MASTER.Depth"][..., 0].astype(np.float64)
        value = np.clip((depth - 6.0) / 4.0, 0.0, 1.0)
        rgb = np.stack([value, value * value, 1.0 - value], axis=-1)
    elif kind == "current-ownership":
        owner = current["parts"]["BFS_F32_MASTER.Object Index"][..., 0].astype(np.int64)
        rgb = np.stack([((owner * 37) % 255) / 255.0, ((owner * 73) % 255) / 255.0, ((owner * 109) % 255) / 255.0], axis=-1)
    else:
        vector = current["parts"]["BFS_F32_MASTER.Vector"][..., :2].astype(np.float64)
        value = np.clip(np.linalg.norm(vector, axis=-1) / 20.0, 0.0, 1.0)
        rgb = np.stack([value, value * value, np.zeros_like(value)], axis=-1)
    return np.rint(np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)


def classify(checks: dict[str, bool], attacks: list[str]) -> str | None:
    for name in attacks:
        if checks.get(name) is not True:
            return name
    return None


def main() -> None:
    args = arguments()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D10.1 formal result")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
    fixtures = {item["id"]: item for item in spec["fixtures"]}
    objects = spec["scene"]["objects"]
    expected_roster = spec["sourceRender"]["expectedSubimages"]
    expected_channels = spec["sourceRender"]["expectedChannels"]
    width, height = spec["sourceRender"]["resolution"]
    gates = spec["measurementGates"]

    parent_identity = all(sha256_file(Path(value["uri"])) == value["sha256"] for value in spec["parents"].values())
    d10_result = json.loads(Path(spec["parents"]["d10Result"]["uri"]).read_text(encoding="utf-8"))
    d10_audit = json.loads(Path(spec["parents"]["d10Audit"]["uri"]).read_text(encoding="utf-8"))
    d10_negative_identity = bool(
        d10_result.get("verdict") == "BLENDER_MULTIPART_TEMPORAL_ADAPTER_HOLDOUT_NOT_SUPPORTED"
        and d10_result.get("baseFailure") == "SCENE_STRUCTURE"
        and d10_result.get("checks", {}).get("ANIMATION_STRUCTURE") is False
        and d10_audit.get("status") == "FAIL"
        and d10_audit.get("attackReplay", {}).get("count") == 0
    )
    source_cells, source_observations = {}, []
    source_report_binding = source_state = scene_state = action_state = pass_layout = runtime_state = True
    float32_canonicalization_state = one_ulp_sensitivity_state = nonfloat_exactness_state = True
    structural_rows = []
    all_source_pids = []
    for record in receipt["sourceRuns"]:
        fixture = fixtures[record["fixtureId"]]
        report_path, exr_path = Path(record["reportUri"]), Path(record["exrUri"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        loaded = load_multipart(exr_path)
        key = (record["fixtureId"], int(record["frame"]), int(record["repeat"]))
        source_cells[key] = {"report": report, "loaded": loaded, "exr": exr_path}
        all_source_pids.append(int(report["pid"]))
        source_report_binding &= bool(report_self_valid(report) and report["output"]["sha256"] == sha256_file(exr_path) and report["fixtureId"] == record["fixtureId"] and report["frame"] == record["frame"] and report["repeat"] == record["repeat"])
        source_state &= bool(
            report["runtime"] == {"engine": "CYCLES", "device": "CPU", "samples": 1, "seed": 521001, "animatedSeed": False, "adaptiveSampling": False, "denoising": False, "motionBlur": False, "persistentData": False, "threadsMode": "FIXED", "threads": 4}
            and report["passState"] == {"viewLayer": "BFS_F32_MASTER", "Combined": True, "Depth": True, "Vector": True, "Object Index": True, "passAlphaThreshold": 0.5}
        )
        expected_scene = expected_scene_structure(spec, fixture, record["frame"], record["repeat"])
        raw_scene = expected_scene_structure(spec, fixture, record["frame"], record["repeat"], canonicalize=False)
        expected_animation = {"camera": expected_action(fixture["cameraByFrame"]), "mover": expected_action(fixture["moverByFrame"])}
        raw_animation = {"camera": expected_action(fixture["cameraByFrame"], canonicalize=False), "mover": expected_action(fixture["moverByFrame"], canonicalize=False)}
        scene_match = report["sceneStructure"] == expected_scene
        action_match = report["animationStructure"] == expected_animation
        raw_scene_rejected = report["sceneStructure"] != raw_scene
        animated = fixture["cameraByFrame"] is not None or fixture["moverByFrame"] is not None
        raw_animation_rejected = report["animationStructure"] != raw_animation if animated else True
        ulp_scene = copy.deepcopy(expected_scene)
        ulp_scene["camera"]["orthoScale"] = next_float32_toward_positive_infinity(ulp_scene["camera"]["orthoScale"])
        one_ulp_rejected = report["sceneStructure"] != ulp_scene
        nonfloat_scene = copy.deepcopy(expected_scene)
        nonfloat_scene["objects"][0]["passIndex"] += 1
        nonfloat_rejected = report["sceneStructure"] != nonfloat_scene
        scene_state &= scene_match
        action_state &= action_match
        float32_canonicalization_state &= bool(scene_match and action_match and raw_scene_rejected and raw_animation_rejected)
        one_ulp_sensitivity_state &= bool(scene_match and one_ulp_rejected)
        nonfloat_exactness_state &= bool(scene_match and nonfloat_rejected)
        structural_rows.append({"fixtureId": record["fixtureId"], "frame": record["frame"], "repeat": record["repeat"], "sceneCanonicalExact": scene_match, "animationCanonicalExact": action_match, "rawDoubleSceneRejected": raw_scene_rejected, "rawDoubleAnimationRejectedWhenApplicable": raw_animation_rejected, "oneUlpOrthoScaleRejected": one_ulp_rejected, "passIndexIncrementRejected": nonfloat_rejected})
        expected_shapes = {"BFS_F32_MASTER.Combined": [height, width, 4], "BFS_F32_MASTER.Depth": [height, width, 1], "BFS_F32_MASTER.Vector": [height, width, 4], "BFS_F32_MASTER.Object Index": [height, width, 1]}
        pass_layout &= bool(loaded["roster"] == expected_roster and loaded["channels"] == expected_channels and all(list(loaded["parts"][name].shape) == shape and np.isfinite(loaded["parts"][name]).all() for name, shape in expected_shapes.items()))
        runtime_state &= bool(report["blender"]["executableSha256"] == spec["runtime"]["blender"]["sha256"] and report["blender"]["version"] == spec["runtime"]["blender"]["version"] and report["blender"]["buildHash"] == spec["runtime"]["blender"]["buildHash"])
        source_observations.append({"fixtureId": record["fixtureId"], "frame": record["frame"], "repeat": record["repeat"], "pid": report["pid"], "exrSha256": sha256_file(exr_path), "roster": loaded["roster"], "channels": loaded["channels"], "allFinite": bool(all(np.isfinite(value).all() for value in loaded["parts"].values()))})

    expected_keys = {(fixture_id, frame, repeat) for fixture_id in fixtures for frame in (0, 1) for repeat in (1, 2)}
    fixture_roster = set(source_cells) == expected_keys

    depth_rows, ownership_rows, vector_rows, static_rows = [], [], [], []
    vector_xy_ok = vector_zw_ok = wrong_separated = depth_ok = ownership_ok = orientation_ok = static_ok = True
    for fixture_id, fixture in fixtures.items():
        for repeat in (1, 2):
            for frame in (0, 1):
                loaded = source_cells[(fixture_id, frame, repeat)]["loaded"]
                owner = loaded["parts"]["BFS_F32_MASTER.Object Index"][..., 0].astype(np.float64)
                depth = loaded["parts"]["BFS_F32_MASTER.Depth"][..., 0].astype(np.float64)
                centroids = {}
                for item in objects:
                    mask = owner == float(item["passIndex"])
                    visible = int(np.count_nonzero(mask))
                    if visible == 0:
                        ownership_ok = False
                        continue
                    x, y = top_left_probe(spec, fixture, item, frame)
                    radius = spec["scene"]["ownershipProbeRadiusPixels"]
                    probe = owner[y - radius:y + radius + 1, x - radius:x + radius + 1]
                    probe_exact = bool(probe.shape == (3, 3) and np.all(probe == float(item["passIndex"])))
                    expected_depth = float(camera_location(spec, fixture, frame)[2] - object_location(spec, fixture, item["name"], frame)[2])
                    error = np.abs(depth[mask] - expected_depth)
                    stats = finite_stats(error, "absoluteError")
                    one_depth_ok = bool(stats["absoluteErrorMaximum"] <= gates["depthAbsoluteErrorMaximum"])
                    rows = np.nonzero(mask)[0]
                    centroids[item["name"]] = float(np.mean(rows))
                    ownership_ok &= probe_exact
                    depth_ok &= one_depth_ok
                    ownership_rows.append({"fixtureId": fixture_id, "frame": frame, "repeat": repeat, "object": item["name"], "passIndex": item["passIndex"], "visiblePixelCount": visible, "probeTopLeftPixel": [x, y], "probeAllExact": probe_exact, "centroidRow": centroids[item["name"]]})
                    depth_rows.append({"fixtureId": fixture_id, "frame": frame, "repeat": repeat, "object": item["name"], "expectedDepth": expected_depth, **stats, "passed": one_depth_ok})
                one_orientation = centroids.get("BFS_F32_TOP", math.inf) < centroids.get("BFS_F32_BOTTOM", -math.inf)
                orientation_ok &= one_orientation

            current = source_cells[(fixture_id, 1, repeat)]["loaded"]
            motion = current["parts"]["BFS_F32_MASTER.Vector"].astype(np.float64)
            owner = current["parts"]["BFS_F32_MASTER.Object Index"][..., 0].astype(np.float64)
            if fixture["expectedMovingOwner"] is None:
                xy_magnitude = np.linalg.norm(motion[..., :2], axis=-1)
                zw_magnitude = np.linalg.norm(motion[..., 2:4], axis=-1)
                xy_stats, zw_stats = finite_stats(xy_magnitude, "magnitude"), finite_stats(zw_magnitude, "magnitude")
                passed = bool(xy_stats["magnitudeP99"] <= gates["staticVectorPairMagnitudeP99MaximumPixels"] and xy_stats["magnitudeMaximum"] <= gates["staticVectorPairMagnitudeAbsoluteMaximumPixels"] and zw_stats["magnitudeP99"] <= gates["staticVectorPairMagnitudeP99MaximumPixels"] and zw_stats["magnitudeMaximum"] <= gates["staticVectorPairMagnitudeAbsoluteMaximumPixels"])
                static_ok &= passed
                static_rows.append({"fixtureId": fixture_id, "repeat": repeat, "XY": xy_stats, "ZW": zw_stats, "passed": passed})
            else:
                names = [item["name"] for item in objects] if fixture["expectedMovingOwner"] == "ALL_VISIBLE_OWNERS" else [fixture["expectedMovingOwner"]]
                for name in names:
                    item = next(value for value in objects if value["name"] == name)
                    mask = owner == float(item["passIndex"])
                    expected_xy, expected_zw = expected_vectors(spec, fixture, name)
                    observed_xy, observed_zw = motion[mask, :2], motion[mask, 2:4]
                    xy_error = np.linalg.norm(observed_xy - expected_xy, axis=-1)
                    zw_error = np.linalg.norm(observed_zw - expected_zw, axis=-1)
                    xy_stats, zw_stats = finite_stats(xy_error, "endpointError"), finite_stats(zw_error, "endpointError")
                    one_xy = bool(xy_stats["endpointErrorP99"] <= gates["movingVectorCorrectCandidateEndpointErrorP99MaximumPixels"] and xy_stats["endpointErrorMaximum"] <= gates["movingVectorCorrectCandidateEndpointErrorAbsoluteMaximumPixels"])
                    one_zw = bool(zw_stats["endpointErrorP99"] <= gates["movingVectorCorrectCandidateEndpointErrorP99MaximumPixels"] and zw_stats["endpointErrorMaximum"] <= gates["movingVectorCorrectCandidateEndpointErrorAbsoluteMaximumPixels"])
                    wrong_xy = {"NEGATED_CORRECT": -expected_xy, "PAIR_SWAP": expected_zw, "NEGATED_PAIR_SWAP": -expected_zw, "COMPONENT_SWAP": expected_xy[::-1]}
                    wrong_zw = {"NEGATED_CORRECT": -expected_zw, "PAIR_SWAP": expected_xy, "NEGATED_PAIR_SWAP": -expected_xy, "COMPONENT_SWAP": expected_zw[::-1]}
                    wrong_xy_medians = {key: float(np.quantile(np.linalg.norm(observed_xy - value, axis=-1), 0.5)) for key, value in wrong_xy.items()}
                    wrong_zw_medians = {key: float(np.quantile(np.linalg.norm(observed_zw - value, axis=-1), 0.5)) for key, value in wrong_zw.items()}
                    nearest_wrong = min([*wrong_xy_medians.values(), *wrong_zw_medians.values()])
                    one_separated = nearest_wrong >= gates["movingVectorNearestWrongCandidateMedianMinimumPixels"]
                    vector_xy_ok &= one_xy
                    vector_zw_ok &= one_zw
                    wrong_separated &= one_separated
                    vector_rows.append({"fixtureId": fixture_id, "repeat": repeat, "object": name, "visiblePixelCount": int(np.count_nonzero(mask)), "expectedXY": expected_xy.tolist(), "expectedZW": expected_zw.tolist(), "XY": xy_stats, "ZW": zw_stats, "wrongXYMedianErrors": wrong_xy_medians, "wrongZWMedianErrors": wrong_zw_medians, "nearestWrongMedianError": nearest_wrong, "xyPassed": one_xy, "zwPassed": one_zw, "wrongSeparated": one_separated})

    repeat_pass_exact = True
    repeat_rows = []
    for fixture_id in fixtures:
        for frame in (0, 1):
            left = source_cells[(fixture_id, frame, 1)]["loaded"]
            right = source_cells[(fixture_id, frame, 2)]["loaded"]
            pass_equal = {name: array_bytes(left["parts"][name]) == array_bytes(right["parts"][name]) for name in expected_roster}
            repeat_pass_exact &= all(pass_equal.values())
            repeat_rows.append({"fixtureId": fixture_id, "frame": frame, "passes": pass_equal, "allExact": all(pass_equal.values())})

    adapter_rows, adapter_cells = [], {}
    adapter_binding = adapter_exact = adapter_runtime = True
    all_adapter_pids = []
    for record in receipt["adapterRuns"]:
        fixture_id, repeat = record["fixtureId"], int(record["repeat"])
        report_path = Path(record["reportUri"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        previous = source_cells[(fixture_id, 0, repeat)]["loaded"]
        current = source_cells[(fixture_id, 1, repeat)]["loaded"]
        expected = {
            "previousRgba": previous["parts"]["BFS_F32_MASTER.Combined"],
            "currentRgba": current["parts"]["BFS_F32_MASTER.Combined"],
            "previousDepth": previous["parts"]["BFS_F32_MASTER.Depth"][..., 0],
            "currentDepth": current["parts"]["BFS_F32_MASTER.Depth"][..., 0],
            "previousLayer": previous["parts"]["BFS_F32_MASTER.Object Index"][..., 0],
            "currentLayer": current["parts"]["BFS_F32_MASTER.Object Index"][..., 0],
            "motion": np.negative(current["parts"]["BFS_F32_MASTER.Vector"][..., :2], dtype=np.float32),
        }
        all_adapter_pids.append(int(report["pid"]))
        previous_record = next(item for item in receipt["sourceRuns"] if item["fixtureId"] == fixture_id and item["frame"] == 0 and item["repeat"] == repeat)
        current_record = next(item for item in receipt["sourceRuns"] if item["fixtureId"] == fixture_id and item["frame"] == 1 and item["repeat"] == repeat)
        binding = bool(
            report_self_valid(report)
            and report["fixtureId"] == fixture_id
            and report["repeat"] == repeat
            and report["transform"]["formula"] == "[-X,-Y]"
            and report["inputs"]["previousExr"]["sha256"] == previous_record["exrSha256"]
            and report["inputs"]["previousExr"]["reportSha256"] == previous_record["reportSha256"]
            and report["inputs"]["currentExr"]["sha256"] == current_record["exrSha256"]
            and report["inputs"]["currentExr"]["reportSha256"] == current_record["reportSha256"]
        )
        adapter_runtime &= bool(report["runtime"]["pythonExecutableSha256"] == spec["runtime"]["python"]["sha256"] and report["runtime"]["openImageIO"] == spec["runtime"]["python"]["openImageIO"] and report["runtime"]["numpy"] == spec["runtime"]["python"]["numpy"])
        array_equal, array_records = {}, {}
        for name, filename in FILES.items():
            path = Path(record["arraysUri"]) / filename
            payload = path.read_bytes()
            wanted = array_bytes(expected[name])
            array_equal[name] = payload == wanted
            array_records[name] = {"uri": str(path), "sha256": sha256_bytes(payload), "bytes": len(payload), "expectedSha256": sha256_bytes(wanted), "exact": payload == wanted}
            binding &= report["arrays"][name]["sha256"] == sha256_bytes(payload) and report["arrays"][name]["bytes"] == len(payload)
        one_exact = all(array_equal.values())
        adapter_binding &= binding
        adapter_exact &= one_exact
        adapter_cells[(fixture_id, repeat)] = {name: array_bytes(value) for name, value in expected.items()}
        adapter_rows.append({"fixtureId": fixture_id, "repeat": repeat, "pid": report["pid"], "reportSelfValid": report_self_valid(report), "bindingPassed": binding, "arrays": array_records, "allExact": one_exact})

    adapter_repeat_exact = True
    adapter_repeat_rows = []
    for fixture_id in fixtures:
        equal = {name: adapter_cells[(fixture_id, 1)][name] == adapter_cells[(fixture_id, 2)][name] for name in FILES}
        adapter_repeat_exact &= all(equal.values())
        adapter_repeat_rows.append({"fixtureId": fixture_id, "arrays": equal, "allExact": all(equal.values())})

    diagnostics_root = args.formal_root / "diagnostics"
    if diagnostics_root.exists():
        raise RuntimeError("refusing to overwrite D10.1 diagnostics")
    diagnostics_root.mkdir(parents=True, exist_ok=False)
    diagnostics = []
    for fixture_id in fixtures:
        current = source_cells[(fixture_id, 1, 1)]["loaded"]
        source_sha = sha256_file(source_cells[(fixture_id, 1, 1)]["exr"])
        for kind in spec["diagnostics"]["perFixture"]:
            pixels = diagnostic_pixels(kind, current)
            stem = f"{fixture_id.lower()}--{kind}"
            png_path = diagnostics_root / f"{stem}.png"
            record = {"schemaVersion": "bfs.blenderMultipartTemporalAdapterF32Diagnostic.v0.1", "experimentId": spec["experimentId"], "fixtureId": fixture_id, "kind": kind, "sourceExrSha256": source_sha, **write_png(png_path, pixels)}
            sidecar_path = diagnostics_root / f"{stem}.json"
            sidecar_path.write_text(json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
            diagnostics.append({**record, "pngUri": str(png_path), "sidecarUri": str(sidecar_path), "sidecarSha256": sha256_file(sidecar_path)})

    process_pids = [*all_source_pids, *all_adapter_pids, os.getpid()]
    operation_counts = {"sourceBlenderProcesses": len(source_observations), "sourceRenderCalls": sum(item["report"]["operationCounts"]["blenderRenderCalls"] for item in source_cells.values()), "cyclesRayRenders": sum(item["report"]["operationCounts"]["cyclesRayRenders"] for item in source_cells.values()), "adapterPythonProcesses": len(adapter_rows), "analysisPythonProcesses": 1, "totalChildProcesses": len(process_pids), "uniqueChildPids": len(set(process_pids)), "sourceBlendFilesOpened": 0, "externalAssetsOpened": 0}
    process_roster_ok = operation_counts == {"sourceBlenderProcesses": 12, "sourceRenderCalls": 12, "cyclesRayRenders": 12, "adapterPythonProcesses": 6, "analysisPythonProcesses": 1, "totalChildProcesses": 19, "uniqueChildPids": 19, "sourceBlendFilesOpened": 0, "externalAssetsOpened": 0}
    runtime_ok = bool(runtime_state and adapter_runtime and all(row["pid"] > 0 for row in adapter_rows) and oiio.VERSION_STRING == spec["runtime"]["python"]["openImageIO"] and np.__version__ == spec["runtime"]["python"]["numpy"] and sha256_file(Path(sys.executable)) == spec["runtime"]["python"]["sha256"])
    tool_freeze_ok = bool(preflight.get("status") == "ACCEPTED" and preflight.get("spec", {}).get("sha256") == SPEC_SHA256 and preflight.get("allFrozenToolsMatchGit") is True)
    prereg_ok = sha256_file(args.spec) == SPEC_SHA256
    diagnostics_ok = bool(len(diagnostics) == spec["diagnostics"]["expectedPngs"] and all(item["reopenExact"] and Path(item["pngUri"]).is_file() and Path(item["sidecarUri"]).is_file() for item in diagnostics))

    checks = {
        "PARENT_IDENTITY": parent_identity,
        "D10_NEGATIVE_IDENTITY": d10_negative_identity,
        "D5_COUNTEREXAMPLE_IDENTITY": sha256_file(Path(spec["parents"]["d5Result"]["uri"])) == spec["parents"]["d5Result"]["sha256"],
        "FRESHNESS_IDENTITY": preflight.get("formalRootAbsent") is True and preflight.get("freshnessMatched") is True,
        "PREREGISTRATION_IDENTITY": prereg_ok,
        "TOOL_FREEZE_IDENTITY": tool_freeze_ok,
        "RUNTIME_IDENTITY": runtime_ok,
        "DISK_ADMISSION": receipt.get("diskAdmission", {}).get("status") == "ACCEPTED",
        "FIXTURE_ROSTER": fixture_roster,
        "RNA_FLOAT32_CANONICALIZATION": float32_canonicalization_state,
        "RNA_FLOAT32_ONE_ULP_SENSITIVITY": one_ulp_sensitivity_state,
        "NONFLOAT_STRUCTURE_EXACTNESS": nonfloat_exactness_state,
        "SCENE_STRUCTURE": scene_state,
        "ANIMATION_STRUCTURE": action_state,
        "RENDER_STATE": source_state,
        "SOURCE_PROCESS_ROSTER": len(source_observations) == 12,
        "PID_UNIQUENESS": len(set(process_pids)) == 19,
        "SOURCE_REPORT_BINDING": source_report_binding,
        "MULTIPART_ROSTER": pass_layout and all(item["roster"] == expected_roster for item in source_observations),
        "MULTIPART_CHANNEL_LAYOUT": pass_layout and all(item["channels"] == expected_channels for item in source_observations),
        "SOURCE_REPEAT_DECODED_IDENTITY": repeat_pass_exact,
        "ANALYTIC_ORACLE_INDEPENDENCE": preflight.get("analyticOracleImportAuditPassed") is True,
        "VECTOR_XY_MAPPING": vector_xy_ok,
        "VECTOR_ZW_MAPPING": vector_zw_ok,
        "VECTOR_COMPONENT_SWAP": wrong_separated,
        "VECTOR_SIGN_FLIP": wrong_separated,
        "D9_COORDINATE_CONVERSION": adapter_exact,
        "STATIC_VECTOR_BOUNDARY": static_ok,
        "DEPTH_SEMANTICS": depth_ok,
        "OWNERSHIP_SEMANTICS": ownership_ok,
        "RASTER_ORIENTATION": orientation_ok,
        "ADAPTER_REPORT_BINDING": adapter_binding,
        "ADAPTER_ARRAY_RECONSTRUCTION": adapter_exact,
        "ADAPTER_REPEAT_IDENTITY": adapter_repeat_exact,
        "DIAGNOSTIC_TOTALITY": diagnostics_ok,
        "OPERATION_BOUNDARY": process_roster_ok,
        "RESULT_SELF_HASH": True,
    }
    base_failure = classify(checks, spec["attacks"])
    attack_audit = []
    if base_failure is None:
        for attack in spec["attacks"]:
            attacked = copy.deepcopy(checks)
            attacked[attack] = False
            observed = classify(attacked, spec["attacks"])
            attack_audit.append({"id": attack, "expectedReason": attack, "observedReason": observed, "passed": observed == attack})
    attacks_pass = len(attack_audit) == len(spec["attacks"]) and all(item["passed"] for item in attack_audit)
    if base_failure is None and not attacks_pass:
        base_failure = "ATTACK_AUDIT"
    verdict = spec["decisionRule"]["passVerdict"] if base_failure is None else spec["decisionRule"]["failVerdict"]

    body = {
        "schemaVersion": "bfs.blenderMultipartTemporalAdapterF32HoldoutResult.v0.1",
        "experimentId": spec["experimentId"],
        "specSha256": SPEC_SHA256,
        "preflightSha256": sha256_file(args.preflight),
        "receiptSha256": sha256_file(args.receipt),
        "verdict": verdict,
        "baseFailure": base_failure,
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha256_file(Path(sys.executable)), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__, "analysisPid": os.getpid()},
        "checks": checks,
        "measurements": {"structuralCanonicalization": structural_rows, "vector": vector_rows, "staticVector": static_rows, "depth": depth_rows, "ownership": ownership_rows, "sourceRepeats": repeat_rows, "adapterRepeats": adapter_repeat_rows},
        "sourceObservations": source_observations,
        "adapterObservations": adapter_rows,
        "diagnostics": diagnostics,
        "operationCounts": operation_counts,
        "attackAudit": attack_audit,
        "nonClaims": spec["nonClaims"],
    }
    result = {**body, "resultHash": canonical_hash(body)}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D10_1_ANALYSIS verdict={verdict} failure={base_failure} attacks={sum(item['passed'] for item in attack_audit)}/{len(spec['attacks'])} result={sha256_file(args.output)}")
    if base_failure is not None:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
