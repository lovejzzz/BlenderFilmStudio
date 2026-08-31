#!/usr/bin/env python3
"""Read-only Blender inventory for post-PB.7 PC.0."""

import json
import math
import sys
from pathlib import Path

import bpy


SENTINELS = (1, 48, 96, 97, 144, 192, 193, 240, 288)
HERO_TOKENS = ("B62", "GUARDIAN", "CONSOLE", "CORE", "HELMET", "VISOR", "HAND", "ARM")


def args_after_separator():
    if "--" not in sys.argv:
        raise RuntimeError("ARGS_SEPARATOR")
    values = sys.argv[sys.argv.index("--") + 1 :]
    if len(values) != 2 or values[0] != "--output":
        raise RuntimeError("USAGE")
    return Path(values[1]).resolve()


def finite(value):
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError("NONFINITE_VALUE")
    return round(number, 9)


def vector(value):
    return [finite(component) for component in value]


def matrix(value):
    return [[finite(component) for component in row] for row in value]


def hero_name(name):
    upper = name.upper()
    return any(token in upper for token in HERO_TOKENS)


def material_record(material):
    nodes = material.node_tree.nodes if material.use_nodes and material.node_tree else []
    links = material.node_tree.links if material.use_nodes and material.node_tree else []
    return {
        "name": material.name,
        "useNodes": bool(material.use_nodes),
        "nodeCount": len(nodes),
        "linkCount": len(links),
        "surfaceRenderMethod": getattr(material, "surface_render_method", None),
    }


def modifier_record(modifier):
    return {"name": modifier.name, "type": modifier.type, "showRender": bool(modifier.show_render)}


def constraint_record(constraint):
    return {
        "name": constraint.name,
        "type": constraint.type,
        "influence": finite(constraint.influence),
        "target": getattr(getattr(constraint, "target", None), "name", None),
    }


def object_record(obj):
    record = {
        "name": obj.name,
        "type": obj.type,
        "data": getattr(obj.data, "name", None),
        "parent": getattr(obj.parent, "name", None),
        "children": sorted(child.name for child in obj.children),
        "collections": sorted(collection.name for collection in obj.users_collection),
        "constraints": [constraint_record(item) for item in obj.constraints],
        "modifiers": [modifier_record(item) for item in obj.modifiers],
        "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
        "heroCandidate": hero_name(obj.name),
        "boundBoxLocal": [vector(corner) for corner in obj.bound_box] if hasattr(obj, "bound_box") else [],
    }
    if obj.type == "MESH":
        mesh = obj.data
        record["mesh"] = {
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
            "loops": len(mesh.loops),
            "uvLayers": len(mesh.uv_layers),
            "colorAttributes": len(mesh.color_attributes),
            "shapeKeys": len(mesh.shape_keys.key_blocks) if mesh.shape_keys else 0,
        }
    if obj.type == "ARMATURE":
        record["armature"] = {
            "bones": len(obj.data.bones),
            "poseBones": len(obj.pose.bones),
            "boneNames": sorted(bone.name for bone in obj.data.bones),
        }
    return record


def curve_record(curve, slot_identifier=None):
    return {
        "slot": slot_identifier,
        "dataPath": curve.data_path,
        "arrayIndex": curve.array_index,
        "keyframes": [
            {
                "frame": finite(point.co.x),
                "value": finite(point.co.y),
                "interpolation": point.interpolation,
            }
            for point in curve.keyframe_points
        ],
    }


def action_record(action):
    curves = []
    seen = set()
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        for curve in legacy:
            key = (None, curve.data_path, curve.array_index)
            if key not in seen:
                seen.add(key)
                curves.append(curve_record(curve))
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for channelbag in getattr(strip, "channelbags", []):
                slot = getattr(channelbag, "slot", None)
                slot_identifier = getattr(slot, "identifier", None)
                for curve in channelbag.fcurves:
                    key = (slot_identifier, curve.data_path, curve.array_index)
                    if key not in seen:
                        seen.add(key)
                        curves.append(curve_record(curve, slot_identifier))
    curves.sort(key=lambda item: (item["slot"] or "", item["dataPath"], item["arrayIndex"]))
    return {
        "name": action.name,
        "frameRange": [finite(action.frame_range[0]), finite(action.frame_range[1])],
        "slots": [
            {
                "identifier": slot.identifier,
                "displayName": slot.name_display,
                "targetIdType": slot.target_id_type,
            }
            for slot in getattr(action, "slots", [])
        ],
        "layerCount": len(getattr(action, "layers", [])),
        "fcurves": curves,
        "fcurveCount": len(curves),
        "keyframeCount": sum(len(item["keyframes"]) for item in curves),
    }


