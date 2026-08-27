#!/usr/bin/env python3
"""Independent replay/integrity audit for B52-D7."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, tempfile
from pathlib import Path
SPEC_SHA256="f102a969cb59d92b0103c6807f20ca5436978504aafadd14a9b0353709ea0df5"
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ch(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def blob(root,commit,uri):
 p=subprocess.run(["git","show",f"{commit}:{uri}"],cwd=root,capture_output=True);return hashlib.sha256(p.stdout).hexdigest() if p.returncode==0 else None
def report_ok(r):return r.get("reportHash")==ch({k:v for k,v in r.items() if k!="reportHash"})
def first(e,s):
 for x in s["attacks"]:
  if not e.get(x,False):return x
 return None
def main():
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--receipt",type=Path,required=True);p.add_argument("--result",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();root=a.spec.resolve().parent.parent;spec=json.loads(a.spec.read_text());rec=json.loads(a.receipt.read_text());res=json.loads(a.result.read_text())
 if sha(a.spec)!=SPEC_SHA256 or a.output.exists():raise RuntimeError("identity/overwrite")
 recself=rec["receiptHash"]==ch({k:v for k,v in rec.items() if k!="receiptHash"});resself=res["resultHash"]==ch({k:v for k,v in res.items() if k!="resultHash"});core={"evidence":res["evidence"],"measurements":res["measurements"],"operationCounts":res["operationCounts"],"verdict":res["verdict"],"baseFailure":res["baseFailure"]};coreself=res["evidenceCoreHash"]==ch(core)
 tools=[]
 for b in rec["tools"].values():
  cur=sha(root/b["uri"]) if (root/b["uri"]).is_file() else None;fr=blob(root,rec["toolFreezeCommit"],b["uri"]);tools.append({"uri":b["uri"],"match":cur==fr==b["sha256"]})
 parents=[]
 for b in rec["parentObservations"]:
  cur=sha(root/b["uri"]) if (root/b["uri"]).is_file() else None;parents.append({"uri":b["uri"],"match":cur==b["expectedSha256"]==b["observedSha256"]})
 runtimes=[]
 for name,b in rec["runtimeObservations"].items():
  path=(root/b["uri"]) if not str(b["uri"]).startswith("/") else Path(b["uri"]);runtimes.append({"name":name,"match":path.is_file() and sha(path)==b["expectedSha256"]==b["observedSha256"]})
 runs=[]
 for run in rec["pythonReferenceRuns"]+rec["nodeReferenceRuns"]+rec["blenderRuns"]:
  rp=root/run["reportUri"];r=json.loads(rp.read_text()) if rp.is_file() else None;b=r.get("output") if r else None;op=root/b["uri"] if b else None;match=bool(r and r==run["report"] and report_ok(r) and op and op.is_file() and sha(op)==b["sha256"] and op.stat().st_size==b["bytes"]);runs.append({"kind":run["kind"],"fixtureId":run["fixtureId"],"repeat":run.get("repeat"),"match":match})
 artifacts=[]
 for d in res["diagnostics"]:
  for k in ("png","sidecar"):
   b=d[k];p=root/b["uri"];artifacts.append({"uri":b["uri"],"match":p.is_file() and sha(p)==b["sha256"] and p.stat().st_size==b["bytes"]})
 reference_replays=[]
 with tempfile.TemporaryDirectory(prefix="bfs-b52-d7-ref-audit-") as td:
  t=Path(td)
  for f in spec["fixtures"]:
   for kind,runtime,tool,formal in [("python",spec["runtime"]["pythonReference"]["executable"],rec["tools"]["pythonReference"]["uri"],next(x for x in rec["pythonReferenceRuns"] if x["fixtureId"]==f["id"])),("node",spec["runtime"]["nodeReference"]["executable"],rec["tools"]["nodeReference"]["uri"],next(x for x in rec["nodeReferenceRuns"] if x["fixtureId"]==f["id"]))]:
    op=t/kind/f["id"]/"reference.rgba32";rp=t/kind/f["id"]/"report.json";cmd=[runtime,str(root/tool),"--spec",str(a.spec.resolve()),"--fixture",f["id"],"--output",str(op),"--report",str(rp)];x=subprocess.run(cmd,cwd=root,capture_output=True,text=True);actual=root/formal["report"]["output"]["uri"];reference_replays.append({"kind":kind,"fixtureId":f["id"],"match":x.returncode==0 and op.is_file() and op.read_bytes()==actual.read_bytes()})
 with tempfile.TemporaryDirectory(prefix="bfs-b52-d7-analysis-audit-",dir=root/"experiments") as td:
  t=Path(td);ro=t/"results.json";cmd=[sys.executable,str(root/rec["tools"]["analyzer"]["uri"]),"--spec",str(a.spec.resolve()),"--receipt",str(a.receipt.resolve()),"--output",str(ro)];x=subprocess.run(cmd,cwd=root,capture_output=True,text=True);replay=x.returncode==0 and ro.is_file() and ro.read_bytes()==a.result.read_bytes();replay_art=[]
  if replay:
   for d in res["diagnostics"]:
    for k in ("png","sidecar"):
     actual=root/d[k]["uri"];other=t/"diagnostics"/actual.name;replay_art.append({"uri":d[k]["uri"],"match":other.is_file() and other.read_bytes()==actual.read_bytes()})
 observed=first(res["evidence"],spec);verdict=spec["decision"]["passVerdict"] if observed is None else spec["decision"]["failVerdict"];expected_counts={k:spec["processMatrix"][k] for k in res["operationCounts"]}
 integrity={"receiptSelfHashExact":recself,"resultSelfHashExact":resself,"evidenceCoreHashExact":coreself,"frozenToolsExact":len(tools)==7 and all(x["match"] for x in tools),"parentsExact":len(parents)==3 and all(x["match"] for x in parents),"runtimesExact":len(runtimes)==4 and all(x["match"] for x in runtimes),"runArtifactsExact":len(runs)==24 and all(x["match"] for x in runs),"derivedArtifactsExact":len(artifacts)==24 and all(x["match"] for x in artifacts),"dualReferenceReplayExact":len(reference_replays)==12 and all(x["match"] for x in reference_replays),"analysisReplayByteExact":replay,"diagnosticReplayByteExact":len(replay_art)==24 and all(x["match"] for x in replay_art),"attackContractExact":res["attacksPassed"]==23 and len(res["attacks"])==23 and all(x["passed"] for x in res["attacks"]),"operationCountsExact":res["operationCounts"]==expected_counts,"scientificVerdictConsistent":res["baseFailure"]==observed and res["verdict"]==verdict};passed=all(integrity.values());body={"schemaVersion":"bfs.subpixelBilinearToleranceAudit.v0.1","status":"PASS" if passed else "FAIL","scientificVerdict":res["verdict"],"baseFailure":res["baseFailure"],"auditInterpretation":"PASS means evidence integrity and replay, not mandatory scientific support.","integrityChecks":integrity,"receipt":{"uri":str(a.receipt.resolve().relative_to(root)),"sha256":sha(a.receipt)},"result":{"uri":str(a.result.resolve().relative_to(root)),"sha256":sha(a.result)},"toolChecks":tools,"parentChecks":parents,"runtimeChecks":runtimes,"runChecks":runs,"artifactChecks":artifacts,"referenceReplayChecks":reference_replays,"diagnosticReplayChecks":replay_art,"replayStdout":x.stdout.strip(),"failures":[] if passed else [k for k,v in integrity.items() if not v]};audit={**body,"auditHash":ch(body)};a.output.write_text(json.dumps(audit,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D7_AUDIT {audit['status']} references={sum(x['match'] for x in reference_replays)}/{len(reference_replays)} runs={sum(x['match'] for x in runs)}/{len(runs)} scientific={res['verdict']}")
 if not passed:raise SystemExit(1)
if __name__=="__main__":main()
