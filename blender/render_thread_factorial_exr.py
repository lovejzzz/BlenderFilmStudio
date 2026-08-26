"""Render one B22 observation and save one scene-linear RGBA32 ZIP OpenEXR."""

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
import OpenImageIO as oiio
import PyOpenColorIO as ocio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--cell", choices=["T01", "T08"], required=True)
    parser.add_argument("--invocation-id", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_number(value: float) -> float:
    return round(float(value), 9)


def require_equal(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise RuntimeError(f"{label} mismatch: observed={observed!r} expected={expected!r}")


def camera_snapshot(scene: bpy.types.Scene) -> dict[str, Any]:
    camera = scene.camera
    if camera is None:
        raise RuntimeError("Compiled scene has no active camera")
    original_frame = scene.frame_current
    samples = []
    for frame in [scene.frame_start, 72, scene.frame_end]:
        scene.frame_set(frame)
        samples.append({
            "frame": frame,
            "location": [stable_number(value) for value in camera.location],
            "rotationEuler": [stable_number(value) for value in camera.rotation_euler],
            "matrixWorld": [stable_number(value) for row in camera.matrix_world for value in row],
            "lensMm": stable_number(camera.data.lens),
            "focusDistanceM": stable_number(camera.data.dof.focus_distance),
        })
    scene.frame_set(original_frame)
    return {
        "camera": camera.name,
        "frameStart": scene.frame_start,
        "frameEnd": scene.frame_end,
        "fps": scene.render.fps,
        "samples": samples,
    }


def inspect_image(path: Path) -> dict[str, Any]:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"OIIO cannot decode {path}: {image.geterror()}")
    spec = image.spec()
    return {
        "width": spec.width,
        "height": spec.height,
        "channels": list(spec.channelnames),
        "pixelFormat": str(spec.format),
    }


def main() -> None:
    args = parse_args()
    review_spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    plan_path = Path.cwd() / receipt["executionIdentity"]["buildPlan"]["uri"]
    plan = json.loads(plan_path.read_text(encoding="utf-8"))["plan"]
    source = review_spec["source"]
    runtime = review_spec["runtime"]
    timeline = review_spec["timeline"]
    proxy = review_spec["proxy"]
    scene = bpy.context.scene

    require_equal(bpy.app.version_string, runtime["blender"]["version"], "Blender version")
    require_equal(bpy.app.build_hash.decode("utf-8"), runtime["blender"]["buildHash"], "Blender build hash")
    require_equal(receipt["receiptHash"], source["receiptHash"], "receipt hash")
    require_equal(receipt["executionIdentityHash"], source["executionIdentityHash"], "execution identity")
    require_equal(sha256_file(Path(bpy.data.filepath)), source["sceneBlendSha256"], "scene bytes")
    require_equal(scene.get("bfs_plan_hash"), source["planHash"], "plan marker")
    require_equal(scene.get("bfs_structure_hash"), source["structureHash"], "structure marker")
    require_equal(scene.get("bfs_ocio_sha256"), runtime["ocioConfigSha256"], "OCIO marker")
    require_equal(ocio.GetCurrentConfig().getName(), plan["outputSpec"]["color"]["ocioConfigName"], "OCIO name")
    if args.frame < timeline["frameStart"] or args.frame > timeline["frameEnd"]:
        raise RuntimeError("Frame outside frozen timeline")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("B22 output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    expected_threads = 1 if args.cell == "T01" else 8
    observed_thread_state = {
        "threadsMode": scene.render.threads_mode,
        "threads": int(scene.render.threads),
    }
    require_equal(
        observed_thread_state,
        {"threadsMode": "FIXED", "threads": expected_threads},
        "B22 thread intervention",
    )

    original_frame = scene.frame_current
    identity_before = camera_snapshot(scene)
    scene.frame_set(args.frame)
    scene.render.engine = proxy["renderEngine"]
    scene.eevee.taa_render_samples = proxy["renderSamples"]
    scene.render.use_motion_blur = proxy["motionBlur"]
    scene.render.resolution_x = proxy["width"]
    scene.render.resolution_y = proxy["height"]
    scene.render.resolution_percentage = proxy["resolutionPercentage"]
    scene.render.film_transparent = proxy["filmTransparent"]
    scene.render.use_stamp = False
    controls = {
        "renderSamples": int(scene.eevee.taa_render_samples),
        "ditherIntensity": float(scene.render.dither_intensity),
        "useFastGi": bool(scene.eevee.use_fast_gi),
        "useTaaReprojection": bool(scene.eevee.use_taa_reprojection),
    }
    require_equal(
        controls,
        {
            "renderSamples": 32,
            "ditherIntensity": 0.0,
            "useFastGi": True,
            "useTaaReprojection": True,
        },
        "fixed controls",
    )

    output_path = args.output_dir / f"frame-{args.frame:04d}.exr"
    scene.render.filepath = str(output_path.resolve())
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"

    started = time.perf_counter()
    render_operator_call_count = 0
    result = bpy.ops.render.render(write_still=False)
    render_operator_call_count += 1
    if "FINISHED" not in result:
        raise RuntimeError(f"Render failed: {sorted(result)}")
    render_result = bpy.data.images.get("Render Result")
    if render_result is None:
        raise RuntimeError("Render Result data-block unavailable")
    render_result.save_render(str(output_path.resolve()), scene=scene)
    save_count = 1
    if render_operator_call_count != 1 or save_count != 1 or not output_path.exists():
        raise RuntimeError("One-render/one-save contract failed")

    scene.frame_set(original_frame)
    identity_after = camera_snapshot(scene)
    require_equal(identity_after, identity_before, "camera/timeline identity")
    decoded = inspect_image(output_path)
    require_equal(
        decoded,
        {"width": 960, "height": 540, "channels": ["R", "G", "B", "A"], "pixelFormat": "float"},
        "EXR layout",
    )
    output = {
        "name": output_path.name,
        "sha256": sha256_file(output_path),
        "bytes": output_path.stat().st_size,
        "settings": {"fileFormat": "OPEN_EXR", "colorMode": "RGBA", "colorDepth": "32", "codec": "ZIP"},
        "decoded": decoded,
    }
    report = {
        "documentType": "BFS_B22_THREAD_FACTORIAL_RENDER",
        "version": "0.1.0",
        "invocationId": args.invocation_id,
        "processId": os.getpid(),
        "frame": args.frame,
        "cell": args.cell,
        "observedThreadState": observed_thread_state,
        "renderOperatorCallCount": render_operator_call_count,
        "saveCount": save_count,
        "source": {
            "sceneBlendSha256": sha256_file(Path(bpy.data.filepath)),
            "planHash": scene["bfs_plan_hash"],
            "structureHash": scene["bfs_structure_hash"],
        },
        "runtime": {
            "blenderVersion": bpy.app.version_string,
            "blenderBuildHash": bpy.app.build_hash.decode("utf-8"),
            "ocioConfigName": ocio.GetCurrentConfig().getName(),
            "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
        },
        "observedControls": controls,
        "output": output,
        "cameraAndTimelineInvariant": identity_before == identity_after,
        "totalSeconds": round(time.perf_counter() - started, 6),
        "savedSourceBlend": False,
    }
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"BFS_B22_RENDER_OK {args.invocation_id} pid={os.getpid()} "
        f"frame={args.frame} cell={args.cell} exr={output['sha256']}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B22_RENDER_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
