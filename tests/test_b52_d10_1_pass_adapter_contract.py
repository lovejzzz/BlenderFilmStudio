#!/usr/bin/env python3
"""Contract tests for the frozen B52-D10.1 adapter holdout."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "specs/blender-multipart-temporal-adapter-f32-holdout.v0.1.json"
SPEC_SHA = "11686c5e796c7bc1b4e45cf137c3d98347bc65bfec428f9d19545b55430f584b"
ANALYZER_PATH = ROOT / "scripts/analyze-b52-d10-1-pass-adapter-f32-holdout.py"


def load_analyzer():
    module_spec = importlib.util.spec_from_file_location("b52_d10_1_analyzer", ANALYZER_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


class B52D10_1ContractTests(unittest.TestCase):
    def test_spec_identity_and_formal_matrix(self) -> None:
        self.assertEqual(hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest(), SPEC_SHA)
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(spec["attacks"]), 37)
        self.assertEqual(spec["processMatrix"]["totalChildProcesses"], 19)
        self.assertEqual(spec["processMatrix"]["sourceBlenderProcesses"], 12)

    def test_independent_analytic_vectors_match_frozen_values(self) -> None:
        module = load_analyzer()
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        for fixture in spec["fixtures"]:
            name = "BFS_F32_MOVER" if fixture["id"].startswith("F32_OBJECT") else "BFS_F32_BACKGROUND"
            xy, zw = module.expected_vectors(spec, fixture, name)
            self.assertTrue(np.array_equal(xy, np.asarray(fixture["expectedVectorXY"], dtype=np.float64)))
            self.assertTrue(np.array_equal(zw, np.asarray(fixture["expectedVectorZW"], dtype=np.float64)))
            self.assertTrue(np.array_equal(-xy, np.asarray(fixture["expectedD9Motion"], dtype=np.float64)))

    def test_classifier_rejects_every_named_attack(self) -> None:
        module = load_analyzer()
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        valid = {name: True for name in spec["attacks"]}
        self.assertIsNone(module.classify(valid, spec["attacks"]))
        for name in spec["attacks"]:
            attacked = dict(valid)
            attacked[name] = False
            self.assertEqual(module.classify(attacked, spec["attacks"]), name)

    def test_static_gate_preserves_d5_counterexample(self) -> None:
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        d5_residual = 2.6702880859375e-5
        self.assertLess(d5_residual, spec["measurementGates"]["staticVectorPairMagnitudeP99MaximumPixels"])
        self.assertLess(d5_residual, spec["measurementGates"]["staticVectorPairMagnitudeAbsoluteMaximumPixels"])

    def test_typed_float32_structure_is_exact_and_not_decimal_rounded(self) -> None:
        module = load_analyzer()
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        fixture = spec["fixtures"][0]
        expected = module.expected_scene_structure(spec, fixture, 1, 1)
        raw = module.expected_scene_structure(spec, fixture, 1, 1, canonicalize=False)
        self.assertEqual(expected["camera"]["orthoScale"], module.float32_roundtrip(18.1))
        self.assertNotEqual(expected["camera"]["orthoScale"], raw["camera"]["orthoScale"])
        self.assertNotEqual(expected["objects"], raw["objects"])

    def test_one_ulp_and_nonfloat_structure_attacks_are_detectable(self) -> None:
        module = load_analyzer()
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        fixture = spec["fixtures"][0]
        expected = module.expected_scene_structure(spec, fixture, 1, 1)
        adjacent = module.next_float32_toward_positive_infinity(expected["camera"]["orthoScale"])
        self.assertNotEqual(adjacent, expected["camera"]["orthoScale"])
        mutated = json.loads(json.dumps(expected))
        mutated["objects"][0]["passIndex"] += 1
        self.assertNotEqual(mutated, expected)

    def test_raster_orientation_markers_are_analytically_ordered(self) -> None:
        module = load_analyzer()
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        fixture = spec["fixtures"][2]
        objects = {item["name"]: item for item in spec["scene"]["objects"]}
        _, top_row = module.top_left_probe(spec, fixture, objects["BFS_F32_TOP"], 1)
        _, bottom_row = module.top_left_probe(spec, fixture, objects["BFS_F32_BOTTOM"], 1)
        self.assertLess(top_row, bottom_row)


if __name__ == "__main__":
    unittest.main()
