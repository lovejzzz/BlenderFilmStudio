#!/usr/bin/env python3
"""Render one preregistered B52-D6 Blender 5.2 Displace cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy
import numpy as np


SPEC_SHA256 = "28d3c0b292b89d5d056d5521aececbfb6d88b70971d2b500fbff69d2498703be"
EXPECTED_INPUTS = [
    ["Image", "Image", "NodeSocketColor"],
    ["Displacement", "Displacement", "NodeSocketVector2D"],
    ["Interpolation", "Interpolation", "NodeSocketMenu"],
    ["Extension X", "Extension X", "NodeSocketMenu"],
    ["Extension Y", "Extension Y", "NodeSocketMenu"],
]


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--output-exr", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--probe-only", action="store_true")
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def array_hash(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array, dtype="<f4").tobytes(order="C")).hexdigest()


def source_array(width: int, height: int) -> np.ndarray:
    source = np.zeros((height, width, 4), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            source[y, x] = (x / 64.0, y / 64.0, ((3 * x + 5 * y) % 64) / 64.0, min(1.0, x / 16.0))
    return source


def displacement_array(width: int, height: int, fixture_id: str) -> np.ndarray:
    field = np.zeros((height, width, 2), dtype=np.float32)
    if fixture_id == "ZERO_NEAREST_CLIP":
        return field
    if fixture_id in {"POSITIVE_INTEGER_NEAREST_CLIP", "POSITIVE_INTEGER_NEAREST_EXTEND", "POSITIVE_INTEGER_NEAREST_REPEAT"}:
        field[..., 0], field[..., 1] = 5.0, -3.0
    elif fixture_id == "NEGATIVE_INTEGER_NEAREST_CLIP":
        field[..., 0], field[..., 1] = -7.0, 4.0
    elif fixture_id == "SUBPIXEL_BILINEAR_CLIP":
        field[..., 0], field[..., 1] = 0.5, -0.25
    elif fixture_id == "DESTINATION_STEP_NEAREST_CLIP":
        field[:, width // 2 :, 0] = 3.0
        field[: height // 2, :, 1] = -2.0
        field[height // 2 :, :, 1] = 1.0
    else:
        raise RuntimeError(f"unknown fixture {fixture_id}")
    return field


def make_image(name: str, top_left_pixels: np.ndarray):
    height, width, channels = top_left_pixels.shape
    rgba = top_left_pixels if channels == 4 else np.dstack((top_left_pixels, np.zeros((height, width), dtype=np.float32), np.ones((height, width), dtype=np.float32)))
    image = bpy.data.images.new(name, width=width, height=height, alpha=True, float_buffer=True)
    image.colorspace_settings.name = "Raw"
    image.pixels.foreach_set(np.ascontiguousarray(rgba[::-1], dtype=np.float32).reshape(-1))
    image.update()
    return image


def main() -> None:
    args = arguments()
    started = time.monotonic()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D6 spec hash mismatch")
    fixture = next((item for item in spec["fixtures"] if item["id"] == args.fixture), None)
    if fixture is None:
        raise RuntimeError("fixture outside preregistered matrix")
    if args.probe_only and args.output_exr is not None:
        raise RuntimeError("probe-only must not receive an output")
    if not args.probe_only and args.output_exr is None:
        raise RuntimeError("formal cell requires output EXR")
    for path in [args.report, args.output_exr]:
        if path is not None and path.exists():
            raise RuntimeError(f"refusing to overwrite {path}")
    if sha256_file(Path(os.environ["OCIO"])) != spec["runtime"]["ocio"]["sha256"]:
        raise RuntimeError("OCIO identity mismatch inside Blender")
    if sha256_file(Path(bpy.app.binary_path)) != spec["runtime"]["blenderExecutableSha256"]:
        raise RuntimeError("Blender executable identity mismatch inside Blender")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    width, height = spec["raster"]["resolution"]
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.use_compositing = True
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    scene.render.compositor_device = spec["runtime"]["compositorDevice"]
    scene.render.threads_mode = spec["runtime"]["threadsMode"]
    scene.render.threads = spec["runtime"]["threads"]
    scene.render.image_settings.file_format = spec["blenderMatrix"]["output"]["fileFormat"]
    scene.render.image_settings.color_mode = spec["blenderMatrix"]["output"]["colorMode"]
    scene.render.image_settings.color_depth = spec["blenderMatrix"]["output"]["colorDepth"]
    scene.render.image_settings.exr_codec = spec["blenderMatrix"]["output"]["exrCodec"]

    source_pixels = source_array(width, height)
    displacement_pixels = displacement_array(width, height, args.fixture)
    tree = bpy.data.node_groups.new("BFS_D6_DISPLACE_TREE", "CompositorNodeTree")
    scene.compositing_node_group = tree
    source = tree.nodes.new("CompositorNodeImage")
    source.name = "BFS_D6_SOURCE"
    source.image = make_image("BFS_D6_SOURCE_IMAGE", source_pixels)
    displacement = tree.nodes.new("CompositorNodeImage")
    displacement.name = "BFS_D6_DISPLACEMENT"
    displacement.image = make_image("BFS_D6_DISPLACEMENT_IMAGE", displacement_pixels)
    warp = tree.nodes.new("CompositorNodeDisplace")
    warp.name = "BFS_D6_DISPLACE"
    warp.inputs["Interpolation"].default_value = fixture["interpolation"]
    warp.inputs["Extension X"].default_value = fixture["extensionX"]
    warp.inputs["Extension Y"].default_value = fixture["extensionY"]
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    group_output = tree.nodes.new("NodeGroupOutput")
    group_output.name = "BFS_D6_GROUP_OUTPUT"
    tree.links.new(source.outputs["Image"], warp.inputs["Image"])
    tree.links.new(displacement.outputs["Image"], warp.inputs["Displacement"])
    tree.links.new(warp.outputs["Image"], group_output.inputs["Image"])
    rna = [[item.identifier, item.name, item.bl_idname] for item in warp.inputs]
    links = sorted(f"{link.from_node.name}.{link.from_socket.identifier}->{link.to_node.name}.{link.to_socket.identifier}" for link in tree.links)
    rna_match = rna == EXPECTED_INPUTS and not hasattr(scene, "node_tree") and scene.compositing_node_group == tree
    graph_match = len(tree.nodes) == 4 and links == sorted(spec["blenderMatrix"]["graph"]["links"])
    if not rna_match or not graph_match:
        raise RuntimeError(f"B52-D6 RNA/graph mismatch: {rna} / {links}")

    render_calls = 0
    output_binding = None
    if not args.probe_only:
        camera_data = bpy.data.cameras.new("BFS_D6_CAMERA_DATA")
        camera = bpy.data.objects.new("BFS_D6_CAMERA", camera_data)
        scene.collection.objects.link(camera)
        scene.camera = camera
        args.output_exr.parent.mkdir(parents=True, exist_ok=False)
        scene.render.filepath = str(args.output_exr)
        outcome = bpy.ops.render.render(write_still=True)
        render_calls = 1
        if "FINISHED" not in outcome or not args.output_exr.is_file():
            raise RuntimeError("B52-D6 compositor render failed")
        output_binding = {"uri": str(args.output_exr), "sha256": sha256_file(args.output_exr), "bytes": args.output_exr.stat().st_size}

    body = {
        "schemaVersion": "bfs.deterministicDisplaceCellReport.v0.1",
        "experimentId": spec["experimentId"],
        "classification": "ZERO_RENDER_FROZEN_TOOL_PREFLIGHT" if args.probe_only else "FORMAL_BLENDER_CELL",
        "fixtureId": args.fixture,
        "repeat": args.repeat,
        "pid": os.getpid(),
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii"), "buildPlatform": bpy.app.build_platform.decode("ascii")},
        "runtime": {"engine": scene.render.engine, "compositorDevice": scene.render.compositor_device, "threadsMode": scene.render.threads_mode, "threads": scene.render.threads},
        "arrays": {"sourceFloat32Sha256": array_hash(source_pixels), "displacementFloat32Sha256": array_hash(displacement_pixels)},
        "rna": {"match": rna_match, "sceneHasLegacyNodeTree": hasattr(scene, "node_tree"), "binding": "Scene.compositing_node_group", "displaceInputs": rna},
        "graph": {"match": graph_match, "nodeCount": len(tree.nodes), "links": links},
        "sampling": {"interpolation": str(warp.inputs["Interpolation"].default_value), "extensionX": str(warp.inputs["Extension X"].default_value), "extensionY": str(warp.inputs["Extension Y"].default_value)},
        "output": output_binding,
        "operationCounts": {"blenderProcesses": 1, "renderCalls": render_calls, "cyclesRayRenders": 0, "sourceBlendFilesOpened": 0, "externalAssetsOpened": 0},
        "elapsedSeconds": round(time.monotonic() - started, 6),
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D6_{'PREFLIGHT' if args.probe_only else 'CELL'}_OK fixture={args.fixture} repeat={args.repeat}", flush=True)


if __name__ == "__main__":
    main()
