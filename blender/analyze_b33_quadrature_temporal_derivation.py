"""Analyze preregistered B33 consecutive-frame temporal-error derivation outputs."""

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


def delta_metrics(delta: np.ndarray, mask: np.ndarray | None = None) -> dict[str, float | int]:
    selected = delta if mask is None else delta[mask]
    absolute = np.abs(selected)
    sampled_pixels = int(selected.shape[0] if selected.ndim == 2 else selected.shape[0] * selected.shape[1])
    return {
        "sampledPixels": sampled_pixels,
        "mae": float(np.mean(absolute)),
        "rmse": float(math.sqrt(float(np.mean(selected * selected)))),
        "maximumAbsoluteError": float(np.max(absolute)),
    }


def difference_metrics(first: np.ndarray, second: np.ndarray, mask: np.ndarray | None = None) -> dict[str, float | int]:
    return delta_metrics(first - second, mask)


def exact_top_k(magnitude: np.ndarray, target: int, label: str) -> tuple[np.ndarray, dict[str, Any]]:
    flat = magnitude.reshape(-1)
    indices = np.arange(flat.size, dtype=np.int64)
    selected = np.lexsort((indices, -flat))[:target]
    mask_flat = np.zeros(flat.size, dtype=bool)
    mask_flat[selected] = True
    mask = mask_flat.reshape(magnitude.shape)
    boundary = float(flat[selected[-1]])
    if int(np.count_nonzero(mask)) != target:
        raise RuntimeError(f"{label} exact top-k cardinality mismatch")
    return mask, {
        "label": label,
        "rule": "exact top-k: magnitude descending, flattened C-row-major index ascending",
        "selectedPixels": target,
        "boundaryMagnitude": boundary,
        "valuesGreaterThanBoundary": int(np.count_nonzero(flat > boundary)),
        "valuesEqualToBoundary": int(np.count_nonzero(flat == boundary)),
        "selectedValuesEqualToBoundary": int(np.count_nonzero(flat[selected] == boundary)),
    }


def spatial_edge_magnitude(reference: np.ndarray) -> np.ndarray:
    gx = np.zeros(reference.shape[:2], dtype=np.float64)
    gy = np.zeros(reference.shape[:2], dtype=np.float64)
    dx = reference[:, 2:, :] - reference[:, :-2, :]
    dy = reference[2:, :, :] - reference[:-2, :, :]
    gx[:, 1:-1] = np.sqrt(np.sum(dx * dx, axis=2)) * 0.5
    gy[1:-1, :] = np.sqrt(np.sum(dy * dy, axis=2)) * 0.5
    return np.sqrt(gx * gx + gy * gy)


def method_frame_arrays(arrays: dict[str, dict[int, np.ndarray]], frame: int) -> dict[str, list[np.ndarray]]:
    return {
        "NATURAL32": [arrays[f"NATURAL32_{replicate}"][frame] for replicate in ("A", "B")],
        "QUADRATURE4": [
            np.mean([arrays[f"Q4_{index}_{replicate}"][frame] for index in range(1, 5)], axis=0)
            for replicate in ("A", "B")
        ],
        "STRATIFIED8": [
            np.mean([arrays[f"Q8_{index}_{replicate}"][frame] for index in range(1, 9)], axis=0)
            for replicate in ("A", "B")
        ],
    }


def finite_positive(value: float) -> bool:
    return math.isfinite(value) and value > 0.0


