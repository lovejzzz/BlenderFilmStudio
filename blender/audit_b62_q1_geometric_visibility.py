import argparse
import json
import os
import sys
import tempfile

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


SHOT_TABLE = [
    {"shot": "WIDE_APPROACH", "frame": 48, "camera": "CAM_WIDE_APPROACH"},
    {"shot": "MEDIUM_CONTACT", "frame": 144, "camera": "CAM_MEDIUM_CONTACT"},
    {"shot": "CLOSE_REFLECTION", "frame": 240, "camera": "CAM_CLOSE_REFLECTION"},
]
ANCHOR_NAMES = ["B62_VISOR", "B62_EYE_SLIT", "B62_CHEST_LIGHT", "B62_HAND_R", "B62_CORE"]
CHARACTER_NAMES = sorted([
    "B62_CHEST_LIGHT", "B62_CHEST_PLATE", "B62_EYE_SLIT", "B62_FOOT_L", "B62_FOOT_R",
    "B62_FOREARM_L", "B62_FOREARM_R", "B62_HAND_L", "B62_HAND_R", "B62_HELMET",
    "B62_NECK", "B62_PELVIS", "B62_SHIN_L", "B62_SHIN_R", "B62_SHOULDER_L",
    "B62_SHOULDER_R", "B62_THIGH_L", "B62_THIGH_R", "B62_TORSO", "B62_UPPER_ARM_L",
    "B62_UPPER_ARM_R", "B62_VISOR",
])
CORE_NAMES = {"B62_CORE", "B62_CORE_RING_A", "B62_CORE_RING_B"}
WIDTH = 64
HEIGHT = 36
NEAR_LIMIT = 0.5


def arguments():
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--master-sha256", required=True)
    return parser.parse_args(tail)


def ensure(value, label):
    if not value:
        raise RuntimeError(label)


def persist(path, payload):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, staging = tempfile.mkstemp(prefix=".b62-q1-independent-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staging, path)
        directory_fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(staging):
            os.unlink(staging)


def group_for(name):
    if name in CHARACTER_NAMES:
        return "CHARACTER"
    if name in CORE_NAMES:
        return "CORE"
    if name.startswith("B62_"):
        return "SCENE_OR_PROP"
    return "OTHER"


def original_name(evaluated_object):
    original = getattr(evaluated_object, "original", None)
    return original.name if original is not None else evaluated_object.name


def trace(scene, graph, origin, direction, maximum):
    found, position, _normal, _polygon, owner, _transform = scene.ray_cast(
        graph, origin, direction.normalized(), distance=maximum
    )
    if not found or owner is None:
        return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None}
    name = original_name(owner)
    return {
        "hit": True,
        "object": name,
        "group": group_for(name),
        "distanceMeters": float((position - origin).length),
    }


def target_center(source, graph):
    evaluated = source.evaluated_get(graph)
    total = Vector((0.0, 0.0, 0.0))
    for corner in evaluated.bound_box:
        total += evaluated.matrix_world @ Vector(corner)
    return total / 8.0


def anchor_rows(scene, graph, camera):
    origin = camera.matrix_world.translation.copy()
    output = []
    for name in ANCHOR_NAMES:
        source = bpy.data.objects.get(name)
        ensure(source is not None, f"anchor missing: {name}")
        point = target_center(source, graph)
        displacement = point - origin
        distance = displacement.length
        ensure(distance > 0.0, f"anchor at camera: {name}")
        first = trace(scene, graph, origin, displacement, distance + 0.01)
        output.append({
            "anchor": name,
            "targetPoint": [float(component) for component in point],
            "targetDistanceMeters": float(distance),
            "firstHit": first,
            "exactTargetVisible": first["hit"] and first["object"] == name,
        })
    return output


def projection(scene, graph, camera):
    total = 0
    front = 0
    visible = 0
    coordinates = []
    object_counts = {}
    for name in CHARACTER_NAMES:
        source = bpy.data.objects.get(name)
        ensure(source is not None and source.type == "MESH", f"character mesh missing: {name}")
        evaluated = source.evaluated_get(graph)
        temporary_mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=graph)
        try:
            object_counts[name] = len(temporary_mesh.vertices)
            for vertex in temporary_mesh.vertices:
                total += 1
                normalized = world_to_camera_view(scene, camera, evaluated.matrix_world @ vertex.co)
                if normalized.z <= 0.0:
                    continue
                front += 1
                xy = (float(normalized.x), float(normalized.y))
                coordinates.append(xy)
                if 0.0 <= xy[0] <= 1.0 and 0.0 <= xy[1] <= 1.0:
                    visible += 1
        finally:
            evaluated.to_mesh_clear()
    ensure(len(coordinates) > 0, "character has no front-facing projection")
    minimum_x = min(row[0] for row in coordinates)
    maximum_x = max(row[0] for row in coordinates)
    minimum_y = min(row[1] for row in coordinates)
    maximum_y = max(row[1] for row in coordinates)
    clipped_width = max(0.0, min(1.0, maximum_x) - max(0.0, minimum_x))
    clipped_height = max(0.0, min(1.0, maximum_y) - max(0.0, minimum_y))
    return {
        "totalVertices": total,
        "inFrontVertices": front,
        "onScreenVertices": visible,
        "onScreenVertexFraction": visible / total,
        "unclampedBounds": {"minX": minimum_x, "maxX": maximum_x, "minY": minimum_y, "maxY": maximum_y},
        "clampedUnionAreaFraction": clipped_width * clipped_height,
        "objectVertexCounts": object_counts,
    }


