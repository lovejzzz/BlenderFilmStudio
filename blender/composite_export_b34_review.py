"""Average B34 source EXRs in scene-linear ACEScg and export pinned display PNGs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import bpy
import numpy as np
import OpenImageIO as oiio
import PyOpenColorIO as ocio


METHODS = ("NATURAL32", "QUADRATURE4", "STRATIFIED8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-spec", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--composite-root", type=Path, required=True)
    parser.add_argument("--display-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_equal(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise RuntimeError(f"{label} mismatch: observed={observed!r} expected={expected!r}")


def method_cells_and_weights(spec: dict[str, Any], method: str) -> tuple[list[str], list[float]]:
    design = spec["renderDesign"]
    if method == "NATURAL32":
        return ["NATURAL32"], [1.0]
    if method == "QUADRATURE4":
        return [f"Q4_{index}" for index in range(1, 5)], design["quadrature4"]["weights"]
    return [f"Q8_{index}" for index in range(1, 9)], design["stratified8"]["weights"]


def read_scene_linear(path: Path, width: int, height: int) -> np.ndarray:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot read source EXR: {path}")
    spec = image.spec()
    layout = [spec.width, spec.height, spec.nchannels, list(spec.channelnames), str(spec.format)]
    require_equal(layout, [width, height, 4, ["R", "G", "B", "A"], "float"], f"EXR layout {path.name}")
    require_equal(spec.getattribute("oiio:ColorSpace"), "lin_ap1_scene", f"EXR colorspace {path.name}")
    return np.asarray(image.get_pixels(oiio.FLOAT), dtype=np.float32)


def write_scene_linear(path: Path, pixels: np.ndarray) -> None:
    height, width, channels = pixels.shape
    require_equal(channels, 4, "composite channel count")
    spec = oiio.ImageSpec(width, height, channels, oiio.FLOAT)
    spec.channelnames = ("R", "G", "B", "A")
    spec.attribute("compression", "zip")
    spec.attribute("oiio:ColorSpace", "lin_ap1_scene")
    spec.attribute("colorInteropID", "lin_ap1_scene")
    output = oiio.ImageOutput.create(str(path))
    if output is None or not output.open(str(path), spec):
        raise RuntimeError(f"Cannot create composite EXR: {path}")
    try:
        if not output.write_image(np.ascontiguousarray(pixels, dtype=np.float32)):
            raise RuntimeError(f"Cannot write composite EXR: {path}")
    finally:
        output.close()


def main() -> None:
    args = parse_args()
    spec = json.loads(args.study_spec.read_text(encoding="utf-8"))
    require_equal(spec["documentType"], "BFS_HUMAN_QUADRATURE_REVIEW_SPEC", "study spec type")
    require_equal(spec["status"], "PREREGISTERED_BEFORE_CARRIER_TOOLING_OR_OUTPUTS", "study spec status")
    runtime = spec["runtime"]
    require_equal(bpy.app.version_string, runtime["blenderVersion"], "Blender version")
    require_equal(bpy.app.build_hash.decode("utf-8"), runtime["blenderBuildHash"], "Blender build hash")
    require_equal(ocio.GetCurrentConfig().getName(), "cg-config-v4.0.0_aces-v2.0_ocio-v2.5", "OCIO config name")
    for target in (args.composite_root, args.display_root):
        if target.exists() and any(target.iterdir()):
            raise RuntimeError(f"B34 composite/display output directory must be empty: {target}")
        target.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    transform = spec["displayTransform"]
    scene = bpy.context.scene
    scene.display_settings.display_device = transform["display"]
    scene.view_settings.view_transform = transform["view"]
    scene.view_settings.look = transform["look"]
    scene.view_settings.exposure = transform["exposure"]
    scene.view_settings.gamma = transform["gamma"]
    scene.render.dither_intensity = transform["dither"]
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    observed_transform = {
        "display": scene.display_settings.display_device,
        "view": scene.view_settings.view_transform,
        "look": scene.view_settings.look,
        "exposure": float(scene.view_settings.exposure),
        "gamma": float(scene.view_settings.gamma),
        "dither": float(scene.render.dither_intensity),
        "output": "PNG RGBA 8-bit",
    }
    require_equal(observed_transform, {
        "display": transform["display"], "view": transform["view"], "look": transform["look"],
        "exposure": transform["exposure"], "gamma": transform["gamma"], "dither": transform["dither"],
        "output": transform["output"],
    }, "display transform")

    width, height = spec["renderDesign"]["resolution"]
    frames = range(spec["renderDesign"]["frames"]["start"], spec["renderDesign"]["frames"]["end"] + 1)
    methods: dict[str, Any] = {}
    started = time.perf_counter()
    for method in METHODS:
        cells, weights = method_cells_and_weights(spec, method)
        require_equal(round(sum(weights), 12), 1.0, f"{method} weight sum")
        composite_dir, display_dir = args.composite_root / method, args.display_root / method
        composite_dir.mkdir(); display_dir.mkdir()
        outputs = []
        for frame in frames:
            source_paths = [args.source_root / cell / f"frame-{frame:04d}.exr" for cell in cells]
            if any(not path.is_file() for path in source_paths):
                raise RuntimeError(f"Missing B34 source for {method} frame {frame}")
            weighted = np.zeros((height, width, 4), dtype=np.float64)
            source_bindings = []
            for path, weight in zip(source_paths, weights, strict=True):
                weighted += read_scene_linear(path, width, height).astype(np.float64) * weight
                source_bindings.append({"cell": path.parent.name, "sha256": sha256_file(path), "weight": weight})
            pixels = weighted.astype(np.float32)
            composite_path = composite_dir / f"frame-{frame:04d}.exr"
            display_path = display_dir / f"frame-{frame:04d}.png"
            write_scene_linear(composite_path, pixels)
            image = bpy.data.images.load(str(composite_path), check_existing=False)
            try:
                require_equal(image.colorspace_settings.name, "ACEScg", f"loaded colorspace {method} frame {frame}")
                image.save_render(str(display_path), scene=scene)
            finally:
                bpy.data.images.remove(image)
            if not display_path.is_file():
                raise RuntimeError(f"Display export missing for {method} frame {frame}")
            outputs.append({
                "frame": frame,
                "sources": source_bindings,
                "compositeName": composite_path.name,
                "compositeSha256": sha256_file(composite_path),
                "compositeBytes": composite_path.stat().st_size,
                "displayName": display_path.name,
                "displaySha256": sha256_file(display_path),
                "displayBytes": display_path.stat().st_size,
            })
            print(f"BFS_B34_COMPOSITE_OK {method} {frame}")
        methods[method] = {"cells": cells, "weights": weights, "frameCount": len(outputs), "outputs": outputs}

    report = {
        "documentType": "BFS_B34_SCENE_LINEAR_COMPOSITE_AND_DISPLAY_EXPORT",
        "version": spec["version"],
        "studySpecSha256": sha256_file(args.study_spec),
        "runtime": {
            "blenderVersion": bpy.app.version_string,
            "blenderBuildHash": bpy.app.build_hash.decode("utf-8"),
            "ocioConfigName": ocio.GetCurrentConfig().getName(),
            "openImageIO": oiio.VERSION_STRING,
            "numpy": np.__version__,
        },
        "observedDisplayTransform": observed_transform,
        "compositeDomain": "scene-linear ACEScg float32 RGBA",
        "methods": methods,
        "totalSourceBindings": sum(len(item["sources"]) for method in methods.values() for item in method["outputs"]),
        "totalCompositeFrames": sum(method["frameCount"] for method in methods.values()),
        "totalDisplayFrames": sum(method["frameCount"] for method in methods.values()),
        "totalSeconds": round(time.perf_counter() - started, 6),
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("BFS_B34_COMPOSITE_EXPORT_OK methods=3 frames=432")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B34_COMPOSITE_EXPORT_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
