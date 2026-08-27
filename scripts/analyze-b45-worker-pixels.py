"""Decode a B45 EXR into one pinned canonical float-pixel representation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--expected-width", type=int, required=True)
    parser.add_argument("--expected-height", type=int, required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    source = args.input.resolve()
    image = cv2.imread(str(source), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise RuntimeError(f"OpenCV could not decode {source}")
    if image.ndim != 3 or image.shape[2] != 4:
        raise RuntimeError(f"expected four channels, observed shape {image.shape}")
    if image.dtype != np.float32:
        raise RuntimeError(f"expected float32, observed {image.dtype}")
    expected_shape = (args.expected_height, args.expected_width, 4)
    if tuple(image.shape) != expected_shape:
        raise RuntimeError(f"expected shape {expected_shape}, observed {image.shape}")
    finite = bool(np.isfinite(image).all())
    if not finite:
        raise RuntimeError("decoded pixels contain NaN or infinity")
    canonical = np.ascontiguousarray(image.astype("<f4", copy=False))
    metadata = {"shape": list(canonical.shape), "dtype": "float32-le", "channelOrder": "BGRA", "order": "C"}
    digest = hashlib.sha256(json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n" + canonical.tobytes(order="C")).hexdigest()
    channels = []
    for index, name in enumerate("BGRA"):
        plane = canonical[:, :, index]
        channels.append({"name": name, "min": float(plane.min()), "max": float(plane.max()), "mean": float(plane.mean())})
    result = {
        "schemaVersion": "bfs.workerPixelDecode.v0.1",
        "input": {"uri": str(source), "sha256": sha256_file(source), "bytes": source.stat().st_size},
        "runtime": {"python": platform.python_version(), "opencv": cv2.__version__, "numpy": np.__version__},
        "metadata": metadata,
        "finite": finite,
        "componentCount": int(canonical.size),
        "pixelCount": int(canonical.shape[0] * canonical.shape[1]),
        "canonicalPixelSha256": digest,
        "channels": channels,
    }
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output == "-":
        sys.stdout.write(encoded)
    else:
        Path(args.output).write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B45_ANALYZE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
