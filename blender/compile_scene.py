"""Compile one verified BFS BuildPlan into a Blender 5.2 scene.

The runtime accepts data only. It never imports or executes code from a
SceneSpec or asset library, and it re-verifies both the plan and asset hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from decimal import Decimal
from pathlib import Path

import bpy
import PyOpenColorIO as ocio
from bpy_extras import anim_utils
from mathutils import Euler, Matrix, Quaternion, Vector


SUPPORTED_COMPILER_VERSIONS = {"0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.4.1", "0.5.0"}


def javascript_number(value: float) -> str:
    """Serialize a finite Python float with JSON.stringify number thresholds."""
    if not math.isfinite(value):
        raise ValueError("Canonical JSON cannot encode a non-finite number")
    if value == 0:
        return "0"
    absolute = abs(value)
    source = repr(value).lower()
    if 1e-6 <= absolute < 1e21:
        if "e" in source:
            fixed = format(Decimal(source), "f")
            return fixed.rstrip("0").rstrip(".") if "." in fixed else fixed
        return source[:-2] if source.endswith(".0") else source
    if "e" not in source:
        source = format(value, ".15e")
        mantissa, exponent = source.split("e")
        mantissa = mantissa.rstrip("0").rstrip(".")
    else:
        mantissa, exponent = source.split("e")
    exponent_value = int(exponent)
    sign = "+" if exponent_value >= 0 else "-"
    return f"{mantissa}e{sign}{abs(exponent_value)}"


def javascript_canonical_json(value: object) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return javascript_number(value)
    if isinstance(value, list):
        return "[" + ",".join(javascript_canonical_json(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(f"{javascript_canonical_json(key)}:{javascript_canonical_json(value[key])}" for key in sorted(value)) + "}"
    raise TypeError(f"Unsupported canonical JSON value: {type(value).__name__}")


def canonical_json(value: object) -> str:
    """Preserve the v0.1–v0.4 structural-hash representation."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def resolve_below(root: Path, candidate: Path, label: str) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve() if candidate.is_absolute() else (resolved_root / candidate).resolve()
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise RuntimeError(f"{label} escapes the repository root: {candidate}")
    return resolved


def load_verified_plan(plan_path: Path) -> dict:
    wrapper = json.loads(plan_path.read_text(encoding="utf-8"))
    if wrapper.get("documentType") != "BFS_BUILD_PLAN" or wrapper.get("planVersion") not in SUPPORTED_COMPILER_VERSIONS:
        raise RuntimeError("Unsupported BuildPlan document or version")
    actual_hash = sha256_bytes(javascript_canonical_json(wrapper["plan"]).encode("utf-8"))
    if actual_hash != wrapper.get("planHash"):
        raise RuntimeError(f"BuildPlan hash mismatch: expected {wrapper.get('planHash')}, received {actual_hash}")
    if tuple(bpy.app.version[:3]) != (5, 2, 0):
        raise RuntimeError(f"Blender 5.2.0 is required, received {bpy.app.version_string}")
    if wrapper["plan"]["compiler"]["version"] not in SUPPORTED_COMPILER_VERSIONS:
        raise RuntimeError("Compiler version does not match BuildPlan")
    if wrapper["plan"]["compiler"]["version"] != wrapper["planVersion"]:
        raise RuntimeError("BuildPlan wrapper and compiler versions disagree")
    return wrapper


def clear_scene(scene: bpy.types.Scene) -> bpy.types.Collection:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for camera in list(bpy.data.cameras):
        bpy.data.cameras.remove(camera)
    for light in list(bpy.data.lights):
        bpy.data.lights.remove(light)
    managed = bpy.data.collections.new("BFS_SHOT")
    scene.collection.children.link(managed)
    return managed


def apply_transform(obj: bpy.types.Object, transform: dict) -> None:
    obj.location = transform["locationM"]
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = [math.radians(value) for value in transform["rotationEulerDeg"]]
    obj.scale = transform["scale"]


def append_asset(root: Path, managed: bpy.types.Collection, asset: dict, direct_import: bool = False) -> tuple[bpy.types.Object, bpy.types.Collection]:
    asset_path = resolve_below(root, Path(asset["uri"]), f"Asset {asset['id']}")
    actual_hash = sha256_file(asset_path)
    if actual_hash != asset["verifiedSha256"] or actual_hash != asset["sha256"]:
        raise RuntimeError(f"Asset hash mismatch during Blender compile: {asset['id']}")
    with bpy.data.libraries.load(str(asset_path), link=False, recursive=True) as (source, target):
        if asset["id"] not in source.collections:
            raise RuntimeError(f"Asset library {asset['uri']} has no collection named {asset['id']}")
        target.collections = [asset["id"]]
    imported = target.collections[0]
    if imported is None:
        raise RuntimeError(f"Blender could not append collection {asset['id']}")
    root_object = bpy.data.objects.new(asset["id"], None)
    root_object.hide_render = not asset["visible"]
    root_object["bfs_asset_sha256"] = actual_hash
    root_object["bfs_asset_version"] = asset["version"]
    apply_transform(root_object, asset["transform"])
    managed.objects.link(root_object)
    if asset["kind"] == "CHARACTER" or direct_import:
        managed.children.link(imported)
        for obj in imported.all_objects:
            if obj.parent is None:
                obj.parent = root_object
        root_object["bfs_character_collection"] = imported.name
    else:
        root_object.instance_type = "COLLECTION"
        root_object.instance_collection = imported
    return root_object, imported


