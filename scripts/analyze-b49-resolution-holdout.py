"""Analyze, attack and decide the preregistered B49-R resolution holdout."""

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


RAW_ROSTER = ["BFS_MASTER.Combined", "BFS_MASTER.Depth", "BFS_MASTER.Normal", "BFS_MASTER.Vector", "BFS_MASTER.CryptoObject00", "BFS_MASTER.CryptoObject01", "BFS_MASTER.CryptoObject02"]


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read_exr(path, width, height):
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror())
    roster, combined, channels = [], None, None
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        roster.append(name)
        if name.endswith(".Combined"):
            combined = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
            channels = list(spec.channelnames)
    if combined is None or combined.shape != (height, width, 4):
        raise RuntimeError(f"invalid Combined shape: {path}")
    finite = bool(np.isfinite(combined).all())
    metadata = {"name": "Combined", "shape": list(combined.shape), "channels": channels, "dtype": "float32-le", "order": "C"}
    header = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    return roster, finite, hashlib.sha256(header + combined.tobytes(order="C")).hexdigest()


def exponent(metric_ratio, pixel_ratio):
    return math.log(metric_ratio) / math.log(pixel_ratio)


def projections(baseline_seconds, projection):
    rows = {}
    for name, ratio in (("twoK", projection["twoKPixelRatio"]), ("fourK", projection["fourKPixelRatio"])):
        low = baseline_seconds * ratio ** projection["exponentBand"][0]
        high = baseline_seconds * ratio ** projection["exponentBand"][1]
        rows[name] = {"resolution": projection[f"{name}Resolution"], "pixelRatio": ratio, "perFrameSecondsRange": [low, high], "frames": projection["frames"], "sequenceSecondsRange": [low * projection["frames"], high * projection["frames"]]}
    return {"labels": projection["labels"], "basis": "committed 128x72 baseline and preregistered exponent band", "rows": rows}


def hash_payload(evidence):
    return {key: value for key, value in evidence.items() if key not in {"evidenceCoreHash", "attacks", "attacksPassed", "verdict"}}


def validate(evidence, spec):
    if not all(item["match"] for item in evidence["parentObservations"]): return "PARENT_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"]): return "SOURCE_IDENTITY"
    expected_image = {"id": spec["image"]["id"], "os": spec["image"]["os"], "architecture": spec["image"]["architecture"], "sizeBytes": spec["image"]["dockerReportedSizeBytes"]}
    if evidence["image"] != expected_image: return "IMAGE_IDENTITY"
    if evidence["securityBoundary"] != spec["containerContract"]: return "SECURITY_BOUNDARY"
    if evidence["diskAdmission"]["status"] != "ACCEPTED": return "DISK_ADMISSION"
    if [item["shotId"] for item in evidence["observations"]] != [item["id"] for item in spec["shots"]]: return "SOURCE_IDENTITY"
    expected_resolution = [*spec["holdout"]["resolution"], 100]
    for item in evidence["observations"]:
        if item["resolution"] != expected_resolution or item["pixelCount"] != spec["holdout"]["pixelCount"] or item["pixelRatioToBaseline"] != spec["holdout"]["pixelRatioToBaseline"]: return "RESOLUTION_SETTING"
        wanted = spec["holdout"]
        if item["samples"] != wanted["samples"] or item["seedOffset"] != wanted["seedOffset"] or item["seed"] != item["baseShotSeed"] + wanted["seedOffset"] or item["animatedSeed"] or item["denoising"] != wanted["denoising"] or item["motionBlur"] != wanted["motionBlur"] or item["persistentData"] != wanted["persistentData"] or item["threads"] != wanted["threads"]: return "RENDER_SETTING"
        if item["roster"] != RAW_ROSTER: return "PASS_ROSTER"
        if not item["allCombinedFinite"]: return "NON_FINITE"
        expected_render_exponent = exponent(item["renderSeconds"] / item["baseline"]["renderSeconds"], item["pixelRatioToBaseline"])
        if abs(item["effectiveExponents"]["renderSeconds"] - expected_render_exponent) > 1e-12 or not spec["gates"]["renderPixelExponentMinimum"] <= item["effectiveExponents"]["renderSeconds"] <= spec["gates"]["renderPixelExponentMaximum"]: return "RENDER_EXPONENT"
        expected_exr_exponent = exponent(item["artifact"]["bytes"] / item["baseline"]["exrBytes"], item["pixelRatioToBaseline"])
        if abs(item["effectiveExponents"]["exrBytes"] - expected_exr_exponent) > 1e-12 or not spec["gates"]["exrByteExponentMinimum"] <= item["effectiveExponents"]["exrBytes"] <= spec["gates"]["exrByteExponentMaximum"]: return "EXR_EXPONENT"
        if item["peakSelfRssKiB"] > spec["gates"]["peakSelfRssKiBMaximum"]: return "RSS_LIMIT"
    counts = evidence["operationCounts"]
    expected_counts = {key: spec["operationBoundary"][key] for key in ("dockerRuns", "hostExrAnalyses", "builds", "pulls", "downloads", "modelCalls", "videoModelCalls")}
    if counts != expected_counts: return "OPERATION_BOUNDARY"
    if evidence["cleanup"]["experimentContainersRunningAfter"] != 0: return "CLEANUP"
    if evidence.get("evidenceCoreHash") != canonical_hash(hash_payload(evidence)): return "EVIDENCE_SELF_HASH"
    return None


