"""Evaluate active-camera visibility for the compiled B05 grasp."""

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
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def triangle_centres(obj: bpy.types.Object, depsgraph: bpy.types.Depsgraph) -> list[Vector]:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        matrix = evaluated.matrix_world
        return [matrix @ (sum((mesh.vertices[index].co for index in triangle.vertices), Vector()) / 3.0) for triangle in mesh.loop_triangles]
    finally:
        evaluated.to_mesh_clear()


def sample_group(scene: bpy.types.Scene, depsgraph: bpy.types.Depsgraph, camera: bpy.types.Object, label: str, object_names: list[str]) -> dict:
    camera_origin = camera.matrix_world.translation
    accepted = set(object_names)
    total = in_frame = visible = 0
    occluders: Counter[str] = Counter()
    for object_name in object_names:
        for centre in triangle_centres(bpy.data.objects[object_name], depsgraph):
            total += 1
            projected = world_to_camera_view(scene, camera, centre)
            if projected.z <= 0 or not (0 <= projected.x <= 1 and 0 <= projected.y <= 1):
                occluders["OUT_OF_FRAME"] += 1
                continue
            in_frame += 1
            delta = centre - camera_origin
            distance = delta.length
            hit, _, _, _, hit_object, _ = scene.ray_cast(depsgraph, camera_origin, delta.normalized(), distance=distance + 0.002)
            if hit and hit_object and hit_object.name in accepted:
                visible += 1
            else:
                occluders[hit_object.name if hit and hit_object else "NO_HIT"] += 1
    return {
        "group": label, "objects": object_names, "triangleCentreSamples": total,
        "inFrameSamples": in_frame, "visibleSamples": visible,
        "inFrameFraction": in_frame / total if total else 0,
        "visibleFraction": visible / total if total else 0,
        "occluders": dict(sorted(occluders.items())),
    }


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    camera = scene.camera
    if camera is None:
        raise RuntimeError("Compiled scene has no active camera")
    finger_objects = sorted(obj.name for obj in bpy.data.objects if obj.name.startswith("MESH_THUMB_") or obj.name.startswith("MESH_INDEX_"))
    groups = {"FINGERS": finger_objects, "PROP": ["PROP_BODY"]}
    frames = []
    for frame in range(args.frame_start, args.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        frames.append({"frame": frame, "groups": [sample_group(scene, depsgraph, camera, label, names) for label, names in groups.items()]})

    summaries = []
    for label in groups:
        rows = [next(item for item in frame["groups"] if item["group"] == label) for frame in frames]
        minimum_in_frame = min(row["inFrameFraction"] for row in rows)
        minimum_visible = min(row["visibleFraction"] for row in rows)
        median_visible = median(row["visibleFraction"] for row in rows)
        gates = {
            "minimumInFrameAtLeast050": minimum_in_frame >= 0.50,
            "minimumVisibleAtLeast025": minimum_visible >= 0.25,
            "medianVisibleAtLeast035": median_visible >= 0.35,
        }
        summaries.append({
            "group": label,
            "minimumInFrameFraction": minimum_in_frame,
            "minimumVisibleFraction": minimum_visible,
            "medianVisibleFraction": median_visible,
            "gates": gates,
            "passed": all(gates.values()),
        })

    report = {
        "documentType": "BFS_B05_COMPILED_GRASP_VISIBILITY",
        "version": "0.1.0",
        "method": "EVALUATED_LOOP_TRIANGLE_CENTRES_ACTIVE_CAMERA_RAY_FIRST_HIT",
        "camera": {"name": camera.name, "locationM": list(camera.location), "rotationEulerRad": list(camera.rotation_euler), "lensMm": camera.data.lens},
        "frameWindow": {"start": args.frame_start, "end": args.frame_end, "count": args.frame_end - args.frame_start + 1},
        "summaries": summaries,
        "frames": frames,
        "visibilityGatePassed": all(summary["passed"] for summary in summaries),
        "explicitNonClaims": [
            "Triangle-centre camera-ray visibility is a geometric diagnostic, not a perceptual or cinematic-quality metric.",
            "The finger group accepts first hits on any member of the group and therefore does not measure self-occlusion between individual segments.",
            "Visibility does not establish anatomy, contact realism, weight, composition, or human acceptance.",
        ],
    }
    if any(math.isnan(summary["medianVisibleFraction"]) for summary in summaries):
        raise RuntimeError("Visibility summary contains NaN")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")
    print(f"BFS_B05_VISIBILITY {'PASS' if report['visibilityGatePassed'] else 'FAIL'} {args.output}")
    if not report["visibilityGatePassed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:
        print(f"BFS_B05_VISIBILITY_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
