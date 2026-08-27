#!/usr/bin/env python3
"""Synthetic contract tests for B52-D6 before formal Blender output exists."""

from __future__ import annotations

import importlib.util
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from b52_d6_reference import SPEC_SHA256, array_hash, displacement_array, reference_warp, sha256_file, source_array  # noqa: E402


ANALYZER_SPEC = importlib.util.spec_from_file_location("b52_d6_analyzer", SCRIPTS / "analyze-b52-d6-deterministic-displace-calibration.py")
ANALYZER = importlib.util.module_from_spec(ANALYZER_SPEC)
assert ANALYZER_SPEC.loader is not None
ANALYZER_SPEC.loader.exec_module(ANALYZER)


class B52D6ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec_path = ROOT / "specs/deterministic-displace-calibration.v0.1.json"
        cls.spec = json.loads(cls.spec_path.read_text(encoding="utf-8"))

    def test_preregistration_identity_and_roster(self) -> None:
        self.assertEqual(sha256_file(self.spec_path), SPEC_SHA256)
        self.assertEqual(len(self.spec["fixtures"]), 7)
        self.assertEqual(self.spec["blenderMatrix"]["expectedProcesses"], 14)
        self.assertFalse((ROOT / self.spec["formalOutputRoot"]).exists())

    def test_zero_reference_is_source_exact(self) -> None:
        source = source_array(self.spec)
        fixture = self.spec["fixtures"][0]
        output = reference_warp(source, displacement_array(self.spec, fixture["id"]), fixture)
        self.assertEqual(array_hash(output), array_hash(source))
        self.assertTrue(np.array_equal(output, source))

    def test_destination_coordinate_signs(self) -> None:
        source = np.arange(5 * 6 * 4, dtype=np.float32).reshape(5, 6, 4)
        displacement = np.zeros((5, 6, 2), dtype=np.float32)
        displacement[..., 0] = 1.0
        displacement[..., 1] = -1.0
        fixture = {"interpolation": "Nearest", "extensionX": "Clip", "extensionY": "Clip"}
        output = reference_warp(source, displacement, fixture)
        self.assertTrue(np.array_equal(output[3, 4], source[2, 3]))
        self.assertTrue(np.array_equal(output[0], np.zeros_like(output[0])))
        self.assertTrue(np.array_equal(output[:, 0], np.zeros_like(output[:, 0])))

    def test_binary_exact_bilinear(self) -> None:
        source = np.arange(5 * 6 * 4, dtype=np.float32).reshape(5, 6, 4) / np.float32(128.0)
        displacement = np.zeros((5, 6, 2), dtype=np.float32)
        displacement[..., 0] = 0.5
        displacement[..., 1] = -0.25
        fixture = {"interpolation": "Bilinear", "extensionX": "Clip", "extensionY": "Clip"}
        output = reference_warp(source, displacement, fixture)
        expected = source[1, 2] * np.float32(0.125) + source[1, 3] * np.float32(0.125) + source[2, 2] * np.float32(0.375) + source[2, 3] * np.float32(0.375)
        self.assertTrue(np.array_equal(output[2, 3], expected))

    def test_repeat_and_extend_are_distinct(self) -> None:
        source = np.arange(3 * 4 * 4, dtype=np.float32).reshape(3, 4, 4)
        displacement = np.zeros((3, 4, 2), dtype=np.float32)
        displacement[..., 0] = 1.0
        repeat = reference_warp(source, displacement, {"interpolation": "Nearest", "extensionX": "Repeat", "extensionY": "Repeat"})
        extend = reference_warp(source, displacement, {"interpolation": "Nearest", "extensionX": "Extend", "extensionY": "Extend"})
        self.assertTrue(np.array_equal(repeat[:, 0], source[:, -1]))
        self.assertTrue(np.array_equal(extend[:, 0], source[:, 0]))
        self.assertFalse(np.array_equal(repeat, extend))

    def test_all_attacks_route_independently(self) -> None:
        attacks = ANALYZER.attack_contract(self.spec)
        self.assertEqual(len(attacks), 20)
        self.assertTrue(all(item["passed"] for item in attacks))
        self.assertIsNone(ANALYZER.first_failure(ANALYZER.synthetic_valid_evidence(self.spec), self.spec))

    def test_smoke_receipt_routes_subpixel_counterexample(self) -> None:
        runs = []
        smoke_root = ROOT / "experiments/deterministic-warp-preflight-v0-1/tool-smoke"
        for fixture_index, fixture in enumerate(self.spec["fixtures"]):
            report_path = smoke_root / fixture["id"] / "report.json"
            original = json.loads(report_path.read_text(encoding="utf-8"))
            for repeat in (1, 2):
                report = copy.deepcopy(original)
                report["repeat"] = repeat
                report["pid"] = 1000 + fixture_index * 2 + repeat
                report_body = {key: value for key, value in report.items() if key != "reportHash"}
                report["reportHash"] = ANALYZER.canonical_hash(report_body)
                runs.append({
                    "cellId": f"{fixture['id']}_R{repeat}",
                    "fixtureId": fixture["id"],
                    "repeat": repeat,
                    "pid": report["pid"],
                    "exitCode": 0,
                    "timedOut": False,
                    "reportUri": str(report_path.relative_to(ROOT)),
                    "report": report,
                })
        receipt = {
            "preregistration": {"commit": "SYNTHETIC", "specSha256": SPEC_SHA256},
            "toolFreezeCommit": "SYNTHETIC",
            "checks": {"parentIdentity": True, "runtimeBinaryIdentity": True, "ocioIdentity": True},
            "runs": runs,
        }
        with tempfile.TemporaryDirectory(prefix="bfs-b52-d6-contract-", dir=ROOT / "experiments") as temporary:
            output = Path(temporary) / "results.json"
            result = ANALYZER.analyze(self.spec, receipt, output, "0" * 64, ROOT)
        self.assertEqual(result["baseFailure"], "REFERENCE_MATCH")
        self.assertEqual(result["verdict"], self.spec["decision"]["failVerdict"])
        self.assertEqual(result["attacksPassed"], 20)
        subpixel = next(item for item in result["measurements"] if item["fixtureId"] == "SUBPIXEL_BILINEAR_CLIP")
        self.assertGreater(subpixel["maximumAbsoluteError"], 0.0)
        self.assertLess(subpixel["maximumAbsoluteError"], 1.0 / 65536.0)


if __name__ == "__main__":
    unittest.main()
