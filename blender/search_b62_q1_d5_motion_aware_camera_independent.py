import argparse
import json
import math
import os
import sys
import tempfile

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector


DERIVATION = [193, 204, 216, 228, 240, 252, 264, 276, 288]
SEALED_VALIDATION = [198, 210, 222, 234, 246, 258, 270, 282]
START_VALUES = [1.75, 2.0, 2.25]
END_VALUES = [2.0, 2.25, 2.5, 2.75, 3.0]
FIRST_FRAME, LAST_FRAME = 193, 288
LOOK_TARGET = Vector((0.0, 0.67, 1.72))
AZIMUTH_RADIANS = math.radians(-45.0)
FIXED_LENS = 65.0
GRID_X, GRID_Y = 32, 18
TRACE_LIMIT, TRACE_STEP, TRACE_DISTANCE = 64, 0.00001, 1000.0
ANCHOR_NAMES = ["B62_VISOR", "B62_EYE_SLIT", "B62_CHEST_LIGHT", "B62_HAND_R", "B62_CORE"]
FACE_NAMES = {"B62_VISOR", "B62_EYE_SLIT"}
CHARACTER_NAMES = sorted([
    "B62_CHEST_LIGHT", "B62_CHEST_PLATE", "B62_EYE_SLIT", "B62_FOOT_L", "B62_FOOT_R",
    "B62_FOREARM_L", "B62_FOREARM_R", "B62_HAND_L", "B62_HAND_R", "B62_HELMET",
    "B62_NECK", "B62_PELVIS", "B62_SHIN_L", "B62_SHIN_R", "B62_SHOULDER_L",
    "B62_SHOULDER_R", "B62_THIGH_L", "B62_THIGH_R", "B62_TORSO", "B62_UPPER_ARM_L",
    "B62_UPPER_ARM_R", "B62_VISOR",
])
CHARACTER_SET = set(CHARACTER_NAMES)
CORE_NAMES = {"B62_CORE", "B62_CORE_RING_A", "B62_CORE_RING_B"}


def command_line():
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--master-sha256", required=True)
    return parser.parse_args(tail)


def ensure(condition, message):
    if not condition:
        raise RuntimeError(message)


def write_document(path, value):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    file_descriptor, temporary = tempfile.mkstemp(prefix=".b62-q1-d5-independent-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n")
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


def semantic_group(object_name):
    if object_name in CHARACTER_SET:
        return "CHARACTER"
    if object_name in CORE_NAMES:
        return "CORE"
    if object_name.startswith("B62_"):
        return "SCENE_OR_PROP"
    return "OTHER"


def material_state(hit_owner):
    owner = getattr(hit_owner, "original", None) or hit_owner
    data = getattr(owner, "data", None)
    populated = [material for material in data.materials if material is not None] if data is not None and hasattr(data, "materials") else []
    material_rows = []
    for material in populated:
        output_nodes = []
        if material.use_nodes and material.node_tree is not None:
            output_nodes = sorted(
                [node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeOutputMaterial"],
                key=lambda node: node.name,
            )
        surface = any(bool(node.inputs.get("Surface") and node.inputs["Surface"].is_linked) for node in output_nodes)
        volume = any(bool(node.inputs.get("Volume") and node.inputs["Volume"].is_linked) for node in output_nodes)
        material_rows.append({"material": material.name, "usesNodes": bool(material.use_nodes), "outputCount": len(output_nodes), "surfaceLinked": surface, "volumeLinked": volume})
    volume_only = len(material_rows) > 0
    for row in material_rows:
        volume_only = volume_only and row["usesNodes"] and row["outputCount"] > 0 and row["volumeLinked"] and not row["surfaceLinked"]
    return {"object": owner.name, "classification": "VOLUME_ONLY_PASS_THROUGH" if volume_only else "VISUAL_BLOCKER", "materials": material_rows}


def first_blocker(scene, graph, start, vector, maximum, inventory):
    direction = vector.normalized()
    position = start.copy()
    cumulative = 0.0
    skipped = 0
    intersections = 0
    while intersections < TRACE_LIMIT:
        remaining = maximum - cumulative
        if remaining <= 0.0:
            return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None, "skippedIntersections": skipped, "exhausted": False}
        found, point, _normal, _face, hit_owner, _transform = scene.ray_cast(graph, position, direction, distance=remaining)
        if not found or hit_owner is None:
            return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None, "skippedIntersections": skipped, "exhausted": False}
        intersections += 1
        cumulative_hit = cumulative + float((point - position).length)
        state = material_state(hit_owner)
        inventory[state["object"]] = state
        if state["classification"] == "VOLUME_ONLY_PASS_THROUGH":
            skipped += 1
            cumulative = cumulative_hit + TRACE_STEP
            position = point + direction * TRACE_STEP
        else:
            return {"hit": True, "object": state["object"], "group": semantic_group(state["object"]), "distanceMeters": cumulative_hit, "skippedIntersections": skipped, "exhausted": False}
    return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None, "skippedIntersections": skipped, "exhausted": True}


