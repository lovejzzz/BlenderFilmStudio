"""Verify a decoded B26 playback carrier against its source PNG manifest."""

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
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--decoded-dir", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
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
    manifest = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    if manifest.get("frameCount") != 144 or len(manifest.get("frames", [])) != 144:
        raise RuntimeError("Source manifest does not bind 144 frames")

    observations = []
    all_alpha_opaque = True
    for expected in manifest["frames"]:
        frame = int(expected["frame"])
        name = f"frame-{frame:04d}.png"
        source_path, decoded_path = args.source_dir / name, args.decoded_dir / name
        if sha256_file(source_path) != expected["sha256"]:
            raise RuntimeError(f"Source frame {frame} SHA does not match manifest")
        source, decoded = oiio.ImageBuf(str(source_path)), oiio.ImageBuf(str(decoded_path))
        if not source.initialized or not decoded.initialized:
            raise RuntimeError(f"Cannot decode roundtrip frame {frame}")
        source_spec, decoded_spec = source.spec(), decoded.spec()
        source_layout = [source_spec.width, source_spec.height, list(source_spec.channelnames), str(source_spec.format)]
        decoded_layout = [decoded_spec.width, decoded_spec.height, list(decoded_spec.channelnames), str(decoded_spec.format)]
        if source_layout != [960, 540, ["R", "G", "B", "A"], "uint8"]:
            raise RuntimeError(f"Unexpected source layout at frame {frame}: {source_layout}")
        if decoded_layout != [960, 540, ["R", "G", "B"], "uint8"]:
            raise RuntimeError(f"Unexpected decoded layout at frame {frame}: {decoded_layout}")
        source_pixels = source.get_pixels(oiio.FLOAT)
        decoded_pixels = decoded.get_pixels(oiio.FLOAT)
        alpha_opaque = bool(np.all(source_pixels[:, :, 3] == 1.0))
        all_alpha_opaque = all_alpha_opaque and alpha_opaque
        delta = source_pixels[:, :, :3] - decoded_pixels[:, :, :3]
        absolute = np.abs(delta)
        maximum = float(absolute.max())
        rms = float(math.sqrt(float(np.mean(np.square(delta, dtype=np.float64)))))
        changed_pixels = int(np.count_nonzero(np.any(absolute > 0.0, axis=2)))
        observations.append({
            "frame": frame,
            "sourceName": name,
            "sourceSha256": expected["sha256"],
            "decodedSha256": sha256_file(decoded_path),
            "sourceAlphaOpaque": alpha_opaque,
            "rgbExact": maximum == 0.0 and changed_pixels == 0,
            "maximumAbsoluteRgbError": maximum,
            "rmsRgbError": rms,
            "changedRgbPixels": changed_pixels,
        })

    report = {
        "documentType": "BFS_B26_LOSSLESS_CARRIER_ROUNDTRIP",
        "version": "0.1.0",
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
        "numpy": np.__version__,
        "sourceManifestSha256": sha256_file(args.source_manifest),
        "frameCount": len(observations),
        "exactRgbFrames": sum(item["rgbExact"] for item in observations),
        "allSourceAlphaOpaque": all_alpha_opaque,
        "maximumAbsoluteRgbError": max(item["maximumAbsoluteRgbError"] for item in observations),
        "maximumRmsRgbError": max(item["rmsRgbError"] for item in observations),
        "totalChangedRgbPixels": sum(item["changedRgbPixels"] for item in observations),
        "frames": observations,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"BFS_B26_CARRIER_ROUNDTRIP exact={report['exactRgbFrames']}/{report['frameCount']} "
        f"max={report['maximumAbsoluteRgbError']} changed={report['totalChangedRgbPixels']} "
        f"alpha={report['allSourceAlphaOpaque']}"
    )
    if report["exactRgbFrames"] != 144 or not all_alpha_opaque or report["totalChangedRgbPixels"] != 0:
        raise RuntimeError("Carrier roundtrip is not exact")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B26_CARRIER_ROUNDTRIP_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
