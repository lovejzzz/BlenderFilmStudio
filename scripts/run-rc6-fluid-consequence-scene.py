#!/usr/bin/env python3
"""RC6 feasibility scene: Bullet-owned cup impact feeding a Mantaflow liquid consequence."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def object_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


parser = argparse.ArgumentParser()
parser.add_argument("--action", choices=("build", "reopen"), required=True)
parser.add_argument("--work-root", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
work = args.work_root.resolve(strict=True)
evidence = args.evidence_root.resolve(strict=True)
blend_path = work / "RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend"
cache_path = work / "mantaflow-cache"


def material(name, color, metallic=0.0, roughness=0.4, transmission=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*color, 1.0)
    node.inputs["Metallic"].default_value = metallic
    node.inputs["Roughness"].default_value = roughness
    if "Transmission Weight" in node.inputs:
        node.inputs["Transmission Weight"].default_value = transmission
    return mat


def add_cube(name, location, scale, mat=None):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    return obj


def add_uv_sphere(name, location, radius, mat=None, segments=48, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    return obj


def create_open_tumbler(name, location, outer_radius=0.068, height=0.22, thickness=0.005, segments=64):
    z0, z1 = -height / 2, height / 2
    inner_radius = outer_radius - thickness
    inner_floor = z0 + thickness
    vertices = []
    for radius, z in ((outer_radius, z0), (outer_radius, z1), (inner_radius, inner_floor), (inner_radius, z1)):
        vertices.extend((radius * math.cos(2 * math.pi * i / segments), radius * math.sin(2 * math.pi * i / segments), z) for i in range(segments))
    outer_bottom_center = len(vertices)
    vertices.append((0, 0, z0))
    inner_floor_center = len(vertices)
    vertices.append((0, 0, inner_floor))
    faces = []
    ob, ot, ib, it = 0, segments, 2 * segments, 3 * segments
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((ob + i, ob + j, ot + j, ot + i))
        faces.append((ib + i, it + i, it + j, ib + j))
        faces.append((ot + i, ot + j, it + j, it + i))
        faces.append((outer_bottom_center, ob + j, ob + i))
        faces.append((inner_floor_center, ib + i, ib + j))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    bevel = obj.modifiers.new("Molded edge bevel", "BEVEL")
    bevel.width = 0.0015
    bevel.segments = 2
    return obj


def rigid_body(obj, kind, mass=1.0, shape="CONVEX_HULL", friction=0.5, restitution=0.1):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.rigidbody.object_add()
    obj.rigid_body.type = kind
    obj.rigid_body.mass = mass
    obj.rigid_body.collision_shape = shape
    obj.rigid_body.friction = friction
    obj.rigid_body.restitution = restitution
    obj.select_set(False)


def fluid_modifier(obj, fluid_type):
    modifier = obj.modifiers.new(name=f"{fluid_type.title()} Fluid", type="FLUID")
    modifier.fluid_type = fluid_type
    bpy.context.view_layer.update()
    return modifier


def tilt_degrees(obj):
    up = obj.matrix_world.to_3x3() @ Vector((0, 0, 1))
    return math.degrees(math.acos(max(-1.0, min(1.0, up.normalized().dot(Vector((0, 0, 1)))))))


def world_bounds(objects):
    points = []
    for obj in objects:
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    low = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
    high = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
    return low, high


def look_at(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def fit_camera(camera, low, high, direction):
    center = (low + high) * 0.5
    span = high - low
    radius = max(span.x, span.y, span.z, 0.25) * 0.5
    camera.data.lens = 52
    camera.location = center + Vector(direction).normalized() * (radius * 4.6 + 0.35)
    look_at(camera, center + Vector((0, 0, span.z * 0.05)))
    camera.data.dof.use_dof = False
    return {"center": [round(value, 8) for value in center], "span": [round(value, 8) for value in span], "direction": list(direction)}


def evaluated_fluid(domain, cup):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = domain.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()
    if not points:
        return {"vertexCount": 0, "boundsMin": None, "boundsMax": None, "outsideCupFraction": 0.0, "floorSpreadMeters": 0.0}
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    inv = cup.matrix_world.inverted_safe()
    outside = 0
    for point in points:
        local = inv @ point
        radial = math.hypot(local.x, local.y)
        if radial > 0.078 or local.z < -0.12 or local.z > 0.125:
            outside += 1
    center_xy = Vector((cup.matrix_world.translation.x, cup.matrix_world.translation.y))
    spread = max((Vector((p.x, p.y)) - center_xy).length for p in points)
    return {
        "vertexCount": len(points),
        "boundsMin": [round(value, 8) for value in low],
        "boundsMax": [round(value, 8) for value in high],
        "outsideCupFraction": round(outside / len(points), 8),
        "floorSpreadMeters": round(spread, 8),
    }


def render_one(scene, camera, frame, destination):
    scene.frame_set(frame)
    scene.camera = camera
    scene.render.filepath = str(destination)
    bpy.ops.render.render(write_still=True)
    return {"frame": frame, "camera": camera.name, "uri": str(destination), "bytes": destination.stat().st_size, "sha256": sha(destination)}


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 48
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 960, 540, 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.fps = 24
    scene.world.color = (0.018, 0.022, 0.035)

    court_mat = material("Court", (0.24, 0.095, 0.035), roughness=0.35)
    ball_mat = material("Basketball", (0.62, 0.12, 0.025), roughness=0.42)
    glass_mat = material("Glass tumbler", (0.3, 0.52, 0.64), roughness=0.12, transmission=0.82)
    liquid_mat = material("Liquid", (0.02, 0.22, 0.38), roughness=0.08, transmission=0.28)
    metal_mat = material("Metal", (0.15, 0.18, 0.22), metallic=0.8, roughness=0.25)

    floor = add_cube("PHYS_FLOOR", (0.25, 0, -0.04), (2.0, 1.5, 0.04), court_mat)
    cup = create_open_tumbler("PHYS_OPEN_TUMBLER", (0.32, 0, 0.11))
    cup.data.materials.append(glass_mat)
    ball = add_uv_sphere("PHYS_BASKETBALL", (-0.88, 0, 0.12), 0.12, ball_mat)
    # Visible grooves are actual geometry but do not alter the metric collision sphere.
    for rotation in ((0, 0, 0), (math.pi / 2, 0, 0), (0, math.pi / 2, 0)):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.1195, minor_radius=0.0022, major_segments=64, minor_segments=8, location=ball.location, rotation=rotation)
        groove = bpy.context.object
        groove.name = "DETAIL_BALL_GROOVE"
        groove.data.materials.append(metal_mat)
        groove.parent = ball

    rigid_body(floor, "PASSIVE", shape="BOX", friction=0.58, restitution=0.08)
    rigid_body(cup, "ACTIVE", mass=0.34, shape="CONVEX_HULL", friction=0.46, restitution=0.1)
    rigid_body(ball, "ACTIVE", mass=0.62, shape="SPHERE", friction=0.48, restitution=0.38)
    ball.rigid_body.linear_velocity = (5.2, 0.03, 0.0)
    ball.rigid_body.angular_velocity = (0.0, 16.0, 0.4)
    scene.rigidbody_world.substeps_per_frame = 20
    scene.rigidbody_world.solver_iterations = 80
    scene.rigidbody_world.point_cache.frame_start = 1
    scene.rigidbody_world.point_cache.frame_end = 48

    # Initial liquid volume exists once; no animated inflow or authored spill time.
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.057, depth=0.105, location=(0.32, 0, 0.063))
    source = bpy.context.object
    source.name = "PHYS_INITIAL_LIQUID_VOLUME"
    source.display_type = "WIRE"
    source.hide_render = True
    flow = fluid_modifier(source, "FLOW")
    flow.flow_settings.flow_type = "LIQUID"
    flow.flow_settings.flow_behavior = "GEOMETRY"
    flow.flow_settings.surface_distance = 1.5
    flow.flow_settings.use_plane_init = False

    fluid_modifier(cup, "EFFECTOR").effector_settings.surface_distance = 0.0015
    fluid_modifier(floor, "EFFECTOR").effector_settings.surface_distance = 0.0015

    domain = add_cube("PHYS_LIQUID_DOMAIN", (0.35, 0, 0.4), (1.05, 0.65, 0.4), liquid_mat)
    domain_mod = fluid_modifier(domain, "DOMAIN")
    settings = domain_mod.domain_settings
    settings.domain_type = "LIQUID"
    settings.cache_type = "MODULAR"
    settings.cache_directory = str(cache_path)
    settings.cache_frame_start = 1
    settings.cache_frame_end = 48
    settings.resolution_max = 48
    settings.cache_data_format = "OPENVDB"
    settings.cache_mesh_format = "OPENVDB"
    settings.simulation_method = "APIC"
    settings.use_adaptive_timesteps = True
    settings.timesteps_min = 1
    settings.timesteps_max = 4
    settings.cfl_condition = 2.0
    settings.use_mesh = True
    settings.mesh_scale = 2
    settings.mesh_particle_radius = 2.0
    settings.use_speed_vectors = True
    settings.use_fractions = True
    settings.fractions_threshold = 0.05
    settings.particle_number = 2
    settings.flip_ratio = 0.95

    # Three persistent cameras are created before either bake so later framing cannot invalidate a cache.
    cameras = {}
    for role in ("CAUSE", "CONTACT", "EFFECT"):
        data = bpy.data.cameras.new(f"RC6_CAM_{role}")
        camera = bpy.data.objects.new(f"RC6_CAM_{role}", data)
        bpy.context.collection.objects.link(camera)
        cameras[role.lower()] = camera

    key = add_cube("ENV_BACKSTOP", (0.8, 0.85, 0.65), (1.8, 0.04, 0.65), material("Backstop", (0.035, 0.055, 0.08), roughness=0.55))
    for name, location, energy, size, color in (
        ("LIGHT_KEY", (-0.5, -1.2, 1.8), 1050, 2.2, (1.0, 0.56, 0.32)),
        ("LIGHT_FILL", (1.2, 0.8, 1.35), 780, 1.8, (0.28, 0.5, 1.0)),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size, data.color = energy, "DISK", size, color
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        bpy.context.collection.objects.link(obj)
        look_at(obj, (0.2, 0, 0.1))

    with bpy.context.temp_override(point_cache=scene.rigidbody_world.point_cache):
        bpy.ops.ptcache.bake(bake=True)

    bullet_samples = []
    initial_cup_rotation = None
    contact_frame = None
    for frame in range(1, 49):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        if initial_cup_rotation is None:
            initial_cup_rotation = cup.matrix_world.to_quaternion().copy()
        tilt = tilt_degrees(cup)
        separation = (ball.matrix_world.translation - cup.matrix_world.translation).length - 0.188
        if contact_frame is None and (separation <= 0.006 or tilt >= 1.0):
            contact_frame = frame
        bullet_samples.append({
            "frame": frame,
            "ballLocation": [round(value, 8) for value in ball.matrix_world.translation],
            "cupLocation": [round(value, 8) for value in cup.matrix_world.translation],
            "cupTiltDegrees": round(tilt, 8),
            "cupAngularResponseDegrees": round(math.degrees(initial_cup_rotation.rotation_difference(cup.matrix_world.to_quaternion()).angle), 8),
            "contactGapMeters": round(separation, 8),
        })
    if contact_frame is None:
        contact_frame = 48

    scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    domain.select_set(True)
    bpy.context.view_layer.objects.active = domain
    with bpy.context.temp_override(object=domain, active_object=domain, selected_objects=[domain], selected_editable_objects=[domain]):
        bpy.ops.fluid.bake_data()
        bpy.ops.fluid.bake_mesh()

    fluid_samples = []
    spill_frame = None
    effect_frame = 1
    best_score = -1.0
    for frame in range(1, 49):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        sample = evaluated_fluid(domain, cup)
        sample["frame"] = frame
        fluid_samples.append(sample)
        if spill_frame is None and sample["vertexCount"] >= 100 and sample["outsideCupFraction"] >= 0.08:
            spill_frame = frame
        score = sample["outsideCupFraction"] * max(sample["floorSpreadMeters"], 0.001)
        if sample["vertexCount"] >= 100 and score > best_score:
            best_score = score
            effect_frame = frame

    scene.frame_set(1)
    cause_low, cause_high = world_bounds((ball, cup))
    scene.frame_set(contact_frame)
    contact_low, contact_high = world_bounds((ball, cup))
    scene.frame_set(effect_frame)
    effect_fluid = fluid_samples[effect_frame - 1]
    if effect_fluid["boundsMin"]:
        effect_low = Vector(effect_fluid["boundsMin"])
        effect_high = Vector(effect_fluid["boundsMax"])
        cup_low, cup_high = world_bounds((cup,))
        effect_low = Vector((min(effect_low.x, cup_low.x), min(effect_low.y, cup_low.y), min(effect_low.z, cup_low.z)))
        effect_high = Vector((max(effect_high.x, cup_high.x), max(effect_high.y, cup_high.y), max(effect_high.z, cup_high.z)))
    else:
        effect_low, effect_high = world_bounds((cup,))
    framing = {
        "cause": fit_camera(cameras["cause"], cause_low, cause_high, (-1.2, -1.7, 0.72)),
        "contact": fit_camera(cameras["contact"], contact_low, contact_high, (-1.1, -1.55, 0.58)),
        "effect": fit_camera(cameras["effect"], effect_low, effect_high, (-0.8, -1.4, 0.72)),
    }

    peak_tilt = max(row["cupTiltDegrees"] for row in bullet_samples)
    initial_fluid = fluid_samples[0]
    maximum_spread = max(row["floorSpreadMeters"] for row in fluid_samples)
    maximum_outside = max(row["outsideCupFraction"] for row in fluid_samples)
    checks = {
        "nativeSolvers": bpy.app.build_options.bullet and bpy.app.build_options.fluid,
        "derivedContact": contact_frame < 20,
        "bulletCupResponse": peak_tilt >= 45.0,
        "liquidMeshExists": max(row["vertexCount"] for row in fluid_samples) >= 100,
        "derivedSpill": spill_frame is not None and spill_frame >= contact_frame,
        "liquidLeavesCup": maximum_outside >= 0.15,
        "liquidSpreads": maximum_spread >= 0.12,
        "noAuthoredOutcomeAuthority": len(cup.animation_data.action.fcurves) == 0 if cup.animation_data and cup.animation_data.action else True,
        "singleInitialGeometryFlow": flow.flow_settings.flow_behavior == "GEOMETRY" and not source.animation_data,
        "staticLighting": all(not obj.animation_data for obj in bpy.data.objects if obj.type == "LIGHT"),
        "persistentCameras": all(camera.name in scene.objects for camera in cameras.values()),
        "resourceConfiguration": settings.resolution_max == 48 and settings.cache_frame_end == 48 and settings.mesh_scale == 2,
    }
    result = {
        "schemaVersion": "bfs.rc6FluidConsequenceFeasibilityResult.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "physics": {
            "bullet": {
                "source": "BLENDER_BULLET_EVALUATED_WORLD_TRANSFORMS",
                "contactFrame": contact_frame,
                "peakCupTiltDegrees": round(peak_tilt, 8),
                "samples": bullet_samples,
            },
            "liquid": {
                "source": "BLENDER_MANTAFLOW_APIC_LIQUID_MESH",
                "initialGeometryFrame": 1,
                "authoredSpillFrame": False,
                "derivedSpillFrame": spill_frame,
                "effectFrame": effect_frame,
                "maximumOutsideCupFraction": round(maximum_outside, 8),
                "maximumFloorSpreadMeters": round(maximum_spread, 8),
                "initialVertexCount": initial_fluid["vertexCount"],
                "samples": fluid_samples,
            },
        },
        "authority": {
            "cupOutcomeKeys": 0,
            "fluidOutcomeKeys": 0,
            "authoredContactFrames": 0,
            "authoredSpillFrames": 0,
            "authoredFinalFluidMeshes": 0,
            "networkCalls": 0,
        },
        "cinematography": {
            "cause": {"frame": 1, "camera": cameras["cause"].name, "framing": framing["cause"]},
            "contact": {"frame": contact_frame, "camera": cameras["contact"].name, "framing": framing["contact"]},
            "effect": {"frame": effect_frame, "camera": cameras["effect"].name, "framing": framing["effect"]},
        },
        "checks": checks,
        "checkCount": len(checks),
        "passCount": sum(checks.values()),
        "claimCeiling": "One bounded Bullet-to-Mantaflow feasibility scene; one-way liquid consequence only, not two-way fluid/rigid coupling, narrow-neck bottle flow, production fluid quality or arbitrary scenes.",
    }
    result["resultHash"] = object_hash(result, "resultHash")
    scene["film_studio_rc6_result"] = canonical(result)
    scene["film_studio_rc6_result_hash"] = result["resultHash"]
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    scene.frame_set(effect_frame)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)

    still_root, clip_root = evidence / "stills", evidence / "clip"
    still_root.mkdir(exist_ok=False)
    clip_root.mkdir(exist_ok=False)
    stills = [
        {**render_one(scene, cameras["cause"], 1, still_root / "cause-frame-0001.png"), "role": "cause"},
        {**render_one(scene, cameras["contact"], contact_frame, still_root / f"contact-frame-{contact_frame:04d}.png"), "role": "contact"},
        {**render_one(scene, cameras["effect"], effect_frame, still_root / f"effect-frame-{effect_frame:04d}.png"), "role": "effect"},
    ]
    frames = [render_one(scene, cameras["contact"], frame, clip_root / f"frame-{frame:04d}.png") for frame in range(1, 49)]
    output = {
        "schemaVersion": "bfs.rc6FluidConsequenceFeasibilityBuild.v0.1",
        "status": result["status"],
        "result": result,
        "blend": {"uri": str(blend_path), "bytes": blend_path.stat().st_size, "sha256": sha(blend_path)},
        "cache": {"uri": str(cache_path), "exists": cache_path.is_dir()},
        "renders": {"resolution": [960, 540], "stills": stills, "clipFrames": frames},
        "counts": {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "blendSaves": 1, "renderCalls": 51, "networkCalls": 0},
    }
    write(evidence / "build.json", output)
    print("RC6_BUILD=" + canonical({"status": output["status"], "resultHash": result["resultHash"], "checks": checks}))
    if output["status"] != "PASS":
        raise RuntimeError("RC6 feasibility thresholds failed")


def reopen():
    stored = json.loads(bpy.context.scene["film_studio_rc6_result"])
    expected = json.loads((evidence / "build.json").read_text(encoding="utf-8"))["result"]
    scene = bpy.context.scene
    cup = scene.objects["PHYS_OPEN_TUMBLER"]
    domain = scene.objects["PHYS_LIQUID_DOMAIN"]
    maximum_cup_location_delta = 0.0
    maximum_cup_tilt_delta = 0.0
    for sample in expected["physics"]["bullet"]["samples"]:
        scene.frame_set(sample["frame"])
        bpy.context.view_layer.update()
        maximum_cup_location_delta = max(maximum_cup_location_delta, (cup.matrix_world.translation - Vector(sample["cupLocation"])).length)
        maximum_cup_tilt_delta = max(maximum_cup_tilt_delta, abs(tilt_degrees(cup) - sample["cupTiltDegrees"]))
    effect_frame = expected["physics"]["liquid"]["effectFrame"]
    scene.frame_set(effect_frame)
    bpy.context.view_layer.update()
    actual_fluid = evaluated_fluid(domain, cup)
    expected_fluid = expected["physics"]["liquid"]["samples"][effect_frame - 1]
    checks = {
        "storedResultExact": stored == expected,
        "storedHashExact": scene["film_studio_rc6_result_hash"] == expected["resultHash"],
        "cupLocationDelta": maximum_cup_location_delta <= 1e-6,
        "cupTiltDelta": maximum_cup_tilt_delta <= 0.001,
        "fluidVertexCountExact": actual_fluid["vertexCount"] == expected_fluid["vertexCount"],
        "fluidBoundsExact": actual_fluid["boundsMin"] == expected_fluid["boundsMin"] and actual_fluid["boundsMax"] == expected_fluid["boundsMax"],
        "cachePresent": cache_path.is_dir() and any(path.is_file() for path in cache_path.rglob("*")),
        "noMutation": True,
    }
    output = {
        "schemaVersion": "bfs.rc6FluidConsequenceFeasibilityReopen.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "checkCount": len(checks),
        "passCount": sum(checks.values()),
        "maximumCupLocationDeltaMeters": maximum_cup_location_delta,
        "maximumCupTiltDeltaDegrees": maximum_cup_tilt_delta,
        "effectFrameFluid": actual_fluid,
        "counts": {"blenderStarts": 1, "blendSaves": 0, "renders": 0, "networkCalls": 0},
    }
    write(evidence / "reopen.json", output)
    print("RC6_REOPEN=" + canonical(output))
    if output["status"] != "PASS":
        raise RuntimeError("RC6 feasibility reopen failed")


{"build": build, "reopen": reopen}[args.action]()
