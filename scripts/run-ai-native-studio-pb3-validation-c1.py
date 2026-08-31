#!/usr/bin/env python3
"""C1 wrapper: enforce PB.3 root-size ceilings and exclusive process logs."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path


CORRECTION_SCHEMA = "bfs.aiNativeStudioPb3ValidationToolC1ResourceEnforcement.v0.3"
CORRECTION_STATUS = "FROZEN_INERT_C1_RESOURCE_ENFORCEMENT"


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
    require(index + 1 < len(sys.argv), f"{name} value is missing")
    value = sys.argv[index + 1]
    del sys.argv[index : index + 2]
    return value


def option_value(name: str) -> str:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    index = sys.argv.index(name)
    require(index + 1 < len(sys.argv), f"{name} value is missing")
    return sys.argv[index + 1]


def load_module(path: Path, expected_sha256: str, name: str):
    require(sha256_file(path) == expected_sha256, f"{name} SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {name}")
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


def write_bytes_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    correction_path = Path(extract_option("--correction-contract")).resolve(strict=True)
    correction = json.loads(correction_path.read_text(encoding="utf-8"))
    require(correction.get("schemaVersion") == CORRECTION_SCHEMA and correction.get("status") == CORRECTION_STATUS, "C1 correction contract is not exact")
    base_path = correction_path.parent.parent / correction["base"]["runner"]
    base = load_module(base_path, correction["base"]["runnerSha256"], "pb3_base_runner")
    require(sha256_file(Path(__file__)) == correction["tools"]["runnerWrapperSha256"], "C1 runner wrapper SHA-256 mismatch")

    if "--self-test" in sys.argv:
        checks = {
            "emptyRootSize": tree_file_bytes(correction_path.parent / "__pb3_c1_absent__") == 0,
            "baseSelfTestDelegated": True,
            "exclusiveFlagPresent": os.O_EXCL > 0,
        }
        require(all(checks.values()), "C1 self-test failed")
        result = base.main()
        require(result == 0, "base self-test failed")
        print(json.dumps({"status": "PASS", "c1Checks": checks}, sort_keys=True))
        return 0

    work_root = Path(option_value("--work-root"))
    evidence_root = Path(option_value("--evidence-root"))
    tool_path = Path(option_value("--tool-contract")).resolve(strict=True)
    execution_path = Path(option_value("--execution-contract")).resolve(strict=True)
    require(sha256_file(tool_path) == correction["base"]["toolFreezeSha256"], "base tool freeze SHA-256 mismatch")
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    require(execution.get("toolCorrection", {}).get("sha256") == sha256_file(correction_path), "execution does not bind C1 correction")
    ceilings = correction["resourceEnforcement"]
    original_write = base.write_exclusive
    original_run_process = base.run_process

    def c1_run_process(argv, cwd, env, stdout_path, stderr_path, timeout):
        require(not stdout_path.exists() and not stderr_path.exists(), "process log path must be fresh")
        started = time.monotonic()
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
        write_bytes_exclusive(stdout_path, result.stdout)
        write_bytes_exclusive(stderr_path, result.stderr)
        return {
            "argv": argv,
            "exitCode": result.returncode,
            "wallSeconds": time.monotonic() - started,
            "stdoutSha256": sha256_bytes(result.stdout),
            "stderrSha256": sha256_bytes(result.stderr),
        }

    def c1_write(path: Path, value: object) -> None:
        if isinstance(value, dict) and value.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationReceipt.v0.1":
            work_bytes = tree_file_bytes(work_root)
            evidence_before = tree_file_bytes(evidence_root)
            require(work_bytes <= ceilings["maximumWorkRootBytes"], "work root exceeds C1 ceiling")
            body = dict(value)
            body.pop("receiptHash", None)
            body["resourceEnforcement"] = {
                "correctionSha256": sha256_file(correction_path),
                "workRootBytes": work_bytes,
                "maximumWorkRootBytes": ceilings["maximumWorkRootBytes"],
                "evidenceRootBytesBeforeReceipt": evidence_before,
                "maximumEvidenceRootBytes": ceilings["maximumEvidenceRootBytes"],
                "processLogsWrittenExclusively": True,
                "symbolicPathsAllowed": False,
            }
            while True:
                body["resourceEnforcement"]["receiptBytes"] = len((json.dumps({**body, "receiptHash": "0" * 64}, indent=2, ensure_ascii=False) + "\n").encode())
                projected = evidence_before + body["resourceEnforcement"]["receiptBytes"]
                if body["resourceEnforcement"].get("projectedEvidenceRootBytes") == projected:
                    break
                body["resourceEnforcement"]["projectedEvidenceRootBytes"] = projected
            require(projected <= ceilings["maximumEvidenceRootBytes"], "evidence root exceeds C1 ceiling")
            body["receiptHash"] = sha256_bytes(canonical(body))
            original_write(path, body)
            return
        original_write(path, value)

    base.run_process = c1_run_process
    base.write_exclusive = c1_write
    result = base.main()
    receipt = json.loads((evidence_root / "receipt.json").read_text(encoding="utf-8"))
    resources = receipt["resourceEnforcement"]
    require(tree_file_bytes(work_root) == resources["workRootBytes"], "work root size changed after receipt")
    require(tree_file_bytes(evidence_root) == resources["projectedEvidenceRootBytes"], "evidence root projected size mismatch")
    return result


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_VALIDATION_C1_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
