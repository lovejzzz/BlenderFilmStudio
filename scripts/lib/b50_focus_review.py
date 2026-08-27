"""Shared response, disclosure and decision rules for B50."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ROOT = ROOT / "experiments/focus-intent-human-review-v0-1"
WORK_ROOT = EXPERIMENT_ROOT / "work"
SPEC_PATH = ROOT / "specs/focus-intent-human-review-spec.v0.1.json"
SPEC_SHA256 = "244d6cc3839bd2923fd85e5069d44d30938bc4b2e8c0a805505c63e2cb789f20"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hash_object(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_private():
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    manifest = json.loads((WORK_ROOT / "evidence/package.manifest.json").read_text(encoding="utf-8"))
    sealed = json.loads((WORK_ROOT / "sealed/mapping.sealed.json").read_text(encoding="utf-8"))
    registry = json.loads((WORK_ROOT / "sealed/sensitive-registry.sealed.json").read_text(encoding="utf-8"))
    return spec, manifest, sealed, registry


def response_body(response):
    return {key: value for key, value in response.items() if key != "responseHash"}


def validate_response(spec, manifest, response):
    if response.get("documentType") != "BFS_B50_BLINDED_RESPONSE" or response.get("version") != spec["version"]:
        return False, "RESPONSE_TYPE"
    if response.get("studySpecSha256") != SPEC_SHA256:
        return False, "SPEC_BINDING"
    if not re.fullmatch(r"[0-9a-f]{64}", str(response.get("responseHash", ""))) or hash_object(response_body(response)) != response.get("responseHash"):
        return False, "RESPONSE_HASH"
    session = next((item for item in manifest["sessions"] if item["sessionId"] == response.get("sessionId")), None)
    if session is None or response.get("mappingCommitment") != session["mappingCommitment"]:
        return False, "SESSION_BINDING"
    expected_images = [{"label": item["label"], "sha256": item["sha256"], "bytes": item["bytes"]} for item in session["imageBindings"]]
    if response.get("imageBindings") != expected_images:
        return False, "IMAGE_BINDING"
    try:
        started = datetime.fromisoformat(response["startedAt"].replace("Z", "+00:00"))
        locked = datetime.fromisoformat(response["lockedAt"].replace("Z", "+00:00"))
        if locked <= started:
            return False, "TIMESTAMPS"
    except Exception:
        return False, "TIMESTAMPS"
    if response.get("primaryChoice") not in spec["observerDesign"]["primaryChoices"]:
        return False, "PRIMARY_CHOICE"
    if response.get("cinematicChoice") not in spec["observerDesign"]["secondaryChoices"]:
        return False, "CINEMATIC_CHOICE"
    attention = response.get("attentionByImage")
    if not isinstance(attention, list) or [item.get("label") for item in attention] != ["IMAGE-A", "IMAGE-B"] or any(item.get("choice") not in spec["observerDesign"]["attentionChoices"] for item in attention):
        return False, "ATTENTION_CHOICES"
    if response.get("confidence") not in spec["observerDesign"]["confidenceChoices"]:
        return False, "CONFIDENCE"
    viewing = response.get("viewing") or {}
    required = ["observerId", "expertise", "directDevelopmentInvolvement", "acuityScreening", "colourVisionScreening", "displayManufacturerModel", "browser", "operatingSystem", "brightnessSetting", "viewingDistance", "ambientLighting"]
    if any(not isinstance(viewing.get(key), str) or not viewing[key].strip() for key in required):
        return False, "VIEWING_RECORD"
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,40}", viewing["observerId"]) or viewing["directDevelopmentInvolvement"] != "NO":
        return False, "OBSERVER_INDEPENDENCE"
    minimum = spec["viewingValidity"]["minimumDisplayNativeResolution"]
    if not isinstance(viewing.get("displayNativeWidth"), int) or viewing["displayNativeWidth"] < minimum[0] or not isinstance(viewing.get("displayNativeHeight"), int) or viewing["displayNativeHeight"] < minimum[1]:
        return False, "DISPLAY_RESOLUTION"
    if viewing.get("browserZoomPercent") != 100 or viewing.get("zoomConfirmed") is not True or viewing.get("cssImageSize") != [960, 540]:
        return False, "DISPLAY_SCALE"
    return True, "OK"


def public_state(registry_values):
    completed = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True)
    tracked = completed.stdout.decode().split("\0")
    paths = [ROOT / item for item in tracked if item]
    out = ROOT / "out"
    if out.exists():
        paths.extend(item for item in out.rglob("*") if item.is_file())
    values = [item.encode("ascii") for item in registry_values]
    records, matches, total = [], [], 0
    for path in sorted(set(paths), key=lambda item: str(item)):
        data = path.read_bytes(); total += len(data)
        relative = str(path.relative_to(ROOT)).replace(os.sep, "/")
        records.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        for value in values:
            if value in data:
                matches.append({"path": relative, "valuePrefix": value[:12].decode()})
    return {"fileCount": len(records), "totalBytes": total, "rootHash": hash_object(records), "matchCount": len(matches), "matches": matches}


def accepted_responses(spec, manifest):
    response_dir = WORK_ROOT / "responses/accepted"
    responses = []
    if not response_dir.exists():
        return responses
    for path in sorted(response_dir.glob("*.json")):
        response = json.loads(path.read_text(encoding="utf-8"))
        valid, reason = validate_response(spec, manifest, response)
        if not valid:
            raise RuntimeError(f"accepted response invalid {path.name}: {reason}")
        responses.append(response)
    return responses


def map_choice(choice, mapping, kind):
    by_label = {item["visibleLabel"]: item["condition"] for item in mapping}
    if choice == "INDISTINGUISHABLE":
        return "INDISTINGUISHABLE"
    if kind == "primary":
        label = "IMAGE-A" if choice == "LEFT_BETTER" else "IMAGE-B"
    else:
        label = "IMAGE-A" if choice == "LEFT_MORE_CINEMATIC" else "IMAGE-B"
    return by_label[label]


def analyze(spec, manifest, sealed, responses):
    if len(responses) != 18:
        raise RuntimeError("formal analysis requires exactly 18 responses")
    mapping_by_session = {item["sessionId"]: item for item in sealed["sessions"]}
    primary = {"FOCUS_NUMERIC_3P2": 0, "FOCUS_OBJECT_CHAIR": 0, "INDISTINGUISHABLE": 0}
    cinematic = {"FOCUS_NUMERIC_3P2": 0, "FOCUS_OBJECT_CHAIR": 0, "INDISTINGUISHABLE": 0}
    attention = {"FOCUS_NUMERIC_3P2": {choice: 0 for choice in spec["observerDesign"]["attentionChoices"]}, "FOCUS_OBJECT_CHAIR": {choice: 0 for choice in spec["observerDesign"]["attentionChoices"]}}
    for response in responses:
        mapping = mapping_by_session[response["sessionId"]]["mapping"]
        primary[map_choice(response["primaryChoice"], mapping, "primary")] += 1
        cinematic[map_choice(response["cinematicChoice"], mapping, "cinematic")] += 1
        by_label = {item["visibleLabel"]: item["condition"] for item in mapping}
        for item in response["attentionByImage"]:
            attention[by_label[item["label"]]][item["choice"]] += 1
    chair_attention = attention["FOCUS_OBJECT_CHAIR"]["CHAIR"]
    original_attention = attention["FOCUS_NUMERIC_3P2"]["CHAIR"]
    if primary["FOCUS_OBJECT_CHAIR"] >= 14 and chair_attention >= 14 and chair_attention >= original_attention:
        decision = spec["formalDecision"]["chairFocusLabel"]
    elif primary["FOCUS_NUMERIC_3P2"] >= 14 and original_attention >= 14 and original_attention >= chair_attention:
        decision = spec["formalDecision"]["originalFocusLabel"]
    elif primary["INDISTINGUISHABLE"] >= 14 and cinematic["INDISTINGUISHABLE"] >= 14 and abs(chair_attention - original_attention) <= 2:
        decision = spec["formalDecision"]["noDifferenceLabel"]
    else:
        decision = spec["formalDecision"]["otherwise"]
    return {"validResponses": 18, "primary": primary, "cinematicSecondary": cinematic, "attention": attention, "decision": decision}
