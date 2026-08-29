import argparse
import json
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
WIDTH, HEIGHT = 64, 36
RAY_MAX_METERS = 1000.0
ADVANCE_EPSILON_METERS = 0.00001
MAX_INTERSECTIONS = 64
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
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
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
    descriptor, temporary = tempfile.mkstemp(prefix=".b62-q1-d2-primary-", suffix=".tmp", dir=directory)
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


def owner_name(owner):
    original = getattr(owner, "original", None)
    return original.name if original is not None else owner.name


def material_linkage(material):
    row = {"material": material.name, "usesNodes": bool(material.use_nodes), "outputCount": 0, "surfaceLinked": False, "volumeLinked": False}
    if not material.use_nodes or material.node_tree is None:
        return row
    outputs = sorted((node for node in material.node_tree.nodes if node.type == "OUTPUT_MATERIAL"), key=lambda node: node.name)
    row["outputCount"] = len(outputs)
    for output in outputs:
        surface = output.inputs.get("Surface")
        volume = output.inputs.get("Volume")
        row["surfaceLinked"] = row["surfaceLinked"] or bool(surface and surface.is_linked)
        row["volumeLinked"] = row["volumeLinked"] or bool(volume and volume.is_linked)
    return row


def classify_owner(owner):
    source = getattr(owner, "original", None) or owner
    materials = []
    if getattr(source, "data", None) is not None and hasattr(source.data, "materials"):
        materials = [material for material in source.data.materials if material is not None]
    slots = [material_linkage(material) for material in materials]
    pass_through = bool(slots) and all(row["usesNodes"] and row["outputCount"] > 0 and row["volumeLinked"] and not row["surfaceLinked"] for row in slots)
    return {
        "object": source.name,
        "classification": "VOLUME_ONLY_PASS_THROUGH" if pass_through else "VISUAL_BLOCKER",
        "materials": slots,
    }


def trace_visual(scene, depsgraph, origin, direction, maximum, classifications):
    unit = direction.normalized()
    cursor = origin.copy()
    travelled = 0.0
    skipped = []
    for intersection_index in range(MAX_INTERSECTIONS):
        remaining = maximum - travelled
        if remaining <= 0.0:
            return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None, "skipped": skipped, "intersections": intersection_index, "exhausted": False}
        hit, location, _normal, _face, owner, _matrix = scene.ray_cast(depsgraph, cursor, unit, distance=remaining)
        if not hit or owner is None:
            return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None, "skipped": skipped, "intersections": intersection_index, "exhausted": False}
        local_distance = float((location - cursor).length)
        total_distance = travelled + local_distance
        name = owner_name(owner)
        classification = classify_owner(owner)
        classifications[name] = classification
        if classification["classification"] == "VOLUME_ONLY_PASS_THROUGH":
            skipped.append({"object": name, "distanceMeters": total_distance})
            travelled = total_distance + ADVANCE_EPSILON_METERS
            cursor = location + unit * ADVANCE_EPSILON_METERS
            continue
        return {
            "hit": True,
            "object": name,
            "group": semantic_group(name),
            "distanceMeters": total_distance,
            "skipped": skipped,
            "intersections": intersection_index + 1,
            "exhausted": False,
        }
    return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None, "skipped": skipped, "intersections": MAX_INTERSECTIONS, "exhausted": True}


