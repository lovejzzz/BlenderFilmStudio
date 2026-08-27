#!/usr/bin/env python3
"""Extract frozen Blender multipart passes into D9.1 canonical raw arrays."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "11686c5e796c7bc1b4e45cf137c3d98347bc65bfec428f9d19545b55430f584b"
FILES = {
    "previousRgba": "previous.rgba32",
    "currentRgba": "current.rgba32",
    "previousDepth": "previous-depth.f32",
    "currentDepth": "current-depth.f32",
    "previousLayer": "previous-layer.f32",
    "currentLayer": "current-layer.f32",
    "motion": "motion.xy32",
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
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
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


def load_multipart(path: Path, render: dict) -> dict:
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
    if roster != render["expectedSubimages"] or channels != render["expectedChannels"]:
        raise RuntimeError("multipart roster or channel layout mismatch")
    height, width = render["resolution"][1], render["resolution"][0]
    for name, count in (("BFS_F32_MASTER.Combined", 4), ("BFS_F32_MASTER.Depth", 1), ("BFS_F32_MASTER.Vector", 4), ("BFS_F32_MASTER.Object Index", 1)):
        if list(parts[name].shape) != [height, width, count] or not np.isfinite(parts[name]).all():
            raise RuntimeError(f"multipart shape or finite mismatch: {name}")
    return {"roster": roster, "channels": channels, "parts": parts}


def source_identity(report_path: Path, exr_path: Path, fixture: str, repeat: int, frame: int) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    body = {key: value for key, value in report.items() if key != "reportHash"}
    if report.get("reportHash") != canonical_hash(body):
        raise RuntimeError("source report self-hash mismatch")
    if report.get("fixtureId") != fixture or report.get("repeat") != repeat or report.get("frame") != frame:
        raise RuntimeError("source report cell mismatch")
    if report["output"]["sha256"] != sha256_file(exr_path):
        raise RuntimeError("source report EXR binding mismatch")
    return report


def encoded(array: np.ndarray) -> bytes:
    return np.ascontiguousarray(array, dtype="<f4").tobytes(order="C")


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D10.1 spec identity mismatch")
    if sha256_file(Path(sys.executable)) != spec["runtime"]["python"]["sha256"]:
        raise RuntimeError("Python runtime identity mismatch")
    if oiio.VERSION_STRING != spec["runtime"]["python"]["openImageIO"] or np.__version__ != spec["runtime"]["python"]["numpy"]:
        raise RuntimeError("analysis library identity mismatch")
    if not any(item["id"] == args.fixture for item in spec["fixtures"]):
        raise RuntimeError("fixture outside frozen D10.1 roster")
    if args.output_dir.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite D10.1 adapter output")

    previous_report = source_identity(args.previous_report, args.previous_exr, args.fixture, args.repeat, spec["scene"]["previousFrame"])
    current_report = source_identity(args.current_report, args.current_exr, args.fixture, args.repeat, spec["scene"]["currentFrame"])
    previous = load_multipart(args.previous_exr, spec["sourceRender"])
    current = load_multipart(args.current_exr, spec["sourceRender"])

    arrays = {
        "previousRgba": previous["parts"]["BFS_F32_MASTER.Combined"],
        "currentRgba": current["parts"]["BFS_F32_MASTER.Combined"],
        "previousDepth": previous["parts"]["BFS_F32_MASTER.Depth"][..., 0],
        "currentDepth": current["parts"]["BFS_F32_MASTER.Depth"][..., 0],
        "previousLayer": previous["parts"]["BFS_F32_MASTER.Object Index"][..., 0],
        "currentLayer": current["parts"]["BFS_F32_MASTER.Object Index"][..., 0],
        "motion": np.negative(current["parts"]["BFS_F32_MASTER.Vector"][..., :2], dtype=np.float32),
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, filename in FILES.items():
        payload = encoded(arrays[name])
        target = args.output_dir / filename
        target.write_bytes(payload)
        records[name] = {"uri": str(target), "sha256": sha256_bytes(payload), "bytes": len(payload), "shape": list(arrays[name].shape), "dtype": "little-endian-float32"}

    body = {
        "schemaVersion": "bfs.blenderMultipartTemporalAdapterF32Report.v0.1",
        "experimentId": spec["experimentId"],
        "fixtureId": args.fixture,
        "repeat": args.repeat,
        "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha256_file(Path(sys.executable)), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "inputs": {
            "previousExr": {"uri": str(args.previous_exr), "sha256": previous_report["output"]["sha256"], "reportSha256": sha256_file(args.previous_report)},
            "currentExr": {"uri": str(args.current_exr), "sha256": current_report["output"]["sha256"], "reportSha256": sha256_file(args.current_report)},
        },
        "multipart": {"previousRoster": previous["roster"], "currentRoster": current["roster"], "previousChannels": previous["channels"], "currentChannels": current["channels"]},
        "transform": {"source": "current BFS_F32_MASTER.Vector.XY", "destination": "motion.xy32", "formula": "[-X,-Y]", "unusedValidatedPair": "current BFS_F32_MASTER.Vector.ZW"},
        "arrays": records,
        "operationCounts": {"adapterProcesses": 1, "multipartExrsOpened": 2, "canonicalArraysWritten": 7, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D10_1_ADAPTER_OK fixture={args.fixture} repeat={args.repeat} motion={records['motion']['sha256']}")


if __name__ == "__main__":
    main()
