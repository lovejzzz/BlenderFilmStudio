#!/usr/bin/env python3
"""Extract one B52-D12.8 multipart pair into canonical float32 arrays."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "67722b1c8fafa0b83518e6e467de1adb9ca88bd32b7145f15be2d5627767b4d4"
FILES = {
    "previousRgba": "previous.rgba32",
    "currentRgba": "current.rgba32",
    "previousDepth": "previous-depth.f32",
    "currentDepth": "current-depth.f32",
    "previousOwner": "previous-owner.f32",
    "currentOwner": "current-owner.f32",
    "vector": "vector.xy32",
    "vectorNext": "vector-next.xy32",
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


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


def expected_channels(layer: str) -> dict[str, list[str]]:
    return {
        f"{layer}.Combined": [f"{layer}.Combined.{channel}" for channel in ("R", "G", "B", "A")],
        f"{layer}.Depth": [f"{layer}.Depth.Z"],
        f"{layer}.Vector": [f"{layer}.Vector.{channel}" for channel in ("X", "Y", "Z", "W")],
        f"{layer}.Object Index": [f"{layer}.Object Index.X"],
    }


def load_multipart(exr_path: Path, fixture: dict, render: dict) -> dict:
    first = oiio.ImageBuf(str(exr_path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    roster, channels, parts = [], {}, {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(exr_path), index, 0)
        image_spec = image.spec()
        name = str(image_spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        roster.append(name)
        channels[name] = list(image_spec.channelnames)
        parts[name] = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
    layer = render["viewLayer"]
    if roster != render["expectedSubimages"] or channels != expected_channels(layer):
        raise RuntimeError("D12.8 multipart roster or channel layout mismatch")
    width, height = fixture["resolution"]
    for name, count in ((f"{layer}.Combined", 4), (f"{layer}.Depth", 1), (f"{layer}.Vector", 4), (f"{layer}.Object Index", 1)):
        if list(parts[name].shape) != [height, width, count] or not np.isfinite(parts[name]).all():
            raise RuntimeError(f"D12.8 multipart shape or finite mismatch: {name}")
    return {"roster": roster, "channels": channels, "parts": parts}


def source_identity(report_path: Path, exr_path: Path, fixture_id: str, repeat: int, frame: int) -> dict:
    report = json.loads(report_path.read_text())
    body = {key: value for key, value in report.items() if key != "reportHash"}
    if report.get("reportHash") != canonical_hash(body):
        raise RuntimeError("D12.8 source report self-hash mismatch")
    if report.get("probeOnly") is not False or report.get("fixtureId") != fixture_id or report.get("repeat") != repeat or report.get("frame") != frame:
        raise RuntimeError("D12.8 source cell mismatch")
    if report.get("output", {}).get("sha256") != sha_file(exr_path):
        raise RuntimeError("D12.8 source EXR binding mismatch")
    return report


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    if sha_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("D12.8 spec identity mismatch")
    if sha_file(Path(sys.executable)) != spec["runtime"]["python"]["sha256"]:
        raise RuntimeError("D12.8 Python identity mismatch")
    if oiio.VERSION_STRING != spec["runtime"]["python"]["openImageIO"] or np.__version__ != spec["runtime"]["python"]["numpy"]:
        raise RuntimeError("D12.8 analysis library identity mismatch")
    fixture = next((row for row in spec["fixtures"] if row["id"] == args.fixture), None)
    if fixture is None or args.output_dir.exists() or args.report.exists():
        raise RuntimeError("D12.8 fixture or adapter output invalid")
    previous_report = source_identity(args.previous_report, args.previous_exr, args.fixture, args.repeat, 0)
    current_report = source_identity(args.current_report, args.current_exr, args.fixture, args.repeat, 1)
    render = spec["sceneContract"]["render"]
    previous = load_multipart(args.previous_exr, fixture, render)
    current = load_multipart(args.current_exr, fixture, render)
    layer = render["viewLayer"]
    arrays = {
        "previousRgba": previous["parts"][f"{layer}.Combined"],
        "currentRgba": current["parts"][f"{layer}.Combined"],
        "previousDepth": previous["parts"][f"{layer}.Depth"][..., 0],
        "currentDepth": current["parts"][f"{layer}.Depth"][..., 0],
        "previousOwner": previous["parts"][f"{layer}.Object Index"][..., 0],
        "currentOwner": current["parts"][f"{layer}.Object Index"][..., 0],
        "vector": current["parts"][f"{layer}.Vector"][..., :2],
        "vectorNext": current["parts"][f"{layer}.Vector"][..., 2:4],
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, filename in FILES.items():
        payload = np.ascontiguousarray(arrays[name], dtype="<f4").tobytes()
        target = args.output_dir / filename
        target.write_bytes(payload)
        records[name] = {
            "uri": str(target),
            "sha256": sha_bytes(payload),
            "bytes": len(payload),
            "shape": list(arrays[name].shape),
            "dtype": "little-endian-float32",
        }
    body = {
        "schemaVersion": "bfs.blenderProjectiveMotionDisocclusionAdapterReport.v0.1",
        "experimentId": spec["experimentId"],
        "fixtureId": args.fixture,
        "repeat": args.repeat,
        "pid": os.getpid(),
        "runtime": {
            "python": sys.version.split()[0],
            "pythonExecutableSha256": sha_file(Path(sys.executable)),
            "openImageIO": oiio.VERSION_STRING,
            "numpy": np.__version__,
        },
        "inputs": {
            "previousExr": {"uri": str(args.previous_exr), "sha256": previous_report["output"]["sha256"], "reportSha256": sha_file(args.previous_report)},
            "currentExr": {"uri": str(args.current_exr), "sha256": current_report["output"]["sha256"], "reportSha256": sha_file(args.current_report)},
        },
        "multipart": {
            "previousRoster": previous["roster"],
            "currentRoster": current["roster"],
            "previousChannels": previous["channels"],
            "currentChannels": current["channels"],
        },
        "contract": spec["adapterContract"],
        "arrays": records,
        "operationCounts": {"adapterProcesses": 1, "multipartExrsOpened": 2, "canonicalArraysWritten": len(FILES), "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D128_ADAPTER_OK fixture={args.fixture} repeat={args.repeat} vector={records['vector']['sha256']}")


if __name__ == "__main__":
    main()