def create_targets(
    managed: bpy.types.Collection,
    target_specs: list[dict],
    asset_collections: dict[str, bpy.types.Collection] | None = None,
) -> dict[tuple[str, str], bpy.types.Object]:
    targets = {}
    for target in target_specs:
        for socket in target["sockets"]:
            obj = bpy.data.objects.new(f"{target['id']}__{socket['id']}", None)
            obj.empty_display_type = "SPHERE"
            obj.empty_display_size = 0.06
            obj["bfs_target_id"] = target["id"]
            obj["bfs_target_kind"] = target["kind"]
            obj["bfs_socket_id"] = socket["id"]
            if socket.get("binding") == "ASSET_OBJECT":
                if not asset_collections or socket["assetRef"] not in asset_collections:
                    raise RuntimeError(f"Target socket asset is missing: {socket['assetRef']}")
                object_map = {item.name: item for item in asset_collections[socket["assetRef"]].all_objects}
                parent = object_map.get(socket["objectRef"])
                if parent is None:
                    raise RuntimeError(f"Target socket object is missing: {socket['assetRef']}.{socket['objectRef']}")
                obj.parent = parent
                obj["bfs_target_binding"] = "ASSET_OBJECT"
                obj["bfs_target_asset_ref"] = socket["assetRef"]
                obj["bfs_target_object_ref"] = socket["objectRef"]
            else:
                obj["bfs_target_binding"] = "WORLD"
            apply_transform(obj, socket["transform"])
            managed.objects.link(obj)
            targets[(target["id"], socket["id"])] = obj
    return targets


def set_interpolation(animation_data, interpolation_by_frame: dict[int, str]) -> None:
    if not animation_data or not animation_data.action:
        return
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(animation_data)
    if not channelbag:
        return
    for curve in channelbag.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = interpolation_by_frame.get(round(point.co.x), "BEZIER")


def apply_actor_performance(
    repository_root: Path,
    actor: dict,
    asset_root: bpy.types.Object,
    asset_collection: bpy.types.Collection,
    targets: dict[tuple[str, str], bpy.types.Object],
) -> dict:
    actor_spec = actor["actorSpec"]
    objects = {obj.name: obj for obj in asset_collection.all_objects}
    rig = objects[actor_spec["rig"]["armatureObject"]]
    actions = []
    for action_spec in actor_spec["performance"]["bodyActions"]:
        action_path = resolve_below(repository_root, Path(action_spec["uri"]), f"Actor action {action_spec['id']}")
        actual_hash = sha256_file(action_path)
        if actual_hash != action_spec["sha256"] or actual_hash != action_spec["verifiedSha256"]:
            raise RuntimeError(f"Actor action hash mismatch during Blender compile: {action_spec['id']}")
        with bpy.data.libraries.load(str(action_path), link=False) as (source, target):
            if action_spec["actionName"] not in source.actions:
                raise RuntimeError(f"Actor action {action_spec['actionName']} is missing from {action_spec['uri']}")
            target.actions = [action_spec["actionName"]]
        action = target.actions[0]
        actions.append(action)
    if actions:
        animation_data = rig.animation_data_create()
        animation_data.action = actions[0]
        animation_data.action_slot = actions[0].slots[0]

    shape_mesh = objects[actor_spec["deformation"]["shapeKeyMesh"]]
    shape_keys = shape_mesh.data.shape_keys
    channel_map = {item["id"]: item for item in actor_spec["deformation"]["shapeChannels"]}
    interpolation = {}
    for curve in actor_spec["performance"]["facialCurves"]:
        key_block = shape_keys.key_blocks[channel_map[curve["channel"]]["targetKey"]]
        for key in curve["keys"]:
            key_block.value = key["value"]
            key_block.keyframe_insert(data_path="value", frame=key["frame"], group="BFS_FACE")
            interpolation[key["frame"]] = key["interpolation"]
    set_interpolation(shape_keys.animation_data, interpolation)

    gaze_target = objects["GAZE_TARGET"]
    bpy.context.view_layer.update()
    actor_inverse = asset_root.matrix_world.inverted()
    gaze_bindings = []
    for key in actor_spec["performance"]["gazeKeys"]:
        external = targets[(key["targetRef"], key["targetSocket"])]
        gaze_target.location = actor_inverse @ external.matrix_world.translation
        gaze_target.keyframe_insert(data_path="location", frame=key["frame"], group="BFS_GAZE_TARGET")
        gaze_bindings.append({"frame": key["frame"], "target": key["targetRef"], "socket": key["targetSocket"]})

    rig["bfs_actor_id"] = actor["id"]
    rig["bfs_actor_spec_sha256"] = actor["verifiedActorSpecSha256"]
    rig["bfs_actor_identity_sha256"] = asset_collection.get("bfs_identity_sha256", "")
    structure = {
        "id": actor["id"],
        "assetRef": actor["assetRef"],
        "actorSpecSha256": actor["verifiedActorSpecSha256"],
        "actorSpecCanonicalSha256": actor["actorSpecCanonicalSha256"],
        "identitySha256": asset_collection.get("bfs_identity_sha256", ""),
        "actions": [
            {"id": spec["id"], "name": spec["actionName"], "sha256": spec["verifiedSha256"]}
            for spec in actor_spec["performance"]["bodyActions"]
        ],
        "gazeBindings": gaze_bindings,
        "contactBindings": [
            {"id": item["id"], "effectorSocket": item["effectorSocket"], "target": item["targetRef"], "targetSocket": item["targetSocket"], "frameStart": item["frameStart"], "frameEnd": item["frameEnd"]}
            for item in actor_spec["performance"]["contacts"]
        ],
        "bodyAnimation": animation_structure(rig),
        "facialAnimation": animation_structure(shape_keys),
        "gazeAnimation": animation_structure(gaze_target),
    }
    return structure


