#!/usr/bin/env python3
"""Synthetic contract tests for B52-D2 validation and negative-result handling."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


ANALYZER = load_module("bfs_b52_d2_analysis_contract", ROOT / "scripts/analyze-b52-d2-native-cpu-adaptive-production.py")
D1 = ANALYZER.load_d1_library(ROOT)
SPEC = json.loads((ROOT / "specs/native-cpu-adaptive-production-holdout.v0.1.json").read_text(encoding="utf-8"))
D5 = json.loads((ROOT / SPEC["parents"]["d5Spec"]["uri"]).read_text(encoding="utf-8"))


def synthetic_evidence() -> dict:
    schedule = ANALYZER.expected_matrix(SPEC, D5)
    run_observations = []
    samples = []
    beauty = []
    for index, cell in enumerate(schedule):
        baseline = cell["profile"] == ANALYZER.BASELINE_ID
        render_seconds = 10.0 if baseline else 6.0
        run_observations.append({
            "runId": cell["runId"],
            "processPid": 10000 + index,
            "runnerObservedPid": 10000 + index,
            "deviceValid": True,
            "settingsValid": True,
            "operationReplayValid": True,
            "sourceIdentityMatch": True,
            "rosterMatch": True,
            "allPartsFinite": True,
            "artifactIdentityMatch": True,
            "renderSeconds": render_seconds,
            "freshProcessWallSeconds": render_seconds + 2.0,
            "saveSeconds": 0.1,
            "artifact": {"bytes": 3000000},
        })
        samples.append({
            "runId": cell["runId"],
            "valid": True,
            "meanEffectiveSamples": 100.0 if baseline else 70.0,
        })
        beauty.append({"runId": cell["runId"], "passed": True, "measurementTotal": True})

    repeat_comparisons = [
        {"variantId": variant["id"], "profileId": profile["id"], "allThreeRepeatsExact": True}
        for profile in SPEC["profiles"] for variant in D5["variants"]
    ]
    baseline_measurements = [
        {"runId": f"{variant['id']}_{ANALYZER.BASELINE_ID}_R{repeat}", "passed": True}
        for variant in D5["variants"] for repeat in range(1, SPEC["repeatsPerProfileVariant"] + 1)
    ]
    data, auxiliary, candidates = [], [], []
    for cell in schedule:
        if cell["role"] != "CANDIDATE":
            continue
        data.append({"runId": cell["runId"], "passed": True, "structuralValid": True, "measurementTotal": True})
        auxiliary.append({
            "runId": cell["runId"],
            "passes": {"BFS_MASTER.Normal": True, "BFS_MASTER.Vector": True},
            "allExact": True,
        })
        candidates.append({
            "runId": cell["runId"],
            "variantId": cell["variant"],
            "profileId": cell["profile"],
            "repeat": cell["repeat"],
            "beautyPass": True,
            "dataSemanticPass": True,
            "auxiliaryPass": True,
            "sampleCountPass": True,
            "combinedPass": True,
        })
    costs, mechanisms = ANALYZER.derive_cost_and_mechanism(run_observations, samples, SPEC, D5)
    evidence = {
        "parentObservations": [{"match": True}],
        "specObservation": {"match": True},
        "blenderObservation": {"match": True},
        "sourceObservations": [{"match": True}],
        "sourcePostObservations": [{"match": True}],
        "referenceObservations": [{"match": True}],
        "referencePostObservations": [{"match": True}],
        "diskAdmission": {"status": "ACCEPTED"},
        "schedule": schedule,
        "runObservations": run_observations,
        "sampleCountMeasurements": samples,
        "baselineMeasurements": baseline_measurements,
        "repeatComparisons": repeat_comparisons,
        "referenceIndependence": [{"threeDistinct": True}, {"threeDistinct": True}],
        "referenceFloors": [
            {"ensembleMean": {"rgbRms": 1.0}, "floor": {name: 0.1 for name in SPEC["beautyQualityGate"]["metrics"]}},
            {"ensembleMean": {"rgbRms": 1.0}, "floor": {name: 0.1 for name in SPEC["beautyQualityGate"]["metrics"]}},
        ],
        "beautyMeasurements": beauty,
        "dataSemanticMeasurements": data,
        "auxiliaryPassMeasurements": auxiliary,
        "candidateMeasurements": candidates,
        "costMeasurements": costs,
        "sampleMechanismMeasurements": mechanisms,
        "operationCounts": copy.deepcopy(SPEC["operationBoundary"]),
    }
    summaries, selected = ANALYZER.replay_selection(evidence, SPEC)
    evidence["profileSummaries"], evidence["selectedProfileId"] = summaries, selected
    evidence["evidenceCoreHash"] = D1.canonical_hash(ANALYZER.hash_payload(evidence))
    return evidence


class B52D2AnalysisContractTests(unittest.TestCase):
    def test_valid_positive_and_all_attacks(self):
        evidence = synthetic_evidence()
        self.assertIsNone(ANALYZER.validate(evidence, SPEC, D5, D1))
        attacks = ANALYZER.run_attacks(evidence, SPEC, D5, D1)
        self.assertEqual(len(attacks), len(SPEC["attacks"]))
        self.assertTrue(all(item["passed"] for item in attacks), attacks)

    def test_legitimate_negative_is_not_invalid(self):
        evidence = synthetic_evidence()
        for auxiliary in evidence["auxiliaryPassMeasurements"]:
            auxiliary["passes"] = {"BFS_MASTER.Normal": False, "BFS_MASTER.Vector": False}
            auxiliary["allExact"] = False
        for candidate in evidence["candidateMeasurements"]:
            candidate["auxiliaryPass"] = False
            candidate["combinedPass"] = False
        summaries, selected = ANALYZER.replay_selection(evidence, SPEC)
        evidence["profileSummaries"], evidence["selectedProfileId"] = summaries, selected
        evidence["evidenceCoreHash"] = D1.canonical_hash(ANALYZER.hash_payload(evidence))
        self.assertIsNone(selected)
        self.assertIsNone(ANALYZER.validate(evidence, SPEC, D5, D1))

    def test_baseline_failure_is_invalid(self):
        evidence = synthetic_evidence()
        evidence["baselineMeasurements"][0]["passed"] = False
        evidence["evidenceCoreHash"] = D1.canonical_hash(ANALYZER.hash_payload(evidence))
        self.assertEqual(ANALYZER.validate(evidence, SPEC, D5, D1), "BASELINE_VALIDITY")

    def test_cost_tampering_is_detected(self):
        evidence = synthetic_evidence()
        evidence["costMeasurements"][0]["renderSavingFraction"] = 0.99
        summaries, selected = ANALYZER.replay_selection(evidence, SPEC)
        evidence["profileSummaries"], evidence["selectedProfileId"] = summaries, selected
        evidence["evidenceCoreHash"] = D1.canonical_hash(ANALYZER.hash_payload(evidence))
        self.assertEqual(ANALYZER.validate(evidence, SPEC, D5, D1), "COST_MEASUREMENT_TOTALITY")


if __name__ == "__main__":
    unittest.main()
