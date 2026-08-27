#!/usr/bin/env python3
"""Irreversibly close the B50 collection after the complete balanced response set."""

import json
import time

from lib.b50_focus_review import WORK_ROOT, accepted_responses, hash_object, load_private, public_state, write_json


def main():
    spec, manifest, sealed, registry = load_private()
    close_path = WORK_ROOT / "sealed/collection-close.json"
    if close_path.exists(): raise RuntimeError("collection already closed")
    audit = public_state(registry["values"])
    if audit["matchCount"] != 0: raise RuntimeError("public-state leak prevents close")
    responses = accepted_responses(spec, manifest)
    if len(responses) != 18: raise RuntimeError(f"requires 18 valid responses, found {len(responses)}")
    if len({item["sessionId"] for item in responses}) != 18 or len({item["viewing"]["observerId"] for item in responses}) != 18: raise RuntimeError("response independence failure")
    order_by_session = {item["sessionId"]: item["orderClass"] for item in manifest["sessions"]}
    counts = {kind: sum(order_by_session[item["sessionId"]] == kind for item in responses) for kind in ("AB", "BA")}
    if counts != {"AB": 9, "BA": 9}: raise RuntimeError(f"unbalanced schedule: {counts}")
    body = {"documentType": "BFS_B50_COLLECTION_CLOSE", "version": spec["version"], "closedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "validResponses": 18, "orderCounts": counts, "responseHashes": sorted(item["responseHash"] for item in responses), "finalPublicStateAudit": audit, "state": "CLOSED_CANNOT_REOPEN"}
    write_json(close_path, {**body, "closeHash": hash_object(body)})
    print("BFS_B50_COLLECTION_CLOSED responses=18 AB=9 BA=9")


if __name__ == "__main__": main()
