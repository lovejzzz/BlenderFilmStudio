"""Analyze formal B31 holdout and apply the frozen decision precedence."""

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
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rgb(path: Path, expected_sha: str) -> tuple[np.ndarray, dict[str, Any]]:
    if sha256_file(path) != expected_sha:
        raise RuntimeError(f"Container SHA mismatch: {path}")
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot read {path}: {image.geterror()}")
    spec = image.spec()
    layout = {"width": spec.width, "height": spec.height, "channels": list(spec.channelnames), "pixelFormat": str(spec.format)}
    if layout != {"width": 960, "height": 540, "channels": ["R", "G", "B", "A"], "pixelFormat": "float"}:
        raise RuntimeError(f"Unexpected EXR layout: {layout!r}")
    rgb = np.asarray(image.get_pixels(oiio.FLOAT)[:, :, :3], dtype=np.float64)
    if not np.isfinite(rgb).all():
        raise RuntimeError(f"Non-finite RGB: {path}")
    return rgb, layout


def metrics(candidate: np.ndarray, reference: np.ndarray, mask: np.ndarray | None = None) -> dict[str, float | int]:
    delta = candidate - reference
    if mask is not None:
        delta = delta[mask]
    absolute = np.abs(delta)
    return {"sampledPixels": int(delta.shape[0] if delta.ndim == 2 else delta.shape[0] * delta.shape[1]),
            "mae": float(np.mean(absolute)), "rmse": float(math.sqrt(float(np.mean(delta * delta)))),
            "maximumAbsoluteError": float(np.max(absolute))}


def edge_mask(reference: np.ndarray, quantile: float) -> tuple[np.ndarray, float]:
    gx = np.zeros(reference.shape[:2], dtype=np.float64)
    gy = np.zeros(reference.shape[:2], dtype=np.float64)
    dx, dy = reference[:, 2:, :] - reference[:, :-2, :], reference[2:, :, :] - reference[:-2, :, :]
    gx[:, 1:-1] = np.sqrt(np.sum(dx * dx, axis=2)) * 0.5
    gy[1:-1, :] = np.sqrt(np.sum(dy * dy, axis=2)) * 0.5
    magnitude = np.sqrt(gx * gx + gy * gy)
    threshold = float(np.quantile(magnitude, quantile))
    return magnitude >= threshold, threshold