def object_center(object_source, graph):
    evaluated = object_source.evaluated_get(graph)
    total = Vector((0.0, 0.0, 0.0))
    for corner in evaluated.bound_box:
        total += evaluated.matrix_world @ Vector(corner)
    return total / len(evaluated.bound_box)


def visibility(scene, graph, camera, inventory):
    camera_position = camera.matrix_world.translation.copy()
    rows = []
    for anchor_name in ANCHOR_NAMES:
        source = bpy.data.objects.get(anchor_name)
        ensure(source is not None, f"missing anchor {anchor_name}")
        point = object_center(source, graph)
        displacement = point - camera_position
        result = first_blocker(scene, graph, camera_position, displacement, displacement.length + 0.01, inventory)
        ensure(not result["exhausted"], f"anchor exhausted {anchor_name}")
        rows.append({"anchor": anchor_name, "firstVisualBlocker": result["object"], "exactTargetVisible": result["hit"] and result["object"] == anchor_name})
    return rows


def character_projection(scene, graph, camera):
    all_vertices = screen_vertices = 0
    projected = []
    for object_name in CHARACTER_NAMES:
        source = bpy.data.objects.get(object_name)
        ensure(source is not None and source.type == "MESH", f"missing character {object_name}")
        evaluated = source.evaluated_get(graph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=graph)
        try:
            for vertex in mesh.vertices:
                all_vertices += 1
                coordinate = world_to_camera_view(scene, camera, evaluated.matrix_world @ vertex.co)
                if coordinate.z > 0.0:
                    x, y = float(coordinate.x), float(coordinate.y)
                    projected.append((x, y))
                    if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                        screen_vertices += 1
        finally:
            evaluated.to_mesh_clear()
    ensure(projected and all_vertices, "empty projection")
    minimum_x, maximum_x = min(row[0] for row in projected), max(row[0] for row in projected)
    minimum_y, maximum_y = min(row[1] for row in projected), max(row[1] for row in projected)
    clipped_width = max(0.0, min(1.0, maximum_x) - max(0.0, minimum_x))
    clipped_height = max(0.0, min(1.0, maximum_y) - max(0.0, minimum_y))
    return {"totalVertices": all_vertices, "onScreenVertices": screen_vertices, "onScreenVertexFraction": screen_vertices / all_vertices, "clampedUnionAreaFraction": clipped_width * clipped_height}


def scale_at(frame, start_value, end_value):
    normalized = (frame - FIRST_FRAME) / (LAST_FRAME - FIRST_FRAME)
    smooth = normalized * normalized * (3.0 - 2.0 * normalized)
    return start_value + (end_value - start_value) * smooth


def identifier(start_value, end_value):
    return f"RS_S{round(start_value * 100):03d}_E{round(end_value * 100):03d}"


def set_candidate(camera, original_location, radial_scale):
    offset = original_location - LOOK_TARGET
    rotated = Matrix.Rotation(AZIMUTH_RADIANS, 4, "Z") @ offset
    camera.location = LOOK_TARGET + rotated * radial_scale
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = (LOOK_TARGET - camera.location).to_track_quat("-Z", "Y")
    camera.data.lens = FIXED_LENS


def observe_candidate_frame(scene, graph, camera, inventory):
    corners = list(camera.data.view_frame(scene=scene))
    x_min, x_max = min(row.x for row in corners), max(row.x for row in corners)
    y_min, y_max = min(row.y for row in corners), max(row.y for row in corners)
    depth = sum(row.z for row in corners) / len(corners)
    origin = camera.matrix_world.translation.copy()
    orientation = camera.matrix_world.to_quaternion()
    object_counts = {}
    group_counts = {"CHARACTER": 0, "CORE": 0, "SCENE_OR_PROP": 0, "OTHER": 0, "MISS": 0}
    skipped_count = 0
    for sample_index in range(GRID_X * GRID_Y):
        row_index, column_index = divmod(sample_index, GRID_X)
        u, v = (column_index + 0.5) / GRID_X, (row_index + 0.5) / GRID_Y
        local_point = Vector((x_min * (1.0 - u) + x_max * u, y_min * (1.0 - v) + y_max * v, depth))
        hit = first_blocker(scene, graph, origin, orientation @ local_point, TRACE_DISTANCE, inventory)
        ensure(not hit["exhausted"], f"grid exhausted {column_index},{row_index}")
        group_counts[hit["group"]] += 1
        skipped_count += hit["skippedIntersections"]
        if hit["hit"]:
            object_counts[hit["object"]] = object_counts.get(hit["object"], 0) + 1
    anchors = visibility(scene, graph, camera, inventory)
    visible_names = [row["anchor"] for row in anchors if row["exactTargetVisible"]]
    projected = character_projection(scene, graph, camera)
    total_samples = GRID_X * GRID_Y
    helmet_share = object_counts.get("B62_HELMET", 0) / total_samples
    character_share = group_counts["CHARACTER"] / total_samples
    acceptable = FACE_NAMES.issubset(visible_names)
    acceptable = acceptable and helmet_share <= 0.70 and 0.20 <= character_share <= 0.90
    acceptable = acceptable and 0.10 <= projected["onScreenVertexFraction"] <= 0.60
    acceptable = acceptable and 0.35 <= projected["clampedUnionAreaFraction"] <= 0.90 and len(visible_names) >= 2
    return {
        "objectCounts": dict(sorted(object_counts.items())), "groupCounts": group_counts,
        "helmetVisualBlockerShare": helmet_share, "characterVisualBlockerShare": character_share,
        "skippedPassThroughIntersections": skipped_count, "anchors": anchors, "visibleAnchors": visible_names,
        "visibleAnchorCount": len(visible_names), "faceAnchorVisibleCount": len(FACE_NAMES.intersection(visible_names)),
        "characterProjection": projected, "feasible": acceptable,
    }


