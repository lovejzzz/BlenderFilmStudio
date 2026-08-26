"""Analyze the preregistered B32 quadrature cost-quality holdout."""

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


def expected_schedule() -> list[str]:
    schedule = [f"{cell}_{replicate}" for cell in ("NATURAL32", "REFERENCE1024") for replicate in ("A", "B")]
    schedule.extend(f"Q4_{index}_{replicate}" for replicate in ("A", "B") for index in range(1, 5))
    schedule.extend(f"Q8_{index}_{replicate}" for replicate in ("A", "B") for index in range(1, 9))
    return schedule


def read_rgb(path: Path, expected_sha: str) -> tuple[np.ndarray, dict[str, Any]]:
    if sha256_file(path) != expected_sha:
        raise RuntimeError(f"Container SHA mismatch: {path}")
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot read {path}: {image.geterror()}")
    spec = image.spec()
    layout = {
        "width": spec.width, "height": spec.height,
        "channels": list(spec.channelnames), "pixelFormat": str(spec.format),
    }
    expected_layout = {"width": 960, "height": 540, "channels": ["R", "G", "B", "A"], "pixelFormat": "float"}
    if layout != expected_layout:
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
    sampled_pixels = int(delta.shape[0] if delta.ndim == 2 else delta.shape[0] * delta.shape[1])
    return {
        "sampledPixels": sampled_pixels,
        "mae": float(np.mean(absolute)),
        "rmse": float(math.sqrt(float(np.mean(delta * delta)))),
        "maximumAbsoluteError": float(np.max(absolute)),
    }


def edge_mask(reference: np.ndarray) -> tuple[np.ndarray, float]:
    gx = np.zeros(reference.shape[:2], dtype=np.float64)
    gy = np.zeros(reference.shape[:2], dtype=np.float64)
    dx = reference[:, 2:, :] - reference[:, :-2, :]
    dy = reference[2:, :, :] - reference[:-2, :, :]
    gx[:, 1:-1] = np.sqrt(np.sum(dx * dx, axis=2)) * 0.5
    gy[1:-1, :] = np.sqrt(np.sum(dy * dy, axis=2)) * 0.5
    magnitude = np.sqrt(gx * gx + gy * gy)
    threshold = float(np.quantile(magnitude, 0.95))
    return magnitude >= threshold, threshold


