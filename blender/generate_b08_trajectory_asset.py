"""Generate the project-owned PROP_B08 library used by the B08 compiler test."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def main() -> None:
    args = parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection = bpy.data.collections.new("PROP_B08")
    bpy.context.scene.collection.children.link(collection)
    bpy.ops.mesh.primitive_cube_add(size=1)
    prop = bpy.context.object
    prop.name = "B06_PROP"
    for owner in list(prop.users_collection):
        owner.objects.unlink(prop)
    collection.objects.link(prop)
    prop.scale = (0.10, 0.12, 0.14)
    bpy.context.view_layer.objects.active = prop
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    material = bpy.data.materials.new("MAT_B08_PROP")
    material.use_nodes = True
    material.diffuse_color = (0.12, 0.42, 0.82, 1.0)
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = material.diffuse_color
    material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.28
    prop.data.materials.append(material)
    prop["bfs_asset_role"] = "B08_TRAJECTORY_REPLAY_TARGET"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), check_existing=False, compress=True)
    if "FINISHED" not in result:
        raise RuntimeError("B08 asset save failed")
    blend_sha = hashlib.sha256(args.output.read_bytes()).hexdigest()
    report = {
        "documentType": "BFS_B08_ASSET_GENERATION",
        "version": "0.1.0",
        "blender": bpy.app.version_string,
        "asset": {"uri": "library/props/B08-prop.blend", "sha256": blend_sha, "collection": collection.name},
        "target": {"name": prop.name, "type": prop.type, "dimensionsM": [round(value, 9) for value in prop.dimensions]},
        "shortcuts": {"rigidBody": prop.rigid_body is not None, "constraints": len(prop.constraints), "animation": prop.animation_data is not None},
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B08_ASSET_OK {blend_sha} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B08_ASSET_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
