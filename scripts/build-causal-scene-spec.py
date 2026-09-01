#!/usr/bin/env python3
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
BASE_TOOL_PATH = ROOT / "scripts/build-causal-studio.py"
loader_spec = importlib.util.spec_from_file_location("bfs_causal_base", BASE_TOOL_PATH)
base = importlib.util.module_from_spec(loader_spec)
loader_spec.loader.exec_module(base)

ALLOWED_FACTORIES = {"GROOVED_SPHERE", "BEVELED_DOMINO_BLOCK", "SIMPLE_WALL", "AREA_LIGHT", "CAMERA_FROM_DIRECTION_CLASS"}
DIRECTION_CAMERA = {
    "FRONT_LEFT_HIGH": ((-5.7, -6.6, 3.25), (0.0, 0.0, 0.58)),
    "FRONT_LEFT_LOW": ((-2.25, -4.6, 1.75), (0.05, 0.0, 0.62)),
    "FRONT_RIGHT_HIGH": ((3.9, -5.8, 2.75), (0.45, 0.0, 0.38)),
}
LIGHT_PLACEMENT = {
    "key_light": ((-2.7, -3.4, 5.8), (0.25, 0.0, 0.45), 3.2),
    "fill_light": ((4.2, -1.0, 3.2), (0.2, 0.0, 0.55), 4.2),
    "rim_light": ((1.7, 3.5, 4.7), (0.35, 0.0, 0.65), 2.5),
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["build", "reopen"], required=True)
    parser.add_argument("--preregistration", required=True)
    parser.add_argument("--scene-spec", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--evidence", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def validate_contract(prereg_path, scene_spec_path, work_root, evidence_root):
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    scene_spec = json.loads(scene_spec_path.read_text(encoding="utf-8"))
    if prereg["specHash"] != base.self_hash(prereg, "specHash"):
        raise RuntimeError("PREREGISTRATION_SELF_HASH")
    if scene_spec["sceneSpecHash"] != base.self_hash(scene_spec, "sceneSpecHash"):
        raise RuntimeError("SCENE_SPEC_SELF_HASH")
    holdout = prereg["holdoutSceneSpec"]
    if holdout["sceneSpecHash"] != scene_spec["sceneSpecHash"] or holdout["sha256"] != base.sha256_file(scene_spec_path):
        raise RuntimeError("HOLDOUT_BINDING")
    if Path(prereg["roots"]["work"]).resolve() != work_root:
        raise RuntimeError("WORK_ROOT_BINDING")
    if (ROOT / prereg["roots"]["evidence"]).resolve() != evidence_root:
        raise RuntimeError("EVIDENCE_ROOT_BINDING")
    observed = {scene_spec["dynamicActor"]["factory"], scene_spec["targetGroup"]["factory"], scene_spec["studio"]["backdrop"]["factory"], "AREA_LIGHT", "CAMERA_FROM_DIRECTION_CLASS"}
    if not observed.issubset(ALLOWED_FACTORIES):
        raise RuntimeError("FACTORY_ALLOWLIST")
    if scene_spec["targetGroup"]["count"] != len(scene_spec["targetGroup"]["initialPositions"]):
        raise RuntimeError("TARGET_CARDINALITY")
    if scene_spec["forbidden"] != {
        "acceptedBottleFactory": True,
        "acceptedBottleFinalCoordinates": True,
        "projectSpecificCameraCoordinates": True,
        "externalModelsOrTextures": True,
        "manualTargetOrFinalPoseAnimation": True,
    }:
        raise RuntimeError("FORBIDDEN_CONTRACT")
    return prereg, scene_spec


def add_wood_material(name, color):
    mat = base.material(name, tuple(color), 0.34, 0.0, 0.08)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.name = "Procedural_Wood_Grain"
    noise.inputs["Scale"].default_value = 7.5
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.62
    mapping = nodes.new("ShaderNodeMapping")
    texcoord = nodes.new("ShaderNodeTexCoord")
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.16
    bump.inputs["Distance"].default_value = 0.025
    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def create_actor(scene_spec, collection, dark_material):
    spec = scene_spec["dynamicActor"]
    if spec["factory"] != "GROOVED_SPHERE" or spec["count"] != 1:
        raise RuntimeError("ACTOR_FACTORY")
    radius = float(spec["radius"])
    location = tuple(float(value) for value in spec["initialPosition"])
    mat_spec = spec["material"]
    actor_mat = base.material("MAT_Actor_Blue_Rubber", tuple(mat_spec["baseColor"]), float(mat_spec["roughness"]))
    if mat_spec["proceduralGrain"]:
        nodes = actor_mat.node_tree.nodes
        links = actor_mat.node_tree.links
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 105.0
        noise.inputs["Detail"].default_value = 2.0
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.16
        bump.inputs["Distance"].default_value = 0.018
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], nodes.get("Principled BSDF").inputs["Normal"])
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=radius, location=location)
    actor = bpy.context.object
    actor.name = "ACTOR_001"
    actor.data.materials.append(actor_mat)
    base.smooth_object(actor)
    actor["semantic_role"] = "dynamic_actor"
    actor["factory"] = spec["factory"]
    actor["release_frame"] = int(scene_spec["timeline"]["releaseFrame"])
    actor["launch_mode"] = "KINEMATIC_TO_DYNAMIC_RIGID_BODY_RELEASE"
    seams = []
    rotations = [(0.0, 0.0, 0.0), (math.pi / 2.0, 0.0, 0.0), (0.0, math.pi / 2.0, 0.0)]
    if int(mat_spec["channelCount"]) != len(rotations):
        raise RuntimeError("CHANNEL_COUNT")
    for index, rotation in enumerate(rotations, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=radius + 0.002, minor_radius=0.009, major_segments=96, minor_segments=10, location=location, rotation=rotation)
        seam = bpy.context.object
        seam.name = f"DETAIL_Actor_Channel_{index:02d}"
        seam.data.materials.append(dark_material)
        seam["semantic_role"] = "modeling_detail"
        base.preserve_parent(seam, actor)
        seams.append(seam)
    rigid = spec["rigidBody"]
    body = base.add_rigid_body(actor, "ACTIVE", rigid["collisionShape"], float(rigid["mass"]), float(rigid["friction"]), float(rigid["restitution"]), float(rigid["linearDamping"]), float(rigid["angularDamping"]))
    body.kinematic = True
    for waypoint in spec["launchWaypoints"]:
        frame = int(waypoint["frame"])
        actor.location = tuple(float(value) for value in waypoint["position"])
        actor.rotation_euler = (0.0, float(waypoint["rotationY"]), 0.0)
        actor.keyframe_insert(data_path="location", frame=frame)
        actor.keyframe_insert(data_path="rotation_euler", frame=frame)
    body.kinematic = True
    actor.keyframe_insert(data_path="rigid_body.kinematic", frame=actor["release_frame"] - 1)
    body.kinematic = False
    actor.keyframe_insert(data_path="rigid_body.kinematic", frame=actor["release_frame"])
    for curve in base.action_fcurves(actor):
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
    return actor, seams


