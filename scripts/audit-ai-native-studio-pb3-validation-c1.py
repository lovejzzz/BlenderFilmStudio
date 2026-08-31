#!/usr/bin/env python3
"""C1 independent-audit wrapper for PB.3 resource and exclusive-write evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path


CORRECTION_SCHEMA = "bfs.aiNativeStudioPb3ValidationToolC1ResourceEnforcement.v0.3"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def extract_option(name: str) -> str:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    index = sys.argv.index(name)
    require(index + 1 < len(sys.argv), f"{name} value missing")
    value = sys.argv[index + 1]
    del sys.argv[index : index + 2]
    return value


def option_value(name: str) -> str:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    return sys.argv[sys.argv.index(name) + 1]


def load_module(path: Path, expected_sha256: str):
    require(sha256_file(path) == expected_sha256, "base auditor SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location("pb3_base_auditor", path)
    require(spec is not None and spec.loader is not None, "cannot load base auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tree_file_bytes(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        require(not path.is_symlink(), f"resource root contains symbolic path: {path}")
        if path.is_file():
            total += path.stat().st_size
    return total


def main() -> int:
    correction_path = Path(extract_option("--correction-contract")).resolve(strict=True)
    correction = json.loads(correction_path.read_text(encoding="utf-8"))
    require(correction.get("schemaVersion") == CORRECTION_SCHEMA, "C1 correction schema mismatch")
    require(correction.get("status") == "FROZEN_INERT_C1_RESOURCE_ENFORCEMENT", "C1 correction status mismatch")
    base_path = correction_path.parent.parent / correction["base"]["independentAuditor"]
    base = load_module(base_path, correction["base"]["independentAuditorSha256"])
    require(sha256_file(Path(__file__)) == correction["tools"]["independentAuditorWrapperSha256"], "C1 auditor wrapper SHA-256 mismatch")
    receipt_path = Path(option_value("--receipt")).resolve(strict=True)
    output_path = Path(option_value("--output"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    work_root = Path(receipt["workRoot"])
    evidence_root = Path(receipt["evidenceRoot"])
    ceilings = correction["resourceEnforcement"]
    original_write = base.write_exclusive

    def c1_write(path: Path, value: object) -> None:
        if isinstance(value, dict) and value.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationIndependentAudit.v0.1":
            body = dict(value)
            body.pop("auditHash", None)
            checks = dict(body["checks"])
            resources = receipt.get("resourceEnforcement", {})
            work_bytes = tree_file_bytes(work_root)
            evidence_before = tree_file_bytes(evidence_root)
            correction_sha = sha256_file(correction_path)
            checks.update({
                "c1CorrectionBinding": resources.get("correctionSha256") == correction_sha,
                "c1WorkRootBytesExact": resources.get("workRootBytes") == work_bytes,
                "c1WorkRootWithinCeiling": work_bytes <= ceilings["maximumWorkRootBytes"] == resources.get("maximumWorkRootBytes"),
                "c1EvidenceBeforeAuditExact": evidence_before == resources.get("projectedEvidenceRootBytes"),
                "c1EvidenceWithinCeilingBeforeAudit": evidence_before <= ceilings["maximumEvidenceRootBytes"] == resources.get("maximumEvidenceRootBytes"),
                "c1ExclusiveLogClaim": resources.get("processLogsWrittenExclusively") is True,
                "c1NoSymbolicPaths": resources.get("symbolicPathsAllowed") is False,
            })
            body["checks"] = checks
            passed = sum(bool(item) for item in checks.values())
            body["status"] = "PASS" if passed == len(checks) else "FAIL"
            body["counts"] = {**body["counts"], "passed": passed, "total": len(checks)}
            body["resourceAudit"] = {
                "correctionSha256": correction_sha,
                "workRootBytes": work_bytes,
                "evidenceRootBytesBeforeAudit": evidence_before,
                "maximumWorkRootBytes": ceilings["maximumWorkRootBytes"],
                "maximumEvidenceRootBytes": ceilings["maximumEvidenceRootBytes"],
            }
            while True:
                body["resourceAudit"]["auditBytes"] = len((json.dumps({**body, "auditHash": "0" * 64}, indent=2, ensure_ascii=False) + "\n").encode())
                projected = evidence_before + body["resourceAudit"]["auditBytes"]
                if body["resourceAudit"].get("projectedEvidenceRootBytesAfterAudit") == projected:
                    break
                body["resourceAudit"]["projectedEvidenceRootBytesAfterAudit"] = projected
            require(projected <= ceilings["maximumEvidenceRootBytes"], "audit would exceed evidence ceiling")
            body["auditHash"] = sha256_bytes(canonical(body))
            original_write(path, body)
            return
        original_write(path, value)

    base.write_exclusive = c1_write
    result = base.main()
    audit = json.loads(output_path.read_text(encoding="utf-8"))
    require(tree_file_bytes(evidence_root) == audit["resourceAudit"]["projectedEvidenceRootBytesAfterAudit"], "final evidence size mismatch")
    return result


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_AUDIT_C1_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
