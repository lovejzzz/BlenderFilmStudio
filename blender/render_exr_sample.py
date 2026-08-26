"""Render one controlled 4K multi-layer EXR sample from a compiled BFS scene."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy
import PyOpenColorIO as ocio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pixel-spec", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    started = time.perf_counter()
    args = parse_args()
    spec = json.loads(args.pixel_spec.read_text(encoding="utf-8"))
    scene = bpy.context.scene
    environment = spec["environment"]
    image = spec["image"]
    color = spec["color"]

    if tuple(bpy.app.version[:3]) != (5, 2, 0):
        raise RuntimeError(f"Blender 5.2.0 required, received {bpy.app.version_string}")
    config = ocio.GetCurrentConfig()
    if config.getName() != color["ocioConfigName"]:
        raise RuntimeError(f"OCIO config mismatch: {config.getName()}")
    if scene.get("bfs_ocio_sha256") != color["ocioConfigSha256"]:
        raise RuntimeError("Compiled scene OCIO hash marker does not match PixelSpec")
    if not scene.get("bfs_plan_hash") or not scene.get("bfs_scene_spec_hash"):
        raise RuntimeError("Compiled BFS scene markers are missing")
    if args.frame < scene.frame_start or args.frame > scene.frame_end:
        raise RuntimeError(f"Frame {args.frame} is outside {scene.frame_start}-{scene.frame_end}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene.frame_set(args.frame)
    scene.render.engine = environment["renderEngine"]
    scene.cycles.device = environment["device"]
    scene.cycles.samples = environment["samples"]
    scene.cycles.seed = int(scene["bfs_shot_seed"])
    scene.cycles.use_animated_seed = environment["animatedSeed"]
    scene.render.threads_mode = environment["threadsMode"]
    scene.render.threads = environment["threads"]
    scene.render.resolution_x = image["width"]
    scene.render.resolution_y = image["height"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.render.image_settings.exr_codec = "ZIP"
    scene.render.filepath = str(args.output)
    scene.render.use_file_extension = True

    # Exclude volatile stamp fields. The render manifest carries controlled provenance.
    scene.render.use_stamp = False
    for name in (
        "use_stamp_date", "use_stamp_time", "use_stamp_render_time", "use_stamp_memory",
        "use_stamp_hostname", "use_stamp_filename", "use_stamp_frame", "use_stamp_scene",
        "use_stamp_camera", "use_stamp_lens", "use_stamp_marker", "use_stamp_note",
    ):
        if hasattr(scene.render, name):
            setattr(scene.render, name, False)

    render_result = bpy.ops.render.render(write_still=True)
    if "FINISHED" not in render_result:
        raise RuntimeError(f"Render failed: {sorted(render_result)}")
    if not args.output.exists():
        suffixed = args.output.with_suffix(args.output.suffix + ".exr")
        if suffixed.exists():
            suffixed.replace(args.output)
        else:
            raise RuntimeError(f"Renderer did not create {args.output}")

    report = {
        "documentType": "BFS_RENDER_SAMPLE",
        "benchmarkShot": scene.name,
        "frame": args.frame,
        "planHash": scene["bfs_plan_hash"],
        "sceneSpecHash": scene["bfs_scene_spec_hash"],
        "ocioConfig": config.getName(),
        "ocioConfigSha256": scene["bfs_ocio_sha256"],
        "blender": bpy.app.version_string,
        "engine": scene.render.engine,
        "device": scene.cycles.device,
        "samples": scene.cycles.samples,
        "seed": scene.cycles.seed,
        "animatedSeed": scene.cycles.use_animated_seed,
        "threadsMode": scene.render.threads_mode,
        "threads": scene.render.threads,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "sha256": sha256_file(args.output),
        "bytes": args.output.stat().st_size,
        "renderSeconds": round(time.perf_counter() - started, 6),
    }
    args.output.with_suffix(".render.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"BFS_RENDER_OK {scene.name} {args.frame} {report['sha256']} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_RENDER_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
