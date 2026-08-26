"""Compare two complete B25 PNG sequences against frozen static/temporal envelopes."""

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
    parser.add_argument("--a-dir", type=Path, required=True)
    parser.add_argument("--b-dir", type=Path, required=True)
    parser.add_argument("--frame-start", type=int, required=True)
    parser.add_argument("--frame-end", type=int, required=True)
    parser.add_argument("--static-envelope", required=True)
    parser.add_argument("--temporal-envelope", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    static_envelope = json.loads(args.static_envelope)
    temporal_envelope = json.loads(args.temporal_envelope)
    frames = []
    transitions = []
    previous_residual = None
    previous_frame = None
    expected_layout = [960, 540, ["R", "G", "B", "A"], "uint8"]

    for frame in range(args.frame_start, args.frame_end + 1):
        name = f"frame-{frame:04d}.png"
        a_path, b_path = args.a_dir / name, args.b_dir / name
        a, b = oiio.ImageBuf(str(a_path)), oiio.ImageBuf(str(b_path))
        if not a.initialized or not b.initialized:
            raise RuntimeError(f"Cannot decode {name}: {a.geterror()} / {b.geterror()}")
        a_spec, b_spec = a.spec(), b.spec()
        a_layout = [a_spec.width, a_spec.height, list(a_spec.channelnames), str(a_spec.format)]
        b_layout = [b_spec.width, b_spec.height, list(b_spec.channelnames), str(b_spec.format)]
        if a_layout != expected_layout or b_layout != expected_layout:
            raise RuntimeError(f"Layout mismatch for {name}: {a_layout} / {b_layout}")

        numeric = oiio.ImageBufAlgo.compare(a, b, 0.0, 0.0)
        static_checks = {
            "maximumAbsoluteError": float(numeric.maxerror) <= float(static_envelope["maximumAbsoluteErrorAtMost"]),
            "rmsError": float(numeric.rms_error) <= float(static_envelope["rmsErrorAtMost"]),
            "zeroThresholdFailurePixels": int(numeric.nfail) <= int(static_envelope["zeroThresholdFailurePixelsAtMost"]),
        }
        a_sha, b_sha = sha256_file(a_path), sha256_file(b_path)
        frames.append({
            "frame": frame,
            "name": name,
            "aSha256": a_sha,
            "bSha256": b_sha,
            "containerExact": a_sha == b_sha,
            "decodedPixelExact": float(numeric.maxerror) == 0.0 and int(numeric.nfail) == 0,
            "maxAbsoluteError": float(numeric.maxerror),
            "rmsError": float(numeric.rms_error),
            "failurePixels": int(numeric.nfail),
            "staticEnvelopeChecks": static_checks,
            "staticEnvelopePass": all(static_checks.values()),
        })

        a_pixels = a.get_pixels(oiio.FLOAT)[:, :, :3].astype(np.float32, copy=False)
        b_pixels = b.get_pixels(oiio.FLOAT)[:, :, :3].astype(np.float32, copy=False)
        residual = a_pixels - b_pixels
        if previous_residual is not None:
            delta = residual - previous_residual
            absolute = np.abs(delta)
            max_delta = float(absolute.max())
            rms_delta = float(math.sqrt(float(np.mean(np.square(delta, dtype=np.float64)))))
            changed_pixels = int(np.count_nonzero(np.any(absolute > 0.0, axis=2)))
            checks = {
                "maximumAbsoluteResidualDelta": max_delta <= float(temporal_envelope["maximumAbsoluteResidualDeltaAtMost"]),
                "rmsResidualDelta": rms_delta <= float(temporal_envelope["rmsResidualDeltaAtMost"]),
                "changedPixels": changed_pixels <= int(temporal_envelope["changedPixelsAtMost"]),
            }
            transitions.append({
                "fromFrame": previous_frame,
                "toFrame": frame,
                "maximumAbsoluteResidualDelta": max_delta,
                "rmsResidualDelta": rms_delta,
                "changedPixels": changed_pixels,
                "changedChannels": int(np.count_nonzero(absolute > 0.0)),
                "temporalEnvelopeChecks": checks,
                "temporalEnvelopePass": all(checks.values()),
            })
        previous_residual, previous_frame = residual, frame

    report = {
        "documentType": "BFS_B25_TEMPORAL_RESIDUAL_COMPARISON",
        "version": "0.1.0",
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
        "numpy": np.__version__,
        "layout": {"width": 960, "height": 540, "channels": ["R", "G", "B", "A"], "pixelFormat": "uint8"},
        "temporalChannels": ["R", "G", "B"],
        "frozenStaticEnvelope": static_envelope,
        "frozenTemporalEnvelope": temporal_envelope,
        "frameStart": args.frame_start,
        "frameEnd": args.frame_end,
        "frameCount": len(frames),
        "transitionCount": len(transitions),
        "containerExactFrames": sum(item["containerExact"] for item in frames),
        "decodedPixelExactFrames": sum(item["decodedPixelExact"] for item in frames),
        "staticEnvelopePassFrames": sum(item["staticEnvelopePass"] for item in frames),
        "temporalExactTransitions": sum(item["maximumAbsoluteResidualDelta"] == 0.0 for item in transitions),
        "temporalEnvelopePassTransitions": sum(item["temporalEnvelopePass"] for item in transitions),
        "maximumAbsoluteError": max(item["maxAbsoluteError"] for item in frames),
        "maximumRmsError": max(item["rmsError"] for item in frames),
        "maximumFailurePixels": max(item["failurePixels"] for item in frames),
        "maximumAbsoluteResidualDelta": max(item["maximumAbsoluteResidualDelta"] for item in transitions),
        "maximumRmsResidualDelta": max(item["rmsResidualDelta"] for item in transitions),
        "maximumChangedPixels": max(item["changedPixels"] for item in transitions),
        "frames": frames,
        "transitions": transitions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "BFS_B25_COMPARE_OK "
        f"static={report['staticEnvelopePassFrames']}/{report['frameCount']} "
        f"temporal={report['temporalEnvelopePassTransitions']}/{report['transitionCount']}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B25_COMPARE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
