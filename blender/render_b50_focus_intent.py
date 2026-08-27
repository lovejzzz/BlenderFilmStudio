"""Render one preregistered B50 focus-intent condition in Blender 5.2."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import time
from pathlib import Path

import bpy
import PyOpenColorIO as ocio
from mathutils import Vector


PREREGISTRATION_COMMIT = "04365d44c16c9be65582184d9ff4d697e5d6e2f6"
SPEC_SHA256 = "244d6cc3839bd2923fd85e5069d44d30938bc4b2e8c0a805505c63e2cb789f20"
SPEC_URI = Path("/repo/specs/focus-intent-human-review-spec.v0.1.json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def close(left, right, tolerance=1e-6):
    return abs(float(left) - float(right)) <= tolerance


def camera_depth(camera, point):
    return -float((camera.matrix_world.inverted() @ point).z)


def focus_geometry(scene, camera):
    chair = scene.objects.get("PROP_CHAIR")
    if chair is None or chair.type != "EMPTY":
        raise RuntimeError("semantic chair object absent or wrong type")
    rows = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for instance in depsgraph.object_instances:
        obj = instance.object
        if obj is None or obj.type != "MESH" or obj.name not in {"CHAIR_SEAT", "CHAIR_BACK"}:
            continue
        world = instance.matrix_world.copy()
        depths = [camera_depth(camera, world @ Vector(corner)) for corner in obj.bound_box]
        center = sum((Vector(corner) for corner in obj.bound_box), Vector()) / 8
        rows[obj.name] = {
            "centerCameraDepthM": camera_depth(camera, world @ center),
            "cameraDepthRangeM": [min(depths), max(depths)],
        }
    if set(rows) != {"CHAIR_SEAT", "CHAIR_BACK"}:
        raise RuntimeError(f"chair evaluated components mismatch: {sorted(rows)}")
    return {
        "chairObject": chair.name,
        "chairObjectOriginCameraDepthM": camera_depth(camera, chair.matrix_world.translation),
        "components": rows,
    }


def control_projection(scene, layer, camera):
    return {
        "bindings": {
            "planHash": scene.get("bfs_plan_hash"),
            "sceneSpecHash": scene.get("bfs_scene_spec_hash"),
            "structureHash": scene.get("bfs_structure_hash"),
            "ocioConfigSha256": scene.get("bfs_ocio_sha256"),
        },
        "camera": {
            "name": camera.name,
            "type": camera.data.type,
            "lensMm": float(camera.data.lens),
            "useDof": bool(camera.data.dof.use_dof),
            "focusDistanceM": float(camera.data.dof.focus_distance),
            "focusObject": camera.data.dof.focus_object.name if camera.data.dof.focus_object else None,
            "apertureFStop": float(camera.data.dof.aperture_fstop),
        },
        "render": {
            "engine": scene.render.engine,
            "device": scene.cycles.device,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
            "samples": scene.cycles.samples,
            "seed": scene.cycles.seed,
            "animatedSeed": scene.cycles.use_animated_seed,
            "denoising": scene.cycles.use_denoising,
            "motionBlur": scene.render.use_motion_blur,
            "motionBlurShutter": scene.render.motion_blur_shutter,
            "motionBlurPosition": scene.render.motion_blur_position,
            "persistentData": scene.render.use_persistent_data,
            "threadsMode": scene.render.threads_mode,
            "threads": scene.render.threads,
        },
        "passes": {
            "combined": layer.use_pass_combined,
            "depth": layer.use_pass_z,
            "normal": layer.use_pass_normal,
            "vector": layer.use_pass_vector,
            "cryptomatteObject": layer.use_pass_cryptomatte_object,
            "cryptomatteDepth": layer.pass_cryptomatte_depth,
        },
        "frame": scene.frame_current,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if sha256_file(SPEC_URI) != SPEC_SHA256:
        raise RuntimeError("spec SHA mismatch")
    spec = json.loads(SPEC_URI.read_text())
    cell = next((item for item in spec["renderDesign"]["cells"] if item["id"] == args.cell_id), None)
    if cell is None:
        raise RuntimeError("unregistered cell")
    source = Path(bpy.data.filepath).resolve()
    if sha256_file(source) != spec["source"]["blendSha256"]:
        raise RuntimeError("source blend SHA mismatch")
    if tuple(bpy.app.version[:3]) != (5, 2, 0):
        raise RuntimeError(f"Blender 5.2 required: {bpy.app.version_string}")
    scene, layer, camera = bpy.context.scene, bpy.context.view_layer, bpy.context.scene.camera
    if camera is None or camera.name != spec["source"]["camera"]:
        raise RuntimeError("active camera mismatch")
    expected_bindings = {
        "planHash": spec["source"]["planHash"],
        "sceneSpecHash": scene.get("bfs_scene_spec_hash"),
        "structureHash": scene.get("bfs_structure_hash"),
        "ocioConfigSha256": spec["runtime"]["ocioSha256"],
    }
    observed_bindings = {
        "planHash": scene.get("bfs_plan_hash"),
        "sceneSpecHash": scene.get("bfs_scene_spec_hash"),
        "structureHash": scene.get("bfs_structure_hash"),
        "ocioConfigSha256": scene.get("bfs_ocio_sha256"),
    }
    if observed_bindings != expected_bindings:
        raise RuntimeError(f"binding mismatch: {observed_bindings}")
    if ocio.GetCurrentConfig().getName() != scene.get("bfs_ocio_config"):
        raise RuntimeError("OCIO config mismatch")
    design = spec["renderDesign"]
    if camera.data.type != "PERSP" or not close(camera.data.lens, design["lensMm"]) or not close(camera.data.dof.aperture_fstop, design["apertureFStop"]) or not close(camera.data.dof.focus_distance, spec["focusDerivation"]["originalFocusDistanceM"]) or camera.data.dof.focus_object is not None:
        raise RuntimeError("source camera binding mismatch")
    scene.frame_set(spec["source"]["frame"])
    geometry = focus_geometry(scene, camera)
    derived = spec["focusDerivation"]
    if not close(geometry["chairObjectOriginCameraDepthM"], derived["chairObjectOriginCameraDepthM"], 2e-5):
        raise RuntimeError("chair origin derivation mismatch")
    if not close(geometry["components"]["CHAIR_BACK"]["centerCameraDepthM"], derived["chairBackCenterCameraDepthM"], 2e-5):
        raise RuntimeError("chair back derivation mismatch")
    if cell["focusObject"] is not None:
        camera.data.dof.focus_object = scene.objects.get(cell["focusObject"])
        if camera.data.dof.focus_object is None:
            raise RuntimeError("focus object binding failed")
    camera.data.dof.use_dof = True
    scene.render.engine = design["engine"]
    scene.cycles.device = design["device"]
    scene.cycles.samples = design["samples"]
    scene.cycles.seed = int(scene["bfs_shot_seed"]) + design["seedOffset"]
    scene.cycles.use_animated_seed = False
    scene.cycles.use_denoising = design["denoising"]
    if hasattr(layer.cycles, "use_denoising"):
        layer.cycles.use_denoising = design["denoising"]
    scene.render.use_motion_blur = design["motionBlur"]
    scene.render.motion_blur_shutter = design["motionBlurShutter"]
    scene.render.motion_blur_position = design["motionBlurPosition"]
    scene.render.use_persistent_data = design["persistentData"]
    scene.render.threads_mode = "FIXED"
    scene.render.threads = design["threads"]
    scene.render.resolution_x, scene.render.resolution_y = design["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
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
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("output directory must start empty")
    projection = control_projection(scene, layer, camera)
    started = time.perf_counter()
    rendered = bpy.ops.render.render(write_still=False)
    render_seconds = time.perf_counter() - started
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
        "schemaVersion": "bfs.focusIntentCellReport.v0.1",
        "experimentId": spec["experimentId"],
        "preregistrationCommit": PREREGISTRATION_COMMIT,
        "specSha256": SPEC_SHA256,
        "cellId": cell["id"],
        "role": cell["role"],
        "source": {"uri": str(source), "sha256": sha256_file(source), "bytes": source.stat().st_size},
        "geometry": geometry,
        "controls": projection,
        "blender": {
            "version": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
            "buildPlatform": bpy.app.build_platform.decode() if isinstance(bpy.app.build_platform, bytes) else str(bpy.app.build_platform),
        },
        "ocio": {"name": ocio.GetCurrentConfig().getName(), "sha256": scene.get("bfs_ocio_sha256")},
        "timing": {"renderSeconds": round(render_seconds, 6), "saveSeconds": round(save_seconds, 6)},
        "peakSelfRssKiB": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "artifact": {"name": exr.name, "sha256": sha256_file(exr), "bytes": exr.stat().st_size},
        "passed": True,
    }
    (output / "render.report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B50_CELL_OK id={cell['id']} renderSeconds={report['timing']['renderSeconds']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B50_CELL_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
