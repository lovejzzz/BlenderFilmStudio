import argparse
import json
import math
import os
import sys
import tempfile

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector


FRAMES = (193, 204, 216, 228, 240, 252, 264, 276, 288)
SEALED = (198, 210, 222, 234, 246, 258, 270, 282)
START_SCALES = (1.75, 2.0, 2.25)
END_SCALES = (2.0, 2.25, 2.5, 2.75, 3.0)
PATH_FRAMES = tuple(range(193, 289))
TARGET = Vector((0.0, 0.67, 1.72))
ANGLE_DEGREES, LENS_MM = -45.0, 65.0
WIDTH, HEIGHT = 32, 18
EPSILON, MAX_INTERSECTIONS, MAX_DISTANCE = 0.00001, 64, 1000.0
ANCHORS = ("B62_VISOR", "B62_EYE_SLIT", "B62_CHEST_LIGHT", "B62_HAND_R", "B62_CORE")
FACE = {"B62_VISOR", "B62_EYE_SLIT"}
CHARACTER = {
    "B62_CHEST_LIGHT", "B62_CHEST_PLATE", "B62_EYE_SLIT", "B62_FOOT_L", "B62_FOOT_R",
    "B62_FOREARM_L", "B62_FOREARM_R", "B62_HAND_L", "B62_HAND_R", "B62_HELMET",
    "B62_NECK", "B62_PELVIS", "B62_SHIN_L", "B62_SHIN_R", "B62_SHOULDER_L",
    "B62_SHOULDER_R", "B62_THIGH_L", "B62_THIGH_R", "B62_TORSO", "B62_UPPER_ARM_L",
    "B62_UPPER_ARM_R", "B62_VISOR",
}
CORE = {"B62_CORE", "B62_CORE_RING_A", "B62_CORE_RING_B"}


def arguments():
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--master-sha256", required=True)
    return parser.parse_args(tail)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def persist(path, payload):
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    descriptor, staging = tempfile.mkstemp(prefix=".b62-q1-d5-primary-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staging, path)
        folder_fd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(folder_fd)
        finally:
            os.close(folder_fd)
    finally:
        if os.path.exists(staging):
            os.unlink(staging)


def group(name):
    if name in CHARACTER:
        return "CHARACTER"
    if name in CORE:
        return "CORE"
    return "SCENE_OR_PROP" if name.startswith("B62_") else "OTHER"


def source(owner):
    return getattr(owner, "original", None) or owner


def classify(owner):
    original = source(owner)
    materials = [material for material in getattr(getattr(original, "data", None), "materials", []) if material is not None]
    rows = []
    for material in materials:
        outputs = sorted(
            [node for node in material.node_tree.nodes if node.type == "OUTPUT_MATERIAL"],
            key=lambda node: node.name,
        ) if material.use_nodes and material.node_tree else []
        rows.append({
            "material": material.name,
            "usesNodes": bool(material.use_nodes),
            "outputCount": len(outputs),
            "surfaceLinked": any(bool(node.inputs.get("Surface") and node.inputs["Surface"].is_linked) for node in outputs),
            "volumeLinked": any(bool(node.inputs.get("Volume") and node.inputs["Volume"].is_linked) for node in outputs),
        })
    passthrough = bool(rows) and all(
        row["usesNodes"] and row["outputCount"] and row["volumeLinked"] and not row["surfaceLinked"] for row in rows
    )
    return {
        "object": original.name,
        "classification": "VOLUME_ONLY_PASS_THROUGH" if passthrough else "VISUAL_BLOCKER",
        "materials": rows,
    }


def trace(scene, graph, origin, heading, maximum, inventory):
    direction = heading.normalized()
    cursor, travelled = origin.copy(), 0.0
    skipped = 0
    for _index in range(MAX_INTERSECTIONS):
        remaining = maximum - travelled
        if remaining <= 0.0:
            return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None, "skippedIntersections": skipped, "exhausted": False}
        hit, location, _normal, _face, owner, _matrix = scene.ray_cast(graph, cursor, direction, distance=remaining)
        if not hit or owner is None:
            return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None, "skippedIntersections": skipped, "exhausted": False}
        local = float((location - cursor).length)
        total = travelled + local
        state = classify(owner)
        inventory[state["object"]] = state
        if state["classification"] == "VOLUME_ONLY_PASS_THROUGH":
            skipped += 1
            travelled = total + EPSILON
            cursor = location + direction * EPSILON
            continue
        return {"hit": True, "object": state["object"], "group": group(state["object"]), "distanceMeters": total, "skippedIntersections": skipped, "exhausted": False}
    return {"hit": False, "object": None, "group": "MISS", "distanceMeters": None, "skippedIntersections": skipped, "exhausted": True}


