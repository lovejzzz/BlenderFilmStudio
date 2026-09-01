#!/usr/bin/env python3
"""Run the bounded RC4 accepted-binary development experiment."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC4-development-attempt-04")
EVIDENCE = RESEARCH / "experiments/unstaged-physical-realism/RC4-2026-09-01-development-attempt-04"
PRODUCT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC1-development/source")
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC3-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
TOOL = RESEARCH / "scripts/run-rc4-unstaged-realism-product.py"
SPEC = "specs/fixtures/physics-action/RC4_R1.unstaged-basketball-three-glass-bottles.physics-action-spec.v0.1.json"
MODULE_ROOT = PRODUCT / "scripts/modules"
BASE = "5f595fe3aca7118847aec5b572f6d90a377a4352"
BINARY_SHA = "c071ce0dd63b7c0a1a422c0ade55329e54339b318933564baae1cd4137eb2ca4"
MINIMUM_FREE = 100 * 1024**3
WORK_LIMIT = 4 * 1024**3
EVIDENCE_LIMIT = 256 * 1024**2


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


def run_capture(argv, cwd):
    return subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.strip()


def command(index, name, argv):
    stdout_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stdout.log"
    stderr_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stderr.log"
    environment = dict(os.environ)
    environment.update({
        "BLENDER_USER_CONFIG": str(WORK / "user/config"),
        "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"),
        "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"),
        "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions"),
    })
    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        done = subprocess.run(argv, cwd=RESEARCH, env=environment, stdout=stdout, stderr=stderr, check=False)
    receipt = {
        "index": index,
        "name": name,
        "argv": [str(item) for item in argv],
        "exitCode": done.returncode,
        "wallSeconds": round(time.monotonic() - started, 6),
        "stdoutSha256": sha(stdout_path),
        "stderrSha256": sha(stderr_path),
    }
    receipt["processHash"] = self_hash(receipt, "processHash")
    write(EVIDENCE / "processes" / f"{index:02d}-{name}.json", receipt)
    if done.returncode:
        raise RuntimeError(f"{name} failed; see {stderr_path}")
    return receipt


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("RC4 attempt-04 development roots are not fresh")
    if not BINARY.is_file() or sha(BINARY) != BINARY_SHA:
        raise RuntimeError("accepted binary mismatch")
    if shutil.disk_usage(WORK.parent).free < MINIMUM_FREE:
        raise RuntimeError("free-space reserve")
    allowed = ["scripts/modules/film_studio_physical_look.py", "scripts/modules/film_studio_physics_action.py"]
    status_rows = run_capture(["git", "status", "--porcelain=v1", "--", "scripts/modules"], PRODUCT).splitlines()
    changed = [row.split()[-1] for row in status_rows]
    if sorted(changed) != allowed:
        raise RuntimeError(f"product path scope mismatch: {changed}")
    tracked_numstat = run_capture(["git", "diff", "--numstat", BASE, "--", "scripts/modules/film_studio_physics_action.py"], PRODUCT).splitlines()
    additions = sum(int(row.split()[0]) for row in tracked_numstat) + len((PRODUCT / "scripts/modules/film_studio_physical_look.py").read_text(encoding="utf-8").splitlines())
    deletions = sum(int(row.split()[1]) for row in tracked_numstat)
    if additions > 1400 or deletions > 180:
        raise RuntimeError("product patch ceiling")
    for path in (WORK, EVIDENCE, EVIDENCE / "logs", EVIDENCE / "processes", WORK / "runtime", WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions"):
        path.mkdir(parents=True, exist_ok=False)
    common = [str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode", "--python", str(TOOL), "--"]
    tail = ["--repository-root", str(RESEARCH), "--scene-spec-uri", SPEC, "--evidence-root", str(EVIDENCE), "--work-root", str(WORK / "runtime"), "--module-root", str(MODULE_ROOT)]
    processes = []
    processes.append(command(1, "r1-build", common + ["--action", "build", *tail]))
    blend = WORK / "runtime/RC4_R1_UNSTAGED_PHYSICAL_REALISM.blend"
    if not blend.is_file():
        raise RuntimeError("R1 blend missing")
    opened = [str(BINARY), "--background", "--disable-autoexec", "--offline-mode", str(blend), "--python", str(TOOL), "--"]
    processes.append(command(2, "r1-reopen", opened + ["--action", "reopen", *tail]))
    processes.append(command(3, "d1-h1-regressions", common + ["--action", "regress", *tail]))
    processes.append(command(4, "negative-controls", common + ["--action", "negative", *tail]))
    processes.append(command(5, "r1-render", opened + ["--action", "render", *tail]))

    build = json.loads((EVIDENCE / "R1-build.json").read_text())
    reopen = json.loads((EVIDENCE / "R1-reopen.json").read_text())
    regressions = json.loads((EVIDENCE / "regressions.json").read_text())
    negative = json.loads((EVIDENCE / "negative-controls.json").read_text())
    render = json.loads((EVIDENCE / "render.json").read_text())
    result = build["result"]
    physics = result["physics"]
    archetypes = result["physicalArchetypes"]
    variation = archetypes
    physical = result["physicalLook"]
    ffmpeg = shutil.which("ffmpeg")
    video = None
    if ffmpeg:
        output = EVIDENCE / "contact-clip.mp4"
        subprocess.run([ffmpeg, "-y", "-framerate", "24", "-pattern_type", "glob", "-i", str(EVIDENCE / "clip/frame-*.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        video = {"path": str(output), "sha256": sha(output), "bytes": output.stat().st_size}
    checks = {
        "r1Executed": build["status"] == "PASS" and result["topology"] == "GROUP_RESPONSE",
        "fourActiveBodiesNoConstraints": result["mechanism"]["activeRigidBodyCount"] == 4 and result["mechanism"]["rigidBodyConstraintCount"] == 0,
        "derivedContactAndResponse": physics["contactFrame"] is not None and physics["firstResponseDelayFrames"] <= 2 and physics["respondingTargetCount"] >= 2 and physics["continuousActorMotionThroughContact"],
        "derivedSettleWindow": physics["settledWindowFrameCount"] >= 10 and physics["settledMaximumAggregateAngularStepDegrees"] <= .25 and physics["settledMaximumTargetTranslationStepMeters"] <= .0015,
        "effectUsesSettledFrame": result["cinematography"]["effect"]["frame"] == physics["settledGroupFrame"],
        "solverOwnsOutcomes": result["authority"]["postReleaseTransformKeyframes"] == result["authority"]["authoredOutcomeFields"] == result["authority"]["authoredContactResponsePeakOrFinalFrames"] == result["authority"]["lightAnimationChannels"] == 0,
        "physicalBottleConstruction": physical["bottles"]["preset"] == "HOUSEHOLD_GLASS_WITH_VISIBLE_FILL_AND_VARIATION" and min(row["readableStageCount"] for row in physical["bottles"]["records"]) >= 9 and all(row["visibleBodyIsCollisionHullSource"] for row in archetypes),
        "boundedDeterministicVariation": len(archetypes) == 3 and all(abs(row["yawDegrees"]) <= 4 and abs(row["friction"] - .44) <= .02500001 and abs(row["restitution"] - .11) <= .01500001 for row in archetypes),
        "environmentScaleCues": physical["environment"]["scaleCueCount"] >= 8,
        "nativeMeasuredMotionBlur": result["cinematography"]["motionBlur"]["nativeTransformMotionBlur"] and not result["cinematography"]["motionBlur"]["compositorOrPostprocessBlur"],
        "saveReopenExact": reopen["status"] == "PASS",
        "d1H1Regressions": regressions["status"] == "PASS",
        "negativeControls": negative["status"] == "PASS" and negative["passCount"] == negative["caseCount"],
        "reviewRendersExact": render["status"] == "PASS_RENDER_COMPLETE" and len(render["stills"]) == 3 and render["clip"]["frameCount"] == 48,
        "fixedContactClipCamera": render["clip"]["cameraPolicy"] == "FIXED_CONTACT_CAMERA_WITH_TIMELINE_MARKERS_REMOVED_AFTER_STILLS" and len(render["clip"]["removedTimelineMarkers"]) == 3,
        "productPatchScope": sorted(changed) == allowed and additions <= 1400 and deletions <= 180,
        "boundedCounts": sum(row["counts"]["sceneMutations"] for row in (build, regressions)) == 3 and build["counts"]["blendSaves"] == 1,
    }
    work_bytes, evidence_bytes = size(WORK), size(EVIDENCE)
    checks["resourceCeilings"] = work_bytes <= WORK_LIMIT and evidence_bytes <= EVIDENCE_LIMIT and shutil.disk_usage(WORK.parent).free >= MINIMUM_FREE
    receipt = {
        "schemaVersion": "bfs.rc4UnstagedRealismDevelopmentReceipt.v0.1",
        "status": "PASS_MACHINE_AND_RENDER_COMPLETE_PENDING_DIRECT_VISUAL_REVIEW" if all(checks.values()) else "FAIL",
        "checks": checks,
        "baseline": BASE,
        "binary": {"path": str(BINARY), "sha256": BINARY_SHA},
        "fixture": {"uri": SPEC, "sha256": sha(RESEARCH / SPEC)},
        "productSource": {"branch": run_capture(["git", "branch", "--show-current"], PRODUCT), "changedPaths": changed, "additions": additions, "deletions": deletions, "fileSha256": {path: sha(PRODUCT / path) for path in allowed}},
        "tools": {Path(__file__).name: sha(Path(__file__)), TOOL.name: sha(TOOL)},
        "processes": [{"index": row["index"], "name": row["name"], "processHash": row["processHash"]} for row in processes],
        "counts": {"acceptedBinaryStarts": 5, "sceneMutations": 3, "blendSaves": 1, "reopens": 1, "reviewStills": 3, "contactClipFrames": 48, "networkCalls": 0, "engineRemoteWrites": 0},
        "resources": {"workBytes": work_bytes, "evidenceBytesBeforeReceipt": evidence_bytes, "freeBytesAfter": shutil.disk_usage(WORK.parent).free},
        "video": video,
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write(EVIDENCE / "receipt.json", receipt)
    print("RC4_DEVELOPMENT=" + canonical(receipt))
    if not receipt["status"].startswith("PASS"):
        raise RuntimeError("RC4 development checks failed")


if __name__ == "__main__":
    main()
