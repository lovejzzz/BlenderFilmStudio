"""Inventory real Blender 5.2 controls relevant to Eevee reproducibility."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

import bpy
import PyOpenColorIO as ocio


TOKENS = (
    "sample", "seed", "random", "noise", "jitter", "temporal", "taa",
    "reprojection", "shadow", "ray", "thread", "gi", "motion", "dither",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scene-uri", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, set):
        return sorted(json_value(item) for item in value)
    try:
        return [json_value(item) for item in value]
    except TypeError:
        return repr(value)


def relevant_rna(owner: Any) -> list[dict[str, Any]]:
    rows = []
    for prop in owner.bl_rna.properties:
        if prop.identifier == "rna_type":
            continue
        haystack = f"{prop.identifier} {prop.name} {prop.description}".lower()
        if not any(token in haystack for token in TOKENS):
            continue
        try:
            value = json_value(getattr(owner, prop.identifier))
        except Exception as error:  # Blender RNA access may be context-dependent.
            value = {"accessError": str(error)}
        row = {
            "identifier": prop.identifier,
            "name": prop.name,
            "type": prop.type,
            "description": prop.description,
            "value": value,
            "isReadOnly": prop.is_readonly,
            "isArray": getattr(prop, "is_array", False),
        }
        if prop.type in {"INT", "FLOAT"}:
            row.update({
                "hardMin": json_value(prop.hard_min),
                "hardMax": json_value(prop.hard_max),
                "softMin": json_value(prop.soft_min),
                "softMax": json_value(prop.soft_max),
            })
        if prop.type == "ENUM":
            row["enumItems"] = [item.identifier for item in prop.enum_items]
        rows.append(row)
    return sorted(rows, key=lambda row: row["identifier"])


def owner_record(label: str, owner: Any) -> dict[str, Any]:
    return {
        "label": label,
        "rnaType": owner.bl_rna.identifier,
        "properties": relevant_rna(owner),
    }


args = parse_args()
scene = bpy.context.scene
source_path = Path(bpy.data.filepath)
domains = [
    owner_record("scene.eevee", scene.eevee),
    owner_record("scene.render", scene.render),
    owner_record("scene.display_settings", scene.display_settings),
    owner_record("scene.view_settings", scene.view_settings),
    owner_record("preferences.system", bpy.context.preferences.system),
]
lights = []
for light in sorted(bpy.data.lights, key=lambda item: item.name):
    lights.append({
        "name": light.name,
        "type": light.type,
        "energy": light.energy,
        "properties": relevant_rna(light),
        "users": sorted(obj.name for obj in bpy.data.objects if obj.data == light),
    })

report = {
    "documentType": "BFS_EEVEE_CONTROL_INVENTORY",
    "version": "0.1.0",
    "classification": "EXPLORATORY_RNA_AUDIT_NOT_CAUSAL_RESULT",
    "source": {
        "sceneBlendUri": args.scene_uri,
        "sceneBlendSha256": sha256_file(source_path),
        "planHash": scene.get("bfs_plan_hash"),
        "structureHash": scene.get("bfs_structure_hash"),
    },
    "runtime": {
        "blenderVersion": bpy.app.version_string,
        "blenderBuildHash": bpy.app.build_hash.decode("utf-8"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "ocioConfigName": ocio.GetCurrentConfig().getName(),
        "debugValue": bpy.app.debug_value,
    },
    "observedRenderState": {
        "engine": scene.render.engine,
        "threadsMode": scene.render.threads_mode,
        "threads": scene.render.threads,
        "ditherIntensity": scene.render.dither_intensity,
        "frameStart": scene.frame_start,
        "frameEnd": scene.frame_end,
    },
    "matchedTokens": list(TOKENS),
    "domains": domains,
    "lights": lights,
    "explicitNonClaims": [
        "RNA property presence does not prove that the property caused B15-B18 differences.",
        "A property description is API metadata, not a determinism guarantee.",
        "The inventory does not mutate or save the source blend.",
        "Unexposed internal renderer state may exist beyond RNA.",
    ],
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"BFS_EEVEE_CONTROL_INVENTORY_OK domains={len(domains)} lights={len(lights)} output={args.output}")
