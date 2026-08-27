#!/usr/bin/env python3
"""Derive B52-D3 task semantics from the frozen B52-D2 EXRs without rendering."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import platform
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


PREREGISTRATION_COMMIT = "51b5033cc76a95638c68b45a8015347863c73a73"
SPEC_SHA256 = "88f9284e014a5c4020aed374eef306cf22ed1c1badf5e680d93a919038526b7d"
EXPECTED_ROSTER = [
    "BFS_MASTER.Combined",
    "BFS_MASTER.Depth",
    "BFS_MASTER.Normal",
    "BFS_MASTER.Vector",
    "BFS_MASTER.Debug Sample Count",
    "BFS_MASTER.CryptoObject00",
    "BFS_MASTER.CryptoObject01",
    "BFS_MASTER.CryptoObject02",
]


def load_analysis_library(root: Path):
    path = root / "scripts/analyze-b52-native-cpu-adaptive-quality-cost.py"
    module_spec = importlib.util.spec_from_file_location("bfs_b52_analysis_library", path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("cannot load B52 analysis library")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


def array_hash(values: np.ndarray, dtype: str = "<f4") -> str:
    return hashlib.sha256(np.ascontiguousarray(values, dtype=dtype).tobytes()).hexdigest()


def mask_hash(values: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(values, dtype=np.uint8).tobytes()).hexdigest()


def percentile(values: np.ndarray, quantile: float) -> float | None:
    return float(np.quantile(values, quantile, method="higher")) if values.size else None


def finite_stats(values: np.ndarray, prefix: str) -> dict:
    flat = np.asarray(values, dtype=np.float64).reshape(-1)
    if not flat.size or not np.isfinite(flat).all():
        return {f"{prefix}P50": None, f"{prefix}P95": None, f"{prefix}P99": None, f"{prefix}Maximum": None, f"{prefix}Rmse": None}
    return {
        f"{prefix}P50": percentile(flat, 0.50),
        f"{prefix}P95": percentile(flat, 0.95),
        f"{prefix}P99": percentile(flat, 0.99),
        f"{prefix}Maximum": float(np.max(flat)),
        f"{prefix}Rmse": float(np.sqrt(np.mean(np.square(flat, dtype=np.float64)))),
    }


def mark_pair_boundaries(mask: np.ndarray, condition: np.ndarray, axis: int) -> None:
    if axis == 1:
        mask[:, :-1] |= condition
        mask[:, 1:] |= condition
    else:
        mask[:-1, :] |= condition
        mask[1:, :] |= condition


def chebyshev_dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius < 0:
        raise ValueError("negative dilation radius")
    result = np.zeros_like(mask, dtype=bool)
    height, width = mask.shape
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            src_y0, src_y1 = max(0, -dy), min(height, height - dy)
            src_x0, src_x1 = max(0, -dx), min(width, width - dx)
            dst_y0, dst_y1 = max(0, dy), min(height, height + dy)
            dst_x0, dst_x1 = max(0, dx), min(width, width + dx)
            result[dst_y0:dst_y1, dst_x0:dst_x1] |= mask[src_y0:src_y1, src_x0:src_x1]
    return result


def derive_region(baseline_loaded: dict, baseline_crypto: dict, spec: dict) -> tuple[dict, dict[str, np.ndarray]]:
    depth = baseline_loaded["parts"]["BFS_MASTER.Depth"][..., 0]
    foreground = np.isfinite(depth) & (depth < float(spec["regionContract"]["depthForegroundThreshold"]))
    dominant_ids = baseline_crypto["ids"][..., 0]
    dominant_coverage = baseline_crypto["coverage"][..., 0]
    seeds = np.zeros(foreground.shape, dtype=bool)
    horizontal = foreground[:, :-1] & foreground[:, 1:] & (dominant_ids[:, :-1] != dominant_ids[:, 1:])
    vertical = foreground[:-1, :] & foreground[1:, :] & (dominant_ids[:-1, :] != dominant_ids[1:, :])
    mark_pair_boundaries(seeds, horizontal, 1)
    mark_pair_boundaries(seeds, vertical, 0)
    visible_names = []
    for name in sorted(baseline_crypto["mattes"]):
        matte = baseline_crypto["mattes"][name]
        if np.any(matte > 0.0):
            visible_names.append(name)
            seeds |= (matte > 0.0) & (matte < 1.0)
    boundary = chebyshev_dilate(seeds, int(spec["regionContract"]["dilation"]["radiusPixels"]))
    confident = dominant_coverage >= float(spec["regionContract"]["confidentDominantCoverage"])
    stable = foreground & confident & ~boundary
    arrays = {"foreground": foreground, "boundarySeed": seeds, "boundary": boundary, "stableInterior": stable, "confident": confident}
    record = {
        "dimensions": [int(foreground.shape[1]), int(foreground.shape[0])],
        "visibleObjectNames": visible_names,
        "visibleObjectCount": len(visible_names),
        "foregroundPixelCount": int(np.count_nonzero(foreground)),
        "confidentDominantPixelCount": int(np.count_nonzero(foreground & confident)),
        "boundarySeedPixelCount": int(np.count_nonzero(seeds)),
        "boundaryPixelCount": int(np.count_nonzero(boundary)),
        "stableInteriorPixelCount": int(np.count_nonzero(stable)),
        "maskSha256": {name: mask_hash(value) for name, value in arrays.items() if name != "confident"},
    }
    return record, arrays


def localization(changed: np.ndarray, boundary: np.ndarray) -> tuple[int, int, float]:
    count = int(np.count_nonzero(changed))
    inside = int(np.count_nonzero(changed & boundary))
    return count, inside, 1.0 if count == 0 else inside / count


def measure_cryptomatte(baseline: dict, candidate: dict, region: dict[str, np.ndarray], spec: dict, hard_threshold: float) -> tuple[dict, np.ndarray]:
    gate = spec["cryptomatteTask"]["derivationClassifier"]
    stable = region["stableInterior"]
    boundary = region["boundary"]
    confident_mismatch = int(np.count_nonzero(stable & (baseline["ids"][..., 0] != candidate["ids"][..., 0])))
    objects = []
    max_error_map = np.zeros(stable.shape, dtype=np.float64)
    for name in sorted(baseline["mattes"]):
        baseline_matte = baseline["mattes"][name]
        if not np.any(baseline_matte > 0.0):
            continue
        candidate_matte = candidate["mattes"][name]
        absolute = np.abs(candidate_matte.astype(np.float64) - baseline_matte.astype(np.float64))
        max_error_map = np.maximum(max_error_map, absolute)
        hard = (candidate_matte >= hard_threshold) != (baseline_matte >= hard_threshold)
        changed_count, changed_inside, changed_fraction = localization(absolute > 0.0, boundary)
        alpha = finite_stats(absolute, "alphaAbsoluteError")
        composites = []
        for foreground in spec["cryptomatteTask"]["unitContrastComposite"]["foregrounds"]:
            foreground_array = np.asarray(foreground, dtype=np.float64)
            background_array = np.asarray(spec["cryptomatteTask"]["unitContrastComposite"]["background"], dtype=np.float64)
            baseline_rgb = baseline_matte[..., None] * foreground_array + (1.0 - baseline_matte[..., None]) * background_array
            candidate_rgb = candidate_matte[..., None] * foreground_array + (1.0 - candidate_matte[..., None]) * background_array
            rgb_absolute = np.abs(candidate_rgb - baseline_rgb)
            rgb = finite_stats(rgb_absolute, "rgbAbsoluteError")
            composites.append({"foreground": foreground, "background": spec["cryptomatteTask"]["unitContrastComposite"]["background"], **rgb})
        object_pass = (
            int(np.count_nonzero(hard & stable)) == gate["stableInteriorHardMatteMismatchPixels"]
            and changed_fraction >= gate["minimumChangedAlphaBoundaryLocalizationFraction"]
            and all(item["rgbAbsoluteErrorP99"] is not None and item["rgbAbsoluteErrorP99"] <= gate["unitContrastCompositeP99Maximum"] for item in composites)
            and all(item["rgbAbsoluteErrorMaximum"] is not None and item["rgbAbsoluteErrorMaximum"] <= gate["unitContrastCompositeAbsoluteMaximum"] for item in composites)
        )
        objects.append({
            "name": name,
            "hardMatteMismatchPixels": int(np.count_nonzero(hard)),
            "hardMatteMismatchPixelsInsideBoundary": int(np.count_nonzero(hard & boundary)),
            "hardMatteMismatchPixelsStableInterior": int(np.count_nonzero(hard & stable)),
            **alpha,
            "changedAlphaPixelCount": changed_count,
            "changedAlphaInsideBoundaryPixelCount": changed_inside,
            "changedAlphaBoundaryLocalizationFraction": changed_fraction,
            "unitContrastComposites": composites,
            "classifierPassed": object_pass,
        })
    passed = bool(objects) and confident_mismatch == gate["stableInteriorConfidentDominantIdMismatchPixels"] and all(item["classifierPassed"] for item in objects)
    return {
        "hardMatteThreshold": hard_threshold,
        "visibleObjectCount": len(objects),
        "stableInteriorConfidentDominantIdMismatchPixels": confident_mismatch,
        "objects": objects,
        "classifierPassed": passed,
        "measurementTotal": bool(objects) and all(all(value is not None and math.isfinite(value) for key, value in item.items() if key.startswith("alphaAbsoluteError")) for item in objects),
    }, max_error_map


def normalized_vectors(values: np.ndarray, epsilon: float) -> tuple[np.ndarray, np.ndarray]:
    vectors = values.astype(np.float64)
    norms = np.linalg.norm(vectors, axis=-1)
    valid = np.isfinite(vectors).all(axis=-1) & (norms > epsilon)
    normalized = np.zeros_like(vectors)
    normalized[valid] = vectors[valid] / norms[valid, None]
    return normalized, valid


def measure_normal(baseline: np.ndarray, candidate: np.ndarray, region: dict[str, np.ndarray], spec: dict) -> tuple[dict, np.ndarray]:
    epsilon = float(spec["normalTask"]["normalizationEpsilon"])
    gate = spec["normalTask"]["derivationClassifier"]
    baseline_n, baseline_valid = normalized_vectors(baseline[..., :3], epsilon)
    candidate_n, candidate_valid = normalized_vectors(candidate[..., :3], epsilon)
    stable = region["stableInterior"]
    both = stable & baseline_valid & candidate_valid
    mask_mismatch = stable & (baseline_valid != candidate_valid)
    cosine = np.clip(np.sum(baseline_n * candidate_n, axis=-1), -1.0, 1.0)
    angle_map = np.zeros(stable.shape, dtype=np.float64)
    angle_map[baseline_valid & candidate_valid] = np.degrees(np.arccos(cosine[baseline_valid & candidate_valid]))
    angles = angle_map[both]
    angle = finite_stats(angles, "angularErrorDegrees")
    changed = np.any(baseline[..., :3] != candidate[..., :3], axis=-1)
    changed_count, changed_inside, changed_fraction = localization(changed, region["boundary"])
    probes = []
    for direction in spec["normalTask"]["lambertianProbeDirections"]:
        light = np.asarray(direction, dtype=np.float64)
        baseline_response = np.maximum(np.sum(baseline_n * light, axis=-1), 0.0)
        candidate_response = np.maximum(np.sum(candidate_n * light, axis=-1), 0.0)
        absolute = np.abs(candidate_response[both] - baseline_response[both])
        probes.append({"direction": direction, **finite_stats(absolute, "absoluteError")})
    passed = (
        int(np.count_nonzero(mask_mismatch)) == gate["validVectorMaskMismatchPixels"]
        and angle["angularErrorDegreesP99"] is not None and angle["angularErrorDegreesP99"] <= gate["angularErrorDegreesP99Maximum"]
        and angle["angularErrorDegreesMaximum"] is not None and angle["angularErrorDegreesMaximum"] <= gate["angularErrorDegreesAbsoluteMaximum"]
        and all(item["absoluteErrorP99"] is not None and item["absoluteErrorP99"] <= gate["lambertianAbsoluteErrorP99Maximum"] for item in probes)
        and all(item["absoluteErrorMaximum"] is not None and item["absoluteErrorMaximum"] <= gate["lambertianAbsoluteErrorMaximum"] for item in probes)
        and changed_fraction >= gate["minimumChangedNormalBoundaryLocalizationFraction"]
    )
    return {
        "stableInteriorBothValidPixelCount": int(np.count_nonzero(both)),
        "validVectorMaskMismatchPixels": int(np.count_nonzero(mask_mismatch)),
        **angle,
        "changedNormalPixelCount": changed_count,
        "changedNormalInsideBoundaryPixelCount": changed_inside,
        "changedNormalBoundaryLocalizationFraction": changed_fraction,
        "lambertianProbes": probes,
        "classifierPassed": passed,
        "measurementTotal": bool(angles.size) and np.isfinite(angles).all() and all(item["absoluteErrorP99"] is not None for item in probes),
    }, angle_map


def measure_vector(baseline: np.ndarray, candidate: np.ndarray, region: dict[str, np.ndarray], spec: dict) -> tuple[dict, np.ndarray]:
    epsilon = float(spec["vectorTask"]["nonzeroEpsilon"])
    gate = spec["vectorTask"]["derivationClassifier"]
    stable = region["stableInterior"]
    pairs = []
    error_maps = []
    support_union = np.zeros(stable.shape, dtype=bool)
    for pair_name, indices in (("pairA", (0, 1)), ("pairB", (2, 3))):
        baseline_pair = baseline[..., indices].astype(np.float64)
        candidate_pair = candidate[..., indices].astype(np.float64)
        baseline_support = np.linalg.norm(baseline_pair, axis=-1) > epsilon
        candidate_support = np.linalg.norm(candidate_pair, axis=-1) > epsilon
        mismatch = stable & (baseline_support != candidate_support)
        support_union |= mismatch
        error_map = np.linalg.norm(candidate_pair - baseline_pair, axis=-1)
        error_maps.append(error_map)
        pairs.append({
            "pair": pair_name,
            "channels": list(spec["vectorTask"]["pairing"][pair_name]),
            "stableInteriorNonzeroSupportMismatchPixels": int(np.count_nonzero(mismatch)),
            **finite_stats(error_map[stable], "endpointError"),
        })
    changed = np.any(baseline[..., :4] != candidate[..., :4], axis=-1)
    changed_count, changed_inside, changed_fraction = localization(changed, region["boundary"])
    passed = (
        int(np.count_nonzero(support_union)) == gate["stableInteriorNonzeroSupportMismatchPixels"]
        and all(item["endpointErrorP99"] is not None and item["endpointErrorP99"] <= gate["pairEndpointErrorP99Maximum"] for item in pairs)
        and all(item["endpointErrorMaximum"] is not None and item["endpointErrorMaximum"] <= gate["pairEndpointErrorAbsoluteMaximum"] for item in pairs)
        and changed_fraction >= gate["minimumChangedVectorBoundaryLocalizationFraction"]
    )
    return {
        "stableInteriorNonzeroSupportMismatchPixels": int(np.count_nonzero(support_union)),
        "pairs": pairs,
        "changedVectorPixelCount": changed_count,
        "changedVectorInsideBoundaryPixelCount": changed_inside,
        "changedVectorBoundaryLocalizationFraction": changed_fraction,
        "classifierPassed": passed,
        "measurementTotal": int(np.count_nonzero(stable)) > 0 and all(item["endpointErrorP99"] is not None for item in pairs),
    }, np.maximum(error_maps[0], error_maps[1])


def write_png(path: Path, pixels: np.ndarray) -> None:
    array = np.ascontiguousarray(pixels, dtype=np.uint8)
    height, width, channels = array.shape
    output = oiio.ImageOutput.create(str(path))
    if output is None:
        raise RuntimeError(f"cannot create PNG output: {path}")
    image_spec = oiio.ImageSpec(width, height, channels, oiio.UINT8)
    image_spec.channelnames = ["R", "G", "B"]
    if not output.open(str(path), image_spec):
        raise RuntimeError(output.geterror())
    if not output.write_image(array):
        raise RuntimeError(output.geterror())
    output.close()


def diagnostic_name(variant_id: str, profile_id: str, kind: str) -> str:
    return f"{variant_id.lower()}--{profile_id.lower()}--{kind}.png"


def write_diagnostic(
    output_directory: Path,
    canonical_directory: str,
    variant_id: str,
    profile_id: str,
    kind: str,
    values: np.ndarray,
    mapping: dict,
    baseline_identity: dict,
    candidate_identity: dict,
) -> dict:
    minimum = float(mapping["minimum"])
    maximum = float(mapping["clipMaximum"])
    normalized = np.clip((values.astype(np.float64) - minimum) / (maximum - minimum), 0.0, 1.0)
    rgb = np.stack([normalized, np.square(normalized), np.zeros_like(normalized)], axis=-1)
    encoded = np.rint(rgb * 255.0).astype(np.uint8)
    filename = diagnostic_name(variant_id, profile_id, kind)
    png_path = output_directory / filename
    sidecar_path = png_path.with_suffix(".json")
    write_png(png_path, encoded)
    reopened = oiio.ImageBuf(str(png_path))
    if not reopened.initialized:
        raise RuntimeError(reopened.geterror() or f"cannot reopen {png_path}")
    reopened_pixels = np.ascontiguousarray(np.asarray(reopened.get_pixels(oiio.UINT8), dtype=np.uint8))
    if reopened_pixels.shape != encoded.shape or not np.array_equal(reopened_pixels, encoded):
        raise RuntimeError(f"diagnostic PNG decoded mismatch: {png_path}")
    value_sha = array_hash(values)
    png_sha = sha256_file(png_path)
    sidecar = {
        "schemaVersion": "bfs.adaptivePayloadDiagnostic.v0.1",
        "experimentId": "B52-D3",
        "variantId": variant_id,
        "profileId": profile_id,
        "kind": kind,
        "mapping": mapping,
        "encoding": {"normalization": "t = clip((value - minimum) / (clipMaximum - minimum), 0, 1)", "rgb": ["R = t", "G = t * t", "B = 0"], "quantization": "round-to-nearest uint8 after multiplication by 255", "fileFormat": "PNG RGB8"},
        "dimensions": [int(values.shape[1]), int(values.shape[0])],
        "decodedValueSha256": value_sha,
        "decodedRgb8Sha256": hashlib.sha256(encoded.tobytes()).hexdigest(),
        "baselineArtifact": baseline_identity,
        "candidateArtifact": candidate_identity,
        "png": {"uri": f"{canonical_directory}/{filename}", "sha256": png_sha, "bytes": png_path.stat().st_size},
    }
    sidecar_path.write_bytes(canonical_bytes(sidecar))
    return {
        "variantId": variant_id,
        "profileId": profile_id,
        "kind": kind,
        "mapping": mapping,
        "decodedValueSha256": value_sha,
        "decodedRgb8Sha256": sidecar["decodedRgb8Sha256"],
        "png": sidecar["png"],
        "sidecar": {"uri": f"{canonical_directory}/{sidecar_path.name}", "sha256": sha256_file(sidecar_path), "bytes": sidecar_path.stat().st_size},
        "identityMatch": True,
    }


def expected_pair_keys(spec: dict) -> list[tuple[str, str]]:
    return [(profile_id, variant_id) for profile_id in spec["inputs"]["candidateProfiles"] for variant_id in spec["inputs"]["variants"]]


def replay_classification(evidence: dict, spec: dict) -> tuple[list[dict], list[str]]:
    by_key = {(item["profileId"], item["variantId"]): item for item in evidence["candidateMeasurements"]}
    summaries = []
    selected = []
    for profile_id in spec["inputs"]["candidateProfiles"]:
        rows = [by_key.get((profile_id, variant_id)) for variant_id in spec["inputs"]["variants"]]
        variant_rows = []
        for variant_id, row in zip(spec["inputs"]["variants"], rows, strict=True):
            variant_rows.append({
                "variantId": variant_id,
                "cryptomatteClassifierPassed": bool(row and row["cryptomatte"]["classifierPassed"]),
                "normalClassifierPassed": bool(row and row["normal"]["classifierPassed"]),
                "vectorClassifierPassed": bool(row and row["vector"]["classifierPassed"]),
                "allTaskClassifiersPassed": bool(row and row["allTaskClassifiersPassed"]),
            })
        candidate = len(rows) == len(spec["inputs"]["variants"]) and all(item["allTaskClassifiersPassed"] for item in variant_rows)
        summaries.append({"profileId": profile_id, "variants": variant_rows, "futureHoldoutCandidate": candidate})
        if candidate:
            selected.append(profile_id)
    return summaries, selected


def hash_payload(evidence: dict) -> dict:
    excluded = {"evidenceCoreHash", "baseFailure", "attacks", "attacksPassed", "verdict"}
    return {key: value for key, value in evidence.items() if key not in excluded}


def finite_measurement_tree(value: object) -> bool:
    if isinstance(value, dict):
        return all(finite_measurement_tree(item) for item in value.values())
    if isinstance(value, list):
        return all(finite_measurement_tree(item) for item in value)
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def validate(evidence: dict, spec: dict, analysis_library) -> str | None:
    expected_keys = expected_pair_keys(spec)
    if not evidence["specObservation"]["match"] or not all(item["match"] for item in evidence["parentObservations"]):
        return "PARENT_IDENTITY"
    expected_runs = 54
    if len(evidence["artifactObservations"]) != expected_runs or not all(item["match"] for item in evidence["artifactObservations"]):
        return "ARTIFACT_IDENTITY"
    if len(evidence["runObservations"]) != expected_runs or not all(item["roster"] == EXPECTED_ROSTER and item["allPartsFinite"] for item in evidence["runObservations"]):
        return "PASS_ROSTER"
    repeat_keys = {(item["profileId"], item["variantId"]) for item in evidence["repeatComparisons"]}
    expected_repeat_keys = {(profile, variant) for profile in [spec["inputs"]["baselineProfile"], *spec["inputs"]["candidateProfiles"]] for variant in spec["inputs"]["variants"]}
    if repeat_keys != expected_repeat_keys or len(evidence["repeatComparisons"]) != 18 or not all(item["allThreeRepeatsExact"] for item in evidence["repeatComparisons"]):
        return "REPEAT_IDENTITY"
    if len(evidence["manifestObservations"]) != expected_runs or not all(item["metadataValid"] and item["manifestMatch"] and item["structuralValid"] for item in evidence["manifestObservations"]):
        return "CRYPTOMATTE_MANIFEST"
    if len(evidence["regions"]) != 2 or {item["variantId"] for item in evidence["regions"]} != set(spec["inputs"]["variants"]):
        return "REGION_TOTALITY"
    if not all(item["foregroundPixelCount"] > 0 and item["boundaryPixelCount"] > 0 and item["stableInteriorPixelCount"] > 0 and set(item["maskSha256"]) == {"foreground", "boundarySeed", "boundary", "stableInterior"} for item in evidence["regions"]):
        return "REGION_TOTALITY"
    measurements = evidence["candidateMeasurements"]
    if len(measurements) != 16 or [(item["profileId"], item["variantId"]) for item in measurements] != expected_keys:
        return "CRYPTOMATTE_MEASUREMENT_TOTALITY"
    if not all(item["cryptomatte"]["measurementTotal"] and item["cryptomatte"]["visibleObjectCount"] > 0 and finite_measurement_tree(item["cryptomatte"]) for item in measurements):
        return "CRYPTOMATTE_MEASUREMENT_TOTALITY"
    if not all(item["normal"]["measurementTotal"] and item["normal"]["stableInteriorBothValidPixelCount"] > 0 and len(item["normal"]["lambertianProbes"]) == 5 and finite_measurement_tree(item["normal"]) for item in measurements):
        return "NORMAL_MEASUREMENT_TOTALITY"
    if not all(item["vector"]["measurementTotal"] and len(item["vector"]["pairs"]) == 2 and finite_measurement_tree(item["vector"]) for item in measurements):
        return "VECTOR_MEASUREMENT_TOTALITY"
    expected_diagnostics = {(profile, variant, kind) for profile in spec["diagnostics"]["profiles"] for variant in spec["inputs"]["variants"] for kind in spec["diagnostics"]["mapsPerPair"]}
    observed_diagnostics = {(item["profileId"], item["variantId"], item["kind"]) for item in evidence["diagnostics"]}
    if len(evidence["diagnostics"]) != spec["diagnostics"]["pngCount"] or observed_diagnostics != expected_diagnostics or not all(item["identityMatch"] for item in evidence["diagnostics"]):
        return "DIAGNOSTIC_TOTALITY"
    summaries, candidates = replay_classification(evidence, spec)
    if evidence["profileSummaries"] != summaries or evidence["futureHoldoutCandidates"] != candidates:
        return "CLASSIFICATION_REPLAY"
    if not all(item["allTaskClassifiersPassed"] == (item["cryptomatte"]["classifierPassed"] and item["normal"]["classifierPassed"] and item["vector"]["classifierPassed"]) for item in measurements):
        return "CLASSIFICATION_REPLAY"
    if evidence["operationCounts"] != spec["operationBoundary"]:
        return "OPERATION_BOUNDARY"
    if evidence.get("evidenceCoreHash") != analysis_library.canonical_hash(hash_payload(evidence)):
        return "EVIDENCE_SELF_HASH"
    return None


def run_attacks(evidence: dict, spec: dict, analysis_library) -> list[dict]:
    rows = []

    def add(identifier: str, reason: str, mutate, rehash: bool = True) -> None:
        clone = copy.deepcopy(evidence)
        mutate(clone)
        clone["evidenceCoreHash"] = analysis_library.canonical_hash(hash_payload(clone)) if rehash else "0" * 64
        observed = validate(clone, spec, analysis_library)
        rows.append({"id": identifier, "expectedReason": reason, "observedReason": observed, "passed": observed == reason})

    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_ARTIFACT", "ARTIFACT_IDENTITY", lambda x: x["artifactObservations"][0].update(match=False))
    add("A03_ROSTER", "PASS_ROSTER", lambda x: x["runObservations"][0]["roster"].pop())
    add("A04_REPEAT", "REPEAT_IDENTITY", lambda x: x["repeatComparisons"][0].update(allThreeRepeatsExact=False))
    add("A05_MANIFEST", "CRYPTOMATTE_MANIFEST", lambda x: x["manifestObservations"][0].update(manifestMatch=False))
    add("A06_REGION", "REGION_TOTALITY", lambda x: x["regions"][0].update(stableInteriorPixelCount=0))
    add("A07_CRYPTO", "CRYPTOMATTE_MEASUREMENT_TOTALITY", lambda x: x["candidateMeasurements"][0]["cryptomatte"].update(measurementTotal=False))
    add("A08_NORMAL", "NORMAL_MEASUREMENT_TOTALITY", lambda x: x["candidateMeasurements"][0]["normal"].update(measurementTotal=False))
    add("A09_VECTOR", "VECTOR_MEASUREMENT_TOTALITY", lambda x: x["candidateMeasurements"][0]["vector"].update(measurementTotal=False))
    add("A10_DIAGNOSTIC", "DIAGNOSTIC_TOTALITY", lambda x: x["diagnostics"][0].update(identityMatch=False))
    add("A11_CLASSIFICATION", "CLASSIFICATION_REPLAY", lambda x: x["profileSummaries"][0].update(futureHoldoutCandidate=not x["profileSummaries"][0]["futureHoldoutCandidate"]))
    add("A12_OPERATION", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(renders=1))
    add("A13_HASH", "EVIDENCE_SELF_HASH", lambda x: None, rehash=False)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.spec.resolve().parent.parent
    analysis_library = load_analysis_library(root)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    expected_preregistration = {
        "commit": PREREGISTRATION_COMMIT,
        "specUri": "specs/adaptive-payload-semantics-derivation.v0.1.json",
        "specSha256": SPEC_SHA256,
    }
    if sha256_file(args.spec) != SPEC_SHA256 or receipt.get("preregistration") != expected_preregistration:
        raise RuntimeError("B52-D3 preregistration identity differs")

    d2_receipt_path = root / spec["parents"]["d2Receipt"]["uri"]
    d2_result_path = root / spec["parents"]["d2Result"]["uri"]
    d2_audit_path = root / spec["parents"]["d2Audit"]["uri"]
    d2_receipt = json.loads(d2_receipt_path.read_text(encoding="utf-8"))
    d2_result = json.loads(d2_result_path.read_text(encoding="utf-8"))
    d2_audit = json.loads(d2_audit_path.read_text(encoding="utf-8"))
    if d2_result["verdict"] != spec["parents"]["d2Result"]["verdict"] or d2_audit["status"] != spec["parents"]["d2Audit"]["status"]:
        raise RuntimeError("B52-D2 parent status differs")
    d6_spec_path = root / d2_result["transitiveD6Spec"]["uri"]
    if sha256_file(d6_spec_path) != d2_result["transitiveD6Spec"]["sha256"]:
        raise RuntimeError("transitive D6 spec differs")
    d6_spec = json.loads(d6_spec_path.read_text(encoding="utf-8"))
    crypto_profile = d6_spec["cryptomatteProfile"]

    expected_artifacts = {item["runId"]: item for item in receipt["artifactObservations"]}
    if len(expected_artifacts) != spec["inputs"]["verifiedArtifacts"]:
        raise RuntimeError("B52-D3 receipt artifact count differs")
    loaded: dict[str, dict] = {}
    paths: dict[str, Path] = {}
    reports: dict[str, dict] = {}
    raw_metadata: dict[str, dict] = {}
    for run in d2_receipt["runs"]:
        run_id = run["runId"]
        report = run["report"]
        path = d2_receipt_path.parent / run_id / "artifacts" / report["artifact"]["uri"]
        loaded[run_id] = analysis_library.load_exr(path)
        paths[run_id] = path
        reports[run_id] = report
        raw_metadata[run_id] = analysis_library.crypto_metadata(loaded[run_id], crypto_profile)

    baseline_manifests = {}
    for variant_id in spec["inputs"]["variants"]:
        baseline_id = f"{variant_id}_{spec['inputs']['baselineProfile']}_R{spec['inputs']['representativeRepeat']}"
        manifest = raw_metadata[baseline_id]["manifest"]
        if not isinstance(manifest, dict) or not manifest:
            raise RuntimeError(f"baseline manifest absent for {variant_id}")
        baseline_manifests[variant_id] = manifest

    decoded_crypto: dict[str, dict] = {}
    artifact_observations = []
    run_observations = []
    manifest_observations = []
    for run in d2_receipt["runs"]:
        run_id, variant_id = run["runId"], run["variant"]
        image, path = loaded[run_id], paths[run_id]
        expected = expected_artifacts[run_id]
        observed_sha, observed_bytes = sha256_file(path), path.stat().st_size
        artifact_match = observed_sha == expected["expectedSha256"] and observed_bytes == expected["expectedBytes"]
        artifact_observations.append({
            "runId": run_id,
            "uri": str(path.relative_to(root)),
            "expectedSha256": expected["expectedSha256"],
            "observedSha256": observed_sha,
            "expectedBytes": expected["expectedBytes"],
            "observedBytes": observed_bytes,
            "match": artifact_match,
        })
        manifest = baseline_manifests[variant_id]
        crypto = analysis_library.decode_crypto(image, crypto_profile, manifest)
        decoded_crypto[run_id] = crypto
        metadata = raw_metadata[run_id]
        structural_values = [crypto["unresolvedRankEntries"], crypto["coverageRangeInvalidEntries"], crypto["coverageSumViolationPixels"], crypto["rankOrderViolationPairs"], crypto["duplicateNonzeroIdPairs"]]
        structural_valid = metadata["valid"] and metadata["manifest"] == manifest and all(value == 0 for value in structural_values)
        hashes = {name: analysis_library.pixel_hash(image["parts"][name]) for name in EXPECTED_ROSTER}
        run_observations.append({
            "runId": run_id,
            "variantId": variant_id,
            "profileId": run["profile"],
            "repeat": run["repeat"],
            "roster": image["roster"],
            "allPartsFinite": all(np.isfinite(value).all() for value in image["parts"].values()),
            "passPixelSha256": hashes,
            "artifact": {"uri": str(path.relative_to(root)), "sha256": observed_sha, "bytes": observed_bytes},
            "artifactIdentityMatch": artifact_match,
        })
        manifest_observations.append({
            "runId": run_id,
            "variantId": variant_id,
            "metadataValid": metadata["valid"],
            "manifestSha256": analysis_library.canonical_hash(metadata["manifest"]) if isinstance(metadata["manifest"], dict) else None,
            "baselineManifestSha256": analysis_library.canonical_hash(manifest),
            "manifestMatch": metadata["manifest"] == manifest,
            "structuralValid": structural_valid,
        })

    run_by_id = {item["runId"]: item for item in run_observations}
    repeat_comparisons = []
    for profile_id in [spec["inputs"]["baselineProfile"], *spec["inputs"]["candidateProfiles"]]:
        for variant_id in spec["inputs"]["variants"]:
            run_ids = [f"{variant_id}_{profile_id}_R{repeat}" for repeat in (1, 2, 3)]
            pairs = []
            for right_id in run_ids[1:]:
                passes = {name: np.array_equal(loaded[run_ids[0]]["parts"][name], loaded[right_id]["parts"][name]) for name in EXPECTED_ROSTER}
                pairs.append({"leftRunId": run_ids[0], "rightRunId": right_id, "passes": passes, "allEightPassesExact": all(passes.values())})
            repeat_comparisons.append({
                "profileId": profile_id,
                "variantId": variant_id,
                "runIds": run_ids,
                "pairs": pairs,
                "allThreeRepeatsExact": all(item["allEightPassesExact"] for item in pairs),
            })

    regions = []
    region_arrays = {}
    for variant_id in spec["inputs"]["variants"]:
        baseline_id = f"{variant_id}_{spec['inputs']['baselineProfile']}_R1"
        region_record, arrays = derive_region(loaded[baseline_id], decoded_crypto[baseline_id], spec)
        region_record.update({"variantId": variant_id, "baselineRunId": baseline_id})
        regions.append(region_record)
        region_arrays[variant_id] = arrays

    diagnostics_directory = args.output.parent / "diagnostics"
    diagnostics_directory.mkdir(parents=True, exist_ok=True)
    canonical_diagnostics_directory = f"{spec['outputRoot']}/diagnostics"
    candidate_measurements = []
    diagnostics = []
    diagnostic_profiles = set(spec["diagnostics"]["profiles"])
    for profile_id, variant_id in expected_pair_keys(spec):
        baseline_id = f"{variant_id}_{spec['inputs']['baselineProfile']}_R1"
        candidate_id = f"{variant_id}_{profile_id}_R1"
        region = region_arrays[variant_id]
        crypto_measurement, crypto_map = measure_cryptomatte(decoded_crypto[baseline_id], decoded_crypto[candidate_id], region, spec, float(crypto_profile["hardMatteThreshold"]))
        normal_measurement, normal_map = measure_normal(loaded[baseline_id]["parts"]["BFS_MASTER.Normal"], loaded[candidate_id]["parts"]["BFS_MASTER.Normal"], region, spec)
        vector_measurement, vector_map = measure_vector(loaded[baseline_id]["parts"]["BFS_MASTER.Vector"], loaded[candidate_id]["parts"]["BFS_MASTER.Vector"], region, spec)
        all_passed = crypto_measurement["classifierPassed"] and normal_measurement["classifierPassed"] and vector_measurement["classifierPassed"]
        candidate_measurements.append({
            "profileId": profile_id,
            "variantId": variant_id,
            "baselineRunId": baseline_id,
            "candidateRunId": candidate_id,
            "cryptomatte": crypto_measurement,
            "normal": normal_measurement,
            "vector": vector_measurement,
            "allTaskClassifiersPassed": all_passed,
        })
        if profile_id in diagnostic_profiles:
            maps = {
                "cryptomatte-maximum-alpha-error": crypto_map,
                "normal-angular-error-degrees": normal_map,
                "vector-maximum-pair-endpoint-error": vector_map,
            }
            for kind in spec["diagnostics"]["mapsPerPair"]:
                diagnostics.append(write_diagnostic(
                    diagnostics_directory,
                    canonical_diagnostics_directory,
                    variant_id,
                    profile_id,
                    kind,
                    maps[kind],
                    spec["diagnostics"]["mappings"][kind],
                    run_by_id[baseline_id]["artifact"],
                    run_by_id[candidate_id]["artifact"],
                ))

    evidence = {
        "schemaVersion": "bfs.adaptivePayloadSemanticsDerivationEvidence.v0.1",
        "experimentId": spec["experimentId"],
        "preregistration": receipt["preregistration"],
        "toolFreezeCommit": receipt["toolFreezeCommit"],
        "tools": receipt["tools"],
        "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "specObservation": receipt["specObservation"],
        "parentObservations": receipt["parentObservations"],
        "d2Invariants": {
            "verdict": d2_result["verdict"],
            "selectedProfileId": d2_result["selectedProfileId"],
            "baseFailure": d2_result["baseFailure"],
            "attacksPassed": d2_result["attacksPassed"],
            "auditStatus": d2_audit["status"],
            "evidenceCoreHash": d2_result["evidenceCoreHash"],
        },
        "transitiveD6Spec": {"uri": str(d6_spec_path.relative_to(root)), "sha256": sha256_file(d6_spec_path)},
        "artifactObservations": artifact_observations,
        "passRoster": EXPECTED_ROSTER,
        "runObservations": run_observations,
        "repeatComparisons": repeat_comparisons,
        "manifestObservations": manifest_observations,
        "regions": regions,
        "candidateMeasurements": candidate_measurements,
        "diagnostics": diagnostics,
        "classificationGates": {"cryptomatte": spec["cryptomatteTask"]["derivationClassifier"], "normal": spec["normalTask"]["derivationClassifier"], "vector": spec["vectorTask"]["derivationClassifier"]},
        "operationCounts": copy.deepcopy(spec["operationBoundary"]),
        "nonClaims": spec["nonClaims"],
        "parentDisclosure": spec["parentDisclosure"],
    }
    evidence["profileSummaries"], evidence["futureHoldoutCandidates"] = replay_classification(evidence, spec)
    evidence["evidenceCoreHash"] = analysis_library.canonical_hash(hash_payload(evidence))
    evidence["baseFailure"] = validate(evidence, spec, analysis_library)
    evidence["attacks"] = run_attacks(evidence, spec, analysis_library)
    evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"])
    valid = evidence["baseFailure"] is None and evidence["attacksPassed"] == len(spec["attacks"])
    evidence["verdict"] = spec["decisionRule"]["usableVerdict"] if valid else spec["decisionRule"]["invalidVerdict"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(
        f"BFS_B52_D3_RESULT verdict={evidence['verdict']} candidates={len(evidence['futureHoldoutCandidates'])} "
        f"attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={evidence['baseFailure'] or 'none'}",
        flush=True,
    )


if __name__ == "__main__":
    main()
