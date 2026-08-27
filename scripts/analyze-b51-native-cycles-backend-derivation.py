"""Analyze and adversarially validate the B51-D1 backend derivation."""

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
EXPECTED_ROSTER = [
    "BFS_MASTER.Combined", "BFS_MASTER.Depth", "BFS_MASTER.Normal", "BFS_MASTER.Vector",
    "BFS_MASTER.CryptoObject00", "BFS_MASTER.CryptoObject01", "BFS_MASTER.CryptoObject02",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def read_exr(path: Path, width: int, height: int) -> tuple[list[str], dict]:
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror())
    roster = []
    passes = {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        if pixels.shape[:2] != (height, width):
            raise RuntimeError(f"invalid pass shape: {name} {pixels.shape}")
        metadata = {"name": name, "shape": list(pixels.shape), "channels": list(spec.channelnames), "dtype": "float32-le", "order": "C"}
        header = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        roster.append(name)
        passes[name] = {
            "pixels": pixels,
            "shape": list(pixels.shape),
            "channels": list(spec.channelnames),
            "finite": bool(np.isfinite(pixels).all()),
            "canonicalFloat32Sha256": hashlib.sha256(header + pixels.tobytes(order="C")).hexdigest(),
        }
    return roster, passes


def edge_mask(reference_rgb: np.ndarray) -> tuple[np.ndarray, int, float]:
    luma = np.maximum(np.tensordot(reference_rgb.astype(np.float64), AP1_LUMA, axes=([2], [0])), 0.0)
    dx = np.zeros_like(luma)
    dy = np.zeros_like(luma)
    dx[:, 1:-1] = 0.5 * (luma[:, 2:] - luma[:, :-2])
    dx[:, 0] = luma[:, 1] - luma[:, 0]
    dx[:, -1] = luma[:, -1] - luma[:, -2]
    dy[1:-1, :] = 0.5 * (luma[2:, :] - luma[:-2, :])
    dy[0, :] = luma[1, :] - luma[0, :]
    dy[-1, :] = luma[-1, :] - luma[-2, :]
    magnitude = np.hypot(dx, dy)
    count = max(1, math.ceil(magnitude.size * 0.10))
    selected = np.argsort(-magnitude.reshape(-1), kind="stable")[:count]
    mask = np.zeros(magnitude.size, dtype=bool)
    mask[selected] = True
    return mask.reshape(magnitude.shape), count, float(magnitude.reshape(-1)[selected[-1]])


def metrics(candidate: np.ndarray, target: np.ndarray, mask: np.ndarray, rms: float) -> dict:
    a = candidate[..., :3].astype(np.float64)
    b = target[..., :3].astype(np.float64)
    delta = a - b
    ay = np.maximum(np.tensordot(a, AP1_LUMA, axes=([2], [0])), 0.0)
    by = np.maximum(np.tensordot(b, AP1_LUMA, axes=([2], [0])), 0.0)
    linear = float(np.sqrt(np.mean(np.square(delta))))
    return {
        "linearRmse": linear,
        "linearNrmseByCpuMeanRms": linear / rms,
        "linearMae": float(np.mean(np.abs(delta))),
        "linearP95AbsoluteError": float(np.percentile(np.abs(delta), 95)),
        "linearMaxAbsoluteError": float(np.max(np.abs(delta))),
        "logLuminanceRmse": float(np.sqrt(np.mean(np.square(np.log2(1 + ay) - np.log2(1 + by))))),
        "edgeLinearRmse": float(np.sqrt(np.mean(np.square(delta[mask])))),
    }


def hash_payload(evidence: dict) -> dict:
    return {key: value for key, value in evidence.items() if key not in {"evidenceCoreHash", "attacks", "attacksPassed", "verdict"}}


def validate(evidence: dict, spec: dict) -> str | None:
    if not all(item["match"] for item in evidence["parentObservations"]):
        return "PARENT_IDENTITY"
    if not evidence["blenderObservation"]["match"]:
        return "BLENDER_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"][:-2]):
        return "SOURCE_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"][-2:]):
        return "OCIO_IDENTITY"
    if evidence["diskAdmission"]["status"] != "ACCEPTED":
        return "DISK_ADMISSION"
    expected_cells = {item["runId"]: item for item in spec["cells"]}
    observed_cells = {item["runId"]: item for item in evidence["observations"]}
    if list(observed_cells) != list(expected_cells):
        return "RUN_MATRIX"
    if len({item["processPid"] for item in evidence["observations"]}) != spec["evidenceGates"]["freshBlenderProcesses"]:
        return "FRESH_PROCESS"
    profile = spec["renderProfile"]
    for run_id, cell in expected_cells.items():
        item = observed_cells[run_id]
        if item["deviceType"] != cell["device"] or item["selectedDeviceCount"] != 1:
            return "DEVICE_ASSIGNMENT"
        settings = item["settings"]
        if settings["resolution"] != [*profile["resolution"], 100] or settings["samples"] != profile["samples"] or settings["seedOffset"] != profile["seedOffset"] or settings["seed"] != item["baseShotSeed"] + profile["seedOffset"] or settings["animatedSeed"] != profile["animatedSeed"] or settings["denoising"] != profile["denoising"] or settings["motionBlur"] != profile["motionBlur"] or settings["persistentData"] != profile["persistentData"] or settings["threads"] != profile["cpuThreads"]:
            return "RENDER_PROFILE"
        if item["roster"] != EXPECTED_ROSTER:
            return "PASS_ROSTER"
        if not all(value["finite"] for value in item["passes"].values()):
            return "NON_FINITE"
        if not item["artifactIdentityMatch"]:
            return "ARTIFACT_IDENTITY"
    expected_operations = {key: spec["operationBoundary"][key] for key in ("nativeBlenderProcesses", "dockerRuns", "imageBuilds", "downloads", "modelCalls", "videoModelCalls")}
    if evidence["operationCounts"] != expected_operations:
        return "OPERATION_BOUNDARY"
    if evidence.get("evidenceCoreHash") != canonical_hash(hash_payload(evidence)):
        return "EVIDENCE_SELF_HASH"
    return None