def bounds_center(obj, graph):
    evaluated = obj.evaluated_get(graph)
    return sum((evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box), Vector()) / len(evaluated.bound_box)


def anchor_rows(scene, graph, camera, inventory):
    result = []
    origin = camera.matrix_world.translation.copy()
    for name in ANCHORS:
        target = bpy.data.objects.get(name)
        require(target is not None, f"missing anchor {name}")
        point = bounds_center(target, graph)
        delta = point - origin
        observed = trace(scene, graph, origin, delta, delta.length + 0.01, inventory)
        require(not observed["exhausted"], f"anchor exhausted {name}")
        result.append({"anchor": name, "firstVisualBlocker": observed["object"], "exactTargetVisible": observed["hit"] and observed["object"] == name})
    return result


def projection(scene, graph, camera):
    total = on_screen = 0
    coordinates = []
    for name in sorted(CHARACTER):
        obj = bpy.data.objects.get(name)
        require(obj is not None and obj.type == "MESH", f"missing character {name}")
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=graph)
        try:
            for vertex in mesh.vertices:
                total += 1
                point = world_to_camera_view(scene, camera, evaluated.matrix_world @ vertex.co)
                if point.z > 0.0:
                    xy = (float(point.x), float(point.y))
                    coordinates.append(xy)
                    if 0.0 <= xy[0] <= 1.0 and 0.0 <= xy[1] <= 1.0:
                        on_screen += 1
        finally:
            evaluated.to_mesh_clear()
    require(coordinates and total, "empty projection")
    low_x, high_x = min(row[0] for row in coordinates), max(row[0] for row in coordinates)
    low_y, high_y = min(row[1] for row in coordinates), max(row[1] for row in coordinates)
    area = max(0.0, min(1.0, high_x) - max(0.0, low_x)) * max(0.0, min(1.0, high_y) - max(0.0, low_y))
    return {"totalVertices": total, "onScreenVertices": on_screen, "onScreenVertexFraction": on_screen / total, "clampedUnionAreaFraction": area}


def radial_scale(frame, start_scale, end_scale):
    u = (frame - PATH_FRAMES[0]) / (PATH_FRAMES[-1] - PATH_FRAMES[0])
    weight = 3.0 * u * u - 2.0 * u * u * u
    return start_scale + (end_scale - start_scale) * weight


def candidate_id(start_scale, end_scale):
    return f"RS_S{round(start_scale * 100):03d}_E{round(end_scale * 100):03d}"


def configure(camera, baseline_location, scale):
    relative = baseline_location - TARGET
    rotated = Matrix.Rotation(math.radians(ANGLE_DEGREES), 4, "Z") @ relative
    camera.location = TARGET + rotated * scale
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = (TARGET - camera.location).to_track_quat("-Z", "Y")
    camera.data.lens = LENS_MM


def measure(scene, graph, camera, inventory):
    corners = camera.data.view_frame(scene=scene)
    left, right = min(row.x for row in corners), max(row.x for row in corners)
    bottom, top = min(row.y for row in corners), max(row.y for row in corners)
    z = sum(row.z for row in corners) / len(corners)
    origin, rotation = camera.matrix_world.translation.copy(), camera.matrix_world.to_quaternion()
    owners, groups, skipped = {}, {"CHARACTER": 0, "CORE": 0, "SCENE_OR_PROP": 0, "OTHER": 0, "MISS": 0}, 0
    for flat in range(WIDTH * HEIGHT):
        y, x = divmod(flat, WIDTH)
        u, v = (x + 0.5) / WIDTH, (y + 0.5) / HEIGHT
        local = Vector((left + (right - left) * u, bottom + (top - bottom) * v, z))
        observed = trace(scene, graph, origin, rotation @ local, MAX_DISTANCE, inventory)
        require(not observed["exhausted"], f"grid exhausted {x},{y}")
        groups[observed["group"]] += 1
        skipped += observed["skippedIntersections"]
        if observed["hit"]:
            owners[observed["object"]] = owners.get(observed["object"], 0) + 1
    total = WIDTH * HEIGHT
    anchors = anchor_rows(scene, graph, camera, inventory)
    visible = [row["anchor"] for row in anchors if row["exactTargetVisible"]]
    projected = projection(scene, graph, camera)
    helmet_share = owners.get("B62_HELMET", 0) / total
    character_share = groups["CHARACTER"] / total
    feasible = FACE.issubset(visible) and helmet_share <= 0.70 and 0.20 <= character_share <= 0.90 and 0.10 <= projected["onScreenVertexFraction"] <= 0.60 and 0.35 <= projected["clampedUnionAreaFraction"] <= 0.90 and len(visible) >= 2
    return {
        "objectCounts": dict(sorted(owners.items())), "groupCounts": groups,
        "helmetVisualBlockerShare": helmet_share, "characterVisualBlockerShare": character_share,
        "skippedPassThroughIntersections": skipped, "anchors": anchors, "visibleAnchors": visible,
        "visibleAnchorCount": len(visible), "faceAnchorVisibleCount": sum(1 for name in visible if name in FACE),
        "characterProjection": projected, "feasible": feasible,
    }


