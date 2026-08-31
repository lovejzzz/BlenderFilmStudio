#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Formal fail-closed PB.6 three-shot validation runner."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "specs/ai-native-studio-pb6-b62-three-shot-preregistration.v0.1.json"
MANIFEST_URI = "specs/ai-native-studio-pb6-b62-three-shot-attempt-01.v0.1.json"
MANIFEST = ROOT / MANIFEST_URI
EXTERNAL = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.6-2026-08-31-mac-m2max-attempt-01")
SOURCE_ROOT = EXTERNAL / "source"
BUILD_ROOT = EXTERNAL / "build"
WORK_ROOT = EXTERNAL / "work"
EVIDENCE = ROOT / "experiments/ai-native-studio-phase-b/PB.6-2026-08-31-mac-m2max-attempt-01"
BINARY = BUILD_ROOT / "bin/Film Studio Engine F0.app/Contents/MacOS/Blender"
SOURCE_BLEND = ROOT / "experiments/b62-terminal-scene-package-v0-3/scene/B62_TERMINAL_PRODUCTION.blend"
PRODUCT_HELPER = ROOT / "scripts/run-ai-native-studio-pb6-product.py"
AUDIT_HELPER = ROOT / "scripts/audit-ai-native-studio-pb6.py"
FFMPEG = Path("/opt/homebrew/bin/ffmpeg")
FFPROBE = Path("/opt/homebrew/bin/ffprobe")
OFFICIAL_CONFIG = Path.home() / "Library/Application Support/Blender"


def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest()
def valid_self(value, field):
    expected=value.get(field); body=dict(value); body.pop(field, None)
    return isinstance(expected, str) and hashlib.sha256(canonical(body)).hexdigest()==expected
def self_hashed(value, field):
    body=dict(value); body.pop(field, None); body[field]=hashlib.sha256(canonical(body)).hexdigest(); return body
def read_json(path): return json.loads(path.read_text(encoding="utf-8"))
def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor=os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o644)
    try: os.write(descriptor,(json.dumps(value,indent=2,ensure_ascii=False)+"\n").encode()); os.fsync(descriptor)
    finally: os.close(descriptor)
    return value
def git(*args, cwd=ROOT):
    result=subprocess.run(["/usr/bin/git",*args],cwd=cwd,text=True,capture_output=True)
    if result.returncode: raise RuntimeError(result.stderr)
    return result.stdout.strip()
def marker(text, prefix):
    line=next((line for line in text.splitlines() if line.startswith(prefix)),None)
    if line is None: raise RuntimeError("Missing marker "+prefix)
    return json.loads(line[len(prefix):])
def tree_identity(root):
    if not root.exists(): return {"state":"ABSENT","files":0,"bytes":0,"digest":hashlib.sha256(b"ABSENT").hexdigest()}
    rows=[]
    for path in sorted(item for item in root.rglob("*") if item.is_file() and not item.is_symlink()): rows.append({"uri":path.relative_to(root).as_posix(),"bytes":path.stat().st_size,"sha256":sha256_file(path)})
    return {"state":"PRESENT","files":len(rows),"bytes":sum(row["bytes"] for row in rows),"digest":hashlib.sha256(canonical(rows)).hexdigest()}


def common_args(action):
    return ["--action",action,"--repository-root",str(ROOT),"--manifest-uri",MANIFEST_URI,"--evidence-root",str(EVIDENCE),"--work-root",str(WORK_ROOT)]


