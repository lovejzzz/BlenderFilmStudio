"""Zero-render locality probe for the retained B62 v0.3 asset libraries."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import bpy


ASSETS = ["CHAR_B62_GUARDIAN", "SET_B62_OBSERVATORY", "PROP_B62_CONSOLE_CORE"]
TRACKED = ["collections", "objects", "meshes", "armatures", "materials"]
ALL_ID_COLLECTIONS = [
    "actions", "armatures", "cache_files", "cameras", "collections", "curves", "fonts",
    "grease_pencils", "images", "lattices", "lights", "lightprobes", "linestyles",
    "masks", "materials", "meshes", "metaballs", "movieclips", "node_groups", "objects",
    "palettes", "particles", "pointclouds", "scenes", "shape_keys", "sounds", "speakers",
    "texts", "textures", "volumes", "worlds", "workspaces",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def normalize_numbers(value: object) -> object:
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_numbers(item) for key, item in value.items()}
    return value


def canonical(value: object) -> bytes:
    return json.dumps(normalize_numbers(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_hashed(path: Path, body: dict, field: str) -> dict:
    record = {**body, field: hashlib.sha256(canonical(body)).hexdigest()}
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def library_path(item: object) -> str | None:
    library = getattr(item, "library", None)
    return str(Path(bpy.path.abspath(library.filepath)).resolve()) if library else None


def library_roster() -> list[dict]:
    return sorted([
        {
            "name": library.name,
            "filepath": str(Path(bpy.path.abspath(library.filepath)).resolve()),
            "isMissing": bool(library.is_missing),
        }
        for library in bpy.data.libraries
    ], key=lambda row: (row["filepath"], row["name"]))


def linked_ids() -> list[dict]:
    rows = []
    for collection_name in ALL_ID_COLLECTIONS:
        collection = getattr(bpy.data, collection_name, None)
        if collection is None:
            continue
        for item in collection:
            path = library_path(item)
            if path:
                rows.append({"type": collection_name, "name": item.name, "library": path})
    return sorted(rows, key=lambda row: (row["type"], row["name"], row["library"]))


def roster() -> dict[str, list[str]]:
    return {name: sorted(item.name for item in getattr(bpy.data, name)) for name in TRACKED}


def tracked_sets() -> dict[str, set]:
    return {name: set(getattr(bpy.data, name)) for name in TRACKED}


def resolve_item(kind: str, name: str) -> object | None:
    return getattr(bpy.data, kind).get(name)


def remove_new_ids(before: dict[str, set]) -> None:
    for item in set(bpy.data.objects) - before["objects"]:
        bpy.data.objects.remove(item, do_unlink=True)
    for item in set(bpy.data.collections) - before["collections"]:
        bpy.data.collections.remove(item)
    for kind in ["armatures", "meshes", "materials"]:
        collection = getattr(bpy.data, kind)
        for item in set(collection) - before[kind]:
            collection.remove(item)


def inspect_asset(asset_path: Path, asset_id: str) -> dict:
    before_sets = tracked_sets()
    before_roster = roster()
    before_libraries = set(bpy.data.libraries)
    before_linked = linked_ids()
    with bpy.data.libraries.load(str(asset_path), link=False, relative=False, recursive=True) as (source, target):
        source_collections = list(source.collections)
        target.collections = [asset_id]
    loaded_collection = target.collections[0]
    after_sets = tracked_sets()
    appended = []
    for kind in TRACKED:
        for item in sorted(after_sets[kind] - before_sets[kind], key=lambda row: row.name):
            appended.append({"type": kind, "name": item.name, "library": library_path(item)})
    new_libraries = sorted(set(bpy.data.libraries) - before_libraries, key=lambda item: item.name)
    descriptors = [{"name": item.name, "filepath": str(Path(bpy.path.abspath(item.filepath)).resolve()), "isMissing": bool(item.is_missing)} for item in new_libraries]
    appended_identity = [(row["type"], row["name"]) for row in appended]
    descriptor_removal_errors = []
    for library in new_libraries:
        try:
            bpy.data.libraries.remove(library)
        except Exception as error:  # diagnostic surface, not a silent pass
            descriptor_removal_errors.append(f"{type(error).__name__}: {error}")
    survived = []
    for kind, name in appended_identity:
        item = resolve_item(kind, name)
        survived.append({"type": kind, "name": name, "present": item is not None, "library": library_path(item) if item else None})
    remove_new_ids(before_sets)
    cleanup = {
        "rosterExact": roster() == before_roster,
        "librariesExact": set(bpy.data.libraries) == before_libraries,
        "linkedIdsExact": linked_ids() == before_linked,
    }
    expected_source = str(asset_path.resolve())
    checks = {
        "sourceRosterExact": source_collections == [asset_id],
        "collectionLoaded": loaded_collection is not None,
        "appendedIdsObserved": len(appended) > 0,
        "appendedIdsAllLocal": all(row["library"] is None for row in appended),
        "sourceDescriptorsObserved": len(descriptors) > 0,
        "descriptorsExactSource": len(descriptors) > 0 and all(row["filepath"] == expected_source and not row["isMissing"] for row in descriptors),
        "descriptorRemovalSucceeded": len(descriptor_removal_errors) == 0,
        "localIdsSurviveDescriptorRemoval": all(row["present"] and row["library"] is None for row in survived),
        "cleanupExact": all(cleanup.values()),
    }
    return {
        "assetId": asset_id,
        "assetPath": expected_source,
        "sourceCollections": source_collections,
        "appendedIds": appended,
        "sourceDescriptors": descriptors,
        "descriptorRemovalErrors": descriptor_removal_errors,
        "afterDescriptorRemoval": survived,
        "cleanup": cleanup,
        "checks": checks,
    }


def main() -> None:
    args = parse_args()
    formal_root = args.formal_root.resolve(strict=True)
    output = args.output.resolve()
    expected_master = (formal_root / "scene/B62_PHASE0_MASTER.blend").resolve(strict=True)
    if Path(bpy.data.filepath).resolve() != expected_master:
        raise RuntimeError("D6 did not load the retained v0.3 master")
    initial_libraries = library_roster()
    initial_linked = linked_ids()
    initial_roster = roster()
    assets = [inspect_asset(formal_root / f"assets/{asset_id}.blend", asset_id) for asset_id in ASSETS]
    final_state = {"libraries": library_roster(), "linkedIds": linked_ids(), "rosterExact": roster() == initial_roster}
    checks = {
        "masterInitialLibrariesZero": len(initial_libraries) == 0,
        "masterInitialLinkedIdsZero": len(initial_linked) == 0,
        "threeAssetsObserved": len(assets) == 3,
        "allAssetChecksPass": all(all(row["checks"].values()) for row in assets),
        "finalLibrariesZero": len(final_state["libraries"]) == 0,
        "finalLinkedIdsZero": len(final_state["linkedIds"]) == 0,
        "finalRosterExact": final_state["rosterExact"],
        "zeroRenderExternalCalls": True,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    record = write_hashed(output, {
        "schemaVersion": "bfs.b62Phase0D6Probe.v0.1",
        "experimentId": "B62-P0-D6",
        "status": status,
        "master": str(expected_master),
        "initial": {"libraries": initial_libraries, "linkedIds": initial_linked},
        "assets": assets,
        "final": final_state,
        "checks": checks,
        "operations": {"blenderStarts": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }, "probeHash")
    print(f"BFS_B62_D6_PROBE {status} {sum(checks.values())}/{len(checks)} {record['probeHash']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B62_D6_PROBE_ERROR {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