def main() -> None:
    args = parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if spec.get("documentType") != "BFS_QUADRATURE_TEMPORAL_DERIVATION_SPEC":
        raise RuntimeError("B33 derivation spec type mismatch")
    if index.get("documentType") != "BFS_B33_QUADRATURE_TEMPORAL_ANALYSIS_INDEX":
        raise RuntimeError("B33 analysis index type mismatch")
    if index.get("derivationSpecSha256") != sha256_file(args.spec):
        raise RuntimeError("B33 index/spec binding mismatch")
    processes = index.get("processes", [])
    schedule = expected_schedule()
    if [item.get("replicateId") for item in processes] != schedule:
        raise RuntimeError("B33 process schedule mismatch")
    if len({item.get("processId") for item in processes}) != spec["design"]["totalProcesses"]:
        raise RuntimeError("B33 process IDs are missing or duplicated")

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

    references = {
        frame: (arrays["REFERENCE1024_A"][frame] + arrays["REFERENCE1024_B"][frame]) * 0.5
        for frame in frames
    }
    method_frames = {frame: method_frame_arrays(arrays, frame) for frame in frames}
    frame_repeatability = []
    for frame in frames:
        frame_repeatability.append({
            "frame": frame,
            "q4CompositeAB": difference_metrics(
                method_frames[frame]["QUADRATURE4"][0], method_frames[frame]["QUADRATURE4"][1]
            ),
            "q8CompositeAB": difference_metrics(
                method_frames[frame]["STRATIFIED8"][0], method_frames[frame]["STRATIFIED8"][1]
            ),
        })

    target = spec["analysis"]["topKPixels"]
    transitions = []
    all_denominators = []
    for previous_frame, frame in zip(frames[:-1], frames[1:], strict=True):
        previous_reference, reference = references[previous_frame], references[frame]
        previous_edge, previous_edge_meta = exact_top_k(
            spatial_edge_magnitude(previous_reference), target, f"spatial-edge-frame-{previous_frame}"
        )
        current_edge, current_edge_meta = exact_top_k(
            spatial_edge_magnitude(reference), target, f"spatial-edge-frame-{frame}"
        )
        edge_union = previous_edge | current_edge
        motion_magnitude = np.sqrt(np.sum((reference - previous_reference) ** 2, axis=2))
        motion_mask, motion_meta = exact_top_k(motion_magnitude, target, f"reference-motion-{previous_frame}-{frame}")
        masks = {
            "global": None,
            "spatialEdgeUnion": edge_union,
            "referenceMotionTopK": motion_mask,
        }
        method_deltas: dict[str, list[np.ndarray]] = {}
        method_results: dict[str, Any] = {}
        for method in ("NATURAL32", "QUADRATURE4", "STRATIFIED8"):
            deltas = []
            replicate_results = []
            for replicate_index, replicate in enumerate(("A", "B")):
                current_error = method_frames[frame][method][replicate_index] - reference
                previous_error = method_frames[previous_frame][method][replicate_index] - previous_reference
                temporal_delta = current_error - previous_error
                deltas.append(temporal_delta)
                replicate_results.append({
                    "replicate": replicate,
                    "domains": {name: delta_metrics(temporal_delta, mask) for name, mask in masks.items()},
                })
            method_deltas[method] = deltas
            method_results[method] = {
                "replicates": replicate_results,
                "withinMethodTemporalAB": {
                    name: difference_metrics(deltas[0], deltas[1], mask) for name, mask in masks.items()
                },
                "rmseMean": {
                    name: float(np.mean([item["domains"][name]["rmse"] for item in replicate_results]))
                    for name in masks
                },
            }

        ref_residual_delta = (
            (arrays["REFERENCE1024_A"][frame] - arrays["REFERENCE1024_B"][frame])
            - (arrays["REFERENCE1024_A"][previous_frame] - arrays["REFERENCE1024_B"][previous_frame])
        )
        reference_residual = {name: delta_metrics(ref_residual_delta, mask) for name, mask in masks.items()}
        ratios: dict[str, dict[str, float]] = {}
        reliability: dict[str, float] = {}
        for name in masks:
            natural = method_results["NATURAL32"]["rmseMean"][name]
            q4 = method_results["QUADRATURE4"]["rmseMean"][name]
            q8 = method_results["STRATIFIED8"]["rmseMean"][name]
            all_denominators.extend([natural, q4])
            ratios[name] = {
                "q4ToNaturalRmse": q4 / natural if finite_positive(natural) else math.inf,
                "q8ToNaturalRmse": q8 / natural if finite_positive(natural) else math.inf,
                "q8ToQ4Rmse": q8 / q4 if finite_positive(q4) else math.inf,
            }
            reliability[name] = reference_residual[name]["rmse"] / natural if finite_positive(natural) else math.inf
        transitions.append({
            "fromFrame": previous_frame,
            "toFrame": frame,
            "masks": {
                "spatialEdgePrevious": previous_edge_meta,
                "spatialEdgeCurrent": current_edge_meta,
                "spatialEdgeUnionPixels": int(np.count_nonzero(edge_union)),
                "referenceMotion": motion_meta,
            },
            "referenceResidualDelta": reference_residual,
            "referenceReliabilityRatio": reliability,
            "methods": method_results,
            "ratios": ratios,
        })

    gates = spec["derivationValidityGates"]
    reference_reliable = all(
        math.isfinite(value) and value <= gates["referenceReliabilityRatioMaximumEveryTransitionEveryDomain"]
        for item in transitions for value in item["referenceReliabilityRatio"].values()
    )
    frame_exact = all(
        item["q4CompositeAB"]["rmse"] == gates["q4CompositeABRmseExactEveryFrame"]
        and item["q8CompositeAB"]["rmse"] == gates["q8CompositeABRmseExactEveryFrame"]
        for item in frame_repeatability
    )
    temporal_exact = all(
        item["methods"]["QUADRATURE4"]["withinMethodTemporalAB"][domain]["rmse"]
        == gates["q4TemporalABRmseExactEveryTransition"]
        and item["methods"]["STRATIFIED8"]["withinMethodTemporalAB"][domain]["rmse"]
        == gates["q8TemporalABRmseExactEveryTransition"]
        for item in transitions for domain in spec["analysis"]["domains"]
    )
    denominators_valid = all(finite_positive(value) for value in all_denominators)
    usable = reference_reliable and frame_exact and temporal_exact and denominators_valid
    decision = spec["derivationDecision"]["allValidityGatesPass"] if usable else spec["derivationDecision"]["otherwise"]

    domains = spec["analysis"]["domains"]
    ratio_summary = {}
    for domain in domains:
        ratio_summary[domain] = {}
        for key in ("q4ToNaturalRmse", "q8ToNaturalRmse", "q8ToQ4Rmse"):
            values = [item["ratios"][domain][key] for item in transitions]
            ratio_summary[domain][key] = {
                "mean": float(np.mean(values)), "maximum": float(np.max(values)), "minimum": float(np.min(values))
            }
    cost_seconds = {
        "NATURAL32": sum(item["totalRenderSeconds"] for item in processes if item["cell"] == "NATURAL32"),
        "REFERENCE1024": sum(item["totalRenderSeconds"] for item in processes if item["cell"] == "REFERENCE1024"),
        "QUADRATURE4": sum(item["totalRenderSeconds"] for item in processes if item["cell"].startswith("Q4_")),
        "STRATIFIED8": sum(item["totalRenderSeconds"] for item in processes if item["cell"].startswith("Q8_")),
    }
    result = {
        "documentType": "BFS_B33_QUADRATURE_TEMPORAL_DERIVATION_ANALYSIS",
        "version": spec["version"],
        "derivationSpecSha256": sha256_file(args.spec),
        "indexSha256": sha256_file(args.index),
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
        "layout": layout,
        "valid": True,
        "status": "EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION",
        "decision": decision,
        "validityComponents": {
            "referenceReliable": reference_reliable,
            "frameCompositeExact": frame_exact,
            "temporalCompositeExact": temporal_exact,
            "ratioDenominatorsFinitePositive": denominators_valid,
        },
        "frameRepeatability": frame_repeatability,
        "transitions": transitions,
        "summary": {
            "frames": len(frames),
            "transitions": len(transitions),
            "maximumReferenceReliabilityRatio": max(
                value for item in transitions for value in item["referenceReliabilityRatio"].values()
            ),
            "ratioByDomain": ratio_summary,
        },
        "cost": {
            "renderSeconds": cost_seconds,
            "q4ToNaturalRenderTimeRatio": cost_seconds["QUADRATURE4"] / cost_seconds["NATURAL32"],
            "q8ToNaturalRenderTimeRatio": cost_seconds["STRATIFIED8"] / cost_seconds["NATURAL32"],
            "q8ToQ4RenderTimeRatio": cost_seconds["STRATIFIED8"] / cost_seconds["QUADRATURE4"],
            "scope": "Blender render timers only; excludes orchestration, I/O and compositing overhead",
        },
        "derivationValidityGates": gates,
        "nonClaims": spec["nonClaims"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    motion = ratio_summary["referenceMotionTopK"]
    print(
        f"BFS_B33_DERIVATION_ANALYZE_OK decision={decision} "
        f"q4_motion_mean={motion['q4ToNaturalRmse']['mean']:.6f} "
        f"q8_motion_mean={motion['q8ToNaturalRmse']['mean']:.6f} "
        f"q8_q4_motion_mean={motion['q8ToQ4Rmse']['mean']:.6f}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B33_DERIVATION_ANALYZE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
