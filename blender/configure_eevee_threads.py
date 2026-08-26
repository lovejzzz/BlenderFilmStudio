"""Apply the frozen B22 render-thread intervention without saving the source blend."""

from __future__ import annotations

import json
import os
from pathlib import Path

import bpy


def main() -> None:
    scene = bpy.context.scene
    report_path = Path(os.environ["BFS_B22_INTERVENTION_REPORT"])
    requested_mode = os.environ["BFS_B22_THREADS_MODE"]
    requested_threads = int(os.environ["BFS_B22_THREADS"])
    cell = os.environ["BFS_B22_CELL"]

    before = {
        "threadsMode": scene.render.threads_mode,
        "threads": int(scene.render.threads),
        "ditherIntensity": float(scene.render.dither_intensity),
        "useFastGi": bool(scene.eevee.use_fast_gi),
        "useTaaReprojection": bool(scene.eevee.use_taa_reprojection),
    }
    if before["threadsMode"] != "FIXED" or before["threads"] != 8:
        raise RuntimeError(f"B22 source thread state mismatch: {before!r}")
    if requested_mode != "FIXED" or requested_threads not in {1, 8}:
        raise RuntimeError(
            f"B22 invalid requested thread state: {requested_mode}/{requested_threads}"
        )
    expected_cell = "T01" if requested_threads == 1 else "T08"
    if cell != expected_cell:
        raise RuntimeError(f"B22 cell mismatch: {cell!r} != {expected_cell!r}")

    scene.render.threads_mode = requested_mode
    scene.render.threads = requested_threads
    scene.render.dither_intensity = 0.0
    scene.eevee.use_fast_gi = True
    scene.eevee.use_taa_reprojection = True
    after = {
        "threadsMode": scene.render.threads_mode,
        "threads": int(scene.render.threads),
        "ditherIntensity": float(scene.render.dither_intensity),
        "useFastGi": bool(scene.eevee.use_fast_gi),
        "useTaaReprojection": bool(scene.eevee.use_taa_reprojection),
    }
    if after != {
        "threadsMode": requested_mode,
        "threads": requested_threads,
        "ditherIntensity": 0.0,
        "useFastGi": True,
        "useTaaReprojection": True,
    }:
        raise RuntimeError(f"B22 intervention did not take effect: {after!r}")

    report = {
        "documentType": "BFS_B22_THREAD_INTERVENTION",
        "version": "0.1.0",
        "cell": cell,
        "before": before,
        "requested": {"threadsMode": requested_mode, "threads": requested_threads},
        "after": after,
        "savedSourceBlend": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"BFS_B22_INTERVENTION_OK cell={cell} "
        f"before={before['threadsMode']}/{before['threads']} "
        f"after={after['threadsMode']}/{after['threads']}"
    )


if __name__ == "__main__":
    main()
