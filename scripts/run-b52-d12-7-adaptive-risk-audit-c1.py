#!/usr/bin/env python3
"""Single-use audit-only correction runner for B52-D12.7-AUDIT-C1."""
from __future__ import annotations

import argparse, datetime as dt, hashlib, json, os, shutil, subprocess, time
from pathlib import Path

CORRECTION_SPEC_SHA256="d66a40dffd8688e28d1887a2b6834e55f8345c9a5ca3bcca3c099fdebc223678"
def sha(path:Path)->str:
 digest=hashlib.sha256()
 with path.open("rb") as handle:
  for chunk in iter(lambda:handle.read(1048576),b""):digest.update(chunk)
 return digest.hexdigest()
def sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def canon(value:object)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def self_ok(document:dict,field:str)->bool:return document.get(field)==canon({k:v for k,v in document.items() if k!=field})

def main()->None:
 parser=argparse.ArgumentParser();parser.add_argument("--correction-spec",type=Path,required=True);parser.add_argument("--tool-freeze-commit",required=True);args=parser.parse_args();repo=Path.cwd().resolve();correction_path=args.correction_spec.resolve();correction=json.loads(correction_path.read_text())
 if sha(correction_path)!=CORRECTION_SPEC_SHA256:raise RuntimeError("D12.7 C1 correction spec mismatch")
 audit_output=(repo/correction["outputs"]["audit"]).resolve();receipt_output=(repo/correction["outputs"]["receipt"]).resolve()
 if audit_output.exists() or receipt_output.exists():raise RuntimeError("refusing to overwrite D12.7 C1 output")
 runtime=Path(correction["runtime"]["pythonExecutable"])
 if sha(runtime)!=correction["runtime"]["pythonSha256"]:raise RuntimeError("D12.7 C1 Python identity mismatch")
 parent_before={};documents={}
 for name,row in correction["parents"].items():
  path=(repo/row["uri"]).resolve()
  if not path.is_file() or sha(path)!=row["sha256"]:raise RuntimeError(f"D12.7 C1 parent mismatch: {name}")
  parent_before[name]=sha(path)
  if path.suffix==".json":documents[name]=json.loads(path.read_text())
 for name,field in (("execution","executionHash"),("result","evidenceHash"),("failedAudit","auditHash"),("failure","failureHash")):
  if documents[name].get(field)!=correction["parents"][name][field] or not self_ok(documents[name],field):raise RuntimeError(f"D12.7 C1 parent internal mismatch: {name}")
 original_blob=subprocess.run(["git","show",f"{correction['parents']['originalAuditTool']['gitCommit']}:{correction['parents']['originalAuditTool']['uri']}"],cwd=repo,capture_output=True)
 if original_blob.returncode!=0 or sha_bytes(original_blob.stdout)!=correction["parents"]["originalAuditTool"]["sha256"]:raise RuntimeError("D12.7 C1 original audit Git blob mismatch")
 tools=("scripts/audit-b52-d12-7-adaptive-risk-c1.py","scripts/run-b52-d12-7-adaptive-risk-audit-c1.py");tool_hashes={};git_hashes={}
 for relative in tools:
  payload=(repo/relative).read_bytes();blob=subprocess.run(["git","show",f"{args.tool_freeze_commit}:{relative}"],cwd=repo,capture_output=True);tool_hashes[relative]=sha_bytes(payload);git_hashes[relative]=sha_bytes(blob.stdout) if blob.returncode==0 else None
  if blob.returncode!=0 or payload!=blob.stdout:raise RuntimeError(f"D12.7 C1 corrected tool not frozen: {relative}")
 free=shutil.disk_usage(repo).free;projected=correction["diskAdmission"]["projectedWriteBytes"];reserve=correction["diskAdmission"]["minimumReserveBytes"]
 if free-projected<reserve:raise RuntimeError("D12.7 C1 disk admission rejected")
 original_spec=(repo/correction["parents"]["d12_7Spec"]["uri"]).resolve();execution=(repo/correction["parents"]["execution"]["uri"]).resolve();result=(repo/correction["parents"]["result"]["uri"]).resolve();formal_root=result.parent;audit_tool=repo/tools[0];started=time.monotonic();env={"PATH":os.environ.get("PATH",""),"LANG":"C.UTF-8","LC_ALL":"C.UTF-8"}
 command=[str(runtime),str(audit_tool),"--correction-spec",str(correction_path),"--spec",str(original_spec),"--root",str(formal_root),"--execution",str(execution),"--result",str(result),"--output",str(audit_output)];process=subprocess.run(command,cwd=repo,env=env,capture_output=True,text=True);parent_after={name:sha((repo/row["uri"]).resolve()) for name,row in correction["parents"].items()};immutable=parent_before==parent_after;audit=json.loads(audit_output.read_text()) if audit_output.is_file() else None
 gates=correction["gates"];audit_ok=process.returncode==0 and audit is not None and self_ok(audit,"auditHash") and audit.get("passed") is True and audit.get("payloadReplayPassed")==gates["payloadReplayPassed"] and audit.get("processTotalityPassed")==gates["processTotalityPassed"] and audit.get("expectedVerdict")==gates["expectedVerdict"] and audit.get("mutationAttackPassed")==gates["mutationAttackPassed"] and audit.get("mutationAttackTotal")==gates["mutationAttackTotal"] and audit.get("operationCounts",{}).get("modelCalls")==0 and audit.get("operationCounts",{}).get("networkCalls")==0
 execution_doc=documents["execution"];result_doc=documents["result"];pids=[row["pid"] for row in execution_doc["children"]]+[result_doc["analyzerPid"],audit.get("auditPid") if audit else None];process_totality=len(pids)==56 and len(set(pids))==56 and all(row["exitCode"]==0 for row in execution_doc["children"])
 passed=audit_ok and immutable and process_totality;body={"schemaVersion":"bfs.blenderStaticAdaptiveRiskGateAuditCorrectionReceipt.v0.1","experimentId":correction["experimentId"],"executedAtUtc":dt.datetime.now(dt.timezone.utc).isoformat(),"runnerPid":os.getpid(),"elapsedSeconds":round(time.monotonic()-started,6),"passed":passed,"correctionSpec":{"uri":str(correction_path),"sha256":sha(correction_path)},"toolFreezeCommit":args.tool_freeze_commit,"toolHashes":tool_hashes,"gitBlobHashes":git_hashes,"parentsBefore":parent_before,"parentsAfter":parent_after,"immutableParents":immutable,"diskAdmission":{"availableBytes":free,"projectedWriteBytes":projected,"minimumReserveBytes":reserve,"freeAfterProjectedBytes":free-projected,"status":"ACCEPTED"},"child":{"role":"AUDIT_C1","pid":audit.get("auditPid") if audit else None,"exitCode":process.returncode,"argv":command,"stdout":process.stdout,"stdoutSha256":sha_bytes(process.stdout.encode()),"stderr":process.stderr,"stderrSha256":sha_bytes(process.stderr.encode())},"processTotality":{"expected":56,"observed":len(pids),"unique":len(set(pids)),"passed":process_totality},"result":{"uri":str(result),"sha256":sha(result),"evidenceHash":result_doc["evidenceHash"],"verdict":result_doc["verdict"]},"correctedAudit":{"uri":str(audit_output),"sha256":sha(audit_output) if audit_output.is_file() else None,"auditHash":audit.get("auditHash") if audit else None,"passed":audit.get("passed") if audit else False},"operationCounts":correction["operations"],"nonClaims":correction["nonClaims"]};receipt={**body,"receiptHash":canon(body)};receipt_output.write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D127_AUDIT_C1_{'COMPLETE' if passed else 'FAILED'} attacks={audit.get('mutationAttackPassed') if audit else 0}/{audit.get('mutationAttackTotal') if audit else 0} receipt={receipt['receiptHash']}")
 if not passed:raise SystemExit(1)

if __name__=="__main__":main()
