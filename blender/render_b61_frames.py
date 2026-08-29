#!/usr/bin/env python3
"""Render one B61 shot/repetition and emit EXR, PNG and decoded-pixel receipts."""

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
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--shot", required=True)
    parser.add_argument("--repetition", choices=["A", "B"], required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def normalize_canonical_numbers(value: object) -> object:
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize_canonical_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_canonical_numbers(item) for key, item in value.items()}
    return value


def canonical(value: object) -> bytes:
    normalized = normalize_canonical_numbers(value)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


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


class StageLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.sequence = 0
        self.previous_hash = None
        with path.open("x", encoding="utf-8") as handle:
            handle.flush()
            os.fsync(handle.fileno())

    def append(self, event_type: str, **payload: object) -> dict:
        self.sequence += 1
        body = {
            "sequence": self.sequence,
            "eventType": event_type,
            "previousEventHash": self.previous_hash,
            "payload": payload,
        }
        record = {**body, "eventHash": sha256_bytes(canonical(body))}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.previous_hash = record["eventHash"]
        return record


def require_below(root: Path, candidate: Path, label: str) -> Path:
    root = root.resolve(strict=True)
    resolved = candidate.resolve(strict=candidate.exists())
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"{label} is outside repository root") from error
    return resolved


def pixel_projection(exr_path: Path) -> dict:
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
        subimage, width, height, channel_count, prefix, names, indices = candidates[0]
        pixels = image_input.read_image(subimage, 0, 0, channel_count, oiio.FLOAT)
        if pixels is None:
            raise RuntimeError(f"OpenImageIO read_image failed: {image_input.geterror()}")
        array_value = numpy.asarray(pixels)
        if tuple(array_value.shape) != (height, width, channel_count):
            raise RuntimeError(f"Decoded shape mismatch: {array_value.shape}")
        values = numpy.ascontiguousarray(array_value[..., indices], dtype=numpy.dtype("<f4"))
        finite = numpy.isfinite(values)
        minima = [float(value) for value in values.min(axis=(0, 1))]
        maxima = [float(value) for value in values.max(axis=(0, 1))]
        means = [float(value) for value in values.mean(axis=(0, 1), dtype=numpy.float64)]
        finite_count = int(finite.sum())
        non_finite_count = int(values.size - finite_count)
        projection = {
            "projection": "DECODED_COMBINED_RGBA_FLOAT32_LE",
            "decoder": {"module": "OpenImageIO", "version": oiio.VERSION_STRING, "numpyVersion": numpy.__version__, "subimage": subimage, "prefix": prefix, "channelNames": names, "channelIndices": indices},
            "width": width,
            "height": height,
            "channels": 4,
            "floatCount": int(values.size),
            "sha256": sha256_bytes(values.tobytes(order="C")),
            "finiteCount": finite_count,
            "nonFiniteCount": non_finite_count,
            "minimum": minima,
            "maximum": maxima,
            "mean": means,
            "rgbDynamicRange": max(maxima[:3]) - min(minima[:3]),
        }
        return projection, values
    finally:
        image_input.close()


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
    scene.cycles.use_denoising = render["denoise"]
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_depth = "16"
    scene.render.image_settings.exr_codec = "ZIP"
    scene.render.film_transparent = False

    production_image_settings = {
        "fileFormat": scene.render.image_settings.file_format,
        "colorDepth": scene.render.image_settings.color_depth,
        "exrCodec": scene.render.image_settings.exr_codec,
    }
    review_scene = bpy.data.scenes.new("BFS_B61_ISOLATED_REVIEW")
    review_scene.display_settings.display_device = scene.display_settings.display_device
    review_scene.view_settings.view_transform = scene.view_settings.view_transform
    review_scene.view_settings.look = scene.view_settings.look
    review_scene.view_settings.exposure = scene.view_settings.exposure
    review_scene.view_settings.gamma = scene.view_settings.gamma
    review_scene.render.image_settings.file_format = "PNG"
    review_scene.render.image_settings.color_depth = "8"
    review_scene.render.image_settings.color_mode = "RGBA"

    reports = []
    ledger = StageLedger(output_dir / "stage-events.jsonl")
    ledger.append("PROCESS_BOUND", shot=args.shot, repetition=args.repetition, sourceBlendSha256=shot["sourceBlend"]["sha256"], ocioSha256=ocio["sha256"])
    process_started = time.perf_counter()
    for frame in render["frames"]:
        stem = f"frame-{frame:04d}"
        exr_path = output_dir / f"{stem}.exr"
        png_path = output_dir / f"{stem}.png"
        report_path = output_dir / f"{stem}.pixel.json"
        ledger.append("FRAME_STARTED", frame=frame)
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
        ledger.append("EXR_WRITTEN", frame=frame, sha256=sha256_file(exr_path), bytes=exr_path.stat().st_size)
        projection, review_pixels = pixel_projection(exr_path)
        ledger.append("EXR_REOPENED", frame=frame, width=projection["width"], height=projection["height"])
        if projection["nonFiniteCount"] != 0 or projection["rgbDynamicRange"] <= 1e-6:
            raise RuntimeError(f"Invalid decoded pixels for frame {frame}")
        ledger.append("PIXEL_PROJECTED", frame=frame, sha256=projection["sha256"], nonFiniteCount=projection["nonFiniteCount"])

        review_image = bpy.data.images.new(f"BFS_B61_REVIEW_{args.shot}_{args.repetition}_{frame}", width=projection["width"], height=projection["height"], alpha=True, float_buffer=True)
        try:
            review_image.colorspace_settings.name = "ACEScg"
            blender_rows = numpy.ascontiguousarray(numpy.flipud(review_pixels), dtype=numpy.float32)
            review_image.pixels.foreach_set(blender_rows.reshape(-1))
            review_image.update()
            if not review_image.has_data or len(review_image.pixels) != projection["floatCount"]:
                raise RuntimeError(f"Generated review image has no data for frame {frame}")
            review_image.save_render(filepath=str(png_path), scene=review_scene)
        finally:
            bpy.data.images.remove(review_image)
        if not png_path.is_file() or png_path.stat().st_size == 0:
            raise RuntimeError(f"Missing PNG for frame {frame}")
        ledger.append("PNG_WRITTEN", frame=frame, sha256=sha256_file(png_path), bytes=png_path.stat().st_size)
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
                "denoise": scene.cycles.use_denoising,
                "format": "OPEN_EXR_MULTILAYER",
                "pixelType": "HALF_16",
                "compression": "ZIP_LOSSLESS",
                "ocioConfigSha256": ocio["sha256"],
                "pngExportContext": "ISOLATED_REVIEW_SCENE",
                "pngPixelSource": "GENERATED_FLOAT_IMAGE_FROM_DECODED_COMBINED",
                "pngSourceColorSpace": "ACEScg",
                "pngRowOrderConversion": "OIIO_Y0_TOP_TO_BLENDER_PIXEL0_BOTTOM",
                "pngSourcePixelSha256": projection["sha256"],
                "productionImageSettingsUnchanged": production_image_settings == {
                    "fileFormat": scene.render.image_settings.file_format,
                    "colorDepth": scene.render.image_settings.color_depth,
                    "exrCodec": scene.render.image_settings.exr_codec,
                },
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
        ledger.append("PIXEL_REPORT_WRITTEN", frame=frame, reportHash=report["reportHash"], sha256=sha256_file(report_path))

    run_report_path = output_dir / "run-report.json"
    run_report = write_hashed(run_report_path, {
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
    ledger.append("RUN_REPORT_WRITTEN", runReportHash=run_report["runReportHash"], sha256=sha256_file(run_report_path))
    bpy.data.scenes.remove(review_scene)
    print(f"BFS_B61_RENDER_OK {args.shot}-{args.repetition} frames={len(reports)}")


if __name__ == "__main__":
    main()
