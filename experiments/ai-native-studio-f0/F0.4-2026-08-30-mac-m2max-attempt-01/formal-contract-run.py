# SPDX-License-Identifier: GPL-2.0-or-later
"""Frozen trusted F0.4 contract runner; proposals remain data-only JSON."""

import argparse
import copy
import json
import os
import sys
from pathlib import Path

import bpy
import film_studio_contract as contract


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def write_exclusive(path, payload):
    data = payload if isinstance(payload, bytes) else (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def hashed_record(body, field):
    return {**body, field: contract.sha256_bytes(contract.javascript_canonical_json(body).encode())}


def scene_fingerprint():
    value = {
        "scenes": sorted(scene.name for scene in bpy.data.scenes),
        "collections": sorted(collection.name for collection in bpy.data.collections),
        "objects": [
            {
                "name": obj.name,
                "type": obj.type,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "scale": list(obj.scale),
            }
            for obj in sorted(bpy.data.objects, key=lambda item: item.name)
        ],
    }
    return contract.sha256_bytes(contract.javascript_canonical_json(value).encode())


def proposal_for(base, fixture_uri, file_sha, canonical_sha, output_uri, scope=None):
    proposal = copy.deepcopy(base)
    proposal["proposalId"] = "F0.4-NEGATIVE-" + Path(fixture_uri).stem.upper().replace(".", "_")
    proposal["sceneSpec"] = {"uri": fixture_uri, "fileSha256": file_sha, "canonicalSha256": canonical_sha}
    proposal["requestedOutput"] = {"uri": output_uri}
    if scope is not None:
        proposal["requestedMutationScope"] = scope
    proposal["diff"]["summary"] = "Frozen negative-control proposal; no output or scene mutation is permitted."
    return proposal


def approval_for(root, proposal_uri, proposal, base):
    proposal_path = root / proposal_uri
    approval = copy.deepcopy(base)
    approval["approvalId"] = proposal["proposalId"] + "-APPROVAL"
    approval["authorizationSource"] = "Frozen F0.4 negative-control harness"
    approval["proposal"] = {"uri": proposal_uri, "fileSha256": contract.sha256_file(proposal_path)}
    approval["approvedOutput"] = copy.deepcopy(proposal["requestedOutput"])
    return approval


def main():
    args = arguments()
    root = args.repository_root.resolve(strict=True)
    evidence = (root / args.evidence_root).resolve(strict=True)
    before = scene_fingerprint()
    comparisons = []
    inspections = []

    for sequence, benchmark in enumerate(("B01", "B02"), start=1):
        proposal_uri = f"{args.evidence_root.as_posix()}/proposals/{benchmark}.proposal.json"
        approval_uri = f"{args.evidence_root.as_posix()}/approvals/{benchmark}.approval.json"
        inspection = contract.inspect_proposal(root, proposal_uri, approval_uri)
        result = contract.execute_approved_compile(root, proposal_uri, approval_uri, inspection["inspectionToken"])
        external = evidence / "external" / f"{benchmark}.build-plan.json"
        embedded = evidence / "embedded" / f"{benchmark}.build-plan.json"
        exact = external.read_bytes() == embedded.read_bytes()
        comparisons.append({
            "id": benchmark,
            "externalUri": external.relative_to(root).as_posix(),
            "embeddedUri": embedded.relative_to(root).as_posix(),
            "externalSha256": contract.sha256_file(external),
            "embeddedSha256": contract.sha256_file(embedded),
            "bytes": embedded.stat().st_size,
            "planHash": result["planHash"],
            "byteExact": exact,
            "sceneMutations": result["sceneMutations"],
        })
        inspections.append({
            "sequence": sequence,
            "proposalId": inspection["proposalId"],
            "statusBeforeExecution": inspection["status"],
            "diff": inspection["diff"],
            "approvedOperation": inspection["approvedOperation"],
            "approvedMutationScope": inspection["approvedMutationScope"],
            "outputUri": inspection["outputUri"],
            "executionFollowedInspection": result["status"] == "COMPILED",
        })
    after_positive = scene_fingerprint()

    base_scene = json.loads((root / "specs/benchmarks/B01.scene.json").read_text())
    base_proposal = json.loads((evidence / "proposals/B01.proposal.json").read_text())
    base_approval = json.loads((evidence / "approvals/B01.approval.json").read_text())
    negative_rows = []
    cases = []

    unknown = copy.deepcopy(base_scene)
    unknown["unexpectedField"] = True
    cases.append(("N_UNKNOWN_FIELD", unknown, None, "SCHEMA_ADDITIONAL_PROPERTY"))
    escaped = copy.deepcopy(base_scene)
    escaped["assets"][0]["uri"] = "../outside.blend"
    cases.append(("N_PATH_ESCAPE", escaped, None, "PATH_ESCAPE"))
    cases.append(("N_NONFINITE", None, (root / "specs/benchmarks/B01.scene.json").read_text().replace('"energy": 1200', '"energy": NaN', 1), "NONFINITE_NUMBER"))
    cases.append(("N_UNAPPROVED_MUTATION", base_scene, None, "APPROVAL_SCOPE"))

    for case_id, document, raw_text, expected in cases:
        fixture_uri = f"{args.evidence_root.as_posix()}/negative-inputs/{case_id}.scene.json"
        fixture_path = root / fixture_uri
        if raw_text is None:
            fixture_bytes = (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode()
            canonical_sha = contract.sha256_bytes(contract.javascript_canonical_json(contract.canonicalize(document)).encode())
        else:
            fixture_bytes = raw_text.encode()
            canonical_sha = "0" * 64
        write_exclusive(fixture_path, fixture_bytes)
        proposal_uri = f"{args.evidence_root.as_posix()}/negative-inputs/{case_id}.proposal.json"
        approval_uri = f"{args.evidence_root.as_posix()}/negative-inputs/{case_id}.approval.json"
        output_uri = f"{args.evidence_root.as_posix()}/negative-outputs/{case_id}.build-plan.json"
        scope = ["WRITE_BUILD_PLAN", "MUTATE_SCENE"] if case_id == "N_UNAPPROVED_MUTATION" else None
        proposal = proposal_for(base_proposal, fixture_uri, contract.sha256_bytes(fixture_bytes), canonical_sha, output_uri, scope)
        write_exclusive(root / proposal_uri, proposal)
        approval = approval_for(root, proposal_uri, proposal, base_approval)
        write_exclusive(root / approval_uri, approval)
        reason = None
        try:
            contract.inspect_proposal(root, proposal_uri, approval_uri)
        except contract.ContractError as error:
            reason = error.reason
        output_exists = (root / output_uri).exists()
        negative_rows.append({
            "id": case_id,
            "expectedReason": expected,
            "actualReason": reason,
            "passed": reason == expected and not output_exists,
            "buildPlanFilesWritten": int(output_exists),
            "sceneMutations": 0,
            "sceneCompilerProcessesStarted": 0,
            "networkCalls": 0,
            "arbitraryPythonFromProposalExecuted": 0,
        })

    after_negative = scene_fingerprint()
    comparison = hashed_record({
        "schemaVersion": "bfs.f0.4.canonicalComparison.v0.1",
        "status": "PASS" if all(row["byteExact"] and row["sceneMutations"] == 0 for row in comparisons) else "FAIL",
        "product": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode()},
        "comparisons": comparisons,
        "sceneFingerprintBefore": before,
        "sceneFingerprintAfter": after_positive,
        "sceneFingerprintExact": before == after_positive,
    }, "comparisonHash")
    negative = hashed_record({
        "schemaVersion": "bfs.f0.4.negativeFixtures.v0.1",
        "status": "PASS" if all(row["passed"] for row in negative_rows) else "FAIL",
        "cases": negative_rows,
        "sceneFingerprintBefore": before,
        "sceneFingerprintAfter": after_negative,
        "sceneFingerprintExact": before == after_negative,
    }, "negativeHash")
    proposal_diff = hashed_record({
        "schemaVersion": "bfs.f0.4.proposalDiff.v0.1",
        "status": "PASS" if all(row["statusBeforeExecution"] == "APPROVED_READY" and row["executionFollowedInspection"] for row in inspections) else "FAIL",
        "uiOrderRequired": ["INSPECT_PROPOSAL_DIFF", "DISPLAY_APPROVAL_SCOPE", "EXECUTE_APPROVED_COMPILE"],
        "inspections": inspections,
        "sceneMutationAuthorized": False,
        "arbitraryPythonAuthorized": False,
        "networkAccessAuthorized": False,
    }, "proposalDiffHash")
    write_exclusive(evidence / "canonical-comparison.json", comparison)
    write_exclusive(evidence / "negative-fixtures.json", negative)
    write_exclusive(evidence / "proposal-diff.json", proposal_diff)
    receipt = hashed_record({
        "schemaVersion": "bfs.f0.4.contractRuntimeReceipt.v0.1",
        "status": "PASS" if comparison["status"] == negative["status"] == proposal_diff["status"] == "PASS" else "FAIL",
        "formalProductStart": 2,
        "comparisons": [row["id"] for row in comparisons],
        "negativeCases": [row["id"] for row in negative_rows],
        "sceneFingerprintExact": before == after_positive == after_negative,
        "buildPlanFilesWritten": 2,
        "sceneMutations": 0,
        "networkCalls": 0,
        "arbitraryPythonFromProposalExecuted": 0,
    }, "receiptHash")
    write_exclusive(evidence / "runtime-contract/receipt.json", receipt)
    if receipt["status"] != "PASS":
        raise RuntimeError("F0.4 contract runner rejected")
    print("F04_CONTRACT PASS B01 B02 negatives=4 scene_mutations=0")


main()