def create_attachments(
    scene: bpy.types.Scene,
    attachment_specs: list[dict],
    actor_specs: list[dict],
    asset_roots: dict[str, bpy.types.Object],
    asset_collections: dict[str, bpy.types.Collection],
) -> list[dict]:
    actor_map = {actor["id"]: actor for actor in actor_specs}
    reports = []
    for spec in attachment_specs:
        actor = actor_map.get(spec["targetActorRef"])
        if actor is None or "actorSpec" not in actor:
            raise RuntimeError(f"Attachment actor is missing or unresolved: {spec['targetActorRef']}")
        actor_spec = actor["actorSpec"]
        socket = next((item for item in actor_spec["sockets"] if item["id"] == spec["targetEffectorSocket"]), None)
        if socket is None:
            raise RuntimeError(f"Attachment socket is missing: {spec['targetActorRef']}.{spec['targetEffectorSocket']}")
        bone_mapping = next((item for item in actor_spec["rig"]["bones"] if item["semantic"] == socket["boneSemantic"]), None)
        if bone_mapping is None:
            raise RuntimeError(f"Attachment socket has no semantic bone mapping: {socket['boneSemantic']}")
        actor_objects = {obj.name: obj for obj in asset_collections[actor["assetRef"]].all_objects}
        rig = actor_objects.get(actor_spec["rig"]["armatureObject"])
        if rig is None or bone_mapping["bone"] not in rig.pose.bones:
            raise RuntimeError(f"Attachment target bone is missing: {bone_mapping['bone']}")
        owner = asset_roots.get(spec["ownerAssetRef"])
        if owner is None:
            raise RuntimeError(f"Attachment owner asset is missing: {spec['ownerAssetRef']}")

        initial_transform = {
            "locationM": rounded(owner.location),
            "rotationEulerDeg": [round(math.degrees(value), 9) for value in owner.rotation_euler],
            "scale": rounded(owner.scale),
        }
        acquire_frame = next(key["frame"] for key in spec["influenceKeys"] if key["value"] == 1)
        release_frame = next(
            key["frame"] for previous, key in zip(spec["influenceKeys"], spec["influenceKeys"][1:])
            if previous["value"] == 1 and key["value"] == 0
        )
        for frame, transform in (
            (scene.frame_start, initial_transform),
            (release_frame - 1, initial_transform),
            (release_frame, spec["releaseTransform"]),
        ):
            apply_transform(owner, transform)
            for data_path in ("location", "rotation_euler", "scale"):
                owner.keyframe_insert(data_path=data_path, frame=frame, group="BFS_ATTACHMENT_BASE")
        set_interpolation(owner.animation_data, {scene.frame_start: "CONSTANT", release_frame - 1: "CONSTANT", release_frame: "CONSTANT"})

        apply_transform(owner, initial_transform)
        constraint = owner.constraints.new("CHILD_OF")
        constraint.name = spec["id"]
        constraint.target = rig
        constraint.subtarget = bone_mapping["bone"]
        scene.frame_set(acquire_frame)
        bpy.context.view_layer.update()
        target_matrix = rig.matrix_world @ rig.pose.bones[bone_mapping["bone"]].matrix
        constraint.inverse_matrix = target_matrix.inverted()
        for key in spec["influenceKeys"]:
            constraint.influence = key["value"]
            constraint.keyframe_insert(data_path="influence", frame=key["frame"], group="BFS_ATTACHMENT_INFLUENCE")
        attachment_interpolation = {
            scene.frame_start: "CONSTANT",
            release_frame - 1: "CONSTANT",
            release_frame: "CONSTANT",
            **{key["frame"]: key["interpolation"] for key in spec["influenceKeys"]},
        }
        set_interpolation(owner.animation_data, attachment_interpolation)
        owner["bfs_attachment_id"] = spec["id"]
        owner["bfs_attachment_inverse_policy"] = spec["inversePolicy"]
        reports.append({
            "id": spec["id"],
            "type": constraint.type,
            "owner": spec["ownerAssetRef"],
            "targetActor": spec["targetActorRef"],
            "targetSocket": spec["targetEffectorSocket"],
            "targetBone": bone_mapping["bone"],
            "inverseMatrix": [rounded(row) for row in constraint.inverse_matrix],
            "influenceKeys": spec["influenceKeys"],
            "ownerAnimation": animation_structure(owner),
        })
    scene.frame_set(scene.frame_start)
    return reports


