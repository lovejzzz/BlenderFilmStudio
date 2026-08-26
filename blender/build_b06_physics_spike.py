"""Build the pre-registered B06 two-collider rigid-body feasibility scene."""

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
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--variant", choices=["POSITIVE", "N01_ZERO_FRICTION", "N02_ONE_COLLIDER", "N03_INSUFFICIENT_CLOSURE", "N04_PROP_KINEMATIC", "N05_FORBIDDEN_PARENT", "N06_FAST_TRANSPORT", "N07_LARGE_MARGIN", "N08_LOW_SUBSTEPS"], default="POSITIVE")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def clear() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def cube(name: str, location: tuple[float, float, float], scale: tuple[float, float, float], color: tuple[float, float, float, float]) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    material = bpy.data.materials.new(f"MAT_{name}")
    material.diffuse_color = color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = 0.42
    obj.data.materials.append(material)
    return obj


def add_rigid_body(obj: bpy.types.Object, body_type: str, friction: float, margin: float) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.rigidbody.object_add()
    obj.select_set(False)
    obj.rigid_body.type = body_type
    obj.rigid_body.collision_shape = "BOX"
    obj.rigid_body.friction = friction
    obj.rigid_body.restitution = 0.0
    obj.rigid_body.use_margin = True
    obj.rigid_body.collision_margin = margin


def set_linear(obj: bpy.types.Object) -> None:
    if not obj.animation_data or not obj.animation_data.action:
        return
    bag = anim_utils.animdata_get_channelbag_for_assigned_slot(obj.animation_data)
    if bag:
        for curve in bag.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = "LINEAR"


