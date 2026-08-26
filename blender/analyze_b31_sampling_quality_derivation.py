"""Analyze exploratory B31 scene-linear error against a dual 1024-sample proxy."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rgb(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot read {path}: {image.geterror()}")
    spec = image.spec()
    pixels = image.get_pixels(oiio.FLOAT)
    if (spec.width, spec.height, list(spec.channelnames)) != (960, 540, ["R", "G", "B", "A"]):
        raise RuntimeError(f"Unexpected layout for {path}: {(spec.width, spec.height, list(spec.channelnames))!r}")
    rgb = np.asarray(pixels[:, :, :3], dtype=np.float64)
    if not np.isfinite(rgb).all():
        raise RuntimeError(f"Non-finite RGB in {path}")
    return rgb, {"width": spec.width, "height": spec.height, "channels": list(spec.channelnames),
                 "pixelFormat": str(spec.format), "oiio": oiio.VERSION_STRING}


def error_metrics(candidate: np.ndarray, reference: np.ndarray, mask: np.ndarray | None = None) -> dict[str, Any]:
    delta = candidate - reference
    if mask is not None:
        delta = delta[mask]
    absolute = np.abs(delta)
    return {
        "sampledPixels": int(delta.shape[0] if delta.ndim == 2 else delta.shape[0] * delta.shape[1]),
        "mae": float(np.mean(absolute)),
        "rmse": float(math.sqrt(float(np.mean(delta * delta)))),
        "maximumAbsoluteError": float(np.max(absolute)),
    }


def edge_mask(reference: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]:
    gx = np.zeros(reference.shape[:2], dtype=np.float64)
    gy = np.zeros(reference.shape[:2], dtype=np.float64)
    dx = reference[:, 2:, :] - reference[:, :-2, :]
    dy = reference[2:, :, :] - reference[:-2, :, :]
    gx[:, 1:-1] = np.sqrt(np.sum(dx * dx, axis=2)) * 0.5
    gy[1:-1, :] = np.sqrt(np.sum(dy * dy, axis=2)) * 0.5
    magnitude = np.sqrt(gx * gx + gy * gy)
    threshold = float(np.quantile(magnitude, 0.95))
    mask = magnitude >= threshold
    return mask, threshold, magnitude


def main() -> None:
    args = parse_args()
    results = json.loads(args.results.read_text(encoding="utf-8"))
    frames = results["design"]["frames"]
    arrays: dict[str, dict[str, dict[int, np.ndarray]]] = {}
    layout = None
    for cell in ("NATURAL32", "CENTER32", "REFERENCE1024"):
        arrays[cell] = {}
        for replicate in ("A", "B"):
            arrays[cell][replicate] = {}
            for frame in frames:
                path = args.work_dir / f"{cell}_{replicate}" / f"frame-{frame:04d}.exr"
                array, observed_layout = read_rgb(path)
                layout = observed_layout if layout is None else layout
                if observed_layout != layout:
                    raise RuntimeError("EXR layout drift")
                arrays[cell][replicate][frame] = array

    observations = []
    ratios = []
    for frame in frames:
        ref_a = arrays["REFERENCE1024"]["A"][frame]
        ref_b = arrays["REFERENCE1024"]["B"][frame]
        reference = (ref_a + ref_b) * 0.5
        mask, threshold, _ = edge_mask(reference)
        frame_item = {
            "frame": frame, "edgeDefinition": "top 5% of dual-reference RGB central-difference magnitude",
            "edgeThreshold": threshold, "edgePixels": int(np.count_nonzero(mask)),
            "referenceAgreement": {"global": error_metrics(ref_a, ref_b), "edge": error_metrics(ref_a, ref_b, mask)},
            "methods": {},
        }
        method_summaries = {}
        for cell in ("NATURAL32", "CENTER32"):
            replicates = []
            for replicate in ("A", "B"):
                candidate = arrays[cell][replicate][frame]
                replicates.append({"replicate": replicate, "global": error_metrics(candidate, reference),
                                   "edge": error_metrics(candidate, reference, mask),
                                   "nonEdge": error_metrics(candidate, reference, ~mask)})
            within = error_metrics(arrays[cell]["A"][frame], arrays[cell]["B"][frame])
            summary = {
                "globalRmseMean": float(np.mean([item["global"]["rmse"] for item in replicates])),
                "edgeRmseMean": float(np.mean([item["edge"]["rmse"] for item in replicates])),
                "nonEdgeRmseMean": float(np.mean([item["nonEdge"]["rmse"] for item in replicates])),
            }
            frame_item["methods"][cell] = {"replicates": replicates, "withinMethodAB": within, "summary": summary}
            method_summaries[cell] = summary
        ratio = {
            "frame": frame,
            "centerToNaturalGlobalRmse": method_summaries["CENTER32"]["globalRmseMean"] / method_summaries["NATURAL32"]["globalRmseMean"],
            "centerToNaturalEdgeRmse": method_summaries["CENTER32"]["edgeRmseMean"] / method_summaries["NATURAL32"]["edgeRmseMean"],
            "centerToNaturalNonEdgeRmse": method_summaries["CENTER32"]["nonEdgeRmseMean"] / method_summaries["NATURAL32"]["nonEdgeRmseMean"],
        }
        ratios.append(ratio)
        observations.append(frame_item)

    result = {
        "documentType": "BFS_B31_SAMPLING_QUALITY_DERIVATION_ANALYSIS", "version": "0.1.0",
        "status": "EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION",
        "resultsSha256": sha256_file(args.results), "layout": layout,
        "referenceProxy": {"definition": "pixelwise mean of two independent NATURAL 1024-sample scene-linear EXR renders",
                           "truthClaim": False, "spatialSupersampling": False},
        "edgeRule": {"gradient": "RGB Euclidean central difference", "quantile": 0.95,
                     "selectedBeforeAnalysisOutput": True},
        "observations": observations, "ratios": ratios,
        "aggregateRatios": {
            "centerToNaturalGlobalRmseMean": float(np.mean([item["centerToNaturalGlobalRmse"] for item in ratios])),
            "centerToNaturalEdgeRmseMean": float(np.mean([item["centerToNaturalEdgeRmse"] for item in ratios])),
            "centerToNaturalNonEdgeRmseMean": float(np.mean([item["centerToNaturalNonEdgeRmse"] for item in ratios])),
        },
        "nonClaims": [
            "The dual 1024-sample mean is a reference proxy, not ground truth.",
            "Three derivation frames cannot establish a production-quality margin.",
            "Scene-linear numerical error does not determine perceived sharpness, aliasing, temporal quality, or cinematic quality.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("BFS_B31_DERIVATION_ANALYZE_OK " + " ".join(
        f"F{item['frame']} edge_ratio={item['centerToNaturalEdgeRmse']:.6f}" for item in ratios))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B31_DERIVATION_ANALYZE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
