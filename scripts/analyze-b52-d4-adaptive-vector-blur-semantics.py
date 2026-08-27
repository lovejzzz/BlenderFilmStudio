#!/usr/bin/env python3
"""Analyze frozen Blender 5.2 Vector Blur outputs for B52-D4."""

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


PREREGISTRATION_COMMIT = "173a2ed294b79b32089bc518249303da3cc5bb17"
SPEC_SHA256 = "e8635a1507eb5a5e8bfd950dc02fc4630a7202fd9af14b5510a991359f2e439f"
EXPECTED_VECTOR_BLUR_INPUTS = [
    {"identifier": "Image", "name": "Image", "type": "RGBA"},
    {"identifier": "Speed", "name": "Speed", "type": "VECTOR"},
    {"identifier": "Z", "name": "Depth", "type": "VALUE"},
    {"identifier": "Samples", "name": "Samples", "type": "INT"},
    {"identifier": "Shutter", "name": "Shutter", "type": "VALUE"},
]
EXPECTED_LINKS = sorted([
    "BFS_BASELINE.Combined->BFS_VECTOR_BLUR.Image",
    "BFS_SPEED_SOURCE.Vector->BFS_VECTOR_BLUR.Speed",
    "BFS_BASELINE.Depth->BFS_VECTOR_BLUR.Z",
    "BFS_VECTOR_BLUR.Image->BFS_GROUP_OUTPUT.Socket_0",
])


def load_module(path: Path, name: str):
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
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


def load_single_exr(path: Path) -> dict:
    image = oiio.ImageBuf(str(path), 0, 0)
    if not image.initialized:
        raise RuntimeError(image.geterror() or f"cannot read {path}")
    spec = image.spec()
    pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
    return {
        "pixels": pixels,
        "channels": list(spec.channelnames),
        "subimageName": str(spec.getattribute("oiio:subimagename") or "subimage-0"),
        "subimages": int(image.nsubimages),
    }


def expected_pair_keys(spec: dict) -> list[tuple[str, str]]:
    return [(profile, variant) for profile in spec["inputs"]["candidateProfiles"] for variant in spec["inputs"]["variants"]]


def expected_cell_keys(spec: dict) -> list[tuple[str, str, int]]:
    profiles = [spec["inputs"]["baselineProfile"], *spec["inputs"]["candidateProfiles"]]
    return [(profile, variant, repeat) for profile in profiles for variant in spec["inputs"]["variants"] for repeat in (1, 2)]


def energy_fraction(error_map: np.ndarray, mask: np.ndarray) -> tuple[float, float, float]:
    energy = np.square(error_map.astype(np.float64), dtype=np.float64)
    total = float(np.sum(energy, dtype=np.float64))
    inside = float(np.sum(energy[mask], dtype=np.float64))
    return total, inside, 1.0 if total == 0.0 else inside / total


def measure_vector(baseline: np.ndarray, candidate: np.ndarray, influence: np.ndarray, stable: np.ndarray) -> tuple[dict, np.ndarray]:
    if baseline.shape[-1] < 4 or candidate.shape != baseline.shape:
        return {"measurementTotal": False}, np.zeros(baseline.shape[:2], dtype=np.float64)
    pair_a = np.linalg.norm(candidate[..., :2].astype(np.float64) - baseline[..., :2].astype(np.float64), axis=-1)
    pair_b = np.linalg.norm(candidate[..., 2:4].astype(np.float64) - baseline[..., 2:4].astype(np.float64), axis=-1)
    error = np.maximum(pair_a, pair_b)
    total, inside, fraction = energy_fraction(error, influence)
    stable_energy = float(np.sum(np.square(error[stable], dtype=np.float64), dtype=np.float64))
    return {
        **finite_stats(error, "endpointError"),
        "changedPixelsAbove1Over65536": int(np.count_nonzero(error > 1.0 / 65536.0)),
        "changedPixelsAbove1Over4096": int(np.count_nonzero(error > 1.0 / 4096.0)),
        "totalSquaredEnergy": total,
        "influenceRegionSquaredEnergy": inside,
        "influenceRegionEnergyFraction": fraction,
        "stableInteriorSquaredEnergy": stable_energy,
        "stableInteriorEnergyFraction": 0.0 if total == 0.0 else stable_energy / total,
        "measurementTotal": bool(error.size) and np.isfinite(error).all(),
    }, error


