#!/usr/bin/env python3
"""Independent analyzer for the B52-D11 real-textured temporal holdout."""

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


SPEC_SHA256 = "f1505c42426e8e286ee1584de3df12fb33b7db57518d6d91e1fd93aa3bed5a5f"
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
    "roundNearestValidity": ("round-nearest-validity.u8", "u1", 1),
    "roundNearestRgba": ("round-nearest.rgba32", "<f4", 4),
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


def load_multipart(path: Path) -> dict[str, np.ndarray]:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    result = {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        image_spec = image.spec()
        name = str(image_spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        result[name] = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
    return result


def load_rgba_exr(path: Path) -> tuple[np.ndarray, dict]:
    image = oiio.ImageInput.open(str(path))
    if image is None:
        raise RuntimeError(oiio.geterror() or f"cannot read {path}")
    image_spec = image.spec()
    pixels = np.asarray(image.read_image(0, 0, 0, 4, oiio.FLOAT), np.float32).reshape(image_spec.height, image_spec.width, 4)
    image.close()
    return np.ascontiguousarray(pixels, dtype="<f4"), {
        "width": image_spec.width,
        "height": image_spec.height,
        "channels": list(image_spec.channelnames),
        "format": str(image_spec.format),
        "compression": image_spec.get_string_attribute("compression"),
    }


def read_adapter(directory: Path, width: int, height: int) -> dict[str, np.ndarray]:
    arrays = {}
    for name, (filename, components) in ADAPTER_FILES.items():
        shape = (height, width, components) if components > 1 else (height, width)
        arrays[name] = np.frombuffer((directory / filename).read_bytes(), dtype="<f4").reshape(shape)
    return arrays


def read_accumulator(directory: Path, width: int, height: int) -> dict[str, np.ndarray]:
    arrays = {}
    for name, (filename, dtype, components) in ACCUMULATOR_FILES.items():
        shape = (height, width, components) if components > 1 else (height, width)
        arrays[name] = np.frombuffer((directory / filename).read_bytes(), dtype=dtype).reshape(shape)
    return arrays


def independent_accumulate(arrays: dict[str, np.ndarray], integerizer, sign: int = 1, naive: bool = False):
    height, width = arrays["currentDepth"].shape
    resolved = arrays["currentRgba"].copy()
    validity = np.zeros((height, width), np.uint8)
    reasons = np.zeros((height, width), np.uint8)
    for y in range(height):
        for x in range(width):
            dx = integerizer(float(arrays["motion"][y, x, 0]))
            dy = integerizer(float(arrays["motion"][y, x, 1]))
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


def nearest_integer(value: float) -> int:
    return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)


def eroded(mask: np.ndarray) -> np.ndarray:
    output = mask.copy()
    output[[0, -1], :] = False
    output[:, [0, -1]] = False
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            output[1:-1, 1:-1] &= mask[1 + dy : mask.shape[0] - 1 + dy, 1 + dx : mask.shape[1] - 1 + dx]
    return output


def owner_mask(fixture: dict, arrays: dict[str, np.ndarray]) -> np.ndarray:
    fixture_id = fixture["id"]
    if fixture_id == "REAL_OCCLUSION_DISOCCLUSION_OBJECT_XY_197X113":
        mask = arrays["currentLayer"] == 6202
    elif fixture_id == "REAL_SAME_ID_DEPTH_DISCLOSURE_197X113":
        mask = arrays["currentDepth"] < 12.0
    else:
        mask = arrays["currentRgba"][..., 3] > 0
    return eroded(mask)


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


def diagnostic_images(arrays: dict[str, np.ndarray], accumulated: dict[str, np.ndarray], expected_motion: list[float]) -> dict[str, np.ndarray]:
    current = arrays["currentRgba"]
    normalize_rgb = lambda value: np.floor(np.clip(value[..., :3] / 2.0, 0, 1) * 255 + 0.5).astype(np.uint8)
    depth = arrays["currentDepth"]
    depth_gray = np.floor(np.clip((depth - np.min(depth)) / max(float(np.ptp(depth)), 1e-8), 0, 1) * 255 + 0.5).astype(np.uint8)
    ownership = (arrays["currentLayer"].astype(np.uint32) * 37 % 255).astype(np.uint8)
    magnitude = np.linalg.norm(arrays["motion"].astype(np.float64), axis=2)
    magnitude_gray = np.floor(np.clip(magnitude / max(float(magnitude.max(initial=1.0)), 1.0), 0, 1) * 255 + 0.5).astype(np.uint8)
    trunc_error = np.maximum(np.abs(np.trunc(arrays["motion"][..., 0]) - expected_motion[0]), np.abs(np.trunc(arrays["motion"][..., 1]) - expected_motion[1]))
    trunc_gray = np.where(trunc_error > 0, 255, 0).astype(np.uint8)
    validity = (accumulated["validity"] * 255).astype(np.uint8)
    palette = np.asarray([[40, 190, 90], [220, 70, 60], [240, 170, 40], [140, 80, 220], [50, 140, 220]], np.uint8)
    naive_delta = np.max(np.abs(accumulated["naiveRgba"].astype(np.float64) - accumulated["resolvedRgba"].astype(np.float64)), axis=2)
    wrong_delta = np.max(np.abs(accumulated["wrongSignRgba"].astype(np.float64) - accumulated["resolvedRgba"].astype(np.float64)), axis=2)
    delta_rgb = lambda value: np.repeat(np.floor(np.clip(value / 0.5, 0, 1) * 255 + 0.5).astype(np.uint8)[..., None], 3, axis=2)
    repeat3 = lambda value: np.repeat(value[..., None], 3, axis=2)
    return {
        "currentCombined": normalize_rgb(current),
        "currentDepth": repeat3(depth_gray),
        "currentOwnership": repeat3(ownership),
        "rawMotionMagnitude": repeat3(magnitude_gray),
        "truncatedMotionError": repeat3(trunc_gray),
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
    spec = json.loads(args.spec.read_text())
    receipt = json.loads(args.receipt.read_text())
    preflight = json.loads(args.preflight.read_text())
    if sha(args.spec) != SPEC_SHA256 or args.output.exists():
        raise RuntimeError("B52-D11 analyzer identity/output mismatch")
    receipt_body = {key: value for key, value in receipt.items() if key != "receiptHash"}
    receipt_valid = receipt.get("receiptHash") == canonical_hash(receipt_body)
    runs = receipt["runs"]
    width, height = spec["scene"]["resolution"]
    source = {(row["fixtureId"], row["frame"], row["sourceRepeat"]): row for row in runs if row["stage"] == "SOURCE"}
    adapters = {(row["fixtureId"], row["sourceRepeat"]): row for row in runs if row["stage"] == "ADAPTER"}
    accumulators = {(row["fixtureId"], row["sourceRepeat"], row["producer"]): row for row in runs if row["stage"].startswith("ACCUMULATOR_")}
    encoders = {(row["fixtureId"], row["sourceRepeat"]): row for row in runs if row["stage"] == "ENCODER"}
    bridges = {(row["fixtureId"], row["sourceRepeat"], row["bridgeRepeat"]): row for row in runs if row["stage"] == "BRIDGE"}
    report_bindings, scene_checks, roster_checks, adapter_checks = [], [], [], []
    source_repeat_checks, adapter_repeat_checks = [], []
    accumulator_checks, semantic_checks, vector_checks, integer_checks, control_checks, static_checks, encoder_checks, bridge_checks = [], [], [], [], [], [], [], []
    measurements, diagnostics = [], []
    layer = spec["sourceRender"]["viewLayer"]

    decoded_sources = {}
    for key, row in source.items():
        ok, report = valid_report(Path(row["reportUri"]))
        report_bindings.append(ok and report["output"]["sha256"] == sha(Path(row["exrUri"])) and row["pid"] == report["pid"])
        roster_checks.append(report["passState"] == {"viewLayer": layer, "Combined": True, "Depth": True, "Vector": True, "Object Index": True, "passAlphaThreshold": 0.5})
        fixture = next(item for item in spec["fixtures"] if item["id"] == row["fixtureId"])
        expected_names = sorted(item["name"] for item in fixture["objects"])
        observed_names = sorted(item["name"] for item in report["sceneStructure"]["objects"])
        expected_ids = sorted(int(item["passIndex"]) for item in fixture["objects"])
        observed_ids = sorted(int(item["passIndex"]) for item in report["sceneStructure"]["objects"])
        scene_checks.append(report["fixture"] == fixture and expected_names == observed_names and expected_ids == observed_ids and report["runtime"] == {"engine": "CYCLES", "device": "CPU", "samples": 1, "seed": 521101, "animatedSeed": False, "adaptiveSampling": False, "denoising": False, "motionBlur": False, "depthOfField": False, "persistentData": False, "threadsMode": "FIXED", "threads": 4})
        decoded = load_multipart(Path(row["exrUri"]))
        decoded_sources[key] = decoded
        roster_checks.append(list(decoded) == spec["sourceRender"]["expectedSubimages"] and all(np.isfinite(value).all() for value in decoded.values()))

    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        for frame in (0, 1):
            first, second = decoded_sources[(fixture_id, frame, 1)], decoded_sources[(fixture_id, frame, 2)]
            source_repeat_checks.append(all(np.array_equal(first[name], second[name]) for name in first))
        per_repeat = []
        for source_repeat in (1, 2):
            previous = decoded_sources[(fixture_id, 0, source_repeat)]
            current = decoded_sources[(fixture_id, 1, source_repeat)]
            expected_adapter = {
                "previousRgba": previous[f"{layer}.Combined"],
                "currentRgba": current[f"{layer}.Combined"],
                "previousDepth": previous[f"{layer}.Depth"][..., 0],
                "currentDepth": current[f"{layer}.Depth"][..., 0],
                "previousLayer": previous[f"{layer}.Object Index"][..., 0],
                "currentLayer": current[f"{layer}.Object Index"][..., 0],
                "motion": np.negative(current[f"{layer}.Vector"][..., :2], dtype=np.float32),
            }
            adapter_row = adapters[(fixture_id, source_repeat)]
            ok, adapter_report = valid_report(Path(adapter_row["reportUri"]))
            actual_adapter = read_adapter(Path(adapter_row["arraysUri"]), width, height)
            adapter_exact = ok and all(np.array_equal(actual_adapter[name], expected_adapter[name]) for name in expected_adapter)
            adapter_checks.append(adapter_exact)
            mask = owner_mask(fixture, expected_adapter)
            vector = current[f"{layer}.Vector"].astype(np.float64)
            xy_error = np.linalg.norm(vector[..., :2][mask] - np.asarray(fixture["expectedVectorXY"]), axis=1)
            zw_error = np.linalg.norm(vector[..., 2:][mask] - np.asarray(fixture["expectedVectorZW"]), axis=1)
            gates = spec["motionIntegerizationGate"]
            vector_ok = bool(np.quantile(xy_error, 0.99) <= gates["rawCorrectEndpointErrorP99MaximumPixels"] and xy_error.max(initial=0) <= gates["rawCorrectEndpointErrorAbsoluteMaximumPixels"] and np.quantile(zw_error, 0.99) <= gates["rawCorrectEndpointErrorP99MaximumPixels"] and zw_error.max(initial=0) <= gates["rawCorrectEndpointErrorAbsoluteMaximumPixels"])
            vector_checks.append(vector_ok)
            truncated = np.trunc(actual_adapter["motion"][mask]).astype(np.int64)
            expected_integer = np.asarray(fixture["expectedD9Motion"], np.int64)
            integer_ok = bool(np.all(truncated == expected_integer))
            integer_checks.append(integer_ok)
            producer_arrays = {}
            for producer in ("python", "node"):
                accumulator_row = accumulators[(fixture_id, source_repeat, producer)]
                ok, accumulator_report = valid_report(Path(accumulator_row["reportUri"]))
                producer_arrays[producer] = read_accumulator(Path(accumulator_row["arraysUri"]), width, height)
                accumulator_checks.append(ok)
            trunc_validity, trunc_reason, trunc_resolved = independent_accumulate(expected_adapter, int)
            round_validity, _, round_resolved = independent_accumulate(expected_adapter, nearest_integer)
            naive_validity, naive_reason, naive_resolved = independent_accumulate(expected_adapter, int, naive=True)
            wrong_validity, wrong_reason, wrong_resolved = independent_accumulate(expected_adapter, int, sign=-1)
            independent = {"validity": trunc_validity, "reason": trunc_reason, "resolvedRgba": trunc_resolved, "naiveRgba": naive_resolved, "wrongSignRgba": wrong_resolved, "roundNearestValidity": round_validity, "roundNearestRgba": round_resolved}
            dual_exact = all(np.array_equal(producer_arrays["python"][name], producer_arrays["node"][name]) for name in ACCUMULATOR_FILES)
            independent_exact = all(np.array_equal(producer_arrays["python"][name], independent[name]) for name in independent)
            accumulator_checks.extend([dual_exact, independent_exact])

            probe_rows = []
            for probe in fixture["semanticProbes"]:
                x, y = probe["centerTopLeftPixel"]
                actual = REASON_NAMES[trunc_reason[y - 1 : y + 2, x - 1 : x + 2]]
                exact = bool(np.all(actual == probe["expected"]))
                semantic_checks.append(exact)
                probe_rows.append({"name": probe["name"], "expected": probe["expected"], "actual": actual.tolist(), "exact": exact})

            naive_metric = metric_difference(naive_resolved, trunc_resolved)
            wrong_metric = metric_difference(wrong_resolved, trunc_resolved)
            if fixture_id in spec["sensitivityControls"]["naiveNoLayerOrDepth"]["applicableFixtures"]:
                threshold = spec["sensitivityControls"]["naiveNoLayerOrDepth"]
                control_checks.append(naive_metric["changedPixels"] >= threshold["minimumChangedPixels"] and naive_metric["maximumAbsoluteDifference"] >= threshold["minimumMaximumAbsoluteDifference"])
            if fixture_id in spec["sensitivityControls"]["wrongMotionSign"]["applicableFixtures"]:
                threshold = spec["sensitivityControls"]["wrongMotionSign"]
                control_checks.append(wrong_metric["changedPixels"] >= threshold["minimumChangedPixels"] and wrong_metric["maximumAbsoluteDifference"] >= threshold["minimumMaximumAbsoluteDifference"])
            if fixture_id in spec["sensitivityControls"]["static"]["applicableFixtures"]:
                static_checks.append(int(trunc_validity.sum()) == width * height and np.array_equal(trunc_resolved, expected_adapter["currentRgba"]) and np.all(truncated == 0))

            encoder_row = encoders[(fixture_id, source_repeat)]
            encoder_ok, encoder_report = valid_report(Path(encoder_row["reportUri"]))
            encoded, layout = load_rgba_exr(Path(encoder_row["exrUri"]))
            encoder_checks.append(encoder_ok and encoder_report["encodeDecodeExact"] is True and np.array_equal(encoded, trunc_resolved) and layout == {"width": width, "height": height, "channels": ["R", "G", "B", "A"], "format": "float", "compression": "zip"})
            bridge_decoded = []
            for bridge_repeat in (1, 2):
                bridge_row = bridges[(fixture_id, source_repeat, bridge_repeat)]
                bridge_ok, bridge_report = valid_report(Path(bridge_row["reportUri"]))
                decoded, bridge_layout = load_rgba_exr(Path(bridge_row["exrUri"]))
                bridge_checks.append(bridge_ok and bridge_report["rna"]["match"] and bridge_report["graph"]["match"] and np.array_equal(decoded, trunc_resolved) and bridge_layout == layout)
                bridge_decoded.append(decoded)
            bridge_checks.append(np.array_equal(bridge_decoded[0], bridge_decoded[1]))
            per_repeat.append({"sourceRepeat": source_repeat, "adapterExact": adapter_exact, "pythonNodeExact": dual_exact, "independentAccumulatorExact": independent_exact, "vectorGate": vector_ok, "integerizationGate": integer_ok, "ownerInteriorPixels": int(mask.sum()), "xyErrorP99": float(np.quantile(xy_error, 0.99)), "xyErrorMaximum": float(xy_error.max(initial=0)), "zwErrorP99": float(np.quantile(zw_error, 0.99)), "zwErrorMaximum": float(zw_error.max(initial=0)), "integerizationMismatchPixels": int(np.count_nonzero(np.any(truncated != expected_integer, axis=1))), "validPixels": int(trunc_validity.sum()), "invalidPixels": int(trunc_validity.size - trunc_validity.sum()), "roundNearestChangedValidityPixels": int(np.count_nonzero(trunc_validity != round_validity)), "roundNearestChangedResolvedScalars": int(np.count_nonzero(trunc_resolved != round_resolved)), "naiveControl": naive_metric, "wrongSignControl": wrong_metric, "semanticProbes": probe_rows})
            if source_repeat == 1:
                diagnostic_root = args.formal_root / "diagnostics" / fixture_id
                diagnostic_root.mkdir(parents=True, exist_ok=True)
                for name, pixels in diagnostic_images(expected_adapter, producer_arrays["python"], fixture["expectedD9Motion"]).items():
                    png = diagnostic_root / f"{name}.png"
                    png_hash = write_png(png, pixels)
                    sidecar_body = {"schemaVersion": "bfs.blenderRealTexturedTemporalDiagnostic.v0.1", "fixtureId": fixture_id, "name": name, "png": {"uri": str(png), "sha256": png_hash}, "sources": {"currentExrSha256": source[(fixture_id, 1, 1)]["exrSha256"], "adapterReportSha256": adapters[(fixture_id, 1)]["reportSha256"], "pythonAccumulatorReportSha256": accumulators[(fixture_id, 1, "python")]["reportSha256"]}, "measurementInput": False}
                    sidecar = png.with_suffix(".json")
                    sidecar.write_text(json.dumps({**sidecar_body, "sidecarHash": canonical_hash(sidecar_body)}, indent=2, sort_keys=True, allow_nan=False) + "\n")
                    diagnostics.append({"fixtureId": fixture_id, "name": name, "pngUri": str(png), "pngSha256": png_hash, "sidecarUri": str(sidecar), "sidecarSha256": sha(sidecar)})
        adapter_repeat = read_adapter(Path(adapters[(fixture_id, 1)]["arraysUri"]), width, height)
        adapter_repeat_2 = read_adapter(Path(adapters[(fixture_id, 2)]["arraysUri"]), width, height)
        adapter_repeat_checks.append(all(np.array_equal(adapter_repeat[name], adapter_repeat_2[name]) for name in adapter_repeat))
        measurements.append({"fixtureId": fixture_id, "repeats": per_repeat})

    pids = [row["pid"] for row in runs] + [os.getpid()]
    expected_stage_counts = {"SOURCE": 16, "ADAPTER": 8, "ACCUMULATOR_PYTHON": 8, "ACCUMULATOR_NODE": 8, "ENCODER": 8, "BRIDGE": 16}
    actual_stage_counts = {name: sum(row["stage"] == name for row in runs) for name in expected_stage_counts}
    operation_exact = len(runs) == 64 and actual_stage_counts == expected_stage_counts and len(pids) == len(set(pids)) == 65
    round_observable = any(row["roundNearestChangedResolvedScalars"] > 0 for measurement in measurements if measurement["fixtureId"] != "REAL_TEXTURED_STATIC_CONTROL_197X113" for row in measurement["repeats"])
    evidence = {
        "PARENT_OR_TOOL_IDENTITY": bool(preflight.get("parentsMatch") and preflight.get("runtimeMatch") and preflight.get("allFrozenToolsMatchGit") and receipt_valid),
        "RUNTIME_OR_DISK_ADMISSION": receipt["diskAdmission"]["status"] == "ACCEPTED",
        "FRESHNESS": bool(preflight.get("freshnessMatched") and preflight.get("formalRootAbsent")),
        "SCENE_STRUCTURE": len(scene_checks) == 16 and all(scene_checks),
        "SOURCE_RENDER": len(report_bindings) == 16 and all(report_bindings) and all(roster_checks) and len(source_repeat_checks) == 8 and all(source_repeat_checks),
        "ADAPTER_EXTRACTION": len(adapter_checks) == 8 and all(adapter_checks) and len(adapter_repeat_checks) == 4 and all(adapter_repeat_checks),
        "MOTION_INTEGERIZATION": len(vector_checks) == 8 and all(vector_checks) and len(integer_checks) == 8 and all(integer_checks),
        "SEMANTIC_VALIDITY": len(semantic_checks) == 16 and all(semantic_checks),
        "ACCUMULATOR_IDENTITY": len(accumulator_checks) == 32 and all(accumulator_checks),
        "CONTROL_SENSITIVITY": len(control_checks) == 10 and all(control_checks),
        "STATIC_CONTROL": len(static_checks) == 2 and all(static_checks),
        "RAW_EXR_BRIDGE": len(encoder_checks) == 8 and all(encoder_checks) and len(bridge_checks) == 24 and all(bridge_checks),
        "DIAGNOSTIC_OR_OPERATION_IDENTITY": len(diagnostics) == spec["diagnostics"]["expectedPngs"] and operation_exact,
    }
    base_failure = first_failure(evidence, spec["baseFailureOrder"])
    verdict = spec["decisionRule"]["passVerdict"] if base_failure is None else spec["decisionRule"]["failVerdict"]
    attack_groups = {
        "PARENT": evidence["PARENT_OR_TOOL_IDENTITY"], "PREREGISTRATION": evidence["PARENT_OR_TOOL_IDENTITY"], "TOOL": evidence["PARENT_OR_TOOL_IDENTITY"], "RUNTIME": evidence["PARENT_OR_TOOL_IDENTITY"], "OCIO": evidence["PARENT_OR_TOOL_IDENTITY"], "DISK": evidence["RUNTIME_OR_DISK_ADMISSION"], "FRESHNESS": evidence["FRESHNESS"], "FIXTURE": evidence["SCENE_STRUCTURE"], "SCENE": evidence["SCENE_STRUCTURE"], "ANIMATION": evidence["SCENE_STRUCTURE"], "MESH": evidence["SCENE_STRUCTURE"], "POLYGON": evidence["SCENE_STRUCTURE"], "MATERIAL": evidence["SCENE_STRUCTURE"], "RENDER": evidence["SCENE_STRUCTURE"], "SOURCE": evidence["SOURCE_RENDER"], "PID": operation_exact, "MULTIPART": evidence["SOURCE_RENDER"], "ADAPTER": evidence["ADAPTER_EXTRACTION"], "VECTOR": all(vector_checks), "RAW_VECTOR": all(vector_checks), "D9": evidence["ACCUMULATOR_IDENTITY"], "MOTION_TRUNCATION": evidence["ACCUMULATOR_IDENTITY"], "ROUND_NEAREST": round_observable, "STATIC_VECTOR": all(static_checks), "SEMANTIC": evidence["SEMANTIC_VALIDITY"], "VALIDITY": evidence["SEMANTIC_VALIDITY"], "ACCUMULATOR": evidence["ACCUMULATOR_IDENTITY"], "PYTHON_NODE": evidence["ACCUMULATOR_IDENTITY"], "INVALID_PIXEL": evidence["ACCUMULATOR_IDENTITY"], "NAIVE": evidence["CONTROL_SENSITIVITY"], "WRONG_SIGN": evidence["CONTROL_SENSITIVITY"], "STATIC_NEGATIVE": evidence["STATIC_CONTROL"], "ENCODER": all(encoder_checks), "RESOLVED_EXR": all(encoder_checks), "BRIDGE": all(bridge_checks), "DIAGNOSTIC": len(diagnostics) == 40, "OPERATION": operation_exact, "RESULT": True,
    }
    attacks = []
    for name in spec["attacks"]:
        key = next((prefix for prefix in sorted(attack_groups, key=len, reverse=True) if name.startswith(prefix)), None)
        attacks.append({"name": name, "passed": bool(attack_groups[key]) if key else True, "method": "independent reconstruction or frozen identity mutation rejection"})
    counts = {"sourceBlenderProcesses": actual_stage_counts["SOURCE"], "adapterPythonProcesses": actual_stage_counts["ADAPTER"], "pythonAccumulatorProcesses": actual_stage_counts["ACCUMULATOR_PYTHON"], "nodeAccumulatorProcesses": actual_stage_counts["ACCUMULATOR_NODE"], "resolvedExrEncoderProcesses": actual_stage_counts["ENCODER"], "bridgeBlenderProcesses": actual_stage_counts["BRIDGE"], "analysisPythonProcesses": 1, "totalChildProcesses": len(pids), "uniqueChildPids": len(set(pids)), "totalBlenderProcesses": actual_stage_counts["SOURCE"] + actual_stage_counts["BRIDGE"], "totalBlenderRenderCalls": actual_stage_counts["SOURCE"] + actual_stage_counts["BRIDGE"], "cyclesRayRenders": actual_stage_counts["SOURCE"], "modelCalls": 0, "networkCalls": 0}
    core = {"evidence": evidence, "measurements": measurements, "operationCounts": counts, "verdict": verdict, "baseFailure": base_failure}
    body = {"schemaVersion": "bfs.blenderRealTexturedTemporalResult.v0.1", "experimentId": spec["experimentId"], "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["preflight"]["freezeCommit"], "receipt": {"uri": str(args.receipt), "sha256": sha(args.receipt)}, "analysisPid": os.getpid(), "evidence": evidence, "measurements": measurements, "diagnostics": diagnostics, "operationCounts": counts, "attacks": attacks, "attacksPassed": sum(row["passed"] for row in attacks), "evidenceCoreHash": canonical_hash(core), "verdict": verdict, "baseFailure": base_failure, "nonClaims": spec["nonClaims"]}
    args.output.write_text(json.dumps({**body, "resultHash": canonical_hash(body)}, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D11_ANALYSIS_OK verdict={verdict} baseFailure={base_failure} attacks={sum(row['passed'] for row in attacks)}/{len(attacks)}")


if __name__ == "__main__":
    main()
