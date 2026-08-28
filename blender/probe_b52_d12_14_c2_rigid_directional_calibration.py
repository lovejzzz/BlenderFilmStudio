#!/usr/bin/env python3
"""Real Blender 5.2 zero-render rigid projection probe for B52-D12.14-C2."""
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


SPEC_SHA256 = "e123b80fdba40c7e7e396e1aad149573e1e123c57198a21fa8af944320d7e4c3"
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


def sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def parse_args() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--oracle-report", type=Path, required=True)
    parser.add_argument("--target", choices=TARGETS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(raw)


def rotation_xyz(values):
    x, y, z = (float(value) for value in values)
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)
    return (
        (cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
        (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx + cz * sx),
        (-sy, cy * sx, cy * cx),
    )


def mat_vec(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3))


def scalar_world(local, location, rotation):
    rotated = mat_vec(rotation_xyz(rotation), local)
    return tuple(float(location[index]) + rotated[index] for index in range(3))


def scalar_project(point, width: int, height: int, camera_spec: dict):
    relative = tuple(float(point[index]) - float(camera_spec["location"][index]) for index in range(3))
    depth = -relative[2]
    if depth <= 0.0:
        raise RuntimeError("D12.14-C2 corner behind camera")
    sensor_width = float(camera_spec["sensorWidthMm"])
    sensor_height = sensor_width * height / width
    lens = float(camera_spec["lensMm"])
    return (
        (0.5 + lens * relative[0] / (depth * sensor_width)) * width - 0.5,
        (0.5 - lens * relative[1] / (depth * sensor_height)) * height - 0.5,
    )


def local_vertex_hash(owner: bpy.types.Object) -> str:
    rows = [[float(vertex.co.x), float(vertex.co.y), float(vertex.co.z)] for vertex in owner.data.vertices]
    return sha_bytes(json.dumps(rows, separators=(",", ":"), allow_nan=False).encode())


def create_plane(name: str, vertices: list[list[float]]) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.update()
    owner = bpy.data.objects.new(name, mesh)
    owner.rotation_mode = "XYZ"
    bpy.context.scene.collection.objects.link(owner)
    return owner