def create_domino(scene_spec, index, position, dark_material):
    spec = scene_spec["targetGroup"]
    dimensions = tuple(float(value) for value in spec["dimensions"])
    color = tuple(float(value) for value in spec["palette"][index - 1])
    body_mat = add_wood_material(f"MAT_Target_{index:02d}_Wood", color)
    panel_mat = base.material(f"MAT_Target_{index:02d}_Panel", tuple(min(1.0, value * 1.28) for value in color), 0.28, 0.0, 0.10)
    bpy.ops.mesh.primitive_cube_add(location=tuple(float(value) for value in position))
    target = bpy.context.object
    target.name = f"TARGET_{index:03d}"
    target.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    target.data.materials.append(body_mat)
    target["semantic_role"] = "target_group"
    target["factory"] = spec["factory"]
    target["target_index"] = index
    bevel = target.modifiers.new("Manufactured_Bevel", "BEVEL")
    bevel.width = float(spec["modeling"]["bevelWidth"])
    bevel.segments = int(spec["modeling"]["bevelSegments"])
    details = []
    if spec["modeling"]["insetFacePanel"]:
        bpy.ops.mesh.primitive_cube_add(location=(position[0], position[1] - dimensions[1] / 2.0 - 0.012, position[2]))
        panel = bpy.context.object
        panel.name = f"DETAIL_Target_{index:02d}_InsetPanel"
        panel.dimensions = (dimensions[0] * 0.72, 0.018, dimensions[2] * 0.44)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        panel.data.materials.append(panel_mat)
        panel["semantic_role"] = "modeling_detail"
        pbevel = panel.modifiers.new("Panel_Bevel", "BEVEL")
        pbevel.width = 0.018
        pbevel.segments = 3
        base.preserve_parent(panel, target)
        details.append(panel)
    if spec["modeling"]["edgeBand"]:
        bpy.ops.mesh.primitive_cube_add(location=(position[0], position[1], position[2] - dimensions[2] * 0.29))
        band = bpy.context.object
        band.name = f"DETAIL_Target_{index:02d}_EdgeBand"
        band.dimensions = (dimensions[0] + 0.012, dimensions[1] + 0.012, 0.055)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        band.data.materials.append(dark_material)
        band["semantic_role"] = "modeling_detail"
        base.preserve_parent(band, target)
        details.append(band)
    rigid = spec["rigidBody"]
    base.add_rigid_body(target, "ACTIVE", rigid["collisionShape"], float(rigid["mass"]), float(rigid["friction"]), float(rigid["restitution"]), float(rigid["linearDamping"]), float(rigid["angularDamping"]))
    return target, details


