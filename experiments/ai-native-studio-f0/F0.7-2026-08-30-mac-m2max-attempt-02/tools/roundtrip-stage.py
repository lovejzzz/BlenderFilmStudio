import argparse
import hashlib
import json
import os
import struct
from pathlib import Path

import bpy


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    return sha_bytes(Path(path).read_bytes())


def f32(value):
    return struct.pack(">f", float(value)).hex()


def normalize_id_property(value):
    if hasattr(value, "keys"):
        return {
            str(key): normalize_id_property(value[key])
            for key in sorted(value.keys())
            if key != "_RNA_UI"
        }
    if isinstance(value, (list, tuple)) or type(value).__name__ == "IDPropertyArray":
        return [normalize_id_property(item) for item in value]
    if isinstance(value, float):
        return {"f32": f32(value)}
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def custom_properties(owner, include_film=False):
    result = {}
    for key in sorted(owner.keys()):
        if key == "_RNA_UI":
            continue
        if not include_film and str(key).startswith("film_studio"):
            continue
        result[str(key)] = normalize_id_property(owner[key])
    return result


def engine_family(engine):
    if engine in {"BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"}:
        return "EEVEE"
    return engine


def object_snapshot(obj):
    row = {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "matrixWorldF32": [[f32(value) for value in matrix_row] for matrix_row in obj.matrix_world],
        "hiddenRender": bool(obj.hide_render),
        "customProperties": custom_properties(obj),
    }
    if obj.type == "MESH":
        mesh = obj.data
        row["data"] = {
            "name": mesh.name,
            "verticesF32": [[f32(value) for value in vertex.co] for vertex in mesh.vertices],
            "edges": [[int(value) for value in edge.vertices] for edge in mesh.edges],
            "polygons": [
                {
                    "vertices": [int(value) for value in polygon.vertices],
                    "materialIndex": int(polygon.material_index),
                    "useSmooth": bool(polygon.use_smooth),
                }
                for polygon in mesh.polygons
            ],
            "materials": [material.name if material else None for material in mesh.materials],
            "customProperties": custom_properties(mesh),
        }
    elif obj.type == "CAMERA":
        camera = obj.data
        row["data"] = {
            "name": camera.name,
            "type": camera.type,
            "lensF32": f32(camera.lens),
            "sensorWidthF32": f32(camera.sensor_width),
            "clipStartF32": f32(camera.clip_start),
            "clipEndF32": f32(camera.clip_end),
            "customProperties": custom_properties(camera),
        }
    elif obj.type == "LIGHT":
        light = obj.data
        row["data"] = {
            "name": light.name,
            "type": light.type,
            "energyF32": f32(light.energy),
            "colorF32": [f32(value) for value in light.color],
            "customProperties": custom_properties(light),
        }
    elif obj.data is not None:
        row["data"] = {"name": obj.data.name, "customProperties": custom_properties(obj.data)}
    else:
        row["data"] = None
    return row


def core_snapshot(scene):
    world = scene.world
    snapshot = {
        "schemaVersion": "bfs.f0.7.coreSceneSemantic.v0.1",
        "scene": {
            "name": scene.name,
            "frameStart": int(scene.frame_start),
            "frameEnd": int(scene.frame_end),
            "frameCurrent": int(scene.frame_current),
            "camera": scene.camera.name if scene.camera else None,
            "render": {
                "engineFamily": engine_family(scene.render.engine),
                "resolutionX": int(scene.render.resolution_x),
                "resolutionY": int(scene.render.resolution_y),
                "resolutionPercentage": int(scene.render.resolution_percentage),
                "fps": int(scene.render.fps),
                "fpsBaseF32": f32(scene.render.fps_base),
                "filmTransparent": bool(scene.render.film_transparent),
                "fileFormat": scene.render.image_settings.file_format,
            },
            "view": {
                "viewTransform": scene.view_settings.view_transform,
                "look": scene.view_settings.look,
                "exposureF32": f32(scene.view_settings.exposure),
                "gammaF32": f32(scene.view_settings.gamma),
            },
            "units": {
                "system": scene.unit_settings.system,
                "scaleLengthF32": f32(scene.unit_settings.scale_length),
            },
            "customProperties": custom_properties(scene),
        },
        "world": None
        if world is None
        else {
            "name": world.name,
            "colorF32": [f32(value) for value in world.color],
            "useNodes": bool(world.use_nodes),
            "customProperties": custom_properties(world),
        },
        "objects": [object_snapshot(obj) for obj in sorted(scene.objects, key=lambda value: value.name)],
        "collections": [
            {
                "name": collection.name,
                "objects": sorted(obj.name for obj in collection.objects),
                "children": sorted(child.name for child in collection.children),
                "customProperties": custom_properties(collection),
            }
            for collection in sorted(bpy.data.collections, key=lambda value: value.name)
        ],
    }
    return snapshot


