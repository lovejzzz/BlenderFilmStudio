import argparse
import hashlib
import json
import math
import os
import sys
import tempfile

import bpy
from bpy_extras import anim_utils
from mathutils import Matrix, Vector


SOURCE_NAME = "CAM_CLOSE_REFLECTION"
CORRECTED_NAME = "CAM_CLOSE_REFLECTION_CORRECTED_D4"
DATA_NAME = "CAM_CLOSE_REFLECTION_CORRECTED_D4_DATA"
TARGET = Vector((0.0, 0.67, 1.72))
ROTATION = Matrix.Rotation(math.radians(-45.0), 4, "Z")
START_FRAME, END_FRAME = 193, 288


def arguments():
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-scene", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--master-sha256", required=True)
    return parser.parse_args(tail)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(value):
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def canonical(value):
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def durable_hashed(path, value, field):
    body = dict(value)
    body[field] = hashlib.sha256(canonical(body)).hexdigest()
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    descriptor, staging = tempfile.mkstemp(prefix=".b62-q1-d4-build-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(body, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staging, path)
    finally:
        if os.path.exists(staging):
            os.unlink(staging)
    return body


def animation_snapshot(obj):
    action = obj.animation_data.action if obj.animation_data and obj.animation_data.action else None
    if action is None:
        return None
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(obj.animation_data)
    require(channelbag is not None, f"assigned channelbag missing for {obj.name}")
    rows = []
    for curve in sorted(channelbag.fcurves, key=lambda item: (item.data_path, item.array_index)):
        rows.append({"dataPath": curve.data_path, "arrayIndex": curve.array_index, "points": [[float(point.co.x), float(point.co.y), point.interpolation] for point in curve.keyframe_points]})
    return {"action": action.name, "curves": rows, "sha256": hashlib.sha256(canonical(rows)).hexdigest()}


def main():
    args = arguments()
    require(bpy.app.version_string.startswith("5.2"), f"unexpected Blender {bpy.app.version_string}")
    require(os.path.basename(bpy.data.filepath) == "B62_PHASE0_MASTER.blend", "unexpected master")
    require(sha256_file(bpy.data.filepath) == args.master_sha256, "master byte identity mismatch")
    require(bpy.data.objects.get(CORRECTED_NAME) is None and bpy.data.cameras.get(DATA_NAME) is None, "corrected camera already exists")
    scene = bpy.context.scene
    source = bpy.data.objects.get(SOURCE_NAME)
    require(source is not None and source.type == "CAMERA", "source camera missing")
    before = {
        "objects": sorted(obj.name for obj in bpy.data.objects),
        "cameras": sorted(camera.name for camera in bpy.data.cameras),
        "actions": sorted(action.name for action in bpy.data.actions),
        "markers": [[marker.name, int(marker.frame), marker.camera.name if marker.camera else None] for marker in scene.timeline_markers],
        "sourceAnimation": animation_snapshot(source),
    }
    data = source.data.copy()
    data.name = DATA_NAME
    data.lens = 65.0
    corrected = bpy.data.objects.new(CORRECTED_NAME, data)
    scene.collection.objects.link(corrected)
    corrected.rotation_mode = "QUATERNION"
    corrected["bfs_correction_id"] = "B62-Q1-D4"
    corrected["bfs_candidate_id"] = "AZ_M045_R200_L065"
    corrected["bfs_source_camera"] = SOURCE_NAME
    corrected["bfs_target"] = list(TARGET)
    bake = []
    for frame in range(START_FRAME, END_FRAME + 1):
        scene.frame_set(frame)
        graph = bpy.context.evaluated_depsgraph_get()
        graph.update()
        source_location = source.evaluated_get(graph).matrix_world.translation.copy()
        corrected.location = TARGET + (ROTATION @ (source_location - TARGET)) * 2.0
        corrected.rotation_quaternion = (TARGET - corrected.location).to_track_quat("-Z", "Y")
        corrected.keyframe_insert(data_path="location", frame=frame, group="B62_D4_LOCATION")
        corrected.keyframe_insert(data_path="rotation_quaternion", frame=frame, group="B62_D4_ROTATION")
        bake.append({"frame": frame, "sourceLocation": [float(value) for value in source_location], "correctedLocation": [float(value) for value in corrected.location], "correctedQuaternion": [float(value) for value in corrected.rotation_quaternion]})
    action = corrected.animation_data.action
    require(action is not None, "corrected action missing")
    action.name = "B62_D4_CLOSE_CAMERA_BAKE"
    corrected_channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(corrected.animation_data)
    require(corrected_channelbag is not None, "corrected assigned channelbag missing")
    for curve in corrected_channelbag.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
    scene.frame_set(START_FRAME)
    after = {
        "objects": sorted(obj.name for obj in bpy.data.objects),
        "cameras": sorted(camera.name for camera in bpy.data.cameras),
        "actions": sorted(item.name for item in bpy.data.actions),
        "markers": [[marker.name, int(marker.frame), marker.camera.name if marker.camera else None] for marker in scene.timeline_markers],
        "sourceAnimation": animation_snapshot(source),
        "correctedAnimation": animation_snapshot(corrected),
    }
    require(after["markers"] == before["markers"] and after["sourceAnimation"] == before["sourceAnimation"], "source scene state drift")
    require(set(after["objects"]) - set(before["objects"]) == {CORRECTED_NAME}, "unexpected object addition")
    require(set(after["cameras"]) - set(before["cameras"]) == {DATA_NAME}, "unexpected camera-data addition")
    require(set(after["actions"]) - set(before["actions"]) == {"B62_D4_CLOSE_CAMERA_BAKE"}, "unexpected action addition")
    require(len(bake) == 96 and len(corrected_channelbag.fcurves) == 7 and all(len(curve.keyframe_points) == 96 for curve in corrected_channelbag.fcurves), "bake roster mismatch")
    output_scene = os.path.abspath(args.output_scene)
    os.makedirs(os.path.dirname(output_scene), exist_ok=True)
    require(not os.path.exists(output_scene), "output scene exists")
    bpy.ops.wm.save_as_mainfile(filepath=output_scene, check_existing=False)
    require(os.path.isfile(output_scene) and os.path.getsize(output_scene) > 0, "derived scene missing")
    report = durable_hashed(os.path.abspath(args.report), {
        "schemaVersion": "bfs.b62CameraQualityCorrectedSceneBuild.v0.1", "experimentId": "B62-Q1-D4", "status": "PASS",
        "source": {"uri": "experiments/b62-phase0-v0-4/scene/B62_PHASE0_MASTER.blend", "sha256": args.master_sha256},
        "derived": {"filepath": output_scene, "sha256": sha256_file(output_scene), "bytes": os.path.getsize(output_scene)},
        "candidateId": "AZ_M045_R200_L065", "camera": {"source": SOURCE_NAME, "corrected": CORRECTED_NAME, "data": DATA_NAME, "lensMillimeters": float(data.lens), "target": list(TARGET)},
        "bake": bake, "stateBefore": before, "stateAfter": after,
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("utf-8")},
        "operations": {"blenderStarts": 1, "sceneSaves": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }, "reportHash")
    print(f"BFS_B62_Q1_D4_BUILD PASS frames={len(bake)} scene={report['derived']['sha256']} report={report['reportHash']}")


if __name__ == "__main__":
    main()
