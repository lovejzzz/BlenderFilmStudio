#!/usr/bin/env python3
"""Extract one B52-D12.12-H1 multipart source pair into canonical arrays."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "b0defadbd120f77dfe81bfa16d9dfd4e3a4d4a15ad1c8ddd1176d21f2e13b648"
FILES = {
    "previousRgba": "previous.rgba32",
    "currentRgba": "current.rgba32",
    "previousDepth": "previous-depth.f32",
    "currentDepth": "current-depth.f32",
    "previousOwner": "previous-owner.f32",
    "currentOwner": "current-owner.f32",
    "previousObjectIndex": "previous-object-index.f32",
    "currentObjectIndex": "current-object-index.f32",
    "vector": "vector.xy32",
    "vectorNext": "vector-next.xy32",
}


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
        f"{layer}.Material Index": [f"{layer}.Material Index.X"],
    }


def load_multipart(path: Path, fixture: dict, render: dict) -> dict:
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
    layer = render["viewLayer"]
    if roster != render["expectedSubimages"] or channels != expected_channels(layer):
        raise RuntimeError("D12.12-H1 multipart roster or channels mismatch")
    width, height = fixture["resolution"]
    for name, count in ((f"{layer}.Combined", 4), (f"{layer}.Depth", 1), (f"{layer}.Vector", 4), (f"{layer}.Object Index", 1), (f"{layer}.Material Index", 1)):
        if list(parts[name].shape) != [height, width, count] or not np.isfinite(parts[name]).all():
            raise RuntimeError(f"D12.12-H1 multipart shape or finite mismatch: {name}")
    return {"roster": roster, "channels": channels, "parts": parts}


def source_identity(report_path: Path, exr_path: Path, fixture_id: str, repeat: int, frame: int) -> dict:
    report = json.loads(report_path.read_text())
    body = {key: value for key, value in report.items() if key != "reportHash"}
    if report.get("reportHash") != canonical_hash(body):
        raise RuntimeError("D12.12-H1 source report self-hash mismatch")
    if report.get("probeOnly") is not False or report.get("fixtureId") != fixture_id or report.get("repeat") != repeat or report.get("frame") != frame:
        raise RuntimeError("D12.12-H1 source cell mismatch")
    if report.get("output", {}).get("sha256") != sha_file(exr_path):
        raise RuntimeError("D12.12-H1 source EXR binding mismatch")
    return report


def main() -> None:
    cli = arguments()
    if sha_file(cli.spec) != SPEC_SHA256 or cli.output_dir.exists() or cli.report.exists():
        raise RuntimeError("D12.12-H1 spec identity or fresh adapter output violation")
    spec = json.loads(cli.spec.read_text())
    runtime = spec["runtime"]["python"]
    if sha_file(Path(sys.executable)) != runtime["sha256"] or oiio.VERSION_STRING != runtime["openImageIO"] or np.__version__ != runtime["numpy"]:
        raise RuntimeError("D12.12-H1 adapter runtime identity mismatch")
    fixture = next((row for row in spec["fixtures"] if row["id"] == cli.fixture), None)
    if fixture is None:
        raise RuntimeError("unknown D12.12-H1 fixture")
    previous_report = source_identity(cli.previous_report, cli.previous_exr, cli.fixture, cli.repeat, 0)
    current_report = source_identity(cli.current_report, cli.current_exr, cli.fixture, cli.repeat, 1)
    render = spec["sceneContract"]["render"]
    previous = load_multipart(cli.previous_exr, fixture, render)
    current = load_multipart(cli.current_exr, fixture, render)
    layer = render["viewLayer"]
    arrays = {
        "previousRgba": previous["parts"][f"{layer}.Combined"],
        "currentRgba": current["parts"][f"{layer}.Combined"],
        "previousDepth": previous["parts"][f"{layer}.Depth"][..., 0],
        "currentDepth": current["parts"][f"{layer}.Depth"][..., 0],
        "previousOwner": previous["parts"][f"{layer}.Material Index"][..., 0],
        "currentOwner": current["parts"][f"{layer}.Material Index"][..., 0],
        "previousObjectIndex": previous["parts"][f"{layer}.Object Index"][..., 0],
        "currentObjectIndex": current["parts"][f"{layer}.Object Index"][..., 0],
        "vector": current["parts"][f"{layer}.Vector"][..., :2],
        "vectorNext": current["parts"][f"{layer}.Vector"][..., 2:4],
    }
    declared_material = {0.0, *(float(owner["materialPassIndex"]) for owner in fixture["owners"])}
    declared_object = {0.0, float(fixture["owners"][0]["objectPassIndex"])}
    for name in ("previousOwner", "currentOwner"):
        if not set(float(value) for value in np.unique(arrays[name])).issubset(declared_material):
            raise RuntimeError(f"D12.12-H1 undeclared Material Index: {name}")
    for name in ("previousObjectIndex", "currentObjectIndex"):
        if not set(float(value) for value in np.unique(arrays[name])).issubset(declared_object):
            raise RuntimeError(f"D12.12-H1 Object Index negative control mismatch: {name}")
    cli.output_dir.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, filename in FILES.items():
        payload = np.ascontiguousarray(arrays[name], dtype="<f4").tobytes()
        target = cli.output_dir / filename
        target.write_bytes(payload)
        records[name] = {"uri": str(target), "sha256": sha_bytes(payload), "bytes": len(payload), "shape": list(arrays[name].shape), "dtype": "little-endian-float32"}
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerOneSidedCurvatureHoldoutAdapterReport.v0.1",
        "experimentId": spec["experimentId"],
        "specSha256": SPEC_SHA256,
        "fixtureId": cli.fixture,
        "repeat": cli.repeat,
        "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha_file(Path(sys.executable)), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "inputs": {
            "previousExr": {"uri": str(cli.previous_exr), "sha256": previous_report["output"]["sha256"], "reportSha256": sha_file(cli.previous_report)},
            "currentExr": {"uri": str(cli.current_exr), "sha256": current_report["output"]["sha256"], "reportSha256": sha_file(cli.current_report)},
        },
        "multipart": {"previousRoster": previous["roster"], "currentRoster": current["roster"], "previousChannels": previous["channels"], "currentChannels": current["channels"]},
        "arrays": records,
        "operationCounts": {"adapterProcesses": 1, "multipartExrsOpened": 2, "canonicalArraysWritten": len(FILES), "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    cli.report.parent.mkdir(parents=True, exist_ok=True)
    cli.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1212H1_ADAPTER_OK fixture={cli.fixture} repeat={cli.repeat} owner={records['currentOwner']['sha256']}")


if __name__ == "__main__":
    main()
