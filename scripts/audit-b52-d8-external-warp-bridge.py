#!/usr/bin/env python3
"""Independent replay/integrity audit for B52-D8."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np, OpenImageIO as oiio
SPEC_SHA256="94a58f4e3c36b1828cb7e1bc4d5646cd577fac1afd411685235185590644a6a5"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def ah(a):return hashlib.sha256(np.ascontiguousarray(a,dtype="<f4").tobytes()).hexdigest()
def blob(root,commit,uri):
 p=subprocess.run(["git","show",f"{commit}:{uri}"],cwd=root,capture_output=True);return hashlib.sha256(p.stdout).hexdigest() if p.returncode==0 else None
def report_ok(r):return isinstance(r,dict) and r.get("reportHash")==ch({k:v for k,v in r.items() if k!="reportHash"})
def read_exr(path):
 im=oiio.ImageInput.open(str(path));sp=im.spec();a=np.asarray(im.read_image(0,0,0,4,oiio.FLOAT),np.float32).reshape(sp.height,sp.width,4);im.close();return np.ascontiguousarray(a,dtype="<f4")
def first(e,s):
 for x in s["attacks"]:
  if not e.get(x,False):return x
 return None
def main():
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--receipt",type=Path,required=True);p.add_argument("--result",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();root=a.spec.resolve().parent.parent;spec=json.loads(a.spec.read_text());rec=json.loads(a.receipt.read_text());res=json.loads(a.result.read_text())
 if sha(a.spec)!=SPEC_SHA256 or a.output.exists():raise RuntimeError("identity/overwrite")
 recself=rec["receiptHash"]==ch({k:v for k,v in rec.items() if k!="receiptHash"});resself=res["resultHash"]==ch({k:v for k,v in res.items() if k!="resultHash"});core={"evidence":res["evidence"],"measurements":res["measurements"],"operationCounts":res["operationCounts"],"verdict":res["verdict"],"baseFailure":res["baseFailure"]};coreself=res["evidenceCoreHash"]==ch(core);tools=[]
 for b in rec["tools"].values():
  current=sha(root/b["uri"]) if (root/b["uri"]).is_file() else None;frozen=blob(root,rec["toolFreezeCommit"],b["uri"]);tools.append({"uri":b["uri"],"match":current==frozen==b["sha256"]})
 parents=[]
 for b in rec["parentObservations"]:
  current=sha(root/b["uri"]) if (root/b["uri"]).is_file() else None;parents.append({"uri":b["uri"],"match":current==b["expectedSha256"]==b["observedSha256"]})
 runtimes=[]
 for name,b in rec["runtimeObservations"].items():
  path=Path(b["uri"]) if str(b["uri"]).startswith("/") else root/b["uri"];runtimes.append({"name":name,"match":path.is_file() and sha(path)==b["expectedSha256"]==b["observedSha256"]})
 runs=[]
 for run in rec["producerRuns"]+rec["encoderRuns"]+rec["blenderRuns"]:
  rp=root/run["reportUri"];r=json.loads(rp.read_text()) if rp.is_file() else None;b=(r or {}).get("output") or {};op=root/b.get("uri","");match=bool(r and r==run["report"] and report_ok(r) and op.is_file() and sha(op)==b.get("sha256") and op.stat().st_size==b.get("bytes"));runs.append({"kind":run["kind"],"fixtureId":run["fixtureId"],"producer":run["producer"],"repeat":run.get("repeat"),"match":match})
 artifacts=[]
 for d in res["diagnostics"]:
  for k in ("png","sidecar"):
   b=d[k];path=root/b["uri"];artifacts.append({"uri":b["uri"],"match":path.is_file() and sha(path)==b["sha256"] and path.stat().st_size==b["bytes"]})
 producer_replays=[];encoder_replays=[]
 with tempfile.TemporaryDirectory(prefix="bfs-b52-d8-replay-") as td:
  t=Path(td)
  for f in spec["fixtures"]:
   for producer,exe,key in (("python",spec["runtime"]["python"]["executable"],"pythonProducer"),("node",spec["runtime"]["node"]["executable"],"nodeProducer")):
    raw=t/producer/f["id"]/"reference.rgba32";rr=raw.with_suffix(".json");x=subprocess.run([exe,str(root/rec["tools"][key]["uri"]),"--spec",str(a.spec.resolve()),"--fixture",f["id"],"--output",str(raw),"--report",str(rr)],cwd=root,capture_output=True,text=True);formal=next(q for q in rec["producerRuns"] if q["fixtureId"]==f["id"] and q["producer"]==producer);actual=root/formal["report"]["output"]["uri"];producer_replays.append({"fixtureId":f["id"],"producer":producer,"match":x.returncode==0 and raw.is_file() and raw.read_bytes()==actual.read_bytes()});ex=t/producer/f["id"]/"source.exr";er=t/producer/f["id"]/"encoder.json";y=subprocess.run([spec["runtime"]["python"]["executable"],str(root/rec["tools"]["encoder"]["uri"]),"--spec",str(a.spec.resolve()),"--fixture",f["id"],"--producer",producer,"--input",str(raw),"--output",str(ex),"--report",str(er)],cwd=root,capture_output=True,text=True);encoder_replays.append({"fixtureId":f["id"],"producer":producer,"match":y.returncode==0 and ex.is_file() and ah(read_exr(ex))==hashlib.sha256(raw.read_bytes()).hexdigest()})
 with tempfile.TemporaryDirectory(prefix="bfs-b52-d8-analysis-",dir=root/"experiments") as td:
  t=Path(td);ro=t/"results.json";x=subprocess.run([spec["runtime"]["python"]["executable"],str(root/rec["tools"]["analyzer"]["uri"]),"--spec",str(a.spec.resolve()),"--receipt",str(a.receipt.resolve()),"--output",str(ro)],cwd=root,capture_output=True,text=True);replay=x.returncode==0 and ro.is_file() and ro.read_bytes()==a.result.read_bytes();replay_art=[]
  if replay:
   for d in res["diagnostics"]:
    for k in ("png","sidecar"):
     actual=root/d[k]["uri"];other=t/"diagnostics"/actual.name;replay_art.append({"uri":d[k]["uri"],"match":other.is_file() and other.read_bytes()==actual.read_bytes()})
 observed=first(res["evidence"],spec);verdict=spec["decisionRule"]["passVerdict"] if observed is None else spec["decisionRule"]["failVerdict"];expected_counts={k:spec["processMatrix"][k] for k in res["operationCounts"]};integrity={"receiptSelfHashExact":recself,"resultSelfHashExact":resself,"evidenceCoreHashExact":coreself,"frozenToolsExact":len(tools)==8 and all(x["match"] for x in tools),"parentsExact":len(parents)==3 and all(x["match"] for x in parents),"runtimesExact":len(runtimes)==4 and all(x["match"] for x in runtimes),"runArtifactsExact":len(runs)==24 and all(x["match"] for x in runs),"derivedArtifactsExact":len(artifacts)==12 and all(x["match"] for x in artifacts),"producerReplayExact":len(producer_replays)==6 and all(x["match"] for x in producer_replays),"encoderDecodedReplayExact":len(encoder_replays)==6 and all(x["match"] for x in encoder_replays),"analysisReplayByteExact":replay,"diagnosticReplayByteExact":len(replay_art)==12 and all(x["match"] for x in replay_art),"attackContractExact":res["attacksPassed"]==24 and len(res["attacks"])==24 and all(x["passed"] for x in res["attacks"]),"operationCountsExact":res["operationCounts"]==expected_counts,"scientificVerdictConsistent":res["baseFailure"]==observed and res["verdict"]==verdict};passed=all(integrity.values());body={"schemaVersion":"bfs.externalCanonicalWarpBridgeAudit.v0.1","status":"PASS" if passed else "FAIL","scientificVerdict":res["verdict"],"baseFailure":res["baseFailure"],"auditInterpretation":"PASS means evidence integrity and replay, not mandatory scientific support.","integrityChecks":integrity,"receipt":{"uri":str(a.receipt.resolve().relative_to(root)),"sha256":sha(a.receipt)},"result":{"uri":str(a.result.resolve().relative_to(root)),"sha256":sha(a.result)},"toolChecks":tools,"parentChecks":parents,"runtimeChecks":runtimes,"runChecks":runs,"artifactChecks":artifacts,"producerReplayChecks":producer_replays,"encoderReplayChecks":encoder_replays,"diagnosticReplayChecks":replay_art,"replayStdout":x.stdout.strip(),"failures":[] if passed else [k for k,v in integrity.items() if not v]};audit={**body,"auditHash":ch(body)};a.output.write_text(json.dumps(audit,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D8_AUDIT {audit['status']} producers={sum(x['match'] for x in producer_replays)}/6 encoders={sum(x['match'] for x in encoder_replays)}/6 runs={sum(x['match'] for x in runs)}/24 scientific={res['verdict']}")
 if not passed:raise SystemExit(1)
if __name__=="__main__":main()
