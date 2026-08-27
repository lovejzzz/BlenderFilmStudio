#!/usr/bin/env python3
"""Single-use formal runner for B52-D12.3."""

from __future__ import annotations

import argparse, datetime as dt, hashlib, json, os, shutil, subprocess, time
from pathlib import Path


SPEC_SHA256="f1ffe5b4fe0912936b1e03677dd0985f11c34e6b5df4ddf70854533c4ad0b590"
def sha_file(path:Path)->str:
    d=hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda:h.read(1024*1024),b""): d.update(chunk)
    return d.hexdigest()
def canon(value:object)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def main()->None:
    p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--preflight",type=Path,required=True);p.add_argument("--output-root",type=Path,required=True);a=p.parse_args()
    repo=Path.cwd().resolve();spec_path=a.spec.resolve();preflight_path=a.preflight.resolve();root=a.output_root.resolve();spec=json.loads(spec_path.read_text());preflight=json.loads(preflight_path.read_text());pre_body={k:v for k,v in preflight.items() if k!="preflightHash"}
    if sha_file(spec_path)!=SPEC_SHA256 or preflight.get("preflightHash")!=canon(pre_body) or preflight.get("status")!="ACCEPTED":raise RuntimeError("D12.3 identity/admission mismatch")
    if root.exists():raise RuntimeError("refusing to reuse D12.3 formal root")
    tools={path:sha_file(repo/path) for path in spec["formalToolPaths"]}
    if tools!=preflight["toolHashes"]:raise RuntimeError("D12.3 tools differ from preflight")
    free=shutil.disk_usage(repo).free;projected=spec["diskAdmission"]["projectedWriteBytes"];reserve=spec["diskAdmission"]["minimumReserveBytes"]
    if free-projected<reserve:raise RuntimeError("D12.3 disk admission rejected")
    root.mkdir(parents=True,exist_ok=False);marker={"experimentId":spec["experimentId"],"createdAtUtc":dt.datetime.now(dt.timezone.utc).isoformat(),"pid":os.getpid(),"specSha256":SPEC_SHA256};marker_path=root/".formal-root-created.json";marker_path.write_text(json.dumps(marker,indent=2,sort_keys=True)+"\n")
    base_env={"PATH":os.environ.get("PATH",""),"LANG":"C.UTF-8","LC_ALL":"C.UTF-8","OCIO":str((repo/spec["runtime"]["ocio"]["uri"]).resolve())};children=[];started=time.monotonic()
    def child(role:str,cell:str,argv:list[str],env:dict[str,str]|None=None)->dict:
        logs=root/"logs"/role.lower();logs.mkdir(parents=True,exist_ok=True);safe=cell.replace("/","_");out=logs/f"{safe}.stdout.log";err=logs/f"{safe}.stderr.log";tick=time.monotonic();proc=subprocess.Popen(argv,cwd=repo,env=env or base_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);stdout,stderr=proc.communicate();out.write_text(stdout);err.write_text(stderr);row={"role":role,"cell":cell,"pid":proc.pid,"exitCode":proc.returncode,"elapsedSeconds":round(time.monotonic()-tick,6),"argv":argv,"stdout":{"uri":str(out),"sha256":sha_file(out)},"stderr":{"uri":str(err),"sha256":sha_file(err)}};children.append(row);print(f"BFS_D123_CHILD role={role} cell={cell} pid={proc.pid} exit={proc.returncode}",flush=True)
        if proc.returncode!=0:
            failure={"schemaVersion":"bfs.blenderStaticNonplanarMultiownerFailure.v0.1","experimentId":spec["experimentId"],"failedChild":row,"completedChildren":children,"specSha256":SPEC_SHA256,"preflightSha256":sha_file(preflight_path),"formalRootMarkerSha256":sha_file(marker_path)};failure["failureHash"]=canon(failure);(root/"run.failure.json").write_text(json.dumps(failure,indent=2,sort_keys=True)+"\n");raise RuntimeError(f"D12.3 child failed: {role} {cell}")
        return row
    blender=spec["runtime"]["blender"]["executable"];python=spec["runtime"]["python"]["executable"];node=spec["runtime"]["node"]["executable"]
    source=str(repo/"blender/render_b52_d12_3_nonplanar_multiowner_source.py");adapter=str(repo/"scripts/adapt-b52-d12-3-nonplanar-multiowner.py");py_consumer=str(repo/"scripts/reconstruct-b52-d12-3-nonplanar-multiowner.py");node_consumer=str(repo/"scripts/reconstruct-b52-d12-3-nonplanar-multiowner.mjs")
    typed_spec=str((repo/spec["parents"]["typedEnvelopeSpec"]["uri"]).resolve());typed_py=str((repo/spec["parents"]["typedEnvelopePython"]["uri"]).resolve());typed_node=str((repo/spec["parents"]["typedEnvelopeNode"]["uri"]).resolve())
    for fixture in spec["fixtures"]:
        fid=fixture["id"]
        for repeat in (1,2):
            for frame in (0,1):
                cell=f"{fid}/R{repeat}/F{frame}";sdir=root/"sources"/fid/f"R{repeat}"/f"frame-{frame}";runtime=root/"runtime"/fid/f"R{repeat}"/f"frame-{frame}";env={**base_env}
                for key,suffix in (("TMPDIR","tmp"),("BLENDER_USER_CONFIG","config"),("BLENDER_USER_SCRIPTS","scripts")):
                    target=runtime/suffix;target.mkdir(parents=True,exist_ok=True);env[key]=str(target)
                child("SOURCE",cell,[blender,*spec["runtime"]["blender"]["launchFlags"],"--python",source,"--","--spec",str(spec_path),"--fixture",fid,"--frame",str(frame),"--repeat",str(repeat),"--output-exr",str(sdir/"source.exr"),"--report",str(sdir/"report.json")],env)
            adir=root/"adapters"/fid/f"R{repeat}";src=root/"sources"/fid/f"R{repeat}"
            child("ADAPTER",f"{fid}/R{repeat}",[python,adapter,"--spec",str(spec_path),"--fixture",fid,"--repeat",str(repeat),"--previous-exr",str(src/"frame-0/source.exr"),"--current-exr",str(src/"frame-1/source.exr"),"--previous-report",str(src/"frame-0/report.json"),"--current-report",str(src/"frame-1/report.json"),"--output-dir",str(adir/"arrays"),"--report",str(adir/"report.json")])
            for producer,exe,tool in (("python",python,py_consumer),("node",node,node_consumer)):
                cdir=root/"consumers"/producer/fid/f"R{repeat}";child(f"CONSUMER_{producer.upper()}",f"{fid}/R{repeat}",[exe,tool,"--spec",str(spec_path),"--fixture",fid,"--repeat",str(repeat),"--input-dir",str(adir/"arrays"),"--adapter-report",str(adir/"report.json"),"--output-dir",str(cdir/"arrays"),"--report",str(cdir/"report.json")]);edir=root/"envelopes"/producer/fid/f"R{repeat}"
                child("ENVELOPE_PYTHON",f"{producer}/{fid}/R{repeat}",[python,typed_py,"--spec",typed_spec,"--input",str(cdir/"report.json"),"--output",str(edir/"report.python-envelope.json")]);child("ENVELOPE_NODE",f"{producer}/{fid}/R{repeat}",[node,typed_node,"--spec",typed_spec,"--input",str(cdir/"report.json"),"--output",str(edir/"report.node-envelope.json")])
    execution={"schemaVersion":"bfs.blenderStaticNonplanarMultiownerExecution.v0.1","experimentId":spec["experimentId"],"rootCreatedFresh":True,"formalRootMarker":{"uri":str(marker_path),"sha256":sha_file(marker_path)},"spec":{"uri":str(spec_path),"sha256":sha_file(spec_path)},"preflight":{"uri":str(preflight_path),"sha256":sha_file(preflight_path),"preflightHash":preflight["preflightHash"]},"toolFreezeCommit":preflight["toolFreezeCommit"],"toolHashes":tools,"diskAdmission":{"availableBytes":free,"projectedWriteBytes":projected,"minimumReserveBytes":reserve,"freeAfterProjectedBytes":free-projected,"status":"ACCEPTED"},"children":children};execution["executionHash"]=canon(execution);execution_path=root/"execution.json";execution_path.write_text(json.dumps(execution,indent=2,sort_keys=True,allow_nan=False)+"\n")
    child("ANALYZER","FORMAL",[python,str(repo/"scripts/analyze-b52-d12-3-nonplanar-multiowner.py"),"--spec",str(spec_path),"--root",str(root),"--preflight",str(preflight_path),"--execution",str(execution_path),"--output",str(root/"results.json")]);result=json.loads((root/"results.json").read_text());pids=[row["pid"] for row in children];process_ok=len(children)==spec["processBoundary"]["expectedUniqueChildProcesses"] and len(set(pids))==len(pids)
    operations={"sourceRenders":sum(r["role"]=="SOURCE" for r in children),"adapters":sum(r["role"]=="ADAPTER" for r in children),"pythonConsumers":sum(r["role"]=="CONSUMER_PYTHON" for r in children),"nodeConsumers":sum(r["role"]=="CONSUMER_NODE" for r in children),"pythonEnvelopeEncoders":sum(r["role"]=="ENVELOPE_PYTHON" for r in children),"nodeEnvelopeEncoders":sum(r["role"]=="ENVELOPE_NODE" for r in children),"analyzers":sum(r["role"]=="ANALYZER" for r in children),"modelCalls":0,"networkCalls":0}
    body={"schemaVersion":"bfs.blenderStaticNonplanarMultiownerReceipt.v0.1","experimentId":spec["experimentId"],"executedAtUtc":dt.datetime.now(dt.timezone.utc).isoformat(),"elapsedSeconds":round(time.monotonic()-started,6),"spec":{"uri":str(spec_path),"sha256":sha_file(spec_path)},"preflight":{"uri":str(preflight_path),"sha256":sha_file(preflight_path),"preflightHash":preflight["preflightHash"]},"execution":{"uri":str(execution_path),"sha256":sha_file(execution_path),"executionHash":execution["executionHash"]},"result":{"uri":str(root/"results.json"),"sha256":sha_file(root/"results.json"),"evidenceHash":result["evidenceHash"],"verdict":result["verdict"]},"toolFreezeCommit":preflight["toolFreezeCommit"],"toolHashes":tools,"processes":{"expected":spec["processBoundary"]["expectedUniqueChildProcesses"],"observed":len(children),"unique":len(set(pids)),"passed":process_ok,"children":children},"operationCounts":operations};receipt={**body,"receiptHash":canon(body)};(root/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+"\n")
    if not process_ok:raise RuntimeError("D12.3 process totality failure")
    print(f"BFS_B52_D123_FORMAL_COMPLETE verdict={result['verdict']} exactZero={result['exactZeroObservation']} receipt={receipt['receiptHash']}")


if __name__=="__main__":main()
