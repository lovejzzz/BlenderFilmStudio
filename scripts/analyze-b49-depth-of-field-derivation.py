"""Analyze, attack, and classify B49-DOF-D1 derivation evidence."""

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
    roster, passes = [], {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        roster.append(name)
        if pixels.shape[0:2] != (height, width):
            raise RuntimeError(f"invalid pass shape: {name} {pixels.shape}")
        metadata = {"name": name, "shape": list(pixels.shape), "channels": list(spec.channelnames), "dtype": "float32-le", "order": "C"}
        header = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        passes[name] = {"pixels": pixels, "shape": list(pixels.shape), "channels": list(spec.channelnames), "finite": bool(np.isfinite(pixels).all()), "canonicalFloat32Sha256": hashlib.sha256(header + pixels.tobytes(order="C")).hexdigest()}
    return roster, passes


def roi_metrics(combined, roi):
    x0, y0, x1, y1 = roi
    rgb = combined[y0:y1, x0:x1, :3].astype(np.float64)
    luminance = np.tensordot(rgb, AP1_LUMA, axes=([2], [0]))
    p05 = float(np.percentile(luminance, 5))
    p95 = float(np.percentile(luminance, 95))
    gradient = np.diff(luminance, axis=1)
    return {"roiPixels": list(roi), "pixelCount": int(luminance.size), "finitePixelCount": int(np.isfinite(luminance).sum()), "p05": p05, "p95": p95, "modulation": float((p95 - p05) / (p95 + p05 + 1e-12)), "horizontalGradientRms": float(np.sqrt(np.mean(np.square(gradient))))}


def domain_compare(left, right):
    result = {}
    for name in RAW_ROSTER:
        a, b = left[name]["pixels"], right[name]["pixels"]
        result[name] = {"exact": bool(np.array_equal(a, b)), "changedFloatComponents": int(np.count_nonzero(np.subtract(a, b, dtype=np.float32))), "rmse": float(np.sqrt(np.mean(np.square(a.astype(np.float64) - b.astype(np.float64))))), "maximumAbsoluteError": float(np.max(np.abs(a.astype(np.float64) - b.astype(np.float64)))), "leftHash": left[name]["canonicalFloat32Sha256"], "rightHash": right[name]["canonicalFloat32Sha256"]}
    return result


def float_equal(left, right):
    return abs(float(left) - float(right)) <= 1e-6


def fixture_matches(observed, spec):
    expected_camera = spec["fixture"]["camera"]
    camera = observed["camera"]
    if camera["type"] != "PERSP" or not float_equal(camera["lensMm"], expected_camera["lensMm"]) or not float_equal(camera["sensorWidthMm"], expected_camera["sensorWidthMm"]):
        return False
    if any(not float_equal(value, expected) for value, expected in zip(camera["locationM"], expected_camera["locationM"])):
        return False
    targets = {item["id"]: item for item in observed["targets"]}
    if list(targets) != [item["id"] for item in spec["fixture"]["targets"]]:
        return False
    for expected in spec["fixture"]["targets"]:
        item = targets[expected["id"]]
        if not float_equal(item["depthM"], expected["depthM"]):
            return False
        if any(not float_equal(a, b) for a, b in zip(item["viewportCenter01"], expected["viewportCenter01"])):
            return False
        if any(not float_equal(a, b) for a, b in zip(item["viewportSize01"], expected["viewportSize01"])):
            return False
    return all(float_equal(a, b) for a, b in zip(observed["focusObjectLocationM"], spec["fixture"]["focusObject"]["locationM"]))


def hash_payload(evidence):
    return {key: value for key, value in evidence.items() if key not in {"evidenceCoreHash", "attacks", "attacksPassed"}}


def validate(evidence, spec):
    if not all(item["match"] for item in evidence["parentObservations"]): return "PARENT_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"]): return "SOURCE_IDENTITY"
    expected_image = {"id": spec["image"]["id"], "os": spec["image"]["os"], "architecture": spec["image"]["architecture"], "sizeBytes": spec["image"]["dockerReportedSizeBytes"]}
    if evidence["image"] != expected_image: return "IMAGE_IDENTITY"
    if evidence["securityBoundary"] != spec["containerContract"]: return "SECURITY_BOUNDARY"
    if evidence["diskAdmission"]["status"] != "ACCEPTED": return "DISK_ADMISSION"
    expected_cells = {item["id"]: item for item in spec["cells"]}
    observed_cells = {item["cellId"]: item for item in evidence["observations"]}
    if list(observed_cells) != list(expected_cells): return "CELL_ROSTER"
    for cell_id, cell in expected_cells.items():
        item = observed_cells[cell_id]
        if not fixture_matches(item["fixture"], spec): return "FIXTURE_ECHO"
        settings = item["settings"]
        expected_object = spec["fixture"]["focusObject"]["id"] if cell["focusMode"] == "OBJECT" else None
        if settings["useDof"] != cell["useDof"] or settings["focusMode"] != cell["focusMode"] or not float_equal(settings["focusDistanceM"], cell["focusDistanceM"]) or settings["focusObject"] != expected_object or not float_equal(settings["apertureFStop"], cell["apertureFStop"]): return "DOF_SETTING"
        if item["roster"] != RAW_ROSTER: return "PASS_ROSTER"
        if not all(value["finite"] for value in item["passes"].values()): return "NON_FINITE"
        for target in spec["fixture"]["targets"]:
            metric = item["targetMetrics"][target["id"]]
            roi = target["roiPixels"]
            expected_count = (roi[2] - roi[0]) * (roi[3] - roi[1])
            if metric["roiPixels"] != roi or metric["pixelCount"] != expected_count or metric["finitePixelCount"] != expected_count or not metric["p95"] > metric["p05"]: return "ROI_INVALID"
    if set(evidence["relations"]) != {"apertureDoseAtMidFocus", "focusSelectivity", "focusObjectOverride", "passDomain"}: return "RELATION_MISSING"
    expected_counts = {key: spec["operationBoundary"][key] for key in ("dockerRuns", "hostExrAnalyses", "builds", "pulls", "downloads", "modelCalls", "videoModelCalls")}
    if evidence["operationCounts"] != expected_counts: return "OPERATION_BOUNDARY"
    if evidence["cleanup"]["experimentContainersRunningAfter"] != 0: return "CLEANUP"
    if evidence.get("evidenceCoreHash") != canonical_hash(hash_payload(evidence)): return "EVIDENCE_SELF_HASH"
    return None


