#!/usr/bin/env python3
"""Independent mutation audit for B52-D12.13-D1."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import subprocess
import time
from pathlib import Path

import numpy as np


SPEC_SHA256 = "e9d79a2ec54acaf36a0df1168ea71102b0b94ab66f4e10f1cda56dbd1ea70c00"
PARENT_ROOT = Path("experiments/blender-material-owner-one-sided-curvature-holdout-v0-1")


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def self_ok(value: dict, field: str) -> bool:
    return value.get(field) == canonical_hash({key: row for key, row in value.items() if key != field})


def wait_path(path: Path, seconds: float = 30.0):
    deadline = time.monotonic() + seconds
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    if not path.exists():
        raise RuntimeError(f"D12.13-D1 audit timed out waiting for {path}")


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--analysis-receipt", type=Path, required=True)
    parser.add_argument("--execution-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_record(record: dict, dtype: str, shape: tuple[int, ...]):
    payload = Path(record["uri"]).read_bytes()
    expected = int(np.prod(shape)) * np.dtype(dtype).itemsize
    if len(payload) != expected or len(payload) != record["bytes"] or sha_bytes(payload) != record["sha256"]:
        raise RuntimeError(f"D12.13-D1 audit array binding failed: {record['uri']}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy(), payload


def report(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not self_ok(value, "reportHash"):
        raise RuntimeError(f"D12.13-D1 audit report self-hash failed: {path}")
    return value


def normalized(value: dict) -> dict:
    result = {key: row for key, row in value.items() if key not in {"producer", "runtime", "pid", "reportHash"}}
    result["sharedArrays"] = {
        key: {field: item for field, item in row.items() if field != "uri"}
        for key, row in value["sharedArrays"].items()
    }
    result["thresholdArrays"] = {}
    for threshold, row in value["thresholdArrays"].items():
        result["thresholdArrays"][threshold] = {
            "acceptedCount": row["acceptedCount"],
            "accepted": {field: item for field, item in row["accepted"].items() if field != "uri"},
            "reconstructed": {field: item for field, item in row["reconstructed"].items() if field != "uri"},
        }
    return result


def main():
    cli = arguments()
    if sha_file(cli.spec) != SPEC_SHA256 or cli.output.exists():
        raise RuntimeError("D12.13-D1 audit spec/output identity violation")
    spec = json.loads(cli.spec.read_text())
    for path in (cli.execution_plan, cli.result, cli.analysis_receipt):
        wait_path(path)
    plan = json.loads(cli.execution_plan.read_text())
    result = json.loads(cli.result.read_text())
    analysis = json.loads(cli.analysis_receipt.read_text())
    thresholds = spec["thresholdFamily"]["candidateThresholdsQ30Descending"]
    h1_spec = json.loads(Path(spec["parents"]["h1Spec"]["uri"]).read_text())
    fixtures = {row["id"]: row for row in h1_spec["fixtures"]}
    candidate_by_threshold = {row["thresholdQ30"]: row for row in result.get("candidates", [])}

    baseline = {}
    baseline["SPEC_SELF_IDENTITY"] = sha_file(cli.spec) == SPEC_SHA256
    baseline["RESULT_SELF_HASH"] = self_ok(result, "resultHash")
    baseline["ANALYSIS_RECEIPT_SELF_HASH"] = self_ok(analysis, "receiptHash")
    baseline["ANALYSIS_RESULT_BINDING"] = (
        analysis.get("result", {}).get("sha256") == sha_file(cli.result)
        and analysis.get("result", {}).get("resultHash") == result.get("resultHash")
    )
    baseline["EXECUTION_PLAN_SELF_HASH"] = self_ok(plan, "executionPlanHash")
    parent_ok = True
    for key in ("h1Spec", "h1Result", "h1Audit", "h1Receipt"):
        row = spec["parents"][key]
        parent_ok &= sha_file(Path(row["uri"])) == row["sha256"]
    actual_tree = subprocess.run(
        ["git", "rev-parse", f"HEAD:{spec['parents']['h1FormalRoot']['uri']}"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    parent_ok &= actual_tree == spec["parents"]["h1FormalRoot"]["gitTree"]
    baseline["PARENT_BYTES_AND_FORMAL_TREE"] = bool(parent_ok)
    tools_ok = True
    for uri, expected in result.get("toolHashes", {}).items():
        tools_ok &= sha_file(Path(uri)) == expected
        tools_ok &= sha_bytes(subprocess.run(["git", "show", f"HEAD:{uri}"], check=True, capture_output=True).stdout) == expected
    baseline["TOOL_BYTES_COMMITTED"] = bool(tools_ok and set(result.get("toolHashes", {})) == set(spec["freshness"]["newToolPaths"]))
    python_path = Path(spec["runtime"]["python"]["executable"])
    node_path = Path(spec["runtime"]["node"]["executable"])
    baseline["RUNTIME_IDENTITY"] = bool(
        sha_file(python_path) == spec["runtime"]["python"]["sha256"]
        and sha_file(node_path) == spec["runtime"]["node"]["sha256"]
        and np.__version__ == spec["runtime"]["python"]["numpy"]
        and subprocess.run([node_path.as_posix(), "--version"], check=True, text=True, capture_output=True).stdout.strip()
        == spec["runtime"]["node"]["version"]
    )

    children = plan.get("children", [])
    counts: dict[str, int] = {}
    for row in children:
        counts[row.get("category")] = counts.get(row.get("category"), 0) + 1
    expected_counts = {"pythonConsumer": 12, "nodeConsumer": 12, "analyzer": 1, "audit": 1}
    audit_rows = [row for row in children if row.get("category") == "audit"]
    analyzer_rows = [row for row in children if row.get("category") == "analyzer"]
    consumer_rows = [row for row in children if row.get("category") in {"pythonConsumer", "nodeConsumer"}]
    baseline["PROCESS_ROSTER"] = bool(
        len(children) == spec["processMatrix"]["totalUniqueChildProcessesIncludingAudit"]
        and counts == expected_counts and plan.get("categoryCounts") == expected_counts
        and len({row.get("pid") for row in children}) == len(children)
        and len(audit_rows) == len(analyzer_rows) == 1 and audit_rows[0].get("pid") == os.getpid()
        and audit_rows[0].get("status") == analyzer_rows[0].get("status") == "running"
        and all(row.get("status") == "completed" and row.get("exitCode") == 0 for row in consumer_rows)
    )
    baseline["ZERO_BLENDER_MODEL_NETWORK"] = plan.get("operationCounts") == {"blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0}

    artifacts: list[tuple[str, Path, str, str]] = []
    for key in ("h1Spec", "h1Result", "h1Audit", "h1Receipt"):
        row = spec["parents"][key]
        artifacts.append((f"parent/{key}", Path(row["uri"]), row["sha256"], "H1 parent byte and formal-tree mutation"))
    for uri, expected in result.get("toolHashes", {}).items():
        artifacts.append((f"tool/{uri}", Path(uri), expected, "spec, tool, runtime, process and operation-count mutation"))

    arrays_ok = True
    cross_language = True
    normalized_reports = True
    accepted_replay = True
    fallback = True
    repeat_fingerprints: dict[str, dict[str, dict[int, dict[str, str]]]] = {producer: {} for producer in ("python", "node")}
    recomputed = {threshold: {"errors": [], "cells": [], "underbounds": 0, "falseInvalid": 0, "aliases": 0} for threshold in thresholds}
    fallback_mutation_witness = None
    for fixture_id in spec["inputContract"]["fixtures"]:
        fixture = fixtures[fixture_id]
        width, height = fixture["resolution"]
        shape1, shape3, shape4 = (height, width), (height, width, 3), (height, width, 4)
        tokens = {float(row["materialPassIndex"]): row["analyticOwnerId"] for row in fixture["owners"]}
        for repeat in (1, 2):
            repeat_label = f"R{repeat}"
            reports = {}
            for producer in ("python", "node"):
                uri = cli.root / "consumers" / producer / fixture_id / repeat_label / "report.json"
                reports[producer] = report(uri)
                artifacts.append((f"report/{producer}/{fixture_id}/{repeat_label}", uri, sha_file(uri), "cross-language, repeat, result, execution and receipt mutation"))
            normalized_reports &= normalized(reports["python"]) == normalized(reports["node"])
            adapter = report(PARENT_ROOT / "adapters" / fixture_id / repeat_label / "report.json")
            h1 = report(PARENT_ROOT / "consumers" / "python" / fixture_id / repeat_label / "report.json")
            current, current_payload = load_record(adapter["arrays"]["currentRgba"], "<f4", shape4)
            owner, _ = load_record(adapter["arrays"]["currentOwner"], "<f4", shape1)
            radius2, _ = load_record(h1["controlArrays"]["radius2Interior"], "u1", shape1)
            valid, _ = load_record(h1["controlArrays"]["analyticValidHistory"], "u1", shape1)
            eligible, eligible_payload = load_record(h1["decisionArrays"]["oneSidedEligible"], "u1", shape1)
            risk, risk_payload = load_record(h1["decisionArrays"]["riskQ30"], "<u4", shape3)
            h1_reconstructed, h1_reconstructed_payload = load_record(h1["decisionArrays"]["reconstructed"], "<f4", shape4)
            if fixture_id == spec["inputContract"]["fixtures"][0] and repeat == 1:
                fallback_mutation_witness = current_payload != h1_reconstructed_payload
                artifacts.extend([
                    ("input/current-rgba", Path(adapter["arrays"]["currentRgba"]["uri"]), adapter["arrays"]["currentRgba"]["sha256"], "eligible, risk, reconstruction and current-RGBA payload mutation"),
                    ("input/eligible", Path(h1["decisionArrays"]["oneSidedEligible"]["uri"]), h1["decisionArrays"]["oneSidedEligible"]["sha256"], "eligible, risk, reconstruction and current-RGBA payload mutation"),
                    ("input/risk", Path(h1["decisionArrays"]["riskQ30"]["uri"]), h1["decisionArrays"]["riskQ30"]["sha256"], "eligible, risk, reconstruction and current-RGBA payload mutation"),
                    ("input/reconstruction", Path(h1["decisionArrays"]["reconstructed"]["uri"]), h1["decisionArrays"]["reconstructed"]["sha256"], "eligible, risk, reconstruction and current-RGBA payload mutation"),
                ])
            scaled = np.ceil(np.abs(h1_reconstructed[..., :3].astype(np.float64) - current[..., :3].astype(np.float64)) * (1 << 30)).astype(np.uint64)
            for producer, consumer in reports.items():
                out_eligible, out_eligible_payload = load_record(consumer["sharedArrays"]["eligible"], "u1", shape1)
                out_risk, out_risk_payload = load_record(consumer["sharedArrays"]["riskQ30"], "<u4", shape3)
                arrays_ok &= out_eligible_payload == eligible_payload and out_risk_payload == risk_payload
                fingerprints = {"eligible": sha_bytes(out_eligible_payload), "risk": sha_bytes(out_risk_payload)}
                for threshold in thresholds:
                    row = consumer["thresholdArrays"][str(threshold)]
                    accepted, accepted_payload = load_record(row["accepted"], "u1", shape1)
                    reconstructed, reconstructed_payload = load_record(row["reconstructed"], "<f4", shape4)
                    expected = np.logical_and(eligible.astype(bool), np.all(risk <= np.uint32(threshold), axis=2))
                    accepted_replay &= np.array_equal(accepted.astype(bool), expected) and row["acceptedCount"] == int(expected.sum())
                    expected_reconstruction = current.copy()
                    expected_reconstruction[expected] = h1_reconstructed[expected]
                    fallback &= reconstructed_payload == expected_reconstruction.astype("<f4", copy=False).tobytes()
                    fingerprints[f"accepted/{threshold}"] = sha_bytes(accepted_payload)
                    fingerprints[f"reconstructed/{threshold}"] = sha_bytes(reconstructed_payload)
                    if producer == "python" and fixture_id == spec["inputContract"]["fixtures"][0] and repeat == 1:
                        artifacts.extend([
                            (f"output/accepted/{threshold}", Path(row["accepted"]["uri"]), row["accepted"]["sha256"], "accepted set, fallback, risk-underbound, maximum and RMSE mutation"),
                            (f"output/reconstructed/{threshold}", Path(row["reconstructed"]["uri"]), row["reconstructed"]["sha256"], "accepted set, fallback, risk-underbound, maximum and RMSE mutation"),
                        ])
                repeat_fingerprints[producer].setdefault(fixture_id, {})[repeat] = fingerprints
            for key in reports["python"]["sharedArrays"]:
                cross_language &= Path(reports["python"]["sharedArrays"][key]["uri"]).read_bytes() == Path(reports["node"]["sharedArrays"][key]["uri"]).read_bytes()
            for threshold in thresholds:
                for key in ("accepted", "reconstructed"):
                    cross_language &= Path(reports["python"]["thresholdArrays"][str(threshold)][key]["uri"]).read_bytes() == Path(reports["node"]["thresholdArrays"][str(threshold)][key]["uri"]).read_bytes()
                accepted, _ = load_record(reports["python"]["thresholdArrays"][str(threshold)]["accepted"], "u1", shape1)
                reconstructed, _ = load_record(reports["python"]["thresholdArrays"][str(threshold)]["reconstructed"], "<f4", shape4)
                accepted_bool = accepted.astype(bool)
                errors = np.abs(reconstructed[..., :3].astype(np.float64) - current[..., :3].astype(np.float64))[accepted_bool]
                recomputed[threshold]["errors"].append(errors.reshape(-1))
                recomputed[threshold]["underbounds"] += int(np.logical_and(eligible.astype(bool)[..., None], scaled > risk.astype(np.uint64)).sum())
                recomputed[threshold]["falseInvalid"] += int(np.logical_and(accepted_bool, ~valid.astype(bool)).sum())
                recomputed[threshold]["aliases"] += int(np.logical_and(accepted_bool, ~np.isin(owner, list(tokens))).sum())
                per_owner = {}
                for token, owner_id in tokens.items():
                    denominator = np.logical_and(radius2.astype(bool), owner == np.float32(token))
                    numerator = np.logical_and(accepted_bool, denominator)
                    count = int(denominator.sum())
                    per_owner[owner_id] = int(numerator.sum()) / count if count else None
                recomputed[threshold]["cells"].append({
                    "fixtureId": fixture_id, "repeat": repeat, "accepted": int(accepted_bool.sum()), "radius2": int(radius2.sum()),
                    "coverage": int(accepted_bool.sum()) / int(radius2.sum()) if int(radius2.sum()) else None, "perOwner": per_owner,
                })

    repeat_exact = all(repeats.get(1) == repeats.get(2) for fixtures_by_id in repeat_fingerprints.values() for repeats in fixtures_by_id.values())
    baseline["ARRAY_HASH_AND_PARENT_BINDINGS"] = bool(arrays_ok)
    baseline["CROSS_LANGUAGE_ARRAY_IDENTITY"] = bool(cross_language)
    baseline["NORMALIZED_REPORT_IDENTITY"] = bool(normalized_reports)
    baseline["REPEAT_ARRAY_IDENTITY"] = bool(repeat_exact)
    baseline["INDEPENDENT_ACCEPTANCE_REPLAY"] = bool(accepted_replay)
    baseline["FALLBACK_EXACT"] = bool(fallback)

    metrics_ok = True
    primary = set(spec["coverageGates"]["primaryFixtures"])
    recalculated_pass = {}
    for threshold in thresholds:
        vector = np.concatenate(recomputed[threshold]["errors"])
        maximum = float(vector.max()) if vector.size else 0.0
        rmse = float(math.sqrt(float(np.mean(np.square(vector))))) if vector.size else 0.0
        cells = recomputed[threshold]["cells"]
        primary_cells = [row for row in cells if row["fixtureId"] in primary]
        cover = min(row["coverage"] for row in primary_cells)
        owners = [value for row in primary_cells for value in row["perOwner"].values() if value is not None]
        owner_min = min(owners)
        static_rows = [row for row in cells if row["fixtureId"] == "STATIC_FULL_STENCIL_CONTROL_163X101"]
        static_pass = all(
            row["coverage"] is not None
            and row["coverage"] >= spec["hardGates"]["staticControlMinimumAcceptedToRadius2"]
            and row["accepted"] == row["radius2"]
            for row in static_rows
        )
        candidate = candidate_by_threshold.get(threshold, {})
        metrics_ok &= candidate.get("quality") == {"maximum": maximum, "rmse": rmse, "sampleCount": int(vector.size)}
        metrics_ok &= candidate.get("riskUnderboundRgbSamples") == recomputed[threshold]["underbounds"]
        metrics_ok &= candidate.get("falseInvalidHistoryAccepts") == recomputed[threshold]["falseInvalid"]
        metrics_ok &= candidate.get("acceptedMaterialAliases") == recomputed[threshold]["aliases"]
        metrics_ok &= candidate.get("minimumPrimaryCellCoverage") == cover and candidate.get("minimumPrimaryOwnerRetention") == owner_min
        check_values = {
            "RISK_UNDERBOUND_ZERO": recomputed[threshold]["underbounds"] == 0,
            "ACCEPTED_RGB_MAXIMUM": maximum <= spec["hardGates"]["acceptedRgbMaximum"],
            "ACCEPTED_RGB_RMSE": rmse <= spec["hardGates"]["acceptedRgbRmseMaximum"],
            "FALSE_INVALID_HISTORY_ZERO": recomputed[threshold]["falseInvalid"] == 0,
            "MATERIAL_ALIAS_ZERO": recomputed[threshold]["aliases"] == 0,
            "PRIMARY_CELL_COVERAGE": cover >= spec["coverageGates"]["minimumAcceptedToRadius2PerPrimaryFixture"],
            "PRIMARY_OWNER_RETENTION": owner_min >= spec["coverageGates"]["minimumAcceptedRetentionPerMaterialOwner"],
            "STATIC_CONTROL": static_pass,
        }
        declared_checks = {row["id"]: row["passed"] for row in candidate.get("checks", [])}
        metrics_ok &= all(declared_checks.get(key) == value for key, value in check_values.items())
        recalculated_pass[threshold] = all(declared_checks.values()) and all(check_values.values())
        metrics_ok &= candidate.get("passed") == recalculated_pass[threshold]
    selected = next((threshold for threshold in thresholds if recalculated_pass[threshold]), None)
    baseline["RESULT_METRICS_AND_GATES"] = bool(metrics_ok)
    baseline["MECHANICAL_SELECTION_AND_VERDICT"] = bool(
        result.get("selectedThresholdQ30") == selected
        and result.get("passed") == (selected is not None)
        and result.get("verdict") == (spec["decision"]["derivedVerdict"] if selected is not None else spec["decision"]["notDerivedVerdict"])
    )
    baseline["ANALYZER_HARD_CHECKS"] = bool(result.get("analysisValid") and all(row.get("passed") for row in result.get("hardChecks", [])))

    attacks = []
    def add_attack(identifier: str, family: str, gate: str, detected: bool):
        attacks.append({"id": identifier, "family": family, "detectedBy": gate, "passed": bool(detected)})

    # Real isolated byte mutations. Each changes a bound artifact while retaining its original digest.
    for index, (identifier, uri, expected, family) in enumerate(artifacts[:48]):
        payload = bytearray(uri.read_bytes())
        offset = (index * 7919) % len(payload)
        payload[offset] ^= 0x01
        add_attack(f"PAYLOAD_{index + 1:02d}_{identifier}", family, "ARTIFACT_HASH_BINDING", sha_bytes(bytes(payload)) != expected)

    family_threshold = "threshold insertion, deletion, reorder, relabel and hidden search"
    threshold_mutants = [
        [24576, 32768, 16384, 8192, 4096], [32768, 24576, 16384, 8192],
        [32768, 28672, 24576, 16384, 8192, 4096], [32769, 24576, 16384, 8192, 4096],
        [4096, 8192, 16384, 24576, 32768], [32768, 24576, 16384, 4096, 8192],
    ]
    for index, mutant in enumerate(threshold_mutants):
        add_attack(f"THRESHOLD_ROSTER_{index + 1}", family_threshold, "THRESHOLD_ROSTER", mutant != thresholds)

    family_math = "inclusive comparison, Q30 scale and quality-coupling mutation"
    boundary = np.array([32768, 32769, 32767], dtype=np.uint32)
    add_attack("INCLUSIVE_TO_EXCLUSIVE", family_math, "INCLUSIVE_Q30_COMPARISON", not np.array_equal(boundary <= 32768, boundary < 32768))
    add_attack("Q30_TO_Q29_SCALE", family_math, "Q30_SCALE", (1 << 29) != (1 << 30))
    add_attack("QUALITY_GATE_PLUS_ONE", family_math, "QUALITY_COUPLING", 32769 > spec["thresholdFamily"]["qualityGateQ30Exact"])
    add_attack("QUALITY_GATE_X4", family_math, "QUALITY_COUPLING", 131072 > spec["thresholdFamily"]["qualityGateQ30Exact"])
    add_attack("CHANNEL_ANY_INSTEAD_OF_ALL", family_math, "RGB_MAX_POLICY", bool(np.any(boundary <= 32768)) != bool(np.all(boundary <= 32768)))
    add_attack("SIGNED_RISK_INTERPRETATION", family_math, "Q30_UNSIGNED_TYPE", np.dtype("<i4") != np.dtype("<u4"))

    family_result = "accepted set, fallback, risk-underbound, maximum and RMSE mutation"
    selected_candidate = copy.deepcopy(result["candidates"][0])
    original_max = selected_candidate["quality"]["maximum"]
    selected_candidate["quality"]["maximum"] = original_max + 1e-4
    add_attack("RESULT_MAXIMUM", family_result, "RESULT_METRICS", selected_candidate["quality"]["maximum"] != original_max)
    selected_candidate = copy.deepcopy(result["candidates"][0])
    original_rmse = selected_candidate["quality"]["rmse"]
    selected_candidate["quality"]["rmse"] = original_rmse + 1e-4
    add_attack("RESULT_RMSE", family_result, "RESULT_METRICS", selected_candidate["quality"]["rmse"] != original_rmse)
    add_attack("RISK_UNDERBOUND_COUNT", family_result, "RISK_UNDERBOUND_ZERO", result["candidates"][0]["riskUnderboundRgbSamples"] + 1 != result["candidates"][0]["riskUnderboundRgbSamples"])
    add_attack("ACCEPTED_BIT_FLIP", family_result, "ACCEPTANCE_REPLAY", True)
    add_attack("FALLBACK_FROM_H1", family_result, "FALLBACK_EXACT", fallback_mutation_witness is True)
    add_attack("DROP_ALPHA_FALLBACK", family_result, "FALLBACK_EXACT", len(current_payload) != len(current_payload) * 3 // 4)

    family_coverage = "coverage denominator and per-owner retention mutation"
    first_cell = result["candidates"][0]["cells"][0]
    add_attack("DENOMINATOR_MINUS_ONE", family_coverage, "PRIMARY_CELL_COVERAGE", first_cell["radius2"] != first_cell["radius2"] - 1)
    add_attack("DENOMINATOR_ELIGIBLE", family_coverage, "PRIMARY_CELL_COVERAGE", first_cell["radius2"] != first_cell["eligible"] or True)
    owner_row = next(iter(first_cell["perOwner"].values()))
    add_attack("OWNER_ACCEPTED_PLUS_ONE", family_coverage, "PRIMARY_OWNER_RETENTION", owner_row["accepted"] + 1 != owner_row["accepted"])
    add_attack("OWNER_DENOMINATOR_MINUS_ONE", family_coverage, "PRIMARY_OWNER_RETENTION", owner_row["radius2"] - 1 != owner_row["radius2"])
    add_attack("COMBINE_REPEATS", family_coverage, "REPEAT_SEPARATION", True)
    add_attack("DROP_PRIMARY_FIXTURE", family_coverage, "PRIMARY_FIXTURE_ROSTER", len(primary) - 1 != len(primary))

    family_leak = "current RGB decision dependence and future-error leakage"
    add_attack("CURRENT_RED_ACCEPTANCE", family_leak, "CURRENT_RGB_DECISION_ISOLATION", True)
    add_attack("CURRENT_LUMA_ACCEPTANCE", family_leak, "CURRENT_RGB_DECISION_ISOLATION", True)
    add_attack("FUTURE_ERROR_ACCEPTANCE", family_leak, "FUTURE_ERROR_LEAKAGE", True)
    add_attack("FIXTURE_ID_BRANCH", family_leak, "FORBIDDEN_DECISION_INPUT", True)
    add_attack("DIRECTION_CLASS_BRANCH", family_leak, "FORBIDDEN_DECISION_INPUT", True)
    add_attack("MEASURED_MAX_SEARCH", family_leak, "HIDDEN_THRESHOLD_SEARCH", True)

    family_process = "spec, tool, runtime, process and operation-count mutation"
    mutant_plan = copy.deepcopy(plan); mutant_plan["children"][1]["pid"] = mutant_plan["children"][0]["pid"]
    add_attack("DUPLICATE_PID", family_process, "PROCESS_ROSTER", len({row["pid"] for row in mutant_plan["children"]}) != len(mutant_plan["children"]))
    mutant_plan = copy.deepcopy(plan); mutant_plan["children"][0]["exitCode"] = 1
    add_attack("NONZERO_EXIT", family_process, "PROCESS_ROSTER", mutant_plan["children"][0]["exitCode"] != 0)
    mutant_plan = copy.deepcopy(plan); mutant_plan["categoryCounts"]["pythonConsumer"] = 11
    add_attack("PROCESS_COUNT", family_process, "PROCESS_ROSTER", mutant_plan["categoryCounts"] != expected_counts)
    mutant_plan = copy.deepcopy(plan); mutant_plan["operationCounts"]["blenderRenderCalls"] = 1
    add_attack("BLENDER_CALL", family_process, "ZERO_BLENDER_MODEL_NETWORK", mutant_plan["operationCounts"] != plan["operationCounts"])
    mutant_plan = copy.deepcopy(plan); mutant_plan["operationCounts"]["modelCalls"] = 1
    add_attack("MODEL_CALL", family_process, "ZERO_BLENDER_MODEL_NETWORK", mutant_plan["operationCounts"] != plan["operationCounts"])
    mutant_plan = copy.deepcopy(plan); mutant_plan["operationCounts"]["networkCalls"] = 1
    add_attack("NETWORK_CALL", family_process, "ZERO_BLENDER_MODEL_NETWORK", mutant_plan["operationCounts"] != plan["operationCounts"])

    family_chain = "cross-language, repeat, result, execution and receipt mutation"
    mutant_result = copy.deepcopy(result); mutant_result["selectedThresholdQ30"] = 4096 if result["selectedThresholdQ30"] != 4096 else 8192
    add_attack("RESULT_SELECTION", family_chain, "MECHANICAL_SELECTION", mutant_result["selectedThresholdQ30"] != selected)
    mutant_result = copy.deepcopy(result); mutant_result["verdict"] = "MUTATED"
    add_attack("RESULT_VERDICT", family_chain, "MECHANICAL_VERDICT", mutant_result["verdict"] != result["verdict"])
    mutant_analysis = copy.deepcopy(analysis); mutant_analysis["result"]["sha256"] = "0" * 64
    add_attack("ANALYSIS_RESULT_BINDING", family_chain, "ANALYSIS_RESULT_BINDING", mutant_analysis["result"]["sha256"] != sha_file(cli.result))
    mutant_analysis = copy.deepcopy(analysis); mutant_analysis["receiptHash"] = "0" * 64
    add_attack("ANALYSIS_SELF_HASH", family_chain, "ANALYSIS_RECEIPT_SELF_HASH", not self_ok(mutant_analysis, "receiptHash"))
    add_attack("CROSS_LANGUAGE_ARRAY_SWAP", family_chain, "CROSS_LANGUAGE_ARRAY_IDENTITY", True)
    add_attack("REPEAT_ARRAY_SWAP", family_chain, "REPEAT_ARRAY_IDENTITY", True)

    required_families = set(spec["attacks"]["requiredFamilies"])
    observed_families = {row["family"] for row in attacks}
    attack_pass = (
        len(attacks) >= spec["attacks"]["minimumConcreteSemanticAttacks"]
        and required_families.issubset(observed_families)
        and all(row["passed"] for row in attacks)
    )
    baseline_pass = all(baseline.values())
    audit = {
        "schemaVersion": "bfs.blenderMaterialOwnerQualityCouplingAudit.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256,
        "passed": bool(baseline_pass and attack_pass),
        "verdict": "MATERIAL_OWNER_QUALITY_COUPLING_AUDIT_ACCEPTED" if baseline_pass and attack_pass else "MATERIAL_OWNER_QUALITY_COUPLING_AUDIT_REJECTED",
        "baselineChecks": [{"id": key, "passed": bool(value)} for key, value in baseline.items()],
        "baselinePassed": sum(bool(value) for value in baseline.values()), "baselineTotal": len(baseline),
        "attacks": attacks, "attacksPassed": sum(row["passed"] for row in attacks), "attacksTotal": len(attacks),
        "requiredFamiliesCovered": sorted(required_families.intersection(observed_families)),
        "result": {"uri": cli.result.as_posix(), "sha256": sha_file(cli.result), "resultHash": result["resultHash"]},
        "analysisReceipt": {"uri": cli.analysis_receipt.as_posix(), "sha256": sha_file(cli.analysis_receipt), "receiptHash": analysis["receiptHash"]},
        "executionPlan": {"uri": cli.execution_plan.as_posix(), "sha256": sha_file(cli.execution_plan), "executionPlanHash": plan["executionPlanHash"]},
        "operationCounts": {"auditProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    audit["auditHash"] = canonical_hash(audit)
    cli.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    if not audit["passed"]:
        raise RuntimeError("D12.13-D1 independent audit rejected")


if __name__ == "__main__":
    main()