def metadata_snapshot(scene):
    present = "film_studio" in scene.keys()
    value = normalize_id_property(scene["film_studio"]) if present else None
    camera_metadata = {
        obj.name: {
            key: normalize_id_property(obj[key])
            for key in sorted(obj.keys())
            if str(key).startswith("film_studio")
        }
        for obj in sorted(scene.objects, key=lambda item: item.name)
        if any(str(key).startswith("film_studio") for key in obj.keys())
    }
    body = {"sceneFilmStudioPresent": present, "sceneFilmStudio": value, "cameraMetadata": camera_metadata}
    return {**body, "metadataSha256": sha_bytes(canonical(body).encode("utf-8")) if present or camera_metadata else None}


def resource_paths():
    result = {}
    for resource in ("CONFIG", "SCRIPTS", "DATAFILES", "EXTENSIONS"):
        try:
            result[resource] = bpy.utils.user_resource(resource)
        except Exception as error:
            result[resource] = f"UNAVAILABLE:{type(error).__name__}"
    return result


def set_eevee(scene):
    enum_items = scene.render.bl_rna.properties["engine"].enum_items
    identifiers = {item.identifier for item in enum_items}
    for identifier in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        if identifier in identifiers:
            scene.render.engine = identifier
            return
    raise RuntimeError(f"No EEVEE engine in {sorted(identifiers)}")