def animation_binding(obj):
    data = obj.animation_data
    drivers = list(data.drivers) if data else []
    return {
        "object": obj.name,
        "action": getattr(getattr(data, "action", None), "name", None),
        "actionSlot": getattr(getattr(data, "action_slot", None), "identifier", None),
        "driverCount": len(drivers),
        "driverPaths": sorted(f"{curve.data_path}[{curve.array_index}]" for curve in drivers),
        "constraintCount": len(obj.constraints),
    }


def transform_record(obj):
    record = {
        "matrixWorld": matrix(obj.matrix_world),
        "location": vector(obj.location),
        "rotationMode": obj.rotation_mode,
        "rotationEuler": vector(obj.rotation_euler),
        "scale": vector(obj.scale),
    }
    if obj.type == "CAMERA":
        record["camera"] = {"lens": finite(obj.data.lens), "sensorWidth": finite(obj.data.sensor_width)}
    if obj.type == "LIGHT":
        record["light"] = {"type": obj.data.type, "energy": finite(obj.data.energy), "color": vector(obj.data.color)}
    if obj.type == "ARMATURE":
        record["poseBones"] = {
            bone.name: {"matrix": matrix(bone.matrix), "location": vector(bone.location), "scale": vector(bone.scale)}
            for bone in sorted(obj.pose.bones, key=lambda item: item.name)
        }
    return record


def main():
    output = args_after_separator()
    if output.exists():
        raise RuntimeError("OUTPUT_EXISTS")
    if output.parent.is_symlink():
        raise RuntimeError("OUTPUT_PARENT_SYMLINK")
    scene = bpy.context.scene
    original_frame = scene.frame_current
    objects = sorted(bpy.data.objects, key=lambda item: item.name)
    object_records = [object_record(obj) for obj in objects]
    actions = [action_record(action) for action in sorted(bpy.data.actions, key=lambda item: item.name)]
    bindings = [animation_binding(obj) for obj in objects]
    animated = sorted(item["object"] for item in bindings if item["action"] or item["driverCount"] or item["constraintCount"])
    sentinels = []
    for frame in SENTINELS:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        sentinels.append({
            "frame": frame,
            "objects": {obj.name: transform_record(obj) for obj in objects},
        })
    scene.frame_set(original_frame)
    bpy.context.view_layer.update()
    meshes = [item for item in object_records if item["type"] == "MESH"]
    inventory = {
        "schemaVersion": "bfs.pc0HeroAssetActionInventory.v0.1",
        "status": "PASS",
        "sourceFilePath": bpy.data.filepath,
        "blender": {
            "version": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
            "binaryPath": bpy.app.binary_path,
        },
        "scene": {
            "name": scene.name,
            "frameStart": scene.frame_start,
            "frameEnd": scene.frame_end,
            "frameCurrentBeforeAndAfter": original_frame,
            "renderEngine": scene.render.engine,
            "camera": getattr(scene.camera, "name", None),
        },
        "counts": {
            "objects": len(objects),
            "meshes": len(meshes),
            "vertices": sum(item["mesh"]["vertices"] for item in meshes),
            "edges": sum(item["mesh"]["edges"] for item in meshes),
            "polygons": sum(item["mesh"]["polygons"] for item in meshes),
            "materials": len(bpy.data.materials),
            "actions": len(actions),
            "fcurves": sum(item["fcurveCount"] for item in actions),
            "keyframes": sum(item["keyframeCount"] for item in actions),
            "constraints": sum(len(obj.constraints) for obj in objects),
            "modifiers": sum(len(obj.modifiers) for obj in objects),
            "animatedTargets": len(animated),
            "heroCandidates": sum(1 for item in object_records if item["heroCandidate"]),
        },
        "objects": object_records,
        "heroCandidates": [item["name"] for item in object_records if item["heroCandidate"]],
        "materials": [material_record(item) for item in sorted(bpy.data.materials, key=lambda material: material.name)],
        "actions": actions,
        "animationBindings": bindings,
        "animatedTargets": animated,
        "sentinels": sentinels,
        "operations": {"renderCalls": 0, "sceneSaves": 0, "dataMutations": 0, "networkCalls": 0, "modelCalls": 0},
    }
    payload = (json.dumps(inventory, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    with output.open("xb") as handle:
        handle.write(payload)
        handle.flush()
    print(f"BFS_PC0_PROBE PASS objects={len(objects)} meshes={len(meshes)} actions={len(actions)} animated={len(animated)}")


main()
