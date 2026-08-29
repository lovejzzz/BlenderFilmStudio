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
WIDTH, HEIGHT = 64, 36
MAX_DISTANCE = 1000.0
STEP = 0.00001
INTERSECTION_LIMIT = 64


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
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    descriptor, staging = tempfile.mkstemp(prefix=".b62-q1-d2-independent-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staging, path)
        folder_descriptor = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(folder_descriptor)
        finally:
            os.close(folder_descriptor)
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


def source_object(evaluated):
    return getattr(evaluated, "original", None) or evaluated


def inspect_material(material):
    result = {"material": material.name, "usesNodes": bool(material.use_nodes), "outputCount": 0, "surfaceLinked": False, "volumeLinked": False}
    if material.use_nodes and material.node_tree is not None:
        output_nodes = sorted([node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeOutputMaterial"], key=lambda node: node.name)
        result["outputCount"] = len(output_nodes)
        surface_flags, volume_flags = [], []
        for node in output_nodes:
            surface_flags.append(bool(node.inputs.get("Surface") and node.inputs["Surface"].is_linked))
            volume_flags.append(bool(node.inputs.get("Volume") and node.inputs["Volume"].is_linked))
        result["surfaceLinked"] = any(surface_flags)
        result["volumeLinked"] = any(volume_flags)
    return result


def inspect_owner(evaluated):
    original = source_object(evaluated)
    source_materials = []
    data = getattr(original, "data", None)
    if data is not None and hasattr(data, "materials"):
        source_materials = [slot for slot in data.materials if slot is not None]
    details = [inspect_material(material) for material in source_materials]
    is_volume_only = len(details) > 0
    for detail in details:
        is_volume_only = is_volume_only and detail["usesNodes"] and detail["outputCount"] > 0 and detail["volumeLinked"] and not detail["surfaceLinked"]
    return {"object": original.name, "classification": "VOLUME_ONLY_PASS_THROUGH" if is_volume_only else "VISUAL_BLOCKER", "materials": details}


def material_trace(scene, graph, starting_point, heading, maximum, inventory):
    direction = heading.normalized()
    origin = starting_point.copy()
    accumulated = 0.0
    bypassed = []
    intersection_count = 0
    while intersection_count < INTERSECTION_LIMIT:
        remaining = maximum - accumulated
        if remaining <= 0.0:
            return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None, "skipped": bypassed, "intersections": intersection_count, "exhausted": False}
        found, position, _normal, _face, evaluated_owner, _matrix = scene.ray_cast(graph, origin, direction, distance=remaining)
        if not found or evaluated_owner is None:
            return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None, "skipped": bypassed, "intersections": intersection_count, "exhausted": False}
        intersection_count += 1
        local_length = float((position - origin).length)
        absolute_length = accumulated + local_length
        material_state = inspect_owner(evaluated_owner)
        name = material_state["object"]
        inventory[name] = material_state
        if material_state["classification"] == "VOLUME_ONLY_PASS_THROUGH":
            bypassed.append({"object": name, "distanceMeters": absolute_length})
            accumulated = absolute_length + STEP
            origin = position + direction * STEP
        else:
            return {"hit": True, "object": name, "group": group_for(name), "distanceMeters": absolute_length, "skipped": bypassed, "intersections": intersection_count, "exhausted": False}
    return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None, "skipped": bypassed, "intersections": INTERSECTION_LIMIT, "exhausted": True}


def center_of_bounds(source, graph):
    evaluated = source.evaluated_get(graph)
    accumulator = Vector((0.0, 0.0, 0.0))
    for corner in evaluated.bound_box:
        accumulator += evaluated.matrix_world @ Vector(corner)
    return accumulator / len(evaluated.bound_box)