def median(values):
    ordered = sorted(values)
    if not ordered:
        return None
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) * 0.5


def observe(scene, descriptor):
    scene.frame_set(descriptor["frame"])
    graph = bpy.context.evaluated_depsgraph_get()
    graph.update()
    source_camera = bpy.data.objects.get(descriptor["camera"])
    ensure(source_camera is not None and source_camera.type == "CAMERA", f"camera missing: {descriptor['camera']}")
    scene.camera = source_camera
    camera = source_camera.evaluated_get(graph)
    ensure(camera.data.type == "PERSP", "perspective camera required")
    frame_corners = list(camera.data.view_frame(scene=scene))
    left, right = min(item.x for item in frame_corners), max(item.x for item in frame_corners)
    bottom, top = min(item.y for item in frame_corners), max(item.y for item in frame_corners)
    depth = sum(item.z for item in frame_corners) / 4.0
    local_frame = {"left": left, "right": right, "bottom": bottom, "top": top, "z": depth}
    origin = camera.matrix_world.translation.copy()
    orientation = camera.matrix_world.to_quaternion()
    owner_counts = {}
    group_counts = {"CHARACTER": 0, "CORE": 0, "SCENE_OR_PROP": 0, "OTHER": 0, "MISS": 0}
    distances = []
    close_count = 0
    for flat_index in range(WIDTH * HEIGHT):
        y_index, x_index = divmod(flat_index, WIDTH)
        horizontal = (x_index + 0.5) / WIDTH
        vertical = (y_index + 0.5) / HEIGHT
        sample = Vector((
            left * (1.0 - horizontal) + right * horizontal,
            bottom * (1.0 - vertical) + top * vertical,
            depth,
        ))
        hit = trace(scene, graph, origin, orientation @ sample, 1000.0)
        group_counts[hit["group"]] += 1
        if not hit["hit"]:
            continue
        owner_counts[hit["object"]] = owner_counts.get(hit["object"], 0) + 1
        distances.append(hit["distanceMeters"])
        if hit["distanceMeters"] <= NEAR_LIMIT:
            close_count += 1
    total_rays = WIDTH * HEIGHT
    owner_order = sorted(owner_counts.items(), key=lambda row: (-row[1], row[0]))
    dominant_object, dominant_count = owner_order[0] if owner_order else (None, 0)
    anchors = anchor_rows(scene, graph, camera)
    center = trace(scene, graph, origin, orientation @ Vector((0.0, 0.0, -1.0)), 1000.0)
    return {
        "shot": descriptor["shot"],
        "frame": descriptor["frame"],
        "camera": {
            "name": descriptor["camera"],
            "matrixWorld": [[float(value) for value in row] for row in camera.matrix_world],
            "lensMillimeters": float(camera.data.lens),
            "sensorWidthMillimeters": float(camera.data.sensor_width),
            "sensorHeightMillimeters": float(camera.data.sensor_height),
            "shiftX": float(camera.data.shift_x),
            "shiftY": float(camera.data.shift_y),
            "clipStartMeters": float(camera.data.clip_start),
            "clipEndMeters": float(camera.data.clip_end),
            "localViewFrame": local_frame,
        },
        "grid": {
            "width": WIDTH,
            "height": HEIGHT,
            "totalRays": total_rays,
            "hitCount": len(distances),
            "missCount": total_rays - len(distances),
            "nearFieldThresholdMeters": NEAR_LIMIT,
            "nearFieldHitCount": close_count,
            "nearFieldHitShare": close_count / total_rays,
            "medianHitDistanceMeters": median(distances),
            "dominantFirstHitObject": dominant_object,
            "dominantFirstHitCount": dominant_count,
            "dominantFirstHitShare": dominant_count / total_rays,
            "objectCounts": dict(sorted(owner_counts.items())),
            "groupCounts": group_counts,
        },
        "centerRay": center,
        "anchors": anchors,
        "visibleAnchorCount": sum(1 for item in anchors if item["exactTargetVisible"]),
        "characterProjection": projection(scene, graph, camera),
    }


def main():
    args = arguments()
    ensure(bpy.app.version_string.startswith("5.2"), f"unexpected Blender version: {bpy.app.version_string}")
    ensure(os.path.basename(bpy.data.filepath) == "B62_PHASE0_MASTER.blend", "unexpected source scene")
    observations = [observe(bpy.context.scene, descriptor) for descriptor in SHOT_TABLE]
    payload = {
        "schemaVersion": "bfs.b62CameraQualityGeometricObservation.v0.1",
        "experimentId": "B62-Q1-D1",
        "implementation": "INDEPENDENT",
        "status": "OBSERVED",
        "master": {"filepath": bpy.data.filepath, "expectedSha256": args.master_sha256},
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("utf-8")},
        "shots": observations,
        "operations": {"blenderStarts": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }
    persist(os.path.abspath(args.output), payload)
    print("BFS_B62_Q1_INDEPENDENT OBSERVED shots=3 rays=6912 render=0")


if __name__ == "__main__":
    main()