def method_metrics(replicates: list[np.ndarray], reference: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    per_replicate = []
    for name, pixels in zip(("A", "B"), replicates, strict=True):
        per_replicate.append({
            "replicate": name,
            "global": metrics(pixels, reference),
            "edge": metrics(pixels, reference, mask),
            "nonEdge": metrics(pixels, reference, ~mask),
        })
    return {
        "replicates": per_replicate,
        "withinMethodAB": metrics(replicates[0], replicates[1]),
        "globalRmseMean": float(np.mean([item["global"]["rmse"] for item in per_replicate])),
        "edgeRmseMean": float(np.mean([item["edge"]["rmse"] for item in per_replicate])),
        "nonEdgeRmseMean": float(np.mean([item["nonEdge"]["rmse"] for item in per_replicate])),
    }


def main() -> None:
    args = parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if spec.get("documentType") != "BFS_QUADRATURE_COST_HOLDOUT_SPEC":
        raise RuntimeError("B32 holdout spec type mismatch")
    if index.get("documentType") != "BFS_B32_QUADRATURE_COST_ANALYSIS_INDEX":
        raise RuntimeError("B32 analysis index type mismatch")
    if index.get("holdoutSpecSha256") != sha256_file(args.spec):
        raise RuntimeError("B32 index/spec binding mismatch")
    processes = index.get("processes", [])
    schedule = expected_schedule()
    if [item.get("replicateId") for item in processes] != schedule:
        raise RuntimeError("B32 process schedule mismatch")
    if len({item.get("processId") for item in processes}) != spec["design"]["totalProcesses"]:
        raise RuntimeError("B32 process IDs are missing or duplicated")

    arrays: dict[str, dict[int, np.ndarray]] = {}
    layout = None
    frames = spec["design"]["frames"]
    for process in processes:
        replicate_id = process["replicateId"]
        arrays[replicate_id] = {}
        if [item["frame"] for item in process["outputs"]] != frames:
            raise RuntimeError(f"{replicate_id} frame order mismatch")
        for item in process["outputs"]:
            pixels, observed_layout = read_rgb(Path.cwd() / item["fileUri"], item["containerSha256"])
            layout = observed_layout if layout is None else layout
            if observed_layout != layout:
                raise RuntimeError("EXR layout drift")
            arrays[replicate_id][item["frame"]] = pixels

    frame_results = []
    for frame in frames:
        ref_a = arrays["REFERENCE1024_A"][frame]
        ref_b = arrays["REFERENCE1024_B"][frame]
        reference = (ref_a + ref_b) * 0.5
        mask, threshold = edge_mask(reference)
        edge_pixels = int(np.count_nonzero(mask))
        if edge_pixels != spec["analysis"]["edgeMaskExpectedPixelsPerFrame"]:
            raise RuntimeError(f"Frame {frame} edge pixel count mismatch")
        natural = [arrays[f"NATURAL32_{replicate}"][frame] for replicate in ("A", "B")]
        q4 = [
            np.mean([arrays[f"Q4_{index}_{replicate}"][frame] for index in range(1, 5)], axis=0)
            for replicate in ("A", "B")
        ]
        q8 = [
            np.mean([arrays[f"Q8_{index}_{replicate}"][frame] for index in range(1, 9)], axis=0)
            for replicate in ("A", "B")
        ]
        methods = {
            "NATURAL32": method_metrics(natural, reference, mask),
            "QUADRATURE4": method_metrics(q4, reference, mask),
            "STRATIFIED8": method_metrics(q8, reference, mask),
        }
        natural_edge = methods["NATURAL32"]["edgeRmseMean"]
        reference_edge = metrics(ref_a, ref_b, mask)["rmse"]
        reliability_ratio = reference_edge / natural_edge if natural_edge > 0 else math.inf
        q4_edge = methods["QUADRATURE4"]["edgeRmseMean"]
        q8_edge = methods["STRATIFIED8"]["edgeRmseMean"]
        natural_global = methods["NATURAL32"]["globalRmseMean"]
        frame_results.append({
            "frame": frame,
            "edgeThreshold": threshold,
            "edgePixels": edge_pixels,
            "referenceAgreement": {
                "global": metrics(ref_a, ref_b),
                "edge": metrics(ref_a, ref_b, mask),
                "reliabilityRatio": reliability_ratio,
            },
            "methods": methods,
            "ratios": {
                "q4ToNaturalEdgeRmse": q4_edge / natural_edge,
                "q8ToNaturalEdgeRmse": q8_edge / natural_edge,
                "q8ToQ4EdgeRmse": q8_edge / q4_edge,
                "q4ToNaturalGlobalRmse": methods["QUADRATURE4"]["globalRmseMean"] / natural_global,
                "q8ToNaturalGlobalRmse": methods["STRATIFIED8"]["globalRmseMean"] / natural_global,
            },
        })

    gates = spec["gates"]
    reference_reliable = all(
        math.isfinite(item["referenceAgreement"]["reliabilityRatio"])
        and item["referenceAgreement"]["reliabilityRatio"] <= gates["referenceReliabilityRatioMaximumEveryFrame"]
        for item in frame_results
    )
    repeatability = all(
        item["methods"]["QUADRATURE4"]["withinMethodAB"]["rmse"] == gates["q4ABRmseExactEveryFrame"]
        and item["methods"]["STRATIFIED8"]["withinMethodAB"]["rmse"] == gates["q8ABRmseExactEveryFrame"]
        for item in frame_results
    )
    q4_support = all(item["ratios"]["q4ToNaturalEdgeRmse"] <= gates["q4ToNaturalEdgeMaximumEveryFrame"] for item in frame_results)
    q8_support = all(item["ratios"]["q8ToNaturalEdgeRmse"] <= gates["q8ToNaturalEdgeMaximumEveryFrame"] for item in frame_results)
    q8_to_q4_values = [item["ratios"]["q8ToQ4EdgeRmse"] for item in frame_results]
    dominance_support = (
        all(value <= gates["q8ToQ4EdgeMaximumEveryFrame"] for value in q8_to_q4_values)
        and float(np.mean(q8_to_q4_values)) <= gates["q8ToQ4EdgeMeanMaximum"]
    )
    verdicts = {
        "reference": "REFERENCE_RELIABLE" if reference_reliable else "REFERENCE_UNRELIABLE",
        "repeatability": "Q4_Q8_EXACT_REPEATABILITY_SUPPORT" if repeatability else "ENSEMBLE_REPEATABILITY_FAILURE",
        "q4": "Q4_COST_POINT_SUPPORT" if q4_support else "Q4_QUALITY_GENERALIZATION_FAILURE",
        "q8": "Q8_NEAR_NATURAL_PROXY_SUPPORT" if q8_support else "Q8_NEAR_NATURAL_GENERALIZATION_FAILURE",
        "dominance": "Q8_OVER_Q4_DOMINANCE_SUPPORT" if dominance_support else "Q8_OVER_Q4_DOMINANCE_FAILURE",
    }
    all_positive = reference_reliable and repeatability and q4_support and q8_support and dominance_support
    decision = spec["overallDecision"]["allPositive"] if all_positive else spec["overallDecision"]["otherwise"]
    cost_seconds = {
        "NATURAL32": sum(item["totalRenderSeconds"] for item in processes if item["cell"] == "NATURAL32"),
        "REFERENCE1024": sum(item["totalRenderSeconds"] for item in processes if item["cell"] == "REFERENCE1024"),
        "QUADRATURE4": sum(item["totalRenderSeconds"] for item in processes if item["cell"].startswith("Q4_")),
        "STRATIFIED8": sum(item["totalRenderSeconds"] for item in processes if item["cell"].startswith("Q8_")),
    }
    result = {
        "documentType": "BFS_B32_QUADRATURE_COST_HOLDOUT_ANALYSIS",
        "version": "0.1.0",
        "holdoutSpecSha256": sha256_file(args.spec),
        "indexSha256": sha256_file(args.index),
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
        "layout": layout,
        "valid": True,
        "decision": decision,
        "componentVerdicts": verdicts,
        "frames": frame_results,
        "summary": {
            "holdoutFrames": len(frame_results),
            "reliableFrames": sum(item["referenceAgreement"]["reliabilityRatio"] <= gates["referenceReliabilityRatioMaximumEveryFrame"] for item in frame_results),
            "q4FramesPassing": sum(item["ratios"]["q4ToNaturalEdgeRmse"] <= gates["q4ToNaturalEdgeMaximumEveryFrame"] for item in frame_results),
            "q8FramesPassing": sum(item["ratios"]["q8ToNaturalEdgeRmse"] <= gates["q8ToNaturalEdgeMaximumEveryFrame"] for item in frame_results),
            "dominanceFramesPassing": sum(value <= gates["q8ToQ4EdgeMaximumEveryFrame"] for value in q8_to_q4_values),
            "q4ToNaturalEdgeMean": float(np.mean([item["ratios"]["q4ToNaturalEdgeRmse"] for item in frame_results])),
            "q8ToNaturalEdgeMean": float(np.mean([item["ratios"]["q8ToNaturalEdgeRmse"] for item in frame_results])),
            "q8ToQ4EdgeMean": float(np.mean(q8_to_q4_values)),
            "maximumQ4ToNaturalEdge": max(item["ratios"]["q4ToNaturalEdgeRmse"] for item in frame_results),
            "maximumQ8ToNaturalEdge": max(item["ratios"]["q8ToNaturalEdgeRmse"] for item in frame_results),
            "maximumReferenceReliabilityRatio": max(item["referenceAgreement"]["reliabilityRatio"] for item in frame_results),
        },
        "cost": {
            "renderSeconds": cost_seconds,
            "q4ToNaturalRenderTimeRatio": cost_seconds["QUADRATURE4"] / cost_seconds["NATURAL32"],
            "q8ToNaturalRenderTimeRatio": cost_seconds["STRATIFIED8"] / cost_seconds["NATURAL32"],
            "q8ToQ4RenderTimeRatio": cost_seconds["STRATIFIED8"] / cost_seconds["QUADRATURE4"],
            "scope": "Blender render timers only; excludes orchestration, I/O and compositing overhead",
        },
        "gates": gates,
        "nonClaims": spec["nonClaims"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"BFS_B32_HOLDOUT_ANALYZE_OK decision={decision} "
        f"q4_mean={result['summary']['q4ToNaturalEdgeMean']:.6f} "
        f"q8_mean={result['summary']['q8ToNaturalEdgeMean']:.6f} "
        f"q8_q4_mean={result['summary']['q8ToQ4EdgeMean']:.6f}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B32_HOLDOUT_ANALYZE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