def measure_blur(baseline: np.ndarray, candidate: np.ndarray, influence: np.ndarray, vector_measurement: dict, gate: dict) -> tuple[dict, np.ndarray]:
    if baseline.shape != candidate.shape or baseline.ndim != 3 or baseline.shape[-1] < 4:
        return {"measurementTotal": False, "classifierPassed": False}, np.zeros(baseline.shape[:2], dtype=np.float64)
    rgb_error = np.max(np.abs(candidate[..., :3].astype(np.float64) - baseline[..., :3].astype(np.float64)), axis=-1)
    alpha_error = np.abs(candidate[..., 3].astype(np.float64) - baseline[..., 3].astype(np.float64))
    total, inside, fraction = energy_fraction(rgb_error, influence)
    stats = finite_stats(rgb_error, "rgbAbsoluteError")
    outside = int(np.count_nonzero((rgb_error > 1.0 / 4096.0) & ~influence))
    total_measurement = bool(rgb_error.size) and np.isfinite(rgb_error).all() and np.isfinite(alpha_error).all()
    passed = (
        total_measurement
        and vector_measurement.get("influenceRegionEnergyFraction", -1.0) >= gate["vectorInfluenceRegionEnergyFractionMinimum"]
        and stats["rgbAbsoluteErrorP99"] <= gate["rgbAbsoluteErrorP99Maximum"]
        and stats["rgbAbsoluteErrorMaximum"] <= gate["rgbAbsoluteErrorMaximum"]
        and stats["rgbAbsoluteErrorRmse"] <= gate["rgbRmseMaximum"]
        and float(np.max(alpha_error)) <= gate["alphaAbsoluteErrorMaximum"]
        and fraction >= gate["blurInfluenceRegionEnergyFractionMinimum"]
        and outside == gate["outsideInfluencePixelsAbove1Over4096"]
    )
    return {
        **stats,
        "alphaAbsoluteErrorMaximum": float(np.max(alpha_error)),
        "changedPixelsAbove1Over65536": int(np.count_nonzero(rgb_error > 1.0 / 65536.0)),
        "changedPixelsAbove1Over4096": int(np.count_nonzero(rgb_error > 1.0 / 4096.0)),
        "totalSquaredEnergy": total,
        "influenceRegionSquaredEnergy": inside,
        "influenceRegionEnergyFraction": fraction,
        "outsideInfluencePixelsAbove1Over4096": outside,
        "measurementTotal": total_measurement,
        "classifierPassed": passed,
    }, rgb_error


def write_png(path: Path, pixels: np.ndarray) -> None:
    array = np.ascontiguousarray(pixels, dtype=np.uint8)
    output = oiio.ImageOutput.create(str(path))
    if output is None:
        raise RuntimeError(f"cannot create PNG output: {path}")
    image_spec = oiio.ImageSpec(array.shape[1], array.shape[0], 3, oiio.UINT8)
    image_spec.channelnames = ["R", "G", "B"]
    if not output.open(str(path), image_spec) or not output.write_image(array) or not output.close():
        raise RuntimeError(output.geterror() or f"cannot write {path}")


