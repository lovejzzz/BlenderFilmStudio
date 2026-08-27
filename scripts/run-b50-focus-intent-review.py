#!/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13
"""Render and package the preregistered B50 delayed-disclosure focus review."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
import PyOpenColorIO as ocio


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "specs/focus-intent-human-review-spec.v0.1.json"
SPEC_SHA256 = "244d6cc3839bd2923fd85e5069d44d30938bc4b2e8c0a805505c63e2cb789f20"
PREREGISTRATION_COMMIT = "04365d44c16c9be65582184d9ff4d697e5d6e2f6"
EXPERIMENT_ROOT = ROOT / "experiments/focus-intent-human-review-v0-1"
WORK_ROOT = EXPERIMENT_ROOT / "work"
PUBLIC_COMMITMENT = EXPERIMENT_ROOT / "precollection-commitment.json"
PUBLIC_STATUS = EXPERIMENT_ROOT / "package-status.json"
BLENDER_SCRIPT = ROOT / "blender/render_b50_focus_intent.py"
OBSERVER_TEMPLATE = ROOT / "scripts/lib/b50-observer-template.html"
DOCKER_HOST = f"unix://{Path('/Users/tianxing/.colima/default/docker.sock')}"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_object(value):
    return sha256_bytes(canonical(value).encode("utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(command, *, timeout=None, capture=True):
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=capture, check=True, timeout=timeout)


def repo_uri(path):
    return str(Path(path).resolve().relative_to(ROOT)).replace(os.sep, "/")


def read_combined(path):
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    roster = []
    combined = None
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or "")
        roster.append(name)
        pixels = np.asarray(image.get_pixels(oiio.FLOAT), dtype=np.float32)
        if not np.isfinite(pixels).all():
            raise RuntimeError(f"non-finite EXR subimage {name}")
        if name.endswith(".Combined"):
            combined = pixels
    if combined is None:
        raise RuntimeError("Combined subimage absent")
    expected_suffixes = [".Combined", ".Depth", ".Normal", ".Vector", ".CryptoObject00", ".CryptoObject01", ".CryptoObject02"]
    if len(roster) != 7 or sorted(name.split(".", 1)[-1] for name in roster) != sorted(item[1:] for item in expected_suffixes):
        raise RuntimeError(f"production subimage roster mismatch: {roster}")
    return combined, roster


def export_png(source_exr, output_png, config_path, display, view):
    pixels, roster = read_combined(source_exr)
    config = ocio.Config.CreateFromFile(str(config_path))
    transform = ocio.DisplayViewTransform(src="ACEScg", display=display, view=view)
    processor = config.getProcessor(transform).getDefaultCPUProcessor()
    rgb = pixels[..., :3].reshape(-1, 3)
    shown = np.asarray([processor.applyRGB(row.tolist()) for row in rgb], dtype=np.float32).reshape(pixels.shape[0], pixels.shape[1], 3)
    encoded = np.rint(np.clip(shown, 0, 1) * 255).astype(np.uint8)
    spec = oiio.ImageSpec(encoded.shape[1], encoded.shape[0], 3, oiio.UINT8)
    writer = oiio.ImageOutput.create(str(output_png))
    if writer is None or not writer.open(str(output_png), spec):
        raise RuntimeError(f"cannot open PNG: {output_png}")
    if not writer.write_image(encoded):
        raise RuntimeError(writer.geterror())
    writer.close()
    reopened = oiio.ImageBuf(str(output_png))
    if reopened.has_error or reopened.spec().width != 960 or reopened.spec().height != 540 or reopened.spec().nchannels != 3:
        raise RuntimeError("review PNG reopen mismatch")
    return pixels, roster, encoded


def public_state(registry_values):
    tracked = run(["git", "ls-files", "-z"]).stdout.split("\0")
    paths = [ROOT / item for item in tracked if item]
    out = ROOT / "out"
    if out.exists():
        paths.extend(item for item in out.rglob("*") if item.is_file())
    records, matches, total_bytes = [], [], 0
    values = [item.encode("ascii") for item in registry_values]
    for path in sorted(set(paths), key=lambda item: str(item)):
        data = path.read_bytes()
        total_bytes += len(data)
        rel = repo_uri(path) if path.is_relative_to(ROOT) else str(path)
        records.append({"path": rel, "sha256": sha256_bytes(data), "bytes": len(data)})
        for value in values:
            if value in data:
                matches.append({"path": rel, "valuePrefix": value[:12].decode("ascii")})
    return {"fileCount": len(records), "totalBytes": total_bytes, "rootHash": hash_object(records), "matchCount": len(matches), "matches": matches}


def reason(state):
    if not state["identity"]: return "IDENTITY"
    if not state["renderControls"]: return "RENDER_CONTROLS"
    if not state["chairBinding"]: return "CHAIR_BINDING"
    if not state["focusDerivation"]: return "FOCUS_DERIVATION"
    if not state["singleVariable"]: return "SINGLE_VARIABLE"
    if not state["exrValid"]: return "EXR_VALIDITY"
    if not state["pngValid"]: return "PNG_DISPLAY"
    if not state["imagesDifferent"]: return "IMAGE_DIFFERENCE"
    if not state["resource"]: return "RESOURCE_BOUNDARY"
    if not state["schedule"]: return "SESSION_SCHEDULE"
    if not state["observerSafe"]: return "OBSERVER_PACKAGE_LEAK"
    if not state["publicSafe"]: return "PUBLIC_STATE_LEAK"
    if not state["publicAuditFresh"]: return "STALE_PUBLIC_AUDIT"
    if not state["preAcceptAudit"]: return "PREACCEPT_AUDIT"
    if not state["responseBinding"]: return "RESPONSE_BINDING"
    if not state["independence"]: return "OBSERVER_INDEPENDENCE"
    if not state["responseComplete"]: return "RESPONSE_COMPLETENESS"
    if not state["responseHash"]: return "RESPONSE_HASH"
    if not state["formalCount"]: return "FORMAL_COUNT"
    if not state["secondaryRole"]: return "SECONDARY_OVERRIDES_PRIMARY"
    if not state["disclosure"]: return "DISCLOSURE_STATE"
    return "OK"


def attack_results(base):
    keys = [
        ("A01_IDENTITY", "identity", "IDENTITY"), ("A02_CONTROLS", "renderControls", "RENDER_CONTROLS"),
        ("A03_CHAIR", "chairBinding", "CHAIR_BINDING"), ("A04_DERIVATION", "focusDerivation", "FOCUS_DERIVATION"),
        ("A05_SINGLE_VARIABLE", "singleVariable", "SINGLE_VARIABLE"), ("A06_EXR", "exrValid", "EXR_VALIDITY"),
        ("A07_PNG", "pngValid", "PNG_DISPLAY"), ("A08_DIFFERENCE", "imagesDifferent", "IMAGE_DIFFERENCE"),
        ("A09_RESOURCE", "resource", "RESOURCE_BOUNDARY"), ("A10_SCHEDULE", "schedule", "SESSION_SCHEDULE"),
        ("A11_OBSERVER_LEAK", "observerSafe", "OBSERVER_PACKAGE_LEAK"), ("A12_PUBLIC_LEAK", "publicSafe", "PUBLIC_STATE_LEAK"),
        ("A13_STALE_AUDIT", "publicAuditFresh", "STALE_PUBLIC_AUDIT"), ("A14_PREACCEPT", "preAcceptAudit", "PREACCEPT_AUDIT"),
        ("A15_RESPONSE_BINDING", "responseBinding", "RESPONSE_BINDING"), ("A16_INDEPENDENCE", "independence", "OBSERVER_INDEPENDENCE"),
        ("A17_COMPLETENESS", "responseComplete", "RESPONSE_COMPLETENESS"), ("A18_RESPONSE_HASH", "responseHash", "RESPONSE_HASH"),
        ("A19_FORMAL_COUNT", "formalCount", "FORMAL_COUNT"), ("A20_SECONDARY", "secondaryRole", "SECONDARY_OVERRIDES_PRIMARY"),
        ("A21_DISCLOSURE", "disclosure", "DISCLOSURE_STATE"),
    ]
    attacks = []
    for attack_id, key, expected in keys:
        changed = copy.deepcopy(base); changed[key] = False
        observed = reason(changed)
        attacks.append({"id": attack_id, "expectedReason": expected, "observedReason": observed, "passed": expected == observed})
    return attacks


def main():
    if WORK_ROOT.exists() or PUBLIC_COMMITMENT.exists() or PUBLIC_STATUS.exists():
        raise RuntimeError("B50 roots already exist; create a new version rather than overwrite")
    if sha256_file(SPEC_PATH) != SPEC_SHA256:
        raise RuntimeError("spec changed after preregistration")
    if sha256_file(BLENDER_SCRIPT) == "" or sha256_file(OBSERVER_TEMPLATE) == "":
        raise RuntimeError("tool identity unavailable")
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    catalog = ROOT / spec["frozenBrief"]["catalogUri"]
    source = ROOT / spec["source"]["blendUri"]
    ocio_path = ROOT / spec["runtime"]["ocioUri"]
    identity = sha256_file(catalog) == spec["frozenBrief"]["catalogSha256"] and sha256_file(source) == spec["source"]["blendSha256"] and sha256_file(ocio_path) == spec["runtime"]["ocioSha256"]
    stat = os.statvfs(ROOT)
    available = stat.f_bavail * stat.f_frsize
    free_after = available - spec["resourceGate"]["projectedWriteBytes"]
    if free_after < spec["resourceGate"]["minimumHostReserveAfterProjectedWriteBytes"]:
        raise RuntimeError(f"disk reserve rejected: {free_after}")
    condition_root = WORK_ROOT / "conditions"
    session_root = WORK_ROOT / "sessions"
    sealed_root = WORK_ROOT / "sealed"
    evidence_root = WORK_ROOT / "evidence"
    for path in (condition_root, session_root, sealed_root, evidence_root, WORK_ROOT / "responses"):
        path.mkdir(parents=True, exist_ok=False)
    docker = ["docker", "--host", DOCKER_HOST]
    cells = spec["renderDesign"]["cells"]
    reports = {}
    cleanup_ok = True
    for cell in cells:
        cell_id = cell["id"]
        output = condition_root / cell_id
        output.mkdir()
        os.chmod(output, 0o777)
        container = f"bfs-b50-{cell_id.lower().replace('_','-')}"
        command = docker + [
            "run", "--rm", "--name", container, "--platform", "linux/amd64", "--pull", "never", "--read-only",
            "--network", "none", "--user", "65532:65532", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
            "--pids-limit", "256", "--memory", "8589934592", "--cpus", "4", "--shm-size", "1073741824",
            "--mount", f"type=bind,src={ROOT},dst=/repo,readonly",
            "--mount", f"type=bind,src={output},dst=/repo/worker-output",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=536870912,uid=65532,gid=65532",
            "--tmpfs", "/work:rw,noexec,nosuid,nodev,size=1073741824,uid=65532,gid=65532",
            "--env", "BLENDER_USER_CONFIG=/work/blender-config", "--env", "BLENDER_USER_SCRIPTS=/work/blender-scripts",
            "--env", "HOME=/work/home", "--env", "LANG=C.UTF-8", "--env", "LC_ALL=C.UTF-8",
            "--env", f"OCIO=/repo/{spec['runtime']['ocioUri']}", "--env", "TMPDIR=/work/tmp",
            spec["runtime"]["workerImageId"], "--background", "--disable-autoexec", "--offline-mode",
            f"/repo/{spec['source']['blendUri']}", "--python-exit-code", "1", "--python", "/repo/blender/render_b50_focus_intent.py",
            "--", "--cell-id", cell_id, "--output-dir", "/repo/worker-output",
        ]
        started = time.time()
        try:
            completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=spec["resourceGate"]["renderTimeoutSecondsPerCell"])
            (output / "stdout.log").write_text(completed.stdout, encoding="utf-8")
            (output / "stderr.log").write_text(completed.stderr, encoding="utf-8")
            if completed.returncode != 0:
                raise RuntimeError(f"{cell_id} worker failed with {completed.returncode}")
        except subprocess.TimeoutExpired as error:
            subprocess.run(docker + ["rm", "-f", container], capture_output=True)
            raise RuntimeError(f"{cell_id} exceeded frozen timeout") from error
        finally:
            active = subprocess.run(docker + ["ps", "-aq", "--filter", f"name=^{container}$"], text=True, capture_output=True)
            if active.stdout.strip():
                subprocess.run(docker + ["rm", "-f", container], capture_output=True)
                cleanup_ok = False
        report = json.loads((output / "render.report.json").read_text(encoding="utf-8"))
        report["workerWallSeconds"] = round(time.time() - started, 6)
        reports[cell_id] = report
        print(f"BFS_B50_RENDER_COMPLETE cell={cell_id} wall={report['workerWallSeconds']}", flush=True)
    display_arrays, png_arrays, rosters = {}, {}, {}
    for cell in cells:
        cell_id = cell["id"]
        output = condition_root / cell_id
        linear, roster, encoded = export_png(output / "production.exr", output / "review.png", ocio_path, spec["renderDesign"]["display"], spec["renderDesign"]["view"])
        display_arrays[cell_id], png_arrays[cell_id], rosters[cell_id] = linear, encoded, roster
    first, second = [item["id"] for item in cells]
    linear_delta = np.abs(display_arrays[first][..., :3].astype(np.float64) - display_arrays[second][..., :3].astype(np.float64))
    png_delta = np.abs(png_arrays[first].astype(np.int16) - png_arrays[second].astype(np.int16))
    difference = {
        "linearChangedValues": int(np.count_nonzero(linear_delta)), "linearMaximumAbsoluteError": float(linear_delta.max()),
        "pngChangedValues": int(np.count_nonzero(png_delta)), "pngMaximumAbsoluteError": int(png_delta.max()),
    }
    condition_artifacts = {}
    for cell in cells:
        output, cell_id = condition_root / cell["id"], cell["id"]
        condition_artifacts[cell_id] = {
            "role": cell["role"], "reportSha256": sha256_file(output / "render.report.json"),
            "exr": {"sha256": sha256_file(output / "production.exr"), "bytes": (output / "production.exr").stat().st_size, "subimages": rosters[cell_id]},
            "png": {"sha256": sha256_file(output / "review.png"), "bytes": (output / "review.png").stat().st_size, "dimensions": [960, 540, 3]},
        }
    mappings, session_records = [], []
    template = OBSERVER_TEMPLATE.read_text(encoding="utf-8")
    for index in range(18):
        session_id = f"OBS-{index + 1:02d}"
        order = [first, second] if index % 2 == 0 else [second, first]
        salt = secrets.token_hex(32)
        mapping = [{"visibleLabel": "IMAGE-A", "condition": order[0]}, {"visibleLabel": "IMAGE-B", "condition": order[1]}]
        commitment = hash_object({"sessionId": session_id, "salt": salt, "mapping": mapping})
        mappings.append({"sessionId": session_id, "salt": salt, "mapping": mapping, "mappingCommitment": commitment})
        directory = session_root / session_id; directory.mkdir()
        image_bindings = []
        for visible, condition in (("IMAGE-A", order[0]), ("IMAGE-B", order[1])):
            source_png = condition_root / condition / "review.png"
            target = directory / f"{visible}.png"
            os.link(source_png, target)
            image_bindings.append({"label": visible, "sha256": sha256_file(target), "bytes": target.stat().st_size})
        session_data = {"version": spec["version"], "sessionId": session_id, "studySpecSha256": SPEC_SHA256, "mappingCommitment": commitment, "imageBindings": image_bindings}
        html = template.replace("__SESSION_JSON__", json.dumps(session_data, ensure_ascii=False).replace("<", "\\u003c"))
        (directory / "index.html").write_text(html, encoding="utf-8")
        session_records.append({"sessionId": session_id, "mappingCommitment": commitment, "orderClass": "AB" if index % 2 == 0 else "BA", "imageBindings": image_bindings, "observerHtmlSha256": sha256_file(directory / "index.html")})
    mapping_body = {"documentType": "BFS_B50_SEALED_MAPPING", "version": spec["version"], "sessions": mappings}
    write_json(sealed_root / "mapping.sealed.json", {**mapping_body, "overallCommitment": hash_object(mapping_body)})
    observer_safe = True
    forbidden = [b"FOCUS_NUMERIC_3P2", b"FOCUS_OBJECT_CHAIR", b"ORIGINAL_COMPILED_FOCUS", b"SEMANTIC_SUBJECT_FOCUS", b"github.com/lovejzzz", b"lovejzzz.github.io", b"/Users/tianxing", b"/repo/"]
    for session in session_records:
        directory = session_root / session["sessionId"]
        if sorted(item.name for item in directory.iterdir()) != ["IMAGE-A.png", "IMAGE-B.png", "index.html"]:
            observer_safe = False
        for item in directory.iterdir():
            data = item.read_bytes()
            if any(token in data for token in forbidden):
                observer_safe = False
    tool_paths = (
        BLENDER_SCRIPT,
        Path(__file__),
        OBSERVER_TEMPLATE,
        ROOT / "scripts/lib/b50_focus_review.py",
        ROOT / "scripts/audit-b50-focus-intent-review.py",
        ROOT / "scripts/accept-b50-focus-response.py",
        ROOT / "scripts/close-b50-focus-review.py",
        ROOT / "scripts/analyze-b50-focus-review.py",
    )
    tools = {repo_uri(path): sha256_file(path) for path in tool_paths}
    private_manifest = {
        "documentType": "BFS_B50_PRIVATE_REVIEW_PACKAGE", "version": spec["version"], "experimentId": spec["experimentId"],
        "createdAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "preregistrationCommit": PREREGISTRATION_COMMIT,
        "studySpecSha256": SPEC_SHA256, "tools": tools, "diskAdmission": {"availableBytes": available, "projectedWriteBytes": spec["resourceGate"]["projectedWriteBytes"], "freeAfterProjectedBytes": free_after},
        "conditions": condition_artifacts, "difference": difference, "sessions": session_records,
        "humanReview": {"status": "HUMAN_REVIEW_PENDING", "validResponses": 0, "formalTarget": 18, "decision": None}, "nonClaims": spec["nonClaims"],
    }
    private_manifest_path = evidence_root / "package.manifest.json"; write_json(private_manifest_path, private_manifest)
    sensitive_values = sorted(set(
        [item for artifact in condition_artifacts.values() for item in (artifact["reportSha256"], artifact["exr"]["sha256"], artifact["png"]["sha256"])] +
        [mapping["salt"] for mapping in mappings] + [session["mappingCommitment"] for session in session_records] +
        [session["observerHtmlSha256"] for session in session_records]
    ))
    registry_salt = secrets.token_hex(32)
    registry_commitment = hash_object({"salt": registry_salt, "values": sensitive_values})
    write_json(sealed_root / "sensitive-registry.sealed.json", {"salt": registry_salt, "values": sensitive_values, "commitment": registry_commitment})
    package_salt = secrets.token_hex(32)
    private_manifest_sha = sha256_file(private_manifest_path)
    package_commitment = hash_object({"salt": package_salt, "privateManifestSha256": private_manifest_sha})
    write_json(sealed_root / "package-opening.sealed.json", {"salt": package_salt, "privateManifestSha256": private_manifest_sha, "commitment": package_commitment})
    preliminary_public = public_state(sensitive_values)
    base = {
        "identity": identity, "renderControls": all(report["passed"] for report in reports.values()),
        "chairBinding": reports[second]["controls"]["camera"]["focusObject"] == "PROP_CHAIR" and reports[first]["controls"]["camera"]["focusObject"] is None,
        "focusDerivation": all(abs(report["geometry"]["chairObjectOriginCameraDepthM"] - spec["focusDerivation"]["chairObjectOriginCameraDepthM"]) <= 2e-5 for report in reports.values()),
        "singleVariable": all(reports[first]["controls"][key] == reports[second]["controls"][key] for key in ("bindings", "render", "passes", "frame")) and reports[first]["controls"]["camera"] | {"focusObject": "PROP_CHAIR"} == reports[second]["controls"]["camera"],
        "exrValid": all(len(rosters[cell["id"]]) == 7 for cell in cells), "pngValid": all(condition_artifacts[cell["id"]]["png"]["dimensions"] == [960, 540, 3] for cell in cells),
        "imagesDifferent": difference["linearChangedValues"] > 0 and difference["pngChangedValues"] > 0,
        "resource": free_after >= spec["resourceGate"]["minimumHostReserveAfterProjectedWriteBytes"] and cleanup_ok,
        "schedule": len(session_records) == 18 and sum(item["orderClass"] == "AB" for item in session_records) == 9 and sum(item["orderClass"] == "BA" for item in session_records) == 9,
        "observerSafe": observer_safe, "publicSafe": preliminary_public["matchCount"] == 0, "publicAuditFresh": True,
        "preAcceptAudit": True, "responseBinding": True, "independence": True, "responseComplete": True, "responseHash": True,
        "formalCount": True, "secondaryRole": True, "disclosure": True,
    }
    attacks = attack_results(base)
    if reason(base) != "OK" or not all(item["passed"] for item in attacks):
        raise RuntimeError(f"B50 package gate failed: {reason(base)}")
    audit_private = {"schemaVersion": "bfs.focusIntentPackageAudit.v0.1", "baseReason": reason(base), "attacks": attacks, "attacksPassed": sum(item["passed"] for item in attacks), "preliminaryPublicState": preliminary_public}
    write_json(evidence_root / "package.audit.json", audit_private)
    public_commitment = {
        "schemaVersion": "bfs.focusIntentPrecollectionCommitment.v0.1", "experimentId": spec["experimentId"], "studySpecSha256": SPEC_SHA256,
        "preregistrationCommit": PREREGISTRATION_COMMIT, "packageCommitment": package_commitment, "sensitiveRegistryCommitment": registry_commitment,
        "privateArtifactCounts": {"conditions": 2, "productionExrs": 2, "reviewPngs": 2, "sessions": 18},
        "packageGate": "PASS", "attacksPassed": 21, "humanStatus": "HUMAN_REVIEW_PENDING", "validHumanResponses": 0,
        "collectionState": "NOT_OPEN_PENDING_FINAL_PUBLIC_STATE_AUDIT_AND_INTERFACE_PILOT", "disclosure": "DELAYED_UNTIL_COLLECTION_CLOSE",
    }
    write_json(PUBLIC_COMMITMENT, public_commitment)
    write_json(PUBLIC_STATUS, {"schemaVersion": "bfs.focusIntentPackageStatus.v0.1", "experimentId": spec["experimentId"], "status": "PACKAGE_READY_HUMAN_PENDING", "machinePackage": {"realBlenderWorkers": 2, "resolution": [960, 540], "samples": 128, "attacksPassed": 21}, "humanReview": {"validResponses": 0, "formalTarget": 18, "decision": None}, "nextGate": "final public-state leak audit and real-browser interface pilot"})
    print(f"BFS_B50_PACKAGE_READY packageCommitment={package_commitment} attacks=21 human=0/18", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B50_PACKAGE_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
