#!/usr/bin/env python3
"""Python producer for the exploratory B52-D12.9-D1 Q30 curvature risk."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np


Q24 = 1 << 24
Q30 = 1 << 30
UINT32_MAX = (1 << 32) - 1


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def exact_scaled(value: float, scale: int, label: str) -> int:
    scaled = value * scale
    integer = int(scaled)
    if scaled != integer:
        raise RuntimeError(f"non-canonical {label}: {value!r}")
    return integer


def ceil_div(numerator: int, denominator: int) -> int:
    return (numerator + denominator - 1) // denominator


def validate_report(path: Path) -> dict:
    report = json.loads(path.read_text())
    body = {key: value for key, value in report.items() if key != "reportHash"}
    if report.get("reportHash") != canonical_hash(body):
        raise RuntimeError(f"report self-hash mismatch: {path}")
    return report


def load_array(path: Path, expected_sha: str, dtype: str, shape: tuple[int, ...]) -> np.ndarray:
    payload = path.read_bytes()
    if sha_bytes(payload) != expected_sha:
        raise RuntimeError(f"array hash mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy()


def main() -> None:
    args = arguments()
    if args.output_root.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite D12.9-D1 Python output")
    spec = json.loads(args.spec.read_text())
    if sha_file(Path(os.path.realpath(os.sys.executable))) != spec["runtime"]["python"]["sha256"] or np.__version__ != spec["runtime"]["python"]["numpy"]:
        raise RuntimeError("Python runtime identity mismatch")
    parent_spec = json.loads((Path.cwd() / spec["sourceEvidence"]["spec"]["uri"]).read_text())
    fixture_by_id = {row["id"]: row for row in parent_spec["fixtures"]}
    output_records: dict[str, object] = {}
    for fixture_id in spec["sourceEvidence"]["fixtures"]:
        fixture = fixture_by_id[fixture_id]
        width, height = fixture["resolution"]
        adapter_dir = args.source_root / "adapters" / fixture_id / "R1"
        consumer_dir = args.source_root / "consumers" / "python" / fixture_id / "R1"
        adapter = validate_report(adapter_dir / "report.json")
        consumer = validate_report(consumer_dir / "report.json")
        previous = load_array(adapter_dir / "arrays" / "previous.rgba32", adapter["arrays"]["previousRgba"]["sha256"], "<f4", (height, width, 4))
        previous_owner = load_array(adapter_dir / "arrays" / "previous-owner.f32", adapter["arrays"]["previousOwner"]["sha256"], "<f4", (height, width))
        vector = load_array(adapter_dir / "arrays" / "vector.xy32", adapter["arrays"]["vector"]["sha256"], "<f4", (height, width, 2))
        radius2 = load_array(consumer_dir / "arrays" / "radius2-interior.u8", consumer["arrays"]["radius2Interior"]["sha256"], "u1", (height, width))
        eligible = np.zeros((height, width), dtype=np.uint8)
        accepted = np.zeros((height, width), dtype=np.uint8)
        risk = np.zeros((height, width, 3), dtype="<u4")
        for y, x in zip(*np.nonzero(radius2)):
            qx = x + float(vector[y, x, 0])
            qy = y - float(vector[y, x, 1])
            x0, y0 = math.floor(qx), math.floor(qy)
            if x0 - 1 < 0 or x0 + 2 >= width or y0 - 1 < 0 or y0 + 2 >= height:
                continue
            owner = previous_owner[y0, x0]
            owner_support = previous_owner[y0 - 1:y0 + 3, x0 - 1:x0 + 3]
            alpha_support = previous[y0 - 1:y0 + 3, x0 - 1:x0 + 3, 3]
            if not np.all(owner_support == owner) or not np.all(alpha_support > np.float32(0.999)):
                continue
            fx = exact_scaled(qx - x0, Q24, "motion fraction x")
            fy = exact_scaled(qy - y0, Q24, "motion fraction y")
            eligible[y, x] = 1
            for channel in range(3):
                color = lambda yy, xx: exact_scaled(float(previous[yy, xx, channel]), Q30, "Q30 RGB")
                mx = max(
                    abs(color(yy, xx - 1) - 2 * color(yy, xx) + color(yy, xx + 1))
                    for yy in (y0, y0 + 1)
                    for xx in (x0, x0 + 1)
                )
                my = max(
                    abs(color(yy - 1, xx) - 2 * color(yy, xx) + color(yy + 1, xx))
                    for xx in (x0, x0 + 1)
                    for yy in (y0, y0 + 1)
                )
                numerator = 2 * (fx * (Q24 - fx) * mx + fy * (Q24 - fy) * my)
                units = ceil_div(numerator, Q24 * Q24) + spec["candidate"]["roundingAllowanceQ30"]
                risk[y, x, channel] = min(units, UINT32_MAX)
            accepted[y, x] = int(int(risk[y, x].max()) <= spec["candidate"]["riskThresholdQ30Inclusive"])
        fixture_dir = args.output_root / fixture_id
        fixture_dir.mkdir(parents=True, exist_ok=False)
        arrays = {}
        for name, array, filename, dtype_name in (
            ("eligible", eligible, "eligible.u8", "uint8"),
            ("accepted", accepted, "accepted.u8", "uint8"),
            ("riskQ30", risk, "risk.q30.u32", "little-endian-uint32"),
        ):
            payload = np.ascontiguousarray(array).tobytes()
            target = fixture_dir / filename
            target.write_bytes(payload)
            arrays[name] = {"uri": str(target), "sha256": sha_bytes(payload), "bytes": len(payload), "shape": list(array.shape), "dtype": dtype_name}
        output_records[fixture_id] = {
            "adapterReport": {"uri": str(adapter_dir / "report.json"), "sha256": sha_file(adapter_dir / "report.json"), "reportHash": adapter["reportHash"]},
            "consumerReport": {"uri": str(consumer_dir / "report.json"), "sha256": sha_file(consumer_dir / "report.json"), "reportHash": consumer["reportHash"]},
            "arrays": arrays,
            "counts": {"radius2": int(radius2.sum()), "eligible": int(eligible.sum()), "accepted": int(accepted.sum())},
        }
    body = {
        "schemaVersion": "bfs.blenderMotionAwareCurvatureRiskProducerReport.v0.1",
        "experimentId": spec["experimentId"],
        "producer": "python",
        "pid": os.getpid(),
        "candidate": spec["candidate"],
        "fixtures": output_records,
        "operationCounts": {"modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D129_D1_PYTHON_OK fixtures={len(output_records)}")


if __name__ == "__main__":
    main()
