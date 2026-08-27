"""Analyze, attack, and decide the formal B49-DOF holdout."""

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


LIBRARY_PATH = Path(__file__).with_name("analyze-b49-motion-blur-holdout.py")
LIBRARY_SPEC = importlib.util.spec_from_file_location("bfs_b49_metric_library", LIBRARY_PATH)
metric_library = importlib.util.module_from_spec(LIBRARY_SPEC)
LIBRARY_SPEC.loader.exec_module(metric_library)
RAW_ROSTER = metric_library.RAW_ROSTER


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def decide(evidence, spec):
    if any(not quality["candidatePassed"] for quality in evidence["qualityByShot"].values()):
        return spec["rejectedVerdict"]
    minimum = spec["qualityGate"]["minimumMetricsWhereCandidateStrictlyCloserThanNegativeControlPerShot"]
    if all(quality["candidateCloserMetricCount"] >= minimum for quality in evidence["qualityByShot"].values()):
        return spec["acceptedVerdict"]
    return spec["indistinguishableVerdict"]


def hash_payload(evidence):
    return {key: value for key, value in evidence.items() if key not in {"evidenceCoreHash", "attacks", "attacksPassed"}}


def close(left, right):
    return abs(float(left) - float(right)) <= 1e-6


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
    shots = {item["id"]: item for item in spec["shots"]}
    for cell_id, cell in expected_cells.items():
        item = observed_cells[cell_id]
        settings, camera, shot = item["settings"], item["camera"], shots[cell["shot"]]
        if settings["samples"] != cell["samples"]: return "SAMPLE_SETTING"
        if settings["seedOffset"] != cell["seedOffset"] or settings["seed"] != item["baseShotSeed"] + cell["seedOffset"]: return "SEED_SETTING"
        render = spec["render"]
        if settings["motionBlur"] != render["motionBlur"] or not close(settings["motionBlurShutter"], render["motionBlurShutter"]) or settings["motionBlurPosition"] != render["motionBlurPosition"]: return "MOTION_BLUR_SETTING"
        if camera["useDof"] != cell["useDof"]: return "DOF_SETTING"
        expected_camera = shot["camera"]
        if camera["name"] != expected_camera["name"] or not close(camera["lensMm"], expected_camera["lensMm"]) or not close(camera["focusDistanceM"], expected_camera["focusDistanceM"]) or not close(camera["apertureFStop"], expected_camera["apertureFStop"]) or camera["focusObject"] != expected_camera["focusObject"]: return "FOCUS_BINDING"
        if item["roster"] != RAW_ROSTER: return "PASS_ROSTER"
        if not all(value["finite"] for value in item["passes"].values()): return "NON_FINITE"
    metrics = spec["qualityGate"]["metrics"]
    for shot_id, quality in evidence["qualityByShot"].items():
        if len({item["combinedCanonicalFloat32Sha256"] for item in quality["references"]}) != spec["qualityGate"]["referenceCountPerShot"]: return "REFERENCE_DISTINCT"
        if any(not math.isfinite(value) or value <= 0 for value in quality["referenceFloor"].values()): return "QUALITY_FLOOR"
        expected_multiples = {name: quality["candidateMetrics"][name] / quality["referenceFloor"][name] for name in metrics}
        if any(abs(expected_multiples[name] - quality["candidateFloorMultiples"][name]) > 1e-12 for name in metrics): return "METRIC_REPLAY"
        expected_pass = all(value <= spec["qualityGate"]["maximumFloorMultiple"] for value in expected_multiples.values())
        closer = [name for name in metrics if quality["candidateMetrics"][name] < quality["negativeControlMetrics"][name]]
        if quality["candidatePassed"] != expected_pass or quality["candidateCloserMetrics"] != closer or quality["candidateCloserMetricCount"] != len(closer): return "METRIC_REPLAY"
    gate = spec["passDomainGate"]
    for relation in evidence["passDomains"].values():
        if any(relation[name]["exact"] for name in gate["mustDiffer"]): return "PASS_DOMAIN"
        if any(not relation[name]["exact"] for name in gate["mustRemainExact"]): return "PASS_DOMAIN"
        if not any(not relation[name]["exact"] for name in gate["atLeastOneAuxiliaryMustDiffer"]): return "PASS_DOMAIN"
    if evidence["verdict"] != decide(evidence, spec): return "VERDICT_REPLAY"
    expected_counts = {key: spec["operationBoundary"][key] for key in ("dockerRuns", "hostExrAnalyses", "builds", "pulls", "downloads", "modelCalls", "videoModelCalls")}
    if evidence["operationCounts"] != expected_counts: return "OPERATION_BOUNDARY"
    if evidence["cleanup"]["experimentContainersRunningAfter"] != 0: return "CLEANUP"
    if evidence.get("evidenceCoreHash") != canonical_hash(hash_payload(evidence)): return "EVIDENCE_SELF_HASH"
    return None


