"""Build a physics-disabled Blender replay from a pinned B07 TrajectorySpec."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras import anim_utils


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--trajectory-sha256", required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate(document: dict, repository_root: Path) -> None:
    if document.get("documentType") != "BFS_TRAJECTORY_SPEC" or document.get("specVersion") != "0.1.0":
        raise RuntimeError("Unsupported TrajectorySpec")
    if document.get("targetObject") != "B06_PROP" or document.get("space") != "WORLD":
        raise RuntimeError("Undeclared trajectory target or space")
    samples = document.get("samples", [])
    if len(samples) != 132 or [item.get("frame") for item in samples] != list(range(1, 133)):
        raise RuntimeError("Trajectory samples must cover frames 1-132 exactly once in order")
    for item in samples:
        values = [*item["locationM"], *item["rotationQuaternionWxyz"]]
        if not all(math.isfinite(value) for value in values):
            raise RuntimeError("Trajectory contains a non-finite value")
        norm = math.sqrt(sum(value * value for value in item["rotationQuaternionWxyz"]))
        if abs(norm - 1.0) > 1e-6:
            raise RuntimeError(f"Trajectory quaternion is not normalized at frame {item['frame']}")
    source_path = (repository_root / document["source"]["evaluationUri"]).resolve()
    if repository_root.resolve() not in source_path.parents:
        raise RuntimeError("Trajectory source escapes repository")
    if sha256_bytes(source_path.read_bytes()) != document["source"]["evaluationSha256"]:
        raise RuntimeError("Trajectory source evaluation hash mismatch")


def animation_structure(obj: bpy.types.Object) -> list[dict]:
    bag = anim_utils.animdata_get_channelbag_for_assigned_slot(obj.animation_data)
    return [
        {
            "dataPath": curve.data_path, "arrayIndex": curve.array_index,
            "keys": [{"frame": round(point.co.x), "value": round(point.co.y, 9), "interpolation": point.interpolation} for point in curve.keyframe_points],
        }
        for curve in sorted(bag.fcurves, key=lambda item: (item.data_path, item.array_index))
    ]


def main() -> None:
    args = parse_args()
    bytes_value = args.trajectory.read_bytes()
    actual_sha = sha256_bytes(bytes_value)
    if actual_sha != args.trajectory_sha256:
        raise RuntimeError(f"Trajectory hash mismatch: expected {args.trajectory_sha256}, received {actual_sha}")
    document = json.loads(bytes_value)
    validate(document, args.repository_root)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end, scene.render.fps = 1, 132, 24
    bpy.ops.mesh.primitive_cube_add(size=1)
    prop = bpy.context.object
    prop.name = document["targetObject"]
    prop.scale = (0.10, 0.12, 0.14)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    prop.rotation_mode = "QUATERNION"
    prop["bfs_trajectory_sha256"] = actual_sha
    prop["bfs_selection_status"] = document["selectionStatus"]
    material = bpy.data.materials.new("MAT_B07_PROP")
    material.diffuse_color = (0.12, 0.42, 0.82, 1)
    material.use_nodes = True
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = material.diffuse_color
    prop.data.materials.append(material)
    for sample in document["samples"]:
        prop.location = sample["locationM"]
        prop.rotation_quaternion = sample["rotationQuaternionWxyz"]
        prop.keyframe_insert(data_path="location", frame=sample["frame"], group="B07_BAKED_WORLD")
        prop.keyframe_insert(data_path="rotation_quaternion", frame=sample["frame"], group="B07_BAKED_WORLD")
    bag = anim_utils.animdata_get_channelbag_for_assigned_slot(prop.animation_data)
    for curve in bag.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
    scene.frame_set(1)
    structure = {
        "documentType": "BFS_B07_REPLAY_STRUCTURE", "version": "0.1.0", "blender": bpy.app.version_string,
        "trajectorySha256": actual_sha, "sourceEvaluationSha256": document["source"]["evaluationSha256"],
        "target": prop.name, "dimensionsM": [round(value, 9) for value in prop.dimensions],
        "rigidBody": prop.rigid_body is not None, "parent": prop.parent.name if prop.parent else None,
        "constraints": len(prop.constraints), "drivers": len(prop.animation_data.drivers),
        "animation": animation_structure(prop), "selectionStatus": document["selectionStatus"],
    }
    structure_hash = sha256_bytes(canonical_json(structure).encode("utf-8"))
    report = {"structureHash": structure_hash, "structure": structure}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), check_existing=False, compress=True)
    args.manifest.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")
    print(f"BFS_B07_REPLAY_BUILD_OK {structure_hash} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B07_REPLAY_BUILD_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