def inspect_anchors(scene, graph, camera, inventory):
    camera_origin = camera.matrix_world.translation.copy()
    records = []
    for anchor_name in ANCHOR_NAMES:
        target = bpy.data.objects.get(anchor_name)
        ensure(target is not None, f"anchor missing {anchor_name}")
        target_point = center_of_bounds(target, graph)
        displacement = target_point - camera_origin
        target_distance = displacement.length
        ensure(target_distance > 0.0, f"anchor at camera {anchor_name}")
        blocker = material_trace(scene, graph, camera_origin, displacement, target_distance + 0.01, inventory)
        ensure(not blocker["exhausted"], f"anchor trace exhausted {anchor_name}")
        records.append({"anchor": anchor_name, "targetPoint": [float(value) for value in target_point], "targetDistanceMeters": float(target_distance), "firstVisualBlocker": blocker, "exactTargetVisible": blocker["hit"] and blocker["object"] == anchor_name})
    return records


def project_character(scene, graph, camera):
    total_vertices = front_vertices = screen_vertices = 0
    points, vertex_roster = [], {}
    for object_name in CHARACTER_NAMES:
        original = bpy.data.objects.get(object_name)
        ensure(original is not None and original.type == "MESH", f"character mesh missing {object_name}")
        evaluated = original.evaluated_get(graph)
        evaluated_mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=graph)
        try:
            vertex_roster[object_name] = len(evaluated_mesh.vertices)
            for vertex in evaluated_mesh.vertices:
                total_vertices += 1
                normalized = world_to_camera_view(scene, camera, evaluated.matrix_world @ vertex.co)
                if normalized.z > 0.0:
                    front_vertices += 1
                    point = (float(normalized.x), float(normalized.y))
                    points.append(point)
                    if 0.0 <= point[0] <= 1.0 and 0.0 <= point[1] <= 1.0:
                        screen_vertices += 1
        finally:
            evaluated.to_mesh_clear()
    ensure(points and total_vertices, "empty character projection")
    low_x, high_x = min(point[0] for point in points), max(point[0] for point in points)
    low_y, high_y = min(point[1] for point in points), max(point[1] for point in points)
    clipped_x = max(0.0, min(1.0, high_x) - max(0.0, low_x))
    clipped_y = max(0.0, min(1.0, high_y) - max(0.0, low_y))
    return {"totalVertices": total_vertices, "inFrontVertices": front_vertices, "onScreenVertices": screen_vertices, "onScreenVertexFraction": screen_vertices / total_vertices, "unclampedBounds": {"minX": low_x, "maxX": high_x, "minY": low_y, "maxY": high_y}, "clampedUnionAreaFraction": clipped_x * clipped_y, "objectVertexCounts": vertex_roster}