def main():
    args = arguments()
    require(bpy.app.version_string.startswith("5.2"), "unexpected Blender")
    scene = bpy.context.scene
    original_camera = bpy.data.objects.get("CAM_CLOSE_REFLECTION")
    require(original_camera is not None and original_camera.type == "CAMERA", "close camera missing")
    data = original_camera.data.copy()
    camera = bpy.data.objects.new("B62_Q1_D5_PRIMARY_CAMERA", data)
    scene.collection.objects.link(camera)
    inventory, candidates = {}, []
    try:
        for start_scale in START_SCALES:
            for end_scale in END_SCALES:
                if end_scale < start_scale:
                    continue
                path = [radial_scale(frame, start_scale, end_scale) for frame in PATH_FRAMES]
                deltas = [path[index + 1] - path[index] for index in range(len(path) - 1)]
                frames = []
                for frame in FRAMES:
                    scene.frame_set(frame)
                    graph = bpy.context.evaluated_depsgraph_get()
                    graph.update()
                    baseline = original_camera.evaluated_get(graph).matrix_world.translation.copy()
                    scale = radial_scale(frame, start_scale, end_scale)
                    configure(camera, baseline, scale)
                    bpy.context.view_layer.update()
                    evaluated_matrix = camera.matrix_world.copy()
                    frames.append({"frame": frame, "radialScale": scale, "evaluatedCameraLocation": [float(value) for value in evaluated_matrix.translation], "assignedCameraQuaternion": [float(value) for value in camera.rotation_quaternion], **measure(scene, graph, camera, inventory)})
                monotonic = all(delta >= 0.0 for delta in deltas)
                maximum_delta = max(deltas)
                path_ok = monotonic and maximum_delta <= 0.02
                candidates.append({
                    "candidateId": candidate_id(start_scale, end_scale), "startScale": start_scale,
                    "endScale": end_scale, "azimuthDegrees": ANGLE_DEGREES, "lensMillimeters": LENS_MM,
                    "maximumAdjacentIntegerFrameScaleDelta": maximum_delta,
                    "meanAbsoluteIntegerFrameScaleDeviationFromTwo": sum(abs(value - 2.0) for value in path) / len(path),
                    "monotonicNondecreasing": monotonic, "frames": frames,
                    "feasible": path_ok and all(row["feasible"] for row in frames),
                })
    finally:
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(data)
    require(len(candidates) == 14, "candidate roster mismatch")
    feasible = [row for row in candidates if row["feasible"]]
    feasible.sort(key=lambda row: (
        abs(row["startScale"] - 2.0), abs(row["endScale"] - 2.0),
        row["meanAbsoluteIntegerFrameScaleDeviationFromTwo"], row["candidateId"],
    ))
    baseline = next(row for row in candidates if row["candidateId"] == "RS_S200_E200")
    atmosphere = inventory.get("B62_ATMOSPHERE") or classify(bpy.data.objects["B62_ATMOSPHERE"])
    require(atmosphere["classification"] == "VOLUME_ONLY_PASS_THROUGH", "atmosphere mismatch")
    payload = {
        "schemaVersion": "bfs.b62CameraQualityMotionAwareSearchObservation.v0.1",
        "experimentId": "B62-Q1-D5", "implementation": "PRIMARY", "status": "OBSERVED",
        "master": {"filepath": bpy.data.filepath, "expectedSha256": args.master_sha256},
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("utf-8")},
        "derivationFramesEvaluated": list(FRAMES), "sealedValidationFramesNotEvaluated": list(SEALED),
        "materialAwareAtmosphere": atmosphere, "candidateCount": len(candidates),
        "feasibleCandidateCount": len(feasible), "baselineCandidateId": baseline["candidateId"],
        "baselineFeasible": baseline["feasible"], "selectedCandidateId": feasible[0]["candidateId"] if feasible else None,
        "candidates": candidates,
        "operations": {"blenderStarts": 1, "framesSet": len(FRAMES) * len(candidates), "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0, "sceneSaves": 0},
    }
    persist(os.path.abspath(args.output), payload)
    print(f"BFS_B62_Q1_D5_PRIMARY OBSERVED candidates=14 feasible={len(feasible)} render=0")


if __name__ == "__main__":
    main()
