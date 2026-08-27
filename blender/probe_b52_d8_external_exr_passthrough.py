#!/usr/bin/env python3
"""Development-only Blender 5.2 probe for Raw EXR compositor passthrough."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :]
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    image = bpy.data.images.load(str(args.input), check_existing=False)
    image.colorspace_settings.name = "Raw"

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = image.size[0]
    scene.render.resolution_y = image.size[1]
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

    tree = bpy.data.node_groups.new("BFS_D8_DEV_TREE", "CompositorNodeTree")
    scene.compositing_node_group = tree
    source = tree.nodes.new("CompositorNodeImage")
    source.name = "BFS_D8_DEV_EXTERNAL_SOURCE"
    source.image = image
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    output = tree.nodes.new("NodeGroupOutput")
    output.name = "BFS_D8_DEV_GROUP_OUTPUT"
    tree.links.new(source.outputs["Image"], output.inputs["Image"])

    camera_data = bpy.data.cameras.new("BFS_D8_DEV_CAMERA_DATA")
    camera = bpy.data.objects.new("BFS_D8_DEV_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(args.output)
    result = bpy.ops.render.render(write_still=True)
    if "FINISHED" not in result or not args.output.is_file():
        raise RuntimeError("development passthrough render failed")

    report = {
        "classification": "DEVELOPMENT_ONLY_NOT_FORMAL_EVIDENCE",
        "blenderVersion": bpy.app.version_string,
        "blenderBuildHash": bpy.app.build_hash.decode("utf-8"),
        "inputColorspace": image.colorspace_settings.name,
        "imageSize": list(image.size),
        "graph": [
            "BFS_D8_DEV_EXTERNAL_SOURCE.Image->BFS_D8_DEV_GROUP_OUTPUT.Socket_0"
        ],
        "renderCalls": 1,
        "cyclesRayRenders": 0,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("BFS_B52_D8_DEVELOPMENT_PASSTHROUGH_OK")


if __name__ == "__main__":
    main()
