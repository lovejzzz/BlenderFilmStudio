#!/usr/bin/env python3
"""Independent, mutation-driven audit for B52-D12.12-H1."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np


SPEC_SHA256 = "b0defadbd120f77dfe81bfa16d9dfd4e3a4d4a15ad1c8ddd1176d21f2e13b648"


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


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--analysis-receipt", type=Path, required=True)
    parser.add_argument("--execution-plan", type=Path, required=True)
    parser.add_argument("--preflight-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def wait_json(path: Path, seconds: float = 10.0):
    deadline = time.monotonic() + seconds
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    if not path.exists():
        raise RuntimeError(f"D12.12-H1 audit input did not appear: {path}")
    return json.loads(path.read_text())


def main():
    cli = arguments()
    if sha_file(cli.spec) != SPEC_SHA256 or cli.output.exists():
        raise RuntimeError("D12.12-H1 audit spec/output identity violation")
    spec = json.loads(cli.spec.read_text())
    result = json.loads(cli.result.read_text())
    analysis_receipt = json.loads(cli.analysis_receipt.read_text())
    execution_plan = wait_json(cli.execution_plan)
    preflight = json.loads(cli.preflight_receipt.read_text())
    state = {
        "result": copy.deepcopy(result),
        "analysisReceipt": copy.deepcopy(analysis_receipt),
        "executionPlan": copy.deepcopy(execution_plan),
        "preflight": copy.deepcopy(preflight),
        "artifacts": {},
        "cells": {},
        "envelopes": [],
    }

    def add_artifact(identifier: str, path: Path, expected_sha: str, family: str):
        payload = path.read_bytes()
        state["artifacts"][identifier] = {"payload": bytearray(payload), "expectedSha": expected_sha, "family": family, "uri": str(path)}

    for name, row in spec["parents"].items():
        if "uri" in row and "sha256" in row:
            add_artifact(f"parent/{name}", Path(row["uri"]), row["sha256"], "parent")
    for uri, expected in result["toolHashes"].items():
        add_artifact(f"tool/{uri}", Path(uri), expected, "tool")
    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        for repeat in (1, 2):
            cell = f"{fixture_id}/R{repeat}"
            cell_state = {"fixture": fixture, "repeat": repeat, "width": width, "height": height, "adapter": {}, "python": {}, "node": {}}
            for frame in (0, 1):
                source_base = cli.root / "sources" / fixture_id / f"R{repeat}"
                source_report_path = source_base / f"frame-{frame}-report.json"
                source_report = json.loads(source_report_path.read_text())
                add_artifact(f"source-report/{cell}/F{frame}", source_report_path, sha_file(source_report_path), "sourceReport")
                add_artifact(f"source-exr/{cell}/F{frame}", source_base / f"frame-{frame}.exr", source_report["output"]["sha256"], "sourceExr")
            adapter_base = cli.root / "adapters" / fixture_id / f"R{repeat}"
            adapter_report_path = adapter_base / "report.json"
            adapter_report = json.loads(adapter_report_path.read_text())
            add_artifact(f"adapter-report/{cell}", adapter_report_path, sha_file(adapter_report_path), "adapterReport")
            for name, row in adapter_report["arrays"].items():
                artifact_id = f"adapter/{cell}/{name}"
                add_artifact(artifact_id, Path(row["uri"]), row["sha256"], "adapterArray")
                cell_state["adapter"][name] = artifact_id
            for producer in ("python", "node"):
                consumer_base = cli.root / "consumers" / producer / fixture_id / f"R{repeat}"
                report_path = consumer_base / "report.json"
                report = json.loads(report_path.read_text())
                add_artifact(f"consumer-report/{producer}/{cell}", report_path, sha_file(report_path), "consumerReport")
                for section in ("controlArrays", "decisionArrays"):
                    for name, row in report[section].items():
                        artifact_id = f"consumer/{producer}/{cell}/{name}"
                        add_artifact(artifact_id, Path(row["uri"]), row["sha256"], "consumerArray")
                        cell_state[producer][name] = artifact_id
            for subtree in ("controlArrays", "decisionArrays"):
                envelope_base = cli.root / "envelopes" / fixture_id / f"R{repeat}" / subtree
                left_id, right_id = f"envelope/python/{cell}/{subtree}", f"envelope/node/{cell}/{subtree}"
                left_path, right_path = envelope_base / "python.bin", envelope_base / "node.bin"
                add_artifact(left_id, left_path, sha_file(left_path), "envelope")
                add_artifact(right_id, right_path, sha_file(right_path), "envelope")
                state["envelopes"].append((left_id, right_id))
            state["cells"][cell] = cell_state

    def payload(identifier):
        return bytes(state["artifacts"][identifier]["payload"])

    def array(identifier, dtype, shape):
        return np.frombuffer(payload(identifier), dtype=dtype).reshape(shape)

    def validate(current):
        gates = {}
        gates["ARTIFACT_HASH_BINDINGS"] = all(sha_bytes(bytes(row["payload"])) == row["expectedSha"] for row in current["artifacts"].values())
        report_self_hashes = True
        for row in current["artifacts"].values():
            if row["family"] in {"sourceReport", "adapterReport", "consumerReport"}:
                try:
                    report_self_hashes &= self_ok(json.loads(bytes(row["payload"]).decode()), "reportHash")
                except (UnicodeDecodeError, json.JSONDecodeError):
                    report_self_hashes = False
        gates["REPORT_SELF_HASHES"] = bool(report_self_hashes)
        candidate = current["result"]
        gates["RESULT_SELF_HASH"] = self_ok(candidate, "resultHash")
        gates["ANALYSIS_RECEIPT_SELF_HASH"] = self_ok(current["analysisReceipt"], "receiptHash")
        gates["ANALYSIS_RECEIPT_RESULT_BINDING"] = (
            current["analysisReceipt"].get("result", {}).get("resultHash") == candidate.get("resultHash")
            and current["analysisReceipt"].get("result", {}).get("sha256") == sha_file(cli.result)
        )
        gates["PREFLIGHT_SELF_HASH"] = self_ok(current["preflight"], "receiptHash") and current["preflight"].get("passed") is True
        gates["PREFLIGHT_TOOL_BINDING"] = current["preflight"].get("toolHashes") == candidate.get("toolHashes")
        plan = current["executionPlan"]
        gates["EXECUTION_PLAN_SELF_HASH"] = self_ok(plan, "executionPlanHash")
        children = plan.get("children", [])
        category_counts = {}
        for row in children:
            category_counts[row.get("category")] = category_counts.get(row.get("category"), 0) + 1
        expected_categories = {
            "sourceBlender": 24, "adapter": 12, "pythonConsumer": 12, "nodeConsumer": 12,
            "typedEnvelopePython": 24, "typedEnvelopeNode": 24, "analyzer": 1, "audit": 1,
        }
        audit_rows = [row for row in children if row.get("category") == "audit"]
        prior_exit = all(row.get("exitCode") == 0 for row in children if row.get("category") != "audit")
        gates["EXECUTION_PROCESS_ROSTER"] = (
            len(children) == spec["processMatrix"]["totalUniqueChildProcessesIncludingAudit"]
            and category_counts == expected_categories and plan.get("categoryCounts") == expected_categories
            and len({row.get("pid") for row in children}) == len(children)
            and prior_exit and len(audit_rows) == 1 and audit_rows[0].get("pid") == os.getpid()
            and audit_rows[0].get("status") == "running" and plan.get("operationCounts") == spec["processMatrix"]
        )
        gates["TOOL_BYTES"] = all(
            sha_bytes(bytes(current["artifacts"][f"tool/{uri}"]["payload"])) == expected
            for uri, expected in candidate.get("toolHashes", {}).items()
        )
        gates["PARENT_FORMAL_TREE_DECLARATIONS"] = candidate.get("parentTrees") == {
            "derivationFormalRoot": spec["parents"]["derivationFormalRoot"]["gitTree"],
            "materialOwnerFormalRoot": spec["parents"]["materialOwnerFormalRoot"]["gitTree"],
        }
        gates["TYPED_ENVELOPES"] = all(payload(left) == payload(right) for left, right in current["envelopes"])
        cross_language = True
        repeat_exact = True
        subset_semantics = True
        fallback = True
        raw_counts = True
        material_tokens = True
        object_control = True
        fingerprints = {}
        result_cells = {row["cell"]: row for row in candidate.get("cells", [])}
        for cell, row in current["cells"].items():
            fixture, width, height = row["fixture"], row["width"], row["height"]
            shape1, shape4 = (height, width), (height, width, 4)
            current_rgba = array(row["adapter"]["currentRgba"], "<f4", shape4)
            current_owner = array(row["adapter"]["currentOwner"], "<f4", shape1)
            previous_owner = array(row["adapter"]["previousOwner"], "<f4", shape1)
            current_object = array(row["adapter"]["currentObjectIndex"], "<f4", shape1)
            previous_object = array(row["adapter"]["previousObjectIndex"], "<f4", shape1)
            declared = {0.0, *(float(owner["materialPassIndex"]) for owner in fixture["owners"])}
            shared_object = float(fixture["owners"][0]["objectPassIndex"])
            material_tokens &= set(float(value) for value in np.unique(current_owner)).issubset(declared)
            material_tokens &= set(float(value) for value in np.unique(previous_owner)).issubset(declared)
            object_control &= fixture["owners"][0]["objectPassIndex"] == fixture["owners"][1]["objectPassIndex"]
            object_control &= set(float(value) for value in np.unique(current_object)).issubset({0.0, shared_object})
            object_control &= set(float(value) for value in np.unique(previous_object)).issubset({0.0, shared_object})
            fingerprints.setdefault(row["fixture"]["id"], {})[row["repeat"]] = {}
            for name in row["python"]:
                left, right = payload(row["python"][name]), payload(row["node"][name])
                cross_language &= left == right
                fingerprints[row["fixture"]["id"]][row["repeat"]][name] = sha_bytes(left)
            accepted = array(row["python"]["accepted"], "u1", shape1).astype(bool)
            eligible = array(row["python"]["oneSidedEligible"], "u1", shape1).astype(bool)
            unavailable = array(row["python"]["oneSidedUnavailable"], "u1", shape1).astype(bool)
            radius2 = array(row["python"]["radius2Interior"], "u1", shape1).astype(bool)
            reconstructed = array(row["python"]["reconstructed"], "<f4", shape4)
            subset_semantics &= np.array_equal(eligible | unavailable, radius2)
            subset_semantics &= not np.logical_and(eligible, unavailable).any() and not np.logical_and(accepted, ~eligible).any()
            fallback &= np.array_equal(reconstructed[~accepted], current_rgba[~accepted])
            declared_row = result_cells.get(cell, {})
            raw_counts &= declared_row.get("accepted") == int(accepted.sum())
            raw_counts &= declared_row.get("radius2") == int(radius2.sum())
            raw_counts &= declared_row.get("oneSidedEligible") == int(eligible.sum())
            raw_counts &= declared_row.get("oneSidedUnavailable") == int(unavailable.sum())
        for fixture_id, repeats in fingerprints.items():
            repeat_exact &= repeats.get(1) == repeats.get(2)
        gates["CROSS_LANGUAGE_ARRAYS"] = bool(cross_language)
        gates["REPEAT_ARRAY_IDENTITY"] = bool(repeat_exact)
        gates["RAW_SUBSET_SEMANTICS"] = bool(subset_semantics)
        gates["FALLBACK_EXACT"] = bool(fallback)
        gates["RAW_RESULT_COUNTS"] = bool(raw_counts)
        gates["MATERIAL_TOKEN_DOMAIN"] = bool(material_tokens)
        gates["OBJECT_INDEX_SHARED_CONTROL"] = bool(object_control)
        hard_pass = all(row.get("passed") for row in candidate.get("hardChecks", []))
        if not hard_pass:
            expected_verdict = spec["decision"]["rejectedVerdict"]
        elif not candidate.get("directionalStressContract"):
            expected_verdict = spec["decision"]["directionFailureVerdict"]
        elif not candidate.get("coverageContract"):
            expected_verdict = spec["decision"]["boundedVerdict"]
        else:
            expected_verdict = spec["decision"]["supportedVerdict"]
        gates["RESULT_VERDICT_MAPPING"] = candidate.get("verdict") == expected_verdict and candidate.get("passed") == (expected_verdict == spec["decision"]["supportedVerdict"])
        quality = candidate.get("globalQuality", {})
        gates["RESULT_SAFETY_SUMMARY"] = (
            candidate.get("factor") == 1 and candidate.get("riskUnderboundRgbSamples") == 0
            and candidate.get("falseInvalidHistoryAccepts") == 0 and candidate.get("acceptedMaterialAliases") == 0
            and quality.get("maximum") is not None and quality["maximum"] <= spec["hardGates"]["acceptedRgbMaximum"]
            and quality.get("rmse") is not None and quality["rmse"] <= spec["hardGates"]["acceptedRgbRmseMaximum"]
        ) == all(next(row["passed"] for row in candidate["hardChecks"] if row["id"] == gate) for gate in (
            "RISK_UNDERBOUND_ZERO", "FALSE_INVALID_HISTORY_ZERO", "MATERIAL_ALIAS_ZERO", "ACCEPTED_RGB_MAXIMUM", "ACCEPTED_RGB_RMSE"
        ))
        return gates

    baseline_gates = validate(state)
    baseline_passed = all(baseline_gates.values())
    attacks = []

    def attack(identifier, family, description, mutate, restore):
        mutate()
        observed = [name for name, passed in validate(state).items() if not passed]
        restore()
        attacks.append({"id": identifier, "family": family, "description": description, "observedFailedGates": observed, "passed": bool(observed)})

    attack_number = 1
    selections = [
        ("parent", 8, "bound parent byte/formal-tree evidence mutation"),
        ("tool", 8, "frozen formal tool byte mutation"),
        ("sourceExr", 12, "source multipart EXR byte mutation"),
        ("adapterArray", 16, "adapter payload/token/vector/depth mutation"),
        ("consumerArray", 24, "decision/support/risk/reconstruction mutation"),
        ("envelope", 8, "cross-language typed-envelope mutation"),
    ]
    for family, count, description in selections:
        candidates = [identifier for identifier, row in state["artifacts"].items() if row["family"] == family][:count]
        if len(candidates) != count:
            raise RuntimeError(f"D12.12-H1 attack family underfilled: {family} {len(candidates)}/{count}")
        for identifier in candidates:
            data = state["artifacts"][identifier]["payload"]
            index = len(data) // 2
            original = data[index]
            attack(
                f"A{attack_number:03d}", family, f"{description}: {identifier}",
                lambda d=data, i=index: d.__setitem__(i, d[i] ^ 1),
                lambda d=data, i=index, value=original: d.__setitem__(i, value),
            )
            attack_number += 1

    def rehash_result():
        state["result"]["resultHash"] = canonical_hash({key: value for key, value in state["result"].items() if key != "resultHash"})

    semantic_mutations = [
        ("verdict", "replace evidence-derived verdict", lambda row: row.__setitem__("verdict", "MUTATED_VERDICT")),
        ("verdict", "invert supported flag", lambda row: row.__setitem__("passed", not row["passed"])),
        ("factor", "replace frozen factor 1", lambda row: row.__setitem__("factor", 2)),
        ("risk", "inject risk-underbound sample", lambda row: row.__setitem__("riskUnderboundRgbSamples", 1)),
        ("history", "inject false invalid-history accept", lambda row: row.__setitem__("falseInvalidHistoryAccepts", 1)),
        ("material", "inject accepted Material alias", lambda row: row.__setitem__("acceptedMaterialAliases", 1)),
        ("quality", "raise accepted RGB maximum", lambda row: row["globalQuality"].__setitem__("maximum", 1.0)),
        ("quality", "raise accepted RGB RMSE", lambda row: row["globalQuality"].__setitem__("rmse", 1.0)),
        ("direction", "invert directional stress summary", lambda row: row.__setitem__("directionalStressContract", not row["directionalStressContract"])),
        ("coverage", "invert coverage summary", lambda row: row.__setitem__("coverageContract", not row["coverageContract"])),
        ("parent", "replace a bound parent formal tree declaration", lambda row: row["parentTrees"].__setitem__("derivationFormalRoot", "0" * 40)),
        ("rawResult", "increment first cell accepted count", lambda row: row["cells"][0].__setitem__("accepted", row["cells"][0]["accepted"] + 1)),
        ("rawResult", "increment first cell radius denominator", lambda row: row["cells"][0].__setitem__("radius2", row["cells"][0]["radius2"] + 1)),
    ]
    for family, description, mutation in semantic_mutations:
        original = copy.deepcopy(state["result"])
        def mutate_result(change=mutation):
            change(state["result"])
            rehash_result()
        attack(f"A{attack_number:03d}", family, description, mutate_result, lambda value=original: state.__setitem__("result", value))
        attack_number += 1

    original_plan = copy.deepcopy(state["executionPlan"])
    def mutate_plan_count():
        state["executionPlan"]["categoryCounts"]["sourceBlender"] += 1
        state["executionPlan"]["executionPlanHash"] = canonical_hash({key: value for key, value in state["executionPlan"].items() if key != "executionPlanHash"})
    attack(f"A{attack_number:03d}", "process", "mutate 24-render process roster", mutate_plan_count, lambda value=original_plan: state.__setitem__("executionPlan", value)); attack_number += 1
    original_plan = copy.deepcopy(state["executionPlan"])
    def mutate_plan_pid():
        state["executionPlan"]["children"][0]["pid"] = state["executionPlan"]["children"][1]["pid"]
        state["executionPlan"]["executionPlanHash"] = canonical_hash({key: value for key, value in state["executionPlan"].items() if key != "executionPlanHash"})
    attack(f"A{attack_number:03d}", "process", "duplicate a formal child PID", mutate_plan_pid, lambda value=original_plan: state.__setitem__("executionPlan", value)); attack_number += 1
    original_preflight = copy.deepcopy(state["preflight"])
    def mutate_preflight():
        first = next(iter(state["preflight"]["toolHashes"]))
        state["preflight"]["toolHashes"][first] = "0" * 64
        state["preflight"]["receiptHash"] = canonical_hash({key: value for key, value in state["preflight"].items() if key != "receiptHash"})
    attack(f"A{attack_number:03d}", "preflight", "replace preflight tool binding", mutate_preflight, lambda value=original_preflight: state.__setitem__("preflight", value)); attack_number += 1
    original_analysis = copy.deepcopy(state["analysisReceipt"])
    def mutate_analysis():
        state["analysisReceipt"]["result"]["resultHash"] = "f" * 64
        state["analysisReceipt"]["receiptHash"] = canonical_hash({key: value for key, value in state["analysisReceipt"].items() if key != "receiptHash"})
    attack(f"A{attack_number:03d}", "receipt", "replace analysis receipt result binding", mutate_analysis, lambda value=original_analysis: state.__setitem__("analysisReceipt", value)); attack_number += 1

    minimum = int(spec["attacks"]["minimumConcreteSemanticAttacks"])
    if len(attacks) < minimum:
        raise RuntimeError(f"D12.12-H1 attack total below preregistration: {len(attacks)} < {minimum}")
    passed = baseline_passed and all(row["passed"] for row in attacks)
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerOneSidedCurvatureHoldoutAudit.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256,
        "passed": passed,
        "verdict": "MATERIAL_OWNER_ONE_SIDED_CURVATURE_HOLDOUT_AUDIT_ACCEPTED" if passed else "MATERIAL_OWNER_ONE_SIDED_CURVATURE_HOLDOUT_AUDIT_REJECTED",
        "scientificVerdict": result["verdict"],
        "baselineGatePassed": sum(baseline_gates.values()), "baselineGateTotal": len(baseline_gates),
        "baselineGates": [{"id": name, "passed": bool(value)} for name, value in baseline_gates.items()],
        "attackPassed": sum(row["passed"] for row in attacks), "attackTotal": len(attacks), "attacks": attacks,
        "independence": {"importsPipelineModules": False, "mutationNonceCounts": False},
        "operationCounts": {"auditProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
        "nonClaims": spec["nonClaims"],
    }
    audit = {**body, "auditHash": canonical_hash(body)}
    cli.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1212H1_AUDIT verdict={audit['verdict']} baseline={audit['baselineGatePassed']}/{audit['baselineGateTotal']} attacks={audit['attackPassed']}/{audit['attackTotal']}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