def write_diagnostic(output_directory: Path, canonical_directory: str, variant: str, profile: str, kind: str, values: np.ndarray, mapping: dict, sources: dict) -> dict:
    normalized = np.clip((values.astype(np.float64) - float(mapping["minimum"])) / (float(mapping["clipMaximum"]) - float(mapping["minimum"])), 0.0, 1.0)
    encoded = np.rint(np.stack([normalized, np.square(normalized), np.zeros_like(normalized)], axis=-1) * 255.0).astype(np.uint8)
    filename = f"{variant.lower()}--{profile.lower()}--{kind}.png"
    png_path = output_directory / filename
    sidecar_path = png_path.with_suffix(".json")
    write_png(png_path, encoded)
    reopened = oiio.ImageBuf(str(png_path))
    reopened_pixels = np.ascontiguousarray(np.asarray(reopened.get_pixels(oiio.UINT8), dtype=np.uint8))
    if reopened_pixels.shape != encoded.shape or not np.array_equal(reopened_pixels, encoded):
        raise RuntimeError(f"diagnostic decoded mismatch: {png_path}")
    sidecar = {
        "schemaVersion": "bfs.adaptiveVectorBlurDiagnostic.v0.1",
        "experimentId": "B52-D4",
        "variantId": variant,
        "profileId": profile,
        "kind": kind,
        "mapping": mapping,
        "encoding": {"normalization": "t = clip((value - minimum) / (clipMaximum - minimum), 0, 1)", "rgb": ["R = t", "G = t * t", "B = 0"], "quantization": "round-to-nearest uint8 after multiplication by 255", "fileFormat": "PNG RGB8"},
        "dimensions": [int(values.shape[1]), int(values.shape[0])],
        "decodedValueSha256": array_hash(values),
        "decodedRgb8Sha256": hashlib.sha256(encoded.tobytes()).hexdigest(),
        "sources": sources,
    }
    png_binding = {"uri": f"{canonical_directory}/{filename}", "sha256": sha256_file(png_path), "bytes": png_path.stat().st_size}
    sidecar["png"] = png_binding
    sidecar_path.write_bytes(canonical_bytes(sidecar))
    return {
        "variantId": variant,
        "profileId": profile,
        "kind": kind,
        "mapping": mapping,
        "decodedValueSha256": sidecar["decodedValueSha256"],
        "decodedRgb8Sha256": sidecar["decodedRgb8Sha256"],
        "png": png_binding,
        "sidecar": {"uri": f"{canonical_directory}/{sidecar_path.name}", "sha256": sha256_file(sidecar_path), "bytes": sidecar_path.stat().st_size},
        "identityMatch": True,
    }


def replay_classification(evidence: dict, spec: dict) -> tuple[list[dict], list[str]]:
    indexed = {(item["profileId"], item["variantId"]): item for item in evidence["candidateMeasurements"]}
    summaries, selected = [], []
    for profile in spec["inputs"]["candidateProfiles"]:
        variants = []
        for variant in spec["inputs"]["variants"]:
            row = indexed.get((profile, variant))
            repeat = next((item for item in evidence["repeatComparisons"] if item["profileId"] == profile and item["variantId"] == variant), None)
            passed = bool(row and repeat and repeat["decodedExact"] and row["blurOutput"]["classifierPassed"])
            variants.append({"variantId": variant, "decodedRepeatExact": bool(repeat and repeat["decodedExact"]), "vectorClassifierPassed": bool(row and row["blurOutput"]["classifierPassed"]), "passed": passed})
        tolerable = all(item["passed"] for item in variants)
        summaries.append({"profileId": profile, "variants": variants, "vectorTaskTolerable": tolerable})
        if tolerable:
            selected.append(profile)
    return summaries, selected


def finite_measurement_tree(value: object) -> bool:
    if isinstance(value, dict):
        return all(finite_measurement_tree(item) for item in value.values())
    if isinstance(value, list):
        return all(finite_measurement_tree(item) for item in value)
    return not isinstance(value, float) or math.isfinite(value)


def hash_payload(evidence: dict) -> dict:
    excluded = {"evidenceCoreHash", "baseFailure", "attacks", "attacksPassed", "verdict"}
    return {key: value for key, value in evidence.items() if key not in excluded}


