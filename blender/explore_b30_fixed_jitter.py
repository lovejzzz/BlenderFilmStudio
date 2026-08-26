"""Exploratory B30 derivation for Eevee override_pixel_jitter_sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import bpy
import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell", required=True)
    parser.add_argument("--jitter", nargs=2, type=float)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decoded_rgb(path: Path) -> tuple[str, dict]:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot decode {path}: {image.geterror()}")
    spec = image.spec()
    pixels = image.get_pixels(oiio.UINT8)[:, :, :3]
    return hashlib.sha256(pixels.tobytes(order="C")).hexdigest(), {"width": spec.width, "height": spec.height, "channels": list(spec.channelnames), "pixelFormat": str(spec.format)}


def main() -> None:
    args = parse_args()
    if args.cell == "NATURAL" and args.jitter is not None:
        raise RuntimeError("NATURAL must omit jitter")
    if args.cell != "NATURAL" and args.jitter is None:
        raise RuntimeError("Fixed cell requires two jitter values")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("Output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.frame_set(38)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.use_motion_blur = False
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 960, 540, 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.use_stamp = False
    if "override_pixel_jitter_sample" in scene:
        del scene["override_pixel_jitter_sample"]
    if args.jitter is not None:
        scene["override_pixel_jitter_sample"] = [float(args.jitter[0]), float(args.jitter[1])]
    observed_property = list(scene["override_pixel_jitter_sample"]) if "override_pixel_jitter_sample" in scene else None
    outputs = []
    for ordinal in range(1, 13):
        started = time.perf_counter()
        path = args.output_dir / f"render-{ordinal:02d}.png"
        scene.render.filepath = str(path.resolve())
        if "FINISHED" not in bpy.ops.render.render(write_still=True):
            raise RuntimeError(f"Render {ordinal} failed")
        digest, layout = decoded_rgb(path)
        outputs.append({"callOrdinal": ordinal, "containerSha256": sha256_file(path), "decodedRgbSha256": digest, "bytes": path.stat().st_size, "layout": layout, "seconds": round(time.perf_counter() - started, 6)})
        print(f"BFS_B30_DERIVATION_CALL_OK {args.cell} {ordinal:02d} {digest}")
    counts = Counter(item["decodedRgbSha256"] for item in outputs)
    report = {"documentType": "BFS_B30_FIXED_JITTER_DERIVATION_CELL", "version": "0.1.0", "status": "EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION", "cell": args.cell, "requestedJitter": args.jitter, "observedSceneProperty": observed_property, "processId": os.getpid(), "runtime": {"blenderVersion": bpy.app.version_string, "blenderBuildHash": bpy.app.build_hash.decode("utf-8")}, "source": {"sceneBlendSha256": sha256_file(Path(bpy.data.filepath)), "planHash": scene.get("bfs_plan_hash"), "structureHash": scene.get("bfs_structure_hash")}, "controls": {"threadsMode": scene.render.threads_mode, "threads": scene.render.threads, "samples": scene.eevee.taa_render_samples, "dither": scene.render.dither_intensity, "fastGi": scene.eevee.use_fast_gi, "taaReprojection": scene.eevee.use_taa_reprojection}, "renderCalls": 12, "uniqueDecodedRgbHashes": len(counts), "frequencies": [{"decodedRgbSha256": digest, "count": count} for digest, count in sorted(counts.items())], "outputs": outputs, "savedSourceBlend": False}
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B30_DERIVATION_CELL_OK {args.cell} pid={os.getpid()} variants={len(counts)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B30_DERIVATION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
