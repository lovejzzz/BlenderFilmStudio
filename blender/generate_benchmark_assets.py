"""Generate small, project-owned .blend libraries for B01 and B02.

This script is trusted project tooling. Runtime SceneSpecs never execute it.
It uses Blender's data API and bmesh, then writes one collection per library.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import bmesh
import bpy


def material(name: str, color: tuple[float, float, float, float], metallic: float, roughness: float, transmission: float = 0.0) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if "Transmission Weight" in shader.inputs:
        shader.inputs["Transmission Weight"].default_value = transmission
    return result


def mesh_object(collection: bpy.types.Collection, name: str, primitive: str, location=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0), assigned_material=None) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    bm = bmesh.new()
    if primitive == "cube":
        bmesh.ops.create_cube(bm, size=1.0)
    elif primitive == "plane":
        bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=0.5)
    elif primitive == "sphere":
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.5)
    elif primitive == "cylinder":
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=32, radius1=0.5, radius2=0.5, depth=1.0)
    else:
        raise ValueError(f"Unsupported primitive: {primitive}")
    bm.to_mesh(mesh)
    bm.free()
    result = bpy.data.objects.new(name, mesh)
    result.location = location
    result.scale = scale
    collection.objects.link(result)
    if assigned_material is not None:
        mesh.materials.append(assigned_material)
    return result


def build_still_life() -> bpy.types.Collection:
    collection = bpy.data.collections.new("SET_STILL_LIFE")
    neutral = material("MAT_NEUTRAL", (0.12, 0.12, 0.12, 1.0), 0.0, 0.42)
    leather = material("MAT_LEATHER", (0.16, 0.035, 0.018, 1.0), 0.0, 0.32)
    metal = material("MAT_BRUSHED_METAL", (0.42, 0.45, 0.48, 1.0), 0.92, 0.18)
    glass = material("MAT_GLASS", (0.82, 0.9, 1.0, 1.0), 0.0, 0.05, 1.0)
    skin = material("MAT_SKIN_REFERENCE", (0.58, 0.28, 0.18, 1.0), 0.0, 0.48)

    mesh_object(collection, "STAGE", "cube", (0.0, 0.0, -0.15), (5.0, 3.2, 0.3), neutral)
    mesh_object(collection, "LEATHER_BLOCK", "cube", (-1.45, 0.2, 0.55), (1.1, 1.1, 1.1), leather)
    mesh_object(collection, "METAL_SPHERE", "sphere", (0.0, 0.15, 0.72), (1.35, 1.35, 1.35), metal)
    mesh_object(collection, "GLASS_CYLINDER", "cylinder", (1.45, 0.2, 0.72), (0.9, 0.9, 1.45), glass)
    mesh_object(collection, "SKIN_TONE_CARD", "cube", (0.0, 1.05, 0.52), (1.55, 0.12, 1.0), skin)
    return collection


def build_room() -> bpy.types.Collection:
    collection = bpy.data.collections.new("SET_ROOM")
    wall = material("MAT_WARM_PLASTER", (0.34, 0.29, 0.23, 1.0), 0.0, 0.72)
    floor = material("MAT_DARK_WOOD", (0.08, 0.045, 0.025, 1.0), 0.0, 0.38)
    frame = material("MAT_WINDOW_FRAME", (0.025, 0.028, 0.03, 1.0), 0.25, 0.24)

    mesh_object(collection, "FLOOR", "cube", (0.0, 0.0, -0.1), (7.0, 7.0, 0.2), floor)
    mesh_object(collection, "BACK_WALL", "cube", (0.0, 3.5, 1.8), (7.0, 0.2, 3.6), wall)
    mesh_object(collection, "LEFT_WALL", "cube", (-3.5, 0.0, 1.8), (0.2, 7.0, 3.6), wall)
    mesh_object(collection, "RIGHT_WALL", "cube", (3.5, 0.0, 1.8), (0.2, 7.0, 3.6), wall)
    mesh_object(collection, "WINDOW_SILL", "cube", (-3.25, 0.8, 1.25), (0.24, 2.1, 0.12), frame)
    mesh_object(collection, "WINDOW_TOP", "cube", (-3.25, 0.8, 2.8), (0.24, 2.1, 0.12), frame)
    mesh_object(collection, "WINDOW_MULLION", "cube", (-3.25, 0.8, 2.0), (0.24, 0.1, 1.5), frame)
    return collection


def build_chair() -> bpy.types.Collection:
    collection = bpy.data.collections.new("PROP_CHAIR")
    wood = material("MAT_CHAIR_WOOD", (0.19, 0.07, 0.025, 1.0), 0.0, 0.3)
    fabric = material("MAT_CHAIR_FABRIC", (0.12, 0.15, 0.17, 1.0), 0.0, 0.68)
    mesh_object(collection, "CHAIR_SEAT", "cube", (0.0, 0.0, 0.52), (0.9, 0.9, 0.16), fabric)
    mesh_object(collection, "CHAIR_BACK", "cube", (0.0, 0.4, 1.18), (0.9, 0.15, 1.25), fabric)
    for index, (x, y) in enumerate(((-0.36, -0.36), (0.36, -0.36), (-0.36, 0.36), (0.36, 0.36)), start=1):
        mesh_object(collection, f"CHAIR_LEG_{index:02d}", "cube", (x, y, 0.24), (0.12, 0.12, 0.48), wood)
    return collection


BUILDERS = {
    "B01_STILL_LIFE": build_still_life,
    "B02_ROOM": build_room,
    "B02_CHAIR": build_chair,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", choices=sorted(BUILDERS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(bpy.app.driver_namespace.get("argv", []))


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    collection = BUILDERS[args.asset]()
    collection["bfs_asset_source"] = args.asset
    collection["bfs_generator_version"] = "0.1.0"
    bpy.data.libraries.write(str(args.output), {collection}, fake_user=True, compress=True)
    print(f"BFS_ASSET_WRITTEN {args.asset} {args.output}")


if __name__ == "__main__":
    import sys

    if "--" in sys.argv:
        bpy.app.driver_namespace["argv"] = sys.argv[sys.argv.index("--") + 1 :]
    else:
        bpy.app.driver_namespace["argv"] = []
    main()
