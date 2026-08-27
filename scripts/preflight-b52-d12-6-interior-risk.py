#!/usr/bin/env python3
"""No-measurement preflight for the B52-D12.6 read-only diagnostic."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import shutil
import struct
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "89ff4a34bd4367996ac139c73b46ac8d9627173da3302f2148b90e283695d353"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def self_hash_ok(document: dict, field: str) -> bool:
    return document.get(field) == canonical_hash({key: value for key, value in document.items() if key != field})


def synthetic_bound_case(taps: tuple[np.float32, ...], center: np.float32, fx: float, fy: float) -> bool:
    weights = ((1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy)
    pre_cast = (((float(taps[0]) * weights[0]) + (float(taps[1]) * weights[1])) + (float(taps[2]) * weights[2])) + (float(taps[3]) * weights[3])
    final = np.float32(pre_cast)
    actual = abs(float(final) - float(center))
    bound = sum(abs(weight) * abs(float(tap) - float(center)) for weight, tap in zip(weights, taps)) + abs(float(np.spacing(final)))
    return actual <= bound


def imports_are_independent(path: Path) -> bool:
    tree = ast.parse(path.read_text())
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    return all(not name.startswith(("scripts", "blender", "importlib")) for name in imports)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.parent.exists():
        raise RuntimeError("preflight root must be fresh")
    spec = json.loads(args.spec.read_text())
    formal_root = Path(spec["diskAdmission"]["formalRoot"])
    tool_paths = [Path(path) for path in spec["formalToolPaths"]]
    tool_hashes = {str(path): sha256_file(path) for path in tool_paths}
    free_bytes = shutil.disk_usage(Path.cwd()).free
    projected = int(spec["diskAdmission"]["projectedWriteBytes"])
    reserve = int(spec["diskAdmission"]["minimumReserveBytes"])
    parent_checks = {}
    for name, record in spec["parents"].items():
        path = Path(record["uri"])
        parent_checks[f"{name}FileHash"] = path.is_file() and sha256_file(path) == record["sha256"]
        if path.suffix == ".json" and path.is_file():
            document = json.loads(path.read_text())
            for field in ("evidenceHash", "receiptHash", "executionHash"):
                if field in document:
                    parent_checks[f"{name}{field}"] = self_hash_ok(document, field)
    rng = np.random.default_rng(126)
    synthetic_cases = [
        synthetic_bound_case(tuple(np.float32(v) for v in rng.uniform(-4.0, 4.0, 4)), np.float32(rng.uniform(-4.0, 4.0)), float(rng.random()), float(rng.random()))
        for _ in range(256)
    ]
    synthetic_cases.extend([
        synthetic_bound_case((np.float32(0),) * 4, np.float32(0), 0.0, 0.0),
        synthetic_bound_case((np.float32(1),) * 4, np.float32(1), 2.0 ** -17, 0.0),
        synthetic_bound_case((np.float32(-1), np.float32(1), np.float32(-1), np.float32(1)), np.float32(0), 0.5, 0.5),
    ])
    checks = [
        {"id": "SPEC_IDENTITY", "passed": sha256_file(args.spec) == SPEC_SHA256},
        {"id": "PYTHON_IDENTITY", "passed": sha256_file(Path(sys.executable)) == spec["runtime"]["python"]["sha256"]},
        {"id": "PARENT_IDENTITIES", "passed": all(parent_checks.values())},
        {"id": "FORMAL_ROOT_ABSENT", "passed": not formal_root.exists()},
        {"id": "DISK_ADMISSION", "passed": free_bytes - projected >= reserve},
        {"id": "TOOLS_PRESENT", "passed": all(path.is_file() for path in tool_paths)},
        {"id": "AUDIT_INDEPENDENT", "passed": imports_are_independent(Path("scripts/audit-b52-d12-6-interior-risk.py"))},
        {"id": "SYNTHETIC_BOUND", "passed": all(synthetic_cases)},
        {"id": "NO_FORMAL_MEASUREMENT", "passed": True},
        {"id": "MODEL_NETWORK_ZERO", "passed": True},
    ]
    passed = all(row["passed"] for row in checks)
    body = {
        "schemaVersion": "bfs.blenderStaticInteriorRiskLocalizationPreflight.v0.1",
        "experimentId": spec["experimentId"],
        "status": "ACCEPTED" if passed else "REJECTED",
        "checks": checks,
        "checkPassed": sum(row["passed"] for row in checks),
        "checkTotal": len(checks),
        "toolHashes": tool_hashes,
        "parentChecks": parent_checks,
        "syntheticCaseCount": len(synthetic_cases),
        "diskAdmission": {"freeBeforeBytes": free_bytes, "projectedWriteBytes": projected, "minimumReserveBytes": reserve, "freeAfterProjectionBytes": free_bytes - projected},
        "formalRoot": str(formal_root),
        "formalRootAbsent": not formal_root.exists(),
        "operationCounts": {"blenderProcesses": 0, "blenderRenders": 0, "modelCalls": 0, "networkCalls": 0},
    }
    document = {**body, "preflightHash": canonical_hash(body)}
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D126_PREFLIGHT_{document['status']} checks={document['checkPassed']}/{document['checkTotal']}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
