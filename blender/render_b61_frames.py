#!/usr/bin/env python3
"""Render one B61 shot/repetition and emit EXR, PNG and decoded-pixel receipts."""

from __future__ import annotations

import argparse
import array
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

import bpy


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--shot", required=True)
    parser.add_argument("--repetition", choices=["A", "B"], required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashed(path: Path, body: dict, hash_field: str) -> dict:
    record = {**body, hash_field: sha256_bytes(canonical(body))}
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def require_below(root: Path, candidate: Path, label: str) -> Path:
    root = root.resolve(strict=True)
    resolved = candidate.resolve(strict=candidate.exists())
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"{label} is outside repository root") from error
    return resolved


def pixels_as_float32(image: bpy.types.Image) -> array.array:
    count = len(image.pixels)
    values = array.array("f", [0.0]) * count
    try:
        image.pixels.foreach_get(values)
    except AttributeError:
        values = array.array("f", image.pixels[:])
    if sys.byteorder != "little":
        values.byteswap()
    return values


def pixel_projection(exr_path: Path) -> dict:
    image = bpy.data.images.load(str(exr_path), check_existing=False)
    try:
        width, height = image.size
        values = pixels_as_float32(image)
        expected = width * height * 4
        if len(values) != expected:
            raise RuntimeError(f"Decoded Combined RGBA float count mismatch: {len(values)} != {expected}")
        minima = [math.inf] * 4
        maxima = [-math.inf] * 4
        sums = [0.0] * 4
        finite_count = 0
        non_finite_count = 0
        for index, value in enumerate(values):
            channel = index % 4
            if math.isfinite(value):
                finite_count += 1
                minima[channel] = min(minima[channel], value)
                maxima[channel] = max(maxima[channel], value)
                sums[channel] += value
            else:
                non_finite_count += 1
        per_channel_count = width * height
        means = [value / per_channel_count for value in sums]
        return {
            "projection": "DECODED_COMBINED_RGBA_FLOAT32_LE",
            "width": width,
            "height": height,
            "channels": 4,
            "floatCount": len(values),
            "sha256": sha256_bytes(values.tobytes()),
            "finiteCount": finite_count,
            "nonFiniteCount": non_finite_count,
            "minimum": minima,
            "maximum": maxima,
            "mean": means,
            "rgbDynamicRange": max(maxima[:3]) - min(minima[:3]),
        }
    finally:
        bpy.data.images.remove(image)


