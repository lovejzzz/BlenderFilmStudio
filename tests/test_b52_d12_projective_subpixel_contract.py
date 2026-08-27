#!/usr/bin/env python3
"""Zero-formal-output contract tests for preregistered B52-D12 tools."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "specs/blender-projective-subpixel-reconstruction-holdout.v0.1.json"
SPEC_SHA256 = "dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2"
PYTHON_TOOL = ROOT / "scripts/reconstruct-b52-d12-subpixel.py"
NODE_TOOL = ROOT / "scripts/reconstruct-b52-d12-subpixel.mjs"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def load_python_tool():
    spec = importlib.util.spec_from_file_location("b52_d12_python_reconstructor", PYTHON_TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ProjectiveSubpixelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads(SPEC_PATH.read_text())
        cls.tool = load_python_tool()

    def test_01_spec_identity_and_pretool_contract(self) -> None:
        self.assertEqual(sha_bytes(SPEC_PATH.read_bytes()), SPEC_SHA256)
        self.assertEqual(len(self.spec["fixtures"]), 4)
        self.assertEqual(len(self.spec["attacks"]), 57)
        self.assertEqual(self.spec["processMatrix"]["totalChildProcesses"], 65)

    def test_02_rotation_identity(self) -> None:
        matrix = self.tool.rotation_xyz([0.0, 0.0, 0.0])
        self.assertEqual(matrix, ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (-0.0, 0.0, 1.0)))

    def test_03_static_oracle_is_zero_motion(self) -> None:
        fixture = next(item for item in self.spec["fixtures"] if item["id"] == "PROJECTIVE_STATIC_CONTROL_107X67")
        for x, y in ((4, 4), (53, 33), (102, 62)):
            vx, vy, current_depth, previous_depth = self.tool.oracle_pixel(fixture, self.spec["scene"], x, y)
            self.assertLessEqual(abs(vx), 1e-12)
            self.assertLessEqual(abs(vy), 1e-12)
            self.assertLessEqual(abs(current_depth - previous_depth), 1e-12)

    def test_04_moving_oracles_are_genuinely_fractional(self) -> None:
        for fixture in self.spec["fixtures"][:3]:
            values = []
            for x, y in ((9, 8), (27, 19), (53, 33), (79, 47), (97, 58)):
                values.extend(self.tool.oracle_pixel(fixture, self.spec["scene"], x, y)[:2])
            fraction = [abs(value - round(value)) for value in values]
            self.assertGreater(max(fraction), 0.05)

    def test_05_bilinear_tap_order_and_clip(self) -> None:
        image = np.asarray([[[0.0], [1.0]], [[2.0], [3.0]]], dtype="<f4")
        value, taps, valid = self.tool.bilinear(image, 0.25, 0.5)
        self.assertTrue(valid)
        self.assertEqual(taps, (0, 0, 1, 1))
        self.assertEqual(float(value[0]), 1.25)
        self.assertFalse(self.tool.bilinear(image, -0.1, 0.5)[2])

    def test_06_ties_to_even_nearest(self) -> None:
        self.assertEqual([self.tool.round_even(value) for value in (0.5, 1.5, 2.5, -0.5, -1.5)], [0, 2, 2, 0, -2])

    def test_07_direct_depth_identity_is_not_transform_depth(self) -> None:
        fixture = self.spec["fixtures"][0]
        _, _, current_depth, previous_depth = self.tool.oracle_pixel(fixture, self.spec["scene"], 53, 33)
        self.assertGreater(abs(previous_depth - current_depth), max(1.0, current_depth) / 1024.0)

    def test_08_python_node_static_cli_identity(self) -> None:
        fixture = self.spec["fixtures"][3]
        width, height = self.spec["scene"]["resolution"]
        pixels = width * height
        rgba = np.empty((height, width, 4), dtype="<f4")
        for y in range(height):
            for x in range(width):
                rgba[y, x] = (np.float32(x / width), np.float32(y / height), np.float32((x + y) / (width + height)), np.float32(1.0))
        depth = np.empty((height, width), dtype="<f4")
        vector = np.empty((height, width, 2), dtype="<f4")
        for y in range(height):
            for x in range(width):
                vx, vy, current_depth, _ = self.tool.oracle_pixel(fixture, self.spec["scene"], x, y)
                vector[y, x] = (vx, vy)
                depth[y, x] = current_depth
        owner = np.full((height, width), np.float32(fixture["passIndex"]), dtype="<f4")
        arrays = {
            "previousRgba": ("previous.rgba32", rgba), "currentRgba": ("current.rgba32", rgba),
            "previousDepth": ("previous-depth.f32", depth), "currentDepth": ("current-depth.f32", depth),
            "previousOwner": ("previous-owner.f32", owner), "currentOwner": ("current-owner.f32", owner),
            "vector": ("vector.xy32", vector), "vectorNext": ("vector-next.xy32", vector),
        }
        with tempfile.TemporaryDirectory(prefix="bfs-d12-contract-") as temp_text:
            temp = Path(temp_text)
            input_dir = temp / "input"
            input_dir.mkdir()
            records = {}
            for name, (filename, array) in arrays.items():
                payload = np.ascontiguousarray(array, dtype="<f4").tobytes()
                path = input_dir / filename
                path.write_bytes(payload)
                records[name] = {"uri": str(path), "sha256": sha_bytes(payload), "bytes": len(payload), "shape": list(array.shape), "dtype": "little-endian-float32"}
            adapter_body = {
                "schemaVersion": "bfs.blenderProjectiveSubpixelAdapterReport.v0.1", "experimentId": "B52-D12",
                "fixtureId": fixture["id"], "repeat": 1, "pid": 1, "runtime": {}, "inputs": {}, "multipart": {}, "transform": {},
                "arrays": records, "operationCounts": {"adapterProcesses": 1},
            }
            adapter = {**adapter_body, "reportHash": canonical_hash(adapter_body)}
            adapter_path = temp / "adapter.report.json"
            adapter_path.write_text(json.dumps(adapter, indent=2, sort_keys=True) + "\n")
            python_dir, node_dir = temp / "python", temp / "node"
            python_report, node_report = temp / "python.report.json", temp / "node.report.json"
            common = ["--spec", str(SPEC_PATH), "--fixture", fixture["id"], "--repeat", "1", "--input-dir", str(input_dir), "--adapter-report", str(adapter_path)]
            subprocess.run([sys.executable, str(PYTHON_TOOL), *common, "--output-dir", str(python_dir), "--report", str(python_report)], cwd=ROOT, check=True, capture_output=True, text=True)
            subprocess.run([self.spec["runtime"]["node"]["executable"], str(NODE_TOOL), *common, "--output-dir", str(node_dir), "--report", str(node_report)], cwd=ROOT, check=True, capture_output=True, text=True)
            for filename, _channels, _dtype in self.tool.OUTPUTS.values():
                self.assertEqual((python_dir / filename).read_bytes(), (node_dir / filename).read_bytes(), filename)
            python_payload, node_payload = json.loads(python_report.read_text()), json.loads(node_report.read_text())
            self.assertGreaterEqual(python_payload["measurements"]["validPixels"], 4000)
            self.assertEqual(python_payload["measurements"]["correct"]["maximum"], 0.0)
            self.assertEqual(node_payload["measurements"]["correct"]["maximum"], 0.0)

    def test_09_formal_roots_absent(self) -> None:
        self.assertFalse((ROOT / self.spec["formalOutputRoot"]).exists())
        self.assertFalse((ROOT / self.spec["preflightOutputRoot"]).exists())

    def test_10_analyzer_import_boundary_is_declared(self) -> None:
        self.assertIn("without bpy", self.spec["projectionOracle"]["implementationIndependence"])
        self.assertIn("tested reconstructor imports", self.spec["projectionOracle"]["implementationIndependence"])

    def test_11_disk_reserve_is_100_gib(self) -> None:
        self.assertEqual(self.spec["diskReserveBytes"], 100 * 1024**3)
        self.assertEqual(self.spec["projectedWriteBytes"], 64 * 1024**2)


if __name__ == "__main__":
    unittest.main()
