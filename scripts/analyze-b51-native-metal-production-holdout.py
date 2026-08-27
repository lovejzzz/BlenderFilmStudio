"""Analyze and adversarially validate the B51-H1 native Metal holdout."""

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


AP1_LUMA = np.asarray([0.2722287168, 0.6740817658, 0.0536895174], dtype=np.float64)
HOLDOUT_ROSTER = ["BFS_MASTER.Combined", "BFS_MASTER.Depth", "BFS_MASTER.Normal", "BFS_MASTER.Vector", "BFS_MASTER.CryptoObject00", "BFS_MASTER.CryptoObject01", "BFS_MASTER.CryptoObject02"]
CANARY_ROSTER = ["BFS_MASTER.Combined"]


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
    fields = value.split(":")
    if len(fields) == 2:
        return int(fields[0]) * 60 + float(fields[1])
    if len(fields) == 3:
        return int(fields[0]) * 3600 + int(fields[1]) * 60 + float(fields[2])
    raise ValueError(f"unsupported EXR duration: {value}")


def read_exr(path: Path, width: int, height: int) -> tuple[list[str], dict, dict]:
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror())
    roster, passes, timing = [], {}, {}
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
            raw = {key: attrs.get(key) for key in ("RenderTime", "cycles.BFS_MASTER.render_time", "cycles.BFS_MASTER.synchronization_time", "cycles.BFS_MASTER.total_time")}
            timing = {"raw": raw, "seconds": {key: duration_seconds(value) for key, value in raw.items()}}
    return roster, passes, timing


def edge_mask(reference_rgb: np.ndarray) -> tuple[np.ndarray, int, float]:
    luma = np.maximum(np.tensordot(reference_rgb.astype(np.float64), AP1_LUMA, axes=([2], [0])), 0.0)
    dx, dy = np.zeros_like(luma), np.zeros_like(luma)
    dx[:, 1:-1] = 0.5 * (luma[:, 2:] - luma[:, :-2]); dx[:, 0] = luma[:, 1] - luma[:, 0]; dx[:, -1] = luma[:, -1] - luma[:, -2]
    dy[1:-1, :] = 0.5 * (luma[2:, :] - luma[:-2, :]); dy[0, :] = luma[1, :] - luma[0, :]; dy[-1, :] = luma[-1, :] - luma[-2, :]
    magnitude = np.hypot(dx, dy)
    count = max(1, math.ceil(magnitude.size * 0.10))
    selected = np.argsort(-magnitude.reshape(-1), kind="stable")[:count]
    mask = np.zeros(magnitude.size, dtype=bool); mask[selected] = True
    return mask.reshape(magnitude.shape), count, float(magnitude.reshape(-1)[selected[-1]])


def metrics(candidate: np.ndarray, reference: np.ndarray, mask: np.ndarray, rms: float) -> dict:
    a, b = candidate[..., :3].astype(np.float64), reference[..., :3].astype(np.float64)
    delta = a - b
    ay = np.maximum(np.tensordot(a, AP1_LUMA, axes=([2], [0])), 0.0)
    by = np.maximum(np.tensordot(b, AP1_LUMA, axes=([2], [0])), 0.0)
    linear = float(np.sqrt(np.mean(np.square(delta))))
    return {"linearRmse": linear, "linearNrmseByReferenceMeanRms": linear / rms, "linearMae": float(np.mean(np.abs(delta))), "linearP95AbsoluteError": float(np.percentile(np.abs(delta), 95)), "linearMaxAbsoluteError": float(np.max(np.abs(delta))), "logLuminanceRmse": float(np.sqrt(np.mean(np.square(np.log2(1 + ay) - np.log2(1 + by))))), "edgeLinearRmse": float(np.sqrt(np.mean(np.square(delta[mask]))))}


