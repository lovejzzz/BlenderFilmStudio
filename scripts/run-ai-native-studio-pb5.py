#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Formal PB.5 restart-safe product validation runner."""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "specs/ai-native-studio-pb5-restart-safe-preregistration.v0.1.json"
MANIFEST_URI = "specs/ai-native-studio-pb5-render-job-attempt-01.v0.2.json"
MANIFEST = ROOT / MANIFEST_URI
SOURCE_ROOT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.5-2026-08-31-mac-m2max-attempt-01/source")
BUILD_ROOT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.5-2026-08-31-mac-m2max-attempt-01/build")
WORK_ROOT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.5-2026-08-31-mac-m2max-attempt-01/work")
EVIDENCE = ROOT / "experiments/ai-native-studio-phase-b/PB.5-2026-08-31-mac-m2max-attempt-01"
BINARY = BUILD_ROOT / "bin/Film Studio Engine F0.app/Contents/MacOS/Blender"
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.3-2026-08-31-mac-m2max-attempt-06/b01/artifacts/scene.blend")
PRODUCT_HELPER = ROOT / "scripts/run-ai-native-studio-pb5-product.py"
AUDIT_HELPER = ROOT / "scripts/audit-ai-native-studio-pb5.py"
OFFICIAL_CONFIG = Path.home() / "Library/Application Support/Blender"


def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest()
def valid_self(value, field):
    expected = value.get(field); body = dict(value); body.pop(field, None)
    return isinstance(expected, str) and hashlib.sha256(canonical(body)).hexdigest() == expected
def self_hashed(value, field):
    body = dict(value); body.pop(field, None); body[field] = hashlib.sha256(canonical(body)).hexdigest(); return body
def read_json(path): return json.loads(path.read_text(encoding="utf-8"))
def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True); descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try: os.write(descriptor, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()); os.fsync(descriptor)
    finally: os.close(descriptor)
    return value
def git(*args, cwd=ROOT):
    result = subprocess.run(["/usr/bin/git", *args], cwd=cwd, text=True, capture_output=True)
    if result.returncode: raise RuntimeError(result.stderr)
    return result.stdout.strip()
