#!/usr/bin/env python3
"""Independent PB.3 evidence auditor; never imports engine modules or starts Blender."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--engine-source", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--tool-contract", type=Path, required=True)
    parser.add_argument("--execution-contract", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def valid_self(document: dict, field: str) -> bool:
    copy = dict(document)
    claimed = copy.pop(field, None)
    return isinstance(claimed, str) and claimed == sha256_bytes(canonical(copy))


def write_exclusive(path: Path, value: object) -> None:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def git(args: list[str], cwd: Path, binary: bool = False):
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=not binary)
    return result.stdout if binary else result.stdout.strip()


def snapshot_without_expert(value: dict) -> dict:
    return {key: item for key, item in value.items() if key != "expertMode"}


def expected_state(row: dict) -> dict:
    mapping = row["workspaceMapping"]
    return {
        "schemaVersion": "bfs.filmWorkspace.v0.1",
        "project": mapping["project"],
        "scene": mapping["scene"],
        "character": mapping["character"],
        "shots": [{**mapping["shot"], "camera": mapping["cameraObject"]}],
        "activeShotIndex": 0,
        "expertMode": False,
        "sceneCamera": mapping["cameraObject"],
        "contractStatus": "COMPILED",
        "contractProposalId": row["proposalId"],
        "contractApprovalScope": "COMPILE_BUILD_PLAN / WRITE_BUILD_PLAN only",
        "contractOutputUri": row["outputUri"],
        "contractPlanHash": row["planHash"],
        "planHash": row["planHash"],
        "sceneSpecHash": row["sceneCanonicalSha256"],
        "structureHash": row["semanticStructureSha256"],
        "structureIdentityVersion": "bfs.semanticSceneStructure.v0.2",
        "productBuildHash": row["productBuildHash"],
    }


def probe_exact(document: dict, row: dict, stage: str) -> bool:
    if not valid_self(document, "receiptHash") or document.get("status") != "PASS" or document.get("fixtureId") != row["id"] or document.get("stage") != stage:
        return False
    if document.get("counts") != {"blenderStarts": 1, "renders": 0, "networkCalls": 0}:
        return False
    expected = expected_state(row)
    if stage == "build":
        final = document.get("final")
        roundtrip = document.get("roundtrip", {})
        artifacts = document.get("artifacts", {})
        return (
            final == expected
            and roundtrip.get("before") == expected
            and roundtrip.get("after") == expected
            and roundtrip.get("expert", {}).get("expertMode") is True
            and snapshot_without_expert(roundtrip.get("expert", {})) == snapshot_without_expert(expected)
            and artifacts.get("buildPlan", {}).get("sha256") == row["buildPlanFileSha256"]
            and artifacts.get("structure", {}).get("sha256") == row["semanticStructureSha256"]
        )
    roundtrip = document.get("roundtrip", {})
    return (
        document.get("before") == expected
        and document.get("after") == expected
        and roundtrip.get("before") == expected
        and roundtrip.get("after") == expected
        and roundtrip.get("expert", {}).get("expertMode") is True
        and snapshot_without_expert(roundtrip.get("expert", {})) == snapshot_without_expert(expected)
    )


def main() -> int:
    args = arguments()
    root = args.repository_root.resolve(strict=True)
    engine = args.engine_source.resolve(strict=True)
    binary = args.binary.resolve(strict=True)
    tool = read_json(args.tool_contract)
    execution = read_json(args.execution_contract)
    receipt = read_json(args.receipt)
    evidence = Path(receipt.get("evidenceRoot", ""))
    work = Path(receipt.get("workRoot", ""))
    rows = {row["id"]: row for row in tool.get("fixtures", [])}
    probes = {}
    for fixture_id in ("B01", "B02"):
        probes[(fixture_id, "build")] = read_json(evidence / fixture_id.lower() / "build.json")
        probes[(fixture_id, "reopen")] = read_json(evidence / fixture_id.lower() / "reopen.json")

    execution_oid = receipt.get("executionCommit", "")
    contract_uri = args.execution_contract.resolve(strict=True).relative_to(root).as_posix()
    expected_counts = {
        "blenderStarts": 4, "proposalExecutions": 2, "buildPlanWrites": 2,
        "sceneBuilds": 2, "workspaceSaves": 2, "reopens": 2, "renders": 0,
        "engineSourceEdits": 0, "engineRemoteWrites": 0, "networkCalls": 0,
    }
    process_rows = receipt.get("processes", [])
    checks = {
        "receiptSelfHash": valid_self(receipt, "receiptHash"),
        "receiptPass": receipt.get("status") == "PASS",
        "toolBinding": receipt.get("toolFreezeSha256") == sha256_file(args.tool_contract),
        "executionCommitExists": bool(execution_oid) and git(["cat-file", "-t", execution_oid], root) == "commit",
        "executionParentExact": bool(execution_oid) and git(["rev-parse", f"{execution_oid}^"], root) == execution.get("executionParentResearchCommit"),
        "executionBytesExact": bool(execution_oid) and git(["show", f"{execution_oid}:{contract_uri}"], root, binary=True) == args.execution_contract.read_bytes(),
        "sourceIdentity": git(["rev-parse", "HEAD"], engine) == tool.get("source", {}).get("head") and git(["status", "--porcelain"], engine) == "",
        "binaryIdentity": sha256_file(binary) == tool.get("binary", {}).get("sha256"),
        "countsExact": receipt.get("counts") == expected_counts,
        "processCount": len(process_rows) == 4,
        "processesExitZero": len(process_rows) == 4 and all(row.get("exitCode") == 0 for row in process_rows),
        "processesOffline": len(process_rows) == 4 and all("--offline-mode" in row.get("argv", []) and "--disable-autoexec" in row.get("argv", []) for row in process_rows),
        "probeRoster": set(probes) == {("B01", "build"), ("B01", "reopen"), ("B02", "build"), ("B02", "reopen")},
        "probesExact": all(probe_exact(probes[(fixture_id, stage)], rows[fixture_id], stage) for fixture_id in ("B01", "B02") for stage in ("build", "reopen")),
        "buildPlansExact": all(sha256_file(work / fixture_id.lower() / rows[fixture_id]["outputUri"]) == rows[fixture_id]["buildPlanFileSha256"] for fixture_id in ("B01", "B02")),
        "semanticStructuresExact": all(sha256_file(work / fixture_id.lower() / rows[fixture_id]["artifactRoot"] / "scene.structure.canonical.json") == rows[fixture_id]["semanticStructureSha256"] for fixture_id in ("B01", "B02")),
        "noRenderArtifacts": not any(path.suffix.lower() in {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"} for path in work.rglob("*") if path.is_file()),
        "claimCeilingExact": receipt.get("claimCeiling") == tool.get("claimCeiling"),
    }
    passed = sum(bool(value) for value in checks.values())
    audit = {
        "schemaVersion": "bfs.aiNativeStudioPb3ValidationIndependentAudit.v0.1",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "independence": "Does not import engine modules, execute proposals or start Blender.",
        "checks": checks,
        "counts": {"passed": passed, "total": len(checks), "blenderStarts": 0, "renders": 0, "networkCalls": 0, "engineSourceEdits": 0, "engineRemoteWrites": 0},
        "receipt": {"uri": str(args.receipt), "sha256": sha256_file(args.receipt), "receiptHash": receipt.get("receiptHash")},
        "claimCeiling": tool.get("claimCeiling"),
    }
    audit["auditHash"] = sha256_bytes(canonical(audit))
    write_exclusive(args.output, audit)
    print(f"PB3_AUDIT {audit['status']} {passed}/{len(checks)} auditHash={audit['auditHash']}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
