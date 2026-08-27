#!/usr/bin/env python3
"""Unblind and analyze B50 only after the durable close record exists."""

import json

from lib.b50_focus_review import WORK_ROOT, accepted_responses, analyze, hash_object, load_private, write_json


def main():
    spec, manifest, sealed, registry = load_private()
    close_path = WORK_ROOT / "sealed/collection-close.json"
    if not close_path.exists(): raise RuntimeError("collection is not closed")
    close = json.loads(close_path.read_text(encoding="utf-8"))
    if close.get("state") != "CLOSED_CANNOT_REOPEN": raise RuntimeError("invalid close state")
    responses = accepted_responses(spec, manifest)
    result = analyze(spec, manifest, sealed, responses)
    body = {"schemaVersion": "bfs.focusIntentHumanResult.v0.1", "experimentId": spec["experimentId"], "closeHash": close["closeHash"], **result, "nonClaims": spec["nonClaims"]}
    write_json(WORK_ROOT / "evidence/human-result.json", {**body, "resultHash": hash_object(body)})
    print(f"BFS_B50_HUMAN_RESULT decision={result['decision']} responses=18")


if __name__ == "__main__": main()
