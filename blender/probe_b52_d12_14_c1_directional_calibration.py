#!/usr/bin/env python3
"""Zero-render Blender 5.2 projection probe for one B52-D12.14-C1 target."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


SPEC_SHA256 = "fd3fe2808346c49a87183b3ed215b07abcbaf4058df13d055cc893b482ae30f5"
TARGETS = (
    "TOP_MISSING_BOTTOM_AVAILABLE",
    "BOTTOM_MISSING_TOP_AVAILABLE",
    "NEITHER_HORIZONTAL_AVAILABLE",
)


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def parse_args() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--oracle-report", type=Path, required=True)
    parser.add_argument("--target", choices=TARGETS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(raw)


def pixel_to_world(pixel_x: float, pixel_y: float, width: int, height: int, plane_z: float, camera_spec: dict) -> tuple[float, float, float]:
    depth = float(camera_spec["location"][2]) - plane_z
    sensor_width = float(camera_spec["sensorWidthMm"])
    sensor_height = sensor_width * height / width
    lens = float(camera_spec["lensMm"])
    u = (pixel_x + 0.5) / width
    v_bottom = 1.0 - (pixel_y + 0.5) / height
    world_x = (u - 0.5) * depth * sensor_width / lens
    world_y = (v_bottom - 0.5) * depth * sensor_height / lens
    return world_x, world_y, plane_z


def scalar_project(point: tuple[float, float, float], width: int, height: int, camera_spec: dict) -> tuple[float, float]:
    camera_x, camera_y, camera_z = (float(value) for value in camera_spec["location"])
    relative_x, relative_y, relative_z = point[0] - camera_x, point[1] - camera_y, point[2] - camera_z
    if relative_z >= 0:
        raise RuntimeError("D12.14-C1 point is not in front of the camera")
    sensor_width = float(camera_spec["sensorWidthMm"])
    sensor_height = sensor_width * height / width
    lens = float(camera_spec["lensMm"])
    u = 0.5 + lens * relative_x / (-relative_z * sensor_width)
    v_bottom = 0.5 + lens * relative_y / (-relative_z * sensor_height)
    return u * width - 0.5, (1.0 - v_bottom) * height - 0.5


def make_plane(name: str, corners: list[tuple[float, float, float]]) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(corners, [], [(0, 1, 2, 3)])
    mesh.update()
    owner = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(owner)
    return owner


def projected_corners(scene: bpy.types.Scene, camera: bpy.types.Object, corners: list[tuple[float, float, float]], width: int, height: int) -> list[list[float]]:
    rows = []
    for corner in corners:
        ndc = world_to_camera_view(scene, camera, Vector(corner))
        rows.append([float(ndc.x) * width - 0.5, (1.0 - float(ndc.y)) * height - 0.5])
    return rows


def main() -> None:
    cli = parse_args()
    if sha_file(cli.spec) != SPEC_SHA256 or cli.output.exists():
        raise RuntimeError("D12.14-C1 probe spec identity or output freshness failure")
    spec = json.loads(cli.spec.read_text())
    runtime = spec["runtime"]["blender"]
    if sha_file(Path(bpy.app.binary_path)) != runtime["sha256"]:
        raise RuntimeError("D12.14-C1 Blender executable identity mismatch")
    if bpy.app.version_string != runtime["version"] or bpy.app.build_hash.decode() != runtime["buildHash"]:
        raise RuntimeError("D12.14-C1 Blender version identity mismatch")
    oracle = json.loads(cli.oracle_report.read_text())
    selected = next(row for row in oracle["selected"] if row["target"] == cli.target)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"BFS_D1214C1_{cli.target}"
    selection_present = selected["candidateId"] is not None
    rows = []
    maximum_blender_error = 0.0
    maximum_scalar_error = 0.0
    if selection_present:
        width, height = (int(value) for value in selected["resolution"])
        scene.render.resolution_x = width
        scene.render.resolution_y = height
        scene.render.resolution_percentage = 100
        scene.render.pixel_aspect_x = 1.0
        scene.render.pixel_aspect_y = 1.0
        camera_spec = spec["blenderProjectionProbe"]["camera"]
        camera_data = bpy.data.cameras.new("BFS_D1214C1_CAMERA_DATA")
        camera_data.type = camera_spec["type"]
        camera_data.lens = camera_spec["lensMm"]
        camera_data.sensor_width = camera_spec["sensorWidthMm"]
        camera_data.sensor_fit = camera_spec["sensorFit"]
        camera_data.clip_start = camera_spec["clipStart"]
        camera_data.clip_end = camera_spec["clipEnd"]
        camera = bpy.data.objects.new("BFS_D1214C1_CAMERA", camera_data)
        camera.location = tuple(camera_spec["location"])
        camera.rotation_mode = "XYZ"
        camera.rotation_euler = tuple(camera_spec["rotationEuler"])
        scene.collection.objects.link(camera)
        scene.camera = camera
        bpy.context.view_layer.update()
        for frame, rectangle_name in ((0, "previousRect"), (1, "currentRect")):
            rectangle = [float(value) for value in selected[rectangle_name]]
            plane_z = float(spec["blenderProjectionProbe"]["planeDepthByFrame"][str(frame)])
            expected = [
                [rectangle[0], rectangle[1]],
                [rectangle[2], rectangle[1]],
                [rectangle[2], rectangle[3]],
                [rectangle[0], rectangle[3]],
            ]
            corners = [pixel_to_world(x, y, width, height, plane_z, camera_spec) for x, y in expected]
            owner = make_plane(f"BFS_D1214C1_{cli.target}_F{frame}", corners)
            blender_projection = projected_corners(scene, camera, corners, width, height)
            scalar_projection = [list(scalar_project(corner, width, height, camera_spec)) for corner in corners]
            blender_error = max(abs(actual[channel] - expected_row[channel]) for actual, expected_row in zip(blender_projection, expected) for channel in (0, 1))
            scalar_error = max(abs(actual[channel] - expected_row[channel]) for actual, expected_row in zip(scalar_projection, expected) for channel in (0, 1))
            maximum_blender_error = max(maximum_blender_error, blender_error)
            maximum_scalar_error = max(maximum_scalar_error, scalar_error)
            rows.append({
                "frame": frame,
                "rectangleName": rectangle_name,
                "planeZ": plane_z,
                "expectedProjectedCorners": expected,
                "worldCorners": [list(corner) for corner in corners],
                "blenderProjectedCorners": blender_projection,
                "scalarProjectedCorners": scalar_projection,
                "blenderMaximumAbsoluteError": blender_error,
                "scalarMaximumAbsoluteError": scalar_error,
                "object": {"name": owner.name, "vertices": len(owner.data.vertices), "polygons": len(owner.data.polygons)},
            })
    render_result_present = bpy.data.images.get("Render Result") is not None
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerDirectionalFixtureCalibrationProbeReport.v0.1",
        "experimentId": spec["experimentId"],
        "specSha256": SPEC_SHA256,
        "target": cli.target,
        "candidateId": selected["candidateId"],
        "selectionPresent": selection_present,
        "pid": os.getpid(),
        "runtime": {
            "blender": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode(),
            "executable": bpy.app.binary_path,
            "executableSha256": sha_file(Path(bpy.app.binary_path)),
        },
        "projectionRows": rows,
        "blenderMaximumAbsoluteError": maximum_blender_error,
        "scalarMaximumAbsoluteError": maximum_scalar_error,
        "renderResultPresent": render_result_present,
        "operationCounts": {"blenderProcesses": 1, "blenderRenderCalls": 0, "cyclesRayRenders": 0, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    cli.output.parent.mkdir(parents=True, exist_ok=True)
    cli.output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if maximum_blender_error > spec["hardGates"]["blenderProjectionMaximumAbsoluteError"] or maximum_scalar_error > spec["hardGates"]["analyticVsBlenderProjectionMaximumAbsoluteError"] or render_result_present:
        raise RuntimeError("D12.14-C1 Blender projection probe gate failed")
    print(f"BFS_B52_D1214C1_BLENDER_PROBE_OK target={cli.target} selected={selected['candidateId']} error={maximum_blender_error:.3e}")


if __name__ == "__main__":
    main()