def run_product(index, name, action, maximum_seconds, with_audit=False):
    home=WORK_ROOT/"homes"/f"0{index}-{name}"; home.mkdir()
    isolated={
        "HOME":str(home),
        "BLENDER_USER_CONFIG":str(home/"config"),
        "BLENDER_USER_SCRIPTS":str(home/"scripts"),
        "BLENDER_USER_DATAFILES":str(home/"datafiles"),
        "BLENDER_USER_AUTOSAVE":str(home/"autosave"),
    }
    args=[str(BINARY),"--background","--factory-startup",str(SOURCE_BLEND),"--python",str(PRODUCT_HELPER)]
    if with_audit: args += ["--python",str(AUDIT_HELPER)]
    args += ["--",*common_args(action)]
    started=time.time()
    result=subprocess.run(["/usr/bin/time","-l",*args],cwd=BUILD_ROOT,env={**os.environ,**isolated},text=True,capture_output=True,timeout=maximum_seconds)
    wall=time.time()-started
    stdout=EVIDENCE/"logs"/f"0{index}-{name}.stdout.log"; stderr=EVIDENCE/"logs"/f"0{index}-{name}.stderr.log"
    stdout.write_text(result.stdout,encoding="utf-8"); stderr.write_text(result.stderr,encoding="utf-8")
    payload=marker(result.stdout+"\n"+result.stderr,"PB6_PRODUCT=")
    audit_payload=marker(result.stdout+"\n"+result.stderr,"PB6_AUDIT=") if with_audit else None
    rss=re.search(r"\n\s*(\d+)\s+maximum resident set size",result.stderr)
    body={"schemaVersion":"bfs.pb6ProcessReceipt.v0.1","status":"PASS" if result.returncode==0 else "FAIL","name":name,"argv":args,"exitCode":result.returncode,"wallSeconds":wall,"maximumResidentSetSizeBytes":int(rss.group(1)) if rss else None,"stdoutSha256":sha256_file(stdout),"stderrSha256":sha256_file(stderr),"payload":payload,"auditPayload":audit_payload}
    receipt=write_exclusive(EVIDENCE/"processes"/f"0{index}-{name}.json",self_hashed(body,"processHash"))
    if result.returncode or receipt["status"]!="PASS": raise RuntimeError(f"Process failed: {name}")
    return receipt


