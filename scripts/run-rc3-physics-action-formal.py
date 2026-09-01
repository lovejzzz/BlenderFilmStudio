#!/usr/bin/env python3
"""Run the frozen RC3 clean-build formal validation in fresh roots."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC3-2026-09-01-attempt-01")
EVIDENCE = ROOT / "experiments/physics-native-action/RC3-2026-09-01-attempt-01"
PRODUCT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC1-development/source")
PRODUCT_COMMIT = "5f595fe3aca7118847aec5b572f6d90a377a4352"
PRODUCT_PARENT = "636f42f28f781f3e858fd5b6bf641910a549c91b"
DEPENDENCIES = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.6-2026-08-31-mac-m2max-attempt-01/source/lib/macos_arm64")
LFS_OBJECTS = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC9-2026-09-01-attempt-01/source/.git/lfs/objects")
PRODUCT_TOOL = ROOT / "scripts/run-rc3-physics-action-product-c3.py"
RENDER_TOOL = ROOT / "scripts/render-rc3-physics-action-review.py"
D1 = "specs/fixtures/physics-action/RC3_D1.signal-gate.physics-action-spec.v0.3.json"
H1 = "specs/fixtures/physics-action/RC3_H1.ball-three-bottles.physics-action-spec.v0.2.json"
MINIMUM_FREE = 100 * 1024**3
PROJECTED_WRITES = 8 * 1024**3
MINIMUM_FREE_BEFORE = 160 * 1024**3
WORK_LIMIT = 64 * 1024**3
EVIDENCE_LIMIT = 1024 * 1024**2


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def size(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def output(argv, cwd=None):
    return subprocess.check_output(argv, cwd=cwd, text=True).strip()


def command(index, name, argv, cwd=None, extra_env=None):
    out = EVIDENCE / "logs" / f"{index:02d}-{name}.stdout.log"
    err = EVIDENCE / "logs" / f"{index:02d}-{name}.stderr.log"
    env = dict(os.environ)
    env.update({
        "BLENDER_USER_CONFIG": str(WORK / "user/config"),
        "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"),
        "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"),
        "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions"),
        "GIT_LFS_SKIP_SMUDGE": "1",
        "GIT_TERMINAL_PROMPT": "0",
    })
    if extra_env:
        env.update(extra_env)
    started = time.monotonic()
    with out.open("wb") as stdout, err.open("wb") as stderr:
        done = subprocess.run(argv, cwd=cwd or ROOT, env=env, stdout=stdout, stderr=stderr, check=False)
    row = {
        "index": index,
        "name": name,
        "argv": [str(item) for item in argv],
        "cwd": str(cwd or ROOT),
        "exitCode": done.returncode,
        "wallSeconds": round(time.monotonic() - started, 6),
        "stdoutSha256": sha(out),
        "stderrSha256": sha(err),
    }
    row["processHash"] = self_hash(row, "processHash")
    write(EVIDENCE / "processes" / f"{index:02d}-{name}.json", row)
    if done.returncode:
        raise RuntimeError(f"{name} failed; see {err}")
    return row


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("formal roots are not fresh")
    if output(["git", "-C", str(PRODUCT), "rev-parse", "HEAD"]) != PRODUCT_COMMIT:
        raise RuntimeError("product commit mismatch")
    if output(["git", "-C", str(PRODUCT), "status", "--porcelain"]):
        raise RuntimeError("product source dirty")
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < MINIMUM_FREE_BEFORE or free_before < MINIMUM_FREE + PROJECTED_WRITES:
        raise RuntimeError("formal resource admission failed")
    for path in (
        WORK,
        EVIDENCE,
        EVIDENCE / "logs",
        EVIDENCE / "processes",
        WORK / "runtime",
        WORK / "user/config",
        WORK / "user/scripts",
        WORK / "user/datafiles",
        WORK / "user/extensions",
    ):
        path.mkdir(parents=True, exist_ok=False)
    admission = {
        "schemaVersion": "bfs.rc3PhysicsActionResourceAdmission.v0.1",
        "status": "PASS",
        "freeBytesBefore": free_before,
        "minimumFreeBeforeBytes": MINIMUM_FREE_BEFORE,
        "minimumReserveBytes": MINIMUM_FREE,
        "projectedWriteBytes": PROJECTED_WRITES,
        "workspaceLimitBytes": WORK_LIMIT,
        "evidenceLimitBytes": EVIDENCE_LIMIT,
    }
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write(EVIDENCE / "admission.json", admission)

    source, build, runtime = WORK / "source", WORK / "build", WORK / "runtime"
    processes = []
    processes.append(command(1, "local-clone", ["git", "clone", "--local", "--no-hardlinks", "--no-checkout", str(PRODUCT), str(source)]))
    lfs_dir = source / ".git/lfs"
    lfs_dir.mkdir(parents=True, exist_ok=True)
    objects = lfs_dir / "objects"
    if objects.exists() and not objects.is_symlink():
        objects.rmdir()
    objects.symlink_to(LFS_OBJECTS, target_is_directory=True)
    processes.append(command(2, "checkout", ["git", "checkout", "--detach", PRODUCT_COMMIT], cwd=source))
    processes.append(command(3, "lfs-checkout", ["git", "lfs", "checkout"], cwd=source))
    if output(["git", "rev-parse", "HEAD"], source) != PRODUCT_COMMIT or output(["git", "status", "--porcelain"], source):
        raise RuntimeError("formal source identity mismatch")
    processes.append(command(4, "clean-native-build", ["/usr/bin/make", "-s", f"BUILD_DIR={build}", f"BUILD_CMAKE_ARGS=-DLIBDIR={DEPENDENCIES}", "-j", "12", "release"], cwd=source))

    built_bundle = build / "bin/Blender.app"
    product_bundle = build / "bin/Film Studio Engine F0.app"
    if not built_bundle.is_dir() or product_bundle.exists():
        raise RuntimeError("bundle rename precondition")
    built_bundle.rename(product_bundle)
    binary = product_bundle / "Contents/MacOS/Blender"
    module_root = product_bundle / "Contents/Resources/5.2/scripts/modules"
    operator = product_bundle / "Contents/Resources/5.2/scripts/startup/bl_operators/film_studio_workspace.py"
    modules = {
        "physicsAction": module_root / "film_studio_physics_action.py",
        "physicalLight": module_root / "film_studio_physical_light.py",
        "physicalPerformance": module_root / "film_studio_physical_performance.py",
        "causal": module_root / "film_studio_causal.py",
    }
    if not binary.is_file() or not operator.is_file() or not all(path.is_file() for path in modules.values()):
        raise RuntimeError("installed product files missing")
    regression = {
        "schemaVersion": "bfs.rc3InstalledRouteRegression.v0.1",
        "status": "PASS",
        "moduleSha256": {name: sha(path) for name, path in modules.items()},
        "expectedSha256": {
            "physicsAction": "6135a3c0582dcc81e4781af7836567bf90c801000911b881ca4c0b4ec2d625ee",
            "physicalLight": "669da32a3616db76cbe015c5055d1c78d758ee5f7753d011e51ec2382529972f",
            "physicalPerformance": "babf705beb1648393e5de3af4714e2cf56f39fbbd2eb31d28497ed2e8148a953",
            "causal": "b45c86d301b509898d05a897f38599d80ca20285c54919eb003719d4439ff6f2",
        },
        "operatorRoutes": {
            "physicsAction": "film_studio_physics_action.matches_physics_action" in operator.read_text(),
            "physicalLight": "film_studio_physical_light.matches_physical_light" in operator.read_text(),
            "physicalPerformance": "film_studio_physical_performance.matches_physical_performance" in operator.read_text(),
            "causalFallback": "film_studio_causal.execute_causal_scene" in operator.read_text(),
        },
    }
    regression["status"] = "PASS" if regression["moduleSha256"] == regression["expectedSha256"] and all(regression["operatorRoutes"].values()) else "FAIL"
    write(EVIDENCE / "installed-route-regression.json", regression)
    if regression["status"] != "PASS":
        raise RuntimeError("installed route regression")

    common = [str(binary), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode", "--python", str(PRODUCT_TOOL), "--"]
    for index, case, spec in ((5, "D1", D1), (7, "H1", H1)):
        processes.append(command(index, f"{case.lower()}-build", common + ["--action", "build", "--case", case, "--repository-root", str(ROOT), "--scene-spec-uri", spec, "--evidence-root", str(EVIDENCE), "--work-root", str(runtime), "--module-root", str(module_root)]))
        blend = runtime / f"RC3_{case}_PHYSICS_ACTION.blend"
        if not (EVIDENCE / f"{case}-build.json").is_file() or not blend.is_file():
            raise RuntimeError(f"{case} formal build artifacts missing")
        processes.append(command(index + 1, f"{case.lower()}-reopen", [str(binary), "--background", "--disable-autoexec", "--offline-mode", str(blend), "--python", str(PRODUCT_TOOL), "--", "--action", "reopen", "--case", case, "--repository-root", str(ROOT), "--scene-spec-uri", spec, "--evidence-root", str(EVIDENCE), "--work-root", str(runtime), "--module-root", str(module_root)]))
    processes.append(command(9, "negative-controls", common + ["--action", "negative", "--case", "D1", "--repository-root", str(ROOT), "--scene-spec-uri", D1, "--evidence-root", str(EVIDENCE), "--work-root", str(runtime), "--module-root", str(module_root)]))

    d1_blend = runtime / "RC3_D1_PHYSICS_ACTION.blend"
    h1_blend = runtime / "RC3_H1_PHYSICS_ACTION.blend"
    processes.append(command(10, "render-both-cases", [str(binary), "--background", "--disable-autoexec", "--offline-mode", str(d1_blend), "--python", str(RENDER_TOOL), "--", "--d1-blend", str(d1_blend), "--h1-blend", str(h1_blend), "--evidence-root", str(EVIDENCE)]))
    render = json.loads((EVIDENCE / "render.json").read_text())
    media = []
    index = 11
    for case in render["cases"]:
        case_id, start = case["case"], case["clip"]["startFrame"]
        clip_root = EVIDENCE / case_id / "clip"
        video = EVIDENCE / case_id / f"{case_id.lower()}-contact-clip.mp4"
        sheet = EVIDENCE / case_id / f"{case_id.lower()}-contact-sheet.png"
        processes.append(command(index, f"{case_id.lower()}-video", ["/opt/homebrew/bin/ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "24", "-start_number", str(start), "-i", str(clip_root / "frame-%04d.png"), "-frames:v", "48", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)]))
        index += 1
        processes.append(command(index, f"{case_id.lower()}-sheet", ["/opt/homebrew/bin/ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-start_number", str(start), "-i", str(clip_root / "frame-%04d.png"), "-vf", "select='not(mod(n,6))',scale=480:270,tile=4x2", "-frames:v", "1", str(sheet)]))
        index += 1
        media.append({"case": case_id, "video": {"path": str(video), "sha256": sha(video), "bytes": video.stat().st_size}, "contactSheet": {"path": str(sheet), "sha256": sha(sheet), "bytes": sheet.stat().st_size}})

    builds = {case: json.loads((EVIDENCE / f"{case}-build.json").read_text()) for case in ("D1", "H1")}
    reopens = {case: json.loads((EVIDENCE / f"{case}-reopen.json").read_text()) for case in ("D1", "H1")}
    negative = json.loads((EVIDENCE / "negative-controls.json").read_text())
    changed = output(["git", "diff", "--numstat", PRODUCT_PARENT, PRODUCT_COMMIT, "--", "scripts/modules/film_studio_physics_action.py", "scripts/startup/bl_operators/film_studio_workspace.py"], source).splitlines()
    work_bytes, evidence_bytes = size(WORK), size(EVIDENCE)
    result_rows = [builds["D1"]["result"], builds["H1"]["result"]]
    checks = {
        "sourceIdentity": output(["git", "rev-parse", "HEAD"], source) == PRODUCT_COMMIT and not output(["git", "status", "--porcelain"], source),
        "sourceScope": changed == ["857\t0\tscripts/modules/film_studio_physics_action.py", "24\t5\tscripts/startup/bl_operators/film_studio_workspace.py"],
        "installedRegression": regression["status"] == "PASS",
        "sameCompiler": result_rows[0]["contractVersion"] == result_rows[1]["contractVersion"] == "bfs.filmStudioPhysicsAction.v0.1",
        "distinctGraphs": result_rows[0]["compiledGraphHash"] != result_rows[1]["compiledGraphHash"],
        "solverAuthority": all(row["authority"]["postReleaseTransformKeyframes"] == row["authority"]["authoredOutcomeFields"] == row["authority"]["authoredContactResponsePeakOrFinalFrames"] == row["authority"]["lightAnimationChannels"] == 0 for row in result_rows),
        "reopenExact": all(row["status"] == "PASS" for row in reopens.values()),
        "negativeControls": negative["status"] == "PASS" and negative["passCount"] == 16,
        "renderCounts": render["counts"]["reviewStills"] == 6 and render["counts"]["clipFrames"] == 96,
        "resourceCeilings": work_bytes <= WORK_LIMIT and evidence_bytes <= EVIDENCE_LIMIT and shutil.disk_usage(WORK.parent).free >= MINIMUM_FREE,
    }
    receipt = {
        "schemaVersion": "bfs.rc3PhysicsActionFormalReceipt.v0.1",
        "status": "PASS_PENDING_INDEPENDENT_AUDIT_AND_VISUAL_BINDING" if all(checks.values()) else "FAIL",
        "product": {"commit": PRODUCT_COMMIT, "parent": PRODUCT_PARENT, "sourceDiffNumstat": changed},
        "binary": {"path": str(binary), "sha256": sha(binary), "bytes": binary.stat().st_size},
        "installed": {"moduleSha256": regression["moduleSha256"], "operatorSha256": sha(operator)},
        "checks": checks,
        "tools": {path.name: sha(path) for path in (Path(__file__).resolve(), PRODUCT_TOOL, RENDER_TOOL)},
        "processes": [{"index": row["index"], "name": row["name"], "processHash": row["processHash"]} for row in processes],
        "results": {case: {"resultHash": builds[case]["result"]["resultHash"], "blendSha256": builds[case]["blend"]["sha256"], "reopenStatus": reopens[case]["status"]} for case in ("D1", "H1")},
        "render": {"sha256": sha(EVIDENCE / "render.json"), "media": media},
        "counts": {"cleanNativeBuilds": 1, "productStarts": 6, "sceneMutatingExecutions": 2, "blendSaves": 2, "reopens": 2, "negativeControlRuns": 16, "reviewStillRenders": 6, "contactClipFrameRenders": 96, "ffmpegProcesses": 4, "networkCalls": 0, "engineRemoteWrites": 0, "forcePushes": 0, "tags": 0, "releases": 0, "binaryDistribution": 0, "signing": 0, "notarization": 0},
        "resources": {"freeBytesBefore": free_before, "workBytes": work_bytes, "evidenceBytes": evidence_bytes, "freeBytesAfter": shutil.disk_usage(WORK.parent).free},
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write(EVIDENCE / "receipt.json", receipt)
    print("RC3_FORMAL=" + canonical(receipt))
    if not all(checks.values()):
        raise RuntimeError("formal checks failed")


if __name__ == "__main__":
    main()
