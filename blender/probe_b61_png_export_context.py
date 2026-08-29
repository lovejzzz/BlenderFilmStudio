import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys

import bpy


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def normalize(value):
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def canonical(value):
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def snapshot(scene):
    settings = scene.render.image_settings
    return {
        "scene": scene.name,
        "engine": scene.render.engine,
        "fileFormat": settings.file_format,
        "colorDepth": settings.color_depth,
        "exrCodec": settings.exr_codec,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
        "display": scene.display_settings.display_device,
        "view": scene.view_settings.view_transform,
    }


def write_hashed(path, body):
    record = {**body, "resultHash": sha256_bytes(canonical(body))}
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def main():
    args = parse_args()
    root = args.repository_root.resolve(strict=True)
    spec_path = args.spec.resolve(strict=True)
    output = args.output.resolve(strict=False)
    for path in [spec_path, output.parent]:
        path.relative_to(root)
    spec = json.loads(spec_path.read_text())
    production = bpy.context.scene
    before = snapshot(production)
    assignment_error = None
    try:
        production.render.image_settings.file_format = "PNG"
    except (TypeError, ValueError) as error:
        assignment_error = str(error)
    after_failed_assignment = snapshot(production)

    review = bpy.data.scenes.new("BFS_D4_REVIEW_SCENE")
    image = bpy.data.images.new("BFS_D4_GENERATED", width=2, height=2, alpha=True, float_buffer=True)
    png_path = output.parent / "generated-review.png"
    try:
        review.display_settings.display_device = production.display_settings.display_device
        review.view_settings.view_transform = production.view_settings.view_transform
        review.render.image_settings.file_format = "PNG"
        review.render.image_settings.color_mode = "RGBA"
        review.render.image_settings.color_depth = "8"
        image.pixels = [1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        image.save_render(filepath=str(png_path), scene=review)
        data = png_path.read_bytes()
        valid_png = len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", data[16:24]) == (2, 2)
        review_snapshot = snapshot(review)
    finally:
        bpy.data.images.remove(image)
        bpy.data.scenes.remove(review)

    after_cleanup = snapshot(production)
    production_unchanged = before == after_failed_assignment == after_cleanup
    success = assignment_error is not None and valid_png and review_snapshot["fileFormat"] == "PNG" and production_unchanged
    body = {
        "schemaVersion": "bfs.b61PngExportContextDiagnosticResult.v0.1",
        "status": "PASS" if success else "FAIL",
        "activeProductionScene": {"before": before, "assignmentError": assignment_error, "after": after_cleanup},
        "isolatedReviewScene": {"settings": review_snapshot, "png": {"uri": png_path.relative_to(root).as_posix(), "bytes": png_path.stat().st_size, "sha256": hashlib.sha256(png_path.read_bytes()).hexdigest(), "validHeader": valid_png, "dimensions": [2, 2]}},
        "productionSettingsUnchanged": production_unchanged,
        "operations": {"blenderProcesses": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
        "verdict": "ISOLATED_REVIEW_SCENE_PNG_EXPORT_SUPPORTED" if success else None,
    }
    record = write_hashed(output, body)
    if record["status"] != "PASS":
        raise RuntimeError("D4 success criteria failed")
    print(f"BFS_B61_D4 PASS {record['resultHash']}")


if __name__ == "__main__":
    main()
