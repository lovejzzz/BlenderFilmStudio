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


FRAMES = (198, 210, 222, 234, 246, 258, 270, 282)
CONDITIONS = (("STATIC", "CAM_CLOSE_STATIC_D6"), ("MOTION_AWARE", "CAM_CLOSE_MOTION_D6"))


def arguments():
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--derived-sha256", required=True)
    return parser.parse_args(tail)


def require(condition, message):
    if not condition: raise RuntimeError(message)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def normalize(value):
    if isinstance(value, float) and math.isfinite(value) and value.is_integer(): return int(value)
    if isinstance(value, float) and math.isfinite(value): return {"$f64be": struct.pack(">d", value).hex()}
    if isinstance(value, list): return [normalize(item) for item in value]
    if isinstance(value, dict): return {key: normalize(item) for key, item in value.items()}
    return value


def canonical(value):
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def write_hashed(path, body, field):
    value = dict(body)
    value[field] = hashlib.sha256(canonical(value)).hexdigest()
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return value


def file_identity(path, base):
    return {"uri": path.relative_to(base).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def png_size(path):
    header = path.read_bytes()[:24]
    require(header[:8] == b"\x89PNG\r\n\x1a\n", f"invalid PNG {path}")
    return [int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")]


def decode_combined(path):
    require(oiio.VERSION_STRING == "3.1.13.1" and numpy.__version__ == "2.3.4", "decoder version mismatch")
    image = oiio.ImageInput.open(str(path))
    require(image is not None, f"cannot open EXR {path}")
    try:
        matches = []
        subimage = 0
        while image.seek_subimage(subimage, 0):
            spec = image.spec()
            names = list(spec.channelnames)
            positions = {name: index for index, name in enumerate(names)}
            for name in names:
                if name.endswith(".R") and name[:-2].split(".")[-1] == "Combined":
                    prefix = name[:-2]
                    wanted = [f"{prefix}.{channel}" for channel in "RGBA"]
                    if all(channel in positions for channel in wanted): matches.append((subimage, spec.width, spec.height, spec.nchannels, prefix, wanted, [positions[channel] for channel in wanted]))
            subimage += 1
        require(len(matches) == 1, f"Combined quartet count {len(matches)}")
        subimage, width, height, channel_count, prefix, names, indices = matches[0]
        pixels = image.read_image(subimage, 0, 0, channel_count, oiio.FLOAT)
        require(pixels is not None, "EXR read failed")
        values = numpy.ascontiguousarray(numpy.asarray(pixels)[..., indices], dtype=numpy.dtype("<f4"))
        finite = numpy.isfinite(values)
        minima = [float(value) for value in values.min(axis=(0, 1))]
        maxima = [float(value) for value in values.max(axis=(0, 1))]
        return {"decoder": {"oiio": oiio.VERSION_STRING, "numpy": numpy.__version__, "subimage": subimage, "prefix": prefix, "channelNames": names, "channelIndices": indices}, "width": width, "height": height, "floatCount": int(values.size), "sha256": hashlib.sha256(values.tobytes(order="C")).hexdigest(), "finiteCount": int(finite.sum()), "nonFiniteCount": int(values.size - finite.sum()), "minimum": minima, "maximum": maxima, "rgbDynamicRange": max(maxima[:3]) - min(minima[:3])}
    finally:
        image.close()


def main():
    args = arguments()
    scene_path = Path(bpy.data.filepath).resolve()
    require(scene_path.name == "B62_PHASE0_D6_MOTION_AWARE.blend" and sha256_file(scene_path) == args.derived_sha256, "derived scene identity mismatch")
    require(bpy.app.version_string.startswith("5.2"), "unexpected Blender")
    scene = bpy.context.scene
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for _condition, camera_name in CONDITIONS: require(bpy.data.objects.get(camera_name) is not None, f"missing camera {camera_name}")
    close_markers = [marker for marker in scene.timeline_markers if marker.name == "SHOT_CLOSE_REFLECTION" and marker.frame == 193]
    require(len(close_markers) == 1 and close_markers[0].camera is not None and close_markers[0].camera.name == "CAM_CLOSE_REFLECTION", "close marker mismatch")
    close_marker = close_markers[0]
    original_marker_camera, original_scene_camera = close_marker.camera, scene.camera
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.cycles.use_animated_seed = False
    scene.cycles.seed = 62006
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.view_settings.look = "Medium High Contrast"
    rows = []
    started = time.perf_counter()
    for frame in FRAMES:
        for condition, camera_name in CONDITIONS:
            scene.frame_set(frame)
            close_marker.camera = bpy.data.objects[camera_name]
            scene.camera = bpy.data.objects[camera_name]
            stem = f"{frame:04d}-{condition.lower().replace('_', '-')}"
            exr_path, png_path = args.output_dir / f"{stem}.exr", args.output_dir / f"{stem}.png"
            scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
            scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
            scene.render.image_settings.color_mode = "RGBA"
            scene.render.image_settings.color_depth = "32"
            scene.render.image_settings.exr_codec = "ZIP"
            scene.render.filepath = str(exr_path)
            frame_started = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            elapsed = time.perf_counter() - frame_started
            require(exr_path.is_file() and exr_path.stat().st_size > 0, "EXR missing")
            projection = decode_combined(exr_path)
            require((projection["width"], projection["height"]) == (960, 540) and projection["nonFiniteCount"] == 0 and projection["rgbDynamicRange"] > 1e-6, "decoded pixels invalid")
            scene.render.image_settings.media_type = "IMAGE"
            scene.render.image_settings.file_format = "PNG"
            scene.render.image_settings.color_mode = "RGBA"
            scene.render.image_settings.color_depth = "8"
            bpy.data.images["Render Result"].save_render(filepath=str(png_path), scene=scene)
            require(png_size(png_path) == [960, 540], "PNG dimensions mismatch")
            rows.append({"frame": frame, "condition": condition, "camera": camera_name, "timelineMarker": close_marker.name, "timelineMarkerCamera": close_marker.camera.name, "renderSeconds": elapsed, "exr": file_identity(exr_path, args.report.parent), "png": file_identity(png_path, args.report.parent), "combined": projection})
    close_marker.camera, scene.camera = original_marker_camera, original_scene_camera
    pairs = []
    for frame in FRAMES:
        static = next(row for row in rows if row["frame"] == frame and row["condition"] == "STATIC")
        motion = next(row for row in rows if row["frame"] == frame and row["condition"] == "MOTION_AWARE")
        pairs.append({"frame": frame, "staticCombinedSha256": static["combined"]["sha256"], "motionCombinedSha256": motion["combined"]["sha256"], "different": static["combined"]["sha256"] != motion["combined"]["sha256"]})
    report = write_hashed(args.report, {"schemaVersion": "bfs.b62CameraQualityMotionAwareHoldoutRender.v0.1", "experimentId": "B62-Q1-D6", "status": "PASS", "derivedScene": {"filepath": str(scene_path), "sha256": args.derived_sha256}, "settings": {"engine": scene.render.engine, "device": scene.cycles.device, "resolution": [960, 540], "samples": 16, "denoise": True, "seed": 62006, "animatedSeed": False, "format": "OPEN_EXR_MULTILAYER", "pixelType": "FLOAT", "compression": "ZIP", "viewTransform": scene.view_settings.view_transform, "look": scene.view_settings.look}, "renders": rows, "pairs": pairs, "elapsedSeconds": time.perf_counter() - started, "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("utf-8")}, "operations": {"blenderStarts": 1, "renderCalls": 16, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0}}, "reportHash")
    print(f"BFS_B62_Q1_D6_RENDER PASS renders={len(rows)} seconds={report['elapsedSeconds']:.3f} report={report['reportHash']}")


if __name__ == "__main__":
    main()
