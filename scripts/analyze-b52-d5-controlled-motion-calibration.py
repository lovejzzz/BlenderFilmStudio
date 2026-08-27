#!/usr/bin/env python3
"""Analyze, attack and decide the preregistered B52-D5 task calibration."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


PREREGISTRATION_COMMIT = "0e127a66d19f16dec7bf88bafb5158d608e574cf"
SPEC_SHA256 = "5c2e6564650d6ab6d98f6bb7d91da4304c1cfeece4601871ed74fe5fd5521e01"
EXPECTED_PARTS = [
    "BFS_MASTER.Combined", "BFS_MASTER.CryptoObject00", "BFS_MASTER.CryptoObject01",
    "BFS_MASTER.CryptoObject02", "BFS_MASTER.Debug Sample Count", "BFS_MASTER.Depth",
    "BFS_MASTER.Normal", "BFS_MASTER.Vector",
]
EXPECTED_IMAGE_OUTPUTS = ["Combined", "Alpha", "Depth", "Normal", "Vector", "CryptoObject00", "CryptoObject01", "CryptoObject02", "Debug Sample Count"]
EXPECTED_VECTOR_BLUR_INPUTS = [
    {"identifier": "Image", "name": "Image", "type": "RGBA"},
    {"identifier": "Speed", "name": "Speed", "type": "VECTOR"},
    {"identifier": "Z", "name": "Depth", "type": "VALUE"},
    {"identifier": "Samples", "name": "Samples", "type": "INT"},
    {"identifier": "Shutter", "name": "Shutter", "type": "VALUE"},
]
EXPECTED_LINKS = sorted([
    "BFS_D5_SOURCE.Combined->BFS_D5_VECTOR_BLUR.Image",
    "BFS_D5_SOURCE.Vector->BFS_D5_VECTOR_BLUR.Speed",
    "BFS_D5_SOURCE.Depth->BFS_D5_VECTOR_BLUR.Z",
    "BFS_D5_VECTOR_BLUR.Image->BFS_D5_GROUP_OUTPUT.Socket_0",
])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


def array_hash(values: np.ndarray, dtype: str = "<f4") -> str:
    return hashlib.sha256(np.ascontiguousarray(values, dtype=dtype).tobytes()).hexdigest()


def load_multipart_exr(path: Path) -> dict:
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror() or f"cannot read {path}")
    roster, parts, channels = [], {}, {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        if not image.initialized:
            raise RuntimeError(image.geterror() or f"cannot read subimage {index} in {path}")
        image_spec = image.spec()
        name = str(image_spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        roster.append(name)
        parts[name] = pixels
        channels[name] = list(image_spec.channelnames)
    return {"roster": roster, "parts": parts, "channels": channels}


def load_single_exr(path: Path) -> dict:
    image = oiio.ImageBuf(str(path), 0, 0)
    if not image.initialized:
        raise RuntimeError(image.geterror() or f"cannot read {path}")
    image_spec = image.spec()
    pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
    return {
        "pixels": pixels,
        "channels": list(image_spec.channelnames),
        "subimageName": str(image_spec.getattribute("oiio:subimagename") or "subimage-0"),
        "subimages": int(image.nsubimages),
    }


def percentile(values: np.ndarray, quantile: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=np.float64).reshape(-1), quantile, method="higher"))


def stats(values: np.ndarray) -> dict:
    flat = np.asarray(values, dtype=np.float64).reshape(-1)
    finite = bool(bool(flat.size) and np.isfinite(flat).all())
    if not finite:
        return {"p50": None, "p95": None, "p99": None, "maximum": None, "rmse": None, "finite": False}
    return {
        "p50": percentile(flat, 0.50), "p95": percentile(flat, 0.95), "p99": percentile(flat, 0.99),
        "maximum": float(np.max(flat)), "rmse": float(np.sqrt(np.mean(np.square(flat, dtype=np.float64)))), "finite": True,
    }


def source_keys(spec: dict) -> list[tuple[str, int]]:
    return [(fixture["id"], repeat) for fixture in spec["fixtures"] for repeat in (1, 2)]


def compositor_keys(spec: dict) -> list[tuple[str, float, int]]:
    return [(fixture["id"], float(shutter), repeat) for fixture in spec["fixtures"] for shutter in spec["compositor"]["shutters"] for repeat in (1, 2)]


def expected_fixture_structure(spec: dict, fixture: dict) -> dict:
    common = spec["fixtureCommon"]
    objects = []
    for item in common["geometry"]:
        location = list(item["location"])
        if item["id"] == "BFS_MOVER" and fixture["moverXByFrame"] is not None:
            location[0] = fixture["moverXByFrame"][str(common["evaluationFrame"])]
        objects.append({"name": item["id"], "type": "MESH", "location": location, "scale": list(item["scale"])})
    camera_location = list(common["camera"]["location"])
    if fixture["cameraXByFrame"] is not None:
        camera_location[0] = fixture["cameraXByFrame"][str(common["evaluationFrame"])]
    objects.extend([
        {"name": "BFS_D5_CAMERA", "type": "CAMERA", "location": camera_location, "scale": [1.0, 1.0, 1.0]},
        {"name": "BFS_D5_KEY", "type": "LIGHT", "location": list(common["keyLight"]["location"]), "scale": [1.0, 1.0, 1.0]},
    ])

    def action(values: dict[str, float] | None) -> list[dict]:
        if values is None:
            return []
        return [{
            "layerIndex": 0, "stripIndex": 0, "channelBagIndex": 0, "dataPath": "location", "arrayIndex": 0,
            "keyframes": [{"frame": float(frame), "value": float(value), "interpolation": "LINEAR"} for frame, value in values.items()],
        }]

    return {
        "sceneName": f"BFS_D5_{fixture['id']}",
        "objects": sorted(objects, key=lambda item: item["name"]),
        "moverAction": action(fixture["moverXByFrame"]),
        "cameraAction": action(fixture["cameraXByFrame"]),
    }


def measure_fixture(source: dict, outputs: dict[float, np.ndarray], fixture_id: str) -> tuple[dict, dict[str, np.ndarray]]:
    combined = source["parts"]["BFS_MASTER.Combined"].astype(np.float64)
    vector = source["parts"]["BFS_MASTER.Vector"].astype(np.float64)
    magnitude = np.maximum(np.linalg.norm(vector[..., :2], axis=-1), np.linalg.norm(vector[..., 2:4], axis=-1))
    vector_measurement = {
        **stats(magnitude),
        "pixelsAboveOne": int(np.count_nonzero(magnitude > 1.0)),
        "pixelsAbove1Over65536": int(np.count_nonzero(magnitude > 1.0 / 65536.0)),
        "decodedPixelSha256": array_hash(vector),
    }
    effects, error_maps = [], {}
    for shutter in sorted(outputs):
        output = outputs[shutter].astype(np.float64)
        rgb_error = np.max(np.abs(output[..., :3] - combined[..., :3]), axis=-1)
        alpha_error = np.abs(output[..., 3] - combined[..., 3])
        error_maps[shutter] = rgb_error
        effects.append({
            "shutter": shutter,
            "rgbAbsoluteError": stats(rgb_error),
            "alphaAbsoluteErrorMaximum": float(np.max(alpha_error)),
            "changedPixelsAbove1Over65536": int(np.count_nonzero(rgb_error > 1.0 / 65536.0)),
            "changedPixelsAbove1Over4096": int(np.count_nonzero(rgb_error > 1.0 / 4096.0)),
            "decodedPixelSha256": array_hash(output),
        })
    return {
        "fixtureId": fixture_id,
        "vectorMagnitudePixels": vector_measurement,
        "shutterEffects": effects,
    }, {"combined": combined, "vector-magnitude": magnitude, "shutter-0p5-rgb-maximum-absolute-error": error_maps[0.5]}


def classify_fixture(measurement: dict, spec: dict) -> dict:
    fixture_id = measurement["fixtureId"]
    vector = measurement["vectorMagnitudePixels"]
    effects = {float(item["shutter"]): item for item in measurement["shutterEffects"]}
    zero_gate = spec["taskValidityGates"]["shutterZero"]
    zero = effects[0.0]
    zero_passed = bool(
        zero["rgbAbsoluteError"]["finite"]
        and zero["rgbAbsoluteError"]["maximum"] <= zero_gate["rgbAbsoluteErrorMaximum"]
        and zero["changedPixelsAbove1Over65536"] == zero_gate["changedPixelsAbove1Over65536"]
    )
    if fixture_id in spec["taskValidityGates"]["movingFixtures"]:
        moving_vector = spec["taskValidityGates"]["movingVector"]
        vector_passed = bool(
            vector["finite"]
            and moving_vector["magnitudeMaximumMinimumPixels"] <= vector["maximum"] <= moving_vector["magnitudeMaximumMaximumPixels"]
            and vector["p99"] >= moving_vector["magnitudeP99MinimumPixels"]
            and vector["pixelsAboveOne"] >= moving_vector["pixelsAboveOnePixelMinimum"]
        )
        half_gate = spec["taskValidityGates"]["movingShutterHalf"]
        half = effects[0.5]
        half_passed = bool(
            half["rgbAbsoluteError"]["finite"]
            and half["rgbAbsoluteError"]["maximum"] >= half_gate["rgbAbsoluteErrorMaximumMinimum"]
            and half["rgbAbsoluteError"]["p99"] >= half_gate["rgbAbsoluteErrorP99Minimum"]
            and half["rgbAbsoluteError"]["rmse"] >= half_gate["rgbRmseMinimum"]
            and half["changedPixelsAbove1Over4096"] >= half_gate["changedPixelsAbove1Over4096Minimum"]
        )
        dose_items = [effects[value]["rgbAbsoluteError"] for value in (0.25, 0.5, 1.0)]
        ratio = dose_items[2]["rmse"] / dose_items[0]["rmse"] if dose_items[0]["rmse"] and dose_items[0]["rmse"] > 0 else None
        dose_gate = spec["taskValidityGates"]["movingDoseResponse"]
        dose_passed = bool(
            all(item["finite"] for item in dose_items)
            and all(left["maximum"] < right["maximum"] for left, right in zip(dose_items, dose_items[1:]))
            and all(left["p99"] < right["p99"] for left, right in zip(dose_items, dose_items[1:]))
            and all(left["rmse"] < right["rmse"] for left, right in zip(dose_items, dose_items[1:]))
            and ratio is not None and ratio >= dose_gate["shutterOneToQuarterRmseRatioMinimum"]
        )
        return {"fixtureId": fixture_id, "motionClass": "MOVING", "vectorPassed": vector_passed, "shutterZeroPassed": zero_passed, "shutterHalfPassed": half_passed, "doseResponsePassed": dose_passed, "shutterOneToQuarterRmseRatio": ratio, "passed": bool(vector_passed and zero_passed and half_passed and dose_passed)}
    static_gate = spec["taskValidityGates"]["staticControl"]
    static_passed = bool(
        vector["finite"]
        and vector["maximum"] <= static_gate["vectorMagnitudeMaximumPixels"]
        and vector["p99"] <= static_gate["vectorMagnitudeP99Pixels"]
        and all(item["rgbAbsoluteError"]["finite"] and item["rgbAbsoluteError"]["maximum"] <= static_gate["allShuttersRgbAbsoluteErrorMaximum"] and item["changedPixelsAbove1Over65536"] == static_gate["allShuttersChangedPixelsAbove1Over65536"] for item in effects.values())
    )
    return {"fixtureId": fixture_id, "motionClass": "STATIC", "vectorPassed": static_passed, "shutterZeroPassed": zero_passed, "staticControlPassed": static_passed, "passed": bool(static_passed and zero_passed)}


def replay_classification(evidence: dict, spec: dict) -> list[dict]:
    return [classify_fixture(next(item for item in evidence["fixtureMeasurements"] if item["fixtureId"] == fixture["id"]), spec) for fixture in spec["fixtures"]]


def write_png(path: Path, pixels: np.ndarray) -> None:
    array = np.ascontiguousarray(pixels, dtype=np.uint8)
    output = oiio.ImageOutput.create(str(path))
    if output is None:
        raise RuntimeError(f"cannot create PNG: {path}")
    image_spec = oiio.ImageSpec(array.shape[1], array.shape[0], 3, oiio.UINT8)
    image_spec.channelnames = ["R", "G", "B"]
    if not output.open(str(path), image_spec) or not output.write_image(array) or not output.close():
        raise RuntimeError(output.geterror() or f"cannot write PNG: {path}")


def write_diagnostic(output_directory: Path, canonical_directory: str, fixture_id: str, kind: str, values: np.ndarray, mapping: dict, sources: dict) -> dict:
    if kind == "combined":
        linear = np.clip(values[..., :3].astype(np.float64), float(mapping["minimum"]), float(mapping["clipMaximum"]))
        normalized = (linear - float(mapping["minimum"])) / (float(mapping["clipMaximum"]) - float(mapping["minimum"]))
        encoded = np.rint(normalized * 255.0).astype(np.uint8)
    else:
        normalized = np.clip((values.astype(np.float64) - float(mapping["minimum"])) / (float(mapping["clipMaximum"]) - float(mapping["minimum"])), 0.0, 1.0)
        encoded = np.rint(np.stack([normalized, np.square(normalized), np.zeros_like(normalized)], axis=-1) * 255.0).astype(np.uint8)
    filename = f"{fixture_id.lower()}--{kind}.png"
    png_path = output_directory / filename
    sidecar_path = png_path.with_suffix(".json")
    write_png(png_path, encoded)
    reopened = oiio.ImageBuf(str(png_path))
    reopened_pixels = np.ascontiguousarray(np.asarray(reopened.get_pixels(oiio.UINT8), dtype=np.uint8))
    if reopened_pixels.shape != encoded.shape or not np.array_equal(reopened_pixels, encoded):
        raise RuntimeError(f"diagnostic decoded mismatch: {png_path}")
    sidecar = {
        "schemaVersion": "bfs.controlledMotionVectorBlurDiagnostic.v0.1", "experimentId": "B52-D5",
        "fixtureId": fixture_id, "kind": kind, "mapping": mapping,
        "dimensions": [int(encoded.shape[1]), int(encoded.shape[0])],
        "decodedValueSha256": array_hash(values), "decodedRgb8Sha256": hashlib.sha256(encoded.tobytes()).hexdigest(),
        "sources": sources,
    }
    png_binding = {"uri": f"{canonical_directory}/{filename}", "sha256": sha256_file(png_path), "bytes": png_path.stat().st_size}
    sidecar["png"] = png_binding
    sidecar_path.write_bytes(canonical_bytes(sidecar))
    return {
        "fixtureId": fixture_id, "kind": kind, "mapping": mapping,
        "decodedValueSha256": sidecar["decodedValueSha256"], "decodedRgb8Sha256": sidecar["decodedRgb8Sha256"],
        "png": png_binding,
        "sidecar": {"uri": f"{canonical_directory}/{sidecar_path.name}", "sha256": sha256_file(sidecar_path), "bytes": sidecar_path.stat().st_size},
        "identityMatch": True,
    }


def finite_tree(value: object) -> bool:
    if isinstance(value, dict):
        return all(finite_tree(item) for item in value.values())
    if isinstance(value, list):
        return all(finite_tree(item) for item in value)
    return not isinstance(value, float) or math.isfinite(value)


def hash_payload(evidence: dict) -> dict:
    excluded = {"evidenceCoreHash", "baseFailure", "attacks", "attacksPassed", "verdict"}
    return {key: value for key, value in evidence.items() if key not in excluded}


def validate(evidence: dict, spec: dict) -> str | None:
    if not evidence["specObservation"]["match"] or len(evidence["parentObservations"]) != len(spec["parents"]) or not all(item["match"] for item in evidence["parentObservations"]):
        return "PARENT_IDENTITY"
    if not evidence["runtimeObservations"]["blender"]["match"]:
        return "BLENDER_IDENTITY"
    if not evidence["runtimeObservations"]["ocio"]["match"]:
        return "OCIO_IDENTITY"
    expected_sources = source_keys(spec)
    observed_sources = [(item["fixtureId"], item["repeat"]) for item in evidence["sourceRunObservations"]]
    if observed_sources != expected_sources:
        return "FIXTURE_ROSTER"
    if not all(item["fixtureMatch"] and item["structureMatch"] for item in evidence["sourceRunObservations"]):
        return "FIXTURE_STRUCTURE"
    if not all(item["animationApiMatch"] for item in evidence["sourceRunObservations"]):
        return "BLENDER52_ANIMATION_API"
    source_pids = [item["pid"] for item in evidence["sourceRunObservations"]]
    if len(source_pids) != 6 or len(set(source_pids)) != 6 or not all(item["exitCode"] == 0 and not item["timedOut"] and item["reportHashMatch"] for item in evidence["sourceRunObservations"]):
        return "SOURCE_PROCESS_ROSTER"
    if (
        len(evidence["sourceOutputObservations"]) != 6
        or not all(item["identityMatch"] and item["partsExact"] and item["finite"] for item in evidence["sourceOutputObservations"])
        or not all(item["settingsMatch"] and item["passStateMatch"] for item in evidence["sourceRunObservations"])
        or len(evidence["sourcePreObservations"]) != 6 or len(evidence["sourcePostObservations"]) != 6
        or not all(item["match"] for item in evidence["sourcePreObservations"] + evidence["sourcePostObservations"])
    ):
        return "SOURCE_PASS_TOTALITY"
    if len(evidence["sourceRepeatComparisons"]) != 24 or not all(item["decodedExact"] for item in evidence["sourceRepeatComparisons"]):
        return "SOURCE_REPEAT_IDENTITY"
    if not all(item["rnaMatch"] and item["imageOutputs"] == EXPECTED_IMAGE_OUTPUTS and item["vectorBlurInputs"] == EXPECTED_VECTOR_BLUR_INPUTS and item["graphMatch"] and item["graphLinks"] == EXPECTED_LINKS and item["graphNodeCount"] == 3 and item["settingsMatch"] and item["vectorBlurMatch"] for item in evidence["compositorRunObservations"]):
        return "COMPOSITOR_GRAPH_CONTRACT"
    expected_compositors = compositor_keys(spec)
    observed_compositors = [(item["fixtureId"], item["shutter"], item["repeat"]) for item in evidence["compositorRunObservations"]]
    all_pids = source_pids + [item["pid"] for item in evidence["compositorRunObservations"]]
    if observed_compositors != expected_compositors or len(all_pids) != 30 or len(set(all_pids)) != 30 or not all(item["exitCode"] == 0 and not item["timedOut"] and item["reportHashMatch"] and item["inputMatch"] for item in evidence["compositorRunObservations"]):
        return "COMPOSITOR_PROCESS_ROSTER"
    if len(evidence["compositorOutputObservations"]) != 24 or not all(item["identityMatch"] and item["shape"] == [288, 512, 4] and item["channels"] == ["R", "G", "B", "A"] and item["subimages"] == 1 and item["finite"] for item in evidence["compositorOutputObservations"]):
        return "COMPOSITOR_OUTPUT_TOTALITY"
    if len(evidence["compositorRepeatComparisons"]) != 12 or not all(item["decodedExact"] for item in evidence["compositorRepeatComparisons"]):
        return "COMPOSITOR_REPEAT_IDENTITY"
    if len(evidence["fixtureMeasurements"]) != 3 or not finite_tree(evidence["fixtureMeasurements"]):
        return "MOVING_TASK_SENSITIVITY"
    replay = replay_classification(evidence, spec)
    if evidence["fixtureClassifications"] != replay:
        return "MOVING_TASK_SENSITIVITY"
    moving = [item for item in replay if item["motionClass"] == "MOVING"]
    static = [item for item in replay if item["motionClass"] == "STATIC"]
    if len(moving) != 2 or not all(item["vectorPassed"] and item["shutterHalfPassed"] for item in moving):
        return "MOVING_TASK_SENSITIVITY"
    if not all(item["shutterZeroPassed"] for item in replay):
        return "SHUTTER_ZERO_IDENTITY"
    if not all(item["doseResponsePassed"] for item in moving):
        return "DOSE_RESPONSE"
    if len(static) != 1 or not static[0]["staticControlPassed"]:
        return "STATIC_NEGATIVE_CONTROL"
    expected_diagnostics = {(fixture["id"], kind) for fixture in spec["fixtures"] for kind in spec["diagnostics"]["mapsPerFixture"]}
    observed_diagnostics = {(item["fixtureId"], item["kind"]) for item in evidence["diagnostics"]}
    if len(evidence["diagnostics"]) != spec["diagnostics"]["pngCount"] or observed_diagnostics != expected_diagnostics or not all(item["identityMatch"] for item in evidence["diagnostics"]):
        return "DIAGNOSTIC_TOTALITY"
    if evidence["operationCounts"] != spec["operationBoundary"]:
        return "OPERATION_BOUNDARY"
    if evidence.get("evidenceCoreHash") != canonical_hash(hash_payload(evidence)):
        return "EVIDENCE_SELF_HASH"
    return None


def synthetic_valid_evidence(spec: dict) -> dict:
    source_runs, source_outputs, source_repeats = [], [], []
    pid = 1000
    for fixture, repeat in source_keys(spec):
        source_runs.append({"fixtureId": fixture, "repeat": repeat, "pid": pid, "exitCode": 0, "timedOut": False, "reportHashMatch": True, "fixtureMatch": True, "structureMatch": True, "animationApiMatch": True, "settingsMatch": True, "passStateMatch": True})
        source_outputs.append({"identityMatch": True, "partsExact": True, "finite": True})
        pid += 1
    for fixture in [item["id"] for item in spec["fixtures"]]:
        for part in EXPECTED_PARTS:
            source_repeats.append({"fixtureId": fixture, "part": part, "decodedExact": True})
    compositor_runs, compositor_outputs, compositor_repeats = [], [], []
    for fixture, shutter, repeat in compositor_keys(spec):
        compositor_runs.append({"fixtureId": fixture, "shutter": shutter, "repeat": repeat, "pid": pid, "exitCode": 0, "timedOut": False, "reportHashMatch": True, "inputMatch": True, "rnaMatch": True, "imageOutputs": EXPECTED_IMAGE_OUTPUTS, "vectorBlurInputs": EXPECTED_VECTOR_BLUR_INPUTS, "graphMatch": True, "graphLinks": EXPECTED_LINKS, "graphNodeCount": 3, "settingsMatch": True, "vectorBlurMatch": True})
        compositor_outputs.append({"identityMatch": True, "shape": [288, 512, 4], "channels": ["R", "G", "B", "A"], "subimages": 1, "finite": True})
        pid += 1
    for fixture in [item["id"] for item in spec["fixtures"]]:
        for shutter in spec["compositor"]["shutters"]:
            compositor_repeats.append({"fixtureId": fixture, "shutter": shutter, "decodedExact": True})

    def effect(shutter: float, value: float) -> dict:
        changed = 0 if value == 0.0 else 5000
        return {"shutter": shutter, "rgbAbsoluteError": {"p50": value / 4, "p95": value / 2, "p99": value / 2, "maximum": value, "rmse": value / 3, "finite": True}, "alphaAbsoluteErrorMaximum": 0.0, "changedPixelsAbove1Over65536": changed, "changedPixelsAbove1Over4096": changed, "decodedPixelSha256": "1" * 64}

    measurements = []
    for fixture in spec["fixtures"]:
        moving = fixture["id"] != "STATIC_CONTROL"
        if moving:
            values = {0.0: 0.0, 0.25: 0.15, 0.5: 0.30, 1.0: 0.60}
            vector = {"p50": 0.0, "p95": 16.0, "p99": 16.0, "maximum": 32.0, "rmse": 8.0, "finite": True, "pixelsAboveOne": 5000, "pixelsAbove1Over65536": 5000, "decodedPixelSha256": "0" * 64}
        else:
            values = {0.0: 0.0, 0.25: 0.0, 0.5: 0.0, 1.0: 0.0}
            vector = {"p50": 0.0, "p95": 0.0, "p99": 0.0, "maximum": 0.0, "rmse": 0.0, "finite": True, "pixelsAboveOne": 0, "pixelsAbove1Over65536": 0, "decodedPixelSha256": "0" * 64}
        measurements.append({"fixtureId": fixture["id"], "vectorMagnitudePixels": vector, "shutterEffects": [effect(shutter, values[shutter]) for shutter in (0.0, 0.25, 0.5, 1.0)]})
    diagnostics = [{"fixtureId": fixture["id"], "kind": kind, "identityMatch": True} for fixture in spec["fixtures"] for kind in spec["diagnostics"]["mapsPerFixture"]]
    evidence = {
        "schemaVersion": "test", "experimentId": "B52-D5", "specObservation": {"match": True},
        "parentObservations": [{"match": True} for _ in spec["parents"]],
        "runtimeObservations": {"blender": {"match": True}, "ocio": {"match": True}},
        "sourcePreObservations": [{"match": True} for _ in range(6)], "sourcePostObservations": [{"match": True} for _ in range(6)],
        "sourceRunObservations": source_runs, "sourceOutputObservations": source_outputs, "sourceRepeatComparisons": source_repeats,
        "compositorRunObservations": compositor_runs, "compositorOutputObservations": compositor_outputs, "compositorRepeatComparisons": compositor_repeats,
        "fixtureMeasurements": measurements, "diagnostics": diagnostics, "operationCounts": copy.deepcopy(spec["operationBoundary"]),
    }
    evidence["fixtureClassifications"] = replay_classification(evidence, spec)
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence))
    return evidence


def run_attacks(_formal_evidence: dict, spec: dict) -> list[dict]:
    base = synthetic_valid_evidence(spec)
    if validate(base, spec) is not None:
        raise RuntimeError("B52-D5 synthetic attack base is not valid")
    rows = []

    def add(identifier: str, reason: str, mutate, rehash: bool = True) -> None:
        clone = copy.deepcopy(base)
        mutate(clone)
        clone["evidenceCoreHash"] = canonical_hash(hash_payload(clone)) if rehash else "0" * 64
        observed = validate(clone, spec)
        rows.append({"id": identifier, "expectedReason": reason, "observedReason": observed, "passed": observed == reason, "base": "SYNTHETIC_VALID_CONTRACT"})

    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_BLENDER", "BLENDER_IDENTITY", lambda x: x["runtimeObservations"]["blender"].update(match=False))
    add("A03_OCIO", "OCIO_IDENTITY", lambda x: x["runtimeObservations"]["ocio"].update(match=False))
    add("A04_FIXTURE_ROSTER", "FIXTURE_ROSTER", lambda x: x["sourceRunObservations"].pop())
    add("A05_FIXTURE_STRUCTURE", "FIXTURE_STRUCTURE", lambda x: x["sourceRunObservations"][0].update(structureMatch=False))
    add("A06_ANIMATION_API", "BLENDER52_ANIMATION_API", lambda x: x["sourceRunObservations"][0].update(animationApiMatch=False))
    add("A07_SOURCE_PROCESS", "SOURCE_PROCESS_ROSTER", lambda x: x["sourceRunObservations"][1].update(pid=x["sourceRunObservations"][0]["pid"]))
    add("A08_SOURCE_PASS", "SOURCE_PASS_TOTALITY", lambda x: x["sourceOutputObservations"][0].update(partsExact=False))
    add("A09_SOURCE_REPEAT", "SOURCE_REPEAT_IDENTITY", lambda x: x["sourceRepeatComparisons"][0].update(decodedExact=False))
    add("A10_GRAPH", "COMPOSITOR_GRAPH_CONTRACT", lambda x: x["compositorRunObservations"][0].update(graphMatch=False))
    add("A11_COMPOSITOR_PROCESS", "COMPOSITOR_PROCESS_ROSTER", lambda x: x["compositorRunObservations"][1].update(pid=x["compositorRunObservations"][0]["pid"]))
    add("A12_COMPOSITOR_OUTPUT", "COMPOSITOR_OUTPUT_TOTALITY", lambda x: x["compositorOutputObservations"][0].update(finite=False))
    add("A13_COMPOSITOR_REPEAT", "COMPOSITOR_REPEAT_IDENTITY", lambda x: x["compositorRepeatComparisons"][0].update(decodedExact=False))

    def break_moving(x: dict) -> None:
        x["fixtureMeasurements"][0]["vectorMagnitudePixels"]["maximum"] = 0.0
        x["fixtureClassifications"] = replay_classification(x, spec)
    add("A14_MOVING", "MOVING_TASK_SENSITIVITY", break_moving)

    def break_zero(x: dict) -> None:
        item = x["fixtureMeasurements"][0]["shutterEffects"][0]
        item["rgbAbsoluteError"]["maximum"] = 0.1
        item["changedPixelsAbove1Over65536"] = 1
        x["fixtureClassifications"] = replay_classification(x, spec)
    add("A15_SHUTTER_ZERO", "SHUTTER_ZERO_IDENTITY", break_zero)

    def break_dose(x: dict) -> None:
        x["fixtureMeasurements"][0]["shutterEffects"][3]["rgbAbsoluteError"]["rmse"] = 0.05
        x["fixtureClassifications"] = replay_classification(x, spec)
    add("A16_DOSE", "DOSE_RESPONSE", break_dose)

    def break_static(x: dict) -> None:
        x["fixtureMeasurements"][2]["vectorMagnitudePixels"]["maximum"] = 1.0
        x["fixtureClassifications"] = replay_classification(x, spec)
    add("A17_STATIC", "STATIC_NEGATIVE_CONTROL", break_static)
    add("A18_DIAGNOSTIC", "DIAGNOSTIC_TOTALITY", lambda x: x["diagnostics"][0].update(identityMatch=False))
    add("A19_OPERATION", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(modelCalls=1))
    add("A20_HASH", "EVIDENCE_SELF_HASH", lambda x: None, rehash=False)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.spec.resolve().parent.parent
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    expected_preregistration = {"commit": PREREGISTRATION_COMMIT, "specUri": "specs/controlled-motion-vector-blur-calibration.v0.1.json", "specSha256": SPEC_SHA256}
    if sha256_file(args.spec) != SPEC_SHA256 or receipt.get("preregistration") != expected_preregistration:
        raise RuntimeError("B52-D5 preregistration identity differs")

    fixtures = {item["id"]: item for item in spec["fixtures"]}
    source_run_observations, source_output_observations, sources = [], [], {}
    for run in receipt["sourceRuns"]:
        report = run.get("report")
        body = {key: value for key, value in report.items() if key != "reportHash"} if isinstance(report, dict) else {}
        report_hash_match = bool(report and report.get("reportHash") == canonical_hash(body))
        fixture = fixtures[run["fixtureId"]]
        structure = report.get("fixtureStructure") if report else None
        expected_structure = expected_fixture_structure(spec, fixture)
        structure_match = structure == expected_structure
        expected_action = expected_structure["moverAction"] or expected_structure["cameraAction"]
        observed_action = (structure or {}).get("moverAction", []) or (structure or {}).get("cameraAction", [])
        animation_api_match = observed_action == expected_action and all(key in row for row in observed_action for key in ("layerIndex", "stripIndex", "channelBagIndex", "dataPath", "arrayIndex", "keyframes"))
        source_run_observations.append({
            "fixtureId": run["fixtureId"], "repeat": run["repeat"], "pid": run["pid"], "exitCode": run["exitCode"], "timedOut": run["timedOut"],
            "reportHashMatch": report_hash_match, "fixtureMatch": bool(report and report.get("fixture") == fixture),
            "structureMatch": structure_match, "animationApiMatch": animation_api_match,
            "settingsMatch": bool(report and report.get("runtime") == {
                "engine": spec["sourceRender"]["engine"], "device": spec["sourceRender"]["device"], "samples": spec["sourceRender"]["samples"],
                "seed": spec["sourceRender"]["seed"], "animatedSeed": spec["sourceRender"]["animatedSeed"],
                "adaptiveSampling": spec["sourceRender"]["adaptiveSampling"], "denoising": spec["sourceRender"]["denoising"],
                "motionBlur": spec["sourceRender"]["motionBlur"], "persistentData": spec["sourceRender"]["persistentData"],
                "threadsMode": spec["sourceRender"]["threadsMode"], "threads": spec["sourceRender"]["threads"],
            }),
            "passStateMatch": bool(report and report.get("passState") == {
                "viewLayer": "BFS_MASTER", "Combined": True, "Depth": True, "Normal": True, "Vector": True,
                "CryptoObject": True, "cryptomatteDepth": 6, "sampleCount": True,
            }),
        })
        output_path = root / report["output"]["uri"]
        loaded = load_multipart_exr(output_path)
        sources[(run["fixtureId"], run["repeat"])] = loaded
        observed_sha, observed_bytes = sha256_file(output_path), output_path.stat().st_size
        source_output_observations.append({
            "fixtureId": run["fixtureId"], "repeat": run["repeat"], "uri": report["output"]["uri"],
            "expectedSha256": report["output"]["sha256"], "observedSha256": observed_sha,
            "expectedBytes": report["output"]["bytes"], "observedBytes": observed_bytes,
            "identityMatch": observed_sha == report["output"]["sha256"] and observed_bytes == report["output"]["bytes"],
            "parts": sorted(loaded["roster"]), "partsExact": sorted(loaded["roster"]) == EXPECTED_PARTS,
            "finite": bool(all(np.isfinite(value).all() for value in loaded["parts"].values())),
            "partPixelSha256": {name: array_hash(value) for name, value in sorted(loaded["parts"].items())},
        })

    source_repeat_comparisons = []
    for fixture in fixtures:
        for part in EXPECTED_PARTS:
            left, right = sources[(fixture, 1)]["parts"][part], sources[(fixture, 2)]["parts"][part]
            source_repeat_comparisons.append({"fixtureId": fixture, "part": part, "leftPixelSha256": array_hash(left), "rightPixelSha256": array_hash(right), "decodedExact": bool(left.shape == right.shape and np.array_equal(left, right))})

    compositor_run_observations, compositor_output_observations, outputs = [], [], {}
    source_sha_by_key = {(item["fixtureId"], item["repeat"]): item["observedSha256"] for item in source_output_observations}
    for run in receipt["compositorRuns"]:
        report = run.get("report")
        body = {key: value for key, value in report.items() if key != "reportHash"} if isinstance(report, dict) else {}
        report_hash_match = bool(report and report.get("reportHash") == canonical_hash(body))
        expected_source_sha = source_sha_by_key[(run["fixtureId"], run["repeat"])]
        input_match = bool(report and report["input"]["sha256"] == expected_source_sha and report["sourcePostSha256"] == expected_source_sha and report["input"]["imagePass"] == "Combined" and report["input"]["speedPass"] == "Vector" and report["input"]["depthPass"] == "Depth")
        compositor_run_observations.append({
            "fixtureId": run["fixtureId"], "shutter": float(run["shutter"]), "repeat": run["repeat"], "pid": run["pid"], "exitCode": run["exitCode"], "timedOut": run["timedOut"],
            "reportHashMatch": report_hash_match, "inputMatch": input_match,
            "rnaMatch": bool(report and report["rna"]["match"]), "imageOutputs": report["rna"]["imageOutputs"] if report else None,
            "vectorBlurInputs": report["rna"]["vectorBlurInputs"] if report else None,
            "graphMatch": bool(report and report["graph"]["match"]), "graphLinks": report["graph"]["links"] if report else None,
            "graphNodeCount": report["graph"]["nodeCount"] if report else None,
            "settingsMatch": bool(report and report.get("runtime") == {"engine": "BLENDER_WORKBENCH", "compositorDevice": spec["compositor"]["device"], "threadsMode": spec["compositor"]["threadsMode"], "threads": spec["compositor"]["threads"]}),
            "vectorBlurMatch": bool(report and report.get("vectorBlur") == {"Samples": spec["compositor"]["samples"], "Shutter": float(run["shutter"])}),
        })
        output_path = root / report["output"]["uri"]
        loaded = load_single_exr(output_path)
        outputs[(run["fixtureId"], float(run["shutter"]), run["repeat"])] = loaded
        observed_sha, observed_bytes = sha256_file(output_path), output_path.stat().st_size
        compositor_output_observations.append({
            "fixtureId": run["fixtureId"], "shutter": float(run["shutter"]), "repeat": run["repeat"], "uri": report["output"]["uri"],
            "expectedSha256": report["output"]["sha256"], "observedSha256": observed_sha,
            "expectedBytes": report["output"]["bytes"], "observedBytes": observed_bytes,
            "identityMatch": observed_sha == report["output"]["sha256"] and observed_bytes == report["output"]["bytes"],
            "shape": list(loaded["pixels"].shape), "channels": loaded["channels"], "subimages": loaded["subimages"],
            "finite": bool(np.isfinite(loaded["pixels"]).all()), "decodedPixelSha256": array_hash(loaded["pixels"]),
        })

    compositor_repeat_comparisons = []
    for fixture in fixtures:
        for shutter in spec["compositor"]["shutters"]:
            left, right = outputs[(fixture, float(shutter), 1)]["pixels"], outputs[(fixture, float(shutter), 2)]["pixels"]
            compositor_repeat_comparisons.append({"fixtureId": fixture, "shutter": float(shutter), "leftPixelSha256": array_hash(left), "rightPixelSha256": array_hash(right), "decodedExact": bool(left.shape == right.shape and np.array_equal(left, right))})

    fixture_measurements, diagnostics = [], []
    diagnostics_directory = args.output.parent / "diagnostics"
    diagnostics_directory.mkdir(parents=True, exist_ok=False)
    canonical_diagnostics_directory = f"{spec['outputRoot']}/diagnostics"
    for fixture in fixtures:
        source = sources[(fixture, 1)]
        fixture_outputs = {float(shutter): outputs[(fixture, float(shutter), 1)]["pixels"] for shutter in spec["compositor"]["shutters"]}
        measurement, maps = measure_fixture(source, fixture_outputs, fixture)
        fixture_measurements.append(measurement)
        sources_binding = {
            "source": next({"uri": item["uri"], "sha256": item["observedSha256"]} for item in source_output_observations if item["fixtureId"] == fixture and item["repeat"] == 1),
            "shutterHalfOutput": next({"uri": item["uri"], "sha256": item["observedSha256"]} for item in compositor_output_observations if item["fixtureId"] == fixture and item["shutter"] == 0.5 and item["repeat"] == 1),
        }
        for kind in spec["diagnostics"]["mapsPerFixture"]:
            diagnostics.append(write_diagnostic(diagnostics_directory, canonical_diagnostics_directory, fixture, kind, maps[kind], spec["diagnostics"]["mappings"][kind], sources_binding))

    source_report_operations = [run["report"]["operationCounts"] for run in receipt["sourceRuns"]]
    compositor_report_operations = [run["report"]["operationCounts"] for run in receipt["compositorRuns"]]
    operation_counts = {
        "blenderProcesses": len(receipt["sourceRuns"]) + len(receipt["compositorRuns"]),
        "blenderRenderCalls": sum(item["blenderRenderCalls"] for item in source_report_operations + compositor_report_operations),
        "cyclesRayRenders": sum(item["cyclesRayRenders"] for item in source_report_operations + compositor_report_operations),
        "sourceMultipartExrsWritten": len(source_output_observations),
        "compositorRgbaExrsWritten": len(compositor_output_observations),
        "sourceDecodedPassPairsCompared": len(source_repeat_comparisons),
        "compositorDecodedPairsCompared": len(compositor_repeat_comparisons),
        "diagnosticPngsWritten": len(diagnostics),
        "sourceBlendFilesOpened": sum(item["sourceBlendFilesOpened"] for item in source_report_operations + compositor_report_operations),
        "sourceBlendFilesModified": 0,
        "externalAssetsOpened": sum(item["externalAssetsOpened"] for item in source_report_operations + compositor_report_operations),
        "networkCalls": 0,
        "modelCalls": 0,
        "videoModelCalls": 0,
        "adaptiveCandidatesEvaluated": 0,
    }
    evidence = {
        "schemaVersion": "bfs.controlledMotionVectorBlurCalibrationEvidence.v0.1", "experimentId": spec["experimentId"],
        "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["toolFreezeCommit"], "tools": receipt["tools"],
        "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "specObservation": receipt["specObservation"], "parentObservations": receipt["parentObservations"], "runtimeObservations": receipt["runtimeObservations"],
        "sourcePreObservations": receipt["sourcePreObservations"], "sourcePostObservations": receipt["sourcePostObservations"],
        "sourceRunObservations": source_run_observations, "sourceOutputObservations": source_output_observations, "sourceRepeatComparisons": source_repeat_comparisons,
        "compositorRunObservations": compositor_run_observations, "compositorOutputObservations": compositor_output_observations, "compositorRepeatComparisons": compositor_repeat_comparisons,
        "fixtureMeasurements": fixture_measurements, "diagnostics": diagnostics, "operationCounts": operation_counts,
        "nonClaims": spec["nonClaims"], "auditSemantics": "Evidence integrity may PASS independently of the supported/invalid scientific verdict.",
    }
    evidence["fixtureClassifications"] = replay_classification(evidence, spec)
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence))
    evidence["baseFailure"] = validate(evidence, spec)
    evidence["attacks"] = run_attacks(evidence, spec)
    evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"])
    evidence["verdict"] = spec["decisionRule"]["supportedVerdict"] if evidence["baseFailure"] is None and evidence["attacksPassed"] == len(spec["attacks"]) else spec["decisionRule"]["invalidVerdict"]
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D5_RESULT verdict={evidence['verdict']} attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={evidence['baseFailure'] or 'none'}", flush=True)


if __name__ == "__main__":
    main()
