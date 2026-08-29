import argparse
import json
import math
import os
import sys
import tempfile

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


SHOTS = (
    ("WIDE_APPROACH", 48, "CAM_WIDE_APPROACH"),
    ("MEDIUM_CONTACT", 144, "CAM_MEDIUM_CONTACT"),
    ("CLOSE_REFLECTION", 240, "CAM_CLOSE_REFLECTION"),
)
GRID_WIDTH = 64
GRID_HEIGHT = 36
NEAR_METERS = 0.5
RAY_MAX_METERS = 1000.0
ANCHORS = ("B62_VISOR", "B62_EYE_SLIT", "B62_CHEST_LIGHT", "B62_HAND_R", "B62_CORE")
CHARACTER = {
    "B62_CHEST_LIGHT", "B62_CHEST_PLATE", "B62_EYE_SLIT", "B62_FOOT_L", "B62_FOOT_R",
    "B62_FOREARM_L", "B62_FOREARM_R", "B62_HAND_L", "B62_HAND_R", "B62_HELMET",
    "B62_NECK", "B62_PELVIS", "B62_SHIN_L", "B62_SHIN_R", "B62_SHOULDER_L",
    "B62_SHOULDER_R", "B62_THIGH_L", "B62_THIGH_R", "B62_TORSO", "B62_UPPER_ARM_L",
    "B62_UPPER_ARM_R", "B62_VISOR",
}
CORE = {"B62_CORE", "B62_CORE_RING_A", "B62_CORE_RING_B"}


def parse_args():
    arguments = list(sys.argv)
    tail = arguments[arguments.index("--") + 1:] if "--" in arguments else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--master-sha256", required=True)
    return parser.parse_args(tail)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def durable_json(path, value):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".b62-q1-primary-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def semantic_group(name):
    if name in CHARACTER:
        return "CHARACTER"
    if name in CORE:
        return "CORE"
    if name.startswith("B62_"):
        return "SCENE_OR_PROP"
    return "OTHER"


def camera_local_frame(camera, scene):
    corners = camera.data.view_frame(scene=scene)
    return {
        "left": min(corner.x for corner in corners),
        "right": max(corner.x for corner in corners),
        "bottom": min(corner.y for corner in corners),
        "top": max(corner.y for corner in corners),
        "z": sum(corner.z for corner in corners) / len(corners),
    }


def cast(scene, depsgraph, origin, direction, distance):
    hit, location, _normal, _face, hit_object, _matrix = scene.ray_cast(
        depsgraph, origin, direction, distance=distance
    )
    if not hit or hit_object is None:
        return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None}
    hit_distance = (location - origin).length
    return {
        "hit": True,
        "object": hit_object.original.name if getattr(hit_object, "original", None) else hit_object.name,
        "group": semantic_group(hit_object.original.name if getattr(hit_object, "original", None) else hit_object.name),
        "distanceMeters": float(hit_distance),
    }


