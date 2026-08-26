"""Derive the frozen B24 numeric envelope from B21 and B23 evidence only."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"pairCount": len(rows)}
    for key in ["meanError", "rmsError", "maxAbsoluteError", "failurePixels"]:
        values = [float(row[key]) for row in rows]
        summary[key] = {
            "minimum": min(values),
            "p50": quantile(values, 0.5),
            "p90": quantile(values, 0.9),
            "p95": quantile(values, 0.95),
            "p99": quantile(values, 0.99),
            "maximum": max(values),
        }
    return summary


def load_rows(paths: list[Path], key: str) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    sources = []
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(document[key])
        sources.append({"uri": path, "sha256": sha256_file(path)})
    return rows, sources


def yee_inventory(repo: Path, frames: list[int]) -> dict[str, Any]:
    root = repo / "experiments/dual-output-localization-v0-1/work"
    pairs = [("A", "B"), ("A", "C"), ("B", "C")]
    observations = []
    for frame in frames:
        for a_id, b_id in pairs:
            name = f"frame-{frame:04d}.png"
            a_path, b_path = root / a_id / name, root / b_id / name
            a, b = oiio.ImageBuf(str(a_path)), oiio.ImageBuf(str(b_path))
            if not a.initialized or not b.initialized:
                raise RuntimeError(f"Cannot decode B21 Yee pair {frame}/{a_id}/{b_id}")
            result = oiio.CompareResults()
            oiio.ImageBufAlgo.compare_Yee(a, b, result, 100.0, 45.0)
            observations.append({
                "frame": frame,
                "pair": f"{a_id}-{b_id}",
                "aSha256": sha256_file(a_path),
                "bSha256": sha256_file(b_path),
                "perceptualFailurePixels": int(result.nfail),
                "maximumPerceptualError": float(result.maxerror),
            })
    return {
        "metric": "OpenImageIO ImageBufAlgo.compare_Yee",
        "luminanceCdM2": 100.0,
        "fieldOfViewDegrees": 45.0,
        "pairCount": len(observations),
        "pairsWithFailures": sum(item["perceptualFailurePixels"] > 0 for item in observations),
        "totalFailurePixels": sum(item["perceptualFailurePixels"] for item in observations),
        "maximumFailurePixelsPerPair": max(item["perceptualFailurePixels"] for item in observations),
        "observations": observations,
    }


def main() -> None:
    args = parse_args()
    repo = args.repo.resolve()
    b21_comparisons = repo / "experiments/dual-output-localization-v0-1/evidence/comparisons"
    b23_comparisons = repo / "experiments/eevee-repeated-render-boundary-v0-1/evidence/comparisons"
    b21_png_paths = [b21_comparisons / f"PNG8_DISPLAY-{pair}.comparison.json" for pair in ["A-B", "A-C", "B-C"]]
    b21_exr_paths = [b21_comparisons / f"EXR32_SCENE_LINEAR-{pair}.comparison.json" for pair in ["A-B", "A-C", "B-C"]]
    b23_exr_paths = [b23_comparisons / f"{gate}.comparison.json" for gate in ["WITHIN_PERSIST", "PERSIST_CROSS", "FRESH_CROSS"]]
    b21_png_rows, b21_png_sources = load_rows(b21_png_paths, "frames")
    b21_exr_rows, b21_exr_sources = load_rows(b21_exr_paths, "frames")
    b23_exr_rows, b23_exr_sources = load_rows(b23_exr_paths, "pairs")
    exr_rows = b21_exr_rows + b23_exr_rows
    sentinels = [1, 5, 20, 35, 38, 47, 83, 93, 103, 110, 114, 144]
    yee = yee_inventory(repo, sentinels)

    exr_summary = summarize(exr_rows)
    png_summary = summarize(b21_png_rows)
    envelope = {
        "EXR32_SCENE_LINEAR": {
            "maximumAbsoluteErrorAtMost": 1.0 / 128.0,
            "rmsErrorAtMost": 1.0 / 65536.0,
            "zeroThresholdFailurePixelsAtMost": 512,
            "derivationMustFit": True,
        },
        "PNG8_DISPLAY": {
            "maximumAbsoluteErrorAtMost": 0.003922,
            "rmsErrorAtMost": 1.0 / 65536.0,
            "zeroThresholdFailurePixelsAtMost": 16,
            "yeeFailurePixelsAtMost": 0,
            "yeeLuminanceCdM2": 100.0,
            "yeeFieldOfViewDegrees": 45.0,
            "derivationMustFit": True,
        },
    }
    exr_fits = (
        exr_summary["maxAbsoluteError"]["maximum"] <= envelope["EXR32_SCENE_LINEAR"]["maximumAbsoluteErrorAtMost"]
        and exr_summary["rmsError"]["maximum"] <= envelope["EXR32_SCENE_LINEAR"]["rmsErrorAtMost"]
        and exr_summary["failurePixels"]["maximum"] <= envelope["EXR32_SCENE_LINEAR"]["zeroThresholdFailurePixelsAtMost"]
    )
    png_fits = (
        png_summary["maxAbsoluteError"]["maximum"] <= envelope["PNG8_DISPLAY"]["maximumAbsoluteErrorAtMost"]
        and png_summary["rmsError"]["maximum"] <= envelope["PNG8_DISPLAY"]["rmsErrorAtMost"]
        and png_summary["failurePixels"]["maximum"] <= envelope["PNG8_DISPLAY"]["zeroThresholdFailurePixelsAtMost"]
        and yee["maximumFailurePixelsPerPair"] <= envelope["PNG8_DISPLAY"]["yeeFailurePixelsAtMost"]
    )
    if not exr_fits or not png_fits:
        raise RuntimeError(f"Derived envelope does not contain derivation evidence: EXR={exr_fits} PNG={png_fits}")

    output = {
        "documentType": "BFS_B24_PRODUCTION_TOLERANCE_DERIVATION",
        "version": "0.1.0",
        "status": "DERIVATION_ONLY_NOT_VALIDATION",
        "tool": {"uri": str(Path(__file__).resolve().relative_to(repo)), "sha256": sha256_file(Path(__file__))},
        "runtime": {"decoder": f"OpenImageIO {oiio.VERSION_STRING}"},
        "sources": {
            "b21PngComparisons": [{"uri": str(item["uri"].relative_to(repo)), "sha256": item["sha256"]} for item in b21_png_sources],
            "b21ExrComparisons": [{"uri": str(item["uri"].relative_to(repo)), "sha256": item["sha256"]} for item in b21_exr_sources],
            "b23ExrComparisons": [{"uri": str(item["uri"].relative_to(repo)), "sha256": item["sha256"]} for item in b23_exr_sources],
        },
        "derivation": {
            "EXR32_SCENE_LINEAR": exr_summary,
            "PNG8_DISPLAY": png_summary,
            "PNG8_YEE_AUXILIARY": yee,
        },
        "selectionMethod": {
            "principle": "Choose simple outward ceilings that contain every pre-holdout pair, then freeze them before rendering algorithmically selected holdout frames.",
            "exrMaxGrid": "next binary ceiling 1/128 above observed maximum",
            "rmsGrid": "next binary ceiling 1/65536 above observed maximum",
            "failurePixelGrid": "next power-of-two ceiling",
            "pngMaxGrid": "six-decimal outward ceiling over approximately one 8-bit code value",
            "validationRule": "The derivation set cannot validate the envelope; every holdout pair must pass without threshold revision.",
        },
        "candidateEnvelope": envelope,
        "derivationFits": {"EXR32_SCENE_LINEAR": exr_fits, "PNG8_DISPLAY": png_fits},
        "nonClaims": [
            "This envelope is a numeric repeatability candidate, not a human visibility threshold.",
            "The Yee defaults model a nominal office-display condition and are not a calibrated cinema audit.",
            "The B21/B23 derivation evidence cannot validate thresholds selected from it.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B24_DERIVATION_OK EXR={len(exr_rows)} PNG={len(b21_png_rows)} YEE={yee['pairCount']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B24_DERIVATION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
