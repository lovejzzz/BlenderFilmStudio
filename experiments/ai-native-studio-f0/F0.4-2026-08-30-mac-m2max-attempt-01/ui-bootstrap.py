# SPDX-License-Identifier: GPL-2.0-or-later
"""Load the frozen B01 proposal into the Film Studio UI without executing it."""

import argparse
import json
import os
import sys
from pathlib import Path

import bpy


parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", required=True)
parser.add_argument("--evidence-root", required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
root = Path(args.repository_root).resolve(strict=True)
evidence = (root / args.evidence_root).resolve(strict=True)
state = bpy.context.scene.film_studio
state.contract_repository_root = str(root)
state.contract_proposal_uri = f"{args.evidence_root}/proposals/B01.proposal.json"
state.contract_approval_uri = f"{args.evidence_root}/approvals/B01.approval.json"
result = bpy.ops.film_studio.inspect_contract()
if "FINISHED" not in result or state.contract_status != "APPROVED_READY" or not state.contract_inspection_token:
    raise RuntimeError(f"UI inspection failed: {result} {state.contract_status}")
record = {
    "schemaVersion": "bfs.f0.4.uiInspection.v0.1",
    "status": state.contract_status,
    "proposalId": state.contract_proposal_id,
    "diff": state.contract_diff_summary,
    "approvalScope": state.contract_approval_scope,
    "outputUri": state.contract_output_uri,
    "planHash": state.contract_plan_hash,
    "executeEnabled": True,
    "executed": False,
    "outputExists": (root / state.contract_output_uri).exists(),
    "formalProductStart": 1,
}
path = evidence / "runtime-ui/inspection.json"
descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
try:
    os.write(descriptor, (json.dumps(record, indent=2) + "\n").encode())
    os.fsync(descriptor)
finally:
    os.close(descriptor)
print("F04_UI_READY APPROVED_READY EXECUTE_ENABLED NOT_EXECUTED")
