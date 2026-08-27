"""Render one bounded B45 Cycles pixel canary from an already compiled BFS .blend."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import time
from pathlib import Path

import bpy
import PyOpenColorIO as ocio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--shot-id", required=True)
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--plan-hash", required=True)
    parser.add_argument("--scene-hash", required=True)
    parser.add_argument("--structure-hash", required=True)
    parser.add_argument("--ocio-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_dimensions(path: Path):
    with path.open("rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    milestone_path = output_dir / "milestones.jsonl"
    sequence = 0

    def milestone(name: str, details=None) -> None:
        nonlocal sequence
        sequence += 1
        record = {
            "shotId": args.shot_id,
            "sequence": sequence,
            "name": name,
            "monotonicNs": time.monotonic_ns(),
            "processId": os.getpid(),
            "details": details or {},
        }
        with milestone_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    started = time.perf_counter()
    milestone("PROCESS_STARTED")
    source_path = Path(bpy.data.filepath).resolve()
    source_sha256 = sha256_file(source_path)
    if source_sha256 != args.source_sha256:
        raise RuntimeError(f"source blend SHA mismatch: {source_sha256}")
    if tuple(bpy.app.version[:3]) != (5, 2, 0):
        raise RuntimeError(f"Blender 5.2.0 required, received {bpy.app.version_string}")

    scene = bpy.context.scene
    bindings = {
        "planHash": scene.get("bfs_plan_hash"),
        "sceneSpecHash": scene.get("bfs_scene_spec_hash"),
        "structureHash": scene.get("bfs_structure_hash"),
        "ocioConfigSha256": scene.get("bfs_ocio_sha256"),
    }
    expected_bindings = {
        "planHash": args.plan_hash,
        "sceneSpecHash": args.scene_hash,
        "structureHash": args.structure_hash,
        "ocioConfigSha256": args.ocio_sha256,
    }
    if bindings != expected_bindings:
        raise RuntimeError(f"compiled scene binding mismatch: {bindings}")
    bindings["shotSeed"] = int(scene["bfs_shot_seed"])
    if args.frame < scene.frame_start or args.frame > scene.frame_end:
        raise RuntimeError(f"frame {args.frame} outside {scene.frame_start}-{scene.frame_end}")
    config = ocio.GetCurrentConfig()
    if config.getName() != scene.get("bfs_ocio_config"):
        raise RuntimeError(f"OCIO config mismatch: {config.getName()}")
    milestone("SOURCE_VERIFIED", {"sourceSha256": source_sha256, **bindings})

    original_settings = {
        "engine": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
        "samples": scene.cycles.samples,
        "device": scene.cycles.device,
        "threadsMode": scene.render.threads_mode,
        "threads": scene.render.threads,
        "frameRange": [scene.frame_start, scene.frame_end],
        "viewTransform": scene.view_settings.view_transform,
        "look": scene.view_settings.look,
        "displayDevice": scene.display_settings.display_device,
    }
    scene.frame_set(args.frame)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.cycles.seed = bindings["shotSeed"]
    scene.cycles.use_animated_seed = False
    if hasattr(scene.cycles, "use_denoising"):
        scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 128
    scene.render.resolution_y = 72
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    for name in (
        "use_stamp_date", "use_stamp_time", "use_stamp_render_time", "use_stamp_memory",
        "use_stamp_hostname", "use_stamp_filename", "use_stamp_frame", "use_stamp_scene",
        "use_stamp_camera", "use_stamp_lens", "use_stamp_marker", "use_stamp_note",
    ):
        if hasattr(scene.render, name):
            setattr(scene.render, name, False)

    applied_settings = {
        "engine": scene.render.engine,
        "device": scene.cycles.device,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
        "samples": scene.cycles.samples,
        "seed": scene.cycles.seed,
        "animatedSeed": scene.cycles.use_animated_seed,
        "denoising": scene.cycles.use_denoising if hasattr(scene.cycles, "use_denoising") else None,
        "threadsMode": scene.render.threads_mode,
        "threads": scene.render.threads,
        "filmTransparent": scene.render.film_transparent,
        "compositing": scene.render.use_compositing,
        "sequencer": scene.render.use_sequencer,
    }
    milestone("SCENE_CONFIGURED", applied_settings)
    milestone("RENDER_STARTED")
    render_result = bpy.ops.render.render(write_still=False)
    if "FINISHED" not in render_result:
        raise RuntimeError(f"render failed: {sorted(render_result)}")

    image = bpy.data.images.get("Render Result")
    if image is None:
        raise RuntimeError("Render Result is absent")
    exr_path = output_dir / "frame.exr"
    png_path = output_dir / "frame.png"
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"
    image.save_render(str(exr_path), scene=scene)
    exr_save_settings = {
        "mediaType": scene.render.image_settings.media_type,
        "fileFormat": scene.render.image_settings.file_format,
        "colorMode": scene.render.image_settings.color_mode,
        "colorDepth": scene.render.image_settings.color_depth,
        "codec": scene.render.image_settings.exr_codec,
    }
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    image.save_render(str(png_path), scene=scene)
    png_save_settings = {
        "mediaType": scene.render.image_settings.media_type,
        "fileFormat": scene.render.image_settings.file_format,
        "colorMode": scene.render.image_settings.color_mode,
        "colorDepth": scene.render.image_settings.color_depth,
    }
    dimensions = png_dimensions(png_path)
    if dimensions != (128, 72) or not exr_path.exists():
        raise RuntimeError(f"output validation failed: PNG {dimensions}, EXR {exr_path.exists()}")
    artifacts = {
        "exr": {"uri": "frame.exr", "bytes": exr_path.stat().st_size, "sha256": sha256_file(exr_path)},
        "png": {"uri": "frame.png", "bytes": png_path.stat().st_size, "sha256": sha256_file(png_path), "dimensions": list(dimensions)},
    }
    milestone("RENDER_COMPLETED", artifacts)

    report = {
        "schemaVersion": "bfs.workerPixelCanaryReport.v0.1",
        "shotId": args.shot_id,
        "frame": args.frame,
        "source": {"uri": str(source_path), "sha256": source_sha256, "bytes": source_path.stat().st_size},
        "bindings": bindings,
        "blender": {
            "version": bpy.app.version_string,
            "versionTuple": list(bpy.app.version),
            "buildHash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
            "buildPlatform": bpy.app.build_platform.decode() if isinstance(bpy.app.build_platform, bytes) else str(bpy.app.build_platform),
        },
        "ocio": {"name": config.getName(), "sha256": scene.get("bfs_ocio_sha256"), "declaredEncoding": scene.get("bfs_declared_encoding")},
        "originalSettings": original_settings,
        "appliedSettings": applied_settings,
        "saveSettings": {"exr": exr_save_settings, "png": png_save_settings},
        "renderOperatorCalls": 1,
        "savesFromSameRenderResult": 2,
        "artifacts": artifacts,
        "elapsedSeconds": round(time.perf_counter() - started, 6),
        "passed": True,
    }
    report_path = output_dir / "render.report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    milestone("REPORT_WRITTEN", {"passed": True, "reportSha256": sha256_file(report_path)})
    print(f"BFS_B45_RENDER_OK {args.shot_id} frame={args.frame} exr={artifacts['exr']['sha256']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B45_RENDER_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
