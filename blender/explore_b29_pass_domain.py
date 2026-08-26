"""Exploratory B29 pilot: save Combined, Depth, Normal and Position per render."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy
import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def subimages(path: Path) -> list[dict]:
    source = oiio.ImageInput.open(str(path))
    if source is None:
        raise RuntimeError(f"Cannot open {path}: {oiio.geterror()}")
    result = []
    index = 0
    try:
        while True:
            spec = source.spec()
            pixels = source.read_image(oiio.FLOAT)
            if pixels is None:
                raise RuntimeError(f"Cannot read subimage {index}: {source.geterror()}")
            result.append({
                "subimage": index,
                "name": spec.get_string_attribute("name", ""),
                "width": spec.width,
                "height": spec.height,
                "channels": list(spec.channelnames),
                "pixelFormat": str(spec.format),
                "decodedFloatSha256": hashlib.sha256(pixels.tobytes(order="C")).hexdigest(),
            })
            index += 1
            if not source.seek_subimage(index, 0):
                break
    finally:
        source.close()
    return result


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("Pilot output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    layer = scene.view_layers[0]
    scene.frame_set(38)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.use_motion_blur = False
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.use_stamp = False
    layer.use_pass_z = True
    layer.use_pass_normal = True
    layer.use_pass_position = True
    enabled = {"Combined": layer.use_pass_combined, "Depth": layer.use_pass_z, "Normal": layer.use_pass_normal, "Position": layer.use_pass_position}
    outputs = []
    for ordinal in range(1, 13):
        started = time.perf_counter()
        scene.render.image_settings.media_type = "IMAGE"
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.image_settings.color_depth = "8"
        if "FINISHED" not in bpy.ops.render.render(write_still=False):
            raise RuntimeError(f"Render {ordinal} failed")
        render_result = bpy.data.images.get("Render Result")
        if render_result is None:
            raise RuntimeError("Render Result missing")
        png = args.output_dir / f"render-{ordinal:02d}.png"
        render_result.save_render(str(png.resolve()), scene=scene)
        scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
        scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.image_settings.color_depth = "32"
        scene.render.image_settings.exr_codec = "ZIP"
        exr = args.output_dir / f"render-{ordinal:02d}.exr"
        render_result.save_render(str(exr.resolve()), scene=scene)
        outputs.append({
            "callOrdinal": ordinal,
            "png": {"name": png.name, "sha256": sha256_file(png), "bytes": png.stat().st_size},
            "exr": {"name": exr.name, "sha256": sha256_file(exr), "bytes": exr.stat().st_size, "subimages": subimages(exr)},
            "seconds": round(time.perf_counter() - started, 6),
        })
        print(f"BFS_B29_PILOT_CALL_OK {ordinal:02d} {outputs[-1]['png']['sha256']}")
    report = {
        "documentType": "BFS_B29_PASS_DOMAIN_EXPLORATORY_PILOT",
        "version": "0.1.0",
        "status": "EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION",
        "processId": os.getpid(),
        "frame": 38,
        "renderCalls": 12,
        "sameRenderResultForPngAndMultilayerExr": True,
        "enabledPasses": enabled,
        "controls": {"threadsMode": scene.render.threads_mode, "threads": scene.render.threads, "samples": scene.eevee.taa_render_samples, "dither": scene.render.dither_intensity, "fastGi": scene.eevee.use_fast_gi, "taaReprojection": scene.eevee.use_taa_reprojection},
        "outputs": outputs,
        "savedSourceBlend": False,
    }
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B29_PASS_DOMAIN_PILOT_OK pid={os.getpid()} calls={len(outputs)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B29_PASS_DOMAIN_PILOT_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
