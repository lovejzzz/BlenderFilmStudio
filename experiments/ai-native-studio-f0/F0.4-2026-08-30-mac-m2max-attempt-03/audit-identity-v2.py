# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent F0.4 identity-v2 audit; imports neither compiler nor contract runner."""

import argparse
import copy
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


def semantic_digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def receipt_self_valid(path):
    value = json.loads(path.read_text())
    expected = value.pop("receiptHash")
    actual = hashlib.sha256((json.dumps(value, indent=2) + "\n").encode()).hexdigest()
    return expected == actual


parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
root = args.repository_root.resolve(strict=True)
evidence = (root / args.evidence_root).resolve(strict=True)
attempt1 = root / "experiments/ai-native-studio-f0/F0.4-2026-08-30-mac-m2max-attempt-01"
attempt2 = root / "experiments/ai-native-studio-f0/F0.4-2026-08-30-mac-m2max-attempt-02"

cross_bound_files = {
    "attempt01Verdict": digest(attempt1 / "verdict.json") == "788ad1014a58cc5446ba00d0abaf6131d4143fd4062157e26457adeaf120ee89",
    "attempt01CanonicalComparison": digest(attempt1 / "canonical-comparison.json") == "9f5f788f5079423e6f41304677d83803a3fed152a842eed41a59263dfe049b3a",
    "attempt01NegativeFixtures": digest(attempt1 / "negative-fixtures.json") == "836354807cf9efec0e23cd6d49052f9d809338baf531eadeed7b25783f7912c2",
    "attempt01ProposalDiff": digest(attempt1 / "proposal-diff.json") == "dcec68c2e184ef8413562ad8004b0deaa5d1b95c207f5d5c697a2267d5bcdbab",
    "attempt02Verdict": digest(attempt2 / "verdict.json") == "6db72890e649e18de68926459947edd490d1c651188ff986ccc230da581ef764",
    "attempt02B01Receipt": json.loads((attempt2 / "b01/receipt.json").read_text())["receiptHash"] == "077a4792dceb95ff36ee793e0c625fea680817b57fc62d68a1835420eaf162cc",
    "B13HistoricalIntent": digest(root / "research/2026-08-26-b13-compile-receipt-protocol.md") == "d1ea8335b5a973bfb634eda87d3ed129fe90f45afcf9b4a7306221ba5a1beaab",
    "correctedCompiler": digest(root / "blender/compile_scene.py") == "d38cc0579397f7e985b197f2a4725ae1c26eb3509166c8030198fa246cccee19",
}
attempt1_verdict = json.loads((attempt1 / "verdict.json").read_text())
attempt2_verdict = json.loads((attempt2 / "verdict.json").read_text())
cross_bound_semantics = {
    "attempt01FailureRetained": attempt1_verdict["status"] == "FAIL" and attempt1_verdict["failure"]["id"] == "B01_OCIO_CONFIG_MISMATCH",
    "attempt02FailureRetained": attempt2_verdict["status"] == "FAIL" and attempt2_verdict["failure"]["id"] == "B01_FROZEN_STRUCTURE_HASH_MISMATCH",
    "attempt01ContractEvidencePassed": all([
        attempt1_verdict["checks"]["embeddedB01CanonicalExact"],
        attempt1_verdict["checks"]["embeddedB02CanonicalExact"],
        attempt1_verdict["checks"]["unknownFieldRejectedBeforeMutation"],
        attempt1_verdict["checks"]["pathEscapeRejectedBeforeMutation"],
        attempt1_verdict["checks"]["nonfiniteNumberRejectedBeforeMutation"],
        attempt1_verdict["checks"]["unapprovedMutationRejectedBeforeMutation"],
    ]),
    "attempt02OnlyProductBuildHashDiffered": attempt2_verdict["failure"]["onlyDifferingJsonPath"] == "$.blender.buildHash",
}

