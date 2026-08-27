#!/usr/bin/env python3
"""Exploratory Blender 5.2 compositor Displace semantics probe.

This is development evidence only. It enumerates a tiny synthetic raster so the
sign, decoded Y direction, interpolation and extension behavior can be frozen
before the B52-D6 confirmatory tool is implemented.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
import numpy as np
import OpenImageIO as oiio


WIDTH = 8
HEIGHT = 6
CASES = [
    ("zero_nearest_clip", (0.0, 0.0), "Nearest", "Clip", "Clip"),
    ("plus_x2_nearest_clip", (2.0, 0.0), "Nearest", "Clip", "Clip"),
    ("plus_y1_nearest_clip", (0.0, 1.0), "Nearest", "Clip", "Clip"),
    ("plus_x_half_bilinear_clip", (0.5, 0.0), "Bilinear", "Clip", "Clip"),
    ("step_x_nearest_clip", (0.0, 0.0), "Nearest", "Clip", "Clip"),
    ("plus_x2_nearest_extend", (2.0, 0.0), "Nearest", "Extend", "Clip"),
    ("plus_x2_nearest_repeat", (2.0, 0.0), "Nearest", "Repeat", "Clip"),
]


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rgba(path: Path) -> np.ndarray:
    source = oiio.ImageInput.open(str(path))
    if source is None:
        raise RuntimeError(f"cannot open {path}: {oiio.geterror()}")
    spec = source.spec()
    pixels = np.asarray(source.read_image(0, 0, 0, 4, oiio.FLOAT), dtype=np.float32)
    source.close()
    return pixels.reshape(spec.height, spec.width, 4)


def shift_reference(image: np.ndarray, dx: int, dy: int, extension_x: str = "Clip") -> np.ndarray:
    height, width, _ = image.shape
    output = np.zeros_like(image)
    for y in range(height):
        for x in range(width):
            sx = x - dx
            sy = y - dy
            if extension_x == "Extend":
                sx = min(max(sx, 0), width - 1)
            elif extension_x == "Repeat":
                sx %= width
            if 0 <= sx < width and 0 <= sy < height:
                output[y, x] = image[sy, sx]
    return output


def max_abs(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.max(np.abs(left.astype(np.float64) - right.astype(np.float64))))


def make_image(name: str, pixels: np.ndarray):
    image = bpy.data.images.new(name, width=WIDTH, height=HEIGHT, alpha=True, float_buffer=True)
    image.colorspace_settings.name = "Raw"
    image.pixels.foreach_set(pixels.astype(np.float32).reshape(-1))
    image.update()
    return image


def main() -> None:
    args = arguments()
    if args.output_dir.exists():
        raise RuntimeError("refusing to overwrite exploratory output directory")
    args.output_dir.mkdir(parents=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.use_compositing = True
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    scene.render.compositor_device = "CPU"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 1
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"

    camera_data = bpy.data.cameras.new("BFS_D6_PROBE_CAMERA_DATA")
    camera = bpy.data.objects.new("BFS_D6_PROBE_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    source_pixels = np.zeros((HEIGHT, WIDTH, 4), dtype=np.float32)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            source_pixels[y, x] = (x / 8.0, y / 8.0, ((x + 2 * y) % 8) / 8.0, min(1.0, x / 4.0))
    displacement_pixels = np.zeros((HEIGHT, WIDTH, 4), dtype=np.float32)
    displacement_pixels[..., 3] = 1.0
    source_image = make_image("BFS_D6_SOURCE", source_pixels)
    displacement_image = make_image("BFS_D6_DISPLACEMENT", displacement_pixels)

    tree = bpy.data.node_groups.new("BFS_D6_DISPLACE_PROBE", "CompositorNodeTree")
    scene.compositing_node_group = tree
    source = tree.nodes.new("CompositorNodeImage")
    source.name = "BFS_D6_SOURCE"
    source.image = source_image
    displacement = tree.nodes.new("CompositorNodeImage")
    displacement.name = "BFS_D6_DISPLACEMENT"
    displacement.image = displacement_image
    warp = tree.nodes.new("CompositorNodeDisplace")
    warp.name = "BFS_D6_DISPLACE"
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    group_output = tree.nodes.new("NodeGroupOutput")
    group_output.name = "BFS_D6_GROUP_OUTPUT"
    tree.links.new(source.outputs["Image"], warp.inputs["Image"])
    tree.links.new(displacement.outputs["Image"], warp.inputs["Displacement"])
    tree.links.new(warp.outputs["Image"], group_output.inputs["Image"])

    records = []
    for case_id, vector, interpolation, extension_x, extension_y in CASES:
        displacement_pixels[..., 0:3] = 0.0
        displacement_pixels[..., 0] = vector[0]
        displacement_pixels[..., 1] = vector[1]
        if case_id == "step_x_nearest_clip":
            displacement_pixels[:, WIDTH // 2 :, 0] = 1.0
        displacement_image.pixels.foreach_set(displacement_pixels.reshape(-1))
        displacement_image.update()
        warp.inputs["Interpolation"].default_value = interpolation
        warp.inputs["Extension X"].default_value = extension_x
        warp.inputs["Extension Y"].default_value = extension_y
        output_path = args.output_dir / f"{case_id}.exr"
        scene.render.filepath = str(output_path)
        outcome = bpy.ops.render.render(write_still=True)
        if "FINISHED" not in outcome or not output_path.is_file():
            raise RuntimeError(f"render failed for {case_id}")
        records.append({
            "caseId": case_id,
            "vector": list(vector),
            "interpolation": interpolation,
            "extensionX": extension_x,
            "extensionY": extension_y,
            "sha256": sha256_file(output_path),
            "bytes": output_path.stat().st_size,
        })

    decoded = {record["caseId"]: read_rgba(args.output_dir / f"{record['caseId']}.exr") for record in records}
    zero = decoded["zero_nearest_clip"]
    comparisons = {
        "zeroVsAuthoredSource": max_abs(zero, source_pixels[::-1]),
        "plusX2_shiftRight": max_abs(decoded["plus_x2_nearest_clip"], shift_reference(zero, 2, 0)),
        "plusX2_shiftLeft": max_abs(decoded["plus_x2_nearest_clip"], shift_reference(zero, -2, 0)),
        "plusY1_shiftDownDecoded": max_abs(decoded["plus_y1_nearest_clip"], shift_reference(zero, 0, 1)),
        "plusY1_shiftUpDecoded": max_abs(decoded["plus_y1_nearest_clip"], shift_reference(zero, 0, -1)),
        "plusX2Extend_shiftRight": max_abs(decoded["plus_x2_nearest_extend"], shift_reference(zero, 2, 0, "Extend")),
        "plusX2Repeat_shiftRight": max_abs(decoded["plus_x2_nearest_repeat"], shift_reference(zero, 2, 0, "Repeat")),
    }
    expected_half = 0.5 * shift_reference(zero, 0, 0) + 0.5 * shift_reference(zero, 1, 0)
    comparisons["plusXHalfBilinear_shiftRight"] = max_abs(decoded["plus_x_half_bilinear_clip"], expected_half)
    expected_step = zero.copy()
    expected_step[:, WIDTH // 2 :] = shift_reference(zero, 1, 0)[:, WIDTH // 2 :]
    comparisons["stepXOutputSampled"] = max_abs(decoded["step_x_nearest_clip"], expected_step)

    report = {
        "schemaVersion": "bfs.b52D6DisplaceExploratoryProbe.v0.1",
        "classification": "EXPLORATORY_NOT_FORMAL_NOT_PROMOTABLE",
        "blender": {
            "version": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode("ascii"),
            "binary": bpy.app.binary_path,
            "pid": os.getpid(),
        },
        "resolution": [WIDTH, HEIGHT],
        "cases": records,
        "comparisons": comparisons,
        "rna": {
            "sceneHasLegacyNodeTree": hasattr(scene, "node_tree"),
            "binding": "Scene.compositing_node_group",
            "displaceInputs": [
                {"identifier": socket.identifier, "name": socket.name, "type": socket.bl_idname, "default": str(socket.default_value)}
                for socket in warp.inputs
            ],
        },
        "operationCounts": {"blenderProcesses": 1, "renderCalls": len(CASES), "cyclesRayRenders": 0},
    }
    (args.output_dir / "observation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    print("BFS_B52_D6_EXPLORATORY_OK " + json.dumps(comparisons, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