def object_bounds_center(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    corners = [evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
    return sum(corners, Vector()) / len(corners)


def anchor_visibility(scene, depsgraph, camera, anchor_name):
    target = bpy.data.objects.get(anchor_name)
    require(target is not None, f"missing anchor {anchor_name}")
    origin = camera.matrix_world.translation.copy()
    target_point = object_bounds_center(target, depsgraph)
    delta = target_point - origin
    target_distance = delta.length
    require(target_distance > 0.0, f"zero anchor distance {anchor_name}")
    observed = cast(scene, depsgraph, origin, delta.normalized(), target_distance + 0.01)
    return {
        "anchor": anchor_name,
        "targetPoint": [float(value) for value in target_point],
        "targetDistanceMeters": float(target_distance),
        "firstHit": observed,
        "exactTargetVisible": observed["hit"] and observed["object"] == anchor_name,
    }


def character_projection(scene, depsgraph, camera):
    projected = []
    total_vertices = 0
    in_front_vertices = 0
    on_screen_vertices = 0
    object_vertex_counts = {}
    for name in sorted(CHARACTER):
        obj = bpy.data.objects.get(name)
        require(obj is not None, f"missing character object {name}")
        require(obj.type == "MESH", f"character object is not mesh {name}")
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=depsgraph)
        try:
            object_vertex_counts[name] = len(mesh.vertices)
            for vertex in mesh.vertices:
                total_vertices += 1
                coordinate = world_to_camera_view(scene, camera, evaluated.matrix_world @ vertex.co)
                if coordinate.z <= 0.0:
                    continue
                in_front_vertices += 1
                projected.append((float(coordinate.x), float(coordinate.y)))
                if 0.0 <= coordinate.x <= 1.0 and 0.0 <= coordinate.y <= 1.0:
                    on_screen_vertices += 1
        finally:
            evaluated.to_mesh_clear()
    require(projected, "no projected character vertices")
    xs = [row[0] for row in projected]
    ys = [row[1] for row in projected]
    bounds = {"minX": min(xs), "maxX": max(xs), "minY": min(ys), "maxY": max(ys)}
    clamped_width = max(0.0, min(1.0, bounds["maxX"]) - max(0.0, bounds["minX"]))
    clamped_height = max(0.0, min(1.0, bounds["maxY"]) - max(0.0, bounds["minY"]))
    return {
        "totalVertices": total_vertices,
        "inFrontVertices": in_front_vertices,
        "onScreenVertices": on_screen_vertices,
        "onScreenVertexFraction": on_screen_vertices / total_vertices,
        "unclampedBounds": bounds,
        "clampedUnionAreaFraction": clamped_width * clamped_height,
        "objectVertexCounts": object_vertex_counts,
    }


def measure_shot(scene, shot_id, frame, camera_name):
    scene.frame_set(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    camera_source = bpy.data.objects.get(camera_name)
    require(camera_source is not None and camera_source.type == "CAMERA", f"missing camera {camera_name}")
    camera = camera_source.evaluated_get(depsgraph)
    require(camera.data.type == "PERSP", f"non-perspective camera {camera_name}")
    scene.camera = camera_source
    local_frame = camera_local_frame(camera, scene)
    origin = camera.matrix_world.translation.copy()
    rotation = camera.matrix_world.to_quaternion()
    object_counts = {}
    group_counts = {"CHARACTER": 0, "CORE": 0, "SCENE_OR_PROP": 0, "OTHER": 0, "MISS": 0}
    hit_distances = []
    near_hit_count = 0
    rows = []
    for row_index in range(GRID_HEIGHT):
        v = (row_index + 0.5) / GRID_HEIGHT
        local_y = local_frame["bottom"] + (local_frame["top"] - local_frame["bottom"]) * v
        for column_index in range(GRID_WIDTH):
            u = (column_index + 0.5) / GRID_WIDTH
            local_x = local_frame["left"] + (local_frame["right"] - local_frame["left"]) * u
            local_point = Vector((local_x, local_y, local_frame["z"]))
            observed = cast(scene, depsgraph, origin, (rotation @ local_point).normalized(), RAY_MAX_METERS)
            group_counts[observed["group"]] += 1
            if observed["hit"]:
                object_counts[observed["object"]] = object_counts.get(observed["object"], 0) + 1
                hit_distances.append(observed["distanceMeters"])
                if observed["distanceMeters"] <= NEAR_METERS:
                    near_hit_count += 1
            rows.append({"x": column_index, "y": row_index, **observed})
    total_rays = GRID_WIDTH * GRID_HEIGHT
    sorted_objects = sorted(object_counts.items(), key=lambda item: (-item[1], item[0]))
    dominant_name, dominant_count = sorted_objects[0] if sorted_objects else (None, 0)
    ordered_distances = sorted(hit_distances)
    middle = len(ordered_distances) // 2
    median_distance = (
        None if not ordered_distances else
        ordered_distances[middle] if len(ordered_distances) % 2 else
        (ordered_distances[middle - 1] + ordered_distances[middle]) / 2.0
    )
    center_direction = rotation @ Vector((0.0, 0.0, -1.0))
    anchors = [anchor_visibility(scene, depsgraph, camera, name) for name in ANCHORS]
    return {
        "shot": shot_id,
        "frame": frame,
        "camera": {
            "name": camera_name,
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
            "width": GRID_WIDTH,
            "height": GRID_HEIGHT,
            "totalRays": total_rays,
            "hitCount": len(hit_distances),
            "missCount": total_rays - len(hit_distances),
            "nearFieldThresholdMeters": NEAR_METERS,
            "nearFieldHitCount": near_hit_count,
            "nearFieldHitShare": near_hit_count / total_rays,
            "medianHitDistanceMeters": median_distance,
            "dominantFirstHitObject": dominant_name,
            "dominantFirstHitCount": dominant_count,
            "dominantFirstHitShare": dominant_count / total_rays,
            "objectCounts": dict(sorted(object_counts.items())),
            "groupCounts": group_counts,
            "rays": rows,
        },
        "centerRay": cast(scene, depsgraph, origin, center_direction.normalized(), RAY_MAX_METERS),
        "anchors": anchors,
        "visibleAnchorCount": sum(1 for row in anchors if row["exactTargetVisible"]),
        "characterProjection": character_projection(scene, depsgraph, camera),
    }


def main():
    args = parse_args()
    require(bpy.app.version_string.startswith("5.2"), f"unexpected Blender {bpy.app.version_string}")
    require(not bpy.data.is_saved or os.path.basename(bpy.data.filepath) == "B62_PHASE0_MASTER.blend", "unexpected master")
    scene = bpy.context.scene
    results = [measure_shot(scene, *shot) for shot in SHOTS]
    document = {
        "schemaVersion": "bfs.b62CameraQualityGeometricObservation.v0.1",
        "experimentId": "B62-Q1-D1",
        "implementation": "PRIMARY",
        "status": "OBSERVED",
        "master": {"filepath": bpy.data.filepath, "expectedSha256": args.master_sha256},
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("utf-8")},
        "shots": results,
        "operations": {"blenderStarts": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }
    require(all(math.isfinite(value) for shot in results for value in shot["camera"]["matrixWorld"][0]), "non-finite camera data")
    durable_json(os.path.abspath(args.output), document)
    print("BFS_B62_Q1_PRIMARY OBSERVED shots=3 rays=6912 render=0")


if __name__ == "__main__":
    main()
