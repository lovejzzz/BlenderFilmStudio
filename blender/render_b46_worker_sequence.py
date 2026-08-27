"""Render one bounded B46 frame sequence from an already compiled BFS .blend."""

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
    parser.add_argument("--frames", required=True)
    parser.add_argument("--plan-hash", required=True)
    parser.add_argument("--scene-hash", required=True)
    parser.add_argument("--structure-hash", required=True)
    parser.add_argument("--ocio-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fault-after-frame", type=int)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    args.frame_list = [int(value) for value in args.frames.split(",")]
    return args


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
    if args.frame_list != sorted(set(args.frame_list)) or len(args.frame_list) != 8:
        raise RuntimeError(f"expected eight strictly ascending unique frames: {args.frame_list}")
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
    if any(frame < scene.frame_start or frame > scene.frame_end for frame in args.frame_list):
        raise RuntimeError(f"frames {args.frame_list} outside {scene.frame_start}-{scene.frame_end}")
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
        "fps": scene.render.fps,
        "fpsBase": scene.render.fps_base,
        "viewTransform": scene.view_settings.view_transform,
        "look": scene.view_settings.look,
        "displayDevice": scene.display_settings.display_device,
    }
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.cycles.seed = bindings["shotSeed"]
    scene.cycles.use_animated_seed = False
    if not hasattr(scene.cycles, "use_denoising") or not hasattr(scene.render, "use_motion_blur") or not hasattr(scene.render, "use_persistent_data"):
        raise RuntimeError("required Cycles sequence controls are unavailable")
    scene.cycles.use_denoising = False
    scene.render.use_motion_blur = False
    scene.render.use_persistent_data = False
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
        "denoising": scene.cycles.use_denoising,
        "motionBlur": scene.render.use_motion_blur,
        "persistentData": scene.render.use_persistent_data,
        "threadsMode": scene.render.threads_mode,
        "threads": scene.render.threads,
        "filmTransparent": scene.render.film_transparent,
        "compositing": scene.render.use_compositing,
        "sequencer": scene.render.use_sequencer,
    }
    milestone("SCENE_CONFIGURED", applied_settings)
    frame_reports = []
    for frame in args.frame_list:
        scene.frame_set(frame)
        milestone("FRAME_STARTED", {"frame": frame})
        render_result = bpy.ops.render.render(write_still=False)
        if "FINISHED" not in render_result:
            raise RuntimeError(f"render failed at frame {frame}: {sorted(render_result)}")
        image = bpy.data.images.get("Render Result")
        if image is None:
            raise RuntimeError(f"Render Result is absent at frame {frame}")
        exr_path = output_dir / f"frame-{frame:04d}.exr"
        png_path = output_dir / f"frame-{frame:04d}.png"
        scene.render.image_settings.media_type = "IMAGE"
        scene.render.image_settings.file_format = "OPEN_EXR"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.image_settings.color_depth = "32"
        scene.render.image_settings.exr_codec = "ZIP"
        image.save_render(str(exr_path), scene=scene)
        scene.render.image_settings.media_type = "IMAGE"
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.image_settings.color_depth = "8"
        image.save_render(str(png_path), scene=scene)
        dimensions = png_dimensions(png_path)
        if dimensions != (128, 72) or not exr_path.exists():
            raise RuntimeError(f"frame {frame} output validation failed")
        artifacts = {
            "exr": {"uri": exr_path.name, "bytes": exr_path.stat().st_size, "sha256": sha256_file(exr_path)},
            "png": {"uri": png_path.name, "bytes": png_path.stat().st_size, "sha256": sha256_file(png_path), "dimensions": list(dimensions)},
        }
        frame_reports.append({"frame": frame, "artifacts": artifacts})
        milestone("FRAME_COMPLETED", {"frame": frame, **artifacts})
        if args.fault_after_frame == frame:
            milestone("FAULT_INJECTED", {"frame": frame, "exitCode": 86})
            os._exit(86)

    report = {
        "schemaVersion": "bfs.workerSequenceReport.v0.1",
        "shotId": args.shot_id,
        "frames": args.frame_list,
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
        "saveSettings": {
            "exr": {"mediaType":"IMAGE","fileFormat":"OPEN_EXR","colorMode":"RGBA","colorDepth":"32","codec":"ZIP"},
            "png": {"mediaType":"IMAGE","fileFormat":"PNG","colorMode":"RGBA","colorDepth":"8"},
        },
        "renderOperatorCalls": len(args.frame_list),
        "savesFromSameRenderResult": len(args.frame_list) * 2,
        "frameReports": frame_reports,
        "elapsedSeconds": round(time.perf_counter() - started, 6),
        "passed": True,
    }
    report_path = output_dir / "sequence.report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    milestone("REPORT_WRITTEN", {"passed": True, "reportSha256": sha256_file(report_path)})
    print(f"BFS_B46_SEQUENCE_OK {args.shot_id} frames={len(args.frame_list)}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B46_RENDER_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
