#!/usr/bin/env python3
"""Pass one B52-D12 Raw reconstruction EXR through Blender 5.2 compositor."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy


SPEC_SHA256 = "dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2"
EXPECTED_LINK = "BFS_D12_EXTERNAL_SOURCE.Image->BFS_D12_GROUP_OUTPUT.Socket_0"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--source-repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--bridge-repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--probe-only", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    fixture = next((item for item in spec["fixtures"] if item["id"] == args.fixture), None)
    if sha(args.spec) != SPEC_SHA256 or fixture is None:
        raise RuntimeError("B52-D12 spec or fixture identity mismatch")
    if sha(Path(bpy.app.binary_path)) != spec["runtime"]["blender"]["sha256"] or sha(Path(os.environ["OCIO"])) != spec["runtime"]["ocio"]["sha256"]:
        raise RuntimeError("Blender or OCIO identity mismatch")
    if (args.probe_only and args.output) or (not args.probe_only and not args.output) or args.report.exists() or (args.output and args.output.exists()):
        raise RuntimeError("D12 bridge output mismatch")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    image = bpy.data.images.load(str(args.input.resolve()), check_existing=False)
    image.colorspace_settings.name = "Raw"
    scene = bpy.context.scene
    width, height = spec["scene"]["resolution"]
    if list(image.size) != [width, height]:
        raise RuntimeError("D12 bridge input size mismatch")
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = width, height
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
    tree = bpy.data.node_groups.new("BFS_D12_TREE", "CompositorNodeTree")
    scene.compositing_node_group = tree
    source = tree.nodes.new("CompositorNodeImage")
    source.name = "BFS_D12_EXTERNAL_SOURCE"
    source.image = image
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    output = tree.nodes.new("NodeGroupOutput")
    output.name = "BFS_D12_GROUP_OUTPUT"
    tree.links.new(source.outputs["Image"], output.inputs["Image"])
    links = sorted(f"{link.from_node.name}.{link.from_socket.identifier}->{link.to_node.name}.{link.to_socket.identifier}" for link in tree.links)
    graph_match = links == [EXPECTED_LINK] and len(tree.nodes) == 2 and not hasattr(scene, "node_tree")
    rna = {"nodeType": source.bl_idname, "outputIdentifier": source.outputs["Image"].identifier, "colorspace": image.colorspace_settings.name, "match": source.bl_idname == "CompositorNodeImage" and source.outputs["Image"].identifier == "Image" and image.colorspace_settings.name == "Raw"}
    renders, output_record = 0, None
    if not args.probe_only:
        camera_data = bpy.data.cameras.new("BFS_D12_BRIDGE_CAMERA_DATA")
        camera = bpy.data.objects.new("BFS_D12_BRIDGE_CAMERA", camera_data)
        scene.collection.objects.link(camera)
        scene.camera = camera
        args.output.parent.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(args.output)
        outcome = bpy.ops.render.render(write_still=True)
        renders = 1
        if "FINISHED" not in outcome or not args.output.is_file():
            raise RuntimeError("D12 bridge render failed")
        output_record = {"uri": str(args.output), "sha256": sha(args.output), "bytes": args.output.stat().st_size}
    body = {
        "schemaVersion": "bfs.blenderProjectiveSubpixelBridgeReport.v0.1",
        "experimentId": spec["experimentId"], "fixtureId": args.fixture, "sourceRepeat": args.source_repeat, "bridgeRepeat": args.bridge_repeat, "pid": os.getpid(),
        "classification": "ZERO_RENDER_FROZEN_TOOL_PREFLIGHT" if args.probe_only else "FORMAL_BLENDER_BRIDGE_CELL",
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode(), "executableSha256": sha(Path(bpy.app.binary_path))},
        "input": {"uri": str(args.input), "sha256": sha(args.input), "bytes": args.input.stat().st_size},
        "rna": rna, "graph": {"links": links, "nodeCount": len(tree.nodes), "match": graph_match}, "output": output_record,
        "operationCounts": {"bridgeBlenderProcesses": 1, "bridgeCompositorRenders": renders, "cyclesRayRenders": 0, "sourceBlendFilesOpened": 0, "generatedExternalExrAssetsOpened": 1},
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({**body, "reportHash": canonical_hash(body)}, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D12_{'PREFLIGHT' if args.probe_only else 'BRIDGE'}_OK fixture={args.fixture} sourceRepeat={args.source_repeat} bridgeRepeat={args.bridge_repeat}")
    if not graph_match or not rna["match"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
