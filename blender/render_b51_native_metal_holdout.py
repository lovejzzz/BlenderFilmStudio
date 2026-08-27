"""Render one preregistered B51-H1 canary or holdout cell."""

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


PREREGISTRATION_COMMIT = "b2c053c0f2c4c498fd8123de628dd83ba76e9ebe"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(raw)


def configure_device(spec: dict, requested: str) -> dict:
    expected = spec["nativeBlender"]["cpuDevice" if requested == "CPU" else "metalDevice"]
    preferences = bpy.context.preferences.addons["cycles"].preferences
    if requested == "METAL":
        preferences.compute_device_type = "METAL"
    preferences.get_devices()
    devices = list(preferences.devices)
    for device in devices:
        device.use = device.id == expected["id"]
    selected = [device for device in devices if device.use]
    if len(selected) != 1 or selected[0].id != expected["id"] or selected[0].type != requested:
        raise RuntimeError(f"device selection mismatch: {[(item.id, item.type, item.use) for item in devices]}")
    return {
        "requested": expected,
        "selected": [{"id": item.id, "name": item.name, "type": item.type} for item in selected],
        "roster": [{"id": item.id, "name": item.name, "type": item.type, "use": bool(item.use)} for item in devices],
    }


def apply_operations(operations: list[dict]) -> list[dict]:
    replay = []
    for operation in operations:
        target = bpy.data.objects.get(operation["target"])
        if target is None:
            raise RuntimeError(f"operation target absent: {operation['target']}")
        kind = operation["kind"]
        value = operation["value"]
        if kind == "LOCATION_DELTA":
            before = [float(item) for item in target.location]
            for index, delta in enumerate(value):
                target.location[index] += float(delta)
            after = [float(item) for item in target.location]
        elif kind == "ROTATION_Z_DELTA":
            before = float(target.rotation_euler.z)
            target.rotation_euler.z += float(value)
            after = float(target.rotation_euler.z)
        elif kind == "CAMERA_LENS_SET":
            if target.type != "CAMERA":
                raise RuntimeError(f"camera operation on {target.name}:{target.type}")
            before = float(target.data.lens)
            target.data.lens = float(value)
            after = float(target.data.lens)
        elif kind == "LIGHT_ENERGY_SCALE":
            if target.type != "LIGHT":
                raise RuntimeError(f"light operation on {target.name}:{target.type}")
            before = float(target.data.energy)
            target.data.energy *= float(value)
            after = float(target.data.energy)
        else:
            raise RuntimeError(f"unsupported operation: {kind}")
        replay.append({"operation": operation, "before": before, "after": after})
    return replay


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    is_canary = args.run_id == spec["canary"]["runId"]
    if is_canary:
        cell = {"runId": args.run_id, "variant": spec["canary"]["variant"], "device": "METAL", "repeat": 1, "order": 0}
        variant = {"id": spec["canary"]["variant"], "source": spec["canary"]["source"], "operations": []}
    else:
        cell = next((item for item in spec["cells"] if item["runId"] == args.run_id), None)
        if cell is None:
            raise RuntimeError("unregistered run id")
        variant = next(item for item in spec["variants"] if item["id"] == cell["variant"])
    source_spec = spec["sources"][variant["source"]]
    source = Path(bpy.data.filepath).resolve()
    if sha256_file(source) != source_spec["blendSha256"] or source.stat().st_size != source_spec["blendBytes"]:
        raise RuntimeError("source identity mismatch")
    if tuple(bpy.app.version[:3]) != (5, 2, 0):
        raise RuntimeError(f"Blender 5.2 required: {bpy.app.version_string}")

    scene = bpy.context.scene
    layer = bpy.context.view_layer
    expected_bindings = {
        "planHash": source_spec["planHash"], "sceneSpecHash": source_spec["sceneHash"],
        "structureHash": source_spec["structureHash"], "ocioConfigSha256": spec["ocio"]["sha256"],
    }
    observed_bindings = {
        "planHash": scene.get("bfs_plan_hash"), "sceneSpecHash": scene.get("bfs_scene_spec_hash"),
        "structureHash": scene.get("bfs_structure_hash"), "ocioConfigSha256": scene.get("bfs_ocio_sha256"),
    }
    if observed_bindings != expected_bindings:
        raise RuntimeError(f"binding mismatch: {observed_bindings}")
    if ocio.GetCurrentConfig().getName() != scene.get("bfs_ocio_config"):
        raise RuntimeError("OCIO config mismatch")

    scene.frame_set(source_spec["frame"])
    operation_replay = apply_operations(variant["operations"])
    device = configure_device(spec, cell["device"])
    profile = spec["renderProfile"]
    width, height = spec["canary"]["resolution"] if is_canary else profile["resolution"]
    samples = spec["canary"]["samples"] if is_canary else profile["samples"]
    base_seed = int(scene["bfs_shot_seed"])
    seed = base_seed + profile["seedOffset"]
    scene.render.engine = profile["engine"]
    scene.cycles.device = "CPU" if cell["device"] == "CPU" else "GPU"
    scene.cycles.samples = samples
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
    layer.use_pass_z = not is_canary
    layer.use_pass_normal = not is_canary
    layer.use_pass_position = False
    layer.use_pass_vector = not is_canary
    layer.use_pass_cryptomatte_object = not is_canary
    layer.use_pass_cryptomatte_material = False
    layer.use_pass_cryptomatte_asset = False
    layer.pass_cryptomatte_depth = 6
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = profile["fileFormat"]
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = profile["colorDepth"]
    scene.render.image_settings.exr_codec = profile["codec"]
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("output directory must be empty")
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
    if not exr.is_file():
        raise RuntimeError("production EXR absent")

    rss_raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    report = {
        "schemaVersion": "bfs.nativeMetalProductionHoldoutWorkerReport.v0.1",
        "preregistrationCommit": PREREGISTRATION_COMMIT, "experimentId": spec["experimentId"],
        "runId": cell["runId"], "isCanary": is_canary, "variantId": variant["id"], "sourceId": variant["source"],
        "frame": source_spec["frame"], "deviceType": cell["device"], "repeat": cell["repeat"], "order": cell["order"],
        "process": {"pid": os.getpid(), "parentPid": os.getppid()},
        "source": {"uri": str(source), "sha256": sha256_file(source), "bytes": source.stat().st_size},
        "bindings": {**observed_bindings, "baseShotSeed": base_seed}, "operationReplay": operation_replay,
        "device": device,
        "settings": {"engine": scene.render.engine, "cyclesDevice": scene.cycles.device, "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage], "pixelCount": width * height, "samples": scene.cycles.samples, "seedOffset": profile["seedOffset"], "seed": seed, "animatedSeed": scene.cycles.use_animated_seed, "denoising": scene.cycles.use_denoising, "motionBlur": scene.render.use_motion_blur, "persistentData": scene.render.use_persistent_data, "threadsMode": scene.render.threads_mode, "threads": scene.render.threads},
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash), "buildPlatform": bpy.app.build_platform.decode() if isinstance(bpy.app.build_platform, bytes) else str(bpy.app.build_platform)},
        "ocio": {"name": ocio.GetCurrentConfig().getName(), "sha256": scene.get("bfs_ocio_sha256")},
        "renderSeconds": round(render_seconds, 6), "saveSeconds": round(save_seconds, 6),
        "peakSelfRssBytes": rss_raw if platform.system() == "Darwin" else rss_raw * 1024,
        "artifact": {"uri": exr.name, "sha256": sha256_file(exr), "bytes": exr.stat().st_size}, "passed": True,
    }
    (output / "render.report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B51_H1_RENDER_OK run={cell['runId']} device={cell['device']} renderSeconds={report['renderSeconds']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B51_H1_RENDER_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
