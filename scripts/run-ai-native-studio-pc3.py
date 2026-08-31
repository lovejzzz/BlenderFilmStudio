#!/usr/bin/env python3
"""Fail-closed PC.3 integrated render, video and semantic-pixel audit runner."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC_URI = "specs/ai-native-studio-pc3-integrated-review-preregistration.v0.1.json"
FREEZE_URI = "specs/ai-native-studio-pc3-tool-freeze.v0.1.json"
EVIDENCE_URI = "experiments/ai-native-studio-post-pb7/PC.3-2026-08-31-mac-m2max-attempt-01"
WORK_ROOT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC.3-2026-08-31-mac-m2max-attempt-01")
def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
def valid_self(value, field):
    body = dict(value); expected = body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()
def write_self(path, value, field):
    body = dict(value); body[field] = hashlib.sha256(canonical(body)).hexdigest()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try: os.write(descriptor, (json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode()); os.fsync(descriptor)
    finally: os.close(descriptor)
    return body
def read_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def tree_files(root): return sorted(path for path in Path(root).rglob("*") if path.is_file() and not path.is_symlink())


def run_process(index, name, argv, env, evidence, ceiling):
    started = time.time(); result = subprocess.run(["/usr/bin/time", "-l", *argv], cwd=ROOT, env=env, text=False, capture_output=True, timeout=ceiling); wall = time.time() - started
    stdout = evidence / "logs" / f"{index:02d}-{name}.stdout.log"; stderr = evidence / "logs" / f"{index:02d}-{name}.stderr.log"; stdout.write_bytes(result.stdout); stderr.write_bytes(result.stderr)
    rss = re.search(rb"\n\s*([0-9]+)\s+maximum resident set size", result.stderr)
    record = write_self(evidence / "processes" / f"{index:02d}-{name}.json", {"schemaVersion": "bfs.pc3Process.v0.1", "name": name, "argv": argv, "exitCode": result.returncode, "wallSeconds": wall, "peakRssBytes": int(rss.group(1)) if rss else None, "stdout": {"uri": stdout.relative_to(ROOT).as_posix(), "sha256": sha256_file(stdout), "bytes": stdout.stat().st_size}, "stderr": {"uri": stderr.relative_to(ROOT).as_posix(), "sha256": sha256_file(stderr), "bytes": stderr.stat().st_size}}, "processHash")
    if result.returncode != 0 or record["peakRssBytes"] is None: raise RuntimeError(f"PROCESS_{name}_{result.returncode}")
    return record


def execute(args):
    if args.spec != SPEC_URI or args.tool_freeze != FREEZE_URI or args.evidence_root != EVIDENCE_URI or Path(args.work_root).resolve() != WORK_ROOT: raise RuntimeError("EXACT_ARGUMENTS")
    spec_path = ROOT / SPEC_URI; freeze_path = ROOT / FREEZE_URI; spec = read_json(spec_path); freeze = read_json(freeze_path)
    if not valid_self(spec, "specHash") or not valid_self(freeze, "specHash") or freeze["status"] != "FROZEN_BEFORE_PC3_RENDER": raise RuntimeError("CONTRACT")
    if freeze["preregistration"]["specHash"] != spec["specHash"] or freeze["preregistration"]["sha256"] != sha256_file(spec_path): raise RuntimeError("PREREG")
    for tool in freeze["tools"]:
        if sha256_file(ROOT / tool["uri"]) != tool["sha256"]: raise RuntimeError("TOOL_" + tool["uri"])
    source = Path(spec["source"]["path"]); binary = Path(freeze["binary"]["path"]); ffmpeg = Path(freeze["ffmpeg"]["path"]); ffprobe = Path(freeze["ffprobe"]["path"])
    if sha256_file(source) != spec["source"]["sha256"] or sha256_file(binary) != freeze["binary"]["sha256"] or sha256_file(ROOT / spec["baselineA"]["videoUri"]) != spec["baselineA"]["videoSha256"]: raise RuntimeError("BASELINE")
    evidence = ROOT / EVIDENCE_URI
    if evidence.exists() or WORK_ROOT.exists(): raise RuntimeError("ROOT_EXISTS")
    resources = spec["resourceCeilings"]; free = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    if free < resources["minimumFreeReserveBytes"] + resources["evidenceBytes"] + resources["workBytes"]: raise RuntimeError("DISK")
    evidence.mkdir(parents=True); WORK_ROOT.mkdir(parents=True)
    for name in ("logs", "processes", "frames", "review"): (evidence / name).mkdir()
    for name in ("home", "tmp", "config", "scripts"): (WORK_ROOT / name).mkdir()
    env = {**os.environ, "HOME": str(WORK_ROOT / "home"), "TMPDIR": str(WORK_ROOT / "tmp") + "/", "BLENDER_USER_CONFIG": str(WORK_ROOT / "config"), "BLENDER_USER_SCRIPTS": str(WORK_ROOT / "scripts"), "PYTHONNOUSERSITE": "1", "LC_ALL": "C", "LANG": "C", "OCIO": str(ROOT / "color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio")}
    common = ["--spec", str(spec_path), "--evidence-root", str(evidence), "--work-root", str(WORK_ROOT)]
    render_argv = [str(binary), "--background", "--factory-startup", str(source), "--python-exit-code", "1", "--python", str(ROOT / freeze["renderer"]["uri"]), "--", *common]
    p1 = run_process(1, "render", render_argv, env, evidence, resources["wallSecondsPerBlenderProcess"])
    render = read_json(evidence / "render.json")
    if not valid_self(render, "renderHash") or render["status"] != "PASS": raise RuntimeError("RENDER")
    video = evidence / spec["renderProfile"]["reviewVideo"]
    ffmpeg_argv = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-framerate", "24", "-start_number", "1", "-i", str(evidence / "frames/frame-%04d.png"), "-frames:v", "288", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)]
    p2 = run_process(2, "ffmpeg", ffmpeg_argv, env, evidence, 180)
    probe_argv = [str(ffprobe), "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames", "-of", "json", str(video)]
    p3 = run_process(3, "ffprobe", probe_argv, env, evidence, 60)
    probe = json.loads((evidence / "logs/03-ffprobe.stdout.log").read_text(encoding="utf-8"))["streams"][0]
    if int(probe["width"]) != 640 or int(probe["height"]) != 360 or probe["avg_frame_rate"] != "24/1" or int(probe["nb_read_frames"]) != 288: raise RuntimeError("VIDEO")
    audit_argv = [str(binary), "--background", "--factory-startup", str(source), "--python-exit-code", "1", "--python", str(ROOT / freeze["semanticAuditor"]["uri"]), "--", *common]
    p4 = run_process(4, "semantic-audit", audit_argv, env, evidence, resources["wallSecondsPerBlenderProcess"])
    semantic = read_json(evidence / "semantic-audit.json")
    if not valid_self(semantic, "auditHash") or semantic["status"] != "PASS": raise RuntimeError("SEMANTIC")
    if sha256_file(source) != spec["source"]["sha256"]: raise RuntimeError("SOURCE_DRIFT")
    frame_files = sorted((evidence / "frames").glob("frame-*.png")); work_files = tree_files(WORK_ROOT); evidence_files = tree_files(evidence)
    if len(frame_files) != 288 or any(path.suffix.lower() == ".exr" for path in [*work_files, *evidence_files]): raise RuntimeError("OUTPUT_ROSTER")
    work_bytes = sum(path.stat().st_size for path in work_files); evidence_bytes = sum(path.stat().st_size for path in evidence_files)
    if work_bytes > resources["workBytes"] or evidence_bytes > resources["evidenceBytes"]: raise RuntimeError("SIZE")
    processes = [p1, p2, p3, p4]
    if any(row["peakRssBytes"] > resources["peakRssBytesPerProcess"] for row in processes): raise RuntimeError("RSS")
    receipt = write_self(evidence / "receipt.json", {"schemaVersion": "bfs.pc3MachineReceipt.v0.1", "status": "MACHINE_PASS_HUMAN_PENDING", "gate": "PC.3", "preregistration": {"uri": SPEC_URI, "sha256": sha256_file(spec_path), "specHash": spec["specHash"]}, "toolFreeze": {"uri": FREEZE_URI, "sha256": sha256_file(freeze_path), "specHash": freeze["specHash"]}, "source": {"path": str(source), "beforeSha256": spec["source"]["sha256"], "afterSha256": sha256_file(source)}, "render": {"uri": f"{EVIDENCE_URI}/render.json", "sha256": sha256_file(evidence / "render.json"), "renderHash": render["renderHash"]}, "semanticAudit": {"uri": f"{EVIDENCE_URI}/semantic-audit.json", "sha256": sha256_file(evidence / "semantic-audit.json"), "auditHash": semantic["auditHash"]}, "video": {"uri": video.relative_to(ROOT).as_posix(), "sha256": sha256_file(video), "bytes": video.stat().st_size, "probe": probe}, "contactSheet": render["contactSheet"], "processes": [{"name": row["name"], "processHash": row["processHash"]} for row in processes], "machineMetrics": {"frameCount": semantic["frameCount"], "uniqueFrameHashes": semantic["uniqueFrameHashes"], "dynamicConsecutivePairs": semantic["dynamicConsecutivePairs"], "visiblyDifferentFrames": semantic["visiblyDifferentFrames"], "medianMeanAbsoluteRgbDifference": semantic["medianMeanAbsoluteRgbDifference"]}, "humanReview": {"status": "PENDING", "questions": [row["id"] for row in spec["delayedHumanReview"]["questions"]]}, "resources": {"freeBytesAtAdmission": free, "workBytes": work_bytes, "evidenceBytesBeforeReceipt": evidence_bytes, "peakRssBytes": [row["peakRssBytes"] for row in processes]}, "operations": {"BlenderStarts": 2, "renderCalls": 288, "ffmpegProcesses": 1, "ffprobeProcesses": 1, "sceneSaves": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0}}, "receiptHash")
    print(f"BFS_PC3_RUN MACHINE_PASS_HUMAN_PENDING {receipt['receiptHash']}")


parser = argparse.ArgumentParser(); parser.add_argument("--spec", required=True); parser.add_argument("--tool-freeze", required=True); parser.add_argument("--evidence-root", required=True); parser.add_argument("--work-root", required=True)
try: execute(parser.parse_args())
except Exception as error: print(f"BFS_PC3_RUN_REJECTED {error}", file=sys.stderr); raise SystemExit(1)
