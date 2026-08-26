"""Render one fixed-offset component of the preregistered B32.1 8-point ensemble."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy
import PyOpenColorIO as ocio


POINTS = {
    "S1": [-0.375, -0.375], "S2": [-0.375, 0.125],
    "S3": [-0.125, -0.125], "S4": [-0.125, 0.375],
    "S5": [0.125, -0.375], "S6": [0.125, 0.125],
    "S7": [0.375, -0.125], "S8": [0.375, 0.375],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--point", choices=tuple(POINTS), required=True)
    parser.add_argument("--replicate", choices=("A", "B"), required=True)
    parser.add_argument("--frames", nargs="+", type=int, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if args.frames != [37, 72, 103]:
        raise RuntimeError("B32.1 derivation frames changed")
    review = json.loads(args.review_spec.read_text(encoding="utf-8"))
    json.loads(args.receipt.read_text(encoding="utf-8"))
    scene = bpy.context.scene
    source, runtime = review["source"], review["runtime"]
    if sha256_file(Path(bpy.data.filepath)) != source["sceneBlendSha256"]:
        raise RuntimeError("B32.1 scene identity mismatch")
    if scene.get("bfs_plan_hash") != source["planHash"] or scene.get("bfs_structure_hash") != source["structureHash"]:
        raise RuntimeError("B32.1 plan/structure mismatch")
    if bpy.app.version_string != runtime["blender"]["version"] or bpy.app.build_hash.decode("utf-8") != runtime["blender"]["buildHash"]:
        raise RuntimeError("B32.1 Blender identity mismatch")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("B32.1 output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    jitter = POINTS[args.point]
    scene["override_pixel_jitter_sample"] = jitter
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.use_motion_blur = False
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 960, 540, 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"
    scene.render.film_transparent = False
    scene.render.use_stamp = False
    observed = {
        "samples": int(scene.eevee.taa_render_samples),
        "jitter": [float(value) for value in scene["override_pixel_jitter_sample"]],
        "threadsMode": scene.render.threads_mode,
        "threads": int(scene.render.threads),
        "dither": float(scene.render.dither_intensity),
        "useFastGi": bool(scene.eevee.use_fast_gi),
        "useTaaReprojection": bool(scene.eevee.use_taa_reprojection),
    }
    expected = {
        "samples": 32, "jitter": jitter, "threadsMode": "FIXED", "threads": 8,
        "dither": 0.0, "useFastGi": True, "useTaaReprojection": True,
    }
    if observed != expected:
        raise RuntimeError(f"B32.1 controls mismatch: {observed!r}")

    outputs = []
    started = time.perf_counter()
    for frame in args.frames:
        scene.frame_set(frame)
        output = args.output_dir / f"frame-{frame:04d}.exr"
        scene.render.filepath = str(output.resolve())
        frame_started = time.perf_counter()
        result = bpy.ops.render.render(write_still=True)
        if "FINISHED" not in result or not output.exists():
            raise RuntimeError(f"B32.1 frame {frame} failed")
        outputs.append({
            "frame": frame, "name": output.name, "sha256": sha256_file(output),
            "bytes": output.stat().st_size,
            "renderSeconds": round(time.perf_counter() - frame_started, 6),
        })
    report = {
        "documentType": "BFS_B32_STRATIFIED8_DERIVATION_RENDER",
        "version": "0.1.0",
        "status": "EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION",
        "point": args.point,
        "replicate": args.replicate,
        "jitter": jitter,
        "processId": os.getpid(),
        "frames": args.frames,
        "observedControls": observed,
        "outputs": outputs,
        "renderCalls": len(outputs),
        "source": {
            "sceneBlendSha256": sha256_file(Path(bpy.data.filepath)),
            "planHash": scene["bfs_plan_hash"],
            "structureHash": scene["bfs_structure_hash"],
        },
        "runtime": {
            "blenderVersion": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode("utf-8"),
            "ocioConfigName": ocio.GetCurrentConfig().getName(),
        },
        "totalRenderSeconds": round(time.perf_counter() - started, 6),
        "savedSourceBlend": False,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B32_STRATIFIED8_RENDER_OK {args.point}_{args.replicate} seconds={report['totalRenderSeconds']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B32_STRATIFIED8_RENDER_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