def file_identity(path: Path, root: Path) -> dict:
    return {
        "uri": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def main() -> None:
    args = parse_args()
    repository_root = args.repository_root.resolve(strict=True)
    contract_path = require_below(repository_root, args.contract, "Contract")
    output_dir = require_below(repository_root, args.output_dir, "Output directory")
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise RuntimeError("Output directory must exist and be empty")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    shot = next((row for row in contract["shots"] if row["label"] == args.shot), None)
    if shot is None:
        raise RuntimeError("Unknown B61 shot")
    source_path = require_below(repository_root, repository_root / shot["sourceBlend"]["uri"], "Source blend")
    if Path(bpy.data.filepath).resolve() != source_path or sha256_file(source_path) != shot["sourceBlend"]["sha256"]:
        raise RuntimeError("Loaded blend identity mismatch")
    ocio = contract["runtime"]["ocio"]
    ocio_path = require_below(repository_root, repository_root / ocio["uri"], "OCIO config")
    if os.environ.get("OCIO") != str(ocio_path) or sha256_file(ocio_path) != ocio["sha256"]:
        raise RuntimeError("Frozen OCIO environment mismatch")
    if bpy.app.version_string != contract["runtime"]["blenderVersion"].replace("Blender ", ""):
        raise RuntimeError("Blender version mismatch")
    build_hash = bpy.app.build_hash.decode("ascii") if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash)
    if build_hash != contract["runtime"]["blenderBuildHash"]:
        raise RuntimeError("Blender build hash mismatch")

    scene = bpy.context.scene
    if scene.get("bfs_ocio_sha256") != ocio["sha256"] or scene.get("bfs_ocio_config") != ocio["name"]:
        raise RuntimeError("Scene OCIO custom-property binding mismatch")
    if scene.display_settings.display_device != ocio["display"] or scene.view_settings.view_transform != ocio["view"]:
        raise RuntimeError("Scene display/view binding mismatch")
    render = contract["render"]
    scene.render.engine = render["engine"]
    scene.cycles.device = render["device"]
    scene.render.resolution_x = render["resolution"]["width"]
    scene.render.resolution_y = render["resolution"]["height"]
    scene.render.resolution_percentage = render["resolution"]["percentage"]
    scene.cycles.samples = render["samples"]
    scene.cycles.use_animated_seed = render["animatedSeed"]
    scene.cycles.seed = render["seed"]
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_depth = "16"
    scene.render.image_settings.exr_codec = "ZIP"
    scene.render.film_transparent = False

    reports = []
    process_started = time.perf_counter()
    for frame in render["frames"]:
        stem = f"frame-{frame:04d}"
        exr_path = output_dir / f"{stem}.exr"
        png_path = output_dir / f"{stem}.png"
        report_path = output_dir / f"{stem}.pixel.json"
        scene.frame_set(frame)
        scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
        scene.render.image_settings.color_depth = "16"
        scene.render.image_settings.exr_codec = "ZIP"
        scene.render.filepath = str(exr_path)
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        render_seconds = time.perf_counter() - started
        if not exr_path.is_file() or exr_path.stat().st_size == 0:
            raise RuntimeError(f"Missing EXR for frame {frame}")
        projection = pixel_projection(exr_path)
        if projection["nonFiniteCount"] != 0 or projection["rgbDynamicRange"] <= 1e-6:
            raise RuntimeError(f"Invalid decoded pixels for frame {frame}")

        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_depth = "8"
        scene.render.image_settings.color_mode = "RGBA"
        bpy.data.images["Render Result"].save_render(filepath=str(png_path), scene=scene)
        if not png_path.is_file() or png_path.stat().st_size == 0:
            raise RuntimeError(f"Missing PNG for frame {frame}")
        report = write_hashed(report_path, {
            "schemaVersion": "bfs.cinematicRenderPixelReport.v0.1",
            "shot": args.shot,
            "repetition": args.repetition,
            "frame": frame,
            "settings": {
                "engine": scene.render.engine,
                "device": scene.cycles.device,
                "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
                "samples": scene.cycles.samples,
                "seed": scene.cycles.seed,
                "animatedSeed": scene.cycles.use_animated_seed,
                "denoise": render["denoise"],
            },
            "renderSeconds": render_seconds,
            "exr": file_identity(exr_path, repository_root),
            "png": file_identity(png_path, repository_root),
            "decodedCombined": projection,
            "renderCalls": 1,
        }, "reportHash")
        reports.append({
            "frame": frame,
            "report": file_identity(report_path, repository_root),
            "reportHash": report["reportHash"],
            "pixelSha256": projection["sha256"],
        })

    write_hashed(output_dir / "run-report.json", {
        "schemaVersion": "bfs.cinematicRenderRunReport.v0.1",
        "status": "PASS",
        "shot": args.shot,
        "repetition": args.repetition,
        "sourceBlend": shot["sourceBlend"],
        "planHash": shot["planHash"],
        "structureHash": shot["structureHash"],
        "runtime": {"blenderVersion": bpy.app.version_string, "blenderBuildHash": build_hash},
        "ocio": ocio,
        "frames": reports,
        "elapsedSeconds": time.perf_counter() - process_started,
        "operations": {"renderCalls": len(reports), "frames": len(reports), "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }, "runReportHash")
    print(f"BFS_B61_RENDER_OK {args.shot}-{args.repetition} frames={len(reports)}")


if __name__ == "__main__":
    main()