def animate_location(obj: bpy.types.Object, keys: list[tuple[int, tuple[float, float, float]]]) -> None:
    for frame, location in keys:
        obj.location = location
        obj.keyframe_insert(data_path="location", frame=frame, group="B06_KINEMATIC_COLLIDER")
    set_linear(obj)


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def main() -> None:
    args = parse_args()
    clear()
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 132
    scene.render.fps = 24
    scene.gravity = (0, 0, -9.81)

    friction = 0.0 if args.variant == "N01_ZERO_FRICTION" else 1.0
    margin = 0.005 if args.variant == "N07_LARGE_MARGIN" else 0.0002
    closure_x = 0.08 if args.variant == "N03_INSUFFICIENT_CLOSURE" else 0.0695
    hold_x = 0.08 if args.variant == "N03_INSUFFICIENT_CLOSURE" else 0.069
    transport_end = 50 if args.variant == "N06_FAST_TRANSPORT" else 108

    prop = cube("B06_PROP", (0, 0, 0), (0.10, 0.12, 0.14), (0.12, 0.42, 0.82, 1))
    # v0.2 diagnostic correction: broad faces prevent immediate Y-axis edge
    # escape, while the small continuing inward motion maintains normal load
    # without the 2 mm initial overlap that exploded the first run.
    left = cube("B06_LEFT", (-0.085, 0, 0), (0.04, 0.24, 0.18), (0.9, 0.18, 0.08, 1))
    right = cube("B06_RIGHT", (0.085, 0, 0), (0.04, 0.24, 0.18), (1.0, 0.62, 0.08, 1))
    # Keep the observation window free of a secondary floor impact; the
    # benchmark concerns grasp support and release, not chaotic bounce.
    floor = cube("B06_FLOOR", (0, 0, -5.0), (0.8, 0.8, 0.02), (0.025, 0.03, 0.04, 1))

    add_rigid_body(prop, "ACTIVE", friction=friction, margin=margin)
    prop.rigid_body.mass = 0.25
    prop.rigid_body.linear_damping = 0.8
    prop.rigid_body.angular_damping = 0.95
    prop.rigid_body.use_deactivation = False
    prop.rigid_body.kinematic = True
    prop.rigid_body.keyframe_insert(data_path="kinematic", frame=1)
    prop.rigid_body.keyframe_insert(data_path="kinematic", frame=48)
    prop.rigid_body.kinematic = args.variant == "N04_PROP_KINEMATIC"
    prop.rigid_body.keyframe_insert(data_path="kinematic", frame=49)

    for collider in (left, right, floor):
        add_rigid_body(collider, "PASSIVE", friction=friction, margin=margin)
        collider.rigid_body.kinematic = True
    left_keys = [(1, (-0.085, 0, 0)), (36, (-0.085, 0, 0)), (48, (-closure_x, 0, 0)), (49, (-closure_x, 0, 0)), (transport_end, (-hold_x, 0, 0.3))]
    if transport_end != 108:
        left_keys.append((108, (-hold_x, 0, 0.3)))
    left_keys.extend([(112, (-0.095, 0, 0.3)), (132, (-0.095, 0, 0.3))])
    if args.variant == "N06_FAST_TRANSPORT":
        left_keys = [(1, (-0.085, 0, 0)), (36, (-0.085, 0, 0)), (48, (-closure_x, 0, 0)), (49, (-closure_x, 0, 0)), (50, (-hold_x, 0, 3.0)), (51, (-hold_x, 0, 0.3)), (108, (-hold_x, 0, 0.3)), (112, (-0.095, 0, 0.3)), (132, (-0.095, 0, 0.3))]
    right_start = 0.5 if args.variant == "N02_ONE_COLLIDER" else 0.085
    right_closure = 0.5 if args.variant == "N02_ONE_COLLIDER" else closure_x
    right_hold = 0.5 if args.variant == "N02_ONE_COLLIDER" else hold_x
    right_release = 0.5 if args.variant == "N02_ONE_COLLIDER" else 0.095
    right_keys = [(1, (right_start, 0, 0)), (36, (right_start, 0, 0)), (48, (right_closure, 0, 0)), (49, (right_closure, 0, 0)), (transport_end, (right_hold, 0, 0.3))]
    if transport_end != 108:
        right_keys.append((108, (right_hold, 0, 0.3)))
    right_keys.extend([(112, (right_release, 0, 0.3)), (132, (right_release, 0, 0.3))])
    if args.variant == "N06_FAST_TRANSPORT":
        right_keys = [(1, (right_start, 0, 0)), (36, (right_start, 0, 0)), (48, (right_closure, 0, 0)), (49, (right_closure, 0, 0)), (50, (right_hold, 0, 3.0)), (51, (right_hold, 0, 0.3)), (108, (right_hold, 0, 0.3)), (112, (right_release, 0, 0.3)), (132, (right_release, 0, 0.3))]
    animate_location(left, left_keys)
    animate_location(right, right_keys)

    if args.variant == "N05_FORBIDDEN_PARENT":
        prop.parent = left
        prop.matrix_parent_inverse = left.matrix_world.inverted()

    world = scene.rigidbody_world
    world.substeps_per_frame = 30 if args.variant == "N08_LOW_SUBSTEPS" else 240
    world.solver_iterations = 40
    world.time_scale = 1.0
    world.point_cache.frame_start = 1
    world.point_cache.frame_end = 132

    declared = {
        "documentType": "BFS_B06_PHYSICS_SPIKE_MANIFEST", "version": "0.2.0", "variant": args.variant, "blender": bpy.app.version_string,
        "frames": {"start": 1, "dynamic": 49, "holdEnd": 108, "releaseEnd": 112, "observationEnd": 132},
        "gravityMPerS2": list(scene.gravity), "substepsPerFrame": world.substeps_per_frame, "solverIterations": world.solver_iterations,
        "prop": {"object": prop.name, "dimensionsM": list(prop.dimensions), "color": list(prop.data.materials[0].diffuse_color), "massKg": prop.rigid_body.mass, "friction": prop.rigid_body.friction, "collisionMarginM": prop.rigid_body.collision_margin, "linearDamping": prop.rigid_body.linear_damping, "angularDamping": prop.rigid_body.angular_damping},
        "colliders": [
            {"object": left.name, "dimensionsM": list(left.dimensions), "color": list(left.data.materials[0].diffuse_color), "friction": left.rigid_body.friction, "collisionMarginM": left.rigid_body.collision_margin, "locationKeys": [{"frame": frame, "locationM": list(location)} for frame, location in left_keys]},
            {"object": right.name, "dimensionsM": list(right.dimensions), "color": list(right.data.materials[0].diffuse_color), "friction": right.rigid_body.friction, "collisionMarginM": right.rigid_body.collision_margin, "locationKeys": [{"frame": frame, "locationM": list(location)} for frame, location in right_keys]},
        ],
        "floor": {"object": floor.name, "locationM": list(floor.location), "dimensionsM": list(floor.dimensions), "color": list(floor.data.materials[0].diffuse_color), "friction": floor.rigid_body.friction, "collisionMarginM": floor.rigid_body.collision_margin},
        "forbiddenShortcuts": {"propParent": prop.parent.name if prop.parent else None, "propConstraints": len(prop.constraints), "rigidBodyConstraints": len(bpy.data.objects) - len([obj for obj in bpy.data.objects if obj.rigid_body_constraint is None])},
    }
    declared["structureHash"] = hashlib.sha256(canonical_json(declared).encode("utf-8")).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), check_existing=False, compress=True)
    args.manifest.write_text(f"{json.dumps(declared, indent=2)}\n", encoding="utf-8")
    print(f"BFS_B06_PHYSICS_SPIKE_OK {declared['structureHash']} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B06_PHYSICS_SPIKE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
