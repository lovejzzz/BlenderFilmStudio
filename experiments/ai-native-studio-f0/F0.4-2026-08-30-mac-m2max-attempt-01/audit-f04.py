# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent F0.4 artifact auditor; imports neither compiler nor runner."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest_file(path):
    return digest_bytes(path.read_bytes())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
root = args.repository_root.resolve(strict=True)
evidence = (root / args.evidence_root).resolve(strict=True)
expected = {
    "B01": {"plan": "316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf", "structure": "c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b"},
    "B02": {"plan": "a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687", "structure": "025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856"},
}
rows = []
for benchmark in ("B01", "B02"):
    folder = evidence / benchmark.lower() / "artifacts"
    manifest = json.loads((folder / "scene.manifest.json").read_text())
    structure_bytes = (folder / "scene.structure.canonical.json").read_bytes()
    structure_sha = digest_bytes(structure_bytes)
    bpy.ops.wm.open_mainfile(filepath=str(folder / "scene.blend"), load_ui=False)
    scene = bpy.context.scene
    checks = {
        "planHash": manifest["execution"]["planHash"] == expected[benchmark]["plan"] == scene["bfs_plan_hash"],
        "structureHash": structure_sha == expected[benchmark]["structure"] == scene["bfs_structure_hash"],
        "manifestStructure": manifest["structureHash"] == expected[benchmark]["structure"],
        "blendExists": (folder / "scene.blend").is_file(),
        "receiptExists": (evidence / benchmark.lower() / "receipt.json").is_file(),
    }
    rows.append({"id": benchmark, "checks": checks, "passed": all(checks.values()), "blendSha256": digest_file(folder / "scene.blend")})
comparison = json.loads((evidence / "canonical-comparison.json").read_text())
negative = json.loads((evidence / "negative-fixtures.json").read_text())
proposal = json.loads((evidence / "proposal-diff.json").read_text())
ui = json.loads((evidence / "runtime-ui/inspection.json").read_text())
cross = {
    "canonicalComparisonPass": comparison["status"] == "PASS" and all(item["byteExact"] for item in comparison["comparisons"]),
    "negativeSuitePass": negative["status"] == "PASS" and len(negative["cases"]) == 4 and all(item["passed"] for item in negative["cases"]),
    "proposalOrderPass": proposal["status"] == "PASS" and all(item["executionFollowedInspection"] for item in proposal["inspections"]),
    "uiPreExecutionPass": ui["status"] == "APPROVED_READY" and ui["executeEnabled"] and not ui["executed"] and not ui["outputExists"],
}
body = {
    "schemaVersion": "bfs.f0.4.independentAudit.v0.1",
    "status": "PASS" if all(item["passed"] for item in rows) and all(cross.values()) else "FAIL",
    "formalProductStart": 5,
    "independence": "Imports neither film_studio_contract nor formal-contract-run.py.",
    "builds": rows,
    "crossChecks": cross,
}
record = {**body, "auditHash": digest_bytes(canonical(body).encode())}
path = evidence / "audit.json"
descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
try:
    os.write(descriptor, (json.dumps(record, indent=2) + "\n").encode())
    os.fsync(descriptor)
finally:
    os.close(descriptor)
if record["status"] != "PASS":
    raise RuntimeError("F0.4 independent audit failed")
print("F04_AUDIT PASS B01 B02 negatives=4 ui=pre-execution")
