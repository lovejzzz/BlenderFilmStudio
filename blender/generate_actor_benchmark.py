"""Generate a small project-owned B03 actor and motion library for ActorSpec tests.

The asset is deliberately a technical mannequin, not a claim about photoreal
human quality. It exists to exercise Blender 5.2 armatures, modifiers, shape
keys, constraints, Action Slots, and identity hashing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from bpy_extras import anim_utils
from mathutils import Matrix


GENERATOR_VERSION = "0.1.1"


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_value(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rounded(values) -> list[float]:
    return [round(float(value), 9) for value in values]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-output", type=Path, required=True)
    parser.add_argument("--motion-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def clear_scene() -> None:
    for datablocks in (bpy.data.objects, bpy.data.collections, bpy.data.armatures, bpy.data.meshes, bpy.data.actions):
        for datablock in list(datablocks):
            datablocks.remove(datablock, do_unlink=True)


def make_material(name: str, color: tuple[float, float, float, float], roughness: float) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    return material


def make_mesh(collection: bpy.types.Collection, name: str, primitive: str, location, scale, material) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    if primitive == "sphere":
        # BMesh's UV-sphere vertex ordering is not a stable serialization
        # contract. Build the topology explicitly so repeated generations have
        # the same vertex, edge, polygon, Shape Key, and identity hashes.
        segments = 24
        rings = 12
        vertices = [(0.0, 0.0, 0.5)]
        for ring in range(1, rings):
            theta = math.pi * ring / rings
            for segment in range(segments):
                phi = 2.0 * math.pi * segment / segments
                vertices.append((
                    0.5 * math.sin(theta) * math.cos(phi),
                    0.5 * math.sin(theta) * math.sin(phi),
                    0.5 * math.cos(theta),
                ))
        bottom = len(vertices)
        vertices.append((0.0, 0.0, -0.5))
        faces = []
        first_ring = 1
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            faces.append((0, first_ring + segment, first_ring + next_segment))
        for ring in range(rings - 2):
            current = 1 + ring * segments
            following = current + segments
            for segment in range(segments):
                next_segment = (segment + 1) % segments
                faces.append((
                    current + segment,
                    following + segment,
                    following + next_segment,
                    current + next_segment,
                ))
        last_ring = 1 + (rings - 2) * segments
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            faces.append((last_ring + next_segment, last_ring + segment, bottom))
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
    elif primitive == "cube":
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bm.to_mesh(mesh)
        bm.free()
    else:
        raise ValueError(primitive)
    # Armature deformation operates on vertex coordinates. Bake model-space
    # placement into the mesh so a fully weighted part rotates around its bone
    # rest-space pivot instead of around an unrelated Object origin.
    mesh.transform(Matrix.Translation(location) @ Matrix.Diagonal((*scale, 1.0)))
    obj = bpy.data.objects.new(name, mesh)
    mesh.materials.append(material)
    collection.objects.link(obj)
    return obj


def create_armature(collection: bpy.types.Collection) -> bpy.types.Object:
    data = bpy.data.armatures.new("RIG_LEAD_DATA")
    rig = bpy.data.objects.new("RIG_LEAD", data)
    collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    definitions = [
        ("root", (0, 0, 0), (0, 0, 0.3), None, False),
        ("pelvis", (0, 0, 0.85), (0, 0, 1.1), "root", True),
        ("head", (0, 0, 1.45), (0, 0, 1.8), "pelvis", True),
        ("eye.L", (0.09, -0.13, 1.68), (0.09, -0.23, 1.68), "head", True),
        ("eye.R", (-0.09, -0.13, 1.68), (-0.09, -0.23, 1.68), "head", True),
        ("jaw", (0, -0.04, 1.58), (0, -0.16, 1.52), "head", True),
        ("hand.L", (0.28, 0, 1.25), (0.58, 0, 1.1), "pelvis", True),
        ("hand.R", (-0.28, 0, 1.25), (-0.58, 0, 1.1), "pelvis", True),
        ("foot.L", (0.12, 0, 0.18), (0.12, -0.18, 0.08), "pelvis", True),
        ("foot.R", (-0.12, 0, 0.18), (-0.12, -0.18, 0.08), "pelvis", True),
    ]
    edit_bones = {}
    for name, head, tail, parent, deform in definitions:
        bone = data.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        bone.use_deform = deform
        if parent:
            bone.parent = edit_bones[parent]
        edit_bones[name] = bone
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.select_set(False)
    for pose_bone in rig.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"
    return rig


def bind_mesh(obj: bpy.types.Object, rig: bpy.types.Object, group_name: str) -> None:
    group = obj.vertex_groups.new(name=group_name)
    group.add(range(len(obj.data.vertices)), 1.0, "REPLACE")
    modifier = obj.modifiers.new("BFS_ARMATURE", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    modifier.use_bone_envelopes = False
    modifier.use_deform_preserve_volume = True


def add_face_shapes(head: bpy.types.Object) -> None:
    head.shape_key_add(name="Basis")
    jaw = head.shape_key_add(name="jawOpen")
    blink_left = head.shape_key_add(name="eyeBlinkLeft")
    blink_right = head.shape_key_add(name="eyeBlinkRight")
    for index, vertex in enumerate(head.data.vertices):
        co = vertex.co
        if co.z < 1.57:
            jaw.data[index].co.z -= 0.28 * max(0.0, 1.57 - co.z)
            jaw.data[index].co.y -= 0.05
        if co.z > 1.67 and co.y < -0.1:
            if co.x > 0:
                blink_left.data[index].co.z -= 0.08
            else:
                blink_right.data[index].co.z -= 0.08


def add_safe_constraints(rig: bpy.types.Object, gaze_target: bpy.types.Object) -> None:
    for name in ("eye.L", "eye.R"):
        constraint = rig.pose.bones[name].constraints.new("DAMPED_TRACK")
        constraint.name = f"BFS_GAZE_{name}"
        constraint.target = gaze_target
        # The eye meshes sit beyond the bone tail in rest space, so local +Y
        # must face the target. TRACK_NEGATIVE_Y would satisfy the angular
        # constraint while rotating the visible geometry behind the head.
        constraint.track_axis = "TRACK_Y"
        constraint.influence = 1.0
    limit = rig.pose.bones["head"].constraints.new("LIMIT_ROTATION")
    limit.name = "BFS_HEAD_LIMIT"
    limit.owner_space = "LOCAL"
    limit.use_limit_x = True
    limit.min_x = -0.45
    limit.max_x = 0.45


def create_motion_action(rig: bpy.types.Object) -> bpy.types.Action:
    head = rig.pose.bones["head"]
    for frame, angle in ((1, -0.035), (72, 0.045), (144, -0.035)):
        head.rotation_quaternion = (1.0, 0.0, 0.0, angle)
        head.keyframe_insert(data_path="rotation_quaternion", frame=frame, group="BODY_HEAD")
    action = rig.animation_data.action
    action.name = "B03_BODY_IDLE"
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(rig.animation_data)
    if channelbag:
        for curve in channelbag.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = "BEZIER"
    return action


def bone_records(rig: bpy.types.Object) -> list[dict]:
    return [
        {
            "name": bone.name,
            "parent": bone.parent.name if bone.parent else None,
            "headLocal": rounded(bone.head_local),
            "tailLocal": rounded(bone.tail_local),
            "matrixLocal": [rounded(row) for row in bone.matrix_local],
            "deform": bone.use_deform,
        }
        for bone in sorted(rig.data.bones, key=lambda item: item.name)
    ]


def topology_record(obj: bpy.types.Object) -> dict:
    return {
        "vertices": [rounded(vertex.co) for vertex in obj.data.vertices],
        "edges": [list(edge.key) for edge in obj.data.edges],
        "polygons": [list(polygon.vertices) for polygon in obj.data.polygons],
    }


def shape_record(head: bpy.types.Object) -> list[dict]:
    return [
        {"name": key.name, "points": [rounded(point.co) for point in key.data]}
        for key in head.data.shape_keys.key_blocks
    ]


def main() -> None:
    args = parse_args()
    for path in (args.asset_output, args.motion_output, args.report_output):
        path.parent.mkdir(parents=True, exist_ok=True)
    clear_scene()

    collection = bpy.data.collections.new("CHAR_B03")
    bpy.context.scene.collection.children.link(collection)
    skin = make_material("MAT_TECH_SKIN", (0.42, 0.16, 0.10, 1.0), 0.5)
    suit = make_material("MAT_TECH_SUIT", (0.025, 0.055, 0.09, 1.0), 0.32)
    eye_material = make_material("MAT_EYE", (0.005, 0.008, 0.012, 1.0), 0.18)
    rig = create_armature(collection)
    # Keep the face, eyes, and jaw unobstructed in the evidence renders. The
    # mannequin is intentionally simple, but every animated channel must remain
    # visually observable.
    body = make_mesh(collection, "BODY", "cube", (0, 0, 0.88), (0.56, 0.30, 0.78), suit)
    head = make_mesh(collection, "HEAD", "sphere", (0, 0, 1.62), (0.42, 0.38, 0.48), skin)
    eye_left = make_mesh(collection, "EYE_L", "sphere", (0.09, -0.40, 1.68), (0.10, 0.06, 0.08), eye_material)
    eye_right = make_mesh(collection, "EYE_R", "sphere", (-0.09, -0.40, 1.68), (0.10, 0.06, 0.08), eye_material)
    gaze_target = bpy.data.objects.new("GAZE_TARGET", None)
    gaze_target.location = (0.0, -3.0, 1.68)
    collection.objects.link(gaze_target)
    for obj, group in ((body, "pelvis"), (head, "head"), (eye_left, "eye.L"), (eye_right, "eye.R")):
        bind_mesh(obj, rig, group)
    add_face_shapes(head)
    add_safe_constraints(rig, gaze_target)
    action = create_motion_action(rig)

    rest_pose = bone_records(rig)
    meshes = {obj.name: topology_record(obj) for obj in (body, head, eye_left, eye_right)}
    shapes = shape_record(head)
    identity = {
        "restPoseSha256": sha256_value(rest_pose),
        "topologySha256": {name: sha256_value(value) for name, value in sorted(meshes.items())},
        "shapeKeySetSha256": sha256_value(shapes),
        "bones": rest_pose,
        "shapeKeys": [item["name"] for item in shapes],
    }
    identity["identitySha256"] = sha256_value(identity)

    bpy.data.libraries.write(str(args.motion_output), {action}, fake_user=True, compress=True)
    rig.animation_data_clear()
    collection["bfs_asset_source"] = "B03_TECHNICAL_ACTOR"
    collection["bfs_generator_version"] = GENERATOR_VERSION
    collection["bfs_identity_sha256"] = identity["identitySha256"]
    bpy.data.libraries.write(str(args.asset_output), {collection}, fake_user=True, compress=True)

    report = {
        "documentType": "BFS_ACTOR_ASSET_GENERATION",
        "generatorVersion": GENERATOR_VERSION,
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "asset": {"path": str(args.asset_output), "sha256": sha256_file(args.asset_output)},
        "motion": {"path": str(args.motion_output), "sha256": sha256_file(args.motion_output), "action": action.name},
        "identity": identity,
        "explicitNonClaims": [
            "This technical mannequin is not a photoreal human benchmark.",
            "The generated motion is not evidence of actor-quality performance.",
            "Socket contacts are not mesh-level finger collision solutions.",
        ],
    }
    args.report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_ACTOR_ASSET_OK {report['asset']['sha256']} {report['motion']['sha256']} {identity['identitySha256']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_ACTOR_ASSET_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
