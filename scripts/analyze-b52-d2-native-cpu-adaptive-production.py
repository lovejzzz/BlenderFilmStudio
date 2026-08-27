#!/usr/bin/env python3
"""Analyze, attack and decide the B52-D2 adaptive-production holdout."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import platform
import statistics
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


PRODUCTION_PASSES = [
    "BFS_MASTER.Combined", "BFS_MASTER.Depth", "BFS_MASTER.Normal", "BFS_MASTER.Vector",
    "BFS_MASTER.CryptoObject00", "BFS_MASTER.CryptoObject01", "BFS_MASTER.CryptoObject02",
]
SAMPLE_COUNT = "BFS_MASTER.Debug Sample Count"
EXPECTED_ROSTER = [
    "BFS_MASTER.Combined", "BFS_MASTER.Depth", "BFS_MASTER.Normal", "BFS_MASTER.Vector",
    SAMPLE_COUNT, "BFS_MASTER.CryptoObject00", "BFS_MASTER.CryptoObject01", "BFS_MASTER.CryptoObject02",
]
BASELINE_ID = "PROD_T010_M0"
PREREGISTRATION_COMMIT = "5467a234c98d4e632705f32ad1209b1703105266"
SPEC_SHA256 = "41288927f5f12c2488b9e9396ff943a152b736157264d156bfea26806eb5273e"


def load_d1_library(root: Path):
    path = root / "scripts/analyze-b52-native-cpu-adaptive-quality-cost.py"
    module_spec = importlib.util.spec_from_file_location("bfs_b52_d1_analysis_library", path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("cannot load B52-D1 analysis library")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def expected_matrix(spec: dict, d5_spec: dict) -> list[dict]:
    rows: list[dict] = []
    order = 1
    variants = {item["id"]: item for item in d5_spec["variants"]}
    for profile in spec["profiles"]:
        for variant_id, variant in variants.items():
            for repeat in range(1, spec["repeatsPerProfileVariant"] + 1):
                rows.append({
                    "runId": f"{variant_id}_{profile['id']}_R{repeat}",
                    "variant": variant_id,
                    "source": variant["source"],
                    "profile": profile["id"],
                    "role": profile["role"],
                    "repeat": repeat,
                    "order": order,
                })
                order += 1
    return rows


def settings_valid(settings: dict, profile: dict, render_profile: dict, base_seed: int) -> bool:
    exact = {
        "engine": render_profile["engine"],
        "cyclesDevice": "CPU",
        "resolution": [*render_profile["resolution"], 100],
        "pixelCount": render_profile["resolution"][0] * render_profile["resolution"][1],
        "maxSamples": profile["maxSamples"],
        "seedOffset": profile["seedOffset"],
        "seed": base_seed + profile["seedOffset"],
        "animatedSeed": render_profile["animatedSeed"],
        "adaptive": profile["adaptive"],
        "minSamples": profile["minSamples"],
        "denoising": render_profile["denoising"],
        "motionBlur": render_profile["motionBlur"],
        "persistentData": render_profile["persistentData"],
        "threadsMode": "FIXED",
        "threads": render_profile["cpuThreads"],
        "sampleCountPass": True,
    }
    return (
        all(settings.get(key) == value for key, value in exact.items())
        and math.isclose(float(settings.get("noiseThreshold", -1)), float(profile["noiseThreshold"]), rel_tol=1e-6, abs_tol=1e-8)
    )


def hash_payload(evidence: dict) -> dict:
    excluded = {"evidenceCoreHash", "baseFailure", "attacks", "attacksPassed", "verdict"}
    return {key: value for key, value in evidence.items() if key not in excluded}


def derive_cost_and_mechanism(run_observations: list[dict], sample_measurements: list[dict], spec: dict, d5_spec: dict) -> tuple[list[dict], list[dict]]:
    observation_by_run = {item["runId"]: item for item in run_observations}
    sample_by_run = {item["runId"]: item for item in sample_measurements}
    variants = [item["id"] for item in d5_spec["variants"]]
    repeats = spec["repeatsPerProfileVariant"]
    costs: list[dict] = []
    mechanisms: list[dict] = []
    for profile in spec["profiles"]:
        if profile["role"] != "CANDIDATE":
            continue
        for variant_id in variants:
            controls = [observation_by_run[f"{variant_id}_{BASELINE_ID}_R{repeat}"] for repeat in range(1, repeats + 1)]
            candidates = [observation_by_run[f"{variant_id}_{profile['id']}_R{repeat}"] for repeat in range(1, repeats + 1)]
            control_render = statistics.median(item["renderSeconds"] for item in controls)
            candidate_render = statistics.median(item["renderSeconds"] for item in candidates)
            control_wall = statistics.median(item["freshProcessWallSeconds"] for item in controls)
            candidate_wall = statistics.median(item["freshProcessWallSeconds"] for item in candidates)
            costs.append({
                "variantId": variant_id,
                "profileId": profile["id"],
                "repeats": repeats,
                "controlMedianRenderSeconds": control_render,
                "candidateMedianRenderSeconds": candidate_render,
                "renderSavingFraction": 1.0 - candidate_render / control_render,
                "controlMedianFreshProcessWallSeconds": control_wall,
                "candidateMedianFreshProcessWallSeconds": candidate_wall,
                "freshProcessWallSavingFraction": 1.0 - candidate_wall / control_wall,
                "medianSaveSeconds": statistics.median(item["saveSeconds"] for item in candidates),
                "medianArtifactBytes": statistics.median(item["artifact"]["bytes"] for item in candidates),
            })
            control_samples = statistics.median(sample_by_run[f"{variant_id}_{BASELINE_ID}_R{repeat}"]["meanEffectiveSamples"] for repeat in range(1, repeats + 1))
            candidate_samples = statistics.median(sample_by_run[f"{variant_id}_{profile['id']}_R{repeat}"]["meanEffectiveSamples"] for repeat in range(1, repeats + 1))
            mechanisms.append({
                "variantId": variant_id,
                "profileId": profile["id"],
                "controlMedianMeanEffectiveSamples": control_samples,
                "candidateMedianMeanEffectiveSamples": candidate_samples,
                "savingFraction": 1.0 - candidate_samples / control_samples,
                "passed": candidate_samples < control_samples,
            })
    return costs, mechanisms


def replay_selection(evidence: dict, spec: dict) -> tuple[list[dict], str | None]:
    cost_floor = spec["costGate"]["minimumMedianRenderSavingFractionVersusProductionBaseline"]
    summaries: list[dict] = []
    for profile in spec["profiles"]:
        if profile["role"] != "CANDIDATE":
            continue
        rows = [item for item in evidence["candidateMeasurements"] if item["profileId"] == profile["id"]]
        costs = [item for item in evidence["costMeasurements"] if item["profileId"] == profile["id"]]
        mechanisms = [item for item in evidence["sampleMechanismMeasurements"] if item["profileId"] == profile["id"]]
        all_payload = len(rows) == 6 and all(item["combinedPass"] for item in rows)
        per_variant_cost = len(costs) == 2 and all(item["renderSavingFraction"] >= cost_floor for item in costs)
        mechanism_pass = len(mechanisms) == 2 and all(item["passed"] for item in mechanisms)
        variant_medians = [item["candidateMedianRenderSeconds"] for item in costs]
        summaries.append({
            "profileId": profile["id"],
            "noiseThreshold": profile["noiseThreshold"],
            "minSamples": profile["minSamples"],
            "allQualityAndPayloadGates": all_payload,
            "perVariantCostGate": per_variant_cost,
            "sampleMechanismGate": mechanism_pass,
            "eligible": all_payload and per_variant_cost and mechanism_pass,
            "crossVariantMedianRenderSeconds": statistics.median(variant_medians) if len(variant_medians) == 2 else None,
            "worstVariantRenderSavingFraction": min((item["renderSavingFraction"] for item in costs), default=None),
        })
    eligible = [item for item in summaries if item["eligible"]]
    eligible.sort(key=lambda item: (
        item["crossVariantMedianRenderSeconds"], item["noiseThreshold"], -item["minSamples"], item["profileId"]
    ))
    return summaries, eligible[0]["profileId"] if eligible else None


def validate(evidence: dict, spec: dict, d5_spec: dict, d1) -> str | None:
    if not all(item["match"] for item in [*evidence["parentObservations"], evidence["specObservation"]]): return "PARENT_IDENTITY"
    if not evidence["blenderObservation"]["match"]: return "BLENDER_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"] + evidence["sourcePostObservations"]): return "SOURCE_IDENTITY"
    if not all(item["match"] for item in evidence["referenceObservations"] + evidence["referencePostObservations"]): return "REFERENCE_IDENTITY"
    if evidence["diskAdmission"]["status"] != "ACCEPTED": return "DISK_ADMISSION"
    expected_schedule = expected_matrix(spec, d5_spec)
    expected_run_ids = [item["runId"] for item in expected_schedule]
    if evidence["schedule"] != expected_schedule or [item["runId"] for item in evidence["runObservations"]] != expected_run_ids: return "MATRIX_TOTALITY"
    if len({item["processPid"] for item in evidence["runObservations"]}) != len(evidence["runObservations"]): return "FRESH_PROCESS"
    if not all(item["processPid"] == item["runnerObservedPid"] for item in evidence["runObservations"]): return "FRESH_PROCESS"
    if not all(item["deviceValid"] for item in evidence["runObservations"]): return "CPU_DEVICE"
    if not all(item["settingsValid"] and item["operationReplayValid"] and item["sourceIdentityMatch"] for item in evidence["runObservations"]): return "ADAPTIVE_SETTINGS"
    if not all(item["rosterMatch"] and item["allPartsFinite"] for item in evidence["runObservations"]): return "PASS_ROSTER"
    if [item["runId"] for item in evidence["sampleCountMeasurements"]] != expected_run_ids or not all(item["valid"] for item in evidence["sampleCountMeasurements"]): return "SAMPLE_COUNT_VALIDITY"
    expected_baseline_ids = [item["runId"] for item in expected_schedule if item["role"] == "PRODUCTION_BASELINE"]
    if [item["runId"] for item in evidence["baselineMeasurements"]] != expected_baseline_ids or not all(item["passed"] for item in evidence["baselineMeasurements"]): return "BASELINE_VALIDITY"
    expected_repeat_keys = {(variant["id"], profile["id"]) for profile in spec["profiles"] for variant in d5_spec["variants"]}
    if {(item["variantId"], item["profileId"]) for item in evidence["repeatComparisons"]} != expected_repeat_keys or not all(item["allThreeRepeatsExact"] for item in evidence["repeatComparisons"]): return "REPEAT_EXACTNESS"
    if len(evidence["referenceIndependence"]) != 2 or not all(item["threeDistinct"] for item in evidence["referenceIndependence"]): return "REFERENCE_INDEPENDENCE"
    floors_valid = len(evidence["referenceFloors"]) == 2 and all(
        item["ensembleMean"]["rgbRms"] > 0.0
        and set(item["floor"]) == set(spec["beautyQualityGate"]["metrics"])
        and all(math.isfinite(value) and value > 0.0 for value in item["floor"].values())
        for item in evidence["referenceFloors"]
    )
    if not floors_valid or len(evidence["beautyMeasurements"]) != len(expected_run_ids) or {item["runId"] for item in evidence["beautyMeasurements"]} != set(expected_run_ids) or not all(item["measurementTotal"] for item in evidence["beautyMeasurements"]): return "BEAUTY_MEASUREMENT_TOTALITY"
    expected_candidates = sum(item["role"] == "CANDIDATE" for item in spec["profiles"]) * spec["matrix"]["variants"] * spec["repeatsPerProfileVariant"]
    expected_candidate_ids = [item["runId"] for item in expected_schedule if item["role"] == "CANDIDATE"]
    if len(expected_candidate_ids) != expected_candidates: return "MATRIX_TOTALITY"
    if [item["runId"] for item in evidence["dataSemanticMeasurements"]] != expected_candidate_ids or not all(item["measurementTotal"] and item["structuralValid"] for item in evidence["dataSemanticMeasurements"]): return "DATA_SEMANTIC_TOTALITY"
    if [item["runId"] for item in evidence["auxiliaryPassMeasurements"]] != expected_candidate_ids or not all(set(item["passes"]) == set(spec["auxiliaryPassGate"]["passes"]) and item["allExact"] == all(item["passes"].values()) for item in evidence["auxiliaryPassMeasurements"]): return "AUXILIARY_PASS_TOTALITY"
    beauty_by_run = {item["runId"]: item for item in evidence["beautyMeasurements"]}
    data_by_run = {item["runId"]: item for item in evidence["dataSemanticMeasurements"]}
    auxiliary_by_run = {item["runId"]: item for item in evidence["auxiliaryPassMeasurements"]}
    sample_by_run = {item["runId"]: item for item in evidence["sampleCountMeasurements"]}
    if [item["runId"] for item in evidence["candidateMeasurements"]] != expected_candidate_ids: return "COST_MEASUREMENT_TOTALITY"
    for item in evidence["candidateMeasurements"]:
        run_id = item["runId"]
        if run_id not in beauty_by_run or run_id not in data_by_run or run_id not in auxiliary_by_run or run_id not in sample_by_run: return "COST_MEASUREMENT_TOTALITY"
        flags = {
            "beautyPass": beauty_by_run[run_id]["passed"],
            "dataSemanticPass": data_by_run[run_id]["passed"] and data_by_run[run_id]["structuralValid"],
            "auxiliaryPass": auxiliary_by_run[run_id]["allExact"],
            "sampleCountPass": sample_by_run[run_id]["valid"],
        }
        if any(item[key] != value for key, value in flags.items()) or item["combinedPass"] != all(flags.values()): return "COST_MEASUREMENT_TOTALITY"
    expected_costs, expected_mechanisms = derive_cost_and_mechanism(evidence["runObservations"], evidence["sampleCountMeasurements"], spec, d5_spec)
    if evidence["costMeasurements"] != expected_costs or evidence["sampleMechanismMeasurements"] != expected_mechanisms: return "COST_MEASUREMENT_TOTALITY"
    summaries, selected = replay_selection(evidence, spec)
    if evidence["profileSummaries"] != summaries or evidence["selectedProfileId"] != selected: return "SELECTION_REPLAY"
    if not all(item["artifactIdentityMatch"] for item in evidence["runObservations"]): return "ARTIFACT_IDENTITY"
    if evidence["operationCounts"] != spec["operationBoundary"]: return "OPERATION_BOUNDARY"
    if evidence.get("evidenceCoreHash") != d1.canonical_hash(hash_payload(evidence)): return "EVIDENCE_SELF_HASH"
    return None


def run_attacks(evidence: dict, spec: dict, d5_spec: dict, d1) -> list[dict]:
    rows: list[dict] = []
    def add(identifier: str, reason: str, mutate, rehash: bool = True) -> None:
        clone = copy.deepcopy(evidence)
        mutate(clone)
        clone["evidenceCoreHash"] = d1.canonical_hash(hash_payload(clone)) if rehash else "0" * 64
        observed = validate(clone, spec, d5_spec, d1)
        rows.append({"id": identifier, "expectedReason": reason, "observedReason": observed, "passed": observed == reason})
    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_BLENDER", "BLENDER_IDENTITY", lambda x: x["blenderObservation"].update(match=False))
    add("A03_SOURCE", "SOURCE_IDENTITY", lambda x: x["sourceObservations"][0].update(match=False))
    add("A04_REFERENCE", "REFERENCE_IDENTITY", lambda x: x["referenceObservations"][0].update(match=False))
    add("A05_DISK", "DISK_ADMISSION", lambda x: x["diskAdmission"].update(status="BLOCKED"))
    add("A06_MATRIX", "MATRIX_TOTALITY", lambda x: x["schedule"].pop())
    add("A07_FRESH", "FRESH_PROCESS", lambda x: x["runObservations"][1].update(processPid=x["runObservations"][0]["processPid"]))
    add("A08_CPU", "CPU_DEVICE", lambda x: x["runObservations"][0].update(deviceValid=False))
    add("A09_SETTINGS", "ADAPTIVE_SETTINGS", lambda x: x["runObservations"][0].update(settingsValid=False))
    add("A10_ROSTER", "PASS_ROSTER", lambda x: x["runObservations"][0].update(rosterMatch=False))
    add("A11_SAMPLE", "SAMPLE_COUNT_VALIDITY", lambda x: x["sampleCountMeasurements"][0].update(valid=False))
    add("A12_BASELINE", "BASELINE_VALIDITY", lambda x: x["baselineMeasurements"][0].update(passed=False))
    add("A13_REPEAT", "REPEAT_EXACTNESS", lambda x: x["repeatComparisons"][-1].update(allThreeRepeatsExact=False))
    add("A14_REFERENCE_INDEPENDENCE", "REFERENCE_INDEPENDENCE", lambda x: x["referenceIndependence"][0].update(threeDistinct=False))
    add("A15_BEAUTY", "BEAUTY_MEASUREMENT_TOTALITY", lambda x: x["beautyMeasurements"][0].update(measurementTotal=False))
    add("A16_DATA", "DATA_SEMANTIC_TOTALITY", lambda x: x["dataSemanticMeasurements"][0].update(measurementTotal=False))
    add("A17_AUX", "AUXILIARY_PASS_TOTALITY", lambda x: x["auxiliaryPassMeasurements"][0]["passes"].pop("BFS_MASTER.Normal"))
    add("A18_COST", "COST_MEASUREMENT_TOTALITY", lambda x: x["costMeasurements"].pop())
    add("A19_SELECTION", "SELECTION_REPLAY", lambda x: x.update(selectedProfileId="UNREGISTERED"))
    add("A20_ARTIFACT", "ARTIFACT_IDENTITY", lambda x: x["runObservations"][0].update(artifactIdentityMatch=False))
    add("A21_BOUNDARY", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(metalRenders=1))
    add("A22_HASH", "EVIDENCE_SELF_HASH", lambda x: None, rehash=False)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.spec.resolve().parent.parent
    d1 = load_d1_library(root)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    expected_preregistration = {
        "commit": PREREGISTRATION_COMMIT,
        "specUri": "specs/native-cpu-adaptive-production-holdout.v0.1.json",
        "specSha256": SPEC_SHA256,
    }
    if d1.sha256_file(args.spec) != SPEC_SHA256 or receipt.get("preregistration") != expected_preregistration:
        raise RuntimeError("B52-D2 preregistration identity differs")
    d5_spec = json.loads((root / spec["parents"]["d5Spec"]["uri"]).read_text(encoding="utf-8"))
    d6_result = json.loads((root / spec["parents"]["d6Result"]["uri"]).read_text(encoding="utf-8"))
    d6_spec_path = root / d6_result["preregistration"]["specUri"]
    d6_spec = json.loads(d6_spec_path.read_text(encoding="utf-8"))
    thresholds = {group: spec["dataSemanticGate"][group] for group in ("cryptomatte", "depth")}
    frozen_thresholds = {group: {key: d6_result["thresholds"][group][key] for key in values} for group, values in thresholds.items()}
    if d6_result["thresholds"] != d6_spec["productionSemanticProfile"] or frozen_thresholds != thresholds:
        raise RuntimeError("B52-D2 D6 semantic thresholds differ")
    crypto_profile = d6_spec["cryptomatteProfile"]
    profiles = {item["id"]: item for item in spec["profiles"]}
    variants = {item["id"]: item for item in d5_spec["variants"]}
    registered_passes = {f"BFS_MASTER.{name}" for name in spec["renderProfile"]["passes"]}
    if set(EXPECTED_ROSTER) != registered_passes:
        raise RuntimeError("B52-D2 registered pass set differs")
    h1_spec = json.loads((root / d5_spec["parents"]["h1Spec"]["uri"]).read_text(encoding="utf-8"))
    expected_cpu = h1_spec["nativeBlender"]["cpuDevice"]

    loaded: dict[str, dict] = {}
    reports: dict[str, dict] = {}
    paths: dict[str, Path] = {}
    metadata: dict[str, dict] = {}
    for run in receipt["runs"]:
        report = run["report"]
        path = args.receipt.parent / run["runId"] / "artifacts" / report["artifact"]["uri"]
        image = d1.load_exr(path)
        loaded[run["runId"]], reports[run["runId"]], paths[run["runId"]] = image, report, path
        metadata[run["runId"]] = d1.crypto_metadata(image, crypto_profile)

    manifests = {variant_id: metadata[f"{variant_id}_{BASELINE_ID}_R1"]["manifest"] for variant_id in variants}
    if not all(isinstance(value, dict) and value for value in manifests.values()):
        raise RuntimeError("B52-D2 baseline manifest absent")
    decoded_crypto: dict[str, dict] = {}
    run_observations: list[dict] = []
    sample_measurements: list[dict] = []
    for run in receipt["runs"]:
        run_id, image, report = run["runId"], loaded[run["runId"]], reports[run["runId"]]
        profile, variant = profiles[run["profile"]], variants[run["variant"]]
        source = d5_spec["sources"][variant["source"]]
        meta, manifest = metadata[run_id], manifests[run["variant"]]
        crypto = d1.decode_crypto(image, crypto_profile, manifest)
        decoded_crypto[run_id] = crypto
        structural = {
            "metadataValid": meta["valid"],
            "manifestConsistent": meta["manifest"] == manifest,
            "unresolvedRankEntries": crypto["unresolvedRankEntries"],
            "coverageRangeInvalidEntries": crypto["coverageRangeInvalidEntries"],
            "coverageSumViolationPixels": crypto["coverageSumViolationPixels"],
            "rankOrderViolationPairs": crypto["rankOrderViolationPairs"],
            "duplicateNonzeroIdPairs": crypto["duplicateNonzeroIdPairs"],
        }
        structural_valid = structural["metadataValid"] and structural["manifestConsistent"] and all(
            structural[key] == 0 for key in structural if key not in {"metadataValid", "manifestConsistent"}
        )
        count_pixels = image["parts"][SAMPLE_COUNT].astype(np.float64).reshape(-1)
        finite = bool(np.isfinite(count_pixels).all())
        in_range = bool(finite and np.all(count_pixels >= 0.0) and np.all(count_pixels <= 1.0))
        sample_measurements.append({
            "runId": run_id,
            "variantId": run["variant"],
            "profileId": run["profile"],
            "repeat": run["repeat"],
            "finite": finite,
            "inRange": in_range,
            "stoppedAtLeastOnePixel": bool(np.any(count_pixels < 1.0)),
            "minimumNormalizedSamples": float(np.min(count_pixels)),
            "p50NormalizedSamples": d1.percentile(count_pixels, 0.50),
            "p95NormalizedSamples": d1.percentile(count_pixels, 0.95),
            "p99NormalizedSamples": d1.percentile(count_pixels, 0.99),
            "maximumNormalizedSamples": float(np.max(count_pixels)),
            "meanEffectiveSamples": float(np.mean(count_pixels) * profile["maxSamples"]),
            "fractionAtMaxSamples": float(np.count_nonzero(count_pixels == 1.0) / count_pixels.size),
            "valid": finite and in_range,
        })
        selected = report["device"]["selected"]
        device_valid = len(selected) == 1 and selected[0]["id"] == expected_cpu["id"] and selected[0]["type"] == "CPU"
        path = paths[run_id]
        run_observations.append({
            "runId": run_id,
            "variantId": run["variant"],
            "sourceId": run["source"],
            "profileId": run["profile"],
            "role": run["role"],
            "repeat": run["repeat"],
            "order": run["order"],
            "processPid": report["process"]["pid"],
            "runnerObservedPid": run["pid"],
            "freshProcessWallSeconds": run["elapsedSeconds"],
            "renderSeconds": report["renderSeconds"],
            "saveSeconds": report["saveSeconds"],
            "peakSelfRssBytes": report["peakSelfRssBytes"],
            "sourceIdentityMatch": report["source"] == {"uri": source["blendUri"], "sha256": source["blendSha256"], "bytes": source["blendBytes"]},
            "operationReplayValid": d1.operation_replay_valid(report["operationReplay"], variant["operations"]),
            "selectedDevices": selected,
            "deviceValid": device_valid,
            "settings": report["settings"],
            "settingsValid": settings_valid(report["settings"], profile, spec["renderProfile"], int(report["bindings"]["baseShotSeed"])),
            "roster": image["roster"],
            "rosterMatch": image["roster"] == EXPECTED_ROSTER,
            "allPartsFinite": all(np.isfinite(value).all() for value in image["parts"].values()),
            "cryptomatteStructure": structural,
            "cryptomatteStructuralValid": structural_valid,
            "passPixelSha256": {name: d1.pixel_hash(image["parts"][name]) for name in EXPECTED_ROSTER},
            "artifact": {"uri": str(path.relative_to(root)), "sha256": d1.sha256_file(path), "bytes": path.stat().st_size},
            "artifactIdentityMatch": report["artifact"]["sha256"] == d1.sha256_file(path) and report["artifact"]["bytes"] == path.stat().st_size,
        })

    repeat_comparisons: list[dict] = []
    for profile in spec["profiles"]:
        for variant_id in variants:
            ids = [f"{variant_id}_{profile['id']}_R{repeat}" for repeat in range(1, spec["repeatsPerProfileVariant"] + 1)]
            pair_passes = []
            for right in ids[1:]:
                passes = {name: np.array_equal(loaded[ids[0]]["parts"][name], loaded[right]["parts"][name]) for name in EXPECTED_ROSTER}
                pair_passes.append({"leftRunId": ids[0], "rightRunId": right, "passes": passes, "allEightPassesExact": all(passes.values())})
            repeat_comparisons.append({
                "variantId": variant_id,
                "profileId": profile["id"],
                "runIds": ids,
                "pairs": pair_passes,
                "allThreeRepeatsExact": all(item["allEightPassesExact"] for item in pair_passes),
            })

    reference_independence: list[dict] = []
    reference_floors: list[dict] = []
    beauty_measurements: list[dict] = []
    for variant_binding in spec["variants"]:
        variant_id = variant_binding["id"]
        reference_images = [(item["id"], d1.load_exr(root / item["uri"])) for item in variant_binding["references"]]
        hashes = [d1.pixel_hash(image["parts"]["BFS_MASTER.Combined"]) for _, image in reference_images]
        reference_independence.append({"variantId": variant_id, "referenceIds": [item[0] for item in reference_images], "combinedPixelSha256": hashes, "threeDistinct": len(set(hashes)) == 3})
        ensemble = np.mean(np.stack([image["parts"]["BFS_MASTER.Combined"].astype(np.float64) for _, image in reference_images]), axis=0)
        rms = float(np.sqrt(np.mean(np.square(ensemble[..., :3]))))
        mask, edge_count, cutoff = d1.edge_mask(ensemble[..., :3])
        reference_rows = [d1.beauty_metrics(image["parts"]["BFS_MASTER.Combined"], ensemble, mask, rms) for _, image in reference_images]
        floor = {name: max(row[name] for row in reference_rows) for name in spec["beautyQualityGate"]["metrics"]}
        reference_floors.append({
            "variantId": variant_id,
            "referenceIds": [item[0] for item in reference_images],
            "ensembleMean": {"dtype": "float64-le", "shape": list(ensemble.shape), "sha256": hashlib.sha256(np.ascontiguousarray(ensemble.astype("<f8")).tobytes()).hexdigest(), "rgbRms": rms},
            "edgeMask": {"pixelCount": edge_count, "gradientCutoff": cutoff},
            "referenceMetrics": reference_rows,
            "floor": floor,
        })
        for profile in spec["profiles"]:
            for repeat in range(1, spec["repeatsPerProfileVariant"] + 1):
                run_id = f"{variant_id}_{profile['id']}_R{repeat}"
                measured = d1.beauty_metrics(loaded[run_id]["parts"]["BFS_MASTER.Combined"], ensemble, mask, rms)
                multiples = {name: measured[name] / floor[name] for name in spec["beautyQualityGate"]["metrics"]}
                passed = all(value <= spec["beautyQualityGate"]["maximumFloorMultiple"] for value in multiples.values())
                beauty_measurements.append({
                    "runId": run_id,
                    "variantId": variant_id,
                    "profileId": profile["id"],
                    "repeat": repeat,
                    "metricsAgainstEnsemble": measured,
                    "floorMultiples": multiples,
                    "passed": passed,
                    "measurementTotal": all(math.isfinite(value) for value in [*measured.values(), *multiples.values()]),
                })

    beauty_by_run = {item["runId"]: item for item in beauty_measurements}
    sample_by_run = {item["runId"]: item for item in sample_measurements}
    repeat_by_key = {(item["variantId"], item["profileId"]): item for item in repeat_comparisons}
    baseline_measurements = []
    observation_by_run = {item["runId"]: item for item in run_observations}
    for variant_id in variants:
        repeat_exact = repeat_by_key[(variant_id, BASELINE_ID)]["allThreeRepeatsExact"]
        for repeat in range(1, spec["repeatsPerProfileVariant"] + 1):
            run_id = f"{variant_id}_{BASELINE_ID}_R{repeat}"
            checks = {
                "beautyPass": beauty_by_run[run_id]["passed"],
                "sampleCountValid": sample_by_run[run_id]["valid"],
                "cryptomatteStructuralValid": observation_by_run[run_id]["cryptomatteStructuralValid"],
                "threeRepeatsExact": repeat_exact,
            }
            baseline_measurements.append({"runId": run_id, "variantId": variant_id, "repeat": repeat, **checks, "passed": all(checks.values())})

    data_measurements: list[dict] = []
    auxiliary_measurements: list[dict] = []
    candidate_measurements: list[dict] = []
    for profile in spec["profiles"]:
        if profile["role"] != "CANDIDATE":
            continue
        for variant_id in variants:
            for repeat in range(1, spec["repeatsPerProfileVariant"] + 1):
                run_id = f"{variant_id}_{profile['id']}_R{repeat}"
                control_id = f"{variant_id}_{BASELINE_ID}_R{repeat}"
                reference = {"crypto": decoded_crypto[control_id], "depth": loaded[control_id]["parts"]["BFS_MASTER.Depth"][..., 0]}
                candidate = {"crypto": decoded_crypto[run_id], "depth": loaded[run_id]["parts"]["BFS_MASTER.Depth"][..., 0]}
                semantic = d1.compare_semantics(candidate, reference, thresholds, crypto_profile)
                structure = observation_by_run[run_id]["cryptomatteStructuralValid"]
                semantic.update({
                    "runId": run_id, "controlRunId": control_id, "variantId": variant_id, "profileId": profile["id"], "repeat": repeat,
                    "structuralValid": structure,
                    "measurementTotal": bool(semantic["cryptomatte"]["objects"] and semantic["depth"]["stableSurfacePixelCount"] > 0),
                })
                data_measurements.append(semantic)
                passes = {name: np.array_equal(loaded[run_id]["parts"][name], loaded[control_id]["parts"][name]) for name in spec["auxiliaryPassGate"]["passes"]}
                auxiliary = {"runId": run_id, "controlRunId": control_id, "variantId": variant_id, "profileId": profile["id"], "repeat": repeat, "passes": passes, "allExact": all(passes.values())}
                auxiliary_measurements.append(auxiliary)
                flags = {
                    "beautyPass": beauty_by_run[run_id]["passed"],
                    "dataSemanticPass": semantic["passed"] and structure,
                    "auxiliaryPass": auxiliary["allExact"],
                    "sampleCountPass": sample_by_run[run_id]["valid"],
                }
                candidate_measurements.append({"runId": run_id, "variantId": variant_id, "profileId": profile["id"], "repeat": repeat, **flags, "combinedPass": all(flags.values())})

    cost_measurements, sample_mechanisms = derive_cost_and_mechanism(run_observations, sample_measurements, spec, d5_spec)

    operation_counts = {
        "nativeBlenderProcesses": sum(item.startswith("NATIVE_BLENDER_PROCESS_") for item in receipt["runtimeOperations"]),
        "renders": len(receipt["runs"]),
        "reusedReferenceExrs": len(receipt["referenceObservations"]),
        "sourceBlendFilesModified": 0,
        "parentExrsModified": 0,
        "metalRenders": 0,
        "dockerRuns": 0,
        "downloadsDuringFormalRun": 0,
        "modelCalls": 0,
        "videoModelCalls": 0,
        "networkRequired": False,
    }
    tools = copy.deepcopy(receipt["tools"])
    for binding in tools.values():
        binding["freezeCommit"] = receipt["toolFreezeCommit"]
    evidence = {
        "schemaVersion": "bfs.nativeCpuAdaptiveProductionEvidence.v0.1",
        "experimentId": spec["experimentId"],
        "preregistration": receipt["preregistration"],
        "toolFreezeCommit": receipt["toolFreezeCommit"],
        "tools": tools,
        "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "transitiveD6Spec": {"uri": str(d6_spec_path.relative_to(root)), "sha256": d1.sha256_file(d6_spec_path)},
        "parentObservations": receipt["parentObservations"],
        "specObservation": receipt["specObservation"],
        "sourceObservations": receipt["sourceObservations"],
        "sourcePostObservations": receipt["sourcePostObservations"],
        "referenceObservations": receipt["referenceObservations"],
        "referencePostObservations": receipt["referencePostObservations"],
        "blenderObservation": receipt["blenderObservation"],
        "diskAdmission": receipt["diskAdmission"],
        "schedule": receipt["schedule"],
        "runObservations": run_observations,
        "sampleCountMeasurements": sample_measurements,
        "baselineMeasurements": baseline_measurements,
        "repeatComparisons": repeat_comparisons,
        "referenceIndependence": reference_independence,
        "referenceFloors": reference_floors,
        "beautyMeasurements": beauty_measurements,
        "dataSemanticMeasurements": data_measurements,
        "auxiliaryPassMeasurements": auxiliary_measurements,
        "candidateMeasurements": candidate_measurements,
        "sampleMechanismMeasurements": sample_mechanisms,
        "costMeasurements": cost_measurements,
        "qualityGate": spec["beautyQualityGate"],
        "dataSemanticGate": thresholds,
        "operationCounts": operation_counts,
        "nonClaims": spec["nonClaims"],
    }
    summaries, selected = replay_selection(evidence, spec)
    evidence["profileSummaries"], evidence["selectedProfileId"] = summaries, selected
    evidence["evidenceCoreHash"] = d1.canonical_hash(hash_payload(evidence))
    evidence["baseFailure"] = validate(evidence, spec, d5_spec, d1)
    evidence["attacks"] = run_attacks(evidence, spec, d5_spec, d1)
    evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"])
    valid = evidence["baseFailure"] is None and evidence["attacksPassed"] == len(spec["attacks"])
    if not valid:
        evidence["verdict"] = spec["selectionRule"]["invalidVerdict"]
    else:
        evidence["verdict"] = spec["selectionRule"]["positiveVerdict"] if selected else spec["selectionRule"]["negativeVerdict"]
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D2_RESULT verdict={evidence['verdict']} selected={selected or 'none'} attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={evidence['baseFailure'] or 'none'}", flush=True)


if __name__ == "__main__":
    main()
