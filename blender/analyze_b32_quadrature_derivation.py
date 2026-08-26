"""Compare the exploratory B32 4-point average with B31 natural/center/reference outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b32-work", type=Path, required=True)
    parser.add_argument("--b32-results", type=Path, required=True)
    parser.add_argument("--b31-work", type=Path, required=True)
    parser.add_argument("--b31-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rgb(path: Path) -> np.ndarray:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot read {path}: {image.geterror()}")
    spec = image.spec()
    if (spec.width, spec.height, list(spec.channelnames), str(spec.format)) != (960, 540, ["R", "G", "B", "A"], "float"):
        raise RuntimeError(f"Layout mismatch: {path}")
    pixels = np.asarray(image.get_pixels(oiio.FLOAT)[:, :, :3], dtype=np.float64)
    if not np.isfinite(pixels).all():
        raise RuntimeError(f"Non-finite pixels: {path}")
    return pixels


def rmse(candidate: np.ndarray, reference: np.ndarray, mask: np.ndarray | None = None) -> float:
    delta = candidate - reference
    if mask is not None:
        delta = delta[mask]
    return float(math.sqrt(float(np.mean(delta * delta))))


def edge_mask(reference: np.ndarray) -> np.ndarray:
    gx, gy = np.zeros(reference.shape[:2]), np.zeros(reference.shape[:2])
    dx, dy = reference[:, 2:, :] - reference[:, :-2, :], reference[2:, :, :] - reference[:-2, :, :]
    gx[:, 1:-1] = np.sqrt(np.sum(dx * dx, axis=2)) * 0.5
    gy[1:-1, :] = np.sqrt(np.sum(dy * dy, axis=2)) * 0.5
    magnitude = np.sqrt(gx * gx + gy * gy)
    return magnitude >= float(np.quantile(magnitude, 0.95))


def main() -> None:
    args = parse_args()
    b32 = json.loads(args.b32_results.read_text(encoding="utf-8"))
    b31 = json.loads(args.b31_results.read_text(encoding="utf-8"))
    frames = b32["design"]["frames"]
    observations = []
    for frame in frames:
        ref_a = read_rgb(args.b31_work / "REFERENCE1024_A" / f"frame-{frame:04d}.exr")
        ref_b = read_rgb(args.b31_work / "REFERENCE1024_B" / f"frame-{frame:04d}.exr")
        reference = (ref_a + ref_b) * 0.5
        mask = edge_mask(reference)
        natural = [(read_rgb(args.b31_work / f"NATURAL32_{rep}" / f"frame-{frame:04d}.exr")) for rep in ("A", "B")]
        center = [(read_rgb(args.b31_work / f"CENTER32_{rep}" / f"frame-{frame:04d}.exr")) for rep in ("A", "B")]
        ensembles = []
        for replicate in ("A", "B"):
            points = [read_rgb(args.b32_work / f"{point}_{replicate}" / f"frame-{frame:04d}.exr") for point in ("Q1", "Q2", "Q3", "Q4")]
            ensembles.append(np.mean(points, axis=0))
        natural_edge = float(np.mean([rmse(item, reference, mask) for item in natural]))
        center_edge = float(np.mean([rmse(item, reference, mask) for item in center]))
        ensemble_edge = float(np.mean([rmse(item, reference, mask) for item in ensembles]))
        natural_global = float(np.mean([rmse(item, reference) for item in natural]))
        ensemble_global = float(np.mean([rmse(item, reference) for item in ensembles]))
        observations.append({
            "frame": frame, "edgePixels": int(np.count_nonzero(mask)),
            "edgeRmse": {"NATURAL32": natural_edge, "CENTER32": center_edge, "QUADRATURE4": ensemble_edge},
            "globalRmse": {"NATURAL32": natural_global, "QUADRATURE4": ensemble_global},
            "ratios": {"quadratureToNaturalEdge": ensemble_edge / natural_edge,
                       "quadratureToCenterEdge": ensemble_edge / center_edge,
                       "quadratureToNaturalGlobal": ensemble_global / natural_global},
            "quadratureABRmse": rmse(ensembles[0], ensembles[1]),
        })
    q_seconds = sum(item["totalRenderSeconds"] for item in b32["reports"])
    n_seconds = sum(item["totalRenderSeconds"] for item in b31["reports"] if item["cell"] == "NATURAL32")
    result = {
        "documentType": "BFS_B32_QUADRATURE_DERIVATION_ANALYSIS", "version": "0.1.0",
        "status": "EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION",
        "b32ResultsSha256": sha256_file(args.b32_results), "b31ResultsSha256": sha256_file(args.b31_results),
        "ensemble": {"points": [[-0.25,-0.25],[-0.25,0.25],[0.25,-0.25],[0.25,0.25]],
                     "weights": [0.25,0.25,0.25,0.25], "domain": "scene-linear RGB"},
        "observations": observations,
        "aggregate": {
            "quadratureToNaturalEdgeMean": float(np.mean([item["ratios"]["quadratureToNaturalEdge"] for item in observations])),
            "quadratureToCenterEdgeMean": float(np.mean([item["ratios"]["quadratureToCenterEdge"] for item in observations])),
            "quadratureToNaturalGlobalMean": float(np.mean([item["ratios"]["quadratureToNaturalGlobal"] for item in observations])),
            "quadratureRenderSeconds": q_seconds, "naturalRenderSeconds": n_seconds,
            "observedRenderTimeRatio": q_seconds / n_seconds,
        },
        "nonClaims": ["Four-point averaging is exploratory and has not passed an unseen-frame holdout.",
                      "The B31 NATURAL1024 mean remains a reference proxy, not truth.",
                      "Numerical error and render-time ratios do not establish perceptual or production acceptability."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("BFS_B32_QUADRATURE_ANALYZE_OK " + " ".join(
        f"F{item['frame']} edge_ratio={item['ratios']['quadratureToNaturalEdge']:.6f}" for item in observations))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B32_QUADRATURE_ANALYZE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
