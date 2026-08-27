#!/usr/bin/env python3
"""Independent integrity/replay audit for B52-D9.1."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, tempfile
from pathlib import Path
import numpy as np, OpenImageIO as oiio

SPEC_SHA256="669077423e0101dd5600576d295c0b7a62189a30b18c1dd6ab18a3b5257cd28f"
FILES=("previous.rgba32","current.rgba32","previous-depth.f32","current-depth.f32","previous-layer.f32","current-layer.f32","motion.xy32","analytic-validity.u8","resolved.rgba32","clean-target.rgba32")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def ah(a): return hashlib.sha256(np.ascontiguousarray(a,dtype="<f4").tobytes()).hexdigest()
def resolved(root,uri):
 p=Path(uri); return p if p.is_absolute() else root/p
def blob(root,commit,uri):
 p=subprocess.run(["git","show",f"{commit}:{uri}"],cwd=root,capture_output=True); return hashlib.sha256(p.stdout).hexdigest() if p.returncode==0 else None
def report_ok(r): return isinstance(r,dict) and r.get("reportHash")==ch({k:v for k,v in r.items() if k!="reportHash"})
def read_exr(path):
 i=oiio.ImageInput.open(str(path))
 if i is None: raise RuntimeError(oiio.geterror() or f"cannot read {path}")
 s=i.spec(); a=np.asarray(i.read_image(0,0,0,4,oiio.FLOAT),np.float32).reshape(s.height,s.width,4); i.close(); return np.ascontiguousarray(a,dtype="<f4")
def first(e,spec):
 for name in spec["attacks"]:
  if not e.get(name,False): return name
 return None
def clean_env(root,spec,tmp,blender=False):
 env={k:v for k,v in os.environ.items() if k=="PATH"}; env.update({"LANG":"C.UTF-8","LC_ALL":"C.UTF-8"})
 if blender:
  env.update({"OCIO":str((root/spec["runtime"]["ocio"]["uri"]).resolve()),"TMPDIR":str(tmp/"tmp"),"BLENDER_USER_CONFIG":str(tmp/"config"),"BLENDER_USER_SCRIPTS":str(tmp/"scripts")})
  for k in ("TMPDIR","BLENDER_USER_CONFIG","BLENDER_USER_SCRIPTS"): Path(env[k]).mkdir(parents=True,exist_ok=True)
 return env
def main():
 p=argparse.ArgumentParser(); p.add_argument("--spec",type=Path,required=True); p.add_argument("--receipt",type=Path,required=True); p.add_argument("--result",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); root=a.spec.resolve().parent.parent; spec=json.loads(a.spec.read_text()); rec=json.loads(a.receipt.read_text()); res=json.loads(a.result.read_text())
 if sha(a.spec)!=SPEC_SHA256 or a.output.exists(): raise RuntimeError("identity/overwrite")
 recself=rec["receiptHash"]==ch({k:v for k,v in rec.items() if k!="receiptHash"}); resself=res["resultHash"]==ch({k:v for k,v in res.items() if k!="resultHash"}); core={"evidence":res["evidence"],"measurements":res["measurements"],"operationCounts":res["operationCounts"],"verdict":res["verdict"],"baseFailure":res["baseFailure"]}; coreself=res["evidenceCoreHash"]==ch(core)
 tools=[]
 for item in rec["tools"].values():
  current=sha(root/item["uri"]) if (root/item["uri"]).is_file() else None; frozen=blob(root,rec["toolFreezeCommit"],item["uri"]); tools.append({"uri":item["uri"],"match":current==frozen==item["sha256"]})
 parents=[]
 for item in rec["parentObservations"]:
  path=resolved(root,item["uri"]); parents.append({"uri":item["uri"],"match":path.is_file() and sha(path)==item["expectedSha256"]==item["observedSha256"]})
 runtimes=[]
 for name,item in rec["runtimeObservations"].items():
  path=resolved(root,item["uri"]); runtimes.append({"name":name,"match":path.is_file() and sha(path)==item["expectedSha256"]==item["observedSha256"] and path.stat().st_size==item["observedBytes"]})
 runs=[]
 for run in rec["producerRuns"]+rec["encoderRuns"]+rec["blenderRuns"]:
  rp=resolved(root,run["reportUri"]); report=json.loads(rp.read_text()) if rp.is_file() else None; match=bool(report and report==run["report"] and report_ok(report))
  if match and run["kind"]=="producer":
   for item in report["arrays"].values():
    path=resolved(root,item["uri"]); match=match and path.is_file() and sha(path)==item["sha256"] and path.stat().st_size==item["bytes"]
  elif match:
   item=report.get("output") or {}; path=resolved(root,item.get("uri","")); match=path.is_file() and sha(path)==item.get("sha256") and path.stat().st_size==item.get("bytes")
  runs.append({"kind":run["kind"],"fixtureId":run["fixtureId"],"producer":run["producer"],"repeat":run.get("repeat"),"match":bool(match)})
 artifacts=[]
 for d in res["diagnostics"]:
  for key in ("png","sidecar"):
   item=d[key]; path=resolved(root,item["uri"]); artifacts.append({"uri":item["uri"],"match":path.is_file() and sha(path)==item["sha256"] and path.stat().st_size==item["bytes"]})
 producer_replays=[]; encoder_replays=[]
 with tempfile.TemporaryDirectory(prefix="bfs-b52-d9-1-replay-") as td:
  t=Path(td)
  for f in spec["fixtures"]:
   fid=f["id"]
   for producer,exe,key in (("python",spec["runtime"]["python"]["executable"],"pythonProducer"),("node",spec["runtime"]["node"]["executable"],"nodeProducer")):
    od=t/producer/fid/"arrays"; rr=t/producer/fid/"report.json"; x=subprocess.run([exe,str(root/rec["tools"][key]["uri"]),"--spec",str(a.spec.resolve()),"--fixture",fid,"--output-dir",str(od),"--report",str(rr)],cwd=root,env=clean_env(root,spec,t),capture_output=True,text=True); formal=next(q for q in rec["producerRuns"] if q["fixtureId"]==fid and q["producer"]==producer); fdir=resolved(root,next(iter(formal["report"]["arrays"].values()))["uri"]).parent; exact=x.returncode==0 and all((od/n).is_file() and (od/n).read_bytes()==(fdir/n).read_bytes() for n in FILES); producer_replays.append({"fixtureId":fid,"producer":producer,"match":exact}); ex=t/producer/fid/"source.exr"; er=t/producer/fid/"encoder.json"; y=subprocess.run([spec["runtime"]["python"]["executable"],str(root/rec["tools"]["encoder"]["uri"]),"--spec",str(a.spec.resolve()),"--fixture",fid,"--producer",producer,"--input",str(od/"resolved.rgba32"),"--output",str(ex),"--report",str(er)],cwd=root,env=clean_env(root,spec,t),capture_output=True,text=True); encoder_replays.append({"fixtureId":fid,"producer":producer,"match":y.returncode==0 and ex.is_file() and ah(read_exr(ex))==sha(od/"resolved.rgba32")})
 experiments=root/"experiments"; experiments.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(prefix="bfs-b52-d9-1-analysis-",dir=experiments) as td:
  t=Path(td); ro=t/"results.json"; x=subprocess.run([spec["runtime"]["python"]["executable"],str(root/rec["tools"]["analyzer"]["uri"]),"--spec",str(a.spec.resolve()),"--receipt",str(a.receipt.resolve()),"--output",str(ro)],cwd=root,env=clean_env(root,spec,t),capture_output=True,text=True); replay=x.returncode==0 and ro.is_file() and ro.read_bytes()==a.result.read_bytes(); replay_art=[]
  if replay:
   for d in res["diagnostics"]:
    for key in ("png","sidecar"):
     actual=resolved(root,d[key]["uri"]); other=t/"diagnostics"/actual.name; replay_art.append({"uri":d[key]["uri"],"match":other.is_file() and other.read_bytes()==actual.read_bytes()})
 observed=first(res["evidence"],spec); verdict=spec["decisionRule"]["passVerdict"] if observed is None else spec["decisionRule"]["failVerdict"]; expected_counts={k:spec["processMatrix"][k] for k in res["operationCounts"]}; integrity={"receiptSelfHashExact":recself,"resultSelfHashExact":resself,"evidenceCoreHashExact":coreself,"frozenToolsExact":len(tools)==8 and all(x["match"] for x in tools),"parentsExact":len(parents)==5 and all(x["match"] for x in parents),"runtimesExact":len(runtimes)==4 and all(x["match"] for x in runtimes),"runArtifactsExact":len(runs)==32 and all(x["match"] for x in runs),"derivedArtifactsExact":len(artifacts)==40 and all(x["match"] for x in artifacts),"producerReplayExact":len(producer_replays)==8 and all(x["match"] for x in producer_replays),"encoderDecodedReplayExact":len(encoder_replays)==8 and all(x["match"] for x in encoder_replays),"analysisReplayByteExact":replay,"diagnosticReplayByteExact":len(replay_art)==40 and all(x["match"] for x in replay_art),"attackContractExact":res["attacksPassed"]==30 and len(res["attacks"])==30 and all(x["passed"] for x in res["attacks"]),"operationCountsExact":res["operationCounts"]==expected_counts,"scientificVerdictConsistent":res["baseFailure"]==observed and res["verdict"]==verdict}; passed=all(integrity.values()); body={"schemaVersion":"bfs.layerDepthTemporalHoldoutAudit.v0.1","status":"PASS" if passed else "FAIL","scientificVerdict":res["verdict"],"baseFailure":res["baseFailure"],"auditInterpretation":"PASS means evidence integrity and replay, not mandatory scientific support.","integrityChecks":integrity,"receipt":{"uri":str(a.receipt.resolve().relative_to(root)),"sha256":sha(a.receipt)},"result":{"uri":str(a.result.resolve().relative_to(root)),"sha256":sha(a.result)},"toolChecks":tools,"parentChecks":parents,"runtimeChecks":runtimes,"runChecks":runs,"artifactChecks":artifacts,"producerReplayChecks":producer_replays,"encoderReplayChecks":encoder_replays,"diagnosticReplayChecks":replay_art,"replayStdout":x.stdout.strip(),"failures":[] if passed else [k for k,v in integrity.items() if not v]}; audit={**body,"auditHash":ch(body)}; a.output.write_text(json.dumps(audit,indent=2,sort_keys=True,allow_nan=False)+"\n"); print(f"BFS_B52_D9_1_AUDIT {audit['status']} producers={sum(x['match'] for x in producer_replays)}/8 encoders={sum(x['match'] for x in encoder_replays)}/8 runs={sum(x['match'] for x in runs)}/32 scientific={res['verdict']}")
 if not passed: raise SystemExit(1)
if __name__=="__main__": main()
