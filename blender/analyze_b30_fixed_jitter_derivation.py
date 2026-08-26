"""Quantify image changes for exploratory B30 fixed-jitter candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--alternate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def pixels(path: Path) -> np.ndarray:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot decode {path}: {image.geterror()}")
    spec = image.spec()
    if [spec.width, spec.height, list(spec.channelnames), str(spec.format)] != [960, 540, ["R", "G", "B", "A"], "uint8"]:
        raise RuntimeError(f"Layout mismatch: {path}")
    return image.get_pixels(oiio.UINT8)[:, :, :3]


def digest(data: np.ndarray) -> str:
    return hashlib.sha256(data.tobytes(order="C")).hexdigest()


def compare(a: np.ndarray, b: np.ndarray) -> dict:
    delta_code = b.astype(np.int16) - a.astype(np.int16)
    mask = np.any(delta_code != 0, axis=2)
    ys, xs = np.where(mask)
    return {"decodedPixelExact": not bool(mask.any()), "changedPixels": int(mask.sum()), "changedChannelValues": int(np.count_nonzero(delta_code)), "maximumAbsoluteCodeDelta": int(np.max(np.abs(delta_code))) if mask.any() else 0, "rmsNormalized": float(np.sqrt(np.mean(np.square(delta_code.astype(np.float64) / 255.0)))), "boundingBox": None if not mask.any() else {"xMin": int(xs.min()), "xMax": int(xs.max()), "yMin": int(ys.min()), "yMax": int(ys.max())}}


def main() -> None:
    args = parse_args()
    derivation = json.loads(args.results.read_text(encoding="utf-8"))
    if derivation["status"] != "EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION":
        raise RuntimeError("Derivation status mismatch")
    cell_pixels = {}
    cells = []
    for cell in ("NATURAL", "CENTER", "POS_QUARTER", "NEG_QUARTER"):
        images = [pixels(args.work_dir / cell / f"render-{ordinal:02d}.png") for ordinal in range(1, 13)]
        counts = Counter(digest(item) for item in images)
        cell_pixels[cell] = images[0]
        cells.append({"cell": cell, "uniqueDecodedRgbHashes": len(counts), "frequencies": [{"decodedRgbSha256": sha, "count": count} for sha, count in sorted(counts.items())], "firstDecodedRgbSha256": digest(images[0])})
    reference, alternate = pixels(args.reference), pixels(args.alternate)
    anchors = {"REFERENCE": reference, "ALTERNATE": alternate}
    anchor_comparisons = []
    for cell in ("CENTER", "POS_QUARTER", "NEG_QUARTER"):
        for label, anchor in anchors.items():
            anchor_comparisons.append({"cell": cell, "anchor": label, **compare(anchor, cell_pixels[cell])})
    fixed_pairwise = []
    fixed = ("CENTER", "POS_QUARTER", "NEG_QUARTER")
    for index, a in enumerate(fixed):
        for b in fixed[index + 1:]:
            fixed_pairwise.append({"a": a, "b": b, **compare(cell_pixels[a], cell_pixels[b])})
    result = {"documentType": "BFS_B30_FIXED_JITTER_DERIVATION_ANALYSIS", "version": "0.1.0", "status": "EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION", "derivationResultsSha256": hashlib.sha256(args.results.read_bytes()).hexdigest(), "anchors": {"REFERENCE": digest(reference), "ALTERNATE": digest(alternate)}, "cells": cells, "anchorComparisons": anchor_comparisons, "fixedPairwise": fixed_pairwise, "selectionRule": "Nominate CENTER for confirmatory testing only if it is within-cell exact; retain all image-change metrics as a cost of intervention rather than optimizing a post-hoc closeness threshold.", "nonClaim": "Static PNG differences do not measure anti-aliasing quality or perceptual acceptability."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("BFS_B30_FIXED_JITTER_ANALYZE_OK " + " ".join(f"{item['cell']}={item['uniqueDecodedRgbHashes']}" for item in cells))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B30_FIXED_JITTER_ANALYZE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