def main() -> None:
    args = parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if spec["documentType"] != "BFS_SAMPLING_QUALITY_HOLDOUT_SPEC" or index["documentType"] != "BFS_B31_ANALYSIS_INDEX":
        raise RuntimeError("B31 document type mismatch")
    if index["b31SpecSha256"] != sha256_file(args.spec):
        raise RuntimeError("B31 index/spec binding mismatch")
    if [item["replicateId"] for item in index["processes"]] != spec["design"]["schedule"]:
        raise RuntimeError("B31 schedule mismatch")

    arrays: dict[str, dict[int, np.ndarray]] = {}
    layout = None
    for process in index["processes"]:
        replicate_id = process["replicateId"]
        arrays[replicate_id] = {}
        if [item["frame"] for item in process["outputs"]] != spec["design"]["holdoutFrames"]:
            raise RuntimeError(f"{replicate_id} frame order mismatch")
        for item in process["outputs"]:
            pixels, observed_layout = read_rgb(Path.cwd() / item["fileUri"], item["containerSha256"])
            layout = observed_layout if layout is None else layout
            if observed_layout != layout:
                raise RuntimeError("EXR layout drift")
            arrays[replicate_id][item["frame"]] = pixels

    frame_results = []
    for frame in spec["design"]["holdoutFrames"]:
        ref_a, ref_b = arrays["REFERENCE1024_A"][frame], arrays["REFERENCE1024_B"][frame]
        reference = (ref_a + ref_b) * 0.5
        mask, threshold = edge_mask(reference, spec["edgeRule"]["quantile"])
        if int(np.count_nonzero(mask)) != spec["edgeRule"]["expectedPixelsPerFrame"]:
            raise RuntimeError(f"Frame {frame} edge pixel count mismatch")
        methods = {}
        for cell in ("NATURAL32", "CENTER32"):
            reps = []
            for replicate in ("A", "B"):
                pixels = arrays[f"{cell}_{replicate}"][frame]
                reps.append({"replicate": replicate, "global": metrics(pixels, reference),
                             "edge": metrics(pixels, reference, mask), "nonEdge": metrics(pixels, reference, ~mask)})
            methods[cell] = {"replicates": reps,
                             "withinMethodAB": metrics(arrays[f"{cell}_A"][frame], arrays[f"{cell}_B"][frame]),
                             "globalRmseMean": float(np.mean([item["global"]["rmse"] for item in reps])),
                             "edgeRmseMean": float(np.mean([item["edge"]["rmse"] for item in reps])),
                             "nonEdgeRmseMean": float(np.mean([item["nonEdge"]["rmse"] for item in reps]))}
        natural_edge = methods["NATURAL32"]["edgeRmseMean"]
        if natural_edge <= 0:
            reliability_ratio = math.inf
            edge_ratio = math.inf
        else:
            reference_edge = metrics(ref_a, ref_b, mask)["rmse"]
            reliability_ratio = reference_edge / natural_edge
            edge_ratio = methods["CENTER32"]["edgeRmseMean"] / natural_edge
        frame_results.append({
            "frame": frame, "edgeThreshold": threshold, "edgePixels": int(np.count_nonzero(mask)),
            "referenceAgreement": {"global": metrics(ref_a, ref_b), "edge": metrics(ref_a, ref_b, mask),
                                   "reliabilityRatio": reliability_ratio},
            "methods": methods, "ratios": {
                "centerToNaturalEdgeRmse": edge_ratio,
                "centerToNaturalGlobalRmse": methods["CENTER32"]["globalRmseMean"] / methods["NATURAL32"]["globalRmseMean"],
                "centerToNaturalNonEdgeRmse": methods["CENTER32"]["nonEdgeRmseMean"] / methods["NATURAL32"]["nonEdgeRmseMean"],
            },
        })

    max_reference_ratio = spec["referenceProxy"]["maximumReliabilityRatioPerFrame"]
    cost_threshold = spec["primaryEndpoint"]["costSupportThreshold"]
    reliable = all(math.isfinite(item["referenceAgreement"]["reliabilityRatio"])
                   and item["referenceAgreement"]["reliabilityRatio"] <= max_reference_ratio for item in frame_results)
    edge_ratios = [item["ratios"]["centerToNaturalEdgeRmse"] for item in frame_results]
    if not reliable:
        decision = "REFERENCE_PROXY_UNSTABLE"
    elif any(value < 1.0 for value in edge_ratios):
        decision = "EDGE_COST_DIRECTION_REVERSED"
    elif all(value >= cost_threshold for value in edge_ratios):
        decision = "EDGE_REFERENCE_COST_SUPPORT"
    elif any(value >= cost_threshold for value in edge_ratios):
        decision = "MIXED_EDGE_REFERENCE_COST"
    else:
        decision = "EDGE_REFERENCE_COST_NOT_REPRODUCED"

    result = {
        "documentType": "BFS_B31_SAMPLING_QUALITY_HOLDOUT_ANALYSIS", "version": "0.1.0",
        "b31SpecSha256": sha256_file(args.spec), "indexSha256": sha256_file(args.index),
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}", "layout": layout, "decision": decision,
        "referenceProxyReliable": reliable, "frames": frame_results,
        "summary": {"holdoutFrames": len(frame_results), "reliableFrames": sum(
            item["referenceAgreement"]["reliabilityRatio"] <= max_reference_ratio for item in frame_results),
            "framesAtOrAboveCostThreshold": sum(value >= cost_threshold for value in edge_ratios),
            "minimumEdgeCostRatio": min(edge_ratios), "maximumEdgeCostRatio": max(edge_ratios),
            "meanEdgeCostRatio": float(np.mean(edge_ratios))},
        "nonClaims": spec["explicitNonClaims"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B31_HOLDOUT_ANALYZE_OK {decision} min={min(edge_ratios):.6f} reliable={reliable}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B31_HOLDOUT_ANALYZE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
