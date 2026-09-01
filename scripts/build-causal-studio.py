#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def self_hash(value, field):
    body = {key: row for key, row in value.items() if key != field}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


def write_record(path, body, field):
    value = dict(body)
    value[field] = self_hash(value, field)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return value


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def set_input(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def material(name, color, roughness=0.35, metallic=0.0, coat=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    set_input(bsdf, "Base Color", (*color, 1.0))
    set_input(bsdf, "Roughness", roughness)
    set_input(bsdf, "Metallic", metallic)
    set_input(bsdf, "Coat Weight", coat)
    return mat


def ball_material():
    mat = material("MAT_Ball_Orange_Rubber", (0.82, 0.105, 0.018), 0.54)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.name = "Procedural_Rubber_Grain"
    noise.inputs["Scale"].default_value = 115.0
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.72
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.018
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def smooth_object(obj):
    if obj.type == "MESH":
        for polygon in obj.data.polygons:
            polygon.use_smooth = True


def preserve_parent(child, parent):
    matrix = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = matrix


def add_rigid_body(obj, kind, shape, mass, friction, restitution, linear_damping, angular_damping):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.rigidbody.object_add()
    obj.select_set(False)
    rigid = obj.rigid_body
    rigid.type = kind
    rigid.collision_shape = shape
    rigid.mass = mass
    rigid.friction = friction
    rigid.restitution = restitution
    rigid.linear_damping = linear_damping
    rigid.angular_damping = angular_damping
    rigid.use_margin = True
    rigid.collision_margin = 0.002
    return rigid


def create_ball(collection, mats):
    location = (-3.20, 0.0, 0.43)
    radius = 0.42
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=radius, location=location)
    ball = bpy.context.object
    ball.name = "ACTOR_SportsBall"
    ball.data.materials.append(mats["ball"])
    smooth_object(ball)
    ball["semantic_role"] = "dynamic_actor"
    ball["asset_method"] = "procedural_uv_sphere_with_great_circle_channels"
    ball["initial_linear_velocity"] = [9.6, 0.0, 0.0]
    collection.objects.link(ball) if ball.name not in collection.objects else None
    seam_specs = [
        ("SEAM_Equator", (0.0, 0.0, 0.0)),
        ("SEAM_Longitude_A", (math.pi / 2.0, 0.0, 0.0)),
        ("SEAM_Longitude_B", (0.0, math.pi / 2.0, 0.0)),
    ]
    seams = []
    for name, rotation in seam_specs:
        bpy.ops.mesh.primitive_torus_add(major_radius=radius + 0.002, minor_radius=0.010, major_segments=96, minor_segments=10, location=location, rotation=rotation)
        seam = bpy.context.object
        seam.name = name
        seam.data.materials.append(mats["seam"])
        smooth_object(seam)
        seam["semantic_role"] = "modeling_detail"
        preserve_parent(seam, ball)
        seams.append(seam)
    add_rigid_body(ball, "ACTIVE", "SPHERE", 2.8, 0.58, 0.32, 0.035, 0.055)
    ball.rigid_body.linear_velocity = Vector(ball["initial_linear_velocity"])
    return ball, seams, radius


def bottle_mesh(name, segments=64):
    profile = [
        (0.205, -0.72),
        (0.258, -0.68),
        (0.274, -0.55),
        (0.278, 0.08),
        (0.262, 0.25),
        (0.225, 0.36),
        (0.145, 0.48),
        (0.122, 0.62),
        (0.128, 0.70),
        (0.145, 0.72),
    ]
    vertices = []
    for radius, z in profile:
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            vertices.append((radius * math.cos(angle), radius * math.sin(angle), z))
    faces = []
    for ring in range(len(profile) - 1):
        for index in range(segments):
            nxt = (index + 1) % segments
            a = ring * segments + index
            b = ring * segments + nxt
            c = (ring + 1) * segments + nxt
            d = (ring + 1) * segments + index
            faces.append((a, b, c, d))
    bottom_index = len(vertices)
    vertices.append((0.0, 0.0, profile[0][1]))
    top_index = len(vertices)
    vertices.append((0.0, 0.0, profile[-1][1]))
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((bottom_index, nxt, index))
        top_a = (len(profile) - 1) * segments + index
        top_b = (len(profile) - 1) * segments + nxt
        faces.append((top_index, top_a, top_b))
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    return mesh


def create_bottle(collection, mats, index, position, body_color, label_color):
    body_mat = material(f"MAT_Bottle_{index}_Body", body_color, 0.25, 0.0, 0.18)
    label_mat = material(f"MAT_Bottle_{index}_Label", label_color, 0.34, 0.04)
    mesh = bottle_mesh(f"TARGET_Bottle_{index}")
    bottle = bpy.data.objects.new(f"TARGET_Bottle_{index}", mesh)
    collection.objects.link(bottle)
    bottle.location = (*position, 0.75)
    bottle.data.materials.append(body_mat)
    smooth_object(bottle)
    bevel = bottle.modifiers.new("Manufactured_Edge_Soften", "BEVEL")
    bevel.width = 0.012
    bevel.segments = 2
    bottle["semantic_role"] = "target_group"
    bottle["target_index"] = index
    bottle["asset_method"] = "procedural_lathed_profile"

    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.283, depth=0.34, location=(position[0], position[1], 0.70))
    label = bpy.context.object
    label.name = f"DETAIL_Bottle_{index}_LabelBand"
    label.data.materials.append(label_mat)
    label["semantic_role"] = "modeling_detail"
    bevel_label = label.modifiers.new("Label_Edge", "BEVEL")
    bevel_label.width = 0.008
    bevel_label.segments = 2
    preserve_parent(label, bottle)

    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.151, depth=0.105, location=(position[0], position[1], 1.515))
    cap = bpy.context.object
    cap.name = f"DETAIL_Bottle_{index}_Cap"
    cap.data.materials.append(mats["cap"])
    cap["semantic_role"] = "modeling_detail"
    bevel_cap = cap.modifiers.new("Cap_Edge", "BEVEL")
    bevel_cap.width = 0.018
    bevel_cap.segments = 3
    preserve_parent(cap, bottle)

    bpy.ops.mesh.primitive_torus_add(major_radius=0.257, minor_radius=0.018, major_segments=64, minor_segments=10, location=(position[0], position[1], 0.155))
    base_ring = bpy.context.object
    base_ring.name = f"DETAIL_Bottle_{index}_BaseRing"
    base_ring.data.materials.append(mats["cap"])
    base_ring["semantic_role"] = "modeling_detail"
    preserve_parent(base_ring, bottle)

    add_rigid_body(bottle, "ACTIVE", "CONVEX_HULL", 0.36, 0.68, 0.10, 0.10, 0.24)
    return bottle, [label, cap, base_ring]


