"""Apply the preregistered B32.1 Q8-versus-Q4 derivation decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


FRAMES = [37, 72, 103]
POINT_IDS = [f"S{index}" for index in range(1, 9)]
POINTS = [
    [-0.375, -0.375], [-0.375, 0.125], [-0.125, -0.125], [-0.125, 0.375],
    [0.125, -0.375], [0.125, 0.125], [0.375, -0.125], [0.375, 0.375],
]
WEIGHTS = [0.125] * 8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b321-work", type=Path, required=True)
    parser.add_argument("--b321-results", type=Path, required=True)
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
    dx = reference[:, 2:, :] - reference[:, :-2, :]
    dy = reference[2:, :, :] - reference[:-2, :, :]
    gx[:, 1:-1] = np.sqrt(np.sum(dx * dx, axis=2)) * 0.5
    gy[1:-1, :] = np.sqrt(np.sum(dy * dy, axis=2)) * 0.5
    magnitude = np.sqrt(gx * gx + gy * gy)
    return magnitude >= float(np.quantile(magnitude, 0.95))


def validate_result(result: dict) -> None:
    expected_design = {
        "frames": FRAMES,
        "points": POINTS,
        "weights": WEIGHTS,
        "processes": 16,
        "renderCalls": 48,
    }
    if result.get("documentType") != "BFS_B32_STRATIFIED8_DERIVATION_RESULT":
        raise RuntimeError("B32.1 result document type mismatch")
    if result.get("design") != expected_design:
        raise RuntimeError("B32.1 frozen design mismatch")
    reports = result.get("reports", [])
    expected_ids = {f"{point}_{replicate}" for point in POINT_IDS for replicate in ("A", "B")}
    if len(reports) != 16 or {item.get("id") for item in reports} != expected_ids:
        raise RuntimeError("B32.1 report cells mismatch")
    if len({item.get("processId") for item in reports}) != 16:
        raise RuntimeError("B32.1 process IDs are not unique")


def main() -> None:
    args = parse_args()
    b321 = json.loads(args.b321_results.read_text(encoding="utf-8"))
    b32 = json.loads(args.b32_results.read_text(encoding="utf-8"))
    b31 = json.loads(args.b31_results.read_text(encoding="utf-8"))
    validate_result(b321)
    observations = []
    for frame in FRAMES:
        ref_a = read_rgb(args.b31_work / "REFERENCE1024_A" / f"frame-{frame:04d}.exr")
        ref_b = read_rgb(args.b31_work / "REFERENCE1024_B" / f"frame-{frame:04d}.exr")
        reference = (ref_a + ref_b) * 0.5
        mask = edge_mask(reference)
        natural = [read_rgb(args.b31_work / f"NATURAL32_{rep}" / f"frame-{frame:04d}.exr") for rep in ("A", "B")]
        center = [read_rgb(args.b31_work / f"CENTER32_{rep}" / f"frame-{frame:04d}.exr") for rep in ("A", "B")]
        q4 = []
        q8 = []
        for replicate in ("A", "B"):
            q4.append(np.mean([
                read_rgb(args.b32_work / f"Q{index}_{replicate}" / f"frame-{frame:04d}.exr")
                for index in range(1, 5)
            ], axis=0))
            q8.append(np.mean([
                read_rgb(args.b321_work / f"S{index}_{replicate}" / f"frame-{frame:04d}.exr")
                for index in range(1, 9)
            ], axis=0))
        natural_edge = float(np.mean([rmse(item, reference, mask) for item in natural]))
        center_edge = float(np.mean([rmse(item, reference, mask) for item in center]))
        q4_edge = float(np.mean([rmse(item, reference, mask) for item in q4]))
        q8_edge = float(np.mean([rmse(item, reference, mask) for item in q8]))
        natural_global = float(np.mean([rmse(item, reference) for item in natural]))
        q8_global = float(np.mean([rmse(item, reference) for item in q8]))
        observations.append({
            "frame": frame,
            "edgePixels": int(np.count_nonzero(mask)),
            "edgeRmse": {"NATURAL32": natural_edge, "CENTER32": center_edge, "QUADRATURE4": q4_edge, "STRATIFIED8": q8_edge},
            "globalRmse": {"NATURAL32": natural_global, "STRATIFIED8": q8_global},
            "ratios": {
                "q8ToNaturalEdge": q8_edge / natural_edge,
                "q8ToCenterEdge": q8_edge / center_edge,
                "q8ToQ4Edge": q8_edge / q4_edge,
                "q8ToNaturalGlobal": q8_global / natural_global,
            },
            "q8ABRmse": rmse(q8[0], q8[1]),
        })

    repeatability = all(item["q8ABRmse"] == 0.0 for item in observations)
    q8_not_worse = all(item["ratios"]["q8ToQ4Edge"] <= 1.0 for item in observations)
    q8_to_q4_mean = float(np.mean([item["ratios"]["q8ToQ4Edge"] for item in observations]))
    near_natural = all(item["ratios"]["q8ToNaturalEdge"] <= 1.10 for item in observations)
    if not repeatability:
        decision = "REJECT_Q8_REPEATABILITY_FAILURE"
    elif not q8_not_worse or q8_to_q4_mean > 0.90:
        decision = "RETAIN_Q4_DIMINISHING_RETURN"
    elif near_natural:
        decision = "PROMOTE_Q4_Q8_COST_CURVE_NEAR_NATURAL"
    else:
        decision = "PROMOTE_Q4_Q8_COST_CURVE_PARTIAL"

    q8_seconds = sum(item["totalRenderSeconds"] for item in b321["reports"])
    q4_seconds = sum(item["totalRenderSeconds"] for item in b32["reports"])
    natural_seconds = sum(item["totalRenderSeconds"] for item in b31["reports"] if item["cell"] == "NATURAL32")
    result = {
        "documentType": "BFS_B32_STRATIFIED8_DERIVATION_ANALYSIS",
        "version": "0.1.0",
        "status": "EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION",
        "decision": decision,
        "valid": True,
        "bindings": {
            "b321ResultsSha256": sha256_file(args.b321_results),
            "b32ResultsSha256": sha256_file(args.b32_results),
            "b31ResultsSha256": sha256_file(args.b31_results),
        },
        "frozenGates": {
            "q8ABRmseExact": 0.0,
            "q8ToQ4EveryFrameMaximum": 1.0,
            "q8ToQ4MeanMaximum": 0.90,
            "q8ToNaturalEveryFrameMaximumForNearNatural": 1.10,
        },
        "observations": observations,
        "aggregate": {
            "repeatabilityExactAllFrames": repeatability,
            "q8NotWorseThanQ4AllFrames": q8_not_worse,
            "q8ToQ4EdgeMean": q8_to_q4_mean,
            "q8ToNaturalEdgeMean": float(np.mean([item["ratios"]["q8ToNaturalEdge"] for item in observations])),
            "q8ToNaturalGlobalMean": float(np.mean([item["ratios"]["q8ToNaturalGlobal"] for item in observations])),
            "nearNaturalAllFrames": near_natural,
            "q8RenderSeconds": q8_seconds,
            "q4RenderSeconds": q4_seconds,
            "naturalRenderSeconds": natural_seconds,
            "q8ToQ4RenderTimeRatio": q8_seconds / q4_seconds,
            "q8ToNaturalRenderTimeRatio": q8_seconds / natural_seconds,
        },
        "nonClaims": [
            "This reuses exposed derivation frames and is not an unseen-frame confirmation.",
            "The B31 NATURAL1024 mean remains a reference proxy, not truth.",
            "Numerical error and render-time ratios do not establish visible or production quality.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"BFS_B32_STRATIFIED8_ANALYZE_OK decision={decision} "
        + " ".join(f"F{item['frame']} q8_natural={item['ratios']['q8ToNaturalEdge']:.6f}" for item in observations)
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B32_STRATIFIED8_ANALYZE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
