"""Render one frozen B51-D1 native Cycles CPU or Metal cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path

import bpy
import PyOpenColorIO as ocio


PREREGISTRATION_COMMIT = "57ae67254c0c269c283acd7e280654a74316442e"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parsed_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(arguments)


def configure_device(requested: str, expected_id: str) -> dict:
    preferences = bpy.context.preferences.addons["cycles"].preferences
    if requested == "METAL":
        preferences.compute_device_type = "METAL"
    preferences.get_devices()
    devices = list(preferences.devices)
    for device in devices:
        device.use = device.id == expected_id
    selected = [device for device in devices if device.use]
    if len(selected) != 1 or selected[0].id != expected_id or selected[0].type != requested:
        raise RuntimeError(f"device selection mismatch: {[(item.id, item.type, item.use) for item in devices]}")
    return {
        "requestedType": requested,
        "requestedId": expected_id,
        "selected": [{"id": item.id, "name": item.name, "type": item.type} for item in selected],
        "roster": [{"id": item.id, "name": item.name, "type": item.type, "use": bool(item.use)} for item in devices],
    }


def main() -> None:
    args = parsed_arguments()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    cell = next((item for item in spec["cells"] if item["runId"] == args.run_id), None)
    if cell is None:
        raise RuntimeError("unregistered run id")
    shot = next(item for item in spec["shots"] if item["id"] == cell["shot"])

    source = Path(bpy.data.filepath).resolve()
    if sha256_file(source) != shot["blendSha256"] or source.stat().st_size != shot["blendBytes"]:
        raise RuntimeError("source identity mismatch")
    if tuple(bpy.app.version[:3]) != (5, 2, 0):
        raise RuntimeError(f"Blender 5.2 required: {bpy.app.version_string}")

    scene = bpy.context.scene
    layer = bpy.context.view_layer
    expected_bindings = {
        "planHash": shot["planHash"],
        "sceneSpecHash": shot["sceneHash"],
        "structureHash": shot["structureHash"],
        "ocioConfigSha256": spec["ocio"]["sha256"],
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

    expected_device = next(item for item in spec["nativeBlender"]["observedDevices"] if item["type"] == cell["device"])
    device = configure_device(cell["device"], expected_device["id"])
    profile = spec["renderProfile"]
    width, height = profile["resolution"]
    base_seed = int(scene["bfs_shot_seed"])
    seed = base_seed + profile["seedOffset"]

    scene.render.engine = profile["engine"]
    scene.cycles.device = "CPU" if cell["device"] == "CPU" else "GPU"
    scene.cycles.samples = profile["samples"]
    scene.cycles.seed = seed
    scene.cycles.use_animated_seed = profile["animatedSeed"]
    scene.cycles.use_denoising = profile["denoising"]
    if hasattr(layer.cycles, "use_denoising"):
        layer.cycles.use_denoising = profile["denoising"]
    scene.render.use_motion_blur = profile["motionBlur"]
    scene.render.use_persistent_data = profile["persistentData"]
    scene.render.threads_mode = "FIXED"
    scene.render.threads = profile["cpuThreads"]
    scene.render.resolution_x = width
    scene.render.resolution_y = height
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
    scene.render.image_settings.file_format = profile["fileFormat"]
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = profile["colorDepth"]
    scene.render.image_settings.exr_codec = profile["codec"]
    scene.frame_set(shot["frame"])

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("output directory must be empty")

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

    rss_raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    rss_bytes = rss_raw if platform.system() == "Darwin" else rss_raw * 1024
    report = {
        "schemaVersion": "bfs.nativeCyclesBackendWorkerReport.v0.1",
        "preregistrationCommit": PREREGISTRATION_COMMIT,
        "experimentId": spec["experimentId"],
        "runId": cell["runId"],
        "shotId": shot["id"],
        "frame": shot["frame"],
        "repeat": cell["repeat"],
        "order": cell["order"],
        "process": {"pid": os.getpid(), "parentPid": os.getppid()},
        "source": {"uri": str(source), "sha256": sha256_file(source), "bytes": source.stat().st_size},
        "bindings": {**observed_bindings, "baseShotSeed": base_seed},
        "device": device,
        "settings": {
            "engine": scene.render.engine,
            "cyclesDevice": scene.cycles.device,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
            "pixelCount": width * height,
            "samples": scene.cycles.samples,
            "seedOffset": profile["seedOffset"],
            "seed": seed,
            "animatedSeed": scene.cycles.use_animated_seed,
            "denoising": scene.cycles.use_denoising,
            "motionBlur": scene.render.use_motion_blur,
            "persistentData": scene.render.use_persistent_data,
            "threadsMode": scene.render.threads_mode,
            "threads": scene.render.threads,
        },
        "blender": {
            "version": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
            "buildPlatform": bpy.app.build_platform.decode() if isinstance(bpy.app.build_platform, bytes) else str(bpy.app.build_platform),
        },
        "ocio": {"name": ocio.GetCurrentConfig().getName(), "sha256": scene.get("bfs_ocio_sha256")},
        "renderSeconds": round(render_seconds, 6),
        "saveSeconds": round(save_seconds, 6),
        "peakSelfRssBytes": rss_bytes,
        "artifact": {"uri": exr.name, "sha256": sha256_file(exr), "bytes": exr.stat().st_size},
        "passed": True,
    }
    (output / "render.report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B51_D1_RENDER_OK run={cell['runId']} device={cell['device']} renderSeconds={report['renderSeconds']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B51_D1_RENDER_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
