"""Compare two B22 RGBA32 EXR replicate directories with an exact float gate."""

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
    config = parse_args()
    frames = [int(value) for value in config.frames.split(",")]
    comparisons = []
    expected_layout = [960, 540, ["R", "G", "B", "A"], "float"]
    for frame in frames:
        name = f"frame-{frame:04d}.exr"
        a_path = config.a_dir / name
        b_path = config.b_dir / name
        a = oiio.ImageBuf(str(a_path))
        b = oiio.ImageBuf(str(b_path))
        if not a.initialized or not b.initialized:
            raise RuntimeError(f"Cannot decode {name}")
        a_spec, b_spec = a.spec(), b.spec()
        a_layout = [a_spec.width, a_spec.height, list(a_spec.channelnames), str(a_spec.format)]
        b_layout = [b_spec.width, b_spec.height, list(b_spec.channelnames), str(b_spec.format)]
        if a_layout != expected_layout or b_layout != expected_layout:
            raise RuntimeError(f"Layout mismatch for {name}: {a_layout} {b_layout}")
        result = oiio.ImageBufAlgo.compare(a, b, 0.0, 0.0)
        a_sha = sha256_file(a_path)
        b_sha = sha256_file(b_path)
        comparisons.append({
            "frame": frame,
            "name": name,
            "aSha256": a_sha,
            "bSha256": b_sha,
            "containerExact": a_sha == b_sha,
            "decodedPixelExact": float(result.maxerror) == 0.0 and int(result.nfail) == 0,
            "meanError": float(result.meanerror),
            "rmsError": float(result.rms_error),
            "maxAbsoluteError": float(result.maxerror),
            "failurePixels": int(result.nfail),
            "largestDifference": {"x": int(result.maxx), "y": int(result.maxy), "channel": int(result.maxc)},
        })
    report = {
        "documentType": "BFS_B22_EXR_COMPARISON",
        "version": "0.1.0",
        "extension": ".exr",
        "pixelFormat": "float",
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
        "selectedFrames": frames,
        "frameCount": len(frames),
        "containerExactFrames": sum(item["containerExact"] for item in comparisons),
        "decodedPixelExactFrames": sum(item["decodedPixelExact"] for item in comparisons),
        "maximumAbsoluteError": max(item["maxAbsoluteError"] for item in comparisons),
        "totalFailurePixels": sum(item["failurePixels"] for item in comparisons),
        "frames": comparisons,
    }
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"BFS_B22_COMPARE_OK exact={report['decodedPixelExactFrames']}/"
        f"{report['frameCount']} max={report['maximumAbsoluteError']}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B22_COMPARE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
