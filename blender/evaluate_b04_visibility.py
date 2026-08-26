"""Evaluate whether the B04 review camera visibly exposes the contact pair."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from statistics import median

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frame-start", type=int, default=49)
    parser.add_argument("--frame-end", type=int, default=108)
    parser.add_argument("--camera-location", nargs=3, type=float, default=(2.45, -4.3, 1.85))
    parser.add_argument("--look-at", nargs=3, type=float, default=(-0.05, 0.02, 1.30))
    parser.add_argument("--lens", type=float, default=62.0)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def triangle_centres(obj: bpy.types.Object, depsgraph: bpy.types.Depsgraph) -> list[Vector]:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        matrix = evaluated.matrix_world
        return [matrix @ (sum((mesh.vertices[index].co for index in triangle.vertices), Vector()) / 3.0) for triangle in mesh.loop_triangles]
    finally:
        evaluated.to_mesh_clear()


def sample_object(scene: bpy.types.Scene, depsgraph: bpy.types.Depsgraph, camera: bpy.types.Object, object_name: str) -> dict:
    obj = bpy.data.objects[object_name]
    centres = triangle_centres(obj, depsgraph)
    camera_origin = camera.matrix_world.translation
    in_frame = 0
    visible = 0
    occluders: Counter[str] = Counter()
    for centre in centres:
        projected = world_to_camera_view(scene, camera, centre)
        if projected.z <= 0 or not (0 <= projected.x <= 1 and 0 <= projected.y <= 1):
            occluders["OUT_OF_FRAME"] += 1
            continue
        in_frame += 1
        delta = centre - camera_origin
        distance = delta.length
        hit, _, _, _, hit_object, _ = scene.ray_cast(depsgraph, camera_origin, delta.normalized(), distance=distance + 0.002)
        if hit and hit_object and hit_object.name == object_name:
            visible += 1
        else:
            occluders[hit_object.name if hit and hit_object else "NO_HIT"] += 1
    total = len(centres)
    return {
        "object": object_name,
        "triangleCentreSamples": total,
        "inFrameSamples": in_frame,
        "visibleSamples": visible,
        "inFrameFraction": in_frame / total if total else 0,
        "visibleFraction": visible / total if total else 0,
        "occluders": dict(sorted(occluders.items())),
    }


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    camera = scene.camera
    camera.location = args.camera_location
    camera.data.lens = args.lens
    look_at(camera, Vector(args.look_at))
    frames = []
    for frame in range(args.frame_start, args.frame_end + 1):
        scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        frames.append({
            "frame": frame,
            "objects": [sample_object(scene, depsgraph, camera, name) for name in ("HAND_R", "PROP_BODY")],
        })

    summaries = []
    for name in ("HAND_R", "PROP_BODY"):
        rows = [next(item for item in frame["objects"] if item["object"] == name) for frame in frames]
        minimum_in_frame = min(row["inFrameFraction"] for row in rows)
        minimum_visible = min(row["visibleFraction"] for row in rows)
        median_visible = median(row["visibleFraction"] for row in rows)
        gates = {
            "minimumInFrameAtLeast050": minimum_in_frame >= 0.50,
            "minimumVisibleAtLeast025": minimum_visible >= 0.25,
            "medianVisibleAtLeast035": median_visible >= 0.35,
        }
        summaries.append({
            "object": name,
            "minimumInFrameFraction": minimum_in_frame,
            "minimumVisibleFraction": minimum_visible,
            "medianVisibleFraction": median_visible,
            "gates": gates,
            "passed": all(gates.values()),
        })

    report = {
        "documentType": "BFS_B04_CONTACT_VISIBILITY_DIAGNOSTIC",
        "version": "0.1.0",
        "method": "EVALUATED_LOOP_TRIANGLE_CENTRES_CAMERA_RAY_FIRST_HIT",
        "camera": {
            "locationM": list(args.camera_location),
            "lookAtM": list(args.look_at),
            "lensMm": args.lens,
        },
        "frameWindow": {"start": args.frame_start, "end": args.frame_end, "count": args.frame_end - args.frame_start + 1},
        "summaries": summaries,
        "frames": frames,
        "visibilityGatePassed": all(summary["passed"] for summary in summaries),
        "explicitNonClaims": [
            "Triangle-centre visibility is not a perceptual visibility metric.",
            "This diagnostic does not establish composition, acting, contact quality or human acceptance.",
        ],
    }
    if any(math.isnan(summary["medianVisibleFraction"]) for summary in summaries):
        raise RuntimeError("Visibility summary contains NaN")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")
    print(f"BFS_B04_VISIBILITY {'PASS' if report['visibilityGatePassed'] else 'FAIL'} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B04_VISIBILITY_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
