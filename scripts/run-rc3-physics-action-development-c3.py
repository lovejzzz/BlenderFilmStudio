#!/usr/bin/env python3
"""Run the bounded accepted-binary RC3 zero-render development pass."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC3-development-attempt-03")
EVIDENCE = RESEARCH / "experiments/physics-native-action/RC3-2026-09-01-development-attempt-03"
PRODUCT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC1-development/source")
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC2-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
MODULE_ROOT = PRODUCT / "scripts/modules"
TOOL = RESEARCH / "scripts/run-rc3-physics-action-product-c3.py"
D1 = "specs/fixtures/physics-action/RC3_D1.signal-gate.physics-action-spec.v0.3.json"
H1 = "specs/fixtures/physics-action/RC3_H1.ball-three-bottles.physics-action-spec.v0.2.json"
MINIMUM_FREE = 100 * 1024**3
WORK_LIMIT = 2 * 1024**3
EVIDENCE_LIMIT = 64 * 1024**2


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def size(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def command(index, name, argv):
    stdout_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stdout.log"
    stderr_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stderr.log"
    started = time.monotonic()
    env = dict(os.environ)
    env.update({"BLENDER_USER_CONFIG": str(WORK / "user/config"), "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"), "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"), "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions")})
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        done = subprocess.run(argv, cwd=RESEARCH, env=env, stdout=stdout, stderr=stderr, check=False)
    receipt = {"index": index, "name": name, "argv": [str(item) for item in argv], "exitCode": done.returncode, "wallSeconds": round(time.monotonic() - started, 6), "stdoutSha256": sha(stdout_path), "stderrSha256": sha(stderr_path)}
    receipt["processHash"] = self_hash(receipt, "processHash")
    write(EVIDENCE / "processes" / f"{index:02d}-{name}.json", receipt)
    if done.returncode:
        raise RuntimeError(f"{name} failed; see {stderr_path}")
    return receipt


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("development roots are not fresh")
    if not BINARY.is_file() or sha(BINARY) != "9e24e64976e5747a415bff3633907c1612871b6220917621fbadebfa04005efb":
        raise RuntimeError("accepted binary mismatch")
    if shutil.disk_usage(WORK.parent).free < MINIMUM_FREE:
        raise RuntimeError("free-space reserve")
    for path in (WORK, EVIDENCE, EVIDENCE / "logs", EVIDENCE / "processes", WORK / "runtime", WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions"):
        path.mkdir(parents=True, exist_ok=False)
    common = [str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode", "--python", str(TOOL), "--"]
    processes = []
    for index, case, spec in ((1, "D1", D1), (3, "H1", H1)):
        processes.append(command(index, f"{case.lower()}-build", common + ["--action", "build", "--case", case, "--repository-root", str(RESEARCH), "--scene-spec-uri", spec, "--evidence-root", str(EVIDENCE), "--work-root", str(WORK / "runtime"), "--module-root", str(MODULE_ROOT)]))
        blend = WORK / "runtime" / f"RC3_{case}_PHYSICS_ACTION.blend"
        if not (EVIDENCE / f"{case}-build.json").is_file() or not blend.is_file():
            raise RuntimeError(f"{case} build process returned without required artifacts")
        processes.append(command(index + 1, f"{case.lower()}-reopen", [str(BINARY), "--background", "--disable-autoexec", "--offline-mode", str(blend), "--python", str(TOOL), "--", "--action", "reopen", "--case", case, "--repository-root", str(RESEARCH), "--scene-spec-uri", spec, "--evidence-root", str(EVIDENCE), "--work-root", str(WORK / "runtime"), "--module-root", str(MODULE_ROOT)]))
        if not (EVIDENCE / f"{case}-reopen.json").is_file():
            raise RuntimeError(f"{case} reopen process returned without required artifact")
    processes.append(command(5, "negative-controls", common + ["--action", "negative", "--case", "D1", "--repository-root", str(RESEARCH), "--scene-spec-uri", D1, "--evidence-root", str(EVIDENCE), "--work-root", str(WORK / "runtime"), "--module-root", str(MODULE_ROOT)]))
    if not (EVIDENCE / "negative-controls.json").is_file():
        raise RuntimeError("negative-control process returned without required artifact")
    builds = [json.loads((EVIDENCE / f"{case}-build.json").read_text()) for case in ("D1", "H1")]
    reopens = [json.loads((EVIDENCE / f"{case}-reopen.json").read_text()) for case in ("D1", "H1")]
    negative = json.loads((EVIDENCE / "negative-controls.json").read_text())
    work_bytes, evidence_bytes = size(WORK), size(EVIDENCE)
    checks = {
        "twoSameCompilerExecutions": len({row["result"]["contractVersion"] for row in builds}) == 1 and len({row["result"]["compiledGraph"]["nodes"][0].get("compiler", "same-module") for row in builds}) == 1,
        "d1HingeTopology": builds[0]["result"]["topology"] == "HINGE_LIGHT" and builds[0]["result"]["mechanism"]["activeRigidBodyCount"] == 2 and builds[0]["result"]["mechanism"]["rigidBodyConstraintCount"] == 1,
        "d1DerivedResponse": builds[0]["result"]["physics"]["contactFrame"] is not None and builds[0]["result"]["physics"]["firstResponseDelayFrames"] <= 2,
        "h1GroupTopology": builds[1]["result"]["topology"] == "GROUP_RESPONSE" and builds[1]["result"]["mechanism"]["activeRigidBodyCount"] == 4 and builds[1]["result"]["mechanism"]["rigidBodyConstraintCount"] == 0,
        "h1DerivedResponse": builds[1]["result"]["physics"]["respondingTargetCount"] >= 2 and builds[1]["result"]["physics"]["firstResponseDelayFrames"] <= 2 and builds[1]["result"]["physics"]["continuousActorMotionThroughContact"],
        "solverAuthority": all(row["result"]["authority"]["postReleaseTransformKeyframes"] == row["result"]["authority"]["authoredOutcomeFields"] == row["result"]["authority"]["lightAnimationChannels"] == 0 for row in builds),
        "nativeMeasuredBlur": all(row["result"]["cinematography"]["motionBlur"]["nativeTransformMotionBlur"] and not row["result"]["cinematography"]["motionBlur"]["compositorOrPostprocessBlur"] for row in builds),
        "reopenExact": all(row["status"] == "PASS" for row in reopens),
        "negativeControls": negative["status"] == "PASS" and negative["passCount"] == 16,
        "zeroRenders": all(row["counts"]["renders"] == 0 for row in builds) and negative["renders"] == 0,
        "resourceCeilings": work_bytes <= WORK_LIMIT and evidence_bytes <= EVIDENCE_LIMIT and shutil.disk_usage(WORK.parent).free >= MINIMUM_FREE,
    }
    receipt = {"schemaVersion": "bfs.rc3PhysicsActionDevelopmentReceipt.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "productSource": {"branch": "codex/rc3-physics-action-grammar", "baseCommit": "636f42f28f781f3e858fd5b6bf641910a549c91b", "moduleSha256": sha(PRODUCT / "scripts/modules/film_studio_physics_action.py"), "operatorSha256": sha(PRODUCT / "scripts/startup/bl_operators/film_studio_workspace.py")}, "tools": {Path(__file__).name: sha(Path(__file__)), TOOL.name: sha(TOOL)}, "processes": [{"index": row["index"], "name": row["name"], "processHash": row["processHash"]} for row in processes], "counts": {"acceptedBinaryStarts": 5, "sceneMutatingExecutions": 2, "blendSaves": 2, "reopens": 2, "renders": 0, "networkCalls": 0, "engineRemoteWrites": 0}, "resources": {"workBytes": work_bytes, "evidenceBytes": evidence_bytes, "freeBytesAfter": shutil.disk_usage(WORK.parent).free}}
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write(EVIDENCE / "receipt.json", receipt)
    print("RC3_DEVELOPMENT=" + canonical(receipt))
    if receipt["status"] != "PASS":
        raise RuntimeError("RC3 development checks failed")


if __name__ == "__main__":
    main()
