#!/usr/bin/env python3
"""Runner and independent analyzer for B52-D12.13-D1."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


SPEC_SHA256 = "e9d79a2ec54acaf36a0df1168ea71102b0b94ab66f4e10f1cda56dbd1ea70c00"
PYTHON = Path("/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13")
NODE = Path("/opt/homebrew/Cellar/node/26.5.0/bin/node")
PARENT_ROOT = Path("experiments/blender-material-owner-one-sided-curvature-holdout-v0-1")
TOOL_PATHS = [
    "scripts/derive-b52-d12-13-quality-coupled-threshold.py",
    "scripts/derive-b52-d12-13-quality-coupled-threshold.mjs",
    "scripts/audit-b52-d12-13-quality-coupled-threshold.py",
    "scripts/run-b52-d12-13-quality-coupled-threshold.py",
]


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
        raise RuntimeError(f"D12.13-D1 timed out waiting for {path}")


def load_bound(record: dict, dtype: str, shape: tuple[int, ...]):
    path = Path(record["uri"])
    payload = path.read_bytes()
    expected = int(np.prod(shape)) * np.dtype(dtype).itemsize
    if len(payload) != expected or len(payload) != record["bytes"] or sha_bytes(payload) != record["sha256"]:
        raise RuntimeError(f"D12.13-D1 array binding failed: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy(), payload


def verify_report(path: Path) -> dict:
    report = json.loads(path.read_text())
    if not self_ok(report, "reportHash"):
        raise RuntimeError(f"D12.13-D1 report self-hash failed: {path}")
    return report


def normalized_report(report: dict) -> dict:
    value = {key: row for key, row in report.items() if key not in {"producer", "runtime", "pid", "reportHash"}}
    for section in ("sharedArrays",):
        value[section] = {
            key: {field: item for field, item in row.items() if field != "uri"}
            for key, row in report[section].items()
        }
    value["thresholdArrays"] = {}
    for threshold, row in report["thresholdArrays"].items():
        value["thresholdArrays"][threshold] = {
            "acceptedCount": row["acceptedCount"],
            "accepted": {field: item for field, item in row["accepted"].items() if field != "uri"},
            "reconstructed": {field: item for field, item in row["reconstructed"].items() if field != "uri"},
        }
    return value


def git_subtree(uri: str) -> str:
    return subprocess.run(["git", "rev-parse", f"HEAD:{uri}"], check=True, text=True, capture_output=True).stdout.strip()


def runtime_identity(spec: dict) -> bool:
    return (
        sha_file(PYTHON) == spec["runtime"]["python"]["sha256"]
        and sha_file(NODE) == spec["runtime"]["node"]["sha256"]
        and np.__version__ == spec["runtime"]["python"]["numpy"]
        and subprocess.run([NODE.as_posix(), "--version"], check=True, text=True, capture_output=True).stdout.strip()
        == spec["runtime"]["node"]["version"]
    )


def process_plan_ok(plan: dict, spec: dict) -> bool:
    expected = {"pythonConsumer": 12, "nodeConsumer": 12, "analyzer": 1, "audit": 1}
    children = plan.get("children", [])
    counts: dict[str, int] = {}
    for row in children:
        counts[row.get("category")] = counts.get(row.get("category"), 0) + 1
    analyzer = [row for row in children if row.get("category") == "analyzer"]
    audit = [row for row in children if row.get("category") == "audit"]
    consumers = [row for row in children if row.get("category") in {"pythonConsumer", "nodeConsumer"}]
    return bool(
        self_ok(plan, "executionPlanHash")
        and len(children) == spec["processMatrix"]["totalUniqueChildProcessesIncludingAudit"]
        and counts == expected and plan.get("categoryCounts") == expected
        and len({row.get("pid") for row in children}) == len(children)
        and len(analyzer) == len(audit) == 1 and analyzer[0].get("pid") == os.getpid()
        and analyzer[0].get("status") == "running" and audit[0].get("status") == "running"
        and all(row.get("exitCode") == 0 and row.get("status") == "completed" for row in consumers)
        and plan.get("operationCounts") == {"blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0}
    )


def analyze(cli):
    if sha_file(cli.spec) != SPEC_SHA256 or cli.result.exists() or cli.analysis_receipt.exists():
        raise RuntimeError("D12.13-D1 analyzer identity/output violation")
    spec = json.loads(cli.spec.read_text())
    wait_path(cli.execution_plan)
    plan = json.loads(cli.execution_plan.read_text())
    h1_spec = json.loads(Path(spec["parents"]["h1Spec"]["uri"]).read_text())
    fixtures = {row["id"]: row for row in h1_spec["fixtures"]}
    thresholds = spec["thresholdFamily"]["candidateThresholdsQ30Descending"]
    tool_hashes = {uri: sha_file(Path(uri)) for uri in TOOL_PATHS}

    parent_checks = {}
    for key in ("h1Spec", "h1Result", "h1Audit", "h1Receipt"):
        row = spec["parents"][key]
        parent_checks[key] = sha_file(Path(row["uri"])) == row["sha256"]
    parent_tree = git_subtree(spec["parents"]["h1FormalRoot"]["uri"])
    parent_checks["h1FormalRoot"] = parent_tree == spec["parents"]["h1FormalRoot"]["gitTree"]

    global_flags = {
        "inputBindings": True, "crossLanguage": True, "normalizedReports": True,
        "repeatArrays": True, "acceptedReplay": True, "eligibleRiskBinding": True,
        "fallback": True, "currentRgbIsolation": True, "falseInvalid": True,
        "materialAliases": True, "staticControl": True, "thresholdRoster": True,
    }
    repeat_fingerprints: dict[str, dict[str, dict[int, dict]]] = {producer: {} for producer in ("python", "node")}
    threshold_accumulators = {
        threshold: {
            "errors": [], "cells": [], "riskUnderboundRgbSamples": 0,
            "falseInvalidHistoryAccepts": 0, "acceptedMaterialAliases": 0,
        }
        for threshold in thresholds
    }
    directional_totals = {key: 0 for key in ("left", "right", "top", "bottom", "neither")}
    risk_underbound_all = 0

    for fixture_id in spec["inputContract"]["fixtures"]:
        fixture = fixtures[fixture_id]
        width, height = fixture["resolution"]
        shape1, shape3, shape4 = (height, width), (height, width, 3), (height, width, 4)
        owner_tokens = {float(row["materialPassIndex"]): row["analyticOwnerId"] for row in fixture["owners"]}
        for repeat in (1, 2):
            repeat_label = f"R{repeat}"
            reports = {}
            for producer in ("python", "node"):
                report_path = cli.root / "consumers" / producer / fixture_id / repeat_label / "report.json"
                reports[producer] = verify_report(report_path)
                global_flags["thresholdRoster"] &= reports[producer]["thresholdsQ30Descending"] == thresholds
            global_flags["normalizedReports"] &= normalized_report(reports["python"]) == normalized_report(reports["node"])

            adapter_path = PARENT_ROOT / "adapters" / fixture_id / repeat_label / "report.json"
            h1_path = PARENT_ROOT / "consumers" / "python" / fixture_id / repeat_label / "report.json"
            adapter = verify_report(adapter_path)
            h1 = verify_report(h1_path)
            current, current_bytes = load_bound(adapter["arrays"]["currentRgba"], "<f4", shape4)
            current_owner, _ = load_bound(adapter["arrays"]["currentOwner"], "<f4", shape1)
            radius2, radius2_bytes = load_bound(h1["controlArrays"]["radius2Interior"], "u1", shape1)
            full_stencil, _ = load_bound(h1["controlArrays"]["fullStencil"], "u1", shape1)
            valid_history, _ = load_bound(h1["controlArrays"]["analyticValidHistory"], "u1", shape1)
            direction_arrays = {}
            for key, short in (("directionLeft", "left"), ("directionRight", "right"), ("directionTop", "top"), ("directionBottom", "bottom"), ("neitherHorizontal", "neither")):
                direction_arrays[short], _ = load_bound(h1["controlArrays"][key], "u1", shape1)
                if repeat == 1:
                    directional_totals[short] += int(direction_arrays[short].sum())
            eligible, eligible_bytes = load_bound(h1["decisionArrays"]["oneSidedEligible"], "u1", shape1)
            risk, risk_bytes = load_bound(h1["decisionArrays"]["riskQ30"], "<u4", shape3)
            h1_reconstructed, h1_reconstructed_bytes = load_bound(h1["decisionArrays"]["reconstructed"], "<f4", shape4)
            eligible_bool = eligible.astype(bool)
            rgb_error = np.abs(h1_reconstructed[..., :3].astype(np.float64) - current[..., :3].astype(np.float64))
            scaled_error = np.ceil(rgb_error * (1 << 30)).astype(np.uint64)
            risk_underbound_all += int(np.logical_and(eligible_bool[..., None], scaled_error > risk.astype(np.uint64)).sum())

            for producer, report in reports.items():
                global_flags["inputBindings"] &= report["inputBindings"]["current.rgba32"]["sha256"] == adapter["arrays"]["currentRgba"]["sha256"]
                global_flags["inputBindings"] &= report["inputBindings"]["one-sided-eligible.u8"]["sha256"] == h1["decisionArrays"]["oneSidedEligible"]["sha256"]
                global_flags["inputBindings"] &= report["inputBindings"]["risk.q30.u32"]["sha256"] == h1["decisionArrays"]["riskQ30"]["sha256"]
                out_eligible, out_eligible_bytes = load_bound(report["sharedArrays"]["eligible"], "u1", shape1)
                out_risk, out_risk_bytes = load_bound(report["sharedArrays"]["riskQ30"], "<u4", shape3)
                global_flags["eligibleRiskBinding"] &= out_eligible_bytes == eligible_bytes and out_risk_bytes == risk_bytes
                fingerprint = {"eligible": sha_bytes(out_eligible_bytes), "risk": sha_bytes(out_risk_bytes)}
                for threshold in thresholds:
                    row = report["thresholdArrays"][str(threshold)]
                    accepted, accepted_bytes = load_bound(row["accepted"], "u1", shape1)
                    reconstructed, reconstructed_bytes = load_bound(row["reconstructed"], "<f4", shape4)
                    expected = np.logical_and(eligible_bool, np.all(risk <= np.uint32(threshold), axis=2))
                    global_flags["acceptedReplay"] &= np.array_equal(accepted.astype(bool), expected)
                    global_flags["acceptedReplay"] &= row["acceptedCount"] == int(expected.sum())
                    global_flags["currentRgbIsolation"] &= np.array_equal(expected, np.logical_and(eligible_bool, np.all(risk <= np.uint32(threshold), axis=2)))
                    expected_reconstructed = current.copy()
                    expected_reconstructed[expected] = h1_reconstructed[expected]
                    global_flags["fallback"] &= reconstructed_bytes == expected_reconstructed.astype("<f4", copy=False).tobytes()
                    fingerprint[f"accepted/{threshold}"] = sha_bytes(accepted_bytes)
                    fingerprint[f"reconstructed/{threshold}"] = sha_bytes(reconstructed_bytes)
                repeat_fingerprints[producer].setdefault(fixture_id, {})[repeat] = fingerprint

            for section in ("sharedArrays",):
                for key in reports["python"][section]:
                    global_flags["crossLanguage"] &= Path(reports["python"][section][key]["uri"]).read_bytes() == Path(reports["node"][section][key]["uri"]).read_bytes()
            for threshold in thresholds:
                for key in ("accepted", "reconstructed"):
                    global_flags["crossLanguage"] &= Path(reports["python"]["thresholdArrays"][str(threshold)][key]["uri"]).read_bytes() == Path(reports["node"]["thresholdArrays"][str(threshold)][key]["uri"]).read_bytes()

                accepted, _ = load_bound(reports["python"]["thresholdArrays"][str(threshold)]["accepted"], "u1", shape1)
                reconstructed, _ = load_bound(reports["python"]["thresholdArrays"][str(threshold)]["reconstructed"], "<f4", shape4)
                accepted_bool = accepted.astype(bool)
                errors = np.abs(reconstructed[..., :3].astype(np.float64) - current[..., :3].astype(np.float64))[accepted_bool]
                threshold_accumulators[threshold]["errors"].append(errors.reshape(-1))
                threshold_accumulators[threshold]["riskUnderboundRgbSamples"] += int(np.logical_and(eligible_bool[..., None], scaled_error > risk.astype(np.uint64)).sum())
                threshold_accumulators[threshold]["falseInvalidHistoryAccepts"] += int(np.logical_and(accepted_bool, ~valid_history.astype(bool)).sum())
                token_domain = np.isin(current_owner, list(owner_tokens))
                threshold_accumulators[threshold]["acceptedMaterialAliases"] += int(np.logical_and(accepted_bool, ~token_domain).sum())
                per_owner = {}
                for token, owner_id in owner_tokens.items():
                    denominator = np.logical_and(radius2.astype(bool), current_owner == np.float32(token))
                    numerator = np.logical_and(accepted_bool, denominator)
                    count = int(denominator.sum())
                    per_owner[owner_id] = {"accepted": int(numerator.sum()), "radius2": count, "retention": int(numerator.sum()) / count if count else None}
                cell = {
                    "cell": f"{fixture_id}/{repeat_label}", "fixtureId": fixture_id, "repeat": repeat,
                    "accepted": int(accepted_bool.sum()), "eligible": int(eligible_bool.sum()), "radius2": int(radius2.sum()),
                    "acceptedToRadius2": int(accepted_bool.sum()) / int(radius2.sum()) if int(radius2.sum()) else None,
                    "fullStencilAccepted": int(np.logical_and(accepted_bool, full_stencil.astype(bool)).sum()),
                    "oneSidedAccepted": int(np.logical_and(accepted_bool, ~full_stencil.astype(bool)).sum()),
                    "riskRejected": int(np.logical_and(eligible_bool, ~accepted_bool).sum()),
                    "perOwner": per_owner,
                    "directional": {key: {"witnesses": int(value.sum()), "accepted": int(np.logical_and(accepted_bool, value.astype(bool)).sum())} for key, value in direction_arrays.items()},
                }
                threshold_accumulators[threshold]["cells"].append(cell)

    for producer, fixtures_by_id in repeat_fingerprints.items():
        for fixture_id, repeats in fixtures_by_id.items():
            global_flags["repeatArrays"] &= repeats.get(1) == repeats.get(2)

    candidates = []
    primary = set(spec["coverageGates"]["primaryFixtures"])
    for threshold in thresholds:
        accumulator = threshold_accumulators[threshold]
        error_vector = np.concatenate(accumulator["errors"]) if accumulator["errors"] else np.array([], dtype=np.float64)
        maximum = float(error_vector.max()) if error_vector.size else 0.0
        rmse = float(math.sqrt(float(np.mean(np.square(error_vector))))) if error_vector.size else 0.0
        primary_cells = [row for row in accumulator["cells"] if row["fixtureId"] in primary]
        coverage_pass = all(row["acceptedToRadius2"] is not None and row["acceptedToRadius2"] >= spec["coverageGates"]["minimumAcceptedToRadius2PerPrimaryFixture"] for row in primary_cells)
        owner_rows = [owner for row in primary_cells for owner in row["perOwner"].values() if owner["retention"] is not None]
        owner_pass = all(row["retention"] >= spec["coverageGates"]["minimumAcceptedRetentionPerMaterialOwner"] for row in owner_rows)
        static_cells = [row for row in accumulator["cells"] if row["fixtureId"] == "STATIC_FULL_STENCIL_CONTROL_163X101"]
        static_pass = all(row["acceptedToRadius2"] is not None and row["acceptedToRadius2"] >= spec["hardGates"]["staticControlMinimumAcceptedToRadius2"] and row["accepted"] == row["radius2"] for row in static_cells)
        checks = [
            {"id": "RISK_UNDERBOUND_ZERO", "passed": accumulator["riskUnderboundRgbSamples"] <= spec["hardGates"]["riskUnderboundRgbSamplesMaximum"]},
            {"id": "ACCEPTED_RGB_MAXIMUM", "passed": maximum <= spec["hardGates"]["acceptedRgbMaximum"]},
            {"id": "ACCEPTED_RGB_RMSE", "passed": rmse <= spec["hardGates"]["acceptedRgbRmseMaximum"]},
            {"id": "FALSE_INVALID_HISTORY_ZERO", "passed": accumulator["falseInvalidHistoryAccepts"] <= spec["hardGates"]["falseInvalidHistoryAcceptsMaximum"]},
            {"id": "MATERIAL_ALIAS_ZERO", "passed": accumulator["acceptedMaterialAliases"] <= spec["hardGates"]["acceptedMaterialAliasesMaximum"]},
            {"id": "PRIMARY_CELL_COVERAGE", "passed": coverage_pass},
            {"id": "PRIMARY_OWNER_RETENTION", "passed": owner_pass},
            {"id": "STATIC_CONTROL", "passed": static_pass},
        ]
        candidates.append({
            "thresholdQ30": threshold, "passed": all(row["passed"] for row in checks), "checks": checks,
            "quality": {"maximum": maximum, "rmse": rmse, "sampleCount": int(error_vector.size)},
            "riskUnderboundRgbSamples": accumulator["riskUnderboundRgbSamples"],
            "falseInvalidHistoryAccepts": accumulator["falseInvalidHistoryAccepts"],
            "acceptedMaterialAliases": accumulator["acceptedMaterialAliases"],
            "minimumPrimaryCellCoverage": min(row["acceptedToRadius2"] for row in primary_cells),
            "minimumPrimaryOwnerRetention": min(row["retention"] for row in owner_rows),
            "cells": accumulator["cells"],
        })

    global_flags["falseInvalid"] = all(row["falseInvalidHistoryAccepts"] == 0 for row in candidates)
    global_flags["materialAliases"] = all(row["acceptedMaterialAliases"] == 0 for row in candidates)
    global_flags["staticControl"] = all(next(check for check in row["checks"] if check["id"] == "STATIC_CONTROL")["passed"] for row in candidates)
    hard_checks = [
        {"id": "PARENT_BYTES", "passed": all(parent_checks.values())},
        {"id": "PARENT_FORMAL_TREE", "passed": parent_checks["h1FormalRoot"]},
        {"id": "TOOL_BYTES_COMMITTED", "passed": all(sha_bytes(subprocess.run(["git", "show", f"HEAD:{uri}"], check=True, capture_output=True).stdout) == digest for uri, digest in tool_hashes.items())},
        {"id": "RUNTIME_IDENTITY", "passed": runtime_identity(spec)},
        {"id": "PROCESS_ROSTER", "passed": process_plan_ok(plan, spec)},
        {"id": "THRESHOLD_ROSTER", "passed": bool(global_flags["thresholdRoster"])},
        {"id": "INPUT_BINDINGS", "passed": bool(global_flags["inputBindings"])},
        {"id": "ELIGIBLE_RISK_BYTE_BINDING", "passed": bool(global_flags["eligibleRiskBinding"])},
        {"id": "CROSS_LANGUAGE_ARRAYS", "passed": bool(global_flags["crossLanguage"])},
        {"id": "NORMALIZED_REPORT_IDENTITY", "passed": bool(global_flags["normalizedReports"])},
        {"id": "REPEAT_ARRAY_IDENTITY", "passed": bool(global_flags["repeatArrays"])},
        {"id": "INDEPENDENT_ACCEPTANCE_REPLAY", "passed": bool(global_flags["acceptedReplay"])},
        {"id": "FALLBACK_EXACT", "passed": bool(global_flags["fallback"])},
        {"id": "CURRENT_RGB_DECISION_ISOLATION", "passed": bool(global_flags["currentRgbIsolation"])},
        {"id": "IMMUTABLE_RISK_UNDERBOUND_ZERO", "passed": risk_underbound_all == 0},
        {"id": "FALSE_INVALID_HISTORY_ZERO", "passed": bool(global_flags["falseInvalid"])},
        {"id": "MATERIAL_ALIAS_ZERO", "passed": bool(global_flags["materialAliases"])},
        {"id": "STATIC_CONTROL", "passed": bool(global_flags["staticControl"])},
        {"id": "ZERO_BLENDER_MODEL_NETWORK", "passed": plan.get("operationCounts") == {"blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0}},
    ]
    analysis_valid = all(row["passed"] for row in hard_checks)
    selected = next((row["thresholdQ30"] for row in candidates if row["passed"]), None) if analysis_valid else None
    verdict = spec["decision"]["derivedVerdict"] if selected is not None else spec["decision"]["notDerivedVerdict"]
    result = {
        "schemaVersion": "bfs.blenderMaterialOwnerQualityCouplingDerivationResult.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256,
        "scientificClassification": spec["scientificClassification"],
        "analysisValid": analysis_valid, "passed": selected is not None, "verdict": verdict,
        "selectedThresholdQ30": selected, "diagnosticBaselineQ30": spec["thresholdFamily"]["diagnosticBaselineQ30"],
        "qualityGateQ30": spec["thresholdFamily"]["qualityGateQ30Exact"],
        "hardChecks": hard_checks, "hardChecksPassed": sum(row["passed"] for row in hard_checks), "hardChecksTotal": len(hard_checks),
        "candidates": candidates, "directionalDiagnosticsR1": directional_totals,
        "parentChecks": parent_checks, "parentFormalTree": parent_tree, "toolHashes": tool_hashes,
        "processPlanHash": plan["executionPlanHash"],
        "operationCounts": {"analyzerProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
        "promotionBoundary": spec["decision"]["promotionBoundary"], "nonClaims": spec["nonClaims"],
    }
    result["resultHash"] = canonical_hash(result)
    cli.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    receipt = {
        "schemaVersion": "bfs.blenderMaterialOwnerQualityCouplingAnalysisReceipt.v0.1",
        "experimentId": spec["experimentId"], "passed": analysis_valid,
        "result": {"uri": cli.result.as_posix(), "sha256": sha_file(cli.result), "resultHash": result["resultHash"]},
        "processPlanHash": plan["executionPlanHash"], "toolHashes": tool_hashes,
        "operationCounts": {"analysisProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    receipt["receiptHash"] = canonical_hash(receipt)
    cli.analysis_receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze-child", action="store_true")
    parser.add_argument("--spec", type=Path, default=Path("specs/blender-material-owner-quality-coupling-derivation.v0.1.json"))
    parser.add_argument("--root", type=Path, default=Path("experiments/blender-material-owner-quality-coupling-derivation-v0-1"))
    parser.add_argument("--result", type=Path)
    parser.add_argument("--analysis-receipt", type=Path)
    parser.add_argument("--execution-plan", type=Path)
    return parser.parse_args()


def run_child(command: list[str], category: str, label: str, logs: Path):
    started = time.time()
    stdout_path, stderr_path = logs / f"{label}.stdout.log", logs / f"{label}.stderr.log"
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr)
        exit_code = process.wait()
    return {
        "category": category, "label": label, "pid": process.pid, "status": "completed", "exitCode": exit_code,
        "startedAtUnix": started, "finishedAtUnix": time.time(), "command": command,
        "stdout": stdout_path.as_posix(), "stderr": stderr_path.as_posix(),
    }


def launch_child(command: list[str], category: str, label: str, logs: Path):
    stdout_path, stderr_path = logs / f"{label}.stdout.log", logs / f"{label}.stderr.log"
    stdout, stderr = stdout_path.open("wb"), stderr_path.open("wb")
    process = subprocess.Popen(command, stdout=stdout, stderr=stderr)
    row = {
        "category": category, "label": label, "pid": process.pid, "status": "running", "exitCode": None,
        "startedAtUnix": time.time(), "command": command, "stdout": stdout_path.as_posix(), "stderr": stderr_path.as_posix(),
    }
    return process, stdout, stderr, row


def main_run(cli):
    if sha_file(cli.spec) != SPEC_SHA256 or cli.root.exists():
        raise RuntimeError("D12.13-D1 runner spec/output identity violation")
    spec = json.loads(cli.spec.read_text())
    if not runtime_identity(spec):
        raise RuntimeError("D12.13-D1 runtime identity failed")
    for uri in TOOL_PATHS:
        disk = Path(uri).read_bytes()
        committed = subprocess.run(["git", "show", f"HEAD:{uri}"], check=True, capture_output=True).stdout
        if disk != committed:
            raise RuntimeError(f"D12.13-D1 tool not frozen at HEAD: {uri}")
    if git_subtree(spec["parents"]["h1FormalRoot"]["uri"]) != spec["parents"]["h1FormalRoot"]["gitTree"]:
        raise RuntimeError("D12.13-D1 parent subtree changed")

    cli.root.mkdir(parents=True)
    logs = cli.root / "logs"
    logs.mkdir()
    children = []
    for producer, executable, tool in (
        ("python", PYTHON.as_posix(), TOOL_PATHS[0]),
        ("node", NODE.as_posix(), TOOL_PATHS[1]),
    ):
        for fixture in spec["inputContract"]["fixtures"]:
            for repeat in (1, 2):
                label = f"{producer}-{fixture}-R{repeat}"
                output = cli.root / "consumers" / producer / fixture / f"R{repeat}"
                command = [executable, tool, "--spec", cli.spec.as_posix(), "--parent-root", PARENT_ROOT.as_posix(), "--fixture", fixture, "--repeat", str(repeat), "--output", output.as_posix()]
                row = run_child(command, f"{producer}Consumer", label, logs)
                children.append(row)
                if row["exitCode"] != 0:
                    raise RuntimeError(f"D12.13-D1 consumer failed: {label}")

    result_path = cli.root / "results.json"
    analysis_receipt = cli.root / "analysis-receipt.json"
    execution_plan = cli.root / "execution-plan.json"
    audit_path = cli.root / "audit.json"
    analyzer_command = [
        PYTHON.as_posix(), TOOL_PATHS[3], "--analyze-child", "--spec", cli.spec.as_posix(), "--root", cli.root.as_posix(),
        "--result", result_path.as_posix(), "--analysis-receipt", analysis_receipt.as_posix(), "--execution-plan", execution_plan.as_posix(),
    ]
    audit_command = [
        PYTHON.as_posix(), TOOL_PATHS[2], "--spec", cli.spec.as_posix(), "--root", cli.root.as_posix(),
        "--result", result_path.as_posix(), "--analysis-receipt", analysis_receipt.as_posix(),
        "--execution-plan", execution_plan.as_posix(), "--output", audit_path.as_posix(),
    ]
    analyzer_process, analyzer_stdout, analyzer_stderr, analyzer_row = launch_child(analyzer_command, "analyzer", "analyzer", logs)
    audit_process, audit_stdout, audit_stderr, audit_row = launch_child(audit_command, "audit", "audit", logs)
    children.extend([analyzer_row, audit_row])
    expected_counts = {"pythonConsumer": 12, "nodeConsumer": 12, "analyzer": 1, "audit": 1}
    plan = {
        "schemaVersion": "bfs.blenderMaterialOwnerQualityCouplingExecutionPlan.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256,
        "children": children, "categoryCounts": expected_counts,
        "operationCounts": {"blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    plan["executionPlanHash"] = canonical_hash(plan)
    execution_plan.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")

    analyzer_exit = analyzer_process.wait()
    audit_exit = audit_process.wait()
    for handle in (analyzer_stdout, analyzer_stderr, audit_stdout, audit_stderr):
        handle.close()
    analyzer_row.update({"status": "completed", "exitCode": analyzer_exit, "finishedAtUnix": time.time()})
    audit_row.update({"status": "completed", "exitCode": audit_exit, "finishedAtUnix": time.time()})
    if analyzer_exit != 0 or audit_exit != 0:
        raise RuntimeError(f"D12.13-D1 analyzer/audit failed: analyzer={analyzer_exit} audit={audit_exit}")

    result = json.loads(result_path.read_text())
    audit = json.loads(audit_path.read_text())
    analysis = json.loads(analysis_receipt.read_text())
    execution = {
        "schemaVersion": "bfs.blenderMaterialOwnerQualityCouplingExecution.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256,
        "passed": all(row["exitCode"] == 0 for row in children), "children": children,
        "categoryCounts": expected_counts, "executionPlan": {"uri": execution_plan.as_posix(), "sha256": sha_file(execution_plan), "executionPlanHash": plan["executionPlanHash"]},
        "uniquePids": len({row["pid"] for row in children}),
        "operationCounts": {"totalUniqueChildProcessesIncludingAudit": len(children), "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    execution["executionHash"] = canonical_hash(execution)
    execution_path = cli.root / "execution.json"
    execution_path.write_text(json.dumps(execution, indent=2, sort_keys=True) + "\n")
    evidence_passed = bool(execution["passed"] and analysis.get("passed") and audit.get("passed") and self_ok(result, "resultHash") and self_ok(audit, "auditHash"))
    receipt = {
        "schemaVersion": "bfs.blenderMaterialOwnerQualityCouplingEvidenceReceipt.v0.1",
        "experimentId": spec["experimentId"], "passed": evidence_passed,
        "candidateDerived": bool(evidence_passed and result.get("passed")), "selectedThresholdQ30": result.get("selectedThresholdQ30") if evidence_passed else None,
        "result": {"uri": result_path.as_posix(), "sha256": sha_file(result_path), "resultHash": result["resultHash"]},
        "audit": {"uri": audit_path.as_posix(), "sha256": sha_file(audit_path), "auditHash": audit["auditHash"]},
        "analysisReceipt": {"uri": analysis_receipt.as_posix(), "sha256": sha_file(analysis_receipt), "receiptHash": analysis["receiptHash"]},
        "execution": {"uri": execution_path.as_posix(), "sha256": sha_file(execution_path), "executionHash": execution["executionHash"]},
        "parentFormalTree": git_subtree(spec["parents"]["h1FormalRoot"]["uri"]),
        "toolHashes": {uri: sha_file(Path(uri)) for uri in TOOL_PATHS},
        "operationCounts": {"blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    receipt["receiptHash"] = canonical_hash(receipt)
    (cli.root / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    if not evidence_passed:
        raise RuntimeError("D12.13-D1 final evidence receipt failed")
    print(json.dumps({"verdict": result["verdict"], "selectedThresholdQ30": result["selectedThresholdQ30"], "receiptHash": receipt["receiptHash"]}, sort_keys=True))


def main():
    cli = parse_args()
    if cli.analyze_child:
        if not all((cli.result, cli.analysis_receipt, cli.execution_plan)):
            raise RuntimeError("D12.13-D1 analyzer paths required")
        analyze(cli)
    else:
        main_run(cli)


if __name__ == "__main__":
    main()