def operation_replay_valid(replay: list[dict], operations: list[dict]) -> bool:
    if [item.get("operation") for item in replay] != operations:
        return False
    for item in replay:
        operation, before, after = item["operation"], item["before"], item["after"]
        kind, value = operation["kind"], operation["value"]
        if kind == "LOCATION_DELTA":
            expected = [float(before[index]) + float(value[index]) for index in range(3)]
            if not np.allclose(after, expected, rtol=0.0, atol=1e-6): return False
        elif kind == "ROTATION_Z_DELTA":
            if not math.isclose(float(after), float(before) + float(value), rel_tol=0.0, abs_tol=1e-6): return False
        elif kind == "CAMERA_LENS_SET":
            if not math.isclose(float(after), float(value), rel_tol=0.0, abs_tol=1e-6): return False
        elif kind == "LIGHT_ENERGY_SCALE":
            if not math.isclose(float(after), float(before) * float(value), rel_tol=1e-6, abs_tol=1e-6): return False
        else:
            return False
    return True


def check_canary(spec: dict, run_root: Path, output: Path, wall_seconds: float) -> dict:
    report_path = run_root / "artifacts/render.report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    exr = run_root / "artifacts" / report["artifact"]["uri"]
    width, height = spec["canary"]["resolution"]
    roster, passes, timing = read_exr(exr, width, height)
    sync = timing["seconds"].get("cycles.BFS_MASTER.synchronization_time")
    source = spec["sources"][spec["canary"]["source"]]
    expected_bindings = {"planHash": source["planHash"], "sceneSpecHash": source["sceneHash"], "structureHash": source["structureHash"], "ocioConfigSha256": spec["ocio"]["sha256"]}
    settings = report["settings"]
    checks = {
        "runIdentity": report["runId"] == spec["canary"]["runId"] and report["isCanary"] and report["order"] == 0,
        "sourceIdentity": report["sourceId"] == spec["canary"]["source"] and report["variantId"] == spec["canary"]["variant"] and report["source"]["sha256"] == source["blendSha256"] and report["source"]["bytes"] == source["blendBytes"] and {key: report["bindings"][key] for key in expected_bindings} == expected_bindings,
        "profileIdentity": settings["resolution"] == [width, height, 100] and settings["samples"] == spec["canary"]["samples"] and settings["seed"] == report["bindings"]["baseShotSeed"] + spec["renderProfile"]["seedOffset"] and not settings["denoising"] and not settings["motionBlur"] and not settings["persistentData"],
        "operationReplay": report["operationReplay"] == [],
        "deviceIdentity": report["deviceType"] == "METAL" and report["device"]["selected"] == [spec["nativeBlender"]["metalDevice"]],
        "roster": roster == CANARY_ROSTER and all(item["finite"] for item in passes.values()),
        "artifactIdentity": report["artifact"]["sha256"] == sha256_file(exr) and report["artifact"]["bytes"] == exr.stat().st_size,
        "renderBudget": report["renderSeconds"] <= spec["canary"]["maxRenderSeconds"],
        "synchronizationBudget": sync is not None and sync <= spec["canary"]["maxSynchronizationSeconds"],
        "wallBudget": wall_seconds <= spec["canary"]["maxProcessWallSeconds"],
    }
    decision = {"schemaVersion": "bfs.nativeMetalCanaryDecision.v0.1", "runId": report["runId"], "renderSeconds": report["renderSeconds"], "synchronizationSeconds": sync, "wallSeconds": wall_seconds, "roster": roster, "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL"}
    output.write_text(json.dumps(decision, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B51_H1_CANARY {decision['status']} render={decision['renderSeconds']:.3f}s sync={sync if sync is not None else 'missing'}s wall={wall_seconds:.3f}s", flush=True)
    return decision


def hash_payload(evidence: dict) -> dict:
    return {key: value for key, value in evidence.items() if key not in {"evidenceCoreHash", "attacks", "attacksPassed", "verdict"}}


def validate(evidence: dict, spec: dict) -> str | None:
    if not all(item["match"] for item in evidence["parentObservations"]): return "PARENT_IDENTITY"
    if not evidence["blenderObservation"]["match"]: return "BLENDER_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"] if item["kind"] == "SOURCE"): return "SOURCE_IDENTITY"
    if not all(item["match"] for item in evidence["sourcePostObservations"]): return "SOURCE_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"] if item["kind"] in {"OCIO", "SPEC"}): return "OCIO_IDENTITY"
    if evidence["diskAdmission"]["status"] != "ACCEPTED": return "DISK_ADMISSION"
    canary = evidence["canary"]
    if canary["runId"] != spec["canary"]["runId"] or canary["order"] != 0 or canary["runtimeOperationIndex"] != 0: return "CANARY_ORDER"
    if canary["decision"]["status"] != "PASS" or not all(canary["decision"]["checks"].values()): return "CANARY_READINESS"
    expected = {item["runId"]: item for item in spec["cells"]}; observed = {item["runId"]: item for item in evidence["observations"]}
    if list(observed) != list(expected): return "VARIANT_MATRIX"
    variants = {item["id"]: item for item in spec["variants"]}
    for run_id, cell in expected.items():
        item = observed[run_id]
        if item["variantId"] != cell["variant"] or item["sourceId"] != variants[cell["variant"]]["source"]: return "VARIANT_MATRIX"
        if not item["operationReplayValid"]: return "OPERATION_REPLAY"
    all_pids = [canary["processPid"], *[item["processPid"] for item in evidence["observations"]]]
    if len(set(all_pids)) != spec["evidenceGates"]["successfulRenders"]: return "FRESH_PROCESS"
    profile = spec["renderProfile"]
    for run_id, cell in expected.items():
        item = observed[run_id]
        expected_device = spec["nativeBlender"]["cpuDevice" if cell["device"] == "CPU" else "metalDevice"]
        if item["deviceType"] != cell["device"] or item["selectedDevices"] != [expected_device]: return "DEVICE_ASSIGNMENT"
        settings = item["settings"]
        if settings["resolution"] != [*profile["resolution"], 100] or settings["samples"] != profile["samples"] or settings["seedOffset"] != profile["seedOffset"] or settings["seed"] != item["baseShotSeed"] + profile["seedOffset"] or settings["animatedSeed"] != profile["animatedSeed"] or settings["denoising"] != profile["denoising"] or settings["motionBlur"] != profile["motionBlur"] or settings["persistentData"] != profile["persistentData"] or settings["threads"] != profile["cpuThreads"]: return "RENDER_PROFILE"
        if item["roster"] != HOLDOUT_ROSTER: return "PASS_ROSTER"
        if not all(value["finite"] for value in item["passes"].values()): return "NON_FINITE"
        if not item["artifactIdentityMatch"]: return "ARTIFACT_IDENTITY"
    limits = spec["promotionThresholds"]["crossBackendCombined"]
    for variant in evidence["comparisons"].values():
        for pair in variant["crossBackend"]:
            row = pair["metrics"]
            if row["linearNrmseByReferenceMeanRms"] > limits["maxLinearNrmseByCpuMeanRms"] or row["logLuminanceRmse"] > limits["maxLogLuminanceRmse"] or row["edgeLinearRmse"] > limits["maxEdgeLinearRmse"] or row["linearP95AbsoluteError"] > limits["maxLinearP95AbsoluteError"] or row["linearMaxAbsoluteError"] > limits["maxLinearAbsoluteError"]: return "CROSS_BACKEND_TOLERANCE"
        repeat = variant["metalRepeat"]["metrics"]; repeat_limits = spec["promotionThresholds"]["metalRepeatCombined"]
        if repeat["linearNrmseByReferenceMeanRms"] > repeat_limits["maxLinearNrmseByFirstMeanRms"] or repeat["linearP95AbsoluteError"] > repeat_limits["maxLinearP95AbsoluteError"]: return "METAL_REPEAT_TOLERANCE"
        if not all(all(values.values()) for values in variant["exactPassesAcrossBackend"].values()): return "EXACT_PASS_DOMAIN"
        if any(value > spec["promotionThresholds"]["maxMetalRenderSecondsPerCell"] for value in variant["metalRenderSeconds"]): return "TIMING_BUDGET"
    wanted = spec["operationBoundary"]
    if evidence["operationCounts"] != wanted: return "OPERATION_BOUNDARY"
    if evidence.get("evidenceCoreHash") != canonical_hash(hash_payload(evidence)): return "EVIDENCE_SELF_HASH"
    return None


