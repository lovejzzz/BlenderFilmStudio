"""Read-only inventory of evaluation-bearing structures in one Blender asset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def main() -> None:
    args = parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    auxiliary_findings = []
    inspected_auxiliary = set()

    def inspect_auxiliary(owner, label: str) -> None:
        pointer = owner.as_pointer()
        if pointer in inspected_auxiliary:
            return
        inspected_auxiliary.add(pointer)
        animation = getattr(owner, "animation_data", None)
        drivers = len(animation.drivers) if animation else 0
        action = animation.action.name if animation and animation.action else None
        library = owner.library.filepath if getattr(owner, "library", None) else None
        override = getattr(owner, "override_library", None) is not None
        if drivers or action or library or override:
            auxiliary_findings.append({"label": label, "drivers": drivers, "action": action, "library": library, "overrideLibrary": override})

    for collection in bpy.data.collections:
        inspect_auxiliary(collection, f"COLLECTION:{collection.name}")
    objects = []
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        animation = obj.animation_data
        data_animation = obj.data.animation_data if obj.data and hasattr(obj.data, "animation_data") else None
        shape_key_animation = obj.data.shape_keys.animation_data if obj.data and getattr(obj.data, "shape_keys", None) else None
        pose_constraints = sum(len(bone.constraints) for bone in obj.pose.bones) if obj.type == "ARMATURE" else 0
        pose_constraint_details = [
            {"bone": bone.name, "name": constraint.name, "type": constraint.type, "target": constraint.target.name if getattr(constraint, "target", None) else None}
            for bone in obj.pose.bones for constraint in bone.constraints
        ] if obj.type == "ARMATURE" else []
        objects.append({
            "name": obj.name, "type": obj.type,
            "drivers": len(animation.drivers) if animation else 0,
            "action": animation.action.name if animation and animation.action else None,
            "dataDrivers": len(data_animation.drivers) if data_animation else 0,
            "dataAction": data_animation.action.name if data_animation and data_animation.action else None,
            "shapeKeyDrivers": len(shape_key_animation.drivers) if shape_key_animation else 0,
            "shapeKeyAction": shape_key_animation.action.name if shape_key_animation and shape_key_animation.action else None,
            "constraints": len(obj.constraints), "poseBoneConstraints": pose_constraints,
            "poseConstraints": pose_constraint_details,
            "rigidBody": obj.rigid_body is not None, "rigidBodyConstraint": obj.rigid_body_constraint is not None,
            "library": obj.library.filepath if obj.library else None, "overrideLibrary": obj.override_library is not None,
            "modifiers": sorted(item.type for item in obj.modifiers),
        })
        for slot in obj.material_slots:
            if slot.material:
                inspect_auxiliary(slot.material, f"MATERIAL:{slot.material.name}")
                if slot.material.node_tree:
                    inspect_auxiliary(slot.material.node_tree, f"NODETREE:{slot.material.name}")
    report = {
        "documentType": "BFS_ASSET_SAFETY_INVENTORY", "version": "0.1.0", "asset": str(args.input), "blender": bpy.app.version_string,
        "autoExecuteEnabled": bpy.context.preferences.filepaths.use_scripts_auto_execute,
        "objects": objects,
        "libraries": sorted(item.filepath for item in bpy.data.libraries),
        "texts": sorted([{"name": item.name, "useModule": item.use_module} for item in bpy.data.texts], key=lambda item: item["name"]),
        "auxiliaryFindings": sorted(auxiliary_findings, key=lambda item: item["label"]),
        "totals": {
            "drivers": sum(item["drivers"] + item["dataDrivers"] + item["shapeKeyDrivers"] for item in objects) + sum(item["drivers"] for item in auxiliary_findings),
            "actions": sum(item["action"] is not None for item in objects) + sum(item["dataAction"] is not None for item in objects) + sum(item["shapeKeyAction"] is not None for item in objects) + sum(item["action"] is not None for item in auxiliary_findings),
            "constraints": sum(item["constraints"] + item["poseBoneConstraints"] for item in objects),
            "rigidBodies": sum(item["rigidBody"] or item["rigidBodyConstraint"] for item in objects),
            "linkedObjects": sum(item["library"] is not None for item in objects), "overrides": sum(item["overrideLibrary"] for item in objects),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_ASSET_SAFETY_INVENTORY {args.input} {report['totals']}")


if __name__ == "__main__":
    main()
