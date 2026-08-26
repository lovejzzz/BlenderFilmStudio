"""Generate project-owned B05 technical gripper and prop asset libraries."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--character-output", type=Path, required=True)
    parser.add_argument("--prop-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rounded(values) -> list[float]:
    return [round(float(value), 9) for value in values]


def clear() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for datablocks in (bpy.data.armatures, bpy.data.meshes, bpy.data.materials, bpy.data.actions):
        for datablock in list(datablocks):
            datablocks.remove(datablock)


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.use_nodes = True
    shader = value.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = 0.42
    return value


def create_armature(collection: bpy.types.Collection) -> bpy.types.Object:
    data = bpy.data.armatures.new("RIG_B05_DATA")
    rig = bpy.data.objects.new("RIG_B05", data)
    collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    definitions = [
        ("PALM_R", (0, 0, -0.04), (0, 0, 0.04), None, False),
        # v0.2 correction: each two-bone chain is 0.18 m long. The v0.1
        # 0.12 m chains could not reach the frozen opposed contact targets.
        ("THUMB_PROXIMAL", (-0.20, -0.10, 0), (-0.11, -0.10, 0), "PALM_R", True),
        ("THUMB_DISTAL", (-0.11, -0.10, 0), (-0.02, -0.10, 0), "THUMB_PROXIMAL", True),
        ("INDEX_PROXIMAL", (0.20, 0.10, 0), (0.11, 0.10, 0), "PALM_R", True),
        ("INDEX_DISTAL", (0.11, 0.10, 0), (0.02, 0.10, 0), "INDEX_PROXIMAL", True),
    ]
    edit_bones = {}
    for name, head, tail, parent, deform in definitions:
        bone = data.edit_bones.new(name)
        bone.head, bone.tail, bone.use_deform = head, tail, deform
        if parent:
            bone.parent = edit_bones[parent]
            bone.use_connect = parent != "PALM_R"
        edit_bones[name] = bone
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.select_set(False)
    return rig


def segment_mesh(collection: bpy.types.Collection, rig: bpy.types.Object, bone_name: str, color: tuple[float, float, float, float]) -> bpy.types.Object:
    bone = rig.data.bones[bone_name]
    head, tail = bone.head_local.copy(), bone.tail_local.copy()
    direction = tail - head
    mesh = bpy.data.meshes.new(f"{bone_name}_MESH")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    transform = Matrix.Translation((head + tail) / 2) @ direction.to_track_quat("X", "Z").to_matrix().to_4x4() @ Matrix.Diagonal((direction.length, 0.024, 0.03, 1))
    bmesh.ops.transform(bm, matrix=transform, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(f"MESH_{bone_name}", mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material(f"MAT_{bone_name}", color))
    group = obj.vertex_groups.new(name=bone_name)
    group.add(range(len(mesh.vertices)), 1.0, "REPLACE")
    modifier = obj.modifiers.new("BFS_ARMATURE", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    modifier.use_bone_envelopes = False
    return obj


def create_character(path: Path) -> dict:
    clear()
    collection = bpy.data.collections.new("CHAR_B05")
    bpy.context.scene.collection.children.link(collection)
    rig = create_armature(collection)
    for name in ("THUMB_PROXIMAL", "THUMB_DISTAL"):
        segment_mesh(collection, rig, name, (0.90, 0.18, 0.08, 1))
    for name in ("INDEX_PROXIMAL", "INDEX_DISTAL"):
        segment_mesh(collection, rig, name, (1.0, 0.62, 0.08, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path.resolve()), check_existing=False, compress=True)
    return {
        "sha256": sha256_file(path),
        "armatureObject": rig.name,
        "bones": [{"name": bone.name, "head": rounded(bone.head_local), "tail": rounded(bone.tail_local), "parent": bone.parent.name if bone.parent else None} for bone in sorted(rig.data.bones, key=lambda item: item.name)],
    }


def create_prop(path: Path) -> dict:
    clear()
    collection = bpy.data.collections.new("PROP_B05")
    bpy.context.scene.collection.children.link(collection)
    mesh = bpy.data.meshes.new("PROP_BODY_MESH")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.transform(bm, matrix=Matrix.Diagonal((0.10, 0.12, 0.14, 1)), verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    prop = bpy.data.objects.new("PROP_BODY", mesh)
    collection.objects.link(prop)
    prop.data.materials.append(material("MAT_PROP_B05", (0.12, 0.42, 0.82, 1)))
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path.resolve()), check_existing=False, compress=True)
    return {"sha256": sha256_file(path), "object": prop.name, "vertices": len(mesh.vertices), "polygons": len(mesh.polygons)}


def main() -> None:
    args = parse_args()
    character = create_character(args.character_output)
    prop = create_prop(args.prop_output)
    report = {
        "documentType": "BFS_B05_COMPILER_ASSETS",
        "version": "0.2.0",
        "blender": bpy.app.version_string,
        "correction": "Finger chain length increased from 0.12 m to 0.18 m after the pre-registered first run falsified contact reachability at 0.044024683 m separation.",
        "character": character,
        "prop": prop,
    }
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")
    print(f"BFS_B05_COMPILER_ASSETS_OK {character['sha256']} {prop['sha256']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B05_COMPILER_ASSETS_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
