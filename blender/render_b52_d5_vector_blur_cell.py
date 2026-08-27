#!/usr/bin/env python3
"""Evaluate one preregistered B52-D5 Blender 5.2 Vector Blur cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy


SPEC_SHA256 = "5c2e6564650d6ab6d98f6bb7d91da4304c1cfeece4601871ed74fe5fd5521e01"
EXPECTED_IMAGE_OUTPUTS = ["Combined", "Alpha", "Depth", "Normal", "Vector", "CryptoObject00", "CryptoObject01", "CryptoObject02", "Debug Sample Count"]
EXPECTED_INPUTS = [
    {"identifier": "Image", "name": "Image", "type": "RGBA"},
    {"identifier": "Speed", "name": "Speed", "type": "VECTOR"},
    {"identifier": "Z", "name": "Depth", "type": "VALUE"},
    {"identifier": "Samples", "name": "Samples", "type": "INT"},
    {"identifier": "Shutter", "name": "Shutter", "type": "VALUE"},
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--source-exr", type=Path, required=True)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--shutter", type=float, required=True)
    parser.add_argument("--repeat", type=int, required=True)
    parser.add_argument("--output-exr", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def socket_contract(node) -> list[dict]:
    return [{"identifier": socket.identifier, "name": socket.name, "type": socket.type} for socket in node.inputs]


def main() -> None:
    args = arguments()
    started = time.monotonic()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D5 spec hash mismatch")
    if args.fixture not in [item["id"] for item in spec["fixtures"]] or args.shutter not in spec["compositor"]["shutters"] or args.repeat not in (1, 2):
        raise RuntimeError("cell outside preregistered compositor matrix")
    if args.output_exr.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite B52-D5 compositor output")
    if sha256_file(args.source_exr) != args.expected_source_sha:
        raise RuntimeError("source EXR identity mismatch inside Blender")
    if sha256_file(Path(os.environ["OCIO"])) != spec["runtime"]["ocio"]["sha256"]:
        raise RuntimeError("OCIO identity mismatch inside Blender")
    if sha256_file(Path(bpy.app.binary_path)) != spec["runtime"]["blenderExecutableSha256"]:
        raise RuntimeError("Blender executable identity mismatch inside Blender")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    compositor = spec["compositor"]
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = compositor["output"]["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.use_compositing = True
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    scene.render.compositor_device = compositor["device"]
    scene.render.threads_mode = compositor["threadsMode"]
    scene.render.threads = compositor["threads"]
    scene.render.image_settings.file_format = compositor["output"]["fileFormat"]
    scene.render.image_settings.color_mode = compositor["output"]["colorMode"]
    scene.render.image_settings.color_depth = compositor["output"]["colorDepth"]
    scene.render.image_settings.exr_codec = compositor["output"]["exrCodec"]
    scene.render.filepath = str(args.output_exr)

    camera_data = bpy.data.cameras.new("BFS_D5_COMPOSITOR_CAMERA_DATA")
    camera = bpy.data.objects.new("BFS_D5_COMPOSITOR_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, 0.0, 10.0)
    scene.camera = camera

    tree = bpy.data.node_groups.new("BFS_D5_VECTOR_BLUR", "CompositorNodeTree")
    scene.compositing_node_group = tree
    source_node = tree.nodes.new("CompositorNodeImage")
    source_node.name = "BFS_D5_SOURCE"
    source_node.image = bpy.data.images.load(str(args.source_exr.resolve()), check_existing=False)
    vector_blur = tree.nodes.new("CompositorNodeVecBlur")
    vector_blur.name = "BFS_D5_VECTOR_BLUR"
    vector_blur.inputs["Samples"].default_value = compositor["samples"]
    vector_blur.inputs["Shutter"].default_value = args.shutter
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    group_output = tree.nodes.new("NodeGroupOutput")
    group_output.name = "BFS_D5_GROUP_OUTPUT"
    group_socket = group_output.inputs["Image"]
    roster = [socket.identifier for socket in source_node.outputs]
    inputs = socket_contract(vector_blur)
    rna_match = roster == EXPECTED_IMAGE_OUTPUTS and inputs == EXPECTED_INPUTS and group_socket.identifier == "Socket_0" and group_socket.name == "Image" and not hasattr(scene, "node_tree")
    if not rna_match:
        raise RuntimeError(f"Blender 5.2 compositor RNA mismatch: {roster} / {inputs}")
    tree.links.new(source_node.outputs["Combined"], vector_blur.inputs["Image"])
    tree.links.new(source_node.outputs["Vector"], vector_blur.inputs["Speed"])
    tree.links.new(source_node.outputs["Depth"], vector_blur.inputs["Z"])
    tree.links.new(vector_blur.outputs["Image"], group_socket)
    links = sorted(f"{link.from_node.name}.{link.from_socket.identifier}->{link.to_node.name}.{link.to_socket.identifier}" for link in tree.links)
    expected_links = sorted([
        "BFS_D5_SOURCE.Combined->BFS_D5_VECTOR_BLUR.Image",
        "BFS_D5_SOURCE.Vector->BFS_D5_VECTOR_BLUR.Speed",
        "BFS_D5_SOURCE.Depth->BFS_D5_VECTOR_BLUR.Z",
        "BFS_D5_VECTOR_BLUR.Image->BFS_D5_GROUP_OUTPUT.Socket_0",
    ])
    graph_match = links == expected_links and len(tree.nodes) == 3
    if not graph_match:
        raise RuntimeError(f"B52-D5 compositor graph mismatch: {links}")

    args.output_exr.parent.mkdir(parents=True, exist_ok=False)
    outcome = bpy.ops.render.render(write_still=True)
    if "FINISHED" not in outcome or not args.output_exr.is_file():
        raise RuntimeError("B52-D5 compositor render failed")
    source_post = sha256_file(args.source_exr)
    if source_post != args.expected_source_sha:
        raise RuntimeError("source EXR changed during compositor execution")
    body = {
        "schemaVersion": "bfs.controlledMotionVectorBlurCellReport.v0.1",
        "experimentId": spec["experimentId"], "fixtureId": args.fixture, "shutter": args.shutter,
        "repeat": args.repeat, "pid": os.getpid(),
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii"), "buildPlatform": bpy.app.build_platform.decode("ascii")},
        "runtime": {"engine": scene.render.engine, "compositorDevice": scene.render.compositor_device, "threadsMode": scene.render.threads_mode, "threads": scene.render.threads},
        "input": {"uri": str(args.source_exr), "sha256": args.expected_source_sha, "imagePass": "Combined", "speedPass": "Vector", "depthPass": "Depth"},
        "rna": {"match": rna_match, "imageOutputs": roster, "vectorBlurInputs": inputs, "groupOutput": {"identifier": group_socket.identifier, "name": group_socket.name}},
        "graph": {"match": graph_match, "links": links, "nodeCount": len(tree.nodes)},
        "vectorBlur": {"Samples": int(vector_blur.inputs["Samples"].default_value), "Shutter": float(vector_blur.inputs["Shutter"].default_value)},
        "output": {"uri": str(args.output_exr), "sha256": sha256_file(args.output_exr), "bytes": args.output_exr.stat().st_size},
        "sourcePostSha256": source_post,
        "operationCounts": {"blenderProcesses": 1, "blenderRenderCalls": 1, "cyclesRayRenders": 0, "sourceBlendFilesOpened": 0, "externalAssetsOpened": 0},
        "elapsedSeconds": round(time.monotonic() - started, 6),
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D5_COMPOSITOR_OK fixture={args.fixture} shutter={args.shutter} repeat={args.repeat} output={body['output']['sha256']}", flush=True)


if __name__ == "__main__":
    main()
