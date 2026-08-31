#!/usr/bin/env python3
"""Fail-closed two-start runner for PC.1 modeling-detail validation."""

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
SPEC_URI = "specs/ai-native-studio-pc1-modeling-detail-preregistration-c1.v0.2.json"
FREEZE_URI = "specs/ai-native-studio-pc1-tool-freeze-c4.v0.4.json"
EVIDENCE_URI = "experiments/ai-native-studio-post-pb7/PC.1-2026-08-31-mac-m2max-attempt-04"
WORK_ROOT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC.1-2026-08-31-mac-m2max-attempt-04")


def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
def sha256_bytes(value): return hashlib.sha256(value).hexdigest()
def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
def valid_self(value, field):
    body = dict(value); expected = body.pop(field, None)
    return expected == sha256_bytes(canonical(body))
def write_self(path, value, field):
    body = dict(value); body[field] = sha256_bytes(canonical(body))
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try: os.write(descriptor, (json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode()); os.fsync(descriptor)
    finally: os.close(descriptor)
    return body
def read_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def tree_files(root): return sorted(path for path in Path(root).rglob("*") if path.is_file() and not path.is_symlink())


def run_process(index, name, argv, env, evidence, ceiling):
    started = time.time()
    result = subprocess.run(["/usr/bin/time", "-l", *argv], cwd=ROOT, env=env, text=False, capture_output=True, timeout=ceiling)
    wall = time.time() - started
    stdout_path = evidence / "logs" / f"{index:02d}-{name}.stdout.log"
    stderr_path = evidence / "logs" / f"{index:02d}-{name}.stderr.log"
    stdout_path.write_bytes(result.stdout); stderr_path.write_bytes(result.stderr)
    rss = re.search(rb"\n\s*([0-9]+)\s+maximum resident set size", result.stderr)
    record = write_self(evidence / "processes" / f"{index:02d}-{name}.json", {
        "schemaVersion": "bfs.pc1Process.v0.1", "name": name, "argv": argv, "exitCode": result.returncode,
        "wallSeconds": wall, "peakRssBytes": int(rss.group(1)) if rss else None,
        "stdout": {"uri": stdout_path.relative_to(ROOT).as_posix(), "sha256": sha256_file(stdout_path), "bytes": stdout_path.stat().st_size},
        "stderr": {"uri": stderr_path.relative_to(ROOT).as_posix(), "sha256": sha256_file(stderr_path), "bytes": stderr_path.stat().st_size},
    }, "processHash")
    if result.returncode != 0 or record["peakRssBytes"] is None: raise RuntimeError(f"PROCESS_{name}_{result.returncode}")
    return record


def execute(args):
    if args.spec != SPEC_URI or args.tool_freeze != FREEZE_URI or args.evidence_root != EVIDENCE_URI or Path(args.work_root).resolve() != WORK_ROOT:
        raise RuntimeError("EXACT_ARGUMENTS")
    spec_path, freeze_path = ROOT / SPEC_URI, ROOT / FREEZE_URI
    spec, freeze = read_json(spec_path), read_json(freeze_path)
    if not valid_self(spec, "specHash") or not valid_self(freeze, "specHash") or freeze["status"] != "FROZEN_BEFORE_PC1_START": raise RuntimeError("CONTRACT")
    if freeze["preregistration"]["specHash"] != spec["specHash"] or freeze["preregistration"]["sha256"] != sha256_file(spec_path): raise RuntimeError("PREREG_BINDING")
    for tool in freeze["tools"]:
        if sha256_file(ROOT / tool["uri"]) != tool["sha256"]: raise RuntimeError("TOOL_" + tool["uri"])
    evidence = ROOT / EVIDENCE_URI
    if evidence.exists() or WORK_ROOT.exists(): raise RuntimeError("ROOT_EXISTS")
    source = ROOT / spec["baseline"]["source"]["uri"]; binary = Path(spec["baseline"]["binary"]["path"])
    if sha256_file(source) != spec["baseline"]["source"]["sha256"] or sha256_file(binary) != spec["baseline"]["binary"]["sha256"]: raise RuntimeError("BASELINE")
    free = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    if free < spec["resourceCeilings"]["minimumFreeReserveBytes"] + spec["resourceCeilings"]["evidenceBytes"] + spec["resourceCeilings"]["workBytes"]: raise RuntimeError("DISK")
    evidence.mkdir(parents=True); WORK_ROOT.mkdir(parents=True)
    for name in ("logs", "processes", "baseline", "derived"): (evidence / name).mkdir()
    home = WORK_ROOT / "home"; tmp = WORK_ROOT / "tmp"; config = WORK_ROOT / "config"; scripts = WORK_ROOT / "scripts"
    for path in (home, tmp, config, scripts): path.mkdir()
    env = {**os.environ, "HOME": str(home), "TMPDIR": str(tmp) + "/", "BLENDER_USER_CONFIG": str(config), "BLENDER_USER_SCRIPTS": str(scripts), "PYTHONNOUSERSITE": "1", "LC_ALL": "C", "LANG": "C", "OCIO": str(ROOT / "color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio")}
    common = ["--spec", str(spec_path), "--evidence-root", str(evidence), "--work-root", str(WORK_ROOT)]
    builder = ROOT / freeze["builder"]["uri"]
    first_argv = [str(binary), "--background", "--factory-startup", str(source), "--python-exit-code", "1", "--python", str(builder), "--", *common]
    p1 = run_process(1, "build", first_argv, env, evidence, spec["resourceCeilings"]["wallSeconds"])
    build = read_json(evidence / "build.json")
    if not valid_self(build, "buildHash") or build["status"] != "PASS": raise RuntimeError("BUILD")
    derived = Path(build["derived"]["path"])
    auditor = ROOT / freeze["semanticAuditor"]["uri"]
    second_argv = [str(binary), "--background", "--factory-startup", str(derived), "--python-exit-code", "1", "--python", str(auditor), "--", *common]
    p2 = run_process(2, "semantic-audit", second_argv, env, evidence, spec["resourceCeilings"]["wallSeconds"])
    semantic = read_json(evidence / "semantic-audit.json")
    if not valid_self(semantic, "auditHash") or semantic["status"] != "PASS": raise RuntimeError("SEMANTIC")
    source_after = sha256_file(source)
    if source_after != spec["baseline"]["source"]["sha256"]: raise RuntimeError("SOURCE_DRIFT")
    render_files = sorted([*(evidence / "baseline").glob("*.png"), *(evidence / "derived").glob("*.png")])
    if len(render_files) != spec["formalAttempt"]["exactRenderCalls"]: raise RuntimeError("RENDER_ROSTER")
    work_files = tree_files(WORK_ROOT); evidence_files = tree_files(evidence)
    work_bytes = sum(path.stat().st_size for path in work_files); evidence_bytes = sum(path.stat().st_size for path in evidence_files)
    if work_bytes > spec["resourceCeilings"]["workBytes"] or evidence_bytes > spec["resourceCeilings"]["evidenceBytes"]: raise RuntimeError("SIZE")
    if any(row["peakRssBytes"] > spec["resourceCeilings"]["peakRssBytesPerProcess"] for row in (p1, p2)): raise RuntimeError("RSS")
    receipt = write_self(evidence / "receipt.json", {
        "schemaVersion": "bfs.pc1ValidationReceipt.v0.1", "status": "PASS", "gate": "PC.1",
        "preregistration": {"uri": SPEC_URI, "sha256": sha256_file(spec_path), "specHash": spec["specHash"]},
        "toolFreeze": {"uri": FREEZE_URI, "sha256": sha256_file(freeze_path), "specHash": freeze["specHash"]},
        "source": {"uri": spec["baseline"]["source"]["uri"], "beforeSha256": spec["baseline"]["source"]["sha256"], "afterSha256": source_after},
        "build": {"uri": f"{EVIDENCE_URI}/build.json", "sha256": sha256_file(evidence / "build.json"), "buildHash": build["buildHash"]},
        "semanticAudit": {"uri": f"{EVIDENCE_URI}/semantic-audit.json", "sha256": sha256_file(evidence / "semantic-audit.json"), "auditHash": semantic["auditHash"]},
        "processes": [{"uri": f"{EVIDENCE_URI}/processes/{index:02d}-{name}.json", "processHash": row["processHash"]} for index, name, row in ((1, "build", p1), (2, "semantic-audit", p2))],
        "renders": [{"uri": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in render_files],
        "visibleViews": sum(row["passesVisibleChange"] for row in semantic["pixelMetrics"]), "pixelMetrics": semantic["pixelMetrics"],
        "resources": {"freeBytesAtAdmission": free, "workBytes": work_bytes, "evidenceBytesBeforeReceipt": evidence_bytes, "processWallSeconds": [p1["wallSeconds"], p2["wallSeconds"]], "peakRssBytes": [p1["peakRssBytes"], p2["peakRssBytes"]]},
        "operations": {"BlenderStarts": 2, "renderCalls": 6, "derivedSceneSaves": 1, "sourceSceneSaves": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0, "engineSourceEdits": 0, "engineCommits": 0, "engineRemoteWrites": 0},
    }, "receiptHash")
    print(f"BFS_PC1_RUN PASS {receipt['receiptHash']}")


parser = argparse.ArgumentParser(); parser.add_argument("--spec", required=True); parser.add_argument("--tool-freeze", required=True); parser.add_argument("--evidence-root", required=True); parser.add_argument("--work-root", required=True)
try: execute(parser.parse_args())
except Exception as error: print(f"BFS_PC1_RUN_REJECTED {error}", file=sys.stderr); raise SystemExit(1)
