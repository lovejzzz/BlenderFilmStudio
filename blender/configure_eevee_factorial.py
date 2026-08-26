"""Apply and report the frozen B17 output-dither factor before review rendering."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import bpy


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


requested = float(os.environ["BFS_FACTORIAL_DITHER_INTENSITY"])
expected_before = float(os.environ["BFS_EXPECT_DITHER_INTENSITY"])
report_path = Path(os.environ["BFS_FACTORIAL_DITHER_REPORT"])
scene = bpy.context.scene
before = float(scene.render.dither_intensity)

if requested not in (0.0, 1.0):
    raise RuntimeError(f"B17 dither factor must be exactly 0.0 or 1.0, received {requested}")
if expected_before != 1.0 or before != expected_before:
    raise RuntimeError(f"B17 starting dither must be exactly 1.0, received {before}")

scene.render.dither_intensity = requested
after = float(scene.render.dither_intensity)
if after != requested:
    raise RuntimeError(f"B17 dither factor did not apply: requested={requested} after={after}")

report = {
    "documentType": "BFS_EEVEE_FACTORIAL_INTERVENTION",
    "version": "0.1.0",
    "sceneBlendSha256": sha256_file(Path(bpy.data.filepath)),
    "scenePlanHash": scene.get("bfs_plan_hash"),
    "before": before,
    "requested": requested,
    "after": after,
    "savedSourceBlend": False,
}
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"BFS_EEVEE_FACTORIAL_INTERVENTION_OK before={before} requested={requested} after={after}")
