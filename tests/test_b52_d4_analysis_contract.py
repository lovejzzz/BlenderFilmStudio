from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYZER = load(ROOT / "scripts/analyze-b52-d4-adaptive-vector-blur-semantics.py", "b52_d4_analyzer")
COMMON = load(ROOT / "scripts/analyze-b52-native-cpu-adaptive-quality-cost.py", "b52_d4_common")
SPEC = json.loads((ROOT / "specs/adaptive-vector-blur-semantics-derivation.v0.1.json").read_text(encoding="utf-8"))


def valid_evidence(classifier: bool = True) -> dict:
    profiles = [SPEC["inputs"]["baselineProfile"], *SPEC["inputs"]["candidateProfiles"]]
    runs = []
    outputs = []
    pid = 1000
    for profile, variant, repeat in ANALYZER.expected_cell_keys(SPEC):
        runs.append({
            "cellId": f"{variant}_{profile}_C{repeat}", "profileId": profile, "variantId": variant, "repeat": repeat, "pid": pid, "exitCode": 0,
            "reportHashMatch": True, "rnaMatch": True, "rnaInputs": ANALYZER.EXPECTED_VECTOR_BLUR_INPUTS,
            "graphMatch": True, "graphLinks": ANALYZER.EXPECTED_LINKS, "graphNodeCount": 4, "inputIsolationMatch": True,
        })
        outputs.append({"identityMatch": True, "shape": [288, 512, 4], "finite": True})
        pid += 1
    repeats = [{"profileId": profile, "variantId": variant, "decodedExact": True} for profile in profiles for variant in SPEC["inputs"]["variants"]]
    measurements = []
    for profile, variant in ANALYZER.expected_pair_keys(SPEC):
        measurements.append({
            "profileId": profile,
            "variantId": variant,
            "vectorInput": {"measurementTotal": True, "influenceRegionEnergyFraction": 1.0, "endpointErrorMaximum": 0.0},
            "blurOutput": {"measurementTotal": True, "classifierPassed": classifier, "rgbAbsoluteErrorMaximum": 0.0},
        })
    diagnostics = [
        {"profileId": profile, "variantId": variant, "kind": kind, "identityMatch": True}
        for profile in SPEC["diagnostics"]["profiles"]
        for variant in SPEC["inputs"]["variants"]
        for kind in SPEC["diagnostics"]["mapsPerPair"]
    ]
    evidence = {
        "schemaVersion": "test", "experimentId": "B52-D4", "specObservation": {"match": True},
        "parentObservations": [{"match": True} for _ in range(5)],
        "parentArtifactObservations": [{"match": True} for _ in range(54)],
        "runtimeObservations": {"blender": {"match": True}, "ocio": {"match": True}},
        "regions": [{"d3MaskIdentityMatch": True}, {"d3MaskIdentityMatch": True}],
        "influenceRegions": [{"radiusOverflow": False}, {"radiusOverflow": False}],
        "runObservations": runs, "outputObservations": outputs, "repeatComparisons": repeats,
        "baselineEffects": [{"passed": True}, {"passed": True}], "candidateMeasurements": measurements,
        "diagnostics": diagnostics, "sourcePostObservations": [{"match": True} for _ in range(18)],
        "operationCounts": SPEC["operationBoundary"],
    }
    evidence["profileSummaries"], evidence["vectorTaskTolerableProfiles"] = ANALYZER.replay_classification(evidence, SPEC)
    evidence["evidenceCoreHash"] = COMMON.canonical_hash(ANALYZER.hash_payload(evidence))
    return evidence


class B52D4ContractTests(unittest.TestCase):
    def test_valid_positive_and_all_attacks(self):
        evidence = valid_evidence(True)
        self.assertIsNone(ANALYZER.validate(evidence, SPEC, COMMON))
        attacks = ANALYZER.run_attacks(evidence, SPEC, COMMON)
        self.assertEqual(len(attacks), len(SPEC["attacks"]))
        self.assertTrue(all(item["passed"] for item in attacks), attacks)

    def test_no_tolerable_profile_is_still_valid(self):
        evidence = valid_evidence(False)
        self.assertEqual(evidence["vectorTaskTolerableProfiles"], [])
        self.assertIsNone(ANALYZER.validate(evidence, SPEC, COMMON))

    def test_classification_tampering_is_rejected(self):
        evidence = valid_evidence(True)
        evidence["profileSummaries"][0]["vectorTaskTolerable"] = False
        evidence["evidenceCoreHash"] = COMMON.canonical_hash(ANALYZER.hash_payload(evidence))
        self.assertEqual(ANALYZER.validate(evidence, SPEC, COMMON), "CLASSIFICATION_REPLAY")

    def test_vector_energy_measurement(self):
        baseline = np.zeros((2, 2, 4), dtype=np.float32)
        candidate = baseline.copy()
        candidate[0, 0, 0] = 0.5
        candidate[1, 1, 2] = 0.25
        influence = np.asarray([[True, False], [False, False]])
        stable = np.asarray([[False, False], [False, True]])
        measured, error = ANALYZER.measure_vector(baseline, candidate, influence, stable)
        self.assertTrue(measured["measurementTotal"])
        self.assertAlmostEqual(measured["totalSquaredEnergy"], 0.3125)
        self.assertAlmostEqual(measured["influenceRegionSquaredEnergy"], 0.25)
        self.assertAlmostEqual(measured["stableInteriorSquaredEnergy"], 0.0625)
        self.assertAlmostEqual(measured["influenceRegionEnergyFraction"], 0.8)
        self.assertEqual(float(error[0, 0]), 0.5)

    def test_blur_output_measurement_exact(self):
        baseline = np.zeros((2, 2, 4), dtype=np.float32)
        baseline[..., 3] = 1.0
        influence = np.ones((2, 2), dtype=bool)
        vector = {"influenceRegionEnergyFraction": 1.0}
        measured, error = ANALYZER.measure_blur(baseline, baseline.copy(), influence, vector, SPEC["blurOutputTask"]["derivationClassifier"])
        self.assertTrue(measured["measurementTotal"])
        self.assertTrue(measured["classifierPassed"])
        self.assertEqual(measured["rgbAbsoluteErrorMaximum"], 0.0)
        self.assertTrue(np.array_equal(error, np.zeros((2, 2))))

    def test_diagnostic_is_byte_deterministic(self):
        values = np.asarray([[0.0, 0.0001], [0.0002, 0.0003]], dtype=np.float32)
        mapping = SPEC["diagnostics"]["mappings"]["vector-endpoint-error"]
        sources = {"test": True}
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            a = ANALYZER.write_diagnostic(Path(left), "diagnostics", "TABLETOP_WIDE", "ADAPT_T015_M0", "vector-endpoint-error", values, mapping, sources)
            b = ANALYZER.write_diagnostic(Path(right), "diagnostics", "TABLETOP_WIDE", "ADAPT_T015_M0", "vector-endpoint-error", values, mapping, sources)
            self.assertEqual(a["png"]["sha256"], b["png"]["sha256"])
            self.assertEqual(a["sidecar"]["sha256"], b["sidecar"]["sha256"])


if __name__ == "__main__":
    unittest.main()