def validate(evidence: dict, spec: dict, common) -> str | None:
    if not evidence["specObservation"]["match"] or len(evidence["parentObservations"]) != 5 or not all(item["match"] for item in evidence["parentObservations"]):
        return "PARENT_IDENTITY"
    if len(evidence["parentArtifactObservations"]) != 54 or not all(item["match"] for item in evidence["parentArtifactObservations"]):
        return "PARENT_ARTIFACT_IDENTITY"
    if not evidence["runtimeObservations"]["blender"]["match"]:
        return "BLENDER_IDENTITY"
    if not evidence["runtimeObservations"]["ocio"]["match"]:
        return "OCIO_IDENTITY"
    if len(evidence["runObservations"]) != 36 or not all(item["rnaMatch"] and item["rnaInputs"] == EXPECTED_VECTOR_BLUR_INPUTS for item in evidence["runObservations"]):
        return "BLENDER52_RNA_CONTRACT"
    if not all(item["graphMatch"] and item["graphLinks"] == EXPECTED_LINKS and item["graphNodeCount"] == 4 for item in evidence["runObservations"]):
        return "COMPOSITOR_GRAPH_CONTRACT"
    if not all(item["inputIsolationMatch"] for item in evidence["runObservations"]):
        return "INPUT_ISOLATION"
    expected_cells = expected_cell_keys(spec)
    observed_cells = [(item["profileId"], item["variantId"], item["repeat"]) for item in evidence["runObservations"]]
    pids = [item["pid"] for item in evidence["runObservations"]]
    if observed_cells != expected_cells or len(set(pids)) != 36:
        return "PROCESS_ROSTER"
    if not all(item["exitCode"] == 0 and item["reportHashMatch"] for item in evidence["runObservations"]):
        return "PROCESS_EXIT_STATUS"
    if len(evidence["outputObservations"]) != 36 or not all(item["identityMatch"] and item["shape"] == [288, 512, 4] and item["finite"] for item in evidence["outputObservations"]):
        return "OUTPUT_TOTALITY"
    if len(evidence["repeatComparisons"]) != 18 or not all(item["decodedExact"] for item in evidence["repeatComparisons"]):
        return "REPEAT_IDENTITY"
    if len(evidence["baselineEffects"]) != 2 or not all(item["passed"] for item in evidence["baselineEffects"]):
        return "BASELINE_EFFECT"
    if len(evidence["regions"]) != 2 or len(evidence["influenceRegions"]) != 2 or not all(item["d3MaskIdentityMatch"] for item in evidence["regions"]) or any(item["radiusOverflow"] for item in evidence["influenceRegions"]):
        return "VECTOR_ENERGY_TOTALITY"
    if len(evidence["candidateMeasurements"]) != 16 or [(item["profileId"], item["variantId"]) for item in evidence["candidateMeasurements"]] != expected_pair_keys(spec):
        return "VECTOR_ENERGY_TOTALITY"
    if not all(item["vectorInput"].get("measurementTotal") and finite_measurement_tree(item["vectorInput"]) for item in evidence["candidateMeasurements"]):
        return "VECTOR_ENERGY_TOTALITY"
    if not all(item["blurOutput"].get("measurementTotal") and finite_measurement_tree(item["blurOutput"]) for item in evidence["candidateMeasurements"]):
        return "BLUR_MEASUREMENT_TOTALITY"
    expected_diagnostics = {(profile, variant, kind) for profile in spec["diagnostics"]["profiles"] for variant in spec["inputs"]["variants"] for kind in spec["diagnostics"]["mapsPerPair"]}
    observed_diagnostics = {(item["profileId"], item["variantId"], item["kind"]) for item in evidence["diagnostics"]}
    if len(evidence["diagnostics"]) != spec["diagnostics"]["pngCount"] or observed_diagnostics != expected_diagnostics or not all(item["identityMatch"] for item in evidence["diagnostics"]):
        return "DIAGNOSTIC_TOTALITY"
    summaries, selected = replay_classification(evidence, spec)
    if evidence["profileSummaries"] != summaries or evidence["vectorTaskTolerableProfiles"] != selected:
        return "CLASSIFICATION_REPLAY"
    if evidence["operationCounts"] != spec["operationBoundary"]:
        return "OPERATION_BOUNDARY"
    if len(evidence["sourcePostObservations"]) != 18 or not all(item["match"] for item in evidence["sourcePostObservations"]):
        return "SOURCE_IMMUTABILITY"
    if evidence.get("evidenceCoreHash") != common.canonical_hash(hash_payload(evidence)):
        return "EVIDENCE_SELF_HASH"
    return None


