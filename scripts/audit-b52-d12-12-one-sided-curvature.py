#!/usr/bin/env python3
"""Independent raw-array and adversarial audit for B52-D12.12-D1."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np


SPEC_SHA256 = "f179b4cea6c8d3bc19b4cf2534055ef98b3fa8dac9954bfeae28bc2a237dd640"
Q30 = 1 << 30


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


def load_array(path: Path, dtype: str, shape):
    payload = path.read_bytes()
    if len(payload) != int(np.prod(shape)) * np.dtype(dtype).itemsize:
        raise RuntimeError(f"D12.12 audit length mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy(), payload


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--analysis-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def result_factor_row(result, factor):
    return next(row for row in result["factorSummaries"] if row["factor"] == factor)


def result_cell_row(result, cell, factor):
    cell_row = next(row for row in result["cells"] if row["cell"] == cell)
    return next(row for row in cell_row["factors"] if row["factor"] == factor)


def main():
    cli = arguments()
    if cli.output.exists() or sha_file(cli.spec) != SPEC_SHA256:
        raise RuntimeError("D12.12 audit output or spec identity invalid")
    spec = json.loads(cli.spec.read_text())
    execution = json.loads(cli.execution.read_text())
    result = json.loads(cli.result.read_text())
    analysis_receipt = json.loads(cli.analysis_receipt.read_text())
    i1_root = Path(spec["parents"]["materialOwnerResult"]["uri"]).parent
    i1_spec = json.loads(Path(spec["parents"]["materialOwnerSpec"]["uri"]).read_text())
    h1_spec = json.loads(Path(i1_spec["parents"]["h1Spec"]["uri"]).read_text())
    fixtures = {row["id"]: row for row in h1_spec["fixtures"]}
    factors = spec["candidateFamily"]["inflationFactors"]
    expected_selected = next((row["factor"] for row in result["factorSummaries"] if row["passed"]), None)
    audited_factor = result["selectedInflationFactor"] if result["selectedInflationFactor"] is not None else factors[0]
    state = {"result": copy.deepcopy(result), "parents": {}, "cells": {}}
    for name, row in spec["parents"].items():
        if "uri" in row and "sha256" in row:
            state["parents"][name] = bytearray(Path(row["uri"]).read_bytes())
    for fixture_id, fixture in fixtures.items():
        width, height = fixture["resolution"]
        for repeat in (1, 2):
            cell = f"{fixture_id}/R{repeat}"
            adapter_dir = i1_root / "adapters" / fixture_id / f"R{repeat}" / "arrays"
            adapter_report = json.loads((i1_root / "adapters" / fixture_id / f"R{repeat}" / "report.json").read_text())
            current_rgba, _ = load_array(adapter_dir / "current.rgba32", "<f4", (height, width, 4))
            current_owner, current_owner_bytes = load_array(adapter_dir / "current-owner.f32", "<f4", (height, width))
            baseline_dir = i1_root / "consumers" / "python" / fixture_id / f"R{repeat}" / "arrays"
            baseline_accepted, _ = load_array(baseline_dir / "accepted.u8", "u1", (height, width))
            baseline_risk, _ = load_array(baseline_dir / "risk.q30.u32", "<u4", (height, width, 3))
            baseline_reconstructed, _ = load_array(baseline_dir / "accepted-reconstructed.rgba32", "<f4", (height, width, 4))
            py_base = cli.root / "consumers" / "python" / fixture_id / f"R{repeat}" / "arrays"
            node_base = cli.root / "consumers" / "node" / fixture_id / f"R{repeat}" / "arrays"
            control = {}
            for name, filename in {"radius2": "radius2-interior.u8", "full": "full-stencil.u8", "opportunity": "localized-opportunity.u8"}.items():
                control[name] = load_array(py_base / "control" / filename, "u1", (height, width))[0]
            def factor_arrays(base, factor):
                folder = base / f"factor-{factor:02d}"
                return {
                    "eligible": load_array(folder / "one-sided-eligible.u8", "u1", (height, width))[0],
                    "unavailable": load_array(folder / "one-sided-unavailable.u8", "u1", (height, width))[0],
                    "accepted": load_array(folder / "accepted.u8", "u1", (height, width))[0],
                    "risk": load_array(folder / "risk.q30.u32", "<u4", (height, width, 3))[0],
                    "reconstructed": load_array(folder / "accepted-reconstructed.rgba32", "<f4", (height, width, 4))[0],
                }
            py = {factor: factor_arrays(py_base, factor) for factor in factors}
            node = {factor: factor_arrays(node_base, factor) for factor in factors}
            state["cells"][cell] = {
                "fixtureId": fixture_id, "repeat": repeat, "currentRgba": current_rgba, "currentOwner": current_owner,
                "currentOwnerExpectedSha": adapter_report["arrays"]["currentOwner"]["sha256"], "currentOwnerBytes": bytearray(current_owner_bytes),
                "baselineAccepted": baseline_accepted, "baselineRisk": baseline_risk, "baselineReconstructed": baseline_reconstructed,
                "radius2": control["radius2"], "full": control["full"], "opportunity": control["opportunity"], "python": py, "node": node,
            }

    def validate(current_state):
        gates = {}
        gates["PARENT_IDENTITY"] = all(sha_bytes(bytes(current_state["parents"][name])) == spec["parents"][name]["sha256"] for name in current_state["parents"])
        candidate_result = current_state["result"]
        gates["RESULT_SELF_HASH"] = self_ok(candidate_result, "resultHash")
        checks_pass = all(row["passed"] for row in candidate_result["checks"])
        gates["RESULT_VERDICT_MAPPING"] = candidate_result["passed"] == checks_pass and candidate_result["verdict"] == (spec["decision"]["derivedVerdict"] if checks_pass else spec["decision"]["notDerivedVerdict"])
        passing_factors = [row["factor"] for row in candidate_result["factorSummaries"] if row["passed"]]
        expected = passing_factors[0] if passing_factors else None
        gates["FACTOR_SELECTION"] = candidate_result["selectedInflationFactor"] == expected and all(row["factor"] in factors for row in candidate_result["factorSummaries"])
        summary_semantics = True
        for row in candidate_result["factorSummaries"]:
            primary = spec["sourceMatrix"]["primaryOpportunityFixtures"]
            expected_gates = {
                "riskUnderbound": row["riskUnderboundRgbSamples"] <= spec["selectionGates"]["riskUnderboundRgbSamplesMaximum"],
                "qualityMaximum": row["acceptedRgbMaximum"] is not None and row["acceptedRgbMaximum"] <= spec["selectionGates"]["acceptedRgbMaximum"],
                "qualityRmse": row["acceptedRgbRmse"] is not None and row["acceptedRgbRmse"] <= spec["selectionGates"]["acceptedRgbRmseMaximum"],
                "falseInvalid": row["falseInvalidAccepts"] <= spec["selectionGates"]["falseInvalidHistoryAcceptsMaximum"],
                "materialAliases": row["registeredMaterialAliasesAccepted"] <= spec["selectionGates"]["registeredMaterialAliasesAcceptedMaximum"],
                "opportunityEligibility": all(row["opportunityEligibilityByFixture"].get(fixture) is not None and row["opportunityEligibilityByFixture"][fixture] >= spec["selectionGates"]["minimumLocalizedOpportunityEligibilityPerPrimaryFixture"] for fixture in primary),
                "opportunityAcceptance": all(row["opportunityAcceptanceByFixture"].get(fixture) is not None and row["opportunityAcceptanceByFixture"][fixture] >= spec["selectionGates"]["minimumLocalizedOpportunityAcceptancePerPrimaryFixture"] for fixture in primary),
                "additionalAccepted": all(row["additionalAcceptedByFixture"].get(fixture, 0) >= spec["selectionGates"]["minimumAdditionalAcceptedPerPrimaryFixture"] for fixture in primary),
                "staticControl": row["staticAcceptedDelta"] == spec["selectionGates"]["staticControlAcceptedDelta"],
                "fallback": row["gates"].get("fallback") is True,
            }
            summary_semantics &= row["gates"] == expected_gates and row["passed"] == all(expected_gates.values())
            summary_semantics &= row["riskUnderboundRgbSamples"] >= 0 and row["falseInvalidAccepts"] >= 0 and row["registeredMaterialAliasesAccepted"] >= 0
            for fixture in spec["sourceMatrix"]["primaryOpportunityFixtures"]:
                eligibility = row["opportunityEligibilityByFixture"].get(fixture)
                acceptance = row["opportunityAcceptanceByFixture"].get(fixture)
                summary_semantics &= eligibility is not None and 0 <= eligibility <= 1 and acceptance is not None and 0 <= acceptance <= 1
        gates["SUMMARY_SEMANTICS"] = bool(summary_semantics)
        cross_language = True; raw_semantics = True; fallback = True; full_identity = True; adapter_identity = True; raw_result = True; monotonic = True
        repeat_fingerprints = {}
        for cell, row in current_state["cells"].items():
            fixture_id = row["fixtureId"]
            adapter_identity &= sha_bytes(bytes(row["currentOwnerBytes"])) == row["currentOwnerExpectedSha"]
            radius2 = row["radius2"].astype(bool); full = row["full"].astype(bool); opportunity = row["opportunity"].astype(bool)
            previous_risk = None; previous_accepted = None
            repeat_fingerprints.setdefault(fixture_id, {})[row["repeat"]] = {}
            for factor in factors:
                py = row["python"][factor]; node = row["node"][factor]
                for key in py:
                    cross_language &= np.array_equal(py[key], node[key])
                    repeat_fingerprints[fixture_id][row["repeat"]][f"{factor}/{key}"] = sha_bytes(np.ascontiguousarray(py[key]).tobytes())
                eligible = py["eligible"].astype(bool); unavailable = py["unavailable"].astype(bool); accepted = py["accepted"].astype(bool)
                raw_semantics &= np.array_equal(eligible | unavailable, radius2) and not np.logical_and(eligible, unavailable).any() and not np.logical_and(accepted, ~eligible).any()
                fallback &= np.array_equal(py["reconstructed"][~accepted], row["currentRgba"][~accepted])
                full_identity &= np.array_equal(py["risk"][full], row["baselineRisk"][full]) and np.array_equal(py["accepted"][full], row["baselineAccepted"][full]) and np.array_equal(py["reconstructed"][full], row["baselineReconstructed"][full])
                if previous_risk is not None:
                    monotonic &= bool(np.all(py["risk"] >= previous_risk)) and not np.logical_and(accepted, ~previous_accepted).any()
                previous_risk, previous_accepted = py["risk"], accepted
                declared = result_cell_row(candidate_result, cell, factor)
                raw_result &= declared["eligible"] == int(eligible.sum()) and declared["unavailable"] == int(unavailable.sum()) and declared["accepted"] == int(accepted.sum())
                raw_result &= declared["localizedOpportunity"] == int(opportunity.sum()) and declared["localizedOpportunityEligible"] == int(np.logical_and(opportunity, eligible).sum()) and declared["localizedOpportunityAccepted"] == int(np.logical_and(opportunity, accepted).sum())
                raw_result &= declared["additionalAccepted"] == int(np.logical_and(accepted, ~row["baselineAccepted"].astype(bool)).sum())
        repeat_identity = all(repeat_fingerprints[fixture][1] == repeat_fingerprints[fixture][2] for fixture in repeat_fingerprints)
        gates["ADAPTER_BYTES"] = bool(adapter_identity)
        gates["CROSS_LANGUAGE"] = bool(cross_language)
        gates["RAW_SUBSETS"] = bool(raw_semantics)
        gates["RAW_RESULT_COUNTS"] = bool(raw_result)
        gates["FALLBACK_EXACT"] = bool(fallback)
        gates["FULL_STENCIL_IDENTITY"] = bool(full_identity)
        gates["FACTOR_MONOTONICITY"] = bool(monotonic)
        gates["REPEAT_IDENTITY"] = bool(repeat_identity)
        return gates

    baseline_gates = validate(state)
    baseline_passed = all(baseline_gates.values())
    attacks = []

    def attack(identifier, description, mutate, restore):
        mutate()
        observed = [name for name, passed in validate(state).items() if not passed]
        restore()
        attacks.append({"id": identifier, "description": description, "observedFailedGates": observed, "passed": bool(observed)})

    attack_index = 1
    for name in list(state["parents"])[:10]:
        original = state["parents"][name][0]
        attack(f"A{attack_index:02d}", f"flip bound parent byte: {name}", lambda n=name: state["parents"][n].__setitem__(0, state["parents"][n][0] ^ 1), lambda n=name, o=original: state["parents"][n].__setitem__(0, o)); attack_index += 1
    for cell, row in state["cells"].items():
        payload = row["currentOwnerBytes"]; original = payload[0]
        attack(f"A{attack_index:02d}", f"flip bound Material owner adapter byte: {cell}", lambda p=payload: p.__setitem__(0, p[0] ^ 1), lambda p=payload, o=original: p.__setitem__(0, o)); attack_index += 1
    for cell, row in state["cells"].items():
        array = row["python"][audited_factor]["accepted"]; index = int(np.flatnonzero(row["python"][audited_factor]["eligible"])[0]); original = int(array.flat[index])
        attack(f"A{attack_index:02d}", f"flip accepted decision byte: {cell}", lambda a=array, i=index: a.flat.__setitem__(i, 1 - int(a.flat[i])), lambda a=array, i=index, o=original: a.flat.__setitem__(i, o)); attack_index += 1
    for cell, row in state["cells"].items():
        array = row["python"][audited_factor]["risk"]; index = int(np.flatnonzero(row["full"])[0]) * 3; original = int(array.flat[index])
        attack(f"A{attack_index:02d}", f"increment full-stencil risk unit: {cell}", lambda a=array, i=index: a.flat.__setitem__(i, int(a.flat[i]) + 1), lambda a=array, i=index, o=original: a.flat.__setitem__(i, o)); attack_index += 1
    for cell, row in state["cells"].items():
        eligible = row["python"][audited_factor]["eligible"]; unavailable = row["python"][audited_factor]["unavailable"]; index = int(np.flatnonzero(row["radius2"])[0]); old_e, old_u = int(eligible.flat[index]), int(unavailable.flat[index])
        attack(f"A{attack_index:02d}", f"inject one-sided eligibility partition change: {cell}", lambda e=eligible, u=unavailable, i=index: (e.flat.__setitem__(i, 1 - int(e.flat[i])), u.flat.__setitem__(i, 1 - int(u.flat[i]))), lambda e=eligible, u=unavailable, i=index, oe=old_e, ou=old_u: (e.flat.__setitem__(i, oe), u.flat.__setitem__(i, ou))); attack_index += 1
    for cell, row in state["cells"].items():
        array = row["python"][audited_factor]["reconstructed"]; accepted = row["python"][audited_factor]["accepted"].astype(bool); index = int(np.flatnonzero(~accepted)[0]) * 4; original = float(array.flat[index])
        attack(f"A{attack_index:02d}", f"mutate fallback payload: {cell}", lambda a=array, i=index: a.flat.__setitem__(i, np.float32(float(a.flat[i]) + 0.125)), lambda a=array, i=index, o=original: a.flat.__setitem__(i, np.float32(o))); attack_index += 1
    semantic_mutations = [
        ("set unregistered selected factor", lambda r: r.__setitem__("selectedInflationFactor", 3)),
        ("raise selected quality maximum", lambda r: result_factor_row(r, audited_factor).__setitem__("acceptedRgbMaximum", 1.0)),
        ("inject risk underbound count", lambda r: result_factor_row(r, audited_factor).__setitem__("riskUnderboundRgbSamples", 1)),
        ("inflate opportunity eligibility ratio", lambda r: result_factor_row(r, audited_factor)["opportunityEligibilityByFixture"].__setitem__("ROTATED_SWEEP_HIGH_FREQUENCY_157X103", 1.5)),
        ("invert factor passed label", lambda r: result_factor_row(r, audited_factor).__setitem__("passed", not result_factor_row(r, audited_factor)["passed"])),
        ("replace verdict", lambda r: r.__setitem__("verdict", "MUTATED_VERDICT")),
    ]
    for description, mutation in semantic_mutations:
        original = copy.deepcopy(state["result"])
        def mutate_result(m=mutation):
            m(state["result"])
            body = {key: value for key, value in state["result"].items() if key != "resultHash"}
            state["result"]["resultHash"] = canonical_hash(body)
        attack(f"A{attack_index:02d}", description, mutate_result, lambda o=original: state.__setitem__("result", o)); attack_index += 1
    first_four = list(state["cells"].items())[:4]
    for cell, row in first_four:
        array = row["node"][audited_factor]["accepted"]; index = int(np.flatnonzero(row["node"][audited_factor]["eligible"])[0]); original = int(array.flat[index])
        attack(f"A{attack_index:02d}", f"break cross-language accepted byte: {cell}", lambda a=array, i=index: a.flat.__setitem__(i, 1 - int(a.flat[i])), lambda a=array, i=index, o=original: a.flat.__setitem__(i, o)); attack_index += 1
    repeat_two = [(cell, row) for cell, row in state["cells"].items() if row["repeat"] == 2][:4]
    for cell, row in repeat_two:
        py = row["python"][audited_factor]["risk"]; node = row["node"][audited_factor]["risk"]; index = int(np.flatnonzero(row["full"])[0]) * 3; old_py, old_node = int(py.flat[index]), int(node.flat[index])
        attack(f"A{attack_index:02d}", f"break repeat while preserving dual language: {cell}", lambda p=py, n=node, i=index: (p.flat.__setitem__(i, int(p.flat[i]) + 1), n.flat.__setitem__(i, int(n.flat[i]) + 1)), lambda p=py, n=node, i=index, op=old_py, on=old_node: (p.flat.__setitem__(i, op), n.flat.__setitem__(i, on))); attack_index += 1
    if len(attacks) != spec["attacks"]["minimumConcreteSemanticAttacks"]:
        raise RuntimeError(f"D12.12 attack roster mismatch: {len(attacks)}")
    formal_tree = subprocess.run(["git", "rev-parse", f"HEAD:{spec['parents']['formalRoot']['uri']}"], check=True, text=True, capture_output=True).stdout.strip()
    tool_hashes = {uri: sha_file(Path(uri)) for uri in spec["freshness"]["newToolPaths"]}
    source_isolation = (
        "currentRgba\"][y, x, 0" not in Path("scripts/derive-b52-d12-12-one-sided-curvature.py").read_text()
        and "currentRgba\"][y, x, 1" not in Path("scripts/derive-b52-d12-12-one-sided-curvature.py").read_text()
        and "currentRgba\"][y, x, 2" not in Path("scripts/derive-b52-d12-12-one-sided-curvature.py").read_text()
        and "arrays.currentRgba[rgba(pixel, 0)]" not in Path("scripts/derive-b52-d12-12-one-sided-curvature.mjs").read_text()
        and "arrays.currentRgba[rgba(pixel, 1)]" not in Path("scripts/derive-b52-d12-12-one-sided-curvature.mjs").read_text()
        and "arrays.currentRgba[rgba(pixel, 2)]" not in Path("scripts/derive-b52-d12-12-one-sided-curvature.mjs").read_text()
    )
    extra_gates = {
        "SPEC_IDENTITY": sha_file(cli.spec) == SPEC_SHA256,
        "EXECUTION_SELF_HASH": self_ok(execution, "executionHash"),
        "ANALYSIS_RECEIPT_SELF_HASH": self_ok(analysis_receipt, "receiptHash"),
        "ANALYSIS_RECEIPT_RESULT": analysis_receipt["result"]["sha256"] == sha_file(cli.result) and analysis_receipt["result"]["resultHash"] == result["resultHash"],
        "TOOL_IDENTITY": tool_hashes == execution["toolHashes"],
        "FORMAL_ROOT_IMMUTABLE": formal_tree == spec["parents"]["formalRoot"]["gitTree"],
        "CURRENT_RGB_DECISION_ISOLATION": source_isolation,
        "OPERATION_COUNTS": execution["operationCounts"] == {"consumerProcesses": 16, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    all_baseline_gates = {**baseline_gates, **extra_gates}
    passed = baseline_passed and all(extra_gates.values()) and all(row["passed"] for row in attacks)
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerOneSidedCurvatureAudit.v0.1",
        "experimentId": spec["experimentId"],
        "passed": passed,
        "verdict": "MATERIAL_OWNER_ONE_SIDED_CURVATURE_DERIVATION_AUDIT_ACCEPTED" if passed else "MATERIAL_OWNER_ONE_SIDED_CURVATURE_DERIVATION_AUDIT_REJECTED",
        "auditedFactor": audited_factor,
        "expectedSelectedFactor": expected_selected,
        "baselineGatePassed": sum(all_baseline_gates.values()),
        "baselineGateTotal": len(all_baseline_gates),
        "baselineGates": [{"id": name, "passed": bool(value)} for name, value in all_baseline_gates.items()],
        "attackPassed": sum(row["passed"] for row in attacks),
        "attackTotal": len(attacks),
        "attacks": attacks,
        "formalRootGitTree": formal_tree,
        "toolHashes": tool_hashes,
        "operationCounts": {"auditProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
        "nonClaims": spec["nonClaims"],
    }
    audit = {**body, "auditHash": canonical_hash(body)}
    cli.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(f"BFS_B52_D1212_AUDIT verdict={audit['verdict']} baseline={audit['baselineGatePassed']}/{audit['baselineGateTotal']} attacks={audit['attackPassed']}/{audit['attackTotal']}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
