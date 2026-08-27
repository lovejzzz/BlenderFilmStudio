"""Analyze and adversarially validate the B51-D5 CPU data sample/cost matrix."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import statistics
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def load_exr(path: Path) -> tuple[list[str], dict[str, dict]]:
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror() or f"cannot read {path}")
    roster, parts = [], {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        if not image.initialized:
            raise RuntimeError(image.geterror() or f"cannot read subimage {index} in {path}")
        name = str(image.spec().getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        roster.append(name)
        parts[name] = {
            "pixels": pixels,
            "sha256": hashlib.sha256(pixels.tobytes()).hexdigest(),
            "finite": bool(np.isfinite(pixels).all()),
            "shape": list(pixels.shape),
        }
    return roster, parts


def matrix(spec: dict) -> list[dict]:
    rows, order = [], 1
    for samples in spec["sampleLadder"]:
        for variant in spec["variants"]:
            for repeat in range(1, spec["repeatsPerVariantDose"] + 1):
                rows.append({"runId": f"{variant['id']}_S{samples:03d}_R{repeat}", "variant": variant["id"], "source": variant["source"], "samples": samples, "repeat": repeat, "order": order})
                order += 1
    return rows


def operation_replay_valid(replay: list[dict], expected: list[dict]) -> bool:
    if len(replay) != len(expected):
        return False
    for row, operation in zip(replay, expected):
        if row.get("operation") != operation:
            return False
        kind, value = operation["kind"], operation["value"]
        before, after = row.get("before"), row.get("after")
        if kind == "LOCATION_DELTA":
            if not np.allclose(np.asarray(after), np.asarray(before) + np.asarray(value), rtol=0, atol=1e-6):
                return False
        elif kind == "ROTATION_Z_DELTA":
            if not np.isclose(float(after), float(before) + float(value), rtol=0, atol=1e-6):
                return False
        elif kind == "CAMERA_LENS_SET":
            if not np.isclose(float(after), float(value), rtol=0, atol=1e-6):
                return False
        elif kind == "LIGHT_ENERGY_SCALE":
            if not np.isclose(float(after), float(before) * float(value), rtol=1e-6, atol=1e-6):
                return False
        else:
            return False
    return True


def compare(left: np.ndarray, right: np.ndarray) -> dict:
    if left.shape != right.shape:
        return {"shapeMatch": False, "floatExact": False, "changedComponents": None, "changedPixels": None, "changedPixelFraction": None, "maxAbsoluteDifference": None}
    changed = left != right
    changed_pixels = np.any(changed, axis=-1) if changed.ndim >= 3 else changed
    absolute = np.abs(left.astype(np.float64) - right.astype(np.float64))
    return {
        "shapeMatch": True,
        "floatExact": bool(np.array_equal(left, right)),
        "changedComponents": int(np.count_nonzero(changed)),
        "changedPixels": int(np.count_nonzero(changed_pixels)),
        "changedPixelFraction": float(np.count_nonzero(changed_pixels) / changed_pixels.size),
        "maxAbsoluteDifference": float(np.max(absolute)) if absolute.size else 0.0,
    }


def expected_settings(spec: dict, samples: int, seed: int) -> dict:
    profile = spec["renderProfile"]
    return {
        "engine": profile["engine"], "cyclesDevice": "CPU", "resolution": [*profile["resolution"], 100],
        "pixelCount": profile["resolution"][0] * profile["resolution"][1], "samples": samples,
        "seedOffset": profile["seedOffset"], "seed": seed, "animatedSeed": profile["animatedSeed"],
        "denoising": profile["denoising"], "motionBlur": profile["motionBlur"],
        "persistentData": profile["persistentData"], "threadsMode": "FIXED", "threads": profile["cpuThreads"],
    }


def hash_payload(evidence: dict) -> dict:
    excluded = {"evidenceCoreHash", "baseFailure", "attacks", "attacksPassed", "verdict"}
    return {key: value for key, value in evidence.items() if key not in excluded}


def validate(evidence: dict, spec: dict) -> str | None:
    if not all(item["match"] for item in evidence["parentObservations"]): return "PARENT_IDENTITY"
    if not evidence["blenderObservation"]["match"]: return "BLENDER_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"] + evidence["sourcePostObservations"] if item["kind"] != "OCIO") or not all(item["sourceIdentityMatch"] for item in evidence["observations"]): return "SOURCE_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"] if item["kind"] == "OCIO"): return "OCIO_IDENTITY"
    if evidence["diskAdmission"]["status"] != "ACCEPTED": return "DISK_ADMISSION"
    if evidence["schedule"] != matrix(spec) or len(evidence["observations"]) != spec["evidenceGates"]["successfulRenders"]: return "VARIANT_DOSE_MATRIX"
    if not all(item["operationReplayValid"] for item in evidence["observations"]): return "OPERATION_REPLAY"
    if len({item["processPid"] for item in evidence["observations"]}) != len(evidence["observations"]) or not all(item["processPid"] == item["runnerObservedPid"] for item in evidence["observations"]): return "FRESH_PROCESS"
    if not all(item["deviceAssignmentValid"] for item in evidence["observations"]): return "CPU_DEVICE_ASSIGNMENT"
    if not all(item["renderProfileValid"] for item in evidence["observations"]): return "RENDER_PROFILE"
    if not all(item["rosterMatch"] for item in evidence["observations"]): return "PASS_ROSTER"
    if not all(item["finite"] for item in evidence["observations"]): return "NON_FINITE"
    if not evidence["parent128DataExact"]: return "PARENT_128_DATA_EXACTNESS"
    if not all(item["allDataPassesExact"] for item in evidence["repeatComparisons"]): return "DOSE_REPEAT_DATA_EXACTNESS"
    expected_measurements = len(spec["variants"]) * len(spec["sampleLadder"])
    if len(evidence["doseMeasurements"]) != expected_measurements or len(evidence["parentComparisons"]) != spec["evidenceGates"]["successfulRenders"]: return "MEASUREMENT_TOTALITY"
    if not all(item["artifactIdentityMatch"] for item in evidence["observations"]): return "ARTIFACT_IDENTITY"
    if evidence["operationCounts"] != spec["operationBoundary"]: return "OPERATION_BOUNDARY"
    if evidence.get("evidenceCoreHash") != canonical_hash(hash_payload(evidence)): return "EVIDENCE_SELF_HASH"
    return None


def run_attacks(evidence: dict, spec: dict) -> list[dict]:
    rows = []
    def add(identifier: str, reason: str, mutate, rehash: bool = True) -> None:
        clone = copy.deepcopy(evidence); mutate(clone)
        clone["evidenceCoreHash"] = canonical_hash(hash_payload(clone)) if rehash else "0" * 64
        observed = validate(clone, spec)
        rows.append({"id": identifier, "expectedReason": reason, "observedReason": observed, "passed": observed == reason})
    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_BLENDER", "BLENDER_IDENTITY", lambda x: x["blenderObservation"].update(match=False))
    add("A03_SOURCE", "SOURCE_IDENTITY", lambda x: next(item for item in x["sourceObservations"] if item["kind"] == "SOURCE").update(match=False))
    add("A04_OCIO", "OCIO_IDENTITY", lambda x: next(item for item in x["sourceObservations"] if item["kind"] == "OCIO").update(match=False))
    add("A05_DISK", "DISK_ADMISSION", lambda x: x["diskAdmission"].update(status="BLOCKED"))
    add("A06_MATRIX", "VARIANT_DOSE_MATRIX", lambda x: x["schedule"].pop())
    add("A07_OPERATION", "OPERATION_REPLAY", lambda x: x["observations"][0].update(operationReplayValid=False))
    add("A08_FRESH", "FRESH_PROCESS", lambda x: x["observations"][1].update(processPid=x["observations"][0]["processPid"]))
    add("A09_DEVICE", "CPU_DEVICE_ASSIGNMENT", lambda x: x["observations"][0].update(deviceAssignmentValid=False))
    add("A10_PROFILE", "RENDER_PROFILE", lambda x: x["observations"][0].update(renderProfileValid=False))
    add("A11_ROSTER", "PASS_ROSTER", lambda x: x["observations"][0].update(rosterMatch=False))
    add("A12_FINITE", "NON_FINITE", lambda x: x["observations"][0].update(finite=False))
    add("A13_PARENT128", "PARENT_128_DATA_EXACTNESS", lambda x: x.update(parent128DataExact=False))
    add("A14_REPEAT", "DOSE_REPEAT_DATA_EXACTNESS", lambda x: x["repeatComparisons"][0].update(allDataPassesExact=False))
    add("A15_TOTALITY", "MEASUREMENT_TOTALITY", lambda x: x["doseMeasurements"].pop())
    add("A16_ARTIFACT", "ARTIFACT_IDENTITY", lambda x: x["observations"][0].update(artifactIdentityMatch=False))
    add("A17_BOUNDARY", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(metalRenders=1))
    add("A18_HASH", "EVIDENCE_SELF_HASH", lambda x: None, rehash=False)
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
    parent_spec = json.loads((root / spec["parents"]["h1Spec"]["uri"]).read_text(encoding="utf-8"))
    expected_cpu = parent_spec["nativeBlender"]["cpuDevice"]
    expected_roster = [f"BFS_MASTER.{name}" for name in spec["renderProfile"]["passes"]]
    data_passes = [f"BFS_MASTER.{name}" for name in spec["renderProfile"]["dataPasses"]]
    variants = {item["id"]: item for item in spec["variants"]}
    parent_parts = {}
    for variant in spec["variants"]:
        roster, parts = load_exr(root / variant["parentExr"]["uri"])
        if roster != expected_roster:
            raise RuntimeError(f"parent roster mismatch: {variant['id']}")
        parent_parts[variant["id"]] = parts

    observations, loaded = [], {}
    for run in receipt["runs"]:
        report = run["report"]
        path = args.receipt.parent / run["runId"] / "artifacts" / report["artifact"]["uri"]
        roster, parts = load_exr(path)
        loaded[run["runId"]] = parts
        variant = variants[run["variant"]]
        source = spec["sources"][variant["source"]]
        selected = report["device"]["selected"]
        device_valid = len(selected) == 1 and selected[0]["id"] == expected_cpu["id"] and selected[0]["type"] == "CPU"
        settings = expected_settings(spec, run["samples"], int(report["bindings"]["baseShotSeed"]) + spec["renderProfile"]["seedOffset"])
        observations.append({
            "runId": run["runId"], "variantId": run["variant"], "sourceId": run["source"], "samples": run["samples"], "repeat": run["repeat"], "order": run["order"],
            "processPid": report["process"]["pid"], "runnerObservedPid": run["pid"], "freshProcessWallSeconds": run["elapsedSeconds"],
            "renderSeconds": report["renderSeconds"], "saveSeconds": report["saveSeconds"], "peakSelfRssBytes": report["peakSelfRssBytes"],
            "sourceIdentityMatch": report["source"] == {"uri": source["blendUri"], "sha256": source["blendSha256"], "bytes": source["blendBytes"]},
            "operationReplay": report["operationReplay"], "operationReplayValid": operation_replay_valid(report["operationReplay"], variant["operations"]),
            "selectedDevices": selected, "deviceAssignmentValid": device_valid, "settings": report["settings"], "renderProfileValid": report["settings"] == settings,
            "roster": roster, "rosterMatch": roster == expected_roster, "finite": all(item["finite"] for item in parts.values()),
            "passPixelSha256": {name: parts[name]["sha256"] for name in expected_roster},
            "artifact": {"uri": str(path.relative_to(root)), "sha256": sha256_file(path), "bytes": path.stat().st_size},
            "artifactIdentityMatch": report["artifact"]["sha256"] == sha256_file(path) and report["artifact"]["bytes"] == path.stat().st_size,
        })

    parent_comparisons = []
    for observation in observations:
        comparisons = {name: compare(loaded[observation["runId"]][name]["pixels"], parent_parts[observation["variantId"]][name]["pixels"]) for name in data_passes}
        parent_comparisons.append({"runId": observation["runId"], "variantId": observation["variantId"], "samples": observation["samples"], "repeat": observation["repeat"], "passes": comparisons, "allDataPassesExact": all(item["floatExact"] for item in comparisons.values())})

    repeat_comparisons = []
    for variant in spec["variants"]:
        for samples in spec["sampleLadder"]:
            left_id = f"{variant['id']}_S{samples:03d}_R1"; right_id = f"{variant['id']}_S{samples:03d}_R2"
            comparisons = {name: compare(loaded[left_id][name]["pixels"], loaded[right_id][name]["pixels"]) for name in data_passes}
            repeat_comparisons.append({"variantId": variant["id"], "samples": samples, "leftRunId": left_id, "rightRunId": right_id, "passes": comparisons, "allDataPassesExact": all(item["floatExact"] for item in comparisons.values())})

    dose_measurements = []
    per_variant_floor = {}
    for variant in spec["variants"]:
        qualifying = []
        parent_time = variant["parentExr"]["renderSeconds"]
        for samples in spec["sampleLadder"]:
            cells = [item for item in observations if item["variantId"] == variant["id"] and item["samples"] == samples]
            parent_rows = [item for item in parent_comparisons if item["variantId"] == variant["id"] and item["samples"] == samples]
            exact = len(parent_rows) == spec["repeatsPerVariantDose"] and all(item["allDataPassesExact"] for item in parent_rows)
            if exact:
                qualifying.append(samples)
            median_render = statistics.median(item["renderSeconds"] for item in cells)
            dose_measurements.append({
                "variantId": variant["id"], "samples": samples, "repeats": len(cells), "allDataPassesExactToParent": exact,
                "medianRenderSeconds": median_render, "medianFreshProcessWallSeconds": statistics.median(item["freshProcessWallSeconds"] for item in cells),
                "medianSaveSeconds": statistics.median(item["saveSeconds"] for item in cells), "speedupVersusFrozen128ParentRender": parent_time / median_render,
            })
        per_variant_floor[variant["id"]] = min(qualifying) if qualifying else None
    global_qualifying = []
    for samples in spec["sampleLadder"]:
        rows = [item for item in parent_comparisons if item["samples"] == samples]
        if len(rows) == len(spec["variants"]) * spec["repeatsPerVariantDose"] and all(item["allDataPassesExact"] for item in rows):
            global_qualifying.append(samples)
    global_floor = min(global_qualifying) if global_qualifying else None
    parent_128_exact = all(item["allDataPassesExact"] for item in parent_comparisons if item["samples"] == 128) and len([item for item in parent_comparisons if item["samples"] == 128]) == len(spec["variants"]) * spec["repeatsPerVariantDose"]

    evidence = {
        "schemaVersion": "bfs.nativeCpuDataPassSampleCostEvidence.v0.1", "experimentId": spec["experimentId"],
        "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["toolFreezeCommit"], "tools": receipt["tools"],
        "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "parentObservations": receipt["parentObservations"], "sourceObservations": receipt["sourceObservations"], "sourcePostObservations": receipt["sourcePostObservations"],
        "blenderObservation": receipt["blenderObservation"], "diskAdmission": receipt["diskAdmission"], "schedule": receipt["schedule"],
        "observations": observations, "parentComparisons": parent_comparisons, "repeatComparisons": repeat_comparisons, "doseMeasurements": dose_measurements,
        "parent128DataExact": parent_128_exact, "perVariantExactFloor": per_variant_floor, "exactDataSampleFloor": global_floor,
        "operationCounts": spec["operationBoundary"], "nonClaims": spec["nonClaims"],
    }
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); evidence["baseFailure"] = validate(evidence, spec)
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); evidence["baseFailure"] = validate(evidence, spec)
    evidence["attacks"] = run_attacks(evidence, spec); evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"])
    if evidence["baseFailure"] is None and evidence["attacksPassed"] == len(spec["attacks"]):
        evidence["verdict"] = spec["validVerdicts"][0] if global_floor is not None and global_floor < 128 else spec["validVerdicts"][1]
    else:
        evidence["verdict"] = spec["invalidVerdict"]
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B51_D5_RESULT verdict={evidence['verdict']} floor={global_floor} attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={evidence['baseFailure'] or 'none'}", flush=True)


if __name__ == "__main__":
    main()
