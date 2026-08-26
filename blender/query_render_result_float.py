"""Exploratory B21 input probe for Blender's in-memory Render Result buffer."""

from __future__ import annotations

import argparse
import array
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exr-output", type=Path, required=True)
    parser.add_argument("--frame", type=int, default=110)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    scene.frame_set(args.frame)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.use_motion_blur = False
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str(args.output.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.exr_output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    result = bpy.ops.render.render(write_still=False)
    if "FINISHED" not in result:
        raise RuntimeError(f"Probe render failed: {sorted(result)}")

    image = bpy.data.images.get("Render Result")
    if image is None:
        raise RuntimeError("Render Result image was not created")
    pixel_count = len(image.pixels)
    pixels = array.array("f", [0.0]) * pixel_count
    image.pixels.foreach_get(pixels)
    if sys.byteorder != "little":
        pixels.byteswap()
    values = list(pixels)
    finite_values = [value for value in values if math.isfinite(value)]
    image.save_render(str(args.output.resolve()), scene=scene)
    if not args.output.exists():
        raise RuntimeError("Render Result save_render did not create the PNG")
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"
    image.save_render(str(args.exr_output.resolve()), scene=scene)
    if not args.exr_output.exists():
        raise RuntimeError("Render Result save_render did not create the OpenEXR")
    exr = oiio.ImageBuf(str(args.exr_output.resolve()))
    if not exr.initialized:
        raise RuntimeError(f"OpenImageIO could not decode probe EXR: {exr.geterror()}")
    exr_spec = exr.spec()
    report = {
        "documentType": "BFS_RENDER_RESULT_FLOAT_INVENTORY",
        "version": "0.1.0",
        "classification": "EXPLORATORY_NOT_CAUSAL",
        "frame": args.frame,
        "renderResult": {
            "name": image.name,
            "type": image.type,
            "source": image.source,
            "size": list(image.size),
            "channels": image.channels,
            "depth": image.depth,
            "isFloat": image.is_float,
            "hasData": image.has_data,
            "alphaMode": image.alpha_mode,
            "useViewAsRender": image.use_view_as_render,
            "colorspaceSettingsName": image.colorspace_settings.name,
            "pixelElementCount": pixel_count,
            "directPixelsAccessible": pixel_count > 0,
            "float32LittleEndianSha256": hashlib.sha256(pixels.tobytes()).hexdigest(),
            "finiteElementCount": len(finite_values),
            "nonFiniteElementCount": len(values) - len(finite_values),
            "minimum": min(finite_values) if finite_values else None,
            "maximum": max(finite_values) if finite_values else None,
            "first16": values[:16],
        },
        "png": { "uri": str(args.output), "sha256": sha256_file(args.output), "bytes": args.output.stat().st_size },
        "openExr": {
            "uri": str(args.exr_output),
            "sha256": sha256_file(args.exr_output),
            "bytes": args.exr_output.stat().st_size,
            "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
            "width": exr_spec.width,
            "height": exr_spec.height,
            "channels": list(exr_spec.channelnames),
            "pixelFormat": str(exr_spec.format),
        },
        "observedControls": {
            "renderSamples": scene.eevee.taa_render_samples,
            "ditherIntensity": scene.render.dither_intensity,
            "useFastGi": scene.eevee.use_fast_gi,
            "useTaaReprojection": scene.eevee.use_taa_reprojection,
        },
        "nonClaims": [
            "The Blender API reports the Render Result as a float buffer, but this one probe does not prove exact reproducibility.",
            "The Image.pixels access path and byte serialization must be frozen and attacked before causal use.",
            "Render Result metadata alone does not prove which working-space primaries the numeric values use.",
        ],
    }
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_RENDER_RESULT_FLOAT_INVENTORY_OK elements={pixel_count} sha={report['renderResult']['float32LittleEndianSha256']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_RENDER_RESULT_FLOAT_INVENTORY_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
