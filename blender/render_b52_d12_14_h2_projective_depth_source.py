#!/usr/bin/env python3
"""Render one preregistered B52-D12.14-H2 Blender 5.2 source cell."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import bpy


SPEC_SHA256 = "2961f621b38f934cffaa7abe36deaaa5e01e7505d6361985039d0380578d244b"
CORRECTION_SHA256 = "9b6fdcedd571ad1ec7fb8d02bc7c6a630014d204de02f4a8b74bf5509c625a92"


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--correction", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--frame", type=int, choices=(0, 1), required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--output-exr", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--probe-only", action="store_true")
    return parser.parse_args(raw)


def math_node(nodes, operation: str, name: str, constant: float | None = None):
    node = nodes.new("ShaderNodeMath")
    node.name = name
    node.operation = operation
    if constant is not None:
        node.inputs[1].default_value = constant
    return node


def make_material(spec: dict, owner: dict):
    materials = spec["sceneContract"]["materials"]
    definition = materials[owner["role"]]
    prefix = f"BFS_D1214H2_{owner['analyticOwnerId']}"
    material = bpy.data.materials.new(f"{prefix}_MATERIAL")
    material.pass_index = int(owner["materialPassIndex"])
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = float(materials["emissionStrength"])
    texcoord = nodes.new("ShaderNodeTexCoord")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    combine = nodes.new("ShaderNodeCombineColor")
    links.new(texcoord.outputs["Generated"], separate.inputs["Vector"])
    u_socket, v_socket = separate.outputs["X"], separate.outputs["Y"]
    wave_u = math_node(nodes, "MULTIPLY", f"{prefix}_WU", definition["waveFrequencyUV"][0])
    wave_v = math_node(nodes, "MULTIPLY", f"{prefix}_WV", definition["waveFrequencyUV"][1])
    links.new(u_socket, wave_u.inputs[0])
    links.new(v_socket, wave_v.inputs[0])
    wave_sum = math_node(nodes, "ADD", f"{prefix}_WS")
    links.new(wave_u.outputs[0], wave_sum.inputs[0])
    links.new(wave_v.outputs[0], wave_sum.inputs[1])
    wave_phase = math_node(nodes, "ADD", f"{prefix}_WP", definition["wavePhase"])
    links.new(wave_sum.outputs[0], wave_phase.inputs[0])
    wave_sine = math_node(nodes, "SINE", f"{prefix}_SIN")
    links.new(wave_phase.outputs[0], wave_sine.inputs[0])
    for channel, socket_name in enumerate(("Red", "Green", "Blue")):
        u_term = math_node(nodes, "MULTIPLY", f"{prefix}_C{channel}U", definition["uCoefficients"][channel])
        v_term = math_node(nodes, "MULTIPLY", f"{prefix}_C{channel}V", definition["vCoefficients"][channel])
        w_term = math_node(nodes, "MULTIPLY", f"{prefix}_C{channel}W", definition["waveAmplitude"][channel])
        links.new(u_socket, u_term.inputs[0])
        links.new(v_socket, v_term.inputs[0])
        links.new(wave_sine.outputs[0], w_term.inputs[0])
        uv = math_node(nodes, "ADD", f"{prefix}_C{channel}UV")
        links.new(u_term.outputs[0], uv.inputs[0])
        links.new(v_term.outputs[0], uv.inputs[1])
        uvw = math_node(nodes, "ADD", f"{prefix}_C{channel}UVW")
        links.new(uv.outputs[0], uvw.inputs[0])
        links.new(w_term.outputs[0], uvw.inputs[1])
        base = math_node(nodes, "ADD", f"{prefix}_C{channel}BASE", definition["baseRGB"][channel])
        links.new(uvw.outputs[0], base.inputs[0])
        clamp = nodes.new("ShaderNodeClamp")
        clamp.inputs["Min"].default_value = materials["clamp"][0]
        clamp.inputs["Max"].default_value = materials["clamp"][1]
        links.new(base.outputs[0], clamp.inputs["Value"])
        links.new(clamp.outputs["Result"], combine.inputs[socket_name])
    links.new(combine.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def make_plane(spec: dict, owner: dict):
    surface = spec["sceneContract"][owner["role"]]
    width, height = (float(value) for value in surface["sizeWorld"])
    columns, rows = (int(value) for value in surface["subdivisions"])
    vertices = [
        (-width / 2.0 + column * width / columns, -height / 2.0 + row * height / rows, 0.0)
        for row in range(rows + 1)
        for column in range(columns + 1)
    ]
    faces = []
    for row in range(rows):
        for column in range(columns):
            index = row * (columns + 1) + column
            faces.append((index, index + 1, index + columns + 2, index + columns + 1))
    prefix = f"BFS_D1214H2_{owner['analyticOwnerId']}"
    mesh = bpy.data.meshes.new(f"{prefix}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(prefix, mesh)
    obj.rotation_mode = spec["sceneContract"]["eulerOrder"]
    obj.pass_index = int(owner["objectPassIndex"])
    mesh.materials.append(make_material(spec, owner))
    bpy.context.scene.collection.objects.link(obj)
    return obj


def key_transform(obj, transforms: dict) -> None:
    for frame_text, row in transforms.items():
        obj.location = tuple(row["location"])
        obj.rotation_euler = tuple(row["rotationEuler"])
        obj.scale = (1.0, 1.0, 1.0)
        frame = int(frame_text)
        obj.keyframe_insert(data_path="location", frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        obj.keyframe_insert(data_path="scale", frame=frame)
    action = obj.animation_data.action if obj.animation_data else None
    if action is None:
        raise RuntimeError(f"H2 missing action: {obj.name}")
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"


def action_rows(obj) -> list[dict]:
    action = obj.animation_data.action if obj.animation_data else None
    rows = []
    if action:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        rows.append({
                            "dataPath": curve.data_path,
                            "arrayIndex": curve.array_index,
                            "keyframes": [[float(p.co.x), float(p.co.y), p.interpolation] for p in curve.keyframe_points],
                        })
    return sorted(rows, key=lambda row: (row["dataPath"], row["arrayIndex"]))


def mesh_record(obj, owner: dict) -> dict:
    vertices = [[float(value) for value in vertex.co] for vertex in obj.data.vertices]
    return {
        "analyticOwnerId": owner["analyticOwnerId"],
        "role": owner["role"],
        "objectName": obj.name,
        "meshDataName": obj.data.name,
        "localVertexSha256": canonical_hash(vertices),
        "vertexCount": len(obj.data.vertices),
        "polygonCount": len(obj.data.polygons),
        "scale": [float(value) for value in obj.scale],
        "objectPassIndex": int(obj.pass_index),
        "materialPassIndex": int(obj.data.materials[0].pass_index),
    }


def setup(spec: dict, frame: int, repeat: int):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"BFS_D1214H2_F{frame}_R{repeat}"
    contract = spec["sceneContract"]
    render = contract["render"]
    scene.render.engine = render["engine"]
    scene.cycles.device = render["device"]
    scene.cycles.samples = render["samples"]
    scene.cycles.seed = render["seed"]
    scene.cycles.use_animated_seed = render["animatedSeed"]
    scene.cycles.use_adaptive_sampling = render["adaptiveSampling"]
    scene.cycles.use_denoising = render["denoising"]
    scene.render.resolution_x, scene.render.resolution_y = render["resolution"]
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
    scene.frame_start, scene.frame_end = contract["frameRange"]
    world = bpy.data.worlds.new("BFS_D1214H2_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.world = world
    camera_spec = contract["camera"]
    camera_data = bpy.data.cameras.new("BFS_D1214H2_CAMERA_DATA")
    camera_data.type = camera_spec["type"]
    camera_data.lens = camera_spec["lensMm"]
    camera_data.sensor_width = camera_spec["sensorWidthMm"]
    camera_data.sensor_fit = camera_spec["sensorFit"]
    camera_data.clip_start = camera_spec["clipStart"]
    camera_data.clip_end = camera_spec["clipEnd"]
    camera_data.dof.use_dof = camera_spec["depthOfField"]
    camera = bpy.data.objects.new("BFS_D1214H2_CAMERA", camera_data)
    camera.rotation_mode = contract["eulerOrder"]
    scene.collection.objects.link(camera)
    scene.camera = camera
    key_transform(camera, {
        key: {"location": camera_spec["locationByFrame"][key], "rotationEuler": camera_spec["rotationEulerByFrame"][key]}
        for key in ("0", "1", "2")
    })
    owners = spec["fixture"]["owners"]
    objects = []
    for owner in owners:
        obj = make_plane(spec, owner)
        key_transform(obj, contract[owner["role"]]["transformByFrame"])
        objects.append(obj)
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    layer = bpy.context.view_layer
    layer.name = render["viewLayer"]
    layer.use_pass_combined = True
    layer.use_pass_z = True
    layer.use_pass_position = True
    layer.use_pass_vector = True
    layer.use_pass_object_index = True
    layer.use_pass_material_index = True
    layer.pass_alpha_threshold = render["passAlphaThreshold"]
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = render["fileFormat"]
    scene.render.image_settings.color_mode = render["colorMode"]
    scene.render.image_settings.color_depth = render["colorDepth"]
    scene.render.image_settings.exr_codec = render["exrCodec"]
    return scene, camera, objects, owners, layer


def main() -> None:
    cli = arguments()
    root = Path(__file__).resolve().parents[1]
    if sha_file(cli.spec) != SPEC_SHA256 or sha_file(cli.correction) != CORRECTION_SHA256 or cli.report.exists():
        raise RuntimeError("H2 spec/correction identity or report freshness failure")
    spec = json.loads(cli.spec.read_text())
    correction = json.loads(cli.correction.read_text())
    if spec.get("experimentId") != "B52-D12.14-H2" or correction.get("experimentId") != spec["experimentId"]:
        raise RuntimeError("H2 experiment identity mismatch")
    if cli.fixture != spec["fixture"]["id"]:
        raise RuntimeError("H2 fixture identity mismatch")
    if not cli.probe_only and (cli.output_exr is None or cli.output_exr.exists()):
        raise RuntimeError("H2 formal EXR path missing or not fresh")
    runtime = spec["runtime"]
    if sha_file(Path(bpy.app.binary_path)) != runtime["blender"]["sha256"]:
        raise RuntimeError("H2 Blender executable identity mismatch")
    if bpy.app.version_string != runtime["blender"]["version"] or bpy.app.build_hash.decode() != runtime["blender"]["buildHash"]:
        raise RuntimeError("H2 Blender version mismatch")
    if sha_file(Path(os.environ["OCIO"])) != runtime["ocio"]["sha256"]:
        raise RuntimeError("H2 OCIO identity mismatch")
    started = time.monotonic()
    scene, camera, objects, owners, layer = setup(spec, cli.frame, cli.repeat)
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthSource.v0.1",
        "experimentId": spec["experimentId"],
        "specSha256": SPEC_SHA256,
        "correctionSha256": CORRECTION_SHA256,
        "fixtureId": cli.fixture,
        "frame": cli.frame,
        "repeat": cli.repeat,
        "probeOnly": bool(cli.probe_only),
        "pid": os.getpid(),
        "runtime": {"blender": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode(), "executableSha256": sha_file(Path(bpy.app.binary_path))},
        "renderState": {"engine": scene.render.engine, "device": scene.cycles.device, "samples": scene.cycles.samples, "seed": scene.cycles.seed, "resolution": [scene.render.resolution_x, scene.render.resolution_y], "threads": scene.render.threads},
        "sceneStructure": {
            "scene": scene.name,
            "camera": {"name": camera.name, "type": camera.data.type, "lensMm": float(camera.data.lens), "sensorWidthMm": float(camera.data.sensor_width)},
            "owners": [mesh_record(obj, owner) for obj, owner in zip(objects, owners)],
        },
        "animation": {"camera": action_rows(camera), "owners": {obj.name: action_rows(obj) for obj in objects}},
        "passState": {"viewLayer": layer.name, "Combined": layer.use_pass_combined, "Depth": layer.use_pass_z, "Position": layer.use_pass_position, "Vector": layer.use_pass_vector, "Object Index": layer.use_pass_object_index, "Material Index": layer.use_pass_material_index, "passAlphaThreshold": layer.pass_alpha_threshold},
    }
    if cli.probe_only:
        body["output"] = None
        body["operationCounts"] = {"blenderProcesses": 1, "blenderRenderCalls": 0, "cyclesRayRenders": 0, "exrFiles": 0, "modelCalls": 0, "networkCalls": 0}
    else:
        cli.output_exr.parent.mkdir(parents=True, exist_ok=True)
        render_started = time.monotonic()
        outcome = bpy.ops.render.render(write_still=False)
        if "FINISHED" not in outcome:
            raise RuntimeError("H2 Blender render failed")
        bpy.data.images["Render Result"].save_render(str(cli.output_exr), scene=scene)
        body["output"] = {"uri": str(cli.output_exr.relative_to(root)), "sha256": sha_file(cli.output_exr), "bytes": cli.output_exr.stat().st_size}
        body["renderSeconds"] = round(time.monotonic() - render_started, 6)
        body["operationCounts"] = {"blenderProcesses": 1, "blenderRenderCalls": 1, "cyclesRayRenders": 1, "exrFiles": 1, "modelCalls": 0, "networkCalls": 0}
    body["elapsedSeconds"] = round(time.monotonic() - started, 6)
    report = {**body, "reportHash": canonical_hash(body)}
    cli.report.parent.mkdir(parents=True, exist_ok=True)
    cli.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_D1214H2_SOURCE_OK probe={cli.probe_only} frame={cli.frame} repeat={cli.repeat}")


if __name__ == "__main__":
    main()
