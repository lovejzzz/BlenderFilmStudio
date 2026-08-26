"""Diagnose quantile tie behavior after the invalid B32 v0.1 holdout analysis attempt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--frames", nargs="+", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def read_rgb(path: Path) -> np.ndarray:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot read {path}: {image.geterror()}")
    pixels = np.asarray(image.get_pixels(oiio.FLOAT)[:, :, :3], dtype=np.float64)
    if pixels.shape != (540, 960, 3) or not np.isfinite(pixels).all():
        raise RuntimeError(f"Unexpected pixels: {path} shape={pixels.shape}")
    return pixels


def magnitude(reference: np.ndarray) -> np.ndarray:
    gx = np.zeros(reference.shape[:2], dtype=np.float64)
    gy = np.zeros(reference.shape[:2], dtype=np.float64)
    dx = reference[:, 2:, :] - reference[:, :-2, :]
    dy = reference[2:, :, :] - reference[:-2, :, :]
    gx[:, 1:-1] = np.sqrt(np.sum(dx * dx, axis=2)) * 0.5
    gy[1:-1, :] = np.sqrt(np.sum(dy * dy, axis=2)) * 0.5
    return np.sqrt(gx * gx + gy * gy)


def main() -> None:
    args = parse_args()
    observations = []
    for frame in args.frames:
        ref_a = read_rgb(args.work / "REFERENCE1024_A" / f"frame-{frame:04d}.exr")
        ref_b = read_rgb(args.work / "REFERENCE1024_B" / f"frame-{frame:04d}.exr")
        gradient = magnitude((ref_a + ref_b) * 0.5)
        threshold = float(np.quantile(gradient, 0.95))
        greater = int(np.count_nonzero(gradient > threshold))
        equal = int(np.count_nonzero(gradient == threshold))
        greater_equal = int(np.count_nonzero(gradient >= threshold))
        target = int(gradient.size * 0.05)
        flat = gradient.reshape(-1)
        exact_cutoff = float(np.partition(flat, flat.size - target)[flat.size - target])
        observations.append({
            "frame": frame,
            "pixels": int(gradient.size),
            "targetTopFivePercentPixels": target,
            "numpyQuantileThreshold": threshold,
            "pixelsGreaterThanThreshold": greater,
            "pixelsEqualToThreshold": equal,
            "pixelsGreaterThanOrEqualThreshold": greater_equal,
            "exactTopKCutoff": exact_cutoff,
            "tiesAtExactTopKCutoff": int(np.count_nonzero(gradient == exact_cutoff)),
        })
    result = {
        "documentType": "BFS_B32_EDGE_MASK_TIE_DIAGNOSTIC",
        "version": "0.1.0",
        "status": "POST_FAILURE_DIAGNOSTIC_NOT_FORMAL_RESULT",
        "question": "Why did the preregistered exact 25,920-pixel edge-mask check fail?",
        "observations": observations,
        "implication": "A quantile threshold plus >= does not guarantee an exact top-k mask when values tie at the cutoff.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for item in observations:
        print(
            f"BFS_B32_EDGE_TIE frame={item['frame']} target={item['targetTopFivePercentPixels']} "
            f"gt={item['pixelsGreaterThanThreshold']} eq={item['pixelsEqualToThreshold']} "
            f"ge={item['pixelsGreaterThanOrEqualThreshold']}"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B32_EDGE_TIE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