def create_cameras(scene_spec):
    cameras = {}
    for shot in scene_spec["shots"]:
        direction = shot["directionClass"]
        if direction not in DIRECTION_CAMERA:
            raise RuntimeError("CAMERA_DIRECTION_ALLOWLIST")
        location, target = DIRECTION_CAMERA[direction]
        cameras[shot["shotId"]] = base.create_camera(f"CAM_{shot['shotId']}", location, target, float(shot["lensMm"]))
    return cameras


def setup_scene(scene_spec):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    timeline = scene_spec["timeline"]
    scene.name = scene_spec["sceneId"]
    scene.frame_start = int(timeline["frameStart"])
    scene.frame_end = int(timeline["frameEnd"])
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.fps = int(timeline["fps"])
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("WORLD_CausalSceneSpec")
    scene.world.color = (0.012, 0.015, 0.025)
    scene.gravity = (0.0, 0.0, -9.81)
    try:
        bpy.context.preferences.filepaths.file_preview_type = "NONE"
    except Exception:
        pass
    dark = base.material("MAT_Dark_Detail", (0.015, 0.020, 0.028), 0.34, 0.08)
    floor_mat = base.material("MAT_StudioFloor", (0.105, 0.125, 0.155), 0.29)
    backdrop_mat = base.material("MAT_StudioBackdrop", (0.055, 0.070, 0.105), 0.42)
    floor, backdrop = base.create_floor_and_backdrop({"floor": floor_mat, "backdrop": backdrop_mat})
    actor_collection = bpy.data.collections.new("COL_SEMANTIC_ACTORS")
    scene.collection.children.link(actor_collection)
    actor, actor_details = create_actor(scene_spec, actor_collection, dark)
    targets, target_details = [], []
    target_spec = scene_spec["targetGroup"]
    if target_spec["factory"] != "BEVELED_DOMINO_BLOCK":
        raise RuntimeError("TARGET_FACTORY")
    for index, position in enumerate(target_spec["initialPositions"], 1):
        target, details = create_domino(scene_spec, index, position, dark)
        targets.append(target)
        target_details.extend(details)
    cameras = create_cameras(scene_spec)
    lights = []
    for light_spec in scene_spec["studio"]["lights"]:
        role = light_spec["semanticRole"]
        if role not in LIGHT_PLACEMENT or light_spec["kind"] != "AREA":
            raise RuntimeError("LIGHT_ALLOWLIST")
        location, target, size = LIGHT_PLACEMENT[role]
        lights.append(base.create_area_light(f"LIGHT_{role}", role, location, target, float(light_spec["energy"]), tuple(light_spec["color"]), size))
    if scene.rigidbody_world:
        scene.rigidbody_world.substeps_per_frame = 10
        scene.rigidbody_world.solver_iterations = 40
        scene.rigidbody_world.point_cache.frame_start = scene.frame_start
        scene.rigidbody_world.point_cache.frame_end = scene.frame_end
    scene["scene_spec_hash"] = scene_spec["sceneSpecHash"]
    scene["scene_id"] = scene_spec["sceneId"]
    return scene, actor, targets, cameras, lights, floor, backdrop, actor_details, target_details


def aabb(obj):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return Vector((min(p.x for p in corners), min(p.y for p in corners), min(p.z for p in corners))), Vector((max(p.x for p in corners), max(p.y for p in corners), max(p.z for p in corners)))


def pair_clearance(left, right):
    lmin, lmax = aabb(left)
    rmin, rmax = aabb(right)
    separations = [max(rmin[i] - lmax[i], lmin[i] - rmax[i], 0.0) for i in range(3)]
    if any(value > 0.0 for value in separations):
        return Vector(separations).length
    overlaps = [min(lmax[i], rmax[i]) - max(lmin[i], rmin[i]) for i in range(3)]
    return -min(overlaps)


def initial_clearances(actor, targets):
    objects = [actor, *targets]
    rows = []
    for index, left in enumerate(objects):
        for right in objects[index + 1:]:
            rows.append({"pair": [left.name, right.name], "meters": round(pair_clearance(left, right), 8)})
    return rows


