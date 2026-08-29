"""Render one preregistered B62 terminal Cycles shot or await interruption."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import time

import bpy
import numpy
import OpenImageIO as oiio


SCENE_SHA256 = "0acd4d135c9bac9a7928a9a38da1a0e2f4838fd052a87a9663cef83cb2c373dc"
EXPECTED_BLENDER = "5.2.0 LTS"
EXPECTED_BUILD = "fbe6228777e7"
EXPECTED_OIIO = "3.1.13.1"
EXPECTED_NUMPY = "2.3.4"
SHOTS = {
    "WIDE": (1, 96, "SHOT_WIDE_APPROACH", "CAM_WIDE_APPROACH"),
    "MEDIUM": (97, 192, "SHOT_MEDIUM_CONTACT", "CAM_MEDIUM_CONTACT"),
    "CLOSE": (193, 288, "SHOT_CLOSE_REFLECTION", "CAM_CLOSE_MOTION_TERMINAL"),
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--attempt-root", type=Path, required=True)
    parser.add_argument("--mode", choices=("interrupt-probe", "render-shot"), required=True)
    parser.add_argument("--shot", choices=tuple(SHOTS), required=True)
    parser.add_argument("--go-file", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize(value):
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, float) and math.isfinite(value):
        return {"$f64be": struct.pack(">d", value).hex()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def canonical(value):
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fsync_file(path):
    with path.open("rb") as handle:
        os.fsync(handle.fileno())
    fsync_directory(path.parent)


def write_hashed(path, body, field):
    require(not path.exists(), f"authoritative path exists {path}")
    record = {**body, field: hashlib.sha256(canonical(body)).hexdigest()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(path.parent)
    return record


def file_identity(path, repository_root):
    return {
        "uri": path.relative_to(repository_root).as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def decode_combined(path):
    require(oiio.VERSION_STRING == EXPECTED_OIIO and numpy.__version__ == EXPECTED_NUMPY, "decoder runtime mismatch")
    image = oiio.ImageInput.open(str(path))
    require(image is not None, f"OpenImageIO open failed {path}")
    try:
        candidates = []
        subimage = 0
        while image.seek_subimage(subimage, 0):
            spec = image.spec()
            channel_names = list(spec.channelnames)
            positions = {name: index for index, name in enumerate(channel_names)}
            for name in channel_names:
                if not name.endswith(".R"):
                    continue
                prefix = name[:-2]
                wanted = [f"{prefix}.{channel}" for channel in "RGBA"]
                if prefix.split(".")[-1] == "Combined" and all(channel in positions for channel in wanted):
                    candidates.append({
                        "subimage": subimage,
                        "width": spec.width,
                        "height": spec.height,
                        "channels": spec.nchannels,
                        "prefix": prefix,
                        "channelNames": wanted,
                        "channelIndices": [positions[channel] for channel in wanted],
                    })
            subimage += 1
        require(len(candidates) == 1, f"expected one Combined RGBA quartet, found {len(candidates)}")
        candidate = candidates[0]
        pixels = image.read_image(candidate["subimage"], 0, 0, candidate["channels"], oiio.FLOAT)
        source = numpy.asarray(pixels)
        expected_shape = (candidate["height"], candidate["width"], candidate["channels"])
        require(tuple(source.shape) == expected_shape, f"decoded shape mismatch {source.shape}")
        rgba = numpy.ascontiguousarray(source[..., candidate["channelIndices"]], dtype=numpy.dtype("<f4"))
        rgb = rgba[..., :3]
        finite = numpy.isfinite(rgba)
        non_finite = int(rgba.size - int(numpy.count_nonzero(finite)))
        require(non_finite == 0, "non-finite Combined pixels")
        observation = {
            **candidate,
            "floatCount": int(rgba.size),
            "nonFiniteCount": non_finite,
            "rgbDynamicRange": float(numpy.max(rgb) - numpy.min(rgb)),
            "meanRgb": float(numpy.mean(rgb, dtype=numpy.float64)),
            "decodedCombinedSha256": hashlib.sha256(rgba.tobytes(order="C")).hexdigest(),
        }
        return rgba, observation
    finally:
        image.close()


def png_dimensions(path):
    data = path.read_bytes()[:24]
    require(data[:8] == b"\x89PNG\r\n\x1a\n", f"invalid PNG {path}")
    return [int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")]


def configure_scene(scene):
    require(scene.name == "B62_PHASE0_MASTER", "production scene name mismatch")
    if bpy.context.window is not None:
        bpy.context.window.scene = scene
    require(bpy.context.scene == scene, "production scene is not active")
    scene.display_settings.display_device = "sRGB - Display"
    scene.view_settings.view_transform = "ACES 2.0 - SDR 100 nits (Rec.709)"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.cycles.seed = 24082960
    scene.cycles.use_animated_seed = False
    scene.render.use_motion_blur = True
    scene.render.film_transparent = False
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.render.image_settings.exr_codec = "ZIP"
    observed = {
        "engine": scene.render.engine,
        "device": scene.cycles.device,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "resolutionPercentage": scene.render.resolution_percentage,
        "samples": scene.cycles.samples,
        "denoise": bool(scene.cycles.use_denoising),
        "seed": scene.cycles.seed,
        "animatedSeed": bool(scene.cycles.use_animated_seed),
        "motionBlur": bool(scene.render.use_motion_blur),
        "filmTransparent": bool(scene.render.film_transparent),
        "productionMediaType": scene.render.image_settings.media_type,
        "fileFormat": scene.render.image_settings.file_format,
        "colorMode": scene.render.image_settings.color_mode,
        "colorDepth": scene.render.image_settings.color_depth,
        "exrCodec": scene.render.image_settings.exr_codec,
        "color": {
            "display": scene.display_settings.display_device,
            "view": scene.view_settings.view_transform,
            "look": scene.view_settings.look,
            "exposure": float(scene.view_settings.exposure),
            "gamma": float(scene.view_settings.gamma),
        },
    }
    require(observed == {
        "engine": "CYCLES", "device": "CPU", "resolution": [1920, 1080], "resolutionPercentage": 100,
        "samples": 64, "denoise": True, "seed": 24082960, "animatedSeed": False,
        "motionBlur": True, "filmTransparent": False, "productionMediaType": "MULTI_LAYER_IMAGE",
        "fileFormat": "OPEN_EXR_MULTILAYER", "colorMode": "RGBA", "colorDepth": "16", "exrCodec": "ZIP",
        "color": {"display": "sRGB - Display", "view": "ACES 2.0 - SDR 100 nits (Rec.709)", "look": "None", "exposure": 0.0, "gamma": 1.0},
    }, "render contract mismatch")
    return observed


def main():
    args = parse_args()
    repository_root = args.repository_root.resolve(strict=True)
    attempt_root = args.attempt_root.resolve(strict=True)
    report_path = args.report.resolve()
    loaded = Path(bpy.data.filepath).resolve(strict=True)
    attempt_root.relative_to(repository_root)
    report_path.relative_to(attempt_root)
    require(bpy.app.version_string == EXPECTED_BLENDER and bpy.app.build_hash.decode("ascii") == EXPECTED_BUILD, "Blender runtime mismatch")
    require(sha256_file(loaded) == SCENE_SHA256, "source scene identity mismatch")
    require(os.environ.get("OCIO", "").endswith("color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio"), "OCIO binding mismatch")
    require(oiio.VERSION_STRING == EXPECTED_OIIO and numpy.__version__ == EXPECTED_NUMPY, "decoder versions mismatch")
    scene = bpy.context.scene
    require(scene.frame_start == 1 and scene.frame_end == 288 and scene.render.fps == 24, "timeline mismatch")
    settings = configure_scene(scene)
    source_before = sha256_file(loaded)

    start_frame, end_frame, expected_marker, expected_camera = SHOTS[args.shot]
    if args.mode == "interrupt-probe":
        require(args.shot == "WIDE" and args.go_file is not None, "interrupt probe contract")
        go_file = args.go_file.resolve()
        go_file.relative_to(attempt_root)
        require(not go_file.exists() and not report_path.exists(), "interrupt probe root is not fresh")
        print(f"BFS_T3_READY_FOR_CONTROLLED_INTERRUPT shot={args.shot} source={source_before}", flush=True)
        while not go_file.exists():
            time.sleep(0.1)
        raise RuntimeError("interrupt probe go file appeared; controlled termination did not occur")

    require(args.go_file is None, "render-shot forbids go file")
    exr_root = attempt_root / "exr"
    png_root = attempt_root / "png"
    frame_root = attempt_root / "frames"
    for directory in (exr_root, png_root, frame_root):
        directory.mkdir(exist_ok=False)
        fsync_directory(directory.parent)

    review_scene = bpy.data.scenes.new("B62_T3_ISOLATED_REVIEW")
    review_scene.display_settings.display_device = settings["color"]["display"]
    review_scene.view_settings.view_transform = settings["color"]["view"]
    review_scene.view_settings.look = settings["color"]["look"]
    review_scene.view_settings.exposure = settings["color"]["exposure"]
    review_scene.view_settings.gamma = settings["color"]["gamma"]
    review_scene.render.image_settings.file_format = "PNG"
    review_scene.render.image_settings.color_mode = "RGBA"
    review_scene.render.image_settings.color_depth = "8"

    frame_bindings = []
    render_seconds_total = 0.0
    process_started = time.perf_counter()
    for frame in range(start_frame, end_frame + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        active = max((marker for marker in scene.timeline_markers if marker.frame <= frame), key=lambda marker: (marker.frame, marker.name))
        require(active.name == expected_marker and active.camera and active.camera.name == expected_camera, f"route mismatch frame {frame}")
        scene.camera = active.camera
        require(bpy.context.scene == scene and scene.frame_current == frame and scene.camera.name == expected_camera, f"active context mismatch frame {frame}")
        context = {"scene": scene.name, "frame": int(scene.frame_current), "marker": active.name, "camera": scene.camera.name}

        exr_path = exr_root / f"frame-{frame:04d}.exr"
        png_path = png_root / f"frame-{frame:04d}.png"
        frame_report_path = frame_root / f"frame-{frame:04d}.json"
        require(not exr_path.exists() and not png_path.exists() and not frame_report_path.exists(), f"frame output exists {frame}")
        scene.render.filepath = str(exr_path)
        started = time.perf_counter()
        result = bpy.ops.render.render(write_still=True)
        render_seconds = time.perf_counter() - started
        render_seconds_total += render_seconds
        require("FINISHED" in result and exr_path.is_file() and exr_path.stat().st_size > 0, f"Cycles render failed frame {frame}")
        fsync_file(exr_path)
        rgba, decoded = decode_combined(exr_path)
        require(decoded["width"] == 1920 and decoded["height"] == 1080 and decoded["rgbDynamicRange"] > 1e-6 and 0.0001 < decoded["meanRgb"] < 0.9999, f"invalid Combined frame {frame}")

        review_image = bpy.data.images.new(f"B62_T3_REVIEW_{frame:04d}", width=1920, height=1080, alpha=True, float_buffer=True)
        try:
            review_image.colorspace_settings.name = "ACEScg"
            blender_rows = numpy.ascontiguousarray(numpy.flipud(rgba), dtype=numpy.float32)
            review_image.pixels.foreach_set(blender_rows.reshape(-1))
            review_image.update()
            require(review_image.has_data and list(review_image.size) == [1920, 1080] and len(review_image.pixels) == 1920 * 1080 * 4, f"generated review image invalid {frame}")
            review_image.save_render(filepath=str(png_path), scene=review_scene)
        finally:
            bpy.data.images.remove(review_image)
        require(png_dimensions(png_path) == [1920, 1080], f"PNG dimensions mismatch {frame}")
        fsync_file(png_path)

        frame_report = write_hashed(frame_report_path, {
            "schemaVersion": "bfs.b62TerminalCyclesFrameReport.v0.1",
            "experimentId": "B62-T3-E1",
            "shot": args.shot,
            "frame": frame,
            "context": context,
            "source": {"uri": loaded.relative_to(repository_root).as_posix(), "sha256": source_before},
            "settings": settings,
            "decoder": {"openImageIO": oiio.VERSION_STRING, "numpy": numpy.__version__},
            "decodedCombined": decoded,
            "exr": file_identity(exr_path, repository_root),
            "png": file_identity(png_path, repository_root),
            "renderSeconds": render_seconds,
            "operations": {"renderCalls": 1, "cyclesRenderCalls": 1, "sceneSaves": 0, "modelCalls": 0, "videoModelCalls": 0, "networkCalls": 0, "dockerProcesses": 0, "colimaProcesses": 0},
        }, "reportHash")
        frame_bindings.append({
            "frame": frame,
            "report": {"uri": frame_report_path.relative_to(repository_root).as_posix(), "sha256": sha256_file(frame_report_path), "reportHash": frame_report["reportHash"]},
            "exr": frame_report["exr"],
            "png": frame_report["png"],
            "decodedCombinedSha256": decoded["decodedCombinedSha256"],
        })
        print(f"BFS_T3_FRAME_COMMITTED shot={args.shot} frame={frame} digest={decoded['decodedCombinedSha256']}", flush=True)

    source_after = sha256_file(loaded)
    require(source_after == source_before == SCENE_SHA256, "source scene changed")
    bpy.data.scenes.remove(review_scene)
    shot_report = write_hashed(report_path, {
        "schemaVersion": "bfs.b62TerminalCyclesShotReport.v0.1",
        "experimentId": "B62-T3-E1",
        "status": "PASS",
        "shot": args.shot,
        "frames": [start_frame, end_frame],
        "frameCount": len(frame_bindings),
        "source": {"uri": loaded.relative_to(repository_root).as_posix(), "sha256": source_before, "sha256After": source_after, "unchanged": True},
        "settings": settings,
        "decoder": {"openImageIO": oiio.VERSION_STRING, "numpy": numpy.__version__},
        "frameBindings": frame_bindings,
        "renderSecondsTotal": render_seconds_total,
        "elapsedSeconds": time.perf_counter() - process_started,
        "operations": {"blenderStarts": 1, "renderCalls": len(frame_bindings), "cyclesRenderCalls": len(frame_bindings), "sceneSaves": 0, "modelCalls": 0, "videoModelCalls": 0, "networkCalls": 0, "dockerProcesses": 0, "colimaProcesses": 0},
    }, "reportHash")
    print(f"BFS_T3_SHOT_PASS shot={args.shot} frames={len(frame_bindings)} report={shot_report['reportHash']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_T3_RENDER_ERROR {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
