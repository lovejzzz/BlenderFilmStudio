#!/usr/bin/env python3
"""Render one preregistered B52-D12.14-H1 Blender 5.2 source cell."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy


SPEC_SHA256 = "7ff239d91dca6ea8708ce4cac955dd0b129ae067028a77ec1699a43a236195a8"


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--frame", type=int, choices=(0, 1), required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--output-exr", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--probe-only", action="store_true")
    return parser.parse_args(raw)


def math_node(nodes: bpy.types.Nodes, operation: str, name: str, constant: float | None = None) -> bpy.types.Node:
    node = nodes.new("ShaderNodeMath")
    node.name = name
    node.operation = operation
    if constant is not None:
        node.inputs[1].default_value = constant
    return node


def material_definition(spec: dict, owner_spec: dict) -> dict:
    variant = owner_spec["materialVariant"]
    materials = spec["sceneContract"]["materials"]
    return materials["background"] if variant == "background" else materials["variants"][variant]


def owner_material(spec: dict, owner_spec: dict) -> bpy.types.Material:
    definition = material_definition(spec, owner_spec)
    prefix = f"BFS_D1214H1_{owner_spec['analyticOwnerId']}"
    material = bpy.data.materials.new(f"{prefix}_MATERIAL")
    material.pass_index = int(owner_spec["materialPassIndex"])
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.name = f"{prefix}_OUTPUT"
    emission = nodes.new("ShaderNodeEmission")
    emission.name = f"{prefix}_EMISSION"
    emission.inputs["Strength"].default_value = spec["sceneContract"]["materials"]["emissionStrength"]
    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.name = f"{prefix}_GENERATED"
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.name = f"{prefix}_SEPARATE"
    combine = nodes.new("ShaderNodeCombineColor")
    combine.name = f"{prefix}_RGB"
    links.new(texcoord.outputs["Generated"], separate.inputs["Vector"])
    u_socket, v_socket = separate.outputs["X"], separate.outputs["Y"]
    wave_u = math_node(nodes, "MULTIPLY", f"{prefix}_WAVE_U", definition["waveFrequencyUV"][0])
    wave_v = math_node(nodes, "MULTIPLY", f"{prefix}_WAVE_V", definition["waveFrequencyUV"][1])
    links.new(u_socket, wave_u.inputs[0])
    links.new(v_socket, wave_v.inputs[0])
    wave_sum = math_node(nodes, "ADD", f"{prefix}_WAVE_SUM")
    links.new(wave_u.outputs[0], wave_sum.inputs[0])
    links.new(wave_v.outputs[0], wave_sum.inputs[1])
    wave_phase = math_node(nodes, "ADD", f"{prefix}_WAVE_PHASE", definition["wavePhase"])
    links.new(wave_sum.outputs[0], wave_phase.inputs[0])
    wave_sine = math_node(nodes, "SINE", f"{prefix}_WAVE_SINE")
    links.new(wave_phase.outputs[0], wave_sine.inputs[0])
    for channel, socket_name in enumerate(("Red", "Green", "Blue")):
        u_term = math_node(nodes, "MULTIPLY", f"{prefix}_C{channel}_U", definition["uCoefficients"][channel])
        v_term = math_node(nodes, "MULTIPLY", f"{prefix}_C{channel}_V", definition["vCoefficients"][channel])
        wave_term = math_node(nodes, "MULTIPLY", f"{prefix}_C{channel}_WAVE", definition["waveAmplitude"][channel])
        links.new(u_socket, u_term.inputs[0])
        links.new(v_socket, v_term.inputs[0])
        links.new(wave_sine.outputs[0], wave_term.inputs[0])
        linear = math_node(nodes, "ADD", f"{prefix}_C{channel}_LINEAR")
        links.new(u_term.outputs[0], linear.inputs[0])
        links.new(v_term.outputs[0], linear.inputs[1])
        with_wave = math_node(nodes, "ADD", f"{prefix}_C{channel}_WITH_WAVE")
        links.new(linear.outputs[0], with_wave.inputs[0])
        links.new(wave_term.outputs[0], with_wave.inputs[1])
        with_base = math_node(nodes, "ADD", f"{prefix}_C{channel}_BASE", definition["baseRGB"][channel])
        links.new(with_wave.outputs[0], with_base.inputs[0])
        clamp = nodes.new("ShaderNodeClamp")
        clamp.name = f"{prefix}_C{channel}_CLAMP"
        clamp.inputs["Min"].default_value = spec["sceneContract"]["materials"]["clamp"][0]
        clamp.inputs["Max"].default_value = spec["sceneContract"]["materials"]["clamp"][1]
        links.new(with_base.outputs[0], clamp.inputs["Value"])
        links.new(clamp.outputs["Result"], combine.inputs[socket_name])
    links.new(combine.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def add_surface(spec: dict, owner_spec: dict) -> bpy.types.Object:
    width, height = (float(value) for value in owner_spec["sizeWorld"])
    columns, rows = (int(value) for value in owner_spec["subdivisions"])
    vertices = []
    for row in range(rows + 1):
        y = -height / 2.0 + row * height / rows
        for column in range(columns + 1):
            x = -width / 2.0 + column * width / columns
            vertices.append((x, y, 0.0))
    faces = []
    for row in range(rows):
        for column in range(columns):
            index = row * (columns + 1) + column
            faces.append((index, index + 1, index + columns + 2, index + columns + 1))
    prefix = f"BFS_D1214H1_{owner_spec['analyticOwnerId']}"
    mesh = bpy.data.meshes.new(f"{prefix}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    owner = bpy.data.objects.new(prefix, mesh)
    owner.rotation_mode = spec["sceneContract"]["eulerOrder"]
    owner.pass_index = int(owner_spec["objectPassIndex"])
    mesh.materials.append(owner_material(spec, owner_spec))
    bpy.context.scene.collection.objects.link(owner)
    return owner


def key_transform(owner: bpy.types.Object, transforms: dict) -> None:
    for frame_text, row in transforms.items():
        owner.location = tuple(row["location"])
        owner.rotation_euler = tuple(row["rotationEuler"])
        owner.keyframe_insert(data_path="location", frame=int(frame_text))
        owner.keyframe_insert(data_path="rotation_euler", frame=int(frame_text))
    action = owner.animation_data.action if owner.animation_data else None
    if action is None:
        raise RuntimeError(f"missing D12.14-H1 action: {owner.name}")
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"


def action_rows(owner: bpy.types.Object) -> list[dict]:
    action = owner.animation_data.action if owner.animation_data else None
    rows = []
    if action:
        for layer_index, layer in enumerate(action.layers):
            for strip_index, strip in enumerate(layer.strips):
                for bag_index, bag in enumerate(strip.channelbags):
                    for curve in bag.fcurves:
                        rows.append({
                            "layerIndex": layer_index,
                            "stripIndex": strip_index,
                            "channelBagIndex": bag_index,
                            "dataPath": curve.data_path,
                            "arrayIndex": curve.array_index,
                            "keyframes": [[float(point.co.x), float(point.co.y), point.interpolation] for point in curve.keyframe_points],
                        })
    return sorted(rows, key=lambda row: (row["dataPath"], row["arrayIndex"]))


def effective_fixture(spec: dict, fixture: dict) -> dict:
    camera = spec["sceneContract"]["camera"]
    result = {
        **fixture,
        "cameraByFrame": {
            frame: {"location": camera["locationByFrame"][frame], "rotationEuler": camera["rotationEulerByFrame"][frame]}
            for frame in ("0", "1", "2")
        },
    }
    owners = []
    for row in fixture["owners"]:
        owner = dict(row)
        if owner["role"] == "background":
            background = spec["sceneContract"]["background"]
            owner.update({
                "sizeWorld": background["sizeWorld"],
                "subdivisions": background["subdivisions"],
                "transformByFrame": background["transformByFrame"],
            })
        else:
            owner["sizeWorld"] = spec["sceneContract"]["foreground"]["sizeWorld"]
        owners.append(owner)
    result["owners"] = owners
    return result


def setup(spec: dict, fixture: dict, frame: int, repeat: int):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"BFS_D1214H1_{fixture['id']}_F{frame}_R{repeat}"
    render = spec["sceneContract"]["render"]
    scene.render.engine = render["engine"]
    scene.cycles.device = render["device"]
    scene.cycles.samples = render["samples"]
    scene.cycles.seed = render["seed"]
    scene.cycles.use_animated_seed = render["animatedSeed"]
    scene.cycles.use_adaptive_sampling = render["adaptiveSampling"]
    scene.cycles.use_denoising = render["denoising"]
    scene.render.resolution_x, scene.render.resolution_y = fixture["resolution"]
    scene.render.resolution_percentage = render["resolutionPercentage"]
    scene.render.pixel_aspect_x, scene.render.pixel_aspect_y = render["pixelAspect"]
    scene.render.film_transparent = render["filmTransparent"]
    scene.render.use_motion_blur = render["motionBlur"]
    scene.render.use_persistent_data = render["persistentData"]
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    scene.render.threads_mode = render["threadsMode"]
    scene.render.threads = render["threads"]
    scene.frame_start, scene.frame_end = spec["sceneContract"]["frameRange"]
    world = bpy.data.worlds.new("BFS_D1214H1_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.world = world
    camera_spec = spec["sceneContract"]["camera"]
    camera_data = bpy.data.cameras.new("BFS_D1214H1_CAMERA_DATA")
    camera_data.type = camera_spec["type"]
    camera_data.lens = camera_spec["lensMm"]
    camera_data.sensor_width = camera_spec["sensorWidthMm"]
    camera_data.sensor_fit = camera_spec["sensorFit"]
    camera_data.clip_start = camera_spec["clipStart"]
    camera_data.clip_end = camera_spec["clipEnd"]
    camera_data.dof.use_dof = camera_spec["depthOfField"]
    camera = bpy.data.objects.new("BFS_D1214H1_CAMERA", camera_data)
    camera.rotation_mode = spec["sceneContract"]["eulerOrder"]
    scene.collection.objects.link(camera)
    scene.camera = camera
    key_transform(camera, fixture["cameraByFrame"])
    owners = []
    for owner_spec in fixture["owners"]:
        owner = add_surface(spec, owner_spec)
        key_transform(owner, owner_spec["transformByFrame"])
        owners.append(owner)
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    layer = bpy.context.view_layer
    layer.name = render["viewLayer"]
    layer.use_pass_combined = True
    layer.use_pass_z = True
    layer.use_pass_vector = True
    layer.use_pass_object_index = True
    layer.use_pass_material_index = True
    layer.pass_alpha_threshold = render["passAlphaThreshold"]
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = render["fileFormat"]
    scene.render.image_settings.color_mode = render["colorMode"]
    scene.render.image_settings.color_depth = render["colorDepth"]
    scene.render.image_settings.exr_codec = render["exrCodec"]
    return scene, camera, owners


def owner_structure(owner: bpy.types.Object, owner_spec: dict) -> dict:
    material = owner.data.materials[0]
    local_vertices = [[float(value) for value in vertex.co] for vertex in owner.data.vertices]
    return {
        "analyticOwnerId": owner_spec["analyticOwnerId"],
        "role": owner_spec["role"],
        "name": owner.name,
        "meshDataName": owner.data.name,
        "localVertexSha256": canonical_hash(local_vertices),
        "objectPassIndex": int(owner.pass_index),
        "materialPassIndex": int(material.pass_index),
        "vertices": len(owner.data.vertices),
        "polygons": len(owner.data.polygons),
        "location": [float(value) for value in owner.location],
        "rotationEuler": [float(value) for value in owner.rotation_euler],
        "scale": [float(value) for value in owner.scale],
        "material": material.name,
        "materialNodes": sorted(node.name for node in material.node_tree.nodes),
    }


def main() -> None:
    cli = arguments()
    if sha_file(cli.spec) != SPEC_SHA256:
        raise RuntimeError("D12.14-H1 spec identity mismatch")
    spec = json.loads(cli.spec.read_text())
    fixture = next((row for row in spec["fixtures"] if row["id"] == cli.fixture), None)
    if fixture is None or cli.report.exists() or (cli.output_exr and cli.output_exr.exists()):
        raise RuntimeError("D12.14-H1 fixture or output invalid")
    if not cli.probe_only and cli.output_exr is None:
        raise RuntimeError("D12.14-H1 output EXR required")
    runtime = spec["runtime"]
    if sha_file(Path(bpy.app.binary_path)) != runtime["blender"]["sha256"]:
        raise RuntimeError("D12.14-H1 Blender executable identity mismatch")
    if bpy.app.version_string != runtime["blender"]["version"] or bpy.app.build_hash.decode() != runtime["blender"]["buildHash"]:
        raise RuntimeError("D12.14-H1 Blender version identity mismatch")
    if sha_file(Path(os.environ["OCIO"])) != runtime["ocio"]["sha256"]:
        raise RuntimeError("D12.14-H1 OCIO identity mismatch")
    fixture = effective_fixture(spec, fixture)
    started = time.monotonic()
    scene, camera, owners = setup(spec, fixture, cli.frame, cli.repeat)
    layer = bpy.context.view_layer
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalRenderHoldoutSourceReport.v0.1",
        "experimentId": spec["experimentId"],
        "specSha256": SPEC_SHA256,
        "fixtureId": fixture["id"],
        "frame": cli.frame,
        "repeat": cli.repeat,
        "pid": os.getpid(),
        "probeOnly": cli.probe_only,
        "fixture": fixture,
        "runtime": {
            "blender": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode(),
            "executableSha256": sha_file(Path(bpy.app.binary_path)),
            "engine": scene.render.engine,
            "device": scene.cycles.device,
            "samples": scene.cycles.samples,
            "seed": scene.cycles.seed,
        },
        "sceneStructure": {
            "camera": {
                "name": camera.name,
                "type": camera.data.type,
                "lensMm": float(camera.data.lens),
                "sensorWidthMm": float(camera.data.sensor_width),
                "location": [float(value) for value in camera.location],
                "rotationEuler": [float(value) for value in camera.rotation_euler],
            },
            "owners": [owner_structure(owner, owner_spec) for owner, owner_spec in zip(owners, fixture["owners"])],
        },
        "animation": {"camera": action_rows(camera), "owners": {owner.name: action_rows(owner) for owner in owners}},
        "passState": {
            "viewLayer": layer.name,
            "Combined": layer.use_pass_combined,
            "Depth": layer.use_pass_z,
            "Vector": layer.use_pass_vector,
            "Object Index": layer.use_pass_object_index,
            "Material Index": layer.use_pass_material_index,
            "passAlphaThreshold": layer.pass_alpha_threshold,
        },
    }
    render_seconds = 0.0
    if not cli.probe_only:
        cli.output_exr.parent.mkdir(parents=True, exist_ok=True)
        render_started = time.monotonic()
        outcome = bpy.ops.render.render(write_still=False)
        if "FINISHED" not in outcome:
            raise RuntimeError(f"D12.14-H1 source render failed: {sorted(outcome)}")
        render_seconds = time.monotonic() - render_started
        bpy.data.images["Render Result"].save_render(str(cli.output_exr), scene=scene)
        body["output"] = {"uri": str(cli.output_exr), "sha256": sha_file(cli.output_exr), "bytes": cli.output_exr.stat().st_size}
    else:
        body["output"] = None
    body["operationCounts"] = {
        "blenderProcesses": 1,
        "blenderRenderCalls": 0 if cli.probe_only else 1,
        "cyclesRayRenders": 0 if cli.probe_only else 1,
        "modelCalls": 0,
        "networkCalls": 0,
    }
    body["renderSeconds"] = round(render_seconds, 6)
    body["elapsedSeconds"] = round(time.monotonic() - started, 6)
    report = {**body, "reportHash": canonical_hash(body)}
    cli.report.parent.mkdir(parents=True, exist_ok=True)
    cli.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1214H1_SOURCE_OK fixture={fixture['id']} frame={cli.frame} repeat={cli.repeat} probe={cli.probe_only}")


if __name__ == "__main__":
    main()