def create_grasps(
    scene: bpy.types.Scene,
    managed: bpy.types.Collection,
    grasp_specs: list[dict],
    asset_roots: dict[str, bpy.types.Object],
    asset_collections: dict[str, bpy.types.Collection],
) -> list[dict]:
    reports = []
    for binding in grasp_specs:
        spec = binding["graspSpec"]
        actor_objects = {obj.name: obj for obj in asset_collections[binding["actorAssetRef"]].all_objects}
        prop_objects = {obj.name: obj for obj in asset_collections[binding["propAssetRef"]].all_objects}
        rig = actor_objects.get(binding["armatureObject"])
        prop_object = prop_objects.get(binding["propObject"])
        actor_root = asset_roots[binding["actorAssetRef"]]
        prop_root = asset_roots[binding["propAssetRef"]]
        if rig is None or rig.type != "ARMATURE":
            raise RuntimeError(f"Grasp armature is missing: {binding['armatureObject']}")
        if prop_object is None or prop_object.type != "MESH":
            raise RuntimeError(f"Grasp prop object is missing: {binding['propObject']}")
        if spec["palmSocket"] not in rig.pose.bones:
            raise RuntimeError(f"Grasp palm bone is missing: {spec['palmSocket']}")

        configured_bones = []
        for finger in spec["fingerChains"]:
            for bone_spec in finger["bones"]:
                name = bone_spec["boneSemantic"]
                if name not in rig.pose.bones:
                    raise RuntimeError(f"Grasp finger bone is missing: {name}")
                bone = rig.pose.bones[name]
                axis = bone_spec["rotationAxis"]
                bone.rotation_mode = "XYZ"
                bone.lock_ik_x = axis != "X"
                bone.lock_ik_y = axis != "Y"
                bone.lock_ik_z = axis != "Z"
                for candidate in ("x", "y", "z"):
                    setattr(bone, f"use_ik_limit_{candidate}", candidate.upper() == axis)
                    if candidate.upper() == axis:
                        setattr(bone, f"ik_min_{candidate}", math.radians(bone_spec["minimumDeg"]))
                        setattr(bone, f"ik_max_{candidate}", math.radians(bone_spec["maximumDeg"]))
                        setattr(bone, f"ik_stiffness_{candidate}", bone_spec["ikStiffness"])
                bone.ik_stretch = 0
                configured_bones.append({
                    "finger": finger["id"], "bone": name, "axis": axis,
                    "minimumDeg": bone_spec["minimumDeg"], "maximumDeg": bone_spec["maximumDeg"],
                    "ikStiffness": bone_spec["ikStiffness"], "ikStretch": bone.ik_stretch,
                })

        frame = bpy.data.objects.new(f"{binding['id']}__TRANSPORT_FRAME", None)
        frame.empty_display_type = "ARROWS"
        frame.empty_display_size = 0.04
        frame["bfs_grasp_id"] = binding["id"]
        managed.objects.link(frame)
        for key in binding["transportKeys"]:
            # Move the full character asset root so both the armature and its
            # visible deformed meshes share the declared transport transform.
            actor_root.location = key["locationM"]
            actor_root.keyframe_insert(data_path="location", frame=key["frame"], group="BFS_GRASP_TRANSPORT")
            frame.location = key["locationM"]
            frame.keyframe_insert(data_path="location", frame=key["frame"], group="BFS_GRASP_TRANSPORT")
        transport_interpolation = {key["frame"]: key["interpolation"] for key in binding["transportKeys"]}
        set_interpolation(actor_root.animation_data, transport_interpolation)
        set_interpolation(frame.animation_data, transport_interpolation)

        scene.frame_set(spec["phases"]["closure"]["end"])
        bpy.context.view_layer.update()
        contact_by_finger = {item["fingerRef"]: item for item in spec["contactPatches"]}
        target_reports = []
        influence_frames = {
            spec["phases"]["closure"]["start"] - 1: 0.0,
            spec["phases"]["closure"]["start"]: 0.0,
            spec["phases"]["closure"]["end"]: 1.0,
            spec["phases"]["hold"]["end"]: 1.0,
            spec["phases"]["release"]["end"]: 0.0,
        }
        for finger in spec["fingerChains"]:
            contact = contact_by_finger.get(finger["id"])
            if contact is None:
                raise RuntimeError(f"Grasp finger has no contact patch: {finger['id']}")
            last_bone = rig.pose.bones[finger["bones"][-1]["boneSemantic"]]
            target = bpy.data.objects.new(f"{binding['id']}__{contact['id']}", None)
            target.empty_display_type = "SPHERE"
            target.empty_display_size = 0.012
            target.parent = frame
            separation = (contact["separationRangeM"]["minimum"] + contact["separationRangeM"]["maximum"]) / 2
            local_point = Vector(contact["targetPointLocalM"]) + Vector(contact["targetNormalLocal"]) * separation
            target.location = prop_object.matrix_world @ local_point
            managed.objects.link(target)
            constraint = last_bone.constraints.new("IK")
            constraint.name = f"BFS_GRASP_IK_{finger['id']}"
            constraint.target = target
            constraint.chain_count = len(finger["bones"])
            constraint.use_stretch = False
            for key_frame, value in sorted(influence_frames.items()):
                constraint.influence = value
                constraint.keyframe_insert(data_path="influence", frame=key_frame, group="BFS_GRASP_IK")
            target_reports.append({
                "finger": finger["id"], "contact": contact["id"], "target": target.name,
                "lastBone": last_bone.name, "chainCount": constraint.chain_count,
                "localPoint": rounded(local_point), "influenceKeys": [{"frame": key, "value": value} for key, value in sorted(influence_frames.items())],
            })
        set_interpolation(rig.animation_data, {**transport_interpolation, **{frame: "LINEAR" for frame in influence_frames}})

        initial_location = Vector(prop_root.location)
        release_frame = spec["phases"]["release"]["end"]
        final_transport = Vector(binding["transportKeys"][-1]["locationM"])
        for key_frame, location in ((scene.frame_start, initial_location), (release_frame - 1, initial_location), (release_frame, initial_location + final_transport)):
            prop_root.location = location
            prop_root.keyframe_insert(data_path="location", frame=key_frame, group="BFS_GRASP_PROP_BASE")
        prop_constraint = prop_root.constraints.new("CHILD_OF")
        prop_constraint.name = f"BFS_GRASP_PROP_{binding['id']}"
        prop_constraint.target = rig
        prop_constraint.subtarget = spec["palmSocket"]
        acquire_frame = spec["phases"]["closure"]["end"]
        scene.frame_set(acquire_frame)
        bpy.context.view_layer.update()
        target_matrix = rig.matrix_world @ rig.pose.bones[spec["palmSocket"]].matrix
        prop_constraint.inverse_matrix = target_matrix.inverted()
        prop_influence = {
            acquire_frame - 1: 0.0, acquire_frame: 1.0,
            spec["phases"]["hold"]["end"]: 1.0, release_frame: 0.0,
        }
        for key_frame, value in sorted(prop_influence.items()):
            prop_constraint.influence = value
            prop_constraint.keyframe_insert(data_path="influence", frame=key_frame, group="BFS_GRASP_PROP")
        set_interpolation(prop_root.animation_data, {scene.frame_start: "CONSTANT", release_frame - 1: "CONSTANT", release_frame: "CONSTANT", **{frame: "CONSTANT" for frame in prop_influence}})
        reports.append({
            "id": binding["id"], "graspSpecSha256": binding["verifiedGraspSpecSha256"],
            "actorAssetRef": binding["actorAssetRef"], "propAssetRef": binding["propAssetRef"],
            "armature": rig.name, "palmBone": spec["palmSocket"], "configuredBones": configured_bones,
            "targets": target_reports, "transportKeys": binding["transportKeys"],
            "propConstraint": {"name": prop_constraint.name, "type": prop_constraint.type, "subtarget": prop_constraint.subtarget, "influenceKeys": [{"frame": key, "value": value} for key, value in sorted(prop_influence.items())]},
            "actorRootAnimation": animation_structure(actor_root), "rigAnimation": animation_structure(rig),
            "frameAnimation": animation_structure(frame), "propAnimation": animation_structure(prop_root),
        })
    scene.frame_set(scene.frame_start)
    return reports