def attacks(evidence: dict, spec: dict) -> list[dict]:
    rows = []
    baseline = copy.deepcopy(evidence)
    baseline["baseFailure"] = None
    for comparison in baseline["comparisons"].values():
        for pair in comparison["crossBackend"]:
            pair["metrics"].update(linearNrmseByReferenceMeanRms=0.0, logLuminanceRmse=0.0, edgeLinearRmse=0.0, linearP95AbsoluteError=0.0, linearMaxAbsoluteError=0.0)
        comparison["metalRepeat"]["metrics"].update(linearNrmseByReferenceMeanRms=0.0, linearP95AbsoluteError=0.0)
        comparison["metalRenderSeconds"] = [0.0 for _ in comparison["metalRenderSeconds"]]
        for exact_passes in comparison["exactPassesAcrossBackend"].values():
            for name in exact_passes:
                exact_passes[name] = True
    baseline["evidenceCoreHash"] = canonical_hash(hash_payload(baseline))
    if validate(baseline, spec) is not None:
        raise RuntimeError("attack baseline could not be isolated from observed gate failures")
    def add(identifier: str, reason: str, mutate) -> None:
        clone = copy.deepcopy(baseline); mutate(clone); clone["evidenceCoreHash"] = canonical_hash(hash_payload(clone)) if reason != "EVIDENCE_SELF_HASH" else "0" * 64
        observed = validate(clone, spec); rows.append({"id": identifier, "expectedReason": reason, "observedReason": observed, "passed": observed == reason})
    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_BLENDER", "BLENDER_IDENTITY", lambda x: x["blenderObservation"].update(match=False))
    add("A03_SOURCE", "SOURCE_IDENTITY", lambda x: x["sourceObservations"][0].update(match=False))
    add("A04_OCIO", "OCIO_IDENTITY", lambda x: next(item for item in x["sourceObservations"] if item["kind"] == "OCIO").update(match=False))
    add("A05_DISK", "DISK_ADMISSION", lambda x: x["diskAdmission"].update(status="BLOCKED"))
    add("A06_CANARY_ORDER", "CANARY_ORDER", lambda x: x["canary"].update(order=1))
    add("A07_CANARY_READY", "CANARY_READINESS", lambda x: x["canary"]["decision"].update(status="FAIL"))
    add("A08_MATRIX", "VARIANT_MATRIX", lambda x: x["observations"].pop())
    add("A09_REPLAY", "OPERATION_REPLAY", lambda x: x["observations"][0].update(operationReplayValid=False))
    add("A10_PROCESS", "FRESH_PROCESS", lambda x: x["observations"][0].update(processPid=x["canary"]["processPid"]))
    add("A11_DEVICE", "DEVICE_ASSIGNMENT", lambda x: x["observations"][0].update(deviceType="METAL"))
    add("A12_PROFILE", "RENDER_PROFILE", lambda x: x["observations"][0]["settings"].update(samples=64))
    add("A13_ROSTER", "PASS_ROSTER", lambda x: x["observations"][0]["roster"].pop())
    add("A14_FINITE", "NON_FINITE", lambda x: x["observations"][0]["passes"]["BFS_MASTER.Combined"].update(finite=False))
    add("A15_CROSS", "CROSS_BACKEND_TOLERANCE", lambda x: next(iter(x["comparisons"].values()))["crossBackend"][0]["metrics"].update(linearNrmseByReferenceMeanRms=1.0))
    add("A16_REPEAT", "METAL_REPEAT_TOLERANCE", lambda x: next(iter(x["comparisons"].values()))["metalRepeat"]["metrics"].update(linearNrmseByReferenceMeanRms=1.0))
    add("A17_EXACT", "EXACT_PASS_DOMAIN", lambda x: next(iter(next(iter(x["comparisons"].values()))["exactPassesAcrossBackend"].values())).update({"Depth": False}))
    add("A18_TIMING", "TIMING_BUDGET", lambda x: next(iter(x["comparisons"].values())).update(metalRenderSeconds=[99.0]))
    add("A19_ARTIFACT", "ARTIFACT_IDENTITY", lambda x: x["observations"][0].update(artifactIdentityMatch=False))
    add("A20_OPERATION", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(sceneFilesModified=1))
    add("A21_HASH", "EVIDENCE_SELF_HASH", lambda x: None)
    return rows