def inventory(scene_spec, actor, targets, details, cameras, lights, floor, backdrop):
    frames = {}
    for obj in [actor, *targets]:
        frames[obj.name] = sorted({int(round(point.co.x)) for curve in base.action_fcurves(obj) for point in curve.keyframe_points})
    release = int(actor["release_frame"])
    return {
        "semanticObjects": {"dynamic_actor": [actor.name], "target_group": [obj.name for obj in targets], "ground": [floor.name], "studio_environment": [backdrop.name], "camera": [obj.name for obj in cameras.values()], "lights": [obj.name for obj in lights]},
        "factories": {"dynamic_actor": actor["factory"], "target_group": scene_spec["targetGroup"]["factory"], "targetCountFromSpec": len(targets)},
        "proceduralModeling": {"actorChannelCount": int(scene_spec["dynamicActor"]["material"]["channelCount"]), "targetDetailObjectCount": len(details), "targetFeatures": ["bevel", "insetFacePanel", "edgeBand", "proceduralWoodGrain"]},
        "authoredKeyframeFrames": frames,
        "dynamicFinalPoseKeyframes": {actor.name: any(frame > release for frame in frames[actor.name]), **{obj.name: len(frames[obj.name]) > 0 for obj in targets}},
        "launch": {"mode": actor["launch_mode"], "releaseFrame": release, "postReleasePoseKeyframes": 0},
        "rigidBodies": {obj.name: {"type": obj.rigid_body.type, "shape": obj.rigid_body.collision_shape, "mass": obj.rigid_body.mass} for obj in [actor, *targets, floor]},
        "externalImages": [image.filepath for image in bpy.data.images if image.source == "FILE" and image.filepath],
        "externalLibraries": [library.filepath for library in bpy.data.libraries],
    }


def main():
    args = parse_args()
    prereg_path = Path(args.preregistration).resolve()
    scene_spec_path = Path(args.scene_spec).resolve()
    work_root = Path(args.work).resolve()
    evidence_root = Path(args.evidence).resolve()
    prereg, scene_spec = validate_contract(prereg_path, scene_spec_path, work_root, evidence_root)
    blend_path = work_root / "PC5_G1_CAUSAL_SCENE.blend"
    if args.mode == "build":
        scene, actor, targets, cameras, lights, floor, backdrop, actor_details, target_details = setup_scene(scene_spec)
        clearances = initial_clearances(actor, targets)
        scene.frame_set(scene.frame_start)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
        physics = base.simulate(scene, actor, targets)
        narrative = [actor, *targets, *actor_details, *target_details]
        reviews = base.render_reviews(scene, cameras, physics, evidence_root, narrative)
        report = base.write_record(evidence_root / "build.json", {
            "schemaVersion": "bfs.causalSceneSpecBuild.v0.1",
            "status": "COMPLETE",
            "preregistrationHash": prereg["specHash"],
            "sceneSpecHash": scene_spec["sceneSpecHash"],
            "blender": {"version": bpy.app.version_string, "binary": bpy.app.binary_path},
            "scene": {"sceneId": scene_spec["sceneId"], "frameStart": scene.frame_start, "frameEnd": scene.frame_end, "fps": scene.render.fps, "physicsEngine": "BLENDER_BULLET_RIGID_BODY"},
            "blend": {"path": str(blend_path), "sha256": base.sha256_file(blend_path), "bytes": blend_path.stat().st_size},
            "initialClearances": clearances,
            "inventory": inventory(scene_spec, actor, targets, [*actor_details, *target_details], cameras, lights, floor, backdrop),
            "physics": physics,
            "reviews": reviews,
        }, "buildHash")
        print(f"BFS_CAUSAL_SCENE_SPEC_BUILD COMPLETE {report['buildHash']}")
    else:
        scene = bpy.context.scene
        if scene.get("scene_spec_hash") != scene_spec["sceneSpecHash"]:
            raise RuntimeError("REOPEN_SCENE_SPEC_BINDING")
        actor = next(obj for obj in bpy.data.objects if obj.get("semantic_role") == "dynamic_actor")
        targets = sorted([obj for obj in bpy.data.objects if obj.get("semantic_role") == "target_group"], key=lambda obj: obj.name)
        if len(targets) != int(scene_spec["targetGroup"]["count"]):
            raise RuntimeError("REOPEN_TARGET_CARDINALITY")
        physics = base.simulate(scene, actor, targets)
        report = base.write_record(evidence_root / "reopen.json", {
            "schemaVersion": "bfs.causalSceneSpecReopen.v0.1",
            "status": "COMPLETE",
            "preregistrationHash": prereg["specHash"],
            "sceneSpecHash": scene_spec["sceneSpecHash"],
            "sourceBlend": {"path": str(blend_path), "sha256": base.sha256_file(blend_path)},
            "physics": physics,
        }, "reopenHash")
        print(f"BFS_CAUSAL_SCENE_SPEC_REOPEN COMPLETE {report['reopenHash']}")


if __name__ == "__main__":
    main()
