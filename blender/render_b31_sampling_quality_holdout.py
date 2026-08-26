"""Render one formal B31 sampling-quality holdout cell/replicate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import bpy
import PyOpenColorIO as ocio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b31-spec", type=Path, required=True)
    parser.add_argument("--review-spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--cell", choices=("NATURAL32", "CENTER32", "REFERENCE1024"), required=True)
    parser.add_argument("--replicate", choices=("A", "B"), required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_equal(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise RuntimeError(f"{label} mismatch: observed={observed!r} expected={expected!r}")


def jitter_value(scene: bpy.types.Scene) -> list[float] | None:
    if "override_pixel_jitter_sample" not in scene:
        return None
    value = scene["override_pixel_jitter_sample"]
    return [float(value[0]), float(value[1])]


def main() -> None:
    args = parse_args()
    spec = json.loads(args.b31_spec.read_text(encoding="utf-8"))
    review = json.loads(args.review_spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    require_equal(spec["documentType"], "BFS_SAMPLING_QUALITY_HOLDOUT_SPEC", "B31 spec type")
    require_equal(spec["status"], "pre-registered", "B31 status")
    require_equal(review["documentType"], "BFS_REVIEW_RENDER_SPEC", "review spec type")
    expected_id = f"{args.cell}_{args.replicate}"
    if expected_id not in spec["design"]["schedule"]:
        raise RuntimeError(f"Unexpected B31 replicate {expected_id}")

    scene = bpy.context.scene
    source, runtime = review["source"], review["runtime"]
    frozen, constants = spec["frozenIdentity"], spec["constants"]
    require_equal(bpy.app.version_string, runtime["blender"]["version"], "Blender version")
    require_equal(bpy.app.build_hash.decode("utf-8"), runtime["blender"]["buildHash"], "Blender build hash")
    require_equal(sha256_file(Path(bpy.data.filepath)), frozen["sceneBlendSha256"], "opened scene bytes")
    require_equal(scene.get("bfs_plan_hash"), frozen["planHash"], "embedded plan marker")
    require_equal(scene.get("bfs_structure_hash"), frozen["structureHash"], "embedded structure marker")
    require_equal(scene.get("bfs_ocio_sha256"), frozen["ocioSha256"], "embedded OCIO marker")
    require_equal(receipt["run"]["sceneBlend"]["sha256"], frozen["sceneBlendSha256"], "receipt scene")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("B31 output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    cell = spec["design"]["cells"][args.cell]
    expected_jitter = cell["overridePixelJitterSample"]
    if expected_jitter is None:
        if "override_pixel_jitter_sample" in scene:
            del scene["override_pixel_jitter_sample"]
    else:
        scene["override_pixel_jitter_sample"] = expected_jitter
    require_equal(jitter_value(scene), expected_jitter, "jitter intervention")

    scene.render.engine = constants["engine"]
    scene.eevee.taa_render_samples = cell["samples"]
    scene.render.use_motion_blur = constants["motionBlur"]
    scene.render.resolution_x, scene.render.resolution_y = constants["width"], constants["height"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"
    scene.render.film_transparent = False
    scene.render.use_stamp = False
    observed_controls = {
        "engine": scene.render.engine, "samples": int(scene.eevee.taa_render_samples), "jitter": jitter_value(scene),
        "threadsMode": scene.render.threads_mode, "threads": int(scene.render.threads),
        "ditherIntensity": float(scene.render.dither_intensity), "useFastGi": bool(scene.eevee.use_fast_gi),
        "useTaaReprojection": bool(scene.eevee.use_taa_reprojection), "motionBlur": bool(scene.render.use_motion_blur),
        "width": scene.render.resolution_x, "height": scene.render.resolution_y,
    }
    require_equal(observed_controls, {
        "engine": constants["engine"], "samples": cell["samples"], "jitter": expected_jitter,
        "threadsMode": constants["threadsMode"], "threads": constants["threads"],
        "ditherIntensity": constants["ditherIntensity"], "useFastGi": constants["useFastGi"],
        "useTaaReprojection": constants["useTaaReprojection"], "motionBlur": constants["motionBlur"],
        "width": constants["width"], "height": constants["height"],
    }, "frozen controls")

    frames = spec["design"]["holdoutFrames"]
    outputs = []
    started = time.perf_counter()
    for frame in frames:
        scene.frame_set(frame)
        output = args.output_dir / f"frame-{frame:04d}.exr"
        scene.render.filepath = str(output.resolve())
        frame_started = time.perf_counter()
        result = bpy.ops.render.render(write_still=True)
        if "FINISHED" not in result or not output.exists():
            raise RuntimeError(f"Frame {frame} failed: {sorted(result)}")
        require_equal(scene.frame_current, frame, f"frame {frame}")
        require_equal(jitter_value(scene), expected_jitter, f"frame {frame} jitter")
        outputs.append({"frame": frame, "name": output.name, "sha256": sha256_file(output),
                        "bytes": output.stat().st_size, "renderSeconds": round(time.perf_counter() - frame_started, 6)})
        print(f"BFS_B31_HOLDOUT_FRAME_OK {expected_id} {frame}")

    report = {
        "documentType": "BFS_B31_SAMPLING_QUALITY_HOLDOUT_RENDER", "version": "0.1.0",
        "b31SpecSha256": sha256_file(args.b31_spec), "replicateId": expected_id, "cell": args.cell,
        "replicate": args.replicate, "processId": os.getpid(),
        "source": {"sceneBlendSha256": sha256_file(Path(bpy.data.filepath)), "planHash": scene["bfs_plan_hash"],
                   "structureHash": scene["bfs_structure_hash"]},
        "runtime": {"blenderVersion": bpy.app.version_string, "blenderBuildHash": bpy.app.build_hash.decode("utf-8"),
                    "ocioConfigName": ocio.GetCurrentConfig().getName()},
        "observedControls": observed_controls, "frames": frames, "outputs": outputs,
        "renderCalls": len(outputs), "outputFileCount": len(outputs),
        "totalRenderSeconds": round(time.perf_counter() - started, 6), "savedSourceBlend": False,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B31_HOLDOUT_PROCESS_OK {expected_id} renders={len(outputs)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B31_HOLDOUT_RENDER_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
