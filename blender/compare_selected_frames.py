"""Decode and exactly compare a pre-registered set of PNG frames with Blender OIIO."""

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
    if not frames or len(frames) != len(set(frames)):
        raise RuntimeError("--frames must be a non-empty unique integer list")
    comparisons = []
    for frame in frames:
        name = f"frame-{frame:04d}.png"
        a_path, b_path = args.a_dir / name, args.b_dir / name
        a, b = oiio.ImageBuf(str(a_path)), oiio.ImageBuf(str(b_path))
        if not a.initialized or not b.initialized:
            raise RuntimeError(f"Cannot decode frame {frame}: {a.geterror()} {b.geterror()}")
        a_spec, b_spec = a.spec(), b.spec()
        layout_a = [a_spec.width, a_spec.height, list(a_spec.channelnames)]
        layout_b = [b_spec.width, b_spec.height, list(b_spec.channelnames)]
        if layout_a != layout_b:
            raise RuntimeError(f"Frame {frame} layout mismatch: {layout_a} != {layout_b}")
        result = oiio.ImageBufAlgo.compare(a, b, 0.0, 0.0)
        a_sha, b_sha = sha256_file(a_path), sha256_file(b_path)
        comparisons.append({
            "frame": frame,
            "name": name,
            "layout": {"width": a_spec.width, "height": a_spec.height, "channels": list(a_spec.channelnames)},
            "aSha256": a_sha,
            "bSha256": b_sha,
            "containerExact": a_sha == b_sha,
            "decodedPixelExact": float(result.maxerror) == 0.0 and int(result.nfail) == 0,
            "meanError": float(result.meanerror),
            "rmsError": float(result.rms_error),
            "maxAbsoluteError": float(result.maxerror),
            "warningPixels": int(result.nwarn),
            "failurePixels": int(result.nfail),
            "largestDifference": {"x": int(result.maxx), "y": int(result.maxy), "z": int(result.maxz), "channel": int(result.maxc)},
        })
        print(f"BFS_B20_COMPARE {frame:04d} bytes={comparisons[-1]['containerExact']} pixels={comparisons[-1]['decodedPixelExact']} max={comparisons[-1]['maxAbsoluteError']}")

    worst = max(comparisons, key=lambda item: item["maxAbsoluteError"])
    report = {
        "documentType": "BFS_B20_SELECTED_FRAME_COMPARISON",
        "version": "0.1.0",
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
        "selectedFrames": frames,
        "frameCount": len(comparisons),
        "containerExactFrames": sum(item["containerExact"] for item in comparisons),
        "decodedPixelExactFrames": sum(item["decodedPixelExact"] for item in comparisons),
        "worstFrame": worst,
        "maximumAbsoluteError": max(item["maxAbsoluteError"] for item in comparisons),
        "totalFailurePixels": sum(item["failurePixels"] for item in comparisons),
        "frames": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B20_SELECTED_COMPARISON_OK pixels={report['decodedPixelExactFrames']}/{report['frameCount']} max={report['maximumAbsoluteError']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B20_SELECTED_COMPARISON_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