def main():
    args = command_line()
    ensure(bpy.app.version_string.startswith("5.2"), "unexpected Blender")
    scene = bpy.context.scene
    close_source = bpy.data.objects.get("CAM_CLOSE_REFLECTION")
    ensure(close_source is not None and close_source.type == "CAMERA", "close camera missing")
    copied_data = close_source.data.copy()
    probe_camera = bpy.data.objects.new("B62_Q1_D5_INDEPENDENT_CAMERA", copied_data)
    scene.collection.objects.link(probe_camera)
    inventory, observations = {}, []
    try:
        for start_value in START_VALUES:
            for end_value in END_VALUES:
                if end_value < start_value:
                    continue
                integer_path = [scale_at(frame, start_value, end_value) for frame in range(FIRST_FRAME, LAST_FRAME + 1)]
                adjacent = [right - left for left, right in zip(integer_path, integer_path[1:])]
                frame_rows = []
                for frame in DERIVATION:
                    scene.frame_set(frame)
                    graph = bpy.context.evaluated_depsgraph_get()
                    graph.update()
                    evaluated_location = close_source.evaluated_get(graph).matrix_world.translation.copy()
                    current_scale = scale_at(frame, start_value, end_value)
                    set_candidate(probe_camera, evaluated_location, current_scale)
                    bpy.context.view_layer.update()
                    evaluated_transform = probe_camera.matrix_world.copy()
                    frame_rows.append({"frame": frame, "radialScale": current_scale, "evaluatedCameraLocation": [float(value) for value in evaluated_transform.translation], "assignedCameraQuaternion": [float(value) for value in probe_camera.rotation_quaternion], **observe_candidate_frame(scene, graph, probe_camera, inventory)})
                monotonic = all(value >= 0.0 for value in adjacent)
                maximum_change = max(adjacent)
                observations.append({
                    "candidateId": identifier(start_value, end_value), "startScale": start_value,
                    "endScale": end_value, "azimuthDegrees": -45.0, "lensMillimeters": FIXED_LENS,
                    "maximumAdjacentIntegerFrameScaleDelta": maximum_change,
                    "meanAbsoluteIntegerFrameScaleDeviationFromTwo": sum(abs(value - 2.0) for value in integer_path) / len(integer_path),
                    "monotonicNondecreasing": monotonic, "frames": frame_rows,
                    "feasible": monotonic and maximum_change <= 0.02 and all(row["feasible"] for row in frame_rows),
                })
    finally:
        bpy.data.objects.remove(probe_camera, do_unlink=True)
        bpy.data.cameras.remove(copied_data)
    ensure(len(observations) == 14, "candidate roster mismatch")
    eligible = [row for row in observations if row["feasible"]]
    eligible.sort(key=lambda row: (
        abs(row["startScale"] - 2.0), abs(row["endScale"] - 2.0),
        row["meanAbsoluteIntegerFrameScaleDeviationFromTwo"], row["candidateId"],
    ))
    baseline = next(row for row in observations if row["candidateId"] == "RS_S200_E200")
    atmosphere = inventory.get("B62_ATMOSPHERE") or material_state(bpy.data.objects["B62_ATMOSPHERE"])
    ensure(atmosphere["classification"] == "VOLUME_ONLY_PASS_THROUGH", "atmosphere mismatch")
    document = {
        "schemaVersion": "bfs.b62CameraQualityMotionAwareSearchObservation.v0.1",
        "experimentId": "B62-Q1-D5", "implementation": "INDEPENDENT", "status": "OBSERVED",
        "master": {"filepath": bpy.data.filepath, "expectedSha256": args.master_sha256},
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("utf-8")},
        "derivationFramesEvaluated": DERIVATION, "sealedValidationFramesNotEvaluated": SEALED_VALIDATION,
        "materialAwareAtmosphere": atmosphere, "candidateCount": len(observations),
        "feasibleCandidateCount": len(eligible), "baselineCandidateId": baseline["candidateId"],
        "baselineFeasible": baseline["feasible"], "selectedCandidateId": eligible[0]["candidateId"] if eligible else None,
        "candidates": observations,
        "operations": {"blenderStarts": 1, "framesSet": len(DERIVATION) * len(observations), "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0, "sceneSaves": 0},
    }
    write_document(os.path.abspath(args.output), document)
    print(f"BFS_B62_Q1_D5_INDEPENDENT OBSERVED candidates=14 feasible={len(eligible)} render=0")


if __name__ == "__main__":
    main()