def full_analysis(spec: dict, receipt: dict, receipt_root: Path, output: Path) -> None:
    width, height = spec["renderProfile"]["resolution"]
    arrays, observations = {}, []
    variants = {item["id"]: item for item in spec["variants"]}
    for run in receipt["runs"]:
        report = run["report"]
        path = receipt_root / run["runId"] / "artifacts" / report["artifact"]["uri"]
        roster, passes, timing = read_exr(path, width, height)
        arrays[run["runId"]] = passes
        cell = next(item for item in spec["cells"] if item["runId"] == run["runId"])
        observations.append({"runId": run["runId"], "variantId": report["variantId"], "sourceId": report["sourceId"], "deviceType": report["deviceType"], "repeat": report["repeat"], "order": report["order"], "processPid": report["process"]["pid"], "runnerObservedPid": run["pid"], "freshProcessWallSeconds": run["elapsedSeconds"], "renderSeconds": report["renderSeconds"], "saveSeconds": report["saveSeconds"], "peakSelfRssBytes": report["peakSelfRssBytes"], "selectedDevices": report["device"]["selected"], "settings": report["settings"], "baseShotSeed": report["bindings"]["baseShotSeed"], "operationReplay": report["operationReplay"], "operationReplayValid": operation_replay_valid(report["operationReplay"], variants[cell["variant"]]["operations"]), "roster": roster, "passes": {name: {key: value for key, value in item.items() if key != "pixels"} for name, item in passes.items()}, "exrTiming": timing, "artifact": {"uri": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}, "artifactIdentityMatch": report["artifact"]["sha256"] == sha256_file(path) and report["artifact"]["bytes"] == path.stat().st_size})

    comparisons = {}
    exact_names = [f"BFS_MASTER.{name}" for name in spec["promotionThresholds"]["exactPassesAcrossBackend"]]
    for variant in spec["variants"]:
        variant_id = variant["id"]
        cpu_id = next(item["runId"] for item in observations if item["variantId"] == variant_id and item["deviceType"] == "CPU")
        metal_ids = sorted((item["runId"] for item in observations if item["variantId"] == variant_id and item["deviceType"] == "METAL"), key=lambda item: next(row["repeat"] for row in observations if row["runId"] == item))
        cpu = arrays[cpu_id]["BFS_MASTER.Combined"]["pixels"]
        rms = float(np.sqrt(np.mean(np.square(cpu[..., :3].astype(np.float64)))))
        mask, edge_count, edge_cutoff = edge_mask(cpu[..., :3])
        cross = [{"cpuRunId": cpu_id, "metalRunId": metal_id, "metrics": metrics(arrays[metal_id]["BFS_MASTER.Combined"]["pixels"], cpu, mask, rms)} for metal_id in metal_ids]
        first = arrays[metal_ids[0]]["BFS_MASTER.Combined"]["pixels"]
        first_rms = float(np.sqrt(np.mean(np.square(first[..., :3].astype(np.float64)))))
        repeat = {"left": metal_ids[0], "right": metal_ids[1], "metrics": metrics(arrays[metal_ids[1]]["BFS_MASTER.Combined"]["pixels"], first, mask, first_rms)}
        exact = {metal_id: {name.removeprefix("BFS_MASTER."): arrays[cpu_id][name]["canonicalFloat32Sha256"] == arrays[metal_id][name]["canonicalFloat32Sha256"] for name in exact_names} for metal_id in metal_ids}
        comparisons[variant_id] = {"cpuRunId": cpu_id, "metalRunIds": metal_ids, "referenceMeanRms": rms, "edgeMask": {"pixelCount": edge_count, "gradientCutoff": edge_cutoff}, "crossBackend": cross, "metalRepeat": repeat, "exactPassesAcrossBackend": exact, "metalRenderSeconds": [next(item["renderSeconds"] for item in observations if item["runId"] == metal_id) for metal_id in metal_ids]}

    canary_report = receipt["canary"]["report"]
    operation_counts = {"nativeBlenderProcesses": sum(item.startswith("NATIVE_BLENDER_PROCESS_") for item in receipt["runtimeOperations"]), "sceneFilesModified": 0 if all(item["match"] for item in receipt["sourcePostObservations"]) else 1, "cacheDirectoriesMoved": 0, "deletions": 0, "dockerRuns": 0, "downloads": 0, "modelCalls": 0, "videoModelCalls": 0, "networkRequired": False}
    evidence = {"schemaVersion": "bfs.nativeMetalProductionHoldoutEvidence.v0.1", "experimentId": spec["experimentId"], "analysisCorrections": [{"id": "B51-H1-C1", "scope": "Isolate attack cases from an already-negative observed baseline without changing renders, metrics, thresholds or the base failure."}, {"id": "B51-H1-C2", "scope": "Resolve EXR evidence from the immutable receipt directory independently from the requested result output directory."}], "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["toolFreezeCommit"], "tools": receipt["tools"], "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__}, "parents": receipt["parents"], "parentObservations": receipt["parentObservations"], "sourceObservations": receipt["sourceObservations"], "sourcePostObservations": receipt["sourcePostObservations"], "blenderObservation": receipt["blenderObservation"], "diskAdmission": receipt["diskAdmission"], "canary": {"runId": canary_report["runId"], "order": canary_report["order"], "processPid": canary_report["process"]["pid"], "runnerObservedPid": receipt["canary"]["pid"], "runtimeOperationIndex": receipt["runtimeOperations"].index(f"NATIVE_BLENDER_PROCESS_{spec['canary']['runId']}"), "decision": receipt["canaryDecision"]}, "observations": observations, "comparisons": comparisons, "operationCounts": operation_counts, "nonClaims": spec["nonClaims"], "baseFailure": None}
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); failure = validate(evidence, spec); evidence["baseFailure"] = failure; evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); failure = validate(evidence, spec); evidence["baseFailure"] = failure
    evidence["attacks"] = attacks(evidence, spec); evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"])
    evidence["verdict"] = "NATIVE_METAL_PRODUCTION_HOLDOUT_SUPPORTED" if failure is None and evidence["attacksPassed"] == len(spec["attacks"]) else "NATIVE_METAL_PRODUCTION_HOLDOUT_NOT_SUPPORTED"
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B51_H1_RESULT verdict={evidence['verdict']} attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={failure or 'none'}", flush=True)
    for variant_id, row in comparisons.items():
        worst = max(item["metrics"]["linearNrmseByReferenceMeanRms"] for item in row["crossBackend"])
        print(f"BFS_B51_H1_VARIANT {variant_id} metal={','.join(f'{value:.3f}' for value in row['metalRenderSeconds'])}s cross_nrmse={worst:.8f}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-canary", action="store_true")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--wall-seconds", type=float)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if args.check_canary:
        if args.run_root is None or args.wall_seconds is None: raise RuntimeError("canary mode requires run root and wall seconds")
        decision = check_canary(spec, args.run_root, args.output, args.wall_seconds)
        if decision["status"] != "PASS": raise SystemExit(1)
    else:
        if args.receipt is None: raise RuntimeError("full analysis requires receipt")
        full_analysis(spec, json.loads(args.receipt.read_text(encoding="utf-8")), args.receipt.parent, args.output)


if __name__ == "__main__":
    main()
