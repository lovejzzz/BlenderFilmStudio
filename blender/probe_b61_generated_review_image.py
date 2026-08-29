import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys

import bpy
import numpy
import OpenImageIO as oiio


EXPECTED_OIIO = "3.1.13.1"
EXPECTED_NUMPY = "2.3.4"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def normalize(value):
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def canonical(value):
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot(scene):
    settings = scene.render.image_settings
    return {
        "scene": scene.name,
        "engine": scene.render.engine,
        "fileFormat": settings.file_format,
        "colorDepth": settings.color_depth,
        "exrCodec": settings.exr_codec,
        "display": scene.display_settings.display_device,
        "view": scene.view_settings.view_transform,
        "look": scene.view_settings.look,
        "exposure": scene.view_settings.exposure,
        "gamma": scene.view_settings.gamma,
    }


def decode_combined(path):
    if oiio.VERSION_STRING != EXPECTED_OIIO or numpy.__version__ != EXPECTED_NUMPY:
        raise RuntimeError("Bundled OpenImageIO/NumPy version mismatch")
    image_input = oiio.ImageInput.open(str(path))
    if image_input is None:
        raise RuntimeError("OpenImageIO open failed")
    try:
        candidates = []
        subimage = 0
        while image_input.seek_subimage(subimage, 0):
            spec = image_input.spec()
            names = list(spec.channelnames)
            positions = {name: index for index, name in enumerate(names)}
            for name in names:
                if not name.endswith(".R"):
                    continue
                prefix = name[:-2]
                wanted = [f"{prefix}.{channel}" for channel in "RGBA"]
                if prefix.split(".")[-1] == "Combined" and all(channel in positions for channel in wanted):
                    candidates.append((subimage, spec.width, spec.height, spec.nchannels, prefix, wanted, [positions[channel] for channel in wanted]))
            subimage += 1
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one Combined RGBA quartet, found {len(candidates)}")
        subimage, width, height, channels, prefix, names, indices = candidates[0]
        pixels = image_input.read_image(subimage, 0, 0, channels, oiio.FLOAT)
        array_value = numpy.asarray(pixels)
        if tuple(array_value.shape) != (height, width, channels):
            raise RuntimeError(f"Unexpected decoded shape {array_value.shape}")
        rgba = numpy.ascontiguousarray(array_value[..., indices], dtype=numpy.dtype("<f4"))
        return rgba, {"subimage": subimage, "prefix": prefix, "channelNames": names, "channelIndices": indices}
    finally:
        image_input.close()


def write_hashed(path, body):
    record = {**body, "resultHash": sha256_bytes(canonical(body))}
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def main():
    args = parse_args()
    root = args.repository_root.resolve(strict=True)
    spec_path = args.spec.resolve(strict=True)
    output = args.output.resolve(strict=False)
    spec_path.relative_to(root)
    output.parent.relative_to(root)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    exr = (root / spec["failedRun"]["retainedExr"]["uri"]).resolve(strict=True)
    if sha256_file(exr) != spec["failedRun"]["retainedExr"]["containerSha256"]:
        raise RuntimeError("D5 retained EXR mismatch")

    production = bpy.context.scene
    before = snapshot(production)
    rgba, decoder = decode_combined(exr)
    decoded_hash = sha256_bytes(rgba.tobytes(order="C"))
    if decoded_hash != spec["failedRun"]["retainedExr"]["decodedCombinedSha256"]:
        raise RuntimeError("D5 decoded projection mismatch")

    review = bpy.data.scenes.new("BFS_D5_REVIEW_SCENE")
    image = bpy.data.images.new("BFS_D5_COMBINED", width=rgba.shape[1], height=rgba.shape[0], alpha=True, float_buffer=True)
    png_path = output.parent / "generated-review-1080p.png"
    try:
        review.display_settings.display_device = production.display_settings.display_device
        review.view_settings.view_transform = production.view_settings.view_transform
        review.view_settings.look = production.view_settings.look
        review.view_settings.exposure = production.view_settings.exposure
        review.view_settings.gamma = production.view_settings.gamma
        review.render.image_settings.file_format = "PNG"
        review.render.image_settings.color_mode = "RGBA"
        review.render.image_settings.color_depth = "8"
        image.colorspace_settings.name = "ACEScg"
        blender_rows = numpy.ascontiguousarray(numpy.flipud(rgba), dtype=numpy.float32)
        image.pixels.foreach_set(blender_rows.reshape(-1))
        image.update()
        generated_has_data = bool(image.has_data) and list(image.size) == [1920, 1080] and len(image.pixels) == 8294400
        image.save_render(filepath=str(png_path), scene=review)
        data = png_path.read_bytes()
        dimensions = list(struct.unpack(">II", data[16:24])) if len(data) >= 24 else [0, 0]
        valid_png = data[:8] == b"\x89PNG\r\n\x1a\n" and dimensions == [1920, 1080]
        review_settings = snapshot(review)
    finally:
        bpy.data.images.remove(image)
        bpy.data.scenes.remove(review)

    production_unchanged = snapshot(production) == before
    success = generated_has_data and valid_png and production_unchanged
    body = {
        "schemaVersion": "bfs.b61GeneratedReviewImageDiagnosticResult.v0.1",
        "status": "PASS" if success else "FAIL",
        "input": {"uri": exr.relative_to(root).as_posix(), "sha256": sha256_file(exr), "decodedCombinedSha256": decoded_hash},
        "decoder": {**decoder, "module": "OpenImageIO", "version": oiio.VERSION_STRING, "numpyVersion": numpy.__version__},
        "generatedImage": {"width": 1920, "height": 1080, "floatCount": int(rgba.size), "hasData": generated_has_data, "sourceColorSpace": "ACEScg", "rowOrderConversion": "OIIO_Y0_TOP_TO_BLENDER_PIXEL0_BOTTOM"},
        "reviewScene": review_settings,
        "png": {"uri": png_path.relative_to(root).as_posix(), "bytes": png_path.stat().st_size, "sha256": sha256_file(png_path), "validHeader": valid_png, "dimensions": dimensions},
        "productionBefore": before,
        "productionSettingsUnchanged": production_unchanged,
        "operations": {"blenderProcesses": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
        "verdict": "OIIO_RGBA_TO_GENERATED_FLOAT_IMAGE_TO_ISOLATED_PNG_SUPPORTED" if success else None,
    }
    result = write_hashed(output, body)
    if result["status"] != "PASS":
        raise RuntimeError("D5 success criteria failed")
    print(f"BFS_B61_D5 PASS {decoded_hash} {result['resultHash']}")


if __name__ == "__main__":
    main()
