#!/usr/bin/env python3
"""Analyze, attack and decide B52-D1 native CPU adaptive quality/cost."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import statistics
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


AP1_LUMA = np.asarray([0.2722287168, 0.6740817658, 0.0536895174], dtype=np.float64)
PRODUCTION_PASSES = [
    "BFS_MASTER.Combined", "BFS_MASTER.Depth", "BFS_MASTER.Normal", "BFS_MASTER.Vector",
    "BFS_MASTER.CryptoObject00", "BFS_MASTER.CryptoObject01", "BFS_MASTER.CryptoObject02",
]
SAMPLE_COUNT = "BFS_MASTER.Debug Sample Count"
CRYPTO_PASSES = ["BFS_MASTER.CryptoObject00", "BFS_MASTER.CryptoObject01", "BFS_MASTER.CryptoObject02"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def pixel_hash(pixels: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(pixels, dtype="<f4").tobytes()).hexdigest()


def percentile(values: np.ndarray, quantile: float) -> float | None:
    return float(np.quantile(values, quantile, method="higher")) if values.size else None


def load_exr(path: Path) -> dict:
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror() or f"cannot read {path}")
    roster: list[str] = []
    parts: dict[str, np.ndarray] = {}
    channels: dict[str, list[str]] = {}
    metadata: dict[str, object] = {}
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
        if index == 0:
            metadata = {item.name: item.value for item in image_spec.extra_attribs if item.name.startswith("cryptomatte/")}
    return {"roster": roster, "parts": parts, "channels": channels, "metadata": metadata}


def edge_mask(reference_rgb: np.ndarray) -> tuple[np.ndarray, int, float]:
    luminance = np.maximum(np.tensordot(reference_rgb.astype(np.float64), AP1_LUMA, axes=([2], [0])), 0.0)
    dx, dy = np.zeros_like(luminance), np.zeros_like(luminance)
    dx[:, 1:-1] = 0.5 * (luminance[:, 2:] - luminance[:, :-2])
    dx[:, 0], dx[:, -1] = luminance[:, 1] - luminance[:, 0], luminance[:, -1] - luminance[:, -2]
    dy[1:-1, :] = 0.5 * (luminance[2:, :] - luminance[:-2, :])
    dy[0, :], dy[-1, :] = luminance[1, :] - luminance[0, :], luminance[-1, :] - luminance[-2, :]
    magnitude = np.hypot(dx, dy)
    count = max(1, math.ceil(magnitude.size * 0.10))
    selected = np.argsort(-magnitude.reshape(-1), kind="stable")[:count]
    mask = np.zeros(magnitude.size, dtype=bool)
    mask[selected] = True
    return mask.reshape(magnitude.shape), count, float(magnitude.reshape(-1)[selected[-1]])


def beauty_metrics(candidate: np.ndarray, target: np.ndarray, mask: np.ndarray, rms: float) -> dict:
    left, right = candidate[..., :3].astype(np.float64), target[..., :3].astype(np.float64)
    delta = left - right
    left_y = np.maximum(np.tensordot(left, AP1_LUMA, axes=([2], [0])), 0.0)
    right_y = np.maximum(np.tensordot(right, AP1_LUMA, axes=([2], [0])), 0.0)
    linear = float(np.sqrt(np.mean(np.square(delta))))
    return {
        "linearNrmseByEnsembleRms": linear / rms,
        "logLuminanceRmse": float(np.sqrt(np.mean(np.square(np.log2(1.0 + left_y) - np.log2(1.0 + right_y))))),
        "edgeLinearRmse": float(np.sqrt(np.mean(np.square(delta[mask])))),
        "linearRmse": linear,
        "linearMae": float(np.mean(np.abs(delta))),
        "linearP95AbsoluteError": float(np.percentile(np.abs(delta), 95)),
        "linearMaxAbsoluteError": float(np.max(np.abs(delta))),
    }


def crypto_metadata(loaded: dict, crypto_profile: dict) -> dict:
    prefix = f"cryptomatte/{crypto_profile['metadataKey']}"
    raw = loaded["metadata"]
    manifest_text = raw.get(f"{prefix}/manifest")
    try:
        manifest = json.loads(manifest_text) if isinstance(manifest_text, str) else None
    except json.JSONDecodeError:
        manifest = None
    valid = (
        raw.get(f"{prefix}/name") == crypto_profile["layerName"]
        and raw.get(f"{prefix}/hash") == crypto_profile["hash"]
        and raw.get(f"{prefix}/conversion") == crypto_profile["conversion"]
        and isinstance(manifest, dict) and bool(manifest)
        and all(isinstance(name, str) and isinstance(value, str) and len(value) == 8 for name, value in manifest.items())
    )
    return {"manifest": manifest, "valid": valid, "name": raw.get(f"{prefix}/name"), "hash": raw.get(f"{prefix}/hash"), "conversion": raw.get(f"{prefix}/conversion")}


def decode_crypto(loaded: dict, crypto_profile: dict, manifest: dict[str, str]) -> dict:
    ids: list[np.ndarray] = []
    coverage: list[np.ndarray] = []
    for part_name, id_channel, coverage_channel in crypto_profile["rankChannels"]:
        pixels = loaded["parts"][part_name]
        ids.append(np.ascontiguousarray(pixels[..., id_channel], dtype="<f4").view("<u4"))
        coverage.append(np.ascontiguousarray(pixels[..., coverage_channel], dtype="<f4"))
    id_stack, coverage_stack = np.stack(ids, axis=-1), np.stack(coverage, axis=-1)
    epsilon = float(crypto_profile["coverageSumEpsilon"])
    low, high = crypto_profile["coverageRange"]
    active = coverage_stack > 0.0
    manifest_bits = {name: int(value, 16) for name, value in manifest.items()}
    known = np.isin(id_stack, np.asarray(list(manifest_bits.values()), dtype="<u4"))
    coverage_sum = np.sum(coverage_stack.astype(np.float64), axis=-1)
    duplicate_pairs = 0
    for left in range(id_stack.shape[-1]):
        for right in range(left + 1, id_stack.shape[-1]):
            duplicate_pairs += int(np.count_nonzero(active[..., left] & active[..., right] & (id_stack[..., left] == id_stack[..., right])))
    return {
        "ids": id_stack,
        "coverage": coverage_stack,
        "mattes": {name: np.sum(np.where(id_stack == bits, coverage_stack, 0.0).astype(np.float64), axis=-1) for name, bits in manifest_bits.items()},
        "unresolvedRankEntries": int(np.count_nonzero(active & ~known)),
        "coverageRangeInvalidEntries": int(np.count_nonzero((~np.isfinite(coverage_stack)) | (coverage_stack < low) | (coverage_stack > high))),
        "coverageSumViolationPixels": int(np.count_nonzero(coverage_sum > 1.0 + epsilon)),
        "coverageSumMaximum": float(np.max(coverage_sum)),
        "rankOrderViolationPairs": int(np.count_nonzero(coverage_stack[..., :-1] + epsilon < coverage_stack[..., 1:])),
        "duplicateNonzeroIdPairs": duplicate_pairs,
    }


def compare_semantics(candidate: dict, reference: dict, thresholds: dict, crypto_profile: dict) -> dict:
    parent_ids, parent_coverage = reference["crypto"]["ids"], reference["crypto"]["coverage"]
    candidate_ids = candidate["crypto"]["ids"]
    confident = parent_coverage[..., 0] >= crypto_profile["confidentDominantCoverage"]
    dominant_mismatch = int(np.count_nonzero(confident & (parent_ids[..., 0] != candidate_ids[..., 0])))
    objects: list[dict] = []
    transition_union = np.zeros(parent_ids.shape[:2], dtype=bool)
    for name in sorted(reference["crypto"]["mattes"]):
        parent_matte, candidate_matte = reference["crypto"]["mattes"][name], candidate["crypto"]["mattes"][name]
        if not np.any(parent_matte > 0.0):
            continue
        transition = (parent_matte > 0.0) & (parent_matte < 1.0)
        transition_union |= transition
        absolute = np.abs(candidate_matte - parent_matte)
        hard_mismatch = int(np.count_nonzero((candidate_matte >= crypto_profile["hardMatteThreshold"]) != (parent_matte >= crypto_profile["hardMatteThreshold"])))
        maximum, p99 = float(np.max(absolute)), percentile(absolute, 0.99)
        rmse = float(np.sqrt(np.mean(np.square(absolute, dtype=np.float64))))
        passed = (
            hard_mismatch <= thresholds["cryptomatte"]["hardMatteMismatchPixelsPerVisibleObject"]
            and maximum <= thresholds["cryptomatte"]["perVisibleObjectMatteMaxAbsoluteError"]
            and p99 is not None and p99 <= thresholds["cryptomatte"]["perVisibleObjectMatteP99AbsoluteError"]
            and rmse <= thresholds["cryptomatte"]["perVisibleObjectMatteRmse"]
        )
        objects.append({"name": name, "hardMatteMismatchPixels": hard_mismatch, "maxAbsoluteError": maximum, "p99AbsoluteError": p99, "rmse": rmse, "transitionPixelCount": int(np.count_nonzero(transition)), "passed": passed})
    crypto_passed = dominant_mismatch <= thresholds["cryptomatte"]["confidentDominantIdMismatchPixels"] and bool(objects) and all(item["passed"] for item in objects)

    parent_depth, candidate_depth = reference["depth"], candidate["depth"]
    sentinel = thresholds["depth"]["backgroundSentinelThreshold"]
    parent_foreground, candidate_foreground = parent_depth < sentinel, candidate_depth < sentinel
    foreground_mismatch = int(np.count_nonzero(parent_foreground != candidate_foreground))
    stable = parent_foreground & (parent_coverage[..., 0] >= crypto_profile["stableSurfaceCoverage"]) & (parent_ids[..., 0] == candidate_ids[..., 0])
    absolute_depth = np.abs(candidate_depth.astype(np.float64) - parent_depth.astype(np.float64))[stable]
    relative_depth = absolute_depth / np.maximum(np.abs(parent_depth.astype(np.float64)[stable]), 1e-6)
    p50_abs, p95_abs, p99_abs = percentile(absolute_depth, 0.50), percentile(absolute_depth, 0.95), percentile(absolute_depth, 0.99)
    max_abs, p99_rel = (float(np.max(absolute_depth)) if absolute_depth.size else None), percentile(relative_depth, 0.99)
    depth_passed = (
        foreground_mismatch <= thresholds["depth"]["foregroundMaskMismatchPixels"]
        and p99_abs is not None and p99_abs <= thresholds["depth"]["stableSurfaceP99AbsoluteErrorMeters"]
        and max_abs is not None and max_abs <= thresholds["depth"]["stableSurfaceMaxAbsoluteErrorMeters"]
        and p99_rel is not None and p99_rel <= thresholds["depth"]["stableSurfaceP99RelativeError"]
    )
    return {
        "cryptomatte": {"manifestObjectCount": len(reference["crypto"]["mattes"]), "visibleObjectCount": len(objects), "confidentParentPixelCount": int(np.count_nonzero(confident)), "confidentDominantIdMismatchPixels": dominant_mismatch, "transitionPixelCount": int(np.count_nonzero(transition_union)), "objects": objects, "passed": crypto_passed},
        "depth": {"foregroundPixelCount": int(np.count_nonzero(parent_foreground)), "foregroundMaskMismatchPixels": foreground_mismatch, "stableSurfacePixelCount": int(np.count_nonzero(stable)), "stableSurfaceP50AbsoluteErrorMeters": p50_abs, "stableSurfaceP95AbsoluteErrorMeters": p95_abs, "stableSurfaceP99AbsoluteErrorMeters": p99_abs, "stableSurfaceMaxAbsoluteErrorMeters": max_abs, "stableSurfaceP99RelativeError": p99_rel, "passed": depth_passed},
        "passed": crypto_passed and depth_passed,
    }


def operation_replay_valid(replay: list[dict], expected: list[dict]) -> bool:
    if len(replay) != len(expected):
        return False
    for item, operation in zip(replay, expected, strict=True):
        if item["operation"] != operation:
            return False
        before, after, value = item["before"], item["after"], operation["value"]
        if operation["kind"] == "LOCATION_DELTA":
            if not np.allclose(np.asarray(after), np.asarray(before) + np.asarray(value), rtol=1e-6, atol=1e-6): return False
        elif operation["kind"] == "ROTATION_Z_DELTA":
            if not np.isclose(float(after), float(before) + float(value), rtol=1e-6, atol=1e-6): return False
        elif operation["kind"] == "CAMERA_LENS_SET":
            if not np.isclose(float(after), float(value), rtol=1e-6, atol=1e-6): return False
        elif operation["kind"] == "LIGHT_ENERGY_SCALE":
            if not np.isclose(float(after), float(before) * float(value), rtol=1e-6, atol=1e-6): return False
        else:
            return False
    return True


def expected_matrix(spec: dict, d5_spec: dict) -> list[dict]:
    rows: list[dict] = []
    order = 1
    variants = {item["id"]: item for item in d5_spec["variants"]}
    for profile in spec["referenceCells"]:
        for variant_id in variants:
            rows.append({"runId": f"{variant_id}_{profile['id']}_R1", "variant": variant_id, "source": variants[variant_id]["source"], "profile": profile["id"], "role": "REFERENCE", "repeat": 1, "order": order})
            order += 1
    for profile in spec["candidateProfiles"]:
        for variant_id in variants:
            for repeat in range(1, spec["candidateRepeats"] + 1):
                rows.append({"runId": f"{variant_id}_{profile['id']}_R{repeat}", "variant": variant_id, "source": variants[variant_id]["source"], "profile": profile["id"], "role": profile["role"], "repeat": repeat, "order": order})
                order += 1
    return rows


def settings_valid(settings: dict, profile: dict, render_profile: dict, base_seed: int) -> bool:
    exact = {
        "engine": render_profile["engine"], "cyclesDevice": "CPU", "resolution": [*render_profile["resolution"], 100],
        "pixelCount": render_profile["resolution"][0] * render_profile["resolution"][1], "maxSamples": profile["maxSamples"],
        "seedOffset": profile["seedOffset"], "seed": base_seed + profile["seedOffset"], "animatedSeed": render_profile["animatedSeed"],
        "adaptive": profile["adaptive"], "minSamples": profile.get("minSamples", 0), "denoising": render_profile["denoising"],
        "motionBlur": render_profile["motionBlur"], "persistentData": render_profile["persistentData"], "threadsMode": "FIXED",
        "threads": render_profile["cpuThreads"], "sampleCountPass": True,
    }
    if any(settings.get(key) != value for key, value in exact.items()):
        return False
    return math.isclose(float(settings.get("noiseThreshold", -1)), float(profile.get("noiseThreshold", 0.01)), rel_tol=1e-6, abs_tol=1e-8)


def hash_payload(evidence: dict) -> dict:
    return {key: value for key, value in evidence.items() if key not in {"evidenceCoreHash", "baseFailure", "attacks", "attacksPassed", "verdict"}}


def replay_selection(evidence: dict, spec: dict) -> tuple[list[dict], str | None]:
    threshold = spec["costGate"]["minimumMedianRenderSavingFractionVersusFixed128"]
    summaries: list[dict] = []
    for profile in spec["candidateProfiles"]:
        if profile["role"] != "CANDIDATE":
            continue
        rows = [item for item in evidence["candidateMeasurements"] if item["profileId"] == profile["id"]]
        costs = [item for item in evidence["costMeasurements"] if item["profileId"] == profile["id"]]
        per_variant_cost = len(costs) == 2 and all(item["renderSavingFraction"] >= threshold for item in costs)
        eligible = len(rows) == 4 and all(item["combinedPass"] for item in rows) and per_variant_cost
        variant_medians = [item["candidateMedianRenderSeconds"] for item in costs]
        summaries.append({
            "profileId": profile["id"], "noiseThreshold": profile["noiseThreshold"], "minSamples": profile["minSamples"],
            "eligible": eligible, "allQualityAndPassGates": len(rows) == 4 and all(item["combinedPass"] for item in rows),
            "perVariantCostGate": per_variant_cost,
            "crossVariantMedianRenderSeconds": statistics.median(variant_medians) if len(variant_medians) == 2 else None,
            "worstVariantRenderSavingFraction": min((item["renderSavingFraction"] for item in costs), default=None),
        })
    eligible = [item for item in summaries if item["eligible"]]
    eligible.sort(key=lambda item: (item["crossVariantMedianRenderSeconds"], item["noiseThreshold"], -item["minSamples"], item["profileId"]))
    return summaries, eligible[0]["profileId"] if eligible else None


def validate(evidence: dict, spec: dict, d5_spec: dict) -> str | None:
    if not all(item["match"] for item in evidence["parentObservations"]): return "PARENT_IDENTITY"
    if not evidence["blenderObservation"]["match"]: return "BLENDER_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"] + evidence["sourcePostObservations"]): return "SOURCE_IDENTITY"
    if evidence["diskAdmission"]["status"] != "ACCEPTED": return "DISK_ADMISSION"
    if evidence["schedule"] != expected_matrix(spec, d5_spec) or len(evidence["runObservations"]) != spec["matrix"]["nativeBlenderProcesses"]: return "MATRIX_TOTALITY"
    if len({item["processPid"] for item in evidence["runObservations"]}) != len(evidence["runObservations"]) or not all(item["processPid"] == item["runnerObservedPid"] for item in evidence["runObservations"]): return "FRESH_PROCESS"
    if not all(item["deviceValid"] for item in evidence["runObservations"]): return "CPU_DEVICE"
    if not all(item["settingsValid"] and item["operationReplayValid"] and item["sourceIdentityMatch"] for item in evidence["runObservations"]): return "ADAPTIVE_SETTINGS"
    if not all(item["rosterMatch"] for item in evidence["runObservations"]): return "PASS_ROSTER"
    if len(evidence["sampleCountMeasurements"]) != spec["matrix"]["renders"] or not all(item["valid"] for item in evidence["sampleCountMeasurements"]): return "SAMPLE_COUNT_VALIDITY"
    if len(evidence["fixed128ParentComparisons"]) != 4 or not all(item["allProductionPassesExact"] for item in evidence["fixed128ParentComparisons"]): return "FIXED128_PARENT_CONTROL"
    if len(evidence["repeatComparisons"]) != len(spec["candidateProfiles"]) * 2 or not all(item["allEightPassesExact"] for item in evidence["repeatComparisons"]): return "REPEAT_EXACTNESS"
    if len(evidence["referenceIndependence"]) != 2 or not all(item["threeDistinct"] for item in evidence["referenceIndependence"]): return "REFERENCE_INDEPENDENCE"
    floors_valid = (
        len(evidence["referenceFloors"]) == 2
        and all(
            item["ensembleMean"]["rgbRms"] > 0.0
            and all(math.isfinite(value) and value > 0.0 for value in item["floor"].values())
            for item in evidence["referenceFloors"]
        )
    )
    if not floors_valid or len(evidence["beautyMeasurements"]) != len(spec["candidateProfiles"]) * 2 * spec["candidateRepeats"] or not all(item["measurementTotal"] for item in evidence["beautyMeasurements"]): return "BEAUTY_MEASUREMENT_TOTALITY"
    if len(evidence["dataSemanticMeasurements"]) != len(spec["candidateProfiles"]) * 2 * spec["candidateRepeats"] or not all(item["measurementTotal"] and item["structuralValid"] for item in evidence["dataSemanticMeasurements"]): return "DATA_SEMANTIC_TOTALITY"
    if len(evidence["auxiliaryPassMeasurements"]) != len(spec["candidateProfiles"]) * 2 * spec["candidateRepeats"] or not all(set(item["passes"]) == set(spec["auxiliaryPassGate"]["passes"]) and item["allExact"] == all(item["passes"].values()) for item in evidence["auxiliaryPassMeasurements"]): return "AUXILIARY_PASS_TOTALITY"
    beauty_by_run = {item["runId"]: item for item in evidence["beautyMeasurements"]}
    data_by_run = {item["runId"]: item for item in evidence["dataSemanticMeasurements"]}
    auxiliary_by_run = {item["runId"]: item for item in evidence["auxiliaryPassMeasurements"]}
    sample_by_run = {item["runId"]: item for item in evidence["sampleCountMeasurements"]}
    expected_candidate_count = len(spec["candidateProfiles"]) * 2 * spec["candidateRepeats"]
    if len(evidence["candidateMeasurements"]) != expected_candidate_count:
        return "COST_MEASUREMENT_TOTALITY"
    for item in evidence["candidateMeasurements"]:
        run_id = item["runId"]
        if run_id not in beauty_by_run or run_id not in data_by_run or run_id not in auxiliary_by_run or run_id not in sample_by_run:
            return "COST_MEASUREMENT_TOTALITY"
        expected_flags = {
            "beautyPass": beauty_by_run[run_id]["passed"],
            "dataSemanticPass": data_by_run[run_id]["passed"] and data_by_run[run_id]["structuralValid"],
            "auxiliaryPass": auxiliary_by_run[run_id]["allExact"],
            "sampleCountPass": sample_by_run[run_id]["valid"],
        }
        expected_flags["combinedPass"] = all(expected_flags.values())
        if any(item[key] != value for key, value in expected_flags.items()):
            return "COST_MEASUREMENT_TOTALITY"
    summaries, selected = replay_selection(evidence, spec)
    if len(evidence["costMeasurements"]) != 10 or evidence["profileSummaries"] != summaries or evidence["selectedProfileId"] != selected: return "COST_MEASUREMENT_TOTALITY"
    if not all(item["artifactIdentityMatch"] for item in evidence["runObservations"]): return "ARTIFACT_IDENTITY"
    if evidence["operationCounts"] != spec["operationBoundary"]: return "OPERATION_BOUNDARY"
    if evidence.get("evidenceCoreHash") != canonical_hash(hash_payload(evidence)): return "EVIDENCE_SELF_HASH"
    return None


def run_attacks(evidence: dict, spec: dict, d5_spec: dict) -> list[dict]:
    rows: list[dict] = []
    def add(identifier: str, reason: str, mutate, rehash: bool = True) -> None:
        clone = copy.deepcopy(evidence)
        mutate(clone)
        clone["evidenceCoreHash"] = canonical_hash(hash_payload(clone)) if rehash else "0" * 64
        observed = validate(clone, spec, d5_spec)
        rows.append({"id": identifier, "expectedReason": reason, "observedReason": observed, "passed": observed == reason})
    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_BLENDER", "BLENDER_IDENTITY", lambda x: x["blenderObservation"].update(match=False))
    add("A03_SOURCE", "SOURCE_IDENTITY", lambda x: x["sourceObservations"][0].update(match=False))
    add("A04_DISK", "DISK_ADMISSION", lambda x: x["diskAdmission"].update(status="BLOCKED"))
    add("A05_MATRIX", "MATRIX_TOTALITY", lambda x: x["schedule"].pop())
    add("A06_FRESH", "FRESH_PROCESS", lambda x: x["runObservations"][1].update(processPid=x["runObservations"][0]["processPid"]))
    add("A07_CPU", "CPU_DEVICE", lambda x: x["runObservations"][0].update(deviceValid=False))
    add("A08_SETTINGS", "ADAPTIVE_SETTINGS", lambda x: x["runObservations"][0].update(settingsValid=False))
    add("A09_ROSTER", "PASS_ROSTER", lambda x: x["runObservations"][0].update(rosterMatch=False))
    add("A10_SAMPLE_COUNT", "SAMPLE_COUNT_VALIDITY", lambda x: x["sampleCountMeasurements"][0].update(valid=False))
    add("A11_FIXED", "FIXED128_PARENT_CONTROL", lambda x: x["fixed128ParentComparisons"][0].update(allProductionPassesExact=False))
    add("A12_REPEAT", "REPEAT_EXACTNESS", lambda x: x["repeatComparisons"][0].update(allEightPassesExact=False))
    add("A13_REFERENCE", "REFERENCE_INDEPENDENCE", lambda x: x["referenceIndependence"][0].update(threeDistinct=False))
    add("A14_BEAUTY", "BEAUTY_MEASUREMENT_TOTALITY", lambda x: x["beautyMeasurements"][0].update(measurementTotal=False))
    add("A15_DATA", "DATA_SEMANTIC_TOTALITY", lambda x: x["dataSemanticMeasurements"][0].update(measurementTotal=False))
    add("A16_AUX", "AUXILIARY_PASS_TOTALITY", lambda x: x["auxiliaryPassMeasurements"][0]["passes"].pop())
    add("A17_COST", "COST_MEASUREMENT_TOTALITY", lambda x: x["costMeasurements"].pop())
    add("A18_ARTIFACT", "ARTIFACT_IDENTITY", lambda x: x["runObservations"][0].update(artifactIdentityMatch=False))
    add("A19_BOUNDARY", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(metalRenders=1))
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
    d5_spec = json.loads((root / spec["parents"]["d5Spec"]["uri"]).read_text(encoding="utf-8"))
    d6_result = json.loads((root / spec["parents"]["d6Result"]["uri"]).read_text(encoding="utf-8"))
    d6_spec_path = root / d6_result["preregistration"]["specUri"]
    if sha256_file(d6_spec_path) != d6_result["preregistration"]["specSha256"]:
        raise RuntimeError("transitively bound D6 spec differs")
    d6_spec = json.loads(d6_spec_path.read_text(encoding="utf-8"))
    registered_thresholds = {group: spec["dataSemanticGate"][group] for group in ("cryptomatte", "depth")}
    frozen_thresholds = {
        group: {key: d6_result["thresholds"][group][key] for key in values}
        for group, values in registered_thresholds.items()
    }
    if d6_result["thresholds"] != d6_spec["productionSemanticProfile"] or frozen_thresholds != registered_thresholds:
        raise RuntimeError("D6 semantic thresholds differ")
    crypto_profile = d6_spec["cryptomatteProfile"]
    thresholds = registered_thresholds
    profiles = {item["id"]: item for item in [*spec["referenceCells"], *spec["candidateProfiles"]]}
    variants = {item["id"]: item for item in d5_spec["variants"]}
    fixed_parents = {item["id"]: item["fixed128Parent"] for item in spec["variantsFromD5"]}
    registered_passes = {f"BFS_MASTER.{name}" for name in spec["renderProfile"]["passes"]}
    expected_roster = [
        "BFS_MASTER.Combined", "BFS_MASTER.Depth", "BFS_MASTER.Normal", "BFS_MASTER.Vector",
        "BFS_MASTER.Debug Sample Count", "BFS_MASTER.CryptoObject00", "BFS_MASTER.CryptoObject01",
        "BFS_MASTER.CryptoObject02",
    ]
    if set(expected_roster) != registered_passes:
        raise RuntimeError("registered B52 pass set differs")
    expected_cpu = json.loads((root / d5_spec["parents"]["h1Spec"]["uri"]).read_text(encoding="utf-8"))["nativeBlender"]["cpuDevice"]

    loaded: dict[str, dict] = {}
    run_observations: list[dict] = []
    sample_measurements: list[dict] = []
    decoded_crypto: dict[str, dict] = {}
    manifests: dict[str, dict[str, str]] = {}
    for run in receipt["runs"]:
        report = run["report"]
        path = args.receipt.parent / run["runId"] / "artifacts" / report["artifact"]["uri"]
        image = load_exr(path)
        loaded[run["runId"]] = image
        profile = profiles[run["profile"]]
        variant = variants[run["variant"]]
        source = d5_spec["sources"][variant["source"]]
        meta = crypto_metadata(image, crypto_profile)
        if run["variant"] not in manifests and isinstance(meta["manifest"], dict):
            manifests[run["variant"]] = meta["manifest"]
        manifest = manifests.get(run["variant"], meta["manifest"] if isinstance(meta["manifest"], dict) else {})
        crypto = decode_crypto(image, crypto_profile, manifest)
        decoded_crypto[run["runId"]] = crypto
        structural = {
            "metadataValid": meta["valid"], "manifestConsistent": meta["manifest"] == manifest,
            "unresolvedRankEntries": crypto["unresolvedRankEntries"], "coverageRangeInvalidEntries": crypto["coverageRangeInvalidEntries"],
            "coverageSumViolationPixels": crypto["coverageSumViolationPixels"], "rankOrderViolationPairs": crypto["rankOrderViolationPairs"],
            "duplicateNonzeroIdPairs": crypto["duplicateNonzeroIdPairs"],
        }
        structural_valid = structural["metadataValid"] and structural["manifestConsistent"] and all(structural[key] == 0 for key in structural if key not in {"metadataValid", "manifestConsistent"})
        count_pixels = image["parts"][SAMPLE_COUNT].astype(np.float64).reshape(-1)
        finite = bool(np.isfinite(count_pixels).all())
        in_range = bool(finite and np.all(count_pixels >= 0.0) and np.all(count_pixels <= 1.0))
        all_at_max = bool(np.array_equal(count_pixels, np.ones_like(count_pixels)))
        stopped = bool(np.any(count_pixels < 1.0))
        sample_valid = finite and in_range and (stopped if profile["adaptive"] else all_at_max)
        sample_measurements.append({
            "runId": run["runId"], "variantId": run["variant"], "profileId": run["profile"], "repeat": run["repeat"],
            "adaptive": profile["adaptive"], "finite": finite, "inRange": in_range, "allAtMaxSamples": all_at_max,
            "stoppedAtLeastOnePixel": stopped, "minimumNormalizedSamples": float(np.min(count_pixels)),
            "p50NormalizedSamples": percentile(count_pixels, 0.50), "p95NormalizedSamples": percentile(count_pixels, 0.95),
            "p99NormalizedSamples": percentile(count_pixels, 0.99), "maximumNormalizedSamples": float(np.max(count_pixels)),
            "meanEffectiveSamples": float(np.mean(count_pixels) * profile["maxSamples"]),
            "fractionAtMaxSamples": float(np.count_nonzero(count_pixels == 1.0) / count_pixels.size), "valid": sample_valid,
        })
        selected = report["device"]["selected"]
        device_valid = len(selected) == 1 and selected[0]["id"] == expected_cpu["id"] and selected[0]["type"] == "CPU"
        hashes = {name: pixel_hash(image["parts"][name]) for name in expected_roster}
        run_observations.append({
            "runId": run["runId"], "variantId": run["variant"], "sourceId": run["source"], "profileId": run["profile"],
            "role": run["role"], "repeat": run["repeat"], "order": run["order"], "processPid": report["process"]["pid"],
            "runnerObservedPid": run["pid"], "freshProcessWallSeconds": run["elapsedSeconds"], "renderSeconds": report["renderSeconds"],
            "saveSeconds": report["saveSeconds"], "peakSelfRssBytes": report["peakSelfRssBytes"],
            "sourceIdentityMatch": report["source"] == {"uri": source["blendUri"], "sha256": source["blendSha256"], "bytes": source["blendBytes"]},
            "operationReplayValid": operation_replay_valid(report["operationReplay"], variant["operations"]),
            "selectedDevices": selected, "deviceValid": device_valid, "settings": report["settings"],
            "settingsValid": settings_valid(report["settings"], profile, spec["renderProfile"], int(report["bindings"]["baseShotSeed"])),
            "roster": image["roster"], "rosterMatch": image["roster"] == expected_roster,
            "allPartsFinite": all(np.isfinite(value).all() for value in image["parts"].values()),
            "cryptomatteStructure": structural, "cryptomatteStructuralValid": structural_valid, "passPixelSha256": hashes,
            "artifact": {"uri": str(path.relative_to(root)), "sha256": sha256_file(path), "bytes": path.stat().st_size},
            "artifactIdentityMatch": report["artifact"]["sha256"] == sha256_file(path) and report["artifact"]["bytes"] == path.stat().st_size,
        })

    fixed_parent_loaded = {variant_id: load_exr(root / binding["uri"]) for variant_id, binding in fixed_parents.items()}
    fixed_comparisons: list[dict] = []
    for variant_id in variants:
        for repeat in range(1, spec["candidateRepeats"] + 1):
            run_id = f"{variant_id}_FIXED_128_R{repeat}"
            passes = {name: np.array_equal(loaded[run_id]["parts"][name], fixed_parent_loaded[variant_id]["parts"][name]) for name in PRODUCTION_PASSES}
            fixed_comparisons.append({"runId": run_id, "variantId": variant_id, "repeat": repeat, "passes": passes, "allProductionPassesExact": all(passes.values())})

    repeat_comparisons: list[dict] = []
    for profile in spec["candidateProfiles"]:
        for variant_id in variants:
            left_id, right_id = f"{variant_id}_{profile['id']}_R1", f"{variant_id}_{profile['id']}_R2"
            passes = {name: np.array_equal(loaded[left_id]["parts"][name], loaded[right_id]["parts"][name]) for name in expected_roster}
            repeat_comparisons.append({"variantId": variant_id, "profileId": profile["id"], "leftRunId": left_id, "rightRunId": right_id, "passes": passes, "allEightPassesExact": all(passes.values())})

    reference_independence: list[dict] = []
    beauty_measurements: list[dict] = []
    reference_floors: list[dict] = []
    for variant_id in variants:
        reference_ids = [f"{variant_id}_{profile['id']}_R1" for profile in spec["referenceCells"]]
        hashes = [pixel_hash(loaded[run_id]["parts"]["BFS_MASTER.Combined"]) for run_id in reference_ids]
        reference_independence.append({"variantId": variant_id, "runIds": reference_ids, "combinedPixelSha256": hashes, "threeDistinct": len(set(hashes)) == 3})
        ensemble = np.mean(np.stack([loaded[run_id]["parts"]["BFS_MASTER.Combined"].astype(np.float64) for run_id in reference_ids]), axis=0)
        rms = float(np.sqrt(np.mean(np.square(ensemble[..., :3]))))
        mask, edge_count, cutoff = edge_mask(ensemble[..., :3])
        reference_rows = [beauty_metrics(loaded[run_id]["parts"]["BFS_MASTER.Combined"], ensemble, mask, rms) for run_id in reference_ids]
        floor = {name: max(row[name] for row in reference_rows) for name in spec["beautyQualityGate"]["metrics"]}
        reference_floors.append({
            "variantId": variant_id, "referenceRunIds": reference_ids,
            "ensembleMean": {"dtype": "float64-le", "shape": list(ensemble.shape), "sha256": hashlib.sha256(np.ascontiguousarray(ensemble.astype("<f8")).tobytes()).hexdigest(), "rgbRms": rms},
            "edgeMask": {"pixelCount": edge_count, "gradientCutoff": cutoff}, "referenceMetrics": reference_rows, "floor": floor,
        })
        for profile in spec["candidateProfiles"]:
            for repeat in range(1, spec["candidateRepeats"] + 1):
                run_id = f"{variant_id}_{profile['id']}_R{repeat}"
                measured = beauty_metrics(loaded[run_id]["parts"]["BFS_MASTER.Combined"], ensemble, mask, rms)
                multiples = {name: measured[name] / floor[name] for name in spec["beautyQualityGate"]["metrics"]}
                passed = all(value <= spec["beautyQualityGate"]["maximumFloorMultiple"] for value in multiples.values())
                beauty_measurements.append({"runId": run_id, "variantId": variant_id, "profileId": profile["id"], "repeat": repeat, "metricsAgainstEnsemble": measured, "floorMultiples": multiples, "passed": passed, "measurementTotal": all(math.isfinite(value) for value in [*measured.values(), *multiples.values()])})

    data_measurements: list[dict] = []
    auxiliary_measurements: list[dict] = []
    for profile in spec["candidateProfiles"]:
        for variant_id in variants:
            for repeat in range(1, spec["candidateRepeats"] + 1):
                run_id, control_id = f"{variant_id}_{profile['id']}_R{repeat}", f"{variant_id}_FIXED_128_R{repeat}"
                reference = {"crypto": decoded_crypto[control_id], "depth": loaded[control_id]["parts"]["BFS_MASTER.Depth"][..., 0]}
                candidate = {"crypto": decoded_crypto[run_id], "depth": loaded[run_id]["parts"]["BFS_MASTER.Depth"][..., 0]}
                semantic = compare_semantics(candidate, reference, thresholds, crypto_profile)
                structure = next(item for item in run_observations if item["runId"] == run_id)["cryptomatteStructuralValid"]
                semantic.update({"runId": run_id, "variantId": variant_id, "profileId": profile["id"], "repeat": repeat, "structuralValid": structure, "measurementTotal": bool(semantic["cryptomatte"]["objects"] and semantic["depth"]["stableSurfacePixelCount"] > 0)})
                data_measurements.append(semantic)
                passes = {name: np.array_equal(loaded[run_id]["parts"][name], loaded[control_id]["parts"][name]) for name in spec["auxiliaryPassGate"]["passes"]}
                auxiliary_measurements.append({"runId": run_id, "controlRunId": control_id, "variantId": variant_id, "profileId": profile["id"], "repeat": repeat, "passes": passes, "allExact": all(passes.values())})

    candidate_measurements: list[dict] = []
    for beauty in beauty_measurements:
        run_id = beauty["runId"]
        semantic = next(item for item in data_measurements if item["runId"] == run_id)
        auxiliary = next(item for item in auxiliary_measurements if item["runId"] == run_id)
        sample = next(item for item in sample_measurements if item["runId"] == run_id)
        candidate_measurements.append({
            "runId": run_id, "variantId": beauty["variantId"], "profileId": beauty["profileId"], "repeat": beauty["repeat"],
            "beautyPass": beauty["passed"], "dataSemanticPass": semantic["passed"] and semantic["structuralValid"],
            "auxiliaryPass": auxiliary["allExact"], "sampleCountPass": sample["valid"],
            "combinedPass": beauty["passed"] and semantic["passed"] and semantic["structuralValid"] and auxiliary["allExact"] and sample["valid"],
        })

    observations_by_run = {item["runId"]: item for item in run_observations}
    cost_measurements: list[dict] = []
    for profile in spec["candidateProfiles"]:
        if profile["role"] != "CANDIDATE":
            continue
        for variant_id in variants:
            controls = [observations_by_run[f"{variant_id}_FIXED_128_R{repeat}"] for repeat in range(1, spec["candidateRepeats"] + 1)]
            candidates = [observations_by_run[f"{variant_id}_{profile['id']}_R{repeat}"] for repeat in range(1, spec["candidateRepeats"] + 1)]
            control_render, candidate_render = statistics.median(item["renderSeconds"] for item in controls), statistics.median(item["renderSeconds"] for item in candidates)
            control_wall, candidate_wall = statistics.median(item["freshProcessWallSeconds"] for item in controls), statistics.median(item["freshProcessWallSeconds"] for item in candidates)
            cost_measurements.append({
                "variantId": variant_id, "profileId": profile["id"], "repeats": spec["candidateRepeats"],
                "controlMedianRenderSeconds": control_render, "candidateMedianRenderSeconds": candidate_render,
                "renderSavingFraction": 1.0 - candidate_render / control_render,
                "controlMedianFreshProcessWallSeconds": control_wall, "candidateMedianFreshProcessWallSeconds": candidate_wall,
                "freshProcessWallSavingFraction": 1.0 - candidate_wall / control_wall,
                "medianSaveSeconds": statistics.median(item["saveSeconds"] for item in candidates),
                "medianArtifactBytes": statistics.median(item["artifact"]["bytes"] for item in candidates),
            })

    operation_counts = {
        "nativeBlenderProcesses": sum(item.startswith("NATIVE_BLENDER_PROCESS_") for item in receipt["runtimeOperations"]),
        "renders": len(receipt["runs"]), "sourceBlendFilesModified": 0, "parentExrsModified": 0,
        "metalRenders": 0, "dockerRuns": 0, "downloadsDuringFormalRun": 0,
        "modelCalls": 0, "videoModelCalls": 0, "networkRequired": False,
    }
    evidence = {
        "schemaVersion": "bfs.nativeCpuAdaptiveQualityCostEvidence.v0.1", "experimentId": spec["experimentId"],
        "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["toolFreezeCommit"], "tools": receipt["tools"],
        "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "transitiveD6Spec": {"uri": str(d6_spec_path.relative_to(root)), "sha256": sha256_file(d6_spec_path)},
        "parentObservations": receipt["parentObservations"], "sourceObservations": receipt["sourceObservations"],
        "sourcePostObservations": receipt["sourcePostObservations"], "blenderObservation": receipt["blenderObservation"],
        "diskAdmission": receipt["diskAdmission"], "schedule": receipt["schedule"], "runObservations": run_observations,
        "sampleCountMeasurements": sample_measurements, "fixed128ParentComparisons": fixed_comparisons,
        "repeatComparisons": repeat_comparisons, "referenceIndependence": reference_independence,
        "referenceFloors": reference_floors, "beautyMeasurements": beauty_measurements,
        "dataSemanticMeasurements": data_measurements, "auxiliaryPassMeasurements": auxiliary_measurements,
        "candidateMeasurements": candidate_measurements, "costMeasurements": cost_measurements,
        "qualityGate": spec["beautyQualityGate"], "dataSemanticGate": thresholds,
        "operationCounts": operation_counts, "nonClaims": spec["nonClaims"],
    }
    summaries, selected = replay_selection(evidence, spec)
    evidence["profileSummaries"], evidence["selectedProfileId"] = summaries, selected
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence))
    evidence["baseFailure"] = validate(evidence, spec, d5_spec)
    evidence["attacks"] = run_attacks(evidence, spec, d5_spec)
    evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"])
    valid = evidence["baseFailure"] is None and evidence["attacksPassed"] == len(spec["attacks"])
    if not valid:
        evidence["verdict"] = spec["selectionRule"]["invalidVerdict"]
    else:
        evidence["verdict"] = spec["selectionRule"]["positiveVerdict"] if selected else spec["selectionRule"]["negativeVerdict"]
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D1_RESULT verdict={evidence['verdict']} selected={selected or 'none'} attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={evidence['baseFailure'] or 'none'}", flush=True)


if __name__ == "__main__":
    main()
