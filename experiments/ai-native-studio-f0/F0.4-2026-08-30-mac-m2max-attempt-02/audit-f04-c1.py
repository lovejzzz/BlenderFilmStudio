# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent cross-bound F0.4 correction audit; imports no compiler or contract runner."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
root = args.repository_root.resolve(strict=True)
evidence = (root / args.evidence_root).resolve(strict=True)
prior = root / "experiments/ai-native-studio-f0/F0.4-2026-08-30-mac-m2max-attempt-01"

expected_files = {
    "verdict.json": "788ad1014a58cc5446ba00d0abaf6131d4143fd4062157e26457adeaf120ee89",
    "canonical-comparison.json": "9f5f788f5079423e6f41304677d83803a3fed152a842eed41a59263dfe049b3a",
    "negative-fixtures.json": "836354807cf9efec0e23cd6d49052f9d809338baf531eadeed7b25783f7912c2",
    "proposal-diff.json": "dcec68c2e184ef8413562ad8004b0deaa5d1b95c207f5d5c697a2267d5bcdbab",
    "runtime-ui/inspection.json": "f782b2e35fd086e5483ea201a65d31592961b78381c9dab7238e009ab118b306",
}
cross_files = {name: digest(prior / name) == expected for name, expected in expected_files.items()}
verdict = json.loads((prior / "verdict.json").read_text())
comparison = json.loads((prior / "canonical-comparison.json").read_text())
negative = json.loads((prior / "negative-fixtures.json").read_text())
proposal = json.loads((prior / "proposal-diff.json").read_text())
ui = json.loads((prior / "runtime-ui/inspection.json").read_text())
cross_semantics = {
    "retainedFailureExact": verdict["status"] == "FAIL" and verdict["failure"]["id"] == "B01_OCIO_CONFIG_MISMATCH",
    "canonicalComparisonPass": comparison["status"] == "PASS" and all(item["byteExact"] for item in comparison["comparisons"]),
    "negativeSuitePass": negative["status"] == "PASS" and len(negative["cases"]) == 4 and all(item["passed"] for item in negative["cases"]),
    "proposalOrderPass": proposal["status"] == "PASS" and all(item["executionFollowedInspection"] for item in proposal["inspections"]),
    "uiPreExecutionPass": ui["status"] == "APPROVED_READY" and ui["executeEnabled"] and not ui["executed"] and not ui["outputExists"],
}

expected = {
    "B01": {"plan": "316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf", "structure": "c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b"},
    "B02": {"plan": "a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687", "structure": "025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856"},
}
rows = []
for benchmark in ("B01", "B02"):
    folder = evidence / benchmark.lower() / "artifacts"
    manifest = json.loads((folder / "scene.manifest.json").read_text())
    structure_sha = digest(folder / "scene.structure.canonical.json")
    bpy.ops.wm.open_mainfile(filepath=str(folder / "scene.blend"), load_ui=False)
    scene = bpy.context.scene
    checks = {
        "planHash": manifest["execution"]["planHash"] == expected[benchmark]["plan"] == scene["bfs_plan_hash"],
        "structureHash": structure_sha == expected[benchmark]["structure"] == scene["bfs_structure_hash"],
        "manifestStructure": manifest["structureHash"] == expected[benchmark]["structure"],
        "ocioConfigName": scene["bfs_ocio_config"] == "cg-config-v4.0.0_aces-v2.0_ocio-v2.5",
        "ocioConfigSha256": manifest["execution"]["ocioConfigSha256"] == "24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15",
        "receiptExists": (evidence / benchmark.lower() / "receipt.json").is_file(),
    }
    rows.append({"id": benchmark, "checks": checks, "passed": all(checks.values()), "blendSha256": digest(folder / "scene.blend")})

body = {
    "schemaVersion": "bfs.f0.4.correctionIndependentAudit.v0.1",
    "status": "PASS" if all(cross_files.values()) and all(cross_semantics.values()) and all(item["passed"] for item in rows) else "FAIL",
    "formalProductStart": 3,
    "correction": "C1_OCIO_LAUNCH_ENVIRONMENT_BINDING",
    "independence": "Imports neither film_studio_contract, compile_scene.py nor a formal contract runner.",
    "crossBoundFiles": cross_files,
    "crossBoundSemantics": cross_semantics,
    "builds": rows,
}
record = {**body, "auditHash": hashlib.sha256(canonical(body).encode()).hexdigest()}
path = evidence / "audit.json"
descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
try:
    os.write(descriptor, (json.dumps(record, indent=2) + "\n").encode())
    os.fsync(descriptor)
finally:
    os.close(descriptor)
if record["status"] != "PASS":
    raise RuntimeError("F0.4 correction independent audit failed")
print("F04_C1_AUDIT PASS B01 B02 cross_bound_attempt01")
