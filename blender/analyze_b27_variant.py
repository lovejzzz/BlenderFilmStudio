"""Post-hoc spatial analysis of the two exact B27 frame-38 decoded RGB modes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--alternate", type=Path, required=True)
    parser.add_argument("--b25-a", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> np.ndarray:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot decode {path}: {image.geterror()}")
    spec = image.spec()
    layout = [spec.width, spec.height, list(spec.channelnames), str(spec.format)]
    expected = [960, 540, ["R", "G", "B", "A"], "uint8"]
    if layout != expected:
        raise RuntimeError(f"Layout mismatch for {path}: {layout!r}")
    return image.get_pixels(oiio.UINT8)


def decoded_rgb_sha256(pixels: np.ndarray) -> str:
    return hashlib.sha256(pixels[:, :, :3].tobytes(order="C")).hexdigest()


def write_png(path: Path, pixels: np.ndarray) -> None:
    height, width, channels = pixels.shape
    output = oiio.ImageOutput.create(str(path))
    if output is None:
        raise RuntimeError(f"Cannot create image output for {path}")
    spec = oiio.ImageSpec(width, height, channels, oiio.UINT8)
    spec.channelnames = ["R", "G", "B", "A"][:channels]
    if not output.open(str(path), spec):
        raise RuntimeError(output.geterror())
    if not output.write_image(pixels):
        raise RuntimeError(output.geterror())
    output.close()


def main() -> None:
    args = parse_args()
    reference = load(args.reference)
    alternate = load(args.alternate)
    b25_a = load(args.b25_a)
    delta = alternate.astype(np.int16) - reference.astype(np.int16)
    mask = np.any(delta != 0, axis=2)
    y_values, x_values = np.where(mask)
    if len(x_values) == 0:
        raise RuntimeError("Reference and alternate are decoded-pixel exact; no variant to analyze")
    bounds = {
        "minX": int(x_values.min()), "minY": int(y_values.min()),
        "maxX": int(x_values.max()), "maxY": int(y_values.max()),
    }
    pad = 8
    x0, y0 = max(0, bounds["minX"] - pad), max(0, bounds["minY"] - pad)
    x1, y1 = min(reference.shape[1], bounds["maxX"] + pad + 1), min(reference.shape[0], bounds["maxY"] + pad + 1)
    scale = 16
    args.output_dir.mkdir(parents=True, exist_ok=True)
    crop_reference = np.repeat(np.repeat(reference[y0:y1, x0:x1], scale, axis=0), scale, axis=1)
    crop_alternate = np.repeat(np.repeat(alternate[y0:y1, x0:x1], scale, axis=0), scale, axis=1)
    base = reference[y0:y1, x0:x1, :3]
    gray = np.mean(base, axis=2, keepdims=True).astype(np.uint8)
    mask_crop = mask[y0:y1, x0:x1]
    visualization = np.concatenate([gray, gray, gray, np.full_like(gray, 255)], axis=2)
    visualization[mask_crop] = np.array([255, 30, 24, 255], dtype=np.uint8)
    crop_difference = np.repeat(np.repeat(visualization, scale, axis=0), scale, axis=1)
    outputs = {
        "referenceCrop": args.output_dir / "frame-0038-reference-crop-16x.png",
        "alternateCrop": args.output_dir / "frame-0038-alternate-crop-16x.png",
        "differenceMask": args.output_dir / "frame-0038-difference-mask-16x.png",
    }
    write_png(outputs["referenceCrop"], crop_reference)
    write_png(outputs["alternateCrop"], crop_alternate)
    write_png(outputs["differenceMask"], crop_difference)
    coordinates = []
    for y, x in zip(y_values.tolist(), x_values.tolist(), strict=True):
        coordinates.append({
            "x": x, "y": y,
            "referenceRgba": reference[y, x].tolist(),
            "alternateRgba": alternate[y, x].tolist(),
            "deltaRgba": delta[y, x].tolist(),
        })
    report = {
        "documentType": "BFS_B27_POST_HOC_VARIANT_ANALYSIS",
        "version": "0.1.0",
        "status": "EXPLORATORY_POST_HOC_DOES_NOT_CHANGE_PREREGISTERED_DECISION",
        "reference": {"containerSha256": sha256_file(args.reference), "decodedRgbSha256": decoded_rgb_sha256(reference)},
        "alternate": {"containerSha256": sha256_file(args.alternate), "decodedRgbSha256": decoded_rgb_sha256(alternate)},
        "b25A": {"containerSha256": sha256_file(args.b25_a), "decodedRgbSha256": decoded_rgb_sha256(b25_a)},
        "alternateDecodedPixelsEqualB25A": bool(np.array_equal(alternate, b25_a)),
        "changedPixels": int(np.count_nonzero(mask)),
        "changedChannels": [int(np.count_nonzero(delta[:, :, channel])) for channel in range(4)],
        "boundingBoxInclusive": bounds,
        "crop": {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0, "nearestNeighborScale": scale},
        "coordinates": coordinates,
        "outputs": {key: str(path) for key, path in outputs.items()},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B27_VARIANT_OK pixels={report['changedPixels']} bbox={bounds} equals_b25_a={report['alternateDecodedPixelsEqualB25A']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B27_VARIANT_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