def create_trajectories(
    scene: bpy.types.Scene,
    trajectory_bindings: list[dict],
    asset_collections: dict[str, bpy.types.Collection],
) -> list[dict]:
    reports = []
    for binding in trajectory_bindings:
        objects = {obj.name: obj for obj in asset_collections[binding["assetRef"]].all_objects}
        target = objects.get(binding["objectRef"])
        if target is None:
            raise RuntimeError(f"Trajectory target object is missing: {binding['assetRef']}.{binding['objectRef']}")
        if target.rigid_body is not None:
            raise RuntimeError(f"Trajectory target has a pre-existing rigid body: {target.name}")
        if len(target.constraints) > 0:
            raise RuntimeError(f"Trajectory target has pre-existing constraints: {target.name}")
        if target.animation_data is not None:
            raise RuntimeError(f"Trajectory target has pre-existing animation or drivers: {target.name}")
        spec = binding["trajectorySpec"]
        if binding["applicationMode"] != "BAKED_WORLD_TRANSFORM" or binding["disablePhysics"] is not True or spec["space"] != "WORLD":
            raise RuntimeError(f"Unsupported trajectory application mode: {binding['id']}")
        target.rotation_mode = "QUATERNION"
        target["bfs_trajectory_id"] = binding["id"]
        target["bfs_trajectory_sha256"] = binding["verifiedTrajectorySpecSha256"]
        target["bfs_source_evaluation_sha256"] = binding["verifiedSourceEvaluationSha256"]
        target["bfs_selection_status"] = spec["selectionStatus"]
        for sample in spec["samples"]:
            scene.frame_set(sample["frame"])
            rotation = Quaternion(sample["rotationQuaternionWxyz"])
            rotation.normalize()
            desired_world = Matrix.Translation(Vector(sample["locationM"])) @ rotation.to_matrix().to_4x4()
            local = target.parent.matrix_world.inverted_safe() @ desired_world if target.parent else desired_world
            location, local_rotation, local_scale = local.decompose()
            if max(abs(value - 1.0) for value in local_scale) > 1e-6:
                raise RuntimeError(f"Trajectory parent introduces scale at frame {sample['frame']}: {target.name}")
            target.location = location
            target.rotation_quaternion = local_rotation
            target.scale = local_scale
            target.keyframe_insert(data_path="location", frame=sample["frame"], group="BFS_TRAJECTORY_REPLAY")
            target.keyframe_insert(data_path="rotation_quaternion", frame=sample["frame"], group="BFS_TRAJECTORY_REPLAY")
        set_interpolation(target.animation_data, {sample["frame"]: "LINEAR" for sample in spec["samples"]})
        reports.append({
            "id": binding["id"],
            "assetRef": binding["assetRef"],
            "objectRef": binding["objectRef"],
            "applicationMode": binding["applicationMode"],
            "disablePhysics": binding["disablePhysics"],
            "trajectorySpecSha256": binding["verifiedTrajectorySpecSha256"],
            "sourceEvaluationSha256": binding["verifiedSourceEvaluationSha256"],
            "selectionStatus": spec["selectionStatus"],
            "samples": len(spec["samples"]),
            "animation": animation_structure(target),
        })
    scene.frame_set(scene.frame_start)
    return reports


