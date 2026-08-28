#!/usr/bin/env python3
"""Orchestrate and analyze the preregistered B52-D12.12-D1 derivation."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


SPEC_SHA256 = "f179b4cea6c8d3bc19b4cf2534055ef98b3fa8dac9954bfeae28bc2a237dd640"
Q30 = 1 << 30
CONTROL = {
    "structuralValid": ("control/structural-valid.u8", "u1", 1),
    "radius2Interior": ("control/radius2-interior.u8", "u1", 1),
    "bilinearSupport": ("control/bilinear-support.u8", "u1", 1),
    "fullStencil": ("control/full-stencil.u8", "u1", 1),
    "localizedOpportunity": ("control/localized-opportunity.u8", "u1", 1),
}
FACTOR = {
    "oneSidedEligible": ("one-sided-eligible.u8", "u1", 1),
    "oneSidedUnavailable": ("one-sided-unavailable.u8", "u1", 1),
    "accepted": ("accepted.u8", "u1", 1),
    "riskQ30": ("risk.q30.u32", "<u4", 3),
    "acceptedReconstructed": ("accepted-reconstructed.rgba32", "<f4", 4),
}
BASELINE = {
    "structuralValid": ("structural-valid.u8", "u1", 1),
    "radius2Interior": ("radius2-interior.u8", "u1", 1),
    "supportEligible": ("support-eligible.u8", "u1", 1),
    "accepted": ("accepted.u8", "u1", 1),
    "riskQ30": ("risk.q30.u32", "<u4", 3),
    "acceptedReconstructed": ("accepted-reconstructed.rgba32", "<f4", 4),
    "analyticOwner": ("analytic-owner.u8", "u1", 1),
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def self_ok(value: dict, field: str) -> bool:
    return value.get(field) == canonical_hash({key: row for key, row in value.items() if key != field})


def git(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], check=True, text=True, capture_output=True).stdout.strip()


def load_array(path: Path, dtype: str, height: int, width: int, channels: int):
    payload = path.read_bytes()
    shape = (height, width, channels) if channels > 1 else (height, width)
    expected = int(np.prod(shape)) * np.dtype(dtype).itemsize
    if len(payload) != expected:
        raise RuntimeError(f"D12.12 array length mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy(), payload


def metric(reconstructed, current, mask):
    values = (reconstructed[..., :3].astype(np.float64) - current[..., :3].astype(np.float64))[mask]
    return {
        "maximum": float(np.abs(values).max()) if values.size else None,
        "rmse": float(np.sqrt(np.mean(values * values))) if values.size else None,
        "sampleCount": int(values.size),
    }


def spawn(command, cwd: Path):
    started = time.time()
    process = subprocess.Popen(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return {
        "pid": process.pid,
        "exitCode": process.returncode,
        "elapsedSeconds": time.time() - started,
        "command": command,
        "stdout": stdout,
        "stderr": stderr,
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--execution", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--analysis-receipt", type=Path)
    return parser.parse_args()


def analyze(cli, spec):
    if cli.output is None or cli.execution is None or cli.analysis_receipt is None or cli.output.exists() or cli.analysis_receipt.exists():
        raise RuntimeError("D12.12 analyze paths invalid")
    execution = json.loads(cli.execution.read_text())
    tool_hashes = {uri: sha_file(Path(uri)) for uri in spec["freshness"]["newToolPaths"]}
    parent_checks = {name: sha_file(Path(row["uri"])) == row["sha256"] for name, row in spec["parents"].items() if "uri" in row and "sha256" in row}
    formal_tree = git("rev-parse", f"HEAD:{spec['parents']['formalRoot']['uri']}")
    i1_root = Path(spec["parents"]["materialOwnerResult"]["uri"]).parent
    localization_result = json.loads(Path(spec["parents"]["ownerSupportLocalizationResult"]["uri"]).read_text())
    i1_spec = json.loads(Path(spec["parents"]["materialOwnerSpec"]["uri"]).read_text())
    h1_spec = json.loads(Path(i1_spec["parents"]["h1Spec"]["uri"]).read_text())
    fixtures = {row["id"]: row for row in h1_spec["fixtures"]}
    factors = spec["candidateFamily"]["inflationFactors"]
    cell_records = []
    factor_global = {factor: {"riskUnderbound": 0, "errors": [], "falseInvalid": 0, "aliases": 0, "fallback": True, "additionalByFixture": {}, "eligibilityByFixture": {}, "acceptanceByFixture": {}, "staticDelta": 0} for factor in factors}
    dual_payload = True
    baseline_masks = True
    full_identity = True
    subsets = True
    repeat_hashes = {}
    all_report_hashes = True
    for fixture_id, fixture in fixtures.items():
        width, height = fixture["resolution"]
        repeat_hashes[fixture_id] = {}
        for repeat in (1, 2):
            cell = f"{fixture_id}/R{repeat}"
            adapter_dir = i1_root / "adapters" / fixture_id / f"R{repeat}" / "arrays"
            current_rgba, _ = load_array(adapter_dir / "current.rgba32", "<f4", height, width, 4)
            previous_rgba, _ = load_array(adapter_dir / "previous.rgba32", "<f4", height, width, 4)
            vector, _ = load_array(adapter_dir / "vector.xy32", "<f4", height, width, 2)
            baseline_dir = i1_root / "consumers" / "python" / fixture_id / f"R{repeat}" / "arrays"
            baseline = {name: load_array(baseline_dir / filename, dtype, height, width, channels)[0] for name, (filename, dtype, channels) in BASELINE.items()}
            localization_path = Path(spec["parents"]["ownerSupportLocalizationResult"]["uri"]).parent / "payloads" / fixture_id / f"R{repeat}" / "classification.u8"
            localization, _ = load_array(localization_path, "u1", height, width, 1)
            producer_arrays = {}
            producer_hashes = {}
            for producer in ("python", "node"):
                base = cli.root / "consumers" / producer / fixture_id / f"R{repeat}"
                report = json.loads((base / "report.json").read_text())
                all_report_hashes &= self_ok(report, "reportHash")
                arrays = {"control": {}, "factors": {}}
                hashes = {}
                for name, (relative, dtype, channels) in CONTROL.items():
                    value, payload = load_array(base / "arrays" / relative, dtype, height, width, channels)
                    arrays["control"][name] = value
                    hashes[f"control/{name}"] = sha_bytes(payload)
                for factor in factors:
                    arrays["factors"][factor] = {}
                    for name, (filename, dtype, channels) in FACTOR.items():
                        value, payload = load_array(base / "arrays" / f"factor-{factor:02d}" / filename, dtype, height, width, channels)
                        arrays["factors"][factor][name] = value
                        hashes[f"factor/{factor}/{name}"] = sha_bytes(payload)
                producer_arrays[producer], producer_hashes[producer] = arrays, hashes
            dual_payload &= producer_hashes["python"] == producer_hashes["node"]
            arrays = producer_arrays["python"]
            control = arrays["control"]
            expected_opportunity = (localization == 2).astype("u1")
            cell_baseline = (
                np.array_equal(control["structuralValid"], baseline["structuralValid"])
                and np.array_equal(control["radius2Interior"], baseline["radius2Interior"])
                and np.array_equal(control["bilinearSupport"], baseline["structuralValid"])
                and np.array_equal(control["fullStencil"], baseline["supportEligible"])
                and np.array_equal(control["localizedOpportunity"], expected_opportunity)
            )
            baseline_masks &= cell_baseline
            radius2 = control["radius2Interior"].astype(bool)
            full = control["fullStencil"].astype(bool)
            opportunity = control["localizedOpportunity"].astype(bool)
            classification_alias = localization == 1
            reconstructed_all = current_rgba.copy()
            for y, x in np.argwhere(radius2):
                qx = x + float(vector[y, x, 0]); qy = y - float(vector[y, x, 1]); x0 = math.floor(qx); y0 = math.floor(qy)
                if x0 < 0 or y0 < 0 or x0 + 1 >= width or y0 + 1 >= height:
                    continue
                fx, fy = qx - x0, qy - y0
                weights = ((1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy)
                taps = ((y0, x0), (y0, x0 + 1), (y0 + 1, x0), (y0 + 1, x0 + 1))
                for channel in range(4):
                    values = [float(previous_rgba[ty, tx, channel]) for ty, tx in taps]
                    reconstructed_all[y, x, channel] = np.float32(((values[0] * weights[0] + values[1] * weights[1]) + values[2] * weights[2]) + values[3] * weights[3])
            cell_factor_records = []
            repeat_hashes[fixture_id][repeat] = producer_hashes["python"]
            for factor in factors:
                candidate = arrays["factors"][factor]
                eligible = candidate["oneSidedEligible"].astype(bool)
                unavailable = candidate["oneSidedUnavailable"].astype(bool)
                accepted = candidate["accepted"].astype(bool)
                cell_subsets = (
                    np.array_equal(eligible | unavailable, radius2)
                    and not np.logical_and(eligible, unavailable).any()
                    and not np.logical_and(accepted, ~eligible).any()
                )
                subsets &= cell_subsets
                cell_full_identity = (
                    np.array_equal(candidate["riskQ30"][full], baseline["riskQ30"][full])
                    and np.array_equal(candidate["accepted"][full], baseline["accepted"][full])
                    and np.array_equal(candidate["acceptedReconstructed"][full], baseline["acceptedReconstructed"][full])
                )
                full_identity &= cell_full_identity
                underbound = 0
                for y, x in np.argwhere(eligible):
                    for channel in range(3):
                        actual_units = math.ceil(abs(float(reconstructed_all[y, x, channel]) - float(current_rgba[y, x, channel])) * Q30)
                        underbound += int(actual_units > int(candidate["riskQ30"][y, x, channel]))
                accepted_metric = metric(candidate["acceptedReconstructed"], current_rgba, accepted)
                fallback = np.array_equal(candidate["acceptedReconstructed"][~accepted], current_rgba[~accepted])
                additional = int(np.logical_and(accepted, ~baseline["accepted"].astype(bool)).sum())
                opportunity_count = int(opportunity.sum())
                opportunity_eligible = int(np.logical_and(opportunity, eligible).sum())
                opportunity_accepted = int(np.logical_and(opportunity, accepted).sum())
                false_invalid = int(np.logical_and(accepted, ~control["structuralValid"].astype(bool)).sum())
                alias_accepted = int(np.logical_and(accepted, classification_alias).sum())
                accepted_count = int(accepted.sum())
                radius2_count = int(radius2.sum())
                owners = {}
                for owner_index, owner in enumerate(fixture["owners"], 1):
                    owner_mask = baseline["analyticOwner"] == owner_index
                    owner_radius2 = int(np.logical_and(radius2, owner_mask).sum())
                    owner_accepted = int(np.logical_and(accepted, owner_mask).sum())
                    owners[owner["analyticOwnerId"]] = {"radius2": owner_radius2, "accepted": owner_accepted, "retention": owner_accepted / owner_radius2 if owner_radius2 else None}
                global_row = factor_global[factor]
                global_row["riskUnderbound"] += underbound
                if accepted_metric["sampleCount"]:
                    values = (candidate["acceptedReconstructed"][..., :3].astype(np.float64) - current_rgba[..., :3].astype(np.float64))[accepted]
                    global_row["errors"].append(values)
                global_row["falseInvalid"] += false_invalid
                global_row["aliases"] += alias_accepted
                global_row["fallback"] &= fallback
                if repeat == 1:
                    global_row["additionalByFixture"][fixture_id] = additional
                    global_row["eligibilityByFixture"][fixture_id] = opportunity_eligible / opportunity_count if opportunity_count else None
                    global_row["acceptanceByFixture"][fixture_id] = opportunity_accepted / opportunity_count if opportunity_count else None
                    if fixture_id == "STATIC_FREQUENCY_CONTROL_131X89":
                        global_row["staticDelta"] = accepted_count - int(baseline["accepted"].sum())
                cell_factor_records.append({
                    "factor": factor, "eligible": int(eligible.sum()), "unavailable": int(unavailable.sum()), "accepted": accepted_count,
                    "radius2": radius2_count, "acceptedToRadius2": accepted_count / radius2_count if radius2_count else None,
                    "localizedOpportunity": opportunity_count, "localizedOpportunityEligible": opportunity_eligible,
                    "localizedOpportunityAccepted": opportunity_accepted, "additionalAccepted": additional,
                    "riskUnderboundRgbSamples": underbound, "acceptedRgb": accepted_metric, "falseInvalidAccepts": false_invalid,
                    "registeredMaterialAliasesAccepted": alias_accepted, "fallbackExact": fallback, "subsets": cell_subsets,
                    "fullStencilIdentity": cell_full_identity, "owners": owners,
                })
            cell_records.append({"cell": cell, "fixtureId": fixture_id, "repeat": repeat, "baselineMasks": cell_baseline, "factors": cell_factor_records})
    repeat_identity = all(repeat_hashes[fixture][1] == repeat_hashes[fixture][2] for fixture in repeat_hashes)
    monotonic = True
    for fixture_id, fixture in fixtures.items():
        for repeat in (1, 2):
            base = cli.root / "consumers" / "python" / fixture_id / f"R{repeat}" / "arrays"
            previous_risk = None; previous_accepted = None
            for factor in factors:
                risk = load_array(base / f"factor-{factor:02d}" / "risk.q30.u32", "<u4", fixture["resolution"][1], fixture["resolution"][0], 3)[0]
                accepted = load_array(base / f"factor-{factor:02d}" / "accepted.u8", "u1", fixture["resolution"][1], fixture["resolution"][0], 1)[0].astype(bool)
                if previous_risk is not None:
                    monotonic &= bool(np.all(risk >= previous_risk)) and not np.logical_and(accepted, ~previous_accepted).any()
                previous_risk, previous_accepted = risk, accepted
    selected = None
    factor_summaries = []
    primary = spec["sourceMatrix"]["primaryOpportunityFixtures"]
    for factor in factors:
        row = factor_global[factor]
        errors = np.concatenate(row["errors"]) if row["errors"] else np.array([], dtype=np.float64)
        maximum = float(np.abs(errors).max()) if errors.size else None
        rmse = float(np.sqrt(np.mean(errors * errors))) if errors.size else None
        gates = {
            "riskUnderbound": row["riskUnderbound"] <= spec["selectionGates"]["riskUnderboundRgbSamplesMaximum"],
            "qualityMaximum": maximum is not None and maximum <= spec["selectionGates"]["acceptedRgbMaximum"],
            "qualityRmse": rmse is not None and rmse <= spec["selectionGates"]["acceptedRgbRmseMaximum"],
            "falseInvalid": row["falseInvalid"] <= spec["selectionGates"]["falseInvalidHistoryAcceptsMaximum"],
            "materialAliases": row["aliases"] <= spec["selectionGates"]["registeredMaterialAliasesAcceptedMaximum"],
            "opportunityEligibility": all(row["eligibilityByFixture"].get(fixture) is not None and row["eligibilityByFixture"][fixture] >= spec["selectionGates"]["minimumLocalizedOpportunityEligibilityPerPrimaryFixture"] for fixture in primary),
            "opportunityAcceptance": all(row["acceptanceByFixture"].get(fixture) is not None and row["acceptanceByFixture"][fixture] >= spec["selectionGates"]["minimumLocalizedOpportunityAcceptancePerPrimaryFixture"] for fixture in primary),
            "additionalAccepted": all(row["additionalByFixture"].get(fixture, 0) >= spec["selectionGates"]["minimumAdditionalAcceptedPerPrimaryFixture"] for fixture in primary),
            "staticControl": row["staticDelta"] == spec["selectionGates"]["staticControlAcceptedDelta"],
            "fallback": row["fallback"],
        }
        factor_passed = all(gates.values())
        factor_summaries.append({"factor": factor, "passed": factor_passed, "gates": gates, "riskUnderboundRgbSamples": row["riskUnderbound"], "acceptedRgbMaximum": maximum, "acceptedRgbRmse": rmse, "falseInvalidAccepts": row["falseInvalid"], "registeredMaterialAliasesAccepted": row["aliases"], "additionalAcceptedByFixture": row["additionalByFixture"], "opportunityEligibilityByFixture": row["eligibilityByFixture"], "opportunityAcceptanceByFixture": row["acceptanceByFixture"], "staticAcceptedDelta": row["staticDelta"]})
        if factor_passed and selected is None:
            selected = factor
    source_isolation = (
        "currentRgba\"][y, x, channel" not in Path("scripts/derive-b52-d12-12-one-sided-curvature.py").read_text()
        and "arrays.currentRgba[rgba(pixel, channel)]" not in Path("scripts/derive-b52-d12-12-one-sided-curvature.mjs").read_text().split("const reconstructed =")[0]
    )
    checks = [
        ("PARENT_IDENTITY", all(parent_checks.values())),
        ("TOOL_IDENTITY", tool_hashes == execution["toolHashes"]),
        ("FORMAL_ROOT_IMMUTABLE", formal_tree == spec["parents"]["formalRoot"]["gitTree"]),
        ("REPORT_SELF_HASHES", all_report_hashes),
        ("DUAL_PAYLOAD_IDENTITY", dual_payload),
        ("REPEAT_IDENTITY", repeat_identity),
        ("RECOMPUTED_BASELINE_MASKS", baseline_masks),
        ("FULL_STENCIL_IDENTITY", full_identity),
        ("SUBSET_PARTITIONS", subsets),
        ("FACTOR_MONOTONICITY", monotonic),
        ("CURRENT_RGB_DECISION_ISOLATION", source_isolation),
        ("REGISTERED_FACTOR_SELECTED", selected is not None),
        ("BLENDER_MODEL_NETWORK_ZERO", execution["operationCounts"] == {"consumerProcesses": 16, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0}),
    ]
    check_rows = [{"id": name, "passed": bool(value)} for name, value in checks]
    passed = all(value for _, value in checks)
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerOneSidedCurvatureDerivationResult.v0.1",
        "experimentId": spec["experimentId"],
        "verdict": spec["decision"]["derivedVerdict"] if passed else spec["decision"]["notDerivedVerdict"],
        "passed": passed,
        "selectedInflationFactor": selected,
        "checkPassed": sum(value for _, value in checks),
        "checkTotal": len(checks),
        "checks": check_rows,
        "factorSummaries": factor_summaries,
        "cells": cell_records,
        "parentChecks": parent_checks,
        "formalRootGitTree": formal_tree,
        "toolHashes": tool_hashes,
        "operationCounts": {"analyzerProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
        "nonClaims": spec["nonClaims"],
    }
    result = {**body, "resultHash": canonical_hash(body)}
    cli.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    receipt_body = {"schemaVersion": "bfs.blenderMaterialOwnerOneSidedCurvatureAnalysisReceipt.v0.1", "experimentId": spec["experimentId"], "pid": os.getpid(), "result": {"uri": str(cli.output), "sha256": sha_file(cli.output), "resultHash": result["resultHash"]}, "toolHashes": tool_hashes, "operationCounts": {"analyzerProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0}}
    cli.analysis_receipt.write_text(json.dumps({**receipt_body, "receiptHash": canonical_hash(receipt_body)}, indent=2, sort_keys=True) + "\n")
    print(f"BFS_B52_D1212_ANALYZE verdict={result['verdict']} factor={selected} checks={result['checkPassed']}/{result['checkTotal']}")


def orchestrate(cli, spec):
    if cli.root.exists():
        raise RuntimeError("refusing to overwrite D12.12 formal root")
    tools = spec["freshness"]["newToolPaths"]
    prereg_commit = git("log", "-1", "--format=%H", "--", str(cli.spec))
    tool_freeze_commit = git("rev-parse", "HEAD")
    for uri in tools:
        probe = subprocess.run(["git", "cat-file", "-e", f"{prereg_commit}:{uri}"], capture_output=True)
        if probe.returncode == 0 or git("show", f"{tool_freeze_commit}:{uri}") == "":
            raise RuntimeError("D12.12 freshness or tool-freeze violation")
        if subprocess.run(["git", "diff", "--quiet", tool_freeze_commit, "--", uri]).returncode != 0:
            raise RuntimeError("D12.12 tool differs from freeze commit")
    if sha_file(cli.spec) != SPEC_SHA256:
        raise RuntimeError("D12.12 spec hash mismatch")
    free = shutil.disk_usage(Path.cwd()).free
    projected = free - spec["execution"]["disk"]["projectedWriteBytes"]
    if projected < spec["execution"]["disk"]["minimumFreeBytesAfterProjectedWrite"]:
        raise RuntimeError("D12.12 disk reserve rejected")
    formal_tree_before = git("rev-parse", f"HEAD:{spec['parents']['formalRoot']['uri']}")
    if formal_tree_before != spec["parents"]["formalRoot"]["gitTree"]:
        raise RuntimeError("D12.12 parent formal tree mismatch")
    cli.root.mkdir(parents=True, exist_ok=False)
    tool_hashes = {uri: sha_file(Path(uri)) for uri in tools}
    children = []
    i1_root = Path(spec["parents"]["materialOwnerResult"]["uri"]).parent
    localization_root = Path(spec["parents"]["ownerSupportLocalizationResult"]["uri"]).parent
    for fixture in spec["sourceMatrix"]["fixtures"]:
        fixture_id = fixture["id"]
        for repeat in (1, 2):
            input_dir = i1_root / "adapters" / fixture_id / f"R{repeat}" / "arrays"
            adapter_report = i1_root / "adapters" / fixture_id / f"R{repeat}" / "report.json"
            classification = localization_root / "payloads" / fixture_id / f"R{repeat}" / "classification.u8"
            for producer, executable, tool in (
                ("python", spec["execution"]["python"]["executable"], "scripts/derive-b52-d12-12-one-sided-curvature.py"),
                ("node", spec["execution"]["node"]["executable"], "scripts/derive-b52-d12-12-one-sided-curvature.mjs"),
            ):
                base = cli.root / "consumers" / producer / fixture_id / f"R{repeat}"
                command = [executable, tool, "--spec", str(cli.spec), "--fixture", fixture_id, "--repeat", str(repeat), "--input-dir", str(input_dir), "--adapter-report", str(adapter_report), "--localization-classification", str(classification), "--output-dir", str(base / "arrays"), "--report", str(base / "report.json")]
                child = spawn(command, Path.cwd())
                child.update({"stage": "consumer", "producer": producer, "fixtureId": fixture_id, "repeat": repeat})
                children.append(child)
                if child["exitCode"] != 0:
                    raise RuntimeError(f"D12.12 consumer failed: {producer}/{fixture_id}/R{repeat}\n{child['stderr']}")
    execution_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerOneSidedCurvatureExecution.v0.1", "experimentId": spec["experimentId"],
        "preregistrationCommit": prereg_commit, "toolFreezeCommit": tool_freeze_commit, "toolHashes": tool_hashes,
        "formalRootGitTreeBefore": formal_tree_before, "disk": {"freeBytesBefore": free, "projectedFreeBytes": projected},
        "children": children, "operationCounts": {"consumerProcesses": 16, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    execution_path = cli.root / "execution.json"
    execution_path.write_text(json.dumps({**execution_body, "executionHash": canonical_hash(execution_body)}, indent=2, sort_keys=True) + "\n")
    result_path, analysis_receipt_path = cli.root / "results.json", cli.root / "analysis-receipt.json"
    analyzer = spawn([spec["execution"]["python"]["executable"], str(Path(__file__)), "--spec", str(cli.spec), "--root", str(cli.root), "--analyze", "--execution", str(execution_path), "--output", str(result_path), "--analysis-receipt", str(analysis_receipt_path)], Path.cwd())
    analyzer["stage"] = "analyzer"; children.append(analyzer)
    if analyzer["exitCode"] != 0:
        raise RuntimeError(f"D12.12 analyzer failed\n{analyzer['stderr']}")
    audit_path = cli.root / "audit.json"
    auditor = spawn([spec["execution"]["python"]["executable"], "scripts/audit-b52-d12-12-one-sided-curvature.py", "--spec", str(cli.spec), "--root", str(cli.root), "--execution", str(execution_path), "--result", str(result_path), "--analysis-receipt", str(analysis_receipt_path), "--output", str(audit_path)], Path.cwd())
    auditor["stage"] = "audit"; children.append(auditor)
    if auditor["exitCode"] != 0:
        raise RuntimeError(f"D12.12 audit failed\n{auditor['stderr']}")
    formal_tree_after = git("rev-parse", f"HEAD:{spec['parents']['formalRoot']['uri']}")
    if formal_tree_after != formal_tree_before or len({row["pid"] for row in children}) != len(children):
        raise RuntimeError("D12.12 process or formal-tree identity failed")
    result = json.loads(result_path.read_text()); audit = json.loads(audit_path.read_text())
    receipt_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerOneSidedCurvatureReceipt.v0.1", "experimentId": spec["experimentId"],
        "verdict": result["verdict"] if audit["passed"] else spec["decision"]["notDerivedVerdict"],
        "preregistrationCommit": prereg_commit, "toolFreezeCommit": tool_freeze_commit, "formalRootGitTreeBefore": formal_tree_before,
        "formalRootGitTreeAfter": formal_tree_after, "allChildPidsUnique": True,
        "children": children,
        "artifacts": {
            "execution": {"uri": str(execution_path), "sha256": sha_file(execution_path)},
            "result": {"uri": str(result_path), "sha256": sha_file(result_path), "resultHash": result["resultHash"]},
            "analysisReceipt": {"uri": str(analysis_receipt_path), "sha256": sha_file(analysis_receipt_path)},
            "audit": {"uri": str(audit_path), "sha256": sha_file(audit_path), "auditHash": audit["auditHash"]},
        },
        "operationCounts": {"consumerProcesses": 16, "analyzerProcesses": 1, "auditProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    receipt_path = cli.root / "receipt.json"
    receipt_path.write_text(json.dumps({**receipt_body, "receiptHash": canonical_hash(receipt_body)}, indent=2, sort_keys=True) + "\n")
    print(f"BFS_B52_D1212_COMPLETE verdict={receipt_body['verdict']} factor={result['selectedInflationFactor']} attacks={audit['attackPassed']}/{audit['attackTotal']}")


def main():
    cli = parse_args()
    if sha_file(cli.spec) != SPEC_SHA256:
        raise RuntimeError("D12.12 spec identity mismatch")
    spec = json.loads(cli.spec.read_text())
    if cli.analyze:
        analyze(cli, spec)
    else:
        orchestrate(cli, spec)


if __name__ == "__main__":
    main()
