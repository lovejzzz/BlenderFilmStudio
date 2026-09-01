#!/usr/bin/env python3
"""Fresh clean-build formal validation for the RC5 breakable attachment."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC5-2026-09-01-attempt-01"
PRODUCT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC1-development/source")
COMMIT = "8e18c82548f8716c415e6e1b69fdbbdeef1f1900"
PARENT = "db662438edfef0a1979d8227c8b58cf8620e2b74"
DEPENDENCIES = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.6-2026-08-31-mac-m2max-attempt-01/source/lib/macos_arm64")
LFS_OBJECTS = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC9-2026-09-01-attempt-01/source/.git/lfs/objects")
PRODUCT_TOOL = RESEARCH / "scripts/run-rc5-breakable-attachment-product.py"
SPEC = "specs/fixtures/physics-action/RC5_B1.basketball-three-bottles-breakaway-cap.physics-action-spec.v0.7.json"
MINIMUM_FREE_BEFORE = 160 * 1024**3
MINIMUM_RESERVE = 100 * 1024**3
PROJECTED_WRITES = 8 * 1024**3
WORK_LIMIT = 64 * 1024**3
EVIDENCE_LIMIT = 1024 * 1024**2


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


def output(argv, cwd=None):
    return subprocess.check_output(argv, cwd=cwd, text=True).strip()


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def command(index, name, argv, cwd=None):
    stdout_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stdout.log"
    stderr_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stderr.log"
    environment = dict(os.environ)
    environment.update({
        "BLENDER_USER_CONFIG": str(WORK / "user/config"),
        "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"),
        "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"),
        "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions"),
        "GIT_LFS_SKIP_SMUDGE": "1",
        "GIT_TERMINAL_PROMPT": "0",
    })
    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        done = subprocess.run(argv, cwd=cwd or RESEARCH, env=environment, stdout=stdout, stderr=stderr, check=False)
    row = {
        "index": index,
        "name": name,
        "argv": [str(item) for item in argv],
        "cwd": str(cwd or RESEARCH),
        "exitCode": done.returncode,
        "wallSeconds": round(time.monotonic() - started, 6),
        "stdoutSha256": sha(stdout_path),
        "stderrSha256": sha(stderr_path),
    }
    row["processHash"] = self_hash(row, "processHash")
    write(EVIDENCE / "processes" / f"{index:02d}-{name}.json", row)
    if done.returncode:
        raise RuntimeError(f"{name} failed; see {stderr_path}")
    return row


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("RC5 formal roots are not fresh")
    if output(["git", "rev-parse", "HEAD"], PRODUCT) != COMMIT or output(["git", "status", "--porcelain"], PRODUCT):
        raise RuntimeError("RC5 candidate source identity mismatch")
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < MINIMUM_FREE_BEFORE or free_before < MINIMUM_RESERVE + PROJECTED_WRITES:
        raise RuntimeError("RC5 formal resource admission failed")
    if not DEPENDENCIES.is_dir() or not LFS_OBJECTS.is_dir():
        raise RuntimeError("exact local dependency or LFS object root missing")
    for root in (WORK, EVIDENCE):
        root.mkdir(parents=True, exist_ok=False)
    for root in (EVIDENCE / "logs", EVIDENCE / "processes", WORK / "runtime", WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions"):
        root.mkdir(parents=True, exist_ok=False)
    admission = {
        "schemaVersion": "bfs.rc5BreakableAttachmentFormalAdmission.v0.1",
        "status": "PASS",
        "freeBytesBefore": free_before,
        "minimumFreeBeforeBytes": MINIMUM_FREE_BEFORE,
        "minimumReserveBytes": MINIMUM_RESERVE,
        "projectedWriteBytes": PROJECTED_WRITES,
        "workLimitBytes": WORK_LIMIT,
        "evidenceLimitBytes": EVIDENCE_LIMIT,
    }
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write(EVIDENCE / "admission.json", admission)

    source, build, runtime = WORK / "source", WORK / "build", WORK / "runtime"
    processes = []
    processes.append(command(1, "local-clone", ["git", "clone", "--local", "--no-hardlinks", "--no-checkout", str(PRODUCT), str(source)]))
    lfs = source / ".git/lfs"
    lfs.mkdir(parents=True, exist_ok=True)
    objects = lfs / "objects"
    if objects.exists() and not objects.is_symlink():
        objects.rmdir()
    objects.symlink_to(LFS_OBJECTS, target_is_directory=True)
    processes.append(command(2, "checkout", ["git", "checkout", "--detach", COMMIT], cwd=source))
    processes.append(command(3, "lfs-checkout", ["git", "lfs", "checkout"], cwd=source))
    if output(["git", "rev-parse", "HEAD"], source) != COMMIT or output(["git", "status", "--porcelain"], source):
        raise RuntimeError("formal source identity mismatch")
    processes.append(command(4, "clean-native-build", ["/usr/bin/make", "-s", f"BUILD_DIR={build}", f"BUILD_CMAKE_ARGS=-DLIBDIR={DEPENDENCIES}", "-j", "12", "release"], cwd=source))

    built = build / "bin/Blender.app"
    bundle = build / "bin/Film Studio Engine F0.app"
    if not built.is_dir() or bundle.exists():
        raise RuntimeError("formal bundle rename precondition failed")
    built.rename(bundle)
    binary = bundle / "Contents/MacOS/Blender"
    module_root = bundle / "Contents/Resources/5.2/scripts/modules"
    operator = bundle / "Contents/Resources/5.2/scripts/startup/bl_operators/film_studio_workspace.py"
    installed = {
        "physicsAction": module_root / "film_studio_physics_action.py",
        "physicalLook": module_root / "film_studio_physical_look.py",
        "causal": module_root / "film_studio_causal.py",
        "physicalLight": module_root / "film_studio_physical_light.py",
        "physicalPerformance": module_root / "film_studio_physical_performance.py",
    }
    expected_installed = {
        "physicsAction": "45df1732894c1b28a4dd92f7463347812e86ff03c7de912363ee78409aa158ad",
        "physicalLook": "0bb4704989bc9a005fbe4a0e62d0dfb83d5f8cc1a433d73da3b697dba7840afc",
        "causal": "b45c86d301b509898d05a897f38599d80ca20285c54919eb003719d4439ff6f2",
        "physicalLight": "669da32a3616db76cbe015c5055d1c78d758ee5f7753d011e51ec2382529972f",
        "physicalPerformance": "babf705beb1648393e5de3af4714e2cf56f39fbbd2eb31d28497ed2e8148a953",
    }
    installed_hashes = {name: sha(path) for name, path in installed.items()}
    if installed_hashes != expected_installed or sha(operator) != "37ee599a287a2938d0fb5d8f0dfecb49ce258c3349bf48cb6e319401fc84f2ce":
        raise RuntimeError("formal installed product hash mismatch")

    common = [str(binary), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode", "--python", str(PRODUCT_TOOL), "--"]
    tail = ["--repository-root", str(RESEARCH), "--scene-spec-uri", SPEC, "--evidence-root", str(EVIDENCE), "--work-root", str(runtime), "--module-root", str(module_root)]
    processes.append(command(5, "b1-build", common + ["--action", "build", *tail]))
    blend = runtime / "RC5_B1_BREAKABLE_ATTACHMENT.blend"
    opened = [str(binary), "--background", "--disable-autoexec", "--offline-mode", str(blend), "--python", str(PRODUCT_TOOL), "--"]
    processes.append(command(6, "b1-reopen", opened + ["--action", "reopen", *tail]))
    processes.append(command(7, "rc4-d1-h1-regression-negative", common + ["--action", "regress-negative", *tail]))
    processes.append(command(8, "b1-render", opened + ["--action", "render", *tail]))
    video = EVIDENCE / "contact-clip.mp4"
    processes.append(command(9, "contact-video", ["/opt/homebrew/bin/ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "24", "-pattern_type", "glob", "-i", str(EVIDENCE / "clip/frame-*.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)]))

    build_row = json.loads((EVIDENCE / "B1-build.json").read_text())
    reopen = json.loads((EVIDENCE / "B1-reopen.json").read_text())
    regression = json.loads((EVIDENCE / "regression-negative.json").read_text())
    render = json.loads((EVIDENCE / "render.json").read_text())
    result, physics = build_row["result"], build_row["result"]["physics"]
    changed = output(["git", "diff", "--numstat", PARENT, COMMIT, "--", "scripts/modules/film_studio_physics_action.py"], source).splitlines()
    work_bytes, evidence_bytes = tree_bytes(WORK), tree_bytes(EVIDENCE)
    checks = {
        "sourceIdentity": output(["git", "rev-parse", "HEAD"], source) == COMMIT and not output(["git", "status", "--porcelain"], source),
        "sourceScope": changed == ["322\t19\tscripts/modules/film_studio_physics_action.py"],
        "installedHashes": installed_hashes == expected_installed,
        "buildTwentyOfTwenty": build_row["status"] == "PASS" and build_row["passCount"] == build_row["checkCount"] == 20,
        "nativeBreakableConstraint": result["mechanism"]["breakableFixedConstraintCount"] == result["mechanism"]["rigidBodyConstraintCount"] == 1 and physics["breakableAttachment"]["source"] == "BLENDER_BULLET_BREAKABLE_FIXED_CONSTRAINT",
        "derivedPhysicalResult": physics["contactFrame"] == 16 and physics["breakableAttachment"]["detachmentFrame"] == 24 and physics["respondingTargetCount"] == 3 and physics["settledWindowStartFrame"] == 132 and physics["settledGroupFrame"] == 141,
        "solverAuthority": result["authority"]["postReleaseTransformKeyframes"] == result["authority"]["authoredOutcomeFields"] == result["authority"]["authoredBreakFrames"] == result["authority"]["authoredDetachedPoses"] == result["authority"]["authoredDetachmentVelocities"] == 0,
        "saveReopen": reopen["status"] == "PASS" and all(reopen["checks"].values()),
        "regressionsAndNegatives": regression["status"] == "PASS" and all(regression["checks"].values()),
        "renderRoster": len(render["stills"]) == 3 and render["clip"]["frameCount"] == 48 and render["clip"]["cameraPolicy"] == "FIXED_CONTACT_CAMERA_WITH_TIMELINE_MARKERS_REMOVED_AFTER_STILLS",
        "resourceCeilings": work_bytes <= WORK_LIMIT and evidence_bytes <= EVIDENCE_LIMIT and shutil.disk_usage(WORK.parent).free >= MINIMUM_RESERVE,
        "noNetwork": all(row["exitCode"] == 0 for row in processes) and all(item["counts"]["networkCalls"] == 0 for item in (build_row, reopen, regression, render)),
    }
    receipt = {
        "schemaVersion": "bfs.rc5BreakableAttachmentFormalReceipt.v0.1",
        "status": "PASS_PENDING_FRESH_DIRECT_VISUAL_REVIEW_AND_INDEPENDENT_AUDIT" if all(checks.values()) else "FAIL",
        "product": {"commit": COMMIT, "parent": PARENT, "sourceDiffNumstat": changed},
        "binary": {"path": str(binary), "sha256": sha(binary), "bytes": binary.stat().st_size},
        "installed": {"moduleSha256": installed_hashes, "operatorSha256": sha(operator)},
        "checks": checks,
        "results": {"resultHash": result["resultHash"], "blendSha256": build_row["blend"]["sha256"], "reopenStatus": reopen["status"]},
        "render": {"receiptSha256": sha(EVIDENCE / "render.json"), "videoSha256": sha(video)},
        "tools": {Path(__file__).name: sha(Path(__file__)), PRODUCT_TOOL.name: sha(PRODUCT_TOOL)},
        "processes": [{"index": row["index"], "name": row["name"], "processHash": row["processHash"]} for row in processes],
        "counts": {"cleanNativeBuilds": 1, "productStarts": 4, "sceneMutations": 4, "blendSaves": 1, "reopens": 1, "reviewStills": 3, "contactClipFrames": 48, "ffmpegProcesses": 1, "networkCalls": 0, "engineRemoteWrites": 0, "forcePushes": 0, "tags": 0, "releases": 0, "binaryDistribution": 0, "signing": 0, "notarization": 0},
        "resources": {"freeBytesBefore": free_before, "workBytes": work_bytes, "evidenceBytes": evidence_bytes, "freeBytesAfter": shutil.disk_usage(WORK.parent).free},
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write(EVIDENCE / "receipt.json", receipt)
    print("RC5_FORMAL=" + canonical(receipt))
    if receipt["status"] == "FAIL":
        raise RuntimeError("RC5 formal machine validation failed")


if __name__ == "__main__":
    main()