def run_attacks(evidence: dict, spec: dict, common) -> list[dict]:
    rows = []
    def add(identifier: str, reason: str, mutate, rehash: bool = True) -> None:
        clone = copy.deepcopy(evidence)
        mutate(clone)
        clone["evidenceCoreHash"] = common.canonical_hash(hash_payload(clone)) if rehash else "0" * 64
        observed = validate(clone, spec, common)
        rows.append({"id": identifier, "expectedReason": reason, "observedReason": observed, "passed": observed == reason})
    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_ARTIFACT", "PARENT_ARTIFACT_IDENTITY", lambda x: x["parentArtifactObservations"][0].update(match=False))
    add("A03_BLENDER", "BLENDER_IDENTITY", lambda x: x["runtimeObservations"]["blender"].update(match=False))
    add("A04_OCIO", "OCIO_IDENTITY", lambda x: x["runtimeObservations"]["ocio"].update(match=False))
    add("A05_RNA", "BLENDER52_RNA_CONTRACT", lambda x: x["runObservations"][0].update(rnaMatch=False))
    add("A06_GRAPH", "COMPOSITOR_GRAPH_CONTRACT", lambda x: x["runObservations"][0].update(graphMatch=False))
    add("A07_ISOLATION", "INPUT_ISOLATION", lambda x: x["runObservations"][0].update(inputIsolationMatch=False))
    add("A08_PROCESS", "PROCESS_ROSTER", lambda x: x["runObservations"][1].update(pid=x["runObservations"][0]["pid"]))
    add("A09_EXIT", "PROCESS_EXIT_STATUS", lambda x: x["runObservations"][0].update(exitCode=1))
    add("A10_OUTPUT", "OUTPUT_TOTALITY", lambda x: x["outputObservations"][0].update(identityMatch=False))
    add("A11_REPEAT", "REPEAT_IDENTITY", lambda x: x["repeatComparisons"][0].update(decodedExact=False))
    add("A12_BASELINE", "BASELINE_EFFECT", lambda x: x["baselineEffects"][0].update(passed=False))
    add("A13_VECTOR", "VECTOR_ENERGY_TOTALITY", lambda x: x["candidateMeasurements"][0]["vectorInput"].update(measurementTotal=False))
    add("A14_BLUR", "BLUR_MEASUREMENT_TOTALITY", lambda x: x["candidateMeasurements"][0]["blurOutput"].update(measurementTotal=False))
    add("A15_DIAGNOSTIC", "DIAGNOSTIC_TOTALITY", lambda x: x["diagnostics"][0].update(identityMatch=False))
    add("A16_CLASSIFICATION", "CLASSIFICATION_REPLAY", lambda x: x["profileSummaries"][0].update(vectorTaskTolerable=not x["profileSummaries"][0]["vectorTaskTolerable"]))
    add("A17_OPERATION", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(cyclesRayRenders=1))
    add("A18_IMMUTABILITY", "SOURCE_IMMUTABILITY", lambda x: x["sourcePostObservations"][0].update(match=False))
    add("A19_HASH", "EVIDENCE_SELF_HASH", lambda x: None, rehash=False)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.spec.resolve().parent.parent
    common = load_module(root / "scripts/analyze-b52-native-cpu-adaptive-quality-cost.py", "bfs_b52_common")
    d3 = load_module(root / "scripts/analyze-b52-d3-adaptive-payload-semantics.py", "bfs_b52_d3")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    expected_preregistration = {"commit": PREREGISTRATION_COMMIT, "specUri": "specs/adaptive-vector-blur-semantics-derivation.v0.1.json", "specSha256": SPEC_SHA256}
    if sha256_file(args.spec) != SPEC_SHA256 or receipt.get("preregistration") != expected_preregistration:
        raise RuntimeError("B52-D4 preregistration identity differs")

    d3_spec = json.loads((root / spec["parents"]["d3Spec"]["uri"]).read_text(encoding="utf-8"))
    d3_result = json.loads((root / spec["parents"]["d3Result"]["uri"]).read_text(encoding="utf-8"))
    d2_result_path = root / d3_spec["parents"]["d2Result"]["uri"]
    d2_result = json.loads(d2_result_path.read_text(encoding="utf-8"))
    d6_spec_path = root / d2_result["transitiveD6Spec"]["uri"]
    d6_spec = json.loads(d6_spec_path.read_text(encoding="utf-8"))
    crypto_profile = d6_spec["cryptomatteProfile"]

    source_paths = {item["uri"]: root / item["uri"] for item in receipt["sourcePreObservations"]}
    source_loaded = {uri: common.load_exr(path) for uri, path in source_paths.items()}
    source_by_cell = {}
    for profile in [spec["inputs"]["baselineProfile"], *spec["inputs"]["candidateProfiles"]]:
        for variant in spec["inputs"]["variants"]:
            uri = f"{spec['inputs']['parentOutputRoot']}/{variant}_{profile}_R1/artifacts/production.exr"
            source_by_cell[(profile, variant)] = source_loaded[uri]

    d3_regions = {item["variantId"]: item for item in d3_result["regions"]}
    region_records, region_arrays, influence_records, influence_arrays = [], {}, [], {}
    for variant in spec["inputs"]["variants"]:
        baseline = source_by_cell[(spec["inputs"]["baselineProfile"], variant)]
        metadata = common.crypto_metadata(baseline, crypto_profile)
        decoded = common.decode_crypto(baseline, crypto_profile, metadata["manifest"])
        record, arrays = d3.derive_region(baseline, decoded, d3_spec)
        record.update({"variantId": variant, "baselineRunId": f"{variant}_{spec['inputs']['baselineProfile']}_R1", "d3MaskIdentityMatch": record["maskSha256"] == d3_regions[variant]["maskSha256"]})
        vector = baseline["parts"]["BFS_MASTER.Vector"].astype(np.float64)
        magnitude = np.maximum(np.linalg.norm(vector[..., :2], axis=-1), np.linalg.norm(vector[..., 2:4], axis=-1))
        finite = magnitude[np.isfinite(magnitude)]
        maximum = float(np.max(finite)) if finite.size else float("nan")
        radius = max(int(spec["influenceRegion"]["radiusMinimumPixels"]), int(math.ceil(maximum * float(spec["compositorMatrix"]["nodeGraph"]["vectorBlurInputs"]["Shutter"]))) + 1)
        overflow = radius > int(spec["influenceRegion"]["radiusMaximumPixels"])
        influence = d3.chebyshev_dilate(arrays["boundarySeed"], min(radius, int(spec["influenceRegion"]["radiusMaximumPixels"])))
        region_records.append(record)
        region_arrays[variant] = arrays
        influence_arrays[variant] = influence
        influence_records.append({"variantId": variant, "baselineMotionMagnitudeMaximum": maximum, "radiusPixels": radius, "radiusOverflow": overflow, "pixelCount": int(np.count_nonzero(influence)), "maskSha256": mask_hash(influence)})

    run_observations, output_observations, outputs = [], [], {}
    for run in receipt["runs"]:
        report = run.get("report")
        body = {key: value for key, value in report.items() if key != "reportHash"} if isinstance(report, dict) else {}
        report_hash_match = isinstance(report, dict) and report.get("reportHash") == common.canonical_hash(body)
        expected_baseline_uri = f"{spec['inputs']['parentOutputRoot']}/{run['variantId']}_{spec['inputs']['baselineProfile']}_R1/artifacts/production.exr"
        expected_speed_uri = f"{spec['inputs']['parentOutputRoot']}/{run['variantId']}_{run['profileId']}_R1/artifacts/production.exr"
        input_isolation = bool(report and report["inputs"]["baseline"]["uri"] == expected_baseline_uri and report["inputs"]["speedSource"]["uri"] == expected_speed_uri and report["inputs"]["imagePass"] == "Combined" and report["inputs"]["depthPass"] == "Depth" and report["inputs"]["speedPass"] == "Vector")
        run_observations.append({
            "cellId": run["cellId"], "profileId": run["profileId"], "variantId": run["variantId"], "repeat": run["repeat"], "pid": run["pid"], "exitCode": run["exitCode"],
            "reportHashMatch": report_hash_match, "rnaMatch": bool(report and report["rna"]["match"]), "rnaInputs": report["rna"]["inputs"] if report else None,
            "graphMatch": bool(report and report["graph"]["match"]), "graphLinks": report["graph"]["links"] if report else None, "graphNodeCount": report["graph"]["nodeCount"] if report else None,
            "inputIsolationMatch": input_isolation,
        })
        output_uri = report["output"]["uri"]
        output_path = root / output_uri
        loaded = load_single_exr(output_path)
        outputs[(run["profileId"], run["variantId"], run["repeat"])] = loaded
        observed_sha, observed_bytes = sha256_file(output_path), output_path.stat().st_size
        output_observations.append({
            "cellId": run["cellId"], "profileId": run["profileId"], "variantId": run["variantId"], "repeat": run["repeat"], "uri": output_uri,
            "expectedSha256": report["output"]["sha256"], "observedSha256": observed_sha, "expectedBytes": report["output"]["bytes"], "observedBytes": observed_bytes,
            "identityMatch": observed_sha == report["output"]["sha256"] and observed_bytes == report["output"]["bytes"], "shape": list(loaded["pixels"].shape), "channels": loaded["channels"], "subimageName": loaded["subimageName"], "subimages": loaded["subimages"], "finite": bool(np.isfinite(loaded["pixels"]).all()), "decodedPixelSha256": array_hash(loaded["pixels"]),
        })

    repeat_comparisons = []
    for profile in [spec["inputs"]["baselineProfile"], *spec["inputs"]["candidateProfiles"]]:
        for variant in spec["inputs"]["variants"]:
            left, right = outputs[(profile, variant, 1)]["pixels"], outputs[(profile, variant, 2)]["pixels"]
            repeat_comparisons.append({"profileId": profile, "variantId": variant, "leftRepeat": 1, "rightRepeat": 2, "leftPixelSha256": array_hash(left), "rightPixelSha256": array_hash(right), "decodedExact": left.shape == right.shape and np.array_equal(left, right)})

    baseline_effects = []
    threshold = float(spec["baselineEffectGate"]["minimumChangedPixelsAbove"]["absoluteError"])
    for variant in spec["inputs"]["variants"]:
        combined = source_by_cell[(spec["inputs"]["baselineProfile"], variant)]["parts"]["BFS_MASTER.Combined"]
        blurred = outputs[(spec["inputs"]["baselineProfile"], variant, 1)]["pixels"]
        rgb_error = np.max(np.abs(blurred[..., :3].astype(np.float64) - combined[..., :3].astype(np.float64)), axis=-1)
        changed = int(np.count_nonzero(rgb_error > threshold))
        baseline_effects.append({"variantId": variant, **finite_stats(rgb_error, "rgbAbsoluteError"), "threshold": threshold, "changedPixelCount": changed, "minimumChangedPixelCount": spec["baselineEffectGate"]["minimumChangedPixelsAbove"]["count"], "passed": changed >= spec["baselineEffectGate"]["minimumChangedPixelsAbove"]["count"]})

    candidate_measurements, diagnostics = [], []
    diagnostics_directory = args.output.parent / "diagnostics"
    diagnostics_directory.mkdir(parents=True, exist_ok=True)
    canonical_diagnostics_directory = f"{spec['outputRoot']}/diagnostics"
    diagnostic_profiles = set(spec["diagnostics"]["profiles"])
    gate = spec["blurOutputTask"]["derivationClassifier"]
    for profile, variant in expected_pair_keys(spec):
        baseline_source = source_by_cell[(spec["inputs"]["baselineProfile"], variant)]
        candidate_source = source_by_cell[(profile, variant)]
        vector_measurement, vector_map = measure_vector(baseline_source["parts"]["BFS_MASTER.Vector"], candidate_source["parts"]["BFS_MASTER.Vector"], influence_arrays[variant], region_arrays[variant]["stableInterior"])
        baseline_blur = outputs[(spec["inputs"]["baselineProfile"], variant, 1)]["pixels"]
        candidate_blur = outputs[(profile, variant, 1)]["pixels"]
        blur_measurement, blur_map = measure_blur(baseline_blur, candidate_blur, influence_arrays[variant], vector_measurement, gate)
        baseline_output = next(item for item in output_observations if item["profileId"] == spec["inputs"]["baselineProfile"] and item["variantId"] == variant and item["repeat"] == 1)
        candidate_output = next(item for item in output_observations if item["profileId"] == profile and item["variantId"] == variant and item["repeat"] == 1)
        candidate_measurements.append({"profileId": profile, "variantId": variant, "vectorInput": vector_measurement, "blurOutput": blur_measurement})
        if profile in diagnostic_profiles:
            maps = {"vector-endpoint-error": vector_map, "vector-blur-rgb-maximum-absolute-error": blur_map}
            sources = {"baselineSource": {"uri": f"{spec['inputs']['parentOutputRoot']}/{variant}_{spec['inputs']['baselineProfile']}_R1/artifacts/production.exr", "sha256": receipt["sourceIdentityByUri"][f"{spec['inputs']['parentOutputRoot']}/{variant}_{spec['inputs']['baselineProfile']}_R1/artifacts/production.exr"]}, "candidateSource": {"uri": f"{spec['inputs']['parentOutputRoot']}/{variant}_{profile}_R1/artifacts/production.exr", "sha256": receipt["sourceIdentityByUri"][f"{spec['inputs']['parentOutputRoot']}/{variant}_{profile}_R1/artifacts/production.exr"]}, "baselineOutput": {"uri": baseline_output["uri"], "sha256": baseline_output["observedSha256"]}, "candidateOutput": {"uri": candidate_output["uri"], "sha256": candidate_output["observedSha256"]}}
            for kind in spec["diagnostics"]["mapsPerPair"]:
                diagnostics.append(write_diagnostic(diagnostics_directory, canonical_diagnostics_directory, variant, profile, kind, maps[kind], spec["diagnostics"]["mappings"][kind], sources))

    evidence = {
        "schemaVersion": "bfs.adaptiveVectorBlurSemanticsDerivationEvidence.v0.1", "experimentId": spec["experimentId"], "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["toolFreezeCommit"], "tools": receipt["tools"],
        "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "specObservation": receipt["specObservation"], "parentObservations": receipt["parentObservations"], "parentArtifactObservations": receipt["parentArtifactObservations"], "runtimeObservations": receipt["runtimeObservations"],
        "d3Invariants": {"verdict": d3_result["verdict"], "futureHoldoutCandidates": d3_result["futureHoldoutCandidates"], "baseFailure": d3_result["baseFailure"], "attacksPassed": d3_result["attacksPassed"]},
        "regions": region_records, "influenceRegions": influence_records, "runObservations": run_observations, "outputObservations": output_observations, "repeatComparisons": repeat_comparisons, "baselineEffects": baseline_effects,
        "candidateMeasurements": candidate_measurements, "diagnostics": diagnostics, "classificationGate": gate, "sourcePostObservations": receipt["sourcePostObservations"], "operationCounts": copy.deepcopy(spec["operationBoundary"]), "nonClaims": spec["nonClaims"], "parentDisclosure": spec["parentDisclosure"],
    }
    evidence["profileSummaries"], evidence["vectorTaskTolerableProfiles"] = replay_classification(evidence, spec)
    evidence["evidenceCoreHash"] = common.canonical_hash(hash_payload(evidence))
    evidence["baseFailure"] = validate(evidence, spec, common)
    evidence["attacks"] = run_attacks(evidence, spec, common)
    evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"])
    valid = evidence["baseFailure"] is None and evidence["attacksPassed"] == len(spec["attacks"])
    evidence["verdict"] = spec["decisionRule"]["usableVerdict"] if valid else spec["decisionRule"]["invalidVerdict"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D4_RESULT verdict={evidence['verdict']} tolerable={len(evidence['vectorTaskTolerableProfiles'])} attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={evidence['baseFailure'] or 'none'}", flush=True)


if __name__ == "__main__":
    main()
