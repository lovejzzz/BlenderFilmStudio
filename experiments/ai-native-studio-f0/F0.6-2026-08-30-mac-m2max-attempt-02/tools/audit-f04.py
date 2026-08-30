# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent merged-product F0.4 semantic/provenance audit."""

import argparse
import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy


PLAN = {
    "B01": "316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf",
    "B02": "a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687",
}
SEMANTIC = {
    "B01": "e8c55fb73737f1871ac0008faa705dc204ebfe5bac471323cbb0a2d31435b4f8",
    "B02": "d197b024c3b1de19c7fa981912c584de51d6d4884ef78b10e29db598ce979954",
}
PROVENANCE = {
    "version": "5.2.1 LTS",
    "buildHash": "fa1b578bb421",
    "buildBranch": "codex/f0.6-upstream-merge-drill",
    "buildPlatform": "Darwin",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


parser = argparse.ArgumentParser()
parser.add_argument("--evidence", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
evidence = args.evidence.resolve(strict=True)
rows = []
attacks = []
for benchmark in ("B01", "B02"):
    artifact = evidence / benchmark.lower() / "artifacts"
    manifest = json.loads((artifact / "scene.manifest.json").read_text())
    structure = manifest["structure"]
    provenance = manifest["execution"]["blender"]
    bpy.ops.wm.open_mainfile(filepath=str(artifact / "scene.blend"), load_ui=False)
    scene = bpy.context.scene
    checks = {
        "manifestVersion": manifest["manifestVersion"] == "0.3.0",
        "structureIdentityVersion": manifest["structureIdentityVersion"] == scene["bfs_structure_identity_version"] == "bfs.semanticSceneStructure.v0.2",
        "planHash": manifest["execution"]["planHash"] == structure["planHash"] == scene["bfs_plan_hash"] == PLAN[benchmark],
        "semanticHash": digest(artifact / "scene.structure.canonical.json") == hashlib.sha256(canonical(structure).encode()).hexdigest() == manifest["structureHash"] == scene["bfs_structure_hash"] == SEMANTIC[benchmark],
        "semanticExcludesProvenance": "blender" not in structure,
        "productProvenanceExact": provenance == PROVENANCE,
        "blendProductBuildHashExact": scene["bfs_product_build_hash"] == PROVENANCE["buildHash"],
        "ocioExact": manifest["execution"]["ocioConfigSha256"] == scene["bfs_ocio_sha256"] == "24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15",
    }
    rows.append({"id": benchmark, "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "blendSha256": digest(artifact / "scene.blend")})
    provenance_attack = copy.deepcopy(manifest)
    provenance_attack["execution"]["blender"]["buildHash"] = "ATTACKED"
    attacks.append({
        "id": benchmark + "_PROVENANCE",
        "passed": hashlib.sha256(canonical(provenance_attack["structure"]).encode()).hexdigest() == SEMANTIC[benchmark] and provenance_attack["execution"]["blender"] != PROVENANCE,
    })
    semantic_attack = copy.deepcopy(manifest)
    semantic_attack["structure"]["shot"]["title"] += " ATTACKED"
    attacks.append({
        "id": benchmark + "_SEMANTIC",
        "passed": hashlib.sha256(canonical(semantic_attack["structure"]).encode()).hexdigest() != SEMANTIC[benchmark] and semantic_attack["execution"]["blender"] == provenance,
    })

body = {
    "schemaVersion": "bfs.f0.6.f04IndependentAudit.v0.1",
    "status": "PASS" if all(row["status"] == "PASS" for row in rows) and all(row["passed"] for row in attacks) else "FAIL",
    "independence": "Imports neither film_studio_contract nor compile_scene.py.",
    "expectedProvenance": PROVENANCE,
    "builds": rows,
    "separationAttacks": attacks,
    "renderCalls": 0,
}
body["auditHash"] = hashlib.sha256(canonical(body).encode()).hexdigest()
descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
try:
    os.write(descriptor, (json.dumps(body, indent=2) + "\n").encode())
    os.fsync(descriptor)
finally:
    os.close(descriptor)
if body["status"] != "PASS":
    raise RuntimeError("F0.4 merged-product audit failed")
print("F06_F04_AUDIT PASS builds=2 attacks=4 renders=0", flush=True)