def bounds_center(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    points = [evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
    return sum(points, Vector()) / len(points)


def anchor_visibility(scene, depsgraph, camera, name, classifications):
    target = bpy.data.objects.get(name)
    require(target is not None, f"missing anchor {name}")
    origin = camera.matrix_world.translation.copy()
    point = bounds_center(target, depsgraph)
    delta = point - origin
    distance = delta.length
    require(distance > 0.0, f"zero anchor distance {name}")
    first = trace_visual(scene, depsgraph, origin, delta, distance + 0.01, classifications)
    require(not first["exhausted"], f"anchor traversal exhausted {name}")
    return {"anchor": name, "targetPoint": [float(value) for value in point], "targetDistanceMeters": float(distance), "firstVisualBlocker": first, "exactTargetVisible": first["hit"] and first["object"] == name}


def character_projection(scene, depsgraph, camera):
    projected, total, front, on_screen, object_counts = [], 0, 0, 0, {}
    for name in sorted(CHARACTER):
        source = bpy.data.objects.get(name)
        require(source is not None and source.type == "MESH", f"missing character mesh {name}")
        evaluated = source.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=depsgraph)
        try:
            object_counts[name] = len(mesh.vertices)
            for vertex in mesh.vertices:
                total += 1
                coordinate = world_to_camera_view(scene, camera, evaluated.matrix_world @ vertex.co)
                if coordinate.z <= 0.0:
                    continue
                front += 1
                xy = (float(coordinate.x), float(coordinate.y))
                projected.append(xy)
                if 0.0 <= xy[0] <= 1.0 and 0.0 <= xy[1] <= 1.0:
                    on_screen += 1
        finally:
            evaluated.to_mesh_clear()
    require(projected and total > 0, "no projected character vertices")
    xs, ys = [row[0] for row in projected], [row[1] for row in projected]
    bounds = {"minX": min(xs), "maxX": max(xs), "minY": min(ys), "maxY": max(ys)}
    width = max(0.0, min(1.0, bounds["maxX"]) - max(0.0, bounds["minX"]))
    height = max(0.0, min(1.0, bounds["maxY"]) - max(0.0, bounds["minY"]))
    return {"totalVertices": total, "inFrontVertices": front, "onScreenVertices": on_screen, "onScreenVertexFraction": on_screen / total, "unclampedBounds": bounds, "clampedUnionAreaFraction": width * height, "objectVertexCounts": object_counts}


def measure_shot(scene, shot_id, frame, camera_name, classifications):
    scene.frame_set(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    source = bpy.data.objects.get(camera_name)
    require(source is not None and source.type == "CAMERA", f"missing camera {camera_name}")
    scene.camera = source
    camera = source.evaluated_get(depsgraph)
    corners = camera.data.view_frame(scene=scene)
    left, right = min(row.x for row in corners), max(row.x for row in corners)
    bottom, top = min(row.y for row in corners), max(row.y for row in corners)
    depth = sum(row.z for row in corners) / len(corners)
    local_frame = {"left": left, "right": right, "bottom": bottom, "top": top, "z": depth}
    origin = camera.matrix_world.translation.copy()
    rotation = camera.matrix_world.to_quaternion()
    object_counts, group_counts, rows = {}, {"CHARACTER": 0, "CORE": 0, "SCENE_OR_PROP": 0, "OTHER": 0, "MISS": 0}, []
    skipped_intersections = 0
    for y in range(HEIGHT):
        v = (y + 0.5) / HEIGHT
        for x in range(WIDTH):
            u = (x + 0.5) / WIDTH
            local = Vector((left + (right - left) * u, bottom + (top - bottom) * v, depth))
            observed = trace_visual(scene, depsgraph, origin, rotation @ local, RAY_MAX_METERS, classifications)
            require(not observed["exhausted"], f"grid traversal exhausted {shot_id} {x},{y}")
            group_counts[observed["group"]] += 1
            skipped_intersections += len(observed["skipped"])
            if observed["hit"]:
                object_counts[observed["object"]] = object_counts.get(observed["object"], 0) + 1
            rows.append({"x": x, "y": y, **observed})
    total = WIDTH * HEIGHT
    ordered = sorted(object_counts.items(), key=lambda row: (-row[1], row[0]))
    dominant, count = ordered[0] if ordered else (None, 0)
    anchors = [anchor_visibility(scene, depsgraph, camera, name, classifications) for name in ANCHORS]
    center = trace_visual(scene, depsgraph, origin, rotation @ Vector((0.0, 0.0, -1.0)), RAY_MAX_METERS, classifications)
    require(not center["exhausted"], f"center traversal exhausted {shot_id}")
    return {
        "shot": shot_id,
        "frame": frame,
        "camera": {"name": camera_name, "matrixWorld": [[float(value) for value in row] for row in camera.matrix_world], "lensMillimeters": float(camera.data.lens), "sensorWidthMillimeters": float(camera.data.sensor_width), "sensorHeightMillimeters": float(camera.data.sensor_height), "shiftX": float(camera.data.shift_x), "shiftY": float(camera.data.shift_y), "clipStartMeters": float(camera.data.clip_start), "clipEndMeters": float(camera.data.clip_end), "localViewFrame": local_frame},
        "grid": {"width": WIDTH, "height": HEIGHT, "totalRays": total, "visualBlockerHitCount": total - group_counts["MISS"], "missCount": group_counts["MISS"], "dominantVisualBlockerObject": dominant, "dominantVisualBlockerCount": count, "dominantVisualBlockerShare": count / total, "characterVisualBlockerShare": group_counts["CHARACTER"] / total, "objectCounts": dict(sorted(object_counts.items())), "groupCounts": group_counts, "skippedPassThroughIntersections": skipped_intersections, "rays": rows},
        "centerRay": center,
        "anchors": anchors,
        "visibleAnchorCount": sum(1 for row in anchors if row["exactTargetVisible"]),
        "characterProjection": character_projection(scene, depsgraph, camera),
    }


def main():
    args = parse_args()
    require(bpy.app.version_string.startswith("5.2"), f"unexpected Blender {bpy.app.version_string}")
    require(os.path.basename(bpy.data.filepath) == "B62_PHASE0_MASTER.blend", "unexpected master")
    classifications = {}
    shots = [measure_shot(bpy.context.scene, *shot, classifications) for shot in SHOTS]
    atmosphere = classifications.get("B62_ATMOSPHERE") or classify_owner(bpy.data.objects["B62_ATMOSPHERE"])
    classifications["B62_ATMOSPHERE"] = atmosphere
    require(atmosphere["classification"] == "VOLUME_ONLY_PASS_THROUGH", "atmosphere classification mismatch")
    document = {"schemaVersion": "bfs.b62CameraQualityMaterialAwareFramingObservation.v0.1", "experimentId": "B62-Q1-D2", "implementation": "PRIMARY", "status": "OBSERVED", "master": {"filepath": bpy.data.filepath, "expectedSha256": args.master_sha256}, "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("utf-8")}, "materialClassifications": dict(sorted(classifications.items())), "shots": shots, "operations": {"blenderStarts": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0}}
    durable_json(os.path.abspath(args.output), document)
    print("BFS_B62_Q1_D2_PRIMARY OBSERVED shots=3 rays=6912 render=0")


if __name__ == "__main__":
    main()