def main() -> None:
    cli = parse_args()
    if sha_file(cli.spec) != SPEC_SHA256 or cli.output.exists():
        raise RuntimeError("D12.14-C2 probe spec identity or output freshness failure")
    spec = json.loads(cli.spec.read_text())
    runtime = spec["runtime"]["blender"]
    if sha_file(Path(bpy.app.binary_path)) != runtime["sha256"] or bpy.app.version_string != runtime["version"] or bpy.app.build_hash.decode() != runtime["buildHash"]:
        raise RuntimeError("D12.14-C2 Blender runtime identity mismatch")
    oracle = json.loads(cli.oracle_report.read_text())
    selected = next(row for row in oracle["selected"] if row["target"] == cli.target)
    selection_present = selected["candidateId"] is not None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"BFS_D1214C2_{cli.target}"
    rows = []
    maximum_projection_error = 0.0
    maximum_rna_error = 0.0
    maximum_world_error = 0.0
    mesh_identity_stable = True
    mesh_hash_stable = True
    scale_stable = True
    if selection_present:
        width, height = (int(value) for value in selected["resolution"])
        scene.render.resolution_x = width
        scene.render.resolution_y = height
        scene.render.resolution_percentage = 100
        scene.render.pixel_aspect_x = 1.0
        scene.render.pixel_aspect_y = 1.0
        camera_spec = spec["sceneContract"]["camera"]
        camera_data = bpy.data.cameras.new("BFS_D1214C2_CAMERA_DATA")
        camera_data.type = camera_spec["type"]
        camera_data.lens = camera_spec["lensMm"]
        camera_data.sensor_width = camera_spec["sensorWidthMm"]
        camera_data.sensor_fit = camera_spec["sensorFit"]
        camera_data.clip_start = camera_spec["clipStart"]
        camera_data.clip_end = camera_spec["clipEnd"]
        camera = bpy.data.objects.new("BFS_D1214C2_CAMERA", camera_data)
        camera.location = tuple(camera_spec["location"])
        camera.rotation_mode = "XYZ"
        camera.rotation_euler = tuple(camera_spec["rotationEuler"])
        scene.collection.objects.link(camera)
        scene.camera = camera
        foreground = create_plane("BFS_D1214C2_FOREGROUND", spec["sceneContract"]["foreground"]["localVertices"])
        background_size = spec["sceneContract"]["background"]["sizeWorld"]
        background = create_plane("BFS_D1214C2_BACKGROUND", [
            [-background_size[0] / 2.0, -background_size[1] / 2.0, 0.0],
            [background_size[0] / 2.0, -background_size[1] / 2.0, 0.0],
            [background_size[0] / 2.0, background_size[1] / 2.0, 0.0],
            [-background_size[0] / 2.0, background_size[1] / 2.0, 0.0],
        ])
        background.location = tuple(spec["sceneContract"]["background"]["locationByFrame"]["0"])
        background.rotation_euler = tuple(spec["sceneContract"]["background"]["rotationEulerByFrame"]["0"])
        initial_mesh_pointer = foreground.data.as_pointer()
        initial_mesh_name = foreground.data.name
        initial_mesh_hash = local_vertex_hash(foreground)
        initial_scale = tuple(float(value) for value in foreground.scale)
        for frame, location_key, rotation_key in (
            (0, "previousLocation", "previousRotationEuler"),
            (1, "currentLocation", "currentRotationEuler"),
        ):
            requested_location = tuple(float(value) for value in selected[location_key])
            requested_rotation = tuple(float(value) for value in selected[rotation_key])
            foreground.location = requested_location
            foreground.rotation_euler = requested_rotation
            foreground.scale = (1.0, 1.0, 1.0)
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            actual_location = tuple(float(value) for value in foreground.location)
            actual_rotation = tuple(float(value) for value in foreground.rotation_euler)
            rna_error = max(abs(actual_location[index] - requested_location[index]) for index in range(3))
            rna_error = max(rna_error, max(abs(actual_rotation[index] - requested_rotation[index]) for index in range(3)))
            maximum_rna_error = max(maximum_rna_error, rna_error)
            corners = []
            for vertex in foreground.data.vertices:
                local = tuple(float(value) for value in vertex.co)
                blender_world = tuple(float(value) for value in foreground.matrix_world @ vertex.co)
                expected_world = scalar_world(local, requested_location, requested_rotation)
                world_error = max(abs(blender_world[index] - expected_world[index]) for index in range(3))
                maximum_world_error = max(maximum_world_error, world_error)
                ndc = world_to_camera_view(scene, camera, Vector(blender_world))
                blender_pixel = (float(ndc.x) * width - 0.5, (1.0 - float(ndc.y)) * height - 0.5)
                scalar_pixel = scalar_project(expected_world, width, height, camera_spec)
                projection_error = max(abs(blender_pixel[index] - scalar_pixel[index]) for index in range(2))
                maximum_projection_error = max(maximum_projection_error, projection_error)
                corners.append({
                    "local": list(local), "blenderWorld": list(blender_world), "scalarWorld": list(expected_world),
                    "blenderPixel": list(blender_pixel), "scalarPixel": list(scalar_pixel),
                    "worldMaximumAbsoluteError": world_error, "projectionMaximumAbsoluteErrorPixels": projection_error,
                })
            mesh_identity_stable = mesh_identity_stable and foreground.data.as_pointer() == initial_mesh_pointer and foreground.data.name == initial_mesh_name
            mesh_hash_stable = mesh_hash_stable and local_vertex_hash(foreground) == initial_mesh_hash
            scale_stable = scale_stable and tuple(float(value) for value in foreground.scale) == initial_scale == (1.0, 1.0, 1.0)
            rows.append({
                "frame": frame, "requestedLocation": list(requested_location), "rnaLocation": list(actual_location),
                "requestedRotationEuler": list(requested_rotation), "rnaRotationEuler": list(actual_rotation),
                "rnaMaximumAbsoluteError": rna_error, "corners": corners,
                "meshPointer": foreground.data.as_pointer(), "meshName": foreground.data.name,
                "meshLocalVertexHash": local_vertex_hash(foreground), "scale": [float(value) for value in foreground.scale],
            })
    render_result_present = bpy.data.images.get("Render Result") is not None
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalCalibrationProbeReport.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "target": cli.target,
        "candidateId": selected["candidateId"], "selectionPresent": selection_present, "pid": os.getpid(),
        "runtime": {"blender": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode(), "executable": bpy.app.binary_path, "executableSha256": sha_file(Path(bpy.app.binary_path))},
        "frameRows": rows, "meshIdentityStable": mesh_identity_stable, "meshLocalVertexHashStable": mesh_hash_stable,
        "scaleStable": scale_stable, "maximumWorldAbsoluteError": maximum_world_error,
        "maximumProjectionAbsoluteErrorPixels": maximum_projection_error, "maximumRnaTransformAbsoluteError": maximum_rna_error,
        "renderResultPresent": render_result_present,
        "operationCounts": {"blenderProcesses": 1, "blenderRenderCalls": 0, "cyclesRayRenders": 0, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    cli.output.parent.mkdir(parents=True, exist_ok=True)
    cli.output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    contract = spec["blenderProbeContract"]
    if selection_present and (
        not mesh_identity_stable or not mesh_hash_stable or not scale_stable
        or maximum_projection_error > contract["projectionMaximumAbsoluteErrorPixels"]
        or maximum_rna_error > contract["rnaTransformMaximumAbsoluteError"]
    ):
        raise RuntimeError("D12.14-C2 rigid Blender probe gate failed")
    if render_result_present:
        raise RuntimeError("D12.14-C2 unexpected Render Result")
    print(f"BFS_B52_D1214C2_BLENDER_PROBE_OK target={cli.target} selected={selected['candidateId']} projection={maximum_projection_error:.9e}")


if __name__ == "__main__":
    main()
