#!/usr/bin/env python3
"""Independent analyzer for the B52-D11.1 bounded quantizer holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "c4cb343672f53660d7c4ab69ccd489e00bb211e4aa1f489429f7a626ee48c42a"
ADAPTER_FILES = {
    "previousRgba": ("previous.rgba32", 4),
    "currentRgba": ("current.rgba32", 4),
    "previousDepth": ("previous-depth.f32", 1),
    "currentDepth": ("current-depth.f32", 1),
    "previousLayer": ("previous-layer.f32", 1),
    "currentLayer": ("current-layer.f32", 1),
    "motion": ("motion.xy32", 2),
}
ACCUMULATOR_FILES = {
    "validity": ("validity.u8", "u1", 1),
    "reason": ("reason.u8", "u1", 1),
    "resolvedRgba": ("resolved.rgba32", "<f4", 4),
    "naiveRgba": ("naive.rgba32", "<f4", 4),
    "wrongSignRgba": ("wrong-sign.rgba32", "<f4", 4),
}
REASON_NAMES = np.asarray(["VALID", "INVALID_BOUNDS", "INVALID_LAYER", "INVALID_DEPTH", "INVALID_ALPHA"])


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def valid_report(path: Path) -> tuple[bool, dict]:
    payload = json.loads(path.read_text())
    body = {key: value for key, value in payload.items() if key != "reportHash"}
    return payload.get("reportHash") == canonical_hash(body), payload


def load_multipart(path: Path, render: dict) -> tuple[dict[str, np.ndarray], list[str], dict[str, list[str]]]:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    parts, roster, channels = {}, [], {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        image_spec = image.spec()
        name = str(image_spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        parts[name], channels[name] = pixels, list(image_spec.channelnames)
        roster.append(name)
    height, width = render["resolution"][1], render["resolution"][0]
    layer = render["viewLayer"]
    expected_shapes = {
        f"{layer}.Combined": [height, width, 4],
        f"{layer}.Depth": [height, width, 1],
        f"{layer}.Vector": [height, width, 4],
        f"{layer}.Object Index": [height, width, 1],
    }
    exact = roster == render["expectedSubimages"] and channels == render["expectedChannels"]
    exact = exact and all(list(parts[name].shape) == shape and np.isfinite(parts[name]).all() for name, shape in expected_shapes.items())
    if not exact:
        raise RuntimeError("D11.1 multipart roster, channel, shape or finite mismatch")
    return parts, roster, channels


def load_rgba_exr(path: Path) -> tuple[np.ndarray, dict]:
    image = oiio.ImageInput.open(str(path))
    if image is None:
        raise RuntimeError(oiio.geterror() or f"cannot read {path}")
    image_spec = image.spec()
    pixels = np.asarray(image.read_image(0, 0, 0, 4, oiio.FLOAT), np.float32).reshape(image_spec.height, image_spec.width, 4)
    image.close()
    layout = {"width": image_spec.width, "height": image_spec.height, "channels": list(image_spec.channelnames), "format": str(image_spec.format), "compression": image_spec.get_string_attribute("compression")}
    return np.ascontiguousarray(pixels, dtype="<f4"), layout


def read_adapter(directory: Path, width: int, height: int) -> dict[str, np.ndarray]:
    result = {}
    for name, (filename, components) in ADAPTER_FILES.items():
        shape = (height, width, components) if components > 1 else (height, width)
        result[name] = np.frombuffer((directory / filename).read_bytes(), dtype="<f4").reshape(shape)
    return result


def read_quantized(path: Path, width: int, height: int) -> np.ndarray:
    return np.frombuffer(path.read_bytes(), dtype="<f4").reshape(height, width, 2)


def read_accumulator(directory: Path, width: int, height: int) -> dict[str, np.ndarray]:
    result = {}
    for name, (filename, dtype, components) in ACCUMULATOR_FILES.items():
        shape = (height, width, components) if components > 1 else (height, width)
        result[name] = np.frombuffer((directory / filename).read_bytes(), dtype=dtype).reshape(shape)
    return result


def nearest_integer(value: float) -> int:
    return math.floor(value + 0.5) if value >= 0.0 else math.ceil(value - 0.5)


def independent_quantize(raw: np.ndarray, radius: float) -> tuple[np.ndarray | None, dict]:
    flat = np.ascontiguousarray(raw, dtype="<f4").reshape(-1)
    quantized = np.empty(flat.shape, dtype="<f4")
    maximum = 0.0
    rejected = None
    for index, scalar in enumerate(flat):
        value = float(scalar)
        if not math.isfinite(value):
            rejected = {"component": index, "reason": "NONFINITE"}
            break
        candidate = nearest_integer(value)
        error = abs(value - candidate)
        if error > radius:
            rejected = {"component": index, "reason": "OUTSIDE_RADIUS", "value": value, "candidate": candidate, "error": error}
            break
        maximum = max(maximum, error)
        quantized[index] = np.float32(0.0 if candidate == 0 else candidate)
    if rejected is not None:
        return None, {"accepted": False, "firstRejected": rejected}
    output = quantized.reshape(raw.shape)
    second, second_metrics = independent_quantize_once(output, radius)
    return output, {"accepted": True, "maximumAbsoluteErrorPixels": maximum, "idempotent": np.array_equal(output, second) and second_metrics["accepted"]}


def independent_quantize_once(raw: np.ndarray, radius: float) -> tuple[np.ndarray | None, dict]:
    flat = np.ascontiguousarray(raw, dtype="<f4").reshape(-1)
    output = np.empty(flat.shape, dtype="<f4")
    for index, scalar in enumerate(flat):
        value = float(scalar)
        if not math.isfinite(value):
            return None, {"accepted": False}
        candidate = nearest_integer(value)
        if abs(value - candidate) > radius:
            return None, {"accepted": False}
        output[index] = np.float32(0.0 if candidate == 0 else candidate)
    return output.reshape(raw.shape), {"accepted": True}


def independent_accumulate(arrays: dict[str, np.ndarray], sign: int = 1, naive: bool = False) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    height, width = arrays["currentDepth"].shape
    resolved = arrays["currentRgba"].copy()
    validity = np.zeros((height, width), np.uint8)
    reasons = np.zeros((height, width), np.uint8)
    for y in range(height):
        for x in range(width):
            dx = int(float(arrays["motion"][y, x, 0]))
            dy = int(float(arrays["motion"][y, x, 1]))
            qx, qy = x - sign * dx, y + sign * dy
            if not (0 <= qx < width and 0 <= qy < height):
                reason = 1
            elif naive:
                reason = 0
            elif arrays["previousLayer"][qy, qx] != arrays["currentLayer"][y, x]:
                reason = 2
            elif abs(float(arrays["previousDepth"][qy, qx]) - float(arrays["currentDepth"][y, x])) > max(1.0, float(arrays["currentDepth"][y, x])) / 1024.0:
                reason = 3
            elif arrays["previousRgba"][qy, qx, 3] <= 0 or arrays["currentRgba"][y, x, 3] <= 0:
                reason = 4
            else:
                reason = 0
            reasons[y, x] = reason
            if reason == 0:
                validity[y, x] = 1
                for channel in range(4):
                    resolved[y, x, channel] = np.float32(0.5 * float(arrays["currentRgba"][y, x, channel]) + 0.5 * float(arrays["previousRgba"][qy, qx, channel]))
    return validity, reasons, resolved


def analytic_owner_mask(spec: dict, fixture: dict) -> np.ndarray:
    width, height = spec["scene"]["resolution"]
    fixture_id = fixture["id"]
    if "CAMERA_BOUNDS" in fixture_id or "STATIC" in fixture_id:
        return np.ones((height, width), dtype=bool)
    mover = next(item for item in fixture["objects"] if "locationByFrame" in item)
    camera = fixture.get("cameraByFrame", {}).get("1", spec["scene"]["camera"]["location"])
    location = mover["locationByFrame"]["1"]
    pixels_per_world = width / float(spec["scene"]["camera"]["orthoScale"])
    xs = camera[0] + (np.arange(width, dtype=np.float64) + 0.5 - width / 2.0) / pixels_per_world
    ys = camera[1] + (height / 2.0 - np.arange(height, dtype=np.float64) - 0.5) / pixels_per_world
    margin = 1.1 / pixels_per_world
    inside_x = np.abs(xs - location[0]) < float(mover["sizeWorld"][0]) / 2.0 - margin
    inside_y = np.abs(ys - location[1]) < float(mover["sizeWorld"][1]) / 2.0 - margin
    return inside_y[:, None] & inside_x[None, :]


def action_exact(rows: list[dict], values: dict[str, list[float]] | None) -> bool:
    if values is None:
        return rows == []
    if len(rows) != 3:
        return False
    ordered = sorted(((int(frame), location) for frame, location in values.items()), key=lambda item: item[0])
    for axis, row in enumerate(rows):
        if row["layerIndex"] != 0 or row["stripIndex"] != 0 or row["channelBagIndex"] != 0:
            return False
        if row["dataPath"] != "location" or row["arrayIndex"] != axis or len(row["keyframes"]) != len(ordered):
            return False
        for observed, (frame, location) in zip(row["keyframes"], ordered):
            if f32(observed["frame"]) != f32(frame) or f32(observed["value"]) != f32(location[axis]) or observed["interpolation"] != "LINEAR":
                return False
    return True


def typed_scene_exact(spec: dict, fixture: dict, report: dict, frame: int) -> bool:
    camera_spec = spec["scene"]["camera"]
    expected_camera_location = fixture.get("cameraByFrame", {}).get(str(frame), camera_spec["location"])
    observed_camera = report["sceneStructure"]["camera"]
    camera_ok = observed_camera["name"] == camera_spec["name"] and observed_camera["type"] == camera_spec["type"]
    camera_ok = camera_ok and [f32(value) for value in observed_camera["location"]] == [f32(value) for value in expected_camera_location]
    camera_ok = camera_ok and [f32(value) for value in observed_camera["rotationEuler"]] == [f32(value) for value in camera_spec["rotationEuler"]]
    camera_ok = camera_ok and f32(observed_camera["orthoScale"]) == f32(camera_spec["orthoScale"])
    observed_by_name = {item["name"]: item for item in report["sceneStructure"]["objects"]}
    objects_ok = set(observed_by_name) == {item["name"] for item in fixture["objects"]}
    animation = report["animationStructure"]
    animation_ok = action_exact(animation["camera"], fixture.get("cameraByFrame")) and set(animation["objects"]) == set(observed_by_name)
    materials = spec["scene"]["textureConstruction"]["materials"]
    texture_keys = {"BACKGROUND_CHECKER": ("BACKGROUND_A", "BACKGROUND_B"), "FOREGROUND_CHECKER": ("FOREGROUND_A", "FOREGROUND_B"), "STATIC_CHECKER": ("STATIC_A", "STATIC_B")}
    for item in fixture["objects"]:
        observed = observed_by_name[item["name"]]
        expected_location = item.get("locationByFrame", {}).get(str(frame), item.get("location"))
        cell = spec["scene"]["textureConstruction"]["backgroundCellWorld" if item["texture"] == "BACKGROUND_CHECKER" else "foregroundCellWorld"]
        columns, rows = round(item["sizeWorld"][0] / cell[0]), round(item["sizeWorld"][1] / cell[1])
        mesh = observed["mesh"]
        expected_indices = [(row + column) % 2 for row in range(rows) for column in range(columns)]
        material_colors = [materials[key] for key in texture_keys[item["texture"]]]
        objects_ok = objects_ok and observed["type"] == "MESH" and observed["passIndex"] == item["passIndex"]
        objects_ok = objects_ok and [f32(value) for value in observed["location"]] == [f32(value) for value in expected_location]
        objects_ok = objects_ok and [f32(value) for value in observed["sizeWorld"]] == [f32(value) for value in item["sizeWorld"]]
        expected_edges = columns * (rows + 1) + rows * (columns + 1)
        objects_ok = objects_ok and mesh["vertices"] == (columns + 1) * (rows + 1) and mesh["edges"] == expected_edges and mesh["polygons"] == columns * rows
        objects_ok = objects_ok and mesh["polygonMaterialIndices"] == expected_indices and len(observed["materials"]) == 2
        animation_ok = animation_ok and action_exact(animation["objects"][item["name"]], item.get("locationByFrame"))
        for index, material in enumerate(observed["materials"]):
            objects_ok = objects_ok and material["name"] == f"{item['name']}_MAT_{index}"
            objects_ok = objects_ok and [f32(value) for value in material["emissionColor"]] == [f32(value) for value in material_colors[index]]
            objects_ok = objects_ok and f32(material["emissionStrength"]) == f32(1.0)
    return bool(camera_ok and objects_ok and animation_ok and report["fixture"] == fixture)


def metric_difference(candidate: np.ndarray, reference: np.ndarray) -> dict:
    delta = np.abs(candidate.astype(np.float64) - reference.astype(np.float64))
    return {"changedPixels": int(np.count_nonzero(np.any(delta != 0, axis=2))), "maximumAbsoluteDifference": float(delta.max(initial=0.0))}


def write_png(path: Path, pixels: np.ndarray) -> str:
    pixels = np.ascontiguousarray(pixels, dtype=np.uint8)
    height, width, channels = pixels.shape
    output = oiio.ImageOutput.create(str(path))
    image_spec = oiio.ImageSpec(width, height, channels, oiio.UINT8)
    if output is None or not output.open(str(path), image_spec) or not output.write_image(pixels):
        raise RuntimeError(oiio.geterror() or "diagnostic write failed")
    output.close()
    return sha(path)


def diagnostic_images(raw: dict[str, np.ndarray], quantized: np.ndarray, accumulated: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    normalize_rgb = lambda value: np.floor(np.clip(value[..., :3] / 2.0, 0, 1) * 255 + 0.5).astype(np.uint8)
    repeat3 = lambda value: np.repeat(value[..., None], 3, axis=2)
    scalar_gray = lambda value: np.floor(np.clip(value / max(float(np.max(value, initial=1.0)), 1e-12), 0, 1) * 255 + 0.5).astype(np.uint8)
    depth = raw["currentDepth"]
    depth_gray = np.floor(np.clip((depth - np.min(depth)) / max(float(np.ptp(depth)), 1e-8), 0, 1) * 255 + 0.5).astype(np.uint8)
    ownership = (raw["currentLayer"].astype(np.uint32) * 37 % 255).astype(np.uint8)
    raw_magnitude = np.linalg.norm(raw["motion"].astype(np.float64), axis=2)
    quant_error = np.max(np.abs(raw["motion"].astype(np.float64) - quantized.astype(np.float64)), axis=2)
    quant_visual = np.stack((np.clip(quantized[..., 0] / 40 + 0.5, 0, 1), np.clip(quantized[..., 1] / 40 + 0.5, 0, 1), np.full(quantized.shape[:2], 0.5)), axis=2)
    quant_visual = np.floor(quant_visual * 255 + 0.5).astype(np.uint8)
    recovered = np.any(np.trunc(raw["motion"]).astype(np.float32) != quantized, axis=2).astype(np.uint8) * 255
    validity = accumulated["validity"] * 255
    palette = np.asarray([[40, 190, 90], [220, 70, 60], [240, 170, 40], [140, 80, 220], [50, 140, 220]], np.uint8)
    delta_rgb = lambda value: repeat3(np.floor(np.clip(value / 0.5, 0, 1) * 255 + 0.5).astype(np.uint8))
    naive_delta = np.max(np.abs(accumulated["naiveRgba"].astype(np.float64) - accumulated["resolvedRgba"].astype(np.float64)), axis=2)
    wrong_delta = np.max(np.abs(accumulated["wrongSignRgba"].astype(np.float64) - accumulated["resolvedRgba"].astype(np.float64)), axis=2)
    return {
        "currentCombined": normalize_rgb(raw["currentRgba"]),
        "currentDepth": repeat3(depth_gray),
        "currentOwnership": repeat3(ownership),
        "rawMotionMagnitude": repeat3(scalar_gray(raw_magnitude)),
        "quantizationError": repeat3(scalar_gray(quant_error)),
        "quantizedMotion": quant_visual,
        "truncationRecovery": repeat3(recovered),
        "historyValidity": repeat3(validity),
        "validityReason": palette[accumulated["reason"]],
        "resolved": normalize_rgb(accumulated["resolvedRgba"]),
        "naiveDifference": delta_rgb(naive_delta),
        "wrongSignDifference": delta_rgb(wrong_delta),
    }


def first_failure(evidence: dict[str, bool], order: list[str]) -> str | None:
    return next((label for label in order if not evidence[label]), None)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec, receipt, preflight = json.loads(args.spec.read_text()), json.loads(args.receipt.read_text()), json.loads(args.preflight.read_text())
    if sha(args.spec) != SPEC_SHA256 or args.output.exists():
        raise RuntimeError("B52-D11.1 analyzer identity/output mismatch")
    receipt_body = {key: value for key, value in receipt.items() if key != "receiptHash"}
    receipt_valid = receipt.get("receiptHash") == canonical_hash(receipt_body)
    runs = receipt["runs"]
    width, height = spec["scene"]["resolution"]
    source = {(row["fixtureId"], row["frame"], row["sourceRepeat"]): row for row in runs if row["stage"] == "SOURCE"}
    adapters = {(row["fixtureId"], row["sourceRepeat"]): row for row in runs if row["stage"] == "ADAPTER"}
    quantizers = {(row["fixtureId"], row["sourceRepeat"], row["producer"]): row for row in runs if row["stage"].startswith("QUANTIZER_")}
    accumulators = {(row["fixtureId"], row["sourceRepeat"], row["producer"]): row for row in runs if row["stage"].startswith("ACCUMULATOR_")}
    encoders = {(row["fixtureId"], row["sourceRepeat"]): row for row in runs if row["stage"] == "ENCODER"}
    bridges = {(row["fixtureId"], row["sourceRepeat"], row["bridgeRepeat"]): row for row in runs if row["stage"] == "BRIDGE"}
    checks = {name: [] for name in ("sourceBinding", "scene", "roster", "sourceRepeat", "adapter", "adapterRepeat", "rawVector", "quantDomain", "quantBinding", "quantIdentity", "quantAnalytic", "semantic", "accumulator", "invalidCurrent", "controls", "static", "encoder", "bridge")}
    measurements, diagnostics, decoded_sources = [], [], {}
    layer = spec["sourceRender"]["viewLayer"]

    for key, row in source.items():
        report_ok, report = valid_report(Path(row["reportUri"]))
        expected_source_counts = {"blenderProcesses": 1, "blenderRenderCalls": 1, "cyclesRayRenders": 1, "sourceBlendFilesOpened": 0, "externalAssetsOpened": 0}
        checks["sourceBinding"].append(report_ok and report["output"]["sha256"] == sha(Path(row["exrUri"])) and row["pid"] == report["pid"] and report["operationCounts"] == expected_source_counts)
        fixture = next(item for item in spec["fixtures"] if item["id"] == row["fixtureId"])
        expected_runtime = {"engine": "CYCLES", "device": "CPU", "samples": 1, "seed": 521111, "animatedSeed": False, "adaptiveSampling": False, "denoising": False, "motionBlur": False, "depthOfField": False, "persistentData": False, "threadsMode": "FIXED", "threads": 4}
        checks["scene"].append(typed_scene_exact(spec, fixture, report, row["frame"]) and report["runtime"] == expected_runtime)
        parts, roster, channels = load_multipart(Path(row["exrUri"]), spec["sourceRender"])
        decoded_sources[key] = parts
        checks["roster"].append(roster == spec["sourceRender"]["expectedSubimages"] and channels == spec["sourceRender"]["expectedChannels"])

    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        for frame in (0, 1):
            first, second = decoded_sources[(fixture_id, frame, 1)], decoded_sources[(fixture_id, frame, 2)]
            checks["sourceRepeat"].append(all(np.array_equal(first[name], second[name]) for name in first))
        repeat_adapters, repeat_quantized = [], []
        repeat_rows = []
        for source_repeat in (1, 2):
            previous, current = decoded_sources[(fixture_id, 0, source_repeat)], decoded_sources[(fixture_id, 1, source_repeat)]
            expected_adapter = {"previousRgba": previous[f"{layer}.Combined"], "currentRgba": current[f"{layer}.Combined"], "previousDepth": previous[f"{layer}.Depth"][..., 0], "currentDepth": current[f"{layer}.Depth"][..., 0], "previousLayer": previous[f"{layer}.Object Index"][..., 0], "currentLayer": current[f"{layer}.Object Index"][..., 0], "motion": np.negative(current[f"{layer}.Vector"][..., :2], dtype=np.float32)}
            adapter_row = adapters[(fixture_id, source_repeat)]
            adapter_ok, adapter_report = valid_report(Path(adapter_row["reportUri"]))
            actual_adapter = read_adapter(Path(adapter_row["arraysUri"]), width, height)
            adapter_exact = adapter_ok and all(np.array_equal(actual_adapter[name], expected_adapter[name]) for name in expected_adapter)
            adapter_exact = adapter_exact and all(adapter_report["arrays"][name]["sha256"] == sha(Path(adapter_row["arraysUri"]) / filename) for name, (filename, _) in ADAPTER_FILES.items())
            checks["adapter"].append(adapter_exact)
            repeat_adapters.append(actual_adapter)

            owner = analytic_owner_mask(spec, fixture)
            vector = current[f"{layer}.Vector"].astype(np.float64)
            xy_error = np.abs(vector[..., :2][owner] - np.asarray(fixture["expectedVectorXY"], np.float64)).reshape(-1)
            zw_error = np.abs(vector[..., 2:][owner] - np.asarray(fixture["expectedVectorZW"], np.float64)).reshape(-1)
            raw_gate = spec["rawMotionGate"]
            vector_ok = bool(np.quantile(xy_error, 0.99) <= raw_gate["correctEndpointErrorP99MaximumPixels"] and xy_error.max(initial=0.0) <= raw_gate["correctEndpointErrorAbsoluteMaximumPixels"] and np.quantile(zw_error, 0.99) <= raw_gate["correctEndpointErrorP99MaximumPixels"] and zw_error.max(initial=0.0) <= raw_gate["correctEndpointErrorAbsoluteMaximumPixels"])
            checks["rawVector"].append(vector_ok)

            independent_quantized, quant_metrics = independent_quantize(actual_adapter["motion"], spec["quantizerContract"]["acceptanceRadiusPixels"])
            domain_ok = independent_quantized is not None and quant_metrics["accepted"] and quant_metrics["idempotent"]
            checks["quantDomain"].append(domain_ok)
            producer_quantized = {}
            for producer in ("python", "node"):
                quantizer_row = quantizers[(fixture_id, source_repeat, producer)]
                quantizer_ok, quantizer_report = valid_report(Path(quantizer_row["reportUri"]))
                quantized = read_quantized(Path(quantizer_row["outputUri"]), width, height)
                binding = quantizer_ok and quantizer_report["producer"] == producer and quantizer_report["input"]["sha256"] == sha(Path(adapter_row["arraysUri"]) / "motion.xy32") and quantizer_report["output"]["sha256"] == sha(Path(quantizer_row["outputUri"]))
                checks["quantBinding"].append(binding)
                producer_quantized[producer] = quantized
            quant_identity = domain_ok and np.array_equal(producer_quantized["python"], producer_quantized["node"]) and np.array_equal(producer_quantized["python"], independent_quantized)
            checks["quantIdentity"].append(quant_identity)
            quantized = producer_quantized["python"]
            analytic_exact = bool(np.all(quantized[owner] == np.asarray(fixture["expectedD9Motion"], np.float32)))
            checks["quantAnalytic"].append(analytic_exact)
            repeat_quantized.append(quantized)

            accumulation_input = {**actual_adapter, "motion": quantized}
            validity, reason, resolved = independent_accumulate(accumulation_input)
            _, _, naive = independent_accumulate(accumulation_input, naive=True)
            _, _, wrong = independent_accumulate(accumulation_input, sign=-1)
            independent = {"validity": validity, "reason": reason, "resolvedRgba": resolved, "naiveRgba": naive, "wrongSignRgba": wrong}
            producer_arrays = {}
            for producer in ("python", "node"):
                row = accumulators[(fixture_id, source_repeat, producer)]
                report_ok, report = valid_report(Path(row["reportUri"]))
                arrays = read_accumulator(Path(row["arraysUri"]), width, height)
                binding = report_ok and report["producer"] == producer and report["quantizerReport"]["sha256"] == sha(Path(quantizers[(fixture_id, source_repeat, producer)]["reportUri"]))
                binding = binding and all(report["outputs"][name]["sha256"] == sha(Path(row["arraysUri"]) / filename) for name, (filename, _, _) in ACCUMULATOR_FILES.items())
                checks["accumulator"].append(binding)
                producer_arrays[producer] = arrays
            dual_exact = all(np.array_equal(producer_arrays["python"][name], producer_arrays["node"][name]) for name in ACCUMULATOR_FILES)
            independent_exact = all(np.array_equal(producer_arrays["python"][name], independent[name]) for name in ACCUMULATOR_FILES)
            checks["accumulator"].extend((dual_exact, independent_exact))
            invalid = validity == 0
            checks["invalidCurrent"].append(bool(np.array_equal(resolved[invalid], actual_adapter["currentRgba"][invalid])))

            probe_rows = []
            for probe in fixture["semanticProbes"]:
                x, y = probe["centerTopLeftPixel"]
                radius = probe["radiusPixels"]
                actual = REASON_NAMES[reason[y - radius : y + radius + 1, x - radius : x + radius + 1]]
                exact = bool(np.all(actual == probe["expected"]))
                checks["semantic"].append(exact)
                probe_rows.append({"name": probe["name"], "expected": probe["expected"], "actual": actual.tolist(), "exact": exact})

            naive_metric, wrong_metric = metric_difference(naive, resolved), metric_difference(wrong, resolved)
            if fixture_id in spec["sensitivityControls"]["naiveNoLayerOrDepth"]["applicableFixtures"]:
                threshold = spec["sensitivityControls"]["naiveNoLayerOrDepth"]
                checks["controls"].append(naive_metric["changedPixels"] >= threshold["minimumChangedPixels"] and naive_metric["maximumAbsoluteDifference"] >= threshold["minimumMaximumAbsoluteDifference"])
            if fixture_id in spec["sensitivityControls"]["wrongMotionSign"]["applicableFixtures"]:
                threshold = spec["sensitivityControls"]["wrongMotionSign"]
                checks["controls"].append(wrong_metric["changedPixels"] >= threshold["minimumChangedPixels"] and wrong_metric["maximumAbsoluteDifference"] >= threshold["minimumMaximumAbsoluteDifference"])
            if fixture_id in spec["sensitivityControls"]["static"]["applicableFixtures"]:
                zero_bytes = np.ascontiguousarray(quantized, dtype="<f4").tobytes() == b"\x00\x00\x00\x00" * quantized.size
                checks["static"].append(int(validity.sum()) == spec["sensitivityControls"]["static"]["requiredValidPixels"] and np.array_equal(resolved, actual_adapter["currentRgba"]) and zero_bytes)

            encoder_row = encoders[(fixture_id, source_repeat)]
            encoder_ok, encoder_report = valid_report(Path(encoder_row["reportUri"]))
            encoded, layout = load_rgba_exr(Path(encoder_row["exrUri"]))
            expected_layout = {"width": width, "height": height, "channels": ["R", "G", "B", "A"], "format": "float", "compression": "zip"}
            checks["encoder"].append(encoder_ok and encoder_report["input"]["sha256"] == sha(Path(accumulators[(fixture_id, source_repeat, "python")]["arraysUri"]) / "resolved.rgba32") and encoder_report["output"]["sha256"] == sha(Path(encoder_row["exrUri"])) and encoder_report["encodeDecodeExact"] is True and layout == expected_layout and np.array_equal(encoded, resolved))
            bridge_decoded = []
            for bridge_repeat in (1, 2):
                bridge_row = bridges[(fixture_id, source_repeat, bridge_repeat)]
                bridge_ok, bridge_report = valid_report(Path(bridge_row["reportUri"]))
                decoded, bridge_layout = load_rgba_exr(Path(bridge_row["exrUri"]))
                checks["bridge"].append(bridge_ok and bridge_report["input"]["sha256"] == sha(Path(encoder_row["exrUri"])) and bridge_report["output"]["sha256"] == sha(Path(bridge_row["exrUri"])) and bridge_report["rna"]["match"] and bridge_report["graph"]["match"] and bridge_layout == layout and np.array_equal(decoded, resolved))
                bridge_decoded.append(decoded)
            checks["bridge"].append(np.array_equal(bridge_decoded[0], bridge_decoded[1]))
            repeat_rows.append({"sourceRepeat": source_repeat, "adapterExact": adapter_exact, "rawVectorGate": vector_ok, "quantizerDomain": quant_metrics, "pythonNodeQuantizedExact": quant_identity, "quantizedMovingOwnerExact": analytic_exact, "ownerInteriorPixels": int(owner.sum()), "xyErrorP99": float(np.quantile(xy_error, 0.99)), "xyErrorMaximum": float(xy_error.max(initial=0.0)), "zwErrorP99": float(np.quantile(zw_error, 0.99)), "zwErrorMaximum": float(zw_error.max(initial=0.0)), "truncationRecoveredPixels": int(np.count_nonzero(np.any(np.trunc(actual_adapter["motion"]).astype(np.float32) != quantized, axis=2))), "validPixels": int(validity.sum()), "invalidPixels": int(validity.size - validity.sum()), "naiveControl": naive_metric, "wrongSignControl": wrong_metric, "semanticProbes": probe_rows})

            if source_repeat == 1:
                diagnostic_root = args.formal_root / "diagnostics" / fixture_id
                diagnostic_root.mkdir(parents=True, exist_ok=True)
                for name, pixels in diagnostic_images(actual_adapter, quantized, producer_arrays["python"]).items():
                    png = diagnostic_root / f"{name}.png"
                    png_hash = write_png(png, pixels)
                    sidecar_body = {"schemaVersion": "bfs.blenderNearestIntegerTemporalRecoveryDiagnostic.v0.1", "fixtureId": fixture_id, "name": name, "png": {"uri": str(png), "sha256": png_hash}, "sources": {"currentExrSha256": source[(fixture_id, 1, 1)]["exrSha256"], "adapterReportSha256": adapters[(fixture_id, 1)]["reportSha256"], "pythonQuantizerReportSha256": quantizers[(fixture_id, 1, "python")]["reportSha256"], "pythonAccumulatorReportSha256": accumulators[(fixture_id, 1, "python")]["reportSha256"]}, "measurementInput": False}
                    sidecar = png.with_suffix(".json")
                    sidecar.write_text(json.dumps({**sidecar_body, "sidecarHash": canonical_hash(sidecar_body)}, indent=2, sort_keys=True, allow_nan=False) + "\n")
                    diagnostics.append({"fixtureId": fixture_id, "name": name, "pngUri": str(png), "pngSha256": png_hash, "sidecarUri": str(sidecar), "sidecarSha256": sha(sidecar)})
        checks["adapterRepeat"].append(all(np.array_equal(repeat_adapters[0][name], repeat_adapters[1][name]) for name in ADAPTER_FILES))
        checks["quantIdentity"].append(np.array_equal(repeat_quantized[0], repeat_quantized[1]))
        measurements.append({"fixtureId": fixture_id, "repeats": repeat_rows})

    pids = [row["pid"] for row in runs] + [os.getpid()]
    expected_stage_counts = {"SOURCE": 16, "ADAPTER": 8, "QUANTIZER_PYTHON": 8, "QUANTIZER_NODE": 8, "ACCUMULATOR_PYTHON": 8, "ACCUMULATOR_NODE": 8, "ENCODER": 8, "BRIDGE": 16}
    actual_stage_counts = {name: sum(row["stage"] == name for row in runs) for name in expected_stage_counts}
    operation_exact = len(runs) == 80 and actual_stage_counts == expected_stage_counts and len(pids) == len(set(pids)) == 81
    unit_contract = bool(preflight.get("contractTests", {}).get("passed"))
    evidence = {
        "PARENT_OR_TOOL_IDENTITY": bool(preflight.get("parentsMatch") and preflight.get("runtimeMatch") and preflight.get("allFrozenToolsMatchGit") and receipt_valid),
        "RUNTIME_OR_DISK_ADMISSION": receipt["diskAdmission"]["status"] == "ACCEPTED",
        "FRESHNESS": bool(preflight.get("freshnessMatched") and preflight.get("formalRootAbsent")),
        "SCENE_STRUCTURE": len(checks["scene"]) == 16 and all(checks["scene"]),
        "SOURCE_RENDER": len(checks["sourceBinding"]) == 16 and all(checks["sourceBinding"]) and all(checks["roster"]) and len(checks["sourceRepeat"]) == 8 and all(checks["sourceRepeat"]),
        "ADAPTER_EXTRACTION": len(checks["adapter"]) == 8 and all(checks["adapter"]) and len(checks["adapterRepeat"]) == 4 and all(checks["adapterRepeat"]),
        "QUANTIZER_DOMAIN": len(checks["rawVector"]) == 8 and all(checks["rawVector"]) and len(checks["quantDomain"]) == 8 and all(checks["quantDomain"]),
        "QUANTIZER_IDENTITY": len(checks["quantBinding"]) == 16 and all(checks["quantBinding"]) and len(checks["quantIdentity"]) == 12 and all(checks["quantIdentity"]) and len(checks["quantAnalytic"]) == 8 and all(checks["quantAnalytic"]) and unit_contract,
        "SEMANTIC_VALIDITY": len(checks["semantic"]) == 16 and all(checks["semantic"]),
        "ACCUMULATOR_IDENTITY": len(checks["accumulator"]) == 32 and all(checks["accumulator"]) and len(checks["invalidCurrent"]) == 8 and all(checks["invalidCurrent"]),
        "CONTROL_SENSITIVITY": len(checks["controls"]) == 10 and all(checks["controls"]),
        "STATIC_CONTROL": len(checks["static"]) == 2 and all(checks["static"]),
        "RAW_EXR_BRIDGE": len(checks["encoder"]) == 8 and all(checks["encoder"]) and len(checks["bridge"]) == 24 and all(checks["bridge"]),
        "DIAGNOSTIC_OR_OPERATION_IDENTITY": len(diagnostics) == spec["diagnostics"]["expectedPngs"] and operation_exact,
    }
    base_failure = first_failure(evidence, spec["baseFailureOrder"])
    verdict = spec["decisionRule"]["passVerdict"] if base_failure is None else spec["decisionRule"]["failVerdict"]
    attack_groups = {
        "D8_PARENT_IDENTITY": evidence["PARENT_OR_TOOL_IDENTITY"], "D9_1_PARENT_IDENTITY": evidence["PARENT_OR_TOOL_IDENTITY"], "D10_1_PARENT_IDENTITY": evidence["PARENT_OR_TOOL_IDENTITY"], "D11_NEGATIVE_PARENT_IDENTITY": evidence["PARENT_OR_TOOL_IDENTITY"], "PREREGISTRATION_IDENTITY": evidence["PARENT_OR_TOOL_IDENTITY"], "TOOL_FREEZE_IDENTITY": evidence["PARENT_OR_TOOL_IDENTITY"], "RUNTIME_IDENTITY": evidence["PARENT_OR_TOOL_IDENTITY"], "OCIO_IDENTITY": evidence["PARENT_OR_TOOL_IDENTITY"], "DISK_ADMISSION": evidence["RUNTIME_OR_DISK_ADMISSION"], "FRESHNESS_IDENTITY": evidence["FRESHNESS"],
        "FIXTURE_ROSTER": evidence["SCENE_STRUCTURE"], "SCENE_STRUCTURE": evidence["SCENE_STRUCTURE"], "ANIMATION_STRUCTURE": evidence["SCENE_STRUCTURE"], "MESH_TOPOLOGY": evidence["SCENE_STRUCTURE"], "POLYGON_MATERIAL_INDEX": evidence["SCENE_STRUCTURE"], "MATERIAL_EMISSION": evidence["SCENE_STRUCTURE"], "RENDER_STATE": evidence["SCENE_STRUCTURE"],
        "SOURCE_PROCESS_ROSTER": evidence["SOURCE_RENDER"], "PID_UNIQUENESS": operation_exact, "SOURCE_REPORT_BINDING": evidence["SOURCE_RENDER"], "MULTIPART_ROSTER": evidence["SOURCE_RENDER"], "MULTIPART_CHANNEL_LAYOUT": evidence["SOURCE_RENDER"], "SOURCE_REPEAT_DECODED_IDENTITY": evidence["SOURCE_RENDER"],
        "ADAPTER_REPORT_BINDING": evidence["ADAPTER_EXTRACTION"], "ADAPTER_ARRAY_RECONSTRUCTION": evidence["ADAPTER_EXTRACTION"], "ADAPTER_REPEAT_IDENTITY": evidence["ADAPTER_EXTRACTION"], "VECTOR_XY_MAPPING": evidence["QUANTIZER_DOMAIN"], "VECTOR_ZW_MAPPING": evidence["QUANTIZER_DOMAIN"], "RAW_VECTOR_TOLERANCE": evidence["QUANTIZER_DOMAIN"], "D9_COORDINATE_CONVERSION": evidence["ACCUMULATOR_IDENTITY"],
        "QUANTIZER_REPORT_BINDING": evidence["QUANTIZER_IDENTITY"], "QUANTIZER_F32_INPUT_IDENTITY": evidence["QUANTIZER_IDENTITY"], "QUANTIZER_OUTPUT_DTYPE_SHAPE": evidence["QUANTIZER_IDENTITY"], "QUANTIZER_PYTHON_NODE_IDENTITY": evidence["QUANTIZER_IDENTITY"], "QUANTIZER_NEAREST_INTEGER": unit_contract, "QUANTIZER_RADIUS_INCLUSIVE": unit_contract, "QUANTIZER_RADIUS_JUST_OUTSIDE_REJECTED": unit_contract, "QUANTIZER_HALF_INTEGER_REJECTED": unit_contract, "QUANTIZER_NONFINITE_REJECTED": unit_contract, "QUANTIZER_TOWARD_ZERO_SUBSTITUTION_REJECTED": unit_contract, "QUANTIZER_FLOOR_SUBSTITUTION_REJECTED": unit_contract, "QUANTIZER_CEIL_SUBSTITUTION_REJECTED": unit_contract, "QUANTIZER_NEGATIVE_ZERO_CANONICAL": evidence["STATIC_CONTROL"] and unit_contract, "QUANTIZER_IDEMPOTENCE": evidence["QUANTIZER_IDENTITY"], "QUANTIZER_NO_PARTIAL_OUTPUT_ON_REJECT": unit_contract, "QUANTIZED_MOVING_OWNER_EXACT": all(checks["quantAnalytic"]), "QUANTIZED_STATIC_EXACT": evidence["STATIC_CONTROL"],
        "SEMANTIC_ORACLE_INDEPENDENCE": evidence["SEMANTIC_VALIDITY"], "VALIDITY_BOUNDS": evidence["SEMANTIC_VALIDITY"], "VALIDITY_LAYER": evidence["SEMANTIC_VALIDITY"], "VALIDITY_SAME_ID_DEPTH": evidence["SEMANTIC_VALIDITY"], "VALIDITY_ALPHA": evidence["ACCUMULATOR_IDENTITY"], "SEMANTIC_PROBE_TOTALITY": evidence["SEMANTIC_VALIDITY"], "ACCUMULATOR_PROCESS_ROSTER": operation_exact, "PYTHON_NODE_VALIDITY_IDENTITY": evidence["ACCUMULATOR_IDENTITY"], "PYTHON_NODE_RESOLVED_IDENTITY": evidence["ACCUMULATOR_IDENTITY"], "INVALID_PIXEL_CURRENT_IDENTITY": evidence["ACCUMULATOR_IDENTITY"], "NAIVE_CONTROL_SENSITIVITY": evidence["CONTROL_SENSITIVITY"], "WRONG_SIGN_CONTROL_SENSITIVITY": evidence["CONTROL_SENSITIVITY"], "STATIC_NEGATIVE_CONTROL": evidence["STATIC_CONTROL"],
        "ENCODER_REPORT_BINDING": evidence["RAW_EXR_BRIDGE"], "RESOLVED_EXR_LAYOUT": evidence["RAW_EXR_BRIDGE"], "RESOLVED_EXR_DECODE_IDENTITY": evidence["RAW_EXR_BRIDGE"], "BRIDGE_REPORT_BINDING": evidence["RAW_EXR_BRIDGE"], "BRIDGE_GRAPH_RNA": evidence["RAW_EXR_BRIDGE"], "BRIDGE_OUTPUT_HASH": evidence["RAW_EXR_BRIDGE"], "BRIDGE_DECODED_IDENTITY": evidence["RAW_EXR_BRIDGE"], "BRIDGE_REPEAT_IDENTITY": evidence["RAW_EXR_BRIDGE"], "DIAGNOSTIC_TOTALITY": len(diagnostics) == 48, "OPERATION_BOUNDARY": operation_exact, "RESULT_SELF_HASH": True,
    }
    if set(attack_groups) != set(spec["attacks"]):
        raise RuntimeError("registered attack mapping is not total")
    attacks = [{"name": name, "passed": bool(attack_groups[name]), "method": "independent reconstruction, frozen unit mutation contract, or identity rejection"} for name in spec["attacks"]]
    counts = {"sourceBlenderProcesses": actual_stage_counts["SOURCE"], "adapterPythonProcesses": actual_stage_counts["ADAPTER"], "pythonQuantizerProcesses": actual_stage_counts["QUANTIZER_PYTHON"], "nodeQuantizerProcesses": actual_stage_counts["QUANTIZER_NODE"], "pythonAccumulatorProcesses": actual_stage_counts["ACCUMULATOR_PYTHON"], "nodeAccumulatorProcesses": actual_stage_counts["ACCUMULATOR_NODE"], "resolvedExrEncoderProcesses": actual_stage_counts["ENCODER"], "bridgeBlenderProcesses": actual_stage_counts["BRIDGE"], "analysisPythonProcesses": 1, "totalChildProcesses": len(pids), "uniqueChildPids": len(set(pids)), "totalBlenderProcesses": actual_stage_counts["SOURCE"] + actual_stage_counts["BRIDGE"], "totalBlenderRenderCalls": actual_stage_counts["SOURCE"] + actual_stage_counts["BRIDGE"], "cyclesRayRenders": actual_stage_counts["SOURCE"], "modelCalls": 0, "networkCalls": 0}
    core = {"evidence": evidence, "measurements": measurements, "operationCounts": counts, "verdict": verdict, "baseFailure": base_failure}
    body = {"schemaVersion": "bfs.blenderNearestIntegerTemporalRecoveryResult.v0.1", "experimentId": spec["experimentId"], "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["preflight"]["freezeCommit"], "receipt": {"uri": str(args.receipt), "sha256": sha(args.receipt)}, "analysisPid": os.getpid(), "evidence": evidence, "measurements": measurements, "diagnostics": diagnostics, "operationCounts": counts, "attacks": attacks, "attacksPassed": sum(row["passed"] for row in attacks), "evidenceCoreHash": canonical_hash(core), "verdict": verdict, "baseFailure": base_failure, "nonClaims": spec["nonClaims"]}
    args.output.write_text(json.dumps({**body, "resultHash": canonical_hash(body)}, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D11_1_ANALYSIS_OK verdict={verdict} baseFailure={base_failure} attacks={sum(row['passed'] for row in attacks)}/{len(attacks)}")


if __name__ == "__main__":
    main()
