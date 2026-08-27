#!/usr/bin/env python3
"""Registered missing-parent regression for the B52-D12-C1 Node correction."""

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
CORRECTION_PATH = ROOT / "specs/blender-projective-subpixel-reconstruction-node-parent-correction.v0.1.json"
PYTHON_TOOL = ROOT / "scripts/reconstruct-b52-d12-subpixel.py"
NODE_C1_TOOL = ROOT / "scripts/reconstruct-b52-d12-subpixel-c1.mjs"
CORRECTION_SHA256 = "f540b6a2ee0bb7b2e149c795b89adbc5ab24355750f73392f21ca65c40020a79"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def load_python_tool():
    module_spec = importlib.util.spec_from_file_location("b52_d12_c1_python_reference", PYTHON_TOOL)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


class NodeMissingParentCorrectionTests(unittest.TestCase):
    def test_node_materializes_absent_cell_parent_and_matches_python(self) -> None:
        self.assertEqual(sha_bytes(CORRECTION_PATH.read_bytes()), CORRECTION_SHA256)
        spec = json.loads(SPEC_PATH.read_text())
        correction = json.loads(CORRECTION_PATH.read_text())
        tool = load_python_tool()
        fixture = spec["fixtures"][3]
        width, height = spec["scene"]["resolution"]

        rgba = np.empty((height, width, 4), dtype="<f4")
        depth = np.empty((height, width), dtype="<f4")
        vector = np.empty((height, width, 2), dtype="<f4")
        for y in range(height):
            for x in range(width):
                rgba[y, x] = (
                    np.float32(x / width),
                    np.float32(y / height),
                    np.float32((x + y) / (width + height)),
                    np.float32(1.0),
                )
                vx, vy, current_depth, _ = tool.oracle_pixel(fixture, spec["scene"], x, y)
                vector[y, x] = (vx, vy)
                depth[y, x] = current_depth
        owner = np.full((height, width), np.float32(fixture["passIndex"]), dtype="<f4")
        arrays = {
            "previousRgba": ("previous.rgba32", rgba),
            "currentRgba": ("current.rgba32", rgba),
            "previousDepth": ("previous-depth.f32", depth),
            "currentDepth": ("current-depth.f32", depth),
            "previousOwner": ("previous-owner.f32", owner),
            "currentOwner": ("current-owner.f32", owner),
            "vector": ("vector.xy32", vector),
            "vectorNext": ("vector-next.xy32", vector),
        }

        with tempfile.TemporaryDirectory(prefix="bfs-d12-c1-parent-contract-") as temp_text:
            temp = Path(temp_text)
            input_dir = temp / "input"
            input_dir.mkdir()
            records = {}
            for name, (filename, array) in arrays.items():
                payload = np.ascontiguousarray(array, dtype="<f4").tobytes()
                path = input_dir / filename
                path.write_bytes(payload)
                records[name] = {
                    "uri": str(path),
                    "sha256": sha_bytes(payload),
                    "bytes": len(payload),
                    "shape": list(array.shape),
                    "dtype": "little-endian-float32",
                }
            adapter_body = {
                "schemaVersion": "bfs.blenderProjectiveSubpixelAdapterReport.v0.1",
                "experimentId": "B52-D12",
                "fixtureId": fixture["id"],
                "repeat": 1,
                "pid": 1,
                "runtime": {},
                "inputs": {},
                "multipart": {},
                "transform": {},
                "arrays": records,
                "operationCounts": {"adapterProcesses": 1},
            }
            adapter = {**adapter_body, "reportHash": canonical_hash(adapter_body)}
            adapter_path = temp / "adapter.report.json"
            adapter_path.write_text(json.dumps(adapter, indent=2, sort_keys=True) + "\n")

            python_arrays = temp / "python-cell" / "arrays"
            node_arrays = temp / "node-cell" / "arrays"
            python_report = temp / "python-cell" / "report.json"
            node_report = temp / "node-cell" / "report.json"
            self.assertFalse(python_arrays.parent.exists())
            self.assertFalse(node_arrays.parent.exists())
            common = [
                "--spec", str(SPEC_PATH), "--fixture", fixture["id"], "--repeat", "1",
                "--input-dir", str(input_dir), "--adapter-report", str(adapter_path),
            ]
            python_run = subprocess.run(
                [sys.executable, str(PYTHON_TOOL), *common, "--output-dir", str(python_arrays), "--report", str(python_report)],
                cwd=ROOT, check=False, capture_output=True, text=True,
            )
            node_run = subprocess.run(
                [spec["runtime"]["node"]["executable"], str(NODE_C1_TOOL), *common, "--output-dir", str(node_arrays), "--report", str(node_report)],
                cwd=ROOT, check=False, capture_output=True, text=True,
            )
            self.assertEqual(python_run.returncode, 0, python_run.stderr)
            self.assertEqual(node_run.returncode, 0, node_run.stderr)
            self.assertTrue(node_arrays.parent.is_dir())
            self.assertTrue(node_arrays.is_dir())
            self.assertTrue(node_report.is_file())
            for filename, _channels, _dtype in tool.OUTPUTS.values():
                self.assertEqual((python_arrays / filename).read_bytes(), (node_arrays / filename).read_bytes(), filename)

            node_payload = json.loads(node_report.read_text())
            self.assertEqual(node_payload["producer"], "node")
            self.assertGreaterEqual(node_payload["measurements"]["validPixels"], 4000)
            self.assertEqual(correction["execution"]["processMatrix"]["nodeReconstructorProcesses"], 8)


if __name__ == "__main__":
    unittest.main()