expected = {
    "B01": {"plan": "316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf", "semantic": "e8c55fb73737f1871ac0008faa705dc204ebfe5bac471323cbb0a2d31435b4f8"},
    "B02": {"plan": "a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687", "semantic": "d197b024c3b1de19c7fa981912c584de51d6d4884ef78b10e29db598ce979954"},
}
builds = []
separation_attacks = []
for benchmark in ("B01", "B02"):
    folder = evidence / benchmark.lower() / "artifacts"
    manifest = json.loads((folder / "scene.manifest.json").read_text())
    structure = manifest["structure"]
    product = manifest["execution"]["blender"]
    structure_sha = digest(folder / "scene.structure.canonical.json")
    bpy.ops.wm.open_mainfile(filepath=str(folder / "scene.blend"), load_ui=False)
    scene = bpy.context.scene
    checks = {
        "manifestVersion": manifest["manifestVersion"] == "0.3.0",
        "structureIdentityVersion": manifest["structureIdentityVersion"] == "bfs.semanticSceneStructure.v0.2" == scene["bfs_structure_identity_version"],
        "planHash": manifest["execution"]["planHash"] == structure["planHash"] == expected[benchmark]["plan"] == scene["bfs_plan_hash"],
        "semanticStructureHash": structure_sha == semantic_digest(structure) == manifest["structureHash"] == expected[benchmark]["semantic"] == scene["bfs_structure_hash"],
        "semanticStructureExcludesProductProvenance": "blender" not in structure,
        "productProvenance": product == {"version": "5.2.0 LTS", "buildHash": "b47eae224b6d", "buildBranch": "codex/f0.4-embedded-contract", "buildPlatform": "Darwin"},
        "blendProductBuildHash": scene["bfs_product_build_hash"] == "b47eae224b6d",
        "ocioConfig": manifest["execution"]["ocioConfigSha256"] == "24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15" == scene["bfs_ocio_sha256"],
        "receiptSelfHash": receipt_self_valid(evidence / benchmark.lower() / "receipt.json"),
    }
    builds.append({"id": benchmark, "checks": checks, "passed": all(checks.values()), "blendSha256": digest(folder / "scene.blend")})

    provenance_mutation = copy.deepcopy(manifest)
    provenance_mutation["execution"]["blender"]["buildHash"] = "ATTACKED"
    provenance_attack = {
        "id": f"{benchmark}_PROVENANCE_MUTATION",
        "semanticHashUnchanged": semantic_digest(provenance_mutation["structure"]) == expected[benchmark]["semantic"],
        "productProvenanceRejected": provenance_mutation["execution"]["blender"]["buildHash"] != "b47eae224b6d",
    }
    provenance_attack["passed"] = all(provenance_attack.values())
    separation_attacks.append(provenance_attack)

    semantic_mutation = copy.deepcopy(manifest)
    semantic_mutation["structure"]["shot"]["title"] += " ATTACKED"
    semantic_attack = {
        "id": f"{benchmark}_SEMANTIC_MUTATION",
        "semanticHashRejected": semantic_digest(semantic_mutation["structure"]) != expected[benchmark]["semantic"],
        "productProvenanceUnchanged": semantic_mutation["execution"]["blender"] == product,
    }
    semantic_attack["passed"] = all(semantic_attack.values())
    separation_attacks.append(semantic_attack)

body = {
    "schemaVersion": "bfs.f0.4.identityV2IndependentAudit.v0.1",
    "formalProductStart": 3,
    "correction": "C2_VERSIONED_SEMANTIC_STRUCTURE_AND_PRODUCT_PROVENANCE",
    "independence": "Imports neither film_studio_contract, compile_scene.py nor a formal contract runner.",
    "crossBoundFiles": cross_bound_files,
    "crossBoundSemantics": cross_bound_semantics,
    "builds": builds,
    "separationAttacks": separation_attacks,
}
body["status"] = "PASS" if all(cross_bound_files.values()) and all(cross_bound_semantics.values()) and all(item["passed"] for item in builds) and all(item["passed"] for item in separation_attacks) else "FAIL"
record = {**body, "auditHash": hashlib.sha256(canonical(body).encode()).hexdigest()}
path = evidence / "audit.json"
descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
try:
    os.write(descriptor, (json.dumps(record, indent=2) + "\n").encode())
    os.fsync(descriptor)
finally:
    os.close(descriptor)
if record["status"] != "PASS":
    raise RuntimeError("F0.4 identity-v2 independent audit failed")
print("F04_C2_AUDIT PASS B01 B02 attacks=4 cross_bound_attempts=2")
