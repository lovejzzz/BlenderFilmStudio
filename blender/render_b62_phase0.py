"""Render the preregistered B62 Phase-0 animatic or one Cycles keyframe."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

import bpy
import numpy
import OpenImageIO as oiio


EXPECTED_OIIO_VERSION = "3.1.13.1"
EXPECTED_NUMPY_VERSION = "2.3.4"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--mode", choices=["animatic", "calibration"], required=True)
    parser.add_argument("--frame", type=int)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def normalize_numbers(value: object) -> object:
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_numbers(item) for key, item in value.items()}
    return value


def canonical(value: object) -> bytes:
    return json.dumps(normalize_numbers(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashed(path: Path, body: dict, field: str) -> dict:
    record = {**body, field: sha256_bytes(canonical(body))}
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def file_identity(path: Path, root: Path) -> dict:
    return {"uri": path.relative_to(root).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def require_master(formal_root: Path) -> tuple[bpy.types.Scene, Path]:
    path = formal_root / "scene/B62_PHASE0_MASTER.blend"
    if Path(bpy.data.filepath).resolve() != path.resolve() or not path.is_file():
        raise RuntimeError("Loaded B62 master blend identity mismatch")
    scene = bpy.data.scenes.get("B62_PHASE0_MASTER")
    if scene is None or scene.get("bfs_experiment_id") != "B62-P0-E1":
        raise RuntimeError("B62 master scene binding is absent")
    if scene.frame_start != 1 or scene.frame_end != 288 or scene.render.fps != 24:
        raise RuntimeError("B62 master timeline drift")
    return scene, path


def png_header(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Invalid PNG header: {path}")
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def make_isolated_scene(master: bpy.types.Scene, name: str) -> bpy.types.Scene:
    scene = bpy.data.scenes.new(name)
    content = bpy.data.collections.get("B62_PHASE0_CONTENT")
    if content is None:
        raise RuntimeError("B62 master content collection is absent")
    scene.collection.children.link(content)
    scene.world = master.world
    scene.frame_start = master.frame_start
    scene.frame_end = master.frame_end
    scene.render.fps = master.render.fps
    scene.render.fps_base = master.render.fps_base
    scene.display_settings.display_device = master.display_settings.display_device
    scene.view_settings.view_transform = master.view_settings.view_transform
    scene.view_settings.look = master.view_settings.look
    scene.view_settings.exposure = master.view_settings.exposure
    scene.view_settings.gamma = master.view_settings.gamma
    for marker in master.timeline_markers:
        clone = scene.timeline_markers.new(marker.name, frame=marker.frame)
        clone.camera = marker.camera
    scene.camera = master.camera
    return scene


def pixel_projection(exr_path: Path) -> tuple[dict, numpy.ndarray]:
    if oiio.VERSION_STRING != EXPECTED_OIIO_VERSION or numpy.__version__ != EXPECTED_NUMPY_VERSION:
        raise RuntimeError("Bundled OpenImageIO/NumPy version mismatch")
    image_input = oiio.ImageInput.open(str(exr_path))
    if image_input is None:
        raise RuntimeError("OpenImageIO could not open multilayer EXR")
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
                if prefix.split(".")[-1] != "Combined":
                    continue
                wanted = [f"{prefix}.{component}" for component in "RGBA"]
                if all(channel in positions for channel in wanted):
                    candidates.append((subimage, spec.width, spec.height, spec.nchannels, prefix, wanted, [positions[channel] for channel in wanted]))
            subimage += 1
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one Combined RGBA quartet, found {len(candidates)}")
        subimage, width, height, channels, prefix, names, indices = candidates[0]
        pixels = image_input.read_image(subimage, 0, 0, channels, oiio.FLOAT)
        if pixels is None:
            raise RuntimeError(f"OpenImageIO read failed: {image_input.geterror()}")
        array = numpy.asarray(pixels)
        values = numpy.ascontiguousarray(array[..., indices], dtype=numpy.dtype("<f4"))
        finite = numpy.isfinite(values)
        minima = [float(value) for value in values.min(axis=(0, 1))]
        maxima = [float(value) for value in values.max(axis=(0, 1))]
        means = [float(value) for value in values.mean(axis=(0, 1), dtype=numpy.float64)]
        projection = {
            "projection": "DECODED_COMBINED_RGBA_FLOAT32_LE",
            "decoder": {"module": "OpenImageIO", "version": oiio.VERSION_STRING, "numpyVersion": numpy.__version__, "subimage": subimage, "prefix": prefix, "channelNames": names, "channelIndices": indices},
            "width": width,
            "height": height,
            "channels": 4,
            "floatCount": int(values.size),
            "sha256": sha256_bytes(values.tobytes(order="C")),
            "finiteCount": int(finite.sum()),
            "nonFiniteCount": int(values.size - finite.sum()),
            "minimum": minima,
            "maximum": maxima,
            "mean": means,
            "rgbDynamicRange": max(maxima[:3]) - min(minima[:3]),
        }
        return projection, values
    finally:
        image_input.close()


def select_scene_linear_colorspace(image: bpy.types.Image) -> str:
    errors = []
    for candidate in ("ACEScg", "Linear Rec.709", "Linear", "scene_linear"):
        try:
            image.colorspace_settings.name = candidate
            return image.colorspace_settings.name
        except TypeError as error:
            errors.append(str(error))
    raise RuntimeError(f"No scene-linear review image colorspace is available: {errors[-1] if errors else 'unknown'}")


def save_review_png(master: bpy.types.Scene, projection: dict, values: numpy.ndarray, path: Path) -> dict:
    review_scene = make_isolated_scene(master, "B62_PHASE0_REVIEW")
    review_scene.render.image_settings.file_format = "PNG"
    review_scene.render.image_settings.color_depth = "8"
    review_scene.render.image_settings.color_mode = "RGBA"
    image = bpy.data.images.new("B62_PHASE0_REVIEW_IMAGE", width=projection["width"], height=projection["height"], alpha=True, float_buffer=True)
    try:
        colorspace = select_scene_linear_colorspace(image)
        rows = numpy.ascontiguousarray(numpy.flipud(values), dtype=numpy.float32)
        image.pixels.foreach_set(rows.reshape(-1))
        image.update()
        image.save_render(filepath=str(path), scene=review_scene)
    finally:
        bpy.data.images.remove(image)
        bpy.data.scenes.remove(review_scene)
    width, height = png_header(path)
    if (width, height) != (projection["width"], projection["height"]):
        raise RuntimeError("Review PNG dimensions drift")
    return {"colorspace": colorspace, "rowConversion": "OIIO_Y0_TOP_TO_BLENDER_PIXEL0_BOTTOM"}


def render_animatic(repository_root: Path, formal_root: Path, master: bpy.types.Scene, master_path: Path) -> None:
    output_dir = formal_root / "animatic"
    output_dir.mkdir(parents=True, exist_ok=False)
    scene = make_isolated_scene(master, "B62_PHASE0_ANIMATIC")
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.use_motion_blur = True
    if not hasattr(scene, "eevee"):
        raise RuntimeError("Blender 5.2 Eevee settings are unavailable")
    scene.eevee.taa_samples = 16
    scene.eevee.taa_render_samples = 16
    started = time.perf_counter()
    frames = []
    for frame in range(1, 289):
        scene.frame_set(frame)
        path = output_dir / f"frame-{frame:04d}.png"
        scene.render.filepath = str(path)
        frame_started = time.perf_counter()
        bpy.ops.render.render(scene=scene.name, write_still=True)
        elapsed = time.perf_counter() - frame_started
        if png_header(path) != (640, 360):
            raise RuntimeError(f"Animatic PNG dimensions drift at frame {frame}")
        frames.append({"frame": frame, "camera": scene.camera.name if scene.camera else None, "renderSeconds": elapsed, **file_identity(path, repository_root)})
    report = write_hashed(output_dir / "animatic-render-report.json", {
        "schemaVersion": "bfs.b62Phase0AnimaticRenderReport.v0.1",
        "status": "PASS",
        "master": file_identity(master_path, repository_root),
        "settings": {"engine": scene.render.engine, "resolution": [640, 360], "samples": scene.eevee.taa_render_samples, "format": "PNG", "fps": 24},
        "frames": frames,
        "elapsedSeconds": time.perf_counter() - started,
        "operations": {"blenderStarts": 1, "renderCalls": 288, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }, "reportHash")
    bpy.data.scenes.remove(scene)
    print(f"BFS_B62_PHASE0_ANIMATIC_OK {len(frames)} {report['reportHash']}")


def render_calibration(repository_root: Path, formal_root: Path, master: bpy.types.Scene, master_path: Path, frame: int) -> None:
    if frame not in (48, 144, 240):
        raise RuntimeError("Calibration frame is not preregistered")
    output_dir = formal_root / "calibration"
    output_dir.mkdir(parents=True, exist_ok=True)
    shot = {48: "WIDE_APPROACH", 144: "MEDIUM_CONTACT", 240: "CLOSE_REFLECTION"}[frame]
    exr_path = output_dir / f"{shot}-{frame:04d}.exr"
    png_path = output_dir / f"{shot}-{frame:04d}.png"
    report_path = output_dir / f"{shot}-{frame:04d}.pixel.json"
    for path in (exr_path, png_path, report_path):
        if path.exists():
            raise RuntimeError(f"Calibration output already exists: {path}")
    scene = master
    scene.frame_set(frame)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.cycles.use_animated_seed = False
    scene.cycles.seed = 62001
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.render.image_settings.exr_codec = "ZIP"
    scene.render.filepath = str(exr_path)
    started = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    render_seconds = time.perf_counter() - started
    if not exr_path.is_file() or exr_path.stat().st_size == 0:
        raise RuntimeError("Calibration EXR is absent")
    projection, values = pixel_projection(exr_path)
    if projection["width"] != 1920 or projection["height"] != 1080 or projection["nonFiniteCount"] != 0 or projection["rgbDynamicRange"] <= 1e-6:
        raise RuntimeError("Calibration decoded pixels are invalid")
    review = save_review_png(master, projection, values, png_path)
    report = write_hashed(report_path, {
        "schemaVersion": "bfs.b62Phase0CalibrationPixelReport.v0.1",
        "status": "PASS",
        "shot": shot,
        "frame": frame,
        "camera": scene.camera.name if scene.camera else None,
        "master": file_identity(master_path, repository_root),
        "settings": {"engine": scene.render.engine, "device": scene.cycles.device, "resolution": [1920, 1080], "samples": scene.cycles.samples, "denoise": scene.cycles.use_denoising, "seed": scene.cycles.seed, "animatedSeed": scene.cycles.use_animated_seed, "mediaType": scene.render.image_settings.media_type, "format": "OPEN_EXR_MULTILAYER", "pixelType": "HALF", "compression": "ZIP"},
        "renderSeconds": render_seconds,
        "exr": file_identity(exr_path, repository_root),
        "png": file_identity(png_path, repository_root),
        "review": review,
        "decodedCombined": projection,
        "operations": {"blenderStarts": 1, "renderCalls": 1, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }, "reportHash")
    print(f"BFS_B62_PHASE0_CALIBRATION_OK {shot} {frame} {report['reportHash']} {projection['sha256']}")


def main() -> None:
    args = parse_args()
    repository_root = args.repository_root.resolve(strict=True)
    formal_root = args.formal_root.resolve(strict=True)
    try:
        formal_root.relative_to(repository_root)
    except ValueError as error:
        raise RuntimeError("Formal root escapes repository") from error
    master, master_path = require_master(formal_root)
    if args.mode == "animatic":
        if args.frame is not None:
            raise RuntimeError("Animatic mode does not accept --frame")
        render_animatic(repository_root, formal_root, master, master_path)
    else:
        if args.frame is None:
            raise RuntimeError("Calibration mode requires --frame")
        render_calibration(repository_root, formal_root, master, master_path, args.frame)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B62_PHASE0_RENDER_ERROR {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