def create_core_scene(with_film_metadata):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "F07_ROUNDTRIP"
    scene.frame_start = 1
    scene.frame_end = 48
    scene.frame_set(1)
    scene.render.resolution_x = 320
    scene.render.resolution_y = 180
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.render.fps_base = 1.0
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    set_eevee(scene)
    scene["f07_core_marker"] = "ROUNDTRIP_CORE_V1"

    mesh = bpy.data.meshes.new("F07_HERO_MESH")
    mesh.from_pydata(
        [(-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (1.0, 1.0, 0.0), (-1.0, 1.0, 0.0), (0.0, 0.0, 2.0)],
        [],
        [(0, 1, 2, 3), (0, 4, 1), (1, 4, 2), (2, 4, 3), (3, 4, 0)],
    )
    mesh.update()
    hero = bpy.data.objects.new("F07_HERO", mesh)
    hero["f07_role"] = "hero"
    scene.collection.objects.link(hero)

    camera_data = bpy.data.cameras.new("F07_CAMERA_DATA")
    camera_data.lens = 50.0
    camera_data.sensor_width = 36.0
    camera = bpy.data.objects.new("F07_CAMERA", camera_data)
    camera.location = (6.0, -6.0, 4.0)
    camera.rotation_euler = (1.109319, 0.0, 0.785398)
    scene.collection.objects.link(camera)
    scene.camera = camera

    light_data = bpy.data.lights.new("F07_KEY_DATA", "AREA")
    light_data.energy = 750.0
    light_data.color = (1.0, 0.8, 0.6)
    light = bpy.data.objects.new("F07_KEY", light_data)
    light.location = (2.0, -2.0, 5.0)
    scene.collection.objects.link(light)

    marker = bpy.data.objects.new("F07_MARKER", None)
    marker.location = (-2.0, 1.0, 0.5)
    marker["f07_marker"] = 7
    scene.collection.objects.link(marker)

    world = bpy.data.worlds.new("F07_WORLD")
    world.use_nodes = False
    world.color = (0.02, 0.03, 0.05)
    scene.world = world

    if with_film_metadata:
        if not hasattr(scene, "film_studio"):
            raise RuntimeError("F0 typed Film Studio metadata is unavailable")
        state = scene.film_studio
        state.schema_version = "bfs.filmWorkspace.v0.1"
        state.project.identifier = "PRJ_F07"
        state.project.name = "F0.7 Round Trip"
        state.story_scene.identifier = "SC_F07"
        state.story_scene.name = "Package Round Trip"
        state.character.identifier = "CHR_F07"
        state.character.name = "Round Trip Witness"
        shot = state.shots.add()
        shot.identifier = "SH_F07"
        shot.name = "PACKAGE"
        shot.camera = camera
        state.active_shot_index = 0
        camera["film_studio_schema"] = "bfs.filmWorkspace.v0.1"
        camera["film_studio_kind"] = "Shot"
        camera["film_studio_identifier"] = "SH_F07"
    return scene


parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", required=True)
parser.add_argument("--stage", required=True)
parser.add_argument("--input")
parser.add_argument("--output")
parser.add_argument("--report", required=True)
parser.add_argument("--expected-core-hash")
parser.add_argument("--expected-metadata-hash")
args = parser.parse_args(os.sys.argv[os.sys.argv.index("--") + 1 :])

repository = Path(args.repository_root).resolve()
report_path = (repository / args.report).resolve()
input_path = (repository / args.input).resolve() if args.input else None
output_path = (repository / args.output).resolve() if args.output else None
for candidate in (report_path, output_path):
    if candidate is not None and candidate.exists():
        raise RuntimeError(f"Formal output already exists: {candidate}")
input_sha_before = sha_file(input_path) if input_path else None

if args.stage == "official-create":
    scene = create_core_scene(False)
elif args.stage == "f0-create":
    scene = create_core_scene(True)
else:
    if input_path is None or not input_path.is_file():
        raise RuntimeError("Input blend is missing")
    bpy.ops.wm.open_mainfile(filepath=str(input_path))
    scene = bpy.context.scene

metadata_before_save = metadata_snapshot(scene)
core = core_snapshot(scene)
core_hash = sha_bytes(canonical(core).encode("utf-8"))
if args.expected_core_hash and core_hash != args.expected_core_hash:
    raise RuntimeError(f"Core semantic mismatch: {core_hash} != {args.expected_core_hash}")
if args.expected_metadata_hash:
    observed = metadata_before_save["metadataSha256"]
    if observed not in {None, args.expected_metadata_hash}:
        raise RuntimeError(f"Optional metadata changed instead of being preserved or dropped: {observed}")

if output_path is not None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path), check_existing=False)
    if not output_path.is_file():
        raise RuntimeError("Blend output was not saved")

if input_path and sha_file(input_path) != input_sha_before:
    raise RuntimeError("Input blend changed")
metadata_after_save = metadata_snapshot(scene)
body = {
    "schemaVersion": "bfs.f0.7.roundtripStageReport.v0.1",
    "stage": args.stage,
    "status": "PASS",
    "runtime": {
        "version": bpy.app.version_string,
        "versionTuple": list(bpy.app.version),
        "buildHash": bpy.app.build_hash.decode("utf-8") if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
        "buildBranch": bpy.app.build_branch.decode("utf-8") if isinstance(bpy.app.build_branch, bytes) else str(bpy.app.build_branch),
        "platform": bpy.app.build_platform.decode("utf-8") if isinstance(bpy.app.build_platform, bytes) else str(bpy.app.build_platform),
    },
    "input": None if input_path is None else {"uri": args.input, "sha256BeforeAndAfter": input_sha_before},
    "output": None if output_path is None else {"uri": args.output, "bytes": output_path.stat().st_size, "sha256": sha_file(output_path)},
    "coreSemanticSha256": core_hash,
    "coreSemantic": core,
    "optionalMetadataBeforeSave": metadata_before_save,
    "optionalMetadataAfterSave": metadata_after_save,
    "missingOptionalMetadataGraceful": args.stage == "f0-open-official" and not metadata_before_save["sceneFilmStudioPresent"],
    "resourcePaths": resource_paths(),
    "renderCalls": 0,
    "mouseInteractions": 0,
}
record = {**body, "reportHash": sha_bytes(canonical(body).encode("utf-8"))}
report_path.parent.mkdir(parents=True, exist_ok=True)
with report_path.open("x", encoding="utf-8") as handle:
    json.dump(record, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
print(f"F07_STAGE PASS stage={args.stage} core={core_hash} metadata={metadata_before_save['metadataSha256']}", flush=True)