def create_camera(managed: bpy.types.Collection, camera_spec: dict) -> bpy.types.Object:
    camera = bpy.data.cameras.new(f"{camera_spec['id']}_DATA")
    camera.lens = camera_spec["lensMm"]
    camera.sensor_width = camera_spec["sensorWidthMm"]
    camera.dof.use_dof = True
    camera.dof.aperture_fstop = camera_spec["apertureFStop"]
    camera.dof.focus_distance = camera_spec["focusDistanceM"]
    obj = bpy.data.objects.new(camera_spec["id"], camera)
    obj["bfs_shutter_angle_deg"] = camera_spec["shutterAngleDeg"]
    apply_transform(obj, camera_spec["transform"])
    managed.objects.link(obj)

    for key in camera_spec.get("transformKeys", []):
        apply_transform(obj, key["transform"])
        for data_path in ("location", "rotation_euler", "scale"):
            obj.keyframe_insert(data_path=data_path, frame=key["frame"], group="BFS_TRANSFORM")
    if camera_spec.get("transformKeys") and obj.animation_data and obj.animation_data.action:
        channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(obj.animation_data)
        curves = channelbag.fcurves if channelbag else []
        interpolation_by_frame = {key["frame"]: key["interpolation"] for key in camera_spec["transformKeys"]}
        for curve in curves:
            for point in curve.keyframe_points:
                point.interpolation = interpolation_by_frame.get(round(point.co.x), "LINEAR")
    if camera_spec.get("transformKeys"):
        apply_transform(obj, camera_spec["transformKeys"][0]["transform"])
    return obj


def create_light(managed: bpy.types.Collection, light_spec: dict) -> bpy.types.Object:
    light = bpy.data.lights.new(f"{light_spec['id']}_DATA", light_spec["type"])
    light.color = light_spec["colorLinear"]
    light.energy = light_spec["energy"]
    if light_spec["type"] == "AREA":
        light.shape = "DISK"
        light.size = light_spec["sizeM"]
    elif light_spec["type"] in {"POINT", "SPOT"}:
        light.shadow_soft_size = light_spec["sizeM"] / 2
    elif light_spec["type"] == "SUN":
        light.angle = min(light_spec["sizeM"], math.pi)
    obj = bpy.data.objects.new(light_spec["id"], light)
    apply_transform(obj, light_spec["transform"])
    managed.objects.link(obj)
    return obj


def configure_world(scene: bpy.types.Scene, world_spec: dict) -> None:
    world = bpy.data.worlds.new("BFS_WORLD")
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (*world_spec["backgroundLinear"], 1.0)
    background.inputs["Strength"].default_value = world_spec["strength"]
    scene.world = world


def configure_render(scene: bpy.types.Scene, render_spec: dict, output_spec: dict, active_camera: dict, artifact_root: Path) -> list[str]:
    warnings = []
    scene.render.engine = render_spec["finalEngine"]
    scene.render.resolution_x = render_spec["resolution"]["width"]
    scene.render.resolution_y = render_spec["resolution"]["height"]
    scene.render.resolution_percentage = render_spec["resolution"]["percentage"]
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.render.image_settings.exr_codec = "ZIP"
    scene.render.filepath = str(artifact_root / "frames" / "frame_")
    scene.render.motion_blur_shutter = active_camera["shutterAngleDeg"] / 360.0
    scene.render.motion_blur_position = "CENTER"
    scene.cycles.samples = render_spec["samplesFinal"]
    scene.cycles.seed = int(scene.get("bfs_shot_seed", 0))
    scene.cycles.use_animated_seed = False
    scene.cycles.device = "CPU"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 8

    view_layer = scene.view_layers[0]
    view_layer.name = "BFS_MASTER"
    view_layer.use_pass_z = "Depth" in render_spec["passes"]
    view_layer.use_pass_normal = "Normal" in render_spec["passes"]
    view_layer.use_pass_vector = "Vector" in render_spec["passes"]
    view_layer.use_pass_cryptomatte_object = "Cryptomatte" in render_spec["passes"]
    view_layer.pass_cryptomatte_depth = 6
    if hasattr(view_layer, "cycles"):
        view_layer.cycles.use_denoising = render_spec["denoise"]

    color_spec = output_spec["color"]
    current_config = ocio.GetCurrentConfig()
    current_name = current_config.getName()
    current_scene_linear = current_config.getRoleColorSpace(ocio.ROLE_SCENE_LINEAR)
    if current_name != color_spec["ocioConfigName"]:
        raise RuntimeError(f"OCIO config mismatch: expected {color_spec['ocioConfigName']}, received {current_name}")
    if current_scene_linear != color_spec["sceneLinearRole"]:
        raise RuntimeError(f"OCIO scene-linear role mismatch: expected {color_spec['sceneLinearRole']}, received {current_scene_linear}")
    review = next(item for item in color_spec["displayTransforms"] if item["id"] == "REVIEW_SDR")
    scene.display_settings.display_device = review["display"]
    scene.view_settings.view_transform = review["view"]
    scene["bfs_output_profile"] = render_spec["outputProfile"]
    scene["bfs_declared_encoding"] = color_spec["sceneLinearEncoding"]
    scene["bfs_ocio_config"] = current_name
    scene["bfs_ocio_sha256"] = color_spec["verifiedOcioConfigSha256"]
    scene["bfs_ocio_status"] = "PINNED_AND_VERIFIED"
    warnings.append("ACES 2 OCIO config is pinned and verified; the physical review display is not yet calibrated by this experiment.")
    return warnings


