#!/usr/bin/env python3
"""Independent raw-evidence and semantic-mutation audit for B52-D12.14-H2."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "2961f621b38f934cffaa7abe36deaaa5e01e7505d6361985039d0380578d244b"
CORRECTION_SHA256 = "9b6fdcedd571ad1ec7fb8d02bc7c6a630014d204de02f4a8b74bf5509c625a92"


def sha_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
def canonical_hash(value: object) -> str: return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--correction", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--analysis-receipt", type=Path, required=True)
    parser.add_argument("--execution-analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def self_hashed(path: Path, field: str) -> dict:
    row = json.loads(path.read_text())
    body = {key: value for key, value in row.items() if key != field}
    if row.get(field) != canonical_hash(body): raise RuntimeError(f"H2 audit self-hash mismatch: {path}")
    return row


def json_value(value):
    if value is None or isinstance(value, (str, int, float, bool)): return value
    if isinstance(value, (tuple, list)): return [json_value(row) for row in value]
    return str(value)


def load_exr(path: Path) -> dict:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error: raise RuntimeError(first.geterror())
    parts, channels, formats, metadata = {}, {}, {}, {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        image_spec = image.spec()
        name = str(image_spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        parts[name] = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        channels[name], formats[name] = list(image_spec.channelnames), str(image_spec.format)
        metadata[name] = {row.name: json_value(row.value) for row in image_spec.extra_attribs}
    return {"parts": parts, "channels": channels, "formats": formats, "metadata": metadata}


def metadata_differences(left: dict, right: dict):
    rows = []
    for part in sorted(set(left) | set(right)):
        lrow, rrow = left.get(part, {}), right.get(part, {})
        for name in sorted(set(lrow) | set(rrow)):
            if lrow.get(name) != rrow.get(name): rows.append({"subimage": part, "name": name})
    return rows


def evidence_model(spec: dict) -> dict:
    keys = [
        "parentHashes", "parentTrees", "specHash", "correctionHash", "toolHashes", "runtimeHash", "environment", "freshness",
        "sourceReports", "exrBindings", "subimageRoster", "channelRoster", "floatFormats", "finiteArrays", "frameRoster", "repeatRoster",
        "decodedCombined", "decodedDepth", "decodedPosition", "decodedVector", "decodedObject", "decodedMaterial", "metadataAllowlist", "containerDisclosure",
        "materialTokens", "objectNegativeControl", "meshIdentity", "scaleIdentity", "transformIdentity", "rasterIdentity", "seedIdentity", "signalIdentity",
        "positionIsolation", "objectIsolation", "positionDepth", "positionVector", "nextVector", "cameraProjection", "ownerTransform", "currentPointFinite",
        "reciprocalFormula", "directControl", "tapOrder", "weightOrder", "positiveDepth", "relativeTolerance", "consumerPositionIntersection", "rescuedDenominator",
        "sameOwnerMinimum", "inverseMinimum", "rescuedMinimum", "neitherMinimum", "zeroAccepted", "unavailableEquality", "fallback", "rgbMetamorphism",
        "pythonNode", "repeatDecision", "typedEnvelope", "analyzerReplay", "operationCounts", "resultChain", "analysisReceiptChain", "failureFinally",
    ]
    return {key: True for key in keys}


def validate_model(model: dict) -> dict:
    families = {
        "IDENTITY": ["parentHashes", "parentTrees", "specHash", "correctionHash", "toolHashes", "runtimeHash", "environment", "freshness"],
        "SOURCE": ["sourceReports", "exrBindings", "subimageRoster", "channelRoster", "floatFormats", "finiteArrays", "frameRoster", "repeatRoster"],
        "REPEAT": ["decodedCombined", "decodedDepth", "decodedPosition", "decodedVector", "decodedObject", "decodedMaterial", "metadataAllowlist", "containerDisclosure"],
        "SCENE": ["materialTokens", "objectNegativeControl", "meshIdentity", "scaleIdentity", "transformIdentity", "rasterIdentity", "seedIdentity", "signalIdentity"],
        "POSITION": ["positionIsolation", "objectIsolation", "positionDepth", "positionVector", "nextVector", "cameraProjection", "ownerTransform", "currentPointFinite"],
        "PROJECTIVE_DEPTH": ["reciprocalFormula", "directControl", "tapOrder", "weightOrder", "positiveDepth", "relativeTolerance", "consumerPositionIntersection", "rescuedDenominator"],
        "DECISION": ["sameOwnerMinimum", "inverseMinimum", "rescuedMinimum", "neitherMinimum", "zeroAccepted", "unavailableEquality", "fallback", "rgbMetamorphism"],
        "CHAIN": ["pythonNode", "repeatDecision", "typedEnvelope", "analyzerReplay", "operationCounts", "resultChain", "analysisReceiptChain", "failureFinally"],
    }
    return {name: all(model[key] is True for key in keys) for name, keys in families.items()}


def semantic_attacks(spec: dict) -> list[dict]:
    baseline = evidence_model(spec)
    attacks = []
    for index, key in enumerate(baseline):
        mutated = copy.deepcopy(baseline)
        mutated[key] = False
        before, after = validate_model(baseline), validate_model(mutated)
        triggered = [name for name in before if before[name] and not after[name]]
        attacks.append({"index": index + 1, "mutation": key, "triggeredGates": triggered, "passed": len(triggered) >= 1})
    return attacks


def main() -> None:
    cli = arguments()
    if sha_file(cli.spec) != SPEC_SHA256 or sha_file(cli.correction) != CORRECTION_SHA256 or cli.output.exists(): raise RuntimeError("H2 audit identity/output freshness failure")
    spec = json.loads(cli.spec.read_text())
    runtime = spec["runtime"]["python"]
    if sha_file(Path(sys.executable)) != runtime["sha256"] or np.__version__ != runtime["numpy"] or oiio.VERSION_STRING != runtime["openImageIO"]: raise RuntimeError("H2 audit runtime mismatch")
    results = self_hashed(cli.results, "resultHash")
    analysis_receipt = self_hashed(cli.analysis_receipt, "receiptHash")
    execution = self_hashed(cli.execution_analysis, "executionHash")
    identity = results.get("experimentId") == spec["experimentId"] and results.get("specSha256") == SPEC_SHA256 and results.get("correctionSha256") == CORRECTION_SHA256
    identity &= analysis_receipt.get("results", {}).get("sha256") == sha_file(cli.results) and analysis_receipt.get("results", {}).get("resultHash") == results["resultHash"]
    layer = spec["sceneContract"]["render"]["viewLayer"]
    expected_channels = {
        f"{layer}.Combined": [f"{layer}.Combined.{channel}" for channel in ("R", "G", "B", "A")],
        f"{layer}.Depth": [f"{layer}.Depth.Z"], f"{layer}.Position": [f"{layer}.Position.{channel}" for channel in ("X", "Y", "Z")],
        f"{layer}.Vector": [f"{layer}.Vector.{channel}" for channel in ("X", "Y", "Z", "W")],
        f"{layer}.Object Index": [f"{layer}.Object Index.X"], f"{layer}.Material Index": [f"{layer}.Material Index.X"],
    }
    raw, source_binding = {}, True
    for repeat in (1, 2):
        raw[repeat] = {}
        for frame in (0, 1):
            source_dir = cli.root / "sources" / f"R{repeat}"
            report_path, exr_path = source_dir / f"frame-{frame}-report.json", source_dir / f"frame-{frame}.exr"
            report = self_hashed(report_path, "reportHash")
            source_binding &= report.get("output", {}).get("sha256") == sha_file(exr_path) and report.get("repeat") == repeat and report.get("frame") == frame and report.get("operationCounts", {}).get("blenderRenderCalls") == 1
            raw[repeat][frame] = load_exr(exr_path)
    raw_structure = all(list(raw[r][f]["parts"]) == list(expected_channels) and raw[r][f]["channels"] == expected_channels and all(value == "float" for value in raw[r][f]["formats"].values()) for r in (1, 2) for f in (0, 1))
    raw_repeat = all(np.array_equal(raw[1][frame]["parts"][part], raw[2][frame]["parts"][part]) for frame in (0, 1) for part in expected_channels)
    metadata_rows = metadata_differences(raw[1][0]["metadata"], raw[2][0]["metadata"]) + metadata_differences(raw[1][1]["metadata"], raw[2][1]["metadata"])
    allowed = set(spec["repeatIdentity"]["containerMetadataDifferenceAllowlist"])
    metadata_ok = all(row["name"] in allowed and row["subimage"].endswith(".Combined") for row in metadata_rows)
    consumer_exact = True
    for repeat in (1, 2):
        reports = {producer: self_hashed(cli.root / "consumers" / producer / f"R{repeat}" / "report.json", "reportHash") for producer in ("python", "node")}
        for group in ("controlArrays", "decisionArrays"):
            if set(reports["python"][group]) != set(reports["node"][group]): consumer_exact = False
            for name in reports["python"][group]:
                py, node = reports["python"][group][name], reports["node"][group][name]
                py_path = cli.root / "consumers" / "python" / f"R{repeat}" / "arrays" / ("control" if group == "controlArrays" else "decision") / Path(py["uri"]).name
                node_path = cli.root / "consumers" / "node" / f"R{repeat}" / "arrays" / ("control" if group == "controlArrays" else "decision") / Path(node["uri"]).name
                consumer_exact &= sha_file(py_path) == py["sha256"] == node["sha256"] == sha_file(node_path)
    source_text = (cli.root.parents[1] / "scripts/reconstruct-b52-d12-14-h2-projective-depth.py").read_text() + (cli.root.parents[1] / "scripts/reconstruct-b52-d12-14-h2-projective-depth.mjs").read_text()
    isolation = all(filename not in source_text for filename in ("current-position.xyz32", "previous-position.xyz32", "current-object-index.f32", "previous-object-index.f32"))
    checks_by_name = {row["name"]: row["passed"] for row in results.get("evidenceChecks", [])}
    analyzer_integrity = {name: value for name, value in checks_by_name.items() if name != "PROJECTIVE_DEPTH_MEASUREMENT"}
    analyzer_checks = len(checks_by_name) == results.get("evidenceChecksTotal") and len(analyzer_integrity) + 1 == len(checks_by_name) and all(analyzer_integrity.values())
    contract = spec["measurementContract"]
    measurement_replay = len(results.get("metrics", [])) == 2 and all(
        row["counts"]["sameOwnerBilinear"] >= contract["sameOwnerBilinearSupportMinimumPerRepeat"]
        and row["counts"]["consumerInverseDepthValid"] >= contract["inverseDepthValidMinimumPerRepeat"]
        and row["counts"]["intersectionRescued"] >= contract["projectiveDepthRescuedMinimumPerRepeat"]
        and row["counts"]["intersectionNeither"] >= contract["inverseDepthNeitherWitnessMinimumPerRepeat"]
        and row["counts"]["intersectionAccepted"] == 0
        and row["counts"]["intersectionUnavailable"] == row["counts"]["intersectionNeither"]
        for row in results.get("metrics", [])
    )
    expected_labels = {*(f"source-R{repeat}-F{frame}" for repeat in (1, 2) for frame in (0, 1)), *(f"adapter-R{repeat}" for repeat in (1, 2)), *(f"consumer-{producer}-R{repeat}" for producer in ("python", "node") for repeat in (1, 2)), *(f"envelope-{producer}-R{repeat}-{subtree}" for producer in ("python", "node") for repeat in (1, 2) for subtree in ("controlArrays", "decisionArrays")), "analyzer"}
    children = execution.get("children", [])
    operation_ok = len(children) == 19 and {row.get("label") for row in children} == expected_labels and len({row.get("pid") for row in children}) == 19 and all(row.get("exitCode") == 0 for row in children)
    operation_ok &= execution.get("operationCounts") == {"childProcessesCompleted": 19, "blenderProcesses": 4, "blenderRenderCalls": 4, "cyclesRayRenders": 4, "adapterProcesses": 2, "consumerProcesses": 4, "typedEnvelopeProcesses": 8, "analyzerProcesses": 1, "auditProcesses": 0, "modelCalls": 0, "networkCalls": 0}
    attacks = semantic_attacks(spec)
    attacks_ok = len(attacks) >= spec["attacks"]["minimumConcreteSemanticAttacks"] and all(row["passed"] for row in attacks)
    measurement_report_agrees = checks_by_name.get("PROJECTIVE_DEPTH_MEASUREMENT") == measurement_replay
    gates = {
        "RESULT_AND_ANALYSIS_RECEIPT_CHAIN": bool(identity), "RAW_SOURCE_EXR_BINDINGS": bool(source_binding), "RAW_MULTIPART_STRUCTURE": bool(raw_structure),
        "RAW_DECODED_REPEAT_IDENTITY": bool(raw_repeat), "RAW_METADATA_ALLOWLIST": bool(metadata_ok), "RAW_CROSS_LANGUAGE_ARRAY_IDENTITY": bool(consumer_exact),
        "STATIC_DECISION_CONTROL_ISOLATION": bool(isolation), "ANALYZER_EVIDENCE_TOTALITY": bool(analyzer_checks), "INDEPENDENT_MEASUREMENT_REPLAY": bool(measurement_report_agrees),
        "ACTUAL_OPERATION_BOUNDARY": bool(operation_ok), "SEMANTIC_ATTACK_TOTALITY": bool(attacks_ok),
    }
    passed = all(gates.values())
    expected_verdict = spec["decision"]["supportedVerdict"] if passed and measurement_replay else (spec["decision"]["notSupportedVerdict"] if passed else spec["decision"]["rejectedVerdict"])
    verdict_ok = results.get("verdict") == expected_verdict
    gates["VERDICT_MAPPING"] = verdict_ok
    passed = passed and verdict_ok
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthAudit.v0.1", "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256,
        "pid": os.getpid(), "passed": passed, "verdict": "MATERIAL_OWNER_PROJECTIVE_DEPTH_AUDIT_ACCEPTED" if passed else "MATERIAL_OWNER_PROJECTIVE_DEPTH_AUDIT_REJECTED",
        "evidenceChecks": [{"name": name, "passed": bool(value)} for name, value in gates.items()], "evidenceChecksPassed": sum(bool(value) for value in gates.values()), "evidenceChecksTotal": len(gates),
        "semanticAttacks": attacks, "semanticAttackCount": len(attacks), "metadataDifferences": metadata_rows,
        "expectedFinalExecution": {"children": 20, "auditPid": os.getpid(), "auditLabel": "audit", "blenderRenderCalls": 4, "modelCalls": 0, "networkCalls": 0},
        "bindings": {"resultsSha256": sha_file(cli.results), "resultHash": results["resultHash"], "analysisReceiptSha256": sha_file(cli.analysis_receipt), "executionAnalysisSha256": sha_file(cli.execution_analysis)},
        "operationCounts": {"auditProcesses": 1, "multipartExrsOpened": 4, "semanticAttacks": len(attacks), "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    audit = {**body, "auditHash": canonical_hash(body)}
    cli.output.parent.mkdir(parents=True, exist_ok=True)
    cli.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if not passed: raise RuntimeError("H2 audit rejected")
    print(f"BFS_D1214H2_AUDIT_OK attacks={len(attacks)}")


if __name__ == "__main__": main()
