"""Decode B46 EXRs and canonicalize both frames and float32 temporal deltas."""

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
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--frames", required=True)
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


def canonical_hash(metadata, pixels) -> str:
    header = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    return hashlib.sha256(header + pixels.tobytes(order="C")).hexdigest()


def main() -> None:
    args = parse_args()
    frame_numbers = [int(value) for value in args.frames.split(",")]
    if frame_numbers != sorted(set(frame_numbers)):
        raise RuntimeError("frames must be strictly ascending and unique")
    root = args.input_dir.resolve()
    expected_shape = (args.expected_height, args.expected_width, 4)
    decoded = []
    frames = []
    for frame in frame_numbers:
        source = root / f"frame-{frame:04d}.exr"
        image = cv2.imread(str(source), cv2.IMREAD_UNCHANGED)
        if image is None or image.dtype != np.float32 or tuple(image.shape) != expected_shape:
            raise RuntimeError(f"invalid EXR frame {frame}: {None if image is None else (image.dtype, image.shape)}")
        if not bool(np.isfinite(image).all()):
            raise RuntimeError(f"non-finite EXR frame {frame}")
        canonical = np.ascontiguousarray(image.astype("<f4", copy=False))
        metadata = {"shape": list(canonical.shape), "dtype": "float32-le", "channelOrder": "BGRA", "order": "C"}
        channels = []
        for index, name in enumerate("BGRA"):
            plane = canonical[:, :, index]
            channels.append({"name":name,"min":float(plane.min()),"max":float(plane.max()),"mean":float(plane.mean())})
        frames.append({
            "frame": frame,
            "input": {"uri": str(source), "sha256": sha256_file(source), "bytes": source.stat().st_size},
            "metadata": metadata,
            "finite": True,
            "componentCount": int(canonical.size),
            "pixelCount": int(canonical.shape[0] * canonical.shape[1]),
            "canonicalPixelSha256": canonical_hash(metadata, canonical),
            "channels": channels,
        })
        decoded.append(canonical)
    transitions = []
    for index in range(1, len(decoded)):
        previous, current = decoded[index - 1], decoded[index]
        delta = np.ascontiguousarray(np.subtract(current, previous, dtype=np.float32).astype("<f4", copy=False))
        metadata = {"shape": list(delta.shape), "dtype":"float32-le", "order":"C", "fromFrame":frame_numbers[index-1], "toFrame":frame_numbers[index]}
        nonzero = int(np.count_nonzero(delta))
        transitions.append({
            "fromFrame": frame_numbers[index - 1],
            "toFrame": frame_numbers[index],
            "changedComponentCount": nonzero,
            "nonZero": nonzero > 0,
            "maxAbs": float(np.max(np.abs(delta))),
            "meanAbs": float(np.mean(np.abs(delta), dtype=np.float64)),
            "canonicalTransitionSha256": canonical_hash(metadata, delta),
        })
    sequence_binding = {
        "frames": [{"frame": item["frame"], "canonicalPixelSha256": item["canonicalPixelSha256"]} for item in frames],
        "transitions": [{"fromFrame": item["fromFrame"], "toFrame": item["toFrame"], "canonicalTransitionSha256": item["canonicalTransitionSha256"]} for item in transitions],
    }
    result = {
        "schemaVersion":"bfs.workerSequenceDecode.v0.1",
        "runtime":{"python":platform.python_version(),"opencv":cv2.__version__,"numpy":np.__version__},
        "frames":frames,
        "transitions":transitions,
        "sequenceSha256":hashlib.sha256(json.dumps(sequence_binding, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
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
        print(f"BFS_B46_ANALYZE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
