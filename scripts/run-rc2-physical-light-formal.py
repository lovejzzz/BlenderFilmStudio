#!/usr/bin/env python3
"""Run the frozen RC2 machine stage in fresh formal roots."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORKSPACE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC2-2026-09-01-attempt-01")
EVIDENCE = RESEARCH / "experiments/physical-light-transfer/RC2-2026-09-01-attempt-01"
PRODUCT_SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC1-development/source")
PRODUCT_COMMIT = "636f42f28f781f3e858fd5b6bf641910a549c91b"
PRODUCT_PARENT = "0e84ef3b6f79521b4f21a9d12a180dfd9713aab4"
DEPENDENCIES = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.6-2026-08-31-mac-m2max-attempt-01/source/lib/macos_arm64")
LFS_OBJECTS = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC9-2026-09-01-attempt-01/source/.git/lfs/objects")
SPEC_URI = "specs/fixtures/physical-light/RC2_F1.rolling-sphere-hinged-shutter.physical-light-spec.v0.1.json"
PC9_SPEC_URI = "specs/fixtures/causal-studio/PC9_F1.metric-basketball-three-filled-bottles.scene-spec.v0.6.json"
RC1_MODULE_SHA256 = "babf705beb1648393e5de3af4714e2cf56f39fbbd2eb31d28497ed2e8148a953"
MINIMUM_RESERVE = 100 * 1024**3
PROJECTED_WRITES = 8 * 1024**3
WORKSPACE_LIMIT = 50 * 1024**3
EVIDENCE_LIMIT = 512 * 1024**2


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest()


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def self_hash(value, field):
    body = dict(value); body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def write(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def directory_bytes(root): return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def output(argv, cwd=None): return subprocess.check_output(argv, cwd=cwd, text=True).strip()


def command(index, name, argv, cwd=None, env=None):
    stdout_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stdout.log"
    stderr_path = EVIDENCE / "logs" / f"{index:02d}-{name}.stderr.log"
    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        completed = subprocess.run(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr, check=False)
    receipt = {"index": index, "name": name, "argv": [str(x) for x in argv], "cwd": None if cwd is None else str(cwd), "exitCode": completed.returncode, "wallSeconds": round(time.monotonic() - started, 6), "stdoutSha256": sha256_file(stdout_path), "stderrSha256": sha256_file(stderr_path)}
    receipt["processHash"] = self_hash(receipt, "processHash")
    write(EVIDENCE / "processes" / f"{index:02d}-{name}.json", receipt)
    if completed.returncode: raise RuntimeError(f"{name} failed; see {stderr_path}")
    return receipt


def main():
    if WORKSPACE.exists() or EVIDENCE.exists(): raise RuntimeError("formal RC2 root is not fresh")
    if output(["git", "-C", str(PRODUCT_SOURCE), "rev-parse", "HEAD"]) != PRODUCT_COMMIT: raise RuntimeError("product commit mismatch")
    if output(["git", "-C", str(PRODUCT_SOURCE), "status", "--porcelain"]): raise RuntimeError("product source dirty")
    usage = shutil.disk_usage(WORKSPACE.parent)
    if usage.free < MINIMUM_RESERVE + PROJECTED_WRITES: raise RuntimeError("resource admission failed")
    for path in (WORKSPACE, EVIDENCE, EVIDENCE / "logs", EVIDENCE / "processes", WORKSPACE / "runtime"):
        path.mkdir(parents=True, exist_ok=False)
    admission = {"schemaVersion": "bfs.rc2ResourceAdmission.v0.1", "status": "PASS", "freeBytesBefore": usage.free, "minimumReserveBytes": MINIMUM_RESERVE, "projectedWriteBytes": PROJECTED_WRITES, "workspaceLimitBytes": WORKSPACE_LIMIT, "evidenceLimitBytes": EVIDENCE_LIMIT}
    admission["admissionHash"] = self_hash(admission, "admissionHash"); write(EVIDENCE / "admission.json", admission)

    source, build, runtime = WORKSPACE / "source", WORKSPACE / "build", WORKSPACE / "runtime"
    env = dict(os.environ); env.update({"GIT_LFS_SKIP_SMUDGE": "1", "GIT_TERMINAL_PROMPT": "0"})
    processes = [command(1, "local-clone", ["git", "clone", "--local", "--no-hardlinks", "--no-checkout", str(PRODUCT_SOURCE), str(source)], env=env)]
    lfs_dir = source / ".git/lfs"; lfs_dir.mkdir(parents=True, exist_ok=True)
    objects = lfs_dir / "objects"
    if objects.exists() and not objects.is_symlink(): objects.rmdir()
    objects.symlink_to(LFS_OBJECTS, target_is_directory=True)
    processes.append(command(2, "checkout", ["git", "checkout", "--detach", PRODUCT_COMMIT], cwd=source, env=env))
    processes.append(command(3, "lfs-checkout", ["git", "lfs", "checkout"], cwd=source, env=env))
    if output(["git", "rev-parse", "HEAD"], source) != PRODUCT_COMMIT or output(["git", "status", "--porcelain"], source): raise RuntimeError("formal source mismatch")
    processes.append(command(4, "clean-native-build", ["/usr/bin/make", "-s", f"BUILD_DIR={build}", f"BUILD_CMAKE_ARGS=-DLIBDIR={DEPENDENCIES}", "-j", "12", "release"], cwd=source, env=env))
    built_bundle, product_bundle = build / "bin/Blender.app", build / "bin/Film Studio Engine F0.app"
    if not built_bundle.is_dir() or product_bundle.exists(): raise RuntimeError("bundle rename precondition")
    built_bundle.rename(product_bundle)
    binary = product_bundle / "Contents/MacOS/Blender"
    module_root = product_bundle / "Contents/Resources/5.2/scripts/modules"
    operator_path = product_bundle / "Contents/Resources/5.2/scripts/startup/bl_operators/film_studio_workspace.py"
    physical_light = module_root / "film_studio_physical_light.py"
    rc1_module = module_root / "film_studio_physical_performance.py"
    if not all(path.is_file() for path in (binary, physical_light, rc1_module, operator_path)): raise RuntimeError("installed product path missing")
    rc1_regression = {"schemaVersion": "bfs.rc2Rc1SourceRegression.v0.1", "status": "PASS" if sha256_file(rc1_module) == RC1_MODULE_SHA256 and "elif film_studio_physical_performance.matches_physical_performance" in operator_path.read_text() else "FAIL", "installedRc1ModuleSha256": sha256_file(rc1_module), "expectedRc1ModuleSha256": RC1_MODULE_SHA256, "operatorPreservesRc1Route": "elif film_studio_physical_performance.matches_physical_performance" in operator_path.read_text()}
    write(EVIDENCE / "rc1-source-regression.json", rc1_regression)
    if rc1_regression["status"] != "PASS": raise RuntimeError("RC1 source regression")

    common = [str(binary), "--background", "--disable-autoexec", "--offline-mode"]
    processes.append(command(5, "pc8-pc9-regression", common + ["--factory-startup", "--python", str(RESEARCH / "scripts/check-pc9-physical-archetypes-development.py"), "--", "--action", "validate", "--repository-root", str(RESEARCH), "--scene-spec-uri", PC9_SPEC_URI, "--evidence-root", str(EVIDENCE), "--module-root", str(module_root)], cwd=RESEARCH))
    product_tool = RESEARCH / "scripts/run-rc2-physical-light-product.py"
    processes.append(command(6, "physical-light-build", common + ["--factory-startup", "--python", str(product_tool), "--", "--action", "build", "--repository-root", str(RESEARCH), "--scene-spec-uri", SPEC_URI, "--evidence-root", str(EVIDENCE), "--work-root", str(runtime)], cwd=RESEARCH))
    saved = runtime / "RC2_THE_SIGNAL_GATE.blend"
    processes.append(command(7, "physical-light-reopen", common + [str(saved), "--python", str(product_tool), "--", "--action", "reopen", "--repository-root", str(RESEARCH), "--scene-spec-uri", SPEC_URI, "--evidence-root", str(EVIDENCE), "--work-root", str(runtime)], cwd=RESEARCH))
    build_result = json.loads((EVIDENCE / "build.json").read_text())
    clip_start = build_result["clip"]["startFrame"]
    video = EVIDENCE / "review" / f"contact-clip-frame-{clip_start:04d}-{build_result['clip']['endFrame']:04d}.mp4"
    processes.append(command(8, "ffmpeg", ["/opt/homebrew/bin/ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "24", "-start_number", str(clip_start), "-i", str(EVIDENCE / "clip/frame-%04d.png"), "-frames:v", "48", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)]))
    probe = json.loads(output(["/opt/homebrew/bin/ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames", "-of", "json", str(video)]))
    write(EVIDENCE / "clip-video.json", {"schemaVersion": "bfs.rc2ClipVideo.v0.1", "status": "PASS", "path": str(video), "sha256": sha256_file(video), "bytes": video.stat().st_size, "probe": probe})

    workspace_bytes, evidence_bytes = directory_bytes(WORKSPACE), directory_bytes(EVIDENCE)
    if workspace_bytes > WORKSPACE_LIMIT or evidence_bytes > EVIDENCE_LIMIT or shutil.disk_usage(WORKSPACE.parent).free < MINIMUM_RESERVE: raise RuntimeError("post-run resource ceiling")
    changed = output(["git", "diff", "--numstat", PRODUCT_PARENT, PRODUCT_COMMIT, "--", "scripts/modules/film_studio_physical_light.py", "scripts/startup/bl_operators/film_studio_workspace.py"], source)
    receipt = {
        "schemaVersion": "bfs.rc2PhysicalLightMachineReceipt.v0.1", "status": "PASS_PENDING_DIRECT_VISUAL_AND_INDEPENDENT_AUDIT", "productCommit": PRODUCT_COMMIT, "productParent": PRODUCT_PARENT,
        "physicalLightSpecHash": json.loads((RESEARCH / SPEC_URI).read_text())["physicalLightSpecHash"],
        "binary": {"path": str(binary), "sha256": sha256_file(binary), "bytes": binary.stat().st_size},
        "installedModule": {"path": str(physical_light), "sha256": sha256_file(physical_light)}, "rc1SourceRegression": rc1_regression,
        "tools": {path.name: sha256_file(path) for path in (Path(__file__).resolve(), product_tool, RESEARCH / "scripts/check-pc9-physical-archetypes-development.py")},
        "sourceDiffNumstat": changed.splitlines(), "processes": [{"index": row["index"], "name": row["name"], "processHash": row["processHash"]} for row in processes],
        "counts": {"cleanNativeBuilds": 1, "productStarts": 3, "sceneMutatingExecutions": 1, "blendSaves": 1, "reopens": 1, "reviewStillRenders": 3, "contactClipFrameRenders": 48, "networkCalls": 0, "engineRemoteWrites": 0, "forcePushes": 0, "tags": 0, "releases": 0, "binaryDistribution": 0, "signing": 0, "notarization": 0},
        "resources": {"workspaceBytes": workspace_bytes, "evidenceBytes": evidence_bytes, "freeBytesAfter": shutil.disk_usage(WORKSPACE.parent).free},
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash"); write(EVIDENCE / "receipt.json", receipt)
    print("RC2_MACHINE_STAGE=" + canonical(receipt))


if __name__ == "__main__": main()
