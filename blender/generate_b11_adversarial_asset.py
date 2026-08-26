"""Generate harmless B11 .blend fixtures carrying hidden evaluation structures."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy


VARIANTS = {"DEPENDENCY", "DRIVER", "SHAPE_KEY_DRIVER", "CONSTRAINT", "RIGID_BODY", "ACTION", "LINKED_LIBRARY", "LIBRARY_OVERRIDE", "COMBINED"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path)
    parser.add_argument("--dependency", type=Path)
    parser.add_argument("--variant", choices=sorted(VARIANTS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def main() -> None:
    args = parse_args()
    if args.variant == "DEPENDENCY":
        bpy.ops.wm.read_factory_settings(use_empty=True)
        collection = bpy.data.collections.new("B11_DEPENDENCY")
        bpy.context.scene.collection.children.link(collection)
        bpy.ops.mesh.primitive_cube_add(size=0.1)
        obj = bpy.context.object
        obj.name = "B11_DEP_OBJECT"
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
    else:
        if not args.base:
            raise RuntimeError("Non-dependency variants require --base")
        bpy.ops.wm.open_mainfile(filepath=str(args.base.resolve()), load_ui=False)
        collection = bpy.data.collections["SET_STILL_LIFE"]
        objects = {obj.name: obj for obj in collection.all_objects}
        if args.variant in {"DRIVER", "COMBINED"}:
            curve = objects["METAL_SPHERE"].driver_add("location", 2)
            curve.driver.expression = "0.25"
        if args.variant == "SHAPE_KEY_DRIVER":
            target = objects["METAL_SPHERE"]
            target.shape_key_add(name="Basis")
            key = target.shape_key_add(name="B11_MORPH")
            curve = key.driver_add("value")
            curve.driver.expression = "0.5"
        if args.variant in {"CONSTRAINT", "COMBINED"}:
            constraint = objects["LEATHER_BLOCK"].constraints.new("COPY_LOCATION")
            constraint.name = "B11_HIDDEN_COPY_LOCATION"
            constraint.target = objects["METAL_SPHERE"]
        if args.variant in {"RIGID_BODY", "COMBINED"}:
            target = objects["GLASS_CYLINDER"]
            temporary_link = target.name not in bpy.context.scene.collection.objects
            if temporary_link:
                bpy.context.scene.collection.objects.link(target)
            bpy.context.view_layer.objects.active = target
            target.select_set(True)
            bpy.ops.rigidbody.object_add()
            target.select_set(False)
            if temporary_link:
                bpy.context.scene.collection.objects.unlink(target)
        if args.variant in {"ACTION", "COMBINED"}:
            target = objects["SKIN_TONE_CARD"]
            target.location.x = 0
            target.keyframe_insert(data_path="location", frame=1, group="B11_HIDDEN_ACTION")
            target.location.x = 0.2
            target.keyframe_insert(data_path="location", frame=2, group="B11_HIDDEN_ACTION")
        if args.variant in {"LINKED_LIBRARY", "LIBRARY_OVERRIDE"}:
            if not args.dependency:
                raise RuntimeError(f"{args.variant} requires --dependency")
            with bpy.data.libraries.load(str(args.dependency.resolve()), link=True) as (source, target):
                target.collections = ["B11_DEPENDENCY"]
            linked = target.collections[0]
            if args.variant == "LINKED_LIBRARY":
                instancer = bpy.data.objects.new("B11_LINKED_INSTANCE", None)
                instancer.instance_type = "COLLECTION"
                instancer.instance_collection = linked
                collection.objects.link(instancer)
            else:
                overridden = linked.override_hierarchy_create(bpy.context.scene, bpy.context.view_layer, do_fully_editable=True)
                if overridden.name not in collection.children:
                    collection.children.link(overridden)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), check_existing=False, compress=True)
    sha = hashlib.sha256(args.output.read_bytes()).hexdigest()
    report = {"documentType": "BFS_B11_ADVERSARIAL_ASSET_GENERATION", "version": "0.1.0", "variant": args.variant, "uri": str(args.output), "sha256": sha, "blender": bpy.app.version_string, "harmlessExecutableCode": False}
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B11_ASSET_OK {args.variant} {sha} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B11_ASSET_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
