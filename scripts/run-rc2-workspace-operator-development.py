#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise RC2 through the Film Studio workspace inspect/execute route."""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bpy


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class Reporter:
    def __init__(self):
        self.messages = []

    def report(self, categories, message):
        self.messages.append({"categories": sorted(categories), "message": message})


parser = argparse.ArgumentParser()
parser.add_argument("--source-root", type=Path, required=True)
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--spec-uri", required=True)
parser.add_argument("--expected-kind", choices=("physical-light", "physical-performance"), default="physical-light")
parser.add_argument("--work-root", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

source = args.source_root.resolve(strict=True)
repository = args.repository_root.resolve(strict=True)
work = args.work_root.resolve(strict=True)
evidence = args.evidence_root.resolve(strict=True)
sys.path.insert(0, str(source / "scripts" / "modules"))

operator_path = source / "scripts" / "startup" / "bl_operators" / "film_studio_workspace.py"
module_spec = importlib.util.spec_from_file_location("film_studio_workspace_rc2_development", operator_path)
workspace = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(workspace)

state = bpy.context.scene.film_studio
state.causal_repository_root = str(repository)
state.causal_scene_spec_uri = args.spec_uri
reporter = Reporter()
inspect_return = workspace.FILMSTUDIO_OT_inspect_causal_scene.execute(reporter, bpy.context)
inspect_snapshot = {
    "return": sorted(inspect_return),
    "status": state.causal_status,
    "sceneId": state.causal_scene_id,
    "sceneSpecHash": state.causal_scene_spec_hash,
    "targetCount": state.causal_target_count,
    "inspectionTokenPresent": bool(state.causal_inspection_token),
}
execute_return = workspace.FILMSTUDIO_OT_execute_causal_scene.execute(reporter, bpy.context)
result_property = "film_studio_physical_light_result" if args.expected_kind == "physical-light" else "film_studio_physical_performance_result"
expected_schema = "bfs.physicalLightResult.v0.1" if args.expected_kind == "physical-light" else "bfs.physicalPerformanceResult.v0.1"
expected_summary_fragment = "reveal geometry-owned" if args.expected_kind == "physical-light" else "peak"
result = json.loads(bpy.context.scene[result_property])
execute_snapshot = {
    "return": sorted(execute_return),
    "status": state.causal_status,
    "resultSummary": state.causal_result_summary,
    "inspectionTokenCleared": state.causal_inspection_token == "",
    "productResultHash": result["resultHash"],
}

bpy.context.preferences.filepaths.file_preview_type = "NONE"
blend = work / "RC2_WORKSPACE_ROUTE.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
checks = {
    "inspectFinished": inspect_return == {"FINISHED"},
    "inspectApproved": inspect_snapshot["status"] == "APPROVED_READY",
    "inspectionTokenPresent": inspect_snapshot["inspectionTokenPresent"],
    "executeFinished": execute_return == {"FINISHED"},
    "executeStatus": execute_snapshot["status"] == "PASS_EXECUTED",
    "inspectionTokenCleared": execute_snapshot["inspectionTokenCleared"],
    "expectedResultStored": result["schemaVersion"] == expected_schema,
    "expectedSummary": expected_summary_fragment in execute_snapshot["resultSummary"],
}
receipt = {
    "schemaVersion": "bfs.rc2WorkspaceOperatorDevelopment.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "operatorSource": {"path": str(operator_path), "sha256": sha256_file(operator_path)},
    "inspect": inspect_snapshot,
    "execute": execute_snapshot,
    "checks": checks,
    "reports": reporter.messages,
    "blend": {"path": str(blend), "bytes": blend.stat().st_size, "sha256": sha256_file(blend)},
}
output = evidence / "workspace-operator-development.json"
output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("RC2_WORKSPACE_OPERATOR=" + json.dumps(receipt, sort_keys=True, separators=(",", ":")))
if receipt["status"] != "PASS":
    raise SystemExit(1)