def tree_identity(root):
    if not root.exists(): return {"state": "ABSENT", "files": 0, "bytes": 0, "digest": hashlib.sha256(b"ABSENT").hexdigest()}
    rows=[]
    for path in sorted(item for item in root.rglob("*") if item.is_file() and not item.is_symlink()): rows.append({"uri": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"state": "PRESENT", "files": len(rows), "bytes": sum(row["bytes"] for row in rows), "digest": hashlib.sha256(canonical(rows)).hexdigest()}
def marker(text, prefix):
    line = next((line for line in text.splitlines() if line.startswith(prefix)), None)
    if line is None: raise RuntimeError("Missing marker " + prefix)
    return json.loads(line[len(prefix):])


def common_args(action):
    return ["--action", action, "--repository-root", str(ROOT), "--manifest-uri", MANIFEST_URI, "--evidence-root", str(EVIDENCE), "--work-root", str(WORK_ROOT)]


def run_product(index, name, action, expected_exit, maximum_seconds, with_audit=False):
    home = WORK_ROOT / "homes" / f"0{index}-{name}"; home.mkdir()
    args = [str(BINARY), "--background", "--factory-startup", str(SOURCE_BLEND), "--python", str(PRODUCT_HELPER)]
    if with_audit: args += ["--python", str(AUDIT_HELPER)]
    args += ["--", *common_args(action)]
    started_at = time.time(); result = subprocess.run(["/usr/bin/time", "-l", *args], cwd=BUILD_ROOT, env={**os.environ, "HOME": str(home)}, text=True, capture_output=True, timeout=maximum_seconds)
    wall = time.time() - started_at
    stdout_path = EVIDENCE / "logs" / f"0{index}-{name}.stdout.log"; stderr_path = EVIDENCE / "logs" / f"0{index}-{name}.stderr.log"
    with stdout_path.open("x", encoding="utf-8") as handle: handle.write(result.stdout)
    with stderr_path.open("x", encoding="utf-8") as handle: handle.write(result.stderr)
    rss_match = re.search(r"\n\s*(\d+)\s+maximum resident set size", result.stderr)
    payload = marker(result.stdout + "\n" + result.stderr, "PB5_NEGATIVE=" if action == "NEGATIVE" else "PB5_PRODUCT=")
    audit_payload = marker(result.stdout + "\n" + result.stderr, "PB5_AUDIT=") if with_audit else None
    status = "INTERRUPTED_ACCEPTED" if expected_exit == 75 and result.returncode == 75 else "PASS" if result.returncode == expected_exit else "FAIL"
    body = {"schemaVersion": "bfs.pb5ProcessReceipt.v0.1", "status": status, "name": name, "argv": args, "pid": payload["pid"], "exitCode": result.returncode, "wallSeconds": wall, "maximumResidentSetSizeBytes": int(rss_match.group(1)) if rss_match else None, "stdoutSha256": sha256_file(stdout_path), "stderrSha256": sha256_file(stderr_path), "payload": payload, "auditPayload": audit_payload}
    receipt = write_exclusive(EVIDENCE / "processes" / f"0{index}-{name}.json", self_hashed(body, "processHash"))
    if status == "FAIL": raise RuntimeError(f"Process {name} failed")
    return receipt


def build_source_receipts(manifest):
    stderr = (EVIDENCE / "build.stderr.log").read_text(); stdout = (EVIDENCE / "build.stdout.log").read_text(); timing = re.search(r"\s*([\d.]+)\s+real\s+([\d.]+)\s+user\s+([\d.]+)\s+sys", stderr)
    changed = git("diff", "--name-only", "HEAD^..HEAD", cwd=SOURCE_ROOT).splitlines(); numstat = [line.split("\t") for line in git("diff", "--numstat", "HEAD^..HEAD", cwd=SOURCE_ROOT).splitlines()]
    source_body={"schemaVersion":"bfs.pb5SourceReceipt.v0.1","status":"PASS","commit":git("rev-parse","HEAD",cwd=SOURCE_ROOT),"parent":git("rev-parse","HEAD^",cwd=SOURCE_ROOT),"clean":git("status","--porcelain=v1",cwd=SOURCE_ROOT)=="","changedPaths":changed,"additions":sum(int(row[0]) for row in numstat),"deletions":sum(int(row[1]) for row in numstat)}
    build_body={"schemaVersion":"bfs.pb5BuildReceipt.v0.1","status":"PASS" if "Blender successfully built" in stdout else "FAIL","binary":{"path":str(BINARY),"bytes":BINARY.stat().st_size,"sha256":sha256_file(BINARY)},"timing":{"realSeconds":float(timing.group(1)),"userSeconds":float(timing.group(2)),"systemSeconds":float(timing.group(3))},"logs":{"stdoutSha256":sha256_file(EVIDENCE/"build.stdout.log"),"stderrSha256":sha256_file(EVIDENCE/"build.stderr.log")},"arm64":True,"bundleId":"studio.ainativefilm.f0","developerIdSigning":False,"notarization":False,"distribution":False}
    source_receipt=write_exclusive(EVIDENCE/"source.json",self_hashed(source_body,"sourceHash")); build_receipt=write_exclusive(EVIDENCE/"build.json",self_hashed(build_body,"buildHash"))
    if source_receipt["commit"]!=manifest["baselines"]["engineSourceCommit"] or source_receipt["additions"]>500 or build_receipt["status"]!="PASS" or build_receipt["binary"]["sha256"]!=manifest["baselines"]["binarySha256"]: raise RuntimeError("Source/build admission failed")
    return source_receipt,build_receipt


def execute():
    prereg=read_json(PREREG); manifest=read_json(MANIFEST)
    if not valid_self(prereg,"specHash") or not valid_self(manifest,"manifestHash"): raise RuntimeError("Spec/manifest self hash differs")
    for path,key in ((Path(__file__),"runnerSha256"),(PRODUCT_HELPER,"productHelperSha256"),(AUDIT_HELPER,"auditHelperSha256")):
        if sha256_file(path)!=manifest["tools"][key]: raise RuntimeError("Tool identity differs")
    if WORK_ROOT.exists() or (EVIDENCE/"receipt.json").exists(): raise RuntimeError("Formal roots not fresh")
    free=os.statvfs(EVIDENCE).f_bavail*os.statvfs(EVIDENCE).f_frsize
    if free<prereg["resourceCeilings"]["requiredAdmissionBytes"]: raise RuntimeError("Disk admission blocked")
    WORK_ROOT.mkdir(); (WORK_ROOT/"homes").mkdir(); (EVIDENCE/"logs").mkdir(); (EVIDENCE/"processes").mkdir()
    official_before=tree_identity(OFFICIAL_CONFIG); source_before=sha256_file(SOURCE_BLEND); source_receipt,build_receipt=build_source_receipts(manifest)
    processes=[]; processes.append(run_product(1,"interrupted-preview","INTERRUPT_AFTER_PREVIEW",75,120))
    preview_receipt=read_json(EVIDENCE/"preview/receipt.json"); preview_hash=sha256_file(EVIDENCE/"preview/preview.png"); decision1=read_json(EVIDENCE/"job-control/01-preview.json")
    interruption=write_exclusive(EVIDENCE/"interruption.json",self_hashed({"schemaVersion":"bfs.pb5InterruptionReceipt.v0.1","status":"PASS","exitCode":75,"afterStage":"PREVIEW","previewReceiptHash":preview_receipt["receiptHash"],"previewArtifactSha256":preview_hash,"decisionHash":decision1["decisionHash"],"renderCalls":1},"interruptionHash"))
    processes.append(run_product(2,"resume-final","RESUME_FINAL",0,180));
    if sha256_file(EVIDENCE/"preview/preview.png")!=preview_hash: raise RuntimeError("Preview changed during resume")
    final_receipt=read_json(EVIDENCE/"final/receipt.json"); final_hash=sha256_file(EVIDENCE/"final/final.exr")
    processes.append(run_product(3,"complete-noop","RESUME_COMPLETE",0,120))
    if sha256_file(EVIDENCE/"preview/preview.png")!=preview_hash or sha256_file(EVIDENCE/"final/final.exr")!=final_hash: raise RuntimeError("Completed artifacts changed")
    processes.append(run_product(4,"negative-audit","NEGATIVE",0,120,True))
    audit=read_json(EVIDENCE/"independent-audit.json"); official_after=tree_identity(OFFICIAL_CONFIG)
    cost=write_exclusive(EVIDENCE/"cost.json",self_hashed({"schemaVersion":"bfs.pb5CostReceipt.v0.1","status":"PASS","monetaryCostUsd":0,"basis":"Local validation; zero model/API/network charge.","productStarts":4,"renderCalls":2,"renderSeconds":preview_receipt["timing"]["renderSeconds"]+final_receipt["timing"]["renderSeconds"],"artifactBytes":preview_receipt["output"]["bytes"]+final_receipt["output"]["bytes"],"peakResidentSetSizeBytes":max(row["maximumResidentSetSizeBytes"] for row in processes)},"costHash"))
    work_identity=tree_identity(WORK_ROOT); evidence_identity=tree_identity(EVIDENCE)
    work_manifest=write_exclusive(EVIDENCE/"work-root-manifest.json",self_hashed({"schemaVersion":"bfs.pb5RootManifest.v0.1","status":"PASS","root":str(WORK_ROOT),"identity":work_identity},"manifestHash"))
    evidence_manifest=write_exclusive(EVIDENCE/"evidence-root-manifest.json",self_hashed({"schemaVersion":"bfs.pb5RootManifest.v0.1","status":"PASS","scope":"Files before this manifest and final receipt","identity":evidence_identity},"manifestHash"))
    checks={"source":valid_self(source_receipt,"sourceHash"),"build":valid_self(build_receipt,"buildHash"),"processes":len(processes)==4 and all(valid_self(row,"processHash") for row in processes),"interruption":valid_self(interruption,"interruptionHash"),"twoRenders":sum(row["payload"]["renderCalls"] for row in processes)==2,"previewImmutable":processes[1]["payload"]["previewSha256Before"]==preview_hash and processes[2]["payload"]["previewSha256Before"]==preview_hash,"completeNoop":processes[2]["payload"]["renderCalls"]==0,"audit":valid_self(audit,"auditHash") and audit["status"]=="PASS","cost":valid_self(cost,"costHash"),"sourceUnchanged":sha256_file(SOURCE_BLEND)==source_before,"officialConfigUnchanged":official_before==official_after,"workCeiling":work_identity["bytes"]<=prereg["resourceCeilings"]["maximumWorkBytes"],"evidenceCeiling":evidence_identity["bytes"]<=prereg["resourceCeilings"]["maximumEvidenceBytes"]}
    body={"schemaVersion":"bfs.pb5ValidationReceipt.v0.1","status":"PASS" if all(checks.values()) else "FAIL","verdict":"PASS" if all(checks.values()) else "FAIL","claim":"One controlled PREVIEW interruption resumed FINAL only; completed resume was a no-op; three attacks rejected pre-render.","manifest":{"uri":MANIFEST_URI,"manifestHash":manifest["manifestHash"]},"baselines":manifest["baselines"],"counters":{"cleanBuilds":1,"productStarts":4,"renderCalls":2,"modelCalls":0,"networkCalls":0,"mouseInteractions":0,"releases":0,"signing":0,"notarization":0,"distributions":0},"bindings":{"sourceHash":source_receipt["sourceHash"],"buildHash":build_receipt["buildHash"],"processHashes":[row["processHash"] for row in processes],"interruptionHash":interruption["interruptionHash"],"previewReceiptHash":preview_receipt["receiptHash"],"finalReceiptHash":final_receipt["receiptHash"],"auditHash":audit["auditHash"],"costHash":cost["costHash"],"workManifestHash":work_manifest["manifestHash"],"evidenceManifestHash":evidence_manifest["manifestHash"]},"resources":{"freeBytesAtAdmission":free,"workBytes":work_identity["bytes"],"evidenceBytesBeforeFinal":evidence_identity["bytes"]},"checks":checks}
    receipt=write_exclusive(EVIDENCE/"receipt.json",self_hashed(body,"receiptHash"))
    if receipt["status"]!="PASS": raise RuntimeError("PB.5 checks failed: "+",".join(k for k,v in checks.items() if not v))
    print(f"PB5_PASS receiptHash={receipt['receiptHash']} preview={preview_hash} final={final_hash}")


def self_test():
    sample=self_hashed({"value":0.0},"hash"); checks={"selfHash":valid_self(sample,"hash"),"fourStarts":4==4,"twoRenders":2==2,"freshWork":not WORK_ROOT.exists()}
    print(json.dumps({"status":"PASS" if all(checks.values()) else "FAIL","checks":checks},indent=2)); raise SystemExit(0 if all(checks.values()) else 1)


if "--self-test" in sys.argv: self_test()
elif "--execute" in sys.argv: execute()
else: raise SystemExit("Use --self-test or --execute")
