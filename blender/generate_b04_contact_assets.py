"""Generate separate B04 actor and prop assets without changing B03 evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_actor_benchmark import (
    bind_mesh,
    bone_records,
    clear_scene,
    make_material,
    make_mesh,
    sha256_file,
    sha256_value,
    shape_record,
    topology_record,
)


GENERATOR_VERSION = "0.1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-actor", type=Path, required=True)
    parser.add_argument("--actor-output", type=Path, required=True)
    parser.add_argument("--prop-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def main() -> None:
    args = parse_args()
    for path in (args.actor_output, args.prop_output, args.report_output):
        path.parent.mkdir(parents=True, exist_ok=True)
    clear_scene()
    with bpy.data.libraries.load(str(args.source_actor.resolve()), link=False, recursive=True) as (source, target):
        if "CHAR_B03" not in source.collections:
            raise RuntimeError("Source actor has no CHAR_B03 collection")
        target.collections = ["CHAR_B03"]
    actor_collection = target.collections[0]
    actor_collection.name = "CHAR_B04"
    bpy.context.scene.collection.children.link(actor_collection)
    objects = {obj.name: obj for obj in actor_collection.all_objects}
    rig = objects["RIG_LEAD"]
    hand_material = make_material("MAT_B04_HAND", (0.30, 0.055, 0.035, 1.0), 0.42)
    hand_left = make_mesh(actor_collection, "HAND_L", "cube", (0.58, -0.02, 1.10), (0.22, 0.16, 0.12), hand_material)
    hand_right = make_mesh(actor_collection, "HAND_R", "cube", (-0.58, -0.02, 1.10), (0.22, 0.16, 0.12), hand_material)
    bind_mesh(hand_left, rig, "hand.L")
    bind_mesh(hand_right, rig, "hand.R")

    meshes = {
        name: topology_record(objects.get(name) or {"HAND_L": hand_left, "HAND_R": hand_right}[name])
        for name in ("BODY", "HEAD", "EYE_L", "EYE_R", "HAND_L", "HAND_R")
    }
    rest_pose = bone_records(rig)
    shapes = shape_record(objects["HEAD"])
    identity = {
        "restPoseSha256": sha256_value(rest_pose),
        "topologySha256": {name: sha256_value(value) for name, value in sorted(meshes.items())},
        "shapeKeySetSha256": sha256_value(shapes),
        "bones": rest_pose,
        "shapeKeys": [item["name"] for item in shapes],
    }
    identity["identitySha256"] = sha256_value(identity)
    actor_collection["bfs_asset_source"] = "B04_TECHNICAL_CONTACT_ACTOR"
    actor_collection["bfs_generator_version"] = GENERATOR_VERSION
    actor_collection["bfs_identity_sha256"] = identity["identitySha256"]
    bpy.data.libraries.write(str(args.actor_output), {actor_collection}, fake_user=True, compress=True)

    prop_collection = bpy.data.collections.new("PROP_B04")
    prop_material = make_material("MAT_B04_PROP", (0.035, 0.18, 0.24, 1.0), 0.24)
    prop = make_mesh(prop_collection, "PROP_BODY", "cube", (0, 0, 0), (0.24, 0.18, 0.34), prop_material)
    prop["bfs_socket_GRIP_location_m"] = (0.0, 0.0, 0.0)
    prop["bfs_socket_GRIP_rotation_deg"] = (0.0, 0.0, 0.0)
    prop_collection["bfs_asset_source"] = "B04_TECHNICAL_PROP"
    prop_topology_sha = sha256_value(topology_record(prop))
    prop_collection["bfs_topology_sha256"] = prop_topology_sha
    bpy.data.libraries.write(str(args.prop_output), {prop_collection}, fake_user=True, compress=True)

    report = {
        "documentType": "BFS_B04_ASSET_GENERATION",
        "generatorVersion": GENERATOR_VERSION,
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "sourceActor": {"path": str(args.source_actor), "sha256": sha256_file(args.source_actor)},
        "actor": {"path": str(args.actor_output), "sha256": sha256_file(args.actor_output)},
        "prop": {"path": str(args.prop_output), "sha256": sha256_file(args.prop_output), "topologySha256": prop_topology_sha},
        "identity": identity,
        "explicitNonClaims": [
            "The box hands are observability proxies, not anatomical hands.",
            "The generated assets do not yet contain a pickup action or constraint track.",
            "No collision or contact quality has been evaluated by asset generation.",
        ],
    }
    args.report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B04_ASSETS_OK {report['actor']['sha256']} {report['prop']['sha256']} {identity['identitySha256']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B04_ASSETS_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
