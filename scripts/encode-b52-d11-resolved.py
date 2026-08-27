#!/usr/bin/env python3
"""Encode one B52-D11 Python-resolved RGBA32 array as Raw FLOAT EXR."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "f1505c42426e8e286ee1584de3df12fb33b7db57518d6d91e1fd93aa3bed5a5f"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def array_hash(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value, dtype="<f4").tobytes()).hexdigest()


def read_exr(path: Path):
    image = oiio.ImageInput.open(str(path))
    if image is None:
        raise RuntimeError(oiio.geterror() or f"cannot read {path}")
    spec = image.spec()
    pixels = np.asarray(image.read_image(0, 0, 0, 4, oiio.FLOAT), np.float32).reshape(spec.height, spec.width, 4)
    image.close()
    return np.ascontiguousarray(pixels, dtype="<f4"), spec


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--source-repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--accumulator-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    fixture = next((item for item in spec["fixtures"] if item["id"] == args.fixture), None)
    if sha(args.spec) != SPEC_SHA256 or fixture is None:
        raise RuntimeError("B52-D11 spec or fixture identity mismatch")
    if sha(Path(sys.executable)) != spec["runtime"]["python"]["sha256"]:
        raise RuntimeError("Python runtime identity mismatch")
    if oiio.VERSION_STRING != spec["runtime"]["python"]["openImageIO"] or np.__version__ != spec["runtime"]["python"]["numpy"]:
        raise RuntimeError("analysis library identity mismatch")
    if args.output.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite D11 encoder output")
    accumulator = json.loads(args.accumulator_report.read_text())
    body_without_hash = {key: value for key, value in accumulator.items() if key != "reportHash"}
    if accumulator.get("reportHash") != canonical_hash(body_without_hash):
        raise RuntimeError("accumulator report self-hash mismatch")
    if accumulator.get("producer") != "python" or accumulator.get("fixtureId") != args.fixture or accumulator.get("repeat") != args.source_repeat:
        raise RuntimeError("accumulator report cell mismatch")
    if accumulator["outputs"]["resolvedRgba"]["sha256"] != sha(args.input):
        raise RuntimeError("accumulator resolved binding mismatch")

    width, height = spec["scene"]["resolution"]
    raw = args.input.read_bytes()
    if len(raw) != width * height * 4 * 4:
        raise RuntimeError("resolved input size mismatch")
    pixels = np.frombuffer(raw, dtype="<f4").reshape(height, width, 4)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = oiio.ImageOutput.create(str(args.output))
    image_spec = oiio.ImageSpec(width, height, 4, oiio.FLOAT)
    image_spec.channelnames = ("R", "G", "B", "A")
    image_spec.attribute("oiio:ColorSpace", "Raw")
    image_spec.attribute("compression", "zip")
    if output is None or not output.open(str(args.output), image_spec) or not output.write_image(pixels):
        raise RuntimeError(oiio.geterror() or "D11 EXR write failed")
    output.close()
    decoded, decoded_spec = read_exr(args.output)
    exact = bool(np.array_equal(decoded, pixels))
    layout = {
        "width": decoded_spec.width,
        "height": decoded_spec.height,
        "channels": list(decoded_spec.channelnames),
        "format": str(decoded_spec.format),
        "compression": decoded_spec.get_string_attribute("compression"),
    }
    body = {
        "schemaVersion": "bfs.blenderRealTexturedTemporalEncoderReport.v0.1",
        "experimentId": spec["experimentId"],
        "fixtureId": args.fixture,
        "sourceRepeat": args.source_repeat,
        "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha(Path(sys.executable)), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "accumulatorReport": {"uri": str(args.accumulator_report), "sha256": sha(args.accumulator_report)},
        "input": {"uri": str(args.input), "sha256": sha(args.input), "bytes": args.input.stat().st_size},
        "output": {"uri": str(args.output), "sha256": sha(args.output), "bytes": args.output.stat().st_size, "decodedCanonicalFloat32Sha256": array_hash(decoded)},
        "layout": layout,
        "encodeDecodeExact": exact,
        "operationCounts": {"resolvedExrEncoderProcesses": 1, "modelCalls": 0, "networkCalls": 0},
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({**body, "reportHash": canonical_hash(body)}, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D11_ENCODER_OK fixture={args.fixture} sourceRepeat={args.source_repeat} exact={exact}")
    if not exact:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