def rounded(values) -> list[float]:
    return [round(float(value), 9) for value in values]


def collection_structure(collection: bpy.types.Collection) -> dict:
    objects = []
    for obj in sorted(collection.all_objects, key=lambda item: item.name):
        record = {
            "name": obj.name,
            "type": obj.type,
            "location": rounded(obj.location),
            "rotationEuler": rounded(obj.rotation_euler),
            "scale": rounded(obj.scale),
            "materials": sorted(slot.material.name for slot in obj.material_slots if slot.material),
        }
        if obj.type == "MESH":
            record["mesh"] = {"vertices": len(obj.data.vertices), "edges": len(obj.data.edges), "polygons": len(obj.data.polygons)}
        objects.append(record)
    return {"name": collection.name, "objects": objects}


def evaluated_camera_samples(scene: bpy.types.Scene, camera_objects: dict[str, bpy.types.Object], cameras: list[dict]) -> list[dict]:
    samples = []
    for camera in cameras:
        obj = camera_objects[camera["id"]]
        key_frames = [key["frame"] for key in camera.get("transformKeys", [])]
        midpoint_frames = [math.floor((left + right) / 2) for left, right in zip(key_frames, key_frames[1:])]
        frames = sorted(set(key_frames + midpoint_frames)) or [scene.frame_start]
        for frame in frames:
            scene.frame_set(frame)
            samples.append({
                "camera": camera["id"],
                "frame": frame,
                "location": rounded(obj.location),
                "rotationEuler": rounded(obj.rotation_euler),
                "scale": rounded(obj.scale),
            })
    scene.frame_set(scene.frame_start)
    return samples


def animation_structure(obj: bpy.types.Object) -> list[dict]:
    if not obj.animation_data or not obj.animation_data.action:
        return []
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(obj.animation_data)
    if channelbag is None:
        return []
    result = []
    for curve in sorted(channelbag.fcurves, key=lambda item: (item.data_path, item.array_index)):
        result.append({
            "dataPath": curve.data_path,
            "arrayIndex": curve.array_index,
            "keyframes": [
                {
                    "frame": round(float(point.co.x), 9),
                    "value": round(float(point.co.y), 9),
                    "interpolation": point.interpolation,
                }
                for point in curve.keyframe_points
            ],
        })
    return result


def build_structure(
    scene: bpy.types.Scene,
    wrapper: dict,
    asset_collections: dict[str, bpy.types.Collection],
    camera_objects: dict[str, bpy.types.Object],
    target_objects: dict[tuple[str, str], bpy.types.Object],
    actor_reports: list[dict],
    attachment_reports: list[dict],
    grasp_reports: list[dict],
    trajectory_reports: list[dict],
) -> dict:
    plan = wrapper["plan"]
    managed = bpy.data.collections["BFS_SHOT"]
    managed_objects = []
    for obj in sorted(managed.objects, key=lambda item: item.name):
        record = {
            "name": obj.name,
            "type": obj.type,
            "location": rounded(obj.location),
            "rotationEuler": rounded(obj.rotation_euler),
            "scale": rounded(obj.scale),
        }
        if obj.type == "CAMERA":
            record["camera"] = {
                "lensMm": round(obj.data.lens, 9),
                "sensorWidthMm": round(obj.data.sensor_width, 9),
                "focusDistanceM": round(obj.data.dof.focus_distance, 9),
                "apertureFStop": round(obj.data.dof.aperture_fstop, 9),
            }
            record["animation"] = animation_structure(obj)
        elif obj.type == "LIGHT":
            record["light"] = {"type": obj.data.type, "energy": round(obj.data.energy, 9), "color": rounded(obj.data.color)}
        elif obj.instance_collection:
            record["instanceCollection"] = obj.instance_collection.name
        managed_objects.append(record)

    structure = {
        "compilerVersion": plan["compiler"]["version"],
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "planHash": wrapper["planHash"],
        "shot": plan["shot"],
        "managedCollection": {"name": managed.name, "objects": managed_objects},
        "assetCollections": [collection_structure(asset_collections[key]) for key in sorted(asset_collections)],
        "cameraSamples": evaluated_camera_samples(scene, camera_objects, plan["cameras"]),
        "render": {
            "engine": scene.render.engine,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
            "fps": scene.render.fps,
            "fpsBase": scene.render.fps_base,
            "frameRange": [scene.frame_start, scene.frame_end],
            "fileFormat": scene.render.image_settings.file_format,
            "colorDepth": scene.render.image_settings.color_depth,
            "exrCodec": scene.render.image_settings.exr_codec,
            "cyclesSamples": scene.cycles.samples,
            "cyclesSeed": scene.cycles.seed,
            "cyclesAnimatedSeed": scene.cycles.use_animated_seed,
            "cyclesDevice": scene.cycles.device,
            "threadsMode": scene.render.threads_mode,
            "threads": scene.render.threads,
            "ocioConfig": scene["bfs_ocio_config"],
            "ocioConfigSha256": scene["bfs_ocio_sha256"],
            "sceneLinearRole": scene["bfs_declared_encoding"],
            "display": scene.display_settings.display_device,
            "view": scene.view_settings.view_transform,
        },
    }
    if wrapper["planVersion"] in {"0.2.0", "0.3.0", "0.4.0", "0.4.1", "0.5.0"}:
        structure["targets"] = [
            {
                "target": target_id,
                "socket": socket_id,
                "binding": obj.get("bfs_target_binding", "WORLD"),
                "parent": obj.parent.name if obj.parent else None,
                "locationLocal": rounded(obj.location),
                "rotationEulerLocal": rounded(obj.rotation_euler),
                "scaleLocal": rounded(obj.scale),
            }
            for (target_id, socket_id), obj in sorted(target_objects.items())
        ]
        structure["actors"] = actor_reports
    if wrapper["planVersion"] in {"0.3.0", "0.4.0", "0.4.1", "0.5.0"}:
        structure["attachments"] = attachment_reports
        structure["geometryEvaluations"] = wrapper["plan"].get("geometryEvaluations", [])
    if wrapper["planVersion"] in {"0.4.0", "0.4.1", "0.5.0"}:
        structure["grasps"] = grasp_reports
    if wrapper["planVersion"] == "0.5.0":
        structure["trajectories"] = trajectory_reports
    return structure


