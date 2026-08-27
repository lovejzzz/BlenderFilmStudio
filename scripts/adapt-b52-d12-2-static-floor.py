#!/usr/bin/env python3
"""Decode one B52-D12.2 multipart pair into canonical float32 arrays."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "fa63daa0c3b7b3f080a488aa0fc84996fd52cd731efce94ebe28bbc81b55d9d3"
FILES = {
    "previousRgba": "previous.rgba32",
    "currentRgba": "current.rgba32",
    "previousOwner": "previous-owner.f32",
    "currentOwner": "current-owner.f32",
    "vector": "vector.xy32",
    "vectorNext": "vector-next.xy32",
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
    parser.add_argument("--previous-exr", type=Path, required=True)
    parser.add_argument("--current-exr", type=Path, required=True)
    parser.add_argument("--previous-report", type=Path, required=True)
    parser.add_argument("--current-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def source_identity(path: Path, exr: Path, fixture: str, repeat: int, frame: int) -> dict:
    report = json.loads(path.read_text())
    body = {key: value for key, value in report.items() if key != "reportHash"}
    if report.get("reportHash") != canonical_hash(body):
        raise RuntimeError("D12.2 source self-hash mismatch")
    if report.get("fixtureId") != fixture or report.get("repeat") != repeat or report.get("frame") != frame or report.get("probeOnly") is not False:
        raise RuntimeError("D12.2 source cell mismatch")
    if report.get("output", {}).get("sha256") != sha256_file(exr):
        raise RuntimeError("D12.2 source EXR binding mismatch")
    return report


def load_multipart(path: Path, width: int, height: int, layer: str) -> dict:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    roster, channels, parts = [], {}, {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        image_spec = image.spec()
        name = str(image_spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        roster.append(name)
        channels[name] = list(image_spec.channelnames)
        parts[name] = pixels
    expected = [f"{layer}.Combined", f"{layer}.Depth", f"{layer}.Vector", f"{layer}.Object Index"]
    if roster != expected:
        raise RuntimeError(f"D12.2 multipart roster mismatch: {roster}")
    expected_channels = {
        f"{layer}.Combined": [f"{layer}.Combined.R", f"{layer}.Combined.G", f"{layer}.Combined.B", f"{layer}.Combined.A"],
        f"{layer}.Depth": [f"{layer}.Depth.Z"],
        f"{layer}.Vector": [f"{layer}.Vector.X", f"{layer}.Vector.Y", f"{layer}.Vector.Z", f"{layer}.Vector.W"],
        f"{layer}.Object Index": [f"{layer}.Object Index.X"],
    }
    if channels != expected_channels:
        raise RuntimeError("D12.2 channel layout mismatch")
    for name, count in ((expected[0], 4), (expected[1], 1), (expected[2], 4), (expected[3], 1)):
        if list(parts[name].shape) != [height, width, count] or not np.isfinite(parts[name]).all():
            raise RuntimeError(f"D12.2 shape/finite mismatch: {name}")
    return {"roster": roster, "channels": channels, "parts": parts}


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D12.2 spec identity mismatch")
    if sha256_file(Path(sys.executable)) != spec["runtime"]["python"]["sha256"]:
        raise RuntimeError("Python runtime identity mismatch")
    if oiio.VERSION_STRING != spec["runtime"]["python"]["openImageIO"] or np.__version__ != spec["runtime"]["python"]["numpy"]:
        raise RuntimeError("analysis library identity mismatch")
    fixture = next((row for row in spec["fixtures"] if row["id"] == args.fixture), None)
    if fixture is None:
        raise RuntimeError("fixture outside D12.2 roster")
    if args.output_dir.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite D12.2 adapter output")
    previous_report = source_identity(args.previous_report, args.previous_exr, args.fixture, args.repeat, 0)
    current_report = source_identity(args.current_report, args.current_exr, args.fixture, args.repeat, 1)
    width, height = fixture["resolution"]
    layer = spec["sceneContract"]["render"]["viewLayer"]
    previous = load_multipart(args.previous_exr, width, height, layer)
    current = load_multipart(args.current_exr, width, height, layer)
    arrays = {
        "previousRgba": previous["parts"][f"{layer}.Combined"],
        "currentRgba": current["parts"][f"{layer}.Combined"],
        "previousOwner": previous["parts"][f"{layer}.Object Index"][..., 0],
        "currentOwner": current["parts"][f"{layer}.Object Index"][..., 0],
        "vector": current["parts"][f"{layer}.Vector"][..., :2],
        "vectorNext": current["parts"][f"{layer}.Vector"][..., 2:4],
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, filename in FILES.items():
        payload = np.ascontiguousarray(arrays[name], dtype="<f4").tobytes(order="C")
        target = args.output_dir / filename
        target.write_bytes(payload)
        records[name] = {"uri": str(target), "sha256": sha256_bytes(payload), "bytes": len(payload), "shape": list(arrays[name].shape), "dtype": "little-endian-float32"}
    body = {
        "schemaVersion": "bfs.blenderStaticVectorFloorAdapterReport.v0.1",
        "experimentId": spec["experimentId"],
        "fixtureId": args.fixture,
        "repeat": args.repeat,
        "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha256_file(Path(sys.executable)), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "inputs": {
            "previousExr": {"uri": str(args.previous_exr), "sha256": previous_report["output"]["sha256"], "reportSha256": sha256_file(args.previous_report)},
            "currentExr": {"uri": str(args.current_exr), "sha256": current_report["output"]["sha256"], "reportSha256": sha256_file(args.current_report)},
        },
        "multipart": {"previousRoster": previous["roster"], "currentRoster": current["roster"], "channels": previous["channels"]},
        "arrays": records,
        "operationCounts": {"adapterProcesses": 1, "multipartExrsOpened": 2, "canonicalArraysWritten": len(FILES), "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D122_ADAPTER_OK fixture={args.fixture} repeat={args.repeat} vector={records['vector']['sha256']}")


if __name__ == "__main__":
    main()
