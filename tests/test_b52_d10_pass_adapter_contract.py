#!/usr/bin/env python3
"""Contract tests for the frozen B52-D10 adapter holdout."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "specs/blender-multipart-temporal-adapter-holdout.v0.1.json"
SPEC_SHA = "147338ae39b9c025a8f2a4921da55b15f8c16f339f34c711502dc3c94ca03566"
ANALYZER_PATH = ROOT / "scripts/analyze-b52-d10-pass-adapter-holdout.py"


def load_analyzer():
    module_spec = importlib.util.spec_from_file_location("b52_d10_analyzer", ANALYZER_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


class B52D10ContractTests(unittest.TestCase):
    def test_spec_identity_and_formal_matrix(self) -> None:
        self.assertEqual(hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest(), SPEC_SHA)
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(spec["attacks"]), 34)
        self.assertEqual(spec["processMatrix"]["totalChildProcesses"], 19)
        self.assertEqual(spec["processMatrix"]["sourceBlenderProcesses"], 12)

    def test_independent_analytic_vectors_match_frozen_values(self) -> None:
        module = load_analyzer()
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        for fixture in spec["fixtures"]:
            name = "BFS_MOVER" if fixture["id"].startswith("HOLDOUT_OBJECT") else "BFS_BACKGROUND"
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

    def test_raster_orientation_markers_are_analytically_ordered(self) -> None:
        module = load_analyzer()
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        fixture = spec["fixtures"][2]
        objects = {item["name"]: item for item in spec["scene"]["objects"]}
        _, top_row = module.top_left_probe(spec, fixture, objects["BFS_TOP_MARKER"], 1)
        _, bottom_row = module.top_left_probe(spec, fixture, objects["BFS_BOTTOM_MARKER"], 1)
        self.assertLess(top_row, bottom_row)


if __name__ == "__main__":
    unittest.main()
