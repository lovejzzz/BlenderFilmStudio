"""Apply and report the frozen B19 Fast-GI/reprojection factors."""

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


def env_bool(name: str) -> bool:
    value = os.environ[name]
    if value not in {"0", "1"}:
        raise RuntimeError(f"{name} must be exactly 0 or 1, received {value!r}")
    return value == "1"


scene = bpy.context.scene
requested_dither = float(os.environ["BFS_B19_DITHER"])
requested_fast_gi = env_bool("BFS_B19_FAST_GI")
requested_reprojection = env_bool("BFS_B19_REPROJECTION")
report_path = Path(os.environ["BFS_B19_INTERVENTION_REPORT"])
before = {
    "ditherIntensity": float(scene.render.dither_intensity),
    "useFastGi": bool(scene.eevee.use_fast_gi),
    "useTaaReprojection": bool(scene.eevee.use_taa_reprojection),
}
if requested_dither != 0.0:
    raise RuntimeError(f"B19 dither must be exactly 0.0, received {requested_dither}")
if before != {"ditherIntensity": 1.0, "useFastGi": True, "useTaaReprojection": True}:
    raise RuntimeError(f"B19 source controls mismatch: {before}")

scene.render.dither_intensity = requested_dither
scene.eevee.use_fast_gi = requested_fast_gi
scene.eevee.use_taa_reprojection = requested_reprojection
after = {
    "ditherIntensity": float(scene.render.dither_intensity),
    "useFastGi": bool(scene.eevee.use_fast_gi),
    "useTaaReprojection": bool(scene.eevee.use_taa_reprojection),
}
requested = {
    "ditherIntensity": requested_dither,
    "useFastGi": requested_fast_gi,
    "useTaaReprojection": requested_reprojection,
}
if after != requested:
    raise RuntimeError(f"B19 intervention did not apply: requested={requested} after={after}")

report = {
    "documentType": "BFS_GI_REPROJECTION_INTERVENTION",
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
print(f"BFS_GI_REPROJECTION_INTERVENTION_OK requested={requested} after={after}")
