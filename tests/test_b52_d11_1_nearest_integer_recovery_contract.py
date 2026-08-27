#!/usr/bin/env python3
"""Zero-formal-output contract tests for B52-D11.1."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "specs/blender-nearest-integer-temporal-recovery-holdout.v0.1.json"
SPEC_SHA256 = "c4cb343672f53660d7c4ab69ccd489e00bb211e4aa1f489429f7a626ee48c42a"
PYTHON_QUANTIZER = ROOT / "scripts/quantize-b52-d11-1-motion.py"
NODE_QUANTIZER = ROOT / "scripts/quantize-b52-d11-1-motion.mjs"
PYTHON_ACCUMULATOR = ROOT / "scripts/accumulate-b52-d11-1-temporal.py"
NODE_ACCUMULATOR = ROOT / "scripts/accumulate-b52-d11-1-temporal.mjs"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def load_module(name: str, source: Path):
    module_spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


def f32_from_bits(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def f32_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


class B52D111ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads(SPEC_PATH.read_text())
        cls.quantizer = load_module("b52_d11_1_quantizer", PYTHON_QUANTIZER)
        cls.accumulator = load_module("b52_d11_1_accumulator", PYTHON_ACCUMULATOR)

    def test_spec_identity_and_formal_boundary(self) -> None:
        self.assertEqual(sha(SPEC_PATH), SPEC_SHA256)
        self.assertEqual(self.spec["experimentId"], "B52-D11.1")
        self.assertEqual(self.spec["scene"]["resolution"], [199, 109])
        self.assertEqual(len(self.spec["fixtures"]), 4)
        self.assertEqual(len(self.spec["formalToolPaths"]), 13)
        self.assertEqual(len(self.spec["attacks"]), 71)
        self.assertEqual(self.spec["processMatrix"]["totalChildProcesses"], 81)

    def test_radius_is_inclusive_and_just_outside_rejects(self) -> None:
        radius = self.spec["quantizerContract"]["acceptanceRadiusPixels"]
        accepted = struct.pack("<4f", 5.0 + radius, -5.0 - radius, 7.0 - radius, -7.0 + radius)
        encoded, maximum = self.quantizer.quantize(accepted, radius)
        self.assertEqual(struct.unpack("<4f", encoded), (5.0, -5.0, 7.0, -7.0))
        self.assertEqual(maximum, radius)
        outside = f32_from_bits(f32_bits(5.0 + radius) + 1)
        with self.assertRaisesRegex(RuntimeError, "QUANTIZER_DOMAIN"):
            self.quantizer.quantize(struct.pack("<f", outside), radius)

    def test_half_integer_adjacent_and_nonfinite_are_rejected(self) -> None:
        radius = self.spec["quantizerContract"]["acceptanceRadiusPixels"]
        half_bits = f32_bits(2.5)
        for value in (2.5, f32_from_bits(half_bits - 1), f32_from_bits(half_bits + 1), math.inf, -math.inf, math.nan):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, "QUANTIZER_DOMAIN"):
                    self.quantizer.quantize(struct.pack("<f", value), radius)

    def test_signed_zero_is_canonical_and_quantization_is_idempotent(self) -> None:
        radius = self.spec["quantizerContract"]["acceptanceRadiusPixels"]
        encoded, _ = self.quantizer.quantize(struct.pack("<4f", -0.0, 0.0, -radius, radius), radius)
        self.assertEqual(encoded, b"\x00\x00\x00\x00" * 4)
        encoded_again, _ = self.quantizer.quantize(encoded, radius)
        self.assertEqual(encoded_again, encoded)

    def test_nearest_rule_detects_trunc_floor_and_ceil_substitutions(self) -> None:
        radius = self.spec["quantizerContract"]["acceptanceRadiusPixels"]
        values = (12.999996185302734, -6.999996185302734)
        encoded, _ = self.quantizer.quantize(struct.pack("<2f", *values), radius)
        self.assertEqual(struct.unpack("<2f", encoded), (13.0, -7.0))
        self.assertNotEqual(tuple(int(value) for value in values), (13, -7))
        self.assertNotEqual(tuple(math.floor(value) for value in values), (13, -7))
        self.assertNotEqual(tuple(math.ceil(value) for value in values), (13, -7))

    def test_python_node_cli_byte_identity_and_report_binding(self) -> None:
        width, height = self.spec["scene"]["resolution"]
        pattern = (12.999996185302734, -6.999996185302734, -0.0, 0.0)
        values = [pattern[index % len(pattern)] for index in range(width * height * 2)]
        with tempfile.TemporaryDirectory(prefix="bfs-d11-1-quantizer-test-") as temporary:
            root = Path(temporary)
            input_file = root / "motion.xy32"
            input_file.write_bytes(struct.pack(f"<{len(values)}f", *values))
            adapter_body = {"experimentId": self.spec["experimentId"], "fixtureId": self.spec["fixtures"][0]["id"], "repeat": 1, "arrays": {"motion": {"sha256": sha(input_file)}}}
            adapter_report = root / "adapter.report.json"
            adapter_report.write_text(json.dumps({**adapter_body, "reportHash": canonical_hash(adapter_body)}))
            outputs = {}
            for producer, executable, tool in (("python", self.spec["runtime"]["python"]["executable"], PYTHON_QUANTIZER), ("node", self.spec["runtime"]["node"]["executable"], NODE_QUANTIZER)):
                output, report = root / producer / "motion-quantized.xy32", root / producer / "quantizer.report.json"
                argv = [executable, str(tool), "--spec", str(SPEC_PATH), "--fixture", adapter_body["fixtureId"], "--repeat", "1", "--input", str(input_file), "--adapter-report", str(adapter_report), "--output", str(output), "--report", str(report)]
                completed = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                payload = json.loads(report.read_text())
                body = {key: value for key, value in payload.items() if key != "reportHash"}
                self.assertEqual(payload["reportHash"], canonical_hash(body), producer)
                self.assertEqual(payload["input"]["sha256"], sha(input_file))
                self.assertEqual(payload["output"]["sha256"], sha(output))
                outputs[producer] = output.read_bytes()
            self.assertEqual(outputs["python"], outputs["node"])

    def test_atomic_rejection_produces_no_output_or_report(self) -> None:
        width, height = self.spec["scene"]["resolution"]
        values = [0.0] * (width * height * 2)
        values[-1] = 0.25
        with tempfile.TemporaryDirectory(prefix="bfs-d11-1-reject-test-") as temporary:
            root = Path(temporary)
            input_file = root / "motion.xy32"
            input_file.write_bytes(struct.pack(f"<{len(values)}f", *values))
            adapter_body = {"fixtureId": self.spec["fixtures"][0]["id"], "repeat": 1, "arrays": {"motion": {"sha256": sha(input_file)}}}
            adapter_report = root / "adapter.report.json"
            adapter_report.write_text(json.dumps({**adapter_body, "reportHash": canonical_hash(adapter_body)}))
            for producer, executable, tool in (("python", self.spec["runtime"]["python"]["executable"], PYTHON_QUANTIZER), ("node", self.spec["runtime"]["node"]["executable"], NODE_QUANTIZER)):
                output, report = root / producer / "motion-quantized.xy32", root / producer / "quantizer.report.json"
                argv = [executable, str(tool), "--spec", str(SPEC_PATH), "--fixture", adapter_body["fixtureId"], "--repeat", "1", "--input", str(input_file), "--adapter-report", str(adapter_report), "--output", str(output), "--report", str(report)]
                completed = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False)
                self.assertNotEqual(completed.returncode, 0)
                self.assertFalse(output.exists())
                self.assertFalse(report.exists())

    def test_accumulator_retains_toward_zero_identity(self) -> None:
        source, node = PYTHON_ACCUMULATOR.read_text(), NODE_ACCUMULATOR.read_text()
        self.assertIn("accumulate(arrays, width, height, int)", source)
        self.assertIn("accumulate(arrays, width, height, Math.trunc)", node)
        self.assertNotIn("nearest_integer", source)
        self.assertNotIn("nearestInteger", node)
        arrays = {"previousRgba": [0.0, 0.0, 0.0, 1.0, 2.0, 4.0, 6.0, 1.0, 0.0, 0.0, 0.0, 1.0], "currentRgba": [9.0, 9.0, 9.0, 1.0, 8.0, 8.0, 8.0, 1.0, 10.0, 12.0, 14.0, 1.0], "previousDepth": [2.0, 2.0, 2.0], "currentDepth": [2.0, 2.0, 2.0], "previousLayer": [1.0, 1.0, 1.0], "currentLayer": [1.0, 1.0, 1.0], "motion": [0.0, 0.0, 0.0, 0.0, 1.0, 0.0]}
        validity, reasons, resolved = self.accumulator.accumulate(arrays, 3, 1, int)
        self.assertEqual(list(validity), [1, 1, 1])
        self.assertEqual(list(reasons), [0, 0, 0])
        self.assertEqual(resolved[8:12], [6.0, 8.0, 10.0, 1.0])

    def test_reason_priority_and_bridge_contract(self) -> None:
        base = {"previousRgba": [1.0, 1.0, 1.0, 0.0], "currentRgba": [2.0, 2.0, 2.0, 1.0], "previousDepth": [100.0], "currentDepth": [2.0], "previousLayer": [9.0], "currentLayer": [1.0], "motion": [2.0, 0.0]}
        _, reasons, _ = self.accumulator.accumulate(base, 1, 1, int)
        self.assertEqual(list(reasons), [self.accumulator.REASONS["INVALID_BOUNDS"]])
        base["motion"] = [0.0, 0.0]
        _, reasons, _ = self.accumulator.accumulate(base, 1, 1, int)
        self.assertEqual(list(reasons), [self.accumulator.REASONS["INVALID_LAYER"]])
        base["previousLayer"] = [1.0]
        _, reasons, _ = self.accumulator.accumulate(base, 1, 1, int)
        self.assertEqual(list(reasons), [self.accumulator.REASONS["INVALID_DEPTH"]])
        base["previousDepth"] = [2.0]
        _, reasons, _ = self.accumulator.accumulate(base, 1, 1, int)
        self.assertEqual(list(reasons), [self.accumulator.REASONS["INVALID_ALPHA"]])
        self.assertEqual(self.spec["rawExrBridge"]["blenderGraph"], ["BFS_D111_EXTERNAL_SOURCE.Image->BFS_D111_GROUP_OUTPUT.Socket_0"])

    def test_analyzer_independence_and_frozen_totals(self) -> None:
        analyzer_path = ROOT / "scripts/analyze-b52-d11-1-nearest-integer-recovery.py"
        source = analyzer_path.read_text()
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertTrue(imported.isdisjoint({"bpy", "bpy_extras", "mathutils"}))
        self.assertNotIn("quantize-b52-d11-1-motion", source)
        self.assertNotIn("accumulate-b52-d11-1-temporal", source)
        self.assertIn("def independent_quantize", source)
        self.assertIn("def independent_accumulate", source)
        self.assertEqual(self.spec["diagnostics"]["expectedPngs"], 48)
        self.assertEqual(self.spec["diagnostics"]["expectedSidecars"], 48)
        self.assertEqual(self.spec["processMatrix"]["totalBlenderProcesses"], 32)


if __name__ == "__main__":
    unittest.main()