def attacks(evidence, spec):
    cases = []
    def add(attack_id, expected, mutator):
        clone = copy.deepcopy(evidence); mutator(clone)
        clone["evidenceCoreHash"] = canonical_hash(hash_payload(clone)) if expected != "EVIDENCE_SELF_HASH" else "0" * 64
        observed = validate(clone, spec)
        cases.append({"id": attack_id, "expectedReason": expected, "observedReason": observed, "passed": observed == expected})
    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_SOURCE", "SOURCE_IDENTITY", lambda x: x["sourceObservations"][0].update(match=False))
    add("A03_IMAGE", "IMAGE_IDENTITY", lambda x: x["image"].update(architecture="arm64"))
    add("A04_SECURITY", "SECURITY_BOUNDARY", lambda x: x["securityBoundary"].update(network="bridge"))
    add("A05_DISK", "DISK_ADMISSION", lambda x: x["diskAdmission"].update(status="BLOCKED"))
    add("A06_CELLS", "CELL_ROSTER", lambda x: x["observations"].pop())
    add("A07_SAMPLES", "SAMPLE_SETTING", lambda x: x["observations"][0]["settings"].update(samples=511))
    add("A08_SEED", "SEED_SETTING", lambda x: x["observations"][0]["settings"].update(seedOffset=1))
    add("A09_BLUR", "MOTION_BLUR_SETTING", lambda x: x["observations"][0]["settings"].update(motionBlur=False))
    add("A10_DOF", "DOF_SETTING", lambda x: x["observations"][0]["camera"].update(useDof=False))
    add("A11_FOCUS", "FOCUS_BINDING", lambda x: x["observations"][0]["camera"].update(focusDistanceM=999))
    add("A12_ROSTER", "PASS_ROSTER", lambda x: x["observations"][0]["roster"].pop())
    add("A13_FINITE", "NON_FINITE", lambda x: x["observations"][0]["passes"]["BFS_MASTER.Combined"].update(finite=False))
    add("A14_REFERENCES", "REFERENCE_DISTINCT", lambda x: x["qualityByShot"]["TABLETOP"]["references"][1].update(combinedCanonicalFloat32Sha256=x["qualityByShot"]["TABLETOP"]["references"][0]["combinedCanonicalFloat32Sha256"]))
    add("A15_FLOOR", "QUALITY_FLOOR", lambda x: x["qualityByShot"]["TABLETOP"]["referenceFloor"].update(linearNrmseByEnsembleRms=0))
    add("A16_METRIC", "METRIC_REPLAY", lambda x: x["qualityByShot"]["TABLETOP"]["candidateFloorMultiples"].update(linearNrmseByEnsembleRms=999))
    add("A17_DOMAIN", "PASS_DOMAIN", lambda x: x["passDomains"]["TABLETOP"]["BFS_MASTER.Vector"].update(exact=False))
    add("A18_VERDICT", "VERDICT_REPLAY", lambda x: x.update(verdict=spec["invalidVerdict"]))
    add("A19_OPERATIONS", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(dockerRuns=11))
    add("A20_CLEANUP", "CLEANUP", lambda x: x["cleanup"].update(experimentContainersRunningAfter=1))
    add("A21_HASH", "EVIDENCE_SELF_HASH", lambda x: None)
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--receipt", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); spec = json.loads(args.spec.read_text()); receipt = json.loads(args.receipt.read_text()); root = args.receipt.parent
    arrays, observations = {}, []
    for run in receipt["runs"]:
        cell = next(item for item in spec["cells"] if item["id"] == run["runId"]); report = run["report"]; path = root / run["runId"] / report["artifact"]["uri"]
        roster, passes = metric_library.read_exr(path, *spec["render"]["resolution"]); arrays[cell["id"]] = passes; settings = report["settings"]
        observations.append({"cellId": cell["id"], "shotId": cell["shot"], "frame": report["frame"], "role": cell["role"], "argv": run["argv"], "baseShotSeed": report["bindings"]["baseShotSeed"], "settings": settings, "camera": report["camera"], "renderSeconds": report["renderSeconds"], "freshContainerWallSeconds": run["elapsedMs"] / 1000, "peakSelfRssKiB": report["peakSelfRssKiB"], "roster": roster, "passes": {name: {key: value for key, value in data.items() if key != "pixels"} for name, data in passes.items()}, "artifact": {"uri": str(path.relative_to(root.parent.parent)), "sha256": sha256_file(path), "bytes": path.stat().st_size}})
    quality_by_shot = {}
    for shot in spec["shots"]:
        shot_cells = [cell for cell in spec["cells"] if cell["shot"] == shot["id"]]; refs = [cell["id"] for cell in shot_cells if cell["role"] == "reference"]
        ref_arrays = [arrays[cell_id]["BFS_MASTER.Combined"]["pixels"] for cell_id in refs]; ensemble = np.mean(np.stack([value.astype(np.float64) for value in ref_arrays]), axis=0); rms = float(np.sqrt(np.mean(np.square(ensemble[..., :3])))); mask, count, cutoff = metric_library.edge_mask(ensemble[..., :3]); ref_rows = []
        for cell_id, pixels in zip(refs, ref_arrays): ref_rows.append({"cellId": cell_id, "combinedCanonicalFloat32Sha256": arrays[cell_id]["BFS_MASTER.Combined"]["canonicalFloat32Sha256"], "metricsAgainstEnsemble": metric_library.metrics(pixels, ensemble, mask, rms)})
        names = spec["qualityGate"]["metrics"]; floor = {name: max(item["metricsAgainstEnsemble"][name] for item in ref_rows) for name in names}; candidate = next(cell["id"] for cell in shot_cells if cell["role"] == "candidate"); negative = next(cell["id"] for cell in shot_cells if cell["role"] == "negative control"); candidate_metrics = metric_library.metrics(arrays[candidate]["BFS_MASTER.Combined"]["pixels"], ensemble, mask, rms); negative_metrics = metric_library.metrics(arrays[negative]["BFS_MASTER.Combined"]["pixels"], ensemble, mask, rms); multiples = {name: candidate_metrics[name] / floor[name] for name in names}; closer = [name for name in names if candidate_metrics[name] < negative_metrics[name]]
        quality_by_shot[shot["id"]] = {"ensemble": {"dtype": "float64-le", "shape": list(ensemble.shape), "sha256": hashlib.sha256(np.ascontiguousarray(ensemble.astype("<f8")).tobytes()).hexdigest(), "rgbRms": rms}, "edgeMask": {"pixelCount": count, "gradientCutoff": cutoff}, "references": ref_rows, "referenceFloor": floor, "candidateCellId": candidate, "candidateMetrics": candidate_metrics, "candidateFloorMultiples": multiples, "candidatePassed": all(value <= spec["qualityGate"]["maximumFloorMultiple"] for value in multiples.values()), "negativeControlCellId": negative, "negativeControlMetrics": negative_metrics, "candidateCloserMetrics": closer, "candidateCloserMetricCount": len(closer)}
    pass_domains = {}
    for left, right in spec["passDomainGate"]["comparisons"]: pass_domains[next(cell["shot"] for cell in spec["cells"] if cell["id"] == left)] = metric_library.domain_compare(arrays[left], arrays[right])
    operation_counts = {"dockerRuns": sum(item.startswith("DOCKER_RUN_") for item in receipt["runtimeOperations"]), "hostExrAnalyses": sum(item.startswith("HOST_EXR_ANALYSIS_") for item in receipt["runtimeOperations"]), "builds": 0, "pulls": 0, "downloads": 0, "modelCalls": 0, "videoModelCalls": 0}
    evidence = {"schemaVersion": "bfs.codexWorkerDepthOfFieldHoldoutEvidence.v0.1", "experimentId": spec["experimentId"], "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["toolFreezeCommit"], "tools": receipt["tools"], "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__}, "parents": receipt["parents"], "parentObservations": receipt["parentObservations"], "sourceObservations": receipt["sourceObservations"], "image": receipt["image"], "hostInspector": receipt["hostInspectorObservation"], "diskAdmission": receipt["diskAdmission"], "securityBoundary": receipt["securityBoundary"], "observations": observations, "qualityByShot": quality_by_shot, "passDomains": pass_domains, "operationCounts": operation_counts, "cleanup": receipt["cleanup"], "nonClaims": spec["nonClaims"], "baseFailure": None}
    evidence["verdict"] = decide(evidence, spec); evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); failure = validate(evidence, spec); evidence["baseFailure"] = failure
    if failure is not None: evidence["verdict"] = spec["invalidVerdict"]
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); failure = validate(evidence, spec); evidence["baseFailure"] = failure; evidence["attacks"] = attacks(evidence, spec); evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"])
    if failure is not None or evidence["attacksPassed"] != len(spec["attacks"]): evidence["verdict"] = spec["invalidVerdict"]; evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence))
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B49_DOF_HOLDOUT_RESULT verdict={evidence['verdict']} closer=" + ",".join(f"{key}:{value['candidateCloserMetricCount']}/3" for key, value in quality_by_shot.items()) + f" attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={failure or 'none'}", flush=True)


if __name__ == "__main__": main()
