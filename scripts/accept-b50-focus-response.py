#!/usr/bin/env python3
"""Validate and append one blinded B50 response after a same-state leak audit."""

import argparse
import json
import shutil
from pathlib import Path

from lib.b50_focus_review import WORK_ROOT, accepted_responses, load_private, public_state, validate_response, write_json


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("response", type=Path); args = parser.parse_args()
    spec, manifest, sealed, registry = load_private()
    if (WORK_ROOT / "sealed/collection-close.json").exists():
        raise RuntimeError("collection already closed")
    audit = public_state(registry["values"])
    if audit["matchCount"] != 0:
        raise RuntimeError(f"public-state leak: {audit['matches']}")
    response = json.loads(args.response.read_text(encoding="utf-8"))
    valid, reason = validate_response(spec, manifest, response)
    if not valid:
        raise RuntimeError(f"response rejected: {reason}")
    existing = accepted_responses(spec, manifest)
    if any(item["sessionId"] == response["sessionId"] for item in existing):
        raise RuntimeError("duplicate session")
    observer = response["viewing"]["observerId"]
    if any(item["viewing"]["observerId"] == observer for item in existing):
        raise RuntimeError("duplicate observer")
    target = WORK_ROOT / "responses/accepted" / f"{response['sessionId']}.{response['responseHash']}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.response, target)
    write_json(WORK_ROOT / "responses" / f"preaccept-audit-{response['sessionId']}.json", audit)
    print(f"BFS_B50_RESPONSE_ACCEPTED session={response['sessionId']} count={len(existing)+1}/18 hash={response['responseHash']}")


if __name__ == "__main__": main()