def run_attacks(evidence: dict, spec: dict) -> list[dict]:
    cases = []
    def add(attack_id: str, expected: str, mutate) -> None:
        clone = copy.deepcopy(evidence)
        mutate(clone)
        clone["evidenceCoreHash"] = canonical_hash(hash_payload(clone)) if expected != "EVIDENCE_SELF_HASH" else "0" * 64
        observed = validate(clone, spec)
        cases.append({"id": attack_id, "expectedReason": expected, "observedReason": observed, "passed": observed == expected})
    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_BLENDER", "BLENDER_IDENTITY", lambda x: x["blenderObservation"].update(match=False))
    add("A03_SOURCE", "SOURCE_IDENTITY", lambda x: x["sourceObservations"][0].update(match=False))
    add("A04_OCIO", "OCIO_IDENTITY", lambda x: x["sourceObservations"][-1].update(match=False))
    add("A05_DISK", "DISK_ADMISSION", lambda x: x["diskAdmission"].update(status="BLOCKED"))
    add("A06_MATRIX", "RUN_MATRIX", lambda x: x["observations"].pop())
    add("A07_PROCESS", "FRESH_PROCESS", lambda x: x["observations"][1].update(processPid=x["observations"][0]["processPid"]))
    add("A08_DEVICE", "DEVICE_ASSIGNMENT", lambda x: x["observations"][0].update(deviceType="METAL"))
    add("A09_PROFILE", "RENDER_PROFILE", lambda x: x["observations"][0]["settings"].update(samples=64))
    add("A10_ROSTER", "PASS_ROSTER", lambda x: x["observations"][0]["roster"].pop())
    add("A11_FINITE", "NON_FINITE", lambda x: x["observations"][0]["passes"]["BFS_MASTER.Combined"].update(finite=False))
    add("A12_ARTIFACT", "ARTIFACT_IDENTITY", lambda x: x["observations"][0].update(artifactIdentityMatch=False))
    add("A13_OPERATIONS", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(nativeBlenderProcesses=7))
    add("A14_HASH", "EVIDENCE_SELF_HASH", lambda x: None)
    return cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    root = args.receipt.parent
    width, height = spec["renderProfile"]["resolution"]
    arrays = {}
    observations = []
    for run in receipt["runs"]:
        report = run["report"]
        path = root / run["runId"] / "artifacts" / report["artifact"]["uri"]
        roster, passes = read_exr(path, width, height)
        arrays[run["runId"]] = passes
        artifact_match = report["artifact"]["sha256"] == sha256_file(path) and report["artifact"]["bytes"] == path.stat().st_size
        observations.append({
            "runId": run["runId"], "shotId": run["shotId"], "deviceType": run["device"], "repeat": run["repeat"], "order": run["order"],
            "processPid": report["process"]["pid"], "runnerObservedPid": run["pid"], "freshProcessWallSeconds": run["elapsedSeconds"],
            "renderSeconds": report["renderSeconds"], "saveSeconds": report["saveSeconds"], "peakSelfRssBytes": report["peakSelfRssBytes"],
            "selectedDeviceCount": len(report["device"]["selected"]), "selectedDevices": report["device"]["selected"],
            "settings": report["settings"], "baseShotSeed": report["bindings"]["baseShotSeed"], "roster": roster,
            "passes": {name: {key: value for key, value in data.items() if key != "pixels"} for name, data in passes.items()},
            "artifact": {"uri": str(path.relative_to(root.parent.parent)), "sha256": sha256_file(path), "bytes": path.stat().st_size},
            "artifactIdentityMatch": artifact_match,
        })

    comparisons = {}
    timings = {}
    for shot in spec["shots"]:
        shot_id = shot["id"]
        ids = {device: sorted([item["runId"] for item in observations if item["shotId"] == shot_id and item["deviceType"] == device]) for device in ("CPU", "METAL")}
        cpu_arrays = [arrays[item]["BFS_MASTER.Combined"]["pixels"] for item in ids["CPU"]]
        metal_arrays = [arrays[item]["BFS_MASTER.Combined"]["pixels"] for item in ids["METAL"]]
        cpu_mean = np.mean(np.stack([item.astype(np.float64) for item in cpu_arrays]), axis=0)
        rms = float(np.sqrt(np.mean(np.square(cpu_mean[..., :3]))))
        mask, edge_count, edge_cutoff = edge_mask(cpu_mean[..., :3])
        qemu_path = args.spec.parent.parent / shot["qemuCpuParent"]["exrUri"]
        _, qemu_passes = read_exr(qemu_path, width, height)
        qemu = qemu_passes["BFS_MASTER.Combined"]["pixels"]
        pair_rows = []
        for repeat in (1, 2):
            cpu_id = next(item["runId"] for item in observations if item["shotId"] == shot_id and item["deviceType"] == "CPU" and item["repeat"] == repeat)
            metal_id = next(item["runId"] for item in observations if item["shotId"] == shot_id and item["deviceType"] == "METAL" and item["repeat"] == repeat)
            pair_rows.append({"repeat": repeat, "cpuRunId": cpu_id, "metalRunId": metal_id, "metrics": metrics(arrays[metal_id]["BFS_MASTER.Combined"]["pixels"], arrays[cpu_id]["BFS_MASTER.Combined"]["pixels"], mask, rms)})
        repeat_rows = {}
        for device in ("CPU", "METAL"):
            left, right = ids[device]
            repeat_rows[device] = {
                "left": left, "right": right,
                "exrByteExact": next(item["artifact"]["sha256"] for item in observations if item["runId"] == left) == next(item["artifact"]["sha256"] for item in observations if item["runId"] == right),
                "combinedFloatExact": arrays[left]["BFS_MASTER.Combined"]["canonicalFloat32Sha256"] == arrays[right]["BFS_MASTER.Combined"]["canonicalFloat32Sha256"],
                "allPassesFloatExact": all(arrays[left][name]["canonicalFloat32Sha256"] == arrays[right][name]["canonicalFloat32Sha256"] for name in EXPECTED_ROSTER),
            }
        comparisons[shot_id] = {
            "cpuMeanRms": rms, "edgeMask": {"pixelCount": edge_count, "gradientCutoff": edge_cutoff},
            "withinDeviceRepeats": repeat_rows, "cpuVsMetalPaired": pair_rows,
            "qemuVsNativeCpuR1": metrics(cpu_arrays[0], qemu, mask, rms),
            "qemuVsNativeMetalR1": metrics(metal_arrays[0], qemu, mask, rms),
            "qemuCombinedCanonicalFloat32Sha256": qemu_passes["BFS_MASTER.Combined"]["canonicalFloat32Sha256"],
        }
        cpu_times = [item["renderSeconds"] for item in observations if item["shotId"] == shot_id and item["deviceType"] == "CPU"]
        metal_times = [item["renderSeconds"] for item in observations if item["shotId"] == shot_id and item["deviceType"] == "METAL"]
        cpu_median = statistics.median(cpu_times)
        metal_median = statistics.median(metal_times)
        timings[shot_id] = {
            "nativeCpuRenderSeconds": cpu_times, "nativeMetalRenderSeconds": metal_times,
            "nativeCpuMedianSeconds": cpu_median, "nativeMetalMedianSeconds": metal_median,
            "nativeCpuOverMetalMedianSpeedup": cpu_median / metal_median,
            "qemuCpuRenderSeconds": shot["qemuCpuParent"]["renderSeconds"],
            "qemuOverNativeCpuMedianSpeedup": shot["qemuCpuParent"]["renderSeconds"] / cpu_median,
            "qemuOverNativeMetalMedianSpeedup": shot["qemuCpuParent"]["renderSeconds"] / metal_median,
        }

    operation_counts = {
        "nativeBlenderProcesses": sum(item.startswith("NATIVE_BLENDER_PROCESS_") for item in receipt["runtimeOperations"]),
        "dockerRuns": 0, "imageBuilds": 0, "downloads": 0, "modelCalls": 0, "videoModelCalls": 0,
    }
    evidence = {
        "schemaVersion": "bfs.nativeCyclesBackendDerivationEvidence.v0.1", "experimentId": spec["experimentId"],
        "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["toolFreezeCommit"], "tools": receipt["tools"],
        "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "parents": receipt["parents"], "parentObservations": receipt["parentObservations"], "sourceObservations": receipt["sourceObservations"],
        "blenderObservation": receipt["blenderObservation"], "diskAdmission": receipt["diskAdmission"], "observations": observations,
        "comparisons": comparisons, "timings": timings, "operationCounts": operation_counts, "nonClaims": spec["nonClaims"], "baseFailure": None,
    }
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence))
    failure = validate(evidence, spec)
    evidence["baseFailure"] = failure
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence))
    failure = validate(evidence, spec)
    evidence["baseFailure"] = failure
    evidence["attacks"] = run_attacks(evidence, spec)
    evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"])
    evidence["verdict"] = "NATIVE_CYCLES_BACKEND_DERIVATION_USABLE" if failure is None and evidence["attacksPassed"] == len(spec["attacks"]) else "NATIVE_CYCLES_BACKEND_DERIVATION_INVALID"
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B51_D1_RESULT verdict={evidence['verdict']} attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={failure or 'none'}", flush=True)
    for shot_id, row in timings.items():
        print(f"BFS_B51_D1_TIMING {shot_id} cpu={row['nativeCpuMedianSeconds']:.6f}s metal={row['nativeMetalMedianSeconds']:.6f}s cpu_over_metal={row['nativeCpuOverMetalMedianSpeedup']:.3f}x", flush=True)


if __name__ == "__main__":
    main()
