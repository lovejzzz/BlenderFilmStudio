#!/usr/bin/env python3
"""Audit-only negative-state replay for immutable B52-D12.8-C1 evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import struct
import sys
import zlib
from pathlib import Path


CORRECTION_SPEC_URI = "specs/blender-projective-motion-disocclusion-adaptive-risk-audit-c2.v0.1.json"
CORRECTION_SPEC_SHA256 = "4808f9fff747a562f5d885e0294a1134d39ab4e3ed35627a46bd253d1fad5aa7"
CORRECTION_PREREGISTRATION_COMMIT = "bfbf3305c17018647289f4f8962fabfa7e0b7034"
THIS_TOOL_URI = "scripts/audit-b52-d12-8-motion-disocclusion-c2.py"
PAYLOADS = (
    "adaptive-reconstructed.rgba32",
    "reason.u8",
    "analytic-owner.u8",
    "structural-valid.u8",
    "radius2-interior.u8",
    "radius3-interior.u8",
    "adaptive-interior.u8",
    "adaptive-rejected.u8",
    "risk.rgb64",
)
RISK_PAYLOAD = "risk.rgb64"


def sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return sha_bytes(payload)


def self_hash_ok(document: dict, field: str) -> bool:
    return document.get(field) == canonical_hash({key: value for key, value in document.items() if key != field})


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def git_dir(repository: Path) -> Path:
    marker = repository / ".git"
    if marker.is_dir():
        return marker
    if marker.is_file():
        line = marker.read_text().strip()
        if line.startswith("gitdir: "):
            candidate = Path(line[8:])
            return candidate if candidate.is_absolute() else (repository / candidate).resolve()
    raise RuntimeError("unable to resolve Git directory")


def read_loose_git_object(repository: Path, oid: str) -> tuple[str, bytes]:
    if len(oid) != 40 or any(character not in "0123456789abcdef" for character in oid):
        raise RuntimeError(f"invalid full Git object id: {oid}")
    object_path = git_dir(repository) / "objects" / oid[:2] / oid[2:]
    if not object_path.is_file():
        raise RuntimeError(f"required frozen Git object is not loose: {oid}")
    inflated = zlib.decompress(object_path.read_bytes())
    header, payload = inflated.split(b"\0", 1)
    kind, length_text = header.decode().split(" ", 1)
    if len(payload) != int(length_text):
        raise RuntimeError(f"Git object length mismatch: {oid}")
    return kind, payload


def commit_metadata(repository: Path, commit_oid: str) -> tuple[str, list[str]]:
    kind, payload = read_loose_git_object(repository, commit_oid)
    if kind != "commit":
        raise RuntimeError(f"not a commit: {commit_oid}")
    tree = ""
    parents: list[str] = []
    for line in payload.decode(errors="strict").splitlines():
        if line.startswith("tree "):
            tree = line[5:]
        elif line.startswith("parent "):
            parents.append(line[7:])
        elif not line:
            break
    if not tree:
        raise RuntimeError(f"commit has no tree: {commit_oid}")
    return tree, parents


def git_blob_at_commit(repository: Path, commit_oid: str, uri: str) -> tuple[str, bytes]:
    tree_oid, _ = commit_metadata(repository, commit_oid)
    parts = Path(uri).parts
    for index, part in enumerate(parts):
        kind, payload = read_loose_git_object(repository, tree_oid)
        if kind != "tree":
            raise RuntimeError(f"expected tree while resolving {uri}")
        cursor = 0
        selected: tuple[str, str] | None = None
        while cursor < len(payload):
            space = payload.index(b" ", cursor)
            nul = payload.index(b"\0", space)
            mode = payload[cursor:space].decode()
            name = payload[space + 1 : nul].decode()
            oid = payload[nul + 1 : nul + 21].hex()
            cursor = nul + 21
            if name == part:
                selected = mode, oid
                break
        if selected is None:
            raise RuntimeError(f"path absent from frozen commit: {commit_oid}:{uri}")
        mode, tree_oid = selected
        if index < len(parts) - 1 and mode not in ("40000", "040000"):
            raise RuntimeError(f"non-tree path component: {commit_oid}:{uri}")
    kind, blob = read_loose_git_object(repository, tree_oid)
    if kind != "blob":
        raise RuntimeError(f"path is not a blob: {commit_oid}:{uri}")
    return tree_oid, blob


def commit_descends_from(repository: Path, descendant: str, ancestor: str) -> bool:
    pending = [descendant]
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current == ancestor:
            return True
        if current in seen:
            continue
        seen.add(current)
        _, parents = commit_metadata(repository, current)
        pending.extend(parents)
    return False


def parent_identity(correction: dict, name: str, field: str | None = None) -> bool:
    row = correction["parents"][name]
    path = Path(row["uri"])
    if not path.is_file() or sha_file(path) != row["sha256"]:
        return False
    if field is None:
        return True
    document = read_json(path)
    return self_hash_ok(document, field) and document.get(field) == row[field]


def exact_result_state(correction: dict, result: dict) -> tuple[bool, dict]:
    expected = correction["expectedNegativeState"]
    checks = {row.get("id"): row.get("passed") for row in result.get("checks", [])}
    false_checks = sorted(name for name, passed in checks.items() if passed is False)
    true_checks = sorted(name for name, passed in checks.items() if passed is True)
    attacks = result.get("mutationAttacks", [])
    state = {
        "verdict": result.get("verdict"),
        "passed": result.get("passed"),
        "checkPassed": result.get("checkPassed"),
        "checkTotal": result.get("checkTotal"),
        "falseChecks": false_checks,
        "trueChecks": true_checks,
        "evidenceHash": result.get("evidenceHash"),
        "mutationAttackPassed": result.get("mutationAttackPassed"),
        "mutationAttackTotal": result.get("mutationAttackTotal"),
    }
    passed = (
        result.get("schemaVersion") == "bfs.blenderProjectiveMotionDisocclusionAdaptiveRiskResult.v0.1"
        and result.get("experimentId") == "B52-D12.8-C1"
        and result.get("verdict") == correction["gates"]["expectedVerdict"]
        and result.get("passed") is False
        and result.get("checkPassed") == correction["parents"]["result"]["checkPassed"]
        and result.get("checkTotal") == correction["parents"]["result"]["checkTotal"]
        and false_checks == sorted(expected["falseResultChecks"])
        and true_checks == sorted(expected["trueResultChecks"])
        and len(checks) == result.get("checkTotal")
        and len(attacks) == correction["gates"]["mutationAttacksTotal"]
        and len({row.get("id") for row in attacks}) == len(attacks)
        and all(row.get("passed") is True for row in attacks)
        and result.get("mutationAttackPassed") == correction["gates"]["mutationAttacksPassed"]
        and result.get("mutationAttackTotal") == correction["gates"]["mutationAttacksTotal"]
        and result.get("operationCounts") == {"analyzerProcesses": 1, "modelCalls": 0, "networkCalls": 0}
        and result.get("parentChecks")
        and all(value is True for value in result["parentChecks"].values())
    )
    return bool(passed), state


def exact_failed_audit_state(correction: dict, audit: dict, result: dict) -> tuple[bool, dict]:
    checks = {row.get("id"): row.get("passed") for row in audit.get("checks", [])}
    false_checks = sorted(name for name, passed in checks.items() if passed is False)
    state = {
        "passed": audit.get("passed"),
        "checkPassed": audit.get("checkPassed"),
        "checkTotal": audit.get("checkTotal"),
        "onlyFalseCheck": false_checks[0] if len(false_checks) == 1 else None,
        "auditHash": audit.get("auditHash"),
        "expectedVerdict": audit.get("expectedVerdict"),
    }
    row = correction["parents"]["failedAudit"]
    passed = (
        audit.get("schemaVersion") == "bfs.blenderProjectiveMotionDisocclusionAdaptiveRiskAudit.v0.1"
        and audit.get("experimentId") == "B52-D12.8-C1"
        and audit.get("passed") is False
        and audit.get("checkPassed") == row["checkPassed"]
        and audit.get("checkTotal") == row["checkTotal"]
        and len(checks) == audit.get("checkTotal")
        and false_checks == [row["onlyFalseCheck"]]
        and audit.get("expectedVerdict") == result.get("verdict")
        and audit.get("resultEvidenceHash") == result.get("evidenceHash")
        and audit.get("resultSha256") == correction["parents"]["result"]["sha256"]
        and audit.get("operationCounts") == {"auditProcesses": 1, "modelCalls": 0, "networkCalls": 0}
    )
    return bool(passed), state


def original_process_state(correction: dict, execution: dict, result: dict, audit: dict, failure: dict) -> tuple[bool, dict]:
    children = execution.get("children", [])
    child_pids = [row.get("pid") for row in children]
    original_pids = child_pids + [result.get("analyzerPid"), audit.get("auditPid")]
    role_counts: dict[str, int] = {}
    for row in children:
        role = row.get("role")
        role_counts[role] = role_counts.get(role, 0) + 1
    expected_roles = {
        "SOURCE": 16,
        "ADAPTER": 8,
        "CONSUMER_PYTHON": 8,
        "CONSUMER_NODE": 8,
        "ENVELOPE_PYTHON": 16,
        "ENVELOPE_NODE": 16,
    }
    failed_child = failure.get("failedChild", {})
    passed = (
        len(children) == 72
        and len(set(child_pids)) == 72
        and all(row.get("exitCode") == 0 for row in children)
        and role_counts == expected_roles
        and len(original_pids) == 74
        and len(set(original_pids)) == 74
        and result.get("analyzerPid") == correction["parents"]["result"]["analyzerPid"]
        and audit.get("auditPid") == correction["parents"]["failedAudit"]["auditPid"]
        and failed_child.get("role") == "AUDIT"
        and failed_child.get("pid") == audit.get("auditPid")
        and failed_child.get("exitCode") == 1
        and execution.get("operationCounts")
        == {
            "sourceRenders": 16,
            "adapters": 8,
            "pythonConsumers": 8,
            "nodeConsumers": 8,
            "pythonEnvelopeEncoders": 16,
            "nodeEnvelopeEncoders": 16,
            "analyzers": 1,
            "audits": 1,
            "modelCalls": 0,
            "networkCalls": 0,
        }
    )
    state = {
        "childCount": len(children),
        "originalPidCount": len(original_pids),
        "uniquePidCount": len(set(original_pids)),
        "originalPidsHash": canonical_hash(original_pids),
        "analyzerPid": result.get("analyzerPid"),
        "auditPid": audit.get("auditPid"),
        "executionHash": execution.get("executionHash"),
        "roles": role_counts,
    }
    return bool(passed), state


def risk_difference_roster(python_payload: bytes, node_payload: bytes) -> list[dict]:
    if len(python_payload) != len(node_payload) or len(python_payload) % 8:
        raise RuntimeError("risk float64 payload length mismatch")
    roster: list[dict] = []
    scalar_total = len(python_payload) // 8
    for index in range(scalar_total):
        python_bits = python_payload[index * 8 : index * 8 + 8]
        node_bits = node_payload[index * 8 : index * 8 + 8]
        python_value = struct.unpack("<d", python_bits)[0]
        node_value = struct.unpack("<d", node_bits)[0]
        if python_value != node_value:
            roster.append(
                {
                    "flatIndex": index,
                    "pythonBits": python_bits.hex(),
                    "nodeBits": node_bits.hex(),
                    "absoluteDifference": abs(python_value - node_value),
                }
            )
    return roster


def derived_decision_difference(
    python_risk: bytes,
    node_risk: bytes,
    radius2: bytes,
    python_decision: bytes,
    node_decision: bytes,
    threshold: float,
) -> tuple[int, bool]:
    if len(radius2) != len(python_decision) or len(radius2) != len(node_decision):
        raise RuntimeError("decision-mask length mismatch")
    expected_risk_bytes = len(radius2) * 3 * 8
    if len(python_risk) != expected_risk_bytes or len(node_risk) != expected_risk_bytes:
        raise RuntimeError("risk/mask shape mismatch")
    differences = 0
    stored_consistency = True
    for pixel, inside in enumerate(radius2):
        if not inside:
            continue
        offset = pixel * 24
        python_values = struct.unpack_from("<ddd", python_risk, offset)
        node_values = struct.unpack_from("<ddd", node_risk, offset)
        python_accept = max(python_values) <= threshold
        node_accept = max(node_values) <= threshold
        differences += int(python_accept != node_accept)
        stored_consistency = stored_consistency and python_decision[pixel] == int(python_accept)
        stored_consistency = stored_consistency and node_decision[pixel] == int(node_accept)
    return differences, stored_consistency


def raw_dual_state(correction: dict, spec: dict, root: Path, result: dict) -> tuple[dict, dict]:
    threshold = float(spec["frozenGates"]["adaptiveQuality"]["rgbMaximum"])
    expected_cells = correction["expectedNegativeState"]["cells"]
    expected_by_cell = {row["cell"]: row for row in expected_cells}
    result_identities = result.get("identities", {})
    cells: list[dict] = []
    non_risk_checks = 0
    non_risk_passed = 0
    risk_identity_checks = 0
    risk_identity_failures = 0
    total_scalar_differences = 0
    total_decision_differences = 0
    python_identity_checks: list[bool] = []
    stored_decision_checks: list[bool] = []
    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        for repeat in (1, 2):
            cell = f"{fixture_id}/R{repeat}"
            python_dir = root / "consumers" / "python" / fixture_id / f"R{repeat}" / "arrays"
            node_dir = root / "consumers" / "node" / fixture_id / f"R{repeat}" / "arrays"
            mismatched: list[str] = []
            payloads: dict[str, tuple[bytes, bytes]] = {}
            for filename in PAYLOADS:
                python_payload = (python_dir / filename).read_bytes()
                node_payload = (node_dir / filename).read_bytes()
                payloads[filename] = python_payload, node_payload
                if python_payload != node_payload:
                    mismatched.append(filename)
                if filename == RISK_PAYLOAD:
                    risk_identity_checks += 1
                    risk_identity_failures += int(python_payload != node_payload)
                else:
                    non_risk_checks += 1
                    non_risk_passed += int(python_payload == node_payload)
            name_to_result_key = {
                "adaptive-reconstructed.rgba32": "adaptiveReconstructed",
                "reason.u8": "reason",
                "analytic-owner.u8": "analyticOwner",
                "structural-valid.u8": "structuralValid",
                "radius2-interior.u8": "radius2Interior",
                "radius3-interior.u8": "radius3Interior",
                "adaptive-interior.u8": "adaptiveInterior",
                "adaptive-rejected.u8": "adaptiveRejected",
                "risk.rgb64": "riskRgb",
            }
            expected_python_hashes = result_identities[fixture_id][str(repeat)]["consumer"]
            for filename, result_key in name_to_result_key.items():
                python_identity_checks.append(sha_bytes(payloads[filename][0]) == expected_python_hashes[result_key])
            roster = risk_difference_roster(*payloads[RISK_PAYLOAD])
            decision_differences, stored_consistency = derived_decision_difference(
                payloads[RISK_PAYLOAD][0],
                payloads[RISK_PAYLOAD][1],
                payloads["radius2-interior.u8"][0],
                payloads["adaptive-interior.u8"][0],
                payloads["adaptive-interior.u8"][1],
                threshold,
            )
            stored_decision_checks.append(stored_consistency)
            row = {
                "cell": cell,
                "mismatchedPayloads": mismatched,
                "riskScalarDifferenceCount": len(roster),
                "riskAbsoluteDifferenceMaximum": max((item["absoluteDifference"] for item in roster), default=0.0),
                "riskDifferenceRosterHash": canonical_hash(roster),
                "derivedDecisionDifferenceCount": decision_differences,
            }
            if cell not in expected_by_cell:
                raise RuntimeError(f"unregistered C2 cell: {cell}")
            cells.append(row)
            total_scalar_differences += len(roster)
            total_decision_differences += decision_differences
    summary = {
        "cells": cells,
        "nonRiskPayloadIdentityChecks": non_risk_checks,
        "nonRiskPayloadIdentityPassed": non_risk_passed,
        "riskPayloadIdentityChecks": risk_identity_checks,
        "riskPayloadIdentityFailures": risk_identity_failures,
        "totalRiskScalarDifferences": total_scalar_differences,
        "totalDerivedDecisionDifferences": total_decision_differences,
    }
    fixture_pairs: dict[str, list[dict]] = {}
    for row in cells:
        fixture_id = row["cell"].rsplit("/R", 1)[0]
        fixture_pairs.setdefault(fixture_id, []).append({key: value for key, value in row.items() if key != "cell"})
    checks = {
        "pythonResultIdentity": all(python_identity_checks),
        "nonRiskDualIdentity": non_risk_checks == non_risk_passed == correction["expectedNegativeState"]["nonRiskPayloadIdentityChecks"],
        "riskDifferenceRoster": cells == expected_cells
        and risk_identity_checks == correction["expectedNegativeState"]["riskPayloadIdentityChecks"]
        and risk_identity_failures == correction["expectedNegativeState"]["riskPayloadIdentityFailures"]
        and total_scalar_differences == correction["expectedNegativeState"]["totalRiskScalarDifferences"],
        "zeroDecisionDifference": total_decision_differences == correction["expectedNegativeState"]["totalDerivedDecisionDifferences"]
        and all(stored_decision_checks),
        "repeatSummaryIdentity": all(len(rows) == 2 and rows[0] == rows[1] for rows in fixture_pairs.values()),
    }
    return summary, checks


def mutate_value(value: object) -> object:
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 1e-12
    if isinstance(value, str):
        return value + "_MUTATED"
    if isinstance(value, list):
        return value + ["MUTATED"]
    if isinstance(value, dict):
        return {**value, "MUTATED": True}
    return "MUTATED"


def mutation_attacks(projection: dict) -> list[dict]:
    targets: list[tuple[str, ...]] = [
        ("result", "verdict"),
        ("result", "passed"),
        ("result", "checkPassed"),
        ("result", "checkTotal"),
        ("result", "falseChecks"),
        ("result", "trueChecks"),
        ("result", "evidenceHash"),
        ("result", "mutationAttackPassed"),
        ("result", "mutationAttackTotal"),
        ("failedAudit", "passed"),
        ("failedAudit", "checkPassed"),
        ("failedAudit", "checkTotal"),
        ("failedAudit", "onlyFalseCheck"),
        ("failedAudit", "auditHash"),
        ("failedAudit", "expectedVerdict"),
        ("process", "childCount"),
        ("process", "originalPidCount"),
        ("process", "uniquePidCount"),
        ("process", "originalPidsHash"),
        ("process", "executionHash"),
    ]
    for index in range(8):
        targets.append(("rawDual", "cells", str(index), "riskScalarDifferenceCount"))
        targets.append(("rawDual", "cells", str(index), "riskDifferenceRosterHash"))
    targets.extend(
        [
            ("rawDual", "nonRiskPayloadIdentityChecks"),
            ("rawDual", "riskPayloadIdentityFailures"),
            ("rawDual", "totalRiskScalarDifferences"),
            ("rawDual", "totalDerivedDecisionDifferences"),
        ]
    )
    if len(targets) != 40:
        raise RuntimeError("C2 mutation target roster must contain exactly 40 entries")
    attacks: list[dict] = []
    for index, path in enumerate(targets, 1):
        changed = copy.deepcopy(projection)
        cursor: object = changed
        for component in path[:-1]:
            cursor = cursor[int(component)] if isinstance(cursor, list) else cursor[component]
        key = path[-1]
        if isinstance(cursor, list):
            position = int(key)
            cursor[position] = mutate_value(cursor[position])
        else:
            cursor[key] = mutate_value(cursor[key])
        attacks.append(
            {
                "id": f"M{index:02d}",
                "target": ".".join(path),
                "passed": changed != projection,
            }
        )
    return attacks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--correction-spec", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--failed-audit", type=Path, required=True)
    parser.add_argument("--failure", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()

    repository = Path.cwd().resolve()
    correction = read_json(args.correction_spec)
    if sha_file(args.correction_spec) != CORRECTION_SPEC_SHA256:
        raise RuntimeError("C2 correction-spec identity mismatch")
    if args.correction_spec.resolve() != (repository / CORRECTION_SPEC_URI).resolve():
        raise RuntimeError("C2 correction-spec path redirect")
    prereg_blob_oid, prereg_blob = git_blob_at_commit(repository, CORRECTION_PREREGISTRATION_COMMIT, CORRECTION_SPEC_URI)
    if prereg_blob != args.correction_spec.read_bytes():
        raise RuntimeError("C2 preregistration Git blob mismatch")
    if not commit_descends_from(repository, args.freeze_commit, CORRECTION_PREREGISTRATION_COMMIT):
        raise RuntimeError("C2 tool freeze commit does not descend from preregistration")
    tool_blob_oid, frozen_tool = git_blob_at_commit(repository, args.freeze_commit, THIS_TOOL_URI)
    working_tool = (repository / THIS_TOOL_URI).read_bytes()
    if frozen_tool != working_tool:
        raise RuntimeError("C2 audit tool differs from frozen Git blob")
    original_tool_parent = correction["parents"]["originalAuditTool"]
    original_blob_oid, original_frozen_tool = git_blob_at_commit(
        repository, original_tool_parent["gitCommit"], original_tool_parent["uri"]
    )
    if sha_bytes(original_frozen_tool) != original_tool_parent["sha256"]:
        raise RuntimeError("original D12.8 audit Git blob mismatch")

    immutable_paths = {
        "spec": correction["parents"]["d12_8C1Spec"]["uri"],
        "preflight": correction["parents"]["preflight"]["uri"],
        "execution": correction["parents"]["execution"]["uri"],
        "result": correction["parents"]["result"]["uri"],
        "failed_audit": correction["parents"]["failedAudit"]["uri"],
        "failure": correction["parents"]["failure"]["uri"],
    }
    actual_paths = {
        "spec": args.spec,
        "preflight": args.preflight,
        "execution": args.execution,
        "result": args.result,
        "failed_audit": args.failed_audit,
        "failure": args.failure,
    }
    for name, expected_uri in immutable_paths.items():
        if actual_paths[name].resolve() != (repository / expected_uri).resolve():
            raise RuntimeError(f"C2 immutable input redirect: {name}")
    if args.root.resolve() != (repository / correction["parents"]["result"]["uri"]).resolve().parent:
        raise RuntimeError("C2 formal-root redirect")
    if args.output.resolve() != (repository / correction["outputs"]["audit"]).resolve():
        raise RuntimeError("C2 output redirect")
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D12.8 C2 audit")

    spec = read_json(args.spec)
    preflight = read_json(args.preflight)
    execution = read_json(args.execution)
    result = read_json(args.result)
    failed_audit = read_json(args.failed_audit)
    failure = read_json(args.failure)

    parent_checks = {
        "spec": parent_identity(correction, "d12_8C1Spec"),
        "preflight": parent_identity(correction, "preflight", "preflightHash"),
        "formalRootMarker": parent_identity(correction, "formalRootMarker"),
        "execution": parent_identity(correction, "execution", "executionHash"),
        "result": parent_identity(correction, "result", "evidenceHash"),
        "failedAudit": parent_identity(correction, "failedAudit", "auditHash"),
        "failure": parent_identity(correction, "failure", "failureHash"),
        "originalAuditTool": sha_bytes(original_frozen_tool) == original_tool_parent["sha256"],
    }
    runtime_ok = sha_file(Path(sys.executable)) == correction["runtime"]["pythonSha256"]
    preflight_ok = (
        preflight.get("status") == "ACCEPTED"
        and preflight.get("toolFreezeCommit") == correction["parents"]["preflight"]["toolFreezeCommit"]
        and preflight.get("checkPassed") in (None, len(preflight.get("checks", [])))
        and all(row.get("passed") is True for row in preflight.get("checks", []))
        and execution.get("toolHashes") == preflight.get("toolHashes")
    )
    result_ok, result_state = exact_result_state(correction, result)
    failed_audit_ok, failed_audit_state = exact_failed_audit_state(correction, failed_audit, result)
    process_ok, process_state = original_process_state(correction, execution, result, failed_audit, failure)
    raw_summary, raw_checks = raw_dual_state(correction, spec, args.root, result)
    negative_state_consistent = (
        result_state["falseChecks"] == sorted(correction["expectedNegativeState"]["falseResultChecks"])
        and raw_summary["riskPayloadIdentityFailures"] > 0
        and raw_summary["totalRiskScalarDifferences"] > 0
        and failed_audit_state["onlyFalseCheck"] == "DUAL_PAYLOAD_IDENTITY"
    )
    disk = shutil.disk_usage(repository)
    disk_ok = disk.free - correction["diskAdmission"]["projectedWriteBytes"] >= correction["diskAdmission"]["minimumReserveBytes"]
    own_pid_ok = os.getpid() not in [result.get("analyzerPid"), failed_audit.get("auditPid")] and os.getpid() not in [
        row.get("pid") for row in execution.get("children", [])
    ]

    projection = {
        "result": result_state,
        "failedAudit": failed_audit_state,
        "process": process_state,
        "rawDual": raw_summary,
    }
    attacks = mutation_attacks(projection)
    attack_ok = len(attacks) == 40 and all(row["passed"] for row in attacks)
    checks = [
        ("CORRECTION_SPEC_PREREGISTRATION_IDENTITY", prereg_blob_oid != "" and sha_bytes(prereg_blob) == CORRECTION_SPEC_SHA256),
        ("C2_TOOL_FROZEN_GIT_BLOB_IDENTITY", tool_blob_oid != "" and frozen_tool == working_tool),
        ("IMMUTABLE_PARENT_IDENTITIES", all(parent_checks.values())),
        ("RUNTIME_AND_PREFLIGHT_STATE", runtime_ok and preflight_ok),
        ("ORIGINAL_RESULT_NEGATIVE_STATE", result_ok),
        ("ORIGINAL_AUDIT_FAILURE_STATE", failed_audit_ok),
        ("ORIGINAL_74_PID_TOTALITY", process_ok and own_pid_ok),
        ("PYTHON_RESULT_PAYLOAD_IDENTITIES", raw_checks["pythonResultIdentity"]),
        ("NON_RISK_DUAL_PAYLOAD_IDENTITY", raw_checks["nonRiskDualIdentity"]),
        ("RISK_DIFFERENCE_ROSTER_STATE_REPLAY", raw_checks["riskDifferenceRoster"]),
        ("ZERO_DERIVED_DECISION_DIFFERENCE", raw_checks["zeroDecisionDifference"]),
        ("REPEAT_SUMMARY_IDENTITY", raw_checks["repeatSummaryIdentity"]),
        ("NEGATIVE_STATE_CONSISTENCY", negative_state_consistent),
        ("MUTATION_ROSTER_TOTALITY", attack_ok),
        ("DISK_ADMISSION", disk_ok),
        ("MODEL_NETWORK_ZERO", correction["operations"]["modelCalls"] == 0 and correction["operations"]["networkCalls"] == 0),
    ]
    passed = all(value for _, value in checks)
    body = {
        "schemaVersion": "bfs.blenderProjectiveMotionDisocclusionAdaptiveRiskAuditC2.v0.1",
        "experimentId": correction["experimentId"],
        "parentExperimentId": spec["experimentId"],
        "auditPid": os.getpid(),
        "passed": passed,
        "checks": [{"id": name, "passed": bool(value)} for name, value in checks],
        "checkPassed": sum(bool(value) for _, value in checks),
        "checkTotal": len(checks),
        "correction": {
            "spec": {"uri": CORRECTION_SPEC_URI, "sha256": CORRECTION_SPEC_SHA256, "gitBlobOid": prereg_blob_oid},
            "preregistrationCommit": CORRECTION_PREREGISTRATION_COMMIT,
            "tool": {"uri": THIS_TOOL_URI, "sha256": sha_bytes(working_tool), "gitBlobOid": tool_blob_oid},
            "toolFreezeCommit": args.freeze_commit,
            "originalAuditToolGitBlobOid": original_blob_oid,
        },
        "immutableResult": result_state,
        "immutableFailedAudit": failed_audit_state,
        "parentChecks": parent_checks,
        "processState": {
            **process_state,
            "c2AuditPid": os.getpid(),
            "recordedPidCountWithC2": process_state["originalPidCount"] + 1,
        },
        "rawDualReplay": raw_summary,
        "mutationAttacks": attacks,
        "mutationAttackPassed": sum(row["passed"] for row in attacks),
        "mutationAttackTotal": len(attacks),
        "diskAdmission": {
            "availableBytesBeforeWrite": disk.free,
            "projectedWriteBytes": correction["diskAdmission"]["projectedWriteBytes"],
            "minimumReserveBytes": correction["diskAdmission"]["minimumReserveBytes"],
            "projectedAvailableBytes": disk.free - correction["diskAdmission"]["projectedWriteBytes"],
        },
        "verdict": result.get("verdict"),
        "operationCounts": {
            "newAuditProcesses": 1,
            "newBlenderProcesses": 0,
            "newBlenderRenders": 0,
            "newAdapterProcesses": 0,
            "newConsumerProcesses": 0,
            "newEnvelopeProcesses": 0,
            "newAnalyzerProcesses": 0,
            "modelCalls": 0,
            "networkCalls": 0,
        },
        "nonClaims": correction["nonClaims"],
    }
    audit = {**body, "auditHash": canonical_hash(body)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(
        f"BFS_B52_D128_AUDIT_C2_{'PASS' if passed else 'FAIL'} "
        f"checks={audit['checkPassed']}/{audit['checkTotal']} "
        f"riskDifferences={raw_summary['totalRiskScalarDifferences']} "
        f"decisionDifferences={raw_summary['totalDerivedDecisionDifferences']}"
    )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
