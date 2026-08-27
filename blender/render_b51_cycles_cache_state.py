"""Render one B51-D2 native Metal cache-state cell."""

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


PREREGISTRATION_COMMIT = "90d73be7b73cb15e6f9a15f7fc5f3d72b6af2595"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(raw)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    cell = next((item for item in spec["cells"] if item["runId"] == args.run_id), None)
    if cell is None:
        raise RuntimeError("unregistered run id")
    shot = spec["shot"]
    source = Path(bpy.data.filepath).resolve()
    if sha256_file(source) != shot["blendSha256"] or source.stat().st_size != shot["blendBytes"]:
        raise RuntimeError("source identity mismatch")
    if tuple(bpy.app.version[:3]) != (5, 2, 0):
        raise RuntimeError(f"Blender 5.2 required: {bpy.app.version_string}")

    scene = bpy.context.scene
    layer = bpy.context.view_layer
    expected_bindings = {"planHash": shot["planHash"], "sceneSpecHash": shot["sceneHash"], "structureHash": shot["structureHash"], "ocioConfigSha256": spec["ocio"]["sha256"]}
    observed_bindings = {"planHash": scene.get("bfs_plan_hash"), "sceneSpecHash": scene.get("bfs_scene_spec_hash"), "structureHash": scene.get("bfs_structure_hash"), "ocioConfigSha256": scene.get("bfs_ocio_sha256")}
    if observed_bindings != expected_bindings:
        raise RuntimeError(f"binding mismatch: {observed_bindings}")
    if ocio.GetCurrentConfig().getName() != scene.get("bfs_ocio_config"):
        raise RuntimeError("OCIO config mismatch")

    device_spec = spec["nativeBlender"]["device"]
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.compute_device_type = "METAL"
    preferences.get_devices()
    devices = list(preferences.devices)
    for device in devices:
        device.use = device.id == device_spec["id"]
    selected = [device for device in devices if device.use]
    if len(selected) != 1 or selected[0].id != device_spec["id"] or selected[0].type != "METAL":
        raise RuntimeError("Metal device selection mismatch")

    profile = spec["renderProfile"]
    width, height = profile["resolution"]
    base_seed = int(scene["bfs_shot_seed"])
    seed = base_seed + profile["seedOffset"]
    scene.render.engine = profile["engine"]
    scene.cycles.device = "GPU"
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
    if not exr.is_file():
        raise RuntimeError("production EXR absent")

    rss_raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    report = {
        "schemaVersion": "bfs.cyclesCacheStateWorkerReport.v0.1", "preregistrationCommit": PREREGISTRATION_COMMIT,
        "experimentId": spec["experimentId"], "runId": cell["runId"], "cacheState": cell["cacheState"], "order": cell["order"],
        "shotId": shot["id"], "frame": shot["frame"], "process": {"pid": os.getpid(), "parentPid": os.getppid()},
        "source": {"uri": str(source), "sha256": sha256_file(source), "bytes": source.stat().st_size},
        "bindings": {**observed_bindings, "baseShotSeed": base_seed},
        "device": {"requested": device_spec, "selected": [{"id": item.id, "name": item.name, "type": item.type} for item in selected], "roster": [{"id": item.id, "name": item.name, "type": item.type, "use": bool(item.use)} for item in devices]},
        "settings": {"engine": scene.render.engine, "cyclesDevice": scene.cycles.device, "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage], "pixelCount": width * height, "samples": scene.cycles.samples, "seedOffset": profile["seedOffset"], "seed": seed, "animatedSeed": scene.cycles.use_animated_seed, "denoising": scene.cycles.use_denoising, "motionBlur": scene.render.use_motion_blur, "persistentData": scene.render.use_persistent_data, "threadsMode": scene.render.threads_mode, "threads": scene.render.threads},
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash), "buildPlatform": bpy.app.build_platform.decode() if isinstance(bpy.app.build_platform, bytes) else str(bpy.app.build_platform)},
        "ocio": {"name": ocio.GetCurrentConfig().getName(), "sha256": scene.get("bfs_ocio_sha256")},
        "renderSeconds": round(render_seconds, 6), "saveSeconds": round(save_seconds, 6),
        "peakSelfRssBytes": rss_raw if platform.system() == "Darwin" else rss_raw * 1024,
        "artifact": {"uri": exr.name, "sha256": sha256_file(exr), "bytes": exr.stat().st_size}, "passed": True,
    }
    (output / "render.report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B51_D2_RENDER_OK run={cell['runId']} renderSeconds={report['renderSeconds']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B51_D2_RENDER_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
