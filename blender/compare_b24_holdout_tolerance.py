"""Evaluate one B24 format pair against its frozen per-pair envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a-dir", type=Path, required=True)
    parser.add_argument("--b-dir", type=Path, required=True)
    parser.add_argument("--frames", required=True)
    parser.add_argument("--format", choices=["EXR32_SCENE_LINEAR", "PNG8_DISPLAY"], required=True)
    parser.add_argument("--envelope", required=True)
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
    frames = [int(value) for value in args.frames.split(",")]
    envelope = json.loads(args.envelope)
    is_png = args.format == "PNG8_DISPLAY"
    extension, pixel_format = (".png", "uint8") if is_png else (".exr", "float")
    expected_layout = [960, 540, ["R", "G", "B", "A"], pixel_format]
    comparisons = []
    for frame in frames:
        name = f"frame-{frame:04d}{extension}"
        a_path, b_path = args.a_dir / name, args.b_dir / name
        a, b = oiio.ImageBuf(str(a_path)), oiio.ImageBuf(str(b_path))
        if not a.initialized or not b.initialized:
            raise RuntimeError(f"Cannot decode {name}")
        a_spec, b_spec = a.spec(), b.spec()
        a_layout = [a_spec.width, a_spec.height, list(a_spec.channelnames), str(a_spec.format)]
        b_layout = [b_spec.width, b_spec.height, list(b_spec.channelnames), str(b_spec.format)]
        if a_layout != expected_layout or b_layout != expected_layout:
            raise RuntimeError(f"Layout mismatch for {name}: {a_layout} {b_layout}")
        numeric = oiio.ImageBufAlgo.compare(a, b, 0.0, 0.0)
        yee_failures = None
        yee_maximum = None
        if is_png:
            yee = oiio.CompareResults()
            oiio.ImageBufAlgo.compare_Yee(
                a, b, yee,
                float(envelope["yeeLuminanceCdM2"]),
                float(envelope["yeeFieldOfViewDegrees"]),
            )
            yee_failures = int(yee.nfail)
            yee_maximum = float(yee.maxerror)
        checks = {
            "maximumAbsoluteError": float(numeric.maxerror) <= float(envelope["maximumAbsoluteErrorAtMost"]),
            "rmsError": float(numeric.rms_error) <= float(envelope["rmsErrorAtMost"]),
            "zeroThresholdFailurePixels": int(numeric.nfail) <= int(envelope["zeroThresholdFailurePixelsAtMost"]),
        }
        if is_png:
            checks["yeeFailurePixels"] = yee_failures <= int(envelope["yeeFailurePixelsAtMost"])
        comparisons.append({
            "frame": frame,
            "name": name,
            "aSha256": sha256_file(a_path),
            "bSha256": sha256_file(b_path),
            "containerExact": sha256_file(a_path) == sha256_file(b_path),
            "decodedPixelExact": float(numeric.maxerror) == 0.0 and int(numeric.nfail) == 0,
            "meanError": float(numeric.meanerror),
            "rmsError": float(numeric.rms_error),
            "maxAbsoluteError": float(numeric.maxerror),
            "failurePixels": int(numeric.nfail),
            "yeeFailurePixels": yee_failures,
            "yeeMaximumError": yee_maximum,
            "envelopeChecks": checks,
            "envelopePass": all(checks.values()),
            "largestDifference": {"x": int(numeric.maxx), "y": int(numeric.maxy), "channel": int(numeric.maxc)},
        })
    report = {
        "documentType": "BFS_B24_HOLDOUT_TOLERANCE_COMPARISON",
        "version": "0.1.0",
        "format": args.format,
        "extension": extension,
        "pixelFormat": pixel_format,
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
        "frozenEnvelope": envelope,
        "selectedFrames": frames,
        "frameCount": len(frames),
        "containerExactFrames": sum(item["containerExact"] for item in comparisons),
        "decodedPixelExactFrames": sum(item["decodedPixelExact"] for item in comparisons),
        "envelopePassFrames": sum(item["envelopePass"] for item in comparisons),
        "maximumAbsoluteError": max(item["maxAbsoluteError"] for item in comparisons),
        "maximumRmsError": max(item["rmsError"] for item in comparisons),
        "maximumFailurePixels": max(item["failurePixels"] for item in comparisons),
        "maximumYeeFailurePixels": max((item["yeeFailurePixels"] or 0) for item in comparisons),
        "frames": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B24_COMPARE_OK {args.format} pass={report['envelopePassFrames']}/{report['frameCount']} exact={report['decodedPixelExactFrames']}/{report['frameCount']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B24_COMPARE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
