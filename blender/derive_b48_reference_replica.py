"""Render one frozen B48-D2 independent 512-spp reference replica."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy
import PyOpenColorIO as ocio


PROTOCOL_COMMIT = "132b6417cde5ad8b95f61e5e77d35a2fa2453ca4"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replica-id", required=True)
    parser.add_argument("--seed-offset", type=int, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--plan-hash", required=True)
    parser.add_argument("--scene-hash", required=True)
    parser.add_argument("--structure-hash", required=True)
    parser.add_argument("--ocio-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    expected_offsets = {"R512-A": 0, "R512-B": 104729, "R512-C": 209759}
    if expected_offsets.get(args.replica_id) != args.seed_offset:
        raise RuntimeError("replica/seed-offset mismatch")

    source = Path(bpy.data.filepath).resolve()
    if sha256_file(source) != args.source_sha256:
        raise RuntimeError("source SHA mismatch")
    if tuple(bpy.app.version[:3]) != (5, 2, 0):
        raise RuntimeError(f"Blender 5.2 required: {bpy.app.version_string}")
    scene = bpy.context.scene
    layer = bpy.context.view_layer
    observed = {
        "planHash": scene.get("bfs_plan_hash"),
        "sceneSpecHash": scene.get("bfs_scene_spec_hash"),
        "structureHash": scene.get("bfs_structure_hash"),
        "ocioConfigSha256": scene.get("bfs_ocio_sha256"),
    }
    expected = {
        "planHash": args.plan_hash,
        "sceneSpecHash": args.scene_hash,
        "structureHash": args.structure_hash,
        "ocioConfigSha256": args.ocio_sha256,
    }
    if observed != expected:
        raise RuntimeError(f"binding mismatch: {observed}")
    if ocio.GetCurrentConfig().getName() != scene.get("bfs_ocio_config"):
        raise RuntimeError("OCIO config mismatch")
    if args.frame < scene.frame_start or args.frame > scene.frame_end:
        raise RuntimeError("frame outside source range")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("output directory must be empty")

    base_seed = int(scene["bfs_shot_seed"])
    seed = base_seed + args.seed_offset
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 512
    scene.cycles.seed = seed
    scene.cycles.use_animated_seed = False
    scene.cycles.use_denoising = False
    if hasattr(layer.cycles, "use_denoising"):
        layer.cycles.use_denoising = False
    scene.render.use_motion_blur = False
    scene.render.use_persistent_data = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 128
    scene.render.resolution_y = 72
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
    scene.frame_set(args.frame)

    render_started = time.perf_counter()
    rendered = bpy.ops.render.render(write_still=False)
    render_seconds = time.perf_counter() - render_started
    if "FINISHED" not in rendered:
        raise RuntimeError(f"render failed: {sorted(rendered)}")
    result = bpy.data.images.get("Render Result")
    if result is None:
        raise RuntimeError("Render Result absent")
    exr = output / "reference.exr"
    save_started = time.perf_counter()
    result.save_render(str(exr), scene=scene)
    save_seconds = time.perf_counter() - save_started
    if not exr.exists():
        raise RuntimeError("reference EXR absent")
    report = {
        "schemaVersion": "bfs.independentReferenceReplicaReport.v0.1",
        "protocolCommit": PROTOCOL_COMMIT,
        "replicaId": args.replica_id,
        "source": {"uri": str(source), "sha256": sha256_file(source), "bytes": source.stat().st_size},
        "frame": args.frame,
        "bindings": {**observed, "baseShotSeed": base_seed},
        "settings": {
            "engine": scene.render.engine,
            "device": scene.cycles.device,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
            "samples": scene.cycles.samples,
            "seedOffset": args.seed_offset,
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
        "artifact": {"uri": exr.name, "sha256": sha256_file(exr), "bytes": exr.stat().st_size},
        "passed": True,
    }
    report_path = output / "render.report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"BFS_B48_D2_RENDER_OK id={args.replica_id} seed={seed} "
        f"renderSeconds={report['renderSeconds']}",
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B48_D2_RENDER_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
