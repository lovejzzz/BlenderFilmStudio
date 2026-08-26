"""Compile one verified BFS BuildPlan into a Blender 5.2 scene.

The runtime accepts data only. It never imports or executes code from a
SceneSpec or asset library, and it re-verifies both the plan and asset hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy
import PyOpenColorIO as ocio
from bpy_extras import anim_utils


COMPILER_VERSION = "0.1.0"


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def resolve_below(root: Path, candidate: Path, label: str) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve() if candidate.is_absolute() else (resolved_root / candidate).resolve()
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise RuntimeError(f"{label} escapes the repository root: {candidate}")
    return resolved


def load_verified_plan(plan_path: Path) -> dict:
    wrapper = json.loads(plan_path.read_text(encoding="utf-8"))
    if wrapper.get("documentType") != "BFS_BUILD_PLAN" or wrapper.get("planVersion") != "0.1.0":
        raise RuntimeError("Unsupported BuildPlan document or version")
    actual_hash = sha256_bytes(canonical_json(wrapper["plan"]).encode("utf-8"))
    if actual_hash != wrapper.get("planHash"):
        raise RuntimeError(f"BuildPlan hash mismatch: expected {wrapper.get('planHash')}, received {actual_hash}")
    if tuple(bpy.app.version[:3]) != (5, 2, 0):
        raise RuntimeError(f"Blender 5.2.0 is required, received {bpy.app.version_string}")
    if wrapper["plan"]["compiler"]["version"] != COMPILER_VERSION:
        raise RuntimeError("Compiler version does not match BuildPlan")
    return wrapper


def clear_scene(scene: bpy.types.Scene) -> bpy.types.Collection:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for camera in list(bpy.data.cameras):
        bpy.data.cameras.remove(camera)
    for light in list(bpy.data.lights):
        bpy.data.lights.remove(light)
    managed = bpy.data.collections.new("BFS_SHOT")
    scene.collection.children.link(managed)
    return managed


def apply_transform(obj: bpy.types.Object, transform: dict) -> None:
    obj.location = transform["locationM"]
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = [math.radians(value) for value in transform["rotationEulerDeg"]]
    obj.scale = transform["scale"]


def append_asset(root: Path, managed: bpy.types.Collection, asset: dict) -> bpy.types.Object:
    asset_path = resolve_below(root, Path(asset["uri"]), f"Asset {asset['id']}")
    actual_hash = sha256_file(asset_path)
    if actual_hash != asset["verifiedSha256"] or actual_hash != asset["sha256"]:
        raise RuntimeError(f"Asset hash mismatch during Blender compile: {asset['id']}")
    with bpy.data.libraries.load(str(asset_path), link=False, recursive=True) as (source, target):
        if asset["id"] not in source.collections:
            raise RuntimeError(f"Asset library {asset['uri']} has no collection named {asset['id']}")
        target.collections = [asset["id"]]
    imported = target.collections[0]
    if imported is None:
        raise RuntimeError(f"Blender could not append collection {asset['id']}")
    instance = bpy.data.objects.new(asset["id"], None)
    instance.instance_type = "COLLECTION"
    instance.instance_collection = imported
    instance.hide_render = not asset["visible"]
    instance["bfs_asset_sha256"] = actual_hash
    instance["bfs_asset_version"] = asset["version"]
    apply_transform(instance, asset["transform"])
    managed.objects.link(instance)
    return instance


def create_camera(managed: bpy.types.Collection, camera_spec: dict) -> bpy.types.Object:
    camera = bpy.data.cameras.new(f"{camera_spec['id']}_DATA")
    camera.lens = camera_spec["lensMm"]
    camera.sensor_width = camera_spec["sensorWidthMm"]
    camera.dof.use_dof = True
    camera.dof.aperture_fstop = camera_spec["apertureFStop"]
    camera.dof.focus_distance = camera_spec["focusDistanceM"]
    obj = bpy.data.objects.new(camera_spec["id"], camera)
    obj["bfs_shutter_angle_deg"] = camera_spec["shutterAngleDeg"]
    apply_transform(obj, camera_spec["transform"])
    managed.objects.link(obj)

    for key in camera_spec.get("transformKeys", []):
        apply_transform(obj, key["transform"])
        for data_path in ("location", "rotation_euler", "scale"):
            obj.keyframe_insert(data_path=data_path, frame=key["frame"], group="BFS_TRANSFORM")
    if camera_spec.get("transformKeys") and obj.animation_data and obj.animation_data.action:
        channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(obj.animation_data)
        curves = channelbag.fcurves if channelbag else []
        interpolation_by_frame = {key["frame"]: key["interpolation"] for key in camera_spec["transformKeys"]}
        for curve in curves:
            for point in curve.keyframe_points:
                point.interpolation = interpolation_by_frame.get(round(point.co.x), "LINEAR")
    if camera_spec.get("transformKeys"):
        apply_transform(obj, camera_spec["transformKeys"][0]["transform"])
    return obj


def create_light(managed: bpy.types.Collection, light_spec: dict) -> bpy.types.Object:
    light = bpy.data.lights.new(f"{light_spec['id']}_DATA", light_spec["type"])
    light.color = light_spec["colorLinear"]
    light.energy = light_spec["energy"]
    if light_spec["type"] == "AREA":
        light.shape = "DISK"
        light.size = light_spec["sizeM"]
    elif light_spec["type"] in {"POINT", "SPOT"}:
        light.shadow_soft_size = light_spec["sizeM"] / 2
    elif light_spec["type"] == "SUN":
        light.angle = min(light_spec["sizeM"], math.pi)
    obj = bpy.data.objects.new(light_spec["id"], light)
    apply_transform(obj, light_spec["transform"])
    managed.objects.link(obj)
    return obj


def configure_world(scene: bpy.types.Scene, world_spec: dict) -> None:
    world = bpy.data.worlds.new("BFS_WORLD")
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (*world_spec["backgroundLinear"], 1.0)
    background.inputs["Strength"].default_value = world_spec["strength"]
    scene.world = world


def configure_render(scene: bpy.types.Scene, render_spec: dict, output_spec: dict, active_camera: dict, artifact_root: Path) -> list[str]:
    warnings = []
    scene.render.engine = render_spec["finalEngine"]
    scene.render.resolution_x = render_spec["resolution"]["width"]
    scene.render.resolution_y = render_spec["resolution"]["height"]
    scene.render.resolution_percentage = render_spec["resolution"]["percentage"]
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.render.image_settings.exr_codec = "ZIP"
    scene.render.filepath = str(artifact_root / "frames" / "frame_")
    scene.render.motion_blur_shutter = active_camera["shutterAngleDeg"] / 360.0
    scene.render.motion_blur_position = "CENTER"
    scene.cycles.samples = render_spec["samplesFinal"]
    scene.cycles.seed = int(scene.get("bfs_shot_seed", 0))
    scene.cycles.use_animated_seed = False
    scene.cycles.device = "CPU"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 8

    view_layer = scene.view_layers[0]
    view_layer.name = "BFS_MASTER"
    view_layer.use_pass_z = "Depth" in render_spec["passes"]
    view_layer.use_pass_normal = "Normal" in render_spec["passes"]
    view_layer.use_pass_vector = "Vector" in render_spec["passes"]
    view_layer.use_pass_cryptomatte_object = "Cryptomatte" in render_spec["passes"]
    view_layer.pass_cryptomatte_depth = 6
    if hasattr(view_layer, "cycles"):
        view_layer.cycles.use_denoising = render_spec["denoise"]

    color_spec = output_spec["color"]
    current_config = ocio.GetCurrentConfig()
    current_name = current_config.getName()
    current_scene_linear = current_config.getRoleColorSpace(ocio.ROLE_SCENE_LINEAR)
    if current_name != color_spec["ocioConfigName"]:
        raise RuntimeError(f"OCIO config mismatch: expected {color_spec['ocioConfigName']}, received {current_name}")
    if current_scene_linear != color_spec["sceneLinearRole"]:
        raise RuntimeError(f"OCIO scene-linear role mismatch: expected {color_spec['sceneLinearRole']}, received {current_scene_linear}")
    review = next(item for item in color_spec["displayTransforms"] if item["id"] == "REVIEW_SDR")
    scene.display_settings.display_device = review["display"]
    scene.view_settings.view_transform = review["view"]
    scene["bfs_output_profile"] = render_spec["outputProfile"]
    scene["bfs_declared_encoding"] = color_spec["sceneLinearEncoding"]
    scene["bfs_ocio_config"] = current_name
    scene["bfs_ocio_sha256"] = color_spec["verifiedOcioConfigSha256"]
    scene["bfs_ocio_status"] = "PINNED_AND_VERIFIED"
    warnings.append("ACES 2 OCIO config is pinned and verified; the physical review display is not yet calibrated by this experiment.")
    return warnings


def rounded(values) -> list[float]:
    return [round(float(value), 9) for value in values]


def collection_structure(collection: bpy.types.Collection) -> dict:
    objects = []
    for obj in sorted(collection.all_objects, key=lambda item: item.name):
        record = {
            "name": obj.name,
            "type": obj.type,
            "location": rounded(obj.location),
            "rotationEuler": rounded(obj.rotation_euler),
            "scale": rounded(obj.scale),
            "materials": sorted(slot.material.name for slot in obj.material_slots if slot.material),
        }
        if obj.type == "MESH":
            record["mesh"] = {"vertices": len(obj.data.vertices), "edges": len(obj.data.edges), "polygons": len(obj.data.polygons)}
        objects.append(record)
    return {"name": collection.name, "objects": objects}


def evaluated_camera_samples(scene: bpy.types.Scene, camera_objects: dict[str, bpy.types.Object], cameras: list[dict]) -> list[dict]:
    samples = []
    for camera in cameras:
        obj = camera_objects[camera["id"]]
        key_frames = [key["frame"] for key in camera.get("transformKeys", [])]
        midpoint_frames = [math.floor((left + right) / 2) for left, right in zip(key_frames, key_frames[1:])]
        frames = sorted(set(key_frames + midpoint_frames)) or [scene.frame_start]
        for frame in frames:
            scene.frame_set(frame)
            samples.append({
                "camera": camera["id"],
                "frame": frame,
                "location": rounded(obj.location),
                "rotationEuler": rounded(obj.rotation_euler),
                "scale": rounded(obj.scale),
            })
    scene.frame_set(scene.frame_start)
    return samples


def animation_structure(obj: bpy.types.Object) -> list[dict]:
    if not obj.animation_data or not obj.animation_data.action:
        return []
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(obj.animation_data)
    if channelbag is None:
        return []
    result = []
    for curve in sorted(channelbag.fcurves, key=lambda item: (item.data_path, item.array_index)):
        result.append({
            "dataPath": curve.data_path,
            "arrayIndex": curve.array_index,
            "keyframes": [
                {
                    "frame": round(float(point.co.x), 9),
                    "value": round(float(point.co.y), 9),
                    "interpolation": point.interpolation,
                }
                for point in curve.keyframe_points
            ],
        })
    return result


def build_structure(scene: bpy.types.Scene, wrapper: dict, asset_collections: dict[str, bpy.types.Collection], camera_objects: dict[str, bpy.types.Object]) -> dict:
    plan = wrapper["plan"]
    managed = bpy.data.collections["BFS_SHOT"]
    managed_objects = []
    for obj in sorted(managed.objects, key=lambda item: item.name):
        record = {
            "name": obj.name,
            "type": obj.type,
            "location": rounded(obj.location),
            "rotationEuler": rounded(obj.rotation_euler),
            "scale": rounded(obj.scale),
        }
        if obj.type == "CAMERA":
            record["camera"] = {
                "lensMm": round(obj.data.lens, 9),
                "sensorWidthMm": round(obj.data.sensor_width, 9),
                "focusDistanceM": round(obj.data.dof.focus_distance, 9),
                "apertureFStop": round(obj.data.dof.aperture_fstop, 9),
            }
            record["animation"] = animation_structure(obj)
        elif obj.type == "LIGHT":
            record["light"] = {"type": obj.data.type, "energy": round(obj.data.energy, 9), "color": rounded(obj.data.color)}
        elif obj.instance_collection:
            record["instanceCollection"] = obj.instance_collection.name
        managed_objects.append(record)

    return {
        "compilerVersion": COMPILER_VERSION,
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "planHash": wrapper["planHash"],
        "shot": plan["shot"],
        "managedCollection": {"name": managed.name, "objects": managed_objects},
        "assetCollections": [collection_structure(asset_collections[key]) for key in sorted(asset_collections)],
        "cameraSamples": evaluated_camera_samples(scene, camera_objects, plan["cameras"]),
        "render": {
            "engine": scene.render.engine,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
            "fps": scene.render.fps,
            "fpsBase": scene.render.fps_base,
            "frameRange": [scene.frame_start, scene.frame_end],
            "fileFormat": scene.render.image_settings.file_format,
            "colorDepth": scene.render.image_settings.color_depth,
            "exrCodec": scene.render.image_settings.exr_codec,
            "cyclesSamples": scene.cycles.samples,
            "cyclesSeed": scene.cycles.seed,
            "cyclesAnimatedSeed": scene.cycles.use_animated_seed,
            "cyclesDevice": scene.cycles.device,
            "threadsMode": scene.render.threads_mode,
            "threads": scene.render.threads,
            "ocioConfig": scene["bfs_ocio_config"],
            "ocioConfigSha256": scene["bfs_ocio_sha256"],
            "sceneLinearRole": scene["bfs_declared_encoding"],
            "display": scene.display_settings.display_device,
            "view": scene.view_settings.view_transform,
        },
    }


def main() -> None:
    started = time.perf_counter()
    args = parse_args()
    repository_root = args.repository_root.resolve()
    plan_path = resolve_below(repository_root, args.plan, "BuildPlan")
    wrapper = load_verified_plan(plan_path)
    plan = wrapper["plan"]
    planned_root = resolve_below(repository_root, Path(plan["outputs"]["root"]), "Planned output")
    artifact_root = resolve_below(repository_root, args.output_dir, "Experiment output") if args.output_dir else planned_root
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "frames").mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    managed = clear_scene(scene)
    scene.name = plan["shot"]["id"]
    scene.frame_start = plan["shot"]["frameStart"]
    scene.frame_end = plan["shot"]["frameEnd"]
    scene.render.fps = plan["shot"]["frameRate"]["numerator"]
    scene.render.fps_base = plan["shot"]["frameRate"]["denominator"]
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = plan["shot"]["unitScaleMeters"]
    scene["bfs_plan_hash"] = wrapper["planHash"]
    scene["bfs_scene_spec_hash"] = plan["source"]["canonicalSha256"]
    scene["bfs_shot_seed"] = plan["shot"]["seed"]

    asset_collections = {}
    for asset in plan["assets"]:
        instance = append_asset(repository_root, managed, asset)
        asset_collections[asset["id"]] = instance.instance_collection

    camera_objects = {camera["id"]: create_camera(managed, camera) for camera in plan["cameras"]}
    for light in plan["lights"]:
        create_light(managed, light)
    configure_world(scene, plan["world"])
    scene.camera = camera_objects[plan["shot"]["activeCamera"]]
    warnings = configure_render(scene, plan["render"], plan["outputSpec"], next(camera for camera in plan["cameras"] if camera["id"] == plan["shot"]["activeCamera"]), artifact_root)

    structure = build_structure(scene, wrapper, asset_collections, camera_objects)
    structure_hash = sha256_bytes(canonical_json(structure).encode("utf-8"))
    blend_path = artifact_root / "scene.blend"
    save_result = bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False, compress=True, relative_remap=True)
    if "FINISHED" not in save_result:
        raise RuntimeError(f"Blender save failed: {sorted(save_result)}")

    manifest = {
        "documentType": "BFS_SCENE_MANIFEST",
        "manifestVersion": "0.1.0",
        "structureHash": structure_hash,
        "structure": structure,
        "warnings": warnings,
        "telemetry": {
            "compileSeconds": round(time.perf_counter() - started, 6),
            "blendBytes": blend_path.stat().st_size,
        },
    }
    manifest_path = artifact_root / "scene.manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_COMPILE_OK {plan['shot']['id']} {wrapper['planHash']} {structure_hash} {manifest_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_COMPILE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