def main() -> None:
    started = time.perf_counter()
    args = parse_args()
    repository_root = args.repository_root.resolve()
    plan_path = resolve_below(repository_root, args.plan, "BuildPlan")
    wrapper = load_verified_plan(plan_path)
    plan = wrapper["plan"]
    planned_root = resolve_below(repository_root, Path(plan["outputs"]["root"]), "Planned output")
    artifact_root = resolve_below(repository_root, args.output_dir, "Experiment output") if args.output_dir else planned_root
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "frames").mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    managed = clear_scene(scene)
    scene.name = plan["shot"]["id"]
    scene.frame_start = plan["shot"]["frameStart"]
    scene.frame_end = plan["shot"]["frameEnd"]
    scene.render.fps = plan["shot"]["frameRate"]["numerator"]
    scene.render.fps_base = plan["shot"]["frameRate"]["denominator"]
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = plan["shot"]["unitScaleMeters"]
    scene["bfs_plan_hash"] = wrapper["planHash"]
    scene["bfs_scene_spec_hash"] = plan["source"]["canonicalSha256"]
    scene["bfs_shot_seed"] = plan["shot"]["seed"]

    asset_collections = {}
    asset_roots = {}
    for asset in plan["assets"]:
        root_object, imported_collection = append_asset(repository_root, managed, asset, direct_import=wrapper["planVersion"] in {"0.3.0", "0.4.0", "0.4.1", "0.5.0"})
        asset_roots[asset["id"]] = root_object
        asset_collections[asset["id"]] = imported_collection

    target_objects = create_targets(managed, plan.get("targets", []), asset_collections)
    camera_objects = {camera["id"]: create_camera(managed, camera) for camera in plan["cameras"]}
    for light in plan["lights"]:
        create_light(managed, light)
    configure_world(scene, plan["world"])
    scene.camera = camera_objects[plan["shot"]["activeCamera"]]
    actor_reports = [
        apply_actor_performance(
            repository_root,
            actor,
            asset_roots[actor["assetRef"]],
            asset_collections[actor["assetRef"]],
            target_objects,
        )
        for actor in plan["actors"]
        if "actorSpec" in actor
    ]
    attachment_reports = create_attachments(scene, plan.get("attachments", []), plan["actors"], asset_roots, asset_collections)
    grasp_reports = create_grasps(scene, managed, plan.get("grasps", []), asset_roots, asset_collections)
    trajectory_reports = create_trajectories(scene, plan.get("trajectories", []), asset_collections)
    warnings = configure_render(scene, plan["render"], plan["outputSpec"], next(camera for camera in plan["cameras"] if camera["id"] == plan["shot"]["activeCamera"]), artifact_root)

    structure = build_structure(scene, wrapper, asset_collections, camera_objects, target_objects, actor_reports, attachment_reports, grasp_reports, trajectory_reports)
    structure_hash = sha256_bytes(canonical_json(structure).encode("utf-8"))
    blend_path = artifact_root / "scene.blend"
    save_result = bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False, compress=True, relative_remap=True)
    if "FINISHED" not in save_result:
        raise RuntimeError(f"Blender save failed: {sorted(save_result)}")

    manifest = {
        "documentType": "BFS_SCENE_MANIFEST",
        "manifestVersion": "0.1.0",
        "structureHash": structure_hash,
        "structure": structure,
        "warnings": warnings,
        "telemetry": {
            "compileSeconds": round(time.perf_counter() - started, 6),
            "blendBytes": blend_path.stat().st_size,
        },
    }
    manifest_path = artifact_root / "scene.manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_COMPILE_OK {plan['shot']['id']} {wrapper['planHash']} {structure_hash} {manifest_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_COMPILE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
