"""Generate and measure the B04 right-hand pickup action in Blender 5.2."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from bpy_extras import anim_utils

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_actor_benchmark import clear_scene, rounded, sha256_file


GENERATOR_VERSION = "0.1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", type=Path, required=True)
    parser.add_argument("--motion-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def palm_world(rig: bpy.types.Object, bone_name: str) -> list[float]:
    evaluated_rig = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    # The visible hand proxy is centred on the bone tail, so the benchmark's
    # PALM_R socket is the evaluated tail rather than the bone head/origin.
    return rounded(evaluated_rig.matrix_world @ evaluated_rig.pose.bones[bone_name].tail)


def main() -> None:
    args = parse_args()
    args.motion_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    clear_scene()
    with bpy.data.libraries.load(str(args.actor.resolve()), link=False, recursive=True) as (source, target):
        if "CHAR_B04" not in source.collections:
            raise RuntimeError("Actor library has no CHAR_B04 collection")
        target.collections = ["CHAR_B04"]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    rig = next(obj for obj in collection.all_objects if obj.name == "RIG_LEAD")
    hand = rig.pose.bones["hand.R"]
    hand.rotation_mode = "QUATERNION"

    # The values are pose-space channels. Their evaluated world-space result is
    # measured below and becomes the contract consumed by the B04 scene fixture.
    keys = [
        (1, (0.0, 0.0, 0.0)),
        (24, (0.0, 0.0, 0.0)),
        (36, (0.0, -0.05, 0.01)),
        (48, (0.0, -0.36, 0.055)),
        (108, (0.0, -0.82, 0.22)),
        (109, (0.0, -0.82, 0.22)),
        (120, (0.0, 0.0, 0.0)),
        (121, (0.0, 0.0, 0.0)),
        (144, (0.0, 0.0, 0.0)),
    ]
    for frame, location in keys:
        hand.location = location
        hand.keyframe_insert(data_path="location", frame=frame, group="B04_PICKUP_HAND_R")
    action = rig.animation_data.action
    action.name = "B04_RIGHT_HAND_PICKUP"
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(rig.animation_data)
    if not channelbag:
        raise RuntimeError("Blender did not create an Action channelbag")
    for curve in channelbag.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"

    scene = bpy.context.scene
    samples = []
    for frame in (1, 24, 36, 37, 47, 48, 49, 78, 108, 109, 121, 144):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        samples.append({"frame": frame, "palmWorldM": palm_world(rig, "hand.R")})
    start = next(sample["palmWorldM"] for sample in samples if sample["frame"] == 48)
    end = next(sample["palmWorldM"] for sample in samples if sample["frame"] == 108)
    transport = sum((a - b) ** 2 for a, b in zip(start, end)) ** 0.5

    bpy.data.libraries.write(str(args.motion_output), {action}, fake_user=True, compress=True)
    report = {
        "documentType": "BFS_B04_MOTION_GENERATION",
        "generatorVersion": GENERATOR_VERSION,
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "actor": {"path": str(args.actor), "sha256": sha256_file(args.actor)},
        "motion": {"path": str(args.motion_output), "sha256": sha256_file(args.motion_output), "action": action.name},
        "poseSpaceKeys": [{"frame": frame, "location": list(location), "interpolation": "LINEAR"} for frame, location in keys],
        "evaluatedSamples": samples,
        "holdTransportDistanceM": round(transport, 9),
        "thresholdM": 0.30,
        "pass": transport >= 0.30,
        "explicitNonClaims": [
            "This Action moves a technical hand proxy; it is not anatomical grasp animation.",
            "This isolated motion generation does not attach, collide, or evaluate the prop.",
        ],
    }
    args.report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["pass"]:
        raise RuntimeError(f"Hold transport {transport:.6f} m is below 0.30 m")
    print(f"BFS_B04_MOTION_OK {report['motion']['sha256']} {transport:.9f}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B04_MOTION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