def inspect_shot(scene, descriptor, inventory):
    scene.frame_set(descriptor["frame"])
    graph = bpy.context.evaluated_depsgraph_get()
    graph.update()
    camera_source = bpy.data.objects.get(descriptor["camera"])
    ensure(camera_source is not None and camera_source.type == "CAMERA", f"camera missing {descriptor['camera']}")
    scene.camera = camera_source
    camera = camera_source.evaluated_get(graph)
    corners = list(camera.data.view_frame(scene=scene))
    left, right = min(point.x for point in corners), max(point.x for point in corners)
    bottom, top = min(point.y for point in corners), max(point.y for point in corners)
    plane_z = sum(point.z for point in corners) / len(corners)
    frame = {"left": left, "right": right, "bottom": bottom, "top": top, "z": plane_z}
    origin = camera.matrix_world.translation.copy()
    orientation = camera.matrix_world.to_quaternion()
    owners, groups = {}, {"CHARACTER": 0, "CORE": 0, "SCENE_OR_PROP": 0, "OTHER": 0, "MISS": 0}
    rays, skipped_count = [], 0
    for flat_index in range(WIDTH * HEIGHT):
        row, column = divmod(flat_index, WIDTH)
        horizontal, vertical = (column + 0.5) / WIDTH, (row + 0.5) / HEIGHT
        point = Vector((left * (1.0 - horizontal) + right * horizontal, bottom * (1.0 - vertical) + top * vertical, plane_z))
        result = material_trace(scene, graph, origin, orientation @ point, MAX_DISTANCE, inventory)
        ensure(not result["exhausted"], f"grid trace exhausted {descriptor['shot']} {column},{row}")
        groups[result["group"]] += 1
        skipped_count += len(result["skipped"])
        if result["hit"]:
            owners[result["object"]] = owners.get(result["object"], 0) + 1
        rays.append({"x": column, "y": row, **result})
    total = WIDTH * HEIGHT
    ranking = sorted(owners.items(), key=lambda item: (-item[1], item[0]))
    dominant_name, dominant_count = ranking[0] if ranking else (None, 0)
    anchor_records = inspect_anchors(scene, graph, camera, inventory)
    center = material_trace(scene, graph, origin, orientation @ Vector((0.0, 0.0, -1.0)), MAX_DISTANCE, inventory)
    ensure(not center["exhausted"], f"center trace exhausted {descriptor['shot']}")
    return {
        "shot": descriptor["shot"], "frame": descriptor["frame"],
        "camera": {"name": descriptor["camera"], "matrixWorld": [[float(value) for value in row] for row in camera.matrix_world], "lensMillimeters": float(camera.data.lens), "sensorWidthMillimeters": float(camera.data.sensor_width), "sensorHeightMillimeters": float(camera.data.sensor_height), "shiftX": float(camera.data.shift_x), "shiftY": float(camera.data.shift_y), "clipStartMeters": float(camera.data.clip_start), "clipEndMeters": float(camera.data.clip_end), "localViewFrame": frame},
        "grid": {"width": WIDTH, "height": HEIGHT, "totalRays": total, "visualBlockerHitCount": total - groups["MISS"], "missCount": groups["MISS"], "dominantVisualBlockerObject": dominant_name, "dominantVisualBlockerCount": dominant_count, "dominantVisualBlockerShare": dominant_count / total, "characterVisualBlockerShare": groups["CHARACTER"] / total, "objectCounts": dict(sorted(owners.items())), "groupCounts": groups, "skippedPassThroughIntersections": skipped_count, "rays": rays},
        "centerRay": center, "anchors": anchor_records, "visibleAnchorCount": sum(1 for record in anchor_records if record["exactTargetVisible"]), "characterProjection": project_character(scene, graph, camera),
    }


def main():
    args = arguments()
    ensure(bpy.app.version_string.startswith("5.2"), f"unexpected Blender {bpy.app.version_string}")
    ensure(os.path.basename(bpy.data.filepath) == "B62_PHASE0_MASTER.blend", "unexpected source scene")
    inventory = {}
    observations = [inspect_shot(bpy.context.scene, descriptor, inventory) for descriptor in SHOT_TABLE]
    atmosphere = inventory.get("B62_ATMOSPHERE") or inspect_owner(bpy.data.objects["B62_ATMOSPHERE"])
    inventory["B62_ATMOSPHERE"] = atmosphere
    ensure(atmosphere["classification"] == "VOLUME_ONLY_PASS_THROUGH", "atmosphere classification mismatch")
    payload = {"schemaVersion": "bfs.b62CameraQualityMaterialAwareFramingObservation.v0.1", "experimentId": "B62-Q1-D2", "implementation": "INDEPENDENT", "status": "OBSERVED", "master": {"filepath": bpy.data.filepath, "expectedSha256": args.master_sha256}, "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("utf-8")}, "materialClassifications": dict(sorted(inventory.items())), "shots": observations, "operations": {"blenderStarts": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0}}
    persist(os.path.abspath(args.output), payload)
    print("BFS_B62_Q1_D2_INDEPENDENT OBSERVED shots=3 rays=6912 render=0")


if __name__ == "__main__":
    main()