def attack_cases(evidence, spec):
    cases = []
    def add(attack_id, expected, mutator):
        clone = copy.deepcopy(evidence)
        mutator(clone)
        clone["evidenceCoreHash"] = canonical_hash(hash_payload(clone)) if expected != "EVIDENCE_SELF_HASH" else "0" * 64
        observed = validate(clone, spec)
        cases.append({"id": attack_id, "expectedReason": expected, "observedReason": observed, "passed": observed == expected})
    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_SOURCE", "SOURCE_IDENTITY", lambda x: x["sourceObservations"][0].update(match=False))
    add("A03_IMAGE", "IMAGE_IDENTITY", lambda x: x["image"].update(architecture="arm64"))
    add("A04_SECURITY", "SECURITY_BOUNDARY", lambda x: x["securityBoundary"].update(network="bridge"))
    add("A05_DISK", "DISK_ADMISSION", lambda x: x["diskAdmission"].update(status="BLOCKED"))
    add("A06_CELLS", "CELL_ROSTER", lambda x: x["observations"].pop())
    add("A07_FIXTURE", "FIXTURE_ECHO", lambda x: x["observations"][0]["fixture"]["targets"][0].update(depthM=4))
    add("A08_DOF", "DOF_SETTING", lambda x: x["observations"][0]["settings"].update(focusDistanceM=6))
    add("A09_ROSTER", "PASS_ROSTER", lambda x: x["observations"][0]["roster"].pop())
    add("A10_FINITE", "NON_FINITE", lambda x: x["observations"][0]["passes"]["BFS_MASTER.Combined"].update(finite=False))
    add("A11_ROI", "ROI_INVALID", lambda x: x["observations"][0]["targetMetrics"]["NEAR"].update(pixelCount=1))
    add("A12_RELATION", "RELATION_MISSING", lambda x: x["relations"].pop("focusSelectivity"))
    add("A13_OPERATIONS", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(dockerRuns=8))
    add("A14_CLEANUP", "CLEANUP", lambda x: x["cleanup"].update(experimentContainersRunningAfter=1))
    add("A15_HASH", "EVIDENCE_SELF_HASH", lambda x: None)
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    receipt = json.loads(args.receipt.read_text())
    root = args.receipt.parent
    arrays, observations = {}, []
    for run in receipt["runs"]:
        cell = next(item for item in spec["cells"] if item["id"] == run["runId"])
        report = run["report"]
        path = root / run["runId"] / report["artifact"]["uri"]
        roster, passes = read_exr(path, *spec["render"]["resolution"])
        arrays[cell["id"]] = passes
        target_metrics = {target["id"]: roi_metrics(passes["BFS_MASTER.Combined"]["pixels"], target["roiPixels"]) for target in spec["fixture"]["targets"]}
        observations.append({"cellId": cell["id"], "role": cell["role"], "argv": run["argv"], "fixture": report["fixture"], "settings": report["settings"], "renderSeconds": report["renderSeconds"], "freshContainerWallSeconds": run["elapsedMs"] / 1000, "peakSelfRssKiB": report["peakSelfRssKiB"], "roster": roster, "passes": {name: {key: value for key, value in data.items() if key != "pixels"} for name, data in passes.items()}, "targetMetrics": target_metrics, "artifact": {"uri": str(path.relative_to(root.parent.parent)), "sha256": sha256_file(path), "bytes": path.stat().st_size}})
    metrics = {item["cellId"]: item["targetMetrics"] for item in observations}
    aperture_ids = ["OFF_D5_F4", "D5_F16", "D5_F4", "D5_F1_4"]
    aperture_dose = {target["id"]: [{"cellId": cell_id, "modulation": metrics[cell_id][target["id"]]["modulation"], "horizontalGradientRms": metrics[cell_id][target["id"]]["horizontalGradientRms"]} for cell_id in aperture_ids] for target in spec["fixture"]["targets"]}
    focus_map = {"D3_F1_4": "NEAR", "D5_F1_4": "MID", "D8_F1_4": "FAR"}
    focus_selectivity = []
    for cell_id, expected in focus_map.items():
        values = {target["id"]: metrics[cell_id][target["id"]]["modulation"] for target in spec["fixture"]["targets"]}
        observed = max(values, key=values.get)
        focus_selectivity.append({"cellId": cell_id, "expectedHighestModulationTarget": expected, "observedHighestModulationTarget": observed, "followsRequestedPlane": observed == expected, "modulationByTarget": values})
    relations = {"apertureDoseAtMidFocus": aperture_dose, "focusSelectivity": focus_selectivity, "focusObjectOverride": domain_compare(arrays["D5_F1_4"], arrays["OBJ5_F1_4"]), "passDomain": domain_compare(arrays["OFF_D5_F4"], arrays["D5_F1_4"])}
    operation_counts = {"dockerRuns": sum(item.startswith("DOCKER_RUN_") for item in receipt["runtimeOperations"]), "hostExrAnalyses": sum(item.startswith("HOST_EXR_ANALYSIS_") for item in receipt["runtimeOperations"]), "builds": 0, "pulls": 0, "downloads": 0, "modelCalls": 0, "videoModelCalls": 0}
    evidence = {"schemaVersion": "bfs.codexWorkerDepthOfFieldDerivationEvidence.v0.1", "experimentId": spec["experimentId"], "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["toolFreezeCommit"], "tools": receipt["tools"], "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__}, "parents": receipt["parents"], "parentObservations": receipt["parentObservations"], "sourceObservations": receipt["sourceObservations"], "image": receipt["image"], "hostInspector": receipt["hostInspectorObservation"], "diskAdmission": receipt["diskAdmission"], "securityBoundary": receipt["securityBoundary"], "observations": observations, "relations": relations, "operationCounts": operation_counts, "cleanup": receipt["cleanup"], "nonClaims": spec["nonClaims"], "status": spec["usableStatus"], "baseFailure": None}
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence))
    failure = validate(evidence, spec)
    evidence["baseFailure"] = failure
    if failure is not None: evidence["status"] = spec["invalidStatus"]
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence))
    failure = validate(evidence, spec)
    evidence["baseFailure"] = failure
    evidence["attacks"] = attack_cases(evidence, spec)
    evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"])
    if failure is not None or evidence["attacksPassed"] != len(spec["attacks"]):
        evidence["status"] = spec["invalidStatus"]
        evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence))
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    focus_count = sum(item["followsRequestedPlane"] for item in focus_selectivity)
    print(f"BFS_B49_DOF_RESULT status={evidence['status']} focusSelectivity={focus_count}/3 attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={failure or 'none'}", flush=True)


if __name__ == "__main__":
    main()
