"""Analyze and attack B51-D2 cache-state evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


ROSTER = ["BFS_MASTER.Combined", "BFS_MASTER.Depth", "BFS_MASTER.Normal", "BFS_MASTER.Vector", "BFS_MASTER.CryptoObject00", "BFS_MASTER.CryptoObject01", "BFS_MASTER.CryptoObject02"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def duration_seconds(value: str | None) -> float | None:
    if not value:
        return None
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def read_exr(path: Path, width: int, height: int) -> tuple[list[str], dict, dict]:
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror())
    roster = []
    passes = {}
    timing = {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        if pixels.shape[:2] != (height, width):
            raise RuntimeError(f"invalid pass shape {name}: {pixels.shape}")
        metadata = {"name": name, "shape": list(pixels.shape), "channels": list(spec.channelnames), "dtype": "float32-le", "order": "C"}
        header = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        roster.append(name)
        passes[name] = {"pixels": pixels, "shape": list(pixels.shape), "channels": list(spec.channelnames), "finite": bool(np.isfinite(pixels).all()), "canonicalFloat32Sha256": hashlib.sha256(header + pixels.tobytes(order="C")).hexdigest()}
        if name.endswith(".Combined"):
            attrs = {item.name: str(item.value) for item in spec.extra_attribs}
            timing = {key: attrs.get(key) for key in ("RenderTime", "cycles.BFS_MASTER.render_time", "cycles.BFS_MASTER.synchronization_time", "cycles.BFS_MASTER.total_time")}
            timing["seconds"] = {key: duration_seconds(value) for key, value in timing.items()}
    return roster, passes, timing


def hash_payload(evidence: dict) -> dict:
    return {key: value for key, value in evidence.items() if key not in {"evidenceCoreHash", "attacks", "attacksPassed", "verdict"}}


def validate(evidence: dict, spec: dict) -> str | None:
    if not all(item["match"] for item in evidence["parentObservations"]): return "PARENT_IDENTITY"
    if not evidence["blenderObservation"]["match"]: return "BLENDER_IDENTITY"
    if not evidence["sourceObservations"][0]["match"]: return "SOURCE_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"][1:]): return "OCIO_IDENTITY"
    if evidence["diskAdmission"]["status"] != "ACCEPTED": return "DISK_ADMISSION"
    pre = evidence["cachePreflight"]
    if pre["status"] != "ACCEPTED" or not pre["quarantineAbsent"] or not pre["generatedRetentionAbsent"] or not pre["sameFilesystem"]: return "CACHE_PREFLIGHT"
    if not evidence["cacheEvents"] or not evidence["cacheEvents"][0]["matchesPreflight"] or not evidence["cacheEvents"][0]["sourceAbsent"]: return "CACHE_SEQUESTER"
    observations = evidence["observations"]
    expected = {item["runId"]: item for item in spec["cells"]}
    observed = {item["runId"]: item for item in observations}
    if list(observed) != list(expected): return "RUN_MATRIX"
    for index, cell in enumerate(spec["cells"]):
        item = observed[cell["runId"]]
        if item["cacheBeforeExists"] != (index != 0) or not item["cacheAfterExists"]: return "CACHE_STATE_SEQUENCE"
    restore = evidence["cacheRestore"]
    if restore["status"] != "PASS" or not restore["matchesPreflight"] or not restore["originalExists"] or restore["originalIsSymlink"] or restore["quarantineExists"] or not restore["generatedRetentionExists"]: return "CACHE_RESTORE"
    if len({item["processPid"] for item in observations}) != spec["evidenceGates"]["freshBlenderProcesses"]: return "FRESH_PROCESS"
    profile = spec["renderProfile"]
    for item in observations:
        if item["selectedDevice"] != spec["nativeBlender"]["device"]: return "DEVICE_ASSIGNMENT"
        settings = item["settings"]
        if settings["resolution"] != [*profile["resolution"], 100] or settings["samples"] != profile["samples"] or settings["seedOffset"] != profile["seedOffset"] or settings["seed"] != item["baseShotSeed"] + profile["seedOffset"] or settings["animatedSeed"] != profile["animatedSeed"] or settings["denoising"] != profile["denoising"] or settings["motionBlur"] != profile["motionBlur"] or settings["persistentData"] != profile["persistentData"]: return "RENDER_PROFILE"
        if item["roster"] != ROSTER: return "PASS_ROSTER"
        if not all(value["finite"] for value in item["passes"].values()): return "NON_FINITE"
        if not item["artifactIdentityMatch"]: return "ARTIFACT_IDENTITY"
    wanted = {key: spec["operationBoundary"][key] for key in ("nativeBlenderProcesses", "atomicDirectoryRenames", "deletions", "dockerRuns", "downloads", "modelCalls", "videoModelCalls")}
    if evidence["operationCounts"] != wanted: return "OPERATION_BOUNDARY"
    if evidence.get("evidenceCoreHash") != canonical_hash(hash_payload(evidence)): return "EVIDENCE_SELF_HASH"
    return None


def attacks(evidence: dict, spec: dict) -> list[dict]:
    cases = []
    def add(attack_id, reason, mutate):
        clone = copy.deepcopy(evidence); mutate(clone); clone["evidenceCoreHash"] = canonical_hash(hash_payload(clone)) if reason != "EVIDENCE_SELF_HASH" else "0" * 64
        observed = validate(clone, spec); cases.append({"id": attack_id, "expectedReason": reason, "observedReason": observed, "passed": observed == reason})
    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_BLENDER", "BLENDER_IDENTITY", lambda x: x["blenderObservation"].update(match=False))
    add("A03_SOURCE", "SOURCE_IDENTITY", lambda x: x["sourceObservations"][0].update(match=False))
    add("A04_OCIO", "OCIO_IDENTITY", lambda x: x["sourceObservations"][1].update(match=False))
    add("A05_DISK", "DISK_ADMISSION", lambda x: x["diskAdmission"].update(status="BLOCKED"))
    add("A06_PREFLIGHT", "CACHE_PREFLIGHT", lambda x: x["cachePreflight"].update(sameFilesystem=False))
    add("A07_SEQUESTER", "CACHE_SEQUESTER", lambda x: x["cacheEvents"][0].update(matchesPreflight=False))
    add("A08_SEQUENCE", "CACHE_STATE_SEQUENCE", lambda x: x["observations"][0].update(cacheBeforeExists=True))
    add("A09_RESTORE", "CACHE_RESTORE", lambda x: x["cacheRestore"].update(matchesPreflight=False))
    add("A10_MATRIX", "RUN_MATRIX", lambda x: x["observations"].pop())
    add("A11_PROCESS", "FRESH_PROCESS", lambda x: x["observations"][1].update(processPid=x["observations"][0]["processPid"]))
    add("A12_DEVICE", "DEVICE_ASSIGNMENT", lambda x: x["observations"][0]["selectedDevice"].update(type="CPU"))
    add("A13_PROFILE", "RENDER_PROFILE", lambda x: x["observations"][0]["settings"].update(samples=64))
    add("A14_ROSTER", "PASS_ROSTER", lambda x: x["observations"][0]["roster"].pop())
    add("A15_FINITE", "NON_FINITE", lambda x: x["observations"][0]["passes"]["BFS_MASTER.Combined"].update(finite=False))
    add("A16_ARTIFACT", "ARTIFACT_IDENTITY", lambda x: x["observations"][0].update(artifactIdentityMatch=False))
    add("A17_OPERATION", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(deletions=1))
    add("A18_HASH", "EVIDENCE_SELF_HASH", lambda x: None)
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--receipt", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8")); receipt = json.loads(args.receipt.read_text(encoding="utf-8")); root = args.receipt.parent; width, height = spec["renderProfile"]["resolution"]
    arrays = {}; observations = []
    for run in receipt["runs"]:
        report = run["report"]; path = root / run["runId"] / "artifacts" / report["artifact"]["uri"]; roster, passes, timing = read_exr(path, width, height); arrays[run["runId"]] = passes
        observations.append({"runId": run["runId"], "cacheState": run["cacheState"], "order": run["order"], "processPid": report["process"]["pid"], "runnerObservedPid": run["pid"], "cacheBeforeExists": run["cacheBefore"]["exists"], "cacheBeforeTreeSha256": run["cacheBefore"]["manifest"]["treeSha256"] if run["cacheBefore"]["manifest"] else None, "cacheAfterExists": run["cacheAfter"]["exists"], "cacheAfterTreeSha256": run["cacheAfter"]["manifest"]["treeSha256"] if run["cacheAfter"]["manifest"] else None, "cacheAfterFiles": run["cacheAfter"]["manifest"]["fileCount"] if run["cacheAfter"]["manifest"] else 0, "cacheAfterBytes": run["cacheAfter"]["manifest"]["bytes"] if run["cacheAfter"]["manifest"] else 0, "freshProcessWallSeconds": run["elapsedSeconds"], "renderSeconds": report["renderSeconds"], "saveSeconds": report["saveSeconds"], "peakSelfRssBytes": report["peakSelfRssBytes"], "selectedDevice": report["device"]["selected"][0], "settings": report["settings"], "baseShotSeed": report["bindings"]["baseShotSeed"], "roster": roster, "passes": {name: {key: value for key, value in data.items() if key != "pixels"} for name, data in passes.items()}, "exrTiming": timing, "artifact": {"uri": str(path.relative_to(root.parent.parent)), "sha256": sha256_file(path), "bytes": path.stat().st_size}, "artifactIdentityMatch": report["artifact"]["sha256"] == sha256_file(path) and report["artifact"]["bytes"] == path.stat().st_size})
    pass_comparisons = {}
    for left, right in (("COLD_R1", "WARM_R1"), ("WARM_R1", "WARM_R2")):
        pass_comparisons[f"{left}_vs_{right}"] = {name: {"exact": arrays[left][name]["canonicalFloat32Sha256"] == arrays[right][name]["canonicalFloat32Sha256"], "changedFloatComponents": int(np.count_nonzero(arrays[left][name]["pixels"] != arrays[right][name]["pixels"])), "maximumAbsoluteDifference": float(np.max(np.abs(arrays[left][name]["pixels"] - arrays[right][name]["pixels"]))) } for name in ROSTER}
    times = {item["runId"]: item for item in observations}
    timing_summary = {"coldRenderSeconds": times["COLD_R1"]["renderSeconds"], "warmRenderSeconds": [times["WARM_R1"]["renderSeconds"], times["WARM_R2"]["renderSeconds"]], "coldSynchronizationSeconds": times["COLD_R1"]["exrTiming"]["seconds"]["cycles.BFS_MASTER.synchronization_time"], "warmSynchronizationSeconds": [times["WARM_R1"]["exrTiming"]["seconds"]["cycles.BFS_MASTER.synchronization_time"], times["WARM_R2"]["exrTiming"]["seconds"]["cycles.BFS_MASTER.synchronization_time"]]}
    timing_summary["coldOverWarmR1RenderRatio"] = timing_summary["coldRenderSeconds"] / timing_summary["warmRenderSeconds"][0]
    timing_summary["coldOverWarmR1SynchronizationRatio"] = timing_summary["coldSynchronizationSeconds"] / timing_summary["warmSynchronizationSeconds"][0]
    operation_counts = {"nativeBlenderProcesses": sum(item.startswith("NATIVE_BLENDER_PROCESS_") for item in receipt["runtimeOperations"]), "atomicDirectoryRenames": sum(item.startswith("ATOMIC_RENAME_") for item in receipt["runtimeOperations"]), "deletions": 0, "dockerRuns": 0, "downloads": 0, "modelCalls": 0, "videoModelCalls": 0}
    evidence = {"schemaVersion": "bfs.cyclesCacheStateDerivationEvidence.v0.1", "experimentId": spec["experimentId"], "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["toolFreezeCommit"], "tools": receipt["tools"], "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__}, "parents": receipt["parents"], "parentObservations": receipt["parentObservations"], "sourceObservations": receipt["sourceObservations"], "blenderObservation": receipt["blenderObservation"], "diskAdmission": receipt["diskAdmission"], "cachePreflight": receipt["cachePreflight"], "cacheEvents": receipt["cacheEvents"], "cacheRestore": receipt["cacheRestore"], "observations": observations, "timingSummary": timing_summary, "passComparisons": pass_comparisons, "operationCounts": operation_counts, "nonClaims": spec["nonClaims"], "baseFailure": None}
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); failure = validate(evidence, spec); evidence["baseFailure"] = failure; evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); failure = validate(evidence, spec); evidence["baseFailure"] = failure
    evidence["attacks"] = attacks(evidence, spec); evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"]); evidence["verdict"] = "CYCLES_CACHE_STATE_DERIVATION_USABLE" if failure is None and evidence["attacksPassed"] == len(spec["attacks"]) else "CYCLES_CACHE_STATE_DERIVATION_INVALID"
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B51_D2_RESULT verdict={evidence['verdict']} attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={failure or 'none'} cold={timing_summary['coldRenderSeconds']:.3f}s warm={timing_summary['warmRenderSeconds'][0]:.3f}s", flush=True)


if __name__ == "__main__": main()
