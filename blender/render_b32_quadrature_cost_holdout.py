"""Render one preregistered B32 quadrature cost-quality holdout process."""

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


CELL_IDS = (
    "NATURAL32", "REFERENCE1024",
    "Q4_1", "Q4_2", "Q4_3", "Q4_4",
    "Q8_1", "Q8_2", "Q8_3", "Q8_4", "Q8_5", "Q8_6", "Q8_7", "Q8_8",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout-spec", type=Path, required=True)
    parser.add_argument("--review-spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--cell", choices=CELL_IDS, required=True)
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


def cell_controls(spec: dict[str, Any], cell: str) -> tuple[int, list[float] | None]:
    if cell == "NATURAL32":
        return spec["design"]["natural32"]["samples"], None
    if cell == "REFERENCE1024":
        return spec["design"]["reference1024"]["samples"], None
    family, index_text = cell.split("_")
    index = int(index_text) - 1
    key = "quadrature4" if family == "Q4" else "stratified8"
    definition = spec["design"][key]
    return definition["samplesPerComponent"], definition["points"][index]


def main() -> None:
    args = parse_args()
    spec = json.loads(args.holdout_spec.read_text(encoding="utf-8"))
    review = json.loads(args.review_spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    require_equal(spec["documentType"], "BFS_QUADRATURE_COST_HOLDOUT_SPEC", "holdout spec type")
    require_equal(spec["status"], "PREREGISTERED_BEFORE_FORMAL_TOOLING_OR_OUTPUTS", "holdout spec status")
    require_equal(review["documentType"], "BFS_REVIEW_RENDER_SPEC", "review spec type")

    scene = bpy.context.scene
    source, runtime = spec["source"], spec["runtime"]
    require_equal(sha256_file(args.review_spec), source["reviewSpecSha256"], "review spec SHA")
    require_equal(bpy.app.version_string, runtime["blenderVersion"], "Blender version")
    require_equal(bpy.app.build_hash.decode("utf-8"), runtime["blenderBuildHash"], "Blender build hash")
    require_equal(sha256_file(Path(bpy.data.filepath)), source["sceneBlendSha256"], "opened scene bytes")
    require_equal(scene.get("bfs_plan_hash"), source["planHash"], "embedded plan marker")
    require_equal(scene.get("bfs_structure_hash"), source["structureHash"], "embedded structure marker")
    require_equal(scene.get("bfs_ocio_sha256"), runtime["ocioSha256"], "embedded OCIO marker")
    require_equal(receipt["run"]["sceneBlend"]["sha256"], source["sceneBlendSha256"], "receipt scene")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("B32 holdout output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    samples, expected_jitter = cell_controls(spec, args.cell)
    if expected_jitter is None:
        if "override_pixel_jitter_sample" in scene:
            del scene["override_pixel_jitter_sample"]
    else:
        scene["override_pixel_jitter_sample"] = expected_jitter
    require_equal(jitter_value(scene), expected_jitter, "jitter intervention")

    scene.render.engine = runtime["engine"]
    scene.eevee.taa_render_samples = samples
    scene.render.use_motion_blur = runtime["motionBlur"]
    scene.render.resolution_x, scene.render.resolution_y = runtime["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"
    scene.render.film_transparent = False
    scene.render.use_stamp = False
    observed_controls = {
        "engine": scene.render.engine,
        "samples": int(scene.eevee.taa_render_samples),
        "jitter": jitter_value(scene),
        "threadsMode": scene.render.threads_mode,
        "threads": int(scene.render.threads),
        "dither": float(scene.render.dither_intensity),
        "useFastGi": bool(scene.eevee.use_fast_gi),
        "useTaaReprojection": bool(scene.eevee.use_taa_reprojection),
        "motionBlur": bool(scene.render.use_motion_blur),
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    }
    require_equal(observed_controls, {
        "engine": runtime["engine"], "samples": samples, "jitter": expected_jitter,
        "threadsMode": runtime["threadsMode"], "threads": runtime["threads"],
        "dither": runtime["dither"], "useFastGi": runtime["useFastGi"],
        "useTaaReprojection": runtime["useTaaReprojection"], "motionBlur": runtime["motionBlur"],
        "resolution": runtime["resolution"],
    }, "frozen controls")

    frames = spec["design"]["frames"]
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
        outputs.append({
            "frame": frame, "name": output.name, "sha256": sha256_file(output),
            "bytes": output.stat().st_size,
            "renderSeconds": round(time.perf_counter() - frame_started, 6),
        })
        print(f"BFS_B32_HOLDOUT_FRAME_OK {args.cell}_{args.replicate} {frame}")

    report = {
        "documentType": "BFS_B32_QUADRATURE_COST_HOLDOUT_RENDER",
        "version": "0.1.0",
        "holdoutSpecSha256": sha256_file(args.holdout_spec),
        "replicateId": f"{args.cell}_{args.replicate}",
        "cell": args.cell,
        "replicate": args.replicate,
        "processId": os.getpid(),
        "source": {
            "sceneBlendSha256": sha256_file(Path(bpy.data.filepath)),
            "planHash": scene["bfs_plan_hash"],
            "structureHash": scene["bfs_structure_hash"],
        },
        "runtime": {
            "blenderVersion": bpy.app.version_string,
            "blenderBuildHash": bpy.app.build_hash.decode("utf-8"),
            "ocioConfigName": ocio.GetCurrentConfig().getName(),
        },
        "observedControls": observed_controls,
        "frames": frames,
        "outputs": outputs,
        "renderCalls": len(outputs),
        "outputFileCount": len(outputs),
        "totalRenderSeconds": round(time.perf_counter() - started, 6),
        "savedSourceBlend": False,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B32_HOLDOUT_PROCESS_OK {args.cell}_{args.replicate} renders={len(outputs)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B32_HOLDOUT_RENDER_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
