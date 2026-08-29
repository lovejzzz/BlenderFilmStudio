import argparse
import hashlib
import json
import math
import os
import struct
import sys
import tempfile

import bpy
from bpy_extras import anim_utils
from mathutils import Matrix, Vector


SOURCE_NAME = "CAM_CLOSE_REFLECTION"
STATIC_NAME, MOTION_NAME = "CAM_CLOSE_STATIC_D6", "CAM_CLOSE_MOTION_D6"
STATIC_DATA, MOTION_DATA = "CAM_CLOSE_STATIC_D6_DATA", "CAM_CLOSE_MOTION_D6_DATA"
STATIC_ACTION, MOTION_ACTION = "B62_D6_STATIC_CAMERA_BAKE", "B62_D6_MOTION_CAMERA_BAKE"
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
    if isinstance(value, float) and math.isfinite(value) and value.is_integer(): return int(value)
    if isinstance(value, float) and math.isfinite(value): return {"$f64be": struct.pack(">d", value).hex()}
    if isinstance(value, list): return [normalize(item) for item in value]
    if isinstance(value, dict): return {key: normalize(item) for key, item in value.items()}
    return value


def canonical(value):
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def durable_hashed(path, value, field):
    body = dict(value)
    body[field] = hashlib.sha256(canonical(body)).hexdigest()
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    descriptor, staging = tempfile.mkstemp(prefix=".b62-q1-d6-build-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(body, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staging, path)
    finally:
        if os.path.exists(staging): os.unlink(staging)
    return body


def animation_snapshot(obj):
    action = obj.animation_data.action if obj.animation_data and obj.animation_data.action else None
    if action is None: return None
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(obj.animation_data)
    require(channelbag is not None, f"assigned channelbag missing for {obj.name}")
    rows = []
    for curve in sorted(channelbag.fcurves, key=lambda item: (item.data_path, item.array_index)):
        rows.append({"dataPath": curve.data_path, "arrayIndex": curve.array_index, "points": [[float(point.co.x), float(point.co.y), point.interpolation] for point in curve.keyframe_points]})
    return {"action": action.name, "curves": rows, "sha256": hashlib.sha256(canonical(rows)).hexdigest()}


def smooth_scale(frame):
    u = (frame - START_FRAME) / (END_FRAME - START_FRAME)
    return 2.0 + 0.25 * (3.0 * u * u - 2.0 * u * u * u)


def create_camera(scene, source, object_name, data_name, condition):
    data = source.data.copy()
    data.name = data_name
    data.lens = 65.0
    camera = bpy.data.objects.new(object_name, data)
    scene.collection.objects.link(camera)
    camera.rotation_mode = "QUATERNION"
    camera["bfs_experiment_id"] = "B62-Q1-D6"
    camera["bfs_candidate_id"] = "RS_S200_E225"
    camera["bfs_condition"] = condition
    camera["bfs_source_camera"] = SOURCE_NAME
    camera["bfs_target"] = list(TARGET)
    return camera


def set_camera(camera, source_location, scale):
    camera.location = TARGET + (ROTATION @ (source_location - TARGET)) * scale
    camera.rotation_quaternion = (TARGET - camera.location).to_track_quat("-Z", "Y")


def finalize_action(camera, action_name):
    action = camera.animation_data.action
    require(action is not None, f"action missing {camera.name}")
    action.name = action_name
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(camera.animation_data)
    require(channelbag is not None, f"channelbag missing {camera.name}")
    for curve in channelbag.fcurves:
        for point in curve.keyframe_points: point.interpolation = "LINEAR"
    require(len(channelbag.fcurves) == 7 and all(len(curve.keyframe_points) == 96 for curve in channelbag.fcurves), f"bake roster {camera.name}")
    return channelbag


def main():
    args = arguments()
    require(bpy.app.version_string.startswith("5.2"), f"unexpected Blender {bpy.app.version_string}")
    require(os.path.basename(bpy.data.filepath) == "B62_PHASE0_MASTER.blend", "unexpected master")
    require(sha256_file(bpy.data.filepath) == args.master_sha256, "master identity mismatch")
    for name in (STATIC_NAME, MOTION_NAME): require(bpy.data.objects.get(name) is None, f"camera already exists {name}")
    scene = bpy.context.scene
    source = bpy.data.objects.get(SOURCE_NAME)
    require(source is not None and source.type == "CAMERA", "source camera missing")
    before = {"objects": sorted(obj.name for obj in bpy.data.objects), "cameras": sorted(camera.name for camera in bpy.data.cameras), "actions": sorted(action.name for action in bpy.data.actions), "markers": [[marker.name, int(marker.frame), marker.camera.name if marker.camera else None] for marker in scene.timeline_markers], "sourceAnimation": animation_snapshot(source)}
    static = create_camera(scene, source, STATIC_NAME, STATIC_DATA, "STATIC")
    motion = create_camera(scene, source, MOTION_NAME, MOTION_DATA, "MOTION_AWARE")
    bake = []
    for frame in range(START_FRAME, END_FRAME + 1):
        scene.frame_set(frame)
        graph = bpy.context.evaluated_depsgraph_get()
        graph.update()
        source_location = source.evaluated_get(graph).matrix_world.translation.copy()
        motion_scale = smooth_scale(frame)
        set_camera(static, source_location, 2.0)
        set_camera(motion, source_location, motion_scale)
        for camera in (static, motion):
            camera.keyframe_insert(data_path="location", frame=frame, group="B62_D6_LOCATION")
            camera.keyframe_insert(data_path="rotation_quaternion", frame=frame, group="B62_D6_ROTATION")
        bake.append({"frame": frame, "sourceLocation": [float(value) for value in source_location], "staticScale": 2.0, "staticLocation": [float(value) for value in static.location], "staticQuaternion": [float(value) for value in static.rotation_quaternion], "motionScale": motion_scale, "motionLocation": [float(value) for value in motion.location], "motionQuaternion": [float(value) for value in motion.rotation_quaternion]})
    static_channels = finalize_action(static, STATIC_ACTION)
    motion_channels = finalize_action(motion, MOTION_ACTION)
    scene.frame_set(START_FRAME)
    after = {"objects": sorted(obj.name for obj in bpy.data.objects), "cameras": sorted(camera.name for camera in bpy.data.cameras), "actions": sorted(action.name for action in bpy.data.actions), "markers": [[marker.name, int(marker.frame), marker.camera.name if marker.camera else None] for marker in scene.timeline_markers], "sourceAnimation": animation_snapshot(source), "staticAnimation": animation_snapshot(static), "motionAnimation": animation_snapshot(motion)}
    require(after["markers"] == before["markers"] and after["sourceAnimation"] == before["sourceAnimation"], "source state drift")
    require(set(after["objects"]) - set(before["objects"]) == {STATIC_NAME, MOTION_NAME}, "object additions")
    require(set(after["cameras"]) - set(before["cameras"]) == {STATIC_DATA, MOTION_DATA}, "camera additions")
    require(set(after["actions"]) - set(before["actions"]) == {STATIC_ACTION, MOTION_ACTION}, "action additions")
    require(len(bake) == 96 and len(static_channels.fcurves) == 7 and len(motion_channels.fcurves) == 7, "bake count")
    output_scene = os.path.abspath(args.output_scene)
    os.makedirs(os.path.dirname(output_scene), exist_ok=True)
    require(not os.path.exists(output_scene), "output scene exists")
    bpy.ops.wm.save_as_mainfile(filepath=output_scene, check_existing=False)
    require(os.path.isfile(output_scene) and os.path.getsize(output_scene) > 0, "derived scene missing")
    report = durable_hashed(os.path.abspath(args.report), {"schemaVersion": "bfs.b62CameraQualityMotionAwareSceneBuild.v0.1", "experimentId": "B62-Q1-D6", "status": "PASS", "source": {"uri": "experiments/b62-phase0-v0-4/scene/B62_PHASE0_MASTER.blend", "sha256": args.master_sha256}, "derived": {"filepath": output_scene, "sha256": sha256_file(output_scene), "bytes": os.path.getsize(output_scene)}, "candidateId": "RS_S200_E225", "cameras": {"source": SOURCE_NAME, "static": STATIC_NAME, "motion": MOTION_NAME, "lensMillimeters": 65.0, "target": list(TARGET)}, "bake": bake, "stateBefore": before, "stateAfter": after, "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("utf-8")}, "operations": {"blenderStarts": 1, "sceneSaves": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0}}, "reportHash")
    print(f"BFS_B62_Q1_D6_BUILD PASS frames={len(bake)} scene={report['derived']['sha256']} report={report['reportHash']}")


if __name__ == "__main__":
    main()
