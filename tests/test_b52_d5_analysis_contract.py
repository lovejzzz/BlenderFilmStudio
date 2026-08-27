from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path, name: str):
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


ANALYZER = load(ROOT / "scripts/analyze-b52-d5-controlled-motion-calibration.py", "b52_d5_analyzer")
SPEC = json.loads((ROOT / "specs/controlled-motion-vector-blur-calibration.v0.1.json").read_text(encoding="utf-8"))


class B52D5ContractTests(unittest.TestCase):
    def test_synthetic_positive_and_all_twenty_attacks(self):
        evidence = ANALYZER.synthetic_valid_evidence(SPEC)
        self.assertIsNone(ANALYZER.validate(evidence, SPEC))
        attacks = ANALYZER.run_attacks(evidence, SPEC)
        self.assertEqual(len(attacks), 20)
        self.assertEqual([item["expectedReason"] for item in attacks], SPEC["attacks"])
        self.assertTrue(all(item["passed"] for item in attacks), attacks)
        self.assertTrue(all(item["base"] == "SYNTHETIC_VALID_CONTRACT" for item in attacks))

    def test_real_failure_is_not_masked_by_attack_base(self):
        evidence = ANALYZER.synthetic_valid_evidence(SPEC)
        evidence["fixtureMeasurements"][0]["vectorMagnitudePixels"]["maximum"] = 0.0
        evidence["fixtureClassifications"] = ANALYZER.replay_classification(evidence, SPEC)
        evidence["evidenceCoreHash"] = ANALYZER.canonical_hash(ANALYZER.hash_payload(evidence))
        self.assertEqual(ANALYZER.validate(evidence, SPEC), "MOVING_TASK_SENSITIVITY")
        attacks = ANALYZER.run_attacks(evidence, SPEC)
        self.assertTrue(all(item["passed"] for item in attacks), attacks)

    def test_shutter_zero_dose_and_static_route_independently(self):
        zero = ANALYZER.synthetic_valid_evidence(SPEC)
        zero_effect = zero["fixtureMeasurements"][0]["shutterEffects"][0]
        zero_effect["rgbAbsoluteError"]["maximum"] = 0.1
        zero_effect["changedPixelsAbove1Over65536"] = 1
        zero["fixtureClassifications"] = ANALYZER.replay_classification(zero, SPEC)
        zero["evidenceCoreHash"] = ANALYZER.canonical_hash(ANALYZER.hash_payload(zero))
        self.assertEqual(ANALYZER.validate(zero, SPEC), "SHUTTER_ZERO_IDENTITY")

        dose = ANALYZER.synthetic_valid_evidence(SPEC)
        dose["fixtureMeasurements"][0]["shutterEffects"][3]["rgbAbsoluteError"]["rmse"] = 0.05
        dose["fixtureClassifications"] = ANALYZER.replay_classification(dose, SPEC)
        dose["evidenceCoreHash"] = ANALYZER.canonical_hash(ANALYZER.hash_payload(dose))
        self.assertEqual(ANALYZER.validate(dose, SPEC), "DOSE_RESPONSE")

        static = ANALYZER.synthetic_valid_evidence(SPEC)
        static["fixtureMeasurements"][2]["vectorMagnitudePixels"]["maximum"] = 1.0
        static["fixtureClassifications"] = ANALYZER.replay_classification(static, SPEC)
        static["evidenceCoreHash"] = ANALYZER.canonical_hash(ANALYZER.hash_payload(static))
        self.assertEqual(ANALYZER.validate(static, SPEC), "STATIC_NEGATIVE_CONTROL")

    def test_measure_fixture_is_strict_json_serializable(self):
        combined = np.zeros((2, 3, 4), dtype=np.float32)
        combined[..., 3] = 1.0
        vector = np.zeros((2, 3, 4), dtype=np.float32)
        vector[0, 0, 0] = 16.0
        source = {"parts": {"BFS_MASTER.Combined": combined, "BFS_MASTER.Vector": vector}}
        outputs = {}
        for shutter, value in ((0.0, 0.0), (0.25, 0.1), (0.5, 0.2), (1.0, 0.4)):
            output = combined.copy()
            output[..., 0] += value
            outputs[shutter] = output
        measured, maps = ANALYZER.measure_fixture(source, outputs, "OBJECT_OCCLUSION_X")
        json.dumps(measured, allow_nan=False)
        self.assertEqual(measured["vectorMagnitudePixels"]["maximum"], 16.0)
        self.assertEqual(maps["shutter-0p5-rgb-maximum-absolute-error"].shape, (2, 3))
        self.assertIs(type(measured["vectorMagnitudePixels"]["finite"]), bool)

    def test_both_diagnostic_encodings_are_byte_deterministic(self):
        combined = np.asarray([[[0.0, 0.25, 1.0, 1.0], [2.0, 0.5, 0.0, 1.0]]], dtype=np.float32)
        scalar = np.asarray([[0.0, 32.0]], dtype=np.float32)
        sources = {"test": True}
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            for kind, values in (("combined", combined), ("vector-magnitude", scalar)):
                mapping = SPEC["diagnostics"]["mappings"][kind]
                a = ANALYZER.write_diagnostic(Path(left), "diagnostics", "OBJECT_OCCLUSION_X", kind, values, mapping, sources)
                b = ANALYZER.write_diagnostic(Path(right), "diagnostics", "OBJECT_OCCLUSION_X", kind, values, mapping, sources)
                self.assertEqual(a["png"]["sha256"], b["png"]["sha256"])
                self.assertEqual(a["sidecar"]["sha256"], b["sidecar"]["sha256"])


if __name__ == "__main__":
    unittest.main()
