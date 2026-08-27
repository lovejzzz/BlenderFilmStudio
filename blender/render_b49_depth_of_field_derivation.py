"""Build and render one preregistered B49-DOF-D1 fixture cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path

import bpy
import PyOpenColorIO as ocio


PREREGISTRATION_COMMIT = "9eef748598a8ec1dfd320eac846eb03a492d9831"
SPEC_SHA256 = "27039abd12cc29a604450708552322442373845e50d5471e068af0c71724f76c"
SPEC_URI = Path("/repo/specs/codex-worker-depth-of-field-derivation.v0.1.json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def emission_material(name: str, value: float):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (value, value, value, 1.0)
    emission.inputs["Strength"].default_value = 1.0
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def make_target(target: dict, sensor_width: float, lens: float, aspect: float, materials: tuple):
    depth = float(target["depthM"])
    center_x, center_y = target["viewportCenter01"]
    size_x, size_y = target["viewportSize01"]
    frame_width = depth * sensor_width / lens
    frame_height = frame_width / aspect
    world_width = frame_width * size_x
    world_height = frame_height * size_y
    world_x = (center_x - 0.5) * frame_width
    world_y = (center_y - 0.5) * frame_height
    bands = 24
    vertices = []
    faces = []
    for index in range(bands):
        left = -world_width / 2 + world_width * index / bands
        right = -world_width / 2 + world_width * (index + 1) / bands
        offset = len(vertices)
        vertices.extend([(left, -world_height / 2, 0), (right, -world_height / 2, 0), (right, world_height / 2, 0), (left, world_height / 2, 0)])
        faces.append((offset, offset + 1, offset + 2, offset + 3))
    mesh = bpy.data.meshes.new(f"TARGET_{target['id']}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(materials[0])
    mesh.materials.append(materials[1])
    for index, polygon in enumerate(mesh.polygons):
        polygon.material_index = index % 2
    obj = bpy.data.objects.new(f"TARGET_{target['id']}", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (world_x, world_y, -depth)
    obj["bfs_depth_m"] = depth
    obj["bfs_viewport_center_01"] = list(target["viewportCenter01"])
    obj["bfs_viewport_size_01"] = list(target["viewportSize01"])
    return obj


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell-id", required=True)
    parser.add_argument("--ocio-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if sha256_file(SPEC_URI) != SPEC_SHA256:
        raise RuntimeError("spec SHA mismatch")
    spec = json.loads(SPEC_URI.read_text())
    cell = next((item for item in spec["cells"] if item["id"] == args.cell_id), None)
    if cell is None:
        raise RuntimeError("unregistered cell")
    if tuple(bpy.app.version[:3]) != (5, 2, 0):
        raise RuntimeError(f"Blender 5.2 required: {bpy.app.version_string}")
    ocio_path = Path(os.environ["OCIO"])
    if sha256_file(ocio_path) != args.ocio_sha256:
        raise RuntimeError("OCIO SHA mismatch")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("output directory must be empty")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in tuple(bpy.data.materials):
        bpy.data.materials.remove(block)
    scene = bpy.context.scene
    layer = bpy.context.view_layer
    layer.name = "BFS_MASTER"
    render = spec["render"]
    width, height = render["resolution"]
    aspect = width / height
    camera_spec = spec["fixture"]["camera"]
    camera_data = bpy.data.cameras.new("CAM_DOF_FIXTURE")
    camera = bpy.data.objects.new("CAM_DOF_FIXTURE", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = tuple(camera_spec["locationM"])
    camera.rotation_euler = (0, 0, 0)
    camera_data.type = "PERSP"
    camera_data.lens = camera_spec["lensMm"]
    camera_data.sensor_width = camera_spec["sensorWidthMm"]
    camera_data.clip_start = 0.1
    camera_data.clip_end = 1000

    focus = bpy.data.objects.new(spec["fixture"]["focusObject"]["id"], None)
    scene.collection.objects.link(focus)
    focus.location = tuple(spec["fixture"]["focusObject"]["locationM"])
    low = emission_material("EMISSION_LOW", spec["fixture"]["targetShader"]["low"])
    high = emission_material("EMISSION_HIGH", spec["fixture"]["targetShader"]["high"])
    targets = [make_target(target, camera_data.sensor_width / 1000, camera_data.lens / 1000, aspect, (low, high)) for target in spec["fixture"]["targets"]]

    camera_data.dof.use_dof = cell["useDof"]
    camera_data.dof.focus_distance = cell["focusDistanceM"]
    camera_data.dof.focus_object = focus if cell["focusMode"] == "OBJECT" else None
    camera_data.dof.aperture_fstop = cell["apertureFStop"]
    camera_data.dof.aperture_blades = camera_spec["apertureBlades"]
    camera_data.dof.aperture_ratio = camera_spec["apertureRatio"]

    scene.render.engine = render["engine"]
    scene.cycles.device = render["device"]
    scene.cycles.samples = render["samples"]
    scene.cycles.seed = render["seedOffset"]
    scene.cycles.use_animated_seed = False
    scene.cycles.use_denoising = render["denoising"]
    if hasattr(layer.cycles, "use_denoising"):
        layer.cycles.use_denoising = render["denoising"]
    scene.render.use_motion_blur = render["motionBlur"]
    scene.render.use_persistent_data = render["persistentData"]
    scene.render.threads_mode = "FIXED"
    scene.render.threads = render["threads"]
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    scene.world.color = tuple(spec["fixture"]["worldColor"])
    if scene.world.use_nodes:
        background = scene.world.node_tree.nodes.get("Background")
        background.inputs["Color"].default_value = (*spec["fixture"]["worldColor"], 1.0)
        background.inputs["Strength"].default_value = 0.0
    layer.use_pass_combined = True
    layer.use_pass_z = True
    layer.use_pass_normal = True
    layer.use_pass_position = False
    layer.use_pass_vector = True
    layer.use_pass_cryptomatte_object = True
    layer.use_pass_cryptomatte_material = False
    layer.use_pass_cryptomatte_asset = False
    layer.pass_cryptomatte_depth = 6
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"

    render_started = time.perf_counter()
    rendered = bpy.ops.render.render(write_still=False)
    render_seconds = time.perf_counter() - render_started
    if "FINISHED" not in rendered:
        raise RuntimeError(f"render failed: {sorted(rendered)}")
    result = bpy.data.images.get("Render Result")
    if result is None:
        raise RuntimeError("Render Result absent")
    exr = output / "production.exr"
    save_started = time.perf_counter()
    result.save_render(str(exr), scene=scene)
    save_seconds = time.perf_counter() - save_started
    if not exr.exists():
        raise RuntimeError("production EXR absent")
    report = {
        "schemaVersion": "bfs.depthOfFieldDerivationCellReport.v0.1",
        "preregistrationCommit": PREREGISTRATION_COMMIT,
        "experimentId": spec["experimentId"],
        "cellId": cell["id"],
        "role": cell["role"],
        "fixture": {
            "camera": {"name": camera.name, "type": camera_data.type, "locationM": list(camera.location), "rotationEulerRad": list(camera.rotation_euler), "lensMm": camera_data.lens, "sensorWidthMm": camera_data.sensor_width},
            "targets": [{"id": target.name.removeprefix("TARGET_"), "depthM": target["bfs_depth_m"], "viewportCenter01": list(target["bfs_viewport_center_01"]), "viewportSize01": list(target["bfs_viewport_size_01"])} for target in targets],
            "focusObjectLocationM": list(focus.location)
        },
        "settings": {"engine": scene.render.engine, "device": scene.cycles.device, "resolution": [width, height, 100], "samples": scene.cycles.samples, "seed": scene.cycles.seed, "animatedSeed": scene.cycles.use_animated_seed, "denoising": scene.cycles.use_denoising, "motionBlur": scene.render.use_motion_blur, "persistentData": scene.render.use_persistent_data, "threadsMode": scene.render.threads_mode, "threads": scene.render.threads, "useDof": camera_data.dof.use_dof, "focusMode": cell["focusMode"], "focusDistanceM": camera_data.dof.focus_distance, "focusObject": camera_data.dof.focus_object.name if camera_data.dof.focus_object else None, "focusObjectDistanceM": (camera.location - focus.location).length if camera_data.dof.focus_object else None, "apertureFStop": camera_data.dof.aperture_fstop, "apertureBlades": camera_data.dof.aperture_blades, "apertureRatio": camera_data.dof.aperture_ratio},
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash), "buildPlatform": bpy.app.build_platform.decode() if isinstance(bpy.app.build_platform, bytes) else str(bpy.app.build_platform)},
        "ocio": {"name": ocio.GetCurrentConfig().getName(), "sha256": sha256_file(ocio_path)},
        "renderSeconds": round(render_seconds, 6),
        "saveSeconds": round(save_seconds, 6),
        "peakSelfRssKiB": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "artifact": {"uri": exr.name, "sha256": sha256_file(exr), "bytes": exr.stat().st_size},
        "passed": True
    }
    (output / "render.report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B49_DOF_CELL_OK id={cell['id']} renderSeconds={report['renderSeconds']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B49_DOF_CELL_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
