"""Render one preregistered B52-D1 native CPU adaptive-sampling cell."""

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


PREREGISTRATION_COMMIT = "30a2a56bdda56ac2aefe0be739afa192edc15202"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--repeat", type=int, required=True)
    parser.add_argument("--order", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(raw)


def apply_operations(operations: list[dict]) -> list[dict]:
    replay: list[dict] = []
    for operation in operations:
        target = bpy.data.objects.get(operation["target"])
        if target is None:
            raise RuntimeError(f"operation target absent: {operation['target']}")
        kind, value = operation["kind"], operation["value"]
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


def configure_cpu(parent_spec: dict) -> dict:
    expected = parent_spec["nativeBlender"]["cpuDevice"]
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.get_devices()
    devices = list(preferences.devices)
    for device in devices:
        device.use = device.id == expected["id"]
    selected = [device for device in devices if device.use]
    if len(selected) != 1 or selected[0].id != expected["id"] or selected[0].type != "CPU":
        raise RuntimeError(f"CPU device selection mismatch: {[(item.id, item.type, item.use) for item in devices]}")
    return {
        "requested": expected,
        "selected": [{"id": item.id, "name": item.name, "type": item.type} for item in selected],
        "roster": [{"id": item.id, "name": item.name, "type": item.type, "use": bool(item.use)} for item in devices],
    }


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    root = args.spec.resolve().parent.parent
    d5_spec_path = root / spec["parents"]["d5Spec"]["uri"]
    d5_spec = json.loads(d5_spec_path.read_text(encoding="utf-8"))
    h1_spec = json.loads((root / d5_spec["parents"]["h1Spec"]["uri"]).read_text(encoding="utf-8"))
    variant = next((item for item in d5_spec["variants"] if item["id"] == args.variant), None)
    profiles = [*spec["referenceCells"], *spec["candidateProfiles"]]
    profile = next((item for item in profiles if item["id"] == args.profile), None)
    if variant is None or profile is None:
        raise RuntimeError("unregistered B52-D1 matrix cell")
    maximum_repeat = 1 if profile in spec["referenceCells"] else spec["candidateRepeats"]
    if args.repeat not in range(1, maximum_repeat + 1):
        raise RuntimeError("unregistered B52-D1 repeat")

    source_spec = d5_spec["sources"][variant["source"]]
    source = Path(bpy.data.filepath).resolve()
    if sha256_file(source) != source_spec["blendSha256"] or source.stat().st_size != source_spec["blendBytes"]:
        raise RuntimeError("source identity mismatch")
    if tuple(bpy.app.version[:3]) != (5, 2, 0):
        raise RuntimeError(f"Blender 5.2 required: {bpy.app.version_string}")

    scene = bpy.context.scene
    layer = bpy.context.view_layer
    expected_bindings = {
        "planHash": source_spec["planHash"],
        "sceneSpecHash": source_spec["sceneHash"],
        "structureHash": source_spec["structureHash"],
        "ocioConfigSha256": d5_spec["ocio"]["sha256"],
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

    scene.frame_set(source_spec["frame"])
    operation_replay = apply_operations(variant["operations"])
    device = configure_cpu(h1_spec)
    render_profile = spec["renderProfile"]
    width, height = render_profile["resolution"]
    base_seed = int(scene["bfs_shot_seed"])
    seed = base_seed + int(profile["seedOffset"])
    scene.render.engine = render_profile["engine"]
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(profile["maxSamples"])
    scene.cycles.seed = seed
    scene.cycles.use_animated_seed = render_profile["animatedSeed"]
    scene.cycles.use_adaptive_sampling = bool(profile["adaptive"])
    scene.cycles.adaptive_threshold = float(profile.get("noiseThreshold", 0.01))
    scene.cycles.adaptive_min_samples = int(profile.get("minSamples", 0))
    scene.cycles.use_denoising = render_profile["denoising"]
    if hasattr(layer.cycles, "use_denoising"):
        layer.cycles.use_denoising = render_profile["denoising"]
    scene.render.use_motion_blur = render_profile["motionBlur"]
    scene.render.use_persistent_data = render_profile["persistentData"]
    scene.render.threads_mode = "FIXED"
    scene.render.threads = render_profile["cpuThreads"]
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
    layer.cycles.pass_debug_sample_count = True
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = render_profile["fileFormat"]
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = render_profile["colorDepth"]
    scene.render.image_settings.exr_codec = render_profile["codec"]

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
    run_id = f"{variant['id']}_{profile['id']}_R{args.repeat}"
    report = {
        "schemaVersion": "bfs.nativeCpuAdaptiveQualityCostWorkerReport.v0.1",
        "preregistrationCommit": PREREGISTRATION_COMMIT,
        "experimentId": spec["experimentId"],
        "runId": run_id,
        "variantId": variant["id"],
        "sourceId": variant["source"],
        "profileId": profile["id"],
        "role": profile.get("role", "REFERENCE"),
        "repeat": args.repeat,
        "order": args.order,
        "frame": source_spec["frame"],
        "deviceType": "CPU",
        "process": {"pid": os.getpid(), "parentPid": os.getppid()},
        "source": {"uri": source_spec["blendUri"], "sha256": sha256_file(source), "bytes": source.stat().st_size},
        "bindings": {**observed_bindings, "baseShotSeed": base_seed},
        "operationReplay": operation_replay,
        "device": device,
        "settings": {
            "engine": scene.render.engine,
            "cyclesDevice": scene.cycles.device,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
            "pixelCount": width * height,
            "maxSamples": scene.cycles.samples,
            "seedOffset": int(profile["seedOffset"]),
            "seed": seed,
            "animatedSeed": scene.cycles.use_animated_seed,
            "adaptive": scene.cycles.use_adaptive_sampling,
            "noiseThreshold": float(scene.cycles.adaptive_threshold),
            "minSamples": scene.cycles.adaptive_min_samples,
            "denoising": scene.cycles.use_denoising,
            "motionBlur": scene.render.use_motion_blur,
            "persistentData": scene.render.use_persistent_data,
            "threadsMode": scene.render.threads_mode,
            "threads": scene.render.threads,
            "sampleCountPass": bool(layer.cycles.pass_debug_sample_count),
        },
        "blender": {
            "version": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
            "buildPlatform": bpy.app.build_platform.decode() if isinstance(bpy.app.build_platform, bytes) else str(bpy.app.build_platform),
        },
        "ocio": {"name": ocio.GetCurrentConfig().getName(), "sha256": scene.get("bfs_ocio_sha256")},
        "renderSeconds": round(render_seconds, 6),
        "saveSeconds": round(save_seconds, 6),
        "peakSelfRssBytes": rss_raw if platform.system() == "Darwin" else rss_raw * 1024,
        "artifact": {"uri": exr.name, "sha256": sha256_file(exr), "bytes": exr.stat().st_size},
        "passed": True,
    }
    (output / "render.report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B52_D1_RENDER_OK run={run_id} renderSeconds={report['renderSeconds']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B52_D1_RENDER_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
