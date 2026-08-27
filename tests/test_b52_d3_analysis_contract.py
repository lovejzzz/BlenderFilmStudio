#!/usr/bin/env python3
"""Synthetic decision-contract tests for the frozen B52-D3 analyzer."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent.parent


def load_module(name: str, path: Path):
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


ANALYZER = load_module("bfs_b52_d3_analyzer", ROOT / "scripts/analyze-b52-d3-adaptive-payload-semantics.py")
LIBRARY = load_module("bfs_b52_analysis_library_for_d3_test", ROOT / "scripts/analyze-b52-native-cpu-adaptive-quality-cost.py")
SPEC = json.loads((ROOT / "specs/adaptive-payload-semantics-derivation.v0.1.json").read_text(encoding="utf-8"))


def synthetic_measurement(profile_id: str, variant_id: str, passed: bool) -> dict:
    composite = {"foreground": [1.0, 1.0, 1.0], "background": [0.0, 0.0, 0.0], "rgbAbsoluteErrorP50": 0.0, "rgbAbsoluteErrorP95": 0.0, "rgbAbsoluteErrorP99": 0.0, "rgbAbsoluteErrorMaximum": 0.0, "rgbAbsoluteErrorRmse": 0.0}
    crypto_object = {
        "name": "Object",
        "hardMatteMismatchPixels": 0,
        "hardMatteMismatchPixelsInsideBoundary": 0,
        "hardMatteMismatchPixelsStableInterior": 0,
        "alphaAbsoluteErrorP50": 0.0,
        "alphaAbsoluteErrorP95": 0.0,
        "alphaAbsoluteErrorP99": 0.0,
        "alphaAbsoluteErrorMaximum": 0.0,
        "alphaAbsoluteErrorRmse": 0.0,
        "changedAlphaPixelCount": 0,
        "changedAlphaInsideBoundaryPixelCount": 0,
        "changedAlphaBoundaryLocalizationFraction": 1.0,
        "unitContrastComposites": [composite, {**composite, "foreground": [1.0, 0.0, 0.0]}],
        "classifierPassed": passed,
    }
    normal_probe = {"direction": [0.0, 0.0, 1.0], "absoluteErrorP50": 0.0, "absoluteErrorP95": 0.0, "absoluteErrorP99": 0.0, "absoluteErrorMaximum": 0.0, "absoluteErrorRmse": 0.0}
    vector_pair = {"pair": "pairA", "channels": ["X", "Y"], "stableInteriorNonzeroSupportMismatchPixels": 0, "endpointErrorP50": 0.0, "endpointErrorP95": 0.0, "endpointErrorP99": 0.0, "endpointErrorMaximum": 0.0, "endpointErrorRmse": 0.0}
    return {
        "profileId": profile_id,
        "variantId": variant_id,
        "baselineRunId": f"{variant_id}_PROD_T010_M0_R1",
        "candidateRunId": f"{variant_id}_{profile_id}_R1",
        "cryptomatte": {"hardMatteThreshold": 0.5, "visibleObjectCount": 1, "stableInteriorConfidentDominantIdMismatchPixels": 0, "objects": [crypto_object], "classifierPassed": passed, "measurementTotal": True},
        "normal": {"stableInteriorBothValidPixelCount": 1, "validVectorMaskMismatchPixels": 0, "angularErrorDegreesP50": 0.0, "angularErrorDegreesP95": 0.0, "angularErrorDegreesP99": 0.0, "angularErrorDegreesMaximum": 0.0, "angularErrorDegreesRmse": 0.0, "changedNormalPixelCount": 0, "changedNormalInsideBoundaryPixelCount": 0, "changedNormalBoundaryLocalizationFraction": 1.0, "lambertianProbes": [{**normal_probe, "direction": direction} for direction in SPEC["normalTask"]["lambertianProbeDirections"]], "classifierPassed": passed, "measurementTotal": True},
        "vector": {"stableInteriorNonzeroSupportMismatchPixels": 0, "pairs": [vector_pair, {**vector_pair, "pair": "pairB", "channels": ["Z", "W"]}], "changedVectorPixelCount": 0, "changedVectorInsideBoundaryPixelCount": 0, "changedVectorBoundaryLocalizationFraction": 1.0, "classifierPassed": passed, "measurementTotal": True},
        "allTaskClassifiersPassed": passed,
    }


def synthetic_evidence(passed: bool = True) -> dict:
    measurements = [synthetic_measurement(profile, variant, passed) for profile, variant in ANALYZER.expected_pair_keys(SPEC)]
    repeat_comparisons = [{"profileId": profile, "variantId": variant, "runIds": ["a", "b", "c"], "pairs": [], "allThreeRepeatsExact": True} for profile in [SPEC["inputs"]["baselineProfile"], *SPEC["inputs"]["candidateProfiles"]] for variant in SPEC["inputs"]["variants"]]
    diagnostics = [{"profileId": profile, "variantId": variant, "kind": kind, "identityMatch": True} for profile in SPEC["diagnostics"]["profiles"] for variant in SPEC["inputs"]["variants"] for kind in SPEC["diagnostics"]["mapsPerPair"]]
    evidence = {
        "specObservation": {"match": True},
        "parentObservations": [{"match": True}],
        "artifactObservations": [{"match": True} for _ in range(54)],
        "runObservations": [{"roster": copy.deepcopy(ANALYZER.EXPECTED_ROSTER), "allPartsFinite": True} for _ in range(54)],
        "repeatComparisons": repeat_comparisons,
        "manifestObservations": [{"metadataValid": True, "manifestMatch": True, "structuralValid": True} for _ in range(54)],
        "regions": [{"variantId": variant, "foregroundPixelCount": 10, "boundaryPixelCount": 2, "stableInteriorPixelCount": 8, "maskSha256": {"foreground": "f", "boundarySeed": "s", "boundary": "b", "stableInterior": "i"}} for variant in SPEC["inputs"]["variants"]],
        "candidateMeasurements": measurements,
        "diagnostics": diagnostics,
        "operationCounts": copy.deepcopy(SPEC["operationBoundary"]),
    }
    evidence["profileSummaries"], evidence["futureHoldoutCandidates"] = ANALYZER.replay_classification(evidence, SPEC)
    evidence["evidenceCoreHash"] = LIBRARY.canonical_hash(ANALYZER.hash_payload(evidence))
    return evidence


class B52D3ContractTests(unittest.TestCase):
    def test_valid_positive_and_all_attacks(self) -> None:
        evidence = synthetic_evidence(True)
        self.assertIsNone(ANALYZER.validate(evidence, SPEC, LIBRARY))
        attacks = ANALYZER.run_attacks(evidence, SPEC, LIBRARY)
        self.assertEqual(len(attacks), 13)
        self.assertTrue(all(item["passed"] for item in attacks), attacks)

    def test_no_future_candidate_is_still_valid(self) -> None:
        evidence = synthetic_evidence(False)
        self.assertEqual(evidence["futureHoldoutCandidates"], [])
        self.assertIsNone(ANALYZER.validate(evidence, SPEC, LIBRARY))

    def test_classification_tampering_is_rejected(self) -> None:
        evidence = synthetic_evidence(True)
        evidence["profileSummaries"][0]["futureHoldoutCandidate"] = False
        evidence["evidenceCoreHash"] = LIBRARY.canonical_hash(ANALYZER.hash_payload(evidence))
        self.assertEqual(ANALYZER.validate(evidence, SPEC, LIBRARY), "CLASSIFICATION_REPLAY")

    def test_diagnostic_identity_tampering_is_rejected(self) -> None:
        evidence = synthetic_evidence(True)
        evidence["diagnostics"][0]["identityMatch"] = False
        evidence["evidenceCoreHash"] = LIBRARY.canonical_hash(ANALYZER.hash_payload(evidence))
        self.assertEqual(ANALYZER.validate(evidence, SPEC, LIBRARY), "DIAGNOSTIC_TOTALITY")

    def test_task_measurements_accept_exact_synthetic_payload(self) -> None:
        shape = (4, 5)
        region = {"stableInterior": np.ones(shape, dtype=bool), "boundary": np.zeros(shape, dtype=bool)}
        ids = np.ones((*shape, 6), dtype=np.uint32)
        coverage = np.zeros((*shape, 6), dtype=np.float32)
        coverage[..., 0] = 1.0
        crypto = {"ids": ids, "coverage": coverage, "mattes": {"Object": np.ones(shape, dtype=np.float64)}}
        crypto_result, crypto_map = ANALYZER.measure_cryptomatte(crypto, crypto, region, SPEC, 0.5)
        normals = np.zeros((*shape, 3), dtype=np.float32)
        normals[..., 2] = 1.0
        normal_result, normal_map = ANALYZER.measure_normal(normals, normals, region, SPEC)
        vectors = np.zeros((*shape, 4), dtype=np.float32)
        vector_result, vector_map = ANALYZER.measure_vector(vectors, vectors, region, SPEC)
        self.assertTrue(crypto_result["classifierPassed"])
        self.assertTrue(normal_result["classifierPassed"])
        self.assertTrue(vector_result["classifierPassed"])
        self.assertTrue(np.array_equal(crypto_map, np.zeros(shape)))
        self.assertTrue(np.array_equal(normal_map, np.zeros(shape)))
        self.assertTrue(np.array_equal(vector_map, np.zeros(shape)))

    def test_diagnostic_png_and_sidecar_are_deterministic(self) -> None:
        values = np.arange(20, dtype=np.float64).reshape(4, 5) / 400.0
        mapping = SPEC["diagnostics"]["mappings"]["cryptomatte-maximum-alpha-error"]
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            left = ANALYZER.write_diagnostic(Path(first), "canonical/diagnostics", "TABLETOP_WIDE", "ADAPT_T015_M0", "cryptomatte-maximum-alpha-error", values, mapping, {"sha256": "a"}, {"sha256": "b"})
            right = ANALYZER.write_diagnostic(Path(second), "canonical/diagnostics", "TABLETOP_WIDE", "ADAPT_T015_M0", "cryptomatte-maximum-alpha-error", values, mapping, {"sha256": "a"}, {"sha256": "b"})
            self.assertEqual(left, right)
            self.assertEqual((Path(first) / "tabletop_wide--adapt_t015_m0--cryptomatte-maximum-alpha-error.png").read_bytes(), (Path(second) / "tabletop_wide--adapt_t015_m0--cryptomatte-maximum-alpha-error.png").read_bytes())


if __name__ == "__main__":
    unittest.main()
