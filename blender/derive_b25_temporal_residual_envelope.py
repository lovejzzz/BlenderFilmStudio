"""Derive (but do not validate) a temporal cross-run residual envelope.

For two renders A and B, the per-frame signed residual is R_t = A_t - B_t.
The temporal residual delta is T_t = R_t - R_(t-1). Shared scene motion
therefore cancels; only change in cross-run disagreement remains.
"""

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
    parser.add_argument("--pair", action="append", required=True, help="ID:A_DIR:B_DIR")
    parser.add_argument("--frame-start", type=int, default=1)
    parser.add_argument("--frame-end", type=int, default=144)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rgb(path: Path) -> tuple[np.ndarray, dict]:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot decode {path}: {image.geterror()}")
    spec = image.spec()
    if spec.width != 960 or spec.height != 540 or list(spec.channelnames) != ["R", "G", "B", "A"]:
        raise RuntimeError(f"Unexpected layout for {path}: {spec.width}x{spec.height} {list(spec.channelnames)}")
    pixels = image.get_pixels(oiio.FLOAT)
    return pixels[:, :, :3].astype(np.float32, copy=False), {
        "width": spec.width,
        "height": spec.height,
        "channelsUsed": ["R", "G", "B"],
        "decodedPixelType": "float32",
    }


def parse_pair(value: str) -> tuple[str, Path, Path]:
    parts = value.split(":", 2)
    if len(parts) != 3 or not parts[0]:
        raise ValueError(f"Invalid --pair {value!r}; expected ID:A_DIR:B_DIR")
    return parts[0], Path(parts[1]), Path(parts[2])


def transition_metrics(delta: np.ndarray) -> dict:
    absolute = np.abs(delta)
    changed_mask = np.any(absolute > 0.0, axis=2)
    return {
        "maximumAbsoluteResidualDelta": float(absolute.max()),
        "rmsResidualDelta": float(math.sqrt(float(np.mean(np.square(delta, dtype=np.float64))))),
        "changedPixels": int(np.count_nonzero(changed_mask)),
        "changedChannels": int(np.count_nonzero(absolute > 0.0)),
    }


def main() -> None:
    args = parse_args()
    pairs = [parse_pair(value) for value in args.pair]
    if args.frame_start >= args.frame_end:
        raise ValueError("Need at least two frames")

    datasets = []
    all_transitions = []
    input_files = []
    layout = None
    for pair_id, a_dir, b_dir in pairs:
        transitions = []
        previous_residual = None
        for frame in range(args.frame_start, args.frame_end + 1):
            name = f"frame-{frame:04d}.png"
            a_path, b_path = a_dir / name, b_dir / name
            if not a_path.is_file() or not b_path.is_file():
                raise FileNotFoundError(f"Missing pair input at frame {frame}: {a_path} / {b_path}")
            a_rgb, current_layout = load_rgb(a_path)
            b_rgb, other_layout = load_rgb(b_path)
            if current_layout != other_layout or (layout is not None and current_layout != layout):
                raise RuntimeError(f"Layout mismatch at {pair_id} frame {frame}")
            layout = current_layout
            residual = a_rgb - b_rgb
            input_files.append({
                "pairId": pair_id,
                "frame": frame,
                "a": {"path": str(a_path), "sha256": sha256_file(a_path)},
                "b": {"path": str(b_path), "sha256": sha256_file(b_path)},
            })
            if previous_residual is not None:
                metrics = {
                    "fromFrame": frame - 1,
                    "toFrame": frame,
                    **transition_metrics(residual - previous_residual),
                }
                transitions.append(metrics)
                all_transitions.append({"pairId": pair_id, **metrics})
            previous_residual = residual
        datasets.append({
            "pairId": pair_id,
            "aDirectory": str(a_dir),
            "bDirectory": str(b_dir),
            "frameCount": args.frame_end - args.frame_start + 1,
            "transitionCount": len(transitions),
            "exactTransitions": sum(item["maximumAbsoluteResidualDelta"] == 0.0 for item in transitions),
            "maximumAbsoluteResidualDelta": max(item["maximumAbsoluteResidualDelta"] for item in transitions),
            "maximumRmsResidualDelta": max(item["rmsResidualDelta"] for item in transitions),
            "maximumChangedPixels": max(item["changedPixels"] for item in transitions),
            "transitions": transitions,
        })

    maxima = {
        "maximumAbsoluteResidualDelta": max(item["maximumAbsoluteResidualDelta"] for item in all_transitions),
        "maximumRmsResidualDelta": max(item["rmsResidualDelta"] for item in all_transitions),
        "maximumChangedPixels": max(item["changedPixels"] for item in all_transitions),
        "maximumChangedChannels": max(item["changedChannels"] for item in all_transitions),
    }
    candidate = {
        "maximumAbsoluteResidualDeltaAtMost": 2.0 / 255.0,
        "rmsResidualDeltaAtMost": 1.0 / 32768.0,
        "changedPixelsAtMost": 64,
        "derivationMustFit": True,
    }
    fits = (
        maxima["maximumAbsoluteResidualDelta"] <= candidate["maximumAbsoluteResidualDeltaAtMost"]
        and maxima["maximumRmsResidualDelta"] <= candidate["rmsResidualDeltaAtMost"]
        and maxima["maximumChangedPixels"] <= candidate["changedPixelsAtMost"]
    )
    if not fits:
        raise RuntimeError(f"Candidate envelope does not contain derivation data: {maxima}")

    report = {
        "documentType": "BFS_B25_TEMPORAL_RESIDUAL_ENVELOPE_DERIVATION",
        "version": "0.1.0",
        "status": "DERIVATION_ONLY_NOT_VALIDATION",
        "question": "How large was cross-run temporal residual change in four retained full-sequence pairs under the candidate production profile?",
        "definition": {
            "signedResidual": "R_t = A_t - B_t",
            "temporalResidualDelta": "T_t = R_t - R_(t-1) = (A_t-A_(t-1)) - (B_t-B_(t-1))",
            "channels": ["R", "G", "B"],
            "colorDomain": "decoded ACES 2 SDR display PNG8 normalized to [0,1]",
            "purpose": "Cancel shared scene motion and measure frame-to-frame change in cross-run disagreement.",
        },
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
        "numpy": np.__version__,
        "layout": layout,
        "frameStart": args.frame_start,
        "frameEnd": args.frame_end,
        "pairCount": len(datasets),
        "transitionCount": len(all_transitions),
        "inputFileCount": len(input_files) * 2,
        "maxima": maxima,
        "candidateEnvelope": candidate,
        "candidateContainsAllDerivationTransitions": fits,
        "datasets": datasets,
        "inputFiles": input_files,
        "explicitNonClaims": [
            "This artifact derives a candidate threshold and does not validate it.",
            "The metric is a numerical temporal proxy, not a calibrated visibility, flicker, or cinematic-quality judgment.",
            "The retained sequences are one scene, one machine, one Blender build, one render profile and PNG8 display output.",
            "Thresholds must be frozen before new B25 holdout sequences are rendered and must not be widened after observation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B25_DERIVATION_OK pairs={len(datasets)} transitions={len(all_transitions)} maxima={maxima}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B25_DERIVATION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
