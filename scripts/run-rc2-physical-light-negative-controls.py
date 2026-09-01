#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Development negative controls for the RC2 physical-light contract."""

import argparse
import json
import sys
from pathlib import Path

import bpy


parser = argparse.ArgumentParser()
parser.add_argument("--source-root", type=Path, required=True)
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--spec-uri", required=True)
parser.add_argument("--work-root", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

source = args.source_root.resolve(strict=True)
repository = args.repository_root.resolve(strict=True)
work = args.work_root.resolve(strict=True)
evidence = args.evidence_root.resolve(strict=True)
sys.path.insert(0, str(source / "scripts" / "modules"))
import film_studio_physical_light as physical_light


def rejection(call):
    try:
        call()
    except physical_light.PhysicalLightError as error:
        return {"rejected": True, "reason": error.reason, "message": str(error)}
    return {"rejected": False, "reason": None, "message": "unexpected acceptance"}


baseline_objects = sorted(bpy.context.scene.objects.keys())
wrong_token = rejection(lambda: physical_light.execute_physical_light(repository, args.spec_uri, "0" * 64, bpy.context.scene))
after_wrong_token = sorted(bpy.context.scene.objects.keys())

path_escape = rejection(lambda: physical_light.inspect_physical_light(repository, "../START_HERE.md"))

tampered_root = work / "tampered-repository"
tampered_root.mkdir(parents=True, exist_ok=False)
document = json.loads((repository / args.spec_uri).read_text(encoding="utf-8"))
document["unapprovedAuthority"] = "POSE_THE_SHUTTER"
tampered_path = tampered_root / "tampered.json"
tampered_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
tampered = rejection(lambda: physical_light.inspect_physical_light(tampered_root, "tampered.json"))
after_all = sorted(bpy.context.scene.objects.keys())

checks = {
    "wrongTokenRejected": wrong_token["reason"] == "INSPECTION_TOKEN_MISMATCH",
    "wrongTokenSceneUnchanged": after_wrong_token == baseline_objects,
    "pathEscapeRejected": path_escape["reason"] == "PATH_ESCAPE",
    "tamperedSpecRejected": tampered["rejected"],
    "allNegativeControlsSceneUnchanged": after_all == baseline_objects,
}
receipt = {
    "schemaVersion": "bfs.rc2PhysicalLightNegativeControlsDevelopment.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "results": {"wrongToken": wrong_token, "pathEscape": path_escape, "tamperedSpec": tampered},
    "sceneObjectCount": len(baseline_objects),
}
output = evidence / "negative-controls-development.json"
output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("RC2_NEGATIVE_CONTROLS=" + json.dumps(receipt, sort_keys=True, separators=(",", ":")))
if receipt["status"] != "PASS":
    raise SystemExit(1)