def create_floor_and_backdrop(mats):
    bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0.0, 0.0, 0.0))
    floor = bpy.context.object
    floor.name = "GROUND_StudioFloor"
    floor.data.materials.append(mats["floor"])
    floor["semantic_role"] = "ground"
    add_rigid_body(floor, "PASSIVE", "BOX", 1.0, 0.72, 0.08, 0.0, 0.0)

    x0, x1 = -9.0, 9.0
    profile = [(2.9, 0.015), (3.7, 0.20), (4.35, 0.95), (4.60, 2.0), (4.60, 6.5)]
    vertices = [(x, y, z) for x in (x0, x1) for y, z in profile]
    faces = []
    count = len(profile)
    for index in range(count - 1):
        faces.append((index, index + 1, count + index + 1, count + index))
    mesh = bpy.data.meshes.new("ENV_Cyclorama_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    backdrop = bpy.data.objects.new("ENV_Cyclorama", mesh)
    bpy.context.collection.objects.link(backdrop)
    backdrop.data.materials.append(mats["backdrop"])
    backdrop["semantic_role"] = "studio_environment"
    bevel = backdrop.modifiers.new("Cyclorama_Soften", "BEVEL")
    bevel.width = 0.18
    bevel.segments = 8
    smooth_object(backdrop)
    return floor, backdrop


def point_camera(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def create_camera(name, location, target, lens):
    data = bpy.data.cameras.new(f"{name}_DATA")
    data.lens = lens
    data.sensor_width = 36.0
    camera = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(camera)
    camera.location = location
    point_camera(camera, target)
    camera["semantic_role"] = "camera"
    return camera


def create_area_light(name, role, location, target, energy, color, size):
    data = bpy.data.lights.new(f"{name}_DATA", "AREA")
    data.energy = energy
    data.color = color
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector(target) - light.location).to_track_quat("-Z", "Y").to_euler()
    light["semantic_role"] = role
    return light


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "PC5_CAUSAL_STUDIO"
    scene.frame_start = 1
    scene.frame_end = 120
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.image_settings.color_depth = "8"
    scene.render.fps = 24
    scene.render.use_file_extension = True
    scene.world.color = (0.012, 0.015, 0.025)
    scene.gravity = (0.0, 0.0, -9.81)
    try:
        scene.view_settings.look = "Medium High Contrast"
    except Exception:
        pass
    try:
        bpy.context.preferences.filepaths.file_preview_type = "NONE"
    except Exception:
        pass

    mats = {
        "ball": ball_material(),
        "seam": material("MAT_Ball_Channels", (0.008, 0.009, 0.012), 0.38),
        "cap": material("MAT_Caps_and_Base", (0.035, 0.042, 0.055), 0.30, 0.12),
        "floor": material("MAT_StudioFloor", (0.105, 0.125, 0.155), 0.29),
        "backdrop": material("MAT_Cyclorama", (0.055, 0.070, 0.105), 0.42),
    }
    floor, backdrop = create_floor_and_backdrop(mats)
    collection = bpy.data.collections.new("COL_CAUSAL_ACTORS")
    scene.collection.children.link(collection)
    ball, seams, ball_radius = create_ball(collection, mats)
    positions = [(0.0, 0.0), (0.68, -0.34), (0.68, 0.34)]
    colors = [(0.08, 0.36, 0.52), (0.58, 0.21, 0.09), (0.18, 0.46, 0.25)]
    labels = [(0.92, 0.55, 0.08), (0.05, 0.62, 0.70), (0.82, 0.24, 0.32)]
    bottles = []
    details = []
    for index, (position, body_color, label_color) in enumerate(zip(positions, colors, labels), 1):
        bottle, bottle_details = create_bottle(collection, mats, index, position, body_color, label_color)
        bottles.append(bottle)
        details.extend(bottle_details)

    cameras = {
        "SETUP": create_camera("CAM_Setup", (-5.7, -6.6, 3.25), (0.0, 0.0, 0.58), 58.0),
        "IMPACT": create_camera("CAM_Impact", (-2.25, -4.6, 1.75), (0.05, 0.0, 0.62), 66.0),
        "AFTERMATH": create_camera("CAM_Aftermath", (3.9, -5.8, 2.75), (0.45, 0.0, 0.38), 56.0),
    }
    lights = [
        create_area_light("LIGHT_Key", "key_light", (-2.7, -3.4, 5.8), (0.25, 0.0, 0.45), 1250.0, (1.0, 0.68, 0.43), 3.2),
        create_area_light("LIGHT_Fill", "fill_light", (4.2, -1.0, 3.2), (0.2, 0.0, 0.55), 720.0, (0.38, 0.58, 1.0), 4.2),
        create_area_light("LIGHT_Rim", "rim_light", (1.7, 3.5, 4.7), (0.35, 0.0, 0.65), 1050.0, (0.55, 0.72, 1.0), 2.5),
    ]
    if scene.rigidbody_world:
        scene.rigidbody_world.substeps_per_frame = 10
        scene.rigidbody_world.solver_iterations = 40
        scene.rigidbody_world.point_cache.frame_start = 1
        scene.rigidbody_world.point_cache.frame_end = 120
    scene["lesson_id"] = "PC5-CAUSAL-STUDIO"
    scene["causal_contract"] = "dynamic_actor impacts target_group through Bullet rigid bodies"
    return scene, ball, bottles, cameras, lights, floor, backdrop, seams, details, ball_radius


def angle_from_upright(obj):
    axis = obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
    cosine = max(-1.0, min(1.0, axis.normalized().dot(Vector((0.0, 0.0, 1.0)))))
    return math.degrees(math.acos(cosine))


def finite_transform(obj):
    values = list(obj.matrix_world)
    return all(math.isfinite(component) for row in values for component in row)


def reset_physics(scene, ball, bottles):
    scene.frame_set(1)
    if scene.rigidbody_world:
        cache = scene.rigidbody_world.point_cache
        try:
            cache.frame_start = 1
            cache.frame_end = 120
        except Exception:
            pass
    ball.rigid_body.linear_velocity = Vector(ball["initial_linear_velocity"])
    ball.rigid_body.angular_velocity = Vector((0.0, 9.0, 0.0))
    for bottle in bottles:
        bottle.rigid_body.linear_velocity = Vector((0.0, 0.0, 0.0))
        bottle.rigid_body.angular_velocity = Vector((0.0, 0.0, 0.0))
    bpy.context.view_layer.update()


def simulate(scene, ball, bottles):
    reset_physics(scene, ball, bottles)
    initial_ball = ball.matrix_world.translation.copy()
    initial = {obj.name: obj.matrix_world.translation.copy() for obj in bottles}
    response = {obj.name: None for obj in bottles}
    trajectory = []
    for frame in range(1, 121):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        ball_location = ball.matrix_world.translation.copy()
        rows = []
        for bottle in bottles:
            location = bottle.matrix_world.translation.copy()
            tilt = angle_from_upright(bottle)
            displacement = (Vector((location.x, location.y)) - Vector((initial[bottle.name].x, initial[bottle.name].y))).length
            if response[bottle.name] is None and (tilt >= 1.0 or displacement >= 0.012):
                response[bottle.name] = frame
            rows.append({"name": bottle.name, "location": [round(v, 8) for v in location], "tiltDegrees": round(tilt, 8)})
        trajectory.append({"frame": frame, "ball": [round(v, 8) for v in ball_location], "targets": rows})
    final_tilts = {obj.name: round(angle_from_upright(obj), 8) for obj in bottles}
    first_frame = min(value for value in response.values() if value is not None) if any(value is not None for value in response.values()) else None
    contact_order = [name for name, frame in sorted(response.items(), key=lambda row: (9999 if row[1] is None else row[1], row[0]))]
    return {
        "initialBall": [round(v, 8) for v in initial_ball],
        "ballTravelBeforeFirstContact": None if first_frame is None else round(Vector(trajectory[first_frame - 1]["ball"])[0] - initial_ball.x, 8),
        "firstTargetContactFrame": first_frame,
        "targetResponseFrames": response,
        "contactOrder": contact_order,
        "finalTiltDegrees": final_tilts,
        "finiteTransforms": {obj.name: finite_transform(obj) for obj in [ball, *bottles]},
        "trajectory": trajectory,
    }


def initial_clearance(ball, bottles, ball_radius):
    clearances = []
    ball_xy = Vector((ball.location.x, ball.location.y))
    for bottle in bottles:
        bottle_xy = Vector((bottle.location.x, bottle.location.y))
        clearances.append({"pair": [ball.name, bottle.name], "meters": round((ball_xy - bottle_xy).length - (ball_radius + 0.278), 8)})
    for left_index, left in enumerate(bottles):
        for right in bottles[left_index + 1:]:
            left_xy = Vector((left.location.x, left.location.y))
            right_xy = Vector((right.location.x, right.location.y))
            clearances.append({"pair": [left.name, right.name], "meters": round((left_xy - right_xy).length - 0.556, 8)})
    return clearances


def render_reviews(scene, cameras, physics, evidence_root):
    first = physics["firstTargetContactFrame"]
    if first is None:
        frames = {"SETUP": 1, "IMPACT": 60, "AFTERMATH": 120}
    else:
        frames = {"SETUP": max(1, first - 2), "IMPACT": first, "AFTERMATH": 120}
    review_root = evidence_root / "review"
    review_root.mkdir(parents=True, exist_ok=True)
    results = []
    for shot_id in ("SETUP", "IMPACT", "AFTERMATH"):
        frame = frames[shot_id]
        scene.frame_set(frame)
        scene.camera = cameras[shot_id]
        path = review_root / f"{shot_id.lower()}-frame-{frame:04d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        results.append({"shotId": shot_id, "frame": frame, "camera": cameras[shot_id].name, "uri": f"review/{path.name}", "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return results


def asset_inventory(ball, bottles, seams, details, cameras, lights, floor, backdrop):
    return {
        "semanticObjects": {
            "dynamic_actor": [ball.name],
            "target_group": [obj.name for obj in bottles],
            "ground": [floor.name],
            "studio_environment": [backdrop.name],
            "camera": [obj.name for obj in cameras.values()],
            "lights": [obj.name for obj in lights],
        },
        "proceduralModeling": {
            "ballChannelCount": len(seams),
            "bottleCount": len(bottles),
            "bottleDetailObjectCount": len(details),
            "bottleProfileStages": ["base", "body", "shoulder", "neck", "cap", "label"],
        },
        "externalImages": [image.filepath for image in bpy.data.images if image.source == "FILE" and image.filepath],
        "externalLibraries": [library.filepath for library in bpy.data.libraries],
        "dynamicFinalPoseKeyframes": {obj.name: bool(obj.animation_data and obj.animation_data.action) for obj in [ball, *bottles]},
        "rigidBodies": {obj.name: {"type": obj.rigid_body.type, "shape": obj.rigid_body.collision_shape, "mass": obj.rigid_body.mass} for obj in [ball, *bottles, floor]},
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["build", "reopen"], required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--evidence", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def main():
    args = parse_args()
    spec_path = Path(args.spec).resolve()
    work_root = Path(args.work).resolve()
    evidence_root = Path(args.evidence).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec["specHash"] != self_hash(spec, "specHash"):
        raise RuntimeError("SPEC_SELF_HASH")
    if Path(spec["roots"]["work"]).resolve() != work_root:
        raise RuntimeError("WORK_ROOT_BINDING")
    repository_root = spec_path.parent.parent
    if (repository_root / spec["roots"]["evidence"]).resolve() != evidence_root:
        raise RuntimeError("EVIDENCE_ROOT_BINDING")
    blend_path = work_root / "PC5_CAUSAL_STUDIO.blend"

    if args.mode == "build":
        scene, ball, bottles, cameras, lights, floor, backdrop, seams, details, ball_radius = setup_scene()
        clearances = initial_clearance(ball, bottles, ball_radius)
        scene.frame_set(1)
        ball.rigid_body.linear_velocity = Vector(ball["initial_linear_velocity"])
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
        physics = simulate(scene, ball, bottles)
        reviews = render_reviews(scene, cameras, physics, evidence_root)
        inventory = asset_inventory(ball, bottles, seams, details, cameras, lights, floor, backdrop)
        build = write_record(evidence_root / "build.json", {
            "schemaVersion": "bfs.causalStudioBuild.v0.1",
            "status": "COMPLETE",
            "specHash": spec["specHash"],
            "blender": {"version": bpy.app.version_string, "binary": bpy.app.binary_path},
            "scene": {"name": scene.name, "frameStart": scene.frame_start, "frameEnd": scene.frame_end, "fps": scene.render.fps, "physicsEngine": "BLENDER_BULLET_RIGID_BODY"},
            "blend": {"path": str(blend_path), "sha256": sha256_file(blend_path), "bytes": blend_path.stat().st_size},
            "initialClearances": clearances,
            "inventory": inventory,
            "physics": physics,
            "reviews": reviews,
        }, "buildHash")
        print(f"BFS_CAUSAL_STUDIO_BUILD COMPLETE {build['buildHash']}")
    else:
        scene = bpy.context.scene
        if scene.get("lesson_id") != "PC5-CAUSAL-STUDIO":
            raise RuntimeError("LESSON_ID")
        ball = bpy.data.objects["ACTOR_SportsBall"]
        bottles = [bpy.data.objects[f"TARGET_Bottle_{index}"] for index in range(1, 4)]
        physics = simulate(scene, ball, bottles)
        record = write_record(evidence_root / "reopen.json", {
            "schemaVersion": "bfs.causalStudioReopen.v0.1",
            "status": "COMPLETE",
            "specHash": spec["specHash"],
            "sourceBlend": {"path": str(blend_path), "sha256": sha256_file(blend_path)},
            "physics": physics,
        }, "reopenHash")
        print(f"BFS_CAUSAL_STUDIO_REOPEN COMPLETE {record['reopenHash']}")


if __name__ == "__main__":
    main()