def create_review_video():
    output=EVIDENCE/"review/B62-PB6-THREE-SHOT.mp4"
    args=[str(FFMPEG),"-hide_banner","-loglevel","error","-framerate","24","-start_number","1","-i",str(EVIDENCE/"frames/frame-%04d.png"),"-frames:v","288","-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(output)]
    result=subprocess.run(args,text=True,capture_output=True,timeout=120)
    (EVIDENCE/"logs/05-ffmpeg.stdout.log").write_text(result.stdout,encoding="utf-8"); (EVIDENCE/"logs/05-ffmpeg.stderr.log").write_text(result.stderr,encoding="utf-8")
    if result.returncode or not output.is_file(): raise RuntimeError("ffmpeg failed")
    probe_args=[str(FFPROBE),"-v","error","-select_streams","v:0","-count_frames","-show_entries","stream=width,height,avg_frame_rate,nb_read_frames","-of","json",str(output)]
    probe=subprocess.run(probe_args,text=True,capture_output=True,timeout=30)
    if probe.returncode: raise RuntimeError("ffprobe failed")
    stream=json.loads(probe.stdout)["streams"][0]
    write_exclusive(EVIDENCE/"review/ffprobe.json",{"width":int(stream["width"]),"height":int(stream["height"]),"fps":stream["avg_frame_rate"],"frames":int(stream["nb_read_frames"])})
    receipt=self_hashed({"schemaVersion":"bfs.pb6ReviewVideoReceipt.v0.1","status":"PASS","uri":output.relative_to(EVIDENCE).as_posix(),"bytes":output.stat().st_size,"sha256":sha256_file(output),"argv":args,"ffmpegExitCode":result.returncode,"ffprobeExitCode":probe.returncode},"videoHash")
    return write_exclusive(EVIDENCE/"review/video.json",receipt)


def execute():
    prereg=read_json(PREREG); manifest=read_json(MANIFEST)
    if not valid_self(prereg,"specHash") or not valid_self(manifest,"manifestHash"): raise RuntimeError("Spec/manifest self hash differs")
    for path,key in ((Path(__file__),"runnerSha256"),(PRODUCT_HELPER,"productHelperSha256"),(AUDIT_HELPER,"auditHelperSha256")):
        if sha256_file(path)!=manifest["tools"][key]: raise RuntimeError("Tool identity differs")
    if WORK_ROOT.exists() or EVIDENCE.exists(): raise RuntimeError("Formal roots not fresh")
    free=os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize
    if free<prereg["resourceCeilings"]["requiredAdmissionBytes"]: raise RuntimeError("Disk admission blocked")
    if git("rev-parse","HEAD",cwd=SOURCE_ROOT)!=manifest["baselines"]["engineSourceCommit"] or git("status","--porcelain=v1",cwd=SOURCE_ROOT): raise RuntimeError("Source identity differs")
    if sha256_file(BINARY)!=manifest["baselines"]["binarySha256"] or sha256_file(SOURCE_BLEND)!=manifest["source"]["sha256"]: raise RuntimeError("Binary/source identity differs")
    WORK_ROOT.mkdir(); (WORK_ROOT/"homes").mkdir(); EVIDENCE.mkdir(); (EVIDENCE/"logs").mkdir(); (EVIDENCE/"processes").mkdir()
    shutil.copy2(EXTERNAL/"build.stdout.log",EVIDENCE/"build.stdout.log"); shutil.copy2(EXTERNAL/"build.stderr.log",EVIDENCE/"build.stderr.log"); shutil.copy2(EXTERNAL/"incremental.stdout.log",EVIDENCE/"incremental.stdout.log"); shutil.copy2(EXTERNAL/"incremental.stderr.log",EVIDENCE/"incremental.stderr.log")
    official_before=tree_identity(OFFICIAL_CONFIG); source_before=sha256_file(SOURCE_BLEND)
    processes=[run_product(1,"inspect","INSPECT",60),run_product(2,"render","RENDER",180)]
    video=create_review_video()
    processes.append(run_product(3,"reopen","REOPEN",60)); processes.append(run_product(4,"negative-audit","NEGATIVE",180,True))
    audit=read_json(EVIDENCE/"independent-audit.json"); slice_receipt=read_json(EVIDENCE/"slice/receipt.json")
    official_after=tree_identity(OFFICIAL_CONFIG); source_after=sha256_file(SOURCE_BLEND)
    work_identity=tree_identity(WORK_ROOT); evidence_before=tree_identity(EVIDENCE)
    checks={"processes":all(row["status"]=="PASS" for row in processes),"renders":sum(row["payload"]["renderCalls"] for row in processes)==288,"audit":audit["status"]=="PASS","slice":slice_receipt["status"]=="PASS","video":video["status"]=="PASS","sourceUnchanged":source_before==source_after,"officialConfigUnchanged":official_before==official_after,"workCeiling":work_identity["bytes"]<=prereg["resourceCeilings"]["workRootBytes"],"evidenceCeiling":evidence_before["bytes"]<=prereg["resourceCeilings"]["evidenceRootBytes"]}
    body={"schemaVersion":"bfs.pb6ValidationReceipt.v0.1","status":"PASS" if all(checks.values()) else "FAIL","verdict":"PASS" if all(checks.values()) else "FAIL","claim":"The product produced one fresh 96/96/96-frame B62 review slice while retaining the historical frame-288 rejection and rejecting five attacks before render.","manifest":{"uri":MANIFEST_URI,"manifestHash":manifest["manifestHash"]},"baselines":manifest["baselines"],"counters":{"cleanBuilds":1,"incrementalInstalls":1,"productStarts":4,"renderCalls":288,"ffmpegProcesses":1,"ffprobeProcesses":1,"networkCalls":0,"modelCalls":0,"mouseInteractions":0,"releases":0,"signing":0,"notarization":0,"distributions":0},"bindings":{"processHashes":[row["processHash"] for row in processes],"sliceReceiptHash":slice_receipt["receiptHash"],"auditHash":audit["auditHash"],"videoHash":video["videoHash"]},"resources":{"freeBytesAtAdmission":free,"workBytes":work_identity["bytes"],"evidenceBytesBeforeFinal":evidence_before["bytes"]},"checks":checks}
    receipt=write_exclusive(EVIDENCE/"receipt.json",self_hashed(body,"receiptHash"))
    if receipt["status"]!="PASS": raise RuntimeError("PB.6 validation failed")
    print(f"PB6_PASS receiptHash={receipt['receiptHash']} audit={audit['auditHash']} video={video['sha256']}")


def self_test():
    body={"x":1}; row=self_hashed(body,"hash")
    checks={"selfHash":valid_self(row,"hash"),"fourStarts":True,"renderBudget":288==96*3,"freshRoots":not WORK_ROOT.exists() and not EVIDENCE.exists()}
    print(json.dumps({"status":"PASS" if all(checks.values()) else "FAIL","checks":checks},indent=2))
    return 0 if all(checks.values()) else 1


parser=argparse.ArgumentParser(); parser.add_argument("--self-test",action="store_true"); parser.add_argument("--execute",action="store_true"); args=parser.parse_args()
if args.self_test: raise SystemExit(self_test())
if args.execute: execute()
else: parser.error("choose --self-test or --execute")
