#!/usr/bin/env python3
"""Evaluate one frozen Blender 5.2 Vector Blur compositor cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy


SPEC_SHA256 = "e8635a1507eb5a5e8bfd950dc02fc4630a7202fd9af14b5510a991359f2e439f"
EXPECTED_IMAGE_OUTPUTS = [
    "Combined",
    "Alpha",
    "Depth",
    "Normal",
    "Vector",
    "CryptoObject00",
    "CryptoObject01",
    "CryptoObject02",
    "Debug Sample Count",
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
    parser.add_argument("--baseline-exr", type=Path, required=True)
    parser.add_argument("--speed-exr", type=Path, required=True)
    parser.add_argument("--expected-baseline-sha", required=True)
    parser.add_argument("--expected-speed-sha", required=True)
    parser.add_argument("--output-exr", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--cell-id", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--repeat", type=int, required=True)
    return parser.parse_args(argv)


def socket_contract(node) -> list[dict]:
    return [{"identifier": socket.identifier, "name": socket.name, "type": socket.type} for socket in node.inputs]


def main() -> None:
    args = arguments()
    started = time.monotonic()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D4 spec hash mismatch")
    if args.variant not in spec["inputs"]["variants"]:
        raise RuntimeError("variant is outside frozen matrix")
    expected_profiles = [spec["inputs"]["baselineProfile"], *spec["inputs"]["candidateProfiles"]]
    if args.profile not in expected_profiles or args.repeat not in (1, 2):
        raise RuntimeError("profile or repeat is outside frozen matrix")
    if args.output_exr.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite B52-D4 cell output")
    baseline_sha = sha256_file(args.baseline_exr)
    speed_sha = sha256_file(args.speed_exr)
    if baseline_sha != args.expected_baseline_sha or speed_sha != args.expected_speed_sha:
        raise RuntimeError("source EXR identity mismatch inside Blender")
    ocio_path = Path(os.environ["OCIO"])
    if sha256_file(ocio_path) != spec["runtime"]["ocio"]["sha256"]:
        raise RuntimeError("OCIO identity mismatch inside Blender")
    executable = Path(bpy.app.binary_path)
    if sha256_file(executable) != spec["runtime"]["blenderExecutableSha256"]:
        raise RuntimeError("Blender executable identity mismatch inside Blender")
    if bpy.app.version_string != spec["runtime"]["version"] or bpy.app.build_hash.decode("ascii") != spec["runtime"]["buildHash"]:
        raise RuntimeError("Blender runtime version mismatch")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    shell = spec["compositorMatrix"]["renderShell"]
    scene.render.engine = shell["engine"]
    scene.render.resolution_x, scene.render.resolution_y = shell["resolution"]
    scene.render.resolution_percentage = shell["resolutionPercentage"]
    scene.render.pixel_aspect_x, scene.render.pixel_aspect_y = shell["pixelAspect"]
    scene.render.film_transparent = shell["filmTransparent"]
    scene.render.use_compositing = shell["renderUseCompositing"]
    scene.render.compositor_device = spec["runtime"]["compositorDevice"]
    scene.render.threads_mode = spec["runtime"]["threadsMode"]
    scene.render.threads = spec["runtime"]["threads"]
    scene.render.image_settings.file_format = shell["output"]["fileFormat"]
    scene.render.image_settings.color_mode = shell["output"]["colorMode"]
    scene.render.image_settings.color_depth = shell["output"]["colorDepth"]
    scene.render.image_settings.exr_codec = shell["output"]["exrCodec"]
    scene.render.use_file_extension = True
    scene.render.filepath = str(args.output_exr)

    camera_data = bpy.data.cameras.new("BFS_D4_CAMERA")
    camera = bpy.data.objects.new("BFS_D4_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, 0.0, 10.0)
    scene.camera = camera

    tree = bpy.data.node_groups.new("BFS_D4_VECTOR_BLUR", "CompositorNodeTree")
    scene.compositing_node_group = tree
    baseline_node = tree.nodes.new("CompositorNodeImage")
    baseline_node.name = "BFS_BASELINE"
    baseline_node.image = bpy.data.images.load(str(args.baseline_exr.resolve()), check_existing=False)
    speed_node = tree.nodes.new("CompositorNodeImage")
    speed_node.name = "BFS_SPEED_SOURCE"
    speed_node.image = bpy.data.images.load(str(args.speed_exr.resolve()), check_existing=False)
    vector_blur = tree.nodes.new("CompositorNodeVecBlur")
    vector_blur.name = "BFS_VECTOR_BLUR"
    vector_blur.inputs["Samples"].default_value = spec["compositorMatrix"]["nodeGraph"]["vectorBlurInputs"]["Samples"]
    vector_blur.inputs["Shutter"].default_value = spec["compositorMatrix"]["nodeGraph"]["vectorBlurInputs"]["Shutter"]
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    group_output = tree.nodes.new("NodeGroupOutput")
    group_output.name = "BFS_GROUP_OUTPUT"
    group_output_socket = group_output.inputs["Image"]
    if group_output_socket.identifier != "Socket_0" or group_output_socket.name != "Image":
        raise RuntimeError(
            "Blender 5.2 Group Output interface mismatch: "
            f"identifier={group_output_socket.identifier} name={group_output_socket.name}"
        )

    baseline_roster = [socket.identifier for socket in baseline_node.outputs]
    speed_roster = [socket.identifier for socket in speed_node.outputs]
    if baseline_roster != EXPECTED_IMAGE_OUTPUTS or speed_roster != EXPECTED_IMAGE_OUTPUTS:
        raise RuntimeError(f"multilayer Image socket roster mismatch: {baseline_roster} / {speed_roster}")
    expected_vec_inputs = [
        {"identifier": "Image", "name": "Image", "type": "RGBA"},
        {"identifier": "Speed", "name": "Speed", "type": "VECTOR"},
        {"identifier": "Z", "name": "Depth", "type": "VALUE"},
        {"identifier": "Samples", "name": "Samples", "type": "INT"},
        {"identifier": "Shutter", "name": "Shutter", "type": "VALUE"},
    ]
    observed_vec_inputs = socket_contract(vector_blur)
    rna_match = observed_vec_inputs == expected_vec_inputs and not hasattr(scene, "node_tree")
    if not rna_match:
        raise RuntimeError(f"Blender 5.2 Vector Blur RNA mismatch: {observed_vec_inputs}")
    tree.links.new(baseline_node.outputs["Combined"], vector_blur.inputs["Image"])
    tree.links.new(speed_node.outputs["Vector"], vector_blur.inputs["Speed"])
    tree.links.new(baseline_node.outputs["Depth"], vector_blur.inputs["Z"])
    tree.links.new(vector_blur.outputs["Image"], group_output_socket)
    observed_links = sorted(
        f"{link.from_node.name}.{link.from_socket.identifier}->{link.to_node.name}.{link.to_socket.identifier}"
        for link in tree.links
    )
    expected_links = sorted([
        "BFS_BASELINE.Combined->BFS_VECTOR_BLUR.Image",
        "BFS_SPEED_SOURCE.Vector->BFS_VECTOR_BLUR.Speed",
        "BFS_BASELINE.Depth->BFS_VECTOR_BLUR.Z",
        "BFS_VECTOR_BLUR.Image->BFS_GROUP_OUTPUT.Socket_0",
    ])
    graph_match = observed_links == expected_links and len(tree.nodes) == 4
    if not graph_match:
        raise RuntimeError(f"compositor graph mismatch: {observed_links}")

    args.output_exr.parent.mkdir(parents=True, exist_ok=False)
    bpy.ops.render.render(write_still=True)
    if not args.output_exr.is_file():
        raise RuntimeError(f"Vector Blur output absent: {args.output_exr}")
    source_post = {"baselineSha256": sha256_file(args.baseline_exr), "speedSha256": sha256_file(args.speed_exr)}
    if source_post != {"baselineSha256": baseline_sha, "speedSha256": speed_sha}:
        raise RuntimeError("source EXR changed during compositor execution")

    body = {
        "schemaVersion": "bfs.adaptiveVectorBlurCellReport.v0.1",
        "experimentId": spec["experimentId"],
        "cellId": args.cell_id,
        "variantId": args.variant,
        "profileId": args.profile,
        "repeat": args.repeat,
        "pid": os.getpid(),
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii"), "buildPlatform": bpy.app.build_platform.decode("ascii")},
        "runtime": {"engine": scene.render.engine, "compositorDevice": scene.render.compositor_device, "threadsMode": scene.render.threads_mode, "threads": scene.render.threads},
        "inputs": {
            "baseline": {"uri": str(args.baseline_exr), "sha256": baseline_sha},
            "speedSource": {"uri": str(args.speed_exr), "sha256": speed_sha},
            "imagePass": "Combined",
            "depthPass": "Depth",
            "speedPass": "Vector"
        },
        "rna": {"inputs": observed_vec_inputs, "match": rna_match},
        "graph": {"links": observed_links, "match": graph_match, "nodeCount": len(tree.nodes)},
        "vectorBlur": {"Samples": int(vector_blur.inputs["Samples"].default_value), "Shutter": float(vector_blur.inputs["Shutter"].default_value)},
        "output": {"uri": str(args.output_exr), "sha256": sha256_file(args.output_exr), "bytes": args.output_exr.stat().st_size},
        "sourcePost": source_post,
        "operationCounts": {"blenderProcesses": 1, "blenderRenderCalls": 1, "cyclesRayRenders": 0, "sourceBlendFilesOpened": 0, "sourceBlendFilesModified": 0, "parentExrsModified": 0},
        "elapsedSeconds": round(time.monotonic() - started, 6),
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D4_CELL_OK cell={args.cell_id} output={report['output']['sha256']} elapsed={body['elapsedSeconds']}", flush=True)


if __name__ == "__main__":
    main()
