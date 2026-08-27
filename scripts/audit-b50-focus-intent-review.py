#!/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13
"""Independent package and disclosure audit for B50."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = ROOT / "experiments/focus-intent-human-review-v0-1"
WORK = EXPERIMENT_ROOT / "work"
SPEC_PATH = ROOT / "specs/focus-intent-human-review-spec.v0.1.json"
SPEC_SHA256 = "244d6cc3839bd2923fd85e5069d44d30938bc4b2e8c0a805505c63e2cb789f20"


def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def hash_object(value): return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value): Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def exr_projection(path):
    first = oiio.ImageBuf(str(path), 0, 0); names = []; combined = None; finite = True
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0); name = str(image.spec().getattribute("oiio:subimagename") or ""); names.append(name)
        pixels = np.asarray(image.get_pixels(oiio.FLOAT), dtype=np.float32); finite = finite and bool(np.isfinite(pixels).all())
        if name.endswith(".Combined"): combined = pixels
    return names, combined, finite


def public_state(values):
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout.decode().split("\0")
    paths = [ROOT / item for item in tracked if item]; out = ROOT / "out"
    if out.exists(): paths.extend(item for item in out.rglob("*") if item.is_file())
    encoded = [value.encode("ascii") for value in values]; records = []; matches = []
    for path in sorted(set(paths), key=lambda item: str(item)):
        data = path.read_bytes(); rel = str(path.relative_to(ROOT)).replace(os.sep, "/")
        records.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        for value in encoded:
            if value in data: matches.append({"path": rel, "valuePrefix": value[:12].decode()})
    return {"fileCount": len(records), "rootHash": hash_object(records), "matchCount": len(matches), "matches": matches}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--require-public-files", action="store_true"); args = parser.parse_args()
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8")); checks = {}
    checks["specIdentity"] = sha256_file(SPEC_PATH) == SPEC_SHA256
    checks["sourceIdentity"] = sha256_file(ROOT / spec["source"]["blendUri"]) == spec["source"]["blendSha256"]
    checks["catalogIdentity"] = sha256_file(ROOT / spec["frozenBrief"]["catalogUri"]) == spec["frozenBrief"]["catalogSha256"]
    checks["ocioIdentity"] = sha256_file(ROOT / spec["runtime"]["ocioUri"]) == spec["runtime"]["ocioSha256"]
    manifest_path = WORK / "evidence/package.manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reports, combined, pngs = {}, {}, {}
    for cell in spec["renderDesign"]["cells"]:
        cell_id = cell["id"]; root = WORK / "conditions" / cell_id; report = json.loads((root / "render.report.json").read_text(encoding="utf-8")); reports[cell_id] = report
        record = manifest["conditions"][cell_id]
        checks[f"{cell_id}.reportHash"] = record["reportSha256"] == sha256_file(root / "render.report.json")
        checks[f"{cell_id}.exrHash"] = record["exr"]["sha256"] == sha256_file(root / "production.exr")
        checks[f"{cell_id}.pngHash"] = record["png"]["sha256"] == sha256_file(root / "review.png")
        roster, pixels, finite = exr_projection(root / "production.exr"); combined[cell_id] = pixels
        checks[f"{cell_id}.exr"] = finite and pixels is not None and len(roster) == 7 and roster == record["exr"]["subimages"]
        image = oiio.ImageBuf(str(root / "review.png")); pngs[cell_id] = np.asarray(image.get_pixels(oiio.UINT8), dtype=np.uint8)
        checks[f"{cell_id}.png"] = image.spec().width == 960 and image.spec().height == 540 and image.spec().nchannels == 3
        checks[f"{cell_id}.camera"] = report["controls"]["camera"]["focusObject"] == cell.get("focusObject") and abs(report["controls"]["camera"]["focusDistanceM"] - spec["focusDerivation"]["originalFocusDistanceM"]) <= 1e-6
        checks[f"{cell_id}.geometry"] = abs(report["geometry"]["chairObjectOriginCameraDepthM"] - spec["focusDerivation"]["chairObjectOriginCameraDepthM"]) <= 2e-5
    original, chair = [cell["id"] for cell in spec["renderDesign"]["cells"]]
    checks["singleVariable"] = all(reports[original]["controls"][key] == reports[chair]["controls"][key] for key in ("bindings", "render", "passes", "frame")) and {**reports[original]["controls"]["camera"], "focusObject": "PROP_CHAIR"} == reports[chair]["controls"]["camera"]
    checks["differentLinear"] = bool(np.any(combined[original][..., :3] != combined[chair][..., :3]))
    checks["differentPng"] = bool(np.any(pngs[original] != pngs[chair]))
    mapping_path = WORK / "sealed/mapping.sealed.json"; sealed = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping_body = {key: value for key, value in sealed.items() if key != "overallCommitment"}
    checks["mappingOverallCommitment"] = hash_object(mapping_body) == sealed["overallCommitment"]
    mapping_by_session = {item["sessionId"]: item for item in sealed["sessions"]}
    session_checks = []; order_counts = {"AB": 0, "BA": 0}
    forbidden = [b"FOCUS_NUMERIC_3P2", b"FOCUS_OBJECT_CHAIR", b"ORIGINAL_COMPILED_FOCUS", b"SEMANTIC_SUBJECT_FOCUS", b"github.com/lovejzzz", b"lovejzzz.github.io", b"/Users/tianxing", b"/repo/"]
    for session in manifest["sessions"]:
        session_id = session["sessionId"]; mapping = mapping_by_session[session_id]
        commitment = hash_object({"sessionId": session_id, "salt": mapping["salt"], "mapping": mapping["mapping"]})
        directory = WORK / "sessions" / session_id
        names = sorted(path.name for path in directory.iterdir()); safe = names == ["IMAGE-A.png", "IMAGE-B.png", "index.html"]
        safe = safe and all(not any(token in path.read_bytes() for token in forbidden) for path in directory.iterdir())
        bindings = {item["label"]: item for item in session["imageBindings"]}
        binding_ok = all(sha256_file(directory / f"{label}.png") == bindings[label]["sha256"] for label in ("IMAGE-A", "IMAGE-B"))
        session_checks.append(commitment == session["mappingCommitment"] == mapping["mappingCommitment"] and safe and binding_ok and sha256_file(directory / "index.html") == session["observerHtmlSha256"])
        order_counts[session["orderClass"]] += 1
    checks["sessions"] = len(session_checks) == 18 and all(session_checks) and order_counts == {"AB": 9, "BA": 9}
    registry = json.loads((WORK / "sealed/sensitive-registry.sealed.json").read_text(encoding="utf-8"))
    checks["registryCommitment"] = hash_object({"salt": registry["salt"], "values": registry["values"]}) == registry["commitment"]
    opening = json.loads((WORK / "sealed/package-opening.sealed.json").read_text(encoding="utf-8"))
    checks["packageCommitment"] = opening["privateManifestSha256"] == sha256_file(manifest_path) and opening["commitment"] == hash_object({"salt": opening["salt"], "privateManifestSha256": opening["privateManifestSha256"]})
    package_audit = json.loads((WORK / "evidence/package.audit.json").read_text(encoding="utf-8"))
    checks["attackRoster"] = package_audit["baseReason"] == "OK" and package_audit["attacksPassed"] == 21 and len(package_audit["attacks"]) == 21 and all(item["passed"] for item in package_audit["attacks"])
    public = public_state(registry["values"]); checks["publicLeak"] = public["matchCount"] == 0
    public_commitment_path = EXPERIMENT_ROOT / "precollection-commitment.json"; public_status_path = EXPERIMENT_ROOT / "package-status.json"
    checks["publicFiles"] = (not args.require_public_files) or (public_commitment_path.exists() and public_status_path.exists())
    if public_commitment_path.exists():
        commitment = json.loads(public_commitment_path.read_text(encoding="utf-8")); checks["publicCommitment"] = commitment["packageCommitment"] == opening["commitment"] and commitment["sensitiveRegistryCommitment"] == registry["commitment"] and commitment["attacksPassed"] == 21 and commitment["validHumanResponses"] == 0
    result = {"schemaVersion": "bfs.focusIntentIndependentAudit.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "publicState": public, "humanResponses": 0, "nonClaim": "package and disclosure audit is not human evidence"}
    write_json(WORK / "evidence/independent.audit.json", result)
    if result["status"] != "PASS": raise RuntimeError(f"independent audit failed: {[key for key,value in checks.items() if not value]}")
    print(f"BFS_B50_INDEPENDENT_AUDIT_PASS checks={len(checks)} publicMatches=0 human=0/18")


if __name__ == "__main__": main()
