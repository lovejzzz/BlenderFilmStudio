#!/usr/bin/env python3
"""Scalar Python static bilinear consumer for B52-D12.2."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "fa63daa0c3b7b3f080a488aa0fc84996fd52cd731efce94ebe28bbc81b55d9d3"
INPUTS = {
    "previousRgba": ("previous.rgba32", 4),
    "currentRgba": ("current.rgba32", 4),
    "previousOwner": ("previous-owner.f32", 1),
    "currentOwner": ("current-owner.f32", 1),
    "vector": ("vector.xy32", 2),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--adapter-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D12.2 spec identity mismatch")
    if sha256_file(Path(sys.executable)) != spec["runtime"]["python"]["sha256"] or np.__version__ != spec["runtime"]["python"]["numpy"]:
        raise RuntimeError("Python runtime identity mismatch")
    fixture = next((row for row in spec["fixtures"] if row["id"] == args.fixture), None)
    if fixture is None:
        raise RuntimeError("fixture outside D12.2 roster")
    if args.output_dir.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite D12.2 consumer output")
    adapter = json.loads(args.adapter_report.read_text())
    adapter_body = {key: value for key, value in adapter.items() if key != "reportHash"}
    if adapter.get("reportHash") != canonical_hash(adapter_body) or adapter.get("fixtureId") != args.fixture or adapter.get("repeat") != args.repeat:
        raise RuntimeError("D12.2 adapter identity mismatch")
    width, height = fixture["resolution"]
    arrays = {}
    for name, (filename, channels) in INPUTS.items():
        path = args.input_dir / filename
        payload = path.read_bytes()
        if sha256_bytes(payload) != adapter["arrays"][name]["sha256"]:
            raise RuntimeError(f"D12.2 adapter array mismatch: {name}")
        shape = (height, width, channels) if channels > 1 else (height, width)
        arrays[name] = np.frombuffer(payload, dtype="<f4").reshape(shape).copy()

    previous = arrays["previousRgba"]
    current = arrays["currentRgba"]
    reconstructed = current.copy()
    valid = np.zeros((height, width), dtype=np.uint8)
    owner_id = np.float32(fixture["passIndex"])
    margin = 4
    for y in range(margin, height - margin):
        for x in range(margin, width - margin):
            if arrays["currentOwner"][y, x] != owner_id or current[y, x, 3] <= np.float32(0.999):
                continue
            vector_x, vector_y = float(arrays["vector"][y, x, 0]), float(arrays["vector"][y, x, 1])
            qx, qy = x + vector_x, y - vector_y
            x0, y0 = math.floor(qx), math.floor(qy)
            x1, y1 = x0 + 1, y0 + 1
            if x0 < 0 or y0 < 0 or x1 >= width or y1 >= height:
                continue
            taps = ((y0, x0), (y0, x1), (y1, x0), (y1, x1))
            if not all(arrays["previousOwner"][ty, tx] == owner_id and previous[ty, tx, 3] > np.float32(0.999) for ty, tx in taps):
                continue
            fx, fy = qx - x0, qy - y0
            w0, w1, w2, w3 = (1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy
            for channel in range(4):
                v0, v1 = float(previous[y0, x0, channel]), float(previous[y0, x1, channel])
                v2, v3 = float(previous[y1, x0, channel]), float(previous[y1, x1, channel])
                reconstructed[y, x, channel] = np.float32((((v0 * w0) + (v1 * w1)) + (v2 * w2)) + (v3 * w3))
            valid[y, x] = 1

    args.output_dir.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, filename, array, dtype in (
        ("reconstructed", "reconstructed.rgba32", reconstructed, "little-endian-float32"),
        ("valid", "valid.u8", valid, "uint8"),
    ):
        payload = np.ascontiguousarray(array, dtype="<f4" if name == "reconstructed" else "u1").tobytes(order="C")
        target = args.output_dir / filename
        target.write_bytes(payload)
        records[name] = {"uri": str(target), "sha256": sha256_bytes(payload), "bytes": len(payload), "shape": list(array.shape), "dtype": dtype}
    report = {
        "schemaVersion": "bfs.blenderStaticVectorFloorConsumerReport.v0.1",
        "experimentId": spec["experimentId"],
        "producer": "python",
        "fixtureId": args.fixture,
        "repeat": args.repeat,
        "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha256_file(Path(sys.executable)), "numpy": np.__version__},
        "adapter": {"uri": str(args.adapter_report), "sha256": sha256_file(args.adapter_report), "reportHash": adapter["reportHash"]},
        "contract": spec["consumer"],
        "arrays": records,
        "integrity": "external dual typed-envelope sidecars",
        "operationCounts": {"consumerProcesses": 1, "pixelsVisited": width * height, "modelCalls": 0, "networkCalls": 0},
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D122_CONSUMER_PY_OK fixture={args.fixture} repeat={args.repeat} valid={int(valid.sum())}")


if __name__ == "__main__":
    main()