def run_attacks(evidence, spec):
    cases = []
    def add(attack_id, expected, mutator):
        clone = copy.deepcopy(evidence); mutator(clone); clone["evidenceCoreHash"] = canonical_hash(hash_payload(clone)) if expected != "EVIDENCE_SELF_HASH" else "0" * 64
        observed = validate(clone, spec); cases.append({"id": attack_id, "expectedReason": expected, "observedReason": observed, "passed": observed == expected})
    add("A01_PARENT_IDENTITY", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_SOURCE_IDENTITY", "SOURCE_IDENTITY", lambda x: x["sourceObservations"][0].update(match=False))
    add("A03_IMAGE_IDENTITY", "IMAGE_IDENTITY", lambda x: x["image"].update(architecture="arm64"))
    add("A04_SECURITY_BOUNDARY", "SECURITY_BOUNDARY", lambda x: x["securityBoundary"].update(network="bridge"))
    add("A05_DISK_ADMISSION", "DISK_ADMISSION", lambda x: x["diskAdmission"].update(status="BLOCKED"))
    add("A06_RESOLUTION_SETTING", "RESOLUTION_SETTING", lambda x: x["observations"][0].update(resolution=[511, 288, 100]))
    add("A07_RENDER_SETTING", "RENDER_SETTING", lambda x: x["observations"][0].update(samples=64))
    add("A08_PASS_ROSTER", "PASS_ROSTER", lambda x: x["observations"][0]["roster"].pop())
    add("A09_NON_FINITE", "NON_FINITE", lambda x: x["observations"][0].update(allCombinedFinite=False))
    add("A10_RENDER_EXPONENT", "RENDER_EXPONENT", lambda x: x["observations"][0]["effectiveExponents"].update(renderSeconds=0.5))
    add("A11_EXR_EXPONENT", "EXR_EXPONENT", lambda x: x["observations"][0]["effectiveExponents"].update(exrBytes=0.5))
    add("A12_RSS_LIMIT", "RSS_LIMIT", lambda x: x["observations"][0].update(peakSelfRssKiB=spec["gates"]["peakSelfRssKiBMaximum"] + 1))
    add("A13_OPERATION_BOUNDARY", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(dockerRuns=3))
    add("A14_CLEANUP", "CLEANUP", lambda x: x["cleanup"].update(experimentContainersRunningAfter=1))
    add("A15_EVIDENCE_SELF_HASH", "EVIDENCE_SELF_HASH", lambda x: None)
    return cases


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--receipt", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8")); receipt = json.loads(args.receipt.read_text(encoding="utf-8")); root = args.receipt.parent; observations = []
    for run in receipt["runs"]:
        shot = next(item for item in spec["shots"] if item["id"] == run["shotId"]); report = run["report"]; path = root / run["runId"] / report["artifact"]["uri"]; width, height = spec["holdout"]["resolution"]; roster, finite, combined_hash = read_exr(path, width, height); settings = report["settings"]; pixel_ratio = spec["holdout"]["pixelRatioToBaseline"]; baseline = shot["baseline"]
        render_exponent = exponent(report["renderSeconds"] / baseline["renderSeconds"], pixel_ratio); exr_exponent = exponent(path.stat().st_size / baseline["exrBytes"], pixel_ratio)
        observations.append({"shotId": shot["id"], "sourceShotId": shot["shotId"], "frame": shot["frame"], "argv": run["argv"], "baseShotSeed": report["bindings"]["baseShotSeed"], "resolution": settings["resolution"], "pixelCount": settings["pixelCount"], "pixelRatioToBaseline": pixel_ratio, "samples": settings["samples"], "seedOffset": settings["seedOffset"], "seed": settings["seed"], "animatedSeed": settings["animatedSeed"], "denoising": settings["denoising"], "motionBlur": settings["motionBlur"], "persistentData": settings["persistentData"], "threads": settings["threads"], "renderSeconds": report["renderSeconds"], "saveSeconds": report["saveSeconds"], "freshContainerWallSeconds": run["elapsedMs"] / 1000, "peakSelfRssKiB": report["peakSelfRssKiB"], "baseline": baseline, "ratiosToBaseline": {"renderSeconds": report["renderSeconds"] / baseline["renderSeconds"], "exrBytes": path.stat().st_size / baseline["exrBytes"]}, "effectiveExponents": {"renderSeconds": render_exponent, "exrBytes": exr_exponent}, "roster": roster, "allCombinedFinite": finite, "combinedCanonicalFloat32Sha256": combined_hash, "artifact": {"uri": str(path.relative_to(root.parent.parent)), "sha256": sha256_file(path), "bytes": path.stat().st_size}, "projection": projections(baseline["renderSeconds"], spec["projection"])})
    operation_counts = {"dockerRuns": sum(item.startswith("DOCKER_RUN_") for item in receipt["runtimeOperations"]), "hostExrAnalyses": sum(item.startswith("HOST_EXR_ANALYSIS_") for item in receipt["runtimeOperations"]), "builds": 0, "pulls": 0, "downloads": 0, "modelCalls": 0, "videoModelCalls": 0}
    evidence = {"schemaVersion": "bfs.codexWorkerResolutionHoldoutEvidence.v0.1", "experimentId": spec["experimentId"], "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["toolFreezeCommit"], "tools": receipt["tools"], "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__}, "parents": receipt["parents"], "parentObservations": receipt["parentObservations"], "sourceObservations": receipt["sourceObservations"], "image": receipt["image"], "hostInspector": receipt["hostInspectorObservation"], "diskAdmission": receipt["diskAdmission"], "securityBoundary": receipt["securityBoundary"], "gates": spec["gates"], "observations": observations, "operationCounts": operation_counts, "cleanup": receipt["cleanup"], "nonClaims": spec["nonClaims"]}
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); base_failure = validate(evidence, spec); evidence["baseFailure"] = base_failure
    # baseFailure is itself evidence, so seal again before attacks and validation.
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); base_failure = validate(evidence, spec); evidence["baseFailure"] = base_failure
    evidence["attacks"] = run_attacks(evidence, spec); evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"]); attack_valid = evidence["attacksPassed"] == len(spec["attacks"])
    invalid_reasons = {"PARENT_IDENTITY", "SOURCE_IDENTITY", "IMAGE_IDENTITY", "SECURITY_BOUNDARY", "DISK_ADMISSION", "RESOLUTION_SETTING", "RENDER_SETTING", "PASS_ROSTER", "NON_FINITE", "OPERATION_BOUNDARY", "CLEANUP", "EVIDENCE_SELF_HASH"}
    evidence["verdict"] = spec["invalidVerdict"] if not attack_valid or base_failure in invalid_reasons else spec["rejectedVerdict"] if base_failure else spec["acceptedVerdict"]
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B49_R_RESULT verdict={evidence['verdict']} attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={base_failure or 'none'}", flush=True)


if __name__ == "__main__":
    main()
