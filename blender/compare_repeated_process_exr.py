"""Compare an explicit B23 pair list with OIIO's zero-tolerance float gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=Path, required=True)
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
    pair_spec = json.loads(args.pairs.read_text(encoding="utf-8"))
    comparisons = []
    expected_layout = [960, 540, ["R", "G", "B", "A"], "float"]
    for pair in pair_spec["pairs"]:
        a_path, b_path = Path(pair["aPath"]), Path(pair["bPath"])
        a, b = oiio.ImageBuf(str(a_path)), oiio.ImageBuf(str(b_path))
        if not a.initialized or not b.initialized:
            raise RuntimeError(f"Cannot decode pair {pair['id']}")
        a_spec, b_spec = a.spec(), b.spec()
        a_layout = [a_spec.width, a_spec.height, list(a_spec.channelnames), str(a_spec.format)]
        b_layout = [b_spec.width, b_spec.height, list(b_spec.channelnames), str(b_spec.format)]
        if a_layout != expected_layout or b_layout != expected_layout:
            raise RuntimeError(f"Layout mismatch for {pair['id']}: {a_layout} {b_layout}")
        result = oiio.ImageBufAlgo.compare(a, b, 0.0, 0.0)
        comparisons.append({
            "id": pair["id"],
            "metadata": pair["metadata"],
            "aSha256": sha256_file(a_path),
            "bSha256": sha256_file(b_path),
            "containerExact": sha256_file(a_path) == sha256_file(b_path),
            "decodedPixelExact": float(result.maxerror) == 0.0 and int(result.nfail) == 0,
            "meanError": float(result.meanerror),
            "rmsError": float(result.rms_error),
            "maxAbsoluteError": float(result.maxerror),
            "failurePixels": int(result.nfail),
            "largestDifference": {"x": int(result.maxx), "y": int(result.maxy), "channel": int(result.maxc)},
        })
    report = {
        "documentType": "BFS_B23_EXR_PAIR_COMPARISON",
        "version": "0.1.0",
        "gate": pair_spec["gate"],
        "pairSpecId": pair_spec["id"],
        "pairSpecHash": pair_spec["pairSpecHash"],
        "pixelFormat": "float",
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
        "pairCount": len(comparisons),
        "containerExactPairs": sum(item["containerExact"] for item in comparisons),
        "decodedPixelExactPairs": sum(item["decodedPixelExact"] for item in comparisons),
        "maximumAbsoluteError": max(item["maxAbsoluteError"] for item in comparisons),
        "totalFailurePixels": sum(item["failurePixels"] for item in comparisons),
        "pairs": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B23_COMPARE_OK gate={report['gate']} exact={report['decodedPixelExactPairs']}/{report['pairCount']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B23_COMPARE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
