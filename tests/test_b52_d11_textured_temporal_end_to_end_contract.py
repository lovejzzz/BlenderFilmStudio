#!/usr/bin/env python3
"""Zero-formal-output contract tests for B52-D11."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "specs/blender-real-textured-temporal-end-to-end-holdout.v0.1.json"
SPEC_SHA256 = "f1505c42426e8e286ee1584de3df12fb33b7db57518d6d91e1fd93aa3bed5a5f"
PYTHON_ACCUMULATOR = ROOT / "scripts/accumulate-b52-d11-temporal.py"
NODE_ACCUMULATOR = ROOT / "scripts/accumulate-b52-d11-temporal.mjs"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_python_accumulator():
    module_spec = importlib.util.spec_from_file_location("b52_d11_accumulator", PYTHON_ACCUMULATOR)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


class B52D11ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads(SPEC_PATH.read_text())
        cls.accumulator = load_python_accumulator()

    def test_spec_identity_and_formal_boundary(self) -> None:
        self.assertEqual(sha(SPEC_PATH), SPEC_SHA256)
        self.assertEqual(self.spec["experimentId"], "B52-D11")
        self.assertEqual(self.spec["scene"]["resolution"], [197, 113])
        self.assertEqual(len(self.spec["fixtures"]), 4)
        self.assertEqual(len(self.spec["formalToolPaths"]), 11)
        self.assertEqual(len(self.spec["attacks"]), 56)
        matrix = self.spec["processMatrix"]
        total = sum(
            matrix[key]
            for key in (
                "sourceBlenderProcesses",
                "adapterPythonProcesses",
                "pythonAccumulatorProcesses",
                "nodeAccumulatorProcesses",
                "resolvedExrEncoderProcesses",
                "bridgeBlenderProcesses",
                "analysisPythonProcesses",
            )
        )
        self.assertEqual(total, matrix["totalChildProcesses"])
        self.assertEqual(total, 65)

    def test_integerization_is_inherited_truncation(self) -> None:
        self.assertEqual(int(12.999996185302734), 12)
        self.assertEqual(int(-6.999996185302734), -6)
        self.assertEqual(self.accumulator.nearest_integer(12.999996185302734), 13)
        self.assertEqual(self.accumulator.nearest_integer(-6.999996185302734), -7)
        node = NODE_ACCUMULATOR.read_text()
        self.assertIn("Math.trunc", node)
        self.assertIn("nearestInteger", node)
        self.assertNotIn("reference-b52-d9", node)
        self.assertNotIn("reference-b52-d9", PYTHON_ACCUMULATOR.read_text())

    def test_scalar_accumulator_coordinate_and_float32_contract(self) -> None:
        arrays = {
            "previousRgba": [0.0, 0.0, 0.0, 1.0, 2.0, 4.0, 6.0, 1.0, 0.0, 0.0, 0.0, 1.0],
            "currentRgba": [9.0, 9.0, 9.0, 1.0, 8.0, 8.0, 8.0, 1.0, 10.0, 12.0, 14.0, 1.0],
            "previousDepth": [2.0, 2.0, 2.0],
            "currentDepth": [2.0, 2.0, 2.0],
            "previousLayer": [1.0, 1.0, 1.0],
            "currentLayer": [1.0, 1.0, 1.0],
            "motion": [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        }
        validity, reasons, resolved = self.accumulator.accumulate(arrays, 3, 1, int)
        self.assertEqual(list(validity), [1, 1, 1])
        self.assertEqual(list(reasons), [0, 0, 0])
        self.assertEqual(resolved[8:12], [6.0, 8.0, 10.0, 1.0])

    def test_reason_priority(self) -> None:
        base = {
            "previousRgba": [1.0, 1.0, 1.0, 1.0],
            "currentRgba": [2.0, 2.0, 2.0, 1.0],
            "previousDepth": [2.0],
            "currentDepth": [2.0],
            "previousLayer": [1.0],
            "currentLayer": [1.0],
            "motion": [2.0, 0.0],
        }
        _, reasons, _ = self.accumulator.accumulate(base, 1, 1, int)
        self.assertEqual(list(reasons), [self.accumulator.REASONS["INVALID_BOUNDS"]])
        base["motion"] = [0.0, 0.0]
        base["previousLayer"] = [9.0]
        base["previousDepth"] = [100.0]
        base["previousRgba"][3] = 0.0
        _, reasons, _ = self.accumulator.accumulate(base, 1, 1, int)
        self.assertEqual(list(reasons), [self.accumulator.REASONS["INVALID_LAYER"]])
        base["previousLayer"] = [1.0]
        _, reasons, _ = self.accumulator.accumulate(base, 1, 1, int)
        self.assertEqual(list(reasons), [self.accumulator.REASONS["INVALID_DEPTH"]])
        base["previousDepth"] = [2.0]
        _, reasons, _ = self.accumulator.accumulate(base, 1, 1, int)
        self.assertEqual(list(reasons), [self.accumulator.REASONS["INVALID_ALPHA"]])

    def test_bridge_and_adapter_contract_are_narrow(self) -> None:
        self.assertEqual(self.spec["rawExrBridge"]["blenderGraph"], ["BFS_D11_EXTERNAL_SOURCE.Image->BFS_D11_GROUP_OUTPUT.Socket_0"])
        self.assertEqual(self.spec["rawExrBridge"]["encoder"]["storage"], "FLOAT")
        self.assertEqual(self.spec["adapterContract"]["motion"], "raw float32 [-current Vector.X,-current Vector.Y]; no rounding, snapping, epsilon, clamping or quantization in the adapter")
        self.assertEqual(self.spec["motionIntegerizationGate"]["failureLabel"], "MOTION_INTEGERIZATION")


if __name__ == "__main__":
    unittest.main()
