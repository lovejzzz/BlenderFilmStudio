"""Render a blind review clip of the exact selected B06 trajectory and colliders."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from bpy_extras import anim_utils
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--physics-manifest", type=Path, required=True)
    parser.add_argument("--physics-manifest-sha256", required=True)
    parser.add_argument("--trajectory-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--clip-id", default="CLIP_P84R")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def set_linear(obj: bpy.types.Object) -> None:
    bag = anim_utils.animdata_get_channelbag_for_assigned_slot(obj.animation_data)
    for curve in bag.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"


def collider(spec: dict) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name = spec["object"]
    obj.scale = spec["dimensionsM"]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    material = bpy.data.materials.new(f"MAT_REVIEW_{obj.name}")
    material.use_nodes = True
    material.diffuse_color = spec["color"]
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = spec["color"]
    material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.42
    obj.data.materials.append(material)
    for key in spec["locationKeys"]:
        obj.location = key["locationM"]
        obj.keyframe_insert(data_path="location", frame=key["frame"], group="B09_DECLARED_COLLIDER")
    set_linear(obj)
    return obj


def main() -> None:
    args = parse_args()
    manifest_sha = sha256_file(args.physics_manifest)
    if manifest_sha != args.physics_manifest_sha256:
        raise RuntimeError(f"Physics manifest hash mismatch: expected {args.physics_manifest_sha256}, received {manifest_sha}")
    manifest = json.loads(args.physics_manifest.read_text(encoding="utf-8"))
    if manifest.get("structureHash") != "e18e4d1d15f9f97890354ce5807f4bdce6ed9c74b507e17c8df0c77d14fdfb6e":
        raise RuntimeError("Unexpected B06 source structure")
    prop = bpy.data.objects.get("B06_PROP")
    if prop is None or prop.get("bfs_trajectory_sha256") != args.trajectory_sha256:
        raise RuntimeError("Compiled replay target or pinned trajectory is missing")
    if prop.rigid_body is not None or len(prop.constraints) or not prop.animation_data:
        raise RuntimeError("Review target must be the physics-disabled compiled replay")
    for name in ("B06_LEFT", "B06_RIGHT"):
        existing = bpy.data.objects.get(name)
        if existing:
            bpy.data.objects.remove(existing, do_unlink=True)
    colliders = [collider(spec) for spec in manifest["colliders"]]
    for obj in list(bpy.data.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("P84R_CAMERA_DATA")
    camera = bpy.data.objects.new("P84R_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.65, -1.35, 0.55)
    camera.data.lens = 45
    look_at(camera, Vector((0, 0, 0.12)))
    scene.camera = camera
    for name, location, energy, size in (
        ("P84R_KEY", (-0.4, -0.6, 0.9), 420, 0.8),
        ("P84R_FILL", (0.7, -0.3, 0.5), 240, 0.7),
    ):
        data = bpy.data.lights.new(name, type="AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        light = bpy.data.objects.new(name, data)
        light.location = location
        look_at(light, Vector((0, 0, 0.12)))
        scene.collection.objects.link(light)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("P84R_WORLD")
    scene.world.color = (0.004, 0.008, 0.015)
    scene.frame_start, scene.frame_end = 1, 116
    scene.render.fps, scene.render.fps_base = 24, 1
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.use_motion_blur = False
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 960, 540, 100
    scene.render.image_settings.media_type = "VIDEO"
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.audio_codec = "NONE"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(args.output.resolve())
    scene["bfs_review_clip_id"] = args.clip_id
    scene["bfs_review_source_manifest_sha256"] = manifest_sha
    result = bpy.ops.render.render(animation=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"Review render failed: {sorted(result)}")
    clip_sha = sha256_file(args.output)
    report = {
        "documentType": "BFS_B09_REVIEW_CLIP_GENERATION", "version": "0.1.0", "clipId": args.clip_id,
        "clip": {"uri": f"public/physics-review/{args.clip_id}.mp4", "sha256": clip_sha, "bytes": args.output.stat().st_size, "frameStart": 1, "frameEnd": 116, "fps": 24, "resolution": [960, 540]},
        "source": {"buildPlanHash": scene.get("bfs_plan_hash"), "trajectorySha256": args.trajectory_sha256, "physicsManifestSha256": manifest_sha, "physicsStructureSha256": manifest["structureHash"]},
        "render": {"physicsEnabled": False, "target": prop.name, "colliders": [item.name for item in colliders]},
        "blender": bpy.app.version_string,
    }
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B09_REVIEW_CLIP_OK {args.clip_id} {clip_sha} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B09_REVIEW_CLIP_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
