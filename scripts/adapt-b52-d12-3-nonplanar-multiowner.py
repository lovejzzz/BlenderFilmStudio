#!/usr/bin/env python3
"""Decode one B52-D12.3 multipart pair into canonical float32 arrays."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "f1ffe5b4fe0912936b1e03677dd0985f11c34e6b5df4ddf70854533c4ad0b590"
FILES = {"previousRgba": "previous.rgba32", "currentRgba": "current.rgba32", "previousOwner": "previous-owner.f32", "currentOwner": "current-owner.f32", "vector": "vector.xy32", "vectorNext": "vector-next.xy32"}


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


def source(path: Path, exr: Path, fixture: str, repeat: int, frame: int) -> dict:
    report = json.loads(path.read_text())
    body = {key: value for key, value in report.items() if key != "reportHash"}
    if report.get("reportHash") != canonical_hash(body) or report.get("fixtureId") != fixture or report.get("repeat") != repeat or report.get("frame") != frame or report.get("probeOnly") is not False:
        raise RuntimeError("D12.3 source identity mismatch")
    if report.get("output", {}).get("sha256") != sha256_file(exr):
        raise RuntimeError("D12.3 source EXR binding mismatch")
    return report


def multipart(path: Path, width: int, height: int, layer: str) -> dict:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    roster, channels, parts = [], {}, {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        image_spec = image.spec()
        name = str(image_spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        roster.append(name)
        channels[name] = list(image_spec.channelnames)
        parts[name] = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
    expected = [f"{layer}.Combined", f"{layer}.Depth", f"{layer}.Vector", f"{layer}.Object Index"]
    expected_channels = {expected[0]: [f"{expected[0]}.R", f"{expected[0]}.G", f"{expected[0]}.B", f"{expected[0]}.A"], expected[1]: [f"{expected[1]}.Z"], expected[2]: [f"{expected[2]}.X", f"{expected[2]}.Y", f"{expected[2]}.Z", f"{expected[2]}.W"], expected[3]: [f"{expected[3]}.X"]}
    if roster != expected or channels != expected_channels:
        raise RuntimeError("D12.3 multipart roster/channel mismatch")
    for name, count in ((expected[0], 4), (expected[1], 1), (expected[2], 4), (expected[3], 1)):
        if list(parts[name].shape) != [height, width, count] or not np.isfinite(parts[name]).all():
            raise RuntimeError(f"D12.3 multipart shape/finite mismatch: {name}")
    return {"roster": roster, "channels": channels, "parts": parts}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--fixture", required=True); parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--previous-exr", type=Path, required=True); parser.add_argument("--current-exr", type=Path, required=True)
    parser.add_argument("--previous-report", type=Path, required=True); parser.add_argument("--current-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True); parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    if sha256_file(args.spec) != SPEC_SHA256 or sha256_file(Path(sys.executable)) != spec["runtime"]["python"]["sha256"]:
        raise RuntimeError("D12.3 spec/Python identity mismatch")
    if oiio.VERSION_STRING != spec["runtime"]["python"]["openImageIO"] or np.__version__ != spec["runtime"]["python"]["numpy"]:
        raise RuntimeError("D12.3 library identity mismatch")
    fixture = next((row for row in spec["fixtures"] if row["id"] == args.fixture), None)
    if fixture is None or args.output_dir.exists() or args.report.exists():
        raise RuntimeError("D12.3 fixture invalid or output exists")
    previous_report = source(args.previous_report, args.previous_exr, args.fixture, args.repeat, 0)
    current_report = source(args.current_report, args.current_exr, args.fixture, args.repeat, 1)
    width, height = fixture["resolution"]
    layer = spec["sceneContract"]["render"]["viewLayer"]
    previous, current = multipart(args.previous_exr, width, height, layer), multipart(args.current_exr, width, height, layer)
    arrays = {"previousRgba": previous["parts"][f"{layer}.Combined"], "currentRgba": current["parts"][f"{layer}.Combined"], "previousOwner": previous["parts"][f"{layer}.Object Index"][..., 0], "currentOwner": current["parts"][f"{layer}.Object Index"][..., 0], "vector": current["parts"][f"{layer}.Vector"][..., :2], "vectorNext": current["parts"][f"{layer}.Vector"][..., 2:4]}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, filename in FILES.items():
        payload = np.ascontiguousarray(arrays[name], dtype="<f4").tobytes(order="C")
        target = args.output_dir / filename; target.write_bytes(payload)
        records[name] = {"uri": str(target), "sha256": sha256_bytes(payload), "bytes": len(payload), "shape": list(arrays[name].shape), "dtype": "little-endian-float32"}
    body = {"schemaVersion": "bfs.blenderStaticNonplanarMultiownerAdapterReport.v0.1", "experimentId": spec["experimentId"], "fixtureId": args.fixture, "repeat": args.repeat, "pid": os.getpid(), "runtime": {"pythonExecutableSha256": sha256_file(Path(sys.executable)), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__}, "inputs": {"previousExr": {"uri": str(args.previous_exr), "sha256": previous_report["output"]["sha256"]}, "currentExr": {"uri": str(args.current_exr), "sha256": current_report["output"]["sha256"]}}, "multipart": {"previousRoster": previous["roster"], "currentRoster": current["roster"], "channels": previous["channels"]}, "arrays": records, "operationCounts": {"adapterProcesses": 1, "multipartExrsOpened": 2, "canonicalArraysWritten": len(FILES), "modelCalls": 0, "networkCalls": 0}}
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True); args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D123_ADAPTER_OK fixture={args.fixture} repeat={args.repeat} vector={records['vector']['sha256']}")


if __name__ == "__main__":
    main()
