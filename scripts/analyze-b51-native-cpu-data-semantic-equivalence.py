"""Decode and adversarially analyze the preregistered B51-D6 data-pass semantics."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


DATA_PASSES = [
    "BFS_MASTER.Depth",
    "BFS_MASTER.CryptoObject00",
    "BFS_MASTER.CryptoObject01",
    "BFS_MASTER.CryptoObject02",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def percentile(values: np.ndarray, quantile: float) -> float | None:
    if not values.size:
        return None
    return float(np.quantile(values, quantile, method="higher"))


def load_exr(path: Path) -> dict:
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror() or f"cannot read {path}")
    roster: list[str] = []
    parts: dict[str, np.ndarray] = {}
    metadata: dict[str, object] = {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        if not image.initialized:
            raise RuntimeError(image.geterror() or f"cannot read subimage {index} in {path}")
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        roster.append(name)
        parts[name] = pixels
        if index == 0:
            metadata = {item.name: item.value for item in spec.extra_attribs if item.name.startswith("cryptomatte/")}
    return {"roster": roster, "parts": parts, "metadata": metadata}


def pixel_hash(pixels: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(pixels, dtype="<f4").tobytes()).hexdigest()


def crypto_metadata(loaded: dict, spec: dict) -> dict:
    profile = spec["cryptomatteProfile"]
    prefix = f"cryptomatte/{profile['metadataKey']}"
    raw = loaded["metadata"]
    manifest_text = raw.get(f"{prefix}/manifest")
    try:
        manifest = json.loads(manifest_text) if isinstance(manifest_text, str) else None
    except json.JSONDecodeError:
        manifest = None
    valid = (
        raw.get(f"{prefix}/name") == profile["layerName"]
        and raw.get(f"{prefix}/hash") == profile["hash"]
        and raw.get(f"{prefix}/conversion") == profile["conversion"]
        and isinstance(manifest, dict)
        and bool(manifest)
        and all(isinstance(name, str) and isinstance(value, str) and len(value) == 8 for name, value in manifest.items())
    )
    return {
        "key": profile["metadataKey"],
        "name": raw.get(f"{prefix}/name"),
        "hash": raw.get(f"{prefix}/hash"),
        "conversion": raw.get(f"{prefix}/conversion"),
        "manifest": manifest,
        "valid": valid,
    }


def decode_crypto(loaded: dict, spec: dict, manifest: dict[str, str]) -> dict:
    ids: list[np.ndarray] = []
    coverage: list[np.ndarray] = []
    for part_name, id_channel, coverage_channel in spec["cryptomatteProfile"]["rankChannels"]:
        pixels = loaded["parts"][part_name]
        ids.append(np.ascontiguousarray(pixels[..., id_channel], dtype="<f4").view("<u4"))
        coverage.append(np.ascontiguousarray(pixels[..., coverage_channel], dtype="<f4"))
    id_stack = np.stack(ids, axis=-1)
    coverage_stack = np.stack(coverage, axis=-1)
    epsilon = float(spec["cryptomatteProfile"]["coverageSumEpsilon"])
    low, high = spec["cryptomatteProfile"]["coverageRange"]
    active = coverage_stack > 0.0
    manifest_bits = {name: int(value, 16) for name, value in manifest.items()}
    known = np.isin(id_stack, np.asarray(list(manifest_bits.values()), dtype="<u4"))
    range_invalid = (~np.isfinite(coverage_stack)) | (coverage_stack < low) | (coverage_stack > high)
    coverage_sum = np.sum(coverage_stack.astype(np.float64), axis=-1)
    sum_invalid = coverage_sum > 1.0 + epsilon
    rank_invalid = coverage_stack[..., :-1] + epsilon < coverage_stack[..., 1:]
    duplicate_pairs = 0
    for left in range(id_stack.shape[-1]):
        for right in range(left + 1, id_stack.shape[-1]):
            duplicate_pairs += int(np.count_nonzero(active[..., left] & active[..., right] & (id_stack[..., left] == id_stack[..., right])))
    unresolved = int(np.count_nonzero(active & ~known))
    mattes = {
        name: np.sum(np.where(id_stack == bits, coverage_stack, 0.0).astype(np.float64), axis=-1)
        for name, bits in manifest_bits.items()
    }
    return {
        "ids": id_stack,
        "coverage": coverage_stack,
        "mattes": mattes,
        "manifestBits": manifest_bits,
        "unresolvedRankEntries": unresolved,
        "coverageRangeInvalidEntries": int(np.count_nonzero(range_invalid)),
        "coverageSumViolationPixels": int(np.count_nonzero(sum_invalid)),
        "coverageSumMaximum": float(np.max(coverage_sum)),
        "rankOrderViolationPairs": int(np.count_nonzero(rank_invalid)),
        "duplicateNonzeroIdPairs": duplicate_pairs,
    }


def compare_reference(candidate: dict, reference: dict, spec: dict) -> dict:
    crypto_thresholds = spec["productionSemanticProfile"]["cryptomatte"]
    depth_thresholds = spec["productionSemanticProfile"]["depth"]
    crypto_profile = spec["cryptomatteProfile"]

    parent_ids = reference["crypto"]["ids"]
    parent_coverage = reference["crypto"]["coverage"]
    candidate_ids = candidate["crypto"]["ids"]
    candidate_coverage = candidate["crypto"]["coverage"]
    confident = parent_coverage[..., 0] >= crypto_profile["confidentDominantCoverage"]
    dominant_mismatch = int(np.count_nonzero(confident & (parent_ids[..., 0] != candidate_ids[..., 0])))

    objects: list[dict] = []
    transition_union = np.zeros(parent_ids.shape[:2], dtype=bool)
    for name in sorted(reference["crypto"]["mattes"]):
        parent_matte = reference["crypto"]["mattes"][name]
        candidate_matte = candidate["crypto"]["mattes"][name]
        visible = bool(np.any(parent_matte > 0.0))
        if not visible:
            continue
        transition = (parent_matte > 0.0) & (parent_matte < 1.0)
        transition_union |= transition
        absolute = np.abs(candidate_matte - parent_matte)
        hard_mismatch = int(np.count_nonzero((candidate_matte >= crypto_profile["hardMatteThreshold"]) != (parent_matte >= crypto_profile["hardMatteThreshold"])))
        maximum = float(np.max(absolute))
        p99 = percentile(absolute, 0.99)
        rmse = float(np.sqrt(np.mean(np.square(absolute, dtype=np.float64))))
        passed = (
            hard_mismatch <= crypto_thresholds["hardMatteMismatchPixelsPerVisibleObject"]
            and maximum <= crypto_thresholds["perVisibleObjectMatteMaxAbsoluteError"]
            and p99 is not None
            and p99 <= crypto_thresholds["perVisibleObjectMatteP99AbsoluteError"]
            and rmse <= crypto_thresholds["perVisibleObjectMatteRmse"]
        )
        objects.append({
            "name": name,
            "hardMatteMismatchPixels": hard_mismatch,
            "maxAbsoluteError": maximum,
            "p99AbsoluteError": p99,
            "rmse": rmse,
            "transitionPixelCount": int(np.count_nonzero(transition)),
            "passed": passed,
        })
    crypto_passed = (
        dominant_mismatch <= crypto_thresholds["confidentDominantIdMismatchPixels"]
        and bool(objects)
        and all(item["passed"] for item in objects)
    )

    parent_depth = reference["depth"]
    candidate_depth = candidate["depth"]
    sentinel = depth_thresholds["backgroundSentinelThreshold"]
    parent_foreground = parent_depth < sentinel
    candidate_foreground = candidate_depth < sentinel
    foreground_mismatch = int(np.count_nonzero(parent_foreground != candidate_foreground))
    stable = (
        parent_foreground
        & (parent_coverage[..., 0] >= crypto_profile["stableSurfaceCoverage"])
        & (parent_ids[..., 0] == candidate_ids[..., 0])
    )
    absolute_depth = np.abs(candidate_depth.astype(np.float64) - parent_depth.astype(np.float64))[stable]
    relative_depth = absolute_depth / np.maximum(np.abs(parent_depth.astype(np.float64)[stable]), 1e-6)
    p50_abs = percentile(absolute_depth, 0.50)
    p95_abs = percentile(absolute_depth, 0.95)
    p99_abs = percentile(absolute_depth, 0.99)
    max_abs = float(np.max(absolute_depth)) if absolute_depth.size else None
    p99_rel = percentile(relative_depth, 0.99)
    depth_passed = (
        foreground_mismatch <= depth_thresholds["foregroundMaskMismatchPixels"]
        and p99_abs is not None
        and max_abs is not None
        and p99_rel is not None
        and p99_abs <= depth_thresholds["stableSurfaceP99AbsoluteErrorMeters"]
        and max_abs <= depth_thresholds["stableSurfaceMaxAbsoluteErrorMeters"]
        and p99_rel <= depth_thresholds["stableSurfaceP99RelativeError"]
    )
    return {
        "cryptomatte": {
            "manifestObjectCount": len(reference["crypto"]["mattes"]),
            "visibleObjectCount": len(objects),
            "confidentParentPixelCount": int(np.count_nonzero(confident)),
            "confidentDominantIdMismatchPixels": dominant_mismatch,
            "transitionPixelCount": int(np.count_nonzero(transition_union)),
            "objects": objects,
            "passed": crypto_passed,
        },
        "depth": {
            "foregroundPixelCount": int(np.count_nonzero(parent_foreground)),
            "foregroundMaskMismatchPixels": foreground_mismatch,
            "stableSurfacePixelCount": int(np.count_nonzero(stable)),
            "stableSurfaceP50AbsoluteErrorMeters": p50_abs,
            "stableSurfaceP95AbsoluteErrorMeters": p95_abs,
            "stableSurfaceP99AbsoluteErrorMeters": p99_abs,
            "stableSurfaceMaxAbsoluteErrorMeters": max_abs,
            "stableSurfaceP99RelativeError": p99_rel,
            "passed": depth_passed,
        },
        "passed": crypto_passed and depth_passed,
    }


def hash_payload(evidence: dict) -> dict:
    excluded = {"evidenceCoreHash", "baseFailure", "attacks", "attacksPassed", "verdict"}
    return {key: value for key, value in evidence.items() if key not in excluded}


def validate(evidence: dict, spec: dict) -> str | None:
    if not all(item["match"] for item in evidence["d5BindingObservations"]): return "D5_BINDING_IDENTITY"
    if len(evidence["artifactObservations"]) != spec["evidenceGates"]["inputExrs"] or not all(item["match"] for item in evidence["artifactObservations"]): return "INPUT_ARTIFACT_IDENTITY"
    if not all(item["rosterMatch"] for item in evidence["inputObservations"]): return "PASS_ROSTER"
    if not all(item["allDataPassesExact"] for item in evidence["reference128Comparisons"]): return "REFERENCE_128_EXACTNESS"
    if not all(item["allDataPassesExact"] for item in evidence["doseRepeatComparisons"]): return "DOSE_REPEAT_EXACTNESS"
    if not all(item["metadataValid"] for item in evidence["inputObservations"]): return "CRYPTOMATTE_METADATA"
    if not all(item["manifestConsistent"] for item in evidence["inputObservations"]): return "CRYPTOMATTE_MANIFEST"
    if not all(item["unresolvedRankEntries"] == 0 for item in evidence["inputObservations"]): return "CRYPTOMATTE_ID_RESOLUTION"
    if not all(item["coverageRangeInvalidEntries"] == 0 for item in evidence["inputObservations"]): return "CRYPTOMATTE_COVERAGE_RANGE"
    if not all(item["coverageSumViolationPixels"] == 0 for item in evidence["inputObservations"]): return "CRYPTOMATTE_COVERAGE_SUM"
    if not all(item["rankOrderViolationPairs"] == 0 for item in evidence["inputObservations"]): return "CRYPTOMATTE_RANK_ORDER"
    if not all(item["duplicateNonzeroIdPairs"] == 0 for item in evidence["inputObservations"]): return "CRYPTOMATTE_DUPLICATE_ID"
    if not all(item["depthValid"] for item in evidence["inputObservations"]): return "DEPTH_SENTINEL"
    expected = spec["evidenceGates"]["variants"] * spec["evidenceGates"]["doses"] * spec["evidenceGates"]["repeatsPerDose"]
    if len(evidence["semanticMeasurements"]) != expected or not all(item["measurementTotal"] for item in evidence["semanticMeasurements"]): return "MEASUREMENT_TOTALITY"
    if evidence["operationCounts"] != spec["operationBoundary"]: return "OPERATION_BOUNDARY"
    if evidence.get("evidenceCoreHash") != canonical_hash(hash_payload(evidence)): return "EVIDENCE_SELF_HASH"
    return None


def run_attacks(evidence: dict, spec: dict) -> list[dict]:
    rows: list[dict] = []
    def add(identifier: str, reason: str, mutate, rehash: bool = True) -> None:
        clone = copy.deepcopy(evidence)
        mutate(clone)
        clone["evidenceCoreHash"] = canonical_hash(hash_payload(clone)) if rehash else "0" * 64
        observed = validate(clone, spec)
        rows.append({"id": identifier, "expectedReason": reason, "observedReason": observed, "passed": observed == reason})
    add("A01_D5_BINDING", "D5_BINDING_IDENTITY", lambda x: x["d5BindingObservations"][0].update(match=False))
    add("A02_ARTIFACT", "INPUT_ARTIFACT_IDENTITY", lambda x: x["artifactObservations"][0].update(match=False))
    add("A03_ROSTER", "PASS_ROSTER", lambda x: x["inputObservations"][0].update(rosterMatch=False))
    add("A04_REFERENCE", "REFERENCE_128_EXACTNESS", lambda x: x["reference128Comparisons"][0].update(allDataPassesExact=False))
    add("A05_REPEAT", "DOSE_REPEAT_EXACTNESS", lambda x: x["doseRepeatComparisons"][0].update(allDataPassesExact=False))
    add("A06_METADATA", "CRYPTOMATTE_METADATA", lambda x: x["inputObservations"][0].update(metadataValid=False))
    add("A07_MANIFEST", "CRYPTOMATTE_MANIFEST", lambda x: x["inputObservations"][0].update(manifestConsistent=False))
    add("A08_ID", "CRYPTOMATTE_ID_RESOLUTION", lambda x: x["inputObservations"][0].update(unresolvedRankEntries=1))
    add("A09_RANGE", "CRYPTOMATTE_COVERAGE_RANGE", lambda x: x["inputObservations"][0].update(coverageRangeInvalidEntries=1))
    add("A10_SUM", "CRYPTOMATTE_COVERAGE_SUM", lambda x: x["inputObservations"][0].update(coverageSumViolationPixels=1))
    add("A11_RANK", "CRYPTOMATTE_RANK_ORDER", lambda x: x["inputObservations"][0].update(rankOrderViolationPairs=1))
    add("A12_DUPLICATE", "CRYPTOMATTE_DUPLICATE_ID", lambda x: x["inputObservations"][0].update(duplicateNonzeroIdPairs=1))
    add("A13_DEPTH", "DEPTH_SENTINEL", lambda x: x["inputObservations"][0].update(depthValid=False))
    add("A14_TOTALITY", "MEASUREMENT_TOTALITY", lambda x: x["semanticMeasurements"].pop())
    add("A15_BOUNDARY", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(renders=1))
    add("A16_HASH", "EVIDENCE_SELF_HASH", lambda x: None, rehash=False)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preregistration-commit", required=True)
    parser.add_argument("--tool-freeze-commit", required=True)
    args = parser.parse_args()
    root = args.spec.resolve().parent.parent
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    d5_receipt = json.loads((root / spec["parents"]["d5Receipt"]["uri"]).read_text(encoding="utf-8"))
    d5_result = json.loads((root / spec["parents"]["d5Result"]["uri"]).read_text(encoding="utf-8"))
    d5_audit = json.loads((root / spec["parents"]["d5Audit"]["uri"]).read_text(encoding="utf-8"))

    d5_bindings = []
    for name in ("d5Spec", "d5Receipt", "d5Result", "d5Audit"):
        binding = spec["parents"][name]
        path = root / binding["uri"]
        observed = sha256_file(path) if path.is_file() else None
        semantic_match = True
        if name == "d5Result": semantic_match = d5_result.get("verdict") == binding["verdict"] and d5_result.get("exactDataSampleFloor") == binding["exactDataSampleFloor"]
        if name == "d5Audit": semantic_match = d5_audit.get("status") == binding["status"]
        d5_bindings.append({"name": name, "uri": binding["uri"], "expectedSha256": binding["sha256"], "observedSha256": observed, "semanticMatch": semantic_match, "match": observed == binding["sha256"] and semantic_match})

    variants = {item["id"]: item for item in spec["variants"]}
    runs = {item["runId"]: item for item in d5_receipt["runs"]}
    references: dict[str, dict] = {}
    manifests: dict[str, dict[str, str]] = {}
    reference_comparisons: list[dict] = []
    for variant_id, variant in variants.items():
        reference_path = root / spec["inputRoot"] / variant["referenceRunId"] / "artifacts" / "production.exr"
        reference_loaded = load_exr(reference_path)
        reference_meta = crypto_metadata(reference_loaded, spec)
        if not reference_meta["valid"]:
            raise RuntimeError(f"invalid reference Cryptomatte metadata: {variant_id}")
        manifest = reference_meta["manifest"]
        reference_crypto = decode_crypto(reference_loaded, spec, manifest)
        references[variant_id] = {"loaded": reference_loaded, "crypto": reference_crypto, "depth": reference_loaded["parts"]["BFS_MASTER.Depth"][..., 0]}
        manifests[variant_id] = manifest
        parent_path = root / variant["frozenParentExr"]["uri"]
        parent_loaded = load_exr(parent_path)
        comparisons = {name: np.array_equal(reference_loaded["parts"][name], parent_loaded["parts"][name]) for name in DATA_PASSES}
        reference_comparisons.append({"variantId": variant_id, "referenceRunId": variant["referenceRunId"], "parentUri": variant["frozenParentExr"]["uri"], "passes": comparisons, "allDataPassesExact": all(comparisons.values())})

    artifact_observations: list[dict] = []
    input_observations: list[dict] = []
    measurements: list[dict] = []
    pass_hashes: dict[str, dict[str, str]] = {}
    for samples in spec["sampleLadder"]:
        for variant_id in variants:
            for repeat in range(1, spec["repeatsPerVariantDose"] + 1):
                run_id = f"{variant_id}_S{samples:03d}_R{repeat}"
                run = runs[run_id]
                path = root / spec["inputRoot"] / run_id / "artifacts" / run["report"]["artifact"]["uri"]
                observed_hash = sha256_file(path) if path.is_file() else None
                observed_bytes = path.stat().st_size if path.is_file() else None
                expected_artifact = run["report"]["artifact"]
                artifact_observations.append({"runId": run_id, "uri": str(path.relative_to(root)), "expectedSha256": expected_artifact["sha256"], "observedSha256": observed_hash, "expectedBytes": expected_artifact["bytes"], "observedBytes": observed_bytes, "match": observed_hash == expected_artifact["sha256"] and observed_bytes == expected_artifact["bytes"]})
                loaded = load_exr(path)
                metadata = crypto_metadata(loaded, spec)
                manifest_consistent = metadata["manifest"] == manifests[variant_id]
                crypto = decode_crypto(loaded, spec, manifests[variant_id])
                depth = loaded["parts"]["BFS_MASTER.Depth"][..., 0]
                depth_valid = bool(np.isfinite(depth).all() and np.all(depth >= 0.0) and np.any(depth < spec["productionSemanticProfile"]["depth"]["backgroundSentinelThreshold"]))
                roster_match = loaded["roster"] == spec["expectedRoster"]
                hashes = {name: pixel_hash(loaded["parts"][name]) for name in DATA_PASSES}
                pass_hashes[run_id] = hashes
                input_observations.append({
                    "runId": run_id, "variantId": variant_id, "samples": samples, "repeat": repeat,
                    "roster": loaded["roster"], "rosterMatch": roster_match,
                    "metadata": {key: metadata[key] for key in ("key", "name", "hash", "conversion")},
                    "metadataValid": metadata["valid"], "manifestSha256": canonical_hash(metadata["manifest"]) if isinstance(metadata["manifest"], dict) else None,
                    "manifestConsistent": manifest_consistent, "manifestObjectCount": len(manifests[variant_id]),
                    "unresolvedRankEntries": crypto["unresolvedRankEntries"], "coverageRangeInvalidEntries": crypto["coverageRangeInvalidEntries"],
                    "coverageSumViolationPixels": crypto["coverageSumViolationPixels"], "coverageSumMaximum": crypto["coverageSumMaximum"],
                    "rankOrderViolationPairs": crypto["rankOrderViolationPairs"], "duplicateNonzeroIdPairs": crypto["duplicateNonzeroIdPairs"],
                    "depthValid": depth_valid, "dataPassPixelSha256": hashes,
                })
                candidate = {"crypto": crypto, "depth": depth}
                metric = compare_reference(candidate, references[variant_id], spec)
                metric.update({"runId": run_id, "variantId": variant_id, "samples": samples, "repeat": repeat, "measurementTotal": bool(metric["cryptomatte"]["objects"] and metric["depth"]["stableSurfacePixelCount"] > 0)})
                measurements.append(metric)

    repeat_comparisons = []
    for variant_id in variants:
        for samples in spec["sampleLadder"]:
            left_id = f"{variant_id}_S{samples:03d}_R1"
            right_id = f"{variant_id}_S{samples:03d}_R2"
            passes = {name: pass_hashes[left_id][name] == pass_hashes[right_id][name] for name in DATA_PASSES}
            repeat_comparisons.append({"variantId": variant_id, "samples": samples, "leftRunId": left_id, "rightRunId": right_id, "passes": passes, "allDataPassesExact": all(passes.values())})

    per_variant_floor: dict[str, int | None] = {}
    dose_response = []
    d5_costs = {(item["variantId"], item["samples"]): item for item in d5_result["doseMeasurements"]}
    for variant_id in variants:
        qualifying: list[int] = []
        for samples in spec["sampleLadder"]:
            rows = [item for item in measurements if item["variantId"] == variant_id and item["samples"] == samples]
            passed = len(rows) == spec["repeatsPerVariantDose"] and all(item["passed"] for item in rows)
            if passed: qualifying.append(samples)
            cost = d5_costs[(variant_id, samples)]
            dose_response.append({"variantId": variant_id, "samples": samples, "repeats": len(rows), "productionSemanticPassed": passed, "medianRenderSeconds": cost["medianRenderSeconds"], "medianFreshProcessWallSeconds": cost["medianFreshProcessWallSeconds"]})
        per_variant_floor[variant_id] = min(qualifying) if qualifying else None
    global_qualifying = []
    for samples in spec["sampleLadder"]:
        rows = [item for item in measurements if item["samples"] == samples]
        if len(rows) == len(variants) * spec["repeatsPerVariantDose"] and all(item["passed"] for item in rows): global_qualifying.append(samples)
    semantic_floor = min(global_qualifying) if global_qualifying else None

    tools = {}
    for name, uri in {
        "analyzer": "scripts/analyze-b51-native-cpu-data-semantic-equivalence.py",
        "audit": "scripts/audit-b51-native-cpu-data-semantic-equivalence.py",
    }.items():
        path = root / uri
        tools[name] = {"uri": uri, "sha256": sha256_file(path)}
    evidence = {
        "schemaVersion": "bfs.nativeCpuDataPassSemanticEquivalenceEvidence.v0.1",
        "experimentId": spec["experimentId"],
        "preregistration": {"commit": args.preregistration_commit, "specUri": str(args.spec.resolve().relative_to(root)), "specSha256": sha256_file(args.spec)},
        "toolFreezeCommit": args.tool_freeze_commit,
        "tools": tools,
        "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "d5BindingObservations": d5_bindings,
        "artifactObservations": artifact_observations,
        "inputObservations": input_observations,
        "reference128Comparisons": reference_comparisons,
        "doseRepeatComparisons": repeat_comparisons,
        "semanticMeasurements": measurements,
        "doseResponseTable": dose_response,
        "perVariantSemanticFloor": per_variant_floor,
        "semanticDataSampleFloor": semantic_floor,
        "thresholds": spec["productionSemanticProfile"],
        "operationCounts": spec["operationBoundary"],
        "nonClaims": spec["nonClaims"],
    }
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence))
    evidence["baseFailure"] = validate(evidence, spec)
    evidence["attacks"] = run_attacks(evidence, spec)
    evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"])
    if evidence["baseFailure"] is None and evidence["attacksPassed"] == len(spec["attacks"]):
        evidence["verdict"] = spec["validVerdicts"][0] if semantic_floor is not None and semantic_floor < 128 else spec["validVerdicts"][1]
    else:
        evidence["verdict"] = spec["invalidVerdict"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B51_D6_RESULT verdict={evidence['verdict']} floor={semantic_floor} attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={evidence['baseFailure'] or 'none'}", flush=True)


if __name__ == "__main__":
    main()
